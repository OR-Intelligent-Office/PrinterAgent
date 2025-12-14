"""
Zarządzanie pragnieniami agenta (Desires)
Single Responsibility: tylko zarządzanie pragnieniami
"""

import logging
from typing import List, Dict, Any
from interfaces.bdi_interfaces import IDesireManager

logger = logging.getLogger(__name__)


class DesireManager(IDesireManager):
    """
    Zarządza pragnieniami agenta (Desires w BDI)
    Zgodnie z SRP: tylko odpowiedzialność za pragnienia
    Zgodnie z OCP: łatwo rozszerzyć o nowe pragnienia
    """
    
    def __init__(self):
        self._desires: List[Dict[str, Any]] = []
        self._initialize_default_desires()
    
    def _initialize_default_desires(self):
        """Inicjalizacja podstawowych pragnień agenta"""
        self._desires = [
            {
                "type": "maintain_printer",
                "priority": 1,
                "description": "Utrzymanie drukarki w dobrym stanie technicznym"
            },
            {
                "type": "save_energy",
                "priority": 2,
                "description": "Oszczędzanie energii poprzez wyłączanie gdy nieużywana"
            },
            {
                "type": "ensure_availability",
                "priority": 3,
                "description": "Zapewnienie dostępności drukarki dla użytkowników"
            },
        ]
    
    def get_desires(self) -> List[Dict[str, Any]]:
        """Zwraca listę pragnień agenta"""
        return self._desires.copy()
    
    def update_desires(self, new_desires: List[Dict[str, Any]]) -> None:
        """Aktualizuje pragnienia"""
        self._desires = new_desires
        logger.info(f"Desires updated: {len(self._desires)} desires")

