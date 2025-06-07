# --- Standard Library ---
import os
import asyncio

# --- Third-Party Libraries ---
import nest_asyncio

# --- Application Config & Constants ---
from constants import (
    CSV_FILE_PATH,
    ORDER_FILE_PATH,
    CONVERSATION_HISTORY_FILE_PATH,
    OLLAMA_MODEL,
    ENABLE_MEMORY,
    STORE_METADATA_FILE,
)

# --- Load Tool Definitions ---
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS

# --- Core Application Modules ---
from core.tools.query_documents import query_documents, set_documents_retriever
from core.tools.query_memory import query_memory, set_memory_retriever  # New memory tool
from core.vector_store import vector_store
from core.memory import ChatHistoryManager
from core.agent import run_agent
from core.utils import print_tool_definitions

from langchain_core.vectorstores import VectorStoreRetriever
from typing import Optional, Tuple

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Global variables for the retrievers
document_retriever: Optional[VectorStoreRetriever] = None
memory_retriever: Optional[VectorStoreRetriever] = None

# --- Main Execution Block ---
async def main():    
    global document_retriever, memory_retriever
    
    try:
        # display tool definitions
        print_tool_definitions()
        
        # Initialize memory
        memory = ChatHistoryManager(
            max_history=15,
            history_file=CONVERSATION_HISTORY_FILE_PATH
        )

        # Initialize vector stores and retrievers (now returns tuple)
        logger.info("Initializing vector stores...")
        retrievers = vector_store(
            file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH],
            enable_memory=ENABLE_MEMORY
        )
        
        # Unpack the tuple - setup_vector_store now returns (document_retriever, memory_retriever)
        if isinstance(retrievers, tuple) and len(retrievers) == 2:
            document_retriever, memory_retriever = retrievers
        else:
            # Fallback for backward compatibility
            document_retriever = retrievers
            memory_retriever = None
            logger.warning("Vector store setup returned single retriever instead of tuple. Memory queries may not work.")

        # Set the retrievers in their respective modules
        if document_retriever is not None:
            set_documents_retriever(document_retriever)
            
        if memory_retriever is not None:
            set_memory_retriever(memory_retriever)

        # Display initialization status
        display_initialization_status()

    except Exception as e:
        document_retriever = None
        memory_retriever = None
        logger.error(f"❌ Error during setup: {e}")

    # Display welcome message
    display_welcome_message()

    # Main interaction loop
    while True:
        try:
            user_input = input("\nPlease ask or order=> ")
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break

            async for response in run_agent(OLLAMA_MODEL, user_input, memory):
                if response.get("status") == "success":
                    if "content" in response:
                        print(response["content"])
                elif response.get("status") == "error":
                    print(f"Error: {response.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            logger.info("\nExiting...")
            break
        except Exception as e:
            logger.error(f"\nAn unexpected error occurred in the main loop: {e}")
            logger.info("Restarting loop...")
            await asyncio.sleep(1)

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
            logger.error("❌ Memory Retriever initialization failed. Memory queries will not work.")
    else:
        logger.info("\n📝 Memory is disabled. Conversation history will not be searchable.\n")

def display_welcome_message():
    """Display welcome message and usage instructions."""
    welcome_msg = "\nWelcome to the Pizza Restaurant Assistant!"
    help_msg = [
        "You can now:",
        "• Ask about reviews, orders, or menu items (searches documents)",
        "• Ask about previous conversations (searches memory)",
        "• Place new orders",
        "",
        "Examples:",
        "  'How is the pepperoni pizza?' (searches reviews)",
        "  'Show me recent orders' (searches order documents)", 
        "  'What did we discuss about delivery?' (searches conversation memory)",
        "  'I want to order 1 large veggie pizza to 456 Oak Avenue'",
        "  'exit' to quit"
    ]
    
    logger.info(welcome_msg)
    for line in help_msg:
        logger.info(line)

def check_file_existence():
    """Check if required files exist and warn if they don't."""
    files_to_check = [
        (CSV_FILE_PATH, "reviews/menu file"),
        (ORDER_FILE_PATH, "orders file"),
    ]
    
    missing_files = []
    for file_path, description in files_to_check:
        if not os.path.exists(file_path):
            missing_files.append(f"{description} ({file_path})")
            logger.warning(f"Warning: {description} not found at {file_path}")
    
    if missing_files:
        logger.info("Missing files will be created automatically when needed.")
    
    return len(missing_files) == 0

if __name__ == "__main__":
    # Check file existence before starting
    check_file_existence()
    
    # Run the async main function
    nest_asyncio.apply()
    asyncio.run(main())

def run_cli():
    """Synchronous wrapper for the CLI entry point."""
    # Check file existence before starting
    check_file_existence()
    
    nest_asyncio.apply()
    asyncio.run(main())