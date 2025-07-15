"""Base property editor classes and interfaces"""

from typing import Any, Optional, Dict, Callable, List
from abc import ABC, abstractmethod, ABCMeta
from enum import Enum
from dataclasses import dataclass, field
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ..models import PropertyValue, PropertyMetadata
from ..events import PropertyNotificationCenter


class PropertyEditorState(Enum):
    """State of property editor"""
    IDLE = "idle"
    EDITING = "editing"
    VALIDATING = "validating"
    COMMITTING = "committing"
    ERROR = "error"


@dataclass
class EditorConfiguration:
    """Configuration for property editors"""
    property_name: str
    property_type: str
    metadata: Optional[PropertyMetadata] = None
    read_only: bool = False
    compact_mode: bool = False
    validation_enabled: bool = True
    auto_commit: bool = True
    commit_delay_ms: int = 500
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class CombinedMeta(type(QWidget), ABCMeta):
    """Combined metaclass for QWidget and ABC"""
    pass


class BasePropertyEditor(QWidget, ABC, metaclass=CombinedMeta):
    """Abstract base class for all property editors"""
    
    # Signals
    value_changed = pyqtSignal(str, object)  # property_name, new_value
    value_committed = pyqtSignal(str, object)  # property_name, committed_value
    editing_started = pyqtSignal(str)  # property_name
    editing_finished = pyqtSignal(str, bool)  # property_name, success
    validation_failed = pyqtSignal(str, str)  # property_name, error_message
    state_changed = pyqtSignal(PropertyEditorState)  # new_state
    
    def __init__(self, config: EditorConfiguration, 
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(parent)
        self._config = config
        self._notification_center = notification_center
        self._current_value: Any = None
        self._original_value: Any = None
        self._state = PropertyEditorState.IDLE
        self._validation_error: Optional[str] = None
        self._is_dirty = False
        
        # Auto-commit timer
        self._commit_timer = QTimer()
        self._commit_timer.setSingleShot(True)
        self._commit_timer.timeout.connect(self._auto_commit)
        
        # Validation state
        self._validation_in_progress = False
        self._pending_validation: Optional[Any] = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Apply initial configuration
        self._apply_configuration()
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """Setup the editor UI components"""
        pass
    
    @abstractmethod
    def _get_editor_value(self) -> Any:
        """Get current value from editor widget"""
        pass
    
    @abstractmethod
    def _set_editor_value(self, value: Any) -> None:
        """Set value in editor widget"""
        pass
    
    @abstractmethod
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate the given value. Returns (is_valid, error_message)"""
        pass
    
    def _connect_signals(self) -> None:
        """Connect internal signals"""
        if self._notification_center:
            self.value_committed.connect(
                lambda name, value: self._notification_center.emit_value_change(
                    "", name, self._original_value, value
                )
            )
            self.validation_failed.connect(
                lambda name, error: self._notification_center.emit_validation_failed(
                    "", name, error
                )
            )
    
    def _apply_configuration(self) -> None:
        """Apply editor configuration"""
        self.setEnabled(not self._config.read_only)
        
        if self._config.compact_mode:
            self.setMaximumHeight(30)
        
        # Apply custom styling if needed
        if 'style' in self._config.custom_attributes:
            self.setStyleSheet(self._config.custom_attributes['style'])
    
    def set_value(self, value: Any) -> None:
        """Set the editor value"""
        self._current_value = value
        self._original_value = value
        self._is_dirty = False
        self._validation_error = None
        
        try:
            self._set_editor_value(value)
            self._set_state(PropertyEditorState.IDLE)
        except Exception as e:
            self._validation_error = str(e)
            self._set_state(PropertyEditorState.ERROR)
            self.validation_failed.emit(self._config.property_name, str(e))
    
    def get_value(self) -> Any:
        """Get current editor value"""
        return self._current_value
    
    def get_original_value(self) -> Any:
        """Get original value before editing"""
        return self._original_value
    
    def is_dirty(self) -> bool:
        """Check if editor has uncommitted changes"""
        return self._is_dirty
    
    def has_validation_error(self) -> bool:
        """Check if editor has validation error"""
        return self._validation_error is not None
    
    def get_validation_error(self) -> Optional[str]:
        """Get current validation error message"""
        return self._validation_error
    
    def get_state(self) -> PropertyEditorState:
        """Get current editor state"""
        return self._state
    
    def start_editing(self) -> bool:
        """Start editing mode"""
        if self._state not in [PropertyEditorState.IDLE, PropertyEditorState.ERROR]:
            return False
        
        self._set_state(PropertyEditorState.EDITING)
        self.editing_started.emit(self._config.property_name)
        return True
    
    def commit_changes(self) -> bool:
        """Commit current changes"""
        if not self._is_dirty:
            return True
        
        self._set_state(PropertyEditorState.COMMITTING)
        
        try:
            current_value = self._get_editor_value()
            
            # Validate if validation is enabled
            if self._config.validation_enabled:
                is_valid, error_message = self._validate_value(current_value)
                if not is_valid:
                    self._validation_error = error_message
                    self._set_state(PropertyEditorState.ERROR)
                    self.validation_failed.emit(self._config.property_name, error_message)
                    return False
            
            # Commit the value
            self._current_value = current_value
            self._original_value = current_value
            self._is_dirty = False
            self._validation_error = None
            
            self._set_state(PropertyEditorState.IDLE)
            self.value_committed.emit(self._config.property_name, current_value)
            self.editing_finished.emit(self._config.property_name, True)
            
            return True
            
        except Exception as e:
            self._validation_error = str(e)
            self._set_state(PropertyEditorState.ERROR)
            self.validation_failed.emit(self._config.property_name, str(e))
            self.editing_finished.emit(self._config.property_name, False)
            return False
    
    def cancel_editing(self) -> None:
        """Cancel editing and revert to original value"""
        if self._state == PropertyEditorState.IDLE:
            return
        
        # Revert to original value
        self._set_editor_value(self._original_value)
        self._current_value = self._original_value
        self._is_dirty = False
        self._validation_error = None
        
        self._set_state(PropertyEditorState.IDLE)
        self.editing_finished.emit(self._config.property_name, False)
    
    def _on_value_changed(self) -> None:
        """Handle value change in editor widget"""
        if self._state == PropertyEditorState.IDLE:
            self.start_editing()
        
        try:
            new_value = self._get_editor_value()
            self._current_value = new_value
            self._is_dirty = (new_value != self._original_value)
            self._validation_error = None
            
            # Emit value changed signal
            self.value_changed.emit(self._config.property_name, new_value)
            
            # Start auto-commit timer if enabled
            if self._config.auto_commit and self._is_dirty:
                self._commit_timer.stop()
                self._commit_timer.start(self._config.commit_delay_ms)
                
        except Exception as e:
            self._validation_error = str(e)
            self._set_state(PropertyEditorState.ERROR)
            self.validation_failed.emit(self._config.property_name, str(e))
    
    def _auto_commit(self) -> None:
        """Auto-commit changes after delay"""
        if self._is_dirty and self._state == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _set_state(self, new_state: PropertyEditorState) -> None:
        """Set editor state and emit signal"""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self.state_changed.emit(new_state)
            self._on_state_changed(old_state, new_state)
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state change (override in subclasses)"""
        pass
    
    # Configuration methods
    def set_read_only(self, read_only: bool) -> None:
        """Set read-only mode"""
        self._config.read_only = read_only
        self.setEnabled(not read_only)
    
    def set_compact_mode(self, compact: bool) -> None:
        """Set compact display mode"""
        self._config.compact_mode = compact
        if compact:
            self.setMaximumHeight(30)
        else:
            self.setMaximumHeight(16777215)  # Reset to default
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """Enable/disable validation"""
        self._config.validation_enabled = enabled
    
    def set_auto_commit(self, enabled: bool, delay_ms: int = 500) -> None:
        """Enable/disable auto-commit with delay"""
        self._config.auto_commit = enabled
        self._config.commit_delay_ms = delay_ms
    
    def get_configuration(self) -> EditorConfiguration:
        """Get editor configuration"""
        return self._config
    
    def set_custom_attribute(self, key: str, value: Any) -> None:
        """Set custom attribute"""
        self._config.custom_attributes[key] = value
    
    def get_custom_attribute(self, key: str, default: Any = None) -> Any:
        """Get custom attribute"""
        return self._config.custom_attributes.get(key, default)


class PropertyEditorMixin:
    """Mixin class for common property editor functionality"""
    
    def setup_common_styling(self, widget: QWidget) -> None:
        """Setup common styling for editor widgets"""
        widget.setStyleSheet("""
            QWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: white;
            }
            QWidget:focus {
                border-color: #007acc;
                outline: none;
            }
            QWidget:disabled {
                background-color: #f0f0f0;
                color: #666;
            }
            QWidget[error="true"] {
                border-color: #f44336;
                background-color: #ffebee;
            }
        """)
    
    def setup_validation_styling(self, widget: QWidget, has_error: bool) -> None:
        """Setup validation-based styling"""
        widget.setProperty("error", has_error)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
    
    def create_error_tooltip(self, error_message: str) -> str:
        """Create formatted error tooltip"""
        return f"<span style='color: red;'>{error_message}</span>"


class EditorValidationMixin:
    """Mixin class for validation functionality"""
    
    def validate_required(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate required field"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, "This field is required"
        return True, None
    
    def validate_type(self, value: Any, expected_type: type) -> tuple[bool, Optional[str]]:
        """Validate value type"""
        if not isinstance(value, expected_type):
            return False, f"Expected {expected_type.__name__}, got {type(value).__name__}"
        return True, None
    
    def validate_range(self, value: Any, min_val: Any = None, max_val: Any = None) -> tuple[bool, Optional[str]]:
        """Validate value range"""
        if min_val is not None and value < min_val:
            return False, f"Value must be at least {min_val}"
        if max_val is not None and value > max_val:
            return False, f"Value must be at most {max_val}"
        return True, None
    
    def validate_length(self, value: str, min_length: int = None, max_length: int = None) -> tuple[bool, Optional[str]]:
        """Validate string length"""
        length = len(value) if value else 0
        if min_length is not None and length < min_length:
            return False, f"Minimum length is {min_length} characters"
        if max_length is not None and length > max_length:
            return False, f"Maximum length is {max_length} characters"
        return True, None
    
    def validate_pattern(self, value: str, pattern: str) -> tuple[bool, Optional[str]]:
        """Validate string pattern using regex"""
        import re
        if not re.match(pattern, value or ""):
            return False, "Value does not match required pattern"
        return True, None