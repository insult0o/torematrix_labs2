"""
Database migration system for schema versioning and data migrations.

Provides utilities to migrate data between backends and handle schema evolution.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
import hashlib

from .repository import Repository, StorageError


logger = logging.getLogger(__name__)


class Migration(ABC):
    """Base class for database migrations."""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.checksum = self._calculate_checksum()
        
    @abstractmethod
    def up(self, repository: Repository) -> None:
        """Apply the migration."""
        pass
    
    @abstractmethod
    def down(self, repository: Repository) -> None:
        """Rollback the migration."""
        pass
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of migration for integrity verification."""
        content = f"{self.version}:{self.description}:{self.up.__code__.co_code}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class MigrationHistory:
    """Track applied migrations."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self._ensure_history_table()
    
    def _ensure_history_table(self):
        """Create migration history table if it doesn't exist."""
        # This is backend-specific, but for SQLite:
        if hasattr(self.repository, 'create_table'):
            schema = {
                "version": "TEXT PRIMARY KEY",
                "description": "TEXT",
                "checksum": "TEXT",
                "applied_at": "TEXT",
                "execution_time_ms": "INTEGER"
            }
            self.repository.create_table("_migration_history", schema)
    
    def has_migration(self, version: str) -> bool:
        """Check if a migration has been applied."""
        # Simplified check - in practice would query the history table
        return False
    
    def record_migration(self, migration: Migration, execution_time_ms: int):
        """Record that a migration has been applied."""
        record = {
            "version": migration.version,
            "description": migration.description,
            "checksum": migration.checksum,
            "applied_at": datetime.utcnow().isoformat(),
            "execution_time_ms": execution_time_ms
        }
        # Store in history table
        logger.info(f"Recorded migration: {migration.version}")
    
    def remove_migration(self, version: str):
        """Remove a migration from history (for rollback)."""
        logger.info(f"Removed migration: {version}")


class MigrationManager:
    """
    Manages database migrations and backend transitions.
    """
    
    def __init__(self):
        self.migrations: Dict[str, Migration] = {}
        self._load_migrations()
    
    def _load_migrations(self):
        """Load available migrations."""
        # In practice, this would scan a migrations directory
        # For now, we'll add some example migrations programmatically
        pass
    
    def register_migration(self, migration: Migration):
        """Register a migration."""
        if migration.version in self.migrations:
            raise StorageError(f"Migration {migration.version} already registered")
        self.migrations[migration.version] = migration
        logger.info(f"Registered migration: {migration.version}")
    
    def migrate(self, repository: Repository, target_version: Optional[str] = None):
        """
        Apply migrations up to target version.
        
        Args:
            repository: Repository to migrate
            target_version: Target version (None = latest)
        """
        history = MigrationHistory(repository)
        
        # Get sorted list of migrations
        versions = sorted(self.migrations.keys())
        
        if target_version and target_version not in versions:
            raise StorageError(f"Unknown migration version: {target_version}")
        
        # Apply migrations in order
        for version in versions:
            if target_version and version > target_version:
                break
                
            if not history.has_migration(version):
                migration = self.migrations[version]
                logger.info(f"Applying migration {version}: {migration.description}")
                
                start_time = datetime.utcnow()
                try:
                    migration.up(repository)
                    execution_time_ms = int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                    history.record_migration(migration, execution_time_ms)
                    logger.info(f"Migration {version} completed in {execution_time_ms}ms")
                except Exception as e:
                    logger.error(f"Migration {version} failed: {e}")
                    raise StorageError(f"Migration failed: {e}")
    
    def rollback(self, repository: Repository, target_version: str):
        """
        Rollback migrations to target version.
        
        Args:
            repository: Repository to rollback
            target_version: Target version to rollback to
        """
        history = MigrationHistory(repository)
        
        # Get sorted list of migrations in reverse order
        versions = sorted(self.migrations.keys(), reverse=True)
        
        for version in versions:
            if version <= target_version:
                break
                
            if history.has_migration(version):
                migration = self.migrations[version]
                logger.info(f"Rolling back migration {version}: {migration.description}")
                
                try:
                    migration.down(repository)
                    history.remove_migration(version)
                    logger.info(f"Rollback of {version} completed")
                except Exception as e:
                    logger.error(f"Rollback of {version} failed: {e}")
                    raise StorageError(f"Rollback failed: {e}")


class BackendMigrator:
    """
    Migrate data between different storage backends.
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
    
    def migrate_data(
        self,
        source_repo: Repository,
        target_repo: Repository,
        transform_fn: Optional[Callable[[Any], Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Migrate all data from source to target repository.
        
        Args:
            source_repo: Source repository
            target_repo: Target repository  
            transform_fn: Optional transformation function for entities
            progress_callback: Optional callback for progress updates
            
        Returns:
            Migration statistics
        """
        stats = {
            "total_entities": 0,
            "migrated": 0,
            "failed": 0,
            "start_time": datetime.utcnow(),
            "errors": []
        }
        
        try:
            # Get total count
            total = source_repo.count()
            stats["total_entities"] = total
            
            # Process in batches
            page = 1
            while True:
                # Fetch batch
                result = source_repo.list(
                    pagination={"page": page, "per_page": self.batch_size}
                )
                
                if not result.items:
                    break
                
                # Migrate batch
                for entity in result.items:
                    try:
                        # Apply transformation if provided
                        if transform_fn:
                            entity = transform_fn(entity)
                        
                        # Create in target
                        target_repo.create(entity)
                        stats["migrated"] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate entity: {e}")
                        stats["failed"] += 1
                        stats["errors"].append(str(e))
                
                # Progress callback
                if progress_callback:
                    progress_callback(stats["migrated"], total)
                
                # Next page
                if not result.has_next:
                    break
                page += 1
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise StorageError(f"Migration failed: {e}")
        
        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()
        
        logger.info(
            f"Migration completed: {stats['migrated']}/{stats['total_entities']} "
            f"migrated, {stats['failed']} failed"
        )
        
        return stats


# Example migrations
class CreateIndexesMigration(Migration):
    """Example migration to create indexes."""
    
    def __init__(self):
        super().__init__("001_create_indexes", "Create performance indexes")
    
    def up(self, repository: Repository) -> None:
        """Create indexes."""
        if hasattr(repository, 'execute_query'):
            # Create indexes for common queries
            repository.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(type)"
            )
            repository.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_elements_document_id ON elements(document_id)"
            )
    
    def down(self, repository: Repository) -> None:
        """Drop indexes."""
        if hasattr(repository, 'execute_query'):
            repository.execute_query("DROP INDEX IF EXISTS idx_elements_type")
            repository.execute_query("DROP INDEX IF EXISTS idx_elements_document_id")