"""
WebSocket Handler Module
Handles WebSocket connections and AI agent communication
"""

import asyncio
import json
import uuid
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

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
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> WebSocket
        self.session_to_user: Dict[str, str] = {}  # session_id -> user_id (if authenticated)
        self.disconnected_sessions: Dict[str, float] = {}  # session_id -> disconnect_timestamp
        self.session_timeout = 3600  # 1 hour timeout for disconnected sessions

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None) -> str:
        """
        Add a WebSocket connection to the manager and return its session ID
        
        Args:
            websocket: The WebSocket connection
            session_id: Optional session ID to reconnect to
            
        Returns:
            str: The session ID (either new or restored)
        """
        new_session = False
        
        if not session_id:
            # No session ID provided, generate new one
            session_id = str(uuid.uuid4())
            new_session = True
        elif session_id in self.active_connections:
            # If session is active, close the old connection and replace it
            try:
                old_websocket = self.active_connections[session_id]
                await old_websocket.close(code=1000, reason="Session replaced by new connection")
            except Exception as e:
                logger.warning(f"Failed to close old websocket for session {session_id}: {e}")
            logger.info(f"🔄 Replacing active connection for session {session_id}")
        elif session_id in self.disconnected_sessions:
            # Restore existing session
            logger.info(f"🔄 Restoring disconnected session {session_id}")
            del self.disconnected_sessions[session_id]
        else:
            # Unknown session ID, generate new one
            logger.warning(f"⚠️ Unknown session ID {session_id}, generating new session")
            session_id = str(uuid.uuid4())
            new_session = True
        
        self.active_connections[session_id] = websocket
        logger.info(f"🔌 WebSocket connected. Session ID: {session_id}. Total connections: {len(self.active_connections)}")
        
        if new_session:
            logger.info(f"🆕 Created new session: {session_id}")
        
        return session_id

    def disconnect(self, session_id: str):
        """
        Remove a WebSocket connection by session ID and store disconnect timestamp
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            # Store disconnect timestamp for potential reconnection
            self.disconnected_sessions[session_id] = asyncio.get_event_loop().time()
            logger.info(f"🔌 WebSocket disconnected. Session ID: {session_id} stored for potential reconnection.")
            
            # Clean up old disconnected sessions
            self._cleanup_old_sessions()

    def _cleanup_old_sessions(self):
        """Remove sessions that have been disconnected for longer than the timeout"""
        current_time = asyncio.get_event_loop().time()
        expired_sessions = [
            sid for sid, timestamp in self.disconnected_sessions.items()
            if current_time - timestamp > self.session_timeout
        ]
        
        for sid in expired_sessions:
            del self.disconnected_sessions[sid]
            if sid in self.session_to_user:
                del self.session_to_user[sid]
            logger.info(f"🧹 Cleaned up expired session: {sid}")

    def is_session_available(self, session_id: str) -> bool:
        """
        Check if a session ID is available for reconnection
        
        Returns:
            bool: True if the session can be reconnected to
        """
        return (
            session_id in self.disconnected_sessions and
            asyncio.get_event_loop().time() - self.disconnected_sessions[session_id] <= self.session_timeout
        )

    async def send_message(self, session_id: str, message: str | dict):
        """Send a message to a specific session"""
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent session: {session_id}")
            return

        websocket = self.active_connections[session_id]
        try:
            if isinstance(message, dict):
                await websocket.send_text(json.dumps(message))
            else:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"❌ Failed to send message to session {session_id}: {e}")
            self.disconnect(session_id)

    def associate_user(self, session_id: str, user_id: str):
        """Associate a user ID with a session ID (for authenticated sessions)"""
        self.session_to_user[session_id] = user_id
        logger.info(f"👤 Associated user {user_id} with session {session_id}")

    def get_session_info(self, session_id: str) -> dict:
        """Get information about a session"""
        return {
            "session_id": session_id,
            "is_active": session_id in self.active_connections,
            "is_disconnected": session_id in self.disconnected_sessions,
            "user_id": self.session_to_user.get(session_id),
            "disconnect_time": self.disconnected_sessions.get(session_id)
        }

# Global WebSocket manager
ws_manager = WebSocketManager()

async def send_welcome_message(session_id: str, is_reconnect: bool = False):
    """Send a single JSON-formatted welcome message"""
    welcome_payload = {
        "status": "success",
        "type": "welcome",
        "message": "🔄 Welcome back! Session restored." if is_reconnect else WELCOME_MESSAGE,
        "session_id": session_id,
        "is_reconnect": is_reconnect
    }
    await ws_manager.send_message(session_id, welcome_payload)

async def process_user_message(session_id: str, message: str) -> bool:
    """
    Process a user message through the AI agent

    Args:
        session_id: The session ID
        message: User message

    Returns:
        bool: True to continue, False to exit
    """
    app_state = get_app_state()

    # Check for exit command
    if message.strip().lower() == "exit":
        await ws_manager.send_message(session_id, {
            "status": "success",
            "type": "goodbye",
            "message": "👋 Session ended. Thanks for using Pizza AI Assistant!",
            "session_id": session_id
        })
        return False

    try:
        logger.info(f"📝 Processing message for session {session_id}: {message[:100]}{'...' if len(message) > 100 else ''}")

        # Stream response from AI agent
        async for chunk in run_agent(
            model=OLLAMA_MODEL,
            user_input=message,
            memory=app_state.memory,
            session_id=session_id,
            system_message=SYSTEM_MESSAGE
        ):
            logger.debug(f"🤖 Received chunk for session {session_id}: {type(chunk)} - {str(chunk)[:100]}...")

            # Always forward the chunk as JSON
            await ws_manager.send_message(session_id, chunk)

        logger.info(f"✅ Message processed for session {session_id}.")
        return True

    except Exception as e:
        logger.error(f"⚠️ Error processing message for session {session_id}: {e}", exc_info=True)
        error_msg = {
            "status": "error",
            "type": "exception",
            "message": f"⚠️ Sorry, I encountered an error: {str(e)}",
            "session_id": session_id
        }
        await ws_manager.send_message(session_id, error_msg)
        return True  # Continue despite error

@websocket_router.websocket("/ws/ai")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None, description="Optional session ID to reconnect to")
):
    """
    Main WebSocket endpoint for AI chat
    
    Args:
        websocket: The WebSocket connection
        session_id: Optional session ID to reconnect to an existing session
    """
    
    # Check if app is ready before accepting connection
    if not is_app_ready():
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "status": "error",
            "type": "server_error",
            "message": "❌ Server is not ready. Please try again in a moment."
        }))
        await websocket.close()
        return

    # Accept the connection first
    await websocket.accept()

    # Validate session ID and handle reconnection
    if session_id:
        if not ws_manager.is_session_available(session_id):
            await websocket.send_text(json.dumps({
                "status": "error",
                "type": "session_error",
                "message": "❌ Invalid or expired session ID. Starting new session."
            }))
            session_id = None  # Will create new session
        else:
            logger.info(f"🔄 Valid session ID provided: {session_id}")
    
    try:
        # Add to connection manager
        session_id = await ws_manager.connect(websocket, session_id)
        is_reconnect = session_id in ws_manager.disconnected_sessions
        
        # Send welcome message
        await send_welcome_message(session_id, is_reconnect)
        
        # Main message loop
        while True:
            logger.debug(f"⏳ Waiting for user input (session {session_id})...")
            
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
            # Process the message
            should_continue = await process_user_message(session_id, data)
            if not should_continue:
                break
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected by client (session {session_id})")
    except Exception as e:
        logger.error(f"⚠️ Unexpected WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "status": "error",
                "type": "exception",
                "message": f"⚠️ An unexpected error occurred: {str(e)}",
                "session_id": session_id
            }))
        except:
            pass  # Connection might already be closed
    finally:
        # Store session for potential reconnection
        ws_manager.disconnect(session_id)
