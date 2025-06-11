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
from constants import SHARED_MEMORY_ENABLED

# Initialize logger
logger = setup_logger(__name__)

class SessionMemoryManager:
    """Manages session-specific memory retrievers."""
    
    def __init__(self):
        self._session_retrievers: Dict[str, VectorStoreRetriever] = {}
        self._global_retriever: Optional[VectorStoreRetriever] = None
    
    def set_global_retriever(self, retriever: VectorStoreRetriever) -> None:
        """Set the global memory retriever for shared memory mode."""
        self._global_retriever = retriever
        logger.info("Global memory retriever set")
    
    def set_session_retriever(self, session_id: str, retriever: VectorStoreRetriever) -> None:
        """Set a session-specific memory retriever."""
        self._session_retrievers[session_id] = retriever
        logger.info(f"Memory retriever set for session {session_id}")
    
    def get_retriever(self, session_id: Optional[str] = None) -> Optional[VectorStoreRetriever]:
        """Get the appropriate memory retriever based on mode and session."""
        if SHARED_MEMORY_ENABLED:
            return self._global_retriever
        elif session_id:
            return self._session_retrievers.get(session_id)
        return None
    
    def remove_session_retriever(self, session_id: str) -> None:
        """Remove a session-specific memory retriever."""
        if session_id in self._session_retrievers:
            del self._session_retrievers[session_id]
            logger.info(f"Memory retriever removed for session {session_id}")

# Global memory manager instance
memory_manager = SessionMemoryManager()

def set_memory_retriever(r: VectorStoreRetriever, session_id: Optional[str] = None):
    """Set the memory retriever - either global or session-specific."""
    if SHARED_MEMORY_ENABLED or session_id is None:
        memory_manager.set_global_retriever(r)
    else:
        memory_manager.set_session_retriever(session_id, r)

def remove_session_retriever(session_id: str):
    """Remove a session-specific memory retriever."""
    memory_manager.remove_session_retriever(session_id)

def query_memory(query: str, session_id: Optional[str] = None, retriever_override: Optional[VectorStoreRetriever] = None) -> str:
    """
    Searches the conversation memory/history for content relevant to the user's query.
    This function specifically searches through past conversations and interactions.

    Args:
        query: The user's question or topic to search for in conversation history.
        session_id: The session ID to restrict memory search to (if memory sharing is disabled).
        retriever_override: Optionally, a specific retriever to use (otherwise uses the appropriate retriever from memory manager).

    Returns:
        A JSON string containing the retrieved conversation history or an error message.
    """
    active_retriever = retriever_override if retriever_override is not None else memory_manager.get_retriever(session_id)
    if active_retriever is None:
        logger.error(f"Memory retriever not available for session {session_id}")
        return json.dumps({"error": "Memory retriever not available. Cannot search conversation history."})

    logger.info(f"Querying conversation memory with: {query}")
    try:
        results: List[Document] = active_retriever.invoke(query)
        
        # Filter results by session_id if memory sharing is disabled
        if not SHARED_MEMORY_ENABLED and session_id:
            filtered_results = []
            for doc in results:
                # Check if the document belongs to the current session
                if doc.metadata.get("session_id") == session_id:
                    filtered_results.append(doc)
            results = filtered_results

        if not results:
            logger.info("No relevant conversation history found")
            return json.dumps({"message": "No relevant conversation history found for your query."})

        formatted_results = []
        for doc in results:
            result = {
                "content": doc.page_content,
                "source": "conversation_history",
                "metadata": {
                    "session_id": doc.metadata.get("session_id"),
                    "document_type": doc.metadata.get("document_type"),
                    "timestamp": doc.metadata.get("timestamp")
                }
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
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to restrict memory search to. Required when memory sharing is disabled.",
                    }
                },
                "required": ["query", "session_id"],
            },
        },
    }