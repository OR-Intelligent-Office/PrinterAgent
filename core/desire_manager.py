# Desire management (BDI Desires)
# Single Responsibility: only desire management

import logging
from typing import List, Dict, Any
from interfaces.bdi_interfaces import IDesireManager

logger = logging.getLogger(__name__)


class DesireManager(IDesireManager):
    # Manages agent desires (BDI Desires)
    # SRP: only responsible for desires
    # OCP: easy to extend with new desires
    
    def __init__(self):
        self._desires: List[Dict[str, Any]] = []
        self._initialize_default_desires()
    
    def _initialize_default_desires(self):
        # Initialize default agent desires
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
        # Return list of agent desires
        return self._desires.copy()
    
    def update_desires(self, new_desires: List[Dict[str, Any]]) -> None:
        # Update desires
        self._desires = new_desires
        logger.info(f"Desires updated: {len(self._desires)} desires")

