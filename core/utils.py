from config import TOOL_DEFINITIONS

def print_tool_definitions():
    """Print all available tool definitions"""
    print("\n=== Available Tool Definitions ===")
    if not TOOL_DEFINITIONS:
        print("No tool definitions available.")
        return
        
    for tool in TOOL_DEFINITIONS:
        if "function" in tool:
            func = tool["function"]
            print(f"\nTool: {func.get('name', 'Unnamed')}")
            print(f"Description: {func.get('description', 'No description')}")
            if 'parameters' in func:
                print("Parameters:")
                for param_name, param_details in func["parameters"].get("properties", {}).items():
                    required = param_name in func["parameters"].get("required", [])
                    print(f"  - {param_name}: {param_details.get('description', 'No description')} {'(Required)' if required else '(Optional)'}")
    print("\n================================")