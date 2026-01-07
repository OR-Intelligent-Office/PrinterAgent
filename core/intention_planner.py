import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from interfaces.bdi_interfaces import IIntentionPlanner
from models.environment_models import PrinterState

logger = logging.getLogger(__name__)


class RuleBasedIntentionPlanner(IIntentionPlanner):
    def __init__(
        self,
        toner_threshold_low: int = 20,
        paper_threshold_low: int = 15,
        print_duration_min: int = 1,
        print_duration_max: int = 10,
        consumption_interval_seconds: float = 1.0,
        idle_shutdown_seconds: int = 20,
        room_inactivity_shutdown_seconds: int = 10,
        min_on_seconds: int = 10,
        min_off_seconds: int = 10,
    ):
        self.toner_threshold_low = toner_threshold_low
        self.paper_threshold_low = paper_threshold_low
        self.print_duration_min = print_duration_min
        self.print_duration_max = print_duration_max
        self.consumption_interval_seconds = consumption_interval_seconds
        self.idle_shutdown_seconds = idle_shutdown_seconds
        self.room_inactivity_shutdown_seconds = room_inactivity_shutdown_seconds
        self.min_on_seconds = min_on_seconds
        self.min_off_seconds = min_off_seconds
        
        self._current_session_start: Optional[datetime] = None
        self._current_session_end: Optional[datetime] = None
        self._last_consumption_time: Optional[datetime] = None
        self._last_printer_state: Optional[str] = None
        self._is_consuming_resources: bool = False
        self._shutdown_pending: bool = False  # Blocks new sessions until actual OFF
        self._print_session_started_once: bool = False  # Single session per ON cycle
        self._session_finished_at: Optional[datetime] = None  # Print mode end time
        self._last_on_at: Optional[datetime] = None
        self._last_off_at: Optional[datetime] = None
        self._last_room_activity_at: Optional[datetime] = None
        self._last_motion_time: Optional[str] = None
        self._last_people_count: int = 0
        self._last_session_started_at: Optional[datetime] = None

        # one-shot alerts (reset when condition clears)
        self._alerted_power_outage: bool = False
        self._alerted_failure: bool = False
        self._alerted_toner_low: bool = False
        self._alerted_paper_low: bool = False
        self._alerted_toner_zero: bool = False
        self._alerted_paper_zero: bool = False
    
    def _reset_consumption_tracking(self):
        self._current_session_start = None
        self._current_session_end = None
        self._last_consumption_time = None
        self._is_consuming_resources = False
        self._shutdown_pending = False
        self._print_session_started_once = False
        self._session_finished_at = None

    def _reset_print_session_only(self):
        self._current_session_start = None
        self._current_session_end = None
        self._last_consumption_time = None
        self._is_consuming_resources = False
        self._shutdown_pending = True
        self._print_session_started_once = False
        self._session_finished_at = None

    def _can_turn_on(self, now: datetime) -> bool:
        return self._last_off_at is None or (now - self._last_off_at).total_seconds() >= self.min_off_seconds

    def _can_turn_off(self, now: datetime) -> bool:
        return self._last_on_at is None or (now - self._last_on_at).total_seconds() >= self.min_on_seconds
    
    def _start_print_session(self, now: datetime, printer_id: str):
        duration = random.randint(self.print_duration_min, self.print_duration_max)
        self._current_session_start = now
        self._current_session_end = now + timedelta(seconds=duration)
        self._last_consumption_time = None
        self._is_consuming_resources = True
        self._last_session_started_at = now
        logger.debug(
            f"Printer {printer_id} entered print mode for {duration}s "
            f"(range {self.print_duration_min}-{self.print_duration_max}s)"
        )
    
    def is_consuming(self) -> bool:
        return self._is_consuming_resources
    
    def deliberate(
        self, 
        beliefs: Optional[PrinterState],
        desires: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not beliefs:
            self._reset_consumption_tracking()
            return []
        
        intentions: List[Dict[str, Any]] = []
        now = datetime.now()

        # Track ON/OFF transitions from observed state
        if self._last_printer_state == "ON" and beliefs.state != "ON":
            self._last_off_at = now
        if self._last_printer_state != "ON" and beliefs.state == "ON":
            self._last_on_at = now

        # Activity detection (entry or motion update)
        if self._last_room_activity_at is None:
            self._last_room_activity_at = now
            self._last_people_count = beliefs.people_count
            self._last_motion_time = beliefs.last_motion_time

        activity_event = False
        if beliefs.people_count > 0 and self._last_people_count <= 0:
            activity_event = True
        if beliefs.last_motion_time and beliefs.last_motion_time != self._last_motion_time:
            activity_event = True
        if beliefs.people_count != self._last_people_count:
            # treat leaving/arriving as activity signal for timers
            activity_event = True

        if activity_event:
            self._last_room_activity_at = now

        self._last_people_count = beliefs.people_count
        self._last_motion_time = beliefs.last_motion_time

        # One-shot alerts
        if beliefs.power_outage:
            if not self._alerted_power_outage:
                intentions.append(
                    {
                        "action": "handle_power_outage",
                        "target": beliefs.printer_id,
                        "reason": "Power outage detected",
                        "priority": 0,
                    }
                )
                self._alerted_power_outage = True
        else:
            self._alerted_power_outage = False

        if beliefs.state == "BROKEN":
            if not self._alerted_failure:
                intentions.append(
                    {
                        "action": "handle_failure",
                        "target": beliefs.printer_id,
                        "reason": "Printer is broken",
                        "priority": 0,
                        "room": beliefs.room_name,
                    }
                )
                self._alerted_failure = True
        else:
            self._alerted_failure = False

        if beliefs.toner_level == 0:
            if not self._alerted_toner_zero:
                intentions.append(
                    {
                        "action": "alert_low_toner",
                        "target": beliefs.printer_id,
                        "reason": "Toner depleted",
                        "priority": 0,
                        "toner_level": beliefs.toner_level,
                    }
                )
                self._alerted_toner_zero = True
                self._alerted_toner_low = True
        else:
            self._alerted_toner_zero = False
            if beliefs.toner_level < self.toner_threshold_low:
                if not self._alerted_toner_low:
                    intentions.append(
                        {
                            "action": "alert_low_toner",
                            "target": beliefs.printer_id,
                            "reason": f"Toner level is low: {beliefs.toner_level}%",
                            "priority": 1,
                            "toner_level": beliefs.toner_level,
                        }
                    )
                    self._alerted_toner_low = True
            else:
                self._alerted_toner_low = False

        if beliefs.paper_level == 0:
            if not self._alerted_paper_zero:
                intentions.append(
                    {
                        "action": "alert_low_paper",
                        "target": beliefs.printer_id,
                        "reason": "Paper depleted",
                        "priority": 0,
                        "paper_level": beliefs.paper_level,
                    }
                )
                self._alerted_paper_zero = True
                self._alerted_paper_low = True
        else:
            self._alerted_paper_zero = False
            if beliefs.paper_level < self.paper_threshold_low:
                if not self._alerted_paper_low:
                    intentions.append(
                        {
                            "action": "alert_low_paper",
                            "target": beliefs.printer_id,
                            "reason": f"Paper level is low: {beliefs.paper_level}%",
                            "priority": 1,
                            "paper_level": beliefs.paper_level,
                        }
                    )
                    self._alerted_paper_low = True
            else:
                self._alerted_paper_low = False

        # Hard conditions: always force OFF (ignore min_on)
        hard_stop = (
            beliefs.power_outage
            or beliefs.state == "BROKEN"
            or beliefs.toner_level == 0
            or beliefs.paper_level == 0
        )
        if hard_stop:
            if beliefs.state == "ON":
                intentions.append(
                    {
                        "action": "turn_off",
                        "target": beliefs.printer_id,
                        "reason": "Hard stop condition",
                        "priority": 0,
                    }
                )
                self._last_off_at = now
                self._reset_print_session_only()
            self._last_printer_state = beliefs.state
            intentions.sort(key=lambda x: x.get("priority", 999))
            return intentions
        
        # OFF -> ON: only on entry/motion activity while people present
        if beliefs.state != "ON":
            should_turn_on = (
                beliefs.people_count > 0
                and activity_event
                and beliefs.toner_level > 0
                and beliefs.paper_level > 0
                and self._can_turn_on(now)
            )
            if should_turn_on:
                intentions.append(
                    {
                        "action": "turn_on",
                        "target": beliefs.printer_id,
                        "reason": "Room activity detected",
                        "priority": 2,
                    }
                )
                self._last_on_at = now
                self._shutdown_pending = False
                self._print_session_started_once = False
            self._reset_consumption_tracking()
            self._last_printer_state = beliefs.state
            intentions.sort(key=lambda x: x.get("priority", 999))
            return intentions

        # Printer is ON
        state_just_turned_on = self._last_printer_state != "ON"
        if state_just_turned_on:
            self._last_on_at = now

        # Start exactly one print session per ON, and protect against state jitter
        # (temporary OFF/ON reads) by applying a cooldown between session starts.
        can_start_session_now = (
            self._last_session_started_at is None
            or (now - self._last_session_started_at).total_seconds()
            >= float((self.print_duration_max + 1) * 5)
        )
        if (
            not self._shutdown_pending
            and state_just_turned_on
            and not self._print_session_started_once
            and can_start_session_now
        ):
            self._start_print_session(now, beliefs.printer_id)
            self._print_session_started_once = True
        
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
            self._is_consuming_resources = False
            if self._session_finished_at is None and self._current_session_end is not None:
                self._session_finished_at = self._current_session_end
            
            last_activity = self._session_finished_at or self._last_consumption_time or now
            idle_seconds = (now - last_activity).total_seconds()

            # OFF after 20s without usage (printing)
            if idle_seconds >= float(self.idle_shutdown_seconds) and self._can_turn_off(now):
                intentions.append(
                    {
                        "action": "turn_off",
                        "target": beliefs.printer_id,
                        "reason": f"No printing for {idle_seconds:.0f}s",
                        "priority": 1,
                    }
                )
                self._last_off_at = now
                self._reset_print_session_only()

        # OFF after 10s without room activity (if not printing)
        room_idle = (now - (self._last_room_activity_at or now)).total_seconds()
        if not self._is_consuming_resources and room_idle >= float(self.room_inactivity_shutdown_seconds):
            if self._can_turn_off(now):
                intentions.append(
                    {
                        "action": "turn_off",
                        "target": beliefs.printer_id,
                        "reason": f"No room activity for {room_idle:.0f}s",
                        "priority": 1,
                    }
                )
                self._last_off_at = now
                self._reset_print_session_only()
        
        self._last_printer_state = beliefs.state
        intentions.sort(key=lambda x: x.get("priority", 999))
        return intentions
