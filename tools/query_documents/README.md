# Query Documents Tool

This tool provides functionality to search and retrieve relevant content from indexed documents.

## Features

- Search across all indexed documents
- Retrieve relevant content based on natural language queries
- Support for various document types (reviews, orders, etc.)
- JSON-formatted results with metadata

## Usage

The tool can be accessed through the standard tool registry:

```python
from tools.query_documents import QueryDocumentsTool

# Create an instance
doc_tool = QueryDocumentsTool()

# Set up the retriever (required before querying)
doc_tool.set_retriever(vector_store.as_retriever())

# Query documents
result = doc_tool.query("What do customers say about the pepperoni pizza?")
```

## Required Setup

Before using the tool, you must:
1. Initialize a vector store with your documents
2. Create a retriever from the vector store
3. Set the retriever using `set_retriever()`

## Parameters

The query method accepts:
- `query`: The search query string (required)
- `retriever_override`: Optional alternative retriever to use for this query

## Return Format

Results are returned as a JSON string containing:
- On success: Array of documents with content and metadata
- On failure: Error message with details