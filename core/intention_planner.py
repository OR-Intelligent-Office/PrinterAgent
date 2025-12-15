# Intention planning (BDI Intentions)
# Single Responsibility: only action planning
# Open/Closed Principle: easy to extend with new rules

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from interfaces.bdi_interfaces import IIntentionPlanner
from models.environment_models import PrinterState

logger = logging.getLogger(__name__)


class RuleBasedIntentionPlanner(IIntentionPlanner):
    # Rule-based intention planner for printer simulation
    # Maintains short print sessions, per-second resource consumption
    # and automatic shutdown when printer is idle or room is empty
    
    def __init__(
        self,
        toner_threshold_low: int = 20,
        paper_threshold_low: int = 15,
        print_duration_min: int = 1,
        print_duration_max: int = 10,
        consumption_interval_seconds: float = 1.0,
        idle_shutdown_seconds: int = 10
    ):
        self.toner_threshold_low = toner_threshold_low
        self.paper_threshold_low = paper_threshold_low
        self.print_duration_min = print_duration_min
        self.print_duration_max = print_duration_max
        self.consumption_interval_seconds = consumption_interval_seconds
        self.idle_shutdown_seconds = idle_shutdown_seconds
        
        # Print session state tracking
        self._current_session_start: Optional[datetime] = None
        self._current_session_end: Optional[datetime] = None
        self._last_consumption_time: Optional[datetime] = None
        self._last_printer_state: Optional[str] = None
        self._is_consuming_resources: bool = False
        self._shutdown_pending: bool = False  # Blocks new sessions until actual OFF
        self._print_session_started_once: bool = False  # Single session per ON cycle
        self._session_finished_at: Optional[datetime] = None  # Print mode end time
        self._last_turn_on_time: Optional[datetime] = None  # Min interval between starts
        self._last_session_end_time: Optional[datetime] = None  # Interval from end to next start
    
    def _reset_consumption_tracking(self):
        # Clear print session data
        self._current_session_start = None
        self._current_session_end = None
        self._last_consumption_time = None
        self._is_consuming_resources = False
        self._shutdown_pending = False
        self._print_session_started_once = False
        self._session_finished_at = None
        # _last_turn_on_time and _last_session_end_time are preserved
        # to respect minimum interval between starts
    
    def _start_print_session(self, now: datetime, printer_id: str):
        # Start new print session with random duration
        duration = random.randint(self.print_duration_min, self.print_duration_max)
        self._current_session_start = now
        self._current_session_end = now + timedelta(seconds=duration)
        self._last_consumption_time = None
        self._is_consuming_resources = True
        logger.debug(
            f"Printer {printer_id} entered print mode for {duration}s "
            f"(range {self.print_duration_min}-{self.print_duration_max}s)"
        )
    
    def is_consuming(self) -> bool:
        # Helper info for agent about actual resource consumption
        return self._is_consuming_resources
    
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # Analyze beliefs and desires, generate intentions with per-second
        # resource consumption and automatic shutdown
        if not beliefs:
            self._reset_consumption_tracking()
            return []
        
        intentions: List[Dict[str, Any]] = []
        now = datetime.now()
        
        # Check resource alerts and failures
        if beliefs.toner_level < self.toner_threshold_low:
            intentions.append({
                "action": "alert_low_toner",
                "target": beliefs.printer_id,
                "reason": f"Toner level is low: {beliefs.toner_level}%",
                "priority": 1,
                "toner_level": beliefs.toner_level
            })
        
        if beliefs.paper_level < self.paper_threshold_low:
            intentions.append({
                "action": "alert_low_paper",
                "target": beliefs.printer_id,
                "reason": f"Paper level is low: {beliefs.paper_level}%",
                "priority": 1,
                "paper_level": beliefs.paper_level
            })
        
        if beliefs.state == "BROKEN":
            intentions.append({
                "action": "handle_failure",
                "target": beliefs.printer_id,
                "reason": "Printer is broken",
                "priority": 1,
                "room": beliefs.room_name
            })
        
        if beliefs.power_outage:
            intentions.append({
                "action": "handle_power_outage",
                "target": beliefs.printer_id,
                "reason": "Power outage detected",
                "priority": 1
            })
            # Turn off printer if ON during power outage
            if beliefs.state == "ON":
                intentions.append({
                    "action": "turn_off",
                    "target": beliefs.printer_id,
                    "reason": "Power outage - forced shutdown",
                    "priority": 0
                })
                self._reset_consumption_tracking()
                self._last_printer_state = beliefs.state
                self._shutdown_pending = True
                self._last_session_end_time = now
                intentions.sort(key=lambda x: x.get("priority", 999))
                return intentions
        
        # Try to start printer if OFF
        if beliefs.state != "ON":
            if (not beliefs.power_outage 
                and beliefs.toner_level > 0 
                and beliefs.paper_level > 0):
                # Probabilistic start based on time of day
                hour = now.hour
                if 7 <= hour < 13:
                    turn_on_prob = 0.8
                elif 13 <= hour < 21:
                    turn_on_prob = 0.5
                else:
                    turn_on_prob = 0.1
                
                # Minimum 5s interval from previous start or session end
                last_blocking_time = self._last_turn_on_time
                if self._last_session_end_time and (last_blocking_time is None or self._last_session_end_time > last_blocking_time):
                    last_blocking_time = self._last_session_end_time
                can_turn_on_now = (
                    last_blocking_time is None or 
                    (now - last_blocking_time).total_seconds() >= 5.0
                )
                
                if can_turn_on_now and random.random() < turn_on_prob:
                    intentions.append({
                        "action": "turn_on",
                        "target": beliefs.printer_id,
                        "reason": "Start print mode (time-window probability)",
                        "priority": 2
                    })
                    self._last_turn_on_time = now
            self._reset_consumption_tracking()
            self._last_printer_state = beliefs.state
            self._shutdown_pending = False
            intentions.sort(key=lambda x: x.get("priority", 999))
            return intentions
        
        # Printer is ON - start print session
        state_just_turned_on = self._last_printer_state != "ON"
        if not self._shutdown_pending and (state_just_turned_on and not self._print_session_started_once):
            self._start_print_session(now, beliefs.printer_id)
            self._print_session_started_once = True
        
        # Turn off immediately if room is empty
        if beliefs.people_count <= 0:
            intentions.append({
                "action": "turn_off",
                "target": beliefs.printer_id,
                "reason": "Room empty - shutting down printer",
                "priority": 0
            })
            self._reset_consumption_tracking()
            self._last_printer_state = beliefs.state
            self._shutdown_pending = True
            self._last_session_end_time = now
            intentions.sort(key=lambda x: x.get("priority", 999))
            return intentions
        
        # Print session: consume resources every 1s within 1-10s window
        session_active = (
            self._current_session_end is not None
            and now < self._current_session_end
            and beliefs.paper_level > 0
            and beliefs.toner_level > 0
        )
        
        if session_active and not self._shutdown_pending:
            time_since_last_tick = (
                (now - self._last_consumption_time).total_seconds()
                if self._last_consumption_time
                else None
            )
            
            if time_since_last_tick is None or time_since_last_tick >= self.consumption_interval_seconds:
                paper_consumption = random.uniform(1.0, 4.0)
                paper_consumption = min(paper_consumption, float(beliefs.paper_level))
                toner_consumption = 1.0 if paper_consumption <= 2.0 else 2.0
                toner_consumption = min(toner_consumption, float(beliefs.toner_level))
                
                intentions.append({
                    "action": "consume_resources",
                    "target": beliefs.printer_id,
                    "reason": "Per-second print consumption",
                    "priority": 0,
                    "toner_consumption": toner_consumption,
                    "paper_consumption": paper_consumption,
                    "current_toner": beliefs.toner_level,
                    "current_paper": beliefs.paper_level
                })
                self._last_consumption_time = now
                self._is_consuming_resources = True
        else:
            # Session ended or no resources - check shutdown after 15s
            self._is_consuming_resources = False
            # Set session end time if not set
            if self._session_finished_at is None and self._current_session_end is not None:
                self._session_finished_at = self._current_session_end
                self._last_session_end_time = self._current_session_end
            
            last_activity = self._session_finished_at or self._last_consumption_time or now
            idle_seconds = (now - last_activity).total_seconds()
            # Wait 15s after session end, then turn off
            shutdown_timeout = 15
            if idle_seconds >= shutdown_timeout:
                intentions.append({
                    "action": "turn_off",
                    "target": beliefs.printer_id,
                    "reason": f"No resource consumption for {idle_seconds:.0f}s",
                    "priority": 1
                })
                self._reset_consumption_tracking()
                self._shutdown_pending = True
                self._last_session_end_time = now
        
        self._last_printer_state = beliefs.state
        intentions.sort(key=lambda x: x.get("priority", 999))
        return intentions
