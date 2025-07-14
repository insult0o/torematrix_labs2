"""Advanced window state persistence system for ToreMatrix V3.

This module provides comprehensive window state management using QSettings,
including geometry, splitter states, panel layouts, and application preferences.
"""

from typing import Dict, List, Optional, Any, Union, Type
from pathlib import Path
from enum import Enum
import logging
import json
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QDockWidget, QHeaderView,
    QTreeWidget, QTableWidget, QListWidget, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QSettings, QByteArray, QRect, QSize, QPoint,
    QObject, pyqtSignal, QTimer, QStandardPaths
)
from PyQt6.QtGui import QScreen

from ..core.config import ConfigManager
from ..core.events import EventBus
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class PersistenceScope(Enum):
    """Scope of persistence settings."""
    GLOBAL = "global"  # Application-wide settings
    PROJECT = "project"  # Project-specific settings
    SESSION = "session"  # Current session only
    TEMPORARY = "temporary"  # Temporary, cleared on restart


@dataclass
class WindowState:
    """Window state data."""
    geometry: tuple  # (x, y, width, height)
    maximized: bool
    minimized: bool
    window_state: Optional[bytes] = None  # QMainWindow state
    screen_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowState':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SplitterState:
    """Splitter state data."""
    sizes: List[int]
    orientation: int  # Qt.Orientation
    collapsed: List[bool]  # Which panes are collapsed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SplitterState':
        """Create from dictionary."""
        return cls(**data)


class PersistentWidget(ABC):
    """Interface for widgets that support state persistence."""
    
    @abstractmethod
    def save_state(self) -> Dict[str, Any]:
        """Save widget state to dictionary."""
        pass
    
    @abstractmethod
    def restore_state(self, state: Dict[str, Any]) -> bool:
        """Restore widget state from dictionary."""
        pass
    
    @abstractmethod
    def get_state_key(self) -> str:
        """Get unique key for this widget's state."""
        pass


class WidgetStateMixin:
    """Mixin to add state persistence to any widget."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_key: Optional[str] = None
        self._auto_save = True
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_state)
    
    def set_state_key(self, key: str) -> None:
        """Set the state key for this widget."""
        self._state_key = key
    
    def get_state_key(self) -> str:
        """Get the state key for this widget."""
        if self._state_key:
            return self._state_key
        return f"{self.__class__.__name__}_{id(self)}"
    
    def enable_auto_save(self, enabled: bool = True, delay_ms: int = 1000) -> None:
        """Enable automatic state saving."""
        self._auto_save = enabled
        if enabled:
            self._save_timer.setInterval(delay_ms)
    
    def schedule_save(self) -> None:
        """Schedule a delayed save operation."""
        if self._auto_save:
            self._save_timer.start()
    
    def _auto_save_state(self) -> None:
        """Auto-save callback."""
        if hasattr(self, 'persistence_manager'):
            self.persistence_manager.save_widget_state(self)


class HeaderViewPersistence:
    """Helper for QHeaderView state persistence."""
    
    @staticmethod
    def save_header_state(header: QHeaderView) -> Dict[str, Any]:
        """Save header view state."""
        state = {
            'sort_indicator_section': header.sortIndicatorSection(),
            'sort_indicator_order': int(header.sortIndicatorOrder()),
            'section_sizes': [],
            'section_hidden': [],
            'section_order': []
        }
        
        for i in range(header.count()):
            state['section_sizes'].append(header.sectionSize(i))
            state['section_hidden'].append(header.isSectionHidden(i))
            state['section_order'].append(header.visualIndex(i))
        
        return state
    
    @staticmethod
    def restore_header_state(header: QHeaderView, state: Dict[str, Any]) -> bool:
        """Restore header view state."""
        try:
            # Restore section sizes
            for i, size in enumerate(state.get('section_sizes', [])):
                if i < header.count():
                    header.resizeSection(i, size)
            
            # Restore hidden sections
            for i, hidden in enumerate(state.get('section_hidden', [])):
                if i < header.count():
                    header.setSectionHidden(i, hidden)
            
            # Restore section order
            section_order = state.get('section_order', [])
            if len(section_order) == header.count():
                for logical_index, visual_index in enumerate(section_order):
                    header.moveSection(header.visualIndex(logical_index), visual_index)
            
            # Restore sort indicator
            sort_section = state.get('sort_indicator_section', -1)
            sort_order = state.get('sort_indicator_order', 0)
            if sort_section >= 0:
                header.setSortIndicator(sort_section, Qt.SortOrder(sort_order))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore header state: {e}")
            return False


class WindowPersistence(QObject):
    """Complete window state management with QSettings."""
    
    # Signals
    state_saved = pyqtSignal(str)  # state_key
    state_restored = pyqtSignal(str)  # state_key
    save_failed = pyqtSignal(str, str)  # state_key, error
    restore_failed = pyqtSignal(str, str)  # state_key, error
    
    def __init__(
        self,
        main_window: QMainWindow,
        config_manager: Optional[ConfigManager] = None,
        scope: PersistenceScope = PersistenceScope.GLOBAL,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.main_window = main_window
        self.config_manager = config_manager
        self.scope = scope
        
        # Settings management
        self.settings = self._create_settings()
        
        # State tracking
        self.widget_states: Dict[str, Dict[str, Any]] = {}
        self.auto_save_enabled = True
        self.save_interval = 5000  # 5 seconds
        
        # Auto-save timer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._auto_save_all)
        
        # Track widgets for automatic persistence
        self.tracked_widgets: Dict[str, QWidget] = {}
        
        logger.info(f"WindowPersistence initialized with scope: {scope.value}")
    
    def _create_settings(self) -> QSettings:
        """Create QSettings instance based on scope."""
        if self.scope == PersistenceScope.GLOBAL:
            return QSettings()
        elif self.scope == PersistenceScope.PROJECT:
            # Use project-specific settings if config manager available
            if self.config_manager:
                project_name = getattr(self.config_manager, 'project_name', 'default')
                return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, 
                               "ToreMatrix", f"Project_{project_name}")
            return QSettings()
        elif self.scope == PersistenceScope.SESSION:
            # Store in temporary location
            temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
            temp_file = Path(temp_dir) / "torematrix_session.ini"
            return QSettings(str(temp_file), QSettings.Format.IniFormat)
        else:  # TEMPORARY
            # Memory-only settings
            return QSettings()
    
    def enable_auto_save(self, enabled: bool = True, interval_ms: int = 5000) -> None:
        """Enable or disable automatic saving."""
        self.auto_save_enabled = enabled
        self.save_interval = interval_ms
        
        if enabled:
            self.auto_save_timer.start(interval_ms)
        else:
            self.auto_save_timer.stop()
    
    def save_window_state(self, key: str = "main_window") -> bool:
        """Save main window state."""
        try:
            window = self.main_window
            
            # Get window geometry
            geometry = window.geometry()
            state_data = WindowState(
                geometry=(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                maximized=window.isMaximized(),
                minimized=window.isMinimized(),
                window_state=window.saveState().data(),
                screen_name=self._get_screen_name(window)
            )
            
            # Save to settings
            self.settings.beginGroup(f"WindowState/{key}")
            self.settings.setValue("geometry", state_data.geometry)
            self.settings.setValue("maximized", state_data.maximized)
            self.settings.setValue("minimized", state_data.minimized)
            self.settings.setValue("window_state", state_data.window_state)
            self.settings.setValue("screen_name", state_data.screen_name)
            self.settings.endGroup()
            
            # Store in memory cache
            self.widget_states[key] = state_data.to_dict()
            
            self.state_saved.emit(key)
            logger.debug(f"Saved window state: {key}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save window state {key}: {e}"
            logger.error(error_msg)
            self.save_failed.emit(key, str(e))
            return False
    
    def restore_window_state(self, key: str = "main_window") -> bool:
        """Restore main window state."""
        try:
            self.settings.beginGroup(f"WindowState/{key}")
            
            # Check if state exists
            if not self.settings.contains("geometry"):
                self.settings.endGroup()
                logger.debug(f"No saved state found for window: {key}")
                return False
            
            # Load state data
            geometry = self.settings.value("geometry")
            maximized = self.settings.value("maximized", False, type=bool)
            minimized = self.settings.value("minimized", False, type=bool)
            window_state = self.settings.value("window_state")
            screen_name = self.settings.value("screen_name")
            
            self.settings.endGroup()
            
            window = self.main_window
            
            # Validate and adjust geometry for current screen setup
            if geometry and len(geometry) == 4:
                x, y, w, h = geometry
                adjusted_geometry = self._validate_geometry(x, y, w, h, screen_name)
                window.setGeometry(*adjusted_geometry)
            
            # Restore window state (docks, toolbars, etc.)
            if window_state:
                window.restoreState(QByteArray(window_state))
            
            # Restore window flags
            if maximized:
                window.showMaximized()
            elif minimized:
                window.showMinimized()
            else:
                window.showNormal()
            
            self.state_restored.emit(key)
            logger.debug(f"Restored window state: {key}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to restore window state {key}: {e}"
            logger.error(error_msg)
            self.restore_failed.emit(key, str(e))
            return False
    
    def save_splitter_state(self, splitter: QSplitter, key: str) -> bool:
        """Save splitter state."""
        try:
            state_data = SplitterState(
                sizes=splitter.sizes(),
                orientation=int(splitter.orientation()),
                collapsed=[splitter.widget(i).isHidden() for i in range(splitter.count())]
            )
            
            # Save to settings
            self.settings.beginGroup(f"SplitterState/{key}")
            self.settings.setValue("sizes", state_data.sizes)
            self.settings.setValue("orientation", state_data.orientation)
            self.settings.setValue("collapsed", state_data.collapsed)
            self.settings.endGroup()
            
            # Store in memory cache
            self.widget_states[f"splitter_{key}"] = state_data.to_dict()
            
            logger.debug(f"Saved splitter state: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save splitter state {key}: {e}")
            return False
    
    def restore_splitter_state(self, splitter: QSplitter, key: str) -> bool:
        """Restore splitter state."""
        try:
            self.settings.beginGroup(f"SplitterState/{key}")
            
            if not self.settings.contains("sizes"):
                self.settings.endGroup()
                return False
            
            sizes = self.settings.value("sizes", [])
            orientation = self.settings.value("orientation", int(Qt.Orientation.Horizontal), type=int)
            collapsed = self.settings.value("collapsed", [])
            
            self.settings.endGroup()
            
            # Restore orientation
            splitter.setOrientation(Qt.Orientation(orientation))
            
            # Restore sizes
            if sizes and len(sizes) == splitter.count():
                splitter.setSizes(sizes)
            
            # Restore collapsed states
            if collapsed and len(collapsed) == splitter.count():
                for i, is_collapsed in enumerate(collapsed):
                    widget = splitter.widget(i)
                    if widget:
                        widget.setHidden(is_collapsed)
            
            logger.debug(f"Restored splitter state: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore splitter state {key}: {e}")
            return False
    
    def save_widget_state(self, widget: QWidget, key: Optional[str] = None) -> bool:
        """Save generic widget state."""
        if not key:
            if hasattr(widget, 'get_state_key'):
                key = widget.get_state_key()
            else:
                key = f"{widget.__class__.__name__}_{id(widget)}"
        
        try:
            state_data = {}
            
            # Handle different widget types
            if isinstance(widget, QSplitter):
                return self.save_splitter_state(widget, key)
            
            elif isinstance(widget, (QTreeWidget, QTableWidget, QListWidget)):
                # Save header state for tree/table widgets
                if hasattr(widget, 'header'):
                    header = widget.header()
                    state_data['header'] = HeaderViewPersistence.save_header_state(header)
                
                # Save selection
                if hasattr(widget, 'selectedItems'):
                    selected = [self._get_item_identifier(item) for item in widget.selectedItems()]
                    state_data['selected_items'] = selected
            
            elif isinstance(widget, QTabWidget):
                state_data['current_index'] = widget.currentIndex()
                state_data['tab_order'] = [widget.tabText(i) for i in range(widget.count())]
            
            # Check if widget implements PersistentWidget interface
            if isinstance(widget, PersistentWidget):
                state_data.update(widget.save_state())
            
            # Save widget geometry
            state_data['geometry'] = (
                widget.x(), widget.y(),
                widget.width(), widget.height()
            )
            state_data['visible'] = widget.isVisible()
            
            # Save to settings
            self.settings.beginGroup(f"WidgetState/{key}")
            for state_key, value in state_data.items():
                self.settings.setValue(state_key, value)
            self.settings.endGroup()
            
            # Store in memory cache
            self.widget_states[key] = state_data
            
            logger.debug(f"Saved widget state: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save widget state {key}: {e}")
            return False
    
    def restore_widget_state(self, widget: QWidget, key: Optional[str] = None) -> bool:
        """Restore generic widget state."""
        if not key:
            if hasattr(widget, 'get_state_key'):
                key = widget.get_state_key()
            else:
                key = f"{widget.__class__.__name__}_{id(widget)}"
        
        try:
            self.settings.beginGroup(f"WidgetState/{key}")
            
            # Check if state exists
            if not self.settings.allKeys():
                self.settings.endGroup()
                return False
            
            # Restore widget geometry
            if self.settings.contains("geometry"):
                geometry = self.settings.value("geometry")
                if geometry and len(geometry) == 4:
                    widget.setGeometry(*geometry)
            
            if self.settings.contains("visible"):
                visible = self.settings.value("visible", True, type=bool)
                widget.setVisible(visible)
            
            # Handle different widget types
            if isinstance(widget, (QTreeWidget, QTableWidget, QListWidget)):
                # Restore header state
                if self.settings.contains("header") and hasattr(widget, 'header'):
                    header_state = self.settings.value("header")
                    if header_state:
                        HeaderViewPersistence.restore_header_state(widget.header(), header_state)
                
                # Restore selection
                if self.settings.contains("selected_items"):
                    selected_items = self.settings.value("selected_items", [])
                    self._restore_widget_selection(widget, selected_items)
            
            elif isinstance(widget, QTabWidget):
                if self.settings.contains("current_index"):
                    index = self.settings.value("current_index", 0, type=int)
                    if 0 <= index < widget.count():
                        widget.setCurrentIndex(index)
            
            # Check if widget implements PersistentWidget interface
            if isinstance(widget, PersistentWidget):
                state_data = {}
                for key in self.settings.allKeys():
                    state_data[key] = self.settings.value(key)
                widget.restore_state(state_data)
            
            self.settings.endGroup()
            
            logger.debug(f"Restored widget state: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore widget state {key}: {e}")
            return False
    
    def track_widget(self, widget: QWidget, key: Optional[str] = None) -> None:
        """Add widget to automatic state tracking."""
        if not key:
            if hasattr(widget, 'get_state_key'):
                key = widget.get_state_key()
            else:
                key = f"{widget.__class__.__name__}_{id(widget)}"
        
        self.tracked_widgets[key] = widget
        
        # Apply mixin if not already present
        if not hasattr(widget, 'schedule_save'):
            # Dynamically add mixin methods
            widget.persistence_manager = self
            widget.schedule_save = lambda: self.save_widget_state(widget, key)
        
        logger.debug(f"Now tracking widget: {key}")
    
    def untrack_widget(self, key: str) -> None:
        """Remove widget from automatic state tracking."""
        if key in self.tracked_widgets:
            del self.tracked_widgets[key]
            logger.debug(f"Stopped tracking widget: {key}")
    
    def save_all_states(self) -> bool:
        """Save all tracked widget states."""
        success = True
        
        # Save main window
        if not self.save_window_state():
            success = False
        
        # Save all tracked widgets
        for key, widget in self.tracked_widgets.items():
            if not self.save_widget_state(widget, key):
                success = False
        
        # Sync settings to disk
        self.settings.sync()
        
        return success
    
    def restore_all_states(self) -> bool:
        """Restore all tracked widget states."""
        success = True
        
        # Restore main window
        if not self.restore_window_state():
            success = False
        
        # Restore all tracked widgets
        for key, widget in self.tracked_widgets.items():
            if not self.restore_widget_state(widget, key):
                success = False
        
        return success
    
    def clear_all_states(self) -> None:
        """Clear all saved states."""
        self.settings.clear()
        self.widget_states.clear()
        logger.info("Cleared all saved states")
    
    def export_states(self, file_path: Union[str, Path]) -> bool:
        """Export all states to JSON file."""
        try:
            # Collect all states
            export_data = {
                'version': '1.0',
                'scope': self.scope.value,
                'states': {}
            }
            
            # Export from settings
            for key in self.settings.allKeys():
                export_data['states'][key] = self.settings.value(key)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported states to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export states: {e}")
            return False
    
    def import_states(self, file_path: Union[str, Path]) -> bool:
        """Import states from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate format
            if 'states' not in import_data:
                logger.error("Invalid import file format")
                return False
            
            # Clear existing states
            self.settings.clear()
            
            # Import states
            for key, value in import_data['states'].items():
                self.settings.setValue(key, value)
            
            self.settings.sync()
            
            logger.info(f"Imported states from: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import states: {e}")
            return False
    
    # Private helper methods
    def _get_screen_name(self, window: QWidget) -> str:
        """Get the name of the screen containing the window."""
        try:
            screen = window.screen()
            if screen:
                return screen.name()
        except:
            pass
        return "primary"
    
    def _validate_geometry(self, x: int, y: int, w: int, h: int, screen_name: Optional[str]) -> tuple:
        """Validate and adjust geometry for current screen setup."""
        from PyQt6.QtWidgets import QApplication
        
        # Get available screens
        screens = QApplication.screens()
        target_screen = None
        
        # Find target screen
        if screen_name:
            target_screen = next((s for s in screens if s.name() == screen_name), None)
        
        # Use primary screen if target not found
        if not target_screen:
            target_screen = QApplication.primaryScreen()
        
        if target_screen:
            screen_geometry = target_screen.availableGeometry()
            
            # Ensure window fits on screen
            w = min(w, screen_geometry.width())
            h = min(h, screen_geometry.height())
            
            # Ensure window is visible
            x = max(screen_geometry.x(), min(x, screen_geometry.right() - w))
            y = max(screen_geometry.y(), min(y, screen_geometry.bottom() - h))
        
        return (x, y, w, h)
    
    def _get_item_identifier(self, item) -> str:
        """Get unique identifier for a widget item."""
        if hasattr(item, 'text'):
            return item.text(0) if hasattr(item.text, '__call__') else str(item.text)
        elif hasattr(item, 'data'):
            return str(item.data(Qt.ItemDataRole.DisplayRole))
        return str(item)
    
    def _restore_widget_selection(self, widget: QWidget, selected_items: List[str]) -> None:
        """Restore widget selection."""
        # Implementation depends on widget type
        # This is a simplified version
        pass
    
    def _auto_save_all(self) -> None:
        """Auto-save all tracked states."""
        if self.auto_save_enabled:
            self.save_all_states()