"""Advanced status bar management system for ToreMatrix V3.

This module provides comprehensive status bar functionality with progress tracking,
system indicators, and integration with the UI framework.
"""

from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import logging
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame, QToolButton,
    QSizePolicy, QStyleOption, QStyle, QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation,
    QEasingCurve, QRect, QSize, QThread, QMutex
)
from PyQt6.QtGui import QIcon, QPainter, QFont, QPixmap, QPalette

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class IndicatorType(Enum):
    """Types of status indicators."""
    TEXT = "text"
    ICON = "icon"
    PROGRESS = "progress"
    LED = "led"
    CUSTOM = "custom"


class IndicatorState(Enum):
    """States for status indicators."""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    INACTIVE = "inactive"
    BUSY = "busy"


@dataclass
class StatusIndicatorConfig:
    """Configuration for a status indicator."""
    name: str
    type: IndicatorType
    position: int  # Position in status bar (lower = left)
    width: Optional[int] = None
    tooltip: Optional[str] = None
    icon_path: Optional[str] = None
    format_string: Optional[str] = None  # For formatted text display
    update_interval: Optional[int] = None  # Auto-update interval in ms
    clickable: bool = False
    click_callback: Optional[Callable[[], None]] = None


class StatusIndicator(QWidget):
    """Individual status indicator widget."""
    
    # Signals
    clicked = pyqtSignal(str)  # indicator_name
    state_changed = pyqtSignal(str, str)  # indicator_name, state
    value_changed = pyqtSignal(str, object)  # indicator_name, value
    
    def __init__(self, config: StatusIndicatorConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = config
        self.current_state = IndicatorState.NORMAL
        self.current_value: Any = None
        
        # Setup UI
        self.setup_ui()
        self.setup_styling()
        
        # Auto-update timer
        if config.update_interval:
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.auto_update)
            self.update_timer.start(config.update_interval)
    
    def setup_ui(self) -> None:
        """Setup the indicator UI based on type."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        if self.config.type == IndicatorType.TEXT:
            self.label = QLabel()
            if self.config.width:
                self.label.setMinimumWidth(self.config.width)
            layout.addWidget(self.label)
            
        elif self.config.type == IndicatorType.ICON:
            self.icon_label = QLabel()
            if self.config.icon_path:
                icon = QIcon(self.config.icon_path)
                self.icon_label.setPixmap(icon.pixmap(16, 16))
            layout.addWidget(self.icon_label)
            
            if self.config.format_string:
                self.text_label = QLabel()
                layout.addWidget(self.text_label)
        
        elif self.config.type == IndicatorType.PROGRESS:
            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximumHeight(14)
            if self.config.width:
                self.progress_bar.setMinimumWidth(self.config.width)
            layout.addWidget(self.progress_bar)
            
        elif self.config.type == IndicatorType.LED:
            self.led_widget = LEDIndicator()
            layout.addWidget(self.led_widget)
        
        # Set tooltip
        if self.config.tooltip:
            self.setToolTip(self.config.tooltip)
        
        # Make clickable if configured
        if self.config.clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def setup_styling(self) -> None:
        """Setup styling based on current state."""
        self.setObjectName(f"StatusIndicator_{self.config.name}")
        
        # Apply state-specific styling
        self.update_styling()
    
    def update_styling(self) -> None:
        """Update styling based on current state."""
        style_classes = {
            IndicatorState.NORMAL: "status-indicator-normal",
            IndicatorState.WARNING: "status-indicator-warning", 
            IndicatorState.ERROR: "status-indicator-error",
            IndicatorState.SUCCESS: "status-indicator-success",
            IndicatorState.INACTIVE: "status-indicator-inactive",
            IndicatorState.BUSY: "status-indicator-busy"
        }
        
        style_class = style_classes.get(self.current_state, "status-indicator-normal")
        self.setProperty("statusIndicatorState", style_class)
        self.style().polish(self)
    
    def set_state(self, state: IndicatorState) -> None:
        """Set the indicator state."""
        if self.current_state != state:
            self.current_state = state
            self.update_styling()
            self.state_changed.emit(self.config.name, state.value)
    
    def set_value(self, value: Any) -> None:
        """Set the indicator value."""
        self.current_value = value
        
        if self.config.type == IndicatorType.TEXT:
            text = str(value)
            if self.config.format_string:
                try:
                    text = self.config.format_string.format(value)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Format error for {self.config.name}: {e}")
                    text = str(value)
            self.label.setText(text)
            
        elif self.config.type == IndicatorType.ICON and hasattr(self, 'text_label'):
            text = str(value)
            if self.config.format_string:
                try:
                    text = self.config.format_string.format(value)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Format error for {self.config.name}: {e}")
                    text = str(value)
            self.text_label.setText(text)
            
        elif self.config.type == IndicatorType.PROGRESS:
            if isinstance(value, (tuple, list)) and len(value) >= 2:
                current, maximum = value[0], value[1]
                self.progress_bar.setRange(0, maximum)
                self.progress_bar.setValue(current)
                if len(value) > 2:
                    self.progress_bar.setFormat(str(value[2]))
            elif isinstance(value, (int, float)):
                self.progress_bar.setValue(int(value))
        
        elif self.config.type == IndicatorType.LED:
            self.led_widget.set_state(value)
        
        self.value_changed.emit(self.config.name, value)
    
    def get_value(self) -> Any:
        """Get current indicator value."""
        return self.current_value
    
    def auto_update(self) -> None:
        """Auto-update callback - override in subclasses."""
        pass
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse clicks."""
        if self.config.clickable:
            self.clicked.emit(self.config.name)
            if self.config.click_callback:
                self.config.click_callback()
        super().mousePressEvent(event)


class LEDIndicator(QWidget):
    """LED-style status indicator."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = False
        self.color = "green"
        self.setFixedSize(12, 12)
    
    def set_state(self, state: Union[bool, str]) -> None:
        """Set LED state."""
        if isinstance(state, bool):
            self.state = state
            self.color = "green" if state else "gray"
        elif isinstance(state, str):
            self.state = state.lower() in ("true", "on", "active", "1")
            self.color = state.lower() if state.lower() in ("red", "yellow", "green", "blue") else "green"
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the LED indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Colors based on state
        colors = {
            "green": "#00ff00" if self.state else "#004000",
            "red": "#ff0000" if self.state else "#400000", 
            "yellow": "#ffff00" if self.state else "#404000",
            "blue": "#0000ff" if self.state else "#000040",
            "gray": "#808080"
        }
        
        color = colors.get(self.color, colors["gray"])
        
        # Draw LED circle
        painter.setBrush(painter.createPen(color).brush())
        painter.setPen(painter.createPen("#333333"))
        painter.drawEllipse(2, 2, 8, 8)


class ProgressWidget(QWidget):
    """Enhanced progress widget with text and cancel support."""
    
    # Signals
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()
        self.is_visible = False
    
    def setup_ui(self) -> None:
        """Setup progress widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setMinimumWidth(200)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_label = QLabel()
        self.status_label.setMaximumWidth(150)
        layout.addWidget(self.status_label)
        
        # Cancel button
        self.cancel_button = QToolButton()
        self.cancel_button.setText("×")
        self.cancel_button.setMaximumSize(20, 16)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self.cancel_button)
        
        # Initially hidden
        self.hide()
    
    def show_progress(self, current: int, maximum: int, text: str = "", cancelable: bool = True) -> None:
        """Show progress with values."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(current)
        self.status_label.setText(text)
        self.cancel_button.setVisible(cancelable)
        
        if not self.is_visible:
            self.show()
            self.is_visible = True
    
    def hide_progress(self) -> None:
        """Hide progress widget."""
        if self.is_visible:
            self.hide()
            self.is_visible = False
            self.progress_bar.setValue(0)
            self.status_label.setText("")


class StatusBarManager(QObject):
    """Comprehensive status bar management with progress tracking and indicators."""
    
    # Signals
    indicator_added = pyqtSignal(str)  # indicator_name
    indicator_removed = pyqtSignal(str)  # indicator_name
    indicator_clicked = pyqtSignal(str)  # indicator_name
    progress_started = pyqtSignal(str)  # operation_id
    progress_finished = pyqtSignal(str)  # operation_id
    progress_cancelled = pyqtSignal(str)  # operation_id
    
    def __init__(
        self,
        main_window: QMainWindow,
        event_bus: EventBus,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.main_window = main_window
        self.event_bus = event_bus
        self.config_manager = config_manager
        
        # Get or create status bar
        self.status_bar = main_window.statusBar()
        if not self.status_bar:
            self.status_bar = QStatusBar(main_window)
            main_window.setStatusBar(self.status_bar)
        
        # Storage
        self.indicators: Dict[str, StatusIndicator] = {}
        self.indicator_configs: Dict[str, StatusIndicatorConfig] = {}
        self.progress_operations: Dict[str, Dict[str, Any]] = {}
        
        # UI components
        self.message_label: Optional[QLabel] = None
        self.progress_widget: Optional[ProgressWidget] = None
        self.permanent_widgets: Dict[str, QWidget] = {}
        
        # Threading protection
        self.mutex = QMutex()
        
        # Setup
        self.setup_ui()
        self.setup_standard_indicators()
        self.setup_connections()
        
        logger.info("StatusBarManager initialized")
    
    def setup_ui(self) -> None:
        """Setup the status bar UI components."""
        # Main message area (left side)
        self.message_label = QLabel("Ready")
        self.status_bar.addWidget(self.message_label, 1)  # Stretch factor 1
        
        # Progress widget (center)
        self.progress_widget = ProgressWidget()
        self.status_bar.addWidget(self.progress_widget)
        
        # Permanent widgets area (right side)
        # Individual indicators will be added here
    
    def setup_standard_indicators(self) -> None:
        """Setup standard application indicators."""
        standard_indicators = [
            StatusIndicatorConfig(
                name="memory_usage",
                type=IndicatorType.TEXT,
                position=100,
                width=80,
                tooltip="Memory Usage",
                format_string="Mem: {:.1f}MB",
                update_interval=5000  # Update every 5 seconds
            ),
            StatusIndicatorConfig(
                name="zoom_level",
                type=IndicatorType.TEXT,
                position=200,
                width=60,
                tooltip="Zoom Level",
                format_string="Zoom: {}%"
            ),
            StatusIndicatorConfig(
                name="cursor_position",
                type=IndicatorType.TEXT,
                position=300,
                width=100,
                tooltip="Cursor Position",
                format_string="Line: {}, Col: {}"
            ),
            StatusIndicatorConfig(
                name="document_status",
                type=IndicatorType.LED,
                position=400,
                tooltip="Document Status",
                width=20
            ),
            StatusIndicatorConfig(
                name="connection_status",
                type=IndicatorType.ICON,
                position=500,
                tooltip="Connection Status",
                icon_path=":/icons/network.svg",
                width=60,
                clickable=True
            )
        ]
        
        for config in standard_indicators:
            self.add_indicator(config)
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        # Event bus connections
        self.event_bus.subscribe("ui.status.message", self._on_status_message_event)
        self.event_bus.subscribe("ui.status.progress", self._on_progress_event)
        self.event_bus.subscribe("ui.status.indicator", self._on_indicator_event)
        
        # Progress widget connections
        if self.progress_widget:
            self.progress_widget.cancel_requested.connect(self._on_progress_cancelled)
    
    def add_indicator(self, config: StatusIndicatorConfig) -> bool:
        """Add a status indicator."""
        if config.name in self.indicators:
            logger.warning(f"Indicator {config.name} already exists")
            return False
        
        try:
            # Create indicator widget
            indicator = StatusIndicator(config)
            
            # Connect signals
            indicator.clicked.connect(self._on_indicator_clicked)
            indicator.state_changed.connect(self._on_indicator_state_changed)
            indicator.value_changed.connect(self._on_indicator_value_changed)
            
            # Add to status bar as permanent widget
            self.status_bar.addPermanentWidget(indicator)
            
            # Store references
            self.indicators[config.name] = indicator
            self.indicator_configs[config.name] = config
            
            self.indicator_added.emit(config.name)
            logger.debug(f"Added status indicator: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add indicator {config.name}: {e}")
            return False
    
    def remove_indicator(self, name: str) -> bool:
        """Remove a status indicator."""
        if name not in self.indicators:
            logger.warning(f"Indicator {name} not found")
            return False
        
        try:
            indicator = self.indicators[name]
            
            # Remove from status bar
            self.status_bar.removeWidget(indicator)
            indicator.deleteLater()
            
            # Remove from storage
            del self.indicators[name]
            del self.indicator_configs[name]
            
            self.indicator_removed.emit(name)
            logger.debug(f"Removed status indicator: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove indicator {name}: {e}")
            return False
    
    def update_indicator(self, name: str, value: Any, state: Optional[IndicatorState] = None) -> bool:
        """Update an indicator's value and/or state."""
        if name not in self.indicators:
            logger.warning(f"Indicator {name} not found")
            return False
        
        try:
            indicator = self.indicators[name]
            
            # Update value
            indicator.set_value(value)
            
            # Update state if provided
            if state is not None:
                indicator.set_state(state)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update indicator {name}: {e}")
            return False
    
    def show_message(self, message: str, timeout: int = 0) -> None:
        """Show a message in the status bar."""
        if self.message_label:
            self.message_label.setText(message)
            
            # Set timeout if specified
            if timeout > 0:
                QTimer.singleShot(timeout, lambda: self.show_message("Ready"))
    
    def show_progress(
        self,
        operation_id: str,
        current: int,
        maximum: int,
        text: str = "",
        cancelable: bool = True
    ) -> None:
        """Show progress for an operation."""
        with QMutex():
            if self.progress_widget:
                self.progress_widget.show_progress(current, maximum, text, cancelable)
                
                # Track operation
                self.progress_operations[operation_id] = {
                    'current': current,
                    'maximum': maximum,
                    'text': text,
                    'started': datetime.now(),
                    'cancelable': cancelable
                }
                
                # Emit signal for first time
                if operation_id not in self.progress_operations or current == 0:
                    self.progress_started.emit(operation_id)
                
                # Auto-hide when complete
                if current >= maximum:
                    QTimer.singleShot(1000, self.hide_progress)
                    self.progress_finished.emit(operation_id)
    
    def hide_progress(self) -> None:
        """Hide the progress indicator."""
        if self.progress_widget:
            self.progress_widget.hide_progress()
    
    def add_permanent_widget(self, name: str, widget: QWidget, stretch: int = 0) -> bool:
        """Add a permanent widget to the status bar."""
        if name in self.permanent_widgets:
            logger.warning(f"Permanent widget {name} already exists")
            return False
        
        try:
            self.status_bar.addPermanentWidget(widget, stretch)
            self.permanent_widgets[name] = widget
            logger.debug(f"Added permanent widget: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add permanent widget {name}: {e}")
            return False
    
    def remove_permanent_widget(self, name: str) -> bool:
        """Remove a permanent widget from the status bar."""
        if name not in self.permanent_widgets:
            logger.warning(f"Permanent widget {name} not found")
            return False
        
        try:
            widget = self.permanent_widgets[name]
            self.status_bar.removeWidget(widget)
            widget.deleteLater()
            del self.permanent_widgets[name]
            logger.debug(f"Removed permanent widget: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove permanent widget {name}: {e}")
            return False
    
    def get_indicator_value(self, name: str) -> Any:
        """Get current value of an indicator."""
        if name in self.indicators:
            return self.indicators[name].get_value()
        return None
    
    def get_indicator_state(self, name: str) -> Optional[IndicatorState]:
        """Get current state of an indicator."""
        if name in self.indicators:
            return self.indicators[name].current_state
        return None
    
    def is_progress_active(self) -> bool:
        """Check if any progress operation is active."""
        return bool(self.progress_operations)
    
    def get_active_progress_operations(self) -> List[str]:
        """Get list of active progress operation IDs."""
        return list(self.progress_operations.keys())
    
    # Event handlers
    def _on_status_message_event(self, data: Dict[str, Any]) -> None:
        """Handle status message event."""
        message = data.get('message', '')
        timeout = data.get('timeout', 0)
        self.show_message(message, timeout)
    
    def _on_progress_event(self, data: Dict[str, Any]) -> None:
        """Handle progress event."""
        operation_id = data.get('operation_id', 'default')
        action = data.get('action', 'update')
        
        if action == 'show' or action == 'update':
            current = data.get('current', 0)
            maximum = data.get('maximum', 100)
            text = data.get('text', '')
            cancelable = data.get('cancelable', True)
            self.show_progress(operation_id, current, maximum, text, cancelable)
        elif action == 'hide':
            self.hide_progress()
    
    def _on_indicator_event(self, data: Dict[str, Any]) -> None:
        """Handle indicator update event."""
        name = data.get('name')
        if not name:
            return
        
        value = data.get('value')
        state_str = data.get('state')
        state = None
        
        if state_str:
            try:
                state = IndicatorState(state_str)
            except ValueError:
                logger.warning(f"Invalid indicator state: {state_str}")
        
        self.update_indicator(name, value, state)
    
    def _on_indicator_clicked(self, indicator_name: str) -> None:
        """Handle indicator click."""
        self.indicator_clicked.emit(indicator_name)
        
        # Emit event bus event
        self.event_bus.emit("ui.status.indicator_clicked", {
            "indicator_name": indicator_name
        })
    
    def _on_indicator_state_changed(self, indicator_name: str, state: str) -> None:
        """Handle indicator state change."""
        self.event_bus.emit("ui.status.indicator_state_changed", {
            "indicator_name": indicator_name,
            "state": state
        })
    
    def _on_indicator_value_changed(self, indicator_name: str, value: Any) -> None:
        """Handle indicator value change."""
        self.event_bus.emit("ui.status.indicator_value_changed", {
            "indicator_name": indicator_name,
            "value": value
        })
    
    def _on_progress_cancelled(self) -> None:
        """Handle progress cancellation."""
        # Cancel all active operations
        for operation_id in list(self.progress_operations.keys()):
            self.progress_cancelled.emit(operation_id)
            del self.progress_operations[operation_id]
        
        self.hide_progress()
        
        # Emit event
        self.event_bus.emit("ui.status.progress_cancelled", {})