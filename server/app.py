"""
FastAPI Application Factory
Creates and configures the main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .initialization import initialize_app_components
from .websocket import websocket_router
from .routes import api_router
from logging_config import setup_logger

logger = setup_logger(__name__)

# Define lifespan context manager
async def async_lifespan(app: FastAPI):
    """Initialize and cleanup application components"""
    # Startup
    logger.info("🚀 FastAPI application starting up...")
    await initialize_app_components()
    logger.info("✅ FastAPI application startup completed")
    
    yield
    
    # Shutdown
    logger.info("🛑 FastAPI application shutting down...")
    # Add any cleanup logic here if needed
    logger.info("✅ FastAPI application shutdown completed")

# 
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    # Create FastAPI instance
    app = FastAPI(
        title="Pizza AI Assistant",
        description="AI-powered pizza restaurant assistant with WebSocket support",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=async_lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(websocket_router)
    app.include_router(api_router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with basic information"""
        return {
            "message": "🍕 Pizza AI Assistant WebSocket Server",
            "status": "running",
            "endpoints": {
                "websocket": "/ws/ai",
                "health": "/health",
                "status": "/status",
                "info": "/info",
                "docs": "/docs"
            }
        }
    
    logger.info("🏗️  FastAPI application created successfully")
    return app