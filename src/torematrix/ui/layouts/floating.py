"""Floating Panel Management for TORE Matrix Labs V3.

This module provides comprehensive floating panel support including detachable panels,
multi-monitor management, docking zones, and persistent floating panel configurations.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from uuid import uuid4
import json

from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QToolBar, QToolButton, QApplication, QMenu,
    QRubberBand, QGraphicsDropShadowEffect, QSizeGrip, QSystemTrayIcon
)
from PyQt6.QtCore import (
    Qt, QRect, QSize, QPoint, QTimer, pyqtSignal, QObject, QEvent,
    QPropertyAnimation, QEasingCurve, QMimeData, QSettings
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap, QPalette,
    QIcon, QScreen, QDrag, QCursor, QResizeEvent, QMoveEvent,
    QCloseEvent, QShowEvent, QHideEvent
)

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent
from .base import LayoutConfiguration, LayoutType, LayoutGeometry
from .animations import AnimationManager, AnimationConfiguration

logger = logging.getLogger(__name__)


class DockZone(Enum):
    """Available docking zones."""
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()
    CENTER = auto()
    FLOATING = auto()


class PanelState(Enum):
    """States of floating panels."""
    DOCKED = auto()
    FLOATING = auto()
    MINIMIZED = auto()
    MAXIMIZED = auto()
    HIDDEN = auto()


class PanelBehavior(Enum):
    """Panel behavior modes."""
    NORMAL = auto()         # Normal floating panel
    ALWAYS_ON_TOP = auto()  # Always stays on top
    TOOL_WINDOW = auto()    # Tool window style
    MODAL = auto()          # Modal panel
    POPUP = auto()          # Popup panel


@dataclass
class FloatingPanelConfig:
    """Configuration for floating panels."""
    panel_id: str
    title: str
    initial_size: QSize = field(default_factory=lambda: QSize(300, 200))
    min_size: QSize = field(default_factory=lambda: QSize(150, 100))
    max_size: QSize = field(default_factory=lambda: QSize(2000, 1500))
    initial_position: Optional[QPoint] = None
    resizable: bool = True
    movable: bool = True
    closable: bool = True
    minimizable: bool = True
    maximizable: bool = True
    dock_zones: Set[DockZone] = field(default_factory=lambda: {DockZone.LEFT, DockZone.RIGHT, DockZone.BOTTOM})
    behavior: PanelBehavior = PanelBehavior.NORMAL
    remember_geometry: bool = True
    auto_hide: bool = False
    opacity: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DockArea:
    """Defines a dock area in the main window."""
    zone: DockZone
    rect: QRect
    max_panels: int = 10
    orientation: Qt.Orientation = Qt.Orientation.Vertical
    tab_mode: bool = True  # Whether to use tabs when multiple panels
    splitter_mode: bool = False  # Whether to use splitters


@dataclass
class PanelGeometry:
    """Saved geometry information for panels."""
    panel_id: str
    state: PanelState
    position: QPoint
    size: QSize
    dock_zone: Optional[DockZone] = None
    screen_index: int = 0
    is_maximized: bool = False
    dock_position: int = -1  # Position within dock area


class FloatingPanelTitleBar(QWidget):
    """Custom title bar for floating panels."""
    
    # Signals
    close_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    dock_requested = pyqtSignal(DockZone)
    undock_requested = pyqtSignal()
    
    def __init__(self, title: str, config: FloatingPanelConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.config = config
        self._dragging = False
        self._drag_start_pos = QPoint()
        
        self._setup_ui(title)
        self._setup_style()
    
    def _setup_ui(self, title: str) -> None:
        """Setup title bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Control buttons
        button_size = QSize(20, 20)
        
        # Dock menu button
        if self.config.dock_zones:
            self.dock_button = QToolButton()
            self.dock_button.setText("⚓")
            self.dock_button.setToolTip("Dock Panel")
            self.dock_button.setFixedSize(button_size)
            self.dock_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self._setup_dock_menu()
            layout.addWidget(self.dock_button)
        
        # Minimize button
        if self.config.minimizable:
            self.minimize_button = QPushButton("−")
            self.minimize_button.setToolTip("Minimize")
            self.minimize_button.setFixedSize(button_size)
            self.minimize_button.clicked.connect(self.minimize_requested.emit)
            layout.addWidget(self.minimize_button)
        
        # Maximize button
        if self.config.maximizable:
            self.maximize_button = QPushButton("□")
            self.maximize_button.setToolTip("Maximize")
            self.maximize_button.setFixedSize(button_size)
            self.maximize_button.clicked.connect(self.maximize_requested.emit)
            layout.addWidget(self.maximize_button)
        
        # Close button
        if self.config.closable:
            self.close_button = QPushButton("×")
            self.close_button.setToolTip("Close")
            self.close_button.setFixedSize(button_size)
            self.close_button.clicked.connect(self.close_requested.emit)
            layout.addWidget(self.close_button)
    
    def _setup_dock_menu(self) -> None:
        """Setup dock menu."""
        menu = QMenu(self)
        
        for zone in self.config.dock_zones:
            if zone != DockZone.FLOATING:
                action = menu.addAction(zone.name.title())
                action.triggered.connect(lambda checked, z=zone: self.dock_requested.emit(z))
        
        menu.addSeparator()
        undock_action = menu.addAction("Undock")
        undock_action.triggered.connect(self.undock_requested.emit)
        
        self.dock_button.setMenu(menu)
    
    def _setup_style(self) -> None:
        """Setup title bar styling."""
        self.setFixedHeight(28)
        self.setStyleSheet("""
            FloatingPanelTitleBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:1 #e0e0e0);
                border-bottom: 1px solid #c0c0c0;
            }
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #d0d0d0;
                border-radius: 2px;
            }
            QPushButton:pressed {
                background: #b0b0b0;
            }
            QToolButton {
                border: none;
                background: transparent;
                font-size: 12px;
            }
            QToolButton:hover {
                background: #d0d0d0;
                border-radius: 2px;
            }
        """)
    
    def set_title(self, title: str) -> None:
        """Set the title bar text."""
        self.title_label.setText(title)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for dragging."""
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # Move the parent window
            if self.window():
                delta = event.globalPosition().toPoint() - self._drag_start_pos
                self.window().move(self.window().pos() + delta)
                self._drag_start_pos = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
    
    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double click to maximize/restore."""
        if event.button() == Qt.MouseButton.LeftButton and self.config.maximizable:
            self.maximize_requested.emit()


class FloatingPanel(QWidget):
    """A floating panel that can be docked or undocked."""
    
    # Signals
    panel_docked = pyqtSignal(DockZone)
    panel_undocked = pyqtSignal()
    panel_closed = pyqtSignal()
    panel_state_changed = pyqtSignal(PanelState)
    geometry_changed = pyqtSignal(QRect)
    
    def __init__(self, config: FloatingPanelConfig, content_widget: Optional[QWidget] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.config = config
        self._state = PanelState.FLOATING
        self._is_docked = False
        self._dock_zone: Optional[DockZone] = None
        self._saved_geometry: Optional[QRect] = None
        
        # Animation
        self._fade_animation: Optional[QPropertyAnimation] = None
        
        self._setup_window()
        self._setup_ui(content_widget)
        self._setup_connections()
        self._apply_initial_configuration()
    
    def _setup_window(self) -> None:
        """Setup window properties."""
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint if self.config.behavior == PanelBehavior.ALWAYS_ON_TOP else Qt.WindowType.Widget
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        
        # Apply opacity
        self.setWindowOpacity(self.config.opacity)
        
        # Set size constraints
        self.setMinimumSize(self.config.min_size)
        self.setMaximumSize(self.config.max_size)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)
    
    def _setup_ui(self, content_widget: Optional[QWidget]) -> None:
        """Setup panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        
        # Title bar
        self.title_bar = FloatingPanelTitleBar(self.config.title, self.config, self)
        layout.addWidget(self.title_bar)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        
        if content_widget:
            self.content_layout.addWidget(content_widget)
        
        layout.addWidget(self.content_frame, 1)
        
        # Resize grip
        if self.config.resizable:
            self.resize_grip = QSizeGrip(self)
            grip_layout = QHBoxLayout()
            grip_layout.addStretch()
            grip_layout.addWidget(self.resize_grip)
            layout.addLayout(grip_layout)
        
        # Apply styling
        self.setStyleSheet("""
            FloatingPanel {
                background: white;
                border: 1px solid #808080;
                border-radius: 4px;
            }
            QFrame#content_frame {
                background: white;
            }
        """)
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        self.title_bar.close_requested.connect(self._handle_close_request)
        self.title_bar.minimize_requested.connect(self._handle_minimize_request)
        self.title_bar.maximize_requested.connect(self._handle_maximize_request)
        self.title_bar.dock_requested.connect(self._handle_dock_request)
        self.title_bar.undock_requested.connect(self._handle_undock_request)
    
    def _apply_initial_configuration(self) -> None:
        """Apply initial configuration."""
        # Set initial size
        self.resize(self.config.initial_size)
        
        # Set initial position
        if self.config.initial_position:
            self.move(self.config.initial_position)
        else:
            # Center on primary screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.geometry()
                x = (screen_rect.width() - self.width()) // 2
                y = (screen_rect.height() - self.height()) // 2
                self.move(x, y)
    
    def set_content_widget(self, widget: QWidget) -> None:
        """Set the content widget."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Add new content
        self.content_layout.addWidget(widget)
    
    def get_content_widget(self) -> Optional[QWidget]:
        """Get the current content widget."""
        if self.content_layout.count() > 0:
            return self.content_layout.itemAt(0).widget()
        return None
    
    def dock_to_zone(self, zone: DockZone) -> None:
        """Dock panel to specified zone."""
        if not self._is_docked:
            self._saved_geometry = self.geometry()
        
        self._is_docked = True
        self._dock_zone = zone
        self._state = PanelState.DOCKED
        
        # Hide floating window
        self.hide()
        
        # Emit signals
        self.panel_docked.emit(zone)
        self.panel_state_changed.emit(self._state)
        
        logger.debug(f"Panel {self.config.panel_id} docked to {zone.name}")
    
    def undock_from_zone(self) -> None:
        """Undock panel from current zone."""
        if self._is_docked:
            self._is_docked = False
            self._dock_zone = None
            self._state = PanelState.FLOATING
            
            # Restore geometry
            if self._saved_geometry:
                self.setGeometry(self._saved_geometry)
            
            # Show floating window
            self.show()
            self.raise_()
            self.activateWindow()
            
            # Emit signals
            self.panel_undocked.emit()
            self.panel_state_changed.emit(self._state)
            
            logger.debug(f"Panel {self.config.panel_id} undocked")
    
    def minimize_panel(self) -> None:
        """Minimize the panel."""
        if not self._is_docked:
            self.showMinimized()
            self._state = PanelState.MINIMIZED
            self.panel_state_changed.emit(self._state)
    
    def maximize_panel(self) -> None:
        """Maximize or restore the panel."""
        if not self._is_docked:
            if self.isMaximized():
                self.showNormal()
                self._state = PanelState.FLOATING
            else:
                self.showMaximized()
                self._state = PanelState.MAXIMIZED
            
            self.panel_state_changed.emit(self._state)
    
    def close_panel(self) -> None:
        """Close the panel."""
        self._state = PanelState.HIDDEN
        self.hide()
        self.panel_closed.emit()
        self.panel_state_changed.emit(self._state)
    
    def show_panel(self) -> None:
        """Show the panel."""
        if not self._is_docked:
            self.show()
            self.raise_()
            self.activateWindow()
            self._state = PanelState.FLOATING
            self.panel_state_changed.emit(self._state)
    
    def fade_in(self, duration_ms: int = 300) -> None:
        """Fade in the panel."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(duration_ms)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(self.config.opacity)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.show()
        self._fade_animation.start()
    
    def fade_out(self, duration_ms: int = 300, hide_on_complete: bool = True) -> None:
        """Fade out the panel."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(duration_ms)
        self._fade_animation.setStartValue(self.config.opacity)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        if hide_on_complete:
            self._fade_animation.finished.connect(self.hide)
        
        self._fade_animation.start()
    
    def get_state(self) -> PanelState:
        """Get current panel state."""
        return self._state
    
    def is_docked(self) -> bool:
        """Check if panel is docked."""
        return self._is_docked
    
    def get_dock_zone(self) -> Optional[DockZone]:
        """Get current dock zone."""
        return self._dock_zone
    
    def save_geometry(self) -> PanelGeometry:
        """Save current panel geometry."""
        screen_index = 0
        app = QApplication.instance()
        if app:
            screen = app.screenAt(self.pos())
            if screen:
                screens = app.screens()
                screen_index = screens.index(screen) if screen in screens else 0
        
        return PanelGeometry(
            panel_id=self.config.panel_id,
            state=self._state,
            position=self.pos(),
            size=self.size(),
            dock_zone=self._dock_zone,
            screen_index=screen_index,
            is_maximized=self.isMaximized()
        )
    
    def restore_geometry(self, geometry: PanelGeometry) -> None:
        """Restore panel geometry."""
        # Restore size and position
        self.resize(geometry.size)
        self.move(geometry.position)
        
        # Restore state
        if geometry.state == PanelState.MAXIMIZED:
            self.showMaximized()
        elif geometry.state == PanelState.MINIMIZED:
            self.showMinimized()
        elif geometry.state == PanelState.DOCKED and geometry.dock_zone:
            self.dock_to_zone(geometry.dock_zone)
        elif geometry.state == PanelState.HIDDEN:
            self.hide()
        else:
            self.show()
        
        self._state = geometry.state
    
    # Event handlers
    def _handle_close_request(self) -> None:
        """Handle close request from title bar."""
        self.close_panel()
    
    def _handle_minimize_request(self) -> None:
        """Handle minimize request from title bar."""
        self.minimize_panel()
    
    def _handle_maximize_request(self) -> None:
        """Handle maximize request from title bar."""
        self.maximize_panel()
    
    def _handle_dock_request(self, zone: DockZone) -> None:
        """Handle dock request from title bar."""
        self.dock_to_zone(zone)
    
    def _handle_undock_request(self) -> None:
        """Handle undock request from title bar."""
        self.undock_from_zone()
    
    # Qt event overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        self.geometry_changed.emit(self.geometry())
    
    def moveEvent(self, event: QMoveEvent) -> None:
        """Handle move events."""
        super().moveEvent(event)
        self.geometry_changed.emit(self.geometry())
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle close events."""
        self.close_panel()
        event.ignore()  # Don't actually close, just hide
    
    def showEvent(self, event: QShowEvent) -> None:
        """Handle show events."""
        super().showEvent(event)
        if not self._is_docked:
            self._state = PanelState.FLOATING
            self.panel_state_changed.emit(self._state)
    
    def hideEvent(self, event: QHideEvent) -> None:
        """Handle hide events."""
        super().hideEvent(event)
        if not self._is_docked:
            self._state = PanelState.HIDDEN
            self.panel_state_changed.emit(self._state)


class DockZoneIndicator(QWidget):
    """Visual indicator for dock zones during drag operations."""
    
    def __init__(self, zone: DockZone, rect: QRect, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.zone = zone
        self.setGeometry(rect)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Style
        self.setStyleSheet("""
            DockZoneIndicator {
                background-color: rgba(0, 120, 215, 100);
                border: 2px solid rgb(0, 120, 215);
                border-radius: 4px;
            }
        """)
    
    def paintEvent(self, event) -> None:
        """Paint the dock zone indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(0, 120, 215, 100))
        
        # Draw border
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # Draw zone label
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.zone.name)


class FloatingPanelManager(BaseUIComponent):
    """Manages floating panels and docking operations."""
    
    # Signals
    panel_created = pyqtSignal(str, FloatingPanel)  # panel_id, panel
    panel_destroyed = pyqtSignal(str)  # panel_id
    panel_docked = pyqtSignal(str, DockZone)  # panel_id, zone
    panel_undocked = pyqtSignal(str)  # panel_id
    dock_layout_changed = pyqtSignal()
    
    def __init__(
        self,
        main_window: QMainWindow,
        animation_manager: AnimationManager,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self.main_window = main_window
        self.animation_manager = animation_manager
        
        # Panel management
        self._panels: Dict[str, FloatingPanel] = {}
        self._panel_configs: Dict[str, FloatingPanelConfig] = {}
        self._dock_areas: Dict[DockZone, DockArea] = {}
        self._docked_panels: Dict[DockZone, List[str]] = {}
        
        # Drag and drop
        self._drag_indicators: Dict[DockZone, DockZoneIndicator] = {}
        self._current_drag_panel: Optional[str] = None
        
        # Persistence
        self._settings = QSettings("ToreMatrix", "FloatingPanels")
        
        self._setup_dock_areas()
        self._setup_drag_detection()
    
    def _setup_component(self) -> None:
        """Setup the floating panel manager."""
        # Subscribe to events
        self.subscribe_to_event("panel.create", self._handle_panel_create)
        self.subscribe_to_event("panel.destroy", self._handle_panel_destroy)
        self.subscribe_to_event("panel.dock", self._handle_panel_dock)
        self.subscribe_to_event("panel.undock", self._handle_panel_undock)
        
        # Load saved configurations
        self._load_panel_configurations()
        
        logger.info("Floating panel manager setup complete")
    
    def _setup_dock_areas(self) -> None:
        """Setup dock areas in the main window."""
        main_rect = self.main_window.geometry()
        
        # Define dock areas
        dock_width = 250
        dock_height = 200
        
        self._dock_areas = {
            DockZone.LEFT: DockArea(
                zone=DockZone.LEFT,
                rect=QRect(0, 0, dock_width, main_rect.height()),
                orientation=Qt.Orientation.Vertical
            ),
            DockZone.RIGHT: DockArea(
                zone=DockZone.RIGHT,
                rect=QRect(main_rect.width() - dock_width, 0, dock_width, main_rect.height()),
                orientation=Qt.Orientation.Vertical
            ),
            DockZone.TOP: DockArea(
                zone=DockZone.TOP,
                rect=QRect(0, 0, main_rect.width(), dock_height),
                orientation=Qt.Orientation.Horizontal
            ),
            DockZone.BOTTOM: DockArea(
                zone=DockZone.BOTTOM,
                rect=QRect(0, main_rect.height() - dock_height, main_rect.width(), dock_height),
                orientation=Qt.Orientation.Horizontal
            ),
        }
        
        # Initialize docked panels lists
        for zone in self._dock_areas:
            self._docked_panels[zone] = []
    
    def _setup_drag_detection(self) -> None:
        """Setup drag and drop detection."""
        # This would involve installing event filters on panels
        # and detecting drag operations
        pass
    
    def create_panel(
        self,
        panel_id: str,
        title: str,
        content_widget: Optional[QWidget] = None,
        config: Optional[FloatingPanelConfig] = None
    ) -> FloatingPanel:
        """Create a new floating panel.
        
        Args:
            panel_id: Unique identifier for the panel
            title: Panel title
            content_widget: Widget to display in panel
            config: Panel configuration (creates default if None)
            
        Returns:
            Created FloatingPanel instance
        """
        if panel_id in self._panels:
            logger.warning(f"Panel {panel_id} already exists")
            return self._panels[panel_id]
        
        # Create configuration
        if config is None:
            config = FloatingPanelConfig(
                panel_id=panel_id,
                title=title
            )
        
        # Create panel
        panel = FloatingPanel(config, content_widget, self.main_window)
        
        # Setup connections
        panel.panel_docked.connect(lambda zone, pid=panel_id: self._on_panel_docked(pid, zone))
        panel.panel_undocked.connect(lambda pid=panel_id: self._on_panel_undocked(pid))
        panel.panel_closed.connect(lambda pid=panel_id: self._on_panel_closed(pid))
        panel.geometry_changed.connect(lambda rect, pid=panel_id: self._on_panel_geometry_changed(pid, rect))
        
        # Store panel
        self._panels[panel_id] = panel
        self._panel_configs[panel_id] = config
        
        # Load saved geometry if available
        self._restore_panel_geometry(panel_id)
        
        # Emit signal
        self.panel_created.emit(panel_id, panel)
        
        logger.info(f"Created floating panel: {panel_id}")
        return panel
    
    def destroy_panel(self, panel_id: str) -> bool:
        """Destroy a floating panel.
        
        Args:
            panel_id: ID of panel to destroy
            
        Returns:
            True if panel was destroyed
        """
        if panel_id not in self._panels:
            return False
        
        panel = self._panels[panel_id]
        
        # Save geometry before destroying
        if self._panel_configs[panel_id].remember_geometry:
            self._save_panel_geometry(panel_id)
        
        # Remove from docked lists
        for zone_panels in self._docked_panels.values():
            if panel_id in zone_panels:
                zone_panels.remove(panel_id)
        
        # Clean up
        panel.deleteLater()
        del self._panels[panel_id]
        del self._panel_configs[panel_id]
        
        # Emit signal
        self.panel_destroyed.emit(panel_id)
        
        logger.info(f"Destroyed floating panel: {panel_id}")
        return True
    
    def get_panel(self, panel_id: str) -> Optional[FloatingPanel]:
        """Get a floating panel by ID.
        
        Args:
            panel_id: Panel identifier
            
        Returns:
            FloatingPanel instance or None
        """
        return self._panels.get(panel_id)
    
    def get_all_panels(self) -> Dict[str, FloatingPanel]:
        """Get all floating panels.
        
        Returns:
            Dictionary of panel_id -> FloatingPanel
        """
        return self._panels.copy()
    
    def dock_panel(self, panel_id: str, zone: DockZone) -> bool:
        """Dock a panel to a specific zone.
        
        Args:
            panel_id: ID of panel to dock
            zone: Zone to dock to
            
        Returns:
            True if panel was docked successfully
        """
        if panel_id not in self._panels or zone not in self._dock_areas:
            return False
        
        panel = self._panels[panel_id]
        
        # Check if zone is allowed
        config = self._panel_configs[panel_id]
        if zone not in config.dock_zones:
            logger.warning(f"Panel {panel_id} not allowed to dock to {zone.name}")
            return False
        
        # Dock the panel
        panel.dock_to_zone(zone)
        
        # Add to docked list
        if panel_id not in self._docked_panels[zone]:
            self._docked_panels[zone].append(panel_id)
        
        # Update dock layout
        self._update_dock_layout(zone)
        
        return True
    
    def undock_panel(self, panel_id: str) -> bool:
        """Undock a panel from its current zone.
        
        Args:
            panel_id: ID of panel to undock
            
        Returns:
            True if panel was undocked successfully
        """
        if panel_id not in self._panels:
            return False
        
        panel = self._panels[panel_id]
        if not panel.is_docked():
            return False
        
        dock_zone = panel.get_dock_zone()
        
        # Undock the panel
        panel.undock_from_zone()
        
        # Remove from docked list
        if dock_zone and panel_id in self._docked_panels[dock_zone]:
            self._docked_panels[dock_zone].remove(panel_id)
        
        # Update dock layout
        if dock_zone:
            self._update_dock_layout(dock_zone)
        
        return True
    
    def toggle_panel(self, panel_id: str) -> bool:
        """Toggle panel visibility.
        
        Args:
            panel_id: ID of panel to toggle
            
        Returns:
            True if panel state was changed
        """
        if panel_id not in self._panels:
            return False
        
        panel = self._panels[panel_id]
        
        if panel.isVisible():
            panel.close_panel()
        else:
            panel.show_panel()
        
        return True
    
    def show_all_panels(self) -> None:
        """Show all hidden panels."""
        for panel in self._panels.values():
            if not panel.isVisible() and not panel.is_docked():
                panel.show_panel()
    
    def hide_all_panels(self) -> None:
        """Hide all floating panels."""
        for panel in self._panels.values():
            if panel.isVisible() and not panel.is_docked():
                panel.close_panel()
    
    def get_docked_panels(self, zone: DockZone) -> List[str]:
        """Get list of panels docked to a zone.
        
        Args:
            zone: Dock zone
            
        Returns:
            List of panel IDs
        """
        return self._docked_panels.get(zone, []).copy()
    
    def get_floating_panels(self) -> List[str]:
        """Get list of floating (not docked) panels.
        
        Returns:
            List of panel IDs
        """
        floating = []
        for panel_id, panel in self._panels.items():
            if not panel.is_docked():
                floating.append(panel_id)
        return floating
    
    def _update_dock_layout(self, zone: DockZone) -> None:
        """Update layout for a specific dock zone."""
        # This would update the actual dock widget layout
        # For now, just emit the signal
        self.dock_layout_changed.emit()
        logger.debug(f"Updated dock layout for zone: {zone.name}")
    
    def _save_panel_geometry(self, panel_id: str) -> None:
        """Save panel geometry to settings."""
        if panel_id not in self._panels:
            return
        
        panel = self._panels[panel_id]
        geometry = panel.save_geometry()
        
        # Convert to dictionary for JSON serialization
        geometry_data = {
            'state': geometry.state.name,
            'position': [geometry.position.x(), geometry.position.y()],
            'size': [geometry.size.width(), geometry.size.height()],
            'dock_zone': geometry.dock_zone.name if geometry.dock_zone else None,
            'screen_index': geometry.screen_index,
            'is_maximized': geometry.is_maximized
        }
        
        self._settings.setValue(f"geometry/{panel_id}", json.dumps(geometry_data))
        logger.debug(f"Saved geometry for panel: {panel_id}")
    
    def _restore_panel_geometry(self, panel_id: str) -> None:
        """Restore panel geometry from settings."""
        if panel_id not in self._panels:
            return
        
        geometry_json = self._settings.value(f"geometry/{panel_id}")
        if not geometry_json:
            return
        
        try:
            geometry_data = json.loads(geometry_json)
            
            # Convert back to PanelGeometry
            geometry = PanelGeometry(
                panel_id=panel_id,
                state=PanelState[geometry_data['state']],
                position=QPoint(*geometry_data['position']),
                size=QSize(*geometry_data['size']),
                dock_zone=DockZone[geometry_data['dock_zone']] if geometry_data['dock_zone'] else None,
                screen_index=geometry_data['screen_index'],
                is_maximized=geometry_data['is_maximized']
            )
            
            # Restore geometry
            panel = self._panels[panel_id]
            panel.restore_geometry(geometry)
            
            logger.debug(f"Restored geometry for panel: {panel_id}")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to restore geometry for panel {panel_id}: {e}")
    
    def _load_panel_configurations(self) -> None:
        """Load saved panel configurations."""
        # This would load panel configurations from settings
        # For now, just log that it's called
        logger.debug("Loading panel configurations from settings")
    
    def save_all_panel_geometries(self) -> None:
        """Save all panel geometries."""
        for panel_id in self._panels:
            if self._panel_configs[panel_id].remember_geometry:
                self._save_panel_geometry(panel_id)
        
        logger.info("Saved all panel geometries")
    
    def restore_all_panel_geometries(self) -> None:
        """Restore all panel geometries."""
        for panel_id in self._panels:
            self._restore_panel_geometry(panel_id)
        
        logger.info("Restored all panel geometries")
    
    # Event handlers
    def _on_panel_docked(self, panel_id: str, zone: DockZone) -> None:
        """Handle panel docked event."""
        if panel_id not in self._docked_panels[zone]:
            self._docked_panels[zone].append(panel_id)
        
        self.panel_docked.emit(panel_id, zone)
        self._update_dock_layout(zone)
        
        logger.debug(f"Panel {panel_id} docked to {zone.name}")
    
    def _on_panel_undocked(self, panel_id: str) -> None:
        """Handle panel undocked event."""
        # Remove from all dock zone lists
        for zone_panels in self._docked_panels.values():
            if panel_id in zone_panels:
                zone_panels.remove(panel_id)
        
        self.panel_undocked.emit(panel_id)
        self.dock_layout_changed.emit()
        
        logger.debug(f"Panel {panel_id} undocked")
    
    def _on_panel_closed(self, panel_id: str) -> None:
        """Handle panel closed event."""
        # Save geometry if configured
        if panel_id in self._panel_configs and self._panel_configs[panel_id].remember_geometry:
            self._save_panel_geometry(panel_id)
        
        logger.debug(f"Panel {panel_id} closed")
    
    def _on_panel_geometry_changed(self, panel_id: str, rect: QRect) -> None:
        """Handle panel geometry changed event."""
        # Auto-save geometry if configured
        if (panel_id in self._panel_configs and 
            self._panel_configs[panel_id].remember_geometry):
            # Save with a delay to avoid too frequent saves
            QTimer.singleShot(1000, lambda: self._save_panel_geometry(panel_id))
    
    # Event handlers for external events
    def _handle_panel_create(self, event_data: Dict[str, Any]) -> None:
        """Handle panel create event."""
        panel_id = event_data.get("panel_id")
        title = event_data.get("title", "Panel")
        
        if panel_id:
            self.create_panel(panel_id, title)
    
    def _handle_panel_destroy(self, event_data: Dict[str, Any]) -> None:
        """Handle panel destroy event."""
        panel_id = event_data.get("panel_id")
        if panel_id:
            self.destroy_panel(panel_id)
    
    def _handle_panel_dock(self, event_data: Dict[str, Any]) -> None:
        """Handle panel dock event."""
        panel_id = event_data.get("panel_id")
        zone_name = event_data.get("zone")
        
        if panel_id and zone_name:
            try:
                zone = DockZone[zone_name.upper()]
                self.dock_panel(panel_id, zone)
            except KeyError:
                logger.warning(f"Invalid dock zone: {zone_name}")
    
    def _handle_panel_undock(self, event_data: Dict[str, Any]) -> None:
        """Handle panel undock event."""
        panel_id = event_data.get("panel_id")
        if panel_id:
            self.undock_panel(panel_id)