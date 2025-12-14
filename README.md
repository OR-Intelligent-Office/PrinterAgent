# PrinterAgent

Agent odpowiedzialny za podstawowe czynności drukarki w systemie MAS (Multi-Agent System).

## Architektura

Projekt został zaprojektowany zgodnie z zasadami SOLID:

- **Single Responsibility Principle (SRP)**: Każda klasa ma jedną odpowiedzialność
  - `SimulatorEnvironmentClient` - tylko komunikacja z API symulatora
  - `SimulatorDeviceController` - tylko kontrola urządzeń
  - `BeliefManager` - tylko zarządzanie przekonaniami
  - `DesireManager` - tylko zarządzanie pragnieniami
  - `RuleBasedIntentionPlanner` - tylko planowanie akcji
  - `ActionExecutor` - tylko wykonywanie akcji

- **Open/Closed Principle (OCP)**: System otwarty na rozszerzenia, zamknięty na modyfikacje
  - Nowe reguły decyzyjne można dodać bez modyfikacji istniejących
  - Nowe typy klientów można dodać implementując interfejsy

- **Liskov Substitution Principle (LSP)**: Wszystkie implementacje są zamienne przez interfejsy

- **Interface Segregation Principle (ISP)**: Specyficzne interfejsy zamiast jednego dużego
  - `IEnvironmentClient`, `IDeviceController`, `IBeliefManager`, etc.

- **Dependency Inversion Principle (DIP)**: Zależności od abstrakcji
  - Agent zależy od interfejsów, nie konkretnych implementacji
  - Dependency Injection przez konstruktor

## Struktura projektu

```
PrinterAgent/
├── interfaces.py              # Wszystkie interfejsy (ISP, DIP)
├── environment_client.py      # Klient środowiska (SRP)
├── device_controller.py       # Kontroler urządzeń (SRP)
├── belief_manager.py         # Zarządzanie przekonaniami (SRP)
├── desire_manager.py          # Zarządzanie pragnieniami (SRP)
├── intention_planner.py       # Planowanie intencji (SRP, OCP)
├── action_executor.py        # Wykonawca akcji (SRP, DIP)
├── message_bus.py            # Komunikacja między agentami (SRP)
├── visualization_client.py   # Klient wizualizacji (SRP)
├── printer_agent.py           # Główna klasa agenta (SOLID)
├── agent_factory.py          # Fabryka agentów (DIP)
├── main.py                    # Punkt wejścia
├── requirements.txt           # Zależności Python
└── README.md                  # Dokumentacja
```

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

### Pojedynczy agent

```bash
python main.py [printer_id] [simulator_url] [visualization_url]
```

Przykłady:
```bash
# Domyślne ustawienia (printer_208, localhost:8080)
python main.py

# Konkretna drukarka
python main.py printer_209

# Z wizualizatorem
python main.py printer_208 http://localhost:8080 http://localhost:3000
```

### Wiele agentów

Można uruchomić wiele agentów dla różnych drukarek:

```bash
# Terminal 1
python main.py printer_208

# Terminal 2
python main.py printer_209

# Terminal 3
python main.py printer_101
```

## Funkcjonalności

### 1. Odbieranie danych ze środowiska

Agent regularnie pobiera stan środowiska z OrSimulator przez API:
- Stan drukarki (ON/OFF/BROKEN)
- Poziom tonera i papieru
- Obecność ludzi w pokoju
- Stan zasilania

### 2. Podejmowanie decyzji (BDI)

Agent implementuje logikę BDI (Beliefs, Desires, Intentions):

- **Beliefs (Przekonania)**: Aktualny stan środowiska i drukarki
- **Desires (Pragnienia)**: 
  - Utrzymanie drukarki w dobrym stanie
  - Oszczędzanie energii
  - Zapewnienie dostępności
- **Intentions (Intencje)**: Planowane akcje na podstawie reguł:
  - Włączenie gdy wykryto ruch
  - Wyłączenie po czasie bezczynności
  - Alerty przy niskim poziomie tonera/papieru
  - Obsługa awarii

### 3. Wykonywanie akcji

Agent wykonuje akcje przez API symulatora:
- Włączanie/wyłączanie drukarki
- Ustawianie poziomu tonera/papieru (symulacja)
- Wysyłanie alertów

### 4. Komunikacja między agentami

Agent może komunikować się z innymi agentami przez:
- Protokół JSON-based (podobny do FIPA ACL)
- Performatywy: `request`, `inform`, `query`, `agree`, `refuse`
- Przykłady:
  - Zapytanie o dostępność innej drukarki
  - Informowanie o stanie
  - Koordynacja działań

### 5. Integracja z wizualizatorem

Agent może wysyłać dane do wizualizatora:
- Alerty (niskie zasoby, awarie)
- Aktualizacje stanu agenta
- Historia zdarzeń

## Rozszerzanie

### Dodanie nowej reguły decyzyjnej

W `intention_planner.py` dodaj nową regułę w metodzie `deliberate()`:

```python
# Reguła 7: Nowa reguła
if beliefs.condition:
    intentions.append({
        "action": "new_action",
        "target": beliefs.printer_id,
        "reason": "Reason for action",
        "priority": 1
    })
```

### Dodanie nowego typu akcji

1. Dodaj obsługę w `action_executor.py`:
```python
elif action == "new_action":
    return await self._do_new_action(intention)
```

2. Dodaj metodę w kontrolerze urządzeń (jeśli potrzebna)

### Dodanie nowego klienta

Zaimplementuj odpowiedni interfejs:
```python
class NewClient(IVisualizationClient):
    async def send_alert(self, alert_type: str, data: Dict[str, Any]):
        # Implementacja
        pass
```

## Testowanie

```bash
# Uruchom symulator
cd OrSimulator
./gradlew run

# W innym terminalu uruchom agenta
cd PrinterAgent
python main.py printer_208
```

## Wymagania

- Python 3.8+
- OrSimulator działający na porcie 8080
- (Opcjonalnie) OrWizualizator dla wizualizacji
