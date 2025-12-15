"""
Główna klasa agenta drukarki
Zgodnie z SOLID: kompozycja zależności, otwarta na rozszerzenia
"""

import asyncio
import logging
from typing import Optional
from enum import Enum

from interfaces.environment_interfaces import IEnvironmentClient
from interfaces.device_interfaces import IDeviceController
from interfaces.bdi_interfaces import IBeliefManager, IDesireManager, IIntentionPlanner
from interfaces.action_interfaces import IActionExecutor
from interfaces.communication_interfaces import IMessageSender, IMessageReceiver
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Stan agenta"""
    IDLE = "idle"
    MONITORING = "monitoring"
    PRINTING = "printing"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class PrinterAgent:
    """
    Agent drukarki z logiką BDI (Beliefs, Desires, Intentions)
    
    Zgodnie z SOLID:
    - SRP: Agent koordynuje komponenty, nie implementuje szczegółów
    - OCP: Otwarty na rozszerzenia (nowe planisty, kontrolery)
    - LSP: Wszystkie komponenty są zamienne przez interfejsy
    - ISP: Używa specyficznych interfejsów
    - DIP: Zależy od abstrakcji, nie konkretnych implementacji
    """
    
    def __init__(
        self,
        printer_id: str,
        environment_client: IEnvironmentClient,
        device_controller: IDeviceController,
        belief_manager: IBeliefManager,
        desire_manager: IDesireManager,
        intention_planner: IIntentionPlanner,
        action_executor: IActionExecutor,
        message_sender: IMessageSender,
        message_receiver: IMessageReceiver,
        visualization_client: IVisualizationClient,
        agent_id: Optional[str] = None
    ):
        self.printer_id = printer_id
        self.agent_id = agent_id or f"agent_{printer_id}"
        
        # Dependency Injection - wszystkie zależności przez interfejsy
        self.environment_client = environment_client
        self.device_controller = device_controller
        self.belief_manager = belief_manager
        self.desire_manager = desire_manager
        self.intention_planner = intention_planner
        self.action_executor = action_executor
        self.message_sender = message_sender
        self.message_receiver = message_receiver
        self.visualization_client = visualization_client
        
        # Stan agenta
        self.state = AgentState.IDLE
        self.running = False
        self.intentions: list = []
    
    async def run_cycle(self):
        """Jeden cykl działania agenta (percepcja-deliberacja-akcja)"""
        # 1. Percepcja - pobierz stan środowiska
        env_state = await self.environment_client.get_environment_state()
        if env_state:
            self.belief_manager.update_beliefs(env_state)
        
        # 2. Przetwórz wiadomości od innych agentów
        messages = self.message_receiver.receive_messages()
        if messages:
            self.message_receiver.process_messages(messages)
            self._handle_messages(messages)
        
        # 3. Deliberacja - stwórz intencje
        beliefs = self.belief_manager.get_beliefs()
        desires = self.desire_manager.get_desires()
        new_intentions = self.intention_planner.deliberate(beliefs, desires)
        
        # 4. Dodaj nowe intencje (unikaj duplikatów, ale alerty mogą być ponawiane)
        for intention in new_intentions:
            action = intention.get("action")
            target = intention.get("target")
            
            # Dla alertów, zawsze aktualizuj intencję (żeby mieć aktualny poziom)
            if action in ["alert_low_toner", "alert_low_paper", "handle_failure"]:
                # Znajdź istniejącą intencję i zaktualizuj ją
                existing = next(
                    (i for i in self.intentions 
                     if i.get("action") == action and i.get("target") == target),
                    None
                )
                if existing:
                    # Aktualizuj istniejącą intencję z nowymi danymi
                    existing.update(intention)
                else:
                    # Dodaj nową intencję
                    self.intentions.append(intention)
            else:
                # Dla innych akcji, unikaj duplikatów
                if not any(
                    i.get("action") == action and 
                    i.get("target") == target
                    for i in self.intentions
                ):
                    self.intentions.append(intention)
        
        # 5. Wykonaj intencje (w kolejności priorytetu)
        self.intentions.sort(key=lambda x: x.get("priority", 999))
        
        for intention in list(self.intentions):
            success = await self.action_executor.execute(intention)
            # Usuń intencję tylko jeśli to nie jest alert (alerty są wysyłane cyklicznie)
            action = intention.get("action")
            if success and action not in ["alert_low_toner", "alert_low_paper", "handle_failure"]:
                self.intentions.remove(intention)
        
        # 6. Aktualizuj stan agenta
        if beliefs:
            if beliefs.state == "BROKEN":
                self.state = AgentState.ERROR
            elif beliefs.state == "ON":
                if hasattr(self.intention_planner, "is_consuming") and self.intention_planner.is_consuming():
                    self.state = AgentState.PRINTING
                else:
                    self.state = AgentState.MONITORING
            else:
                self.state = AgentState.IDLE
        
        # 7. Wyślij aktualizację stanu do wizualizatora
        await self._send_state_update()
    
    def _handle_messages(self, messages: list):
        """Obsługuje wiadomości od innych agentów"""
        for msg in messages:
            if msg.get("performative") == "request":
                if msg.get("content", {}).get("action") == "status":
                    beliefs = self.belief_manager.get_beliefs()
                    self.message_sender.send_message(
                        msg.get("sender"),
                        "inform",
                        {
                            "printer_id": self.printer_id,
                            "state": beliefs.state if beliefs else "unknown",
                            "toner": beliefs.toner_level if beliefs else 0,
                            "paper": beliefs.paper_level if beliefs else 0
                        }
                    )
            
            elif msg.get("performative") == "query":
                query_type = msg.get("content", {}).get("query_type")
                if query_type == "availability":
                    beliefs = self.belief_manager.get_beliefs()
                    available = (
                        beliefs and
                        beliefs.state == "ON" and
                        not beliefs.power_outage
                    )
                    self.message_sender.send_message(
                        msg.get("sender"),
                        "inform",
                        {"available": available, "printer_id": self.printer_id}
                    )
    
    async def _send_state_update(self):
        """Wysyła aktualizację stanu do wizualizatora"""
        beliefs = self.belief_manager.get_beliefs()
        if beliefs:
            await self.visualization_client.send_state_update({
                "agent_id": self.agent_id,
                "printer_id": self.printer_id,
                "state": self.state.value,
                "printer_state": beliefs.state,
                "toner_level": beliefs.toner_level,
                "paper_level": beliefs.paper_level,
                "room": beliefs.room_name
            })
    
    async def start(self):
        """Uruchamia agenta"""
        logger.info(f"Starting PrinterAgent {self.agent_id} for printer {self.printer_id}")
        self.running = True
        self.state = AgentState.MONITORING
        
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self._choose_cycle_delay())
            except Exception as e:
                logger.error(f"Error in agent cycle: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Zatrzymuje agenta"""
        logger.info(f"Stopping PrinterAgent {self.agent_id}")
        self.running = False
    
    async def cleanup(self):
        """Czyszczenie zasobów"""
        if hasattr(self.environment_client, 'close'):
            await self.environment_client.close()
        if hasattr(self.device_controller, 'close'):
            await self.device_controller.close()
        if hasattr(self.visualization_client, 'close'):
            await self.visualization_client.close()

    def _choose_cycle_delay(self) -> float:
        """
        Wybiera opóźnienie kolejnego cyklu.
        - 1s podczas drukowania (wymóg odświeżania co sekundę)
        - 2s gdy drukarka włączona, ale nie drukuje
        - 3s w trybie czuwania/IDLE
        """
        beliefs = self.belief_manager.get_beliefs()
        if beliefs and beliefs.state == "ON":
            if hasattr(self.intention_planner, "is_consuming") and self.intention_planner.is_consuming():
                return 1.0
            return 2.0
        return 3.0

