import asyncio
import logging
import sys

import aiohttp

from agents.printer_agent import AgentState
from clients.device_controller import SimulatorDeviceController
from clients.environment_client import SimulatorEnvironmentClient
from clients.visualization_client import HttpVisualizationClient
from core.action_executor import ActionExecutor
from core.belief_manager import BeliefManager
from core.desire_manager import DesireManager
from core.intention_planner import RuleBasedIntentionPlanner
from factory.agent_factory import AgentFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_SIMULATOR_URL = "http://localhost:8080"


async def get_all_printers(simulator_url: str, retries: int = 3) -> set[str]:
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{simulator_url}/api/environment/state",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        state = await response.json()
                        printers: set[str] = set()
                        for room in state.get("rooms", []):
                            printer = room.get("printer")
                            if printer and printer.get("id"):
                                printers.add(printer["id"])
                        return printers

                    if attempt < retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return set()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
    return set()


class MultiPrinterAgent:
    def __init__(
        self,
        simulator_url: str = DEFAULT_SIMULATOR_URL,
        visualization_url: str | None = None,
        check_interval: int = 30,
        agent_id: str = "agent_manager",
    ):
        self.simulator_url = simulator_url
        self.visualization_url = visualization_url
        self.check_interval = check_interval
        self.agent_id = agent_id

        self.environment_client = SimulatorEnvironmentClient(simulator_url)
        self.device_controller = SimulatorDeviceController(simulator_url)
        self.visualization_client = HttpVisualizationClient(visualization_url or simulator_url)

        self.action_executor = ActionExecutor(self.device_controller, self.visualization_client)
        self.desire_manager = DesireManager()

        self._running = False

        self._belief_managers: dict[str, BeliefManager] = {}
        self._planners: dict[str, RuleBasedIntentionPlanner] = {}
        self._intentions: dict[str, list[dict]] = {}
        self._states: dict[str, AgentState] = {}

    def _ensure_printer(self, printer_id: str) -> None:
        if printer_id in self._belief_managers:
            return
        self._belief_managers[printer_id] = BeliefManager(printer_id)
        self._planners[printer_id] = RuleBasedIntentionPlanner(
            toner_threshold_low=20,
            paper_threshold_low=15,
            print_duration_min=1,
            print_duration_max=10,
            consumption_interval_seconds=1.0,
            idle_shutdown_seconds=20,
            room_inactivity_shutdown_seconds=10,
            min_on_seconds=10,
            min_off_seconds=10,
        )
        self._intentions[printer_id] = []
        self._states[printer_id] = AgentState.IDLE

    def _drop_printer(self, printer_id: str) -> None:
        self._belief_managers.pop(printer_id, None)
        self._planners.pop(printer_id, None)
        self._intentions.pop(printer_id, None)
        self._states.pop(printer_id, None)

    async def _refresh_printers(self) -> None:
        printers = await get_all_printers(self.simulator_url)

        for pid in printers:
            self._ensure_printer(pid)

        for pid in list(self._belief_managers.keys()):
            if pid not in printers:
                self._drop_printer(pid)

    async def _run_cycle(self) -> None:
        env_state = await self.environment_client.get_environment_state()
        if not env_state:
            return

        desires = self.desire_manager.get_desires()

        for printer_id, belief_manager in self._belief_managers.items():
            belief_manager.update_beliefs(env_state)
            beliefs = belief_manager.get_beliefs()
            if not beliefs:
                continue

            planner = self._planners[printer_id]
            new_intentions = planner.deliberate(beliefs, desires)

            intentions = self._intentions[printer_id]

            for intention in new_intentions:
                action = intention.get("action")
                target = intention.get("target")
                if not any(i.get("action") == action and i.get("target") == target for i in intentions):
                    intentions.append(intention)

            intentions.sort(key=lambda x: x.get("priority", 999))

            for intention in list(intentions):
                success = await self.action_executor.execute(intention)
                if success:
                    intentions.remove(intention)

            if beliefs.state == "BROKEN":
                state = AgentState.ERROR
            elif beliefs.state == "ON":
                state = AgentState.PRINTING if planner.is_consuming() else AgentState.MONITORING
            else:
                state = AgentState.IDLE

            self._states[printer_id] = state

            await self.visualization_client.send_state_update(
                {
                    "agent_id": self.agent_id,
                    "printer_id": printer_id,
                    "state": state.value,
                    "printer_state": beliefs.state,
                    "toner_level": beliefs.toner_level,
                    "paper_level": beliefs.paper_level,
                    "room": beliefs.room_name,
                }
            )

    def _choose_cycle_delay(self) -> float:
        any_printing = any(
            self._planners[pid].is_consuming()
            for pid in self._planners
            if self._states.get(pid) in (AgentState.MONITORING, AgentState.PRINTING)
        )
        if any_printing:
            return 1.0
        any_on = any(state in (AgentState.MONITORING, AgentState.PRINTING) for state in self._states.values())
        return 3.0 if any_on else 5.0

    async def start(self) -> None:
        logger.info("PrinterAgent manager started")
        logger.debug(f"Simulator URL: {self.simulator_url}")
        if self.visualization_url:
            logger.debug(f"Visualization URL: {self.visualization_url}")
        logger.debug(f"Check interval: {self.check_interval} seconds")

        self._running = True

        max_wait_time = 30
        waited = 0
        while waited < max_wait_time:
            printers = await get_all_printers(self.simulator_url, retries=1)
            if printers:
                break
            await asyncio.sleep(2)
            waited += 2

        if waited >= max_wait_time:
            logger.warning("Simulator did not respond. Start simulator: cd OrSimulator && ./gradlew run")
            return

        await self._refresh_printers()

        last_refresh = asyncio.get_running_loop().time()

        try:
            while self._running:
                now = asyncio.get_running_loop().time()
                if now - last_refresh >= float(self.check_interval):
                    await self._refresh_printers()
                    last_refresh = now

                await self._run_cycle()
                await asyncio.sleep(self._choose_cycle_delay())
        except KeyboardInterrupt:
            logger.info("Stopping agent manager...")
        finally:
            await self.cleanup()

    def stop(self) -> None:
        self._running = False

    async def cleanup(self) -> None:
        await self.environment_client.close()
        await self.device_controller.close()
        await self.visualization_client.close()


async def main():
    try:
        # Backward-compatible single-printer mode:
        # python main.py printer_209 [simulator_url] [visualization_url]
        if len(sys.argv) > 1 and sys.argv[1].startswith("printer_"):
            printer_id = sys.argv[1]
            simulator_url = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SIMULATOR_URL
            visualization_url = sys.argv[3] if len(sys.argv) > 3 else None
            agent = AgentFactory.create_agent(
                printer_id=printer_id,
                simulator_url=simulator_url,
                visualization_url=visualization_url,
            )
            await agent.start()
            return

        # Manager mode (one agent managing many printers):
        # python main.py [simulator_url] [visualization_url] [check_interval]
        simulator_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SIMULATOR_URL
        visualization_url = sys.argv[2] if len(sys.argv) > 2 else None
        check_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        manager = MultiPrinterAgent(
            simulator_url=simulator_url,
            visualization_url=visualization_url,
            check_interval=check_interval,
        )
        await manager.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())
