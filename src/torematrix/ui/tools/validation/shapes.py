"""
Selection shape tools for validation area selection.

This module provides different shape tools (rectangle, polygon, freehand)
for creating validation areas with various selection modes.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt6.QtGui import QPainter, QPainterPath, QPolygonF
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
    
    @abstractmethod
    def draw(self, painter: QPainter):
        """Draw the shape."""
        pass
    
    @abstractmethod
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle of the shape."""
        pass
    
    @abstractmethod
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the shape."""
        pass
    
    @abstractmethod
    def get_handles(self) -> List[QPointF]:
        """Get handle points for manipulation."""
        pass
    
    @abstractmethod
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a specific handle to a new position."""
        pass
    
    @abstractmethod
    def translate(self, offset: QPointF):
        """Translate the entire shape by an offset."""
        pass
    
    @abstractmethod
    def to_path(self) -> QPainterPath:
        """Convert shape to QPainterPath."""
        pass
    
    def intersects(self, other: 'SelectionShape') -> bool:
        """Check if this shape intersects with another."""
        return self.to_path().intersects(other.to_path())
    
    def united(self, other: 'SelectionShape') -> QPainterPath:
        """Unite this shape with another."""
        return self.to_path().united(other.to_path())
    
    def subtracted(self, other: 'SelectionShape') -> QPainterPath:
        """Subtract another shape from this one."""
        return self.to_path().subtracted(other.to_path())


@dataclass
class RectangleShape(SelectionShape):
    """Rectangle selection shape."""
    
    top_left: QPointF = field(default_factory=QPointF)
    bottom_right: QPointF = field(default_factory=QPointF)
    
    def draw(self, painter: QPainter):
        """Draw the rectangle."""
        rect = QRectF(self.top_left, self.bottom_right)
        painter.drawRect(rect)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        return QRectF(self.top_left, self.bottom_right).normalized()
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the rectangle."""
        return self.get_bounding_rect().contains(point)
    
    def get_handles(self) -> List[QPointF]:
        """Get corner and edge handles."""
        rect = self.get_bounding_rect()
        return [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomRight(),
            rect.bottomLeft(),
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.center().y()),
            QPointF(rect.center().x(), rect.bottom()),
            QPointF(rect.left(), rect.center().y())
        ]
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a specific handle."""
        rect = self.get_bounding_rect()
        
        # Corner handles
        if index == 0:  # Top-left
            self.top_left = new_pos
        elif index == 1:  # Top-right
            self.top_left.setY(new_pos.y())
            self.bottom_right.setX(new_pos.x())
        elif index == 2:  # Bottom-right
            self.bottom_right = new_pos
        elif index == 3:  # Bottom-left
            self.bottom_right.setY(new_pos.y())
            self.top_left.setX(new_pos.x())
        # Edge handles
        elif index == 4:  # Top
            self.top_left.setY(new_pos.y())
        elif index == 5:  # Right
            self.bottom_right.setX(new_pos.x())
        elif index == 6:  # Bottom
            self.bottom_right.setY(new_pos.y())
        elif index == 7:  # Left
            self.top_left.setX(new_pos.x())
    
    def translate(self, offset: QPointF):
        """Translate the rectangle."""
        self.top_left += offset
        self.bottom_right += offset
    
    def to_path(self) -> QPainterPath:
        """Convert to painter path."""
        path = QPainterPath()
        path.addRect(self.get_bounding_rect())
        return path
    
    def maintain_aspect_ratio(self, ratio: float):
        """Maintain aspect ratio during resize."""
        rect = self.get_bounding_rect()
        center = rect.center()
        width = rect.width()
        height = rect.height()
        
        # Adjust dimensions to maintain ratio
        if width / height > ratio:
            # Too wide, adjust width
            new_width = height * ratio
            self.top_left.setX(center.x() - new_width / 2)
            self.bottom_right.setX(center.x() + new_width / 2)
        else:
            # Too tall, adjust height
            new_height = width / ratio
            self.top_left.setY(center.y() - new_height / 2)
            self.bottom_right.setY(center.y() + new_height / 2)
    
    def set_fixed_size(self, width: float, height: float):
        """Set fixed size from center."""
        center = self.get_bounding_rect().center()
        self.top_left = QPointF(center.x() - width/2, center.y() - height/2)
        self.bottom_right = QPointF(center.x() + width/2, center.y() + height/2)


@dataclass
class PolygonShape(SelectionShape):
    """Polygon selection shape."""
    
    points: List[QPointF] = field(default_factory=list)
    closed: bool = True
    
    def draw(self, painter: QPainter):
        """Draw the polygon."""
        if len(self.points) < 2:
            return
        
        polygon = QPolygonF(self.points)
        if self.closed:
            painter.drawPolygon(polygon)
        else:
            painter.drawPolyline(polygon)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        if not self.points:
            return QRectF()
        
        polygon = QPolygonF(self.points)
        return polygon.boundingRect()
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the polygon."""
        if len(self.points) < 3:
            return False
        
        polygon = QPolygonF(self.points)
        return polygon.containsPoint(point, Qt.FillRule.OddEvenFill)
    
    def get_handles(self) -> List[QPointF]:
        """Get vertex handles."""
        return self.points.copy()
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a specific vertex."""
        if 0 <= index < len(self.points):
            self.points[index] = new_pos
    
    def translate(self, offset: QPointF):
        """Translate the polygon."""
        self.points = [p + offset for p in self.points]
    
    def to_path(self) -> QPainterPath:
        """Convert to painter path."""
        path = QPainterPath()
        if self.points:
            polygon = QPolygonF(self.points)
            path.addPolygon(polygon)
            if self.closed:
                path.closeSubpath()
        return path
    
    def add_point(self, point: QPointF):
        """Add a point to the polygon."""
        self.points.append(point)
    
    def insert_point(self, index: int, point: QPointF):
        """Insert a point at specific index."""
        if 0 <= index <= len(self.points):
            self.points.insert(index, point)
    
    def remove_point(self, index: int):
        """Remove a point at specific index."""
        if 0 <= index < len(self.points) and len(self.points) > 3:
            self.points.pop(index)
    
    def simplify(self, tolerance: float = 1.0):
        """Simplify polygon using Douglas-Peucker algorithm."""
        if len(self.points) <= 3:
            return
        
        # This is a placeholder - Agent 3 will implement the actual algorithm
        # For now, just remove points that are too close
        simplified = [self.points[0]]
        for i in range(1, len(self.points)):
            if (self.points[i] - simplified[-1]).manhattanLength() > tolerance:
                simplified.append(self.points[i])
        
        if len(simplified) >= 3:
            self.points = simplified


@dataclass
class FreehandShape(SelectionShape):
    """Freehand selection shape."""
    
    points: List[QPointF] = field(default_factory=list)
    smoothing_factor: float = 2.0
    
    def draw(self, painter: QPainter):
        """Draw the freehand shape."""
        if len(self.points) < 2:
            return
        
        # Draw as smooth path
        path = self.to_path()
        painter.drawPath(path)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        if not self.points:
            return QRectF()
        
        return self.to_path().boundingRect()
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the shape."""
        return self.to_path().contains(point)
    
    def get_handles(self) -> List[QPointF]:
        """Get control points for manipulation."""
        # Return every Nth point to avoid too many handles
        step = max(1, len(self.points) // 20)
        return self.points[::step]
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a control point."""
        # Map handle index to actual point index
        step = max(1, len(self.points) // 20)
        actual_index = index * step
        
        if 0 <= actual_index < len(self.points):
            offset = new_pos - self.points[actual_index]
            # Move nearby points with falloff
            for i in range(max(0, actual_index - step), 
                          min(len(self.points), actual_index + step + 1)):
                distance = abs(i - actual_index)
                factor = 1.0 - (distance / step)
                self.points[i] += offset * factor
    
    def translate(self, offset: QPointF):
        """Translate the shape."""
        self.points = [p + offset for p in self.points]
    
    def to_path(self) -> QPainterPath:
        """Convert to smooth painter path."""
        path = QPainterPath()
        if len(self.points) < 2:
            return path
        
        # Start at first point
        path.moveTo(self.points[0])
        
        # Create smooth curve through points
        if len(self.points) == 2:
            path.lineTo(self.points[1])
        else:
            # Use quadratic bezier curves for smoothing
            for i in range(1, len(self.points) - 1):
                # Control point is current point
                # End point is midpoint to next
                control = self.points[i]
                end = (self.points[i] + self.points[i + 1]) / 2.0
                path.quadTo(control, end)
            
            # Last segment
            path.lineTo(self.points[-1])
        
        # Close the path
        path.closeSubpath()
        
        return path
    
    def add_point(self, point: QPointF):
        """Add a point to the shape."""
        # Only add if it's far enough from the last point
        if not self.points or (point - self.points[-1]).manhattanLength() > self.smoothing_factor:
            self.points.append(point)
    
    def smooth(self):
        """Apply smoothing to the points."""
        if len(self.points) <= 2:
            return
        
        # Simple smoothing - average with neighbors
        smoothed = [self.points[0]]
        
        for i in range(1, len(self.points) - 1):
            avg = (self.points[i-1] + self.points[i] + self.points[i+1]) / 3.0
            smoothed.append(avg)
        
        smoothed.append(self.points[-1])
        self.points = smoothed


class SelectionTool(ABC):
    """Abstract base class for selection tools."""
    
    def __init__(self):
        self.is_active = False
        self.current_shape = None
    
    @abstractmethod
    def start_selection(self, point: QPointF):
        """Start a new selection."""
        pass
    
    @abstractmethod
    def update_selection(self, point: QPointF):
        """Update the current selection."""
        pass
    
    @abstractmethod
    def complete_selection(self) -> Optional[SelectionShape]:
        """Complete and return the selection."""
        pass
    
    def cancel_selection(self):
        """Cancel the current selection."""
        self.is_active = False
        self.current_shape = None
    
    def get_current_shape(self) -> Optional[SelectionShape]:
        """Get the current shape being created."""
        return self.current_shape


class RectangleSelectionTool(SelectionTool):
    """Tool for creating rectangle selections."""
    
    def __init__(self):
        super().__init__()
        self.start_point = None
    
    def start_selection(self, point: QPointF):
        """Start a new rectangle selection."""
        self.start_point = point
        self.current_shape = RectangleShape(point, point)
        self.is_active = True
    
    def update_selection(self, point: QPointF):
        """Update the rectangle to the current point."""
        if self.is_active and self.current_shape:
            self.current_shape.bottom_right = point
    
    def complete_selection(self) -> Optional[RectangleShape]:
        """Complete the rectangle selection."""
        if self.is_active and self.current_shape:
            shape = self.current_shape
            self.is_active = False
            self.current_shape = None
            self.start_point = None
            return shape
        return None


class PolygonSelectionTool(SelectionTool):
    """Tool for creating polygon selections."""
    
    def __init__(self):
        super().__init__()
        self.temp_point = None
    
    def start_selection(self, point: QPointF):
        """Start a new polygon selection."""
        self.current_shape = PolygonShape([point])
        self.is_active = True
    
    def update_selection(self, point: QPointF):
        """Update temporary preview point."""
        if self.is_active:
            self.temp_point = point
    
    def add_point(self, point: QPointF):
        """Add a point to the polygon."""
        if self.is_active and self.current_shape:
            self.current_shape.add_point(point)
    
    def complete_selection(self) -> Optional[PolygonShape]:
        """Complete the polygon selection."""
        if self.is_active and self.current_shape and len(self.current_shape.points) >= 3:
            shape = self.current_shape
            shape.closed = True
            self.is_active = False
            self.current_shape = None
            self.temp_point = None
            return shape
        return None
    
    def get_preview_shape(self) -> Optional[PolygonShape]:
        """Get preview shape with temporary point."""
        if self.is_active and self.current_shape and self.temp_point:
            preview = PolygonShape(self.current_shape.points + [self.temp_point])
            preview.closed = False
            return preview
        return self.current_shape


class FreehandSelectionTool(SelectionTool):
    """Tool for creating freehand selections."""
    
    def __init__(self):
        super().__init__()
    
    def start_selection(self, point: QPointF):
        """Start a new freehand selection."""
        self.current_shape = FreehandShape([point])
        self.is_active = True
    
    def update_selection(self, point: QPointF):
        """Add point to the freehand shape."""
        if self.is_active and self.current_shape:
            self.current_shape.add_point(point)
    
    def complete_selection(self) -> Optional[FreehandShape]:
        """Complete the freehand selection."""
        if self.is_active and self.current_shape and len(self.current_shape.points) >= 3:
            shape = self.current_shape
            shape.smooth()  # Apply smoothing
            self.is_active = False
            self.current_shape = None
            return shape
        return None
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
