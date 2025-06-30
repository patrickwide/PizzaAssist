# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# --- Load Messages from Files ---
def load_message_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        error_msg = f"Error: Message file not found: {file_path}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error loading message from {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg
