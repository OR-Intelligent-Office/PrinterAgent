# Agent factory - creates agent with all dependencies
# Dependency Injection Container

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

logger = logging.getLogger(__name__)


class AgentFactory:
    # Factory for creating agents with all dependencies
    # DIP: centralizes dependency creation
    
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
        # Create agent with all dependencies
        # Args:
        #   printer_id: Printer ID to manage
        #   simulator_url: Simulator URL
        #   visualization_url: Visualizer URL (optional)
        #   agent_id: Agent ID (optional)
        #   toner_threshold_low: Low toner threshold
        #   paper_threshold_low: Low paper threshold
        #   motion_timeout: Idle timeout before shutdown (seconds)
        # Create components
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
            idle_shutdown_seconds=10
        )
        
        # Visualization client uses simulator for alerts
        if visualization_url:
            viz_client = HttpVisualizationClient(visualization_url)
        else:
            viz_client = HttpVisualizationClient(simulator_url)
        
        action_executor = ActionExecutor(device_controller, viz_client)
        
        # Create agent with all dependencies
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
        
        logger.info(f"Agent {agent_id_final} created successfully")
        return agent

