"""
Application Initialization Module
Handles startup initialization of vector store, memory, and other components
"""

import os
import json
from typing import Optional
from langchain_core.vectorstores import VectorStoreRetriever

# Core imports
from core.memory import AgentMemory
from core.constants import (
    CONVERSATION_HISTORY_FILE_PATH,
    CSV_FILE_PATH,
    ORDER_FILE_PATH,
    ENABLE_MEMORY
)
from core.vector_store import setup_vector_store
from core.tools.query_documents import set_retriever
from core.config import TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS
from logging_config import setup_logger

logger = setup_logger(__name__)

# Global state - shared across the application
class AppState:
    """Application state container"""
    memory: Optional[AgentMemory] = None
    retriever: Optional[VectorStoreRetriever] = None
    initialized: bool = False

# Global instance
app_state = AppState()

async def initialize_vector_store() -> Optional[VectorStoreRetriever]:
    """
    Initialize the vector store and retriever
    
    Returns:
        Optional[VectorStoreRetriever]: Initialized retriever or None if failed
    """
    try:
        logger.info("📚 Initializing vector store...")
        
        # Check if required files exist
        file_paths = [CSV_FILE_PATH, ORDER_FILE_PATH]
        missing_files = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                logger.warning(f"⚠️  File not found: {file_path}")
        
        if missing_files:
            logger.warning(f"⚠️  Missing files will be created automatically: {missing_files}")
        
        # Initialize vector store
        retriever = setup_vector_store(
            file_paths=file_paths,
            enable_memory=ENABLE_MEMORY
        )
        
        if retriever is None:
            logger.error("❌ Vector store initialization failed")
            return None
        
        # Set the retriever in query_documents module
        set_retriever(retriever)
        
        # Log success details
        vector_store_type = type(getattr(retriever, 'vectorstore', 'Unknown')).__name__
        search_params = getattr(retriever, 'search_kwargs', 'N/A')
        tags = getattr(retriever, 'tags', 'N/A')
        
        success_msg = (
            "✅ Vector store initialized successfully!\n"
            f"   • Vector Store Type: {vector_store_type}\n"
            f"   • Search Parameters: {search_params}\n"
            f"   • Tags: {tags}"
        )
        logger.info(success_msg)
        
        return retriever
        
    except Exception as e:
        logger.error(f"❌ Vector store initialization failed: {e}", exc_info=True)
        return None

async def initialize_memory() -> Optional[AgentMemory]:
    """
    Initialize the conversation memory
    
    Returns:
        Optional[AgentMemory]: Initialized memory or None if failed
    """
    try:
        logger.info("🧠 Initializing conversation memory...")
        
        memory = AgentMemory(
            max_history=15,
            history_file=CONVERSATION_HISTORY_FILE_PATH
        )
        
        logger.info("✅ Conversation memory initialized successfully")
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
            app_state.memory = AgentMemory(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)
        
        # Initialize vector store
        app_state.retriever = await initialize_vector_store()
        if app_state.retriever is None:
            logger.warning("⚠️  Vector store not available - document queries will be limited")
        
        # Mark as initialized
        app_state.initialized = True
        
        # Log final status
        status_msg = (
            "🎉 Application initialization completed!\n"
            f"   • Memory: {'✅ Ready' if app_state.memory else '❌ Failed'}\n"
            f"   • Vector Store: {'✅ Ready' if app_state.retriever else '⚠️  Limited'}\n"
            f"   • Overall Status: {'✅ Ready' if app_state.initialized else '❌ Failed'}"
        )
        logger.info(status_msg)
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}", exc_info=True)
        app_state.initialized = False
        
        # Ensure we have at least basic memory
        if app_state.memory is None:
            app_state.memory = AgentMemory(max_history=15, history_file=CONVERSATION_HISTORY_FILE_PATH)

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