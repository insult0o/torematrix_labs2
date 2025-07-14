"""
Tool state serialization and persistence for selection tools.

This module provides comprehensive serialization capabilities for tool
states, configurations, and session data with support for multiple
formats and version compatibility.
"""

import json
import pickle
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle


logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    BINARY = "binary"
    XML = "xml"


class SerializationVersion(Enum):
    """Serialization format versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"
    CURRENT = V2_0


@dataclass
class SerializationMetadata:
    """Metadata for serialized data."""
    version: SerializationVersion = SerializationVersion.CURRENT
    format: SerializationFormat = SerializationFormat.JSON
    created_at: datetime = field(default_factory=datetime.now)
    application_version: str = "2.0.0"
    schema_version: str = "2.0"
    compression: bool = False
    encryption: bool = False
    checksum: Optional[str] = None


@dataclass
class ToolConfiguration:
    """Serializable tool configuration."""
    tool_id: str
    tool_type: str
    name: str
    description: str
    enabled: bool = True
    visible: bool = True
    config_data: Dict[str, Any] = field(default_factory=dict)
    theme_data: Dict[str, Any] = field(default_factory=dict)
    shortcuts: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolConfiguration':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SelectionData:
    """Serializable selection data."""
    selection_id: str = field(default_factory=lambda: str(uuid4()))
    elements: List[Dict[str, Any]] = field(default_factory=list)
    geometry: Optional[Dict[str, Any]] = None
    tool_type: str = ""
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionData':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_selection_result(cls, result: SelectionResult) -> 'SelectionData':
        """Create from SelectionResult."""
        elements = []
        for element in result.elements:
            # Serialize element data
            element_data = {
                'id': getattr(element, 'id', str(uuid4())),
                'type': getattr(element, 'type', 'unknown'),
                'bounds': getattr(element, 'bounds', {})
            }
            elements.append(element_data)
        
        geometry_data = None
        if result.geometry:
            geometry_data = {
                'x': result.geometry.x,
                'y': result.geometry.y,
                'width': result.geometry.width,
                'height': result.geometry.height
            }
        
        return cls(
            elements=elements,
            geometry=geometry_data,
            tool_type=result.tool_type,
            timestamp=result.timestamp,
            metadata=result.metadata or {}
        )


@dataclass
class ToolSession:
    """Serializable tool session data."""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Tool states
    active_tool: Optional[str] = None
    tool_configurations: Dict[str, ToolConfiguration] = field(default_factory=dict)
    tool_states: Dict[str, str] = field(default_factory=dict)
    
    # Selections
    current_selection: Optional[SelectionData] = None
    selection_history: List[SelectionData] = field(default_factory=list)
    
    # Application state
    viewport_state: Dict[str, Any] = field(default_factory=dict)
    overlay_state: Dict[str, Any] = field(default_factory=dict)
    
    # Performance data
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolSession':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert nested dictionaries
        if 'tool_configurations' in data:
            configs = {}
            for tool_id, config_data in data['tool_configurations'].items():
                configs[tool_id] = ToolConfiguration.from_dict(config_data)
            data['tool_configurations'] = configs
        
        if 'current_selection' in data and data['current_selection']:
            data['current_selection'] = SelectionData.from_dict(data['current_selection'])
        
        if 'selection_history' in data:
            history = []
            for selection_data in data['selection_history']:
                history.append(SelectionData.from_dict(selection_data))
            data['selection_history'] = history
        
        return cls(**data)


class ToolSerializer:
    """
    Serializer for tool data with multiple format support.
    
    Handles serialization and deserialization of tool configurations,
    states, and session data with version compatibility.
    """
    
    def __init__(self, format: SerializationFormat = SerializationFormat.JSON):
        self._format = format
        self._version = SerializationVersion.CURRENT
        self._registered_types: Dict[str, Type] = {}
        
        # Register built-in types
        self._register_builtin_types()
        
        logger.info(f"ToolSerializer initialized with format: {format}")
    
    def _register_builtin_types(self) -> None:
        """Register built-in serializable types."""
        self._registered_types.update({
            'ToolConfiguration': ToolConfiguration,
            'SelectionData': SelectionData,
            'ToolSession': ToolSession,
            'SerializationMetadata': SerializationMetadata
        })
    
    def register_type(self, type_name: str, type_class: Type) -> None:
        """Register a custom type for serialization."""
        self._registered_types[type_name] = type_class
        logger.debug(f"Registered type for serialization: {type_name}")
    
    def serialize_tool_configuration(self, tool: SelectionTool) -> Dict[str, Any]:
        """Serialize tool configuration."""
        config = ToolConfiguration(
            tool_id=tool.tool_id,
            tool_type=type(tool).__name__,
            name=tool.name,
            description=tool.description,
            enabled=tool.is_enabled(),
            visible=tool.is_visible(),
            config_data=tool.get_config_dict() if hasattr(tool, 'get_config_dict') else {},
            theme_data={},  # Would be populated from theme system
            shortcuts={}   # Would be populated from shortcut system
        )
        
        return self._serialize_object(config)
    
    def deserialize_tool_configuration(self, data: Dict[str, Any]) -> ToolConfiguration:
        """Deserialize tool configuration."""
        return self._deserialize_object(data, ToolConfiguration)
    
    def serialize_selection(self, result: SelectionResult) -> Dict[str, Any]:
        """Serialize selection result."""
        selection_data = SelectionData.from_selection_result(result)
        return self._serialize_object(selection_data)
    
    def deserialize_selection(self, data: Dict[str, Any]) -> SelectionData:
        """Deserialize selection data."""
        return self._deserialize_object(data, SelectionData)
    
    def serialize_session(self, session: ToolSession) -> Dict[str, Any]:
        """Serialize complete tool session."""
        return self._serialize_object(session)
    
    def deserialize_session(self, data: Dict[str, Any]) -> ToolSession:
        """Deserialize tool session."""
        return self._deserialize_object(data, ToolSession)
    
    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        """Serialize an object to dictionary."""
        if hasattr(obj, 'to_dict'):
            data = obj.to_dict()
        else:
            data = asdict(obj) if hasattr(obj, '__dataclass_fields__') else obj
        
        # Add type information
        data['__type__'] = type(obj).__name__
        data['__version__'] = self._version.value
        
        return data
    
    def _deserialize_object(self, data: Dict[str, Any], expected_type: Type) -> Any:
        """Deserialize an object from dictionary."""
        # Check version compatibility
        version = data.get('__version__', SerializationVersion.V1_0.value)
        if version != self._version.value:
            data = self._migrate_data(data, version)
        
        # Remove metadata
        obj_data = {k: v for k, v in data.items() if not k.startswith('__')}
        
        # Create object
        if hasattr(expected_type, 'from_dict'):
            return expected_type.from_dict(obj_data)
        else:
            return expected_type(**obj_data)
    
    def _migrate_data(self, data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate data between versions."""
        # Implement version migration logic here
        logger.info(f"Migrating data from version {from_version} to {self._version.value}")
        
        # For now, just return the data unchanged
        # In a real implementation, you would handle schema changes
        return data


class ToolPersistenceManager(QObject):
    """
    Manager for persistent storage of tool data.
    
    Handles saving and loading tool configurations, sessions, and
    state data with automatic backup and recovery capabilities.
    """
    
    # Signals
    session_saved = pyqtSignal(str)  # session_id
    session_loaded = pyqtSignal(str)  # session_id
    auto_save_triggered = pyqtSignal()
    backup_created = pyqtSignal(str)  # backup_path
    
    def __init__(self, 
                 storage_dir: Union[str, Path] = Path.home() / ".torematrix" / "tools",
                 auto_save_interval: int = 300,  # 5 minutes
                 max_backups: int = 10):
        super().__init__()
        
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._serializer = ToolSerializer()
        self._current_session: Optional[ToolSession] = None
        self._auto_save_interval = auto_save_interval
        self._max_backups = max_backups
        
        # Auto-save timer
        from PyQt6.QtCore import QTimer
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start(auto_save_interval * 1000)
        
        # File paths
        self._session_file = self._storage_dir / "current_session.json"
        self._config_file = self._storage_dir / "tool_configs.json"
        self._backup_dir = self._storage_dir / "backups"
        self._backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"ToolPersistenceManager initialized with storage: {self._storage_dir}")
    
    def create_session(self) -> ToolSession:
        """Create a new tool session."""
        session = ToolSession()
        self._current_session = session
        logger.info(f"Created new session: {session.session_id}")
        return session
    
    def get_current_session(self) -> Optional[ToolSession]:
        """Get the current tool session."""
        return self._current_session
    
    def save_session(self, session: Optional[ToolSession] = None, backup: bool = True) -> bool:
        """
        Save tool session to disk.
        
        Args:
            session: Session to save, or current session if None
            backup: Whether to create a backup before saving
            
        Returns:
            True if save was successful
        """
        if session is None:
            session = self._current_session
        
        if session is None:
            logger.warning("No session to save")
            return False
        
        try:
            # Create backup if requested
            if backup and self._session_file.exists():
                self._create_backup()
            
            # Update timestamp
            session.updated_at = datetime.now()
            
            # Serialize session
            session_data = self._serializer.serialize_session(session)
            
            # Add metadata
            metadata = SerializationMetadata(
                version=SerializationVersion.CURRENT,
                format=SerializationFormat.JSON,
                created_at=datetime.now()
            )
            
            save_data = {
                'metadata': asdict(metadata),
                'session': session_data
            }
            
            # Save to file
            with open(self._session_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.session_saved.emit(session.session_id)
            logger.info(f"Saved session: {session.session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, session_path: Optional[Union[str, Path]] = None) -> Optional[ToolSession]:
        """
        Load tool session from disk.
        
        Args:
            session_path: Path to session file, or current session if None
            
        Returns:
            Loaded session or None if failed
        """
        if session_path is None:
            session_path = self._session_file
        else:
            session_path = Path(session_path)
        
        if not session_path.exists():
            logger.info("No session file found")
            return None
        
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check metadata
            metadata = data.get('metadata', {})
            version = metadata.get('version', SerializationVersion.V1_0.value)
            
            if version != SerializationVersion.CURRENT.value:
                logger.warning(f"Loading session with different version: {version}")
            
            # Deserialize session
            session_data = data.get('session', {})
            session = self._serializer.deserialize_session(session_data)
            
            self._current_session = session
            self.session_loaded.emit(session.session_id)
            logger.info(f"Loaded session: {session.session_id}")
            return session
        
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def save_tool_configuration(self, tool: SelectionTool) -> bool:
        """Save individual tool configuration."""
        try:
            # Load existing configurations
            configs = self._load_tool_configurations()
            
            # Update with new configuration
            config_data = self._serializer.serialize_tool_configuration(tool)
            configs[tool.tool_id] = config_data
            
            # Save back to file
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=2, default=str)
            
            logger.debug(f"Saved configuration for tool: {tool.tool_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save tool configuration: {e}")
            return False
    
    def load_tool_configuration(self, tool_id: str) -> Optional[ToolConfiguration]:
        """Load individual tool configuration."""
        try:
            configs = self._load_tool_configurations()
            
            if tool_id in configs:
                config_data = configs[tool_id]
                return self._serializer.deserialize_tool_configuration(config_data)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to load tool configuration: {e}")
            return None
    
    def _load_tool_configurations(self) -> Dict[str, Any]:
        """Load all tool configurations."""
        if not self._config_file.exists():
            return {}
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tool configurations: {e}")
            return {}
    
    def _create_backup(self) -> Optional[str]:
        """Create backup of current session."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._backup_dir / f"session_backup_{timestamp}.json"
            
            # Copy current session file
            import shutil
            shutil.copy2(self._session_file, backup_path)
            
            # Clean up old backups
            self._cleanup_backups()
            
            self.backup_created.emit(str(backup_path))
            logger.debug(f"Created backup: {backup_path}")
            return str(backup_path)
        
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _cleanup_backups(self) -> None:
        """Remove old backup files."""
        try:
            backup_files = list(self._backup_dir.glob("session_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove oldest files beyond the limit
            for backup_file in backup_files[self._max_backups:]:
                backup_file.unlink()
                logger.debug(f"Removed old backup: {backup_file}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
    
    def _auto_save(self) -> None:
        """Perform automatic save."""
        if self._current_session:
            if self.save_session(backup=False):
                self.auto_save_triggered.emit()
                logger.debug("Auto-save completed")
    
    def export_session(self, 
                      export_path: Union[str, Path],
                      format: SerializationFormat = SerializationFormat.JSON,
                      session: Optional[ToolSession] = None) -> bool:
        """
        Export session to specified path and format.
        
        Args:
            export_path: Where to export the session
            format: Export format
            session: Session to export, or current if None
            
        Returns:
            True if export was successful
        """
        if session is None:
            session = self._current_session
        
        if session is None:
            logger.error("No session to export")
            return False
        
        try:
            export_path = Path(export_path)
            
            if format == SerializationFormat.JSON:
                session_data = self._serializer.serialize_session(session)
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, default=str)
            
            elif format == SerializationFormat.PICKLE:
                with open(export_path, 'wb') as f:
                    pickle.dump(session, f)
            
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Exported session to: {export_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return False
    
    def import_session(self, 
                      import_path: Union[str, Path],
                      format: SerializationFormat = SerializationFormat.JSON) -> Optional[ToolSession]:
        """
        Import session from specified path and format.
        
        Args:
            import_path: Path to import from
            format: Import format
            
        Returns:
            Imported session or None if failed
        """
        try:
            import_path = Path(import_path)
            
            if not import_path.exists():
                logger.error(f"Import file not found: {import_path}")
                return None
            
            if format == SerializationFormat.JSON:
                with open(import_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                session = self._serializer.deserialize_session(session_data)
            
            elif format == SerializationFormat.PICKLE:
                with open(import_path, 'rb') as f:
                    session = pickle.load(f)
            
            else:
                logger.error(f"Unsupported import format: {format}")
                return None
            
            logger.info(f"Imported session from: {import_path}")
            return session
        
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics."""
        try:
            session_size = self._session_file.stat().st_size if self._session_file.exists() else 0
            config_size = self._config_file.stat().st_size if self._config_file.exists() else 0
            
            backup_files = list(self._backup_dir.glob("*.json"))
            backup_size = sum(f.stat().st_size for f in backup_files)
            
            return {
                'storage_directory': str(self._storage_dir),
                'session_file_size': session_size,
                'config_file_size': config_size,
                'backup_count': len(backup_files),
                'backup_size': backup_size,
                'total_size': session_size + config_size + backup_size,
                'auto_save_interval': self._auto_save_interval,
                'max_backups': self._max_backups
            }
        
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {}