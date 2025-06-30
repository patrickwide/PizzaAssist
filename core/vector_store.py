# --- Standard Library ---
import os
import json
import hashlib
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime

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

# Keep track of session-specific memory retrievers
session_retrievers: Dict[str, VectorStoreRetriever] = {}

# Configure Chroma client settings once
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    allow_reset=True,
    is_persistent=True
)

# Initialize a persistent Chroma client
def get_chroma_client():
    return chromadb.PersistentClient(
        path=DB_LOCATION,
        settings=CHROMA_SETTINGS
    )

def remove_session_retriever(session_id: str):
    """Remove a session-specific memory retriever."""
    if session_id in session_retrievers:
        try:
            # Clean up the vector store
            retriever = session_retrievers[session_id]
            if hasattr(retriever, 'vectorstore'):
                retriever.vectorstore.delete_collection()
            del session_retrievers[session_id]
            logger.info(f"Cleaned up memory retriever for session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up memory retriever for session {session_id}: {e}")

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
                retriever = create_empty_memory_store(memory_db_location, embedding_model, session_id)
                if retriever:
                    session_retrievers[session_id] = retriever
                return retriever
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
            
            # Use the shared client
            chroma_client = get_chroma_client()
            collection_name = "memory_collection"
            
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
                embedding_function=embeddings,
                client_settings=CHROMA_SETTINGS
            )
            
            # Clear existing and add new documents
            try:
                vector_store.delete_collection()
                vector_store = Chroma(
                    collection_name="memory_collection",
                    persist_directory=memory_db_location,
                    embedding_function=embeddings,
                    client_settings=CHROMA_SETTINGS
                )
            except:
                pass

            # Convert documents to LangChain format
            langchain_docs = [Document(**doc) for doc in all_memory_documents]
            
            # Add documents to vector store
            if langchain_docs:
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
        
        # Use the shared client
        chroma_client = get_chroma_client()
        collection_name = "memory_collection"
        
        # Clear any existing collection
        try:
            if collection_name in chroma_client.list_collections():
                chroma_client.delete_collection(collection_name)
        except:
            pass
            
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
            
            # Use the shared client
            chroma_client = get_chroma_client()
            
            vector_store = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
            
            return vector_store.as_retriever(search_kwargs={"k": 5})
        except Exception as e:
            logger.error(f"Error loading existing document store, will recreate: {e}")
            needs_refresh = True
    
    if needs_refresh:
        logger.info("Setting up document vector store...")
        embeddings = OllamaEmbeddings(model=embedding_model)
        
        # Parse and enhance documents
        enhanced_documents = []
        for i, doc in enumerate(parse_files_to_documents(file_paths)):
            # Extract source file from metadata
            source_file = doc.metadata.get('source', '')
            
            # Determine document type based on file name or content
            source_type = "unknown"
            if source_file:
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
            # Use the shared client
            chroma_client = get_chroma_client()
            
            # Clear existing collection if it exists
            try:
                if collection_name in chroma_client.list_collections():
                    chroma_client.delete_collection(collection_name)
            except:
                pass
            
            vector_store = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
            
            # Add documents to vector store
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
        
        # Setup document store
        document_retriever = None
        memory_retriever = None
        
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