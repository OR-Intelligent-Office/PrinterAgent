"""
Planowanie intencji agenta (Intentions)
Single Responsibility: tylko planowanie akcji
Open/Closed Principle: łatwo rozszerzyć o nowe reguły
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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
        motion_timeout: int = 20,  # 20 seconds of inactivity = 20 minutes simulation
        active_consumption_time_min: int = 1,  # Min active consumption time (seconds)
        active_consumption_time_max: int = 15  # Max active consumption time (seconds)
    ):
        self.toner_threshold_low = toner_threshold_low
        self.paper_threshold_low = paper_threshold_low
        self.motion_timeout = motion_timeout
        self.active_consumption_time_min = active_consumption_time_min
        self.active_consumption_time_max = active_consumption_time_max
        
        # Printer state tracking
        self._printer_turned_on_at: Optional[datetime] = None
        self._active_consumption_end_time: Optional[datetime] = None  # When active consumption ends
        self._last_motion_time: Optional[datetime] = None  # Last motion detection time
        self._previous_people_count: int = 0  # Previous people count (to detect exit)
        self._is_consuming_resources: bool = False  # Whether printer is currently consuming resources
        self._turn_off_cooldown_until: Optional[datetime] = None  # Cooldown after turning off (prevent immediate turn on)
        self._scheduled_turn_on_time: Optional[datetime] = None  # Scheduled random time to turn on
    
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deliberation process - analyzes beliefs and desires,
        creates intentions (action plan)
        """
        if not beliefs:
            return []
        
        intentions = []
        current_time = datetime.now()
        
        # Rule 1: Check toner level
        if beliefs.toner_level < self.toner_threshold_low:
            intentions.append({
                "action": "alert_low_toner",
                "target": beliefs.printer_id,
                "reason": f"Toner level is low: {beliefs.toner_level}%",
                "priority": 1,
                "toner_level": beliefs.toner_level
            })
        
        # Rule 2: Check paper level
        if beliefs.paper_level < self.paper_threshold_low:
            intentions.append({
                "action": "alert_low_paper",
                "target": beliefs.printer_id,
                "reason": f"Paper level is low: {beliefs.paper_level}%",
                "priority": 1,
                "paper_level": beliefs.paper_level
            })
        
        # Rule 3: Printer failure
        if beliefs.state == "BROKEN":
            intentions.append({
                "action": "handle_failure",
                "target": beliefs.printer_id,
                "reason": "Printer is broken",
                "priority": 1,
                "room": beliefs.room_name
            })
        
        # Rule 4: Power outage
        if beliefs.power_outage:
            intentions.append({
                "action": "handle_power_outage",
                "target": beliefs.printer_id,
                "reason": "Power outage detected",
                "priority": 1
            })
        
        # Track printer state and motion
        if beliefs.state == "ON":
            # Printer is on - track turn on time and active consumption period
            if self._printer_turned_on_at is None:
                # Just turned on - initialize tracking
                self._printer_turned_on_at = current_time
                # Random active consumption time: 1-15 seconds
                active_duration = random.uniform(
                    float(self.active_consumption_time_min),
                    float(self.active_consumption_time_max)
                )
                self._active_consumption_end_time = current_time + timedelta(seconds=active_duration)
                self._is_consuming_resources = True
                logger.info(
                    f"Printer {beliefs.printer_id} turned on. "
                    f"Active consumption for {active_duration:.1f}s (1-{self.active_consumption_time_max}s)"
                )
            
            # Update last motion time if motion detected
            if beliefs.last_motion_time:
                try:
                    last_motion = datetime.fromisoformat(
                        beliefs.last_motion_time.replace('Z', '+00:00')
                    )
                    self._last_motion_time = last_motion.replace(tzinfo=None)
                except Exception as e:
                    logger.warning(f"Error parsing motion time: {e}")
            
            # Check if active consumption period has ended
            if (self._active_consumption_end_time is not None and 
                current_time >= self._active_consumption_end_time):
                if self._is_consuming_resources:
                    self._is_consuming_resources = False
                    logger.info(
                        f"Printer {beliefs.printer_id} active consumption period ended. "
                        f"Printer remains on but stops consuming resources."
                    )
            
            # Consume resources during active period
            if self._is_consuming_resources and self._printer_turned_on_at is not None:
                # Consume paper: 1-4% per cycle (random)
                paper_consumption = random.uniform(1.0, 4.0)
                
                # Consume toner based on paper consumption:
                # - If paper consumption is in lower half (1.0-2.5): 1% toner
                # - If paper consumption is in upper half (2.5-4.0): 2% toner
                if paper_consumption <= 2.5:
                    toner_consumption = 1.0
                else:
                    toner_consumption = 2.0
                
                intentions.append({
                    "action": "consume_resources",
                    "target": beliefs.printer_id,
                    "reason": "Active consumption period",
                    "priority": 2,
                    "toner_consumption": toner_consumption,
                    "paper_consumption": paper_consumption,
                    "current_toner": beliefs.toner_level,
                    "current_paper": beliefs.paper_level
                })
        else:
            # Printer is off - reset all tracking
            if self._printer_turned_on_at is not None:
                self._printer_turned_on_at = None
                self._active_consumption_end_time = None
                self._is_consuming_resources = False
                self._last_motion_time = None
                # Cooldown is set when turning off, don't reset it here
                # Reset scheduled times
                self._scheduled_turn_on_time = None
        
        # Rule 5: Turn off immediately if someone left the room (people_count changed from >0 to 0)
        if (beliefs.state == "ON" and 
            self._previous_people_count > 0 and 
            beliefs.people_count == 0):
            intentions.append({
                "action": "turn_off",
                "target": beliefs.printer_id,
                "reason": "Someone left the room",
                "priority": 1
            })
            # Set cooldown after turning off (15-25 seconds random)
            cooldown_duration = random.uniform(15.0, 25.0)
            self._turn_off_cooldown_until = current_time + timedelta(seconds=cooldown_duration)
            logger.info(
                f"Printer {beliefs.printer_id} turning off: someone left the room. "
                f"Cooldown for {cooldown_duration:.1f}s"
            )
        
        # Rule 6: Turn off after 20 seconds of inactivity
        if beliefs.state == "ON" and self._printer_turned_on_at is not None:
            # Use last motion time if available, otherwise use turn on time
            reference_time = self._last_motion_time if self._last_motion_time is not None else self._printer_turned_on_at
            time_since_reference = (current_time - reference_time).total_seconds()
            
            # Fixed timeout: 20 seconds
            if time_since_reference >= self.motion_timeout:
                intentions.append({
                    "action": "turn_off",
                    "target": beliefs.printer_id,
                    "reason": f"No activity for {time_since_reference:.0f} seconds",
                    "priority": 1
                })
                # Set cooldown after turning off (15-25 seconds random)
                cooldown_duration = random.uniform(15.0, 25.0)
                self._turn_off_cooldown_until = current_time + timedelta(seconds=cooldown_duration)
                logger.info(
                    f"Printer {beliefs.printer_id} turning off: "
                    f"no activity for {time_since_reference:.0f}s (timeout: {self.motion_timeout}s). "
                    f"Cooldown for {cooldown_duration:.1f}s"
                )
        
        # Rule 7: Turn on printer (can turn on even if no one is in room, but respect cooldown)
        # Check if cooldown has expired
        cooldown_active = (self._turn_off_cooldown_until is not None and 
                          current_time < self._turn_off_cooldown_until)
        
        if cooldown_active:
            # Cooldown still active, don't turn on
            pass
        elif (beliefs.state == "OFF" and 
              not beliefs.power_outage and
              beliefs.toner_level > 0 and 
              beliefs.paper_level > 0):
            # Schedule turn on with random delay (1-100 seconds) and random probability (30-70%)
            if self._scheduled_turn_on_time is None:
                # Random probability to actually turn on (30-70% chance)
                turn_on_probability = random.uniform(0.3, 0.7)
                if random.random() < turn_on_probability:
                    # Schedule turn on with random delay (1-100 seconds)
                    delay = random.uniform(1.0, 100.0)
                    self._scheduled_turn_on_time = current_time + timedelta(seconds=delay)
                    logger.info(
                        f"Printer {beliefs.printer_id} scheduled to turn on in {delay:.1f}s "
                        f"(probability: {turn_on_probability*100:.0f}%)"
                    )
            
            # Check if scheduled time has arrived
            if (self._scheduled_turn_on_time is not None and 
                current_time >= self._scheduled_turn_on_time):
                # Clear cooldown and scheduled time when turning on
                self._turn_off_cooldown_until = None
                self._scheduled_turn_on_time = None
                intentions.append({
                    "action": "turn_on",
                    "target": beliefs.printer_id,
                    "reason": "Printer available and ready",
                    "priority": 3
                })
        else:
            # Reset scheduled turn on if condition no longer applies
            if self._scheduled_turn_on_time is not None:
                self._scheduled_turn_on_time = None
        
        # Update previous people count for next cycle
        # If printer just turned on, initialize to current count to avoid false exit detection
        if beliefs.state == "ON" and self._printer_turned_on_at is not None:
            time_since_turn_on = (current_time - self._printer_turned_on_at).total_seconds()
            if time_since_turn_on < 2.5:  # Within first cycle after turn on
                self._previous_people_count = beliefs.people_count
            else:
                # Normal update - only if printer has been on for a while
                self._previous_people_count = beliefs.people_count
        elif beliefs.state == "OFF":
            # Reset when printer is off
            self._previous_people_count = 0
        
        # Sort by priority
        intentions.sort(key=lambda x: x.get("priority", 999))
        
        return intentions
