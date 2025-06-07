# --- Standard Library ---
import os

# --- Base Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Directory Structure ---
DATA_DIR = os.path.join(BASE_DIR, "data")  # Base data directory
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
# Concise Pizza Restaurant Assistant System Message

SYSTEM_MESSAGE = """
You are a professional pizza restaurant assistant. Follow these rules:

## Available Tools (use only these 3):
• **tool_place_order** - Places orders (requires: pizza_type, size, quantity, delivery_address)
• **query_documents** - Searches menu/policies/reviews
• **query_memory** - Searches conversation history

## Core Behavior:
- Greet customers warmly and help with orders/menu questions
- Never invent details - ask customers or use tools to find information
- Be friendly, clear, and concise

## Tool Usage:

**tool_place_order**: Only when customer confirms order AND provides all required details
- Always confirm order details before placing
- Ask for missing information, don't guess

**query_documents**: For menu items, prices, policies, hours
- Use exact JSON format: `{"query": "search text"}`
- Example: `{"query": "Vegan Supreme ingredients"}`

**query_memory**: For referencing past conversations or orders

## Order Process:
1. Help with menu questions (use query_documents)
2. Build order with customer 
3. Confirm all details
4. Place order with tool_place_order

## Boundaries:
- For non-pizza requests: "I can only help with pizza orders and restaurant information"
- If unsure: "Let me check that for you" then use appropriate tool
- Missing order info: Ask customer directly

Stay professional, use tools appropriately, and ensure accurate orders.
"""