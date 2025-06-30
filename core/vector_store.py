# --- Standard Library ---
import os
import json
import hashlib
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from contextlib import contextmanager

# --- Third-Party Libraries ---
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.documents import Document
import chromadb
from chromadb.config import Settings

# --- Core Imports ---
from core.doc_utils import parse_files_to_documents, get_memory_documents
from logging_config import setup_logger
from constants import (
    DB_LOCATION,
    HISTORY_DIR,
    EMBEDDING_MODEL,
    COLLECTION_NAME,
    SHARED_MEMORY_ENABLED,
    STORE_METADATA_FILE,
)

# Initialize logger
logger = setup_logger(__name__)

# Global client instance
_chroma_client = None
_embeddings_cache = {}

# Keep track of session-specific memory retrievers
session_retrievers: Dict[str, VectorStoreRetriever] = {}

# Configure Chroma client settings once
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    allow_reset=True,
    is_persistent=True
)

def get_chroma_client():
    """Get or create a singleton Chroma client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=DB_LOCATION,
            settings=CHROMA_SETTINGS
        )
    return _chroma_client

def get_embeddings(model_name: str):
    """Get or create cached embeddings instance."""
    if model_name not in _embeddings_cache:
        _embeddings_cache[model_name] = OllamaEmbeddings(model=model_name)
    return _embeddings_cache[model_name]

@contextmanager
def collection_context(client, collection_name: str, reset: bool = False):
    """Context manager for safe collection operations."""
    try:
        if reset:
            try:
                existing_collections = [col.name for col in client.list_collections()]
                if collection_name in existing_collections:
                    client.delete_collection(collection_name)
                    logger.info(f"Deleted existing collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Could not delete collection {collection_name}: {e}")
        
        yield collection_name
        
    except Exception as e:
        logger.error(f"Error in collection context for {collection_name}: {e}")
        raise

def remove_session_retriever(session_id: str):
    """Remove a session-specific memory retriever."""
    if session_id in session_retrievers:
        try:
            # Clean up the vector store
            retriever = session_retrievers[session_id]
            if hasattr(retriever, 'vectorstore') and hasattr(retriever.vectorstore, 'delete_collection'):
                try:
                    retriever.vectorstore.delete_collection()
                except Exception as e:
                    logger.warning(f"Could not delete collection for session {session_id}: {e}")
            
            del session_retrievers[session_id]
            logger.info(f"Cleaned up memory retriever for session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up memory retriever for session {session_id}: {e}")

def get_files_hash(file_paths: List[str]) -> str:
    """Generate a hash of the file contents and modification times to detect changes."""
    if not file_paths:
        return ""
    
    hasher = hashlib.md5()
    for file_path in sorted(file_paths):  # Sort for consistency
        if os.path.exists(file_path):
            try:
                # Add file modification time and size
                stat = os.stat(file_path)
                hasher.update(f"{stat.st_mtime}:{stat.st_size}".encode())
            except OSError as e:
                logger.warning(f"Could not stat file {file_path}: {e}")
                continue
    
    return hasher.hexdigest()

def save_store_metadata(db_location: str, files_hash: str, store_type: str = "documents"):
    """Save metadata about the current state of the vector store."""
    metadata = {
        "files_hash": files_hash,
        "last_updated": datetime.now().isoformat(),
        "embedding_model": EMBEDDING_MODEL,
        "store_type": store_type,
        "version": "1.0"
    }
    
    metadata_path = (
        os.path.join(DB_LOCATION, "memory_metadata.json") 
        if store_type == "memory" 
        else STORE_METADATA_FILE
    )
        
    try:
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.debug(f"Saved metadata for {store_type} store")
    except Exception as e:
        logger.error(f"Error saving store metadata: {e}")

def load_store_metadata(db_location: str, store_type: str = "documents") -> dict:
    """Load metadata about the current state of the vector store."""
    metadata_path = (
        os.path.join(DB_LOCATION, "memory_metadata.json") 
        if store_type == "memory" 
        else STORE_METADATA_FILE
    )
        
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                logger.debug(f"Loaded metadata for {store_type} store")
                return metadata
        except Exception as e:
            logger.error(f"Error loading store metadata: {e}")
    
    return {}

def initialize_directories():
    """Create required directories if they don't exist."""
    directories = [DB_LOCATION, HISTORY_DIR, os.path.dirname(STORE_METADATA_FILE)]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            except OSError as e:
                logger.error(f"Failed to create directory {directory}: {e}")

def enhance_document_metadata(documents: List[Document], source_info: Dict[str, str]) -> List[Document]:
    """Enhance document metadata with source information."""
    for doc in documents:
        if hasattr(doc, 'metadata') and doc.metadata:
            doc.metadata.update(source_info)
        else:
            doc.metadata = source_info.copy()
    return documents

def load_session_documents(session_files: List[str]) -> List[Dict[str, Any]]:
    """Load and parse session documents from history files."""
    all_memory_documents = []
    doc_id = 0
    
    for session_file in session_files:
        if not os.path.exists(session_file):
            logger.warning(f"Session file does not exist: {session_file}")
            continue
            
        current_session_id = os.path.splitext(os.path.basename(session_file))[0]
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        message = json.loads(line)
                        
                        # Skip system messages
                        if message.get("role") == "system":
                            continue
                        
                        # Extract content
                        content = message.get("content", "")
                        if isinstance(content, str):
                            try:
                                parsed_content = json.loads(content)
                                if isinstance(parsed_content, dict):
                                    content = parsed_content.get("content", content)
                            except json.JSONDecodeError:
                                pass
                        
                        # Skip empty content
                        if not content or not content.strip():
                            continue
                            
                        # Create memory document
                        memory_doc = {
                            "page_content": str(content).strip(),
                            "metadata": {
                                "document_type": "conversation",
                                "source_file": session_file,
                                "session_id": current_session_id,
                                "document_id": f"memory_{doc_id}",
                                "store_type": "memory",
                                "timestamp": message.get("timestamp"),
                                "role": message.get("role", "unknown"),
                                "line_number": line_num
                            }
                        }
                        all_memory_documents.append(memory_doc)
                        doc_id += 1
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_num} in {session_file}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error processing session file {session_file}: {e}")
            continue
    
    return all_memory_documents

def setup_memory_store(
    history_dir: str,
    db_location: str,
    embedding_model: str,
    force_refresh: bool = False,
    session_id: Optional[str] = None
) -> Optional[VectorStoreRetriever]:
    """Setup the memory/conversation vector store."""
    
    # Ensure history directory exists
    if not os.path.exists(history_dir):
        logger.info(f"Creating history directory: {history_dir}")
        os.makedirs(history_dir, exist_ok=True)
    
    # Get session files based on configuration
    session_files = []
    if SHARED_MEMORY_ENABLED:
        # Get all session files for shared memory
        try:
            session_files = [
                os.path.join(history_dir, f) 
                for f in os.listdir(history_dir) 
                if f.endswith('.jsonl')
            ]
        except OSError as e:
            logger.error(f"Error listing history directory: {e}")
            return None
            
        if not session_files:
            logger.info("No session history files found for shared memory")
            return create_empty_memory_store(db_location, embedding_model)
    else:
        # Get only the current session file for isolated memory
        if not session_id:
            logger.warning("No session ID provided for isolated memory mode")
            return None
            
        session_file = os.path.join(history_dir, f"{session_id}.jsonl")
        if os.path.exists(session_file):
            session_files = [session_file]
        else:
            logger.info(f"Creating new memory store for session {session_id}")
            retriever = create_empty_memory_store(db_location, embedding_model, session_id)
            if retriever and session_id:
                session_retrievers[session_id] = retriever
            return retriever
    
    # Check if refresh is needed
    current_files_hash = get_files_hash(session_files)
    stored_metadata = load_store_metadata(db_location, "memory")
    
    needs_refresh = (
        force_refresh or
        stored_metadata.get("files_hash") != current_files_hash or
        stored_metadata.get("embedding_model") != embedding_model
    )

    # Try to load existing store if no refresh needed
    if not needs_refresh:
        try:
            logger.info("Loading existing memory vector store...")
            embeddings = get_embeddings(embedding_model)
            chroma_client = get_chroma_client()
            collection_name = "memory_collection"
            
            # Check if collection exists
            existing_collections = [col.name for col in chroma_client.list_collections()]
            if collection_name not in existing_collections:
                logger.info("Memory collection not found, will create new one")
                needs_refresh = True
            else:
                vector_store = Chroma(
                    client=chroma_client,
                    collection_name=collection_name,
                    embedding_function=embeddings
                )
                
                retriever = vector_store.as_retriever(search_kwargs={"k": 3})
                if not SHARED_MEMORY_ENABLED and session_id:
                    session_retrievers[session_id] = retriever
                return retriever
                
        except Exception as e:
            logger.error(f"Error loading existing memory vector store: {e}")
            needs_refresh = True

    # Create or refresh the memory store
    if needs_refresh:
        mode = "shared" if SHARED_MEMORY_ENABLED else "isolated"
        logger.info(f"Setting up {mode} memory vector store from session history files...")
        
        try:
            # Load documents from session files
            all_memory_documents = load_session_documents(session_files)
            
            if not all_memory_documents:
                logger.info("No conversation documents found, creating empty memory store")
                return create_empty_memory_store(db_location, embedding_model, session_id)

            # Setup vector store
            embeddings = get_embeddings(embedding_model)
            chroma_client = get_chroma_client()
            collection_name = "memory_collection"
            
            with collection_context(chroma_client, collection_name, reset=True):
                vector_store = Chroma(
                    client=chroma_client,
                    collection_name=collection_name,
                    embedding_function=embeddings
                )
                
                # Convert to LangChain documents and add to store
                langchain_docs = [Document(**doc) for doc in all_memory_documents]
                
                if langchain_docs:
                    # Add documents in batches to avoid memory issues
                    batch_size = 100
                    for i in range(0, len(langchain_docs), batch_size):
                        batch = langchain_docs[i:i + batch_size]
                        ids = [f"memory_{j}" for j in range(i, i + len(batch))]
                        vector_store.add_documents(documents=batch, ids=ids)
                    
                    logger.info(f"Added {len(langchain_docs)} conversation entries to memory store ({mode} mode)")
                
                # Save metadata
                save_store_metadata(db_location, current_files_hash, "memory")
                
                retriever = vector_store.as_retriever(search_kwargs={"k": 3})
                
                if not SHARED_MEMORY_ENABLED and session_id:
                    session_retrievers[session_id] = retriever
                
                logger.info(f"Memory retriever setup complete ({mode} mode)")
                return retriever
            
        except Exception as e:
            logger.error(f"Error setting up memory store: {e}")
            return create_empty_memory_store(db_location, embedding_model, session_id)

def create_empty_memory_store(
    db_location: str, 
    embedding_model: str, 
    session_id: Optional[str] = None
) -> Optional[VectorStoreRetriever]:
    """Create an empty memory vector store for new sessions or when no documents exist."""
    try:
        embeddings = get_embeddings(embedding_model)
        chroma_client = get_chroma_client()
        collection_name = "memory_collection"
        
        with collection_context(chroma_client, collection_name, reset=True):
            vector_store = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            mode = "shared" if SHARED_MEMORY_ENABLED else f"session {session_id}"
            logger.info(f"Created empty memory store for {mode}")
            return retriever
        
    except Exception as e:
        logger.error(f"Error creating empty memory store: {e}")
        return None

def setup_document_store(
    file_paths: List[str],
    db_location: str,
    embedding_model: str,
    collection_name: str,
    force_refresh: bool = False
) -> Optional[VectorStoreRetriever]:
    """Setup the document vector store."""
    if not file_paths:
        logger.warning("No file paths provided for document store")
        return None
    
    # Filter existing files
    existing_files = [f for f in file_paths if os.path.exists(f)]
    if not existing_files:
        logger.warning("No existing files found for document store")
        return None
    
    current_files_hash = get_files_hash(existing_files)
    stored_metadata = load_store_metadata(db_location, "documents")
    
    needs_refresh = (
        force_refresh or
        stored_metadata.get("files_hash") != current_files_hash or
        stored_metadata.get("embedding_model") != embedding_model
    )

    # Try to load existing store
    if not needs_refresh:
        try:
            logger.info("Loading existing document vector store...")
            embeddings = get_embeddings(embedding_model)
            chroma_client = get_chroma_client()
            
            # Check if collection exists
            existing_collections = [col.name for col in chroma_client.list_collections()]
            if collection_name not in existing_collections:
                logger.info("Document collection not found, will create new one")
                needs_refresh = True
            else:
                vector_store = Chroma(
                    client=chroma_client,
                    collection_name=collection_name,
                    embedding_function=embeddings
                )
                
                return vector_store.as_retriever(search_kwargs={"k": 5})
                
        except Exception as e:
            logger.error(f"Error loading existing document store: {e}")
            needs_refresh = True
    
    # Create or refresh the document store
    if needs_refresh:
        logger.info("Setting up document vector store...")
        
        try:
            # Parse documents
            documents = list(parse_files_to_documents(existing_files))
            if not documents:
                logger.warning("No documents parsed from files")
                return None
            
            # Enhance documents with metadata
            enhanced_documents = []
            for i, doc in enumerate(documents):
                source_file = doc.metadata.get('source', '')
                
                # Determine document type
                source_type = "document"
                if source_file:
                    source_lower = source_file.lower()
                    if 'review' in source_lower:
                        source_type = "review"
                    elif 'order' in source_lower:
                        source_type = "order"
                    elif 'menu' in source_lower:
                        source_type = "menu"
                
                source_info = {
                    "document_type": source_type,
                    "source_file": source_file,
                    "document_id": f"doc_{i}",
                    "store_type": "documents"
                }
                
                enhanced_doc = enhance_document_metadata([doc], source_info)[0]
                enhanced_documents.append(enhanced_doc)

            # Setup vector store
            embeddings = get_embeddings(embedding_model)
            chroma_client = get_chroma_client()
            
            with collection_context(chroma_client, collection_name, reset=True):
                vector_store = Chroma(
                    client=chroma_client,
                    collection_name=collection_name,
                    embedding_function=embeddings
                )
                
                # Add documents in batches
                batch_size = 50
                for i in range(0, len(enhanced_documents), batch_size):
                    batch = enhanced_documents[i:i + batch_size]
                    ids = [f"doc_{j}" for j in range(i, i + len(batch))]
                    vector_store.add_documents(documents=batch, ids=ids)
                
                logger.info(f"Added {len(enhanced_documents)} documents to the document vector store")
                
                # Save metadata
                save_store_metadata(db_location, current_files_hash, "documents")
                
                retriever = vector_store.as_retriever(search_kwargs={"k": 5})
                logger.info("Document retriever setup complete")
                return retriever
                
        except Exception as e:
            logger.error(f"Error setting up document vector store: {e}")
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
) -> Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]:
    """
    Initialize and return vector store retrievers.
    
    Args:
        file_paths: List of files to index in document store
        enable_memory: Whether to initialize memory store
        history_dir: Directory containing session history files
        db_location: Base directory for vector stores
        embedding_model: Name of the embedding model to use
        collection_name: Name for the document collection
        force_refresh: Whether to force rebuild stores
        session_id: Optional session ID for memory isolation
        
    Returns:
        Tuple of (document_retriever, memory_retriever)
        Either may be None if disabled or initialization fails
    """
    try:
        initialize_directories()
        
        document_retriever = None
        memory_retriever = None
        
        # Setup document store
        if file_paths:
            logger.info("Setting up document vector store...")
            document_retriever = setup_document_store(
                file_paths=file_paths,
                db_location=db_location,
                embedding_model=embedding_model,
                collection_name=collection_name,
                force_refresh=force_refresh
            )
        
        # Setup memory store if enabled
        if enable_memory:
            logger.info("Setting up memory vector store...")
            memory_retriever = setup_memory_store(
                history_dir=history_dir,
                db_location=db_location,
                embedding_model=embedding_model,
                force_refresh=force_refresh,
                session_id=session_id
            )
            
        return document_retriever, memory_retriever
        
    except Exception as e:
        logger.error(f"Error in vector store setup: {e}")
        return None, None

def cleanup_resources():
    """Clean up global resources."""
    global _chroma_client, _embeddings_cache, session_retrievers
    
    # Clean up session retrievers
    for session_id in list(session_retrievers.keys()):
        remove_session_retriever(session_id)
    
    # Clear caches
    _embeddings_cache.clear()
    
    # Close client if exists
    if _chroma_client:
        try:
            # ChromaDB client doesn't have an explicit close method
            _chroma_client = None
        except Exception as e:
            logger.error(f"Error closing Chroma client: {e}")
    
    logger.info("Cleaned up vector store resources")