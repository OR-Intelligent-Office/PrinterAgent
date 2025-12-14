"""
Fabryka agentów - tworzy agenta z wszystkimi zależnościami
Dependency Injection Container
"""

import logging
from typing import Optional

from agents.printer_agent import PrinterAgent
from clients.environment_client import SimulatorEnvironmentClient
from clients.device_controller import SimulatorDeviceController
from clients.visualization_client import HttpVisualizationClient, NullVisualizationClient
from core.belief_manager import BeliefManager
from core.desire_manager import DesireManager
from core.intention_planner import RuleBasedIntentionPlanner
from core.action_executor import ActionExecutor
from communication.message_bus import SimpleMessageBus

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Fabryka do tworzenia agentów z wszystkimi zależnościami
    Zgodnie z DIP: centralizuje tworzenie zależności
    """
    
    @staticmethod
    def create_agent(
        printer_id: str,
        simulator_url: str = "http://localhost:8080",
        visualization_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        toner_threshold_low: int = 20,
        paper_threshold_low: int = 15,
        motion_timeout: int = 300
    ) -> PrinterAgent:
        """
        Tworzy agenta z wszystkimi zależnościami
        
        Args:
            printer_id: ID drukarki do zarządzania
            simulator_url: URL symulatora
            visualization_url: URL wizualizatora (opcjonalne)
            agent_id: ID agenta (opcjonalne)
            toner_threshold_low: Próg niskiego poziomu tonera
            paper_threshold_low: Próg niskiego poziomu papieru
            motion_timeout: Czas bezczynności przed wyłączeniem (sekundy)
        """
        # Tworzenie komponentów
        env_client = SimulatorEnvironmentClient(simulator_url)
        device_controller = SimulatorDeviceController(simulator_url)
        belief_manager = BeliefManager(printer_id)
        desire_manager = DesireManager()
        intention_planner = RuleBasedIntentionPlanner(
            toner_threshold_low=toner_threshold_low,
            paper_threshold_low=paper_threshold_low,
            motion_timeout=motion_timeout
        )
        
        # Klient wizualizacji - używa symulatora do wysyłania alertów (symulator przekazuje do wizualizatora)
        # Jeśli visualization_url nie jest podany, używamy symulatora jako pośrednika
        if visualization_url:
            viz_client = HttpVisualizationClient(visualization_url)
        else:
            # Używamy symulatora jako pośrednika dla alertów
            viz_client = HttpVisualizationClient(simulator_url)
        
        action_executor = ActionExecutor(device_controller, viz_client)
        
        # Komunikacja między agentami
        agent_id_final = agent_id or f"agent_{printer_id}"
        message_bus = SimpleMessageBus(agent_id_final)
        
        # Tworzenie agenta z wszystkimi zależnościami
        agent = PrinterAgent(
            printer_id=printer_id,
            environment_client=env_client,
            device_controller=device_controller,
            belief_manager=belief_manager,
            desire_manager=desire_manager,
            intention_planner=intention_planner,
            action_executor=action_executor,
            message_sender=message_bus,
            message_receiver=message_bus,
            visualization_client=viz_client,
            agent_id=agent_id_final
        )
        
        logger.info(f"Agent {agent_id_final} created successfully")
        return agent

