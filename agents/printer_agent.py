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
        env_state = await self.environment_client.get_environment_state()
        if env_state:
            self.belief_manager.update_beliefs(env_state)
        
        beliefs = self.belief_manager.get_beliefs()
        desires = self.desire_manager.get_desires()
        new_intentions = self.intention_planner.deliberate(beliefs, desires)
        
        for intention in new_intentions:
            action = intention.get("action")
            target = intention.get("target")

            if not any(
                i.get("action") == action and i.get("target") == target
                for i in self.intentions
            ):
                self.intentions.append(intention)
        
        self.intentions.sort(key=lambda x: x.get("priority", 999))
        
        for intention in list(self.intentions):
            success = await self.action_executor.execute(intention)
            if success:
                self.intentions.remove(intention)
        
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
        
        await self._send_state_update()
    
    async def _send_state_update(self):
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
        logger.debug(f"Starting PrinterAgent {self.agent_id} for printer {self.printer_id}")
        self.running = True
        self.state = AgentState.MONITORING
        
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self._choose_cycle_delay())
            except Exception as e:
                logger.warning(f"Error in agent cycle: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        logger.debug(f"Stopping PrinterAgent {self.agent_id}")
        self.running = False
    
    async def cleanup(self):
        if hasattr(self.environment_client, 'close'):
            await self.environment_client.close()
        if hasattr(self.device_controller, 'close'):
            await self.device_controller.close()
        if hasattr(self.visualization_client, 'close'):
            await self.visualization_client.close()

    def _choose_cycle_delay(self) -> float:
        beliefs = self.belief_manager.get_beliefs()
        if beliefs and beliefs.state == "ON":
            if hasattr(self.intention_planner, "is_consuming") and self.intention_planner.is_consuming():
                return 1.0
            return 3.0
        return 5.0

