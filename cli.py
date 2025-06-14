# --- Standard Library ---
import os
import asyncio
import json
import uuid
import textwrap

# --- Third-Party Libraries ---
import nest_asyncio

# --- Application Config & Constants ---
from constants import (
    CSV_FILE_PATH,
    ORDER_FILE_PATH,
    HISTORY_DIR,
    OLLAMA_MODEL,
    ENABLE_MEMORY,
    STORE_METADATA_FILE,
    SYSTEM_MESSAGE
)

# --- Load Tool Definitions ---
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS

# --- Core Application Modules ---
from core.tools.query_documents import query_documents, set_documents_retriever
from core.tools.query_memory import query_memory, set_memory_retriever
from core.vector_store import vector_store
from core.memory import ChatHistoryManager
from core.agent import run_agent
from core.utils import log_available_tools
from server.initialization import initialize_vector_store

# --- Type Hints ---
from langchain_core.vectorstores import VectorStoreRetriever
from typing import Optional, Tuple

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Global variables for the retrievers
document_retriever: Optional[VectorStoreRetriever] = None
memory_retriever: Optional[VectorStoreRetriever] = None

def initialize_memory() -> ChatHistoryManager:
    """Initialize the chat history manager"""
    return ChatHistoryManager()

async def initialize_retriever() -> Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]:
    """Initialize document and memory retrievers"""
    try:
        document_retriever, memory_retriever = await initialize_vector_store()
        if document_retriever:
            set_documents_retriever(document_retriever)
        return document_retriever, memory_retriever
    except Exception as e:
        logger.error(f"Failed to initialize retrievers: {e}")
        return None, None

def truncate_response(response: str, max_length: int = 100) -> str:
    """Truncate long responses for display"""
    try:
        if len(response) > max_length:
            return textwrap.shorten(response, width=max_length, placeholder="...")
        return response
    except Exception:
        return str(response)

# --- Main Execution Block ---
async def main():
    """Main entry point for CLI interface"""
    try:
        # Initialize system
        logger.info("🚀 Starting Pizza AI Assistant CLI...")
        
        # Initialize components
        memory = initialize_memory()
        document_retriever = None
        memory_retriever = None
        
        try:
            document_retriever, memory_retriever = await initialize_retriever()
            set_memory_retriever(memory_retriever)
        except Exception as e:
            logger.error(f"❌ Error initializing retrieval system: {e}")

        # Display initialization status
        display_initialization_status()

    except Exception as e:
        document_retriever = None
        memory_retriever = None
        logger.error(f"❌ Error during setup: {e}")

    # Display welcome message
    display_welcome_message()

    # Initialize conversation tracking
    session_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    message_sequence = 0
    last_message_id = None

    # Main interaction loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Thanks for using Pizza AI Assistant! Goodbye!")
                break

            # Generate correlation IDs for this interaction
            user_input_id = str(uuid.uuid4())
            
            async for response in run_agent(
                model=OLLAMA_MODEL,
                user_input=user_input,
                memory=memory,
                session_id=session_id,
                system_message=SYSTEM_MESSAGE,
                user_input_id=user_input_id,
                parent_id=last_message_id,
                conversation_id=conversation_id
            ):
                if response.get("status") == "error":
                    logger.error(f"Error: {response.get('error', 'Unknown error')}")
                    continue
                
                # Update tracking variables
                last_message_id = response.get("message_id")
                message_sequence = response.get("sequence", message_sequence + 1)
                
                if "message" in response:
                    if isinstance(response["message"], str):
                        print(f"\nAssistant: {response['message']}")
                    else:
                        print(f"\nAssistant: {json.dumps(response['message'], indent=2)}")
                elif "content" in response:
                    if response.get("stage") == "tool_call":
                        print(f"\n🔧 Using tool: {response.get('tool', 'unknown')}")
                    elif response.get("stage") == "tool_result":
                        print(f"\n📊 Tool result: {truncate_response(response.get('response', ''))}")
                    elif response.get("stage") in ["initial_response", "final_response"]:
                        print(f"\nAssistant: {response['content']}")
                
                # Debug logging of correlation IDs if needed
                logger.debug(f"Message correlation: message_id={response.get('message_id')}, " 
                           f"parent_id={response.get('parent_id')}, "
                           f"conversation_id={response.get('conversation_id')}, "
                           f"sequence={response.get('sequence')}")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            break
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            print(f"\n⚠️ Sorry, I encountered an error: {e}")

def display_initialization_status():
    """Display the status of retriever initialization."""
    # Document retriever status
    if document_retriever is not None:
        doc_status_msg = (
            f"\n✅ Document Retriever successfully initialized!"
            f"\n   • Tags         : {getattr(document_retriever, 'tags', 'N/A')}"
            f"\n   • Vector Store : {type(getattr(document_retriever, 'vectorstore', 'N/A')).__name__}"
            f"\n   • Search Params: {getattr(document_retriever, 'search_kwargs', 'N/A')}"
        )
        logger.info(doc_status_msg)
    else:
        logger.error("❌ Document Retriever initialization failed. Document queries will not work.")

    # Memory retriever status
    if ENABLE_MEMORY:
        if memory_retriever is not None:
            memory_status_msg = (
                f"\n✅ Memory Retriever successfully initialized!"
                f"\n   • Tags         : {getattr(memory_retriever, 'tags', 'N/A')}"
                f"\n   • Vector Store : {type(getattr(memory_retriever, 'vectorstore', 'N/A')).__name__}"
                f"\n   • Search Params: {getattr(memory_retriever, 'search_kwargs', 'N/A')}\n"
            )
            logger.info(memory_status_msg)
        else:
            logger.info("\n📝 Memory retriever not initialized - memory queries will be session-based only\n")
    else:
        logger.info("\n📝 Memory is disabled. Conversation history will not be searchable.\n")

def display_welcome_message():
    """Display the welcome message."""
    print("\n" + "="*50)
    print("🤖 Welcome to the Pizza AI Assistant CLI!")
    print("Type 'exit' or 'quit' to end the session")
    print("="*50)

if __name__ == "__main__":
    try:
        nest_asyncio.apply()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")