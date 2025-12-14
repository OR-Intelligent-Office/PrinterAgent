"""
Zarządzanie przekonaniami agenta (Beliefs)
Single Responsibility: tylko zarządzanie przekonaniami
"""

import logging
from typing import Optional
from interfaces.bdi_interfaces import IBeliefManager
from models.environment_models import EnvironmentState, PrinterState

logger = logging.getLogger(__name__)


class BeliefManager(IBeliefManager):
    """
    Zarządza przekonaniami agenta (Beliefs w BDI)
    Zgodnie z SRP: tylko odpowiedzialność za przekonania
    """
    
    def __init__(self, printer_id: str):
        self.printer_id = printer_id
        self._beliefs: Optional[PrinterState] = None
    
    def update_beliefs(self, env_state: EnvironmentState) -> None:
        """Aktualizuje przekonania na podstawie stanu środowiska"""
        # Znajdź pokój z naszą drukarką
        printer_data = None
        room_data = None
        
        for room in env_state.rooms:
            if room.get("printer") and room["printer"].get("id") == self.printer_id:
                printer_data = room["printer"]
                room_data = room
                break
        
        if not printer_data or not room_data:
            logger.warning(f"Printer {self.printer_id} not found in environment")
            return
        
        # Aktualizuj przekonania
        self._beliefs = PrinterState(
            printer_id=self.printer_id,
            room_id=room_data.get("id", ""),
            room_name=room_data.get("name", ""),
            state=printer_data.get("state", "OFF"),
            toner_level=printer_data.get("tonerLevel", 0),
            paper_level=printer_data.get("paperLevel", 0),
            people_count=room_data.get("peopleCount", 0),
            last_motion_time=room_data.get("motionSensor", {}).get("lastMotionTime"),
            power_outage=env_state.power_outage
        )
        
        logger.debug(f"Beliefs updated: {self._beliefs}")
    
    def get_beliefs(self) -> Optional[PrinterState]:
        """Zwraca aktualne przekonania"""
        return self._beliefs

