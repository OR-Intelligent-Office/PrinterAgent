import asyncio
import logging
from typing import Dict, Any, Optional

import aiohttp
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)

_SIMULATOR_PORT_MARKER = ":8080"


class HttpVisualizationClient(IVisualizationClient):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> Optional[aiohttp.ClientSession]:
        if not self.base_url:
            return None
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        if not self.base_url:
            logger.debug(f"Alert (no visualization): {alert_type} - {data}")
            return
        
        try:
            session = await self._get_session()
            if not session:
                return
            
            alert = {
                "type": alert_type,
                "data": data
            }
            
            # If target is the simulator, post to its alerts endpoint.
            if _SIMULATOR_PORT_MARKER in self.base_url:
                async with session.post(
                    f"{self.base_url}/api/environment/alerts",
                    json=alert
                ) as response:
                    if response.status != 200:
                        logger.debug(f"Failed to send alert to simulator: {response.status}")
            else:
                async with session.post(
                    f"{self.base_url}/api/alerts",
                    json=alert
                ) as response:
                    if response.status != 200:
                        logger.debug(f"Failed to send alert: {response.status}")
        except Exception as e:
            logger.debug(f"Could not send alert: {e}")
    
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        if not self.base_url:
            logger.debug(f"State update (no visualization): {state}")
            return
        
        # If UI reads from simulator by polling, there's nothing to send.
        if _SIMULATOR_PORT_MARKER in self.base_url:
            logger.debug(
                f"State update (visualizer reads from simulator): printer_id={state.get('printer_id')}"
            )
            return
        
        try:
            session = await self._get_session()
            if not session:
                return
            
            async with session.post(
                f"{self.base_url}/api/agent-state",
                json=state,
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    logger.debug(f"State update sent to visualizer")
                elif response.status == 404:
                    logger.debug(f"Visualizer doesn't have /api/agent-state endpoint")
                else:
                    logger.debug(f"Visualizer response: {response.status}")
        except asyncio.TimeoutError:
            logger.debug(f"Timeout sending state update")
        except Exception as e:
            logger.debug(f"Could not send state update: {e}")
