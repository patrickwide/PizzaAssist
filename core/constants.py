import os

# Get the base directory path (core directory's parent)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Directory Structure ---
DATA_DIR = os.path.join(BASE_DIR, "core", "data")  # Base data directory
DB_DIR = os.path.join(DATA_DIR, "db")  # Database files
HISTORY_DIR = os.path.join(DATA_DIR, "history")  # History and conversation files
REVIEWS_DIR = os.path.join(DATA_DIR, "reviews")  # Reviews and orders

# --- Path Configuration ---
DB_LOCATION = DB_DIR  # Directory for Chroma DB
CONVERSATION_HISTORY_FILE_PATH = os.path.join(HISTORY_DIR, "conversation_history.jsonl")  # File to save conversation history
CSV_FILE_PATH = os.path.join(REVIEWS_DIR, "realistic_restaurant_reviews.csv")  # Reviews file
ORDER_FILE_PATH = os.path.join(REVIEWS_DIR, "orders.txt")  # File to save orders
STORE_METADATA_FILE = os.path.join(DB_DIR, "store_metadata.json")  # Vector store metadata file in db directory

# --- Model Configuration ---
OLLAMA_MODEL = "llama3.2"  # Specify your desired Ollama model
EMBEDDING_MODEL = "mxbai-embed-large"  # Specify your desired embedding model
VISION_MODEL = "llama3.2-vision"  # Dedicated vision model

# --- Application Configuration ---
COLLECTION_NAME = "restaurant_reviews"  # Collection name for Chroma DB
ENABLE_MEMORY = True  # Set to False to disable memory