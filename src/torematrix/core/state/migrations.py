"""
State migration utilities.

This module provides utilities for migrating state data between different
versions and schemas.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of migrations."""
    SCHEMA_CHANGE = "schema_change"
    DATA_TRANSFORM = "data_transform"
    VERSION_UPGRADE = "version_upgrade"
    FORMAT_CHANGE = "format_change"


@dataclass
class MigrationInfo:
    """Information about a migration."""
    id: str
    name: str
    description: str
    from_version: str
    to_version: str
    migration_type: MigrationType
    required: bool = True
    reversible: bool = False


class StateMigration(ABC):
    """Abstract base class for state migrations."""
    
    @property
    @abstractmethod
    def info(self) -> MigrationInfo:
        """Get migration information."""
        pass
    
    @abstractmethod
    def migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the migration to state."""
        pass
    
    def can_migrate(self, state: Dict[str, Any]) -> bool:
        """Check if this migration can be applied to the state."""
        # Default implementation checks version
        current_version = state.get("_meta", {}).get("version", "0.0.0")
        return self._version_matches(current_version, self.info.from_version)
    
    def reverse_migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse the migration (if supported)."""
        if not self.info.reversible:
            raise NotImplementedError(f"Migration {self.info.id} is not reversible")
        raise NotImplementedError("Reverse migration not implemented")
    
    def _version_matches(self, current: str, target: str) -> bool:
        """Check if current version matches target pattern."""
        if target == "*":
            return True
        if "." in target and "x" in target:
            # Pattern like "1.x.x" or "1.2.x"
            pattern = target.replace("x", r"\d+")
            return bool(re.match(f"^{pattern}$", current))
        return current == target


class StateMigrator:
    """
    State migration manager.
    
    Manages and applies state migrations to ensure compatibility
    across different versions.
    """
    
    def __init__(self):
        self._migrations: Dict[str, StateMigration] = {}
        self._migration_order: List[str] = []
        self._version_history: List[str] = []
    
    def register_migration(self, migration: StateMigration) -> None:
        """Register a migration."""
        migration_id = migration.info.id
        
        if migration_id in self._migrations:
            logger.warning(f"Migration {migration_id} already registered, overwriting")
        
        self._migrations[migration_id] = migration
        
        # Insert in order based on version
        self._insert_migration_ordered(migration_id)
        
        logger.debug(f"Registered migration: {migration_id}")
    
    def migrate_state(
        self,
        state: Dict[str, Any],
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Migrate state to target version.
        
        Args:
            state: State to migrate
            target_version: Target version, or None for latest
            
        Returns:
            Migrated state
        """
        current_state = state.copy()
        current_version = self._get_state_version(current_state)
        
        if target_version is None:
            target_version = self._get_latest_version()
        
        logger.info(f"Migrating state from {current_version} to {target_version}")
        
        # Find applicable migrations
        applicable_migrations = self._find_migration_path(current_version, target_version)
        
        if not applicable_migrations:
            logger.debug("No migrations needed")
            return current_state
        
        # Apply migrations in order
        for migration_id in applicable_migrations:
            migration = self._migrations[migration_id]
            
            if not migration.can_migrate(current_state):
                if migration.info.required:
                    raise ValueError(
                        f"Required migration {migration_id} cannot be applied to current state"
                    )
                else:
                    logger.warning(f"Skipping optional migration {migration_id}")
                    continue
            
            logger.debug(f"Applying migration: {migration_id}")
            
            try:
                current_state = migration.migrate(current_state)
                
                # Update version in state
                if "_meta" not in current_state:
                    current_state["_meta"] = {}
                current_state["_meta"]["version"] = migration.info.to_version
                current_state["_meta"]["last_migration"] = migration_id
                
            except Exception as e:
                logger.error(f"Migration {migration_id} failed: {e}")
                raise
        
        logger.info(f"State migration completed: {current_version} -> {target_version}")
        return current_state
    
    def can_migrate_to(self, state: Dict[str, Any], target_version: str) -> bool:
        """Check if state can be migrated to target version."""
        current_version = self._get_state_version(state)
        migration_path = self._find_migration_path(current_version, target_version)
        
        # Check if all required migrations can be applied
        for migration_id in migration_path:
            migration = self._migrations[migration_id]
            if migration.info.required and not migration.can_migrate(state):
                return False
        
        return True
    
    def get_migration_info(self, migration_id: str) -> Optional[MigrationInfo]:
        """Get information about a migration."""
        if migration_id in self._migrations:
            return self._migrations[migration_id].info
        return None
    
    def list_migrations(self) -> List[MigrationInfo]:
        """List all registered migrations."""
        return [migration.info for migration in self._migrations.values()]
    
    def get_migration_path(
        self,
        from_version: str,
        to_version: str
    ) -> List[MigrationInfo]:
        """Get the migration path between two versions."""
        migration_ids = self._find_migration_path(from_version, to_version)
        return [self._migrations[mid].info for mid in migration_ids]
    
    # Private methods
    
    def _get_state_version(self, state: Dict[str, Any]) -> str:
        """Get version from state metadata."""
        return state.get("_meta", {}).get("version", "0.0.0")
    
    def _get_latest_version(self) -> str:
        """Get the latest version from registered migrations."""
        if not self._migrations:
            return "0.0.0"
        
        latest = "0.0.0"
        for migration in self._migrations.values():
            if self._compare_versions(migration.info.to_version, latest) > 0:
                latest = migration.info.to_version
        
        return latest
    
    def _find_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """Find the migration path between two versions."""
        if from_version == to_version:
            return []
        
        # Simple implementation - apply migrations in order
        # A more sophisticated implementation would use graph algorithms
        path = []
        current_version = from_version
        
        while current_version != to_version:
            found_migration = None
            
            for migration_id in self._migration_order:
                migration = self._migrations[migration_id]
                
                if (migration.info.from_version == current_version or
                    migration.info.from_version == "*"):
                    
                    # Check if this migration moves us toward target
                    if (self._compare_versions(migration.info.to_version, current_version) > 0 and
                        self._compare_versions(migration.info.to_version, to_version) <= 0):
                        
                        found_migration = migration
                        break
            
            if found_migration is None:
                raise ValueError(
                    f"No migration path found from {from_version} to {to_version}"
                )
            
            path.append(found_migration.info.id)
            current_version = found_migration.info.to_version
        
        return path
    
    def _insert_migration_ordered(self, migration_id: str) -> None:
        """Insert migration in correct order."""
        migration = self._migrations[migration_id]
        
        # Remove if already present
        if migration_id in self._migration_order:
            self._migration_order.remove(migration_id)
        
        # Find correct position
        insert_pos = len(self._migration_order)
        
        for i, existing_id in enumerate(self._migration_order):
            existing = self._migrations[existing_id]
            
            # Insert before migrations with higher from_version
            if self._compare_versions(migration.info.from_version, 
                                   existing.info.from_version) < 0:
                insert_pos = i
                break
        
        self._migration_order.insert(insert_pos, migration_id)
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        def parse_version(v):
            try:
                return tuple(map(int, v.split('.')))
            except ValueError:
                # Handle non-numeric versions
                return (0, 0, 0)
        
        parsed_v1 = parse_version(v1)
        parsed_v2 = parse_version(v2)
        
        if parsed_v1 < parsed_v2:
            return -1
        elif parsed_v1 > parsed_v2:
            return 1
        else:
            return 0


# Example migrations

class InitialStateMigration(StateMigration):
    """Migration to initialize state metadata."""
    
    @property
    def info(self) -> MigrationInfo:
        return MigrationInfo(
            id="initial_state",
            name="Initialize State",
            description="Add initial metadata to state",
            from_version="*",
            to_version="1.0.0",
            migration_type=MigrationType.SCHEMA_CHANGE,
            required=False
        )
    
    def migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata if not present."""
        if "_meta" not in state:
            state["_meta"] = {
                "version": "1.0.0",
                "created_at": None,
                "schema_version": 1
            }
        return state


class ElementsListMigration(StateMigration):
    """Migration to convert elements dict to list."""
    
    @property
    def info(self) -> MigrationInfo:
        return MigrationInfo(
            id="elements_list",
            name="Elements Dict to List",
            description="Convert elements from dict to list format",
            from_version="1.0.0",
            to_version="1.1.0",
            migration_type=MigrationType.DATA_TRANSFORM,
            required=True,
            reversible=True
        )
    
    def migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert elements dict to list."""
        if "elements" in state and isinstance(state["elements"], dict):
            # Convert dict to list, preserving order by ID
            elements_list = []
            for element_id, element in sorted(state["elements"].items()):
                if "id" not in element:
                    element["id"] = element_id
                elements_list.append(element)
            
            state["elements"] = elements_list
        
        return state
    
    def reverse_migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert elements list back to dict."""
        if "elements" in state and isinstance(state["elements"], list):
            elements_dict = {}
            for element in state["elements"]:
                element_id = element.get("id", str(len(elements_dict)))
                elements_dict[element_id] = element
            
            state["elements"] = elements_dict
        
        return state


class DocumentMetadataMigration(StateMigration):
    """Migration to restructure document metadata."""
    
    @property
    def info(self) -> MigrationInfo:
        return MigrationInfo(
            id="document_metadata",
            name="Document Metadata Restructure",
            description="Restructure document metadata format",
            from_version="1.1.0",
            to_version="1.2.0",
            migration_type=MigrationType.SCHEMA_CHANGE,
            required=True
        )
    
    def migrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Restructure document metadata."""
        if "document" in state and "metadata" in state["document"]:
            old_metadata = state["document"]["metadata"]
            
            new_metadata = {
                "file_info": {
                    "name": old_metadata.get("filename", ""),
                    "size": old_metadata.get("file_size", 0),
                    "type": old_metadata.get("file_type", ""),
                    "path": old_metadata.get("file_path", "")
                },
                "processing_info": {
                    "parsed_at": old_metadata.get("parsed_at"),
                    "parser_version": old_metadata.get("parser_version", ""),
                    "page_count": old_metadata.get("pages", 0)
                },
                "content_info": {
                    "elements_count": len(state.get("elements", [])),
                    "has_tables": old_metadata.get("has_tables", False),
                    "has_images": old_metadata.get("has_images", False)
                }
            }
            
            state["document"]["metadata"] = new_metadata
        
        return state