from typing import Protocol, Dict, Any
from typing_extensions import runtime_checkable

@runtime_checkable
class PizzaAssistTool(Protocol):
    """Standard interface that all pizza assistant tools must implement."""
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Return the tool's metadata and schema."""
        ...
        
    def validate(self) -> bool:
        """Validate that the tool meets all requirements."""
        ...