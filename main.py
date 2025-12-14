#!/usr/bin/env python3
"""
Główny plik uruchomieniowy agenta drukarki
"""

import asyncio
import logging
import sys
from factory.agent_factory import AgentFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Główna funkcja - uruchamia agenta"""
    # Parametry z linii poleceń
    printer_id = sys.argv[1] if len(sys.argv) > 1 else "printer_208"
    simulator_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8080"
    visualization_url = sys.argv[3] if len(sys.argv) > 3 else None
    
    logger.info(f"Starting PrinterAgent for printer: {printer_id}")
    logger.info(f"Simulator URL: {simulator_url}")
    if visualization_url:
        logger.info(f"Visualization URL: {visualization_url}")
    
    # Tworzenie agenta przez fabrykę
    agent = AgentFactory.create_agent(
        printer_id=printer_id,
        simulator_url=simulator_url,
        visualization_url=visualization_url
    )
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down agent...")
        agent.stop()
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
