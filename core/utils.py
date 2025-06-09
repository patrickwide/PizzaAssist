# --- Standard Library ---
from typing import List

# --- Application Config ---
from config import TOOL_DEFINITIONS

# --- Logging ---
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def log_available_tools() -> List[str]:
    """Initialize and log available tool definitions"""
    try:
        logger.info("🔧 Initializing tools...")
        
        if not TOOL_DEFINITIONS:
            logger.warning("⚠️  No tool definitions available")
            return

        logger.info(f"📋 Available tools ({len(TOOL_DEFINITIONS)}):")
        
        for i, tool in enumerate(TOOL_DEFINITIONS, 1):
            # Compact one-liner with key info
            required_params = tool.get('parameters', {}).get('required', [])
            logger.info(f"  🔨 #{i}: {tool['name']} | Required: {', '.join(required_params)}")
            
            # Optional: Show description on separate line for readability
            if 'description' in tool:
                logger.info(f"     📝 {tool['description'][:80]}{'...' if len(tool['description']) > 80 else ''}")

        logger.info("🎉 Tools initialization completed")

    except Exception as e:
        logger.error(f"❌ Tools initialization failed: {e}", exc_info=True)
