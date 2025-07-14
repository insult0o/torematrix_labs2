"""
Storage layer for TORE Matrix Labs V3.

Provides multi-backend storage support with a consistent repository interface.
"""

# Core repository interfaces
from .repository import (
    Repository, AsyncRepository, QueryFilter, Pagination, 
    PaginatedResult, SortOrder, StorageError, NotFoundError, 
    DuplicateError, TransactionError
)

# Backend implementations
from .base_backend import BaseBackend, BackendConfig
from .sqlite_backend import SQLiteBackend, SQLiteRepository, SQLiteConfig

# Optional backends (may not be available if dependencies aren't installed)
_optional_imports = {}

try:
    from .postgres_backend import PostgreSQLBackend, PostgreSQLRepository, PostgreSQLConfig
    _optional_imports.update({
        'PostgreSQLBackend': PostgreSQLBackend,
        'PostgreSQLRepository': PostgreSQLRepository,
        'PostgreSQLConfig': PostgreSQLConfig
    })
except ImportError:
    # PostgreSQL dependencies not available
    pass

try:
    from .mongodb_backend import MongoDBBackend, MongoDBRepository, MongoDBConfig
    _optional_imports.update({
        'MongoDBBackend': MongoDBBackend,
        'MongoDBRepository': MongoDBRepository,
        'MongoDBConfig': MongoDBConfig
    })
except ImportError:
    # MongoDB dependencies not available
    pass

# Migration system
from .migrations import (
    Migration, MigrationManager, MigrationHistory, BackendMigrator,
    CreateIndexesMigration
)

# Factory
from .factory import StorageFactory, StorageBackend

# Build __all__ dynamically based on available imports
__all__ = [
    # Repository interfaces
    "Repository",
    "AsyncRepository",
    "QueryFilter",
    "Pagination", 
    "PaginatedResult",
    "SortOrder",
    
    # Exceptions
    "StorageError",
    "NotFoundError",
    "DuplicateError", 
    "TransactionError",
    
    # Base classes
    "BaseBackend",
    "BackendConfig",
    
    # SQLite backend (always available)
    "SQLiteBackend",
    "SQLiteRepository", 
    "SQLiteConfig",
    
    # Migration system
    "Migration",
    "MigrationManager",
    "MigrationHistory",
    "BackendMigrator",
    "CreateIndexesMigration",
    
    # Factory
    "StorageFactory",
    "StorageBackend",
]

# Add optional imports to __all__ and globals
for name, cls in _optional_imports.items():
    __all__.append(name)
    globals()[name] = cls


def __getattr__(name):
    """Handle dynamic attribute access for optional backends."""
    if name in _optional_imports:
        return _optional_imports[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")