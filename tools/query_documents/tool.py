"""Document querying tool implementation."""
# --- Standard Library ---
import json
from typing import Optional, List, Dict, Any
from langchain.schema import Document
from langchain_core.vectorstores import VectorStoreRetriever

# --- Core Imports ---
from core.interfaces.pizza_assist_tool import PizzaAssistTool
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

class QueryDocumentsTool(PizzaAssistTool):
    """Tool for querying indexed documents."""
    
    name = "query_documents"
    description = "Searches and retrieves relevant content from any indexed document (reviews, orders, or other files) based on a query. Useful for answering questions about food, service, price, atmosphere, orders, or any information present in the indexed files. Do NOT use this to place an order."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The specific question or topic to search for in the documents (e.g., 'pepperoni pizza quality', 'service speed', 'orders for John Doe', 'comments about the crust').",
            },
        },
        "required": ["query"],
    }
    
    def __init__(self):
        """Initialize the document query tool."""
        self.retriever = None
        
    def validate(self) -> bool:
        """Validate tool requirements."""
        return self.retriever is not None
        
    def set_retriever(self, r: VectorStoreRetriever) -> None:
        """Set the retriever instance."""
        self.retriever = r
        
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

    def query_documents(self, query: str) -> str:
        """Query indexed documents."""
        if self.retriever is None:
            logger.error("Document database could not be initialized")
            return json.dumps({"error": "Document database could not be initialized. Cannot search documents."})

        logger.info(f"Querying documents with: {query}")
        try:
            results: List[Document] = self.retriever.invoke(query)
            if not results:
                logger.info("No relevant documents found")
                return json.dumps({"message": "No relevant documents found for your query."})

            formatted_results = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
            logger.info(f"Found {len(results)} relevant documents")
            return json.dumps(formatted_results, indent=2)

        except Exception as e:
            logger.error(f"Error during document query: {e}")
            return json.dumps({"error": f"Failed to query documents: {str(e)}"})

# Create singleton instance for global use
document_tool = QueryDocumentsTool()

# Export the instance
__all__ = ['QueryDocumentsTool', 'document_tool']