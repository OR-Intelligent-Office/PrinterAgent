# Environment client implementation
# Single Responsibility: only communication with simulator API

import logging
from typing import Optional
import aiohttp
from interfaces.environment_interfaces import IEnvironmentClient
from models.environment_models import EnvironmentState, PrinterState

logger = logging.getLogger(__name__)


class SimulatorEnvironmentClient(IEnvironmentClient):
    # Environment client - communication with OrSimulator API
    # SRP: only responsible for API communication
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_environment_state(self) -> Optional[EnvironmentState]:
        # Get current environment state from simulator
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/environment/state") as response:
                if response.status == 200:
                    data = await response.json()
                    return EnvironmentState(
                        simulation_time=data.get("simulationTime", ""),
                        rooms=data.get("rooms", []),
                        external_temperature=data.get("externalTemperature", 0.0),
                        power_outage=data.get("powerOutage", False),
                        time_speed_multiplier=data.get("timeSpeedMultiplier", 1.0),
                        daylight_intensity=data.get("daylightIntensity", 1.0)
                    )
                else:
                    logger.debug(f"Failed to fetch environment state: {response.status}")
                    return None
        except Exception as e:
            logger.debug(f"Error fetching environment state: {e}")
            return None
    
    async def get_printer_state(self, printer_id: str) -> Optional[PrinterState]:
        # Get specific printer state
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/environment/devices/printer/{printer_id}"
            ) as response:
                if response.status == 200:
                    printer_data = await response.json()
                    
                    # Get room information
                    env_state = await self.get_environment_state()
                    if not env_state:
                        return None
                    
                    room_data = None
                    for room in env_state.rooms:
                        if room.get("printer") and room["printer"].get("id") == printer_id:
                            room_data = room
                            break
                    
                    if not room_data:
                        return None
                    
                    return PrinterState(
                        printer_id=printer_id,
                        room_id=room_data.get("id", ""),
                        room_name=room_data.get("name", ""),
                        state=printer_data.get("state", "OFF"),
                        toner_level=printer_data.get("tonerLevel", 0),
                        paper_level=printer_data.get("paperLevel", 0),
                        people_count=room_data.get("peopleCount", 0),
                        last_motion_time=room_data.get("motionSensor", {}).get("lastMotionTime"),
                        power_outage=env_state.power_outage
                    )
                else:
                    logger.debug(f"Failed to fetch printer state: {response.status}")
                    return None
        except Exception as e:
            logger.debug(f"Error fetching printer state: {e}")
            return None

