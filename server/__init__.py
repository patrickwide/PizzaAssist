"""
Server Package
Contains all server-related modules for the Pizza AI Assistant
"""

from .app import create_app
from .initialization import get_app_state, is_app_ready
from .websocket import websocket_router
from .routes import api_router

__all__ = [
    "create_app",
    "get_app_state", 
    "is_app_ready",
    "websocket_router",
    "api_router"
]

__version__ = "1.0.0"
__description__ = "Pizza AI Assistant Server Components"