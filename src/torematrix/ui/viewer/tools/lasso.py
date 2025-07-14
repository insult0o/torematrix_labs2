"""
Lasso Tool for freeform polygon selection.

This tool provides freeform selection with polygon-based selection,
path smoothing, and automatic polygon closure functionality.
"""

import math
import time
from typing import List, Optional, Set

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QPainter, QCursor, QPen, QColor, QBrush, QPolygon

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from ..multi_select import GeometryUtils


class LassoTool(SelectionTool):
    """
    Freeform selection tool with polygon-based selection.
    
    Features:
    - Freehand polygon drawing
    - Automatic polygon closure detection
    - Path smoothing for cleaner selection
    - Point-in-polygon selection testing
    - Real-time preview during drawing
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Lasso path
        self._lasso_points: List[QPoint] = []
        self._closed_polygon: List[QPoint] = []
        self._is_drawing = False
        self._is_closed = False
        
        # Path configuration
        self._min_points = 3
        self._min_distance = 5  # Minimum distance between points
        self._close_distance = 15  # Distance to auto-close polygon
        self._smoothing_enabled = True
        self._smoothing_factor = 0.3
        
        # Selection state
        self._preview_elements: Set[LayerElement] = set()
        self._final_elements: Set[LayerElement] = set()
        
        # Visual styling
        self._path_color = QColor(50, 205, 50)  # Green
        self._closed_color = QColor(50, 205, 50, 100)  # Semi-transparent green
        self._preview_color = QColor(50, 205, 50, 150)  # Highlight green
        self._path_width = 2
        self._closed_width = 2
        
        # Performance tracking
        self._path_operations = 0
        self._points_processed = 0
        self._smoothing_operations = 0
    
    def activate(self) -> None:
        """Activate lasso tool with crosshair cursor."""
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.CrossCursor))
    
    def deactivate(self) -> None:
        """Deactivate lasso tool and reset state."""
        self._update_state(ToolState.INACTIVE)
        self._reset_lasso()
    
    def set_smoothing_enabled(self, enabled: bool) -> None:
        """Enable or disable path smoothing."""
        self._smoothing_enabled = enabled
    
    def set_smoothing_factor(self, factor: float) -> None:
        """Set smoothing factor (0.0 to 1.0)."""
        self._smoothing_factor = max(0.0, min(1.0, factor))
    
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Start lasso selection."""
        if self._state != ToolState.ACTIVE:
            return False
        
        start_time = time.time()
        
        # Initialize lasso path
        self._lasso_points = [point]
        self._closed_polygon = []
        self._is_drawing = True
        self._is_closed = False
        self._preview_elements.clear()
        self._final_elements.clear()
        
        self._update_state(ToolState.SELECTING)
        self.set_cursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self._path_operations += 1
        operation_time = time.time() - start_time
        self._update_metrics(operation_time)
        
        return True
    
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Add points to lasso path."""
        if self._state == ToolState.SELECTING and self._is_drawing:
            # Check if we should close the polygon
            if len(self._lasso_points) >= self._min_points:
                distance_to_start = self._get_distance(point, self._lasso_points[0])
                if distance_to_start <= self._close_distance:
                    # Close polygon by connecting to start
                    self._close_polygon()
                    return True
            
            # Add point if it's far enough from the last point
            if (not self._lasso_points or 
                self._get_distance(point, self._lasso_points[-1]) > self._min_distance):
                
                self._lasso_points.append(point)
                self._points_processed += 1
                
                # Update preview selection if we have enough points
                if len(self._lasso_points) >= self._min_points:
                    self._update_preview_selection()
                
                # Update cursor to show we're drawing
                self.set_cursor(QCursor(Qt.CursorShape.PointingHandCursor))
            
            return True
        
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Complete lasso selection."""
        if self._state == ToolState.SELECTING and self._is_drawing:
            start_time = time.time()
            
            # Auto-close if we have enough points and haven't closed yet
            if len(self._lasso_points) >= self._min_points and not self._is_closed:
                self._close_polygon()
            
            # Find elements in polygon
            if self._closed_polygon:
                self._final_elements = self._find_elements_in_polygon(self._closed_polygon)
                
                if self._final_elements:
                    # Calculate selection bounds
                    selection_bounds = self._calculate_selection_bounds(self._final_elements)
                    polygon_bounds = self._get_polygon_bounds(self._closed_polygon)
                    
                    # Create selection result
                    result = SelectionResult(
                        elements=list(self._final_elements),
                        geometry=selection_bounds,
                        tool_type="lasso",
                        timestamp=time.time(),
                        metadata={
                            "polygon_points": len(self._closed_polygon),
                            "polygon_bounds": polygon_bounds,
                            "element_count": len(self._final_elements),
                            "polygon_area": self._calculate_polygon_area(self._closed_polygon),
                            "path_length": self._calculate_path_length(self._lasso_points),
                            "smoothing_enabled": self._smoothing_enabled,
                            "modifiers": int(modifiers)
                        }
                    )
                    
                    # Update selection
                    self._current_selection = result
                    self._update_state(ToolState.SELECTED)
                    self.selection_changed.emit(result)
                    
                    operation_time = time.time() - start_time
                    self._update_metrics(operation_time)
                    
                    return True
            
            # No valid selection
            self._reset_lasso()
            return True
        
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle keyboard input."""
        if key == Qt.Key.Key_Escape:
            if self._state == ToolState.SELECTING:
                self._reset_lasso()
            else:
                self.clear_selection()
            return True
        
        # Enter key to manually close polygon
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            if self._state == ToolState.SELECTING and len(self._lasso_points) >= self._min_points:
                self._close_polygon()
            return True
        
        # Toggle smoothing
        if key == Qt.Key.Key_S:
            self.set_smoothing_enabled(not self._smoothing_enabled)
            return True
        
        return False
    
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render lasso path and selection."""
        if not self._visible:
            return
        
        # Draw lasso path
        if self._lasso_points and self._state == ToolState.SELECTING:
            painter.setPen(QPen(self._path_color, self._path_width))
            painter.setBrush(QBrush())  # No fill
            
            # Draw path segments
            for i in range(1, len(self._lasso_points)):
                painter.drawLine(self._lasso_points[i-1], self._lasso_points[i])
            
            # Draw closing line if close to start
            if len(self._lasso_points) >= self._min_points:
                last_point = self._lasso_points[-1]
                start_point = self._lasso_points[0]
                distance = self._get_distance(last_point, start_point)
                
                if distance <= self._close_distance:
                    painter.setPen(QPen(self._path_color, self._path_width, Qt.PenStyle.DashLine))
                    painter.drawLine(last_point, start_point)
        
        # Draw closed polygon
        if self._closed_polygon:
            polygon = QPolygon(self._closed_polygon)
            painter.setPen(QPen(self._closed_color, self._closed_width))
            painter.setBrush(QBrush(QColor(self._closed_color.red(), 
                                         self._closed_color.green(), 
                                         self._closed_color.blue(), 30)))
            painter.drawPolygon(polygon)
        
        # Highlight preview elements
        if self._preview_elements and self._state == ToolState.SELECTING:
            painter.setPen(QPen(self._preview_color, 1))
            painter.setBrush(QBrush())  # No fill
            
            for element in self._preview_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    qrect = self._rectangle_to_qrect(bounds)
                    painter.drawRect(qrect)
        
        # Draw final selection
        if self._final_elements and self._state == ToolState.SELECTED:
            painter.setPen(QPen(self._path_color, self._path_width + 1))
            painter.setBrush(QBrush())  # No fill
            
            for element in self._final_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    qrect = self._rectangle_to_qrect(bounds)
                    painter.drawRect(qrect)
            
            # Draw final polygon
            if self._closed_polygon:
                polygon = QPolygon(self._closed_polygon)
                painter.setPen(QPen(self._path_color, self._closed_width))
                painter.setBrush(QBrush())  # No fill
                painter.drawPolygon(polygon)
    
    def _close_polygon(self) -> None:
        """Close the polygon and apply smoothing if enabled."""
        if len(self._lasso_points) < self._min_points:
            return
        
        # Create closed polygon
        self._closed_polygon = self._lasso_points + [self._lasso_points[0]]
        
        # Apply smoothing if enabled
        if self._smoothing_enabled:
            self._closed_polygon = self._smooth_polygon(self._closed_polygon)
            self._smoothing_operations += 1
        
        self._is_closed = True
        self._is_drawing = False
        self.set_cursor(QCursor(Qt.CursorShape.ClosedHandCursor))
    
    def _update_preview_selection(self) -> None:
        """Update preview elements during lasso drawing."""
        if len(self._lasso_points) < self._min_points:
            return
        
        # Create temporary closed polygon for preview
        temp_polygon = self._lasso_points + [self._lasso_points[0]]
        
        # Find elements in temporary polygon
        new_preview = self._find_elements_in_polygon(temp_polygon)
        
        # Update preview if changed
        if new_preview != self._preview_elements:
            self._preview_elements = new_preview
            
            # Create preview result
            if self._preview_elements:
                preview_bounds = self._calculate_selection_bounds(self._preview_elements)
                preview_result = SelectionResult(
                    elements=list(self._preview_elements),
                    geometry=preview_bounds,
                    tool_type="lasso",
                    timestamp=time.time(),
                    metadata={
                        "preview": True,
                        "element_count": len(self._preview_elements),
                        "polygon_points": len(temp_polygon)
                    }
                )
                
                self._preview_selection = preview_result
                self.preview_changed.emit(preview_result)
    
    def _find_elements_in_polygon(self, polygon: List[QPoint]) -> Set[LayerElement]:
        """Find all elements that intersect with the polygon."""
        if not polygon or len(polygon) < 3:
            return set()
        
        # Convert to Point objects for geometry utils
        polygon_points = [self._qpoint_to_point(p) for p in polygon]
        
        # Get bounding box for initial filtering
        polygon_bounds = self._get_polygon_bounds(polygon)
        
        # TODO: Get elements from overlay API within bounding box
        candidate_elements = self._get_elements_in_area(polygon_bounds)
        
        # Filter elements using point-in-polygon test
        selected_elements = set()
        for element in candidate_elements:
            if self._element_intersects_polygon(element, polygon_points):
                selected_elements.add(element)
        
        return selected_elements
    
    def _element_intersects_polygon(self, element: LayerElement, polygon: List[Point]) -> bool:
        """Check if element intersects with polygon."""
        element_bounds = self._get_element_bounds(element)
        if not element_bounds:
            return False
        
        # Test element corners and center
        test_points = [
            element_bounds.top_left,
            element_bounds.top_right,
            element_bounds.bottom_left,
            element_bounds.bottom_right,
            element_bounds.center
        ]
        
        # If any point is inside polygon, element intersects
        for point in test_points:
            if GeometryUtils.point_in_polygon(point, polygon):
                return True
        
        # TODO: More sophisticated polygon-rectangle intersection test
        return False
    
    def _get_elements_in_area(self, area: Rectangle) -> List[LayerElement]:
        """Get all elements in the specified area."""
        # TODO: Implement actual element retrieval from overlay API
        return []
    
    def _smooth_polygon(self, polygon: List[QPoint]) -> List[QPoint]:
        """Apply smoothing to polygon points."""
        if len(polygon) < 3:
            return polygon
        
        smoothed = []
        for i in range(len(polygon)):
            if i == 0 or i == len(polygon) - 1:
                # Keep first and last points (same for closed polygon)
                smoothed.append(polygon[i])
                continue
            
            prev_point = polygon[i-1]
            curr_point = polygon[i]
            next_point = polygon[i+1]
            
            # Apply smoothing using weighted average
            smooth_x = (
                prev_point.x() * (1 - self._smoothing_factor) +
                curr_point.x() * self._smoothing_factor +
                next_point.x() * (1 - self._smoothing_factor)
            ) / (2 - self._smoothing_factor)
            
            smooth_y = (
                prev_point.y() * (1 - self._smoothing_factor) +
                curr_point.y() * self._smoothing_factor +
                next_point.y() * (1 - self._smoothing_factor)
            ) / (2 - self._smoothing_factor)
            
            smoothed.append(QPoint(int(smooth_x), int(smooth_y)))
        
        return smoothed
    
    def _get_polygon_bounds(self, polygon: List[QPoint]) -> Rectangle:
        """Get bounding rectangle of polygon."""
        if not polygon:
            return Rectangle(0, 0, 0, 0)
        
        min_x = min(p.x() for p in polygon)
        min_y = min(p.y() for p in polygon)
        max_x = max(p.x() for p in polygon)
        max_y = max(p.y() for p in polygon)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _calculate_polygon_area(self, polygon: List[QPoint]) -> float:
        """Calculate area of polygon using shoelace formula."""
        if len(polygon) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            area += polygon[i].x() * polygon[j].y()
            area -= polygon[j].x() * polygon[i].y()
        
        return abs(area) / 2.0
    
    def _calculate_path_length(self, path: List[QPoint]) -> float:
        """Calculate total length of path."""
        if len(path) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(1, len(path)):
            total_length += self._get_distance(path[i-1], path[i])
        
        return total_length
    
    def _calculate_selection_bounds(self, elements: Set[LayerElement]) -> Rectangle:
        """Calculate bounding rectangle for a set of elements."""
        if not elements:
            return Rectangle(0, 0, 0, 0)
        
        bounds_list = []
        for element in elements:
            bounds = self._get_element_bounds(element)
            if bounds:
                bounds_list.append(bounds)
        
        if not bounds_list:
            return Rectangle(0, 0, 0, 0)
        
        # Calculate union of all bounds
        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _get_element_bounds(self, element: LayerElement) -> Optional[Rectangle]:
        """Get element bounding rectangle."""
        if hasattr(element, 'get_bounds'):
            return element.get_bounds()
        elif hasattr(element, 'bounds'):
            return element.bounds
        elif hasattr(element, 'bounding_rect'):
            return element.bounding_rect
        else:
            return None
    
    def _reset_lasso(self) -> None:
        """Reset lasso state."""
        self._lasso_points = []
        self._closed_polygon = []
        self._is_drawing = False
        self._is_closed = False
        self._preview_elements.clear()
        self._final_elements.clear()
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.CrossCursor))
        
        # Clear preview
        self._preview_selection = SelectionResult()
        self.preview_changed.emit(self._preview_selection)
    
    def get_path_statistics(self) -> dict:
        """Get path drawing statistics."""
        return {
            "path_operations": self._path_operations,
            "points_processed": self._points_processed,
            "smoothing_operations": self._smoothing_operations,
            "current_path_length": len(self._lasso_points),
            "is_closed": self._is_closed,
            "polygon_area": (
                self._calculate_polygon_area(self._closed_polygon) 
                if self._closed_polygon else 0.0
            )
        }
    
    def get_tool_info(self) -> dict:
        """Get tool information and statistics."""
        return {
            "name": "Lasso Tool",
            "type": "lasso",
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "smoothing_enabled": self._smoothing_enabled,
            "smoothing_factor": self._smoothing_factor,
            "is_drawing": self._is_drawing,
            "is_closed": self._is_closed,
            "path_points": len(self._lasso_points),
            "preview_elements": len(self._preview_elements),
            "final_elements": len(self._final_elements),
            "path_statistics": self.get_path_statistics(),
            "metrics": self.get_metrics()
        }