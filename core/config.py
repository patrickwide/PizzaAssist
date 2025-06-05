# Import all constants
from core.constants import *

# Import the tool loader
from core.tools import load_tools

# Load tools dynamically
TOOL_DEFINITIONS, AVAILABLE_FUNCTIONS = load_tools()