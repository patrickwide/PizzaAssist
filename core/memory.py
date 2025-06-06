# --- Standard Library ---
import os
import json
from typing import List, Dict, Any, Optional

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
    """Class to maintain conversation history and context for the agent"""
    def __init__(self, max_history: int = 10, history_file: Optional[str] = None):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
        self.function_call_attempts: Dict[str, int] = {}
        self.history_file = history_file

        if history_file:
            self.load_history_from_file(history_file)

    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a message to the conversation history."""
        # Ensure message is serializable before adding
        serializable_message = {k: make_serializable(v) for k, v in message.items()}
        self.conversation_history.append(serializable_message)
        if len(self.conversation_history) > self.max_history:
            # A simple trim keeping the last max_history items
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Save to file if configured
        if self.history_file:
            self.save_history_to_file(self.history_file)

    def get_recent_messages(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        if count is None:
            return self.conversation_history
        return self.conversation_history[-count:]

    def record_function_attempt(self, function_name: str, args: Dict[str, Any]) -> int:
        key = f"{function_name}:{json.dumps(args, sort_keys=True)}"
        self.function_call_attempts[key] = self.function_call_attempts.get(key, 0) + 1
        return self.function_call_attempts[key]

    def save_history_to_file(self, file_path: str) -> None:
        """Save conversation history to a JSONL file (one message per line)."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for msg in self.conversation_history:
                    serializable_msg = make_serializable(msg)
                    f.write(json.dumps(serializable_msg) + '\n')
            logger.debug(f"Successfully saved conversation history to {file_path}")
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")

    def load_history_from_file(self, file_path: str) -> None:
        """Load conversation history from a JSONL file."""
        try:
            if not os.path.exists(file_path):
                logger.info(f"No existing history file found at {file_path}")
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                self.conversation_history = [json.loads(line) for line in f]
            logger.debug(f"Successfully loaded conversation history from {file_path}")
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")