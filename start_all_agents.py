#!/usr/bin/env python3
"""
Skrypt do automatycznego uruchamiania agentów dla wszystkich drukarek
Wykrywa wszystkie drukarki z symulatora i uruchamia dla nich agentów
Automatycznie wykrywa nowe drukarki i uruchamia dla nich agentów
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
    """Pobiera listę wszystkich drukarek z symulatora z retry logic"""
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                # Użyj /api/environment/state zamiast /devices (bardziej niezawodny)
                async with session.get(
                    f"{simulator_url}/api/environment/state",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        state = await response.json()
                        printers = set()
                        
                        # Przejdź przez wszystkie pokoje i znajdź drukarki
                        rooms = state.get("rooms", [])
                        for room in rooms:
                            printer = room.get("printer")
                            if printer and printer.get("id"):
                                printers.add(printer["id"])
                        
                        if printers:
                            logger.info(f"Znaleziono {len(printers)} drukarek: {printers}")
                        return printers
                    elif response.status == 500:
                        error_text = await response.text()
                        logger.warning(
                            f"Symulator zwrócił błąd 500 (próba {attempt + 1}/{retries}): {error_text[:200]}"
                        )
                        if attempt < retries - 1:
                            await asyncio.sleep(2)  # Poczekaj przed ponowną próbą
                            continue
                    else:
                        logger.warning(
                            f"Failed to fetch devices: {response.status} (próba {attempt + 1}/{retries})"
                        )
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return set()
        except asyncio.TimeoutError:
            logger.warning(f"Timeout przy pobieraniu drukarek (próba {attempt + 1}/{retries})")
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
        except aiohttp.ClientError as e:
            logger.warning(f"Błąd połączenia z symulatorem (próba {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd przy pobieraniu drukarek: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
    
    logger.error("Nie udało się pobrać listy drukarek po wszystkich próbach")
    return set()


async def start_agent_for_printer(
    printer_id: str,
    simulator_url: str,
    visualization_url: str = None
) -> PrinterAgent:
    """Uruchamia agenta dla konkretnej drukarki"""
    logger.info(f"🚀 Uruchamianie agenta dla drukarki: {printer_id}")
    
    agent = AgentFactory.create_agent(
        printer_id=printer_id,
        simulator_url=simulator_url,
        visualization_url=visualization_url
    )
    
    # Uruchom agenta w tle
    asyncio.create_task(agent.start())
    
    return agent


async def main():
    """Główna funkcja - uruchamia agentów dla wszystkich drukarek"""
    simulator_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    visualization_url = sys.argv[2] if len(sys.argv) > 2 else None
    check_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30  # Sprawdzaj co 30 sekund
    
    logger.info("=" * 60)
    logger.info("🤖 Manager Agentów Drukarek")
    logger.info("=" * 60)
    logger.info(f"Simulator URL: {simulator_url}")
    if visualization_url:
        logger.info(f"Visualization URL: {visualization_url}")
    logger.info(f"Interwał sprawdzania nowych drukarek: {check_interval} sekund")
    logger.info("")
    
    # Słownik przechowujący uruchomione agenty: printer_id -> agent
    running_agents: Dict[str, PrinterAgent] = {}
    
    # Poczekaj chwilę, aby symulator się uruchomił i sprawdź czy działa
    logger.info("Czekanie na symulator...")
    max_wait_time = 30  # Maksymalnie 30 sekund
    wait_interval = 2
    waited = 0
    
    while waited < max_wait_time:
        printers = await get_all_printers(simulator_url, retries=1)
        if printers:
            logger.info(f"✅ Symulator działa! Znaleziono {len(printers)} drukarek.")
            break
        else:
            logger.info(f"⏳ Czekam na symulator... ({waited}/{max_wait_time}s)")
            await asyncio.sleep(wait_interval)
            waited += wait_interval
    
    if waited >= max_wait_time:
        logger.error("❌ Symulator nie odpowiada po 30 sekundach. Sprawdź czy symulator jest uruchomiony.")
        logger.error("   Uruchom symulator: cd OrSimulator && ./gradlew run")
        return
    
    # Funkcja do sprawdzania i uruchamiania agentów
    async def check_and_start_agents():
        nonlocal running_agents
        
        # Pobierz wszystkie drukarki
        printers = await get_all_printers(simulator_url)
        
        # Uruchom agentów dla nowych drukarek
        for printer_id in printers:
            if printer_id not in running_agents:
                try:
                    agent = await start_agent_for_printer(
                        printer_id,
                        simulator_url,
                        visualization_url
                    )
                    running_agents[printer_id] = agent
                    await asyncio.sleep(1)  # Małe opóźnienie między uruchomieniami
                except Exception as e:
                    logger.error(f"Błąd przy uruchamianiu agenta dla {printer_id}: {e}")
        
        # Usuń agentów dla drukarek, które już nie istnieją
        printers_to_remove = set(running_agents.keys()) - printers
        for printer_id in printers_to_remove:
            logger.info(f"⚠️  Drukarka {printer_id} już nie istnieje, zatrzymywanie agenta...")
            agent = running_agents.pop(printer_id)
            agent.stop()
            await agent.cleanup()
        
        logger.info(f"📊 Status: {len(running_agents)} aktywnych agentów dla drukarek: {list(running_agents.keys())}")
    
    # Pierwsze uruchomienie
    await check_and_start_agents()
    
    # Pętla monitorująca nowe drukarki
    try:
        while True:
            await asyncio.sleep(check_interval)
            await check_and_start_agents()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🛑 Zatrzymywanie wszystkich agentów...")
        logger.info("=" * 60)
        
        # Zatrzymaj wszystkich agentów
        for printer_id, agent in running_agents.items():
            logger.info(f"Zatrzymywanie agenta dla {printer_id}...")
            agent.stop()
            await agent.cleanup()
        
        logger.info("✅ Wszystkie agenty zostały zatrzymane")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Zakończono przez użytkownika")
