"""
Planowanie intencji agenta (Intentions)
Single Responsibility: tylko planowanie akcji
Open/Closed Principle: łatwo rozszerzyć o nowe reguły
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from interfaces.bdi_interfaces import IIntentionPlanner
from models.environment_models import PrinterState

logger = logging.getLogger(__name__)


class RuleBasedIntentionPlanner(IIntentionPlanner):
    """
    Planista intencji oparty na regułach
    Zgodnie z SRP: tylko odpowiedzialność za planowanie
    Zgodnie z OCP: łatwo dodać nowe reguły bez modyfikacji istniejących
    """
    
    def __init__(
        self,
        toner_threshold_low: int = 20,
        paper_threshold_low: int = 15,
        motion_timeout: int = 300
    ):
        self.toner_threshold_low = toner_threshold_low
        self.paper_threshold_low = paper_threshold_low
        self.motion_timeout = motion_timeout
    
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Proces deliberacji - analizuje przekonania i pragnienia,
        tworzy intencje (plan działania)
        """
        if not beliefs:
            return []
        
        intentions = []
        
        # Reguła 1: Sprawdź poziom tonera
        if beliefs.toner_level < self.toner_threshold_low:
            intentions.append({
                "action": "alert_low_toner",
                "target": beliefs.printer_id,
                "reason": f"Toner level is low: {beliefs.toner_level}%",
                "priority": 1,
                "toner_level": beliefs.toner_level
            })
        
        # Reguła 2: Sprawdź poziom papieru
        if beliefs.paper_level < self.paper_threshold_low:
            intentions.append({
                "action": "alert_low_paper",
                "target": beliefs.printer_id,
                "reason": f"Paper level is low: {beliefs.paper_level}%",
                "priority": 1,
                "paper_level": beliefs.paper_level
            })
        
        # Reguła 3: Awaria drukarki
        if beliefs.state == "BROKEN":
            intentions.append({
                "action": "handle_failure",
                "target": beliefs.printer_id,
                "reason": "Printer is broken",
                "priority": 1,
                "room": beliefs.room_name
            })
        
        # Reguła 4: Brak zasilania
        if beliefs.power_outage:
            intentions.append({
                "action": "handle_power_outage",
                "target": beliefs.printer_id,
                "reason": "Power outage detected",
                "priority": 1
            })
        
        # Reguła 5: Zarządzanie energią - wyłącz jeśli brak ruchu
        if beliefs.state == "ON" and beliefs.people_count == 0:
            if beliefs.last_motion_time:
                try:
                    last_motion = datetime.fromisoformat(
                        beliefs.last_motion_time.replace('Z', '+00:00')
                    )
                    time_since_motion = (datetime.now() - last_motion.replace(tzinfo=None)).total_seconds()
                    if time_since_motion > self.motion_timeout:
                        intentions.append({
                            "action": "turn_off",
                            "target": beliefs.printer_id,
                            "reason": f"No motion for {time_since_motion:.0f} seconds",
                            "priority": 2
                        })
                except Exception as e:
                    logger.warning(f"Error parsing motion time: {e}")
        
        # Reguła 6: Włącz jeśli jest ruch i drukarka wyłączona
        if (beliefs.state == "OFF" and 
            beliefs.people_count > 0 and
            not beliefs.power_outage):
            # 50% szans na włączenie drukarki przy wykryciu ruchu
            if random.random() < 0.5:
                intentions.append({
                    "action": "turn_on",
                    "target": beliefs.printer_id,
                    "reason": f"Motion detected: {beliefs.people_count} people in room (50% chance)",
                    "priority": 3
                })
        
        # Sortuj według priorytetu
        intentions.sort(key=lambda x: x.get("priority", 999))
        
        return intentions

