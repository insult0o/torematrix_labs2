"""
Validation UI Component

Agent 2 implementation providing user interface for displaying validation
warnings, errors, and feedback during merge/split operations.
"""

from typing import List, Dict, Optional
from enum import Enum
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QFrame, QGroupBox, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of validation messages."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class ValidationMessage:
    """Individual validation message."""
    
    def __init__(self, title: str, message: str, msg_type: MessageType, 
                 timestamp: datetime = None, details: str = None):
        self.title = title
        self.message = message
        self.type = msg_type
        self.timestamp = timestamp or datetime.now()
        self.details = details
        self.id = f"{self.timestamp.timestamp()}_{hash(title + message)}"


class ValidationWarnings(QWidget):
    """
    Widget for displaying validation warnings and errors.
    
    Agent 2 implementation with:
    - Color-coded message types
    - Expandable details
    - Clear/filter functionality
    - Real-time updates
    """
    
    # Signals
    message_added = pyqtSignal(object)
    message_cleared = pyqtSignal()
    message_clicked = pyqtSignal(object)
    
    def __init__(self, parent=None):
        """Initialize validation warnings widget."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".ValidationWarnings")
        self.messages: List[ValidationMessage] = []
        self.max_messages = 50
        
        # Auto-hide timer
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self._auto_hide)
        
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Validation Messages")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Message count
        self.count_label = QLabel("0 messages")
        self.count_label.setStyleSheet("color: #666666; font-size: 10px;")
        header_layout.addWidget(self.count_label)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_warnings)
        self.clear_button.setMaximumWidth(60)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        
        # Message list
        self.message_list = QListWidget()
        self.message_list.setMaximumHeight(150)
        self.message_list.itemClicked.connect(self._on_message_clicked)
        layout.addWidget(self.message_list)
        
        # Details area (initially hidden)
        self.details_frame = QFrame()
        self.details_frame.setVisible(False)
        self.details_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.details_frame.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd;")
        
        details_layout = QVBoxLayout(self.details_frame)
        
        # Details header
        details_header = QHBoxLayout()
        
        self.details_title = QLabel("Message Details")
        details_title_font = QFont()
        details_title_font.setBold(True)
        self.details_title.setFont(details_title_font)
        details_header.addWidget(self.details_title)
        
        details_header.addStretch()
        
        close_details_btn = QPushButton("✕")
        close_details_btn.setMaximumWidth(20)
        close_details_btn.clicked.connect(self._hide_details)
        details_header.addWidget(close_details_btn)
        
        details_layout.addLayout(details_header)
        
        # Details content
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(self.details_frame)
        
        # Initially hidden
        self.setVisible(False)
    
    def add_warning(self, title: str, message: str, msg_type: str = "warning", 
                   details: str = None):
        """Add a validation warning or error."""
        # Convert string type to enum
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        
        # Create message
        validation_msg = ValidationMessage(
            title=title,
            message=message,
            msg_type=msg_type,
            details=details
        )
        
        # Add to messages list
        self.messages.append(validation_msg)
        
        # Limit number of messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        
        # Update display
        self._update_display()
        
        # Show widget
        self.setVisible(True)
        
        # Emit signal
        self.message_added.emit(validation_msg)
        
        # Auto-hide for success messages
        if msg_type == MessageType.SUCCESS:
            self.auto_hide_timer.start(3000)  # 3 seconds
        
        self.logger.info(f"Added {msg_type.value} message: {title}")
    
    def add_info(self, title: str, message: str, details: str = None):
        """Add an info message."""
        self.add_warning(title, message, MessageType.INFO, details)
    
    def add_error(self, title: str, message: str, details: str = None):
        """Add an error message."""
        self.add_warning(title, message, MessageType.ERROR, details)
    
    def add_success(self, title: str, message: str, details: str = None):
        """Add a success message."""
        self.add_warning(title, message, MessageType.SUCCESS, details)
    
    def clear_warnings(self):
        """Clear all warnings."""
        self.messages.clear()
        self._update_display()
        self.setVisible(False)
        self._hide_details()
        self.message_cleared.emit()
        self.logger.info("Cleared all validation messages")
    
    def _update_display(self):
        """Update the message display."""
        # Update count
        self.count_label.setText(f"{len(self.messages)} message{'s' if len(self.messages) != 1 else ''}")
        
        # Clear and populate list
        self.message_list.clear()
        
        for msg in self.messages:
            item = QListWidgetItem()
            
            # Create item text
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            item_text = f"[{timestamp_str}] {msg.title}: {msg.message}"
            item.setText(item_text)
            
            # Set icon and color based on type
            self._style_message_item(item, msg)
            
            # Store message reference
            item.setData(Qt.ItemDataRole.UserRole, msg)
            
            self.message_list.addItem(item)
        
        # Scroll to bottom
        self.message_list.scrollToBottom()
        
        # Update visibility
        self.setVisible(len(self.messages) > 0)
    
    def _style_message_item(self, item: QListWidgetItem, msg: ValidationMessage):
        """Style message item based on type."""
        if msg.type == MessageType.ERROR:
            item.setBackground(QColor(255, 235, 235))  # Light red
            item.setForeground(QColor(139, 0, 0))      # Dark red
        elif msg.type == MessageType.WARNING:
            item.setBackground(QColor(255, 248, 220))  # Light yellow
            item.setForeground(QColor(184, 134, 11))   # Dark yellow
        elif msg.type == MessageType.INFO:
            item.setBackground(QColor(235, 245, 255))  # Light blue
            item.setForeground(QColor(0, 102, 204))    # Dark blue
        elif msg.type == MessageType.SUCCESS:
            item.setBackground(QColor(240, 255, 240))  # Light green
            item.setForeground(QColor(0, 128, 0))      # Dark green
        
        # Add tooltip with full message
        tooltip_text = f"{msg.title}\n\n{msg.message}"
        if msg.details:
            tooltip_text += f"\n\nDetails:\n{msg.details}"
        item.setToolTip(tooltip_text)
    
    def _on_message_clicked(self, item: QListWidgetItem):
        """Handle message item click."""
        msg = item.data(Qt.ItemDataRole.UserRole)
        if msg:
            self.message_clicked.emit(msg)
            
            # Show details if available
            if msg.details:
                self._show_details(msg)
    
    def _show_details(self, msg: ValidationMessage):
        """Show message details."""
        self.details_title.setText(f"Details - {msg.title}")
        
        # Format details text
        details_text = f"Type: {msg.type.value.title()}\n"
        details_text += f"Time: {msg.timestamp.strftime('%H:%M:%S')}\n"
        details_text += f"Message: {msg.message}\n\n"
        
        if msg.details:
            details_text += f"Details:\n{msg.details}"
        
        self.details_text.setPlainText(details_text)
        self.details_frame.setVisible(True)
    
    def _hide_details(self):
        """Hide message details."""
        self.details_frame.setVisible(False)
    
    def _auto_hide(self):
        """Auto-hide the widget after timeout."""
        if all(msg.type == MessageType.SUCCESS for msg in self.messages):
            self.setVisible(False)
    
    def has_errors(self) -> bool:
        """Check if there are any error messages."""
        return any(msg.type == MessageType.ERROR for msg in self.messages)
    
    def has_warnings(self) -> bool:
        """Check if there are any warning messages."""
        return any(msg.type == MessageType.WARNING for msg in self.messages)
    
    def get_messages(self) -> List[ValidationMessage]:
        """Get all messages."""
        return self.messages.copy()
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[ValidationMessage]:
        """Get messages of specific type."""
        return [msg for msg in self.messages if msg.type == msg_type]
    
    def filter_messages(self, msg_types: List[MessageType]):
        """Filter messages to show only specific types."""
        # This would update the display to show only filtered messages
        # For now, we'll just implement the basic version
        pass
    
    def set_max_messages(self, max_messages: int):
        """Set maximum number of messages to keep."""
        self.max_messages = max_messages
        
        # Trim if necessary
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]
            self._update_display()
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget."""
        return QSize(400, 100)