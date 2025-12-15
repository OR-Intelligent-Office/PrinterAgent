#!/usr/bin/env python3
"""
Script for automatically starting agents for all printers.
Discovers all printers from the simulator and starts agents for them.
Automatically detects new printers and starts agents for them.
"""

import asyncio
import logging
import sys
import aiohttp
from typing import Set, Dict
from factory.agent_factory import AgentFactory
from agents.printer_agent import PrinterAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_all_printers(simulator_url: str, retries: int = 3) -> Set[str]:
    """
    Fetches list of all printers from simulator with retry logic.
    
    Args:
        simulator_url: URL of the simulator
        retries: Number of retry attempts
        
    Returns:
        Set of printer IDs
    """
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{simulator_url}/api/environment/state",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        state = await response.json()
                        printers = set()
                        
                        # Find printers in all rooms
                        rooms = state.get("rooms", [])
                        for room in rooms:
                            printer = room.get("printer")
                            if printer and printer.get("id"):
                                printers.add(printer["id"])
                        
                        if printers:
                            logger.info(f"Successfully connected to simulator. Found {len(printers)} printers: {printers}")
                        return printers
                    elif response.status == 500:
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                    else:
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return set()
        except asyncio.TimeoutError:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
        except aiohttp.ClientError:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
    
    logger.warning("Failed to fetch printer list after all attempts")
    return set()


async def start_agent_for_printer(
    printer_id: str,
    simulator_url: str,
    visualization_url: str = None
) -> PrinterAgent:
    """
    Starts an agent for a specific printer.
    
    Args:
        printer_id: ID of the printer
        simulator_url: URL of the simulator
        visualization_url: Optional URL of the visualization service
        
    Returns:
        Started PrinterAgent instance
    """
    logger.debug(f"Starting agent for printer: {printer_id}")
    
    agent = AgentFactory.create_agent(
        printer_id=printer_id,
        simulator_url=simulator_url,
        visualization_url=visualization_url
    )
    
    # Start agent in background
    asyncio.create_task(agent.start())
    
    return agent


async def main():
    """
    Main function - starts agents for all printers.
    Monitors for new printers and manages agent lifecycle.
    """
    simulator_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    visualization_url = sys.argv[2] if len(sys.argv) > 2 else None
    check_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    
    logger.info("Printer Agent Manager started")
    logger.debug(f"Simulator URL: {simulator_url}")
    if visualization_url:
        logger.debug(f"Visualization URL: {visualization_url}")
    logger.debug(f"Check interval: {check_interval} seconds")
    
    running_agents: Dict[str, PrinterAgent] = {}
    
    # Wait for simulator to start
    max_wait_time = 30
    wait_interval = 2
    waited = 0
    
    while waited < max_wait_time:
        printers = await get_all_printers(simulator_url, retries=1)
        if printers:
            logger.debug(f"Found {len(printers)} printers")
            break
        else:
            logger.debug(f"Waiting for simulator... ({waited}/{max_wait_time}s)")
            await asyncio.sleep(wait_interval)
            waited += wait_interval
    
    if waited >= max_wait_time:
        logger.warning("Simulator did not respond. Start simulator: cd OrSimulator && ./gradlew run")
        return
    
    async def check_and_start_agents():
        """Check for new printers and start/stop agents as needed."""
        nonlocal running_agents
        
        # Fetch all printers
        printers = await get_all_printers(simulator_url)
        
        # Start agents for new printers
        for printer_id in printers:
            if printer_id not in running_agents:
                try:
                    agent = await start_agent_for_printer(
                        printer_id,
                        simulator_url,
                        visualization_url
                    )
                    running_agents[printer_id] = agent
                    await asyncio.sleep(1)  # Small delay between starts
                except Exception as e:
                    logger.warning(f"Error starting agent for {printer_id}: {e}")
        
        # Remove agents for printers that no longer exist
        printers_to_remove = set(running_agents.keys()) - printers
        for printer_id in printers_to_remove:
            logger.debug(f"Printer {printer_id} no longer exists, stopping agent")
            agent = running_agents.pop(printer_id)
            agent.stop()
            await agent.cleanup()
        
        logger.debug(f"Active agents: {len(running_agents)} for printers: {list(running_agents.keys())}")
    
    # Initial agent startup
    await check_and_start_agents()
    
    # Monitoring loop
    try:
        while True:
            await asyncio.sleep(check_interval)
            await check_and_start_agents()
    except KeyboardInterrupt:
        logger.info("Stopping all agents...")
        
        # Stop all agents
        for printer_id, agent in running_agents.items():
            logger.debug(f"Stopping agent for {printer_id}")
            agent.stop()
            await agent.cleanup()
        
        logger.info("All agents stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("Stopped")
