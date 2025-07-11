#!/usr/bin/env python3
"""
Repository Base for TORE Matrix Labs V2

This module provides the abstract base repository and transaction support
for the storage layer, implementing clean data access patterns.

Key improvements:
- Repository pattern for testable data access
- Transaction support for data consistency
- Abstract interfaces for multiple storage backends
- Performance optimization with connection pooling
- Comprehensive error handling and logging
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Type, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import json
import sqlite3
import threading
from enum import Enum

# Generic type for repository entities
T = TypeVar('T')


class StorageBackend(Enum):
    """Supported storage backends."""
    JSON_FILE = "json_file"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


@dataclass
class StorageConfig:
    """Configuration for storage backend."""
    
    backend: StorageBackend = StorageBackend.JSON_FILE
    connection_string: str = ""
    database_path: Optional[Path] = None
    
    # Performance settings
    enable_caching: bool = True
    cache_size: int = 1000
    connection_timeout: int = 30
    
    # Transaction settings
    auto_commit: bool = True
    isolation_level: str = "READ_COMMITTED"
    
    # JSON file settings
    backup_enabled: bool = True
    backup_count: int = 5


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class TransactionError(StorageError):
    """Exception for transaction operations."""
    pass


class StorageTransaction:
    """
    Storage transaction for atomic operations.
    
    Provides ACID properties for storage operations across different backends.
    """
    
    def __init__(self, repository: 'RepositoryBase'):
        """Initialize transaction."""
        self.repository = repository
        self.transaction_id = f"txn_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.operations: List[Dict[str, Any]] = []
        self.is_active = False
        self.is_committed = False
        self.is_rolled_back = False
        
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        """Enter transaction context."""
        self.begin()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
        else:
            # No exception, commit
            self.commit()
    
    def begin(self):
        """Begin the transaction."""
        if self.is_active:
            raise TransactionError("Transaction is already active")
        
        self.is_active = True
        self.repository._begin_transaction(self)
        self.logger.debug(f"Transaction began: {self.transaction_id}")
    
    def commit(self):
        """Commit the transaction."""
        if not self.is_active:
            raise TransactionError("No active transaction to commit")
        
        if self.is_committed or self.is_rolled_back:
            raise TransactionError("Transaction already finalized")
        
        try:
            self.repository._commit_transaction(self)
            self.is_committed = True
            self.is_active = False
            self.logger.debug(f"Transaction committed: {self.transaction_id}")
            
        except Exception as e:
            self.logger.error(f"Transaction commit failed: {str(e)}")
            self.rollback()
            raise TransactionError(f"Commit failed: {str(e)}") from e
    
    def rollback(self):
        """Rollback the transaction."""
        if not self.is_active:
            return  # Nothing to rollback
        
        try:
            self.repository._rollback_transaction(self)
            self.is_rolled_back = True
            self.is_active = False
            self.logger.debug(f"Transaction rolled back: {self.transaction_id}")
            
        except Exception as e:
            self.logger.error(f"Transaction rollback failed: {str(e)}")
            raise TransactionError(f"Rollback failed: {str(e)}") from e
    
    def add_operation(self, operation_type: str, data: Dict[str, Any]):
        """Add an operation to the transaction."""
        if not self.is_active:
            raise TransactionError("No active transaction")
        
        operation = {
            "type": operation_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.operations.append(operation)


class RepositoryBase(ABC, Generic[T]):
    """
    Abstract base class for repositories.
    
    Provides common repository functionality with support for different
    storage backends and transaction management.
    """
    
    def __init__(self, 
                 config: StorageConfig,
                 entity_type: Type[T]):
        """Initialize repository."""
        self.config = config
        self.entity_type = entity_type
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Connection management
        self._connection = None
        self._connection_lock = threading.Lock()
        
        # Transaction management
        self._active_transactions: Dict[str, StorageTransaction] = {}
        
        # Caching
        self._cache: Dict[str, T] = {}
        self._cache_enabled = config.enable_caching
        
        # Performance statistics
        self.stats = {
            "operations_performed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "transactions_committed": 0,
            "transactions_rolled_back": 0
        }
        
        self._initialize_storage()
        self.logger.info(f"{self.__class__.__name__} initialized with {config.backend.value} backend")
    
    @abstractmethod
    def create(self, entity: T, transaction: Optional[StorageTransaction] = None) -> str:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            transaction: Optional transaction
            
        Returns:
            ID of created entity
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: ID of entity to retrieve
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update(self, entity: T, transaction: Optional[StorageTransaction] = None) -> bool:
        """
        Update an existing entity.
        
        Args:
            entity: Entity to update
            transaction: Optional transaction
            
        Returns:
            True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str, transaction: Optional[StorageTransaction] = None) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: ID of entity to delete
            transaction: Optional transaction
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        List all entities.
        
        Args:
            limit: Optional limit on number of entities
            offset: Offset for pagination
            
        Returns:
            List of entities
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count total number of entities.
        
        Returns:
            Total count
        """
        pass
    
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """
        Find entities matching criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching entities
        """
        # Default implementation - subclasses should override for efficiency
        all_entities = self.list_all()
        
        matching = []
        for entity in all_entities:
            if self._matches_criteria(entity, criteria):
                matching.append(entity)
        
        return matching
    
    def exists(self, entity_id: str) -> bool:
        """
        Check if entity exists.
        
        Args:
            entity_id: ID to check
            
        Returns:
            True if entity exists, False otherwise
        """
        return self.get_by_id(entity_id) is not None
    
    def transaction(self) -> StorageTransaction:
        """
        Create a new transaction.
        
        Returns:
            New transaction instance
        """
        return StorageTransaction(self)
    
    def clear_cache(self):
        """Clear the entity cache."""
        if self._cache_enabled:
            self._cache.clear()
            self.logger.debug("Entity cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return {
            **self.stats,
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "active_transactions": len(self._active_transactions)
        }
    
    def _initialize_storage(self):
        """Initialize storage backend."""
        if self.config.backend == StorageBackend.JSON_FILE:
            self._initialize_json_storage()
        elif self.config.backend == StorageBackend.SQLITE:
            self._initialize_sqlite_storage()
        else:
            raise StorageError(f"Unsupported backend: {self.config.backend}")
    
    def _initialize_json_storage(self):
        """Initialize JSON file storage."""
        if self.config.database_path:
            self.config.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file if it doesn't exist
            if not self.config.database_path.exists():
                with open(self.config.database_path, 'w') as f:
                    json.dump({}, f)
        else:
            raise StorageError("database_path required for JSON storage")
    
    def _initialize_sqlite_storage(self):
        """Initialize SQLite storage."""
        if not self.config.database_path:
            raise StorageError("database_path required for SQLite storage")
        
        # Create database file and tables
        with sqlite3.connect(str(self.config.database_path)) as conn:
            self._create_tables(conn)
    
    @abstractmethod
    def _create_tables(self, connection):
        """Create database tables (for SQL backends)."""
        pass
    
    def _get_connection(self):
        """Get database connection (thread-safe)."""
        with self._connection_lock:
            if self._connection is None:
                if self.config.backend == StorageBackend.SQLITE:
                    self._connection = sqlite3.connect(
                        str(self.config.database_path),
                        timeout=self.config.connection_timeout,
                        check_same_thread=False
                    )
                    self._connection.row_factory = sqlite3.Row
                else:
                    # For JSON backend, connection is file path
                    self._connection = self.config.database_path
            
            return self._connection
    
    def _close_connection(self):
        """Close database connection."""
        with self._connection_lock:
            if self._connection and self.config.backend == StorageBackend.SQLITE:
                self._connection.close()
                self._connection = None
    
    def _cache_get(self, entity_id: str) -> Optional[T]:
        """Get entity from cache."""
        if not self._cache_enabled:
            return None
        
        if entity_id in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[entity_id]
        
        self.stats["cache_misses"] += 1
        return None
    
    def _cache_put(self, entity_id: str, entity: T):
        """Put entity in cache."""
        if self._cache_enabled:
            self._cache[entity_id] = entity
            
            # Implement simple LRU by removing oldest if cache is full
            if len(self._cache) > self.config.cache_size:
                # Remove first item (oldest)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
    
    def _cache_remove(self, entity_id: str):
        """Remove entity from cache."""
        if self._cache_enabled and entity_id in self._cache:
            del self._cache[entity_id]
    
    def _matches_criteria(self, entity: T, criteria: Dict[str, Any]) -> bool:
        """Check if entity matches search criteria."""
        for key, value in criteria.items():
            if not hasattr(entity, key):
                return False
            
            entity_value = getattr(entity, key)
            
            # Handle different comparison types
            if isinstance(value, dict):
                # Complex criteria (e.g., {"$gt": 10, "$lt": 20})
                for op, op_value in value.items():
                    if op == "$gt" and not (entity_value > op_value):
                        return False
                    elif op == "$lt" and not (entity_value < op_value):
                        return False
                    elif op == "$eq" and not (entity_value == op_value):
                        return False
                    elif op == "$ne" and not (entity_value != op_value):
                        return False
                    elif op == "$in" and entity_value not in op_value:
                        return False
            else:
                # Simple equality check
                if entity_value != value:
                    return False
        
        return True
    
    def _begin_transaction(self, transaction: StorageTransaction):
        """Begin a transaction (backend-specific implementation)."""
        self._active_transactions[transaction.transaction_id] = transaction
        
        if self.config.backend == StorageBackend.SQLITE:
            connection = self._get_connection()
            connection.execute("BEGIN")
    
    def _commit_transaction(self, transaction: StorageTransaction):
        """Commit a transaction (backend-specific implementation)."""
        if transaction.transaction_id not in self._active_transactions:
            raise TransactionError("Transaction not found")
        
        if self.config.backend == StorageBackend.SQLITE:
            connection = self._get_connection()
            connection.commit()
        
        # Remove from active transactions
        del self._active_transactions[transaction.transaction_id]
        self.stats["transactions_committed"] += 1
    
    def _rollback_transaction(self, transaction: StorageTransaction):
        """Rollback a transaction (backend-specific implementation)."""
        if transaction.transaction_id not in self._active_transactions:
            return  # Transaction not found, nothing to rollback
        
        if self.config.backend == StorageBackend.SQLITE:
            connection = self._get_connection()
            connection.rollback()
        
        # Remove from active transactions
        del self._active_transactions[transaction.transaction_id]
        self.stats["transactions_rolled_back"] += 1
    
    def _update_stats(self):
        """Update operation statistics."""
        self.stats["operations_performed"] += 1
    
    def __del__(self):
        """Cleanup when repository is destroyed."""
        try:
            self._close_connection()
        except:
            pass  # Ignore cleanup errors