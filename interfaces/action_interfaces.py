"""
Interfejsy związane z wykonywaniem akcji
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IActionExecutor(ABC):
    """Interfejs wykonawcy akcji (SRP, DIP)"""
    
    @abstractmethod
    async def execute(self, intention: Dict[str, Any]) -> bool:
        """Wykonuje intencję (akcję)"""
        pass

