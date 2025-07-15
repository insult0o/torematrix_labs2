"""Property editors package for the property panel

This package provides a comprehensive set of property editors for different data types
and input methods, including factory patterns for dynamic editor creation.
"""

# Factory system
from .factory import PropertyEditorFactory, EditorRegistry, EditorType, EditorRegistration

# Base classes and configuration
from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)

# Inline editing framework
from .inline import InlineEditingManager, InlineEditContext, InlineEditMode, InlineEditableWidget

# Specialized editors
from .text import TextPropertyEditor, MultilineTextEditor, RichTextEditor
from .numeric import NumericPropertyEditor, IntegerPropertyEditor, FloatPropertyEditor
from .boolean import BooleanPropertyEditor, CheckboxPropertyEditor, RadioButtonPropertyEditor, ToggleSwitchEditor
from .choice import ChoicePropertyEditor, ComboBoxPropertyEditor, ListPropertyEditor, RadioButtonChoiceEditor
from .coordinate import CoordinatePropertyEditor, Point2DEditor, Point3DEditor, CoordinateVisualWidget

# Validation system
from .validation import (
    ValidationEngine, ValidationResult, ValidationSeverity, ValidationRuleParser,
    BaseValidator, RequiredValidator, LengthValidator, RangeValidator, 
    PatternValidator, EmailValidator, URLValidator, TypeValidator, 
    ChoiceValidator, CustomValidator
)

__all__ = [
    # Factory system
    "PropertyEditorFactory", "EditorRegistry", "EditorType", "EditorRegistration",
    
    # Base classes
    "BasePropertyEditor", "EditorConfiguration", "PropertyEditorMixin", 
    "EditorValidationMixin", "PropertyEditorState",
    
    # Inline editing
    "InlineEditingManager", "InlineEditContext", "InlineEditMode", "InlineEditableWidget",
    
    # Text editors
    "TextPropertyEditor", "MultilineTextEditor", "RichTextEditor",
    
    # Numeric editors
    "NumericPropertyEditor", "IntegerPropertyEditor", "FloatPropertyEditor",
    
    # Boolean editors
    "BooleanPropertyEditor", "CheckboxPropertyEditor", "RadioButtonPropertyEditor", "ToggleSwitchEditor",
    
    # Choice editors
    "ChoicePropertyEditor", "ComboBoxPropertyEditor", "ListPropertyEditor", "RadioButtonChoiceEditor",
    
    # Coordinate editors
    "CoordinatePropertyEditor", "Point2DEditor", "Point3DEditor", "CoordinateVisualWidget",
    
    # Validation system
    "ValidationEngine", "ValidationResult", "ValidationSeverity", "ValidationRuleParser",
    "BaseValidator", "RequiredValidator", "LengthValidator", "RangeValidator", 
    "PatternValidator", "EmailValidator", "URLValidator", "TypeValidator", 
    "ChoiceValidator", "CustomValidator",
]