"""
Base backend implementation with common functionality.

Provides shared utilities and default implementations for storage backends.
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar, List
from contextlib import contextmanager
from datetime import datetime
import json
import uuid
from pathlib import Path

from .repository import (
    Repository, AsyncRepository, StorageError, 
    NotFoundError, DuplicateError, TransactionError
)


logger = logging.getLogger(__name__)
T = TypeVar('T')


class BackendConfig:
    """Configuration base for storage backends."""
    
    def __init__(self, **kwargs):
        self.connection_retries = kwargs.get('connection_retries', 3)
        self.connection_timeout = kwargs.get('connection_timeout', 30)
        self.pool_size = kwargs.get('pool_size', 10)
        self.echo_sql = kwargs.get('echo_sql', False)
        self.compression_enabled = kwargs.get('compression_enabled', True)
        self.backup_enabled = kwargs.get('backup_enabled', True)
        self.backup_path = kwargs.get('backup_path', Path('./backups'))
        
        # Store additional backend-specific config
        self.extra = {k: v for k, v in kwargs.items() 
                     if k not in self.__dict__}


class BaseBackend:
    """
    Base class for storage backend implementations.
    
    Provides common functionality like connection management,
    serialization, and error handling.
    """
    
    def __init__(self, config: BackendConfig):
        self.config = config
        self._connection = None
        self._in_transaction = False
        
    @property
    def backend_name(self) -> str:
        """Return backend name for logging."""
        return self.__class__.__name__
    
    def connect(self) -> None:
        """
        Establish connection to the backend.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
    
    def disconnect(self) -> None:
        """
        Close connection to the backend.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
    
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connection is not None
    
    @contextmanager
    def ensure_connected(self):
        """Context manager to ensure connection is established."""
        was_connected = self.is_connected()
        
        if not was_connected:
            self.connect()
            
        try:
            yield
        finally:
            if not was_connected:
                self.disconnect()
    
    def serialize_entity(self, entity: T) -> Dict[str, Any]:
        """
        Serialize entity to dictionary for storage.
        
        Handles dataclasses, pydantic models, and regular classes.
        """
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        elif hasattr(entity, 'dict'):  # Pydantic
            return entity.dict()
        elif hasattr(entity, '__dict__'):
            return {
                k: v for k, v in entity.__dict__.items()
                if not k.startswith('_')
            }
        else:
            raise StorageError(f"Cannot serialize entity of type {type(entity)}")
    
    def deserialize_entity(self, data: Dict[str, Any], entity_class: Type[T]) -> T:
        """
        Deserialize dictionary to entity instance.
        
        Handles dataclasses, pydantic models, and regular classes.
        """
        if hasattr(entity_class, 'from_dict'):
            return entity_class.from_dict(data)
        elif hasattr(entity_class, 'parse_obj'):  # Pydantic
            return entity_class.parse_obj(data)
        else:
            # Try to instantiate with dict unpacking
            try:
                return entity_class(**data)
            except Exception as e:
                raise StorageError(
                    f"Cannot deserialize data to {entity_class}: {e}"
                )
    
    def generate_id(self) -> str:
        """Generate unique identifier."""
        return str(uuid.uuid4())
    
    def add_timestamps(self, data: Dict[str, Any], update: bool = False) -> Dict[str, Any]:
        """Add created_at/updated_at timestamps."""
        now = datetime.utcnow().isoformat()
        
        if not update and 'created_at' not in data:
            data['created_at'] = now
            
        data['updated_at'] = now
        return data
    
    def validate_id(self, entity_id: str) -> bool:
        """Validate entity ID format."""
        if not entity_id or not isinstance(entity_id, str):
            return False
            
        # Check if it's a valid UUID
        try:
            uuid.UUID(entity_id)
            return True
        except ValueError:
            # Allow non-UUID strings for flexibility
            return len(entity_id) > 0 and len(entity_id) < 256
    
    def handle_storage_error(self, operation: str, error: Exception) -> None:
        """
        Log and re-raise storage errors with context.
        """
        logger.error(
            f"Storage error in {self.backend_name}.{operation}: {error}",
            exc_info=True
        )
        
        # Convert specific errors to our exception types
        error_msg = str(error).lower()
        
        if 'not found' in error_msg or '404' in error_msg:
            raise NotFoundError(f"{operation} failed: {error}")
        elif 'duplicate' in error_msg or 'already exists' in error_msg:
            raise DuplicateError(f"{operation} failed: {error}")
        elif 'transaction' in error_msg or 'rollback' in error_msg:
            raise TransactionError(f"{operation} failed: {error}")
        else:
            raise StorageError(f"{operation} failed: {error}")
    
    def create_backup(self, collection_name: str) -> Path:
        """
        Create backup of a collection/table.
        Must be implemented by subclasses if backup is supported.
        """
        if not self.config.backup_enabled:
            return None
            
        raise NotImplementedError(
            f"Backup not implemented for {self.backend_name}"
        )
    
    def restore_backup(self, backup_path: Path, collection_name: str) -> None:
        """
        Restore collection/table from backup.
        Must be implemented by subclasses if backup is supported.
        """
        if not self.config.backup_enabled:
            return
            
        raise NotImplementedError(
            f"Restore not implemented for {self.backend_name}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get backend statistics (connections, performance, etc).
        Can be overridden by subclasses.
        """
        return {
            'backend': self.backend_name,
            'connected': self.is_connected(),
            'in_transaction': self._in_transaction,
            'config': {
                'pool_size': self.config.pool_size,
                'compression': self.config.compression_enabled,
                'backup': self.config.backup_enabled
            }
        }