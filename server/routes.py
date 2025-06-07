"""
HTTP Routes Module
Defines REST API endpoints for the application
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .initialization import get_app_state, is_app_ready
from core.constants import OLLAMA_MODEL, SYSTEM_MESSAGE
from logging_config import setup_logger

logger = setup_logger(__name__)

# Create router for API endpoints
api_router = APIRouter(prefix="/api/v1", tags=["api"])

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    message: str
    components: Dict[str, Any]
    ready: bool

class StatusResponse(BaseModel):
    """Status response model"""
    application: str
    version: str
    model: str
    components: Dict[str, Any]

@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns the current health status of the application
    """
    try:
        app_state = get_app_state()
        is_ready = is_app_ready()
        
        components = {
            "memory": {
                "status": "healthy" if app_state.memory is not None else "unhealthy",
                "initialized": app_state.memory is not None,
                "max_history": getattr(app_state.memory, 'max_history', None) if app_state.memory else None
            },
            "vector_store": {
                "status": "healthy" if app_state.retriever is not None else "limited",
                "initialized": app_state.retriever is not None,
                "type": type(getattr(app_state.retriever, 'vectorstore', None)).__name__ if app_state.retriever else None
            },
            "initialization": {
                "status": "healthy" if app_state.initialized else "failed",
                "completed": app_state.initialized
            }
        }
        
        overall_status = "healthy" if is_ready else "degraded"
        message = "All systems operational" if is_ready else "Some components have issues"
        
        return HealthResponse(
            status=overall_status,
            message=message,
            components=components,
            ready=is_ready
        )
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@api_router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get detailed application status
    Returns comprehensive information about the application state
    """
    try:
        app_state = get_app_state()
        
        components = {
            "memory": {
                "initialized": app_state.memory is not None,
                "max_history": getattr(app_state.memory, 'max_history', None) if app_state.memory else None,
                "history_file": getattr(app_state.memory, 'history_file', None) if app_state.memory else None
            },
            "vector_store": {
                "initialized": app_state.retriever is not None,
                "vector_store_type": type(getattr(app_state.retriever, 'vectorstore', None)).__name__ if app_state.retriever else None,
                "search_kwargs": getattr(app_state.retriever, 'search_kwargs', None) if app_state.retriever else None,
                "tags": getattr(app_state.retriever, 'tags', None) if app_state.retriever else None
            },
            "initialization": {
                "completed": app_state.initialized,
                "overall_ready": is_app_ready()
            }
        }
        
        return StatusResponse(
            application="Pizza AI Assistant",
            version="1.0.0",
            model=OLLAMA_MODEL,
            components=components
        )
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@api_router.get("/info")
async def get_info():
    """
    Get basic application information
    """
    return {
        "name": "Pizza AI Assistant",
        "description": "AI-powered pizza restaurant assistant with WebSocket support",
        "version": "1.0.0",
        "endpoints": {
            "websocket": {
                "chat": "/ws/ai",
                "status": "/ws/status"
            },
            "http": {
                "health": "/api/v1/health",
                "status": "/api/v1/status",
                "info": "/api/v1/info"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "model": OLLAMA_MODEL,
        "features": [
            "Real-time chat via WebSocket",
            "Document query and retrieval",
            "Order processing",
            "Restaurant reviews and recommendations",
            "Conversation memory"
        ]
    }

@api_router.post("/reset")
async def reset_memory():
    """
    Reset conversation memory
    Clears the conversation history
    """
    try:
        app_state = get_app_state()
        
        if app_state.memory is None:
            raise HTTPException(status_code=503, detail="Memory not initialized")
        
        # Reset memory (you might need to implement this method in AgentMemory)
        if hasattr(app_state.memory, 'clear'):
            app_state.memory.clear()
            logger.info("🧠 Conversation memory reset")
            return {"message": "Conversation memory reset successfully", "status": "success"}
        else:
            logger.warning("⚠️ Memory reset method not available")
            return {"message": "Memory reset not supported", "status": "warning"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Memory reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Memory reset failed: {str(e)}")

@api_router.get("/metrics")
async def get_metrics():
    """
    Get basic application metrics
    """
    try:
        app_state = get_app_state()
        
        # Basic metrics - you can expand this based on your needs
        metrics = {
            "uptime": "Not implemented",  # You can implement uptime tracking
            "memory_usage": "Not implemented",  # You can implement memory usage tracking
            "total_conversations": "Not implemented",  # You can track this
            "components": {
                "memory_initialized": app_state.memory is not None,
                "vector_store_initialized": app_state.retriever is not None,
                "app_initialized": app_state.initialized
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {str(e)}")