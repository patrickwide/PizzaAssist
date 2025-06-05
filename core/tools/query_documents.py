from typing import Optional, List, Dict, Any
import json
from langchain.schema import Document
from langchain_core.vectorstores import VectorStoreRetriever

def query_documents(query: str, retriever_override: Optional[VectorStoreRetriever] = None) -> str:
    """
    Searches the indexed documents (reviews, orders, or any supported file) for content relevant to the user's query.
    This is a general-purpose retrieval function for the agent to use on any indexed file.

    Args:
        query: The user's question or topic to search for in the documents.
        retriever_override: Optionally, a specific retriever to use (otherwise uses the global retriever).

    Returns:
        A JSON string containing the retrieved documents or an error message.
    """
    global retriever 
    active_retriever = retriever_override if retriever_override is not None else retriever
    if active_retriever is None:
        return json.dumps({"error": "Document database could not be initialized. Cannot search documents."})

    print(f"\n--- Tool Call: query_documents ---")
    print(f"--- Query: {query}")
    try:
        results: List[Document] = active_retriever.invoke(query)
        if not results:
            return json.dumps({"message": "No relevant documents found for your query."})

        formatted_results = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
        print(f"--- Found {len(results)} documents.")
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        print(f"Error during document query: {e}")
        return json.dumps({"error": f"Failed to query documents: {str(e)}"})

def get_tool_info() -> Dict[str, Any]:
    """Return the tool definition for this module."""
    return {
        "type": "function",
        "function": {
            "name": "query_documents",
            "description": "Searches and retrieves relevant content from any indexed document (reviews, orders, or other files) based on a query. Useful for answering questions about food, service, price, atmosphere, orders, or any information present in the indexed files. Do NOT use this to place an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The specific question or topic to search for in the documents (e.g., 'pepperoni pizza quality', 'service speed', 'orders for John Doe', 'comments about the crust').",
                    },
                },
                "required": ["query"],
            },
        },
    }


# Test the function directly
if __name__ == "__main__":
    # Example usage
    test_query = "What are the reviews for pepperoni pizza?"
    print("Testing query_documents with query:", test_query)
    result = query_documents(test_query)
    print("Query result:", result)

    # Example of tool info retrieval
    tool_info = get_tool_info()
    print("Tool info:", json.dumps(tool_info, indent=2))