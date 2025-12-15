# Environment-related interfaces

from abc import ABC, abstractmethod
from typing import Optional
from models.environment_models import EnvironmentState, PrinterState


class IEnvironmentClient(ABC):
    # Environment client interface (SRP, DIP)
    
    @abstractmethod
    async def get_environment_state(self) -> Optional[EnvironmentState]:
        # Get current environment state
        pass
    
    @abstractmethod
    async def get_printer_state(self, printer_id: str) -> Optional[PrinterState]:
        # Get specific printer state
        pass

