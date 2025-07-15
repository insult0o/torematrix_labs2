<<<<<<< HEAD
"""Property editor factory system for creating and managing editors"""

from typing import Dict, Type, Optional, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

from .base import BasePropertyEditor, EditorConfiguration
from ..models import PropertyMetadata
from ..events import PropertyNotificationCenter
=======
"""Property editor factory system with dynamic editor creation and registration"""

from typing import Dict, Type, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from .base import BasePropertyEditor, EditorConfiguration, PropertyEditorState
>>>>>>> origin/main


class EditorType(Enum):
    """Standard property editor types"""
    TEXT = "text"
    MULTILINE_TEXT = "multiline_text"
<<<<<<< HEAD
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
=======
    RICH_TEXT = "rich_text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    TOGGLE_SWITCH = "toggle_switch"
    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    RADIO_GROUP = "radio_group"
    TAGS = "tags"
    POINT2D = "point2d"
    RECTANGLE2D = "rectangle2d"
    
    # Future editor types
    COLOR = "color"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    FILE = "file"
    IMAGE = "image"
>>>>>>> origin/main


@dataclass
class EditorRegistration:
<<<<<<< HEAD
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
=======
    """Registration information for a property editor"""
    editor_type: EditorType
    editor_class: Type[BasePropertyEditor]
    priority: int = 0
    predicate: Optional[Callable[[Any], bool]] = None
    description: str = ""
>>>>>>> origin/main


class EditorRegistry(QObject):
    """Registry for managing property editor types and instances"""
    
    # Signals
<<<<<<< HEAD
    editor_registered = pyqtSignal(str, EditorRegistration)  # editor_id, registration
    editor_unregistered = pyqtSignal(str)  # editor_id
    
    def __init__(self):
        super().__init__()
        self._registrations: Dict[str, EditorRegistration] = {}
        self._type_mappings: Dict[str, List[str]] = {}  # property_type -> [editor_ids]
        self._editor_instances: Dict[str, BasePropertyEditor] = {}
=======
    editor_registered = pyqtSignal(str, object)  # editor_type, editor_class
    editor_unregistered = pyqtSignal(str)  # editor_type
    
    def __init__(self):
        super().__init__()
        self._registrations: Dict[EditorType, EditorRegistration] = {}
        self._instances: Dict[str, BasePropertyEditor] = {}
        self._type_predicates: List[EditorRegistration] = []
>>>>>>> origin/main
        
        # Register default editors
        self._register_default_editors()
    
<<<<<<< HEAD
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
=======
    def register_editor(self, registration: EditorRegistration) -> None:
        """Register a property editor type"""
        self._registrations[registration.editor_type] = registration
        
        # Add to type predicates if predicate is provided
        if registration.predicate:
            self._type_predicates.append(registration)
            # Sort by priority (higher priority first)
            self._type_predicates.sort(key=lambda x: x.priority, reverse=True)
        
        self.editor_registered.emit(registration.editor_type.value, registration.editor_class)
    
    def unregister_editor(self, editor_type: EditorType) -> None:
        """Unregister a property editor type"""
        if editor_type in self._registrations:
            registration = self._registrations[editor_type]
            del self._registrations[editor_type]
            
            # Remove from type predicates
            self._type_predicates = [r for r in self._type_predicates if r.editor_type != editor_type]
            
            self.editor_unregistered.emit(editor_type.value)
    
    def get_editor_class(self, editor_type: EditorType) -> Optional[Type[BasePropertyEditor]]:
        """Get editor class for given type"""
        registration = self._registrations.get(editor_type)
        return registration.editor_class if registration else None
    
    def create_editor(self, editor_type: EditorType, config: EditorConfiguration) -> Optional[BasePropertyEditor]:
        """Create editor instance of given type"""
        editor_class = self.get_editor_class(editor_type)
        if not editor_class:
            return None
        
        try:
            editor = editor_class(config)
            # Store instance for management
            instance_key = f"{editor_type.value}_{id(editor)}"
            self._instances[instance_key] = editor
            return editor
        except Exception as e:
            print(f"Failed to create editor of type {editor_type.value}: {e}")
            return None
    
    def detect_editor_type(self, value: Any) -> EditorType:
        """Detect appropriate editor type for a value"""
        # Try custom predicates first (by priority)
        for registration in self._type_predicates:
            if registration.predicate and registration.predicate(value):
                return registration.editor_type
        
        # Fallback to type-based detection
        return EditorTypeDetector.detect_type(value)
    
    def get_available_types(self) -> List[EditorType]:
        """Get list of all registered editor types"""
        return list(self._registrations.keys())
    
    def get_registration_info(self, editor_type: EditorType) -> Optional[EditorRegistration]:
        """Get registration information for editor type"""
        return self._registrations.get(editor_type)
    
    def clear_instances(self) -> None:
        """Clear all cached editor instances"""
        for instance in self._instances.values():
            if hasattr(instance, 'deleteLater'):
                instance.deleteLater()
        self._instances.clear()
    
    def _register_default_editors(self) -> None:
        """Register default editor types"""
        # Import editor classes to avoid circular imports
        try:
            from .text import TextPropertyEditor, MultilineTextEditor, RichTextEditor
            from .numeric import IntegerPropertyEditor, FloatPropertyEditor
            from .boolean import CheckboxPropertyEditor, RadioButtonPropertyEditor, ToggleSwitchEditor
            from .choice import DropdownPropertyEditor, MultiSelectListEditor, RadioButtonGroupEditor, TagsEditor
            from .coordinate import Point2DEditor, Rectangle2DEditor
            
            # Text editors
            self.register_editor(EditorRegistration(
                EditorType.TEXT, TextPropertyEditor, 0,
                lambda v: isinstance(v, str) and len(v) < 100,
                "Single-line text input"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.MULTILINE_TEXT, MultilineTextEditor, 0,
                lambda v: isinstance(v, str) and len(v) >= 100,
                "Multi-line text input"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.RICH_TEXT, RichTextEditor, 0,
                None,  # Manual selection only
                "Rich text editor with formatting"
            ))
            
            # Numeric editors
            self.register_editor(EditorRegistration(
                EditorType.INTEGER, IntegerPropertyEditor, 0,
                lambda v: isinstance(v, int),
                "Integer number input"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.FLOAT, FloatPropertyEditor, 0,
                lambda v: isinstance(v, float),
                "Floating point number input"
            ))
            
            # Boolean editors
            self.register_editor(EditorRegistration(
                EditorType.CHECKBOX, CheckboxPropertyEditor, 0,
                lambda v: isinstance(v, bool),
                "Checkbox for boolean values"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.RADIO_BUTTON, RadioButtonPropertyEditor, 0,
                None,  # Manual selection only
                "Radio buttons for boolean values"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.TOGGLE_SWITCH, ToggleSwitchEditor, 0,
                None,  # Manual selection only
                "Toggle switch for boolean values"
            ))
            
            # Choice editors
            self.register_editor(EditorRegistration(
                EditorType.DROPDOWN, DropdownPropertyEditor, 0,
                None,  # Manual selection with choices config
                "Dropdown selection from choices"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.MULTISELECT, MultiSelectListEditor, 0,
                lambda v: isinstance(v, list),
                "Multi-selection from choices"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.RADIO_GROUP, RadioButtonGroupEditor, 0,
                None,  # Manual selection only
                "Radio button group for exclusive selection"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.TAGS, TagsEditor, 0,
                None,  # Manual selection only
                "Tag input with add/remove functionality"
            ))
            
            # Coordinate editors
            self.register_editor(EditorRegistration(
                EditorType.POINT2D, Point2DEditor, 0,
                None,  # Manual selection only
                "2D point coordinate editor"
            ))
            
            self.register_editor(EditorRegistration(
                EditorType.RECTANGLE2D, Rectangle2DEditor, 0,
                None,  # Manual selection only
                "2D rectangle coordinate editor"
            ))
            
        except ImportError as e:
            print(f"Warning: Could not import some editor classes: {e}")


class EditorTypeDetector:
    """Utility class for detecting appropriate editor types based on value characteristics"""
    
    @staticmethod
    def detect_type(value: Any) -> EditorType:
        """Detect editor type based on value type and characteristics"""
        if value is None:
            return EditorType.TEXT
        
        # Boolean detection
        if isinstance(value, bool):
            return EditorType.CHECKBOX
        
        # Numeric detection
        if isinstance(value, int):
            return EditorType.INTEGER
        if isinstance(value, float):
            return EditorType.FLOAT
        
        # String detection with content analysis
        if isinstance(value, str):
            if len(value) > 100 or '\n' in value:
                return EditorType.MULTILINE_TEXT
            return EditorType.TEXT
        
        # List detection
        if isinstance(value, list):
            return EditorType.MULTISELECT
        
        # Dict detection - could be coordinate data
        if isinstance(value, dict):
            if 'x' in value and 'y' in value:
                if 'width' in value and 'height' in value:
                    return EditorType.RECTANGLE2D
                return EditorType.POINT2D
        
        # Tuple detection - could be coordinates
        if isinstance(value, tuple):
            if len(value) == 2:
                return EditorType.POINT2D
            elif len(value) == 4:
                return EditorType.RECTANGLE2D
>>>>>>> origin/main
        
        # Default fallback
        return EditorType.TEXT
    
    @staticmethod
<<<<<<< HEAD
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
=======
    def detect_from_metadata(metadata: Dict[str, Any]) -> EditorType:
        """Detect editor type from property metadata"""
        # Check explicit editor type hint
        if 'editor_type' in metadata:
            try:
                return EditorType(metadata['editor_type'])
            except ValueError:
                pass
        
        # Check for choices (indicates selection editor)
        if 'choices' in metadata:
            choices = metadata['choices']
            if isinstance(choices, (list, dict)) and len(choices) > 0:
                return EditorType.DROPDOWN
        
        # Check validation rules for type hints
        validation_rules = metadata.get('validation_rules', [])
        for rule in validation_rules:
            if isinstance(rule, dict):
                rule_type = rule.get('type')
                if rule_type == 'range':
                    return EditorType.FLOAT
                elif rule_type == 'pattern':
                    return EditorType.TEXT
                elif rule_type == 'email':
                    return EditorType.TEXT
        
        # Check custom attributes
        custom_attrs = metadata.get('custom_attributes', {})
        if 'multiline' in custom_attrs and custom_attrs['multiline']:
            return EditorType.MULTILINE_TEXT
        if 'rich_text' in custom_attrs and custom_attrs['rich_text']:
            return EditorType.RICH_TEXT
        
        # Default
        return EditorType.TEXT


class PropertyEditorFactory(QObject):
    """Main factory for creating property editors with automatic type detection"""
    
    # Signals
    editor_created = pyqtSignal(object)  # BasePropertyEditor
    editor_failed = pyqtSignal(str, str)  # editor_type, error_message
    
    def __init__(self):
        super().__init__()
        self.registry = EditorRegistry()
        self.default_config = EditorConfiguration()
        
        # Connect registry signals
        self.registry.editor_registered.connect(self._on_editor_registered)
        self.registry.editor_unregistered.connect(self._on_editor_unregistered)
    
    def create_editor(self, 
                     value: Any = None,
                     editor_type: Optional[EditorType] = None,
                     config: Optional[EditorConfiguration] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Optional[BasePropertyEditor]:
        """Create property editor with automatic or explicit type detection"""
        
        # Use provided config or default
        if config is None:
            config = EditorConfiguration()
            if metadata:
                config.custom_attributes.update(metadata.get('custom_attributes', {}))
        
        # Determine editor type
        if editor_type is None:
            if metadata:
                editor_type = EditorTypeDetector.detect_from_metadata(metadata)
            else:
                editor_type = self.registry.detect_editor_type(value)
        
        # Create editor
        editor = self.registry.create_editor(editor_type, config)
        
        if editor:
            # Set initial value if provided
            if value is not None:
                editor.set_value(value)
            
            self.editor_created.emit(editor)
            return editor
        else:
            error_msg = f"Failed to create editor of type {editor_type.value}"
            self.editor_failed.emit(editor_type.value, error_msg)
            return None
    
    def create_editor_for_property(self, 
                                  property_name: str,
                                  property_value: Any,
                                  property_metadata: Dict[str, Any]) -> Optional[BasePropertyEditor]:
        """Create editor for a specific property with metadata"""
        
        # Create configuration from metadata
        config = EditorConfiguration()
        config.property_name = property_name
        config.display_name = property_metadata.get('display_name', property_name)
        config.description = property_metadata.get('description', '')
        config.editable = property_metadata.get('editable', True)
        config.visible = property_metadata.get('visible', True)
        config.placeholder_text = property_metadata.get('placeholder', '')
        config.custom_attributes = property_metadata.get('custom_attributes', {})
        
        # Add validation rules
        validation_rules = property_metadata.get('validation_rules', [])
        config.custom_attributes['validation_rules'] = validation_rules
        
        return self.create_editor(
            value=property_value,
            config=config,
            metadata=property_metadata
        )
    
    def register_custom_editor(self, 
                              editor_type: EditorType,
                              editor_class: Type[BasePropertyEditor],
                              predicate: Optional[Callable[[Any], bool]] = None,
                              priority: int = 0) -> None:
        """Register a custom editor type"""
        registration = EditorRegistration(
            editor_type=editor_type,
            editor_class=editor_class,
            priority=priority,
            predicate=predicate,
            description=f"Custom editor: {editor_class.__name__}"
        )
        self.registry.register_editor(registration)
    
    def get_available_editor_types(self) -> List[EditorType]:
        """Get list of available editor types"""
        return self.registry.get_available_types()
    
    def get_editor_info(self, editor_type: EditorType) -> Optional[Dict[str, Any]]:
        """Get information about an editor type"""
        registration = self.registry.get_registration_info(editor_type)
        if registration:
            return {
                'type': registration.editor_type.value,
                'class': registration.editor_class.__name__,
                'description': registration.description,
                'priority': registration.priority
            }
        return None
    
    def cleanup(self) -> None:
        """Clean up factory resources"""
        self.registry.clear_instances()
    
    def _on_editor_registered(self, editor_type: str, editor_class: object) -> None:
        """Handle editor registration"""
        pass
    
    def _on_editor_unregistered(self, editor_type: str) -> None:
        """Handle editor unregistration"""
        pass


# Global factory instance
_factory_instance: Optional[PropertyEditorFactory] = None

def get_property_editor_factory() -> PropertyEditorFactory:
    """Get global property editor factory instance"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = PropertyEditorFactory()
    return _factory_instance


# Export main classes
__all__ = [
    'EditorType',
    'EditorRegistration',
    'EditorRegistry',
    'EditorTypeDetector',
    'PropertyEditorFactory',
    'get_property_editor_factory'
]
>>>>>>> origin/main
