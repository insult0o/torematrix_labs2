"""Advanced window and dialog management system for ToreMatrix V3.

This module provides comprehensive window management functionality including
multi-window support, dialog management, and cross-platform compatibility.
"""

from typing import Dict, List, Optional, Type, Any, Callable, Union
from pathlib import Path
from enum import Enum
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QMessageBox,
    QFileDialog, QInputDialog, QProgressDialog, QColorDialog,
    QFontDialog, QWizard, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import (
    Qt, QObject, QTimer, pyqtSignal, QSettings, QRect, QPoint,
    QSize, QThread, QMutex, QEvent
)
from PyQt6.QtGui import QIcon, QScreen, QPixmap, QAction

from ..core.events import EventBus
from ..core.config import ConfigManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class WindowType(Enum):
    """Types of windows in the application."""
    MAIN = "main"
    SECONDARY = "secondary"
    DIALOG = "dialog"
    POPUP = "popup"
    FLOATING = "floating"
    TOOL = "tool"


class DialogResult(Enum):
    """Standard dialog results."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    YES = "yes"
    NO = "no"
    OK = "ok"
    CUSTOM = "custom"


@dataclass
class WindowInfo:
    """Information about a managed window."""
    window_id: str
    window: QWidget
    window_type: WindowType
    title: str
    icon_path: Optional[str] = None
    closable: bool = True
    minimizable: bool = True
    maximizable: bool = True
    modal: bool = False
    parent_id: Optional[str] = None
    created_at: Optional[str] = None


class ManagedWindow(QWidget):
    """Base class for managed windows with common functionality."""
    
    # Signals
    window_closing = pyqtSignal(str)  # window_id
    window_activated = pyqtSignal(str)  # window_id
    window_deactivated = pyqtSignal(str)  # window_id
    window_resized = pyqtSignal(str, QSize)  # window_id, size
    window_moved = pyqtSignal(str, QPoint)  # window_id, position
    
    def __init__(
        self,
        window_id: str,
        window_type: WindowType = WindowType.SECONDARY,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.window_id = window_id
        self.window_type = window_type
        self._window_manager: Optional['WindowManager'] = None
        
        # Setup window properties
        self.setWindowTitle(f"ToreMatrix - {window_id}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Default size
        self.resize(800, 600)
    
    def set_window_manager(self, manager: 'WindowManager') -> None:
        """Set the window manager reference."""
        self._window_manager = manager
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.window_closing.emit(self.window_id)
        
        # Notify window manager
        if self._window_manager:
            self._window_manager.unregister_window(self.window_id)
        
        super().closeEvent(event)
    
    def changeEvent(self, event: QEvent) -> None:
        """Handle window state changes."""
        super().changeEvent(event)
        
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.window_activated.emit(self.window_id)
            else:
                self.window_deactivated.emit(self.window_id)
    
    def resizeEvent(self, event) -> None:
        """Handle window resize."""
        super().resizeEvent(event)
        self.window_resized.emit(self.window_id, event.size())
    
    def moveEvent(self, event) -> None:
        """Handle window move."""
        super().moveEvent(event)
        self.window_moved.emit(self.window_id, event.pos())


class ManagedDialog(QDialog):
    """Base class for managed dialogs."""
    
    # Signals
    dialog_finished = pyqtSignal(str, int)  # dialog_id, result
    
    def __init__(
        self,
        dialog_id: str,
        parent: Optional[QWidget] = None,
        modal: bool = True
    ):
        super().__init__(parent)
        self.dialog_id = dialog_id
        self._window_manager: Optional['WindowManager'] = None
        
        # Setup dialog properties
        self.setModal(modal)
        self.setWindowTitle(f"ToreMatrix - {dialog_id}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Connect finished signal
        self.finished.connect(self._on_finished)
    
    def set_window_manager(self, manager: 'WindowManager') -> None:
        """Set the window manager reference."""
        self._window_manager = manager
    
    def _on_finished(self, result: int) -> None:
        """Handle dialog finished."""
        self.dialog_finished.emit(self.dialog_id, result)
        
        # Notify window manager
        if self._window_manager:
            self._window_manager.unregister_window(self.dialog_id)


class SystemTrayManager(QObject):
    """System tray icon management."""
    
    # Signals
    tray_activated = pyqtSignal(int)  # activation_reason
    tray_message_clicked = pyqtSignal()
    
    def __init__(self, main_window: QMainWindow, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.main_window = main_window
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_menu: Optional[QMenu] = None
        
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_tray_icon()
    
    def setup_tray_icon(self) -> None:
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon
        icon = self.main_window.windowIcon()
        if not icon.isNull():
            self.tray_icon.setIcon(icon)
        else:
            # Use default icon
            self.tray_icon.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon
            ))
        
        # Create context menu
        self.tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_main_window)
        self.tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide_main_window)
        self.tray_menu.addAction(hide_action)
        
        self.tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # Connect signals
        self.tray_icon.activated.connect(self.tray_activated.emit)
        self.tray_icon.messageClicked.connect(self.tray_message_clicked.emit)
        
        # Set tooltip
        self.tray_icon.setToolTip("ToreMatrix V3")
    
    def show_tray_icon(self) -> None:
        """Show system tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
    
    def hide_tray_icon(self) -> None:
        """Hide system tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        timeout: int = 5000
    ) -> None:
        """Show tray notification message."""
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, timeout)
    
    def show_main_window(self) -> None:
        """Show and activate main window."""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def hide_main_window(self) -> None:
        """Hide main window."""
        self.main_window.hide()
    
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return QSystemTrayIcon.isSystemTrayAvailable()


class WindowManager(QObject):
    """Advanced window and dialog management system."""
    
    # Signals
    window_registered = pyqtSignal(str)  # window_id
    window_unregistered = pyqtSignal(str)  # window_id
    window_activated = pyqtSignal(str)  # window_id
    active_window_changed = pyqtSignal(str, str)  # old_id, new_id
    dialog_opened = pyqtSignal(str)  # dialog_id
    dialog_closed = pyqtSignal(str, int)  # dialog_id, result
    
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
        
        # Window tracking
        self.windows: Dict[str, WindowInfo] = {}
        self.active_window_id: Optional[str] = None
        
        # Dialog tracking
        self.open_dialogs: Dict[str, QDialog] = {}
        
        # System tray
        self.tray_manager = SystemTrayManager(main_window, self)
        
        # Threading protection
        self.mutex = QMutex()
        
        # Register main window
        self._register_main_window()
        
        # Setup connections
        self.setup_connections()
        
        logger.info("WindowManager initialized")
    
    def _register_main_window(self) -> None:
        """Register the main window."""
        main_info = WindowInfo(
            window_id="main",
            window=self.main_window,
            window_type=WindowType.MAIN,
            title=self.main_window.windowTitle(),
            closable=True,
            minimizable=True,
            maximizable=True
        )
        
        self.windows["main"] = main_info
        self.active_window_id = "main"
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        # Event bus connections
        self.event_bus.subscribe("ui.window.create", self._on_create_window_event)
        self.event_bus.subscribe("ui.window.close", self._on_close_window_event)
        self.event_bus.subscribe("ui.dialog.show", self._on_show_dialog_event)
        
        # Tray manager connections
        self.tray_manager.tray_activated.connect(self._on_tray_activated)
    
    def register_window(
        self,
        window: QWidget,
        window_id: str,
        window_type: WindowType = WindowType.SECONDARY,
        **kwargs
    ) -> bool:
        """Register a window for management."""
        if window_id in self.windows:
            logger.warning(f"Window {window_id} already registered")
            return False
        
        try:
            window_info = WindowInfo(
                window_id=window_id,
                window=window,
                window_type=window_type,
                title=kwargs.get('title', window.windowTitle()),
                icon_path=kwargs.get('icon_path'),
                closable=kwargs.get('closable', True),
                minimizable=kwargs.get('minimizable', True),
                maximizable=kwargs.get('maximizable', True),
                modal=kwargs.get('modal', False),
                parent_id=kwargs.get('parent_id')
            )
            
            self.windows[window_id] = window_info
            
            # Setup window properties
            if hasattr(window, 'set_window_manager'):
                window.set_window_manager(self)
            
            # Connect signals if it's a managed window
            if isinstance(window, (ManagedWindow, ManagedDialog)):
                self._connect_window_signals(window)
            
            self.window_registered.emit(window_id)
            logger.debug(f"Registered window: {window_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register window {window_id}: {e}")
            return False
    
    def unregister_window(self, window_id: str) -> bool:
        """Unregister a window."""
        if window_id not in self.windows:
            logger.warning(f"Window {window_id} not found")
            return False
        
        try:
            window_info = self.windows[window_id]
            
            # Remove from tracking
            del self.windows[window_id]
            
            # Update active window
            if self.active_window_id == window_id:
                self.active_window_id = "main" if "main" in self.windows else None
            
            self.window_unregistered.emit(window_id)
            logger.debug(f"Unregistered window: {window_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister window {window_id}: {e}")
            return False
    
    def create_window(
        self,
        window_class: Type[QWidget],
        window_id: str,
        window_type: WindowType = WindowType.SECONDARY,
        **kwargs
    ) -> Optional[QWidget]:
        """Create and register a new window."""
        try:
            # Create window instance
            parent = kwargs.get('parent', self.main_window)
            
            if issubclass(window_class, ManagedWindow):
                window = window_class(window_id, window_type, parent)
            else:
                window = window_class(parent)
            
            # Register window
            if self.register_window(window, window_id, window_type, **kwargs):
                return window
            else:
                window.deleteLater()
                return None
                
        except Exception as e:
            logger.error(f"Failed to create window {window_id}: {e}")
            return None
    
    def close_window(self, window_id: str, force: bool = False) -> bool:
        """Close a window."""
        if window_id not in self.windows:
            logger.warning(f"Window {window_id} not found")
            return False
        
        try:
            window_info = self.windows[window_id]
            window = window_info.window
            
            if force:
                window.close()
            else:
                # Try graceful close
                if hasattr(window, 'closeEvent'):
                    window.close()
                else:
                    window.hide()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to close window {window_id}: {e}")
            return False
    
    def show_window(self, window_id: str) -> bool:
        """Show and activate a window."""
        if window_id not in self.windows:
            logger.warning(f"Window {window_id} not found")
            return False
        
        try:
            window = self.windows[window_id].window
            window.show()
            window.raise_()
            window.activateWindow()
            
            # Update active window
            old_active = self.active_window_id
            self.active_window_id = window_id
            
            if old_active != window_id:
                self.active_window_changed.emit(old_active or "", window_id)
            
            self.window_activated.emit(window_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to show window {window_id}: {e}")
            return False
    
    def hide_window(self, window_id: str) -> bool:
        """Hide a window."""
        if window_id not in self.windows:
            logger.warning(f"Window {window_id} not found")
            return False
        
        try:
            window = self.windows[window_id].window
            window.hide()
            return True
            
        except Exception as e:
            logger.error(f"Failed to hide window {window_id}: {e}")
            return False
    
    def get_window(self, window_id: str) -> Optional[QWidget]:
        """Get a window by ID."""
        if window_id in self.windows:
            return self.windows[window_id].window
        return None
    
    def get_window_info(self, window_id: str) -> Optional[WindowInfo]:
        """Get window information."""
        return self.windows.get(window_id)
    
    def get_all_windows(self) -> List[str]:
        """Get list of all window IDs."""
        return list(self.windows.keys())
    
    def get_windows_by_type(self, window_type: WindowType) -> List[str]:
        """Get windows of a specific type."""
        return [
            window_id for window_id, info in self.windows.items()
            if info.window_type == window_type
        ]
    
    def show_message_box(
        self,
        title: str,
        message: str,
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        parent: Optional[QWidget] = None
    ) -> DialogResult:
        """Show a message box dialog."""
        if not parent:
            parent = self.main_window
        
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setStandardButtons(buttons)
        
        result = msg_box.exec()
        
        # Convert QMessageBox result to DialogResult
        if result == QMessageBox.StandardButton.Ok:
            return DialogResult.OK
        elif result == QMessageBox.StandardButton.Yes:
            return DialogResult.YES
        elif result == QMessageBox.StandardButton.No:
            return DialogResult.NO
        elif result == QMessageBox.StandardButton.Cancel:
            return DialogResult.CANCELLED
        else:
            return DialogResult.CUSTOM
    
    def show_file_dialog(
        self,
        dialog_type: str = "open",
        title: str = "",
        directory: str = "",
        filter: str = "",
        parent: Optional[QWidget] = None
    ) -> Optional[str]:
        """Show a file dialog."""
        if not parent:
            parent = self.main_window
        
        if dialog_type == "open":
            file_path, _ = QFileDialog.getOpenFileName(parent, title, directory, filter)
        elif dialog_type == "save":
            file_path, _ = QFileDialog.getSaveFileName(parent, title, directory, filter)
        elif dialog_type == "directory":
            file_path = QFileDialog.getExistingDirectory(parent, title, directory)
        else:
            return None
        
        return file_path if file_path else None
    
    def show_input_dialog(
        self,
        title: str,
        label: str,
        default_text: str = "",
        parent: Optional[QWidget] = None
    ) -> Optional[str]:
        """Show an input dialog."""
        if not parent:
            parent = self.main_window
        
        text, ok = QInputDialog.getText(parent, title, label, text=default_text)
        return text if ok else None
    
    def show_progress_dialog(
        self,
        title: str,
        label: str,
        minimum: int = 0,
        maximum: int = 100,
        parent: Optional[QWidget] = None
    ) -> QProgressDialog:
        """Show a progress dialog."""
        if not parent:
            parent = self.main_window
        
        progress = QProgressDialog(label, "Cancel", minimum, maximum, parent)
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        return progress
    
    def enable_system_tray(self) -> bool:
        """Enable system tray icon."""
        if self.tray_manager.is_available():
            self.tray_manager.show_tray_icon()
            return True
        return False
    
    def disable_system_tray(self) -> None:
        """Disable system tray icon."""
        self.tray_manager.hide_tray_icon()
    
    def show_tray_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        timeout: int = 5000
    ) -> None:
        """Show system tray notification."""
        self.tray_manager.show_message(title, message, icon, timeout)
    
    def cascade_windows(self) -> None:
        """Arrange windows in cascade layout."""
        offset = 30
        x, y = 100, 100
        
        for window_id, window_info in self.windows.items():
            if window_info.window_type != WindowType.MAIN and window_info.window.isVisible():
                window_info.window.move(x, y)
                x += offset
                y += offset
    
    def tile_windows(self) -> None:
        """Arrange windows in tile layout."""
        visible_windows = [
            info.window for info in self.windows.values()
            if info.window_type != WindowType.MAIN and info.window.isVisible()
        ]
        
        if not visible_windows:
            return
        
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        
        # Calculate tile dimensions
        cols = int(len(visible_windows) ** 0.5) + 1
        rows = (len(visible_windows) + cols - 1) // cols
        
        width = screen_rect.width() // cols
        height = screen_rect.height() // rows
        
        for i, window in enumerate(visible_windows):
            row = i // cols
            col = i % cols
            
            x = screen_rect.x() + col * width
            y = screen_rect.y() + row * height
            
            window.setGeometry(x, y, width, height)
    
    # Private methods
    def _connect_window_signals(self, window: Union[ManagedWindow, ManagedDialog]) -> None:
        """Connect signals for managed windows."""
        if isinstance(window, ManagedWindow):
            window.window_activated.connect(self.window_activated.emit)
        elif isinstance(window, ManagedDialog):
            window.dialog_finished.connect(self._on_dialog_finished)
    
    def _on_dialog_finished(self, dialog_id: str, result: int) -> None:
        """Handle dialog finished."""
        self.dialog_closed.emit(dialog_id, result)
    
    # Event handlers
    def _on_create_window_event(self, data: Dict[str, Any]) -> None:
        """Handle create window event."""
        window_class = data.get('window_class')
        window_id = data.get('window_id')
        window_type = data.get('window_type', WindowType.SECONDARY)
        
        if window_class and window_id:
            self.create_window(window_class, window_id, window_type, **data)
    
    def _on_close_window_event(self, data: Dict[str, Any]) -> None:
        """Handle close window event."""
        window_id = data.get('window_id')
        force = data.get('force', False)
        
        if window_id:
            self.close_window(window_id, force)
    
    def _on_show_dialog_event(self, data: Dict[str, Any]) -> None:
        """Handle show dialog event."""
        dialog_type = data.get('type', 'message')
        
        if dialog_type == 'message':
            self.show_message_box(
                data.get('title', ''),
                data.get('message', ''),
                data.get('icon', QMessageBox.Icon.Information),
                data.get('buttons', QMessageBox.StandardButton.Ok)
            )
        elif dialog_type == 'file':
            self.show_file_dialog(
                data.get('dialog_type', 'open'),
                data.get('title', ''),
                data.get('directory', ''),
                data.get('filter', '')
            )
    
    def _on_tray_activated(self, reason: int) -> None:
        """Handle system tray activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.show_window("main")