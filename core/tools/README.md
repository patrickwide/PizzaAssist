# Tool Development Guide

This guide explains how to create and test new tools for the PizzaAssist system.

## Creating a New Tool

1. Use the tool template generator:
```python
from core.tools.dev_utils import create_tool_template

# Generate template code
template = create_tool_template(
    name="my_tool",
    description="Description of what the tool does"
)

# Save to new file
with open("my_tool.py", "w") as f:
    f.write(template)
```

2. Implement the required interface methods:
- `get_tool_info()`: Define your tool's schema and parameters
- `validate()`: Add any runtime validation logic

## Validating Your Tool

```python
from core.tool_registry import ToolRegistry
from core.tools.test_utils import ToolTester

# Initialize testing utilities
registry = ToolRegistry()
tester = ToolTester(registry)

# Validate your tool
results = tester.validate_tool(my_tool)

# Run test cases
test_results = tester.run_tool_test(
    tool=my_tool,
    test_inputs={"param_name": "test_value"},
    expected_output="expected result"
)

# Generate readable report
print(tester.generate_test_report(test_results))
```

## Tool Requirements

1. **Interface Compliance**
   - Must implement `PizzaAssistTool` interface
   - All required methods must be present

2. **Schema Validation**
   - Tool info must include: name, description, parameters
   - Parameters must specify: properties, required fields
   - Types must be valid JSON schema types

3. **Runtime Validation**
   - Tool must implement runtime checks in `validate()`
   - Should verify all required dependencies/resources

## Best Practices

1. **Naming**
   - Use clear, descriptive names for your tool
   - Follow Python naming conventions
   - End class names with 'Tool'

2. **Documentation**
   - Include detailed docstrings
   - Document parameters and return types
   - Provide usage examples

3. **Error Handling**
   - Use appropriate exception types
   - Include helpful error messages
   - Log errors appropriately

4. **Testing**
   - Create comprehensive test cases
   - Test edge cases and failures
   - Validate parameter types

## Example Tool

```python
from typing import Dict, Any
from core.interfaces.pizza_assist_tool import PizzaAssistTool

class GreetingTool(PizzaAssistTool):
    """A simple greeting tool example."""
    
    def validate(self) -> bool:
        return True
        
    def get_tool_info(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "greet",
                "description": "Generate a greeting message",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet"
                        }
                    },
                    "required": ["name"]
                }
            }
        }

# Create singleton instance
greeting_tool = GreetingTool()
```