# Query Memory Tool

This tool provides access to conversation history and memory, allowing retrieval of past interactions and user preferences.

## Features

- Search conversation history
- Support for both shared and session-specific memory
- Session-based memory isolation
- Structured JSON response format

## Usage

The tool can be accessed through the standard tool registry:

```python
from tools.query_memory import QueryMemoryTool

# Create an instance
memory_tool = QueryMemoryTool()

# Set up memory retriever (required before querying)
memory_tool.set_memory_retriever(vector_store.as_retriever(), session_id="user123")

# Query memory
result = memory_tool.query_memory(
    query="What did the user say about pizza preferences?",
    session_id="user123"
)
```

## Required Setup

Before using the tool, you must:
1. Initialize a vector store for memory
2. Create a memory retriever
3. Set the retriever using `set_memory_retriever()`

## Memory Modes

The tool supports two memory modes:
- Shared Memory: All sessions share the same memory space
- Session Memory: Each session has isolated memory

## Parameters

The query_memory method accepts:
- `query`: Search query string (required)
- `session_id`: Session identifier (required when memory sharing is disabled)
- `retriever_override`: Optional alternative retriever

## Return Format

Results are returned as a JSON string containing:
- On success: Array of conversation entries with content and metadata
- On failure: Error message with details

## Session Management

For session-based memory:
- Use `set_memory_retriever()` to initialize a session
- Use `remove_session_retriever()` to clean up when done