"""
Screen Coordinate System for Document Viewer.

This module provides screen coordinate management including multi-monitor
support, DPI awareness, and window system integration.
"""

import math
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSize, QPoint
from PyQt6.QtGui import QScreen, QWindow
from PyQt6.QtWidgets import QApplication, QWidget

from .coordinates import Point, Rectangle


class ScreenType(Enum):
    """Types of screens in the system."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXTENDED = "extended"
    MIRRORED = "mirrored"


class DPIMode(Enum):
    """DPI handling modes."""
    SYSTEM = "system"        # Use system DPI settings
    AWARE = "aware"          # DPI aware scaling
    UNAWARE = "unaware"      # Ignore DPI scaling
    PER_MONITOR = "per_monitor"  # Per-monitor DPI awareness


@dataclass
class ScreenMetrics:
    """Detailed screen metrics and capabilities."""
    logical_dpi: float
    physical_dpi: float
    scale_factor: float
    pixel_density: float
    color_depth: int
    refresh_rate: float
    orientation: int = 0  # 0, 90, 180, 270 degrees
    
    def copy(self) -> 'ScreenMetrics':
        """Create a copy of screen metrics."""
        return ScreenMetrics(
            logical_dpi=self.logical_dpi,
            physical_dpi=self.physical_dpi,
            scale_factor=self.scale_factor,
            pixel_density=self.pixel_density,
            color_depth=self.color_depth,
            refresh_rate=self.refresh_rate,
            orientation=self.orientation
        )


@dataclass
class ScreenConfiguration:
    """Screen configuration and settings."""
    screen_id: str
    name: str
    screen_type: ScreenType
    geometry: Rectangle
    available_geometry: Rectangle
    metrics: ScreenMetrics
    is_enabled: bool = True
    position_in_layout: Point = field(default_factory=lambda: Point(0, 0))
    
    def copy(self) -> 'ScreenConfiguration':
        """Create a copy of screen configuration."""
        return ScreenConfiguration(
            screen_id=self.screen_id,
            name=self.name,
            screen_type=self.screen_type,
            geometry=Rectangle(self.geometry.x, self.geometry.y, 
                             self.geometry.width, self.geometry.height),
            available_geometry=Rectangle(self.available_geometry.x, self.available_geometry.y,
                                       self.available_geometry.width, self.available_geometry.height),
            metrics=self.metrics.copy(),
            is_enabled=self.is_enabled,
            position_in_layout=Point(self.position_in_layout.x, self.position_in_layout.y)
        )


class ScreenManager(QObject):
    """
    Comprehensive screen management system.
    
    Handles multi-monitor setups, DPI awareness, screen changes,
    and coordinate mapping between screens.
    """
    
    # Signals
    screen_added = pyqtSignal(object)      # ScreenConfiguration
    screen_removed = pyqtSignal(str)       # screen_id
    screen_changed = pyqtSignal(object)    # ScreenConfiguration
    primary_screen_changed = pyqtSignal(str)  # new_primary_screen_id
    dpi_changed = pyqtSignal(str, float)   # screen_id, new_dpi
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Screen tracking
        self._screens: Dict[str, ScreenConfiguration] = {}
        self._primary_screen_id: Optional[str] = None
        self._current_screen_id: Optional[str] = None
        
        # DPI settings
        self._dpi_mode = DPIMode.SYSTEM
        self._custom_dpi_scale = 1.0
        self._dpi_override: Dict[str, float] = {}
        
        # Window tracking
        self._tracked_windows: Dict[QWidget, str] = {}  # widget -> screen_id
        self._window_screen_cache: Dict[int, str] = {}  # window_id -> screen_id
        
        # Monitoring
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._check_screen_changes)
        self._monitor_interval = 1000  # 1 second
        
        # Performance tracking
        self._screen_queries = 0
        self._cache_hits = 0
        self._last_detection_time = 0.0
        
        # Initialize screen detection
        self._detect_all_screens()
        self._setup_screen_monitoring()
    
    def initialize(self) -> None:
        """Initialize screen management system."""
        self._detect_all_screens()
        self._start_monitoring()
    
    def shutdown(self) -> None:
        """Shutdown screen management system."""
        self._stop_monitoring()
        self._screens.clear()
        self._tracked_windows.clear()
        self._window_screen_cache.clear()
    
    def get_screen_count(self) -> int:
        """Get the number of available screens."""
        return len(self._screens)
    
    def get_screen_configurations(self) -> List[ScreenConfiguration]:
        """Get all screen configurations."""
        return [config.copy() for config in self._screens.values()]
    
    def get_screen_configuration(self, screen_id: str) -> Optional[ScreenConfiguration]:
        """Get configuration for specific screen."""
        config = self._screens.get(screen_id)
        return config.copy() if config else None
    
    def get_primary_screen_id(self) -> Optional[str]:
        """Get primary screen ID."""
        return self._primary_screen_id
    
    def get_primary_screen_configuration(self) -> Optional[ScreenConfiguration]:
        """Get primary screen configuration."""
        if self._primary_screen_id:
            return self.get_screen_configuration(self._primary_screen_id)
        return None
    
    def get_current_screen_id(self) -> Optional[str]:
        """Get current screen ID."""
        return self._current_screen_id
    
    def get_current_screen_configuration(self) -> Optional[ScreenConfiguration]:
        """Get current screen configuration."""
        if self._current_screen_id:
            return self.get_screen_configuration(self._current_screen_id)
        return None
    
    def set_current_screen(self, screen_id: str) -> bool:
        """Set current screen."""
        if screen_id in self._screens:
            old_screen_id = self._current_screen_id
            self._current_screen_id = screen_id
            
            if old_screen_id != screen_id:
                config = self._screens[screen_id]
                self.screen_changed.emit(config)
            
            return True
        return False
    
    def get_screen_at_point(self, point: Point) -> Optional[str]:
        """Get screen ID containing the given point."""
        for screen_id, config in self._screens.items():
            if config.geometry.contains(point):
                return screen_id
        return None
    
    def get_screen_for_widget(self, widget: QWidget) -> Optional[str]:
        """Get screen ID for the given widget."""
        # Check cache first
        widget_id = id(widget)
        if widget_id in self._window_screen_cache:
            self._cache_hits += 1
            return self._window_screen_cache[widget_id]
        
        self._screen_queries += 1
        
        # Get widget screen
        screen_id = None
        if widget.window() and widget.window().screen():
            qt_screen = widget.window().screen()
            screen_id = self._qt_screen_to_id(qt_screen)
        
        # Cache result
        if screen_id:
            self._window_screen_cache[widget_id] = screen_id
        
        return screen_id
    
    def map_point_to_screen(self, point: Point, from_screen_id: str, to_screen_id: str) -> Point:
        """Map point from one screen coordinate system to another."""
        if from_screen_id == to_screen_id:
            return Point(point.x, point.y)
        
        from_config = self._screens.get(from_screen_id)
        to_config = self._screens.get(to_screen_id)
        
        if not from_config or not to_config:
            return point
        
        # Convert to global coordinates
        global_x = point.x + from_config.geometry.x
        global_y = point.y + from_config.geometry.y
        
        # Convert to target screen coordinates
        local_x = global_x - to_config.geometry.x
        local_y = global_y - to_config.geometry.y
        
        # Apply DPI scaling if needed
        if from_config.metrics.scale_factor != to_config.metrics.scale_factor:
            scale_ratio = to_config.metrics.scale_factor / from_config.metrics.scale_factor
            local_x *= scale_ratio
            local_y *= scale_ratio
        
        return Point(local_x, local_y)
    
    def map_rectangle_to_screen(self, rect: Rectangle, from_screen_id: str, to_screen_id: str) -> Rectangle:
        """Map rectangle from one screen coordinate system to another."""
        if from_screen_id == to_screen_id:
            return Rectangle(rect.x, rect.y, rect.width, rect.height)
        
        # Map top-left and bottom-right corners
        top_left = self.map_point_to_screen(
            Point(rect.x, rect.y), from_screen_id, to_screen_id
        )
        bottom_right = self.map_point_to_screen(
            Point(rect.x + rect.width, rect.y + rect.height),
            from_screen_id, to_screen_id
        )
        
        return Rectangle(
            top_left.x, top_left.y,
            bottom_right.x - top_left.x,
            bottom_right.y - top_left.y
        )
    
    def get_effective_dpi(self, screen_id: str) -> float:
        """Get effective DPI for screen considering current mode."""
        config = self._screens.get(screen_id)
        if not config:
            return 96.0  # Default DPI
        
        base_dpi = config.metrics.logical_dpi
        
        if self._dpi_mode == DPIMode.SYSTEM:
            return base_dpi
        elif self._dpi_mode == DPIMode.AWARE:
            return base_dpi * config.metrics.scale_factor
        elif self._dpi_mode == DPIMode.UNAWARE:
            return 96.0  # Standard DPI
        elif self._dpi_mode == DPIMode.PER_MONITOR:
            # Check for override
            if screen_id in self._dpi_override:
                return self._dpi_override[screen_id]
            return base_dpi * config.metrics.scale_factor
        
        return base_dpi
    
    def get_effective_scale_factor(self, screen_id: str) -> float:
        """Get effective scale factor for screen."""
        config = self._screens.get(screen_id)
        if not config:
            return 1.0
        
        if self._dpi_mode == DPIMode.UNAWARE:
            return 1.0
        
        base_scale = config.metrics.scale_factor
        
        if self._dpi_mode == DPIMode.PER_MONITOR and screen_id in self._dpi_override:
            return self._dpi_override[screen_id] / 96.0
        
        return base_scale * self._custom_dpi_scale
    
    def set_dpi_mode(self, mode: DPIMode) -> None:
        """Set DPI handling mode."""
        if self._dpi_mode != mode:
            old_mode = self._dpi_mode
            self._dpi_mode = mode
            
            # Emit DPI change signals for all screens
            for screen_id, config in self._screens.items():
                new_dpi = self.get_effective_dpi(screen_id)
                self.dpi_changed.emit(screen_id, new_dpi)
    
    def set_custom_dpi_scale(self, scale: float) -> None:
        """Set custom DPI scale factor."""
        if scale > 0 and self._custom_dpi_scale != scale:
            self._custom_dpi_scale = scale
            
            # Emit DPI change signals
            for screen_id in self._screens:
                new_dpi = self.get_effective_dpi(screen_id)
                self.dpi_changed.emit(screen_id, new_dpi)
    
    def set_screen_dpi_override(self, screen_id: str, dpi: float) -> None:
        """Set DPI override for specific screen."""
        if screen_id in self._screens:
            self._dpi_override[screen_id] = dpi
            self.dpi_changed.emit(screen_id, dpi)
    
    def remove_screen_dpi_override(self, screen_id: str) -> None:
        """Remove DPI override for specific screen."""
        if screen_id in self._dpi_override:
            del self._dpi_override[screen_id]
            new_dpi = self.get_effective_dpi(screen_id)
            self.dpi_changed.emit(screen_id, new_dpi)
    
    def get_virtual_desktop_bounds(self) -> Rectangle:
        """Get bounds of the entire virtual desktop."""
        if not self._screens:
            return Rectangle(0, 0, 1920, 1080)  # Default
        
        min_x = min(config.geometry.x for config in self._screens.values())
        min_y = min(config.geometry.y for config in self._screens.values())
        max_x = max(config.geometry.x + config.geometry.width for config in self._screens.values())
        max_y = max(config.geometry.y + config.geometry.height for config in self._screens.values())
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def get_screen_performance_metrics(self) -> Dict[str, Any]:
        """Get screen management performance metrics."""
        cache_hit_rate = 0.0
        if self._screen_queries > 0:
            cache_hit_rate = self._cache_hits / self._screen_queries
        
        return {
            'screen_count': len(self._screens),
            'screen_queries': self._screen_queries,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': cache_hit_rate,
            'last_detection_time': self._last_detection_time,
            'monitor_interval': self._monitor_interval,
            'dpi_mode': self._dpi_mode.value,
            'custom_dpi_scale': self._custom_dpi_scale,
            'dpi_overrides': len(self._dpi_override)
        }
    
    def track_widget(self, widget: QWidget) -> None:
        """Start tracking widget for screen changes."""
        screen_id = self.get_screen_for_widget(widget)
        if screen_id:
            self._tracked_windows[widget] = screen_id
    
    def untrack_widget(self, widget: QWidget) -> None:
        """Stop tracking widget."""
        if widget in self._tracked_windows:
            del self._tracked_windows[widget]
        
        widget_id = id(widget)
        if widget_id in self._window_screen_cache:
            del self._window_screen_cache[widget_id]
    
    def _detect_all_screens(self) -> None:
        """Detect all available screens."""
        start_time = time.time()
        
        app = QApplication.instance()
        if not app:
            return
        
        new_screens: Dict[str, ScreenConfiguration] = {}
        qt_screens = app.screens()
        primary_screen = app.primaryScreen()
        
        for i, qt_screen in enumerate(qt_screens):
            screen_id = self._qt_screen_to_id(qt_screen)
            
            # Get screen geometry
            geometry = qt_screen.geometry()
            available_geometry = qt_screen.availableGeometry()
            
            # Get screen metrics
            metrics = ScreenMetrics(
                logical_dpi=qt_screen.logicalDotsPerInch(),
                physical_dpi=qt_screen.physicalDotsPerInch(),
                scale_factor=qt_screen.devicePixelRatio(),
                pixel_density=qt_screen.physicalDotsPerInch() / 25.4,  # dots per mm
                color_depth=qt_screen.depth(),
                refresh_rate=qt_screen.refreshRate()
            )
            
            # Determine screen type
            screen_type = ScreenType.PRIMARY if qt_screen == primary_screen else ScreenType.SECONDARY
            
            # Create configuration
            config = ScreenConfiguration(
                screen_id=screen_id,
                name=qt_screen.name(),
                screen_type=screen_type,
                geometry=Rectangle(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                available_geometry=Rectangle(
                    available_geometry.x(), available_geometry.y(),
                    available_geometry.width(), available_geometry.height()
                ),
                metrics=metrics,
                position_in_layout=Point(geometry.x(), geometry.y())
            )
            
            new_screens[screen_id] = config
        
        # Update screen tracking
        old_screens = set(self._screens.keys())
        new_screen_ids = set(new_screens.keys())
        
        # Emit signals for added screens
        for screen_id in new_screen_ids - old_screens:
            self.screen_added.emit(new_screens[screen_id])
        
        # Emit signals for removed screens
        for screen_id in old_screens - new_screen_ids:
            self.screen_removed.emit(screen_id)
        
        # Emit signals for changed screens
        for screen_id in old_screens & new_screen_ids:
            old_config = self._screens[screen_id]
            new_config = new_screens[screen_id]
            
            if (old_config.geometry != new_config.geometry or
                old_config.metrics.scale_factor != new_config.metrics.scale_factor):
                self.screen_changed.emit(new_config)
        
        # Update primary screen
        if primary_screen:
            primary_id = self._qt_screen_to_id(primary_screen)
            if self._primary_screen_id != primary_id:
                self._primary_screen_id = primary_id
                self.primary_screen_changed.emit(primary_id)
        
        # Update screens dict
        self._screens = new_screens
        
        # Set current screen if not set
        if not self._current_screen_id and self._primary_screen_id:
            self._current_screen_id = self._primary_screen_id
        
        self._last_detection_time = time.time() - start_time
    
    def _setup_screen_monitoring(self) -> None:
        """Setup screen change monitoring."""
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_qt_screen_added)
            app.screenRemoved.connect(self._on_qt_screen_removed)
            app.primaryScreenChanged.connect(self._on_qt_primary_screen_changed)
    
    def _start_monitoring(self) -> None:
        """Start screen monitoring timer."""
        self._monitor_timer.start(self._monitor_interval)
    
    def _stop_monitoring(self) -> None:
        """Stop screen monitoring timer."""
        self._monitor_timer.stop()
    
    def _check_screen_changes(self) -> None:
        """Check for screen changes periodically."""
        # Update tracked windows
        widgets_to_remove = []
        for widget, old_screen_id in self._tracked_windows.items():
            if widget.isVisible():
                new_screen_id = self.get_screen_for_widget(widget)
                if new_screen_id and new_screen_id != old_screen_id:
                    self._tracked_windows[widget] = new_screen_id
                    config = self._screens.get(new_screen_id)
                    if config:
                        self.screen_changed.emit(config)
            else:
                widgets_to_remove.append(widget)
        
        # Remove invisible widgets
        for widget in widgets_to_remove:
            self.untrack_widget(widget)
    
    def _qt_screen_to_id(self, qt_screen: QScreen) -> str:
        """Convert Qt screen to our screen ID."""
        return f"screen_{qt_screen.name()}_{id(qt_screen)}"
    
    def _on_qt_screen_added(self, qt_screen: QScreen) -> None:
        """Handle Qt screen added event."""
        self._detect_all_screens()
    
    def _on_qt_screen_removed(self, qt_screen: QScreen) -> None:
        """Handle Qt screen removed event."""
        self._detect_all_screens()
    
    def _on_qt_primary_screen_changed(self, qt_screen: QScreen) -> None:
        """Handle Qt primary screen changed event."""
        self._detect_all_screens()


class ScreenCoordinateMapper:
    """
    Utility class for coordinate mapping between different screen spaces.
    """
    
    def __init__(self, screen_manager: ScreenManager):
        self._screen_manager = screen_manager
        self._coordinate_cache: Dict[str, Tuple[Point, Point]] = {}
        self._cache_max_size = 1000
    
    def map_document_to_screen(self, doc_point: Point, document_bounds: Rectangle,
                              target_screen_id: str) -> Point:
        """Map document coordinate to screen coordinate."""
        screen_config = self._screen_manager.get_screen_configuration(target_screen_id)
        if not screen_config:
            return doc_point
        
        # Normalize document coordinate (0-1 range)
        norm_x = (doc_point.x - document_bounds.x) / document_bounds.width
        norm_y = (doc_point.y - document_bounds.y) / document_bounds.height
        
        # Map to screen coordinates
        screen_x = screen_config.available_geometry.x + norm_x * screen_config.available_geometry.width
        screen_y = screen_config.available_geometry.y + norm_y * screen_config.available_geometry.height
        
        # Apply DPI scaling
        scale_factor = self._screen_manager.get_effective_scale_factor(target_screen_id)
        screen_x *= scale_factor
        screen_y *= scale_factor
        
        return Point(screen_x, screen_y)
    
    def map_screen_to_document(self, screen_point: Point, document_bounds: Rectangle,
                              source_screen_id: str) -> Point:
        """Map screen coordinate to document coordinate."""
        screen_config = self._screen_manager.get_screen_configuration(source_screen_id)
        if not screen_config:
            return screen_point
        
        # Apply inverse DPI scaling
        scale_factor = self._screen_manager.get_effective_scale_factor(source_screen_id)
        adjusted_x = screen_point.x / scale_factor
        adjusted_y = screen_point.y / scale_factor
        
        # Normalize screen coordinate
        norm_x = (adjusted_x - screen_config.available_geometry.x) / screen_config.available_geometry.width
        norm_y = (adjusted_y - screen_config.available_geometry.y) / screen_config.available_geometry.height
        
        # Map to document coordinates
        doc_x = document_bounds.x + norm_x * document_bounds.width
        doc_y = document_bounds.y + norm_y * document_bounds.height
        
        return Point(doc_x, doc_y)
    
    def get_optimal_screen_for_document(self, document_bounds: Rectangle) -> Optional[str]:
        """Get the optimal screen for displaying a document."""
        configs = self._screen_manager.get_screen_configurations()
        if not configs:
            return None
        
        # Prefer primary screen
        primary_id = self._screen_manager.get_primary_screen_id()
        if primary_id:
            return primary_id
        
        # Fallback to largest screen
        largest_screen = max(configs, key=lambda c: c.available_geometry.width * c.available_geometry.height)
        return largest_screen.screen_id
    
    def clear_cache(self) -> None:
        """Clear coordinate mapping cache."""
        self._coordinate_cache.clear()


# Global screen manager instance
screen_manager = ScreenManager()