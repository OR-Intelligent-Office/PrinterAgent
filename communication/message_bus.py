"""
Komunikacja między agentami
Single Responsibility: tylko komunikacja między agentami
"""

import logging
from typing import List, Dict, Any
from interfaces.communication_interfaces import IMessageSender, IMessageReceiver
from models.message_models import Message

logger = logging.getLogger(__name__)


class SimpleMessageBus(IMessageSender, IMessageReceiver):
    """
    Prosty system komunikacji między agentami
    Zgodnie z SRP: tylko odpowiedzialność za komunikację
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._incoming_messages: List[Message] = []
        self._outgoing_messages: List[Message] = []
    
    def send_message(
        self, 
        receiver: str, 
        performative: str, 
        content: Dict[str, Any]
    ) -> None:
        """Wysyła wiadomość do innego agenta"""
        message = Message(
            sender=self.agent_id,
            receiver=receiver,
            performative=performative,
            content=content
        )
        self._outgoing_messages.append(message)
        logger.info(f"Message sent to {receiver}: {performative}")
    
    def receive_messages(self) -> List[Dict[str, Any]]:
        """Odbiera wiadomości od innych agentów"""
        messages = [msg.to_dict() for msg in self._incoming_messages]
        self._incoming_messages.clear()
        return messages
    
    def process_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Przetwarza otrzymane wiadomości"""
        for msg_dict in messages:
            if msg_dict.get("receiver") == self.agent_id or msg_dict.get("receiver") == "broadcast":
                message = Message(
                    sender=msg_dict.get("sender", ""),
                    receiver=msg_dict.get("receiver", ""),
                    performative=msg_dict.get("performative", ""),
                    content=msg_dict.get("content", {})
                )
                self._incoming_messages.append(message)
                logger.info(f"Received message from {message.sender}: {message.performative}")


class AgentCommunicationHub:
    """
    Hub komunikacyjny dla wielu agentów
    Zgodnie z SRP: tylko zarządzanie komunikacją między agentami
    """
    
    def __init__(self):
        self._agents: Dict[str, SimpleMessageBus] = {}
    
    def register_agent(self, agent_id: str, message_bus: SimpleMessageBus):
        """Rejestruje agenta w hubie"""
        self._agents[agent_id] = message_bus
        logger.info(f"Agent {agent_id} registered in communication hub")
    
    def unregister_agent(self, agent_id: str):
        """Wyrejestrowuje agenta"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent {agent_id} unregistered from communication hub")
    
    def route_messages(self):
        """Rozsyła wiadomości między agentami"""
        for agent_id, message_bus in self._agents.items():
            # Pobierz wiadomości wychodzące
            outgoing = message_bus._outgoing_messages.copy()
            message_bus._outgoing_messages.clear()
            
            # Rozsyłaj wiadomości
            for message in outgoing:
                if message.receiver == "broadcast":
                    # Broadcast do wszystkich
                    for target_id, target_bus in self._agents.items():
                        if target_id != agent_id:
                            target_bus._incoming_messages.append(message)
                elif message.receiver in self._agents:
                    # Wiadomość do konkretnego agenta
                    self._agents[message.receiver]._incoming_messages.append(message)
                else:
                    logger.warning(f"Agent {message.receiver} not found")
