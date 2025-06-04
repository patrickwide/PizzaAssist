import json
import os
from typing import List, Dict, Any, Optional

# --- Agent Memory ---
def make_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    elif hasattr(obj, 'to_dict'):
        return make_serializable(obj.to_dict())
    elif hasattr(obj, '__dict__') and not isinstance(obj, str):
        return make_serializable(vars(obj))
    else:
        return obj

class AgentMemory:
    """Class to maintain conversation history and context for the agent"""
    def __init__(self, max_history: int = 10, history_file: Optional[str] = None):
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.function_call_attempts: Dict[str, int] = {} # Track attempts per function/args
        self.history_file = history_file
        if self.history_file:
            self.load_history_from_file(self.history_file)

    def add_message(self, message: Dict[str, Any]) -> None:
        self.conversation_history.append(message)
        if len(self.conversation_history) > self.max_history:
            # A simple trim keeping the last max_history items
            self.conversation_history = self.conversation_history[-self.max_history:]
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
        except Exception as e:
            print(f"Error saving conversation history: {e}")

    def load_history_from_file(self, file_path: str) -> None:
        """Load conversation history from a JSONL file."""
        try:
            if not os.path.exists(file_path):
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                self.conversation_history = [json.loads(line) for line in f]
        except Exception as e:
            print(f"Error loading conversation history: {e}")