#!/usr/bin/env python3
# Main entry point for printer agent

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
    # Main function - start agent
    # Command line parameters
    printer_id = sys.argv[1] if len(sys.argv) > 1 else "printer_208"
    simulator_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8080"
    visualization_url = sys.argv[3] if len(sys.argv) > 3 else None
    
    logger.info(f"Starting PrinterAgent for printer: {printer_id}")
    logger.debug(f"Simulator URL: {simulator_url}")
    if visualization_url:
        logger.debug(f"Visualization URL: {visualization_url}")
    
    # Create agent via factory
    agent = AgentFactory.create_agent(
        printer_id=printer_id,
        simulator_url=simulator_url,
        visualization_url=visualization_url
    )
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.debug("Shutting down agent...")
        agent.stop()
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
