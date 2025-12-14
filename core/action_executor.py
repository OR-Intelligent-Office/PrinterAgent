"""
Wykonawca akcji agenta
Single Responsibility: tylko wykonywanie akcji
"""

import logging
from typing import Dict, Any
from interfaces.action_interfaces import IActionExecutor
from interfaces.device_interfaces import IDeviceController
from interfaces.visualization_interfaces import IVisualizationClient

logger = logging.getLogger(__name__)


class ActionExecutor(IActionExecutor):
    """
    Wykonawca akcji - wykonuje intencje agenta
    Zgodnie z SRP: tylko odpowiedzialność za wykonywanie akcji
    Zgodnie z DIP: zależy od abstrakcji (IDeviceController, IVisualizationClient)
    """
    
    def __init__(
        self,
        device_controller: IDeviceController,
        visualization_client: IVisualizationClient
    ):
        self.device_controller = device_controller
        self.visualization_client = visualization_client
    
    async def execute(self, intention: Dict[str, Any]) -> bool:
        """Wykonuje intencję (akcję)"""
        action = intention.get("action")
        target = intention.get("target")
        reason = intention.get("reason", "")
        
        logger.info(f"Executing intention: {action} - {reason}")
        
        try:
            if action == "turn_on":
                return await self.device_controller.turn_on(target)
            
            elif action == "turn_off":
                return await self.device_controller.turn_off(target)
            
            elif action == "alert_low_toner":
                toner_level = intention.get("toner_level", 0)
                logger.warning(f"⚠️ ALERT: Low toner level in {target}: {toner_level}%")
                await self.visualization_client.send_alert("low_toner", {
                    "printer_id": target,
                    "toner_level": toner_level
                })
                # Zwracamy True, ale intencja będzie ponownie dodana w następnym cyklu jeśli problem nadal istnieje
                return True
            
            elif action == "alert_low_paper":
                paper_level = intention.get("paper_level", 0)
                logger.warning(f"⚠️ ALERT: Low paper level in {target}: {paper_level}%")
                await self.visualization_client.send_alert("low_paper", {
                    "printer_id": target,
                    "paper_level": paper_level
                })
                # Zwracamy True, ale intencja będzie ponownie dodana w następnym cyklu jeśli problem nadal istnieje
                return True
            
            elif action == "handle_failure":
                await self.visualization_client.send_alert("printer_failure", {
                    "printer_id": target,
                    "room": intention.get("room", "unknown")
                })
                return True
            
            elif action == "handle_power_outage":
                logger.warning("Power outage - printer will be unavailable")
                return True
            
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing intention {action}: {e}")
            return False

