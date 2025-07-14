"""
Storage factory for creating repository instances.

Provides a unified interface for creating repositories with different backends.
"""

import logging
from typing import Type, TypeVar, Dict, Any, Optional, List
from enum import Enum

from .repository import Repository, AsyncRepository
from .sqlite_backend import SQLiteRepository, SQLiteConfig
from .base_backend import BackendConfig

# Optional backend imports
_BACKEND_IMPORTS = {
    'sqlite': (SQLiteRepository, SQLiteConfig)
}

try:
    from .postgres_backend import PostgreSQLRepository, PostgreSQLConfig
    _BACKEND_IMPORTS['postgresql'] = (PostgreSQLRepository, PostgreSQLConfig)
except ImportError:
    pass

try:
    from .mongodb_backend import MongoDBRepository, MongoDBConfig
    _BACKEND_IMPORTS['mongodb'] = (MongoDBRepository, MongoDBConfig)
except ImportError:
    pass


logger = logging.getLogger(__name__)
T = TypeVar('T')


class StorageBackend(Enum):
    """Available storage backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


class StorageFactory:
    """
    Factory for creating repository instances with appropriate backends.
    
    Handles backend selection, configuration, and repository creation.
    """
    
    @classmethod
    def _get_backends(cls) -> Dict[StorageBackend, tuple]:
        """Get available backend implementations."""
        backends = {}
        
        if 'sqlite' in _BACKEND_IMPORTS:
            backends[StorageBackend.SQLITE] = _BACKEND_IMPORTS['sqlite']
        
        if 'postgresql' in _BACKEND_IMPORTS:
            backends[StorageBackend.POSTGRESQL] = _BACKEND_IMPORTS['postgresql']
            
        if 'mongodb' in _BACKEND_IMPORTS:
            backends[StorageBackend.MONGODB] = _BACKEND_IMPORTS['mongodb']
            
        return backends
    
    @classmethod
    def create_repository(
        cls,
        backend: StorageBackend,
        entity_class: Type[T],
        collection_name: str,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Repository[T]:
        """
        Create a repository instance for the specified backend.
        
        Args:
            backend: Storage backend to use
            entity_class: Class of entities to store
            collection_name: Name of collection/table
            config: Backend-specific configuration
            **kwargs: Additional configuration parameters
            
        Returns:
            Repository instance
            
        Raises:
            ValueError: If backend is not supported
        """
        backends = cls._get_backends()
        if backend not in backends:
            available = [b.value for b in backends.keys()]
            raise ValueError(f"Unsupported backend: {backend}. Available: {available}")
        
        repo_class, config_class = backends[backend]
        
        # Merge config dict with kwargs
        all_config = dict(kwargs)  # Make a copy
        if config:
            all_config.update(config)
        
        # Create configuration instance
        if backend == StorageBackend.SQLITE:
            backend_config = config_class(
                database_path=all_config.get('database_path', 'data/torematrix.db'),
                **{k: v for k, v in all_config.items() if k != 'database_path'}
            )
        elif backend == StorageBackend.POSTGRESQL:
            backend_config = config_class(
                host=all_config.get('host', 'localhost'),
                port=all_config.get('port', 5432),
                database=all_config.get('database', 'torematrix'),
                user=all_config.get('user', 'torematrix'),
                password=all_config.get('password', ''),
                **{k: v for k, v in all_config.items() 
                   if k not in ['host', 'port', 'database', 'user', 'password']}
            )
        elif backend == StorageBackend.MONGODB:
            backend_config = config_class(
                connection_string=all_config.get('connection_string', 'mongodb://localhost:27017/'),
                database=all_config.get('database', 'torematrix'),
                **{k: v for k, v in all_config.items() 
                   if k not in ['connection_string', 'database']}
            )
        else:
            backend_config = config_class(**all_config)
        
        # Create repository instance
        repository = repo_class(backend_config, entity_class, collection_name)
        
        logger.info(
            f"Created {backend.value} repository for {entity_class.__name__} "
            f"in collection '{collection_name}'"
        )
        
        return repository
    
    @classmethod
    def create_from_config(
        cls,
        config_dict: Dict[str, Any],
        entity_class: Type[T],
        collection_name: str
    ) -> Repository[T]:
        """
        Create a repository from a configuration dictionary.
        
        Args:
            config_dict: Configuration with 'backend' key and backend-specific config
            entity_class: Class of entities to store
            collection_name: Name of collection/table
            
        Returns:
            Repository instance
            
        Example config:
            {
                "backend": "sqlite",
                "database_path": "/path/to/db.sqlite",
                "enable_wal": true
            }
        """
        backend_name = config_dict.get('backend', 'sqlite').lower()
        
        try:
            backend = StorageBackend(backend_name)
        except ValueError:
            raise ValueError(f"Unknown backend: {backend_name}")
        
        # Remove backend key from config
        backend_config = {k: v for k, v in config_dict.items() if k != 'backend'}
        
        return cls.create_repository(
            backend=backend,
            entity_class=entity_class,
            collection_name=collection_name,
            config=backend_config
        )
    
    @classmethod
    def get_default_config(cls, backend: StorageBackend) -> Dict[str, Any]:
        """
        Get default configuration for a backend.
        
        Args:
            backend: Storage backend
            
        Returns:
            Default configuration dictionary
        """
        if backend == StorageBackend.SQLITE:
            return {
                "backend": "sqlite",
                "database_path": "data/torematrix.db",
                "enable_wal": True,
                "enable_foreign_keys": True,
                "backup_enabled": True
            }
        elif backend == StorageBackend.POSTGRESQL:
            return {
                "backend": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "torematrix",
                "user": "torematrix",
                "password": "",
                "pool_size": 10,
                "echo_sql": False
            }
        elif backend == StorageBackend.MONGODB:
            return {
                "backend": "mongodb",
                "connection_string": "mongodb://localhost:27017/",
                "database": "torematrix",
                "write_concern": "majority",
                "read_preference": "primary"
            }
        else:
            return {"backend": backend.value}
    
    @classmethod
    def register_backend(
        cls,
        backend: StorageBackend,
        repository_class: Type[Repository],
        config_class: Type[BackendConfig]
    ):
        """
        Register a custom backend implementation.
        
        Args:
            backend: Backend identifier
            repository_class: Repository implementation class
            config_class: Configuration class for the backend
        """
        _BACKEND_IMPORTS[backend.value] = (repository_class, config_class)
        logger.info(f"Registered backend: {backend.value}")
    
    @classmethod
    def get_available_backends(cls) -> List[StorageBackend]:
        """Get list of available backends."""
        return list(cls._get_backends().keys())


# Convenience functions
def create_sqlite_repository(
    entity_class: Type[T],
    collection_name: str,
    database_path: str = "data/torematrix.db",
    **kwargs
) -> Repository[T]:
    """Create a SQLite repository with common defaults."""
    return StorageFactory.create_repository(
        backend=StorageBackend.SQLITE,
        entity_class=entity_class,
        collection_name=collection_name,
        database_path=database_path,
        **kwargs
    )


def create_repository_from_env(
    entity_class: Type[T],
    collection_name: str
) -> Repository[T]:
    """
    Create a repository using environment variables for configuration.
    
    Environment variables:
        TOREMATRIX_STORAGE_BACKEND: Backend name (default: sqlite)
        TOREMATRIX_DATABASE_PATH: SQLite database path
        TOREMATRIX_POSTGRES_HOST: PostgreSQL host
        TOREMATRIX_POSTGRES_PORT: PostgreSQL port
        etc.
    """
    import os
    
    backend_name = os.getenv('TOREMATRIX_STORAGE_BACKEND', 'sqlite').lower()
    backend = StorageBackend(backend_name)
    
    config = {}
    
    if backend == StorageBackend.SQLITE:
        if db_path := os.getenv('TOREMATRIX_DATABASE_PATH'):
            config['database_path'] = db_path
            
    elif backend == StorageBackend.POSTGRESQL:
        if host := os.getenv('TOREMATRIX_POSTGRES_HOST'):
            config['host'] = host
        if port := os.getenv('TOREMATRIX_POSTGRES_PORT'):
            config['port'] = int(port)
        if database := os.getenv('TOREMATRIX_POSTGRES_DATABASE'):
            config['database'] = database
        if user := os.getenv('TOREMATRIX_POSTGRES_USER'):
            config['user'] = user
        if password := os.getenv('TOREMATRIX_POSTGRES_PASSWORD'):
            config['password'] = password
            
    elif backend == StorageBackend.MONGODB:
        if conn_str := os.getenv('TOREMATRIX_MONGODB_CONNECTION'):
            config['connection_string'] = conn_str
        if database := os.getenv('TOREMATRIX_MONGODB_DATABASE'):
            config['database'] = database
    
    return StorageFactory.create_repository(
        backend=backend,
        entity_class=entity_class,
        collection_name=collection_name,
        config=config
    )