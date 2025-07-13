"""Confirmation dialog implementation.

Provides customizable confirmation dialogs with various
button combinations and icon support.
"""

from typing import Optional, List, Callable
from enum import Enum, auto

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QCheckBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

from .base import BaseDialog, DialogResult, DialogButton

class MessageType(Enum):
    """Types of confirmation messages."""
    INFORMATION = auto()
    WARNING = auto()
    ERROR = auto()
    QUESTION = auto()
    SUCCESS = auto()


class ConfirmationDialog(BaseDialog):
    """Customizable confirmation dialog.
    
    Features:
    - Multiple message types with icons
    - Customizable button sets
    - Optional detailed text
    - Don't show again option
    - Custom content support
    """
    
    # Standard button sets
    BUTTONS_OK = [DialogResult.OK]
    BUTTONS_OK_CANCEL = [DialogResult.OK, DialogResult.CANCEL]
    BUTTONS_YES_NO = [DialogResult.YES, DialogResult.NO]
    BUTTONS_YES_NO_CANCEL = [DialogResult.YES, DialogResult.NO, DialogResult.CANCEL]
    BUTTONS_RETRY_CANCEL = [DialogResult.RETRY, DialogResult.CANCEL]
    BUTTONS_ABORT_RETRY_IGNORE = [DialogResult.ABORT, DialogResult.RETRY, DialogResult.CANCEL]
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Confirmation",
        message: str = "",
        message_type: MessageType = MessageType.INFORMATION,
        detailed_text: Optional[str] = None,
        buttons: Optional[List[DialogResult]] = None,
        default_button: Optional[DialogResult] = None,
        show_dont_ask: bool = False,
        dont_ask_text: str = "Don't show this message again",
        custom_widget: Optional[QWidget] = None,
        **kwargs
    ):
        """Initialize confirmation dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Main message text
            message_type: Type of message
            detailed_text: Optional detailed explanation
            buttons: Button set to show
            default_button: Default button
            show_dont_ask: Show don't ask checkbox
            dont_ask_text: Text for don't ask checkbox
            custom_widget: Custom widget to add
            **kwargs: Additional BaseDialog arguments
        """
        super().__init__(parent, title, **kwargs)
        
        self.message = message
        self.message_type = message_type
        self.detailed_text = detailed_text
        self.buttons = buttons or self.BUTTONS_OK
        self.default_button = default_button or self.buttons[0]
        self.show_dont_ask = show_dont_ask
        self.dont_ask_text = dont_ask_text
        self.custom_widget = custom_widget
        self.dont_ask_checked = False
        
        self._setup_confirmation_ui()
    
    def _setup_confirmation_ui(self) -> None:
        """Setup the confirmation dialog UI."""
        # Main message layout
        message_layout = QHBoxLayout()
        message_layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel()
        icon_pixmap = self._get_icon_pixmap()
        if icon_pixmap:
            icon_label.setPixmap(icon_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            message_layout.addWidget(icon_label)
        
        # Message content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        
        # Main message
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        content_layout.addWidget(self.message_label)
        
        # Detailed text
        if self.detailed_text:
            self.details_text = QTextEdit()
            self.details_text.setPlainText(self.detailed_text)
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(150)
            content_layout.addWidget(self.details_text)
        
        # Custom widget
        if self.custom_widget:
            content_layout.addWidget(self.custom_widget)
        
        message_layout.addLayout(content_layout, 1)
        self.content_layout.addLayout(message_layout)
        
        # Don't ask checkbox
        if self.show_dont_ask:
            self.dont_ask_checkbox = QCheckBox(self.dont_ask_text)
            self.dont_ask_checkbox.stateChanged.connect(self._on_dont_ask_changed)
            self.content_layout.addWidget(self.dont_ask_checkbox)
        
        # Add spacing
        self.content_layout.addStretch()
        
        # Add buttons
        self._add_confirmation_buttons()
    
    def _get_icon_pixmap(self) -> Optional[QPixmap]:
        """Get appropriate icon for message type.
        
        Returns:
            Icon pixmap or None
        """
        # Using standard icons from style
        style = self.style()
        icon_map = {
            MessageType.INFORMATION: style.StandardPixmap.SP_MessageBoxInformation,
            MessageType.WARNING: style.StandardPixmap.SP_MessageBoxWarning,
            MessageType.ERROR: style.StandardPixmap.SP_MessageBoxCritical,
            MessageType.QUESTION: style.StandardPixmap.SP_MessageBoxQuestion,
            MessageType.SUCCESS: style.StandardPixmap.SP_DialogApplyButton
        }
        
        if self.message_type in icon_map:
            icon = style.standardIcon(icon_map[self.message_type])
            return icon.pixmap(48, 48)
        
        return None
    
    def _add_confirmation_buttons(self) -> None:
        """Add confirmation buttons."""
        button_configs = {
            DialogResult.OK: ("OK", False),
            DialogResult.CANCEL: ("Cancel", False),
            DialogResult.YES: ("Yes", False),
            DialogResult.NO: ("No", False),
            DialogResult.RETRY: ("Retry", False),
            DialogResult.ABORT: ("Abort", True)  # Destructive
        }
        
        for result in self.buttons:
            if result in button_configs:
                text, is_destructive = button_configs[result]
                button = DialogButton(
                    text=text,
                    result=result,
                    is_default=(result == self.default_button),
                    is_destructive=is_destructive
                )
                self.add_button(button)
    
    def _on_dont_ask_changed(self, state: int) -> None:
        """Handle don't ask checkbox state change.
        
        Args:
            state: Checkbox state
        """
        self.dont_ask_checked = (state == Qt.CheckState.Checked.value)
        
        # Update state
        self.update_state({'dont_ask_again': self.dont_ask_checked})
    
    def set_message(self, message: str) -> None:
        """Update the main message.
        
        Args:
            message: New message text
        """
        self.message = message
        if hasattr(self, 'message_label'):
            self.message_label.setText(message)
    
    def set_detailed_text(self, text: str) -> None:
        """Set or update detailed text.
        
        Args:
            text: Detailed text
        """
        self.detailed_text = text
        if hasattr(self, 'details_text'):
            self.details_text.setPlainText(text)
        else:
            # Create details widget if not exists
            self.details_text = QTextEdit()
            self.details_text.setPlainText(text)
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(150)
            self.content_layout.insertWidget(1, self.details_text)
    
    def get_dont_ask_checked(self) -> bool:
        """Get don't ask checkbox state.
        
        Returns:
            Whether don't ask is checked
        """
        return self.dont_ask_checked


def confirm(
    parent: Optional[QWidget] = None,
    title: str = "Confirm",
    message: str = "Are you sure?",
    message_type: MessageType = MessageType.QUESTION,
    buttons: Optional[List[DialogResult]] = None,
    **kwargs
) -> DialogResult:
    """Show confirmation dialog and return result.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Confirmation message
        message_type: Type of message
        buttons: Buttons to show
        **kwargs: Additional dialog arguments
        
    Returns:
        Selected dialog result
    """
    dialog = ConfirmationDialog(
        parent,
        title,
        message,
        message_type,
        buttons=buttons or ConfirmationDialog.BUTTONS_YES_NO,
        **kwargs
    )
    dialog.exec()
    return dialog.get_result()


def alert(
    parent: Optional[QWidget] = None,
    title: str = "Alert",
    message: str = "",
    message_type: MessageType = MessageType.WARNING,
    **kwargs
) -> None:
    """Show alert dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Alert message
        message_type: Type of message
        **kwargs: Additional dialog arguments
    """
    dialog = ConfirmationDialog(
        parent,
        title,
        message,
        message_type,
        buttons=ConfirmationDialog.BUTTONS_OK,
        **kwargs
    )
    dialog.exec()


def error(
    parent: Optional[QWidget] = None,
    title: str = "Error",
    message: str = "",
    detailed_text: Optional[str] = None,
    **kwargs
) -> None:
    """Show error dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Error message
        detailed_text: Detailed error information
        **kwargs: Additional dialog arguments
    """
    dialog = ConfirmationDialog(
        parent,
        title,
        message,
        MessageType.ERROR,
        detailed_text=detailed_text,
        buttons=ConfirmationDialog.BUTTONS_OK,
        **kwargs
    )
    dialog.exec()


def info(
    parent: Optional[QWidget] = None,
    title: str = "Information",
    message: str = "",
    **kwargs
) -> None:
    """Show information dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Information message
        **kwargs: Additional dialog arguments
    """
    dialog = ConfirmationDialog(
        parent,
        title,
        message,
        MessageType.INFORMATION,
        buttons=ConfirmationDialog.BUTTONS_OK,
        **kwargs
    )
    dialog.exec()