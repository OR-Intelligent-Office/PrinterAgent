import logging
from typing import Optional

from agents.printer_agent import PrinterAgent
from clients.environment_client import SimulatorEnvironmentClient
from clients.device_controller import SimulatorDeviceController
from clients.visualization_client import HttpVisualizationClient
from core.belief_manager import BeliefManager
from core.desire_manager import DesireManager
from core.intention_planner import RuleBasedIntentionPlanner
from core.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class AgentFactory:
    @staticmethod
    def create_agent(
        printer_id: str,
        simulator_url: str = "http://localhost:8080",
        visualization_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        toner_threshold_low: int = 20,
        paper_threshold_low: int = 15,
    ) -> PrinterAgent:
        env_client = SimulatorEnvironmentClient(simulator_url)
        device_controller = SimulatorDeviceController(simulator_url)
        belief_manager = BeliefManager(printer_id)
        desire_manager = DesireManager()
        intention_planner = RuleBasedIntentionPlanner(
            toner_threshold_low=toner_threshold_low,
            paper_threshold_low=paper_threshold_low,
            print_duration_min=1,
            print_duration_max=10,
            consumption_interval_seconds=1,
            idle_shutdown_seconds=20,
            room_inactivity_shutdown_seconds=10,
            min_on_seconds=10,
            min_off_seconds=10,
        )
        
        if visualization_url:
            viz_client = HttpVisualizationClient(visualization_url)
        else:
            viz_client = HttpVisualizationClient(simulator_url)
        
        action_executor = ActionExecutor(device_controller, viz_client)
        
        agent_id_final = agent_id or f"agent_{printer_id}"
        agent = PrinterAgent(
            printer_id=printer_id,
            environment_client=env_client,
            device_controller=device_controller,
            belief_manager=belief_manager,
            desire_manager=desire_manager,
            intention_planner=intention_planner,
            action_executor=action_executor,
            visualization_client=viz_client,
            agent_id=agent_id_final
        )
        
        logger.debug(f"Agent {agent_id_final} created successfully")
        return agent

