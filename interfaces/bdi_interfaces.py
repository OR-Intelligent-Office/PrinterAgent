# BDI-related interfaces (Beliefs, Desires, Intentions)

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models.environment_models import EnvironmentState, PrinterState


class IBeliefManager(ABC):
    # Belief management interface (SRP, DIP)
    
    @abstractmethod
    def update_beliefs(self, env_state: EnvironmentState) -> None:
        # Update beliefs based on environment state
        pass
    
    @abstractmethod
    def get_beliefs(self) -> Optional[PrinterState]:
        # Return current beliefs
        pass


class IDesireManager(ABC):
    # Desire management interface (SRP, DIP)
    
    @abstractmethod
    def get_desires(self) -> List[Dict[str, Any]]:
        # Return list of agent desires
        pass
    
    @abstractmethod
    def update_desires(self, new_desires: List[Dict[str, Any]]) -> None:
        # Update desires
        pass


class IIntentionPlanner(ABC):
    # Intention planning interface (SRP, DIP)
    
    @abstractmethod
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # Deliberation process - analyze beliefs and desires, create intentions (action plan)
        pass

