"""
Modele wiadomości między agentami
"""

from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime


@dataclass
class Message:
    """Model wiadomości między agentami"""
    sender: str
    receiver: str
    performative: str
    content: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje wiadomość do słownika"""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "performative": self.performative,
            "content": self.content,
            "timestamp": self.timestamp
        }

