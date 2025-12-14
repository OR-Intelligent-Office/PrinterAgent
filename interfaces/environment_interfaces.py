"""
Interfejsy związane ze środowiskiem
"""

from abc import ABC, abstractmethod
from typing import Optional
from models.environment_models import EnvironmentState, PrinterState


class IEnvironmentClient(ABC):
    """Interfejs klienta środowiska (SRP, DIP)"""
    
    @abstractmethod
    async def get_environment_state(self) -> Optional[EnvironmentState]:
        """Pobiera aktualny stan środowiska"""
        pass
    
    @abstractmethod
    async def get_printer_state(self, printer_id: str) -> Optional[PrinterState]:
        """Pobiera stan konkretnej drukarki"""
        pass

