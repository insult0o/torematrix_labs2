"""
Persistence backends for state management.

Provides multiple storage backends for saving and loading application state:
- JSON file-based persistence
- SQLite database persistence  
- Redis in-memory persistence

All backends implement the common PersistenceBackend interface.
"""

from .base import PersistenceBackend, PersistenceConfig, PersistenceMiddleware
from .json_backend import JSONPersistenceBackend
from .sqlite_backend import SQLitePersistenceBackend
from .redis_backend import RedisPersistenceBackend

__all__ = [
    "PersistenceBackend",
    "PersistenceConfig", 
    "PersistenceMiddleware",
    "JSONPersistenceBackend",
    "SQLitePersistenceBackend",
    "RedisPersistenceBackend",
]