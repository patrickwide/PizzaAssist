# --- Standard Library ---
import os
import json
import hashlib
from typing import List
from datetime import datetime

# --- Third-Party Libraries ---
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# --- Application Config & Constants ---
from constants import (
    CONVERSATION_HISTORY_FILE_PATH,
    DB_LOCATION,
    EMBEDDING_MODEL,
    COLLECTION_NAME,
    STORE_METADATA_FILE,
)

# --- Internal Modules ---
from doc_utils import parse_files_to_documents, get_memory_documents

def get_files_hash(file_paths: List[str]) -> str:
    """
    Generate a hash of the file contents and modification times to detect changes.
    """
    hasher = hashlib.md5()
    for file_path in sorted(file_paths):  # Sort for consistency
        if os.path.exists(file_path):
            # Add file modification time
            mtime = str(os.path.getmtime(file_path))
            hasher.update(mtime.encode())
            
            # Add file size
            size = str(os.path.getsize(file_path))
            hasher.update(size.encode())
    
    return hasher.hexdigest()

def save_store_metadata(db_location: str, files_hash: str):
    """Save metadata about the current state of the vector store."""
    metadata = {
        "files_hash": files_hash,
        "last_updated": datetime.now().isoformat(),
        "embedding_model": EMBEDDING_MODEL
    }
    metadata_path = STORE_METADATA_FILE
    os.makedirs(db_location, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

def load_store_metadata(db_location: str) -> dict:
    """Load metadata about the current state of the vector store."""
    metadata_path = STORE_METADATA_FILE
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def initialize_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DB_LOCATION, os.path.dirname(CONVERSATION_HISTORY_FILE_PATH)]:
        os.makedirs(directory, exist_ok=True)

# --- Vector Store Setup ---
def setup_vector_store(
    file_paths: List[str],
    enable_memory: bool = False,
    conversation_file_path: str = CONVERSATION_HISTORY_FILE_PATH,
    db_location: str = DB_LOCATION,
    embedding_model: str = EMBEDDING_MODEL,
    collection_name: str = COLLECTION_NAME,
    force_refresh: bool = False
):
    """
    Initializes the vector store and retriever from a list of files.
    Handles CSV, JSON, TXT, Markdown formats.
    Integrates conversation history if enabled.

    The store will only be recreated if:
    - It doesn't exist
    - The source files have changed
    - The embedding model has changed
    - force_refresh is True

    Args:
        file_paths: List of files to index
        enable_memory: Whether to include conversation history
        conversation_file_path: Path to conversation history file
        db_location: Where to store the vector database
        embedding_model: Model to use for embeddings
        collection_name: Name for the Chroma collection
        force_refresh: Force reindexing even if no changes detected

    Returns:
        The initialized retriever object or None if setup fails
    """
    # Initialize required directories
    initialize_directories()

    # Check if we need to recreate the store
    current_files_hash = get_files_hash(file_paths)
    stored_metadata = load_store_metadata(db_location)
    
    needs_refresh = (
        force_refresh or
        not os.path.exists(db_location) or
        stored_metadata.get("files_hash") != current_files_hash or
        stored_metadata.get("embedding_model") != embedding_model
    )

    if not needs_refresh:
        try:
            print("Loading existing vector store...")
            embeddings = OllamaEmbeddings(model=embedding_model)
            vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=db_location,
                embedding_function=embeddings
            )
            return vector_store.as_retriever(search_kwargs={"k": 3})
        except Exception as e:
            print(f"Error loading existing vector store, will recreate: {e}")
            needs_refresh = True

    if needs_refresh:
        print("Setting up vector store from files:", file_paths)
        embeddings = OllamaEmbeddings(model=embedding_model)

        # Parse documents from the provided files
        documents = parse_files_to_documents(file_paths)

        # Integrate conversation history if memory is enabled
        if enable_memory:
            if os.path.exists(conversation_file_path):
                try:
                    conversation_data = []
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
            
            # Save metadata about this store
            save_store_metadata(db_location, current_files_hash)
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            print("Retriever setup complete.")
            return retriever
        except Exception as e:
            print(f"Error setting up vector store: {e}")
            return None
