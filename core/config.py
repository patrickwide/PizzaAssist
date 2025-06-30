# --- Standard Library ---
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Import constants
from constants import *

# Initialize empty tool containers - will be populated during app startup
TOOL_DEFINITIONS = []
AVAILABLE_FUNCTIONS = {}