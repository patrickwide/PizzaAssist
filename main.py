#!/usr/bin/env python3
"""
Pizza AI Assistant - Main Entry Point
Run this file to set up project structure and start the WebSocket server.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import internal modules
from server.app import create_app
from logging_config import setup_logger
from scripts.create_data_structure import (
    create_directories,
    create_files,
)

# Import constants
from constants import (
    DB_DIR,
    HISTORY_DIR,
    DOCUMENTS_DIR,
    # 
    ORDER_FILE_PATH,
    CSV_FILE_PATH
)


# Initialize logger
logger = setup_logger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Start the Pizza AI Assistant WebSocket server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Logging level")
    return parser.parse_args()

def prepare_project_structure():
    """Prepare necessary directories, files, and templates."""
    # Ensure base directories exist
    logger.info("Ensuring project directories and files are set up...")
    base_dirs = [
        DB_DIR,
        HISTORY_DIR,
        DOCUMENTS_DIR,
    ]
    create_directories(base_dirs)


    # Create necessary files
    logger.info("Creating necessary files for the project...")
    doc_files = [
        ORDER_FILE_PATH,
        CSV_FILE_PATH
    ]
    create_files(doc_files)

    logger.info("✅ Setup complete. Project structure and message templates are ready.")

def main():
    """Main entry point for the Pizza AI Assistant."""
    try:
        args = parse_args()

        logger.info("🍕 Starting Pizza AI Assistant setup and server...")

        # Ensure necessary directories and files exist
        prepare_project_structure()

        # Create FastAPI app - tools will be initialized during startup
        app = create_app()

        import uvicorn
        config = uvicorn.Config(
            app=app,
            host=args.host,
            port=args.port,
            loop="asyncio",
            log_level=args.log_level,
            access_log=True
        )

        server = uvicorn.Server(config)

        logger.info(f"🚀 Server starting on http://{args.host}:{args.port}")
        logger.info(f"🔌 WebSocket endpoint: ws://{args.host}:{args.port}/ws/ai")
        logger.info(f"❤️  Health check: http://{args.host}:{args.port}/health")
        logger.info("🛑 Press Ctrl+C to stop the server")

        asyncio.run(server.serve())

    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested by user")
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.info("💡 Please install required packages: pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
