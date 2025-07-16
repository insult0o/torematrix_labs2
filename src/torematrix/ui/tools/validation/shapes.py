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
from PyQt6.QtCore import QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QPainterPath
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


@dataclass
class SelectionHandle:
    """Handle for resizing selections."""
    position: QPointF
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
    
    top_left: QPointF
    bottom_right: QPointF
    
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
        # Corner handles
        if index == 0:  # Top-left
            self.top_left = new_pos
        elif index == 1:  # Top-right
            self.top_left = QPointF(self.top_left.x(), new_pos.y())
            self.bottom_right = QPointF(new_pos.x(), self.bottom_right.y())
        elif index == 2:  # Bottom-right
            self.bottom_right = new_pos
        elif index == 3:  # Bottom-left
            self.bottom_right = QPointF(self.bottom_right.x(), new_pos.y())
            self.top_left = QPointF(new_pos.x(), self.top_left.y())
        # Edge handles
        elif index == 4:  # Top
            self.top_left = QPointF(self.top_left.x(), new_pos.y())
        elif index == 5:  # Right
            self.bottom_right = QPointF(new_pos.x(), self.bottom_right.y())
        elif index == 6:  # Bottom
            self.bottom_right = QPointF(self.bottom_right.x(), new_pos.y())
        elif index == 7:  # Left
            self.top_left = QPointF(new_pos.x(), self.top_left.y())
    
    def translate(self, offset: QPointF):
        """Translate the rectangle."""
        self.top_left = QPointF(self.top_left.x() + offset.x(), self.top_left.y() + offset.y())
        self.bottom_right = QPointF(self.bottom_right.x() + offset.x(), self.bottom_right.y() + offset.y())
    
    def to_path(self) -> QPainterPath:
        """Convert to painter path."""
        path = QPainterPath()
        path.addRect(self.get_bounding_rect())
        return path


@dataclass
class PolygonShape(SelectionShape):
    """Polygon selection shape."""
    
    points: List[QPointF]
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
        self.points = [QPointF(p.x() + offset.x(), p.y() + offset.y()) for p in self.points]
    
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


@dataclass
class FreehandShape(SelectionShape):
    """Freehand selection shape."""
    
    stroke_points: List[QPointF]
    smoothed_path: Optional[QPainterPath] = None
    
    def draw(self, painter: QPainter):
        """Draw the freehand shape."""
        if len(self.stroke_points) < 2:
            return
        
        # Use smoothed path if available, otherwise raw points
        if self.smoothed_path:
            painter.drawPath(self.smoothed_path)
        else:
            # Draw raw stroke
            path = QPainterPath()
            path.moveTo(self.stroke_points[0])
            for point in self.stroke_points[1:]:
                path.lineTo(point)
            painter.drawPath(path)
    
    def get_bounding_rect(self) -> QRectF:
        """Get the bounding rectangle."""
        if not self.stroke_points:
            return QRectF()
        
        if self.smoothed_path:
            return self.smoothed_path.boundingRect()
        
        # Calculate bounds from stroke points
        min_x = min(p.x() for p in self.stroke_points)
        max_x = max(p.x() for p in self.stroke_points)
        min_y = min(p.y() for p in self.stroke_points)
        max_y = max(p.y() for p in self.stroke_points)
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the shape."""
        if self.smoothed_path:
            return self.smoothed_path.contains(point)
        
        # Simple containment check for raw points
        return self.get_bounding_rect().contains(point)
    
    def get_handles(self) -> List[QPointF]:
        """Get control points for manipulation."""
        # Return every Nth point to avoid too many handles
        if len(self.stroke_points) <= 10:
            return self.stroke_points.copy()
        
        step = len(self.stroke_points) // 10
        return self.stroke_points[::step]
    
    def move_handle(self, index: int, new_pos: QPointF):
        """Move a control point."""
        if 0 <= index < len(self.stroke_points):
            self.stroke_points[index] = new_pos
            # Invalidate smoothed path
            self.smoothed_path = None
    
    def translate(self, offset: QPointF):
        """Translate the shape."""
        self.stroke_points = [QPointF(p.x() + offset.x(), p.y() + offset.y()) for p in self.stroke_points]
        # Invalidate smoothed path
        self.smoothed_path = None
    
    def to_path(self) -> QPainterPath:
        """Convert to painter path."""
        if self.smoothed_path:
            return self.smoothed_path
        
        path = QPainterPath()
        if len(self.stroke_points) < 2:
            return path
        
        path.moveTo(self.stroke_points[0])
        for point in self.stroke_points[1:]:
            path.lineTo(point)
        
        return path
    
    def smooth_stroke(self):
        """Apply smoothing to the stroke."""
        if len(self.stroke_points) < 3:
            return
        
        # Create smoothed path using quadratic bezier curves
        self.smoothed_path = QPainterPath()
        self.smoothed_path.moveTo(self.stroke_points[0])
        
        for i in range(1, len(self.stroke_points) - 1):
            # Use current point as control point and midpoint as end point
            control_point = self.stroke_points[i]
            end_point = QPointF(
                (self.stroke_points[i].x() + self.stroke_points[i + 1].x()) / 2,
                (self.stroke_points[i].y() + self.stroke_points[i + 1].y()) / 2
            )
            self.smoothed_path.quadTo(control_point, end_point)
        
        # Connect to final point
        self.smoothed_path.lineTo(self.stroke_points[-1])
        
        # Close the path for filled shapes
        self.smoothed_path.closeSubpath()


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
    def finish_selection(self) -> Optional[SelectionShape]:
        """Finish and return the selection."""
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
    
    def finish_selection(self) -> Optional[RectangleShape]:
        """Finish the rectangle selection."""
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
    
    def finish_selection(self) -> Optional[PolygonShape]:
        """Finish the polygon selection."""
        if self.is_active and self.current_shape and len(self.current_shape.points) >= 3:
            shape = self.current_shape
            shape.closed = True
            self.is_active = False
            self.current_shape = None
            self.temp_point = None
            return shape
        return None


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
            self.current_shape.stroke_points.append(point)
    
    def finish_selection(self) -> Optional[FreehandShape]:
        """Finish the freehand selection."""
        if self.is_active and self.current_shape and len(self.current_shape.stroke_points) >= 3:
            shape = self.current_shape
            shape.smooth_stroke()  # Apply smoothing
            self.is_active = False
            self.current_shape = None
            return shape
        return None