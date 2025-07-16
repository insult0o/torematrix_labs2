"""Base classes and interfaces for inline editors

This module provides the foundational classes and interfaces for the
inline editing system, including the base editor class and common data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, Callable, List
from enum import Enum, auto

try:
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtCore import pyqtSignal, QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None): pass
    class QObject:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args): return lambda: None


class EditorState(Enum):
    """State enumeration for inline editors."""
    INACTIVE = auto()
    ACTIVE = auto()
    EDITING = auto()
    SAVING = auto()
    ERROR = auto()
    VALIDATING = auto()


class EditorType(Enum):
    """Type of editor based on data type."""
    TEXT = auto()
    NUMERIC = auto()
    DATE = auto()
    BOOLEAN = auto()
    LIST = auto()
    RICH_TEXT = auto()
    MULTILINE = auto()


@dataclass
class EditorConfig:
    """Configuration for inline editors."""
    
    # Core settings
    editor_type: EditorType = EditorType.TEXT
    allow_empty: bool = True
    auto_save: bool = True
    auto_save_delay: int = 1000  # milliseconds
    
    # Validation
    validators: List[Callable[[Any], bool]] = field(default_factory=list)
    validate_on_change: bool = True
    
    # UI settings
    placeholder_text: str = ""
    tooltip_text: str = ""
    enable_spellcheck: bool = False
    
    # Accessibility
    aria_label: str = ""
    aria_description: str = ""
    enable_screen_reader: bool = True
    
    # Advanced features
    enable_autocomplete: bool = False
    autocomplete_source: Optional[Callable[[], List[str]]] = None
    enable_undo_redo: bool = True
    max_length: Optional[int] = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        if self.auto_save_delay < 0:
            errors.append("auto_save_delay must be non-negative")
            
        if self.max_length is not None and self.max_length < 0:
            errors.append("max_length must be positive")
            
        if not self.aria_label and self.enable_screen_reader:
            errors.append("aria_label required when screen reader is enabled")
            
        return errors


@dataclass
class EditorValidationResult:
    """Result of editor validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
        
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class BaseEditor(QObject, ABC):
    """Abstract base class for all inline editors.
    
    Provides the interface that all inline editors must implement,
    including lifecycle management, validation, and event handling.
    """
    
    # Signals for editor lifecycle
    editing_started = pyqtSignal(str)  # element_id
    editing_finished = pyqtSignal(str, object)  # element_id, value
    editing_cancelled = pyqtSignal(str)  # element_id
    value_changed = pyqtSignal(str, object)  # element_id, value
    validation_changed = pyqtSignal(str, EditorValidationResult)  # element_id, result
    state_changed = pyqtSignal(str, EditorState)  # element_id, state
    error_occurred = pyqtSignal(str, str)  # element_id, error_message
    
    def __init__(self, element_id: str, config: EditorConfig, parent: Optional[QWidget] = None):
        """Initialize the editor.
        
        Args:
            element_id: Unique identifier for the element being edited
            config: Editor configuration
            parent: Parent widget
        """
        super().__init__(parent)
        self._element_id = element_id
        self._config = config
        self._state = EditorState.INACTIVE
        self._current_value = None
        self._original_value = None
        self._validation_result = EditorValidationResult(is_valid=True)
        self._is_dirty = False
        
        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"Invalid editor configuration: {', '.join(config_errors)}")
    
    @property
    def element_id(self) -> str:
        """Get the element ID."""
        return self._element_id
    
    @property
    def config(self) -> EditorConfig:
        """Get the editor configuration."""
        return self._config
    
    @property
    def state(self) -> EditorState:
        """Get the current editor state."""
        return self._state
    
    @property
    def current_value(self) -> Any:
        """Get the current editor value."""
        return self._current_value
    
    @property
    def original_value(self) -> Any:
        """Get the original value before editing."""
        return self._original_value
    
    @property
    def is_dirty(self) -> bool:
        """Check if the editor value has been modified."""
        return self._is_dirty
    
    @property
    def validation_result(self) -> EditorValidationResult:
        """Get the current validation result."""
        return self._validation_result
    
    def _set_state(self, new_state: EditorState) -> None:
        """Set the editor state and emit signal."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self.state_changed.emit(self._element_id, new_state)
    
    def _set_dirty(self, dirty: bool) -> None:
        """Set the dirty flag."""
        self._is_dirty = dirty
    
    def _validate_value(self, value: Any) -> EditorValidationResult:
        """Validate a value using configured validators."""
        result = EditorValidationResult(is_valid=True)
        
        # Check if empty when not allowed
        if not self._config.allow_empty and (value is None or value == ""):
            result.is_valid = False
            result.errors.append("Value cannot be empty")
            return result
        
        # Check max length for strings
        if (self._config.max_length is not None and 
            isinstance(value, str) and 
            len(value) > self._config.max_length):
            result.is_valid = False
            result.errors.append(f"Value exceeds maximum length of {self._config.max_length}")
        
        # Run custom validators
        for validator in self._config.validators:
            try:
                if not validator(value):
                    result.is_valid = False
                    result.errors.append("Custom validation failed")
            except Exception as e:
                result.is_valid = False
                result.errors.append(f"Validation error: {str(e)}")
        
        return result
    
    @abstractmethod
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create the editor widget.
        
        Args:
            parent: Parent widget for the editor
            
        Returns:
            The editor widget
        """
        pass
    
    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Set the editor value.
        
        Args:
            value: The value to set
        """
        pass
    
    @abstractmethod
    def get_value(self) -> Any:
        """Get the current editor value.
        
        Returns:
            The current value
        """
        pass
    
    def start_editing(self, initial_value: Any = None) -> bool:
        """Start editing with an initial value.
        
        Args:
            initial_value: The initial value to edit
            
        Returns:
            True if editing started successfully
        """
        try:
            if self._state != EditorState.INACTIVE:
                return False
            
            self._original_value = initial_value
            self._current_value = initial_value
            self._is_dirty = False
            
            # Validate initial value
            self._validation_result = self._validate_value(initial_value)
            
            self._set_state(EditorState.ACTIVE)
            self.editing_started.emit(self._element_id)
            
            return True
            
        except Exception as e:
            self._handle_error(f"Failed to start editing: {str(e)}")
            return False
    
    def finish_editing(self, save: bool = True) -> bool:
        """Finish editing and optionally save the value.
        
        Args:
            save: Whether to save the current value
            
        Returns:
            True if editing finished successfully
        """
        try:
            if self._state not in [EditorState.ACTIVE, EditorState.EDITING]:
                return False
            
            if save:
                # Validate before saving
                current_value = self.get_value()
                validation_result = self._validate_value(current_value)
                
                if not validation_result.is_valid:
                    self._validation_result = validation_result
                    self.validation_changed.emit(self._element_id, validation_result)
                    return False
                
                self._current_value = current_value
                self.editing_finished.emit(self._element_id, current_value)
            else:
                self.editing_cancelled.emit(self._element_id)
            
            self._set_state(EditorState.INACTIVE)
            return True
            
        except Exception as e:
            self._handle_error(f"Failed to finish editing: {str(e)}")
            return False
    
    def cancel_editing(self) -> bool:
        """Cancel editing and revert to original value.
        
        Returns:
            True if editing cancelled successfully
        """
        try:
            if self._state not in [EditorState.ACTIVE, EditorState.EDITING]:
                return False
            
            # Revert to original value
            self.set_value(self._original_value)
            self._current_value = self._original_value
            self._is_dirty = False
            
            self.editing_cancelled.emit(self._element_id)
            self._set_state(EditorState.INACTIVE)
            
            return True
            
        except Exception as e:
            self._handle_error(f"Failed to cancel editing: {str(e)}")
            return False
    
    def validate_current_value(self) -> EditorValidationResult:
        """Validate the current editor value.
        
        Returns:
            Validation result
        """
        try:
            current_value = self.get_value()
            result = self._validate_value(current_value)
            self._validation_result = result
            self.validation_changed.emit(self._element_id, result)
            return result
            
        except Exception as e:
            result = EditorValidationResult(
                is_valid=False,
                errors=[f"Validation failed: {str(e)}"]
            )
            self._validation_result = result
            self.validation_changed.emit(self._element_id, result)
            return result
    
    def _handle_error(self, error_message: str) -> None:
        """Handle an error condition.
        
        Args:
            error_message: The error message
        """
        self._set_state(EditorState.ERROR)
        self.error_occurred.emit(self._element_id, error_message)
    
    def _on_value_changed(self) -> None:
        """Called when the editor value changes."""
        try:
            if self._state == EditorState.ACTIVE:
                self._set_state(EditorState.EDITING)
            
            current_value = self.get_value()
            self._current_value = current_value
            self._set_dirty(current_value != self._original_value)
            
            # Validate on change if enabled
            if self._config.validate_on_change:
                self.validate_current_value()
            
            self.value_changed.emit(self._element_id, current_value)
            
        except Exception as e:
            self._handle_error(f"Error handling value change: {str(e)}")
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Get accessibility information for the editor.
        
        Returns:
            Dictionary of accessibility properties
        """
        return {
            'element_id': self._element_id,
            'aria_label': self._config.aria_label,
            'aria_description': self._config.aria_description,
            'role': 'textbox',
            'state': self._state.name.lower(),
            'is_dirty': self._is_dirty,
            'validation_errors': self._validation_result.errors if not self._validation_result.is_valid else [],
            'tooltip': self._config.tooltip_text
        }


class EditorFactory(ABC):
    """Abstract factory for creating editors."""
    
    @abstractmethod
    def create_editor(self, element_id: str, editor_type: EditorType, 
                     config: EditorConfig, parent: Optional[QWidget] = None) -> BaseEditor:
        """Create an editor instance.
        
        Args:
            element_id: Unique identifier for the element
            editor_type: Type of editor to create
            config: Editor configuration
            parent: Parent widget
            
        Returns:
            Editor instance
        """
        pass
    
    @abstractmethod
    def supports_type(self, editor_type: EditorType) -> bool:
        """Check if this factory supports the given editor type.
        
        Args:
            editor_type: Type to check
            
        Returns:
            True if supported
        """
        pass