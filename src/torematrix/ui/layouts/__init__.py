"""Layout management system for ToreMatrix V3.

This package provides comprehensive layout management including:
- Layout serialization and persistence
- Custom layout creation and management
- Multi-monitor support
- Layout migration and versioning
- Integration with configuration system
"""

from .serialization import (
    LayoutSerializer,
    LayoutDeserializer,
    SerializationError,
    DeserializationError,
)
from .persistence import (
    LayoutPersistence,
    LayoutConfigManager,
    PersistenceError,
)
from .custom import (
    CustomLayoutManager,
    LayoutTemplate,
    LayoutError,
)
from .migration import (
    LayoutMigrator,
    MigrationError,
    LayoutVersionManager,
)
from .multimonitor import (
    MultiMonitorManager,
    DisplayInfo,
    MonitorError,
)

__all__ = [
    # Serialization
    "LayoutSerializer",
    "LayoutDeserializer", 
    "SerializationError",
    "DeserializationError",
    
    # Persistence
    "LayoutPersistence",
    "LayoutConfigManager",
    "PersistenceError",
    
    # Custom layouts
    "CustomLayoutManager",
    "LayoutTemplate",
    "LayoutError",
    
    # Migration
    "LayoutMigrator",
    "MigrationError", 
    "LayoutVersionManager",
    
    # Multi-monitor
    "MultiMonitorManager",
    "DisplayInfo",
    "MonitorError",
]