# Main printer agent class
# SOLID: dependency composition, open for extensions

import asyncio
import logging
from typing import Optional
from enum import Enum

from interfaces.environment_interfaces import IEnvironmentClient
from interfaces.device_interfaces import IDeviceController
from interfaces.bdi_interfaces import IBeliefManager, IDesireManager, IIntentionPlanner
from interfaces.action_interfaces import IActionExecutor
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)


class AgentState(Enum):
    # Agent state
    IDLE = "idle"
    MONITORING = "monitoring"
    PRINTING = "printing"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class PrinterAgent:
    # Printer agent with BDI logic (Beliefs, Desires, Intentions)
    # SOLID:
    # - SRP: Agent coordinates components, doesn't implement details
    # - OCP: Open for extensions (new planners, controllers)
    # - LSP: All components are interchangeable via interfaces
    # - ISP: Uses specific interfaces
    # - DIP: Depends on abstractions, not concrete implementations
    
    def __init__(
        self,
        printer_id: str,
        environment_client: IEnvironmentClient,
        device_controller: IDeviceController,
        belief_manager: IBeliefManager,
        desire_manager: IDesireManager,
        intention_planner: IIntentionPlanner,
        action_executor: IActionExecutor,
        visualization_client: IVisualizationClient,
        agent_id: Optional[str] = None
    ):
        self.printer_id = printer_id
        self.agent_id = agent_id or f"agent_{printer_id}"
        
        self.environment_client = environment_client
        self.device_controller = device_controller
        self.belief_manager = belief_manager
        self.desire_manager = desire_manager
        self.intention_planner = intention_planner
        self.action_executor = action_executor
        self.visualization_client = visualization_client
        
        # Agent state
        self.state = AgentState.IDLE
        self.running = False
        self.intentions: list = []
    
    async def run_cycle(self):
        # One agent cycle (perception-deliberation-action)
        # Perception: get environment state
        env_state = await self.environment_client.get_environment_state()
        if env_state:
            self.belief_manager.update_beliefs(env_state)
        
        # Deliberation: create intentions
        beliefs = self.belief_manager.get_beliefs()
        desires = self.desire_manager.get_desires()
        new_intentions = self.intention_planner.deliberate(beliefs, desires)
        
        # Add new intentions (avoid duplicates, but alerts can be repeated)
        for intention in new_intentions:
            action = intention.get("action")
            target = intention.get("target")
            
            # For alerts, always update intention (to have current level)
            if action in ["alert_low_toner", "alert_low_paper", "handle_failure"]:
                # Find existing intention and update it
                existing = next(
                    (i for i in self.intentions 
                     if i.get("action") == action and i.get("target") == target),
                    None
                )
                if existing:
                    # Update existing intention with new data
                    existing.update(intention)
                else:
                    # Add new intention
                    self.intentions.append(intention)
            else:
                # For other actions, avoid duplicates
                if not any(
                    i.get("action") == action and 
                    i.get("target") == target
                    for i in self.intentions
                ):
                    self.intentions.append(intention)
        
        # Execute intentions (in priority order)
        self.intentions.sort(key=lambda x: x.get("priority", 999))
        
        for intention in list(self.intentions):
            success = await self.action_executor.execute(intention)
            # Remove intention only if it's not an alert (alerts are sent cyclically)
            action = intention.get("action")
            if success and action not in ["alert_low_toner", "alert_low_paper", "handle_failure"]:
                self.intentions.remove(intention)
        
        # Update agent state
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
        
        # Send state update to visualizer
        await self._send_state_update()
    
    async def _send_state_update(self):
        # Send state update to visualizer
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
        # Start agent
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
        # Stop agent
        logger.info(f"Stopping PrinterAgent {self.agent_id}")
        self.running = False
    
    async def cleanup(self):
        # Cleanup resources
        if hasattr(self.environment_client, 'close'):
            await self.environment_client.close()
        if hasattr(self.device_controller, 'close'):
            await self.device_controller.close()
        if hasattr(self.visualization_client, 'close'):
            await self.visualization_client.close()

    def _choose_cycle_delay(self) -> float:
        # Choose delay for next cycle
        # - 1s during printing (1s refresh requirement)
        # - 3s when printer ON but not printing
        # - 5s in IDLE mode (slower polling, less load)
        beliefs = self.belief_manager.get_beliefs()
        if beliefs and beliefs.state == "ON":
            if hasattr(self.intention_planner, "is_consuming") and self.intention_planner.is_consuming():
                return 1.0
            return 3.0
        return 5.0

