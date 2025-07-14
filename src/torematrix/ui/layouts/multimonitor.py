"""Multi-monitor layout support for ToreMatrix V3.

Provides comprehensive multi-monitor layout management including display detection,
cross-monitor layouts, DPI scaling, and monitor configuration changes.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timezone
import json

from PyQt6.QtWidgets import (
    QWidget, QApplication, QSplitter, QMainWindow,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QSpinBox,
    QFormLayout, QGroupBox, QTabWidget
)
from PyQt6.QtCore import (
    QObject, pyqtSignal, QTimer, QRect, QPoint, QSize,
    QSettings, Qt
)
from PyQt6.QtGui import QScreen, QResizeEvent, QMoveEvent

from ..base import BaseUIComponent
from ...core.events import EventBus
from ...core.config import ConfigurationManager  
from ...core.state import Store
from .serialization import DisplayGeometry, LayoutSerializer, LayoutDeserializer
from .persistence import LayoutPersistence

logger = logging.getLogger(__name__)


class MonitorError(Exception):
    """Raised when multi-monitor operations fail."""
    pass


class DisplayRole(Enum):
    """Display role in multi-monitor setup."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXTENDED = "extended"
    MIRROR = "mirror"
    AUXILIARY = "auxiliary"


class LayoutSpanMode(Enum):
    """How layouts span across monitors."""
    SINGLE_MONITOR = "single"          # Layout confined to one monitor
    SPAN_HORIZONTAL = "span_horizontal" # Layout spans horizontally
    SPAN_VERTICAL = "span_vertical"     # Layout spans vertically
    SPAN_ALL = "span_all"              # Layout uses all available space
    CUSTOM_SPAN = "custom"             # Custom spanning configuration


@dataclass
class DisplayInfo:
    """Comprehensive display information."""
    screen_name: str
    geometry: QRect
    available_geometry: QRect
    logical_dpi: float
    physical_dpi: float
    device_pixel_ratio: float
    is_primary: bool
    orientation: int
    refresh_rate: float = 60.0
    color_depth: int = 32
    
    # Multi-monitor properties
    role: DisplayRole = DisplayRole.SECONDARY
    layout_priority: int = 0
    preferred_layouts: List[str] = field(default_factory=list)
    
    # Scaling and adaptation
    scale_factor: float = 1.0
    text_scale_factor: float = 1.0
    ui_scale_factor: float = 1.0
    
    # Position in multi-monitor array
    monitor_index: int = 0
    relative_position: str = ""  # "left", "right", "above", "below"


@dataclass
class MonitorConfiguration:
    """Multi-monitor configuration."""
    config_id: str
    name: str
    description: str
    displays: List[DisplayInfo]
    primary_display: str
    layout_span_mode: LayoutSpanMode
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auto_apply: bool = True
    
    # Layout assignments per display
    display_layouts: Dict[str, str] = field(default_factory=dict)
    
    # Cross-monitor layout rules
    span_rules: Dict[str, Any] = field(default_factory=dict)


class DisplayManager:
    """Manages display detection and information."""
    
    def __init__(self):
        self._displays: Dict[str, DisplayInfo] = {}
        self._primary_display: Optional[str] = None
        self._last_config_hash: Optional[str] = None
        
        self._update_display_info()
    
    def get_displays(self) -> Dict[str, DisplayInfo]:
        """Get current display information."""
        return self._displays.copy()
    
    def get_primary_display(self) -> Optional[DisplayInfo]:
        """Get primary display information."""
        if self._primary_display:
            return self._displays.get(self._primary_display)
        return None
    
    def get_display_by_name(self, name: str) -> Optional[DisplayInfo]:
        """Get display by name."""
        return self._displays.get(name)
    
    def detect_configuration_change(self) -> bool:
        """Detect if monitor configuration has changed."""
        current_hash = self._get_configuration_hash()
        changed = current_hash != self._last_config_hash
        self._last_config_hash = current_hash
        return changed
    
    def update_display_info(self) -> bool:
        """Update display information and return if changed."""
        old_displays = self._displays.copy()
        self._update_display_info()
        return old_displays != self._displays
    
    def get_display_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current display configuration."""
        return {
            "display_count": len(self._displays),
            "primary_display": self._primary_display,
            "total_width": sum(d.geometry.width() for d in self._displays.values()),
            "total_height": max(d.geometry.height() for d in self._displays.values()),
            "dpi_range": (
                min(d.logical_dpi for d in self._displays.values()),
                max(d.logical_dpi for d in self._displays.values())
            ),
            "scale_factors": [d.device_pixel_ratio for d in self._displays.values()],
            "configuration_hash": self._get_configuration_hash()
        }
    
    def _update_display_info(self) -> None:
        """Update display information from Qt."""
        self._displays.clear()
        
        app = QApplication.instance()
        if not app:
            return
        
        screens = app.screens()
        primary_screen = app.primaryScreen()
        
        for i, screen in enumerate(screens):
            if not screen:
                continue
            
            screen_name = screen.name() or f"Display_{i}"
            is_primary = screen == primary_screen
            
            if is_primary:
                self._primary_display = screen_name
            
            # Get screen geometry and properties
            geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            logical_dpi = screen.logicalDotsPerInch()
            physical_dpi = screen.physicalDotsPerInch()
            device_pixel_ratio = screen.devicePixelRatio()
            
            # Detect relative position
            relative_position = self._determine_relative_position(screen, screens)
            
            display_info = DisplayInfo(
                screen_name=screen_name,
                geometry=geometry,
                available_geometry=available_geometry,
                logical_dpi=logical_dpi,
                physical_dpi=physical_dpi,
                device_pixel_ratio=device_pixel_ratio,
                is_primary=is_primary,
                orientation=screen.orientation(),
                refresh_rate=getattr(screen, 'refreshRate', lambda: 60.0)(),
                role=DisplayRole.PRIMARY if is_primary else DisplayRole.SECONDARY,
                monitor_index=i,
                relative_position=relative_position,
                scale_factor=device_pixel_ratio,
                text_scale_factor=self._calculate_text_scale_factor(logical_dpi),
                ui_scale_factor=self._calculate_ui_scale_factor(device_pixel_ratio, logical_dpi)
            )
            
            self._displays[screen_name] = display_info
    
    def _determine_relative_position(self, screen: QScreen, all_screens: List[QScreen]) -> str:
        """Determine relative position of screen to others."""
        if len(all_screens) <= 1:
            return "single"
        
        screen_rect = screen.geometry()
        positions = []
        
        for other_screen in all_screens:
            if other_screen == screen:
                continue
            
            other_rect = other_screen.geometry()
            
            # Check relative positions
            if screen_rect.x() < other_rect.x():
                positions.append("left_of")
            elif screen_rect.x() > other_rect.x():
                positions.append("right_of")
            
            if screen_rect.y() < other_rect.y():
                positions.append("above")
            elif screen_rect.y() > other_rect.y():
                positions.append("below")
        
        return ",".join(set(positions)) if positions else "overlapping"
    
    def _calculate_text_scale_factor(self, dpi: float) -> float:
        """Calculate text scaling factor based on DPI."""
        standard_dpi = 96.0
        return dpi / standard_dpi
    
    def _calculate_ui_scale_factor(self, device_ratio: float, logical_dpi: float) -> float:
        """Calculate UI scaling factor."""
        # Combine device pixel ratio with DPI scaling
        dpi_scale = logical_dpi / 96.0
        return device_ratio * min(dpi_scale, 2.0)  # Cap at 2x for usability
    
    def _get_configuration_hash(self) -> str:
        """Get hash of current configuration for change detection."""
        config_data = []
        for display in self._displays.values():
            config_data.append(f"{display.screen_name}:{display.geometry.width()}x{display.geometry.height()}")
        
        import hashlib
        return hashlib.md5("|".join(sorted(config_data)).encode()).hexdigest()


class MultiMonitorLayoutManager:
    """Manages layouts across multiple monitors."""
    
    def __init__(
        self,
        display_manager: DisplayManager,
        persistence: LayoutPersistence
    ):
        self._display_manager = display_manager
        self._persistence = persistence
        self._monitor_configs: Dict[str, MonitorConfiguration] = {}
        self._active_config: Optional[str] = None
        
        # Layout state tracking
        self._monitor_layouts: Dict[str, str] = {}  # display_name -> layout_name
        self._spanning_layouts: Dict[str, LayoutSpanMode] = {}
        
        self._load_monitor_configurations()
    
    def create_monitor_configuration(
        self,
        config_id: str,
        name: str,
        description: str,
        span_mode: LayoutSpanMode = LayoutSpanMode.SINGLE_MONITOR
    ) -> MonitorConfiguration:
        """Create a new monitor configuration."""
        if config_id in self._monitor_configs:
            raise MonitorError(f"Monitor configuration '{config_id}' already exists")
        
        displays = list(self._display_manager.get_displays().values())
        primary_display = self._display_manager.get_primary_display()
        
        config = MonitorConfiguration(
            config_id=config_id,
            name=name,
            description=description,
            displays=displays,
            primary_display=primary_display.screen_name if primary_display else "",
            layout_span_mode=span_mode
        )
        
        self._monitor_configs[config_id] = config
        self._save_monitor_configurations()
        
        logger.info(f"Created monitor configuration '{config_id}'")
        return config
    
    def assign_layout_to_display(
        self,
        config_id: str,
        display_name: str,
        layout_name: str
    ) -> bool:
        """Assign a layout to a specific display in a configuration."""
        config = self._monitor_configs.get(config_id)
        if not config:
            return False
        
        config.display_layouts[display_name] = layout_name
        self._save_monitor_configurations()
        
        logger.info(f"Assigned layout '{layout_name}' to display '{display_name}' in config '{config_id}'")
        return True
    
    def apply_monitor_configuration(self, config_id: str) -> bool:
        """Apply a monitor configuration."""
        config = self._monitor_configs.get(config_id)
        if not config:
            logger.error(f"Monitor configuration '{config_id}' not found")
            return False
        
        try:
            # Apply layouts to each display
            for display_name, layout_name in config.display_layouts.items():
                display = self._display_manager.get_display_by_name(display_name)
                if display and self._persistence.layout_exists(layout_name):
                    self._apply_layout_to_display(layout_name, display)
            
            # Update active configuration
            self._active_config = config_id
            config.last_used = datetime.now(timezone.utc)
            self._save_monitor_configurations()
            
            logger.info(f"Applied monitor configuration '{config_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply monitor configuration '{config_id}': {e}")
            return False
    
    def create_spanning_layout(
        self,
        layout_name: str,
        root_widget: QWidget,
        span_mode: LayoutSpanMode,
        display_assignments: Optional[Dict[str, List[str]]] = None
    ) -> bool:
        """Create a layout that spans across multiple monitors."""
        try:
            displays = self._display_manager.get_displays()
            
            if span_mode == LayoutSpanMode.SPAN_ALL:
                # Calculate total spanning geometry
                total_geometry = self._calculate_spanning_geometry(list(displays.values()))
                root_widget.setGeometry(total_geometry)
                
            elif span_mode == LayoutSpanMode.SPAN_HORIZONTAL:
                # Arrange horizontally across monitors
                self._arrange_horizontal_spanning(root_widget, displays)
                
            elif span_mode == LayoutSpanMode.SPAN_VERTICAL:
                # Arrange vertically across monitors
                self._arrange_vertical_spanning(root_widget, displays)
                
            elif span_mode == LayoutSpanMode.CUSTOM_SPAN and display_assignments:
                # Custom spanning based on assignments
                self._apply_custom_spanning(root_widget, displays, display_assignments)
            
            # Save the spanning layout
            self._persistence.save_layout(
                layout_name,
                root_widget,
                description=f"Multi-monitor spanning layout ({span_mode.value})"
            )
            
            # Track spanning layout
            self._spanning_layouts[layout_name] = span_mode
            
            logger.info(f"Created spanning layout '{layout_name}' with mode {span_mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create spanning layout: {e}")
            return False
    
    def adapt_layout_for_display(
        self,
        layout_name: str,
        target_display: DisplayInfo,
        source_display: Optional[DisplayInfo] = None
    ) -> bool:
        """Adapt a layout for a different display with DPI/scaling considerations."""
        try:
            # Load the original layout
            layout_widget = self._persistence.load_layout(layout_name)
            
            # Calculate scaling factors
            if source_display:
                scale_factor = target_display.ui_scale_factor / source_display.ui_scale_factor
                dpi_factor = target_display.logical_dpi / source_display.logical_dpi
            else:
                # Assume standard baseline
                scale_factor = target_display.ui_scale_factor
                dpi_factor = target_display.logical_dpi / 96.0
            
            # Apply scaling to layout
            self._apply_display_scaling(layout_widget, scale_factor, dpi_factor)
            
            # Position on target display
            target_rect = target_display.available_geometry
            layout_widget.move(target_rect.topLeft())
            
            # Ensure layout fits within display
            self._constrain_to_display(layout_widget, target_display)
            
            # Save adapted layout
            adapted_name = f"{layout_name}_adapted_{target_display.screen_name}"
            self._persistence.save_layout(
                adapted_name,
                layout_widget,
                description=f"Layout adapted for {target_display.screen_name}"
            )
            
            logger.info(f"Adapted layout '{layout_name}' for display '{target_display.screen_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to adapt layout for display: {e}")
            return False
    
    def handle_display_change(self) -> None:
        """Handle display configuration changes."""
        if not self._display_manager.detect_configuration_change():
            return
        
        logger.info("Display configuration change detected")
        
        # Update display info
        self._display_manager.update_display_info()
        
        # Reapply active configuration if available
        if self._active_config:
            self.apply_monitor_configuration(self._active_config)
        
        # Adapt existing spanning layouts
        for layout_name, span_mode in self._spanning_layouts.items():
            self._readapt_spanning_layout(layout_name, span_mode)
    
    def get_monitor_configurations(self) -> List[MonitorConfiguration]:
        """Get all monitor configurations."""
        return list(self._monitor_configs.values())
    
    def get_active_configuration(self) -> Optional[MonitorConfiguration]:
        """Get currently active monitor configuration."""
        if self._active_config:
            return self._monitor_configs.get(self._active_config)
        return None
    
    def delete_monitor_configuration(self, config_id: str) -> bool:
        """Delete a monitor configuration."""
        if config_id in self._monitor_configs:
            del self._monitor_configs[config_id]
            
            if self._active_config == config_id:
                self._active_config = None
            
            self._save_monitor_configurations()
            logger.info(f"Deleted monitor configuration '{config_id}'")
            return True
        
        return False
    
    # Private methods
    
    def _apply_layout_to_display(self, layout_name: str, display: DisplayInfo) -> None:
        """Apply a layout to a specific display."""
        layout_widget = self._persistence.load_layout(layout_name)
        
        # Position on the display
        display_rect = display.available_geometry
        layout_widget.move(display_rect.topLeft())
        
        # Scale if needed
        if display.ui_scale_factor != 1.0:
            self._apply_display_scaling(layout_widget, display.ui_scale_factor, display.text_scale_factor)
        
        # Ensure it fits
        self._constrain_to_display(layout_widget, display)
        
        # Track assignment
        self._monitor_layouts[display.screen_name] = layout_name
    
    def _calculate_spanning_geometry(self, displays: List[DisplayInfo]) -> QRect:
        """Calculate geometry that spans all displays."""
        if not displays:
            return QRect()
        
        min_x = min(d.geometry.x() for d in displays)
        min_y = min(d.geometry.y() for d in displays)
        max_x = max(d.geometry.x() + d.geometry.width() for d in displays)
        max_y = max(d.geometry.y() + d.geometry.height() for d in displays)
        
        return QRect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _arrange_horizontal_spanning(self, widget: QWidget, displays: Dict[str, DisplayInfo]) -> None:
        """Arrange widget to span horizontally across displays."""
        display_list = sorted(displays.values(), key=lambda d: d.geometry.x())
        
        if len(display_list) > 1:
            left_display = display_list[0]
            right_display = display_list[-1]
            
            start_x = left_display.geometry.x()
            end_x = right_display.geometry.x() + right_display.geometry.width()
            
            # Use height of primary display or first display
            primary = next((d for d in display_list if d.is_primary), display_list[0])
            height = primary.geometry.height()
            y = primary.geometry.y()
            
            widget.setGeometry(start_x, y, end_x - start_x, height)
    
    def _arrange_vertical_spanning(self, widget: QWidget, displays: Dict[str, DisplayInfo]) -> None:
        """Arrange widget to span vertically across displays."""
        display_list = sorted(displays.values(), key=lambda d: d.geometry.y())
        
        if len(display_list) > 1:
            top_display = display_list[0]
            bottom_display = display_list[-1]
            
            start_y = top_display.geometry.y()
            end_y = bottom_display.geometry.y() + bottom_display.geometry.height()
            
            # Use width of primary display or first display
            primary = next((d for d in display_list if d.is_primary), display_list[0])
            width = primary.geometry.width()
            x = primary.geometry.x()
            
            widget.setGeometry(x, start_y, width, end_y - start_y)
    
    def _apply_custom_spanning(
        self,
        widget: QWidget,
        displays: Dict[str, DisplayInfo],
        assignments: Dict[str, List[str]]
    ) -> None:
        """Apply custom spanning configuration."""
        # This would implement custom spanning logic based on assignments
        # For now, fall back to spanning all
        total_geometry = self._calculate_spanning_geometry(list(displays.values()))
        widget.setGeometry(total_geometry)
    
    def _apply_display_scaling(
        self,
        widget: QWidget,
        scale_factor: float,
        text_scale_factor: float
    ) -> None:
        """Apply scaling to widget for different display characteristics."""
        # Scale the widget size
        current_size = widget.size()
        new_size = QSize(
            int(current_size.width() * scale_factor),
            int(current_size.height() * scale_factor)
        )
        widget.resize(new_size)
        
        # Scale fonts if significant text scaling is needed
        if abs(text_scale_factor - 1.0) > 0.1:
            self._apply_font_scaling(widget, text_scale_factor)
    
    def _apply_font_scaling(self, widget: QWidget, scale_factor: float) -> None:
        """Apply font scaling to widget and children."""
        font = widget.font()
        current_size = font.pointSizeF()
        if current_size > 0:
            new_size = current_size * scale_factor
            font.setPointSizeF(new_size)
            widget.setFont(font)
        
        # Apply to children recursively
        for child in widget.findChildren(QWidget):
            child_font = child.font()
            child_size = child_font.pointSizeF()
            if child_size > 0:
                child_font.setPointSizeF(child_size * scale_factor)
                child.setFont(child_font)
    
    def _constrain_to_display(self, widget: QWidget, display: DisplayInfo) -> None:
        """Ensure widget fits within display bounds."""
        display_rect = display.available_geometry
        widget_rect = widget.geometry()
        
        # Adjust position if outside display
        new_x = max(display_rect.x(), min(widget_rect.x(), 
                                         display_rect.x() + display_rect.width() - widget_rect.width()))
        new_y = max(display_rect.y(), min(widget_rect.y(), 
                                         display_rect.y() + display_rect.height() - widget_rect.height()))
        
        # Adjust size if too large
        max_width = display_rect.width()
        max_height = display_rect.height()
        
        new_width = min(widget_rect.width(), max_width)
        new_height = min(widget_rect.height(), max_height)
        
        widget.setGeometry(new_x, new_y, new_width, new_height)
    
    def _readapt_spanning_layout(self, layout_name: str, span_mode: LayoutSpanMode) -> None:
        """Re-adapt a spanning layout after display changes."""
        try:
            layout_widget = self._persistence.load_layout(layout_name)
            displays = self._display_manager.get_displays()
            
            if span_mode == LayoutSpanMode.SPAN_ALL:
                total_geometry = self._calculate_spanning_geometry(list(displays.values()))
                layout_widget.setGeometry(total_geometry)
            elif span_mode == LayoutSpanMode.SPAN_HORIZONTAL:
                self._arrange_horizontal_spanning(layout_widget, displays)
            elif span_mode == LayoutSpanMode.SPAN_VERTICAL:
                self._arrange_vertical_spanning(layout_widget, displays)
            
            # Save the re-adapted layout
            self._persistence.save_layout(
                layout_name,
                layout_widget,
                description=f"Re-adapted spanning layout ({span_mode.value})",
                overwrite=True
            )
            
        except Exception as e:
            logger.warning(f"Failed to re-adapt spanning layout '{layout_name}': {e}")
    
    def _load_monitor_configurations(self) -> None:
        """Load monitor configurations from storage."""
        # This would load from persistent storage
        # For now, create a default configuration
        try:
            displays = list(self._display_manager.get_displays().values())
            if displays:
                primary = self._display_manager.get_primary_display()
                
                default_config = MonitorConfiguration(
                    config_id="default",
                    name="Default Configuration",
                    description="Automatically created default configuration",
                    displays=displays,
                    primary_display=primary.screen_name if primary else "",
                    layout_span_mode=LayoutSpanMode.SINGLE_MONITOR
                )
                
                self._monitor_configs["default"] = default_config
                logger.info("Created default monitor configuration")
                
        except Exception as e:
            logger.warning(f"Failed to create default monitor configuration: {e}")
    
    def _save_monitor_configurations(self) -> None:
        """Save monitor configurations to storage."""
        # This would save to persistent storage
        # Implementation would depend on storage backend
        logger.debug("Monitor configurations saved")


class MultiMonitorManager(BaseUIComponent):
    """Main manager for multi-monitor layout functionality."""
    
    # Signals
    display_configuration_changed = pyqtSignal()
    layout_adapted = pyqtSignal(str, str)  # layout_name, display_name
    spanning_layout_created = pyqtSignal(str, str)  # layout_name, span_mode
    monitor_config_applied = pyqtSignal(str)  # config_id
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        persistence: LayoutPersistence,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._persistence = persistence
        self._display_manager = DisplayManager()
        self._layout_manager = MultiMonitorLayoutManager(self._display_manager, persistence)
        
        # Change detection timer
        self._change_timer = QTimer(self)
        self._change_timer.timeout.connect(self._check_display_changes)
        self._change_timer.start(5000)  # Check every 5 seconds
    
    def _setup_component(self) -> None:
        """Setup the multi-monitor manager."""
        # Subscribe to events
        self.subscribe_event("application.window_moved", self._on_window_moved)
        self.subscribe_event("application.window_resized", self._on_window_resized)
        
        logger.info("Multi-monitor manager initialized")
    
    def get_display_info(self) -> Dict[str, DisplayInfo]:
        """Get current display information."""
        return self._display_manager.get_displays()
    
    def get_display_summary(self) -> Dict[str, Any]:
        """Get display configuration summary."""
        return self._display_manager.get_display_configuration_summary()
    
    def create_spanning_layout(
        self,
        layout_name: str,
        root_widget: QWidget,
        span_mode: LayoutSpanMode = LayoutSpanMode.SPAN_ALL
    ) -> bool:
        """Create a layout that spans multiple monitors."""
        success = self._layout_manager.create_spanning_layout(layout_name, root_widget, span_mode)
        
        if success:
            self.spanning_layout_created.emit(layout_name, span_mode.value)
            self.publish_event("layout.spanning_created", {
                "layout_name": layout_name,
                "span_mode": span_mode.value,
                "display_count": len(self._display_manager.get_displays())
            })
        
        return success
    
    def adapt_layout_for_display(
        self,
        layout_name: str,
        target_display_name: str,
        source_display_name: Optional[str] = None
    ) -> bool:
        """Adapt a layout for a specific display."""
        displays = self._display_manager.get_displays()
        
        target_display = displays.get(target_display_name)
        if not target_display:
            logger.error(f"Target display '{target_display_name}' not found")
            return False
        
        source_display = None
        if source_display_name:
            source_display = displays.get(source_display_name)
        
        success = self._layout_manager.adapt_layout_for_display(
            layout_name, target_display, source_display
        )
        
        if success:
            self.layout_adapted.emit(layout_name, target_display_name)
            self.publish_event("layout.adapted", {
                "layout_name": layout_name,
                "target_display": target_display_name,
                "source_display": source_display_name
            })
        
        return success
    
    def create_monitor_configuration(
        self,
        config_id: str,
        name: str,
        description: str,
        span_mode: LayoutSpanMode = LayoutSpanMode.SINGLE_MONITOR
    ) -> bool:
        """Create a new monitor configuration."""
        try:
            self._layout_manager.create_monitor_configuration(config_id, name, description, span_mode)
            return True
        except MonitorError as e:
            logger.error(f"Failed to create monitor configuration: {e}")
            return False
    
    def apply_monitor_configuration(self, config_id: str) -> bool:
        """Apply a monitor configuration."""
        success = self._layout_manager.apply_monitor_configuration(config_id)
        
        if success:
            self.monitor_config_applied.emit(config_id)
            self.publish_event("monitor.config_applied", {
                "config_id": config_id
            })
        
        return success
    
    def assign_layout_to_display(
        self,
        config_id: str,
        display_name: str,
        layout_name: str
    ) -> bool:
        """Assign a layout to a display in a configuration."""
        return self._layout_manager.assign_layout_to_display(config_id, display_name, layout_name)
    
    def get_monitor_configurations(self) -> List[MonitorConfiguration]:
        """Get all monitor configurations."""
        return self._layout_manager.get_monitor_configurations()
    
    def get_active_configuration(self) -> Optional[MonitorConfiguration]:
        """Get currently active monitor configuration."""
        return self._layout_manager.get_active_configuration()
    
    def enable_display_change_detection(self, enabled: bool) -> None:
        """Enable or disable automatic display change detection."""
        if enabled:
            self._change_timer.start(5000)
        else:
            self._change_timer.stop()
    
    def force_display_refresh(self) -> None:
        """Force refresh of display information."""
        self._display_manager.update_display_info()
        self._layout_manager.handle_display_change()
        self.display_configuration_changed.emit()
    
    def _check_display_changes(self) -> None:
        """Check for display configuration changes."""
        if self._display_manager.update_display_info():
            self._layout_manager.handle_display_change()
            self.display_configuration_changed.emit()
            
            self.publish_event("display.configuration_changed", {
                "display_count": len(self._display_manager.get_displays()),
                "summary": self._display_manager.get_display_configuration_summary()
            })
    
    def _on_window_moved(self, event_data: Dict[str, Any]) -> None:
        """Handle window move events."""
        # Could trigger layout adaptation based on which display the window moved to
        pass
    
    def _on_window_resized(self, event_data: Dict[str, Any]) -> None:
        """Handle window resize events."""
        # Could trigger layout scaling adjustments
        pass