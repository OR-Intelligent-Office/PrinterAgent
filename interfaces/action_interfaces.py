# Action execution interfaces

from abc import ABC, abstractmethod
from typing import Dict, Any


class IActionExecutor(ABC):
    # Action executor interface (SRP, DIP)
    
    @abstractmethod
    async def execute(self, intention: Dict[str, Any]) -> bool:
        # Execute intention (action)
        pass

