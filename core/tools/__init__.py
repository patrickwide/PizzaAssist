import os
import sys
import importlib
from typing import Dict, Any, List, Tuple

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def load_tools() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Dynamically load all tools from the tools directory.
    Returns a tuple of (tool_definitions, available_functions)
    """
    logger.info("Starting to load tools from the tools directory.")
    
    tool_definitions = []
    available_functions = {}
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add parent directories to Python path
    parent_dir = os.path.dirname(current_dir)  # core/
    root_dir = os.path.dirname(parent_dir)     # ai_app/
    sys.path.extend([current_dir, parent_dir, root_dir])
    logger.debug(f"Added to sys.path: {current_dir}, {parent_dir}, {root_dir}")
    
    # List all Python files in the directory
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            logger.debug(f"Attempting to load tool module: {module_name}")
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
                        logger.info(f"Loaded tool: {function_name} from {module_name}")
                    else:
                        logger.warning(f"Function '{function_name}' not found in module '{module_name}'")
                else:
                    logger.warning(f"No 'get_tool_info' found in module '{module_name}'")
            except Exception as e:
                logger.error(f"Error loading tool from {filename}: {e}", exc_info=True)
    
    logger.info(f"Finished loading tools. Total tools loaded: {len(tool_definitions)}")
    return tool_definitions, available_functions

# Export the loader function
__all__ = ['load_tools']
