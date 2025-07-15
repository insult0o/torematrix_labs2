"""
Magnetic snapping system for precise element selection and alignment.
Provides smart snapping to document elements, grid points, and guides.
"""

import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from .hit_testing import SpatialIndex


class SnapType(Enum):
    """Types of snapping."""
    ELEMENT_EDGE = "element_edge"
    ELEMENT_CENTER = "element_center"
    ELEMENT_CORNER = "element_corner"
    GRID_POINT = "grid_point"
    GUIDE_LINE = "guide_line"
    DOCUMENT_EDGE = "document_edge"
    BASELINE = "baseline"
    MARGIN = "margin"


@dataclass
class SnapPoint:
    """A snappable point with metadata."""
    point: Point
    snap_type: SnapType
    element: Optional[LayerElement] = None
    strength: float = 1.0  # 0.0 to 1.0
    description: str = ""
    
    def distance_to(self, other_point: Point) -> float:
        """Calculate distance to another point."""
        dx = self.point.x - other_point.x
        dy = self.point.y - other_point.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class SnapResult:
    """Result of a snap operation."""
    snapped: bool = False
    original_point: Optional[Point] = None
    snapped_point: Optional[Point] = None
    snap_points: List[SnapPoint] = None
    total_offset: Optional[Point] = None
    
    def __post_init__(self):
        if self.snap_points is None:
            self.snap_points = []


class SnapSettings:
    """Configuration for snapping behavior."""
    
    def __init__(self):
        # Snap distances (in pixels)
        self.element_snap_distance = 10.0
        self.grid_snap_distance = 8.0
        self.guide_snap_distance = 12.0
        self.edge_snap_distance = 15.0
        
        # Enabled snap types
        self.enabled_types: Set[SnapType] = {
            SnapType.ELEMENT_EDGE,
            SnapType.ELEMENT_CENTER,
            SnapType.ELEMENT_CORNER,
            SnapType.GRID_POINT
        }
        
        # Grid settings
        self.grid_size = 20.0
        self.grid_enabled = True
        self.grid_subdivision = 4  # Minor grid lines
        
        # Visual feedback
        self.show_snap_indicators = True
        self.show_snap_lines = True
        self.snap_indicator_size = 8
        
        # Performance
        self.max_snap_candidates = 50
        self.cache_snap_points = True
        
        # Magnetic strength
        self.magnetic_strength = 1.0  # Multiplier for snap distances
        
    def get_snap_distance(self, snap_type: SnapType) -> float:
        """Get snap distance for a specific type."""
        distances = {
            SnapType.ELEMENT_EDGE: self.element_snap_distance,
            SnapType.ELEMENT_CENTER: self.element_snap_distance,
            SnapType.ELEMENT_CORNER: self.element_snap_distance,
            SnapType.GRID_POINT: self.grid_snap_distance,
            SnapType.GUIDE_LINE: self.guide_snap_distance,
            SnapType.DOCUMENT_EDGE: self.edge_snap_distance,
            SnapType.BASELINE: self.element_snap_distance,
            SnapType.MARGIN: self.element_snap_distance
        }
        return distances.get(snap_type, self.element_snap_distance) * self.magnetic_strength
    
    def is_enabled(self, snap_type: SnapType) -> bool:
        """Check if snap type is enabled."""
        return snap_type in self.enabled_types


class MagneticSnapping(QObject):
    """
    Advanced magnetic snapping system for precise element selection.
    
    Features:
    - Multiple snap types (edges, centers, corners, grid, guides)
    - Configurable snap distances and strengths
    - Visual feedback with snap indicators
    - Performance optimization with spatial indexing
    - Smart prioritization of snap candidates
    """
    
    # Signals
    snap_occurred = pyqtSignal(object)  # SnapResult
    snap_candidates_changed = pyqtSignal(list)  # List[SnapPoint]
    settings_changed = pyqtSignal()
    
    def __init__(self, spatial_index: Optional[SpatialIndex] = None, parent=None):
        super().__init__(parent)
        
        self.spatial_index = spatial_index
        self.settings = SnapSettings()
        
        # Snap point cache
        self._snap_point_cache: Dict[str, List[SnapPoint]] = {}
        self._cache_timestamp = 0.0
        self._cache_ttl = 1000  # 1 second
        
        # Current snap state
        self._current_candidates: List[SnapPoint] = []
        self._last_snap_result: Optional[SnapResult] = None
        
        # Document bounds for edge snapping
        self._document_bounds: Optional[Rectangle] = None
        
        # Guide lines
        self._horizontal_guides: List[float] = []
        self._vertical_guides: List[float] = []
        
        # Performance metrics
        self._performance_metrics = {
            'snap_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_snap_time': 0.0
        }
    
    def set_document_bounds(self, bounds: Rectangle) -> None:
        """Set document bounds for edge snapping."""
        self._document_bounds = bounds
        self._invalidate_cache()
    
    def add_guide_line(self, position: float, horizontal: bool = True) -> None:
        """Add a guide line for snapping."""
        if horizontal:
            if position not in self._horizontal_guides:
                self._horizontal_guides.append(position)
                self._horizontal_guides.sort()
        else:
            if position not in self._vertical_guides:
                self._vertical_guides.append(position)
                self._vertical_guides.sort()
        
        self._invalidate_cache()
    
    def remove_guide_line(self, position: float, horizontal: bool = True) -> None:
        """Remove a guide line."""
        try:
            if horizontal:
                self._horizontal_guides.remove(position)
            else:
                self._vertical_guides.remove(position)
            self._invalidate_cache()
        except ValueError:
            pass  # Guide not found
    
    def clear_guides(self) -> None:
        """Clear all guide lines."""
        self._horizontal_guides.clear()
        self._vertical_guides.clear()
        self._invalidate_cache()
    
    def snap_point(self, point: Point, exclude_elements: Optional[Set[str]] = None) -> SnapResult:
        """
        Perform snapping for a point.
        
        Args:
            point: Original point to snap
            exclude_elements: Set of element IDs to exclude from snapping
            
        Returns:
            SnapResult with snapping information
        """
        start_time = time.perf_counter()
        
        if exclude_elements is None:
            exclude_elements = set()
        
        try:
            # Get snap candidates
            candidates = self._get_snap_candidates(point, exclude_elements)
            
            if not candidates:
                return SnapResult(
                    snapped=False,
                    original_point=point,
                    snapped_point=point
                )
            
            # Find best snap points
            best_snaps = self._find_best_snaps(point, candidates)
            
            if not best_snaps:
                return SnapResult(
                    snapped=False,
                    original_point=point,
                    snapped_point=point,
                    snap_points=candidates
                )
            
            # Calculate snapped position
            snapped_point = self._calculate_snapped_position(point, best_snaps)
            
            # Create result
            result = SnapResult(
                snapped=True,
                original_point=point,
                snapped_point=snapped_point,
                snap_points=best_snaps,
                total_offset=Point(
                    snapped_point.x - point.x,
                    snapped_point.y - point.y
                )
            )
            
            self._last_snap_result = result
            self.snap_occurred.emit(result)
            
            return result
        
        finally:
            # Update performance metrics
            end_time = time.perf_counter()
            snap_time = (end_time - start_time) * 1000
            self._update_performance_metrics(snap_time)
    
    def get_snap_candidates(self, point: Point, radius: float = None) -> List[SnapPoint]:
        """Get all snap candidates around a point."""
        if radius is None:
            radius = max(self.settings.get_snap_distance(snap_type) 
                        for snap_type in self.settings.enabled_types)
        
        return self._get_snap_candidates(point, set(), radius)
    
    def update_settings(self, **kwargs) -> None:
        """Update snap settings."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        self._invalidate_cache()
        self.settings_changed.emit()
    
    def render_snap_indicators(self, painter: QPainter, viewport_rect: QRectF) -> None:
        """Render snap indicators and feedback."""
        if not self.settings.show_snap_indicators:
            return
        
        if not self._current_candidates:
            return
        
        # Set up drawing
        painter.save()
        
        # Draw snap points
        for snap_point in self._current_candidates:
            self._draw_snap_indicator(painter, snap_point, viewport_rect)
        
        # Draw snap lines if enabled
        if self.settings.show_snap_lines and self._last_snap_result:
            self._draw_snap_lines(painter, self._last_snap_result, viewport_rect)
        
        painter.restore()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self._performance_metrics.copy()
    
    def clear_cache(self) -> None:
        """Clear snap point cache."""
        self._snap_point_cache.clear()
        self._cache_timestamp = 0.0
    
    # Private methods
    
    def _get_snap_candidates(self, point: Point, exclude_elements: Set[str], 
                           max_distance: float = None) -> List[SnapPoint]:
        """Get snap candidates around a point."""
        if max_distance is None:
            max_distance = max(self.settings.get_snap_distance(snap_type) 
                             for snap_type in self.settings.enabled_types)
        
        # Check cache first
        cache_key = f"{point.x}_{point.y}_{max_distance}"
        current_time = time.time() * 1000
        
        if (self.settings.cache_snap_points and 
            cache_key in self._snap_point_cache and
            current_time - self._cache_timestamp < self._cache_ttl):
            
            self._performance_metrics['cache_hits'] += 1
            cached_candidates = self._snap_point_cache[cache_key]
            
            # Filter out excluded elements
            return [sp for sp in cached_candidates 
                   if not sp.element or sp.element.id not in exclude_elements]
        
        self._performance_metrics['cache_misses'] += 1
        
        candidates = []
        
        # Grid snap points
        if self.settings.is_enabled(SnapType.GRID_POINT):
            candidates.extend(self._get_grid_snap_points(point, max_distance))
        
        # Guide line snap points
        if (self.settings.is_enabled(SnapType.GUIDE_LINE) and 
            (self._horizontal_guides or self._vertical_guides)):
            candidates.extend(self._get_guide_snap_points(point, max_distance))
        
        # Document edge snap points
        if (self.settings.is_enabled(SnapType.DOCUMENT_EDGE) and 
            self._document_bounds):
            candidates.extend(self._get_edge_snap_points(point, max_distance))
        
        # Element snap points
        if self.spatial_index:
            element_candidates = self._get_element_snap_points(point, max_distance, exclude_elements)
            candidates.extend(element_candidates)
        
        # Cache results
        if self.settings.cache_snap_points:
            self._snap_point_cache[cache_key] = candidates
            self._cache_timestamp = current_time
        
        return candidates
    
    def _get_grid_snap_points(self, point: Point, max_distance: float) -> List[SnapPoint]:
        """Get grid snap points around a point."""
        if not self.settings.grid_enabled:
            return []
        
        snap_points = []
        grid_size = self.settings.grid_size
        snap_distance = self.settings.get_snap_distance(SnapType.GRID_POINT)
        
        if snap_distance > max_distance:
            return []
        
        # Find nearby grid points
        grid_range = int(max_distance / grid_size) + 1
        
        base_x = int(point.x / grid_size) * grid_size
        base_y = int(point.y / grid_size) * grid_size
        
        for dx in range(-grid_range, grid_range + 1):
            for dy in range(-grid_range, grid_range + 1):
                grid_x = base_x + dx * grid_size
                grid_y = base_y + dy * grid_size
                
                grid_point = Point(grid_x, grid_y)
                distance = math.sqrt(
                    (grid_point.x - point.x) ** 2 + 
                    (grid_point.y - point.y) ** 2
                )
                
                if distance <= snap_distance:
                    snap_points.append(SnapPoint(
                        point=grid_point,
                        snap_type=SnapType.GRID_POINT,
                        strength=1.0 - (distance / snap_distance),
                        description=f"Grid ({grid_x}, {grid_y})"
                    ))
        
        return snap_points
    
    def _get_guide_snap_points(self, point: Point, max_distance: float) -> List[SnapPoint]:
        """Get guide line snap points."""
        snap_points = []
        snap_distance = self.settings.get_snap_distance(SnapType.GUIDE_LINE)
        
        if snap_distance > max_distance:
            return []
        
        # Horizontal guides (snap Y coordinate)
        for guide_y in self._horizontal_guides:
            if abs(guide_y - point.y) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(point.x, guide_y),
                    snap_type=SnapType.GUIDE_LINE,
                    strength=1.0 - (abs(guide_y - point.y) / snap_distance),
                    description=f"Horizontal guide at {guide_y}"
                ))
        
        # Vertical guides (snap X coordinate)
        for guide_x in self._vertical_guides:
            if abs(guide_x - point.x) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(guide_x, point.y),
                    snap_type=SnapType.GUIDE_LINE,
                    strength=1.0 - (abs(guide_x - point.x) / snap_distance),
                    description=f"Vertical guide at {guide_x}"
                ))
        
        return snap_points
    
    def _get_edge_snap_points(self, point: Point, max_distance: float) -> List[SnapPoint]:
        """Get document edge snap points."""
        if not self._document_bounds:
            return []
        
        snap_points = []
        snap_distance = self.settings.get_snap_distance(SnapType.DOCUMENT_EDGE)
        
        if snap_distance > max_distance:
            return []
        
        bounds = self._document_bounds
        
        # Left edge
        if abs(point.x - bounds.x) <= snap_distance:
            snap_points.append(SnapPoint(
                point=Point(bounds.x, point.y),
                snap_type=SnapType.DOCUMENT_EDGE,
                strength=1.0 - (abs(point.x - bounds.x) / snap_distance),
                description="Document left edge"
            ))
        
        # Right edge
        right_edge = bounds.x + bounds.width
        if abs(point.x - right_edge) <= snap_distance:
            snap_points.append(SnapPoint(
                point=Point(right_edge, point.y),
                snap_type=SnapType.DOCUMENT_EDGE,
                strength=1.0 - (abs(point.x - right_edge) / snap_distance),
                description="Document right edge"
            ))
        
        # Top edge
        if abs(point.y - bounds.y) <= snap_distance:
            snap_points.append(SnapPoint(
                point=Point(point.x, bounds.y),
                snap_type=SnapType.DOCUMENT_EDGE,
                strength=1.0 - (abs(point.y - bounds.y) / snap_distance),
                description="Document top edge"
            ))
        
        # Bottom edge
        bottom_edge = bounds.y + bounds.height
        if abs(point.y - bottom_edge) <= snap_distance:
            snap_points.append(SnapPoint(
                point=Point(point.x, bottom_edge),
                snap_type=SnapType.DOCUMENT_EDGE,
                strength=1.0 - (abs(point.y - bottom_edge) / snap_distance),
                description="Document bottom edge"
            ))
        
        return snap_points
    
    def _get_element_snap_points(self, point: Point, max_distance: float, 
                               exclude_elements: Set[str]) -> List[SnapPoint]:
        """Get element snap points."""
        if not self.spatial_index:
            return []
        
        snap_points = []
        
        # Query nearby elements
        search_bounds = Rectangle(
            point.x - max_distance, point.y - max_distance,
            max_distance * 2, max_distance * 2
        )
        
        nearby_elements = self.spatial_index.query_rectangle(search_bounds)
        
        for element in nearby_elements:
            if element.id in exclude_elements:
                continue
            
            if not hasattr(element, 'bounds') or not element.bounds:
                continue
            
            # Generate snap points for this element
            element_snaps = self._get_element_specific_snap_points(
                element, point, max_distance
            )
            snap_points.extend(element_snaps)
        
        return snap_points
    
    def _get_element_specific_snap_points(self, element: LayerElement, 
                                        point: Point, max_distance: float) -> List[SnapPoint]:
        """Get snap points for a specific element."""
        snap_points = []
        bounds = element.bounds
        
        # Element edges
        if self.settings.is_enabled(SnapType.ELEMENT_EDGE):
            snap_distance = self.settings.get_snap_distance(SnapType.ELEMENT_EDGE)
            
            # Left edge
            if abs(point.x - bounds.x) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(bounds.x, point.y),
                    snap_type=SnapType.ELEMENT_EDGE,
                    element=element,
                    strength=1.0 - (abs(point.x - bounds.x) / snap_distance),
                    description=f"Element {element.id} left edge"
                ))
            
            # Right edge
            right_x = bounds.x + bounds.width
            if abs(point.x - right_x) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(right_x, point.y),
                    snap_type=SnapType.ELEMENT_EDGE,
                    element=element,
                    strength=1.0 - (abs(point.x - right_x) / snap_distance),
                    description=f"Element {element.id} right edge"
                ))
            
            # Top edge
            if abs(point.y - bounds.y) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(point.x, bounds.y),
                    snap_type=SnapType.ELEMENT_EDGE,
                    element=element,
                    strength=1.0 - (abs(point.y - bounds.y) / snap_distance),
                    description=f"Element {element.id} top edge"
                ))
            
            # Bottom edge
            bottom_y = bounds.y + bounds.height
            if abs(point.y - bottom_y) <= snap_distance:
                snap_points.append(SnapPoint(
                    point=Point(point.x, bottom_y),
                    snap_type=SnapType.ELEMENT_EDGE,
                    element=element,
                    strength=1.0 - (abs(point.y - bottom_y) / snap_distance),
                    description=f"Element {element.id} bottom edge"
                ))
        
        # Element center
        if self.settings.is_enabled(SnapType.ELEMENT_CENTER):
            center_x = bounds.x + bounds.width / 2
            center_y = bounds.y + bounds.height / 2
            center_point = Point(center_x, center_y)
            
            distance = math.sqrt(
                (center_point.x - point.x) ** 2 + 
                (center_point.y - point.y) ** 2
            )
            
            snap_distance = self.settings.get_snap_distance(SnapType.ELEMENT_CENTER)
            if distance <= snap_distance:
                snap_points.append(SnapPoint(
                    point=center_point,
                    snap_type=SnapType.ELEMENT_CENTER,
                    element=element,
                    strength=1.0 - (distance / snap_distance),
                    description=f"Element {element.id} center"
                ))
        
        # Element corners
        if self.settings.is_enabled(SnapType.ELEMENT_CORNER):
            snap_distance = self.settings.get_snap_distance(SnapType.ELEMENT_CORNER)
            
            corners = [
                Point(bounds.x, bounds.y),  # Top-left
                Point(bounds.x + bounds.width, bounds.y),  # Top-right
                Point(bounds.x, bounds.y + bounds.height),  # Bottom-left
                Point(bounds.x + bounds.width, bounds.y + bounds.height)  # Bottom-right
            ]
            
            corner_names = ["top-left", "top-right", "bottom-left", "bottom-right"]
            
            for corner, name in zip(corners, corner_names):
                distance = math.sqrt(
                    (corner.x - point.x) ** 2 + 
                    (corner.y - point.y) ** 2
                )
                
                if distance <= snap_distance:
                    snap_points.append(SnapPoint(
                        point=corner,
                        snap_type=SnapType.ELEMENT_CORNER,
                        element=element,
                        strength=1.0 - (distance / snap_distance),
                        description=f"Element {element.id} {name} corner"
                    ))
        
        return snap_points
    
    def _find_best_snaps(self, point: Point, candidates: List[SnapPoint]) -> List[SnapPoint]:
        """Find the best snap points from candidates."""
        if not candidates:
            return []
        
        # Sort by strength (highest first)
        candidates.sort(key=lambda sp: sp.strength, reverse=True)
        
        # Limit to maximum candidates for performance
        max_candidates = min(len(candidates), self.settings.max_snap_candidates)
        top_candidates = candidates[:max_candidates]
        
        # Group by axis (X and Y)
        x_snaps = []
        y_snaps = []
        
        for snap_point in top_candidates:
            distance = snap_point.distance_to(point)
            max_distance = self.settings.get_snap_distance(snap_point.snap_type)
            
            if distance <= max_distance:
                # Check if this snap affects X or Y coordinate
                if abs(snap_point.point.x - point.x) > abs(snap_point.point.y - point.y):
                    x_snaps.append(snap_point)
                else:
                    y_snaps.append(snap_point)
        
        # Select best snap for each axis
        best_snaps = []
        
        if x_snaps:
            best_x = max(x_snaps, key=lambda sp: sp.strength)
            best_snaps.append(best_x)
        
        if y_snaps:
            best_y = max(y_snaps, key=lambda sp: sp.strength)
            best_snaps.append(best_y)
        
        self._current_candidates = best_snaps
        self.snap_candidates_changed.emit(best_snaps)
        
        return best_snaps
    
    def _calculate_snapped_position(self, original_point: Point, 
                                  snap_points: List[SnapPoint]) -> Point:
        """Calculate the final snapped position."""
        snapped_x = original_point.x
        snapped_y = original_point.y
        
        for snap_point in snap_points:
            # Apply snapping based on which coordinate is closer
            dx = abs(snap_point.point.x - original_point.x)
            dy = abs(snap_point.point.y - original_point.y)
            
            if dx > dy:  # X-axis snap
                snapped_x = snap_point.point.x
            else:  # Y-axis snap
                snapped_y = snap_point.point.y
        
        return Point(snapped_x, snapped_y)
    
    def _draw_snap_indicator(self, painter: QPainter, snap_point: SnapPoint, 
                           viewport_rect: QRectF) -> None:
        """Draw a snap indicator."""
        # Convert to screen coordinates
        x = snap_point.point.x
        y = snap_point.point.y
        
        # Check if point is in viewport
        if not viewport_rect.contains(x, y):
            return
        
        # Set up drawing style based on snap type
        color = self._get_snap_color(snap_point.snap_type)
        alpha = int(255 * snap_point.strength * 0.8)  # Semi-transparent
        color.setAlpha(alpha)
        
        pen = QPen(color, 2)
        brush = QBrush(color)
        
        painter.setPen(pen)
        painter.setBrush(brush)
        
        # Draw indicator based on type
        size = self.settings.snap_indicator_size
        half_size = size / 2
        
        if snap_point.snap_type == SnapType.GRID_POINT:
            # Small circle for grid points
            painter.drawEllipse(QPointF(x, y), half_size, half_size)
        
        elif snap_point.snap_type == SnapType.ELEMENT_CENTER:
            # Cross for element centers
            painter.drawLine(QPointF(x - half_size, y), QPointF(x + half_size, y))
            painter.drawLine(QPointF(x, y - half_size), QPointF(x, y + half_size))
        
        elif snap_point.snap_type in [SnapType.ELEMENT_EDGE, SnapType.DOCUMENT_EDGE]:
            # Line segment for edges
            if abs(snap_point.point.x - snap_point.point.x) < 0.1:  # Vertical edge
                painter.drawLine(QPointF(x, y - size), QPointF(x, y + size))
            else:  # Horizontal edge
                painter.drawLine(QPointF(x - size, y), QPointF(x + size, y))
        
        elif snap_point.snap_type == SnapType.ELEMENT_CORNER:
            # Small square for corners
            painter.drawRect(QRectF(x - half_size, y - half_size, size, size))
        
        else:
            # Default: small circle
            painter.drawEllipse(QPointF(x, y), half_size, half_size)
    
    def _draw_snap_lines(self, painter: QPainter, snap_result: SnapResult, 
                        viewport_rect: QRectF) -> None:
        """Draw snap alignment lines."""
        if not snap_result.snapped or not snap_result.snap_points:
            return
        
        pen = QPen(QColor(100, 150, 255, 128), 1)  # Light blue, semi-transparent
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        snapped_point = snap_result.snapped_point
        
        for snap_point in snap_result.snap_points:
            if snap_point.snap_type in [SnapType.ELEMENT_EDGE, SnapType.GUIDE_LINE]:
                # Draw alignment line
                if abs(snap_point.point.x - snapped_point.x) < 1:  # Vertical line
                    painter.drawLine(
                        QPointF(snapped_point.x, viewport_rect.top()),
                        QPointF(snapped_point.x, viewport_rect.bottom())
                    )
                elif abs(snap_point.point.y - snapped_point.y) < 1:  # Horizontal line
                    painter.drawLine(
                        QPointF(viewport_rect.left(), snapped_point.y),
                        QPointF(viewport_rect.right(), snapped_point.y)
                    )
    
    def _get_snap_color(self, snap_type: SnapType) -> QColor:
        """Get color for snap type."""
        colors = {
            SnapType.ELEMENT_EDGE: QColor(255, 100, 100),    # Red
            SnapType.ELEMENT_CENTER: QColor(100, 255, 100),  # Green
            SnapType.ELEMENT_CORNER: QColor(255, 255, 100),  # Yellow
            SnapType.GRID_POINT: QColor(150, 150, 255),      # Light blue
            SnapType.GUIDE_LINE: QColor(255, 150, 100),      # Orange
            SnapType.DOCUMENT_EDGE: QColor(200, 100, 255),   # Purple
            SnapType.BASELINE: QColor(100, 200, 255),        # Cyan
            SnapType.MARGIN: QColor(255, 200, 100)           # Light orange
        }
        return colors.get(snap_type, QColor(128, 128, 128))  # Default gray
    
    def _invalidate_cache(self) -> None:
        """Invalidate snap point cache."""
        self._snap_point_cache.clear()
        self._cache_timestamp = 0.0
    
    def _update_performance_metrics(self, snap_time: float) -> None:
        """Update performance metrics."""
        metrics = self._performance_metrics
        metrics['snap_operations'] += 1
        
        # Update average time
        count = metrics['snap_operations']
        current_avg = metrics['average_snap_time']
        metrics['average_snap_time'] = (
            (current_avg * (count - 1) + snap_time) / count
        )