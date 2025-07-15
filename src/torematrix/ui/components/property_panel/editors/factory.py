"""Property editor factory system with dynamic editor creation and registration"""

from typing import Dict, Type, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from .base import BasePropertyEditor, EditorConfiguration, PropertyEditorState


class EditorType(Enum):
    """Standard property editor types"""
    TEXT = "text"
    MULTILINE_TEXT = "multiline_text"
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


@dataclass
class EditorRegistration:
    """Registration information for a property editor"""
    editor_type: EditorType
    editor_class: Type[BasePropertyEditor]
    priority: int = 0
    predicate: Optional[Callable[[Any], bool]] = None
    description: str = ""


class EditorRegistry(QObject):
    """Registry for managing property editor types and instances"""
    
    # Signals
    editor_registered = pyqtSignal(str, object)  # editor_type, editor_class
    editor_unregistered = pyqtSignal(str)  # editor_type
    
    def __init__(self):
        super().__init__()
        self._registrations: Dict[EditorType, EditorRegistration] = {}
        self._instances: Dict[str, BasePropertyEditor] = {}
        self._type_predicates: List[EditorRegistration] = []
        
        # Register default editors
        self._register_default_editors()
    
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
        
        # Default fallback
        return EditorType.TEXT
    
    @staticmethod
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