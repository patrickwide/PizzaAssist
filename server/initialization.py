"""
Application Initialization Module
Handles startup initialization of vector store, memory, and other components
"""

import os
import json
from typing import Optional, Tuple
from langchain_core.vectorstores import VectorStoreRetriever

# Core imports
from core.memory import ChatHistoryManager
from constants import (
    HISTORY_DIR,
    CSV_FILE_PATH,
    ORDER_FILE_PATH,
    ENABLE_MEMORY,
    SHARED_MEMORY_ENABLED
)
from core.vector_store import vector_store
from core.tools.query_documents import set_documents_retriever
from core.tools.query_memory import query_memory, set_memory_retriever
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS
from core.utils import log_available_tools
from logging_config import setup_logger

logger = setup_logger(__name__)

# Global state - shared across the application
class AppState:
    """Application state container"""
    memory: Optional[ChatHistoryManager] = None
    document_retriever: Optional[VectorStoreRetriever] = None
    memory_retriever: Optional[VectorStoreRetriever] = None  # Only used in shared memory mode
    initialized: bool = False

# Initialize global state
app_state = AppState()

async def initialize_vector_store(session_id: Optional[str] = None) -> Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]:
    """
    Initialize vector stores for documents and memory
    
    Args:
        session_id: Optional session ID for memory isolation
        
    Returns:
        Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]: 
            A tuple of (document_retriever, memory_retriever)
    """
    try:
        logger.info("📚 Initializing vector stores...")
        
        # Initialize document retriever first
        document_retriever = None
        memory_retriever = None
        
        # Always initialize document retriever
        retrievers = vector_store(
            file_paths=[CSV_FILE_PATH, ORDER_FILE_PATH],
            enable_memory=False  # We'll handle memory separately
        )
        
        if isinstance(retrievers, tuple) and len(retrievers) == 2:
            document_retriever, _ = retrievers
            if document_retriever is not None:
                set_documents_retriever(document_retriever)
                logger.info("✅ Document retriever initialized successfully")
        
        # Initialize memory retriever only if:
        # 1. Memory is enabled
        # 2. Either SHARED_MEMORY_ENABLED is True OR we have a session_id
        if ENABLE_MEMORY and (SHARED_MEMORY_ENABLED or session_id):
            memory_retrievers = vector_store(
                file_paths=[],  # No document files needed for memory
                enable_memory=True,
                session_id=session_id
            )
            if isinstance(memory_retrievers, tuple) and len(memory_retrievers) == 2:
                _, memory_retriever = memory_retrievers
                if memory_retriever is not None:
                    set_memory_retriever(memory_retriever, session_id)
                    logger.info(f"✅ Memory retriever initialized successfully for {'shared mode' if SHARED_MEMORY_ENABLED else f'session {session_id}'}")
                
        logger.info("✅ Vector stores initialized successfully")
        return document_retriever, memory_retriever
            
    except Exception as e:
        logger.error(f"❌ Vector store initialization failed: {e}")
        return None, None

async def initialize_memory() -> Optional[ChatHistoryManager]:
    """
    Initialize the conversation memory manager for session-based storage
    
    Returns:
        Optional[ChatHistoryManager]: Initialized memory or None if failed
    """
    try:
        logger.info("🧠 Initializing conversation memory...")
        
        # Create history directory for session files
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        memory = ChatHistoryManager(
            max_history=15,
            history_dir=HISTORY_DIR
        )
        
        logger.info("✅ ChatHistoryManager initialized successfully")
        return memory
        
    except Exception as e:
        logger.error(f"❌ Memory initialization failed: {e}", exc_info=True)
        return None

async def initialize_tools():
    """Initialize and log available tool definitions"""
    log_available_tools()

def display_initialization_status():
    """Display the status of retriever initialization."""
    # Document retriever status
    if app_state.document_retriever is not None:
        doc_status_msg = (
            f"✅ Document Retriever successfully initialized!\n"
            f"   • Tags         : {getattr(app_state.document_retriever, 'tags', 'N/A')}\n"
            f"   • Vector Store : {type(getattr(app_state.document_retriever, 'vectorstore', 'N/A')).__name__}\n"
            f"   • Search Params: {getattr(app_state.document_retriever, 'search_kwargs', 'N/A')}"
        )
        logger.info(doc_status_msg)
    else:
        logger.error("❌ Document Retriever initialization failed. Document queries will not work.")

    # Memory retriever status
    if ENABLE_MEMORY:
        if SHARED_MEMORY_ENABLED:
            if app_state.memory_retriever is not None:
                memory_status_msg = (
                    f"✅ Memory Retriever successfully initialized (shared mode)!\n"
                    f"   • Tags         : {getattr(app_state.memory_retriever, 'tags', 'N/A')}\n"
                    f"   • Vector Store : {type(getattr(app_state.memory_retriever, 'vectorstore', 'N/A')).__name__}\n"
                    f"   • Search Params: {getattr(app_state.memory_retriever, 'search_kwargs', 'N/A')}"
                )
                logger.info(memory_status_msg)
            else:
                logger.error("❌ Shared Memory Retriever initialization failed")
        else:
            logger.info("📝 Memory retriever will be initialized per session")
    else:
        logger.info("📝 Memory is disabled. Conversation history will not be searchable.")

async def initialize_app_components():
    """
    Initialize all application components
    This function is called during FastAPI startup
    """
    global app_state
    
    try:
        logger.info("🚀 Starting application initialization...")
        
        # Initialize tools first
        await initialize_tools()
        
        # Initialize memory
        app_state.memory = await initialize_memory()
        if app_state.memory is None:
            logger.error("❌ Failed to initialize memory manager")
            return
        
        # Initialize vector stores (without session ID for initial setup)
        app_state.document_retriever, app_state.memory_retriever = await initialize_vector_store()
        
        if app_state.document_retriever is None:
            logger.warning("⚠️  Document retriever not available - document queries will be limited")
        
        # Mark as initialized
        app_state.initialized = True
        
        # Display detailed initialization status
        display_initialization_status()
        
        # Log final status
        memory_status = (
            "✅ Ready" if SHARED_MEMORY_ENABLED and app_state.memory_retriever 
            else "⏳ Session-based" if not SHARED_MEMORY_ENABLED 
            else "⚠️  Failed"
        )
        
        status_msg = (
            "🎉 Application initialization completed!\n"
            f"   • Memory: {'✅ Ready' if app_state.memory else '❌ Failed'}\n"
            f"   • Document Retriever: {'✅ Ready' if app_state.document_retriever else '⚠️  Limited'}\n"
            f"   • Memory Retriever: {memory_status}\n"
            f"   • Overall Status: {'✅ Ready' if app_state.initialized else '❌ Failed'}"
        )
        logger.info(status_msg)
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}", exc_info=True)
        app_state.initialized = False

def get_app_state() -> AppState:
    """Get the global application state"""
    return app_state

def is_app_ready() -> bool:
    """
    Check if the application is ready to handle requests
    
    Returns:
        bool: True if app is ready, False otherwise
    """
    return app_state.initialized and app_state.memory is not None

def get_memory() -> Optional[ChatHistoryManager]:
    """
    Get the initialized memory instance
    
    Returns:
        Optional[ChatHistoryManager]: Memory instance or None if not available
    """
    return app_state.memory

def get_document_retriever() -> Optional[VectorStoreRetriever]:
    """
    Get the initialized document retriever
    
    Returns:
        Optional[VectorStoreRetriever]: Document retriever or None if not available
    """
    return app_state.document_retriever

def get_memory_retriever() -> Optional[VectorStoreRetriever]:
    """
    Get the initialized memory retriever
    
    Returns:
        Optional[VectorStoreRetriever]: Memory retriever or None if not available
    """
    return app_state.memory_retriever