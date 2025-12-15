"""
Interfejsy i abstrakcje zgodnie z zasadami SOLID
Interface Segregation Principle (ISP) - specyficzne interfejsy
Dependency Inversion Principle (DIP) - zależności od abstrakcji
"""

from .environment_interfaces import IEnvironmentClient
from .device_interfaces import IDeviceController
from .bdi_interfaces import IBeliefManager, IDesireManager, IIntentionPlanner
from .action_interfaces import IActionExecutor
from .visualization_interfaces import IVisualizationClient

__all__ = [
    'IEnvironmentClient',
    'IDeviceController',
    'IBeliefManager',
    'IDesireManager',
    'IIntentionPlanner',
    'IActionExecutor',
    'IVisualizationClient'
]

