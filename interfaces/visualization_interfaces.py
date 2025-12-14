"""
Interfejsy związane z wizualizacją
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IVisualizationClient(ABC):
    """Interfejs klienta wizualizacji (SRP, DIP)"""
    
    @abstractmethod
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """Wysyła alert do wizualizatora"""
        pass
    
    @abstractmethod
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        """Wysyła aktualizację stanu do wizualizatora"""
        pass

