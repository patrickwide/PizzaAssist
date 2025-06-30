"""Memory querying tool implementation."""
# --- Standard Library ---
import json
from typing import Optional, List, Dict, Any
from langchain.schema import Document
from langchain_core.vectorstores import VectorStoreRetriever

# --- Core Imports ---
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from constants import SHARED_MEMORY_ENABLED
from logging_config import setup_logger

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

class QueryMemoryTool(PizzaAssistTool):
    """Tool for querying conversation memory."""

    name = "query_memory"
    description = "Searches and retrieves relevant content from conversation history and memory. Use this to recall past conversations, user preferences, or previous interactions. This is specifically for accessing conversation memory, not for searching documents like reviews or orders."
    parameters = {
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
    }
    
    def __init__(self):
        """Initialize the memory query tool."""
        self.memory_manager = SessionMemoryManager()
        
    def validate(self) -> bool:
        """Validate tool requirements."""
        return True  # Basic validation - more specific checks done during query
        
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
    
    def set_memory_retriever(self, retriever: VectorStoreRetriever, session_id: Optional[str] = None) -> None:
        """Set the memory retriever - either global or session-specific."""
        if SHARED_MEMORY_ENABLED or session_id is None:
            self.memory_manager.set_global_retriever(retriever)
        else:
            self.memory_manager.set_session_retriever(session_id, retriever)
            
    def remove_session_retriever(self, session_id: str) -> None:
        """Remove a session-specific memory retriever."""
        self.memory_manager.remove_session_retriever(session_id)
        
    def query_memory(self, query: str, session_id: Optional[str] = None) -> str:
        """Query the conversation memory for relevant content."""
        active_retriever = self.memory_manager.get_retriever(session_id)
        if active_retriever is None:
            logger.error(f"Memory retriever not available for session {session_id}")
            return json.dumps({"error": "Memory retriever not available. Cannot search conversation history."})

        logger.info(f"Querying conversation memory with: {query}")
        try:
            results: List[Document] = active_retriever.invoke(query)
            
            if not SHARED_MEMORY_ENABLED and session_id:
                filtered_results = []
                for doc in results:
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

# Create singleton instance for global use
memory_tool = QueryMemoryTool()

# Export the instance
__all__ = ['QueryMemoryTool', 'memory_tool']