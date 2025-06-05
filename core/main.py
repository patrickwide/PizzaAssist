# --- Standard Library ---
import os
import asyncio

# --- Third-Party Libraries ---
import nest_asyncio

# --- Application Config & Constants ---
from core.constants import (
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
from core.tools.query_documents import query_documents, set_retriever
from core.vector_store import setup_vector_store
from core.memory import AgentMemory
from core.agent import run_agent
from core.utils import print_tool_definitions

from langchain_core.vectorstores import VectorStoreRetriever
from typing import Optional

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Global variable for the retriever (or pass it around)
retriever: Optional[VectorStoreRetriever] = None

# --- Main Execution Block ---
async def main():    
    try:
        # Get and display tool definitions
        tool_definitions = print_tool_definitions()
        for line in tool_definitions:
            logger.info(line)

        # Initialize memory
        memory = AgentMemory(
            max_history=15,
            history_file=CONVERSATION_HISTORY_FILE_PATH
        )

        # Initialize vector store and retriever
        logger.info("Initializing vector store...")
        retriever = setup_vector_store(
            file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH],
            enable_memory=ENABLE_MEMORY
        )

        # Set the retriever in query_documents module
        set_retriever(retriever)

        # If retriever is initialized correctly
        if retriever is not None:
            status_msg = (
                f"\n✅ Retriever successfully initialized!"
                f"\n   • Tags         : {getattr(retriever, 'tags', 'N/A')}"
                f"\n   • Vector Store : {type(getattr(retriever, 'vectorstore', 'N/A')).__name__}"
                f"\n   • Search Params: {getattr(retriever, 'search_kwargs', 'N/A')}\n"
            )
            logger.info(status_msg)
        else:
            logger.error("❌ Retriever initialization failed. Please check logs for details.")

    except Exception as e:
        retriever = None
        logger.error(f"❌ Error during setup: {e}")

    # Display welcome message
    welcome_msg = "\nWelcome to the Pizza Restaurant Assistant!"
    help_msg = [
        "Ask about reviews or place an order.",
        "(e.g., 'How is the pepperoni pizza?', 'Tell me about the service',",
        "      'I want to order 1 large veggie pizza to 456 Oak Avenue', 'exit' to quit)"
    ]
    
    logger.info(welcome_msg)
    for line in help_msg:
        logger.info(line)

    while True:
        try:
            user_input = input("\nPlease ask or order=> ")
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break

            await run_agent(OLLAMA_MODEL, user_input, memory)

        except KeyboardInterrupt:
            logger.info("\nExiting...")
            break
        except Exception as e:
            logger.error(f"\nAn unexpected error occurred in the main loop: {e}")
            logger.info("Restarting loop...")
            await asyncio.sleep(1)

if __name__ == "__main__":
    if not os.path.exists(CSV_FILE_PATH):
        logger.warning(f"Warning: {CSV_FILE_PATH} not found. A dummy file will be created on first run.")
    # Replace asyncio.run(main()) with the following:
    nest_asyncio.apply()
    asyncio.run(main())


