# --- Standard Library ---
import os
import json
import hashlib
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# --- Third-Party Libraries ---
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

# --- Application Config & Constants ---
from constants import (
    DB_LOCATION,
    EMBEDDING_MODEL,
    COLLECTION_NAME,
    STORE_METADATA_FILE,
    HISTORY_DIR,
    SHARED_MEMORY_ENABLED,
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
    """Create required directories if they don't exist."""
    for directory in [DB_LOCATION, HISTORY_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def enhance_document_metadata(documents: List, source_info: Dict[str, str]):
    """Enhance document metadata with source information."""
    for doc in documents:
        # Add source type to metadata
        if hasattr(doc, 'metadata'):
            doc.metadata.update(source_info)
        else:
            doc.metadata = source_info.copy()
    return documents

def setup_memory_store(
    history_dir: str,
    db_location: str,
    embedding_model: str,
    force_refresh: bool = False,
    session_id: Optional[str] = None
):
    """
    Setup the memory/conversation vector store.
    
    Args:
        history_dir: Directory containing session history files
        db_location: Base directory for vector store
        embedding_model: Name of the embedding model to use
        force_refresh: Whether to force rebuild the vector store
        session_id: Optional session ID to restrict memory to a single session
    """
    memory_db_location = os.path.join(db_location, "memory_store")
    
    # Check if history directory exists
    if not os.path.exists(history_dir):
        logger.info(f"History directory not found: {history_dir}")
        os.makedirs(history_dir, exist_ok=True)
    
    # Get session files based on configuration
    session_files = []
    if SHARED_MEMORY_ENABLED:
        # Get all session files for shared memory
        for file in os.listdir(history_dir):
            if file.endswith('.jsonl'):
                session_files.append(os.path.join(history_dir, file))
        # For shared memory, we need at least one file
        if not session_files:
            logger.info("No session history files found for shared memory")
            # Create empty vector store for shared memory
            return create_empty_memory_store(memory_db_location, embedding_model)
    else:
        # Get only the current session file for isolated memory
        if session_id:
            session_file = os.path.join(history_dir, f"{session_id}.jsonl")
            if os.path.exists(session_file):
                session_files = [session_file]
            else:
                logger.info(f"Creating new memory store for session {session_id}")
                # Create empty vector store for new session
                return create_empty_memory_store(memory_db_location, embedding_model, session_id)
        else:
            logger.info("No session ID provided for isolated memory mode")
            return None
    
    current_files_hash = get_files_hash(session_files)
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
        mode = "shared" if SHARED_MEMORY_ENABLED else "isolated"
        logger.info(f"Setting up {mode} memory vector store from session history files...")
        embeddings = OllamaEmbeddings(model=embedding_model)

        try:
            all_memory_documents = []
            doc_id = 0
            
            for session_file in session_files:
                current_session_id = os.path.splitext(os.path.basename(session_file))[0]
                try:
                    with open(session_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    message = json.loads(line)
                                    # Skip system messages as they don't need to be in memory
                                    if message.get("role") == "system":
                                        continue
                                        
                                    # Handle nested JSON content if present
                                    content = message.get("content", "")
                                    if isinstance(content, str):
                                        try:
                                            # Try to parse content as JSON if it's a string
                                            parsed_content = json.loads(content)
                                            if isinstance(parsed_content, dict):
                                                content = parsed_content.get("content", content)
                                        except json.JSONDecodeError:
                                            # If content is not JSON, use it as is
                                            pass
                                            
                                    # Create memory document
                                    memory_doc = {
                                        "page_content": content,
                                        "metadata": {
                                            "document_type": "conversation",
                                            "source_file": session_file,
                                            "session_id": current_session_id,
                                            "document_id": f"memory_{doc_id}",
                                            "store_type": "memory",
                                            "timestamp": message.get("timestamp"),
                                            "role": message.get("role")
                                        }
                                    }
                                    all_memory_documents.append(memory_doc)
                                    doc_id += 1
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error parsing message in {session_file}: {e}")
                                    continue
                except Exception as e:
                    logger.error(f"Error processing session file {session_file}: {e}")
                    continue
            
            if not all_memory_documents:
                logger.info("No conversation documents found, creating empty memory store")
                return create_empty_memory_store(memory_db_location, embedding_model, session_id)

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
            
            # Convert documents to Langchain Document format
            from langchain_core.documents import Document
            langchain_docs = [Document(**doc) for doc in all_memory_documents]
            
            # Add documents to vector store
            ids = [f"memory_{i}" for i in range(len(langchain_docs))]
            vector_store.add_documents(documents=langchain_docs, ids=ids)
            logger.info(f"Added {len(langchain_docs)} conversation entries to memory store ({mode} mode).")
            
            # Save metadata about this store
            save_store_metadata(db_location, current_files_hash, "memory")
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            logger.info(f"Memory retriever setup complete ({mode} mode).")
            return retriever
            
        except Exception as e:
            logger.error(f"Error setting up memory store: {e}")
            return create_empty_memory_store(memory_db_location, embedding_model, session_id)

def create_empty_memory_store(db_location: str, embedding_model: str, session_id: Optional[str] = None) -> Optional[VectorStoreRetriever]:
    """Create an empty memory vector store for new sessions or when no documents exist."""
    try:
        os.makedirs(db_location, exist_ok=True)
        embeddings = OllamaEmbeddings(model=embedding_model)
        vector_store = Chroma(
            collection_name="memory_collection",
            persist_directory=db_location,
            embedding_function=embeddings
        )
        
        # Clear any existing data
        try:
            vector_store.delete_collection()
            vector_store = Chroma(
                collection_name="memory_collection",
                persist_directory=db_location,
                embedding_function=embeddings
            )
        except:
            pass
        
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        mode = "shared" if SHARED_MEMORY_ENABLED else f"session {session_id}"
        logger.info(f"Created empty memory store for {mode}")
        return retriever
        
    except Exception as e:
        logger.error(f"Error creating empty memory store: {e}")
        return None

def vector_store(
    file_paths: List[str],
    enable_memory: bool = False,
    history_dir: str = HISTORY_DIR,
    db_location: str = DB_LOCATION,
    embedding_model: str = EMBEDDING_MODEL,
    collection_name: str = COLLECTION_NAME,
    force_refresh: bool = False,
    session_id: Optional[str] = None
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
            history_dir, db_location, embedding_model, force_refresh, session_id
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