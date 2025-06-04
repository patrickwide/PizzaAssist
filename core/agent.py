# --- Standard Library ---
import json
from typing import Any, Dict

# --- Third-Party Libraries ---
import ollama

# --- Application Config & Constants ---
from config import (
    TOOL_DEFINITIONS,
    AVAILABLE_FUNCTIONS,
)

# --- Core Application Modules ---
from memory import AgentMemory

def format_tool_response(response_str: str) -> str:
    """Format tool response for better readability in logs."""
    print(f"--- Agent --- Raw Tool Response: {response_str}") # Log the raw response for debugging
    try:
        # Try to parse as JSON for pretty printing
        data = json.loads(response_str)
        if isinstance(data, list):
            return "\nReceived documents:\n" + "\n".join(
                f"- Content: {doc.get('content', 'No content')}\n  Metadata: {doc.get('metadata', 'No metadata')}"
                for doc in data
            )
        elif isinstance(data, dict):
            if "error" in data:
                return f"\nError Response: {data['error']}"
            elif "message" in data:
                return f"\nMessage: {data['message']}"
            else:
                return "\nResponse data:\n" + json.dumps(data, indent=2)
        return f"\nRaw response:\n{response_str}"
    except json.JSONDecodeError:
        return f"\nNon-JSON response:\n{response_str}"

# --- Agent Runner ---
async def run_agent(model: str, user_input: str, memory: AgentMemory):
    client = ollama.AsyncClient()

    memory.add_message({"role": "user", "content": user_input})
    messages = memory.get_recent_messages()

    # Define available tools
    tools = TOOL_DEFINITIONS

    print("\n--- Agent --- Sending request to LLM...")
    try:
        response = await client.chat(
            model=model,
            messages=messages,
            tools=tools,
        )
    except Exception as e:
        print(f"Error calling Ollama chat API: {e}")
        memory.add_message({"role": "system", "content": f"Error contacting LLM: {e}"})
        return

    memory.add_message(response["message"])

    if not response["message"].get("tool_calls"):
        print("\n--- Agent --- LLM Response (no tool call):")
        print(response["message"]["content"])
        return

    print("\n--- Agent --- LLM decided to use a tool.")
    available_functions = AVAILABLE_FUNCTIONS

    tool_calls_to_process = list(response["message"].get("tool_calls", []))

    for tool_call in tool_calls_to_process:
        # Robustly access potentially missing keys
        function_info = tool_call.get("function", {})
        function_name = function_info.get("name")
        raw_function_args = function_info.get("arguments")
        tool_call_id = tool_call.get("id")

        if not function_name or raw_function_args is None:
            print(f"--- Agent --- ERROR: Invalid tool call structure received: {tool_call}")
            err_content = json.dumps({"error": "Received invalid tool call structure from LLM."})
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name or "unknown", "content": err_content})
            continue

        function_args = None
        print(f"--- Agent --- Attempting Tool Call: {function_name}")

        if isinstance(raw_function_args, dict):
            print("--- Agent --- Arguments received as dict.")
            function_args = raw_function_args
        elif isinstance(raw_function_args, str):
            print("--- Agent --- Arguments received as string, attempting JSON parse.")
            try:
                function_args = json.loads(raw_function_args)
            except json.JSONDecodeError:
                print(f"--- Agent --- ERROR: Could not parse function arguments string: {raw_function_args}")
                err_content = json.dumps({"error": f"Malformed arguments JSON received: {raw_function_args}"})
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": err_content})
                continue
        else:
            print(f"--- Agent --- ERROR: Unexpected type for function arguments: {type(raw_function_args)}")
            err_content = json.dumps({"error": f"Unexpected argument type: {type(raw_function_args)}"})
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": err_content})
            continue

        if function_args is None:
            continue

        attempt_count = memory.record_function_attempt(function_name, function_args)
        print(f"--- Agent --- Calling: {function_name} (attempt {attempt_count}) | Args: {function_args}")

        if function_name in available_functions:
            function_to_call = available_functions[function_name]
            try:
                function_response = function_to_call(**function_args)
                print(f"--- Agent --- Function {function_name} executed.")
                
                # Add detailed response logging
                print("--- Agent --- Tool Response:", format_tool_response(function_response))
                
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": function_response,
                }
                memory.add_message(tool_message)
                print(f"--- Agent --- Added tool response to memory.")

            except TypeError as e:
                print(f"Error calling function {function_name} due to argument mismatch: {e}")
                error_content = json.dumps({"error": f"Argument mismatch calling {function_name}: {str(e)}. Check if LLM provided all required args correctly. Provided: {function_args}"})
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": error_content})
            except Exception as e:
                print(f"Error executing function {function_name}: {e}")
                error_content = json.dumps({"error": f"Runtime error calling function {function_name}: {str(e)}"})
                memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": error_content})
        else:
            print(f"Error: Function '{function_name}' not found in available_functions.")
            error_content = json.dumps({"error": f"Function '{function_name}' is not implemented."})
            memory.add_message({"role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": error_content})

    # After processing ALL tool calls, send updated history back to LLM
    print("\n--- Agent --- Sending updated conversation history to LLM for final response...")
    try:
        if not memory.get_recent_messages():
            print("--- Agent --- Error: No messages in history to send for final response.")
            return

        final_response = await client.chat(
            model=model,
            messages=memory.get_recent_messages(),
        )
        
        if final_response["message"].get("content"):
            memory.add_message(final_response["message"])
            print("\n--- Agent --- Final LLM Response:\n")
            print(final_response["message"]["content"])
        else:
            print("\n--- Agent --- LLM provided no final content response (might happen after tool error).")

    except Exception as e:
        print(f"Error getting final response from Ollama: {e}")
        memory.add_message({"role": "system", "content": f"Error getting final LLM response: {e}"})