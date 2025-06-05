# --- Standard Library ---
from typing import List

# --- Application Config ---
from config import TOOL_DEFINITIONS

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def print_tool_definitions() -> List[str]:
    """Format and return tool definitions as a list of strings."""
    output = []
    output.append("\n=== Available Tool Definitions ===")
    
    if not TOOL_DEFINITIONS:
        message = "No tool definitions available."
        logger.warning(message)
        output.append(message)
        return output

    for tool in TOOL_DEFINITIONS:
        if "function" in tool:
            func = tool["function"]
            tool_name = func.get('name', 'Unnamed')
            description = func.get('description', 'No description')
            
            output.append(f"\nTool: {tool_name}")
            output.append(f"Description: {description}")
            
            if 'parameters' in func:
                output.append("Parameters:")
                for param_name, param_details in func["parameters"].get("properties", {}).items():
                    required = param_name in func["parameters"].get("required", [])
                    param_desc = param_details.get('description', 'No description')
                    req_status = '(Required)' if required else '(Optional)'
                    output.append(f"  - {param_name}: {param_desc} {req_status}")
    
    output.append("\n================================")
    
    # Log the full tool definitions at debug level
    logger.debug("Tool definitions loaded:\n%s", "\n".join(output))
    
    return output