"""Advanced dockable panel management system for ToreMatrix V3.

This module provides comprehensive panel management with persistence,
flexible docking architecture, and seamless integration with the UI framework.
"""

from typing import Dict, List, Optional, Type, Any, Callable, Set
from pathlib import Path
from enum import Enum
import logging
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QFrame, QSizePolicy,
    QApplication, QSplitter
)
from PyQt6.QtCore import (
    Qt, QSettings, QTimer, pyqtSignal, QObject, QSize, QRect,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QIcon, QAction

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class PanelState(Enum):
    """Panel visibility and state enumeration."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    FLOATING = "floating"
    DOCKED = "docked"
    MINIMIZED = "minimized"


@dataclass
class PanelConfig:
    """Configuration for a panel."""
    panel_id: str
    title: str
    default_area: Qt.DockWidgetArea
    default_visible: bool = True
    can_close: bool = True
    can_float: bool = True
    can_dock: bool = True
    minimum_size: Optional[QSize] = None
    maximum_size: Optional[QSize] = None
    icon_path: Optional[str] = None
    widget_factory: Optional[Callable[[], QWidget]] = None
    context_menu_actions: List[str] = field(default_factory=list)


@dataclass
class PanelLayout:
    """Represents a saved panel layout configuration."""
    name: str
    description: str
    panel_states: Dict[str, Dict[str, Any]]
    window_geometry: Optional[QRect] = None
    splitter_states: Optional[Dict[str, bytes]] = None
    created_at: Optional[str] = None


class BasePanelWidget(QWidget, ABC):
    """Base class for all panel widgets with common functionality."""
    
    # Signals
    panel_modified = pyqtSignal(str)  # panel_id
    panel_action_requested = pyqtSignal(str, str)  # panel_id, action
    
    def __init__(self, panel_id: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.panel_id = panel_id
        self._is_modified = False
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
    
    @abstractmethod
    def setup_ui(self) -> None:
        """Setup the panel's user interface."""
        pass
    
    def setup_connections(self) -> None:
        """Setup signal connections. Override if needed."""
        pass
    
    def set_modified(self, modified: bool = True) -> None:
        """Mark panel as modified."""
        if self._is_modified != modified:
            self._is_modified = modified
            self.panel_modified.emit(self.panel_id)
    
    def is_modified(self) -> bool:
        """Check if panel has been modified."""
        return self._is_modified
    
    def save_state(self) -> Dict[str, Any]:
        """Save panel state. Override in subclasses."""
        return {}
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore panel state. Override in subclasses."""
        pass


class PanelTitleBar(QFrame):
    """Custom title bar for panels with enhanced features."""
    
    # Signals
    close_requested = pyqtSignal()
    float_requested = pyqtSignal()
    dock_requested = pyqtSignal()
    
    def __init__(self, title: str, panel_config: PanelConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.panel_config = panel_config
        self.setObjectName("PanelTitleBar")
        
        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Icon (if available)
        if panel_config.icon_path:
            icon_label = QLabel()
            icon = QIcon(panel_config.icon_path)
            icon_label.setPixmap(icon.pixmap(16, 16))
            layout.addWidget(icon_label)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; color: palette(windowText);")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Action buttons
        self.setup_action_buttons(layout)
    
    def setup_action_buttons(self, layout: QHBoxLayout) -> None:
        """Setup title bar action buttons."""
        button_size = QSize(20, 20)
        
        # Float/Dock button
        if self.panel_config.can_float:
            self.float_button = QToolButton()
            self.float_button.setFixedSize(button_size)
            self.float_button.setToolTip("Float Panel")
            self.float_button.setText("⧉")
            self.float_button.clicked.connect(self.float_requested.emit)
            layout.addWidget(self.float_button)
        
        # Close button
        if self.panel_config.can_close:
            self.close_button = QToolButton()
            self.close_button.setFixedSize(button_size)
            self.close_button.setToolTip("Close Panel")
            self.close_button.setText("×")
            self.close_button.clicked.connect(self.close_requested.emit)
            layout.addWidget(self.close_button)
    
    def set_title(self, title: str) -> None:
        """Update the title text."""
        self.title_label.setText(title)


class DockWidget(QDockWidget):
    """Enhanced dock widget with advanced features."""
    
    # Signals
    panel_state_changed = pyqtSignal(str, str)  # panel_id, state
    panel_geometry_changed = pyqtSignal(str, QRect)  # panel_id, geometry
    
    def __init__(self, panel_config: PanelConfig, parent: Optional[QWidget] = None):
        super().__init__(panel_config.title, parent)
        self.panel_config = panel_config
        self.panel_id = panel_config.panel_id
        
        # Configure dock widget
        self.setup_dock_widget()
        self.setup_connections()
    
    def setup_dock_widget(self) -> None:
        """Configure the dock widget properties."""
        # Set features
        features = QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        
        if self.panel_config.can_close:
            features |= QDockWidget.DockWidgetFeature.DockWidgetClosable
        
        if self.panel_config.can_float:
            features |= QDockWidget.DockWidgetFeature.DockWidgetFloatable
        
        if self.panel_config.can_dock:
            features |= QDockWidget.DockWidgetFeature.DockWidgetMovable
        
        self.setFeatures(features)
        
        # Set size constraints
        if self.panel_config.minimum_size:
            self.setMinimumSize(self.panel_config.minimum_size)
        
        if self.panel_config.maximum_size:
            self.setMaximumSize(self.panel_config.maximum_size)
        
        # Set object name for styling
        self.setObjectName(f"DockWidget_{self.panel_id}")
        
        # Custom title bar if needed
        if hasattr(self.panel_config, 'custom_title_bar') and self.panel_config.custom_title_bar:
            title_bar = PanelTitleBar(self.panel_config.title, self.panel_config)
            self.setTitleBarWidget(title_bar)
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        self.visibilityChanged.connect(self._on_visibility_changed)
        self.topLevelChanged.connect(self._on_float_changed)
        self.dockLocationChanged.connect(self._on_dock_location_changed)
    
    def _on_visibility_changed(self, visible: bool) -> None:
        """Handle visibility changes."""
        state = PanelState.VISIBLE.value if visible else PanelState.HIDDEN.value
        self.panel_state_changed.emit(self.panel_id, state)
    
    def _on_float_changed(self, floating: bool) -> None:
        """Handle floating state changes."""
        state = PanelState.FLOATING.value if floating else PanelState.DOCKED.value
        self.panel_state_changed.emit(self.panel_id, state)
        
        # Emit geometry change
        if floating:
            self.panel_geometry_changed.emit(self.panel_id, self.geometry())
    
    def _on_dock_location_changed(self, area: Qt.DockWidgetArea) -> None:
        """Handle dock location changes."""
        self.panel_state_changed.emit(self.panel_id, PanelState.DOCKED.value)
        logger.debug(f"Panel {self.panel_id} docked to area: {area}")


class PanelManager(QObject):
    """Advanced dockable panel management with persistence and layouts."""
    
    # Signals
    panel_registered = pyqtSignal(str)  # panel_id
    panel_created = pyqtSignal(str)  # panel_id
    panel_state_changed = pyqtSignal(str, str)  # panel_id, state
    layout_saved = pyqtSignal(str)  # layout_name
    layout_restored = pyqtSignal(str)  # layout_name
    
    def __init__(
        self,
        main_window: QMainWindow,
        config_manager: ConfigManager,
        event_bus: EventBus,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.main_window = main_window
        self.config_manager = config_manager
        self.event_bus = event_bus
        
        # Storage
        self.panel_configs: Dict[str, PanelConfig] = {}
        self.panel_widgets: Dict[str, DockWidget] = {}
        self.panel_layouts: Dict[str, PanelLayout] = {}
        
        # State tracking
        self.panel_states: Dict[str, PanelState] = {}
        self.panel_geometries: Dict[str, QRect] = {}
        
        # Settings
        self.settings = QSettings()
        
        # Initialize
        self._setup_standard_panels()
        self._setup_connections()
        logger.info("PanelManager initialized")
    
    def _setup_standard_panels(self) -> None:
        """Setup standard application panels."""
        standard_panels = {
            'project_explorer': PanelConfig(
                panel_id='project_explorer',
                title='Project Explorer',
                default_area=Qt.DockWidgetArea.LeftDockWidgetArea,
                default_visible=True,
                icon_path=":/icons/folder.svg"
            ),
            'properties': PanelConfig(
                panel_id='properties',
                title='Properties',
                default_area=Qt.DockWidgetArea.RightDockWidgetArea,
                default_visible=True,
                icon_path=":/icons/properties.svg"
            ),
            'console': PanelConfig(
                panel_id='console',
                title='Console',
                default_area=Qt.DockWidgetArea.BottomDockWidgetArea,
                default_visible=False,
                icon_path=":/icons/console.svg"
            ),
            'log_viewer': PanelConfig(
                panel_id='log_viewer',
                title='Log Viewer',
                default_area=Qt.DockWidgetArea.BottomDockWidgetArea,
                default_visible=False,
                icon_path=":/icons/log.svg"
            )
        }
        
        for panel_id, config in standard_panels.items():
            self.register_panel(config)
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        # Event bus connections
        self.event_bus.subscribe("ui.panel.show", self._on_show_panel_event)
        self.event_bus.subscribe("ui.panel.hide", self._on_hide_panel_event)
        self.event_bus.subscribe("ui.panel.toggle", self._on_toggle_panel_event)
    
    def register_panel(self, panel_config: PanelConfig) -> None:
        """Register a panel configuration."""
        self.panel_configs[panel_config.panel_id] = panel_config
        self.panel_states[panel_config.panel_id] = (
            PanelState.VISIBLE if panel_config.default_visible else PanelState.HIDDEN
        )
        
        self.panel_registered.emit(panel_config.panel_id)
        logger.debug(f"Registered panel: {panel_config.panel_id}")
    
    def create_panel(self, panel_id: str) -> Optional[DockWidget]:
        """Create a panel widget if not already created."""
        if panel_id in self.panel_widgets:
            return self.panel_widgets[panel_id]
        
        if panel_id not in self.panel_configs:
            logger.error(f"Panel config not found: {panel_id}")
            return None
        
        config = self.panel_configs[panel_id]
        
        # Create dock widget
        dock_widget = DockWidget(config, self.main_window)
        
        # Create panel content
        if config.widget_factory:
            content_widget = config.widget_factory()
        else:
            content_widget = self._create_default_panel_content(panel_id)
        
        dock_widget.setWidget(content_widget)
        
        # Connect signals
        dock_widget.panel_state_changed.connect(self._on_panel_state_changed)
        dock_widget.panel_geometry_changed.connect(self._on_panel_geometry_changed)
        
        # Add to main window
        self.main_window.addDockWidget(config.default_area, dock_widget)
        
        # Store reference
        self.panel_widgets[panel_id] = dock_widget
        
        # Set initial visibility
        dock_widget.setVisible(config.default_visible)
        
        self.panel_created.emit(panel_id)
        logger.debug(f"Created panel: {panel_id}")
        
        return dock_widget
    
    def _create_default_panel_content(self, panel_id: str) -> QWidget:
        """Create default panel content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel(f"Panel: {panel_id}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        return widget
    
    def show_panel(self, panel_id: str, visible: bool = True) -> bool:
        """Show or hide a panel."""
        if panel_id not in self.panel_configs:
            logger.error(f"Panel not registered: {panel_id}")
            return False
        
        # Create panel if needed
        dock_widget = self.create_panel(panel_id)
        if not dock_widget:
            return False
        
        # Set visibility
        dock_widget.setVisible(visible)
        
        # Update state
        self.panel_states[panel_id] = PanelState.VISIBLE if visible else PanelState.HIDDEN
        
        # Emit event
        self.event_bus.emit("ui.panel.visibility_changed", {
            "panel_id": panel_id,
            "visible": visible
        })
        
        return True
    
    def hide_panel(self, panel_id: str) -> bool:
        """Hide a panel."""
        return self.show_panel(panel_id, False)
    
    def toggle_panel(self, panel_id: str) -> bool:
        """Toggle panel visibility."""
        if panel_id not in self.panel_widgets:
            return self.show_panel(panel_id, True)
        
        dock_widget = self.panel_widgets[panel_id]
        return self.show_panel(panel_id, not dock_widget.isVisible())
    
    def is_panel_visible(self, panel_id: str) -> bool:
        """Check if panel is visible."""
        if panel_id not in self.panel_widgets:
            return False
        return self.panel_widgets[panel_id].isVisible()
    
    def get_panel_widget(self, panel_id: str) -> Optional[QWidget]:
        """Get the content widget of a panel."""
        if panel_id not in self.panel_widgets:
            return None
        return self.panel_widgets[panel_id].widget()
    
    def save_panel_state(self) -> Dict[str, Any]:
        """Save current panel state to dictionary."""
        state = {
            'panels': {},
            'window_geometry': self.main_window.geometry().getRect(),
            'window_state': self.main_window.saveState().data().hex()
        }
        
        for panel_id, dock_widget in self.panel_widgets.items():
            panel_state = {
                'visible': dock_widget.isVisible(),
                'floating': dock_widget.isFloating(),
                'area': int(self.main_window.dockWidgetArea(dock_widget)),
                'geometry': dock_widget.geometry().getRect() if dock_widget.isFloating() else None
            }
            
            # Get panel-specific state if widget supports it
            content_widget = dock_widget.widget()
            if isinstance(content_widget, BasePanelWidget):
                panel_state['content_state'] = content_widget.save_state()
            
            state['panels'][panel_id] = panel_state
        
        return state
    
    def restore_panel_state(self, state: Dict[str, Any]) -> bool:
        """Restore panel state from dictionary."""
        try:
            # Restore window geometry
            if 'window_geometry' in state:
                x, y, w, h = state['window_geometry']
                self.main_window.setGeometry(x, y, w, h)
            
            # Restore window state (dock layout)
            if 'window_state' in state:
                window_state = bytes.fromhex(state['window_state'])
                self.main_window.restoreState(window_state)
            
            # Restore individual panels
            for panel_id, panel_state in state.get('panels', {}).items():
                self._restore_individual_panel_state(panel_id, panel_state)
            
            logger.info("Panel state restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore panel state: {e}")
            return False
    
    def _restore_individual_panel_state(self, panel_id: str, panel_state: Dict[str, Any]) -> None:
        """Restore state for an individual panel."""
        # Create panel if it doesn't exist
        dock_widget = self.create_panel(panel_id)
        if not dock_widget:
            return
        
        # Restore visibility
        dock_widget.setVisible(panel_state.get('visible', True))
        
        # Restore floating geometry
        if panel_state.get('floating', False) and panel_state.get('geometry'):
            x, y, w, h = panel_state['geometry']
            dock_widget.setFloating(True)
            dock_widget.setGeometry(x, y, w, h)
        
        # Restore content state
        if 'content_state' in panel_state:
            content_widget = dock_widget.widget()
            if isinstance(content_widget, BasePanelWidget):
                content_widget.restore_state(panel_state['content_state'])
    
    def save_layout(self, name: str, description: str = "") -> bool:
        """Save current panel layout with a name."""
        try:
            layout = PanelLayout(
                name=name,
                description=description,
                panel_states=self.save_panel_state(),
                window_geometry=self.main_window.geometry(),
                created_at=str(QTimer().currentTime())
            )
            
            self.panel_layouts[name] = layout
            
            # Persist to settings
            self.settings.beginGroup("PanelLayouts")
            self.settings.setValue(f"{name}/description", description)
            self.settings.setValue(f"{name}/panel_states", layout.panel_states)
            self.settings.setValue(f"{name}/window_geometry", layout.window_geometry)
            self.settings.setValue(f"{name}/created_at", layout.created_at)
            self.settings.endGroup()
            
            self.layout_saved.emit(name)
            logger.info(f"Saved panel layout: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout {name}: {e}")
            return False
    
    def restore_layout(self, name: str) -> bool:
        """Restore a saved panel layout."""
        if name not in self.panel_layouts:
            # Try to load from settings
            if not self._load_layout_from_settings(name):
                logger.error(f"Layout not found: {name}")
                return False
        
        layout = self.panel_layouts[name]
        success = self.restore_panel_state(layout.panel_states)
        
        if success:
            self.layout_restored.emit(name)
            logger.info(f"Restored panel layout: {name}")
        
        return success
    
    def _load_layout_from_settings(self, name: str) -> bool:
        """Load layout from QSettings."""
        try:
            self.settings.beginGroup("PanelLayouts")
            
            if not self.settings.contains(f"{name}/panel_states"):
                self.settings.endGroup()
                return False
            
            description = self.settings.value(f"{name}/description", "")
            panel_states = self.settings.value(f"{name}/panel_states", {})
            window_geometry = self.settings.value(f"{name}/window_geometry")
            created_at = self.settings.value(f"{name}/created_at", "")
            
            self.settings.endGroup()
            
            layout = PanelLayout(
                name=name,
                description=description,
                panel_states=panel_states,
                window_geometry=window_geometry,
                created_at=created_at
            )
            
            self.panel_layouts[name] = layout
            return True
            
        except Exception as e:
            logger.error(f"Failed to load layout {name} from settings: {e}")
            self.settings.endGroup()
            return False
    
    def get_available_layouts(self) -> List[str]:
        """Get list of available layout names."""
        # Load from settings if needed
        self.settings.beginGroup("PanelLayouts")
        layout_names = []
        
        for group in self.settings.childGroups():
            if group not in self.panel_layouts:
                self._load_layout_from_settings(group)
            layout_names.append(group)
        
        self.settings.endGroup()
        
        return sorted(set(layout_names + list(self.panel_layouts.keys())))
    
    def delete_layout(self, name: str) -> bool:
        """Delete a saved layout."""
        try:
            # Remove from memory
            if name in self.panel_layouts:
                del self.panel_layouts[name]
            
            # Remove from settings
            self.settings.beginGroup("PanelLayouts")
            self.settings.remove(name)
            self.settings.endGroup()
            
            logger.info(f"Deleted panel layout: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete layout {name}: {e}")
            return False
    
    def get_panel_list(self) -> List[str]:
        """Get list of all registered panels."""
        return list(self.panel_configs.keys())
    
    def get_visible_panels(self) -> List[str]:
        """Get list of currently visible panels."""
        visible = []
        for panel_id, dock_widget in self.panel_widgets.items():
            if dock_widget.isVisible():
                visible.append(panel_id)
        return visible
    
    # Event handlers
    def _on_show_panel_event(self, data: Dict[str, Any]) -> None:
        """Handle show panel event."""
        panel_id = data.get('panel_id')
        if panel_id:
            self.show_panel(panel_id)
    
    def _on_hide_panel_event(self, data: Dict[str, Any]) -> None:
        """Handle hide panel event."""
        panel_id = data.get('panel_id')
        if panel_id:
            self.hide_panel(panel_id)
    
    def _on_toggle_panel_event(self, data: Dict[str, Any]) -> None:
        """Handle toggle panel event."""
        panel_id = data.get('panel_id')
        if panel_id:
            self.toggle_panel(panel_id)
    
    def _on_panel_state_changed(self, panel_id: str, state: str) -> None:
        """Handle panel state changes."""
        try:
            self.panel_states[panel_id] = PanelState(state)
            self.panel_state_changed.emit(panel_id, state)
        except ValueError:
            logger.warning(f"Invalid panel state: {state}")
    
    def _on_panel_geometry_changed(self, panel_id: str, geometry: QRect) -> None:
        """Handle panel geometry changes."""
        self.panel_geometries[panel_id] = geometry
        logger.debug(f"Panel {panel_id} geometry changed: {geometry}")