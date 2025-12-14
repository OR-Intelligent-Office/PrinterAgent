"""
Interfejsy związane z BDI (Beliefs, Desires, Intentions)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models.environment_models import EnvironmentState, PrinterState


class IBeliefManager(ABC):
    """Interfejs zarządzania przekonaniami (SRP, DIP)"""
    
    @abstractmethod
    def update_beliefs(self, env_state: EnvironmentState) -> None:
        """Aktualizuje przekonania na podstawie stanu środowiska"""
        pass
    
    @abstractmethod
    def get_beliefs(self) -> Optional[PrinterState]:
        """Zwraca aktualne przekonania"""
        pass


class IDesireManager(ABC):
    """Interfejs zarządzania pragnieniami (SRP, DIP)"""
    
    @abstractmethod
    def get_desires(self) -> List[Dict[str, Any]]:
        """Zwraca listę pragnień agenta"""
        pass
    
    @abstractmethod
    def update_desires(self, new_desires: List[Dict[str, Any]]) -> None:
        """Aktualizuje pragnienia"""
        pass


class IIntentionPlanner(ABC):
    """Interfejs planowania intencji (SRP, DIP)"""
    
    @abstractmethod
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Proces deliberacji - analizuje przekonania i pragnienia,
        tworzy intencje (plan działania)
        """
        pass

