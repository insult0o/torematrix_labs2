"""
Custom Shape Support for Document Viewer Overlay.
This module provides extensible custom shape rendering including
arrows, callouts, polygons, and bezier curves for enhanced visualization.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Tuple, Union

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QPainterPath, 
                        QPolygonF, QTransform, QLinearGradient, QRadialGradient)

from .coordinates import Point, Rectangle


class ShapeType(Enum):
    """Types of custom shapes."""
    ARROW = "arrow"
    CALLOUT = "callout"
    POLYGON = "polygon"
    BEZIER = "bezier"
    STAR = "star"
    HEART = "heart"
    BUBBLE = "bubble"
    ANNOTATION_BOX = "annotation_box"
    HIGHLIGHT_BAND = "highlight_band"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    BRACKET = "bracket"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    ROUNDED_RECT = "rounded_rect"


class ArrowStyle(Enum):
    """Arrow head styles."""
    SIMPLE = "simple"
    TRIANGLE = "triangle"
    FILLED = "filled"
    DIAMOND = "diamond"
    CIRCLE = "circle"
    SQUARE = "square"
    NONE = "none"


class CalloutStyle(Enum):
    """Callout bubble styles."""
    ROUNDED = "rounded"
    RECTANGULAR = "rectangular"
    CLOUD = "cloud"
    THOUGHT = "thought"
    SPEECH = "speech"


@dataclass
class ShapeStyle:
    """Style configuration for shapes."""
    fill_color: QColor = field(default_factory=lambda: QColor(255, 255, 255, 128))
    border_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 255))
    border_width: float = 1.0
    border_style: str = "solid"  # solid, dashed, dotted
    shadow_enabled: bool = False
    shadow_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 64))
    shadow_offset: Point = field(default_factory=lambda: Point(2, 2))
    shadow_blur: float = 4.0
    gradient_enabled: bool = False
    gradient_start_color: Optional[QColor] = None
    gradient_end_color: Optional[QColor] = None
    gradient_direction: str = "vertical"  # vertical, horizontal, radial
    opacity: float = 1.0


@dataclass
class ShapeParameters:
    """Base parameters for shape creation."""
    bounds: Rectangle
    style: ShapeStyle = field(default_factory=ShapeStyle)
    rotation: float = 0.0
    scale: Point = field(default_factory=lambda: Point(1.0, 1.0))
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArrowParameters(ShapeParameters):
    """Parameters for arrow shapes."""
    start_point: Point = field(default_factory=lambda: Point(0, 0))
    end_point: Point = field(default_factory=lambda: Point(100, 0))
    head_style: ArrowStyle = ArrowStyle.TRIANGLE
    head_size: float = 10.0
    tail_style: ArrowStyle = ArrowStyle.NONE
    tail_size: float = 5.0
    shaft_width: float = 2.0
    curved: bool = False
    curve_amount: float = 0.0  # Curvature for curved arrows


@dataclass
class CalloutParameters(ShapeParameters):
    """Parameters for callout shapes."""
    text: str = ""
    callout_style: CalloutStyle = CalloutStyle.ROUNDED
    pointer_position: Point = field(default_factory=lambda: Point(0, 0))
    pointer_length: float = 20.0
    corner_radius: float = 5.0
    padding: float = 10.0
    text_alignment: str = "center"  # left, center, right


@dataclass
class PolygonParameters(ShapeParameters):
    """Parameters for polygon shapes."""
    points: List[Point] = field(default_factory=list)
    closed: bool = True
    smooth: bool = False  # Use smooth curves between points


@dataclass
class BezierParameters(ShapeParameters):
    """Parameters for bezier curve shapes."""
    control_points: List[Point] = field(default_factory=list)
    closed: bool = False
    smooth: bool = True


class Shape(ABC):
    """Abstract base class for custom shapes."""
    
    def __init__(self, parameters: ShapeParameters):
        self.parameters = parameters
        self.cached_path: Optional[QPainterPath] = None
        self.cache_valid = False
    
    @abstractmethod
    def create_path(self) -> QPainterPath:
        """Create the QPainterPath for this shape."""
        pass
    
    def get_path(self) -> QPainterPath:
        """Get the shape path, using cache if valid."""
        if not self.cache_valid or self.cached_path is None:
            self.cached_path = self.create_path()
            self.cache_valid = True
        
        return self.cached_path
    
    def invalidate_cache(self) -> None:
        """Invalidate the cached path."""
        self.cache_valid = False
    
    def render(self, painter: QPainter) -> None:
        """Render the shape using the provided painter."""
        path = self.get_path()
        style = self.parameters.style
        
        # Apply transformations
        transform = QTransform()
        if self.parameters.rotation != 0:
            center = self.parameters.bounds.center()
            transform.translate(center.x, center.y)
            transform.rotate(self.parameters.rotation)
            transform.translate(-center.x, -center.y)
        
        if self.parameters.scale.x != 1.0 or self.parameters.scale.y != 1.0:
            transform.scale(self.parameters.scale.x, self.parameters.scale.y)
        
        painter.setTransform(transform, True)
        
        # Set opacity
        painter.setOpacity(style.opacity)
        
        # Render shadow if enabled
        if style.shadow_enabled:
            self._render_shadow(painter, path, style)
        
        # Set up brush (fill)
        brush = self._create_brush(style)
        painter.setBrush(brush)
        
        # Set up pen (border)
        pen = self._create_pen(style)
        painter.setPen(pen)
        
        # Draw the shape
        painter.drawPath(path)
        
        # Reset transform
        painter.resetTransform()
    
    def _render_shadow(self, painter: QPainter, path: QPainterPath, style: ShapeStyle) -> None:
        """Render shape shadow."""
        # Save current state
        painter.save()
        
        # Create shadow brush
        shadow_brush = QBrush(style.shadow_color)
        painter.setBrush(shadow_brush)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        
        # Translate for shadow offset
        painter.translate(style.shadow_offset.x, style.shadow_offset.y)
        
        # Draw shadow (simplified - real implementation would use blur)
        painter.drawPath(path)
        
        # Restore state
        painter.restore()
    
    def _create_brush(self, style: ShapeStyle) -> QBrush:
        """Create brush for shape fill."""
        if style.gradient_enabled and style.gradient_start_color and style.gradient_end_color:
            if style.gradient_direction == "radial":
                gradient = QRadialGradient(
                    self.parameters.bounds.center().x,
                    self.parameters.bounds.center().y,
                    min(self.parameters.bounds.width, self.parameters.bounds.height) / 2
                )
            else:
                gradient = QLinearGradient()
                if style.gradient_direction == "horizontal":
                    gradient.setStart(self.parameters.bounds.x, self.parameters.bounds.y)
                    gradient.setFinalStop(
                        self.parameters.bounds.x + self.parameters.bounds.width,
                        self.parameters.bounds.y
                    )
                else:  # vertical
                    gradient.setStart(self.parameters.bounds.x, self.parameters.bounds.y)
                    gradient.setFinalStop(
                        self.parameters.bounds.x,
                        self.parameters.bounds.y + self.parameters.bounds.height
                    )
            
            gradient.setColorAt(0.0, style.gradient_start_color)
            gradient.setColorAt(1.0, style.gradient_end_color)
            return QBrush(gradient)
        else:
            return QBrush(style.fill_color)
    
    def _create_pen(self, style: ShapeStyle) -> QPen:
        """Create pen for shape border."""
        pen = QPen(style.border_color)
        pen.setWidthF(style.border_width)
        
        if style.border_style == "dashed":
            pen.setStyle(QPen.Style.DashLine)
        elif style.border_style == "dotted":
            pen.setStyle(QPen.Style.DotLine)
        else:
            pen.setStyle(QPen.Style.SolidLine)
        
        return pen
    
    def update_parameters(self, parameters: ShapeParameters) -> None:
        """Update shape parameters and invalidate cache."""
        self.parameters = parameters
        self.invalidate_cache()
    
    def get_bounds(self) -> Rectangle:
        """Get the bounding rectangle of the shape."""
        path = self.get_path()
        rect = path.boundingRect()
        return Rectangle(rect.x(), rect.y(), rect.width(), rect.height())
    
    def contains_point(self, point: Point) -> bool:
        """Check if the shape contains the specified point."""
        path = self.get_path()
        return path.contains(QPointF(point.x, point.y))


class ArrowShape(Shape):
    """Arrow shape implementation."""
    
    def __init__(self, parameters: ArrowParameters):
        super().__init__(parameters)
    
    def create_path(self) -> QPainterPath:
        """Create arrow path."""
        params = self.parameters
        path = QPainterPath()
        
        if params.curved:
            return self._create_curved_arrow_path(params)
        else:
            return self._create_straight_arrow_path(params)
    
    def _create_straight_arrow_path(self, params: ArrowParameters) -> QPainterPath:
        """Create straight arrow path."""
        path = QPainterPath()
        
        start = QPointF(params.start_point.x, params.start_point.y)
        end = QPointF(params.end_point.x, params.end_point.y)
        
        # Calculate arrow direction
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        
        if length == 0:
            return path
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Perpendicular direction
        px = -dy
        py = dx
        
        # Arrow shaft
        shaft_half_width = params.shaft_width / 2
        
        # Calculate shaft points
        shaft_start_1 = QPointF(
            start.x() + px * shaft_half_width,
            start.y() + py * shaft_half_width
        )
        shaft_start_2 = QPointF(
            start.x() - px * shaft_half_width,
            start.y() - py * shaft_half_width
        )
        
        # Adjust end point for arrow head
        head_base_distance = params.head_size if params.head_style != ArrowStyle.NONE else 0
        shaft_end = QPointF(
            end.x() - dx * head_base_distance,
            end.y() - dy * head_base_distance
        )
        
        shaft_end_1 = QPointF(
            shaft_end.x() + px * shaft_half_width,
            shaft_end.y() + py * shaft_half_width
        )
        shaft_end_2 = QPointF(
            shaft_end.x() - px * shaft_half_width,
            shaft_end.y() - py * shaft_half_width
        )
        
        # Create shaft
        path.moveTo(shaft_start_1)
        path.lineTo(shaft_end_1)
        path.lineTo(shaft_end_2)
        path.lineTo(shaft_start_2)
        path.closeSubpath()
        
        # Add arrow head
        if params.head_style != ArrowStyle.NONE:
            head_path = self._create_arrow_head(end, dx, dy, px, py, params.head_style, params.head_size)
            path.addPath(head_path)
        
        # Add arrow tail
        if params.tail_style != ArrowStyle.NONE:
            tail_path = self._create_arrow_head(start, -dx, -dy, px, py, params.tail_style, params.tail_size)
            path.addPath(tail_path)
        
        return path
    
    def _create_curved_arrow_path(self, params: ArrowParameters) -> QPainterPath:
        """Create curved arrow path."""
        path = QPainterPath()
        
        start = QPointF(params.start_point.x, params.start_point.y)
        end = QPointF(params.end_point.x, params.end_point.y)
        
        # Calculate control point for curve
        mid_x = (start.x() + end.x()) / 2
        mid_y = (start.y() + end.y()) / 2
        
        # Perpendicular offset for curve
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        
        if length > 0:
            # Perpendicular direction
            px = -dy / length
            py = dx / length
            
            # Control point with curve amount
            curve_offset = params.curve_amount * length * 0.3
            control = QPointF(
                mid_x + px * curve_offset,
                mid_y + py * curve_offset
            )
            
            # Create curved path (simplified)
            path.moveTo(start)
            path.quadTo(control, end)
        
        return path
    
    def _create_arrow_head(self, tip: QPointF, dx: float, dy: float, 
                          px: float, py: float, style: ArrowStyle, size: float) -> QPainterPath:
        """Create arrow head path."""
        path = QPainterPath()
        
        if style == ArrowStyle.TRIANGLE or style == ArrowStyle.FILLED:
            # Triangle arrow head
            base_point = QPointF(tip.x() - dx * size, tip.y() - dy * size)
            left_point = QPointF(
                base_point.x() + px * size * 0.5,
                base_point.y() + py * size * 0.5
            )
            right_point = QPointF(
                base_point.x() - px * size * 0.5,
                base_point.y() - py * size * 0.5
            )
            
            path.moveTo(tip)
            path.lineTo(left_point)
            path.lineTo(right_point)
            path.closeSubpath()
        
        elif style == ArrowStyle.DIAMOND:
            # Diamond arrow head
            back_point = QPointF(tip.x() - dx * size, tip.y() - dy * size)
            left_point = QPointF(
                tip.x() - dx * size * 0.5 + px * size * 0.3,
                tip.y() - dy * size * 0.5 + py * size * 0.3
            )
            right_point = QPointF(
                tip.x() - dx * size * 0.5 - px * size * 0.3,
                tip.y() - dy * size * 0.5 - py * size * 0.3
            )
            
            path.moveTo(tip)
            path.lineTo(left_point)
            path.lineTo(back_point)
            path.lineTo(right_point)
            path.closeSubpath()
        
        elif style == ArrowStyle.CIRCLE:
            # Circle arrow head
            circle_center = QPointF(tip.x() - dx * size * 0.5, tip.y() - dy * size * 0.5)
            path.addEllipse(circle_center, size * 0.5, size * 0.5)
        
        return path


class CalloutShape(Shape):
    """Callout/speech bubble shape implementation."""
    
    def __init__(self, parameters: CalloutParameters):
        super().__init__(parameters)
    
    def create_path(self) -> QPainterPath:
        """Create callout path."""
        params = self.parameters
        path = QPainterPath()
        
        bounds = params.bounds
        
        if params.callout_style == CalloutStyle.ROUNDED:
            # Rounded rectangle callout
            main_rect = QRectF(
                bounds.x, bounds.y,
                bounds.width, bounds.height
            )
            path.addRoundedRect(main_rect, params.corner_radius, params.corner_radius)
            
            # Add pointer
            pointer_path = self._create_callout_pointer(params)
            path.addPath(pointer_path)
        
        elif params.callout_style == CalloutStyle.CLOUD:
            # Cloud-like callout
            path = self._create_cloud_shape(bounds, params.corner_radius)
        
        return path
    
    def _create_callout_pointer(self, params: CalloutParameters) -> QPainterPath:
        """Create callout pointer."""
        path = QPainterPath()
        
        bounds = params.bounds
        pointer_pos = params.pointer_position
        
        # Find closest edge of bounds to pointer position
        center_x = bounds.x + bounds.width / 2
        center_y = bounds.y + bounds.height / 2
        
        # Determine which edge to attach pointer to
        dx = pointer_pos.x - center_x
        dy = pointer_pos.y - center_y
        
        if abs(dx) > abs(dy):
            # Horizontal edge
            if dx > 0:
                # Right edge
                attach_point = Point(bounds.x + bounds.width, center_y)
            else:
                # Left edge
                attach_point = Point(bounds.x, center_y)
        else:
            # Vertical edge
            if dy > 0:
                # Bottom edge
                attach_point = Point(center_x, bounds.y + bounds.height)
            else:
                # Top edge
                attach_point = Point(center_x, bounds.y)
        
        # Create pointer triangle
        pointer_width = 10
        p1 = QPointF(attach_point.x - pointer_width/2, attach_point.y)
        p2 = QPointF(attach_point.x + pointer_width/2, attach_point.y)
        p3 = QPointF(pointer_pos.x, pointer_pos.y)
        
        path.moveTo(p1)
        path.lineTo(p2)
        path.lineTo(p3)
        path.closeSubpath()
        
        return path
    
    def _create_cloud_shape(self, bounds: Rectangle, radius: float) -> QPainterPath:
        """Create cloud-like shape."""
        path = QPainterPath()
        
        # Create multiple overlapping circles to form a cloud
        num_bubbles = 8
        bubble_radius = radius
        
        for i in range(num_bubbles):
            angle = (i / num_bubbles) * 2 * math.pi
            x = bounds.x + bounds.width/2 + math.cos(angle) * bubble_radius
            y = bounds.y + bounds.height/2 + math.sin(angle) * bubble_radius
            
            bubble_path = QPainterPath()
            bubble_path.addEllipse(
                QPointF(x, y),
                bubble_radius * 0.8,
                bubble_radius * 0.8
            )
            path = path.united(bubble_path)
        
        return path


class PolygonShape(Shape):
    """Polygon shape implementation."""
    
    def __init__(self, parameters: PolygonParameters):
        super().__init__(parameters)
    
    def create_path(self) -> QPainterPath:
        """Create polygon path."""
        params = self.parameters
        path = QPainterPath()
        
        if not params.points:
            return path
        
        # Convert points to QPointF
        qt_points = [QPointF(p.x, p.y) for p in params.points]
        
        if params.smooth:
            # Create smooth curves between points
            path = self._create_smooth_polygon(qt_points, params.closed)
        else:
            # Create straight line polygon
            polygon = QPolygonF(qt_points)
            path.addPolygon(polygon)
            
            if params.closed:
                path.closeSubpath()
        
        return path
    
    def _create_smooth_polygon(self, points: List[QPointF], closed: bool) -> QPainterPath:
        """Create smooth polygon with curves."""
        path = QPainterPath()
        
        if len(points) < 2:
            return path
        
        if len(points) == 2:
            path.moveTo(points[0])
            path.lineTo(points[1])
            return path
        
        # Calculate control points for smooth curves
        path.moveTo(points[0])
        
        for i in range(1, len(points)):
            if i == len(points) - 1 and not closed:
                path.lineTo(points[i])
            else:
                # Calculate control points
                prev_point = points[i - 1] if i > 0 else points[-1]
                current_point = points[i]
                next_point = points[(i + 1) % len(points)]
                
                # Simple curve control point calculation
                control_point = QPointF(
                    (prev_point.x() + current_point.x()) / 2,
                    (prev_point.y() + current_point.y()) / 2
                )
                
                path.quadTo(control_point, current_point)
        
        if closed:
            path.closeSubpath()
        
        return path


class BezierShape(Shape):
    """Bezier curve shape implementation."""
    
    def __init__(self, parameters: BezierParameters):
        super().__init__(parameters)
    
    def create_path(self) -> QPainterPath:
        """Create bezier curve path."""
        params = self.parameters
        path = QPainterPath()
        
        if len(params.control_points) < 2:
            return path
        
        # Convert to QPointF
        qt_points = [QPointF(p.x, p.y) for p in params.control_points]
        
        # Start path
        path.moveTo(qt_points[0])
        
        # Create bezier curves
        if len(qt_points) == 3:
            # Quadratic bezier
            path.quadTo(qt_points[1], qt_points[2])
        elif len(qt_points) == 4:
            # Cubic bezier
            path.cubicTo(qt_points[1], qt_points[2], qt_points[3])
        else:
            # Multiple segments
            i = 1
            while i < len(qt_points):
                if i + 2 < len(qt_points):
                    # Cubic bezier
                    path.cubicTo(qt_points[i], qt_points[i + 1], qt_points[i + 2])
                    i += 3
                elif i + 1 < len(qt_points):
                    # Quadratic bezier
                    path.quadTo(qt_points[i], qt_points[i + 1])
                    i += 2
                else:
                    # Line to last point
                    path.lineTo(qt_points[i])
                    i += 1
        
        if params.closed:
            path.closeSubpath()
        
        return path


class ShapeFactory:
    """Factory for creating shapes."""
    
    def __init__(self):
        self.shape_classes: Dict[ShapeType, type] = {
            ShapeType.ARROW: ArrowShape,
            ShapeType.CALLOUT: CalloutShape,
            ShapeType.POLYGON: PolygonShape,
            ShapeType.BEZIER: BezierShape,
        }
    
    def create_shape(self, shape_type: ShapeType, parameters: ShapeParameters) -> Shape:
        """Create a shape of the specified type."""
        shape_class = self.shape_classes.get(shape_type)
        if not shape_class:
            raise ValueError(f"Unknown shape type: {shape_type}")
        
        return shape_class(parameters)
    
    def register_shape_class(self, shape_type: ShapeType, shape_class: type) -> None:
        """Register a custom shape class."""
        self.shape_classes[shape_type] = shape_class
    
    def create_arrow(self, start: Point, end: Point, style: Optional[ShapeStyle] = None) -> ArrowShape:
        """Convenience method to create an arrow."""
        if not style:
            style = ShapeStyle()
        
        params = ArrowParameters(
            bounds=Rectangle(
                min(start.x, end.x), min(start.y, end.y),
                abs(end.x - start.x), abs(end.y - start.y)
            ),
            style=style,
            start_point=start,
            end_point=end
        )
        
        return ArrowShape(params)
    
    def create_callout(self, bounds: Rectangle, pointer_pos: Point, 
                      text: str = "", style: Optional[ShapeStyle] = None) -> CalloutShape:
        """Convenience method to create a callout."""
        if not style:
            style = ShapeStyle()
        
        params = CalloutParameters(
            bounds=bounds,
            style=style,
            text=text,
            pointer_position=pointer_pos
        )
        
        return CalloutShape(params)
    
    def create_polygon(self, points: List[Point], closed: bool = True,
                      style: Optional[ShapeStyle] = None) -> PolygonShape:
        """Convenience method to create a polygon."""
        if not style:
            style = ShapeStyle()
        
        # Calculate bounds
        if points:
            min_x = min(p.x for p in points)
            max_x = max(p.x for p in points)
            min_y = min(p.y for p in points)
            max_y = max(p.y for p in points)
            bounds = Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
        else:
            bounds = Rectangle(0, 0, 0, 0)
        
        params = PolygonParameters(
            bounds=bounds,
            style=style,
            points=points,
            closed=closed
        )
        
        return PolygonShape(params)


class CustomShapeRenderer:
    """Renderer for custom shapes in the overlay system."""
    
    def __init__(self, overlay_engine: Optional[Any] = None):
        self.overlay_engine = overlay_engine
        self.shape_factory = ShapeFactory()
        self.rendered_shapes: Dict[str, Shape] = {}
    
    def render_shape(self, shape: Shape, painter: QPainter) -> None:
        """Render a shape using the provided painter."""
        shape.render(painter)
    
    def render_arrow(self, painter: QPainter, start: Point, end: Point,
                    style: Optional[ShapeStyle] = None) -> None:
        """Render an arrow shape."""
        arrow = self.shape_factory.create_arrow(start, end, style)
        self.render_shape(arrow, painter)
    
    def render_callout(self, painter: QPainter, bounds: Rectangle, 
                      pointer_pos: Point, text: str = "",
                      style: Optional[ShapeStyle] = None) -> None:
        """Render a callout shape."""
        callout = self.shape_factory.create_callout(bounds, pointer_pos, text, style)
        self.render_shape(callout, painter)
    
    def render_polygon(self, painter: QPainter, points: List[Point],
                      closed: bool = True, style: Optional[ShapeStyle] = None) -> None:
        """Render a polygon shape."""
        polygon = self.shape_factory.create_polygon(points, closed, style)
        self.render_shape(polygon, painter)
    
    def add_persistent_shape(self, shape_id: str, shape: Shape) -> None:
        """Add a shape that persists until explicitly removed."""
        self.rendered_shapes[shape_id] = shape
    
    def remove_persistent_shape(self, shape_id: str) -> bool:
        """Remove a persistent shape."""
        if shape_id in self.rendered_shapes:
            del self.rendered_shapes[shape_id]
            return True
        return False
    
    def render_all_persistent_shapes(self, painter: QPainter) -> None:
        """Render all persistent shapes."""
        for shape in self.rendered_shapes.values():
            self.render_shape(shape, painter)
    
    def get_persistent_shape(self, shape_id: str) -> Optional[Shape]:
        """Get a persistent shape by ID."""
        return self.rendered_shapes.get(shape_id)
    
    def clear_persistent_shapes(self) -> None:
        """Clear all persistent shapes."""
        self.rendered_shapes.clear()
    
    def register_custom_shape(self, shape_type: ShapeType, shape_class: type) -> None:
        """Register a custom shape class."""
        self.shape_factory.register_shape_class(shape_type, shape_class)


# Utility functions for shape creation
def create_annotation_arrow(start: Point, end: Point, color: QColor = QColor(255, 0, 0)) -> ArrowShape:
    """Create an annotation arrow with default styling."""
    style = ShapeStyle(
        fill_color=color,
        border_color=color,
        border_width=2.0
    )
    
    factory = ShapeFactory()
    return factory.create_arrow(start, end, style)


def create_highlight_band(bounds: Rectangle, color: QColor = QColor(255, 255, 0, 100)) -> PolygonShape:
    """Create a highlight band rectangle."""
    style = ShapeStyle(
        fill_color=color,
        border_color=QColor(255, 255, 0, 200),
        border_width=1.0
    )
    
    # Create rectangle as polygon
    points = [
        Point(bounds.x, bounds.y),
        Point(bounds.x + bounds.width, bounds.y),
        Point(bounds.x + bounds.width, bounds.y + bounds.height),
        Point(bounds.x, bounds.y + bounds.height)
    ]
    
    factory = ShapeFactory()
    return factory.create_polygon(points, True, style)


class ShapeMixin:
    """Mixin to add shape support to any object."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_renderer: Optional[CustomShapeRenderer] = None
    
    def set_shape_renderer(self, renderer: CustomShapeRenderer) -> None:
        """Set the shape renderer."""
        self.shape_renderer = renderer
    
    def add_shape(self, shape_id: str, shape: Shape) -> None:
        """Add a shape to this object."""
        if self.shape_renderer:
            self.shape_renderer.add_persistent_shape(shape_id, shape)
    
    def remove_shape(self, shape_id: str) -> bool:
        """Remove a shape from this object."""
        if self.shape_renderer:
            return self.shape_renderer.remove_persistent_shape(shape_id)
        return False