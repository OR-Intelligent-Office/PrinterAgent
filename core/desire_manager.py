import logging
from typing import List, Dict, Any
from interfaces.bdi_interfaces import IDesireManager

logger = logging.getLogger(__name__)


class DesireManager(IDesireManager):
    def __init__(self):
        self._desires: List[Dict[str, Any]] = []
        self._initialize_default_desires()
    
    def _initialize_default_desires(self):
        self._desires = [
            {
                "type": "maintain_printer",
                "priority": 1,
                "description": "Maintain printer in good technical condition"
            },
            {
                "type": "save_energy",
                "priority": 2,
                "description": "Save energy by turning off when unused"
            },
            {
                "type": "ensure_availability",
                "priority": 3,
                "description": "Ensure printer availability for users"
            },
        ]
    
    def get_desires(self) -> List[Dict[str, Any]]:
        return self._desires.copy()
    
    def update_desires(self, new_desires: List[Dict[str, Any]]) -> None:
        self._desires = new_desires
        logger.debug(f"Desires updated: {len(self._desires)} desires")

