"""Validation utilities for tool development."""
from typing import Dict, Any, List, Type
from inspect import isclass, getmembers

def analyze_tool_class(cls: Type[Any]) -> Dict[str, Any]:
    """Analyze a tool class for interface implementation."""
    required_methods = ["get_tool_info", "validate"]
    
    methods = {}
    for method in required_methods:
        if hasattr(cls, method) and callable(getattr(cls, method)):
            methods[method] = "Implemented"
        else:
            methods[method] = "Missing"
            
    return {
        "name": cls.__name__,
        "implements_interface": all(status == "Implemented" for status in methods.values()),
        "methods": methods
    }

def validate_tool_schema(tool_info: Dict[str, Any]) -> List[str]:
    """Validate a tool's schema and return any errors."""
    errors = []
    
    if "function" not in tool_info:
        errors.append("Missing top-level 'function' key")
        return errors
        
    function = tool_info["function"]
    required_fields = {
        "name": str,
        "description": str,
        "parameters": dict
    }
    
    for field, expected_type in required_fields.items():
        if field not in function:
            errors.append(f"Missing required field '{field}'")
        elif not isinstance(function[field], expected_type):
            errors.append(f"Field '{field}' has wrong type. Expected {expected_type.__name__}")
            
    if "parameters" in function:
        params = function["parameters"]
        if "properties" not in params:
            errors.append("Parameters object missing 'properties' field")
        if "required" not in params:
            errors.append("Parameters object missing 'required' field")
            
    return errors