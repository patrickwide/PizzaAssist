# --- Standard Library ---
import json
import time
import uuid
from datetime import datetime

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
async def run_agent(
    model: str,
    user_input: str,
    memory: ChatHistoryManager,
    session_id: Optional[str] = None,
    system_message: Optional[str] = None,
    user_input_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    conversation_id: Optional[str] = None
):
    """
    Orchestrates a chat session with Ollama, allowing an optional system prompt.

    Args:
        model (str): The Ollama model to use (e.g., "llama3.2").
        user_input (str): The latest user message/content.
        memory (ChatHistoryManager): The agent's memory, storing past messages and tool-call history.
        session_id (Optional[str]): The session ID for this conversation. If None, a new one is generated.
        system_message (Optional[str]): An optional "system" message to prime the assistant.
    Yields:
        Dict[str, Any]: A sequence of status updates and content strings for each stage:
            - initial_response: The LLM's first reply (or error).
            - tool_result: Results of any tool invocation (or error).
            - final_response: The LLM's final reply after tool usage (or warning/error).
    """

    # Generate session ID if not provided
    if session_id is None:
        session_id = str(uuid.uuid4())
        logger.debug(f"Generated new session ID: {session_id}")

    # Generate correlation IDs if not provided
    if user_input_id is None:
        user_input_id = str(uuid.uuid4())
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    client = ollama.AsyncClient()

    # Load existing messages from memory
    recent_messages = memory.get_recent_messages(session_id)
    
    # Only add system message if there are no messages AND a system message is provided
    if system_message and len(recent_messages) == 0:
        system_msg_id = str(uuid.uuid4())
        logger.debug("Adding system message as first message in conversation.")
        memory.add_message(session_id, {
            "role": "system", 
            "content": system_message,
            "message_id": system_msg_id,
            "conversation_id": conversation_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat()
        })
        parent_id = system_msg_id

    # Add the new user message
    user_msg_id = str(uuid.uuid4())
    user_message = {
        "role": "user", 
        "content": user_input,
        "message_id": user_msg_id,
        "parent_id": parent_id,
        "conversation_id": conversation_id,
        "user_input_id": user_input_id,
        "sequence": memory.next_sequence(session_id),
        "timestamp": datetime.now().isoformat()
    }
    memory.add_message(session_id, user_message)
    parent_id = user_msg_id

    # Get all messages for context
    messages = memory.get_recent_messages(session_id)
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
            error_msg = {
                "role": "system", 
                "content": "No response from LLM.",
                "message_id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat()
            }
            memory.add_message(session_id, error_msg)
            yield {
                "status": "error", 
                "stage": "initial_response", 
                "content": "No response from LLM.",
                "message_id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat()
            }
            return

    except Exception as e:
        logger.error(f"Error calling Ollama chat API: {e}")
        error_msg = {
            "role": "system", 
            "content": f"Error contacting LLM: {e}",
            "message_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat()
        }
        memory.add_message(session_id, error_msg)
        yield {
            "status": "error", 
            "stage": "initial_call", 
            "error": str(e),
            "message_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat()
        }
        return

    # Add correlation fields to the message
    message = response_dict["message"]
    message["message_id"] = str(uuid.uuid4())
    message["parent_id"] = parent_id
    message["conversation_id"] = conversation_id
    message["user_input_id"] = user_input_id
    message["sequence"] = memory.next_sequence(session_id)
    message["timestamp"] = datetime.now().isoformat()
    parent_id = message["message_id"]

    # Ensure message has a role field
    if "role" not in message:
        message["role"] = "assistant"
        
    memory.add_message(session_id, message)

    # Process LLM message response
    if message.get("content") and not message.get("tool_calls"):
        # Case: Normal assistant message with no tool usage
        yield {
            "status": "success",
            "stage": "initial_response",
            "content": message["content"],
            "message_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        logger.info("LLM Response (no tool call).")
        return

    elif message.get("tool_calls"):
        # Case: Assistant invoked tool(s)
        logger.info("LLM decided to use tool(s).")
        tool_calls_to_process = list(message.get("tool_calls", []))
        
        for tool_call in tool_calls_to_process:
            function_info = tool_call.get("function", {})
            function_name = function_info.get("name")
            raw_function_args = function_info.get("arguments")
            # Generate tool_call_id only once and reuse it
            tool_call_id = str(uuid.uuid4())
            tool_call_msg_id = str(uuid.uuid4())
            
            # Send initial tool call message
            yield {
                "status": "success",
                "stage": "tool_call",
                "tool": function_name,
                "arguments": raw_function_args,
                "content": message.get("content", ""),
                "message_id": tool_call_msg_id,
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "tool_call_id": tool_call_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }

            if not function_name or raw_function_args is None:
                logger.error(f"Invalid tool call structure: {tool_call}")
                err_content = {"error": "Invalid tool call structure"}
                memory.add_message(session_id, {
                    "role": "tool", 
                    "tool_call_id": tool_call_id,
                    "name": function_name or "unknown",
                    "content": json.dumps(err_content)
                })
                yield {
                    "status": "error",
                    "stage": "tool_call",
                    "tool": function_name,
                    "error": err_content,
                    "message_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "conversation_id": conversation_id,
                    "user_input_id": user_input_id,
                    "tool_call_id": tool_call_id,
                    "sequence": memory.next_sequence(session_id),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
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
                    memory.add_message(session_id, {"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
                    yield {"status": "error", "stage": "tool_args", "tool": function_name, "error": err, "tool_call_id": tool_call_id, "session_id": session_id}
                    continue
            else:
                err = f"Unexpected type for args: {type(raw_function_args)}"
                logger.error(err)
                memory.add_message(session_id, {"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": err})})
                yield {"status": "error", "stage": "tool_args", "tool": function_name, "error": err, "tool_call_id": tool_call_id, "session_id": session_id}
                continue

            if function_args is None:
                continue

            attempt_count = memory.record_function_attempt(session_id, function_name, function_args)
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
                    memory.add_message(session_id, tool_message)
                    logger.info(f"{function_name} executed.")
                    yield {
                        "status": "success",
                        "stage": "tool_result",
                        "tool": function_name,
                        "response": function_response,
                        "message_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "conversation_id": conversation_id,
                        "user_input_id": user_input_id,
                        "tool_call_id": tool_call_id,
                        "sequence": memory.next_sequence(session_id),
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id
                    }

                except TypeError as e:
                    err = f"Argument mismatch: {e}"
                    logger.error(err)
                    memory.add_message(session_id, {
                        "role": "tool", 
                        "tool_call_id": tool_call_id,
                        "name": function_name,
                        "content": json.dumps({"error": err}),
                        "message_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "conversation_id": conversation_id,
                        "user_input_id": user_input_id,
                        "sequence": memory.next_sequence(session_id)
                    })
                    yield {
                        "status": "error",
                        "stage": "tool_exec",
                        "tool": function_name,
                        "error": err,
                        "message_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "conversation_id": conversation_id,
                        "user_input_id": user_input_id,
                        "tool_call_id": tool_call_id,
                        "sequence": memory.next_sequence(session_id),
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id
                    }
                except Exception as e:
                    err = f"Runtime error: {e}"
                    logger.error(err)
                    memory.add_message(session_id, {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": function_name,
                        "content": json.dumps({"error": err}),
                        "message_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "conversation_id": conversation_id,
                        "user_input_id": user_input_id,
                        "sequence": memory.next_sequence(session_id)
                    })
                    yield {
                        "status": "error",
                        "stage": "tool_exec",
                        "tool": function_name,
                        "error": err,
                        "message_id": str(uuid.uuid4()),
                        "parent_id": parent_id,
                        "conversation_id": conversation_id,
                        "user_input_id": user_input_id,
                        "tool_call_id": tool_call_id,
                        "sequence": memory.next_sequence(session_id),
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id
                    }
            else:
                err = f"Function '{function_name}' not implemented"
                logger.error(err)
                memory.add_message(session_id, {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": json.dumps({"error": err}),
                    "message_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "conversation_id": conversation_id,
                    "user_input_id": user_input_id,
                    "sequence": memory.next_sequence(session_id)
                })
                yield {
                    "status": "error",
                    "stage": "tool_missing",
                    "tool": function_name,
                    "error": err,
                    "message_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "conversation_id": conversation_id,
                    "user_input_id": user_input_id,
                    "tool_call_id": tool_call_id,
                    "sequence": memory.next_sequence(session_id),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }

    # --- Final LLM response ---
    logger.info("Sending updated history for final LLM response...")
    try:
        final_response = await client.chat(
            model=model,
            messages=memory.get_recent_messages(session_id),
            tools=tools,
        )

        # Ensure consistent error handling with correlation IDs
        if not final_response:
            error_msg = "No response received from LLM for final message"
            logger.error(error_msg)
            yield {
                "status": "error",
                "stage": "final_response",
                "error": error_msg,
                "message_id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            return

        final_dict = final_response.model_dump() if hasattr(final_response, "model_dump") else final_response
        raw_final_msg = final_dict.get("message", {})
        
        if not raw_final_msg:
            error_msg = "Empty message received from LLM for final response"
            logger.error(error_msg)
            yield {
                "status": "error",
                "stage": "final_response",
                "error": error_msg,
                "message_id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            return
        
        # Process the final message
        final_message = raw_final_msg.model_dump() if hasattr(raw_final_msg, "model_dump") else (
            raw_final_msg if isinstance(raw_final_msg, dict) else {
                "role": getattr(raw_final_msg, "role", "assistant"),
                "content": getattr(raw_final_msg, "content", ""),
                "tool_calls": getattr(raw_final_msg, "tool_calls", [])
            }
        )

        # Add correlation fields to final message
        final_msg_id = str(uuid.uuid4())
        final_message.update({
            "message_id": final_msg_id,
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat()
        })

        content = final_message.get("content")
        if content is not None:  # Allow empty string but not None
            memory.add_message(session_id, final_message)
            logger.info("Final response received.")
            yield {
                "status": "success",
                "stage": "final_response",
                "content": content,
                "message_id": final_msg_id,
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
        else:
            warning_msg = "Final response missing content"
            logger.warning(warning_msg)
            yield {
                "status": "error",
                "stage": "final_response",
                "error": warning_msg,
                "message_id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "conversation_id": conversation_id,
                "user_input_id": user_input_id,
                "sequence": memory.next_sequence(session_id),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }

    except Exception as e:
        err = f"Final response error: {e}"
        logger.error(err)
        error_msg_id = str(uuid.uuid4())
        error_message = {
            "role": "system", 
            "content": err,
            "message_id": error_msg_id,
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat()
        }
        memory.add_message(session_id, error_message)
        yield {
            "status": "error", 
            "stage": "final_response", 
            "error": str(e),
            "message_id": error_msg_id,
            "parent_id": parent_id,
            "conversation_id": conversation_id,
            "user_input_id": user_input_id,
            "sequence": memory.next_sequence(session_id),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }