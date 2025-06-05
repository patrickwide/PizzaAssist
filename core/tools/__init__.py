import os
import sys
import importlib
from typing import Dict, Any, List, Tuple

def load_tools() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Dynamically load all tools from the tools directory.
    Returns a tuple of (tool_definitions, available_functions)
    """
    tool_definitions = []
    available_functions = {}
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add parent directories to Python path
    parent_dir = os.path.dirname(current_dir)  # core/
    root_dir = os.path.dirname(parent_dir)     # ai_app/
    sys.path.extend([current_dir, parent_dir, root_dir])
    
    # List all Python files in the directory
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            try:
                # Import the module using relative imports
                module = importlib.import_module(f'.{module_name}', package='core.tools')
                
                # Get the tool info if available
                if hasattr(module, 'get_tool_info'):
                    tool_info = module.get_tool_info()
                    tool_definitions.append(tool_info['function'])
                    
                    # Get the function name from the tool info
                    function_name = tool_info['function']['name']
                    if hasattr(module, function_name):
                        available_functions[function_name] = getattr(module, function_name)
            except Exception as e:
                print(f"Error loading tool from {filename}: {e}")
    
    return tool_definitions, available_functions

# Export the loader function
__all__ = ['load_tools']