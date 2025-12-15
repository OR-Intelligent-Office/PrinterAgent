# Device control interfaces

from abc import ABC, abstractmethod


class IDeviceController(ABC):
    # Device controller interface (SRP, DIP)
    
    @abstractmethod
    async def turn_on(self, device_id: str) -> bool:
        # Turn on device
        pass
    
    @abstractmethod
    async def turn_off(self, device_id: str) -> bool:
        # Turn off device
        pass
    
    @abstractmethod
    async def set_toner_level(self, device_id: str, level: int) -> bool:
        # Set toner level
        pass
    
    @abstractmethod
    async def set_paper_level(self, device_id: str, level: int) -> bool:
        # Set paper level
        pass

