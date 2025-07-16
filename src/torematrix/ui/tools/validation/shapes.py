"""
Selection shape tools for validation area selection.

This module provides different shape tools (rectangle, polygon, freehand)
for creating validation areas with various selection modes.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt6.QtGui import QPainter, QPainterPath, QPolygonF


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
        return QRectF(self.top_left, self.bottom_right)
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the rectangle."""
        return self.get_bounding_rect().contains(point)
    
    def get_handles(self) -> List[QPointF]:
        """Get corner handles for resizing."""
        rect = self.get_bounding_rect()
        return [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight(),
            # Edge midpoints
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.center().y()),
            QPointF(rect.center().x(), rect.bottom()),
            QPointF(rect.left(), rect.center().y())
        ]
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a specific handle."""
        if index == 0:  # Top-left
            self.top_left = new_pos
        elif index == 1:  # Top-right
            self.top_left.setY(new_pos.y())
            self.bottom_right.setX(new_pos.x())
        elif index == 2:  # Bottom-left
            self.top_left.setX(new_pos.x())
            self.bottom_right.setY(new_pos.y())
        elif index == 3:  # Bottom-right
            self.bottom_right = new_pos
        elif index == 4:  # Top edge
            self.top_left.setY(new_pos.y())
        elif index == 5:  # Right edge
            self.bottom_right.setX(new_pos.x())
        elif index == 6:  # Bottom edge
            self.bottom_right.setY(new_pos.y())
        elif index == 7:  # Left edge
            self.top_left.setX(new_pos.x())
    
    def translate(self, offset: QPointF):
        """Translate the rectangle."""
        self.top_left += offset
        self.bottom_right += offset
    
    def to_path(self) -> QPainterPath:
        """Convert to QPainterPath."""
        path = QPainterPath()
        path.addRect(self.get_bounding_rect())
        return path
    
    def set_from_points(self, start: QPointF, end: QPointF):
        """Set rectangle from two points."""
        self.top_left = QPointF(min(start.x(), end.x()), min(start.y(), end.y()))
        self.bottom_right = QPointF(max(start.x(), end.x()), max(start.y(), end.y()))


@dataclass
class PolygonShape(SelectionShape):
    """Polygon selection shape."""
    
    points: List[QPointF] = field(default_factory=list)
    
    def draw(self, painter: QPainter):
        """Draw the polygon."""
        if len(self.points) >= 2:
            polygon = QPolygonF(self.points)
            painter.drawPolygon(polygon)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        if not self.points:
            return QRectF()
        
        min_x = min(p.x() for p in self.points)
        max_x = max(p.x() for p in self.points)
        min_y = min(p.y() for p in self.points)
        max_y = max(p.y() for p in self.points)
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the polygon."""
        if len(self.points) < 3:
            return False
        
        polygon = QPolygonF(self.points)
        return polygon.containsPoint(point, Qt.FillRule.OddEvenFill)
    
    def get_handles(self) -> List[QPointF]:
        """Get vertex handles for manipulation."""
        return self.points.copy()
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a specific vertex."""
        if 0 <= index < len(self.points):
            self.points[index] = new_pos
    
    def translate(self, offset: QPointF):
        """Translate the polygon."""
        self.points = [p + offset for p in self.points]
    
    def to_path(self) -> QPainterPath:
        """Convert to QPainterPath."""
        path = QPainterPath()
        if self.points:
            path.moveTo(self.points[0])
            for point in self.points[1:]:
                path.lineTo(point)
            path.closeSubpath()
        return path
    
    def add_point(self, point: QPointF):
        """Add a point to the polygon."""
        self.points.append(point)
    
    def close_polygon(self):
        """Close the polygon by connecting last point to first."""
        if len(self.points) >= 3 and self.points[-1] != self.points[0]:
            # Polygon is automatically closed by QPainterPath
            pass


class FreehandShape(SelectionShape):
    """Freehand selection shape."""
    
    def __init__(self):
        self.points: List[QPointF] = []
        self.smoothed_points: List[QPointF] = []
        self.smoothing_factor = 2.0
    
    def draw(self, painter: QPainter):
        """Draw the freehand shape."""
        if len(self.smoothed_points) >= 2:
            path = self.to_path()
            painter.drawPath(path)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        if not self.smoothed_points:
            return QRectF()
        
        min_x = min(p.x() for p in self.smoothed_points)
        max_x = max(p.x() for p in self.smoothed_points)
        min_y = min(p.y() for p in self.smoothed_points)
        max_y = max(p.y() for p in self.smoothed_points)
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the freehand shape."""
        path = self.to_path()
        return path.contains(point)
    
    def get_handles(self) -> List[QPointF]:
        """Get control points for manipulation."""
        # Return every nth point for manageable handle count
        step = max(1, len(self.smoothed_points) // 8)
        return self.smoothed_points[::step]
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a control point."""
        # Find the nearest actual point to the handle
        if self.smoothed_points:
            step = max(1, len(self.smoothed_points) // 8)
            actual_index = index * step
            if actual_index < len(self.smoothed_points):
                self.smoothed_points[actual_index] = new_pos
    
    def translate(self, offset: QPointF):
        """Translate the freehand shape."""
        self.points = [p + offset for p in self.points]
        self.smoothed_points = [p + offset for p in self.smoothed_points]
    
    def to_path(self) -> QPainterPath:
        """Convert to QPainterPath with smoothing."""
        path = QPainterPath()
        if not self.smoothed_points:
            return path
        
        if len(self.smoothed_points) == 1:
            path.addEllipse(self.smoothed_points[0], 2, 2)
        elif len(self.smoothed_points) >= 2:
            path.moveTo(self.smoothed_points[0])
            
            # Use quadratic curves for smoother appearance
            for i in range(1, len(self.smoothed_points) - 1):
                control_point = self.smoothed_points[i]
                end_point = QPointF(
                    (self.smoothed_points[i].x() + self.smoothed_points[i + 1].x()) / 2,
                    (self.smoothed_points[i].y() + self.smoothed_points[i + 1].y()) / 2
                )
                path.quadTo(control_point, end_point)
            
            # Close the path
            path.closeSubpath()
        
        return path
    
    def add_point(self, point: QPointF):
        """Add a point to the freehand shape."""
        self.points.append(point)
        self._update_smoothed_points()
    
    def _update_smoothed_points(self):
        """Update smoothed points for better appearance."""
        if len(self.points) < 2:
            self.smoothed_points = self.points.copy()
            return
        
        # Simple smoothing algorithm
        self.smoothed_points = [self.points[0]]
        
        for i in range(1, len(self.points) - 1):
            # Average with neighboring points
            prev_point = self.points[i - 1]
            curr_point = self.points[i]
            next_point = self.points[i + 1]
            
            smoothed_x = (prev_point.x() + curr_point.x() + next_point.x()) / 3.0
            smoothed_y = (prev_point.y() + curr_point.y() + next_point.y()) / 3.0
            
            self.smoothed_points.append(QPointF(smoothed_x, smoothed_y))
        
        self.smoothed_points.append(self.points[-1])


# Selection Tool Classes
class SelectionTool(ABC):
    """Abstract base class for selection tools."""
    
    def __init__(self):
        self.is_active = False
        self.current_shape: Optional[SelectionShape] = None
    
    @abstractmethod
    def start_selection(self, point: QPointF):
        """Start a new selection at the given point."""
        pass
    
    @abstractmethod
    def update_selection(self, point: QPointF):
        """Update the current selection with a new point."""
        pass
    
    @abstractmethod
    def complete_selection(self) -> Optional[SelectionShape]:
        """Complete the selection and return the shape."""
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
        self.start_point: Optional[QPointF] = None
    
    def start_selection(self, point: QPointF):
        """Start rectangle selection."""
        self.is_active = True
        self.start_point = point
        self.current_shape = RectangleShape()
        self.current_shape.set_from_points(point, point)
    
    def update_selection(self, point: QPointF):
        """Update rectangle selection."""
        if self.is_active and self.start_point and self.current_shape:
            self.current_shape.set_from_points(self.start_point, point)
    
    def complete_selection(self) -> Optional[SelectionShape]:
        """Complete rectangle selection."""
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
        self.min_points = 3
    
    def start_selection(self, point: QPointF):
        """Start polygon selection."""
        if not self.is_active:
            self.is_active = True
            self.current_shape = PolygonShape()
        
        if self.current_shape:
            self.current_shape.add_point(point)
    
    def update_selection(self, point: QPointF):
        """Update polygon selection (preview next point)."""
        # For polygon, this could show a preview line to the next point
        pass
    
    def complete_selection(self) -> Optional[SelectionShape]:
        """Complete polygon selection."""
        if (self.is_active and self.current_shape and 
            len(self.current_shape.points) >= self.min_points):
            self.current_shape.close_polygon()
            shape = self.current_shape
            self.is_active = False
            self.current_shape = None
            return shape
        return None


class FreehandSelectionTool(SelectionTool):
    """Tool for creating freehand selections."""
    
    def start_selection(self, point: QPointF):
        """Start freehand selection."""
        self.is_active = True
        self.current_shape = FreehandShape()
        self.current_shape.add_point(point)
    
    def update_selection(self, point: QPointF):
        """Update freehand selection."""
        if self.is_active and self.current_shape:
            self.current_shape.add_point(point)
    
    def complete_selection(self) -> Optional[SelectionShape]:
        """Complete freehand selection."""
        if self.is_active and self.current_shape:
            shape = self.current_shape
            self.is_active = False
            self.current_shape = None
            return shape
        return None