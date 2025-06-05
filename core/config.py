# --- Standard Library ---
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Import constants and tools
from core.constants import *
from core.tools import load_tools

try:
    # Load tools dynamically
    TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS = load_tools()
except Exception as e:
    logger.warning(f"Error loading tools: {e}")
    TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS = [], {}