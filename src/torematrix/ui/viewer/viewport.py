"""
Viewport Management System for Document Viewer.

This module provides comprehensive viewport management including screen coordinate
mapping, DPI awareness, viewport clipping, and multi-monitor support.
"""

import math
import time
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QRect, QSize, QPoint, QObject, pyqtSignal
from PyQt6.QtGui import QScreen, QWindow
from PyQt6.QtWidgets import QApplication

from .coordinates import Point, Rectangle, CoordinateTransform


class ViewportState(Enum):
    """Viewport states for different operations."""
    IDLE = "idle"
    UPDATING = "updating"
    PANNING = "panning"
    ZOOMING = "zooming"
    RESIZING = "resizing"


@dataclass
class ViewportInfo:
    """Information about the current viewport."""
    size: Rectangle
    visible_bounds: Rectangle
    scale_factor: float
    rotation_angle: float = 0.0
    pan_offset: Point = field(default_factory=lambda: Point(0, 0))
    dpi_scale: float = 1.0
    
    def copy(self) -> 'ViewportInfo':
        """Create a copy of viewport info."""
        return ViewportInfo(
            size=Rectangle(self.size.x, self.size.y, self.size.width, self.size.height),
            visible_bounds=Rectangle(self.visible_bounds.x, self.visible_bounds.y, 
                                   self.visible_bounds.width, self.visible_bounds.height),
            scale_factor=self.scale_factor,
            rotation_angle=self.rotation_angle,
            pan_offset=Point(self.pan_offset.x, self.pan_offset.y),
            dpi_scale=self.dpi_scale
        )


@dataclass
class ScreenInfo:
    """Information about screen and monitor setup."""
    screen_rect: Rectangle
    available_rect: Rectangle
    dpi: float
    scale_factor: float
    is_primary: bool = False
    name: str = ""
    
    def copy(self) -> 'ScreenInfo':
        """Create a copy of screen info."""
        return ScreenInfo(
            screen_rect=Rectangle(self.screen_rect.x, self.screen_rect.y,
                                self.screen_rect.width, self.screen_rect.height),
            available_rect=Rectangle(self.available_rect.x, self.available_rect.y,
                                   self.available_rect.width, self.available_rect.height),
            dpi=self.dpi,
            scale_factor=self.scale_factor,
            is_primary=self.is_primary,
            name=self.name
        )


class ViewportManager(QObject):
    """
    Comprehensive viewport management system.
    
    Handles viewport transformations, screen coordinate mapping, DPI awareness,
    clipping operations, and multi-monitor support.
    """
    
    # Signals
    viewport_changed = pyqtSignal(object)  # ViewportInfo
    screen_changed = pyqtSignal(object)    # ScreenInfo
    dpi_changed = pyqtSignal(float)        # DPI scale factor
    state_changed = pyqtSignal(object)     # ViewportState
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Viewport state
        self._state = ViewportState.IDLE
        self._viewport_info = ViewportInfo(
            size=Rectangle(0, 0, 800, 600),
            visible_bounds=Rectangle(0, 0, 800, 600),
            scale_factor=1.0
        )
        
        # Screen information
        self._screen_info = self._detect_screen_info()
        self._all_screens: List[ScreenInfo] = []
        self._current_screen_index = 0
        
        # Coordinate transformation
        self._coordinate_transform: Optional[CoordinateTransform] = None
        self._document_bounds = Rectangle(0, 0, 1000, 1000)  # Default document size
        
        # Clipping and bounds
        self._clipping_enabled = True
        self._margin = 10  # Viewport margin in pixels
        
        # Performance tracking
        self._transformation_cache: Dict[str, Any] = {}
        self._cache_max_size = 1000
        self._performance_metrics = {
            'viewport_updates': 0,
            'coordinate_transformations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_transform_time': 0.0
        }
        
        # Initialize screen detection
        self._detect_all_screens()
        self._setup_screen_monitoring()
    
    def initialize(self, widget_size: QSize, document_bounds: Rectangle) -> None:
        """Initialize viewport with widget size and document bounds."""
        self._viewport_info.size = Rectangle(0, 0, widget_size.width(), widget_size.height())
        self._document_bounds = document_bounds
        
        # Create coordinate transformation
        self._coordinate_transform = CoordinateTransform(
            document_bounds=self._document_bounds,
            viewport_bounds=self._viewport_info.size,
            zoom_level=self._viewport_info.scale_factor
        )
        
        # Update visible bounds
        self._update_visible_bounds()
        
        # Emit initialization signals
        self.viewport_changed.emit(self._viewport_info)
    
    def get_viewport_info(self) -> ViewportInfo:
        """Get current viewport information."""
        return self._viewport_info.copy()
    
    def get_screen_info(self) -> ScreenInfo:
        """Get current screen information."""
        return self._screen_info.copy()
    
    def get_all_screens(self) -> List[ScreenInfo]:
        """Get information about all available screens."""
        return [screen.copy() for screen in self._all_screens]
    
    def set_viewport_size(self, size: QSize) -> None:
        """Set viewport size and update transformations."""
        self._state = ViewportState.RESIZING
        self.state_changed.emit(self._state)
        
        # Update viewport size
        self._viewport_info.size = Rectangle(0, 0, size.width(), size.height())
        
        # Update coordinate transformation
        if self._coordinate_transform:
            self._coordinate_transform.update_viewport(
                self._viewport_info.size,
                self._viewport_info.scale_factor
            )
        
        # Update visible bounds
        self._update_visible_bounds()
        
        # Update performance metrics
        self._performance_metrics['viewport_updates'] += 1
        
        self._state = ViewportState.IDLE
        self.state_changed.emit(self._state)
        self.viewport_changed.emit(self._viewport_info)
    
    def set_zoom_level(self, zoom_level: float, center_point: Optional[Point] = None) -> None:
        """Set zoom level with optional center point."""
        self._state = ViewportState.ZOOMING
        self.state_changed.emit(self._state)
        
        # Clamp zoom level to reasonable bounds
        zoom_level = max(0.01, min(100.0, zoom_level))
        
        if center_point:
            # Calculate pan offset to keep center point stable
            old_scale = self._viewport_info.scale_factor
            scale_ratio = zoom_level / old_scale
            
            # Convert center point to document coordinates
            doc_center = self.screen_to_document(center_point)
            
            # Update scale factor
            self._viewport_info.scale_factor = zoom_level
            
            # Update coordinate transformation
            if self._coordinate_transform:
                self._coordinate_transform.set_zoom_level(zoom_level)
            
            # Calculate new pan offset to maintain center point
            new_screen_center = self.document_to_screen(doc_center)
            pan_adjustment = Point(
                center_point.x - new_screen_center.x,
                center_point.y - new_screen_center.y
            )
            self._viewport_info.pan_offset = self._viewport_info.pan_offset + pan_adjustment
            
            if self._coordinate_transform:
                self._coordinate_transform.set_pan_offset(self._viewport_info.pan_offset)
        else:
            # Simple zoom without center point
            self._viewport_info.scale_factor = zoom_level
            if self._coordinate_transform:
                self._coordinate_transform.set_zoom_level(zoom_level)
        
        # Update visible bounds
        self._update_visible_bounds()
        
        self._state = ViewportState.IDLE
        self.state_changed.emit(self._state)
        self.viewport_changed.emit(self._viewport_info)
    
    def set_pan_offset(self, offset: Point) -> None:
        """Set pan offset."""
        self._state = ViewportState.PANNING
        self.state_changed.emit(self._state)
        
        self._viewport_info.pan_offset = offset
        
        if self._coordinate_transform:
            self._coordinate_transform.set_pan_offset(offset)
        
        # Update visible bounds
        self._update_visible_bounds()
        
        self._state = ViewportState.IDLE
        self.state_changed.emit(self._state)
        self.viewport_changed.emit(self._viewport_info)
    
    def pan_by_delta(self, delta: Point) -> None:
        """Pan viewport by delta amount."""
        new_offset = self._viewport_info.pan_offset + delta
        self.set_pan_offset(new_offset)
    
    def set_rotation(self, angle_radians: float) -> None:
        """Set rotation angle."""
        self._viewport_info.rotation_angle = angle_radians
        
        if self._coordinate_transform:
            self._coordinate_transform.set_rotation(angle_radians)
        
        # Update visible bounds
        self._update_visible_bounds()
        
        self.viewport_changed.emit(self._viewport_info)
    
    def document_to_screen(self, doc_point: Point) -> Point:
        """Convert document coordinates to screen coordinates."""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"doc_to_screen_{doc_point.x}_{doc_point.y}_{self._viewport_info.scale_factor}"
        if cache_key in self._transformation_cache:
            self._performance_metrics['cache_hits'] += 1
            return self._transformation_cache[cache_key]
        
        # Perform transformation
        if self._coordinate_transform:
            screen_point = self._coordinate_transform.document_to_screen(doc_point)
        else:
            # Fallback simple transformation
            screen_point = Point(
                (doc_point.x - self._document_bounds.x) * self._viewport_info.scale_factor + self._viewport_info.pan_offset.x,
                (doc_point.y - self._document_bounds.y) * self._viewport_info.scale_factor + self._viewport_info.pan_offset.y
            )
        
        # Apply DPI scaling
        if self._viewport_info.dpi_scale != 1.0:
            screen_point = Point(
                screen_point.x * self._viewport_info.dpi_scale,
                screen_point.y * self._viewport_info.dpi_scale
            )
        
        # Cache result
        if len(self._transformation_cache) < self._cache_max_size:
            self._transformation_cache[cache_key] = screen_point
        
        # Update metrics
        self._performance_metrics['cache_misses'] += 1
        self._performance_metrics['coordinate_transformations'] += 1
        
        transform_time = time.time() - start_time
        self._update_average_transform_time(transform_time)
        
        return screen_point
    
    def screen_to_document(self, screen_point: Point) -> Point:
        """Convert screen coordinates to document coordinates."""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"screen_to_doc_{screen_point.x}_{screen_point.y}_{self._viewport_info.scale_factor}"
        if cache_key in self._transformation_cache:
            self._performance_metrics['cache_hits'] += 1
            return self._transformation_cache[cache_key]
        
        # Apply inverse DPI scaling
        adjusted_point = screen_point
        if self._viewport_info.dpi_scale != 1.0:
            adjusted_point = Point(
                screen_point.x / self._viewport_info.dpi_scale,
                screen_point.y / self._viewport_info.dpi_scale
            )
        
        # Perform transformation
        if self._coordinate_transform:
            doc_point = self._coordinate_transform.screen_to_document(adjusted_point)
        else:
            # Fallback simple transformation
            doc_point = Point(
                (adjusted_point.x - self._viewport_info.pan_offset.x) / self._viewport_info.scale_factor + self._document_bounds.x,
                (adjusted_point.y - self._viewport_info.pan_offset.y) / self._viewport_info.scale_factor + self._document_bounds.y
            )
        
        # Cache result
        if len(self._transformation_cache) < self._cache_max_size:
            self._transformation_cache[cache_key] = doc_point
        
        # Update metrics
        self._performance_metrics['cache_misses'] += 1
        self._performance_metrics['coordinate_transformations'] += 1
        
        transform_time = time.time() - start_time
        self._update_average_transform_time(transform_time)
        
        return doc_point
    
    def transform_rectangle_to_screen(self, doc_rect: Rectangle) -> Rectangle:
        """Transform document rectangle to screen coordinates."""
        # Transform corners
        top_left = self.document_to_screen(Point(doc_rect.x, doc_rect.y))
        bottom_right = self.document_to_screen(Point(
            doc_rect.x + doc_rect.width,
            doc_rect.y + doc_rect.height
        ))
        
        return Rectangle(
            top_left.x,
            top_left.y,
            bottom_right.x - top_left.x,
            bottom_right.y - top_left.y
        )
    
    def transform_rectangle_to_document(self, screen_rect: Rectangle) -> Rectangle:
        """Transform screen rectangle to document coordinates."""
        # Transform corners
        top_left = self.screen_to_document(Point(screen_rect.x, screen_rect.y))
        bottom_right = self.screen_to_document(Point(
            screen_rect.x + screen_rect.width,
            screen_rect.y + screen_rect.height
        ))
        
        return Rectangle(
            top_left.x,
            top_left.y,
            bottom_right.x - top_left.x,
            bottom_right.y - top_left.y
        )
    
    def get_visible_document_bounds(self) -> Rectangle:
        """Get document bounds visible in current viewport."""
        if self._coordinate_transform:
            return self._coordinate_transform.get_visible_document_bounds()
        else:
            # Fallback calculation
            return self.transform_rectangle_to_document(self._viewport_info.size)
    
    def is_point_visible(self, doc_point: Point) -> bool:
        """Check if document point is visible in viewport."""
        screen_point = self.document_to_screen(doc_point)
        return self.is_screen_point_in_viewport(screen_point)
    
    def is_screen_point_in_viewport(self, screen_point: Point) -> bool:
        """Check if screen point is within viewport bounds."""
        return (0 <= screen_point.x <= self._viewport_info.size.width and
                0 <= screen_point.y <= self._viewport_info.size.height)
    
    def is_rectangle_visible(self, doc_rect: Rectangle) -> bool:
        """Check if document rectangle is visible in viewport."""
        screen_rect = self.transform_rectangle_to_screen(doc_rect)
        return self._rectangles_intersect(screen_rect, self._viewport_info.size)
    
    def clip_to_viewport(self, screen_rect: Rectangle) -> Optional[Rectangle]:
        """Clip rectangle to viewport bounds."""
        if not self._clipping_enabled:
            return screen_rect
        
        # Calculate intersection
        left = max(screen_rect.x, 0)
        top = max(screen_rect.y, 0)
        right = min(screen_rect.x + screen_rect.width, self._viewport_info.size.width)
        bottom = min(screen_rect.y + screen_rect.height, self._viewport_info.size.height)
        
        if left < right and top < bottom:
            return Rectangle(left, top, right - left, bottom - top)
        else:
            return None  # No intersection
    
    def fit_document_to_viewport(self, margin: float = 0.1) -> None:
        """Fit entire document to viewport with optional margin."""
        if not self._document_bounds:
            return
        
        # Calculate scale to fit document
        scale_x = self._viewport_info.size.width / self._document_bounds.width
        scale_y = self._viewport_info.size.height / self._document_bounds.height
        
        # Use smaller scale to ensure entire document fits
        fit_scale = min(scale_x, scale_y) * (1.0 - margin)
        
        # Center document in viewport
        self.set_zoom_level(fit_scale)
        
        # Calculate center position
        scaled_doc_width = self._document_bounds.width * fit_scale
        scaled_doc_height = self._document_bounds.height * fit_scale
        
        center_offset = Point(
            (self._viewport_info.size.width - scaled_doc_width) / 2,
            (self._viewport_info.size.height - scaled_doc_height) / 2
        )
        
        self.set_pan_offset(center_offset)
    
    def center_on_point(self, doc_point: Point) -> None:
        """Center viewport on document point."""
        # Calculate screen center
        center_screen = Point(
            self._viewport_info.size.width / 2,
            self._viewport_info.size.height / 2
        )
        
        # Calculate required pan offset
        current_screen_point = self.document_to_screen(doc_point)
        pan_delta = Point(
            center_screen.x - current_screen_point.x,
            center_screen.y - current_screen_point.y
        )
        
        new_pan_offset = self._viewport_info.pan_offset + pan_delta
        self.set_pan_offset(new_pan_offset)
    
    def get_dpi_scale_factor(self) -> float:
        """Get current DPI scale factor."""
        return self._viewport_info.dpi_scale
    
    def update_dpi_awareness(self) -> None:
        """Update DPI awareness based on current screen."""
        screen_info = self._detect_screen_info()
        
        if screen_info.scale_factor != self._viewport_info.dpi_scale:
            old_dpi = self._viewport_info.dpi_scale
            self._viewport_info.dpi_scale = screen_info.scale_factor
            self._screen_info = screen_info
            
            # Clear transformation cache as DPI changed
            self._transformation_cache.clear()
            
            # Emit DPI change signal
            self.dpi_changed.emit(self._viewport_info.dpi_scale)
            self.screen_changed.emit(self._screen_info)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get viewport performance metrics."""
        metrics = self._performance_metrics.copy()
        metrics['cache_size'] = len(self._transformation_cache)
        metrics['cache_hit_rate'] = (
            self._performance_metrics['cache_hits'] / 
            max(1, self._performance_metrics['cache_hits'] + self._performance_metrics['cache_misses'])
        )
        return metrics
    
    def clear_cache(self) -> None:
        """Clear transformation cache."""
        self._transformation_cache.clear()
    
    def _update_visible_bounds(self) -> None:
        """Update visible document bounds."""
        self._viewport_info.visible_bounds = self.get_visible_document_bounds()
    
    def _detect_screen_info(self) -> ScreenInfo:
        """Detect current screen information."""
        app = QApplication.instance()
        if not app:
            # Return default screen info if no application
            return ScreenInfo(
                screen_rect=Rectangle(0, 0, 1920, 1080),
                available_rect=Rectangle(0, 0, 1920, 1080),
                dpi=96.0,
                scale_factor=1.0,
                is_primary=True,
                name="Default"
            )
        
        # Get primary screen
        primary_screen = app.primaryScreen()
        if not primary_screen:
            return ScreenInfo(
                screen_rect=Rectangle(0, 0, 1920, 1080),
                available_rect=Rectangle(0, 0, 1920, 1080),
                dpi=96.0,
                scale_factor=1.0,
                is_primary=True,
                name="Default"
            )
        
        # Extract screen information
        screen_geometry = primary_screen.geometry()
        available_geometry = primary_screen.availableGeometry()
        
        return ScreenInfo(
            screen_rect=Rectangle(
                screen_geometry.x(), screen_geometry.y(),
                screen_geometry.width(), screen_geometry.height()
            ),
            available_rect=Rectangle(
                available_geometry.x(), available_geometry.y(),
                available_geometry.width(), available_geometry.height()
            ),
            dpi=primary_screen.logicalDotsPerInch(),
            scale_factor=primary_screen.devicePixelRatio(),
            is_primary=True,
            name=primary_screen.name()
        )
    
    def _detect_all_screens(self) -> None:
        """Detect all available screens."""
        app = QApplication.instance()
        if not app:
            return
        
        self._all_screens = []
        screens = app.screens()
        primary_screen = app.primaryScreen()
        
        for i, screen in enumerate(screens):
            screen_geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            
            screen_info = ScreenInfo(
                screen_rect=Rectangle(
                    screen_geometry.x(), screen_geometry.y(),
                    screen_geometry.width(), screen_geometry.height()
                ),
                available_rect=Rectangle(
                    available_geometry.x(), available_geometry.y(),
                    available_geometry.width(), available_geometry.height()
                ),
                dpi=screen.logicalDotsPerInch(),
                scale_factor=screen.devicePixelRatio(),
                is_primary=(screen == primary_screen),
                name=screen.name()
            )
            
            self._all_screens.append(screen_info)
    
    def _setup_screen_monitoring(self) -> None:
        """Setup monitoring for screen changes."""
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(self._on_screen_removed)
            app.primaryScreenChanged.connect(self._on_primary_screen_changed)
    
    def _on_screen_added(self, screen: QScreen) -> None:
        """Handle screen added event."""
        self._detect_all_screens()
    
    def _on_screen_removed(self, screen: QScreen) -> None:
        """Handle screen removed event."""
        self._detect_all_screens()
    
    def _on_primary_screen_changed(self, screen: QScreen) -> None:
        """Handle primary screen changed event."""
        self.update_dpi_awareness()
        self._detect_all_screens()
    
    def _rectangles_intersect(self, rect1: Rectangle, rect2: Rectangle) -> bool:
        """Check if two rectangles intersect."""
        return not (rect1.x + rect1.width < rect2.x or
                   rect2.x + rect2.width < rect1.x or
                   rect1.y + rect1.height < rect2.y or
                   rect2.y + rect2.height < rect1.y)
    
    def _update_average_transform_time(self, transform_time: float) -> None:
        """Update average transformation time metric."""
        count = self._performance_metrics['coordinate_transformations']
        current_avg = self._performance_metrics['average_transform_time']
        
        if count == 1:
            self._performance_metrics['average_transform_time'] = transform_time
        else:
            self._performance_metrics['average_transform_time'] = (
                (current_avg * (count - 1) + transform_time) / count
            )