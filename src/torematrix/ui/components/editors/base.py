"""Base classes and interfaces for inline editors

This module provides the foundational classes and interfaces for the
inline editing system, including the base editor class and common data structures.
"""

from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

try:
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None):
            self.parent_widget = parent
            
    class QObject:
        def __init__(self, parent=None):
            self.parent_object = parent
            
    def pyqtSignal(*args):
        return lambda: None


class EditorState(Enum):
    """States of an inline editor"""
    INACTIVE = "inactive"
    EDITING = "editing"
    VALIDATING = "validating"
    SAVING = "saving"
    ERROR = "error"


@dataclass
class EditorConfig:
    """Configuration for inline editors"""
    # Validation settings
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    
    # Behavior settings
    auto_commit: bool = True
    commit_delay: int = 1000  # milliseconds
    placeholder: str = ""
    
    # Visual settings
    font_size: int = 12
    background_color: str = "#ffffff"
    border_width: int = 1
    
    # Accessibility settings
    accessible_name: str = ""
    accessible_description: str = ""
    tab_index: int = 0
    
    # Editor type specific settings
    choices: Optional[List[str]] = None
    precision: Optional[int] = None
    prefix: str = ""
    suffix: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'required': self.required,
            'min_length': self.min_length,
            'max_length': self.max_length,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'pattern': self.pattern,
            'auto_commit': self.auto_commit,
            'commit_delay': self.commit_delay,
            'placeholder': self.placeholder,
            'font_size': self.font_size,
            'background_color': self.background_color,
            'border_width': self.border_width,
            'accessible_name': self.accessible_name,
            'accessible_description': self.accessible_description,
            'tab_index': self.tab_index,
            'choices': self.choices,
            'precision': self.precision,
            'prefix': self.prefix,
            'suffix': self.suffix
        }


class BaseEditor(QWidget, ABC):
    """Abstract base class for all inline editors
    
    This class defines the interface that all inline editors must implement.
    It provides common functionality and signals for the editing workflow.
    """
    
    # Signals
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal(bool)  # success
    value_changed = pyqtSignal(object)  # new_value
    validation_failed = pyqtSignal(str)  # error_message
    save_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state = EditorState.INACTIVE
        self._config = EditorConfig()
        self._original_value = None
        self._current_value = None
        self._dirty = False
        
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    def get_value(self) -> Any:
        """Get the current value of the editor"""
        pass
    
    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Set the value of the editor"""
        pass
    
    @abstractmethod
    def start_editing(self, initial_value: Any = None) -> None:
        """Start editing mode"""
        pass
    
    @abstractmethod
    def finish_editing(self, save: bool = True) -> None:
        """Finish editing mode"""
        pass
    
    @abstractmethod
    def cancel_editing(self) -> None:
        """Cancel editing and revert to original value"""
        pass
    
    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        """Validate current value. Returns (is_valid, error_message)"""
        pass
    
    # Common functionality
    
    def get_state(self) -> EditorState:
        """Get current editor state"""
        return self._state
    
    def set_state(self, state: EditorState) -> None:
        """Set editor state"""
        self._state = state
    
    def get_config(self) -> EditorConfig:
        """Get editor configuration"""
        return self._config
    
    def set_config(self, config: EditorConfig) -> None:
        """Set editor configuration"""
        self._config = config
    
    def is_dirty(self) -> bool:
        """Check if editor has unsaved changes"""
        return self._dirty
    
    def is_editing(self) -> bool:
        """Check if editor is in editing mode"""
        return self._state == EditorState.EDITING
    
    def save(self) -> bool:
        """Save current value"""
        try:
            is_valid, error_msg = self.validate()
            if not is_valid:
                self.validation_failed.emit(error_msg)
                return False
            
            self._original_value = self.get_value()
            self._dirty = False
            return True
            
        except Exception as e:
            self.validation_failed.emit(str(e))
            return False
    
    def reset(self) -> None:
        """Reset to original value"""
        if self._original_value is not None:
            self.set_value(self._original_value)
            self._dirty = False
    
    def mark_dirty(self) -> None:
        """Mark editor as having unsaved changes"""
        self._dirty = True
        
    def mark_clean(self) -> None:
        """Mark editor as having no unsaved changes"""
        self._dirty = False


# Export public API
__all__ = [
    'BaseEditor',
    'EditorState', 
    'EditorConfig'
]