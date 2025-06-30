# Development Utilities Tool

This tool provides utilities for developing and testing new PizzaAssist tools.

## Features

- Schema validation for tool definitions
- Tool interface analysis
- Tool template generation

## Usage

The tool can be accessed through the standard tool registry:

```python
from tools.dev_utils import DevUtilsTool

# Create an instance
dev_tool = DevUtilsTool()

# Validate a tool schema
errors = dev_tool.validate_tool_schema(tool_info)
```

## Actions

1. `validate_schema`: Validates a tool's schema definition
2. `analyze_tool`: Analyzes a tool's implementation of the PizzaAssistTool interface
3. `create_template`: Creates a new tool template with basic structure

## Parameters

- `action`: The utility action to perform (required)
- `tool_name`: Name of the tool to work with (required)
- `tool_description`: Description when creating a new tool (optional)

## Examples

```python
# Validate a tool schema
result = dev_tool.execute({
    "action": "validate_schema",
    "tool_name": "my_tool"
})

# Create a new tool template
result = dev_tool.execute({
    "action": "create_template",
    "tool_name": "new_tool",
    "tool_description": "A new pizza assistant tool"
})
```