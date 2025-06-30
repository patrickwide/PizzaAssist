# PizzaAssist Tools

This directory contains all tools that can be used by PizzaAssist. Each tool is organized in its own directory with a consistent structure.

## Directory Structure

Each tool should be organized as follows:

```
tools/
└── your_tool_name/
    ├── tool.py         # Main tool implementation
    ├── __init__.py     # Tool exports
    └── README.md       # Tool documentation
```

## Creating a New Tool

1. Create a new directory under `tools/` with your tool name
2. Implement your tool in `tool.py` extending `PizzaAssistTool`
3. Document usage and configuration in your tool's README.md
4. Register your tool by adding it to `__init__.py`

## Tool Requirements

- All tools must implement the `PizzaAssistTool` interface
- Tools must provide complete documentation in their README.md
- Each tool must validate its dependencies in the `validate()` method