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
    copy_template_if_missing
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
    base_dirs = [
        "data/db",
        "data/history",
        "data/documents",
        "scripts/templates"
    ]
    create_directories(base_dirs)

    doc_files = [
        "data/documents/orders.txt",
        "data/documents/realistic_restaurant_reviews.csv"
    ]
    create_files(doc_files)

    logger.info("Ensuring system and welcome messages are initialized...")
    template_dir = Path("scripts/templates")
    system_template = template_dir / "system_message.template.txt"
    welcome_template = template_dir / "welcome_message.template.txt"

    system_file = Path("data/system_message.txt")
    welcome_file = Path("data/welcome_message.txt")

    copy_template_if_missing(system_template, system_file)
    copy_template_if_missing(welcome_template, welcome_file)

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
