# --- Standard Library ---
import os
import sys
from typing import Optional, List, Dict, Any
import json
from langchain.schema import Document
from langchain_core.vectorstores import VectorStoreRetriever

# Add the parent directory to Python path to allow core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Global retriever instance
retriever = None

def set_documents_retriever(r: VectorStoreRetriever):
    """Set the global retriever instance."""
    global retriever
    retriever = r

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
    active_retriever = retriever_override if retriever_override is not None else retriever
    if active_retriever is None:
        logger.error("Document database could not be initialized")
        return json.dumps({"error": "Document database could not be initialized. Cannot search documents."})

    logger.info(f"Querying documents with: {query}")
    try:
        results: List[Document] = active_retriever.invoke(query)
        if not results:
            logger.info("No relevant documents found")
            return json.dumps({"message": "No relevant documents found for your query."})

        formatted_results = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
        logger.info(f"Found {len(results)} relevant documents")
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        logger.error(f"Error during document query: {e}")
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
