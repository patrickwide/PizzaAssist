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
    CONVERSATION_HISTORY_FILE_PATH,
    CSV_FILE_PATH,
    ORDER_FILE_PATH,
    ENABLE_MEMORY
)
from core.vector_store import vector_store
from core.tools.query_documents import set_documents_retriever
from core.tools.query_memory import query_memory, set_memory_retriever  # Import memory tool
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS
from logging_config import setup_logger

logger = setup_logger(__name__)

# Global state - shared across the application
class AppState:
    """Application state container"""
    memory: Optional[ChatHistoryManager] = None
    document_retriever: Optional[VectorStoreRetriever] = None
    memory_retriever: Optional[VectorStoreRetriever] = None
    initialized: bool = False

# Global instance
app_state = AppState()

async def initialize_vector_store() -> Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]:
    """
    Initialize the vector store and both retrievers
    
    Returns:
        Tuple[Optional[VectorStoreRetriever], Optional[VectorStoreRetriever]]: 
        (document_retriever, memory_retriever) or (None, None) if failed
    """
    try:
        logger.info("📚 Initializing vector stores...")
        
        # Check if required files exist
        file_paths = [CSV_FILE_PATH, ORDER_FILE_PATH]
        missing_files = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                logger.warning(f"⚠️  File not found: {file_path}")
        
        if missing_files:
            logger.warning(f"⚠️  Missing files will be created automatically: {missing_files}")
        
        # Initialize vector store - now returns tuple
        retrievers = vector_store(
            file_paths=file_paths,
            enable_memory=ENABLE_MEMORY
        )
        
        # Unpack the tuple - vector_store now returns (document_retriever, memory_retriever)
        if isinstance(retrievers, tuple) and len(retrievers) == 2:
            document_retriever, memory_retriever = retrievers
        else:
            # Fallback for backward compatibility
            document_retriever = retrievers
            memory_retriever = None
            logger.warning("Vector store setup returned single retriever instead of tuple. Memory queries may not work.")
        
        if document_retriever is None:
            logger.error("❌ Document retriever initialization failed")
            return None, None
        
        # Set the document retriever in query_documents module
        set_documents_retriever(document_retriever)
        
        # Set the memory retriever in query_memory module if available
        if memory_retriever is not None:
            set_memory_retriever(memory_retriever)
        
        # Just log basic success - detailed status will be shown by display_initialization_status()
        logger.info("✅ Vector stores initialized successfully")
        
        return document_retriever, memory_retriever
        
    except Exception as e:
        logger.error(f"❌ Vector store initialization failed: {e}", exc_info=True)
        return None, None

async def initialize_memory() -> Optional[ChatHistoryManager]:
    """
    Initialize the conversation memory
    
    Returns:
        Optional[ChatHistoryManager]: Initialized memory or None if failed
    """
    try:
        logger.info("🧠 Initializing conversation memory...")
        
        memory = ChatHistoryManager(
            max_history=15,
            history_file=CONVERSATION_HISTORY_FILE_PATH
        )
        
        logger.info("✅ ChatHistoryManager initialized successfully")
        return memory
        
    except Exception as e:
        logger.error(f"❌ Memory initialization failed: {e}", exc_info=True)
        return None

async def initialize_tools():
    """Initialize and log available tool definitions"""
    try:
        logger.info("🔧 Initializing tools...")
        
        if not TOOL_DEFINITIONS:
            logger.warning("⚠️  No tool definitions available")
            return

        logger.info(f"📋 Available tools ({len(TOOL_DEFINITIONS)}):")
        
        for i, tool in enumerate(TOOL_DEFINITIONS, 1):
            # Compact one-liner with key info
            required_params = tool.get('parameters', {}).get('required', [])
            logger.info(f"  🔨 #{i}: {tool['name']} | Required: {', '.join(required_params)}")
            
            # Optional: Show description on separate line for readability
            if 'description' in tool:
                logger.info(f"     📝 {tool['description'][:80]}{'...' if len(tool['description']) > 80 else ''}")

        logger.info("🎉 Tools initialization completed")

    except Exception as e:
        logger.error(f"❌ Tools initialization failed: {e}", exc_info=True)

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
        if app_state.memory_retriever is not None:
            memory_status_msg = (
                f"✅ Memory Retriever successfully initialized!\n"
                f"   • Tags         : {getattr(app_state.memory_retriever, 'tags', 'N/A')}\n"
                f"   • Vector Store : {type(getattr(app_state.memory_retriever, 'vectorstore', 'N/A')).__name__}\n"
                f"   • Search Params: {getattr(app_state.memory_retriever, 'search_kwargs', 'N/A')}"
            )
            logger.info(memory_status_msg)
        else:
            logger.error("❌ Memory Retriever initialization failed. Memory queries will not work.")
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
            logger.error("❌ Failed to initialize memory - using fallback")
            app_state.memory = ChatHistoryManager(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)
        
        # Initialize vector stores - now returns tuple
        app_state.document_retriever, app_state.memory_retriever = await initialize_vector_store()
        
        if app_state.document_retriever is None:
            logger.warning("⚠️  Document retriever not available - document queries will be limited")
        
        if ENABLE_MEMORY and app_state.memory_retriever is None:
            logger.warning("⚠️  Memory retriever not available - memory queries will be limited")
        
        # Mark as initialized
        app_state.initialized = True
        
        # Display detailed initialization status
        display_initialization_status()
        
        # Log final status
        status_msg = (
            "🎉 Application initialization completed!\n"
            f"   • Memory: {'✅ Ready' if app_state.memory else '❌ Failed'}\n"
            f"   • Document Retriever: {'✅ Ready' if app_state.document_retriever else '⚠️  Limited'}\n"
            f"   • Memory Retriever: {'✅ Ready' if app_state.memory_retriever else ('⚠️  Limited' if ENABLE_MEMORY else '📝 Disabled')}\n"
            f"   • Overall Status: {'✅ Ready' if app_state.initialized else '❌ Failed'}"
        )
        logger.info(status_msg)
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}", exc_info=True)
        app_state.initialized = False
        
        # Ensure we have at least basic memory
        if app_state.memory is None:
            app_state.memory = ChatHistoryManager(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)

def get_app_state() -> AppState:
    """
    Get the current application state
    
    Returns:
        AppState: Current application state
    """
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