# --- Standard Library ---
import os
import json
from typing import List

# --- Third-Party Libraries ---
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# --- Application Config & Constants ---
from config import (
    CONVERSATION_HISTORY_FILE_PATH,
    DB_LOCATION,
    EMBEDDING_MODEL,
    COLLECTION_NAME,
)

# --- Internal Modules ---
from doc_utils import parse_files_to_documents, get_memory_documents

# --- Vector Store Setup ---
def setup_vector_store(
    file_paths: List[str],
    enable_memory: bool = False,
    conversation_file_path: str = CONVERSATION_HISTORY_FILE_PATH,
    db_location: str = DB_LOCATION,
    embedding_model: str = EMBEDDING_MODEL,
    collection_name: str = COLLECTION_NAME  # Now passed as a parameter
):
    """
    Initializes the vector store and retriever from a list of files.
    Handles CSV, JSON, TXT, Markdown formats.
    Integrates conversation history if enabled.

    If the conversation history file is in JSONL format (ends with .jsonl),
    it is parsed line-by-line.

    Returns:
        The initialized retriever object or None if setup fails
    """
    print("Setting up vector store from files:", file_paths)
    embeddings = OllamaEmbeddings(model=embedding_model)

    # Parse documents from the provided files
    documents = parse_files_to_documents(file_paths)

    # Integrate conversation history if memory is enabled
    if enable_memory:
        if os.path.exists(conversation_file_path):
            try:
                conversation_data = []
                # Check file extension to decide how to read it.
                if conversation_file_path.endswith('.jsonl'):
                    with open(conversation_file_path, "r") as f:
                        for line in f:
                            if line.strip():
                                conversation_data.append(json.loads(line))
                else:
                    with open(conversation_file_path, "r") as f:
                        conversation_data = json.load(f)
                documents.extend(get_memory_documents(conversation_data))
            except Exception as e:
                print(f"Error reading conversation history from {conversation_file_path}: {e}")
        else:
            print(f"Warning: {conversation_file_path} not found. Conversation memory not loaded.")

    if not documents:
        print("No documents found to add to the vector store.")
        return None

    try:
        vector_store = Chroma(
            collection_name=collection_name,
            persist_directory=db_location,
            embedding_function=embeddings
        )
        # Always add documents (overwrite or append)
        ids = [f"doc_{i}" for i in range(len(documents))]
        vector_store.add_documents(documents=documents, ids=ids)
        print(f"Added {len(documents)} documents to the vector store.")
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        print("Retriever setup complete.")
        return retriever
    except Exception as e:
        print(f"Error setting up vector store: {e}")
        return None
