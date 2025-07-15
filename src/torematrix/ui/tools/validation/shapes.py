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