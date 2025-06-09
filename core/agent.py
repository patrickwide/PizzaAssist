# --- Standard Library ---
import json
import time

# --- Type Hinting ---
from typing import Optional

# --- Third-Party Libraries ---
import ollama

# --- Application Config & Constants ---
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS

# --- Core Application Modules ---
from core.memory import ChatHistoryManager

# --- Logging ---
from logging_config import setup_logger

logger = setup_logger(__name__)

# --- Agent Runner ---
async def run_agent(model: str, user_input: str, memory: ChatHistoryManager, system_message: Optional[str] = None):
    """
    Orchestrates a chat session with Ollama, allowing an optional system prompt.

    Args:
        model (str): The Ollama model to use (e.g., "llama3.2").
        user_input (str): The latest user message/content.
        memory (AgentMemory): The agent’s memory, storing past messages and tool-call history.
        system_message (Optional[str]): An optional “system” message to prime the assistant.
    Yields:
        Dict[str, Any]: A sequence of status updates and content strings for each stage:
            - initial_response: The LLM’s first reply (or error).
            - tool_result: Results of any tool invocation (or error).
            - final_response: The LLM’s final reply after tool usage (or warning/error).
    """

    client = ollama.AsyncClient()

    # Only add system message if there are no messages in memory AND a system message is provided
    recent_messages = memory.get_recent_messages()
    if system_message and len(recent_messages) == 0:
        logger.debug("Adding system message as first message in conversation.")
        memory.add_message({"role": "system", "content": system_message})

    memory.add_message({"role": "user", "content": user_input})
    messages = memory.get_recent_messages()
    tools = TOOL_DEFINITIONS

    logger.debug("Sending request to LLM...")
    logger.debug(f"Sending Messages: {json.dumps(messages, indent=2)}")
    logger.debug(f"Sending Tools: {json.dumps(tools, indent=2)}")

    try:
        response = await client.chat(
            model=model,
            messages=messages,
            tools=tools,
        )

        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        logger.debug(f"LLM Raw Response: {json.dumps(response_dict, indent=2)}")

        if not response_dict or "message" not in response_dict:
            logger.error("No message in LLM response.")
            memory.add_message({"role": "system", "content": "No response from LLM."})
            yield {"status": "error", "stage": "initial_response", "content": "No response from LLM."}
            return

    except Exception as e:
        logger.error(f"Error calling Ollama chat API: {e}")
        memory.add_message({"role": "system", "content": f"Error contacting LLM: {e}"})
        yield {"status": "error", "stage": "initial_call", "error": str(e)}
        return

    message = response_dict["message"]
    memory.add_message(message)


    # Process LLM message response
    if message.get("content") and not message.get("tool_calls"):
        # Case: Normal assistant message with no tool usage
        yield {
            "status": "success",
            "stage": "initial_response",
            "content": message["content"]
        }
        logger.info("LLM Response (no tool call).")
        return

    elif message.get("tool_calls"):
        # Case: Assistant invoked tool(s)
        for tool_call in message["tool_calls"]:
            yield {
                "status": "success",
                "stage": "tool_call",
                "tool": tool_call["function"]["name"],  # e.g., "query_documents"
                "arguments": tool_call["function"]["arguments"],
                "content": message.get("content", "")  # optional, if content accompanies the tool call
            }
        logger.info("LLM decided to use tool(s).")


    logger.info("LLM decided to use tool(s).")
    tool_calls_to_process = list(message.get("tool_calls", []))

    for tool_call in tool_calls_to_process:
        function_info = tool_call.get("function", {})
        function_name = function_info.get("name")
        raw_function_args = function_info.get("arguments")
        tool_call_id = tool_call.get("id")

        if not function_name or raw_function_args is None:
            logger.error(f"Invalid tool call structure: {tool_call}")
            err_content = {"error": "Invalid tool call structure"}
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name or "unknown", "content": json.dumps(err_content)})
            yield {"status": "error", "stage": "tool_call", "tool": function_name, "error": err_content}
            continue

        # Parse args
        function_args = None
        if isinstance(raw_function_args, dict):
            function_args = raw_function_args
        elif isinstance(raw_function_args, str):
            try:
                function_args = json.loads(raw_function_args)
            except json.JSONDecodeError as e:
                err = f"Malformed JSON: {raw_function_args}"
                logger.error(err)
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
                yield {"status": "error", "stage": "tool_args", "tool": function_name, "error": err}
                continue
        else:
            err = f"Unexpected type for args: {type(raw_function_args)}"
            logger.error(err)
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
            yield {"status": "error", "stage": "tool_args", "tool": function_name, "error": err}
            continue

        if function_args is None:
            continue

        attempt_count = memory.record_function_attempt(function_name, function_args)
        logger.info(f"Calling: {function_name} (attempt {attempt_count})")

        if function_name in AVAILABLE_FUNCTIONS:
            try:
                function_to_call = AVAILABLE_FUNCTIONS[function_name]
                function_response = function_to_call(**function_args)

                if isinstance(function_response, dict):
                    function_response = json.dumps(function_response)

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": function_response,
                }
                memory.add_message(tool_message)
                logger.info(f"{function_name} executed.")
                yield {
                    "status": "success",
                    "stage": "tool_result",
                    "tool": function_name,
                    "response": function_response,
                }

            except TypeError as e:
                err = f"Argument mismatch: {e}"
                logger.error(err)
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
                yield {"status": "error", "stage": "tool_exec", "tool": function_name, "error": err}
            except Exception as e:
                err = f"Runtime error: {e}"
                logger.error(err)
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
                yield {"status": "error", "stage": "tool_exec", "tool": function_name, "error": err}
        else:
            err = f"Function '{function_name}' not implemented"
            logger.error(err)
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
            yield {"status": "error", "stage": "tool_missing", "tool": function_name, "error": err}

  # --- Final LLM response (WITH UNWRAPPING) ---
    logger.info("Sending updated history for final LLM response...")
    try:
        final_response = await client.chat(
            model=model,
            messages=memory.get_recent_messages(),
            tools=tools,
        )

        # Convert top‐level final_response into a dict if needed
        final_dict = final_response.model_dump() if hasattr(final_response, "model_dump") else final_response

        # Unwrap the nested Message object (if present)
        raw_final_msg = final_dict.get("message", {})
        if hasattr(raw_final_msg, "model_dump"):
            final_message = raw_final_msg.model_dump()
        elif isinstance(raw_final_msg, dict):
            final_message = raw_final_msg
        else:
            final_message = {
                "role": getattr(raw_final_msg, "role", ""),
                "content": getattr(raw_final_msg, "content", ""),
                "tool_calls": getattr(raw_final_msg, "tool_calls", []),
            }

        if final_message.get("content"):
            memory.add_message(final_message)
            logger.info("Final response received.")
            yield {
                "status": "success",
                "stage": "final_response",
                "content": final_message["content"],
            }
        else:
            logger.warning("No content in final response.")
            yield {
                "status": "warning",
                "stage": "final_response",
                "content": None,
            }

    except Exception as e:
        err = f"Final response error: {e}"
        logger.error(err)
        memory.add_message({"role": "system", "content": f"Final response error: {e}"})
        yield {"status": "error", "stage": "final_response", "error": str(e)}