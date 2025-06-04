# Import all constants
from constants import *

# Import the tool loader
from tools import load_tools

# Load tools dynamically
TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS = load_tools()