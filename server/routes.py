"""
HTTP Routes Module
Defines REST API endpoints for the application
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .initialization import get_app_state, is_app_ready
from .websocket import ws_manager
from constants import OLLAMA_MODEL
from logging_config import setup_logger

logger = setup_logger(__name__)

# Create router for API endpoints - removed prefix to make routes accessible at root
api_router = APIRouter(tags=["api"])

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    message: str
    components: Dict[str, Any]
    ready: bool
    sessions: Dict[str, Any]


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
                "status": "healthy" if app_state.document_retriever is not None else "limited",
                "initialized": app_state.document_retriever is not None,
                "type": type(getattr(app_state.document_retriever, 'vectorstore', None)).__name__ if app_state.document_retriever else None
            },
            "initialization": {
                "status": "healthy" if app_state.initialized else "failed",
                "completed": app_state.initialized
            }
        }
        
        # Get session information
        active_sessions = len(ws_manager.active_connections)
        session_info = {
            "active_sessions": active_sessions,
            "session_ids": list(ws_manager.active_connections.keys()),
            "authenticated_users": list(ws_manager.session_to_user.values())
        }
        
        overall_status = "healthy" if is_ready else "degraded"
        message = "All systems operational" if is_ready else "Some components have issues"
        
        return HealthResponse(
            status=overall_status,
            message=message,
            components=components,
            ready=is_ready,
            sessions=session_info
        )
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
