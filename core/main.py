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

from config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS

# --- Core Application Modules ---
from vector_store import setup_vector_store
from memory import AgentMemory
from agent import run_agent
from langchain_core.vectorstores import VectorStoreRetriever # Explicit import
from typing import Optional

# Global variable for the retriever (or pass it around)
retriever: Optional[VectorStoreRetriever] = None

from tools.query_documents import retriever as query_documents_retriever

def print_tool_definitions():
    """Print all available tool definitions"""
    print("\n=== Available Tool Definitions ===")
    if not TOOL_DEFINITIONS:
        print("No tool definitions available.")
        return
        
    for tool in TOOL_DEFINITIONS:
        if "function" in tool:
            func = tool["function"]
            print(f"\nTool: {func.get('name', 'Unnamed')}")
            print(f"Description: {func.get('description', 'No description')}")
            if 'parameters' in func:
                print("Parameters:")
                for param_name, param_details in func["parameters"].get("properties", {}).items():
                    required = param_name in func["parameters"].get("required", [])
                    print(f"  - {param_name}: {param_details.get('description', 'No description')} {'(Required)' if required else '(Optional)'}")
    print("\n================================")

# --- Main Execution Block ---
async def main():    
    # Print tool definitions before starting
    print_tool_definitions()
    
    # Set up the vector store without including the conversation history file in file_paths.
    # The conversation history file will be automatically collected via the default parameter.
    setup_vector_store(file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH], enable_memory=ENABLE_MEMORY)

    if retriever is None:
        print("Warning: Failed to initialize retriever. Review search functionality will be unavailable.")
        # Proceeding without retriever functionality

    memory = AgentMemory(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)  # Increased history slightly

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