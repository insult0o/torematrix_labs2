"""Base classes and core data structures for inline editors

Provides abstract base classes and core data structures that all inline
editors inherit from, ensuring consistent interface and behavior.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict, Callable
from enum import Enum

try:
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtCore import pyqtSignal, QObject
except ImportError:
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None):
            pass
            
    class QObject:
        def __init__(self, parent=None):
            pass
            
    def pyqtSignal(*args):
        return lambda: None


class EditorState(Enum):
    """States that an inline editor can be in"""
    INACTIVE = "inactive"
    EDITING = "editing"
    SAVING = "saving"
    ERROR = "error"


@dataclass
class EditorConfig:
    """Configuration for inline editors"""
    auto_commit: bool = False
    commit_delay: int = 500  # milliseconds
    allow_empty: bool = True
    validation_rules: Optional[Dict[str, Any]] = None
    placeholder_text: str = ""
    max_length: Optional[int] = None
    required: bool = False
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = {}


class BaseEditor(QWidget, ABC):
    """Abstract base class for all inline editors
    
    Defines the interface that all editors must implement and provides
    common functionality for value management, validation, and lifecycle.
    """
    
    # Signals
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal(bool)  # success
    value_changed = pyqtSignal(object)
    validation_failed = pyqtSignal(str)  # error message
    save_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None, config: Optional[EditorConfig] = None):
        super().__init__(parent)
        self.config = config or EditorConfig()
        self._state = EditorState.INACTIVE
        self._original_value = None
        self._current_value = None
        self._is_dirty = False
        
    @abstractmethod
    def set_value(self, value: Any) -> bool:
        """Set the editor value
        
        Args:
            value: Value to set
            
        Returns:
            True if value was set successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def get_value(self) -> Any:
        """Get current editor value
        
        Returns:
            Current value of the editor
        """
        pass
        
    @abstractmethod
    def start_editing(self, value: Any = None) -> bool:
        """Start editing mode
        
        Args:
            value: Optional initial value
            
        Returns:
            True if editing started successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def save(self) -> bool:
        """Save current value and exit editing mode
        
        Returns:
            True if save was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def cancel_editing(self) -> bool:
        """Cancel editing and revert to original value
        
        Returns:
            True if cancel was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def validate(self, value: Any = None) -> tuple[bool, str]:
        """Validate value
        
        Args:
            value: Value to validate (uses current value if None)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
        
    # Common functionality
    
    def is_editing(self) -> bool:
        """Check if editor is in editing mode"""
        return self._state == EditorState.EDITING
        
    def is_dirty(self) -> bool:
        """Check if editor has unsaved changes"""
        return self._is_dirty
        
    def get_state(self) -> EditorState:
        """Get current editor state"""
        return self._state
        
    def _set_state(self, state: EditorState):
        """Set editor state"""
        self._state = state
        
    def _mark_dirty(self, dirty: bool = True):
        """Mark editor as having changes"""
        self._is_dirty = dirty
        
    def _set_original_value(self, value: Any):
        """Set the original value for change tracking"""
        self._original_value = value
        self._is_dirty = False
        
    def _set_current_value(self, value: Any):
        """Set current value and emit change signal"""
        self._current_value = value
        self._is_dirty = (value != self._original_value)
        self.value_changed.emit(value)


# Export public API
__all__ = [
    'BaseEditor',
    'EditorConfig', 
    'EditorState'
]