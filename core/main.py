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

# Global variable for the retriever (or pass it around)
retriever: Optional[VectorStoreRetriever] = None

# --- Main Execution Block ---
async def main():    
    try:
        # Print available tool definitions
        print_tool_definitions()

        # Initialize memory
        memory = AgentMemory(
            max_history=15,
            history_file=CONVERSATION_HISTORY_FILE_PATH
        )

        # Initialize vector store and retriever
        print("Initializing vector store...")
        retriever = setup_vector_store(
            file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH],
            enable_memory=ENABLE_MEMORY
        )

        # Set the retriever in query_documents module
        set_retriever(retriever)

        # If retriever is initialized correctly
        if retriever is not None:
            print(
                f"\n✅ Retriever successfully initialized!"
                f"\n   • Tags         : {getattr(retriever, 'tags', 'N/A')}"
                f"\n   • Vector Store : {type(getattr(retriever, 'vectorstore', 'N/A')).__name__}"
                f"\n   • Search Params: {getattr(retriever, 'search_kwargs', 'N/A')}\n"
            )
        else:
            print("\n❌ Retriever initialization failed. Please check logs for details.\n")

    except Exception as e:
        retriever = None
        print(f"❌ Error during setup: {e}")

    print("\nWelcome to the Pizza Restaurant Assistant!")
    print("Ask about reviews or place an order.")
    print("(e.g., 'How is the pepperoni pizza?', 'Tell me about the service',")
    print("      'I want to order 1 large veggie pizza to 456 Oak Avenue', 'exit' to quit)")

    while True:
        try:
            user_input = input("\nPlease ask or order=> ")
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break

            await run_agent(OLLAMA_MODEL, user_input, memory)

        except KeyboardInterrupt:
             print("\nExiting...")
             break
        except Exception as e:
             print(f"\nAn unexpected error occurred in the main loop: {e}")
             print("Restarting loop...")
             await asyncio.sleep(1)

if __name__ == "__main__":
    if not os.path.exists(CSV_FILE_PATH):
         print(f"Warning: {CSV_FILE_PATH} not found. A dummy file will be created on first run.")
    # Replace asyncio.run(main()) with the following:
    nest_asyncio.apply()
    asyncio.run(main()) # or loop.run_until_complete(main())

# # Test the function directly
# if __name__ == "__main__":
#     if not os.path.exists(CSV_FILE_PATH):
#          print(f"Warning: {CSV_FILE_PATH} not found. A dummy file will be created on first run.")
    
#     # Initialize vector store and retriever for testing
#     print("Initializing vector store for test...")
#     test_retriever = setup_vector_store(
#         file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH],
#         enable_memory=ENABLE_MEMORY
#     )
    
#     if test_retriever:
#         test_query = "What are the reviews for pepperoni pizza?"
#         print("Testing query_documents with query:", test_query)
#         result = query_documents(test_query, retriever_override=test_retriever)
#         print("Query result:", result)
#     else:
#         print("Failed to initialize retriever for testing")


