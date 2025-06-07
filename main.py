#!/usr/bin/env python3
"""
Pizza AI Assistant - Main Entry Point
Run this file to start the WebSocket server
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import server app
from server.app import create_app
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def main():
    """Main entry point for the Pizza AI Assistant"""
    try:
        logger.info("🍕 Starting Pizza AI Assistant Server...")
        
        # Create the FastAPI app
        app = create_app()
        
        # Import uvicorn here to avoid import issues
        import uvicorn
        
        # Server configuration
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            loop="asyncio",
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        logger.info("🚀 Server starting on http://127.0.0.1:8000")
        logger.info("🔌 WebSocket endpoint: ws://127.0.0.1:8000/ws/ai")
        logger.info("❤️  Health check: http://127.0.0.1:8000/health")
        logger.info("🛑 Press Ctrl+C to stop the server")
        
        # Run the server
        asyncio.run(server.serve())
        
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested by user")
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.info("💡 Please install required packages: pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()