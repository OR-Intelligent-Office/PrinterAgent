"""
Modele danych środowiska
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class EnvironmentState:
    """Model stanu środowiska"""
    simulation_time: str
    rooms: List[Dict[str, Any]]
    external_temperature: float
    power_outage: bool
    time_speed_multiplier: float = 1.0
    daylight_intensity: float = 1.0


@dataclass
class PrinterState:
    """Model stanu drukarki"""
    printer_id: str
    room_id: str
    room_name: str
    state: str  # ON, OFF, BROKEN
    toner_level: int
    paper_level: int
    people_count: int = 0
    last_motion_time: Optional[str] = None
    power_outage: bool = False

