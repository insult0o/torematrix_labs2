"""Base editor interface and configuration for inline editing system"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class EditorConfig:
    """Configuration for editor instances"""
    
    # Basic configuration
    auto_focus: bool = True
    auto_select: bool = True
    placeholder_text: str = "Enter text..."
    max_length: int = 10000
    
    # Validation settings
    validation_enabled: bool = True
    validation_on_change: bool = True
    validation_rules: List[str] = field(default_factory=list)
    
    # Auto-save settings
    auto_save_enabled: bool = True
    auto_save_interval: int = 30  # seconds
    
    # UI settings
    border_style: str = "1px solid #ccc"
    focus_border_style: str = "2px solid #007acc"
    background_color: str = "#ffffff"
    text_color: str = "#000000"
    font_family: str = "Arial, sans-serif"
    font_size: int = 12
    
    # Behavior settings
    escape_cancels: bool = True
    enter_commits: bool = True
    tab_behavior: str = "indent"  # "indent", "next_field", "commit"
    
    # Element context
    element_id: Optional[str] = None
    element_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'auto_focus': self.auto_focus,
            'auto_select': self.auto_select,
            'placeholder_text': self.placeholder_text,
            'max_length': self.max_length,
            'validation_enabled': self.validation_enabled,
            'validation_on_change': self.validation_on_change,
            'validation_rules': self.validation_rules,
            'auto_save_enabled': self.auto_save_enabled,
            'auto_save_interval': self.auto_save_interval,
            'border_style': self.border_style,
            'focus_border_style': self.focus_border_style,
            'background_color': self.background_color,
            'text_color': self.text_color,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'escape_cancels': self.escape_cancels,
            'enter_commits': self.enter_commits,
            'tab_behavior': self.tab_behavior,
            'element_id': self.element_id,
            'element_type': self.element_type,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditorConfig':
        """Create configuration from dictionary"""
        return cls(**data)


class BaseEditor(QWidget, ABC):
    """Abstract base class for all inline editors
    
    This class defines the common interface that all inline editors must implement.
    It provides signals for editor lifecycle events and abstract methods for
    core editing functionality.
    
    Signals:
        editing_started: Emitted when editing begins
        editing_finished: Emitted when editing ends (success: bool)
        content_changed: Emitted when content changes (content: str)
        validation_failed: Emitted when validation fails (message: str)
        focus_lost: Emitted when editor loses focus
        key_pressed: Emitted when key is pressed (key: int)
    """
    
    # Core lifecycle signals
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal(bool)  # success
    content_changed = pyqtSignal(str)    # content
    
    # Validation signals
    validation_failed = pyqtSignal(str)  # error_message
    validation_passed = pyqtSignal()
    
    # Interaction signals
    focus_lost = pyqtSignal()
    focus_gained = pyqtSignal()
    key_pressed = pyqtSignal(int)        # key_code
    
    # State signals
    dirty_changed = pyqtSignal(bool)     # is_dirty
    readonly_changed = pyqtSignal(bool)  # is_readonly
    
    def __init__(self, config: Optional[EditorConfig] = None, parent=None):
        super().__init__(parent)
        
        self.config = config or EditorConfig()
        self._is_editing = False
        self._is_dirty = False
        self._is_readonly = False
        self._original_content = ""
        self._current_content = ""
        
        # Element context
        self._element_id: Optional[str] = None
        self._element_type: str = "text"
        self._element_metadata: Dict[str, Any] = {}
        
        # Validation
        self._validators: List[Callable[[str], bool]] = []
        self._validation_messages: List[str] = []
        
        # Features
        self._auto_save_enabled = False
        self._spell_check_enabled = False
        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []
        
        self._setup_editor()
    
    def _setup_editor(self):
        """Setup basic editor functionality"""
        # Apply configuration
        self._apply_config()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Initialize features
        self._initialize_features()
    
    def _apply_config(self):
        """Apply configuration to editor"""
        if self.config.auto_focus:
            self.setFocusPolicy(self.config.auto_focus)
        
        # Apply styling
        self._apply_styling()
    
    def _apply_styling(self):
        """Apply visual styling based on configuration"""
        style = f"""
        QWidget {{
            border: {self.config.border_style};
            background-color: {self.config.background_color};
            color: {self.config.text_color};
            font-family: {self.config.font_family};
            font-size: {self.config.font_size}px;
        }}
        QWidget:focus {{
            border: {self.config.focus_border_style};
        }}
        """
        self.setStyleSheet(style)
    
    def _setup_event_handlers(self):
        """Setup event handlers for editor interaction"""
        # Override in subclasses for specific event handling
        pass
    
    def _initialize_features(self):
        """Initialize editor features based on configuration"""
        if self.config.auto_save_enabled:
            self._setup_auto_save()
        
        if self.config.validation_enabled:
            self._setup_validation()
    
    def _setup_auto_save(self):
        """Setup auto-save functionality"""
        self._auto_save_enabled = True
        # Auto-save implementation will be provided by mixins
    
    def _setup_validation(self):
        """Setup validation functionality"""
        # Set up validation rules from configuration
        for rule in self.config.validation_rules:
            self._add_validation_rule(rule)
    
    def _add_validation_rule(self, rule: str):
        """Add a validation rule
        
        Args:
            rule: Validation rule name or pattern
        """
        # Basic validation rules
        if rule == "required":
            self._validators.append(lambda content: bool(content.strip()))
        elif rule.startswith("max_length:"):
            max_len = int(rule.split(":")[1])
            self._validators.append(lambda content: len(content) <= max_len)
        elif rule.startswith("min_length:"):
            min_len = int(rule.split(":")[1])
            self._validators.append(lambda content: len(content) >= min_len)
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    def start_editing(self, content: str) -> None:
        """Start editing with given content
        
        Args:
            content: Initial content to edit
        """
        pass
    
    @abstractmethod
    def finish_editing(self, save: bool = True) -> Optional[str]:
        """Finish editing and optionally save changes
        
        Args:
            save: Whether to save changes
            
        Returns:
            Final content if saved, None if cancelled
        """
        pass
    
    @abstractmethod
    def get_content(self) -> str:
        """Get current editor content
        
        Returns:
            Current content as string
        """
        pass
    
    @abstractmethod
    def set_content(self, content: str) -> None:
        """Set editor content
        
        Args:
            content: Content to set
        """
        pass
    
    @abstractmethod
    def is_modified(self) -> bool:
        """Check if content has been modified
        
        Returns:
            True if content is modified
        """
        pass
    
    # Optional methods with default implementations
    
    def cancel_editing(self) -> None:
        """Cancel editing and revert changes"""
        self.finish_editing(save=False)
    
    def validate_content(self, content: Optional[str] = None) -> bool:
        """Validate editor content
        
        Args:
            content: Content to validate (current content if None)
            
        Returns:
            True if content is valid
        """
        if content is None:
            content = self.get_content()
        
        self._validation_messages.clear()
        
        for validator in self._validators:
            try:
                if not validator(content):
                    return False
            except Exception as e:
                self._validation_messages.append(str(e))
                return False
        
        return True
    
    def get_validation_messages(self) -> List[str]:
        """Get current validation error messages
        
        Returns:
            List of validation error messages
        """
        return self._validation_messages.copy()
    
    # Element context methods
    
    def set_element_context(self, element_id: str, element_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Set element context for this editor
        
        Args:
            element_id: Unique element identifier
            element_type: Type of element being edited
            metadata: Additional element metadata
        """
        self._element_id = element_id
        self._element_type = element_type
        self._element_metadata = metadata or {}
        
        # Update configuration
        self.config.element_id = element_id
        self.config.element_type = element_type
        self.config.metadata = self._element_metadata
    
    def get_element_context(self) -> Dict[str, Any]:
        """Get element context information
        
        Returns:
            Dictionary with element context
        """
        return {
            'element_id': self._element_id,
            'element_type': self._element_type,
            'metadata': self._element_metadata
        }
    
    # Configuration methods
    
    def update_config(self, config: EditorConfig):
        """Update editor configuration
        
        Args:
            config: New configuration
        """
        self.config = config
        self._apply_config()
    
    def get_config(self) -> EditorConfig:
        """Get current editor configuration
        
        Returns:
            Current configuration
        """
        return self.config
    
    # State management methods
    
    def is_editing(self) -> bool:
        """Check if editor is currently in editing mode
        
        Returns:
            True if editing
        """
        return self._is_editing
    
    def is_dirty(self) -> bool:
        """Check if editor has unsaved changes
        
        Returns:
            True if dirty
        """
        return self._is_dirty
    
    def is_readonly(self) -> bool:
        """Check if editor is in readonly mode
        
        Returns:
            True if readonly
        """
        return self._is_readonly
    
    def set_readonly(self, readonly: bool):
        """Set readonly mode
        
        Args:
            readonly: Whether to enable readonly mode
        """
        if self._is_readonly != readonly:
            self._is_readonly = readonly
            self.readonly_changed.emit(readonly)
            self._update_visual_state()
    
    def _update_visual_state(self):
        """Update visual appearance based on current state"""
        # Apply different styling based on state
        if self._is_readonly:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
    
    # Undo/Redo support
    
    def can_undo(self) -> bool:
        """Check if undo is available
        
        Returns:
            True if undo is available
        """
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available
        
        Returns:
            True if redo is available
        """
        return len(self._redo_stack) > 0
    
    def undo(self) -> bool:
        """Perform undo operation
        
        Returns:
            True if undo was performed
        """
        if self.can_undo():
            current_content = self.get_content()
            self._redo_stack.append(current_content)
            
            previous_content = self._undo_stack.pop()
            self.set_content(previous_content)
            return True
        return False
    
    def redo(self) -> bool:
        """Perform redo operation
        
        Returns:
            True if redo was performed
        """
        if self.can_redo():
            current_content = self.get_content()
            self._undo_stack.append(current_content)
            
            next_content = self._redo_stack.pop()
            self.set_content(next_content)
            return True
        return False
    
    def _push_undo_state(self, content: str):
        """Push content to undo stack
        
        Args:
            content: Content to save for undo
        """
        self._undo_stack.append(content)
        
        # Limit undo stack size
        max_undo_levels = 50
        if len(self._undo_stack) > max_undo_levels:
            self._undo_stack.pop(0)
        
        # Clear redo stack when new action is performed
        self._redo_stack.clear()
    
    # Utility methods
    
    def focus_editor(self):
        """Give focus to the editor"""
        self.setFocus()
    
    def select_all(self):
        """Select all content in editor"""
        # Override in subclasses for specific implementation
        pass
    
    def clear(self):
        """Clear editor content"""
        self.set_content("")
    
    def get_editor_info(self) -> Dict[str, Any]:
        """Get information about this editor instance
        
        Returns:
            Dictionary with editor information
        """
        return {
            'editor_type': self.__class__.__name__,
            'is_editing': self._is_editing,
            'is_dirty': self._is_dirty,
            'is_readonly': self._is_readonly,
            'element_context': self.get_element_context(),
            'config': self.config.to_dict(),
            'content_length': len(self.get_content()),
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }