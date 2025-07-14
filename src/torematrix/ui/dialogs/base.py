"""Base dialog implementation for ToreMatrix UI framework.

This module provides the foundation for all dialog types with common
functionality including state management, keyboard navigation, and
theme integration.
"""

from typing import Optional, List, Dict, Any, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
import asyncio
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal as Signal
from PyQt6.QtGui import QKeyEvent, QCloseEvent, QPalette

from ...core.events import Event, DocumentEventTypes, EventBus
from ...core.state import Store as StateManager

logger = logging.getLogger(__name__)


class DialogResult(Enum):
    """Possible dialog results."""
    OK = auto()
    CANCEL = auto()
    YES = auto()
    NO = auto()
    RETRY = auto()
    ABORT = auto()
    CUSTOM = auto()


@dataclass
class DialogButton:
    """Configuration for a dialog button."""
    text: str
    result: DialogResult
    is_default: bool = False
    is_destructive: bool = False
    callback: Optional[Callable[[], None]] = None
    enabled: bool = True
    tooltip: Optional[str] = None


@dataclass
class DialogState:
    """State information for a dialog."""
    dialog_id: str
    is_open: bool = False
    is_modal: bool = True
    result: Optional[DialogResult] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None


class BaseDialog(QDialog):
    """Base class for all dialogs with common functionality.
    
    Provides:
    - State management integration
    - Event bus support
    - Keyboard navigation
    - Theme integration
    - Animation support
    - Async operation support
    """
    
    # Signals
    dialog_opened = Signal(str)  # dialog_id
    dialog_closed = Signal(str, DialogResult)  # dialog_id, result
    state_changed = Signal(dict)  # state data
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        modal: bool = True,
        width: int = 400,
        height: int = 300,
        dialog_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None
    ):
        """Initialize the base dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            modal: Whether dialog is modal
            width: Initial width
            height: Initial height
            dialog_id: Unique dialog identifier
            event_bus: Event bus instance
            state_manager: State manager instance
        """
        super().__init__(parent)
        
        # Core properties
        self.dialog_id = dialog_id or f"dialog_{id(self)}"
        self.event_bus = event_bus
        self.state_manager = state_manager
        self._result = DialogResult.CANCEL
        
        # State
        self.state = DialogState(
            dialog_id=self.dialog_id,
            is_modal=modal
        )
        
        # Configuration
        self.setWindowTitle(title)
        self.setModal(modal)
        self.resize(width, height)
        
        # Setup
        self._setup_ui()
        self._setup_keyboard_navigation()
        self._setup_animations()
        self._register_with_state_manager()
        
        # Track in dialog manager
        if hasattr(parent, 'dialog_manager'):
            parent.dialog_manager.register_dialog(self)
    
    def _setup_ui(self) -> None:
        """Setup the base UI structure."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_widget, 1)
        
        # Button area
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(8)
        self.main_layout.addLayout(self.button_layout)
        
        # Default styling
        self.setStyleSheet(self._get_default_style())
    
    def _setup_keyboard_navigation(self) -> None:
        """Setup keyboard navigation handlers."""
        # Will be implemented with tab order and shortcuts
        pass
    
    def _setup_animations(self) -> None:
        """Setup dialog animations."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(200)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    def _register_with_state_manager(self) -> None:
        """Register dialog state with state manager."""
        if self.state_manager:
            self.state_manager.dispatch({
                'type': 'DIALOG_REGISTER',
                'payload': {
                    'dialog_id': self.dialog_id,
                    'state': self.state
                }
            })
    
    def _get_default_style(self) -> str:
        """Get default dialog styling."""
        return """
        QDialog {
            background-color: palette(window);
            border: 1px solid palette(mid);
            border-radius: 8px;
        }
        QPushButton {
            min-width: 80px;
            min-height: 28px;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QPushButton:default {
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }
        QPushButton:destructive {
            background-color: #dc3545;
            color: white;
        }
        """
    
    def add_button(self, button: DialogButton) -> QPushButton:
        """Add a button to the dialog.
        
        Args:
            button: Button configuration
            
        Returns:
            The created QPushButton
        """
        btn = QPushButton(button.text)
        btn.setEnabled(button.enabled)
        
        if button.tooltip:
            btn.setToolTip(button.tooltip)
        
        if button.is_default:
            btn.setDefault(True)
            btn.setProperty("default", True)
        
        if button.is_destructive:
            btn.setProperty("destructive", True)
        
        # Connect handler
        def handle_click():
            if button.callback:
                button.callback()
            self._result = button.result
            self.accept() if button.result != DialogResult.CANCEL else self.reject()
        
        btn.clicked.connect(handle_click)
        
        # Add to layout
        if button.is_default or button.is_destructive:
            self.button_layout.addStretch()
        self.button_layout.addWidget(btn)
        
        return btn
    
    def add_standard_buttons(self, buttons: List[DialogResult]) -> None:
        """Add standard button set to dialog.
        
        Args:
            buttons: List of standard buttons to add
        """
        button_configs = {
            DialogResult.OK: DialogButton("OK", DialogResult.OK, is_default=True),
            DialogResult.CANCEL: DialogButton("Cancel", DialogResult.CANCEL),
            DialogResult.YES: DialogButton("Yes", DialogResult.YES, is_default=True),
            DialogResult.NO: DialogButton("No", DialogResult.NO),
            DialogResult.RETRY: DialogButton("Retry", DialogResult.RETRY),
            DialogResult.ABORT: DialogButton("Abort", DialogResult.ABORT, is_destructive=True)
        }
        
        for result in buttons:
            if result in button_configs:
                self.add_button(button_configs[result])
    
    def set_content(self, widget: QWidget) -> None:
        """Set the main content widget.
        
        Args:
            widget: Widget to set as content
        """
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new content
        self.content_layout.addWidget(widget)
    
    def show_animated(self) -> None:
        """Show dialog with fade animation."""
        self.setWindowOpacity(0)
        self.show()
        
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()
    
    def hide_animated(self) -> None:
        """Hide dialog with fade animation."""
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.start()
    
    def get_result(self) -> DialogResult:
        """Get the dialog result.
        
        Returns:
            The dialog result
        """
        return self._result
    
    def get_state(self) -> DialogState:
        """Get current dialog state.
        
        Returns:
            Current dialog state
        """
        return self.state
    
    def update_state(self, data: Dict[str, Any]) -> None:
        """Update dialog state data.
        
        Args:
            data: Data to merge into state
        """
        self.state.data.update(data)
        self.state_changed.emit(self.state.data)
        
        if self.state_manager:
            self.state_manager.dispatch({
                'type': 'DIALOG_UPDATE',
                'payload': {
                    'dialog_id': self.dialog_id,
                    'data': data
                }
            })
    
    async def show_async(self) -> DialogResult:
        """Show dialog and wait for result asynchronously.
        
        Returns:
            The dialog result
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        def on_finished(result: int):
            loop.call_soon_threadsafe(future.set_result, self._result)
        
        self.finished.connect(on_finished)
        self.show()
        
        return await future
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for navigation.
        
        Args:
            event: Key event
        """
        if event.key() == Qt.Key.Key_Escape:
            self._result = DialogResult.CANCEL
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def showEvent(self, event) -> None:
        """Handle show event."""
        super().showEvent(event)
        
        self.state.is_open = True
        self.dialog_opened.emit(self.dialog_id)
        
        if self.event_bus:
            self.event_bus.emit(Event(
                type=EventType.UI_STATE_CHANGED,
                data={
                    'dialog_id': self.dialog_id,
                    'action': 'opened'
                }
            ))
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle close event."""
        self.state.is_open = False
        self.state.closed_at = datetime.now()
        self.dialog_closed.emit(self.dialog_id, self._result)
        
        if self.event_bus:
            self.event_bus.emit(Event(
                type=EventType.UI_STATE_CHANGED,
                data={
                    'dialog_id': self.dialog_id,
                    'action': 'closed',
                    'result': self._result.name
                }
            ))
        
        if self.state_manager:
            self.state_manager.dispatch({
                'type': 'DIALOG_CLOSE',
                'payload': {
                    'dialog_id': self.dialog_id,
                    'result': self._result
                }
            })
        
        super().closeEvent(event)


class DialogManager:
    """Manages dialog instances and stacking."""
    
    def __init__(self):
        self._dialogs: Dict[str, BaseDialog] = {}
        self._dialog_stack: List[str] = []
        
    def register_dialog(self, dialog: BaseDialog) -> None:
        """Register a dialog instance.
        
        Args:
            dialog: Dialog to register
        """
        self._dialogs[dialog.dialog_id] = dialog
        if dialog.isModal():
            self._dialog_stack.append(dialog.dialog_id)
    
    def unregister_dialog(self, dialog_id: str) -> None:
        """Unregister a dialog.
        
        Args:
            dialog_id: ID of dialog to unregister
        """
        if dialog_id in self._dialogs:
            del self._dialogs[dialog_id]
            if dialog_id in self._dialog_stack:
                self._dialog_stack.remove(dialog_id)
    
    def get_top_dialog(self) -> Optional[BaseDialog]:
        """Get the topmost dialog.
        
        Returns:
            Top dialog or None
        """
        if self._dialog_stack:
            return self._dialogs.get(self._dialog_stack[-1])
        return None
    
    def close_all(self) -> None:
        """Close all open dialogs."""
        for dialog in list(self._dialogs.values()):
            dialog.close()