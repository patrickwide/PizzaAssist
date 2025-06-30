"""Enhanced tool registry with validation and testing capabilities."""
from typing import Dict, Any, List
import os
from pathlib import Path
import importlib.util
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from core.validation_utils import validate_tool_schema, analyze_tool_class
from logging_config import setup_logger

logger = setup_logger(__name__)

# Update tools directory path to point to root level
TOOLS_DIR = Path(__file__).parent.parent / "tools"

class ToolRegistry:
    """Central registry for managing tool lifecycle with enhanced validation."""
    
    def __init__(self):
        self._tools: Dict[str, PizzaAssistTool] = {}
        self._validation_results: Dict[str, List[str]] = {}

    def discover_tools(self) -> List[str]:
        """Discover tools in the tools directory structure."""
        tools = []
        for tool_dir in TOOLS_DIR.iterdir():
            if tool_dir.is_dir() and not tool_dir.name.startswith('__'):
                tool_path = tool_dir / "tool.py"
                if tool_path.exists():
                    tools.append(str(tool_path))
        return tools

    def load_tool_from_path(self, tool_path: str) -> None:
        """Load and register a tool from its file path."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"tools.{Path(tool_path).parent.name}.tool", 
                tool_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for PizzaAssistTool implementations
                for name, obj in vars(module).items():
                    if (isinstance(obj, type) and 
                        issubclass(obj, PizzaAssistTool) and 
                        obj != PizzaAssistTool):
                        tool = obj()
                        self.register(tool)
                        
        except Exception as e:
            logger.error(f"❌ Failed to load tool from {tool_path}: {e}")

    def register(self, tool: PizzaAssistTool) -> None:
        """Register a tool with validation.
        
        Args:
            tool: Tool instance implementing PizzaAssistTool interface
            
        Raises:
            ValueError: If tool info is invalid
        """
        # Validate interface implementation
        analysis = analyze_tool_class(tool.__class__)
        if not analysis["implements_interface"]:
            missing = [m for m, status in analysis["methods"].items() if status == "Missing"]
            raise ValueError(f"Tool missing required methods: {', '.join(missing)}")
        
        # Get and validate tool info
        info = tool.get_tool_info()
        errors = validate_tool_schema(info)
        
        if errors:
            self._validation_results[tool.__class__.__name__] = errors
            raise ValueError(f"Invalid tool schema: {'; '.join(errors)}")
            
        name = info["function"]["name"]
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")
        
    def get_tool(self, name: str) -> PizzaAssistTool:
        """Get a registered tool by name."""
        return self._tools[name]
        
    def list_tools(self) -> Dict[str, Any]:
        """List all registered tools and their info."""
        return {name: tool.get_tool_info() for name, tool in self._tools.items()}
        
    def get_validation_status(self, tool_name: str = None) -> Dict[str, List[str]]:
        """Get validation errors for a tool or all tools."""
        if tool_name:
            return {tool_name: self._validation_results.get(tool_name, [])}
        return self._validation_results
        
    def test_tool(self, name: str, test_input: Dict[str, Any]) -> Dict[str, Any]:
        """Test a tool with sample input.
        
        Args:
            name: Name of the tool to test
            test_input: Sample input parameters
            
        Returns:
            Dict containing test results and any validation errors
        """
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}
            
        tool = self._tools[name]
        info = tool.get_tool_info()
        
        # Validate input against schema
        required = info["function"]["parameters"].get("required", [])
        properties = info["function"]["parameters"].get("properties", {})
        
        errors = []
        for param in required:
            if param not in test_input:
                errors.append(f"Missing required parameter: {param}")
                
        for param, value in test_input.items():
            if param not in properties:
                errors.append(f"Unknown parameter: {param}")
            else:
                expected_type = properties[param]["type"]
                if not self._validate_type(value, expected_type):
                    errors.append(f"Invalid type for {param}. Expected {expected_type}")
                    
        if errors:
            return {"status": "error", "validation_errors": errors}
            
        # Run basic validation
        if not tool.validate():
            return {"status": "error", "message": "Tool validation failed"}
            
        return {
            "status": "success",
            "message": "Tool schema and validation passed",
            "tool_info": info
        }
        
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate a parameter value against its expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        if expected_type not in type_map:
            return True  # Skip validation for unknown types
            
        expected = type_map[expected_type]
        return isinstance(value, expected)