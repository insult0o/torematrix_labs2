"""
TORE Matrix V3 Integration Module

This module provides the glue code that connects all components together
into a cohesive document processing system.
"""

from .system import ToreMatrixSystem, SystemConfig, SystemStatus, create_system
from .coordinator import EventFlowCoordinator
from .transformer import DataTransformer, ElementTransformer
from .adapters import (
    EventBusAdapter,
    StorageAdapter,
    StateAdapter,
    ConfigAdapter
)

__all__ = [
    # Main system
    "ToreMatrixSystem",
    "SystemConfig", 
    "SystemStatus",
    "create_system",
    
    # Coordinators
    "EventFlowCoordinator",
    
    # Transformers
    "DataTransformer",
    "ElementTransformer",
    
    # Adapters
    "EventBusAdapter",
    "StorageAdapter",
    "StateAdapter",
    "ConfigAdapter"
]

__version__ = "3.0.0"