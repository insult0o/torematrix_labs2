"""Inline editing framework for property panels"""

from typing import Dict, Optional, Any, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QPushButton, QApplication
)
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect, QTimer, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QFocusEvent

from .base import BasePropertyEditor, PropertyEditorState, EditorConfiguration
from .factory import PropertyEditorFactory, EditorRegistry
from ..models import PropertyMetadata
from ..events import PropertyNotificationCenter


class InlineEditMode(Enum):
    """Inline edit activation modes"""
    SINGLE_CLICK = "single_click"
    DOUBLE_CLICK = "double_click"
    KEY_PRESS = "key_press"
    PROGRAMMATIC = "programmatic"


class InlineEditState(Enum):
    """State of inline editing session"""
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    COMMITTING = "committing"
    CANCELLING = "cancelling"


@dataclass
class InlineEditContext:
    """Context information for inline editing session"""
    property_name: str
    property_type: str
    current_value: Any
    original_value: Any
    metadata: Optional[PropertyMetadata] = None
    activation_mode: InlineEditMode = InlineEditMode.PROGRAMMATIC
    source_widget: Optional[QWidget] = None
    edit_rect: Optional[QRect] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class InlineEditingManager(QObject):
    """Manager for inline property editing sessions"""
    
    # Signals
    edit_started = pyqtSignal(str, InlineEditContext)  # property_name, context
    edit_finished = pyqtSignal(str, bool, Any)  # property_name, success, final_value
    edit_cancelled = pyqtSignal(str)  # property_name
    value_changed = pyqtSignal(str, Any, Any)  # property_name, old_value, new_value
    state_changed = pyqtSignal(InlineEditState)  # new_state
    
    def __init__(self, editor_factory: PropertyEditorFactory,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(parent)
        self._editor_factory = editor_factory
        self._notification_center = notification_center
        
        # Inline editing state
        self._state = InlineEditState.INACTIVE
        self._current_context: Optional[InlineEditContext] = None
        self._current_editor: Optional[BasePropertyEditor] = None
        self._edit_overlay: Optional[QWidget] = None
        
        # Configuration
        self._activation_modes = {InlineEditMode.DOUBLE_CLICK}
        self._auto_commit_delay = 500  # ms
        self._escape_cancels = True
        self._click_outside_commits = True
        self._tab_advances = True
        
        # Timers
        self._commit_timer = QTimer()
        self._commit_timer.setSingleShot(True)
        self._commit_timer.timeout.connect(self._auto_commit)
        
        # Active sessions
        self._active_sessions: Dict[str, InlineEditContext] = {}
        
        # Connect to application events for global handling
        if QApplication.instance():
            QApplication.instance().installEventFilter(self)
    
    def start_inline_edit(self, property_name: str, property_type: str,
                         current_value: Any, source_widget: QWidget,
                         metadata: Optional[PropertyMetadata] = None,
                         activation_mode: InlineEditMode = InlineEditMode.PROGRAMMATIC,
                         custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """Start an inline editing session"""
        
        # Check if already editing this property
        if property_name in self._active_sessions:
            return False
        
        # Check if we can start editing
        if self._state != InlineEditState.INACTIVE:
            # Finish current edit first
            if not self.finish_current_edit():
                return False
        
        try:
            # Create edit context
            context = InlineEditContext(
                property_name=property_name,
                property_type=property_type,
                current_value=current_value,
                original_value=current_value,
                metadata=metadata,
                activation_mode=activation_mode,
                source_widget=source_widget,
                edit_rect=source_widget.rect() if source_widget else None
            )
            
            if custom_config:
                context.custom_attributes.update(custom_config)
            
            # Create inline editor
            editor = self._create_inline_editor(context)
            if editor is None:
                return False
            
            # Setup editing session
            self._current_context = context
            self._current_editor = editor
            self._active_sessions[property_name] = context
            
            # Create and show edit overlay
            self._create_edit_overlay(source_widget, editor)
            
            # Set state and emit signals
            self._set_state(InlineEditState.ACTIVE)
            self.edit_started.emit(property_name, context)
            
            # Focus the editor
            editor.setFocus()
            
            return True
            
        except Exception as e:
            print(f"Failed to start inline edit for '{property_name}': {e}")
            return False
    
    def finish_current_edit(self, commit: bool = True) -> bool:
        """Finish the current inline editing session"""
        if self._state == InlineEditState.INACTIVE:
            return True
        
        if not self._current_context or not self._current_editor:
            return False
        
        try:
            property_name = self._current_context.property_name
            
            if commit:
                self._set_state(InlineEditState.COMMITTING)
                success = self._current_editor.commit_changes()
                final_value = self._current_editor.get_value()
            else:
                self._set_state(InlineEditState.CANCELLING)
                self._current_editor.cancel_editing()
                success = False
                final_value = self._current_context.original_value
            
            # Clean up
            self._cleanup_edit_session()
            
            # Emit signals
            if commit:
                self.edit_finished.emit(property_name, success, final_value)
            else:
                self.edit_cancelled.emit(property_name)
            
            self._set_state(InlineEditState.INACTIVE)
            return success
            
        except Exception as e:
            print(f"Failed to finish inline edit: {e}")
            self._cleanup_edit_session()
            self._set_state(InlineEditState.INACTIVE)
            return False
    
    def cancel_current_edit(self) -> bool:
        """Cancel the current inline editing session"""
        return self.finish_current_edit(commit=False)
    
    def is_editing(self, property_name: Optional[str] = None) -> bool:
        """Check if currently editing (optionally for specific property)"""
        if property_name:
            return property_name in self._active_sessions
        return self._state != InlineEditState.INACTIVE
    
    def get_current_context(self) -> Optional[InlineEditContext]:
        """Get current edit context"""
        return self._current_context
    
    def get_current_editor(self) -> Optional[BasePropertyEditor]:
        """Get current inline editor"""
        return self._current_editor
    
    def get_state(self) -> InlineEditState:
        """Get current inline edit state"""
        return self._state
    
    def _create_inline_editor(self, context: InlineEditContext) -> Optional[BasePropertyEditor]:
        """Create an inline editor for the context"""
        # Create editor configuration for inline editing
        custom_config = {
            'compact_mode': True,
            'auto_commit': False,  # We handle commit manually
            'validation_enabled': True,
        }
        custom_config.update(context.custom_attributes)
        
        # Create editor
        editor = self._editor_factory.create_editor(
            property_name=context.property_name,
            property_type=context.property_type,
            metadata=context.metadata,
            custom_config=custom_config
        )
        
        if editor:
            # Set initial value
            editor.set_value(context.current_value)
            
            # Connect editor signals
            editor.value_changed.connect(self._on_editor_value_changed)
            editor.editing_finished.connect(self._on_editor_finished)
            editor.validation_failed.connect(self._on_editor_validation_failed)
            
            # Setup inline-specific styling
            editor.setStyleSheet(editor.styleSheet() + """
                QWidget {
                    border: 2px solid #007acc;
                    background-color: white;
                    selection-background-color: #007acc;
                }
            """)
        
        return editor
    
    def _create_edit_overlay(self, source_widget: QWidget, editor: BasePropertyEditor) -> None:
        """Create overlay widget for inline editing"""
        if not source_widget:
            return
        
        # Get parent container
        parent = source_widget.parent()
        if not parent:
            return
        
        # Create overlay frame
        overlay = QFrame(parent)
        overlay.setFrameStyle(QFrame.Shape.NoFrame)
        overlay.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Layout for overlay
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(editor)
        
        # Position overlay over source widget
        source_pos = source_widget.mapTo(parent, QPoint(0, 0))
        source_size = source_widget.size()
        
        overlay.setGeometry(source_pos.x(), source_pos.y(),
                          source_size.width(), source_size.height())
        
        # Show overlay
        overlay.show()
        overlay.raise_()
        
        self._edit_overlay = overlay
    
    def _cleanup_edit_session(self) -> None:
        """Clean up current editing session"""
        if self._current_context:
            property_name = self._current_context.property_name
            if property_name in self._active_sessions:
                del self._active_sessions[property_name]
        
        if self._edit_overlay:
            self._edit_overlay.deleteLater()
            self._edit_overlay = None
        
        if self._current_editor:
            self._current_editor.deleteLater()
            self._current_editor = None
        
        self._current_context = None
        self._commit_timer.stop()
    
    def _set_state(self, new_state: InlineEditState) -> None:
        """Set inline edit state"""
        if new_state != self._state:
            self._state = new_state
            self.state_changed.emit(new_state)
    
    def _on_editor_value_changed(self, property_name: str, new_value: Any) -> None:
        """Handle value change in inline editor"""
        if self._current_context:
            old_value = self._current_context.current_value
            self._current_context.current_value = new_value
            self.value_changed.emit(property_name, old_value, new_value)
            
            # Start auto-commit timer if configured
            if self._auto_commit_delay > 0:
                self._commit_timer.stop()
                self._commit_timer.start(self._auto_commit_delay)
    
    def _on_editor_finished(self, property_name: str, success: bool) -> None:
        """Handle editor finishing"""
        if success:
            self.finish_current_edit(commit=True)
        else:
            self.cancel_current_edit()
    
    def _on_editor_validation_failed(self, property_name: str, error_message: str) -> None:
        """Handle validation failure in editor"""
        # Show validation error but don't finish editing
        if self._current_editor:
            self._current_editor.setToolTip(f"Validation Error: {error_message}")
    
    def _auto_commit(self) -> None:
        """Auto-commit after delay"""
        if self._state == InlineEditState.ACTIVE:
            self.finish_current_edit(commit=True)
    
    def eventFilter(self, obj: QObject, event) -> bool:
        """Global event filter for inline editing"""
        if self._state == InlineEditState.INACTIVE:
            return False
        
        # Handle key events
        if event.type() == event.Type.KeyPress:
            key_event = event
            
            # Escape cancels editing
            if (self._escape_cancels and 
                key_event.key() == Qt.Key.Key_Escape):
                self.cancel_current_edit()
                return True
            
            # Enter/Return commits editing
            elif (key_event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter] and
                  key_event.modifiers() == Qt.KeyboardModifier.NoModifier):
                self.finish_current_edit(commit=True)
                return True
            
            # Tab advances to next property (if configured)
            elif (self._tab_advances and
                  key_event.key() == Qt.Key.Key_Tab):
                # For now, just commit - could be enhanced to advance to next property
                self.finish_current_edit(commit=True)
                return True
        
        # Handle mouse events
        elif event.type() == event.Type.MouseButtonPress:
            mouse_event = event
            
            # Click outside commits editing (if configured)
            if (self._click_outside_commits and
                self._edit_overlay and
                not self._edit_overlay.geometry().contains(mouse_event.globalPosition().toPoint())):
                self.finish_current_edit(commit=True)
                return False  # Let the click proceed
        
        return False
    
    # Configuration methods
    def set_activation_modes(self, modes: set[InlineEditMode]) -> None:
        """Set activation modes for inline editing"""
        self._activation_modes = modes
    
    def add_activation_mode(self, mode: InlineEditMode) -> None:
        """Add an activation mode"""
        self._activation_modes.add(mode)
    
    def remove_activation_mode(self, mode: InlineEditMode) -> None:
        """Remove an activation mode"""
        self._activation_modes.discard(mode)
    
    def set_auto_commit_delay(self, delay_ms: int) -> None:
        """Set auto-commit delay in milliseconds (0 to disable)"""
        self._auto_commit_delay = delay_ms
    
    def set_escape_cancels(self, enabled: bool) -> None:
        """Set whether Escape key cancels editing"""
        self._escape_cancels = enabled
    
    def set_click_outside_commits(self, enabled: bool) -> None:
        """Set whether clicking outside commits editing"""
        self._click_outside_commits = enabled
    
    def set_tab_advances(self, enabled: bool) -> None:
        """Set whether Tab key advances to next property"""
        self._tab_advances = enabled


class InlineEditableWidget(QWidget):
    """Mixin widget that supports inline editing"""
    
    # Signals
    inline_edit_requested = pyqtSignal(str, str, object, QWidget)  # prop_name, prop_type, value, widget
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._inline_manager: Optional[InlineEditingManager] = None
        self._property_mappings: Dict[str, Tuple[str, Any]] = {}  # widget_id -> (property_name, property_type)
        self._click_count = 0
        self._last_click_time = 0
        self._double_click_threshold = 500  # ms
    
    def set_inline_manager(self, manager: InlineEditingManager) -> None:
        """Set the inline editing manager"""
        self._inline_manager = manager
        self.inline_edit_requested.connect(
            lambda name, ptype, value, widget: manager.start_inline_edit(
                name, ptype, value, widget, activation_mode=InlineEditMode.PROGRAMMATIC
            )
        )
    
    def register_property_widget(self, widget: QWidget, property_name: str, 
                                property_type: str) -> None:
        """Register a widget for inline editing of a property"""
        widget_id = id(widget)
        self._property_mappings[widget_id] = (property_name, property_type)
        
        # Install event filter on widget
        widget.installEventFilter(self)
    
    def unregister_property_widget(self, widget: QWidget) -> None:
        """Unregister a widget from inline editing"""
        widget_id = id(widget)
        if widget_id in self._property_mappings:
            del self._property_mappings[widget_id]
        
        widget.removeEventFilter(self)
    
    def eventFilter(self, obj: QObject, event) -> bool:
        """Event filter for inline editing activation"""
        if not self._inline_manager:
            return False
        
        widget_id = id(obj)
        if widget_id not in self._property_mappings:
            return False
        
        property_name, property_type = self._property_mappings[widget_id]
        
        # Handle mouse events for activation
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                current_time = QApplication.instance().time()
                
                # Check for double-click
                if (current_time - self._last_click_time < self._double_click_threshold and
                    self._click_count == 1):
                    # Double-click detected
                    self._click_count = 0
                    self._request_inline_edit(obj, property_name, property_type, 
                                            InlineEditMode.DOUBLE_CLICK)
                    return True
                else:
                    # Single click
                    self._click_count = 1
                    self._last_click_time = current_time
                    
                    # Check if single-click editing is enabled
                    if (self._inline_manager and
                        InlineEditMode.SINGLE_CLICK in self._inline_manager._activation_modes):
                        self._request_inline_edit(obj, property_name, property_type,
                                                InlineEditMode.SINGLE_CLICK)
                        return True
        
        # Handle key events for activation
        elif event.type() == event.Type.KeyPress:
            key_event = event
            
            # F2 or Enter starts editing
            if (key_event.key() in [Qt.Key.Key_F2, Qt.Key.Key_Return, Qt.Key.Key_Enter] and
                InlineEditMode.KEY_PRESS in self._inline_manager._activation_modes):
                self._request_inline_edit(obj, property_name, property_type,
                                        InlineEditMode.KEY_PRESS)
                return True
        
        return False
    
    def _request_inline_edit(self, widget: QWidget, property_name: str, 
                           property_type: str, activation_mode: InlineEditMode) -> None:
        """Request inline editing for a property"""
        # Get current value (override in subclasses)
        current_value = self._get_property_value(property_name)
        
        self.inline_edit_requested.emit(property_name, property_type, 
                                      current_value, widget)
    
    def _get_property_value(self, property_name: str) -> Any:
        """Get current value for property (override in subclasses)"""
        return None