"""
Implementacja kontrolera urządzeń
Single Responsibility: tylko kontrola urządzeń przez API
"""

import logging
from typing import Optional
import aiohttp
from interfaces.device_interfaces import IDeviceController

logger = logging.getLogger(__name__)


class SimulatorDeviceController(IDeviceController):
    """
    Kontroler urządzeń - wykonuje akcje na urządzeniach przez API
    Zgodnie z SRP: tylko odpowiedzialność za kontrolę urządzeń
    """
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Zamyka sesję HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _control_printer(self, device_id: str, action: str, **kwargs) -> bool:
        """Wykonuje akcję kontroli drukarki przez API"""
        try:
            session = await self._get_session()
            payload = {"action": action, **kwargs}
            
            async with session.post(
                f"{self.base_url}/api/environment/devices/printer/{device_id}/control",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        logger.info(f"Printer {action} successful for {device_id}")
                        return True
                    else:
                        logger.error(f"Printer {action} failed: {result.get('error')}")
                        return False
                else:
                    logger.error(f"HTTP error {response.status} for {action}")
                    return False
        except Exception as e:
            logger.error(f"Error controlling printer: {e}")
            return False
    
    async def turn_on(self, device_id: str) -> bool:
        """Włącza urządzenie"""
        return await self._control_printer(device_id, "turn_on")
    
    async def turn_off(self, device_id: str) -> bool:
        """Wyłącza urządzenie"""
        return await self._control_printer(device_id, "turn_off")
    
    async def set_toner_level(self, device_id: str, level: int) -> bool:
        """Ustawia poziom tonera"""
        return await self._control_printer(device_id, "set_toner", level=level)
    
    async def set_paper_level(self, device_id: str, level: int) -> bool:
        """Ustawia poziom papieru"""
        return await self._control_printer(device_id, "set_paper", level=level)

