# --- Standard Library ---
import os

# --- Model Configuration ---
OLLAMA_MODEL = "llama3.2"  # Specify your desired Ollama model
EMBEDDING_MODEL = "mxbai-embed-large"  # Specify your desired embedding model
VISION_MODEL = "llama3.2-vision"  # Dedicated vision model

# --- Base Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Directory Structure ---
DATA_DIR = os.path.join(BASE_DIR, "data")  # Base data directory
DB_DIR = os.path.join(DATA_DIR, "db")  # Database files
HISTORY_DIR = os.path.join(DATA_DIR, "history")  # Directory for session-based conversation history
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")  # Documents and orders

# --- Path Configuration ---
DB_LOCATION = DB_DIR  # Directory for Chroma DB
CSV_FILE_PATH = os.path.join(DOCUMENTS_DIR, "realistic_restaurant_reviews.csv")  # Reviews file
ORDER_FILE_PATH = os.path.join(DOCUMENTS_DIR, "orders.txt")  # File to save orders
STORE_METADATA_FILE = os.path.join(DB_DIR, "store_metadata.json")  # Vector store metadata file in db directory
SYSTEM_MESSAGE_FILE = os.path.join(DATA_DIR, "system_message.md")  # System message file
WELCOME_MESSAGE_FILE = os.path.join(DATA_DIR, "welcome_message.md")  # Welcome message file

# --- Memory Configuration ---
ENABLE_MEMORY = True  # Set to False to disable memory completely
SHARED_MEMORY_ENABLED = False  # Set to True to enable cross-session memory sharing
MAX_MEMORY_ENTRIES = 15  # Maximum number of messages to keep per session

# --- Application Configuration ---
COLLECTION_NAME = "restaurant_reviews"  # Collection name for Chroma DB

# --- Load Messages from Files ---
def load_message_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        return "Error: Message file not found."
    except Exception as e:
        return f"Error loading message: {str(e)}"

# Load messages
SYSTEM_MESSAGE = load_message_from_file(SYSTEM_MESSAGE_FILE)
WELCOME_MESSAGE = load_message_from_file(WELCOME_MESSAGE_FILE)