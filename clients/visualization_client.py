"""
Klient wizualizacji
Single Responsibility: tylko komunikacja z wizualizatorem
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)


class HttpVisualizationClient(IVisualizationClient):
    """
    Klient wizualizacji przez HTTP
    Zgodnie z SRP: tylko odpowiedzialność za komunikację z wizualizatorem
    """
    
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
        """Zamyka sesję HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """Wysyła alert do symulatora (który przekazuje do wizualizatora)"""
        if not self.base_url:
            logger.debug(f"Alert (no visualization): {alert_type} - {data}")
            return
        
        try:
            session = await self._get_session()
            if not session:
                return
            
            # Wysyłamy do symulatora, który przechowuje alerty i udostępnia je wizualizatorowi
            alert = {
                "type": alert_type,
                "data": data
            }
            
            # Jeśli base_url wskazuje na symulator (8080), użyj endpointu alertów
            # W przeciwnym razie próbuj bezpośrednio do wizualizatora
            if ":8080" in self.base_url or "localhost:8080" in self.base_url:
                # Wysyłamy do symulatora
                async with session.post(
                    f"{self.base_url}/api/environment/alerts",
                    json=alert
                ) as response:
                    if response.status == 200:
                        logger.info(f"⚠️ Alert sent to simulator: {alert_type} - {data.get('printer_id', 'unknown')}")
                    else:
                        logger.warning(f"Failed to send alert to simulator: {response.status}")
            else:
                # Wysyłamy bezpośrednio do wizualizatora (stary sposób)
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
        """Wysyła aktualizację stanu do wizualizatora"""
        if not self.base_url:
            logger.debug(f"State update (no visualization): {state}")
            return
        
        try:
            session = await self._get_session()
            if not session:
                return
            
            # Wizualizator pobiera dane z symulatora, więc nie wysyłamy aktualizacji bezpośrednio
            # Zamiast tego logujemy stan dla debugowania
            logger.debug(
                f"Agent state update: printer_id={state.get('printer_id')}, "
                f"printer_state={state.get('printer_state')}, "
                f"agent_state={state.get('state')}"
            )
            
            # Próba wysłania do wizualizatora (jeśli ma endpoint)
            async with session.post(
                f"{self.base_url}/api/agent-state",
                json=state,
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    logger.debug(f"State update sent to visualizer")
                elif response.status == 404:
                    # Wizualizator nie ma tego endpointu - to normalne, wizualizator pobiera dane z symulatora
                    logger.debug(f"Visualizer doesn't have /api/agent-state endpoint (normal - visualizer reads from simulator)")
                else:
                    logger.debug(f"Visualizer response: {response.status}")
        except asyncio.TimeoutError:
            # Timeout jest normalny, jeśli wizualizator nie ma tego endpointu
            logger.debug(f"Timeout sending state update (normal if visualizer doesn't have endpoint)")
        except Exception as e:
            logger.debug(f"Could not send state update to visualizer: {e}")


class NullVisualizationClient(IVisualizationClient):
    """
    Null object pattern - klient wizualizacji, który nic nie robi
    Użyteczne gdy wizualizacja nie jest dostępna
    """
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """Nic nie robi"""
        pass
    
    async def send_state_update(self, state: Dict[str, Any]) -> None:
        """Nic nie robi"""
        pass

