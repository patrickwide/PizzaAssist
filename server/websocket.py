"""
WebSocket Handler Module
Handles WebSocket connections and AI agent communication with persistent sessions
"""

import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from core.agent import run_agent
from constants import OLLAMA_MODEL, SYSTEM_MESSAGE, WELCOME_MESSAGE, SHARED_MEMORY_ENABLED
from .initialization import get_app_state, is_app_ready, initialize_vector_store
from core.tools.query_memory import remove_session_retriever
from logging_config import setup_logger

logger = setup_logger(__name__)

# Create router for WebSocket endpoints
websocket_router = APIRouter()

class WebSocketManager:
    """Manages WebSocket connections and messaging with persistent storage"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> WebSocket
        self.session_to_user: Dict[str, str] = {}  # session_id -> user_id
        self.history_dir = "data/history"  # Directory for storing session history
        
        # Ensure history directory exists
        os.makedirs(self.history_dir, exist_ok=True)

    def _get_session_file(self, session_id: str) -> str:
        """Get the path to a session's history file"""
        return os.path.join(self.history_dir, f"{session_id}.jsonl")

    def _load_session_history(self, session_id: str) -> tuple[list, dict]:
        """Load session history from disk"""
        history_file = self._get_session_file(session_id)
        messages = []
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            messages.append(json.loads(line))
                logger.info(f"📚 Loaded {len(messages)} messages from session {session_id}")
            stats = self._analyze_session_history(messages)
            return messages, stats
        except Exception as e:
            logger.error(f"❌ Error loading session history for {session_id}: {e}")
            return [], self._analyze_session_history([])

    def _analyze_session_history(self, messages: list) -> dict:
        """Analyze session history and return statistics"""
        if not messages:
            return {
                "user_messages": 0,
                "assistant_messages": 0,
                "total_messages": 0,
                "approx_tokens": 0,
                "last_message_time": None
            }

        user_msgs = sum(1 for m in messages if m.get("role") == "user")
        assistant_msgs = sum(1 for m in messages if m.get("role") == "assistant")
        # Rough token estimation (4 chars ≈ 1 token)
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        approx_tokens = total_chars // 4

        last_message = messages[-1]
        last_time = last_message.get("timestamp", None)

        return {
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "total_messages": len(messages),
            "approx_tokens": approx_tokens,
            "last_message_time": last_time
        }

    def session_exists(self, session_id: str) -> bool:
        """Check if a session file exists"""
        return os.path.exists(self._get_session_file(session_id))

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None) -> tuple[str, dict, list]:
        """
        Add a WebSocket connection to the manager and return session info
        
        Args:
            websocket: The WebSocket connection
            session_id: Optional session ID to reconnect to
            
        Returns:
            tuple[str, dict, list]: Session ID, session statistics, and message history
        """
        new_session = False
        
        if not session_id:
            session_id = str(uuid.uuid4())
            new_session = True
            logger.info(f"🆕 Created new session: {session_id}")
        elif not self.session_exists(session_id):
            session_id = str(uuid.uuid4())
            new_session = True
            logger.info(f"⚠️ Session file not found, creating new session: {session_id}")
        
        # Load existing session history if available
        messages, session_stats = self._load_session_history(session_id)
        
        if session_id in self.active_connections:
            try:
                old_websocket = self.active_connections[session_id]
                await old_websocket.close(code=1000, reason="Session replaced by new connection")
            except Exception as e:
                logger.warning(f"Failed to close old websocket for session {session_id}: {e}")
        
        self.active_connections[session_id] = websocket
        logger.info(f"🔌 WebSocket connected. Session ID: {session_id}. Total connections: {len(self.active_connections)}")
        
        return session_id, session_stats, messages

    def save_message(self, session_id: str, message: dict):
        """Save a message to the session history"""
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            history_file = self._get_session_file(session_id)
            with open(history_file, 'a') as f:
                f.write(json.dumps(message) + '\n')
        except Exception as e:
            logger.error(f"❌ Error saving message for session {session_id}: {e}")

    async def send_message(self, session_id: str, message: str | dict):
        """Send a message to a specific session"""
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent session: {session_id}")
            return

        websocket = self.active_connections[session_id]
        try:
            if isinstance(message, dict):
                # Save non-system messages to history
                if message.get("type") not in ["welcome", "session_info"]:
                    self.save_message(session_id, message)
                await websocket.send_text(json.dumps(message))
            else:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"❌ Failed to send message to session {session_id}: {e}")
            self.disconnect(session_id)

    def disconnect(self, session_id: str):
        """Remove a WebSocket connection and clean up session resources"""
        if session_id in self.active_connections:
            # Clean up session-specific memory retriever if not in shared mode
            if not SHARED_MEMORY_ENABLED:
                remove_session_retriever(session_id)
                logger.info(f"🧹 Cleaned up memory retriever for session {session_id}")
            
            del self.active_connections[session_id]
            logger.info(f"🔌 WebSocket disconnected. Session ID: {session_id}")

    def associate_user(self, session_id: str, user_id: str):
        """Associate a user ID with a session ID"""
        self.session_to_user[session_id] = user_id
        logger.info(f"👤 Associated user {user_id} with session {session_id}")

# Global WebSocket manager
ws_manager = WebSocketManager()

async def send_welcome_message(session_id: str, session_stats: dict, is_existing_session: bool):
    """Send a welcome message with session statistics"""
    last_time = session_stats["last_message_time"]
    last_time_str = f" (last message: {last_time})" if last_time else ""
    
    if is_existing_session:
        welcome_text = f"""Welcome back! 🎉 
I've loaded your previous conversation with {session_stats['total_messages']} messages.
We can continue right where we left off{last_time_str}."""
    else:
        welcome_text = WELCOME_MESSAGE
    
    welcome_payload = {
        "status": "success",
        "type": "welcome",
        "message": welcome_text,
        "session_id": session_id,
        "session_info": {
            "user_messages": session_stats["user_messages"],
            "assistant_messages": session_stats["assistant_messages"],
            "total_messages": session_stats["total_messages"],
            "approx_tokens": session_stats["approx_tokens"],
            "last_message_time": last_time,
            "is_existing_session": is_existing_session
        }
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
    
    try:
        # Add to connection manager and get session info
        session_id, session_stats, messages = await ws_manager.connect(websocket, session_id)
        is_existing_session = bool(messages)  # True if we have existing messages
        
        # Send welcome message
        await send_welcome_message(session_id, session_stats, is_existing_session)
        
        # Initialize memory with existing messages if any
        app_state = get_app_state()
        if messages and app_state.memory:
            # Use batch loading for efficiency
            app_state.memory.add_messages_batch(session_id, messages)
        
        # Initialize session-specific memory retriever if not in shared mode
        if not SHARED_MEMORY_ENABLED:
            _, memory_retriever = await initialize_vector_store(session_id=session_id)
            if memory_retriever is None:
                logger.warning(f"⚠️ Failed to initialize memory retriever for session {session_id}")
            else:
                logger.info(f"✅ Initialized session-specific memory retriever for session {session_id}")
        
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
        ws_manager.disconnect(session_id)  # This now handles memory retriever cleanup
