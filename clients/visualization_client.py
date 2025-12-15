# Visualization client
# Single Responsibility: only communication with visualizer

import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)


class HttpVisualizationClient(IVisualizationClient):
    # Visualization client via HTTP
    # SRP: only responsible for communication with visualizer
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> Optional[aiohttp.ClientSession]:
        """Lazy initialization session"""
        if not self.base_url:
            return None
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        # Send alert to simulator (which forwards to visualizer)
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
            
            # Send to simulator (8080) or directly to visualizer
            if ":8080" in self.base_url or "localhost:8080" in self.base_url:
                async with session.post(
                    f"{self.base_url}/api/environment/alerts",
                    json=alert
                ) as response:
                    if response.status == 200:
                        logger.info(f"⚠️ Alert sent to simulator: {alert_type} - {data.get('printer_id', 'unknown')}")
                    else:
                        logger.warning(f"Failed to send alert to simulator: {response.status}")
            else:
                # Send directly to visualizer
                async with session.post(
                    f"{self.base_url}/api/alerts",
                    json=alert
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Alert sent to visualizer: {alert_type}")
                    else:
                        logger.warning(f"Failed to send alert: {response.status}")
        except Exception as e:
            logger.warning(f"Could not send alert: {e}")
    
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        # Send state update to visualizer
        if not self.base_url:
            logger.debug(f"State update (no visualization): {state}")
            return
        
        # Visualizer reads from simulator, skip sending update
        if ":8080" in self.base_url or "localhost:8080" in self.base_url:
            logger.debug(
                f"State update (visualizer reads from simulator): printer_id={state.get('printer_id')}"
            )
            return
        
        # Try sending directly to visualizer
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


class NullVisualizationClient(IVisualizationClient):
    # Null object pattern - visualization client that does nothing
    # Useful when visualization is not available
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        # Do nothing
        pass
    
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        # Do nothing
        pass

