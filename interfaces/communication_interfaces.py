"""
Interfejsy związane z komunikacją między agentami
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IMessageSender(ABC):
    """Interfejs wysyłania wiadomości (SRP, DIP)"""
    
    @abstractmethod
    def send_message(
        self, 
        receiver: str, 
        performative: str, 
        content: Dict[str, Any]
    ) -> None:
        """Wysyła wiadomość do innego agenta"""
        pass


class IMessageReceiver(ABC):
    """Interfejs odbierania wiadomości (SRP, DIP)"""
    
    @abstractmethod
    def receive_messages(self) -> List[Dict[str, Any]]:
        """Odbiera wiadomości od innych agentów"""
        pass
    
    @abstractmethod
    def process_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Przetwarza otrzymane wiadomości"""
        pass

