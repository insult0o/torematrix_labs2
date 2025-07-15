"""Property editor factory system for creating and managing editors"""

from typing import Dict, Type, Optional, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

from .base import BasePropertyEditor, EditorConfiguration
from ..models import PropertyMetadata
from ..events import PropertyNotificationCenter


class EditorType(Enum):
    """Standard property editor types"""
    TEXT = "text"
    MULTILINE_TEXT = "multiline_text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    COORDINATE = "coordinate"
    COLOR = "color"
    DATE = "date"
    TIME = "time"
    FILE_PATH = "file_path"
    URL = "url"
    EMAIL = "email"
    CUSTOM = "custom"


@dataclass
class EditorRegistration:
    """Registration information for property editors"""
    editor_type: EditorType
    editor_class: Type[BasePropertyEditor]
    property_types: List[str]
    priority: int = 0
    description: str = ""
    supports_inline: bool = True
    supports_validation: bool = True
    custom_attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_attributes is None:
            self.custom_attributes = {}


class EditorRegistry(QObject):
    """Registry for managing property editor types and instances"""
    
    # Signals
    editor_registered = pyqtSignal(str, EditorRegistration)  # editor_id, registration
    editor_unregistered = pyqtSignal(str)  # editor_id
    
    def __init__(self):
        super().__init__()
        self._registrations: Dict[str, EditorRegistration] = {}
        self._type_mappings: Dict[str, List[str]] = {}  # property_type -> [editor_ids]
        self._editor_instances: Dict[str, BasePropertyEditor] = {}
        
        # Register default editors
        self._register_default_editors()
    
    def register_editor(self, editor_id: str, registration: EditorRegistration) -> None:
        """Register a new property editor"""
        if editor_id in self._registrations:
            raise ValueError(f"Editor '{editor_id}' is already registered")
        
        self._registrations[editor_id] = registration
        
        # Update type mappings
        for property_type in registration.property_types:
            if property_type not in self._type_mappings:
                self._type_mappings[property_type] = []
            self._type_mappings[property_type].append(editor_id)
            # Sort by priority (higher priority first)
            self._type_mappings[property_type].sort(
                key=lambda eid: self._registrations[eid].priority, reverse=True
            )
        
        self.editor_registered.emit(editor_id, registration)
    
    def unregister_editor(self, editor_id: str) -> bool:
        """Unregister a property editor"""
        if editor_id not in self._registrations:
            return False
        
        registration = self._registrations[editor_id]
        
        # Remove from type mappings
        for property_type in registration.property_types:
            if property_type in self._type_mappings:
                if editor_id in self._type_mappings[property_type]:
                    self._type_mappings[property_type].remove(editor_id)
                if not self._type_mappings[property_type]:
                    del self._type_mappings[property_type]
        
        # Remove registration
        del self._registrations[editor_id]
        
        # Clean up instances
        if editor_id in self._editor_instances:
            self._editor_instances[editor_id].deleteLater()
            del self._editor_instances[editor_id]
        
        self.editor_unregistered.emit(editor_id)
        return True
    
    def get_editors_for_type(self, property_type: str) -> List[str]:
        """Get list of editor IDs for a property type (sorted by priority)"""
        return self._type_mappings.get(property_type, []).copy()
    
    def get_best_editor_for_type(self, property_type: str) -> Optional[str]:
        """Get the best (highest priority) editor for a property type"""
        editors = self.get_editors_for_type(property_type)
        return editors[0] if editors else None
    
    def get_registration(self, editor_id: str) -> Optional[EditorRegistration]:
        """Get registration for an editor"""
        return self._registrations.get(editor_id)
    
    def get_all_registrations(self) -> Dict[str, EditorRegistration]:
        """Get all editor registrations"""
        return self._registrations.copy()
    
    def is_registered(self, editor_id: str) -> bool:
        """Check if an editor is registered"""
        return editor_id in self._registrations
    
    def _register_default_editors(self) -> None:
        """Register default property editors"""
        # Import here to avoid circular imports
        from .text import TextPropertyEditor, MultilineTextEditor, RichTextEditor
        from .numeric import IntegerPropertyEditor, FloatPropertyEditor
        from .boolean import CheckboxPropertyEditor, RadioButtonPropertyEditor, ToggleSwitchEditor
        from .choice import ComboBoxPropertyEditor, ListPropertyEditor, RadioButtonChoiceEditor
        from .coordinate import Point2DEditor, Point3DEditor
        
        # Register text editors
        self.register_editor("text", EditorRegistration(
            editor_type=EditorType.TEXT,
            editor_class=TextPropertyEditor,
            property_types=["string", "text", "str"],
            priority=10,
            description="Single-line text input"
        ))
        
        self.register_editor("multiline_text", EditorRegistration(
            editor_type=EditorType.MULTILINE_TEXT,
            editor_class=MultilineTextEditor,
            property_types=["multiline", "textarea", "longtext"],
            priority=10,
            description="Multi-line text input"
        ))
        
        self.register_editor("rich_text", EditorRegistration(
            editor_type=EditorType.MULTILINE_TEXT,
            editor_class=RichTextEditor,
            property_types=["richtext", "html"],
            priority=15,
            description="Rich text editor with formatting"
        ))
        
        # Register numeric editors
        self.register_editor("integer", EditorRegistration(
            editor_type=EditorType.INTEGER,
            editor_class=IntegerPropertyEditor,
            property_types=["integer", "int", "long"],
            priority=10,
            description="Integer number input"
        ))
        
        self.register_editor("float", EditorRegistration(
            editor_type=EditorType.FLOAT,
            editor_class=FloatPropertyEditor,
            property_types=["float", "double", "number", "decimal"],
            priority=10,
            description="Floating point number input"
        ))
        
        # Register boolean editors
        self.register_editor("checkbox", EditorRegistration(
            editor_type=EditorType.BOOLEAN,
            editor_class=CheckboxPropertyEditor,
            property_types=["boolean", "bool"],
            priority=10,
            description="Checkbox boolean input"
        ))
        
        self.register_editor("radio_boolean", EditorRegistration(
            editor_type=EditorType.BOOLEAN,
            editor_class=RadioButtonPropertyEditor,
            property_types=["boolean", "bool"],
            priority=5,
            description="Radio button boolean input"
        ))
        
        self.register_editor("toggle_switch", EditorRegistration(
            editor_type=EditorType.BOOLEAN,
            editor_class=ToggleSwitchEditor,
            property_types=["boolean", "bool"],
            priority=8,
            description="Toggle switch boolean input"
        ))
        
        # Register choice editors
        self.register_editor("combobox", EditorRegistration(
            editor_type=EditorType.CHOICE,
            editor_class=ComboBoxPropertyEditor,
            property_types=["choice", "select", "enum", "option"],
            priority=10,
            description="Dropdown choice selection"
        ))
        
        self.register_editor("list_choice", EditorRegistration(
            editor_type=EditorType.CHOICE,
            editor_class=ListPropertyEditor,
            property_types=["choice", "select", "enum", "option", "multiple"],
            priority=8,
            description="List choice selection with multiple support"
        ))
        
        self.register_editor("radio_choice", EditorRegistration(
            editor_type=EditorType.CHOICE,
            editor_class=RadioButtonChoiceEditor,
            property_types=["choice", "select", "enum", "option"],
            priority=5,
            description="Radio button choice selection"
        ))
        
        # Register coordinate editors
        self.register_editor("point2d", EditorRegistration(
            editor_type=EditorType.COORDINATE,
            editor_class=Point2DEditor,
            property_types=["coordinate", "point", "point2d", "vector2"],
            priority=10,
            description="2D point coordinate input"
        ))
        
        self.register_editor("point3d", EditorRegistration(
            editor_type=EditorType.COORDINATE,
            editor_class=Point3DEditor,
            property_types=["point3d", "vector3", "coordinate3d"],
            priority=10,
            description="3D point coordinate input"
        ))


class PropertyEditorFactory(QObject):
    """Factory for creating property editors"""
    
    # Signals
    editor_created = pyqtSignal(str, BasePropertyEditor)  # property_name, editor
    editor_creation_failed = pyqtSignal(str, str)  # property_name, error_message
    
    def __init__(self, registry: Optional[EditorRegistry] = None,
                 notification_center: Optional[PropertyNotificationCenter] = None):
        super().__init__()
        self._registry = registry or EditorRegistry()
        self._notification_center = notification_center
        self._active_editors: Dict[str, BasePropertyEditor] = {}
        self._editor_configs: Dict[str, EditorConfiguration] = {}
        
    def create_editor(self, property_name: str, property_type: str,
                     metadata: Optional[PropertyMetadata] = None,
                     editor_type: Optional[str] = None,
                     custom_config: Optional[Dict[str, Any]] = None) -> Optional[BasePropertyEditor]:
        """Create a property editor for the given property"""
        try:
            # Determine editor type
            if editor_type is None:
                editor_type = self._registry.get_best_editor_for_type(property_type)
                if editor_type is None:
                    # Fallback to text editor
                    editor_type = self._registry.get_best_editor_for_type("string")
            
            if editor_type is None:
                raise ValueError(f"No editor available for property type '{property_type}'")
            
            # Get editor registration
            registration = self._registry.get_registration(editor_type)
            if registration is None:
                raise ValueError(f"Editor type '{editor_type}' is not registered")
            
            # Create editor configuration
            config = self._create_editor_config(
                property_name, property_type, metadata, custom_config
            )
            
            # Create editor instance
            editor = registration.editor_class(
                config=config,
                notification_center=self._notification_center
            )
            
            # Store references
            self._active_editors[property_name] = editor
            self._editor_configs[property_name] = config
            
            # Connect cleanup signal
            editor.destroyed.connect(lambda: self._on_editor_destroyed(property_name))
            
            self.editor_created.emit(property_name, editor)
            return editor
            
        except Exception as e:
            error_message = f"Failed to create editor for '{property_name}': {str(e)}"
            self.editor_creation_failed.emit(property_name, error_message)
            return None
    
    def get_editor(self, property_name: str) -> Optional[BasePropertyEditor]:
        """Get existing editor for property"""
        return self._active_editors.get(property_name)
    
    def destroy_editor(self, property_name: str) -> bool:
        """Destroy editor for property"""
        if property_name in self._active_editors:
            editor = self._active_editors[property_name]
            editor.deleteLater()
            return True
        return False
    
    def destroy_all_editors(self) -> None:
        """Destroy all active editors"""
        for property_name in list(self._active_editors.keys()):
            self.destroy_editor(property_name)
    
    def get_active_editors(self) -> Dict[str, BasePropertyEditor]:
        """Get all active editors"""
        return self._active_editors.copy()
    
    def get_editor_config(self, property_name: str) -> Optional[EditorConfiguration]:
        """Get configuration for an editor"""
        return self._editor_configs.get(property_name)
    
    def update_editor_config(self, property_name: str, 
                           config_updates: Dict[str, Any]) -> bool:
        """Update configuration for an existing editor"""
        if property_name not in self._active_editors:
            return False
        
        config = self._editor_configs[property_name]
        editor = self._active_editors[property_name]
        
        # Update configuration
        for key, value in config_updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Apply configuration to editor
        if hasattr(editor, '_apply_configuration'):
            editor._apply_configuration()
        
        return True
    
    def _create_editor_config(self, property_name: str, property_type: str,
                            metadata: Optional[PropertyMetadata],
                            custom_config: Optional[Dict[str, Any]]) -> EditorConfiguration:
        """Create editor configuration"""
        config = EditorConfiguration(
            property_name=property_name,
            property_type=property_type,
            metadata=metadata
        )
        
        # Apply metadata-based configuration
        if metadata:
            config.read_only = not metadata.editable
            if metadata.custom_attributes:
                config.custom_attributes.update(metadata.custom_attributes)
        
        # Apply custom configuration
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.custom_attributes[key] = value
        
        return config
    
    def _on_editor_destroyed(self, property_name: str) -> None:
        """Handle editor destruction"""
        if property_name in self._active_editors:
            del self._active_editors[property_name]
        if property_name in self._editor_configs:
            del self._editor_configs[property_name]
    
    def get_registry(self) -> EditorRegistry:
        """Get the editor registry"""
        return self._registry
    
    def set_notification_center(self, notification_center: PropertyNotificationCenter) -> None:
        """Set the notification center for future editors"""
        self._notification_center = notification_center


class EditorTypeDetector:
    """Utility class for detecting appropriate editor types"""
    
    @staticmethod
    def detect_editor_type(property_name: str, property_type: str, 
                          metadata: Optional[PropertyMetadata] = None,
                          sample_value: Any = None) -> EditorType:
        """Detect the best editor type for a property"""
        
        # Check metadata hints first
        if metadata and metadata.custom_attributes:
            hint = metadata.custom_attributes.get('editor_hint')
            if hint:
                try:
                    return EditorType(hint)
                except ValueError:
                    pass
        
        # Detect based on property type
        type_mapping = {
            'string': EditorType.TEXT,
            'text': EditorType.TEXT,
            'integer': EditorType.INTEGER,
            'int': EditorType.INTEGER,
            'float': EditorType.FLOAT,
            'number': EditorType.FLOAT,
            'boolean': EditorType.BOOLEAN,
            'bool': EditorType.BOOLEAN,
            'choice': EditorType.CHOICE,
            'enum': EditorType.CHOICE,
            'coordinate': EditorType.COORDINATE,
            'point': EditorType.COORDINATE,
            'color': EditorType.COLOR,
            'date': EditorType.DATE,
            'time': EditorType.TIME,
            'datetime': EditorType.DATE,
            'file': EditorType.FILE_PATH,
            'path': EditorType.FILE_PATH,
            'url': EditorType.URL,
            'email': EditorType.EMAIL,
        }
        
        if property_type.lower() in type_mapping:
            return type_mapping[property_type.lower()]
        
        # Detect based on property name patterns
        name_lower = property_name.lower()
        
        if any(word in name_lower for word in ['email', 'mail']):
            return EditorType.EMAIL
        elif any(word in name_lower for word in ['url', 'link', 'href']):
            return EditorType.URL
        elif any(word in name_lower for word in ['file', 'path', 'directory']):
            return EditorType.FILE_PATH
        elif any(word in name_lower for word in ['color', 'colour']):
            return EditorType.COLOR
        elif any(word in name_lower for word in ['date', 'created', 'modified']):
            return EditorType.DATE
        elif any(word in name_lower for word in ['time', 'duration']):
            return EditorType.TIME
        elif any(word in name_lower for word in ['description', 'comment', 'notes']):
            return EditorType.MULTILINE_TEXT
        elif any(word in name_lower for word in ['x', 'y', 'coord', 'position', 'point']):
            return EditorType.COORDINATE
        
        # Detect based on sample value
        if sample_value is not None:
            if isinstance(sample_value, bool):
                return EditorType.BOOLEAN
            elif isinstance(sample_value, int):
                return EditorType.INTEGER
            elif isinstance(sample_value, float):
                return EditorType.FLOAT
            elif isinstance(sample_value, str):
                if len(sample_value) > 100 or '\n' in sample_value:
                    return EditorType.MULTILINE_TEXT
                else:
                    return EditorType.TEXT
            elif isinstance(sample_value, dict) and 'x' in sample_value and 'y' in sample_value:
                return EditorType.COORDINATE
        
        # Default fallback
        return EditorType.TEXT
    
    @staticmethod
    def get_editor_requirements(editor_type: EditorType) -> Dict[str, Any]:
        """Get requirements and capabilities for an editor type"""
        requirements = {
            EditorType.TEXT: {
                'supports_validation': True,
                'supports_inline': True,
                'validation_types': ['required', 'length', 'pattern'],
                'input_types': ['text']
            },
            EditorType.MULTILINE_TEXT: {
                'supports_validation': True,
                'supports_inline': False,
                'validation_types': ['required', 'length'],
                'input_types': ['text']
            },
            EditorType.INTEGER: {
                'supports_validation': True,
                'supports_inline': True,
                'validation_types': ['required', 'range'],
                'input_types': ['number']
            },
            EditorType.FLOAT: {
                'supports_validation': True,
                'supports_inline': True,
                'validation_types': ['required', 'range'],
                'input_types': ['number']
            },
            EditorType.BOOLEAN: {
                'supports_validation': False,
                'supports_inline': True,
                'validation_types': [],
                'input_types': ['checkbox']
            },
            EditorType.CHOICE: {
                'supports_validation': True,
                'supports_inline': True,
                'validation_types': ['required'],
                'input_types': ['select']
            },
            EditorType.COORDINATE: {
                'supports_validation': True,
                'supports_inline': False,
                'validation_types': ['required', 'range'],
                'input_types': ['number', 'point']
            },
        }
        
        return requirements.get(editor_type, {
            'supports_validation': True,
            'supports_inline': True,
            'validation_types': [],
            'input_types': ['text']
        })