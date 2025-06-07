# --- Standard Library ---
import os
import json
import hashlib
from typing import List, Dict, Tuple, Optional
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

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def get_files_hash(file_paths: List[str]) -> str:
    """Generate a hash of the file contents and modification times to detect changes."""
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

def save_store_metadata(db_location: str, files_hash: str, store_type: str = "documents"):
    """Save metadata about the current state of the vector store."""
    metadata = {
        "files_hash": files_hash,
        "last_updated": datetime.now().isoformat(),
        "embedding_model": EMBEDDING_MODEL,
        "store_type": store_type
    }
    
    if store_type == "memory":
        metadata_path = os.path.join(DB_LOCATION, "memory_metadata.json")
    else:
        metadata_path = STORE_METADATA_FILE
        
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

def load_store_metadata(db_location: str, store_type: str = "documents") -> dict:
    """Load metadata about the current state of the vector store."""
    if store_type == "memory":
        metadata_path = os.path.join(DB_LOCATION, "memory_metadata.json")
    else:
        metadata_path = STORE_METADATA_FILE
        
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading store metadata: {e}")
            return {}
    return {}

def initialize_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DB_LOCATION, os.path.dirname(CONVERSATION_HISTORY_FILE_PATH)]:
        os.makedirs(directory, exist_ok=True)

def enhance_document_metadata(documents: List, source_info: Dict[str, str]):
    """Enhance document metadata with source information."""
    for doc in documents:
        # Add source type to metadata
        if hasattr(doc, 'metadata'):
            doc.metadata.update(source_info)
        else:
            doc.metadata = source_info.copy()
    return documents

def vector_store(
    file_paths: List[str],
    enable_memory: bool = False,
    conversation_file_path: str = CONVERSATION_HISTORY_FILE_PATH,
    db_location: str = DB_LOCATION,
    embedding_model: str = EMBEDDING_MODEL,
    collection_name: str = COLLECTION_NAME,
    force_refresh: bool = False
) -> Tuple[Optional[object], Optional[object]]:
    """
    Initialize vector store and retriever from files.
    Returns a tuple of (document_retriever, memory_retriever).
    """
    # Initialize required directories
    initialize_directories()

    # Setup document retriever
    document_retriever = setup_document_store(
        file_paths, db_location, embedding_model, collection_name, force_refresh
    )
    
    # Setup memory retriever if enabled
    memory_retriever = None
    if enable_memory:
        memory_retriever = setup_memory_store(
            conversation_file_path, db_location, embedding_model, force_refresh
        )
    
    return document_retriever, memory_retriever

def setup_document_store(
    file_paths: List[str],
    db_location: str,
    embedding_model: str,
    collection_name: str,
    force_refresh: bool = False
):
    """Setup the main document vector store."""
    current_files_hash = get_files_hash(file_paths)
    stored_metadata = load_store_metadata(db_location, "documents")
    
    needs_refresh = (
        force_refresh or
        not os.path.exists(db_location) or
        stored_metadata.get("files_hash") != current_files_hash or
        stored_metadata.get("embedding_model") != embedding_model
    )

    if not needs_refresh:
        try:
            logger.info("Loading existing document vector store...")
            embeddings = OllamaEmbeddings(model=embedding_model)
            vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=db_location,
                embedding_function=embeddings
            )
            return vector_store.as_retriever(search_kwargs={"k": 5})
        except Exception as e:
            logger.error(f"Error loading existing document vector store, will recreate: {e}")
            needs_refresh = True

    if needs_refresh:
        logger.info(f"Setting up document vector store from files: {file_paths}")
        embeddings = OllamaEmbeddings(model=embedding_model)

        # Parse documents from the provided files
        from doc_utils import parse_files_to_documents
        documents = parse_files_to_documents(file_paths)

        # Enhance documents with source information
        enhanced_documents = []
        for i, doc in enumerate(documents):
            # Determine source type based on file path or content
            source_type = "unknown"
            source_file = "unknown"
            
            if hasattr(doc, 'metadata') and doc.metadata:
                source_file = doc.metadata.get('source', 'unknown')
                
                # Determine document type based on file path
                if 'review' in source_file.lower():
                    source_type = "review"
                elif 'order' in source_file.lower():
                    source_type = "order"
                elif 'menu' in source_file.lower():
                    source_type = "menu"
                else:
                    source_type = "document"
            
            # Enhance metadata
            source_info = {
                "document_type": source_type,
                "source_file": source_file,
                "document_id": f"doc_{i}",
                "store_type": "documents"
            }
            
            enhanced_doc = enhance_document_metadata([doc], source_info)[0]
            enhanced_documents.append(enhanced_doc)

        if not enhanced_documents:
            logger.warning("No documents found to add to the document vector store.")
            return None

        try:
            vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=db_location,
                embedding_function=embeddings
            )
            
            # Clear existing documents and add new ones
            try:
                vector_store.delete_collection()
                vector_store = Chroma(
                    collection_name=collection_name,
                    persist_directory=db_location,
                    embedding_function=embeddings
                )
            except:
                pass  # Collection might not exist
            
            ids = [f"doc_{i}" for i in range(len(enhanced_documents))]
            vector_store.add_documents(documents=enhanced_documents, ids=ids)
            logger.info(f"Added {len(enhanced_documents)} documents to the document vector store.")
            
            # Save metadata about this store
            save_store_metadata(db_location, current_files_hash, "documents")
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            logger.info("Document retriever setup complete.")
            return retriever
        except Exception as e:
            logger.error(f"Error setting up document vector store: {e}")
            return None

def setup_memory_store(
    conversation_file_path: str,
    db_location: str,
    embedding_model: str,
    force_refresh: bool = False
):
    """Setup the memory/conversation vector store."""
    memory_db_location = os.path.join(db_location, "memory_store")
    
    # Check if conversation file exists
    if not os.path.exists(conversation_file_path):
        logger.warning(f"Conversation history file not found: {conversation_file_path}")
        return None
    
    current_files_hash = get_files_hash([conversation_file_path])
    stored_metadata = load_store_metadata(db_location, "memory")
    
    needs_refresh = (
        force_refresh or
        not os.path.exists(memory_db_location) or
        stored_metadata.get("files_hash") != current_files_hash or
        stored_metadata.get("embedding_model") != embedding_model
    )

    if not needs_refresh:
        try:
            logger.info("Loading existing memory vector store...")
            embeddings = OllamaEmbeddings(model=embedding_model)
            vector_store = Chroma(
                collection_name="memory_collection",
                persist_directory=memory_db_location,
                embedding_function=embeddings
            )
            return vector_store.as_retriever(search_kwargs={"k": 3})
        except Exception as e:
            logger.error(f"Error loading existing memory vector store, will recreate: {e}")
            needs_refresh = True

    if needs_refresh:
        logger.info("Setting up memory vector store from conversation history...")
        embeddings = OllamaEmbeddings(model=embedding_model)

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
            
            # Parse conversation documents
            from doc_utils import get_memory_documents
            memory_documents = get_memory_documents(conversation_data)
            
            # Enhance memory documents with source information
            enhanced_memory_docs = []
            for i, doc in enumerate(memory_documents):
                source_info = {
                    "document_type": "conversation",
                    "source_file": conversation_file_path,
                    "document_id": f"memory_{i}",
                    "store_type": "memory"
                }
                enhanced_doc = enhance_document_metadata([doc], source_info)[0]
                enhanced_memory_docs.append(enhanced_doc)
            
            if not enhanced_memory_docs:
                logger.warning("No conversation documents found to add to memory store.")
                return None

            os.makedirs(memory_db_location, exist_ok=True)
            vector_store = Chroma(
                collection_name="memory_collection",
                persist_directory=memory_db_location,
                embedding_function=embeddings
            )
            
            # Clear existing and add new documents
            try:
                vector_store.delete_collection()
                vector_store = Chroma(
                    collection_name="memory_collection",
                    persist_directory=memory_db_location,
                    embedding_function=embeddings
                )
            except:
                pass
            
            ids = [f"memory_{i}" for i in range(len(enhanced_memory_docs))]
            vector_store.add_documents(documents=enhanced_memory_docs, ids=ids)
            logger.info(f"Added {len(enhanced_memory_docs)} conversation entries to memory store.")
            
            # Save metadata about this store
            save_store_metadata(db_location, current_files_hash, "memory")
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            logger.info("Memory retriever setup complete.")
            return retriever
            
        except Exception as e:
            logger.error(f"Error reading conversation history from {conversation_file_path}: {e}")
            return None