# --- Standard Library ---
import json

# --- Third-Party Libraries ---
import ollama

# --- Application Config & Constants ---
from core.config import (
    TOOL_DEFINITIONS,
    AVAILABLE_FUNCTIONS,
)

# --- Core Application Modules ---
from core.memory import AgentMemory


# --- Agent Runner ---
async def run_agent(model: str, user_input: str, memory: AgentMemory):
    client = ollama.AsyncClient()

    memory.add_message({"role": "user", "content": user_input})
    messages = memory.get_recent_messages()

    # Define available tools
    tools = TOOL_DEFINITIONS

    print("\n--- Agent --- Sending request to LLM...")
    # print("--- Sending Messages:", json.dumps(messages, indent=2)) # DEBUG: See messages sent
    # print("--- Sending Tools:", json.dumps(tools, indent=2)) # DEBUG: See tools sent
    try:
        response = await client.chat(
            model=model,
            messages=messages,
            tools=tools,
        )
        print("--- LLM Raw Response:", json.dumps(response.model_dump(), indent=2)) # DEBUG: See raw response
        # Check if response contains a message
        if not response or "message" not in response:
            print("--- Agent --- Error: No message in LLM response.")
            memory.add_message({"role": "system", "content": "No response from LLM."})
            # return None
            return            

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
        tool_call_id = tool_call.get("id") # Use this if provided by Ollama

        if not function_name or raw_function_args is None:
             print(f"--- Agent --- ERROR: Invalid tool call structure received: {tool_call}")
             # Add minimal error message if possible
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
             continue # Skip if args are invalid

        attempt_count = memory.record_function_attempt(function_name, function_args)
        print(f"--- Agent --- Calling: {function_name} (attempt {attempt_count}) | Args: {function_args}")

        if function_name in available_functions:
            function_to_call = available_functions[function_name]
            try:
                function_response = function_to_call(**function_args)

                print(f"--- Agent --- Function {function_name} returned response: {function_response}")
                if isinstance(function_response, dict):
                    # Convert dict response to JSON string
                    function_response = json.dumps(function_response)

                print(f"--- Agent --- Function {function_name} executed.")
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name,
                    "content": function_response, # Should be JSON string
                }
                memory.add_message(tool_message)
                print(f"--- Agent --- Added tool response to memory.")

            except TypeError as e:
                 # More specific error for bad arguments passed to the python function
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
    # print("--- Sending Messages for Final Response:", json.dumps(memory.get_recent_messages(), indent=2)) # DEBUG
    try:
        # Ensure messages list is not empty before calling chat
        if not memory.get_recent_messages():
            print("--- Agent --- Error: No messages in history to send for final response.")
            return

        final_response = await client.chat(
            model=model,
            messages=memory.get_recent_messages(),
            # No tools needed here usually
        )
        # print("--- Final LLM Raw Response:", json.dumps(final_response, indent=2)) # DEBUG
        # Add the final response only if it contains content
        if final_response["message"].get("content"):
             memory.add_message(final_response["message"])
             print("\n--- Agent --- Final LLM Response:\n")
             print(final_response["message"]["content"])
        else:
             print("\n--- Agent --- LLM provided no final content response (might happen after tool error).")


    except Exception as e:
        print(f"Error getting final response from Ollama: {e}")
        memory.add_message({"role": "system", "content": f"Error getting final LLM response: {e}"})