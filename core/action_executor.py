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
                result = await self.device_controller.turn_on(target)
                if result:
                    logger.info(f"✅ Successfully turned ON printer {target}")
                else:
                    logger.warning(f"❌ Failed to turn ON printer {target}")
                return result
            
            elif action == "turn_off":
                result = await self.device_controller.turn_off(target)
                if result:
                    logger.info(f"✅ Successfully turned OFF printer {target}")
                else:
                    logger.warning(f"❌ Failed to turn OFF printer {target}")
                return result
            
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
            
            elif action == "consume_resources":
                # Per-second consumption of toner and paper
                toner_consumption = float(intention.get("toner_consumption", 0.0))
                paper_consumption = float(intention.get("paper_consumption", 0.0))
                current_toner = int(intention.get("current_toner", 100))
                current_paper = int(intention.get("current_paper", 100))
                
                # Clamp values to avoid negative levels
                paper_used = min(max(paper_consumption, 0.0), float(current_paper))
                toner_used = min(max(toner_consumption, 0.0), float(current_toner))
                
                if paper_used > 0 or toner_used > 0:
                    new_toner = max(0, int(current_toner - toner_used))
                    new_paper = max(0, int(current_paper - paper_used))
                    
                    if toner_used > 0:
                        await self.device_controller.set_toner_level(target, new_toner)
                    if paper_used > 0:
                        await self.device_controller.set_paper_level(target, new_paper)
                    
                    logger.debug(
                        f"Consumed resources for {target}: "
                        f"toner -{toner_used:.2f}% ({current_toner}% -> {new_toner}%), "
                        f"paper -{paper_used:.2f}% ({current_paper}% -> {new_paper}%)"
                    )
                    
                    # Informacja co sekundę do wizualizatora
                    await self.visualization_client.send_state_update({
                        "printer_id": target,
                        "state": "printing",
                        "printer_state": "ON",
                        "toner_level": new_toner,
                        "paper_level": new_paper,
                        "consumption": {
                            "toner": toner_used,
                            "paper": paper_used
                        }
                    })
                
                return True
            
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing intention {action}: {e}")
            return False

