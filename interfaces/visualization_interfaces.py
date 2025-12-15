# Visualization interfaces

from abc import ABC, abstractmethod
from typing import Dict, Any


class IVisualizationClient(ABC):
    # Visualization client interface (SRP, DIP)
    
    @abstractmethod
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        # Send alert to visualizer
        pass
    
    @abstractmethod
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        # Send state update to visualizer
        pass

