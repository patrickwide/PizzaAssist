"""Tool loading and registration system."""
from typing import Dict, Any
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from core.tool_registry import ToolRegistry
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Initialize the global tool registry
registry = ToolRegistry()

def initialize_tools() -> Dict[str, Any]:
    """Initialize and register all tools."""
    global TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS
    
    # Only initialize if not already done
    if TOOL_DEFINITIONS and AVAILABLE_FUNCTIONS:
        logger.info("🔄 Tools already initialized, skipping...")
        return AVAILABLE_FUNCTIONS
    
    logger.info("🔧 Initializing tools...")
    
    tool_paths = registry.discover_tools()
    for tool_path in tool_paths:
        registry.load_tool_from_path(tool_path)
        
    tools = registry.list_tools()
    
    # Store both tool instances and their definitions
    tool_defs = []
    available_funcs = {}
    
    for name, tool_info in tools.items():
        tool = registry.get_tool(name)
        if isinstance(tool, PizzaAssistTool):
            tool_info = tool.get_tool_info()
            if "function" in tool_info:
                func_info = tool_info["function"]
                tool_defs.append({
                    "function": {
                        "name": func_info["name"],
                        "description": func_info["description"],
                        "parameters": func_info["parameters"]
                    }
                })
                # Store the actual method reference
                available_funcs[func_info["name"]] = getattr(tool, func_info["name"])
    
    # Update global config
    TOOL_DEFINITIONS.extend(tool_defs)
    AVAILABLE_FUNCTIONS.update(available_funcs)
    
    logger.info(f"📋 Registered {len(tools)} tools")
    return AVAILABLE_FUNCTIONS

def get_tool(name: str) -> PizzaAssistTool:
    """Get a registered tool by name."""
    tool = registry.get_tool(name)
    if not isinstance(tool, PizzaAssistTool):
        raise ValueError(f"Tool {name} is not properly initialized")
    return tool

# Export the registry instance and functions
__all__ = ['registry', 'initialize_tools', 'get_tool']
