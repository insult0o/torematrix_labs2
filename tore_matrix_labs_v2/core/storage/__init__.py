#!/usr/bin/env python3
"""
Storage module for TORE Matrix Labs V2

This module provides the storage layer with repository pattern implementation,
replacing the scattered storage logic from the original codebase.

Key improvements:
- Repository pattern for clean data access
- Abstracted storage interfaces
- Migration support for .tore files
- Transaction support
- Performance optimization
- Comprehensive error handling

Storage components:
- RepositoryBase: Abstract base for all repositories
- DocumentRepository: Document storage and retrieval
- AreaRepository: Visual area storage and management
- MigrationManager: .tore file migration and compatibility
"""

from .repository_base import RepositoryBase, StorageTransaction
from .document_repository import DocumentRepository
from .area_repository import AreaRepository
from .migration_manager import MigrationManager

__all__ = [
    "RepositoryBase",
    "StorageTransaction",
    "DocumentRepository", 
    "AreaRepository",
    "MigrationManager"
]