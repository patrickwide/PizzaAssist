"""
WebSocket Handler Module
Handles WebSocket connections and AI agent communication
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.agent import run_agent
from constants import OLLAMA_MODEL, SYSTEM_MESSAGE, WELCOME_MESSAGE
from .initialization import get_app_state, is_app_ready
from logging_config import setup_logger

logger = setup_logger(__name__)

# Create router for WebSocket endpoints
websocket_router = APIRouter()

class WebSocketManager:
    """Manages WebSocket connections and messaging"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 New WebSocket connection. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_message(self, websocket: WebSocket, message: str | dict):
        """Send a message to a specific WebSocket"""
        try:
            if isinstance(message, dict):
                await websocket.send_text(json.dumps(message))
            else:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            self.disconnect(websocket)

# Global WebSocket manager
ws_manager = WebSocketManager()

async def send_welcome_message(websocket: WebSocket):
    """Send a single JSON-formatted welcome message"""
    welcome_payload = {
        "status": "success",
        "type": "welcome",
        "message": WELCOME_MESSAGE,
    }
    await ws_manager.send_message(websocket, welcome_payload)

async def process_user_message(websocket: WebSocket, message: str) -> bool:
    """
    Process a user message through the AI agent

    Args:
        websocket: WebSocket connection
        message: User message

    Returns:
        bool: True to continue, False to exit
    """
    app_state = get_app_state()

    # Check for exit command
    if message.strip().lower() == "exit":
        await ws_manager.send_message(websocket, {
            "status": "success",
            "type": "goodbye",
            "message": "👋 Session ended. Thanks for using Pizza AI Assistant!"
        })
        return False

    try:
        logger.info(f"📝 Processing message: {message[:100]}{'...' if len(message) > 100 else ''}")

        # Stream response from AI agent
        async for chunk in run_agent(OLLAMA_MODEL, message, app_state.memory, system_message=SYSTEM_MESSAGE):
            logger.debug(f"🤖 Received chunk: {type(chunk)} - {str(chunk)[:100]}...")

            # Always forward the chunk as JSON
            await ws_manager.send_message(websocket, chunk)

        logger.info(f"✅ Message processed.")
        return True

    except Exception as e:
        logger.error(f"⚠️ Error processing message: {e}", exc_info=True)
        error_msg = {
            "status": "error",
            "type": "exception",
            "message": f"⚠️ Sorry, I encountered an error: {str(e)}"
        }
        await ws_manager.send_message(websocket, error_msg)
        return True  # Continue despite error

@websocket_router.websocket("/ws/ai")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for AI chat"""
    
    # Check if app is ready
    if not is_app_ready():
        await websocket.accept()
        await websocket.send_text("❌ Server is not ready. Please try again in a moment.")
        await websocket.close()
        return
    
    # Connect to WebSocket
    await ws_manager.connect(websocket)
    
    try:
        # Send welcome messages
        await send_welcome_message(websocket)
        
        # Main message loop
        while True:
            logger.debug("⏳ Waiting for user input...")
            
            # Receive message from client
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
            # Process the message
            should_continue = await process_user_message(websocket, data)
            if not should_continue:
                break
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"⚠️ Unexpected WebSocket error: {e}", exc_info=True)
        try:
            await ws_manager.send_message(websocket, f"⚠️ An unexpected error occurred: {str(e)}")
        except:
            pass  # Connection might already be closed
    finally:
        # Clean up connection
        ws_manager.disconnect(websocket)
