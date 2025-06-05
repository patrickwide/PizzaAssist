# --- Standard Library ---
import json

# --- Third-Party Libraries ---
import ollama

# --- Application Config & Constants ---
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS

# --- Core Application Modules ---
from core.memory import AgentMemory

# --- Logging ---
from logging_config import setup_logger

logger = setup_logger(__name__)

# --- Agent Runner ---
async def run_agent(model: str, user_input: str, memory: AgentMemory):
    client = ollama.AsyncClient()

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
    yield {"status": "success", "stage": "initial_response", "content": message["content"]}

    if not message.get("tool_calls"):
        logger.info("LLM Response (no tool call).")
        return

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

    # Final LLM response
    logger.info("Sending updated history for final LLM response...")
    try:
        final_response = await client.chat(
            model=model,
            messages=memory.get_recent_messages(),
        )

        if final_response["message"].get("content"):
            memory.add_message(final_response["message"])
            logger.info("Final response received.")
            yield {
                "status": "success",
                "stage": "final_response",
                "content": final_response["message"]["content"],
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
