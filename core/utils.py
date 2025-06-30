# --- Standard Library ---
from typing import List

# --- Application Config ---
from core.config import TOOL_DEFINITIONS

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def log_available_tools() -> List[str]:
    """Log available tool definitions without re-initializing"""
    try:
        if not TOOL_DEFINITIONS:
            logger.warning("⚠️  No tool definitions available")
            return []

        logger.info(f"📋 Available tools ({len(TOOL_DEFINITIONS)}):")
        
        tool_names = []
        for i, tool in enumerate(TOOL_DEFINITIONS, 1):
            if isinstance(tool, dict) and 'function' in tool:
                tool_info = tool['function']
                tool_name = tool_info.get('name', 'Unknown')
                tool_names.append(tool_name)
                # Compact one-liner with key info
                required_params = tool_info.get('parameters', {}).get('required', [])
                logger.info(f"  🔨 #{i}: {tool_name} | Required: {', '.join(required_params)}")
                
                # Optional: Show description on separate line for readability
                if 'description' in tool_info:
                    logger.info(f"     📝 {tool_info['description'][:80]}{'...' if len(tool_info['description']) > 80 else ''}")

        return tool_names

    except Exception as e:
        logger.error(f"❌ Error logging tools: {e}", exc_info=True)
        return []
