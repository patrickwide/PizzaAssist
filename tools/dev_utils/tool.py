"""Development utilities for tool creation and testing."""
# --- Standard Library ---
import json
from typing import Dict, Any, List, Optional
from inspect import isclass, getmembers

# --- Core Imports ---
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from core.validation_utils import validate_tool_schema, analyze_tool_class
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

class ToolTester:
    """Helper class for testing tools during development."""
    
    def __init__(self, registry):
        self.registry = registry
        
    def validate_tool(self, tool: PizzaAssistTool) -> Dict[str, Any]:
        """Run comprehensive validation on a tool."""
        results = {
            "interface_check": {},
            "schema_validation": [],
            "runtime_validation": False
        }
        
        # Check interface implementation
        analysis = analyze_tool_class(tool.__class__)
        results["interface_check"] = analysis
        
        # Validate schema
        try:
            info = tool.get_tool_info()
            schema_errors = validate_tool_schema(info)
            results["schema_validation"] = schema_errors
        except Exception as e:
            results["schema_validation"] = [f"Error getting tool info: {str(e)}"]
            
        # Runtime validation
        try:
            results["runtime_validation"] = tool.validate()
        except Exception as e:
            results["runtime_validation"] = f"Validation error: {str(e)}"
            
        return results

    def run_tool_test(self, 
                      tool: PizzaAssistTool, 
                      test_inputs: Dict[str, Any],
                      expected_output: Optional[Any] = None) -> Dict[str, Any]:
        """Run a test case for a tool."""
        results = {
            "validation": self.validate_tool(tool),
            "test_case": {
                "inputs": test_inputs,
                "expected": expected_output,
                "actual": None,
                "errors": []
            }
        }
        
        if results["validation"]["schema_validation"]:
            results["test_case"]["errors"].append(
                "Skipped execution due to schema validation errors"
            )
            return results
            
        try:
            info = tool.get_tool_info()
            tool_name = info["function"]["name"]
            
            # Test using registry
            test_result = self.registry.test_tool(tool_name, test_inputs)
            results["test_case"]["actual"] = test_result
            
            if expected_output is not None:
                results["test_case"]["matches_expected"] = (
                    test_result == expected_output
                )
                
        except Exception as e:
            results["test_case"]["errors"].append(f"Execution error: {str(e)}")
            
        return results

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a readable report from test results."""
        report = []
        report.append("🔍 Tool Test Report")
        report.append("=" * 50)
        
        # Interface check
        interface = results["validation"]["interface_check"]
        report.append(f"\n📋 Interface Implementation ({interface['name']})")
        report.append(f"Implements Interface: {interface['implements_interface']}")
        for method, status in interface["methods"].items():
            report.append(f"  - {method}: {status}")
            
        # Schema validation
        schema_errors = results["validation"]["schema_validation"]
        report.append("\n📝 Schema Validation")
        if not schema_errors:
            report.append("  ✅ No schema errors")
        else:
            for error in schema_errors:
                report.append(f"  ❌ {error}")
                
        # Runtime validation
        report.append("\n⚙️ Runtime Validation")
        report.append(f"  {'✅' if results['validation']['runtime_validation'] else '❌'} " + 
                     f"Result: {results['validation']['runtime_validation']}")
                     
        # Test case results
        test_case = results["test_case"]
        report.append("\n🧪 Test Case")
        report.append(f"Inputs: {json.dumps(test_case['inputs'], indent=2)}")
        
        if test_case["errors"]:
            report.append("\nErrors:")
            for error in test_case["errors"]:
                report.append(f"  ❌ {error}")
        else:
            report.append("\nExecution:")
            report.append(f"  Output: {json.dumps(test_case['actual'], indent=2)}")
            
            if "matches_expected" in test_case:
                report.append(f"\nExpected Output Match: " +
                            f"{'✅' if test_case['matches_expected'] else '❌'}")
                
        return "\n".join(report)

class DevUtilsTool(PizzaAssistTool):
    """Tool for development utilities."""
    
    name = "dev_utils"
    description = "Development utilities for creating and testing tools"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The utility action to perform",
                "enum": ["validate_schema", "analyze_tool", "create_template", "test_tool"]
            },
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to work with"
            },
            "tool_description": {
                "type": "string",
                "description": "Description when creating a new tool"
            },
            "test_inputs": {
                "type": "object",
                "description": "Test inputs when testing a tool"
            },
            "expected_output": {
                "type": "object",
                "description": "Expected output when testing a tool"
            }
        },
        "required": ["action", "tool_name"]
    }
    
    def __init__(self):
        """Initialize the tool."""
        self.tool_tester = None
        self.registry = None
        
    def set_registry(self, registry) -> None:
        """Set the tool registry for testing."""
        self.registry = registry
        self.tool_tester = ToolTester(registry)
        
    def validate(self) -> bool:
        """Validate tool requirements are met."""
        return True
        
    def get_tool_info(self) -> Dict[str, Any]:
        """Return the tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def dev_utils(
        self,
        action: str,
        tool_name: str,
        tool_description: Optional[str] = None,
        test_inputs: Optional[Dict[str, Any]] = None,
        expected_output: Optional[Any] = None
    ) -> str:
        """Execute a development utility action."""
        try:
            if action == "validate_schema":
                if not self.registry or tool_name not in self.registry._tools:
                    return json.dumps({"error": f"Tool '{tool_name}' not found"})
                tool = self.registry._tools[tool_name]
                info = tool.get_tool_info()
                errors = validate_tool_schema(info)
                return json.dumps({
                    "tool": tool_name,
                    "valid": not errors,
                    "errors": errors
                }, indent=2)

            elif action == "analyze_tool":
                if not self.registry or tool_name not in self.registry._tools:
                    return json.dumps({"error": f"Tool '{tool_name}' not found"})
                tool = self.registry._tools[tool_name]
                analysis = analyze_tool_class(tool.__class__)
                return json.dumps(analysis, indent=2)

            elif action == "test_tool":
                if not self.tool_tester:
                    return json.dumps({"error": "Tool tester not initialized. Call set_registry first."})
                if not self.registry or tool_name not in self.registry._tools:
                    return json.dumps({"error": f"Tool '{tool_name}' not found"})
                if not test_inputs:
                    return json.dumps({"error": "test_inputs required for test_tool action"})
                    
                tool = self.registry._tools[tool_name]
                results = self.tool_tester.run_tool_test(tool, test_inputs, expected_output)
                return self.tool_tester.generate_test_report(results)

            elif action == "create_template":
                if not tool_description:
                    return json.dumps({"error": "tool_description required for create_template action"})
                    
                template = self._generate_tool_template(tool_name, tool_description)
                return json.dumps({
                    "message": f"Template generated for tool: {tool_name}",
                    "template": template
                }, indent=2)

            else:
                return json.dumps({"error": f"Unknown action: {action}"})

        except Exception as e:
            logger.error(f"Error executing dev util action: {e}")
            return json.dumps({"error": f"Failed to execute {action}: {str(e)}"})

    def _generate_tool_template(self, name: str, description: str) -> Dict[str, Any]:
        """Generate a tool template."""
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Description of first parameter"
                        }
                    },
                    "required": ["param1"]
                }
            }
        }

# Create singleton instance for global use
dev_tool = DevUtilsTool()

# Export the instance
__all__ = ['DevUtilsTool', 'dev_tool']