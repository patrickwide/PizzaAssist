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

# Global memory retriever instance
memory_retriever = None

def set_memory_retriever(r: VectorStoreRetriever):
    """Set the global memory retriever instance."""
    global memory_retriever
    memory_retriever = r

def query_memory(query: str, retriever_override: Optional[VectorStoreRetriever] = None) -> str:
    """
    Searches the conversation memory/history for content relevant to the user's query.
    This function specifically searches through past conversations and interactions.

    Args:
        query: The user's question or topic to search for in conversation history.
        retriever_override: Optionally, a specific retriever to use (otherwise uses the global memory retriever).

    Returns:
        A JSON string containing the retrieved conversation history or an error message.
    """
    active_retriever = retriever_override if retriever_override is not None else memory_retriever
    if active_retriever is None:
        logger.error("Memory database could not be initialized")
        return json.dumps({"error": "Memory database could not be initialized. Cannot search conversation history."})

    logger.info(f"Querying conversation memory with: {query}")
    try:
        results: List[Document] = active_retriever.invoke(query)
        if not results:
            logger.info("No relevant conversation history found")
            return json.dumps({"message": "No relevant conversation history found for your query."})

        formatted_results = []
        for doc in results:
            result = {
                "content": doc.page_content,
                "source": "conversation_history",
                "metadata": doc.metadata
            }
            formatted_results.append(result)

        logger.info(f"Found {len(results)} relevant conversation entries")
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        logger.error(f"Error during memory query: {e}")
        return json.dumps({"error": f"Failed to query conversation memory: {str(e)}"})

def get_tool_info() -> Dict[str, Any]:
    """Return the tool definition for this module."""
    return {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Searches and retrieves relevant content from conversation history and memory. Use this to recall past conversations, user preferences, or previous interactions. This is specifically for accessing conversation memory, not for searching documents like reviews or orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The specific question or topic to search for in conversation history (e.g., 'user preferences', 'previous orders discussed', 'what did the user say about pizza').",
                    },
                },
                "required": ["query"],
            },
        },
    }