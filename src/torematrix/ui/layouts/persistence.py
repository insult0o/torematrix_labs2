"""Layout persistence and configuration integration for ToreMatrix V3.

Provides integration with the configuration system for persistent layout storage,
restoration, and profile management.
"""

from typing import Dict, List, Optional, Any, Set, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import json
import logging
from datetime import datetime, timezone
from enum import Enum

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QScreen

from ..base import BaseUIComponent
from ...core.events import EventBus
from ...core.config import ConfigManager  
from ...core.state import StateManager
from .serialization import (
    LayoutSerializer, LayoutDeserializer, SerializedLayout,
    LayoutMetadata, SerializationError, DeserializationError
)

logger = logging.getLogger(__name__)


class PersistenceError(Exception):
    """Raised when layout persistence operations fail."""
    pass


class LayoutStorageType(Enum):
    """Layout storage types."""
    DEFAULT = "default"
    CUSTOM = "custom"
    TEMPORARY = "temporary"
    PROJECT_SPECIFIC = "project_specific"
    USER_PROFILE = "user_profile"


@dataclass
class LayoutProfile:
    """Layout profile information."""
    name: str
    description: str = ""
    storage_type: LayoutStorageType = LayoutStorageType.CUSTOM
    auto_restore: bool = True
    created: datetime = None
    last_used: datetime = None
    usage_count: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created is None:
            self.created = datetime.now(timezone.utc)
        if self.last_used is None:
            self.last_used = self.created
        if self.tags is None:
            self.tags = []


@dataclass 
class LayoutBackup:
    """Layout backup information."""
    backup_id: str
    original_name: str
    backup_timestamp: datetime
    backup_reason: str
    layout_data: str  # Serialized JSON
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LayoutConfigManager:
    """Manages layout configuration settings and preferences."""
    
    def __init__(self, config_manager: ConfigManager):
        self._config = config_manager
        self._layout_config_section = "layouts"
        
        # Ensure layout section exists
        self._ensure_layout_config()
    
    def _ensure_layout_config(self) -> None:
        """Ensure layout configuration section exists."""
        if not self._config.has_section(self._layout_config_section):
            self._config.set_section(self._layout_config_section, {
                "default_layout": None,
                "auto_restore": True,
                "backup_enabled": True,
                "backup_retention_days": 30,
                "max_custom_layouts": 50,
                "custom_layouts": {},
                "layout_profiles": {},
                "backup_layouts": {},
                "recent_layouts": [],
                "project_layouts": {},
                "user_preferences": {
                    "show_layout_preview": True,
                    "confirm_layout_deletion": True,
                    "auto_save_interval": 300,  # 5 minutes
                    "enable_layout_migration": True
                }
            })
    
    def get_default_layout(self) -> Optional[str]:
        """Get the default layout name."""
        return self._config.get(f"{self._layout_config_section}.default_layout")
    
    def set_default_layout(self, layout_name: str) -> None:
        """Set the default layout."""
        self._config.set(f"{self._layout_config_section}.default_layout", layout_name)
        logger.info(f"Set default layout to: {layout_name}")
    
    def is_auto_restore_enabled(self) -> bool:
        """Check if auto restore is enabled."""
        return self._config.get(f"{self._layout_config_section}.auto_restore", True)
    
    def set_auto_restore_enabled(self, enabled: bool) -> None:
        """Enable or disable auto restore."""
        self._config.set(f"{self._layout_config_section}.auto_restore", enabled)
    
    def is_backup_enabled(self) -> bool:
        """Check if backup is enabled."""
        return self._config.get(f"{self._layout_config_section}.backup_enabled", True)
    
    def set_backup_enabled(self, enabled: bool) -> None:
        """Enable or disable backup."""
        self._config.set(f"{self._layout_config_section}.backup_enabled", enabled)
    
    def get_backup_retention_days(self) -> int:
        """Get backup retention period in days."""
        return self._config.get(f"{self._layout_config_section}.backup_retention_days", 30)
    
    def set_backup_retention_days(self, days: int) -> None:
        """Set backup retention period."""
        self._config.set(f"{self._layout_config_section}.backup_retention_days", max(1, days))
    
    def get_max_custom_layouts(self) -> int:
        """Get maximum number of custom layouts."""
        return self._config.get(f"{self._layout_config_section}.max_custom_layouts", 50)
    
    def set_max_custom_layouts(self, max_layouts: int) -> None:
        """Set maximum number of custom layouts."""
        self._config.set(f"{self._layout_config_section}.max_custom_layouts", max(1, max_layouts))
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference value."""
        return self._config.get(f"{self._layout_config_section}.user_preferences.{key}", default)
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """Set user preference value."""
        self._config.set(f"{self._layout_config_section}.user_preferences.{key}", value)
    
    def get_recent_layouts(self) -> List[str]:
        """Get list of recently used layouts."""
        return self._config.get(f"{self._layout_config_section}.recent_layouts", [])
    
    def add_recent_layout(self, layout_name: str, max_recent: int = 10) -> None:
        """Add layout to recent list."""
        recent = self.get_recent_layouts()
        
        # Remove if already in list
        if layout_name in recent:
            recent.remove(layout_name)
        
        # Add to front
        recent.insert(0, layout_name)
        
        # Limit size
        recent = recent[:max_recent]
        
        self._config.set(f"{self._layout_config_section}.recent_layouts", recent)
    
    def get_project_layout(self, project_id: str) -> Optional[str]:
        """Get layout for specific project."""
        project_layouts = self._config.get(f"{self._layout_config_section}.project_layouts", {})
        return project_layouts.get(project_id)
    
    def set_project_layout(self, project_id: str, layout_name: str) -> None:
        """Set layout for specific project."""
        project_layouts = self._config.get(f"{self._layout_config_section}.project_layouts", {})
        project_layouts[project_id] = layout_name
        self._config.set(f"{self._layout_config_section}.project_layouts", project_layouts)


class LayoutPersistence(BaseUIComponent):
    """Manages layout persistence, storage, and restoration."""
    
    # Signals
    layout_saved = pyqtSignal(str, str)  # layout_name, storage_type
    layout_loaded = pyqtSignal(str)      # layout_name
    layout_deleted = pyqtSignal(str)     # layout_name
    backup_created = pyqtSignal(str, str) # layout_name, backup_id
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        storage_path: Optional[Path] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._config_mgr = LayoutConfigManager(config_manager)
        self._serializer = LayoutSerializer(event_bus, config_manager, state_manager)
        self._deserializer = LayoutDeserializer(event_bus, config_manager, state_manager)
        
        # Storage configuration
        self._storage_path = storage_path or Path.home() / ".torematrix" / "layouts"
        self._backup_path = self._storage_path / "backups"
        self._temp_path = self._storage_path / "temp"
        
        # Runtime state
        self._loaded_layouts: Dict[str, SerializedLayout] = {}
        self._layout_profiles: Dict[str, LayoutProfile] = {}
        self._backup_registry: Dict[str, LayoutBackup] = {}
        
        # Auto-save tracking
        self._auto_save_enabled = True
        self._last_auto_save: Optional[datetime] = None
    
    def _setup_component(self) -> None:
        """Setup the layout persistence system."""
        self._ensure_storage_directories()
        self._load_layout_profiles()
        self._load_backup_registry()
        self._setup_auto_save()
        
        # Subscribe to events
        self.subscribe_event("application.shutdown", self._on_application_shutdown)
        self.subscribe_event("layout.changed", self._on_layout_changed)
        
        logger.info("Layout persistence system initialized")
    
    def _ensure_storage_directories(self) -> None:
        """Ensure storage directories exist."""
        for path in [self._storage_path, self._backup_path, self._temp_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def save_layout(
        self,
        layout_name: str,
        root_widget: QWidget,
        description: str = "",
        storage_type: LayoutStorageType = LayoutStorageType.CUSTOM,
        overwrite: bool = False,
        create_backup: bool = True,
        displays: Optional[List[QScreen]] = None
    ) -> bool:
        """Save a layout with metadata and configuration integration."""
        try:
            # Check if layout exists and handle overwrite
            if self.layout_exists(layout_name) and not overwrite:
                raise PersistenceError(f"Layout '{layout_name}' already exists. Use overwrite=True to replace.")
            
            # Create backup if requested and layout exists
            if create_backup and self.layout_exists(layout_name):
                self._create_backup(layout_name, "before_overwrite")
            
            # Create layout metadata
            metadata = LayoutMetadata(
                name=layout_name,
                description=description,
                author=self._get_current_user(),
                modified=datetime.now(timezone.utc)
            )
            
            # Serialize layout
            serialized = self._serializer.serialize_layout(root_widget, metadata, displays)
            
            # Save to storage
            storage_file = self._get_layout_file_path(layout_name, storage_type)
            with open(storage_file, 'w', encoding='utf-8') as f:
                json_data = self._serializer._to_json(serialized)
                f.write(json_data)
            
            # Update configuration
            self._update_layout_config(layout_name, serialized, storage_type)
            
            # Update runtime state
            self._loaded_layouts[layout_name] = serialized
            
            # Update profile
            profile = self._get_or_create_profile(layout_name, storage_type)
            profile.last_used = datetime.now(timezone.utc)
            profile.usage_count += 1
            
            # Add to recent layouts
            self._config_mgr.add_recent_layout(layout_name)
            
            # Emit signal
            self.layout_saved.emit(layout_name, storage_type.value)
            
            # Publish event
            self.publish_event("layout.saved", {
                "layout_name": layout_name,
                "storage_type": storage_type.value,
                "description": description
            })
            
            logger.info(f"Saved layout '{layout_name}' as {storage_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout '{layout_name}': {e}")
            raise PersistenceError(f"Failed to save layout: {e}") from e
    
    def load_layout(
        self,
        layout_name: str,
        storage_type: Optional[LayoutStorageType] = None
    ) -> QWidget:
        """Load a layout from persistent storage."""
        try:
            # Check cache first
            if layout_name in self._loaded_layouts:
                serialized = self._loaded_layouts[layout_name]
            else:
                # Find layout file
                layout_file = self._find_layout_file(layout_name, storage_type)
                if not layout_file.exists():
                    raise PersistenceError(f"Layout '{layout_name}' not found")
                
                # Load and deserialize
                with open(layout_file, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                
                widget = self._deserializer.deserialize_from_json(json_data)
                
                # Cache the serialized version
                serialized = self._deserializer._from_dict(json.loads(json_data))
                self._loaded_layouts[layout_name] = serialized
            
            # Deserialize to widget
            widget = self._deserializer.deserialize_layout(serialized)
            
            # Update usage tracking
            profile = self._get_or_create_profile(layout_name)
            profile.last_used = datetime.now(timezone.utc)
            profile.usage_count += 1
            
            # Add to recent layouts
            self._config_mgr.add_recent_layout(layout_name)
            
            # Emit signal
            self.layout_loaded.emit(layout_name)
            
            # Publish event
            self.publish_event("layout.loaded", {
                "layout_name": layout_name
            })
            
            logger.info(f"Loaded layout '{layout_name}'")
            return widget
            
        except Exception as e:
            logger.error(f"Failed to load layout '{layout_name}': {e}")
            raise PersistenceError(f"Failed to load layout: {e}") from e
    
    def delete_layout(
        self,
        layout_name: str,
        create_backup: bool = True,
        storage_type: Optional[LayoutStorageType] = None
    ) -> bool:
        """Delete a layout from storage."""
        try:
            # Find layout file
            layout_file = self._find_layout_file(layout_name, storage_type)
            if not layout_file.exists():
                logger.warning(f"Layout '{layout_name}' not found for deletion")
                return False
            
            # Create backup if requested
            if create_backup:
                self._create_backup(layout_name, "before_deletion")
            
            # Remove file
            layout_file.unlink()
            
            # Remove from configuration
            self._remove_layout_from_config(layout_name)
            
            # Remove from runtime state
            self._loaded_layouts.pop(layout_name, None)
            self._layout_profiles.pop(layout_name, None)
            
            # Emit signal
            self.layout_deleted.emit(layout_name)
            
            # Publish event
            self.publish_event("layout.deleted", {
                "layout_name": layout_name
            })
            
            logger.info(f"Deleted layout '{layout_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete layout '{layout_name}': {e}")
            raise PersistenceError(f"Failed to delete layout: {e}") from e
    
    def list_layouts(
        self,
        storage_type: Optional[LayoutStorageType] = None,
        include_metadata: bool = False
    ) -> Union[List[str], List[Dict[str, Any]]]:
        """List available layouts."""
        layouts = []
        
        # Search in storage directory
        pattern = "*.json"
        search_paths = []
        
        if storage_type:
            search_paths.append(self._storage_path / storage_type.value)
        else:
            # Search all storage types
            for st in LayoutStorageType:
                search_paths.append(self._storage_path / st.value)
        
        for search_path in search_paths:
            if search_path.exists():
                for layout_file in search_path.glob(pattern):
                    layout_name = layout_file.stem
                    
                    if include_metadata:
                        try:
                            with open(layout_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            metadata = data.get("metadata", {})
                            profile = self._layout_profiles.get(layout_name)
                            
                            layout_info = {
                                "name": layout_name,
                                "description": metadata.get("description", ""),
                                "created": metadata.get("created"),
                                "modified": metadata.get("modified"),
                                "author": metadata.get("author", ""),
                                "storage_type": storage_type.value if storage_type else "unknown",
                                "usage_count": profile.usage_count if profile else 0,
                                "last_used": profile.last_used.isoformat() if profile and profile.last_used else None
                            }
                            layouts.append(layout_info)
                        except Exception as e:
                            logger.warning(f"Failed to read metadata for {layout_name}: {e}")
                            layouts.append({"name": layout_name, "error": str(e)})
                    else:
                        layouts.append(layout_name)
        
        return layouts
    
    def layout_exists(self, layout_name: str, storage_type: Optional[LayoutStorageType] = None) -> bool:
        """Check if a layout exists."""
        try:
            layout_file = self._find_layout_file(layout_name, storage_type)
            return layout_file.exists()
        except:
            return False
    
    def export_layout(
        self,
        layout_name: str,
        export_path: Path,
        include_metadata: bool = True
    ) -> bool:
        """Export layout to external file."""
        try:
            # Load layout data
            layout_file = self._find_layout_file(layout_name)
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = f.read()
            
            # Write to export path
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(layout_data)
            
            logger.info(f"Exported layout '{layout_name}' to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export layout '{layout_name}': {e}")
            return False
    
    def import_layout(
        self,
        import_path: Path,
        layout_name: Optional[str] = None,
        overwrite: bool = False
    ) -> bool:
        """Import layout from external file."""
        try:
            # Read layout data
            with open(import_path, 'r', encoding='utf-8') as f:
                layout_data = f.read()
            
            # Parse to validate
            data = json.loads(layout_data)
            original_name = data.get("metadata", {}).get("name", import_path.stem)
            final_name = layout_name or original_name
            
            # Check if exists
            if self.layout_exists(final_name) and not overwrite:
                raise PersistenceError(f"Layout '{final_name}' already exists")
            
            # Save to storage
            storage_file = self._get_layout_file_path(final_name, LayoutStorageType.CUSTOM)
            
            # Update name in metadata if changed
            if final_name != original_name:
                data["metadata"]["name"] = final_name
                data["metadata"]["modified"] = datetime.now(timezone.utc).isoformat()
                layout_data = json.dumps(data, indent=2)
            
            with open(storage_file, 'w', encoding='utf-8') as f:
                f.write(layout_data)
            
            # Update configuration
            serialized = self._deserializer._from_dict(data)
            self._update_layout_config(final_name, serialized, LayoutStorageType.CUSTOM)
            
            logger.info(f"Imported layout as '{final_name}' from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import layout from {import_path}: {e}")
            return False
    
    def restore_from_backup(self, layout_name: str, backup_id: str) -> bool:
        """Restore layout from backup."""
        try:
            backup = self._backup_registry.get(backup_id)
            if not backup or backup.original_name != layout_name:
                raise PersistenceError(f"Backup {backup_id} not found for layout {layout_name}")
            
            # Create current backup before restoring
            if self.layout_exists(layout_name):
                self._create_backup(layout_name, "before_restore")
            
            # Restore from backup
            storage_file = self._get_layout_file_path(layout_name, LayoutStorageType.CUSTOM)
            with open(storage_file, 'w', encoding='utf-8') as f:
                f.write(backup.layout_data)
            
            # Clear cache to force reload
            self._loaded_layouts.pop(layout_name, None)
            
            logger.info(f"Restored layout '{layout_name}' from backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore layout '{layout_name}' from backup: {e}")
            return False
    
    def cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy."""
        retention_days = self._config_mgr.get_backup_retention_days()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        removed_count = 0
        backups_to_remove = []
        
        for backup_id, backup in self._backup_registry.items():
            if backup.backup_timestamp < cutoff_date:
                backups_to_remove.append(backup_id)
        
        for backup_id in backups_to_remove:
            backup = self._backup_registry.pop(backup_id)
            backup_file = self._backup_path / f"{backup_id}.json"
            if backup_file.exists():
                backup_file.unlink()
                removed_count += 1
        
        # Save updated registry
        self._save_backup_registry()
        
        logger.info(f"Cleaned up {removed_count} old backups")
        return removed_count
    
    def get_layout_info(self, layout_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a layout."""
        try:
            layout_file = self._find_layout_file(layout_name)
            if not layout_file.exists():
                return None
            
            with open(layout_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get("metadata", {})
            profile = self._layout_profiles.get(layout_name)
            
            return {
                "name": layout_name,
                "description": metadata.get("description", ""),
                "created": metadata.get("created"),
                "modified": metadata.get("modified"),
                "author": metadata.get("author", ""),
                "version": metadata.get("version", "1.0.0"),
                "tags": metadata.get("tags", []),
                "file_path": str(layout_file),
                "file_size": layout_file.stat().st_size,
                "usage_count": profile.usage_count if profile else 0,
                "last_used": profile.last_used.isoformat() if profile and profile.last_used else None,
                "auto_restore": profile.auto_restore if profile else True
            }
            
        except Exception as e:
            logger.error(f"Failed to get info for layout '{layout_name}': {e}")
            return None
    
    def set_auto_restore_layout(self, layout_name: Optional[str]) -> None:
        """Set layout to auto-restore on application startup."""
        self._config_mgr.set_default_layout(layout_name)
        
        if layout_name:
            profile = self._get_or_create_profile(layout_name)
            profile.auto_restore = True
        
        logger.info(f"Set auto-restore layout to: {layout_name}")
    
    def auto_save_current_layout(self, root_widget: QWidget, layout_name: str = "autosave") -> bool:
        """Auto-save current layout state."""
        if not self._auto_save_enabled:
            return False
        
        try:
            auto_save_interval = self._config_mgr.get_user_preference("auto_save_interval", 300)
            now = datetime.now(timezone.utc)
            
            if (self._last_auto_save and 
                (now - self._last_auto_save).total_seconds() < auto_save_interval):
                return False
            
            # Save as temporary layout
            self.save_layout(
                layout_name,
                root_widget,
                description="Auto-saved layout",
                storage_type=LayoutStorageType.TEMPORARY,
                overwrite=True,
                create_backup=False
            )
            
            self._last_auto_save = now
            return True
            
        except Exception as e:
            logger.warning(f"Auto-save failed: {e}")
            return False
    
    # Private methods
    
    def _get_layout_file_path(
        self,
        layout_name: str,
        storage_type: LayoutStorageType
    ) -> Path:
        """Get file path for layout storage."""
        storage_dir = self._storage_path / storage_type.value
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir / f"{layout_name}.json"
    
    def _find_layout_file(
        self,
        layout_name: str,
        storage_type: Optional[LayoutStorageType] = None
    ) -> Path:
        """Find layout file in storage."""
        if storage_type:
            return self._get_layout_file_path(layout_name, storage_type)
        
        # Search all storage types
        for st in LayoutStorageType:
            file_path = self._get_layout_file_path(layout_name, st)
            if file_path.exists():
                return file_path
        
        # Return default path if not found
        return self._get_layout_file_path(layout_name, LayoutStorageType.CUSTOM)
    
    def _create_backup(self, layout_name: str, reason: str) -> str:
        """Create backup of existing layout."""
        try:
            layout_file = self._find_layout_file(layout_name)
            if not layout_file.exists():
                raise PersistenceError(f"Layout '{layout_name}' not found for backup")
            
            # Read layout data
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = f.read()
            
            # Create backup
            backup_id = f"{layout_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            backup = LayoutBackup(
                backup_id=backup_id,
                original_name=layout_name,
                backup_timestamp=datetime.now(timezone.utc),
                backup_reason=reason,
                layout_data=layout_data,
                metadata={"file_path": str(layout_file)}
            )
            
            # Save backup file
            backup_file = self._backup_path / f"{backup_id}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(layout_data)
            
            # Register backup
            self._backup_registry[backup_id] = backup
            self._save_backup_registry()
            
            # Emit signal
            self.backup_created.emit(layout_name, backup_id)
            
            logger.info(f"Created backup {backup_id} for layout '{layout_name}' ({reason})")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup for '{layout_name}': {e}")
            raise PersistenceError(f"Backup creation failed: {e}") from e
    
    def _update_layout_config(
        self,
        layout_name: str,
        serialized: SerializedLayout,
        storage_type: LayoutStorageType
    ) -> None:
        """Update layout in configuration."""
        config_key = f"layouts.{storage_type.value}_layouts"
        layouts = self._config_manager.get(config_key, {})
        
        layouts[layout_name] = {
            "description": serialized.metadata.description,
            "created": serialized.metadata.created.isoformat(),
            "modified": serialized.metadata.modified.isoformat(),
            "version": serialized.metadata.version,
            "tags": serialized.metadata.tags
        }
        
        self._config_manager.set(config_key, layouts)
    
    def _remove_layout_from_config(self, layout_name: str) -> None:
        """Remove layout from configuration."""
        for storage_type in LayoutStorageType:
            config_key = f"layouts.{storage_type.value}_layouts"
            layouts = self._config_manager.get(config_key, {})
            layouts.pop(layout_name, None)
            self._config_manager.set(config_key, layouts)
    
    def _get_or_create_profile(
        self,
        layout_name: str,
        storage_type: LayoutStorageType = LayoutStorageType.CUSTOM
    ) -> LayoutProfile:
        """Get or create layout profile."""
        if layout_name not in self._layout_profiles:
            self._layout_profiles[layout_name] = LayoutProfile(
                name=layout_name,
                storage_type=storage_type
            )
        
        return self._layout_profiles[layout_name]
    
    def _load_layout_profiles(self) -> None:
        """Load layout profiles from configuration."""
        profiles_data = self._config_manager.get("layouts.layout_profiles", {})
        
        for name, data in profiles_data.items():
            self._layout_profiles[name] = LayoutProfile(
                name=name,
                description=data.get("description", ""),
                storage_type=LayoutStorageType(data.get("storage_type", "custom")),
                auto_restore=data.get("auto_restore", True),
                created=datetime.fromisoformat(data.get("created", datetime.now(timezone.utc).isoformat())),
                last_used=datetime.fromisoformat(data.get("last_used", datetime.now(timezone.utc).isoformat())),
                usage_count=data.get("usage_count", 0),
                tags=data.get("tags", [])
            )
    
    def _save_layout_profiles(self) -> None:
        """Save layout profiles to configuration."""
        profiles_data = {}
        
        for name, profile in self._layout_profiles.items():
            profiles_data[name] = {
                "description": profile.description,
                "storage_type": profile.storage_type.value,
                "auto_restore": profile.auto_restore,
                "created": profile.created.isoformat(),
                "last_used": profile.last_used.isoformat(),
                "usage_count": profile.usage_count,
                "tags": profile.tags
            }
        
        self._config_manager.set("layouts.layout_profiles", profiles_data)
    
    def _load_backup_registry(self) -> None:
        """Load backup registry from configuration."""
        registry_data = self._config_manager.get("layouts.backup_layouts", {})
        
        for backup_id, data in registry_data.items():
            self._backup_registry[backup_id] = LayoutBackup(
                backup_id=backup_id,
                original_name=data["original_name"],
                backup_timestamp=datetime.fromisoformat(data["backup_timestamp"]),
                backup_reason=data["backup_reason"],
                layout_data="",  # Not stored in config
                metadata=data.get("metadata", {})
            )
    
    def _save_backup_registry(self) -> None:
        """Save backup registry to configuration."""
        registry_data = {}
        
        for backup_id, backup in self._backup_registry.items():
            registry_data[backup_id] = {
                "original_name": backup.original_name,
                "backup_timestamp": backup.backup_timestamp.isoformat(),
                "backup_reason": backup.backup_reason,
                "metadata": backup.metadata
            }
        
        self._config_manager.set("layouts.backup_layouts", registry_data)
    
    def _setup_auto_save(self) -> None:
        """Setup auto-save functionality."""
        auto_save_enabled = self._config_mgr.get_user_preference("auto_save_enabled", True)
        self._auto_save_enabled = auto_save_enabled
    
    def _get_current_user(self) -> str:
        """Get current user identifier."""
        import getpass
        return getpass.getuser()
    
    def _on_application_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handle application shutdown."""
        self._save_layout_profiles()
        self._save_backup_registry()
        logger.info("Layout persistence data saved on shutdown")
    
    def _on_layout_changed(self, event_data: Dict[str, Any]) -> None:
        """Handle layout change events."""
        # Could trigger auto-save here
        logger.debug("Layout changed event received")

from datetime import timedelta  # Add this import at the top