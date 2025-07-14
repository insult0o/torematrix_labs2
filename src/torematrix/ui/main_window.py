"""Main window implementation for ToreMatrix V3.

This module provides the core QMainWindow implementation with modern
PyQt6 patterns, cross-platform support, and a solid foundation for
the entire application UI.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
import sys
import logging
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMenuBar, 
    QToolBar, QStatusBar, QApplication
)
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QCloseEvent, QScreen

from .base import BaseUIComponent
from .exceptions import WindowInitializationError, StateRestorationError

if TYPE_CHECKING:
    from ..core.events import EventBus
    from ..core.config import ConfigManager
    from ..core.state import StateManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Core application main window with modern PyQt6 patterns.
    
    This class provides the foundation for the entire ToreMatrix UI,
    including layout management, window lifecycle, and integration
    points for all other UI components.
    """
    
    # Signals
    window_initialized = pyqtSignal()
    window_closing = pyqtSignal()
    window_ready = pyqtSignal()
    window_state_changed = pyqtSignal(dict)  # state_data
    
    # Window settings
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800
    MIN_WIDTH = 800
    MIN_HEIGHT = 600
    
    def __init__(
        self,
        event_bus: 'EventBus',
        config_manager: 'ConfigManager',
        state_manager: 'StateManager',
        parent: Optional[QWidget] = None
    ):
        """Initialize main window.
        
        Args:
            event_bus: Event bus for communication
            config_manager: Configuration manager instance
            state_manager: State manager instance
            parent: Parent widget (usually None for main window)
        """
        # Initialize QMainWindow
        super().__init__(parent)
        
        # Store dependencies
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._state_manager = state_manager
        
        # UI components
        self._central_widget: Optional[QWidget] = None
        self._central_layout: Optional[QVBoxLayout] = None
        self._menubar: Optional[QMenuBar] = None
        self._toolbar: Optional[QToolBar] = None
        self._statusbar: Optional[QStatusBar] = None
        
        # Settings
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # State tracking
        self._is_closing = False
        self._window_state: Dict[str, Any] = {
            'geometry': None,
            'state': None,
            'maximized': False,
            'fullscreen': False
        }
        
        # Platform-specific setup
        self._setup_platform_specific()
        
        # Initialize window
        self._setup_window()
        self._setup_ui_containers()
        self._restore_window_state()
        
        # Connect events
        self._connect_events()
        
        # Perform initialization
        self._initialize_window()
        
        # Signal ready
        self.window_ready.emit()
    
    def _initialize_window(self) -> None:
        """Perform main window specific initialization."""
        # Additional initialization that requires Qt event loop
        self._start_autosave_timer()
        
        # Emit initialization signal
        self.window_initialized.emit()
        
        # Emit event through event bus
        if self._event_bus:
            self._event_bus.publish("window.initialized", {
                "platform": platform.system(),
                "size": {"width": self.width(), "height": self.height()},
                "source": "MainWindow"
            })
    
    def _setup_platform_specific(self) -> None:
        """Configure platform-specific settings."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # macOS specific settings
            self.setUnifiedTitleAndToolBarOnMac(True)
        elif system == "Windows":
            # Windows specific settings
            self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        elif system == "Linux":
            # Linux specific settings
            pass
        
        # High DPI support (PyQt6 handles this automatically)
        # Legacy attributes for PyQt5 compatibility
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    def _setup_window(self) -> None:
        """Configure basic window properties."""
        try:
            self.setWindowTitle("ToreMatrix V3 - Document Processing Platform")
            self.setMinimumSize(QSize(self.MIN_WIDTH, self.MIN_HEIGHT))
            self.resize(QSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT))
            
            # Set application icon if available
            icon_path = Path(__file__).parent / "icons" / "app_icon.svg"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
            
            logger.info("Window properties configured")
        except Exception as e:
            raise WindowInitializationError(f"Failed to setup window: {str(e)}") from e
    
    def _setup_ui_containers(self) -> None:
        """Create the main UI container structure."""
        try:
            # Central widget container
            self._central_widget = QWidget()
            self._central_layout = QVBoxLayout(self._central_widget)
            self._central_layout.setContentsMargins(0, 0, 0, 0)
            self._central_layout.setSpacing(0)
            self.setCentralWidget(self._central_widget)
            
            # Menubar container
            self._menubar = self.menuBar()
            self._menubar.setNativeMenuBar(True)  # Use native menubar on macOS
            
            # Toolbar container
            self._toolbar = QToolBar("Main Toolbar", self)
            self._toolbar.setObjectName("mainToolBar")
            self._toolbar.setMovable(True)
            self._toolbar.setFloatable(False)
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)
            
            # Status bar container
            self._statusbar = self.statusBar()
            self._statusbar.showMessage("Ready", 5000)
            
            # Apply base styling
            self._apply_base_styling()
            
            logger.info("UI containers setup completed")
        except Exception as e:
            raise WindowInitializationError(f"Failed to setup UI containers: {str(e)}") from e
    
    def _apply_base_styling(self) -> None:
        """Apply base window styling."""
        # Base stylesheet - will be enhanced by theme system (Agent 3)
        base_style = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 4px;
            spacing: 4px;
        }
        
        QStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #e0e0e0;
        }
        """
        self.setStyleSheet(base_style)
    
    def _connect_events(self) -> None:
        """Connect to event bus signals."""
        # Register for relevant events
        if self._event_bus:
            self._event_bus.subscribe("app.quit", self._handle_quit_request)
            self._event_bus.subscribe("window.show_status", self._handle_status_message)
            self._event_bus.subscribe("window.center", self._handle_center_request)
    
    def _handle_quit_request(self, event_data: dict) -> None:
        """Handle application quit request."""
        self.close_application()
    
    def _handle_status_message(self, event_data: dict) -> None:
        """Handle status bar message updates."""
        message = event_data.get("message", "")
        timeout = event_data.get("timeout", 5000)
        self.show_status_message(message, timeout)
    
    def _handle_center_request(self, event_data: dict) -> None:
        """Handle window center request."""
        self._center_on_screen()
    
    def _save_window_state(self) -> None:
        """Save window geometry and state."""
        try:
            self._settings.setValue("window/geometry", self.saveGeometry())
            self._settings.setValue("window/state", self.saveState())
            self._settings.setValue("window/maximized", self.isMaximized())
            self._settings.setValue("window/fullscreen", self.isFullScreen())
            self._settings.setValue("window/toolbars", self.saveState())
            
            logger.debug("Window state saved")
        except Exception as e:
            logger.error(f"Failed to save window state: {str(e)}")
    
    def _restore_window_state(self) -> None:
        """Restore window geometry and state."""
        try:
            # Restore geometry
            geometry = self._settings.value("window/geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            # Restore window state
            state = self._settings.value("window/state")
            if state:
                self.restoreState(state)
            
            # Restore maximized state
            if self._settings.value("window/maximized", False, type=bool):
                self.showMaximized()
            
            logger.debug("Window state restored")
        except Exception as e:
            logger.error(f"Failed to restore window state: {str(e)}")
            # Don't raise here - allow window to open with defaults
    
    def _start_autosave_timer(self) -> None:
        """Start timer for periodic state saving."""
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._save_window_state)
        self._autosave_timer.start(30000)  # Save every 30 seconds
    
    def _center_on_screen(self) -> None:
        """Center window on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            window_geometry.moveCenter(screen_geometry.center())
            self.move(window_geometry.topLeft())
    
    # Public API for other agents
    
    def show_application(self) -> None:
        """Show the main window with proper initialization."""
        # Center on screen if no saved position
        if not self._window_state.get('geometry'):
            self._center_on_screen()
        
        # Show window
        self.show()
        
        # Raise and activate
        self.raise_()
        self.activateWindow()
        
        logger.info("Application window shown")
    
    def close_application(self) -> None:
        """Close the application with proper cleanup."""
        if not self._is_closing:
            self._is_closing = True
            logger.info("Closing application")
            
            # Emit closing signal
            self.window_closing.emit()
            
            # Save state
            self._save_window_state()
            
            # Publish close event
            if self._event_bus:
                self._event_bus.publish("window.closing", {"source": "main_window"})
            
            # Close window
            self.close()
    
    def get_menubar_container(self) -> QMenuBar:
        """Get the menubar container for Agent 2.
        
        Returns:
            QMenuBar instance for menu creation
        """
        if not self._menubar:
            raise WindowInitializationError("Menubar not initialized")
        return self._menubar
    
    def get_toolbar_container(self) -> QToolBar:
        """Get the main toolbar container for Agent 2.
        
        Returns:
            QToolBar instance for action buttons
        """
        if not self._toolbar:
            raise WindowInitializationError("Toolbar not initialized")
        return self._toolbar
    
    def get_statusbar_container(self) -> QStatusBar:
        """Get the statusbar container for Agent 4.
        
        Returns:
            QStatusBar instance for status display
        """
        if not self._statusbar:
            raise WindowInitializationError("Statusbar not initialized")
        return self._statusbar
    
    def get_central_widget(self) -> QWidget:
        """Get the central widget container.
        
        Returns:
            Central widget for content
        """
        if not self._central_widget:
            raise WindowInitializationError("Central widget not initialized")
        return self._central_widget
    
    def get_central_layout(self) -> QVBoxLayout:
        """Get the central layout.
        
        Returns:
            Central layout for adding widgets
        """
        if not hasattr(self, '_central_layout') or self._central_layout is None:
            raise WindowInitializationError("Central layout not initialized")
        return self._central_layout
    
    def add_toolbar(self, toolbar: QToolBar, area: Qt.ToolBarArea = Qt.ToolBarArea.TopToolBarArea) -> None:
        """Add a new toolbar to the window.
        
        Args:
            toolbar: Toolbar to add
            area: Toolbar area (top, bottom, left, right)
        """
        self.addToolBar(area, toolbar)
        logger.debug(f"Added toolbar: {toolbar.windowTitle()}")
    
    def set_central_content(self, widget: QWidget) -> None:
        """Set the main content widget.
        
        Args:
            widget: Widget to set as central content
        """
        # Clear existing content
        while self._central_layout.count():
            item = self._central_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Add new content
        self._central_layout.addWidget(widget)
        logger.debug("Central content updated")
    
    def show_status_message(self, message: str, timeout: int = 5000) -> None:
        """Show a message in the status bar.
        
        Args:
            message: Message to display
            timeout: Display duration in milliseconds
        """
        if self._statusbar:
            self._statusbar.showMessage(message, timeout)
    
    def get_window_state(self) -> Dict[str, Any]:
        """Get current window state.
        
        Returns:
            Dictionary containing window state
        """
        return {
            'geometry': self.geometry().getRect(),
            'maximized': self.isMaximized(),
            'fullscreen': self.isFullScreen(),
            'size': {'width': self.width(), 'height': self.height()},
            'position': {'x': self.x(), 'y': self.y()}
        }
    
    # Event handlers
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if not self._is_closing:
            self.close_application()
        event.accept()


def create_application() -> QApplication:
    """Create and configure QApplication instance with high DPI support."""
    # PyQt6 handles high DPI automatically, but we keep these for PyQt5 compatibility
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ToreMatrix V3")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("ToreMatrix Labs")
    app.setOrganizationDomain("torematrix.com")
    
    # Set application style (will be overridden by theme system later)
    app.setStyle("Fusion")
    
    return app