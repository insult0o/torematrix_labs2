"""Property panel editors package

This package provides specialized property editors for different data types:
- Base editor classes and interfaces
- Factory system for dynamic editor creation
- Inline editing framework
- Text editors (single-line, multi-line, rich text)
- Numeric editors (integer, float with optional sliders)
- Boolean editors (checkbox, radio buttons, toggle switch)
- Choice editors (dropdown, multi-select, radio groups, tags)
- Coordinate editors (2D point, rectangle with visual preview)
- Validation framework for input validation
"""

from .base import BasePropertyEditor, EditorConfiguration, PropertyEditorState
from .factory import PropertyEditorFactory, EditorRegistry, EditorType, EditorTypeDetector
from .inline import InlineEditingManager, InlineEditContext, InlineEditMode, InlineEditableWidget
from .text import TextPropertyEditor, MultilineTextEditor, RichTextEditor
from .numeric import NumericPropertyEditor, IntegerPropertyEditor, FloatPropertyEditor
from .boolean import CheckboxPropertyEditor, RadioButtonPropertyEditor, ToggleSwitchEditor
from .choice import DropdownPropertyEditor, MultiSelectListEditor, RadioButtonGroupEditor, TagsEditor
from .coordinate import Point2D, Rectangle2D, Point2DEditor, Rectangle2DEditor
from .validation import ValidationSeverity, ValidationResult, ValidationRule, PropertyValidator, ValidationMixin

__all__ = [
    # Base classes
    'BasePropertyEditor',
    'EditorConfiguration', 
    'PropertyEditorState',
    
    # Factory system
    'PropertyEditorFactory',
    'EditorRegistry',
    'EditorType',
    'EditorTypeDetector',
    
    # Inline editing
    'InlineEditingManager',
    'InlineEditContext',
    'InlineEditMode',
    'InlineEditableWidget',
    
    # Text editors
    'TextPropertyEditor',
    'MultilineTextEditor',
    'RichTextEditor',
    
    # Numeric editors
    'NumericPropertyEditor',
    'IntegerPropertyEditor',
    'FloatPropertyEditor',
    
    # Boolean editors
    'CheckboxPropertyEditor',
    'RadioButtonPropertyEditor',
    'ToggleSwitchEditor',
    
    # Choice editors
    'DropdownPropertyEditor',
    'MultiSelectListEditor',
    'RadioButtonGroupEditor',
    'TagsEditor',
    
    # Coordinate editors
    'Point2D',
    'Rectangle2D',
    'Point2DEditor',
    'Rectangle2DEditor',
    
    # Validation framework
    'ValidationSeverity',
    'ValidationResult',
    'ValidationRule',
    'PropertyValidator',
    'ValidationMixin',
]