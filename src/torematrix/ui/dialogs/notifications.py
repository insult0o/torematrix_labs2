"""Non-modal notification system implementation.

Provides toast notifications, notification management,
and integration with the application's notification area.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsOpacityEffect,
    QApplication, QStyle
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation,
    QRect, QPoint, QEasingCurve, QParallelAnimationGroup
)
from PySide6.QtGui import QPainter, QColor, QPalette, QBrush

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CUSTOM = auto()


class NotificationPosition(Enum):
    """Notification display positions."""
    TOP_RIGHT = auto()
    TOP_LEFT = auto()
    TOP_CENTER = auto()
    BOTTOM_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    CENTER = auto()


@dataclass
class NotificationData:
    """Data for a notification."""
    id: str
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    icon: Optional[str] = None
    duration: int = 5000  # milliseconds, 0 for persistent
    closable: bool = True
    actions: List[tuple[str, Callable]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToastNotification(QFrame):
    """Individual toast notification widget.
    
    Features:
    - Animated appearance/disappearance
    - Auto-dismiss with timer
    - Action buttons
    - Close button
    - Type-based styling
    """
    
    # Signals
    closed = Signal(str)  # notification_id
    action_clicked = Signal(str, str)  # notification_id, action_name
    
    def __init__(
        self,
        data: NotificationData,
        parent: Optional[QWidget] = None
    ):
        """Initialize toast notification.
        
        Args:
            data: Notification data
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.data = data
        self._opacity_effect = QGraphicsOpacityEffect()
        self._close_timer: Optional[QTimer] = None
        
        self._setup_ui()
        self._apply_styling()
        
        # Auto-close timer
        if data.duration > 0:
            self._close_timer = QTimer()
            self._close_timer.timeout.connect(self.close_animated)
            self._close_timer.start(data.duration)
    
    def _setup_ui(self) -> None:
        """Setup the notification UI."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setGraphicsEffect(self._opacity_effect)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Icon
        if self.data.icon:
            icon_label = QLabel()
            # Load icon based on type or custom icon
            style = self.style()
            icon_map = {
                NotificationType.INFO: style.StandardPixmap.SP_MessageBoxInformation,
                NotificationType.SUCCESS: style.StandardPixmap.SP_DialogApplyButton,
                NotificationType.WARNING: style.StandardPixmap.SP_MessageBoxWarning,
                NotificationType.ERROR: style.StandardPixmap.SP_MessageBoxCritical
            }
            
            if self.data.type in icon_map:
                icon = style.standardIcon(icon_map[self.data.type])
                icon_label.setPixmap(icon.pixmap(24, 24))
                header_layout.addWidget(icon_label)
        
        # Title
        self.title_label = QLabel(self.data.title)
        self.title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.title_label, 1)
        
        # Close button
        if self.data.closable:
            close_button = QPushButton("×")
            close_button.setFixedSize(20, 20)
            close_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }
            """)
            close_button.clicked.connect(self.close_animated)
            header_layout.addWidget(close_button)
        
        main_layout.addLayout(header_layout)
        
        # Message
        if self.data.message:
            self.message_label = QLabel(self.data.message)
            self.message_label.setWordWrap(True)
            self.message_label.setStyleSheet("color: palette(text);")
            main_layout.addWidget(self.message_label)
        
        # Actions
        if self.data.actions:
            action_layout = QHBoxLayout()
            action_layout.setSpacing(4)
            
            for action_text, action_callback in self.data.actions:
                action_button = QPushButton(action_text)
                action_button.setStyleSheet("""
                    QPushButton {
                        border: 1px solid palette(mid);
                        padding: 2px 8px;
                        border-radius: 3px;
                        background: transparent;
                    }
                    QPushButton:hover {
                        background: palette(button);
                    }
                """)
                action_button.clicked.connect(
                    lambda checked, t=action_text: self._on_action_clicked(t)
                )
                action_layout.addWidget(action_button)
            
            action_layout.addStretch()
            main_layout.addLayout(action_layout)
        
        # Set size constraints
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
    
    def _apply_styling(self) -> None:
        """Apply type-based styling."""
        color_map = {
            NotificationType.INFO: "#2196F3",
            NotificationType.SUCCESS: "#4CAF50",
            NotificationType.WARNING: "#FF9800",
            NotificationType.ERROR: "#F44336"
        }
        
        accent_color = color_map.get(self.data.type, "#2196F3")
        
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: palette(window);
                border: 2px solid {accent_color};
                border-radius: 8px;
            }}
        """)
    
    def _on_action_clicked(self, action_text: str) -> None:
        """Handle action button click.
        
        Args:
            action_text: Text of clicked action
        """
        # Find and execute callback
        for text, callback in self.data.actions:
            if text == action_text:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Action callback error: {e}")
                
                self.action_clicked.emit(self.data.id, action_text)
                break
        
        # Close notification after action
        self.close_animated()
    
    def show_animated(self) -> None:
        """Show notification with fade animation."""
        self.show()
        
        # Fade in
        self._opacity_effect.setOpacity(0)
        self.fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()
    
    def close_animated(self) -> None:
        """Close notification with fade animation."""
        if self._close_timer:
            self._close_timer.stop()
        
        # Fade out
        self.fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self._on_close_finished)
        self.fade_animation.start()
    
    def _on_close_finished(self) -> None:
        """Handle close animation completion."""
        self.closed.emit(self.data.id)
        self.deleteLater()
    
    def pause_auto_close(self) -> None:
        """Pause auto-close timer."""
        if self._close_timer:
            self._close_timer.stop()
    
    def resume_auto_close(self) -> None:
        """Resume auto-close timer."""
        if self._close_timer and self.data.duration > 0:
            self._close_timer.start(self.data.duration)
    
    def enterEvent(self, event) -> None:
        """Handle mouse enter - pause auto close."""
        super().enterEvent(event)
        self.pause_auto_close()
    
    def leaveEvent(self, event) -> None:
        """Handle mouse leave - resume auto close."""
        super().leaveEvent(event)
        self.resume_auto_close()


class NotificationManager(QWidget):
    """Manages toast notifications for the application.
    
    Features:
    - Multiple notification positions
    - Notification stacking
    - History tracking
    - Filtering and search
    - Batch operations
    """
    
    # Signals
    notification_shown = Signal(NotificationData)
    notification_closed = Signal(str)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        position: NotificationPosition = NotificationPosition.TOP_RIGHT,
        max_visible: int = 5,
        spacing: int = 10,
        offset: tuple[int, int] = (20, 20)
    ):
        """Initialize notification manager.
        
        Args:
            parent: Parent widget (usually main window)
            position: Default notification position
            max_visible: Maximum visible notifications
            spacing: Spacing between notifications
            offset: Offset from screen edges (x, y)
        """
        super().__init__(parent)
        
        self.position = position
        self.max_visible = max_visible
        self.spacing = spacing
        self.offset = offset
        
        self._notifications: Dict[str, ToastNotification] = {}
        self._notification_queue: List[NotificationData] = []
        self._notification_history: List[NotificationData] = []
        self._notification_counter = 0
        
        # Make transparent and non-interactive
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        if parent:
            self.resize(parent.size())
    
    def show_notification(
        self,
        title: str,
        message: str = "",
        type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        **kwargs
    ) -> str:
        """Show a notification.
        
        Args:
            title: Notification title
            message: Notification message
            type: Notification type
            duration: Display duration in ms
            **kwargs: Additional NotificationData fields
            
        Returns:
            Notification ID
        """
        # Create notification data
        self._notification_counter += 1
        notification_id = f"notification_{self._notification_counter}"
        
        data = NotificationData(
            id=notification_id,
            title=title,
            message=message,
            type=type,
            duration=duration,
            **kwargs
        )
        
        # Add to history
        self._notification_history.append(data)
        
        # Check if can show immediately
        if len(self._notifications) < self.max_visible:
            self._show_notification(data)
        else:
            # Add to queue
            self._notification_queue.append(data)
        
        self.notification_shown.emit(data)
        return notification_id
    
    def _show_notification(self, data: NotificationData) -> None:
        """Show a notification widget.
        
        Args:
            data: Notification data
        """
        # Create notification widget
        notification = ToastNotification(data, self)
        notification.closed.connect(self._on_notification_closed)
        
        # Position notification
        self._position_notification(notification)
        
        # Track notification
        self._notifications[data.id] = notification
        
        # Show with animation
        notification.show_animated()
    
    def _position_notification(self, notification: ToastNotification) -> None:
        """Position notification based on settings.
        
        Args:
            notification: Notification to position
        """
        # Get parent geometry
        if self.parent():
            parent_rect = self.parent().rect()
        else:
            parent_rect = QApplication.primaryScreen().geometry()
        
        # Calculate base position
        x, y = self.offset
        
        # Get existing notifications for stacking
        visible_notifications = list(self._notifications.values())
        stack_index = visible_notifications.index(notification) if notification in visible_notifications else len(visible_notifications) - 1
        
        # Calculate offset for stacking
        if stack_index > 0:
            total_height = sum(n.height() + self.spacing for n in visible_notifications[:stack_index])
        else:
            total_height = 0
        
        # Position based on anchor
        if self.position == NotificationPosition.TOP_RIGHT:
            x = parent_rect.width() - notification.width() - x
            y = y + total_height
            
        elif self.position == NotificationPosition.TOP_LEFT:
            x = x
            y = y + total_height
            
        elif self.position == NotificationPosition.TOP_CENTER:
            x = (parent_rect.width() - notification.width()) // 2
            y = y + total_height
            
        elif self.position == NotificationPosition.BOTTOM_RIGHT:
            x = parent_rect.width() - notification.width() - x
            y = parent_rect.height() - notification.height() - y - total_height
            
        elif self.position == NotificationPosition.BOTTOM_LEFT:
            x = x
            y = parent_rect.height() - notification.height() - y - total_height
            
        elif self.position == NotificationPosition.BOTTOM_CENTER:
            x = (parent_rect.width() - notification.width()) // 2
            y = parent_rect.height() - notification.height() - y - total_height
            
        elif self.position == NotificationPosition.CENTER:
            x = (parent_rect.width() - notification.width()) // 2
            y = (parent_rect.height() - notification.height()) // 2
        
        notification.move(x, y)
    
    def _on_notification_closed(self, notification_id: str) -> None:
        """Handle notification close.
        
        Args:
            notification_id: ID of closed notification
        """
        # Remove from tracking
        if notification_id in self._notifications:
            del self._notifications[notification_id]
        
        # Reposition remaining notifications
        self._reposition_notifications()
        
        # Show queued notification if any
        if self._notification_queue:
            next_data = self._notification_queue.pop(0)
            self._show_notification(next_data)
        
        self.notification_closed.emit(notification_id)
    
    def _reposition_notifications(self) -> None:
        """Reposition all visible notifications."""
        for notification in self._notifications.values():
            self._position_notification(notification)
    
    def close_notification(self, notification_id: str) -> None:
        """Close a specific notification.
        
        Args:
            notification_id: ID of notification to close
        """
        if notification_id in self._notifications:
            self._notifications[notification_id].close_animated()
    
    def close_all(self) -> None:
        """Close all notifications."""
        for notification in list(self._notifications.values()):
            notification.close_animated()
        
        self._notification_queue.clear()
    
    def get_history(self) -> List[NotificationData]:
        """Get notification history.
        
        Returns:
            List of all notifications shown
        """
        return self._notification_history.copy()
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self._notification_history.clear()
    
    def set_position(self, position: NotificationPosition) -> None:
        """Change notification position.
        
        Args:
            position: New position
        """
        self.position = position
        self._reposition_notifications()
    
    def resizeEvent(self, event) -> None:
        """Handle parent resize."""
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())
            self._reposition_notifications()


# Convenience functions

def notify(
    title: str,
    message: str = "",
    type: NotificationType = NotificationType.INFO,
    parent: Optional[QWidget] = None,
    **kwargs
) -> Optional[str]:
    """Show a notification using the global manager.
    
    Args:
        title: Notification title
        message: Notification message  
        type: Notification type
        parent: Parent widget to find manager
        **kwargs: Additional notification options
        
    Returns:
        Notification ID if shown
    """
    # Find notification manager
    if parent:
        # Look for manager in parent hierarchy
        widget = parent
        while widget:
            if hasattr(widget, 'notification_manager'):
                return widget.notification_manager.show_notification(
                    title, message, type, **kwargs
                )
            widget = widget.parent()
    
    # Try to find in main window
    app = QApplication.instance()
    if app:
        for window in app.topLevelWidgets():
            if hasattr(window, 'notification_manager'):
                return window.notification_manager.show_notification(
                    title, message, type, **kwargs
                )
    
    logger.warning("No notification manager found")
    return None


def success(title: str, message: str = "", **kwargs) -> Optional[str]:
    """Show success notification."""
    return notify(title, message, NotificationType.SUCCESS, **kwargs)


def error(title: str, message: str = "", **kwargs) -> Optional[str]:
    """Show error notification."""
    return notify(title, message, NotificationType.ERROR, **kwargs)


def warning(title: str, message: str = "", **kwargs) -> Optional[str]:
    """Show warning notification."""
    return notify(title, message, NotificationType.WARNING, **kwargs)


def info(title: str, message: str = "", **kwargs) -> Optional[str]:
    """Show info notification."""
    return notify(title, message, NotificationType.INFO, **kwargs)