"""
Interfejsy związane z kontrolą urządzeń
"""

from abc import ABC, abstractmethod


class IDeviceController(ABC):
    """Interfejs kontrolera urządzeń (SRP, DIP)"""
    
    @abstractmethod
    async def turn_on(self, device_id: str) -> bool:
        """Włącza urządzenie"""
        pass
    
    @abstractmethod
    async def turn_off(self, device_id: str) -> bool:
        """Wyłącza urządzenie"""
        pass
    
    @abstractmethod
    async def set_toner_level(self, device_id: str, level: int) -> bool:
        """Ustawia poziom tonera"""
        pass
    
    @abstractmethod
    async def set_paper_level(self, device_id: str, level: int) -> bool:
        """Ustawia poziom papieru"""
        pass

