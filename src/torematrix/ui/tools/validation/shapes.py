"""
Shape tools for area selection during manual validation.

This module provides shape classes and tools for creating and manipulating
selection areas during manual validation workflows.
"""

import math
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any, Dict
from PyQt6.QtCore import QPoint, QRect, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QPainterPath
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


@dataclass
class SelectionHandle:
    """Handle for resizing selections."""
    position: QPoint
    size: int = 8
    handle_type: str = "corner"  # corner, edge, center
    cursor_type: str = "default"


class SelectionShape(ABC):
    """Abstract base class for selection shapes."""
    
    def __init__(self, start_point: QPoint):
        self.start_point = start_point
        self.current_point = start_point
        self.finished = False
        self.selected = False
        self.color = QColor(0, 120, 215, 100)
        self.border_color = QColor(0, 120, 215, 255)
        self.border_width = 2
        self.handles = []
        self.handle_size = 8
        
    @abstractmethod
    def update_shape(self, point: QPoint):
        """Update shape with new point."""
        pass
    
    @abstractmethod
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle of shape."""
        pass
    
    @abstractmethod
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside shape."""
        pass
    
    @abstractmethod
    def render(self, painter: QPainter):
        """Render shape to painter."""
        pass
    
    @abstractmethod
    def get_handles(self) -> List[SelectionHandle]:
        """Get resize handles for shape."""
        pass
    
    @abstractmethod
    def resize_by_handle(self, handle_index: int, new_position: QPoint):
        """Resize shape by dragging handle."""
        pass
    
    def finish(self):
        """Mark shape as finished."""
        self.finished = True
        self.handles = self.get_handles()
    
    def select(self, selected: bool = True):
        """Select or deselect shape."""
        self.selected = selected
    
    def hit_test_handle(self, point: QPoint) -> int:
        """Test if point hits a handle. Returns handle index or -1."""
        for i, handle in enumerate(self.handles):
            handle_rect = QRect(
                handle.position.x() - handle.size // 2,
                handle.position.y() - handle.size // 2,
                handle.size,
                handle.size
            )
            if handle_rect.contains(point):
                return i
        return -1
    
    def move(self, offset: QPoint):
        """Move shape by offset."""
        self.start_point += offset
        self.current_point += offset
        self.handles = self.get_handles()
    
    def get_area(self) -> float:
        """Get area of shape."""
        rect = self.get_bounding_rect()
        return rect.width() * rect.height()
    
    def get_center(self) -> QPoint:
        """Get center point of shape."""
        rect = self.get_bounding_rect()
        return rect.center()


class RectangleShape(SelectionShape):
    """Rectangle selection shape."""
    
    def __init__(self, start_point: QPoint):
        super().__init__(start_point)
        self.rect = QRect(start_point, start_point)
    
    def update_shape(self, point: QPoint):
        """Update rectangle with new point."""
        self.current_point = point
        self.rect = QRect(self.start_point, point).normalized()
    
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle."""
        return self.rect
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside rectangle."""
        return self.rect.contains(point)
    
    def render(self, painter: QPainter):
        """Render rectangle."""
        # Fill
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRect(self.rect)
        
        # Draw handles if selected
        if self.selected and self.finished:
            self._draw_handles(painter)
    
    def get_handles(self) -> List[SelectionHandle]:
        """Get resize handles."""
        if not self.finished:
            return []
        
        handles = []
        rect = self.rect
        
        # Corner handles
        handles.append(SelectionHandle(rect.topLeft(), self.handle_size, "corner"))
        handles.append(SelectionHandle(rect.topRight(), self.handle_size, "corner"))
        handles.append(SelectionHandle(rect.bottomRight(), self.handle_size, "corner"))
        handles.append(SelectionHandle(rect.bottomLeft(), self.handle_size, "corner"))
        
        # Edge handles
        handles.append(SelectionHandle(QPoint(rect.center().x(), rect.top()), self.handle_size, "edge"))
        handles.append(SelectionHandle(QPoint(rect.right(), rect.center().y()), self.handle_size, "edge"))
        handles.append(SelectionHandle(QPoint(rect.center().x(), rect.bottom()), self.handle_size, "edge"))
        handles.append(SelectionHandle(QPoint(rect.left(), rect.center().y()), self.handle_size, "edge"))
        
        return handles
    
    def resize_by_handle(self, handle_index: int, new_position: QPoint):
        """Resize rectangle by dragging handle."""
        if handle_index < 0 or handle_index >= len(self.handles):
            return
        
        rect = self.rect
        
        if handle_index == 0:  # Top-left
            self.rect = QRect(new_position, rect.bottomRight()).normalized()
        elif handle_index == 1:  # Top-right
            self.rect = QRect(QPoint(rect.left(), new_position.y()), 
                             QPoint(new_position.x(), rect.bottom())).normalized()
        elif handle_index == 2:  # Bottom-right
            self.rect = QRect(rect.topLeft(), new_position).normalized()
        elif handle_index == 3:  # Bottom-left
            self.rect = QRect(QPoint(new_position.x(), rect.top()), 
                             QPoint(rect.right(), new_position.y())).normalized()
        elif handle_index == 4:  # Top edge
            self.rect = QRect(QPoint(rect.left(), new_position.y()), rect.bottomRight()).normalized()
        elif handle_index == 5:  # Right edge
            self.rect = QRect(rect.topLeft(), QPoint(new_position.x(), rect.bottom())).normalized()
        elif handle_index == 6:  # Bottom edge
            self.rect = QRect(rect.topLeft(), QPoint(rect.right(), new_position.y())).normalized()
        elif handle_index == 7:  # Left edge
            self.rect = QRect(QPoint(new_position.x(), rect.top()), rect.bottomRight()).normalized()
        
        # Update start and current points
        self.start_point = self.rect.topLeft()
        self.current_point = self.rect.bottomRight()
        
        # Update handles
        self.handles = self.get_handles()
    
    def _draw_handles(self, painter: QPainter):
        """Draw resize handles."""
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.setPen(QPen(self.border_color, 1))
        
        for handle in self.handles:
            handle_rect = QRect(
                handle.position.x() - handle.size // 2,
                handle.position.y() - handle.size // 2,
                handle.size,
                handle.size
            )
            painter.drawRect(handle_rect)


class PolygonShape(SelectionShape):
    """Polygon selection shape."""
    
    def __init__(self, start_point: QPoint):
        super().__init__(start_point)
        self.points = [start_point]
        self.polygon = QPolygonF()
        self.closed = False
        self.close_threshold = 10  # pixels
    
    def add_point(self, point: QPoint):
        """Add point to polygon."""
        if self.closed:
            return
        
        # Check if we should close the polygon
        if len(self.points) > 2:
            distance = math.sqrt(
                (point.x() - self.points[0].x()) ** 2 + 
                (point.y() - self.points[0].y()) ** 2
            )
            if distance <= self.close_threshold:
                self.closed = True
                self.finish()
                return
        
        self.points.append(point)
        self.current_point = point
        self._update_polygon()
    
    def update_shape(self, point: QPoint):
        """Update polygon with new point."""
        if not self.closed:
            self.current_point = point
    
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle."""
        if not self.points:
            return QRect()
        
        min_x = min(p.x() for p in self.points)
        max_x = max(p.x() for p in self.points)
        min_y = min(p.y() for p in self.points)
        max_y = max(p.y() for p in self.points)
        
        return QRect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside polygon."""
        if not self.closed:
            return False
        return self.polygon.containsPoint(QPointF(point), 0)  # 0 = Qt.OddEvenFill
    
    def render(self, painter: QPainter):
        """Render polygon."""
        if len(self.points) < 2:
            return
        
        # Create polygon path
        path = QPainterPath()
        path.moveTo(self.points[0])
        
        for point in self.points[1:]:
            path.lineTo(point)
        
        if not self.closed:
            # Draw line to current point
            path.lineTo(self.current_point)
        else:
            # Close polygon
            path.closeSubpath()
        
        # Fill and stroke
        if self.closed:
            painter.setBrush(QBrush(self.color))
        else:
            painter.setBrush(QBrush())
        
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawPath(path)
        
        # Draw vertex points
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.setPen(QPen(self.border_color, 1))
        
        for point in self.points:
            painter.drawEllipse(point, 3, 3)
        
        # Draw handles if selected
        if self.selected and self.finished:
            self._draw_handles(painter)
    
    def get_handles(self) -> List[SelectionHandle]:
        """Get resize handles (vertex points)."""
        if not self.finished:
            return []
        
        handles = []
        for i, point in enumerate(self.points):
            handles.append(SelectionHandle(point, self.handle_size, "vertex"))
        
        return handles
    
    def resize_by_handle(self, handle_index: int, new_position: QPoint):
        """Resize polygon by moving vertex."""
        if handle_index < 0 or handle_index >= len(self.points):
            return
        
        self.points[handle_index] = new_position
        self._update_polygon()
        self.handles = self.get_handles()
    
    def _update_polygon(self):
        """Update internal polygon representation."""
        self.polygon = QPolygonF()
        for point in self.points:
            self.polygon.append(QPointF(point))
    
    def _draw_handles(self, painter: QPainter):
        """Draw vertex handles."""
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.setPen(QPen(self.border_color, 1))
        
        for handle in self.handles:
            painter.drawEllipse(handle.position, handle.size // 2, handle.size // 2)


class FreehandShape(SelectionShape):
    """Freehand selection shape."""
    
    def __init__(self, start_point: QPoint):
        super().__init__(start_point)
        self.path_points = [start_point]
        self.smoothed_points = []
        self.smoothing_factor = 0.5
        self.min_distance = 3  # Minimum distance between points
    
    def add_point(self, point: QPoint):
        """Add point to freehand path."""
        if not self.path_points:
            self.path_points.append(point)
            return
        
        # Check minimum distance
        last_point = self.path_points[-1]
        distance = math.sqrt(
            (point.x() - last_point.x()) ** 2 + 
            (point.y() - last_point.y()) ** 2
        )
        
        if distance >= self.min_distance:
            self.path_points.append(point)
            self.current_point = point
    
    def update_shape(self, point: QPoint):
        """Update freehand path."""
        self.add_point(point)
    
    def finish(self):
        """Finish freehand shape and smooth path."""
        super().finish()
        self.smoothed_points = self._smooth_path(self.path_points)
    
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle."""
        if not self.path_points:
            return QRect()
        
        min_x = min(p.x() for p in self.path_points)
        max_x = max(p.x() for p in self.path_points)
        min_y = min(p.y() for p in self.path_points)
        max_y = max(p.y() for p in self.path_points)
        
        return QRect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside freehand shape."""
        if not self.finished or len(self.smoothed_points) < 3:
            return False
        
        # Use winding number algorithm for point-in-polygon test
        return self._point_in_polygon(point, self.smoothed_points)
    
    def render(self, painter: QPainter):
        """Render freehand shape."""
        if len(self.path_points) < 2:
            return
        
        # Create path
        path = QPainterPath()
        
        if self.finished and self.smoothed_points:
            # Use smoothed points for finished shape
            points = self.smoothed_points
        else:
            # Use raw points for drawing
            points = self.path_points
        
        path.moveTo(points[0])
        
        if len(points) > 2:
            # Create smooth curve using quadratic bezier
            for i in range(1, len(points) - 1):
                control_point = points[i]
                end_point = QPoint(
                    (points[i].x() + points[i + 1].x()) // 2,
                    (points[i].y() + points[i + 1].y()) // 2
                )
                path.quadTo(control_point, end_point)
            
            # Add final point
            path.lineTo(points[-1])
        else:
            # Simple line
            for point in points[1:]:
                path.lineTo(point)
        
        # Close path if finished
        if self.finished:
            path.closeSubpath()
        
        # Fill and stroke
        if self.finished:
            painter.setBrush(QBrush(self.color))
        else:
            painter.setBrush(QBrush())
        
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawPath(path)
        
        # Draw handles if selected
        if self.selected and self.finished:
            self._draw_handles(painter)
    
    def get_handles(self) -> List[SelectionHandle]:
        """Get resize handles (key points)."""
        if not self.finished:
            return []
        
        # Use every nth point as handle
        handles = []
        points = self.smoothed_points if self.smoothed_points else self.path_points
        step = max(1, len(points) // 8)  # Maximum 8 handles
        
        for i in range(0, len(points), step):
            handles.append(SelectionHandle(points[i], self.handle_size, "path"))
        
        return handles
    
    def resize_by_handle(self, handle_index: int, new_position: QPoint):
        """Resize freehand shape by moving handle."""
        if handle_index < 0 or handle_index >= len(self.handles):
            return
        
        # Find corresponding point index
        points = self.smoothed_points if self.smoothed_points else self.path_points
        step = max(1, len(points) // 8)
        point_index = handle_index * step
        
        if point_index < len(points):
            # Calculate offset and apply to nearby points
            offset = new_position - points[point_index]
            influence_radius = 20  # pixels
            
            for i, point in enumerate(points):
                distance = math.sqrt(
                    (point.x() - points[point_index].x()) ** 2 + 
                    (point.y() - points[point_index].y()) ** 2
                )
                
                if distance <= influence_radius:
                    # Apply weighted offset
                    weight = 1.0 - (distance / influence_radius)
                    weighted_offset = QPoint(
                        int(offset.x() * weight),
                        int(offset.y() * weight)
                    )
                    points[i] += weighted_offset
        
        self.handles = self.get_handles()
    
    def _smooth_path(self, points: List[QPoint]) -> List[QPoint]:
        """Smooth path using moving average."""
        if len(points) < 3:
            return points
        
        smoothed = [points[0]]  # Keep first point
        
        for i in range(1, len(points) - 1):
            # Average with neighbors
            prev_point = points[i - 1]
            curr_point = points[i]
            next_point = points[i + 1]
            
            smooth_x = int(
                (prev_point.x() + curr_point.x() + next_point.x()) / 3
            )
            smooth_y = int(
                (prev_point.y() + curr_point.y() + next_point.y()) / 3
            )
            
            smoothed.append(QPoint(smooth_x, smooth_y))
        
        smoothed.append(points[-1])  # Keep last point
        return smoothed
    
    def _point_in_polygon(self, point: QPoint, polygon: List[QPoint]) -> bool:
        """Test if point is inside polygon using winding number."""
        if len(polygon) < 3:
            return False
        
        # Ray casting algorithm
        x, y = point.x(), point.y()
        inside = False
        
        p1x, p1y = polygon[0].x(), polygon[0].y()
        for i in range(1, len(polygon) + 1):
            p2x, p2y = polygon[i % len(polygon)].x(), polygon[i % len(polygon)].y()
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _draw_handles(self, painter: QPainter):
        """Draw path handles."""
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.setPen(QPen(self.border_color, 1))
        
        for handle in self.handles:
            painter.drawEllipse(handle.position, handle.size // 2, handle.size // 2)


# Selection Tools

class SelectionTool(QObject):
    """Base class for selection tools."""
    
    shape_created = pyqtSignal(SelectionShape)
    shape_updated = pyqtSignal(SelectionShape)
    shape_finished = pyqtSignal(SelectionShape)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = False
        self.current_shape = None
        self.shapes = []
        
    def activate(self):
        """Activate tool."""
        self.active = True
        logger.debug(f"{self.__class__.__name__} activated")
    
    def deactivate(self):
        """Deactivate tool."""
        self.active = False
        self.current_shape = None
        logger.debug(f"{self.__class__.__name__} deactivated")
    
    def handle_mouse_press(self, point: QPoint):
        """Handle mouse press event."""
        if not self.active:
            return
        
        self.current_shape = self.create_shape(point)
        self.shape_created.emit(self.current_shape)
    
    def handle_mouse_move(self, point: QPoint):
        """Handle mouse move event."""
        if not self.active or not self.current_shape:
            return
        
        self.current_shape.update_shape(point)
        self.shape_updated.emit(self.current_shape)
    
    def handle_mouse_release(self, point: QPoint):
        """Handle mouse release event."""
        if not self.active or not self.current_shape:
            return
        
        self.current_shape.finish()
        self.shapes.append(self.current_shape)
        self.shape_finished.emit(self.current_shape)
        self.current_shape = None
    
    def create_shape(self, start_point: QPoint) -> SelectionShape:
        """Create new shape. Override in subclasses."""
        raise NotImplementedError
    
    def get_shapes(self) -> List[SelectionShape]:
        """Get all created shapes."""
        return self.shapes.copy()
    
    def clear_shapes(self):
        """Clear all shapes."""
        self.shapes.clear()
    
    def remove_shape(self, shape: SelectionShape):
        """Remove specific shape."""
        if shape in self.shapes:
            self.shapes.remove(shape)


class RectangleSelectionTool(SelectionTool):
    """Rectangle selection tool."""
    
    def create_shape(self, start_point: QPoint) -> SelectionShape:
        """Create rectangle shape."""
        return RectangleShape(start_point)


class PolygonSelectionTool(SelectionTool):
    """Polygon selection tool."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.creating_polygon = False
    
    def handle_mouse_press(self, point: QPoint):
        """Handle mouse press for polygon creation."""
        if not self.active:
            return
        
        if not self.creating_polygon:
            # Start new polygon
            self.current_shape = self.create_shape(point)
            self.creating_polygon = True
            self.shape_created.emit(self.current_shape)
        else:
            # Add point to existing polygon
            self.current_shape.add_point(point)
            self.shape_updated.emit(self.current_shape)
            
            # Check if polygon is closed
            if self.current_shape.closed:
                self.current_shape.finish()
                self.shapes.append(self.current_shape)
                self.shape_finished.emit(self.current_shape)
                self.current_shape = None
                self.creating_polygon = False
    
    def handle_mouse_move(self, point: QPoint):
        """Handle mouse move for polygon preview."""
        if not self.active or not self.creating_polygon or not self.current_shape:
            return
        
        self.current_shape.update_shape(point)
        self.shape_updated.emit(self.current_shape)
    
    def handle_mouse_release(self, point: QPoint):
        """Handle mouse release (no-op for polygon)."""
        pass
    
    def create_shape(self, start_point: QPoint) -> SelectionShape:
        """Create polygon shape."""
        return PolygonShape(start_point)


class FreehandSelectionTool(SelectionTool):
    """Freehand selection tool."""
    
    def handle_mouse_press(self, point: QPoint):
        """Start freehand drawing."""
        if not self.active:
            return
        
        self.current_shape = self.create_shape(point)
        self.shape_created.emit(self.current_shape)
    
    def handle_mouse_move(self, point: QPoint):
        """Continue freehand drawing."""
        if not self.active or not self.current_shape:
            return
        
        self.current_shape.add_point(point)
        self.shape_updated.emit(self.current_shape)
    
    def create_shape(self, start_point: QPoint) -> SelectionShape:
        """Create freehand shape."""
        return FreehandShape(start_point)


# Utility functions

def create_selection_tool(tool_type: str) -> SelectionTool:
    """Factory function to create selection tools."""
    if tool_type.lower() == "rectangle":
        return RectangleSelectionTool()
    elif tool_type.lower() == "polygon":
        return PolygonSelectionTool()
    elif tool_type.lower() == "freehand":
        return FreehandSelectionTool()
    else:
        raise ValueError(f"Unknown tool type: {tool_type}")


def get_available_tools() -> List[str]:
    """Get list of available selection tools."""
    return ["rectangle", "polygon", "freehand"]