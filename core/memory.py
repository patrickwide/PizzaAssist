# --- Standard Library ---
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def make_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    else:
        return str(obj)

class ChatHistoryManager:
    """Class to maintain conversation history and context for multiple chat sessions."""
    def __init__(self, max_history: int = 10, history_dir: Optional[str] = None):
        """
        Initialize the ChatHistoryManager.
        
        Args:
            max_history (int): Maximum number of messages to keep per session (excluding system message)
            history_dir (Optional[str]): Directory to store session history files
        """
        self.max_history = max_history
        self.history_dir = history_dir
        if history_dir:
            os.makedirs(history_dir, exist_ok=True)
        
        # Per-session storage
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        self._system_messages: Dict[str, Dict[str, Any]] = {}
        self._function_call_attempts: Dict[str, Dict[str, int]] = {}
        self._sequence_counters: Dict[str, int] = {}  # Track sequence per session
        self._is_loading: bool = False  # Flag to track bulk loading state

    def _get_history_path(self, session_id: str) -> str:
        """Get the full path for a session's history file."""
        if not self.history_dir:
            raise ValueError("No history directory configured")
        return os.path.join(self.history_dir, f"{session_id}.jsonl")

    def _ensure_session(self, session_id: str) -> None:
        """Ensure session data structures exist."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        if session_id not in self._function_call_attempts:
            self._function_call_attempts[session_id] = {}
        if session_id not in self._sequence_counters:
            self._sequence_counters[session_id] = 0

    def set_system_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Set the persistent system message for a specific session."""
        self._ensure_session(session_id)
        self._system_messages[session_id] = make_serializable(message)
        self._rebuild_history(session_id)
        if self.history_dir and not self._is_loading:
            self.save_history(session_id)

    def add_message(self, session_id: str, message: Dict[str, Any], bulk_load: bool = False) -> None:
        """
        Add a message to the conversation history for a specific session.
        
        Args:
            session_id: The session identifier
            message: The message to add
            bulk_load: If True, skip immediate save to disk (for batch loading)
        """
        self._ensure_session(session_id)
        serializable_message = make_serializable(message)

        # Get non-system messages
        non_system_msgs = (
            self._conversations[session_id][1:] 
            if session_id in self._system_messages 
            else self._conversations[session_id]
        )
        non_system_msgs.append(serializable_message)

        # Trim to max_history
        if len(non_system_msgs) > self.max_history:
            non_system_msgs = non_system_msgs[-self.max_history:]

        # Rebuild full history
        self._conversations[session_id] = (
            [self._system_messages[session_id]] + non_system_msgs 
            if session_id in self._system_messages 
            else non_system_msgs
        )

        # Only save to disk if not bulk loading and not in loading state
        if self.history_dir and not bulk_load and not self._is_loading:
            self.save_history(session_id)

    def add_messages_batch(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """
        Add multiple messages at once efficiently.
        
        Args:
            session_id: The session identifier
            messages: List of messages to add
        """
        if not messages:
            return
            
        for message in messages:
            self.add_message(session_id, message, bulk_load=True)
            
        # Save all messages at once
        if self.history_dir:
            self.save_history(session_id)
            logger.info(f"Batch loaded {len(messages)} messages for session {session_id}")

    def get_recent_messages(self, session_id: str, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent messages for a specific session."""
        self._ensure_session(session_id)
        if count is None:
            return self._conversations[session_id]
        
        has_system = session_id in self._system_messages
        messages = self._conversations[session_id]
        
        if has_system:
            return messages[:1] + messages[-count:]
        return messages[-count:]

    def record_function_attempt(self, session_id: str, function_name: str, args: Dict[str, Any]) -> int:
        """Record a function call attempt for a specific session."""
        self._ensure_session(session_id)
        key = f"{function_name}:{json.dumps(args, sort_keys=True)}"
        self._function_call_attempts[session_id][key] = (
            self._function_call_attempts[session_id].get(key, 0) + 1
        )
        return self._function_call_attempts[session_id][key]

    def save_history(self, session_id: str) -> None:
        """Save conversation history for a specific session to its JSONL file."""
        if not self.history_dir:
            logger.warning(f"No history directory configured, skipping save for session {session_id}")
            return

        try:
            history_path = self._get_history_path(session_id)
            with open(history_path, 'w', encoding='utf-8') as f:
                for msg in self._conversations[session_id]:
                    serializable_msg = make_serializable(msg)
                    f.write(json.dumps(serializable_msg) + '\n')
            
            # Only log during normal operation, not during bulk loading
            if not self._is_loading:
                logger.debug(f"Successfully saved conversation history for session {session_id}")
        except Exception as e:
            logger.error(f"Error saving conversation history for session {session_id}: {e}")

    def load_history(self, session_id: str) -> None:
        """Load conversation history for a specific session from its JSONL file."""
        if not self.history_dir:
            logger.warning(f"No history directory configured, skipping load for session {session_id}")
            return

        try:
            history_path = self._get_history_path(session_id)
            if not os.path.exists(history_path):
                logger.info(f"No existing history file found for session {session_id}")
                return

            # Set loading flag to prevent save operations during bulk load
            self._is_loading = True
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    loaded_messages = [json.loads(line) for line in f]

                if loaded_messages and loaded_messages[0].get("role") == "system":
                    self._system_messages[session_id] = loaded_messages[0]
                    self._conversations[session_id] = loaded_messages
                else:
                    self._conversations[session_id] = loaded_messages
                
                logger.info(f"Successfully loaded {len(loaded_messages)} messages for session {session_id}")
            finally:
                self._is_loading = False
                
        except Exception as e:
            logger.error(f"Error loading conversation history for session {session_id}: {e}")
            self._is_loading = False

    def _rebuild_history(self, session_id: str) -> None:
        """Rebuild history for a specific session with system message at the top."""
        self._ensure_session(session_id)
        non_system_msgs = (
            self._conversations[session_id][1:] 
            if session_id in self._system_messages 
            else self._conversations[session_id]
        )
        if len(non_system_msgs) > self.max_history:
            non_system_msgs = non_system_msgs[-self.max_history:]
        self._conversations[session_id] = (
            [self._system_messages[session_id]] + non_system_msgs 
            if session_id in self._system_messages 
            else non_system_msgs
        )

    def next_sequence(self, session_id: str) -> int:
        """Get next sequence number for a session."""
        self._ensure_session(session_id)
        self._sequence_counters[session_id] += 1
        return self._sequence_counters[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear all history and data for a specific session."""
        self._conversations.pop(session_id, None)
        self._system_messages.pop(session_id, None)
        self._function_call_attempts.pop(session_id, None)
        self._sequence_counters.pop(session_id, None)
        
        # Remove history file if it exists
        if self.history_dir:
            try:
                history_path = self._get_history_path(session_id)
                if os.path.exists(history_path):
                    os.remove(history_path)
            except Exception as e:
                logger.error(f"Error removing history file for session {session_id}: {e}")

    def get_all_sessions(self) -> List[str]:
        """Get a list of all active session IDs."""
        return list(self._conversations.keys())
