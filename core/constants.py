# --- Path Configuration ---
DB_LOCATION = "./chrome_langchain_db"  # Directory for Chroma DB
CONVERSATION_HISTORY_FILE_PATH = "conversation_history.jsonl"  # File to save conversation history
CSV_FILE_PATH = "realistic_restaurant_reviews.csv"  # Reviews file
ORDER_FILE_PATH = "orders.txt"  # File to save orders

# --- Model Configuration ---
OLLAMA_MODEL = "llama3.2"  # Specify your desired Ollama model
EMBEDDING_MODEL = "mxbai-embed-large"  # Specify your desired embedding model
VISION_MODEL = "llama3.2-vision"  # Dedicated vision model

# --- Application Configuration ---
COLLECTION_NAME = "restaurant_reviews"  # Collection name for Chroma DB
ENEBLE_MEMORY = True  # Set to False to disable memory