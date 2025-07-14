"""
Renderer Backend System for Document Viewer Overlay.
This module provides Canvas and SVG renderer implementations for the overlay system,
with support for efficient drawing primitives and performance optimization.
"""
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PyQt6.QtCore import QRectF, QPointF, QSizeF, Qt
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient,
    QFont, QFontMetrics, QPolygonF, QPainterPath, QPixmap, QImage
)
from PyQt6.QtWidgets import QWidget
from PyQt6.QtSvg import QSvgGenerator

from .coordinates import Rectangle, Point


class RenderPrimitive(Enum):
    """Supported rendering primitives."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"
    LINE = "line"
    TEXT = "text"
    PATH = "path"


@dataclass
class RenderStyle:
    """Style configuration for rendering operations."""
    # Colors
    fill_color: Optional[QColor] = None
    stroke_color: Optional[QColor] = None
    background_color: Optional[QColor] = None
    
    # Stroke properties
    stroke_width: float = 1.0
    stroke_style: Qt.PenStyle = Qt.PenStyle.SolidLine
    stroke_cap: Qt.PenCapStyle = Qt.PenCapStyle.RoundCap
    stroke_join: Qt.PenJoinStyle = Qt.PenJoinStyle.RoundJoin
    
    # Fill properties
    fill_style: Qt.BrushStyle = Qt.BrushStyle.SolidPattern
    gradient: Optional[Union[QLinearGradient, QRadialGradient]] = None
    
    # Text properties
    font: Optional[QFont] = None
    font_size: float = 12.0
    font_weight: int = 400
    font_style: str = "normal"
    text_align: str = "left"
    
    # Visual effects
    opacity: float = 1.0
    blend_mode: Qt.CompositionMode = Qt.CompositionMode.CompositionMode_SourceOver
    shadow_offset: Tuple[float, float] = (0, 0)
    shadow_color: Optional[QColor] = None
    shadow_blur: float = 0.0
    
    # Transformation
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    
    @classmethod
    def default(cls) -> RenderStyle:
        """Create default style."""
        return cls(
            fill_color=QColor(0, 0, 0, 255),
            stroke_color=QColor(0, 0, 0, 255),
            font=QFont("Arial", 12)
        )


class RendererBackend(ABC):
    """Abstract base class for renderer backends."""
    
    def __init__(self, target_widget: QWidget):
        self.target_widget = target_widget
        self.current_context = None
        self.rendering_active = False
        self.performance_metrics = {
            'primitive_count': 0,
            'render_time': 0.0,
            'memory_usage': 0
        }
    
    @abstractmethod
    def begin_render(self, context) -> None:
        """Begin a rendering session."""
        pass
    
    @abstractmethod
    def end_render(self) -> None:
        """End a rendering session."""
        pass
    
    @abstractmethod
    def render_rectangle(self, bounds: Rectangle, style: RenderStyle) -> None:
        """Render a rectangle."""
        pass
    
    @abstractmethod
    def render_circle(self, center: Point, radius: float, style: RenderStyle) -> None:
        """Render a circle."""
        pass
    
    @abstractmethod
    def render_polygon(self, points: List[Point], style: RenderStyle) -> None:
        """Render a polygon."""
        pass
    
    @abstractmethod
    def render_line(self, start: Point, end: Point, style: RenderStyle) -> None:
        """Render a line."""
        pass
    
    @abstractmethod
    def render_text(self, text: str, position: Point, style: RenderStyle) -> None:
        """Render text."""
        pass
    
    @abstractmethod
    def render_path(self, path_data: str, style: RenderStyle) -> None:
        """Render a path (SVG path syntax)."""
        pass
    
    @abstractmethod
    def render_element(self, element, bounds: Rectangle, style: Dict[str, Any], context) -> None:
        """Render a generic element."""
        pass
    
    @abstractmethod
    def clear_region(self, bounds: Rectangle) -> None:
        """Clear a rectangular region."""
        pass
    
    @abstractmethod
    def save_state(self) -> None:
        """Save current rendering state."""
        pass
    
    @abstractmethod
    def restore_state(self) -> None:
        """Restore previous rendering state."""
        pass
    
    @abstractmethod
    def set_clip_region(self, bounds: Rectangle) -> None:
        """Set clipping region."""
        pass
    
    @abstractmethod
    def clear_clip_region(self) -> None:
        """Clear clipping region."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.performance_metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.performance_metrics = {
            'primitive_count': 0,
            'render_time': 0.0,
            'memory_usage': 0
        }


class CanvasRenderer(RendererBackend):
    """Canvas-based renderer using QPainter for high-performance rendering."""
    
    def __init__(self, target_widget: QWidget):
        super().__init__(target_widget)
        self.painter: Optional[QPainter] = None
        self.paint_device: Optional[Union[QWidget, QPixmap]] = None
        self.state_stack: List[Dict[str, Any]] = []
        self.use_double_buffering = True
        self.buffer_pixmap: Optional[QPixmap] = None
        
    def begin_render(self, context) -> None:
        """Begin canvas rendering session."""
        if self.rendering_active:
            return
        
        self.rendering_active = True
        self.current_context = context
        self.reset_metrics()
        
        # Setup paint device
        if self.use_double_buffering:
            # Create or resize buffer
            widget_size = self.target_widget.size()
            if (not self.buffer_pixmap or 
                self.buffer_pixmap.size() != widget_size):
                self.buffer_pixmap = QPixmap(widget_size)
                self.buffer_pixmap.fill(Qt.GlobalColor.transparent)
            
            self.paint_device = self.buffer_pixmap
        else:
            self.paint_device = self.target_widget
        
        # Initialize painter
        self.painter = QPainter(self.paint_device)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # Clear background if needed
        if hasattr(context, 'clear_background') and context.clear_background:
            self.painter.fillRect(self.target_widget.rect(), Qt.GlobalColor.transparent)
        
        start_time = time.time()
        self.performance_metrics['render_start'] = start_time
    
    def end_render(self) -> None:
        """End canvas rendering session."""
        if not self.rendering_active:
            return
        
        # Finalize painting
        if self.painter:
            self.painter.end()
            self.painter = None
        
        # Copy buffer to widget if double buffering
        if self.use_double_buffering and self.buffer_pixmap:
            widget_painter = QPainter(self.target_widget)
            widget_painter.drawPixmap(0, 0, self.buffer_pixmap)
            widget_painter.end()
        
        # Update metrics
        end_time = time.time()
        if 'render_start' in self.performance_metrics:
            self.performance_metrics['render_time'] = end_time - self.performance_metrics['render_start']
        
        self.rendering_active = False
        self.current_context = None
    
    def render_rectangle(self, bounds: Rectangle, style: RenderStyle) -> None:
        """Render a rectangle using QPainter."""
        if not self.painter:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Convert to Qt rectangle
        rect = QRectF(bounds.x, bounds.y, bounds.width, bounds.height)
        
        # Apply style
        self._apply_style(style)
        
        # Apply transformations
        self._apply_transformations(style, bounds.center)
        
        # Draw rectangle
        if style.fill_color:
            self.painter.fillRect(rect, style.fill_color)
        
        if style.stroke_color and style.stroke_width > 0:
            self.painter.drawRect(rect)
    
    def render_circle(self, center: Point, radius: float, style: RenderStyle) -> None:
        """Render a circle using QPainter."""
        if not self.painter:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Convert to Qt rectangle for ellipse
        rect = QRectF(center.x - radius, center.y - radius, radius * 2, radius * 2)
        
        # Apply style
        self._apply_style(style)
        
        # Apply transformations
        self._apply_transformations(style, center)
        
        # Draw circle
        if style.fill_color:
            self.painter.setBrush(QBrush(style.fill_color))
        else:
            self.painter.setBrush(Qt.BrushStyle.NoBrush)
        
        self.painter.drawEllipse(rect)
    
    def render_polygon(self, points: List[Point], style: RenderStyle) -> None:
        """Render a polygon using QPainter."""
        if not self.painter or len(points) < 3:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Convert to Qt polygon
        qt_points = [QPointF(p.x, p.y) for p in points]
        polygon = QPolygonF(qt_points)
        
        # Apply style
        self._apply_style(style)
        
        # Calculate center for transformations
        center = Point(
            sum(p.x for p in points) / len(points),
            sum(p.y for p in points) / len(points)
        )
        self._apply_transformations(style, center)
        
        # Draw polygon
        if style.fill_color:
            self.painter.setBrush(QBrush(style.fill_color))
        else:
            self.painter.setBrush(Qt.BrushStyle.NoBrush)
        
        self.painter.drawPolygon(polygon)
    
    def render_line(self, start: Point, end: Point, style: RenderStyle) -> None:
        """Render a line using QPainter."""
        if not self.painter:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Apply style
        self._apply_style(style)
        
        # Draw line
        self.painter.drawLine(QPointF(start.x, start.y), QPointF(end.x, end.y))
    
    def render_text(self, text: str, position: Point, style: RenderStyle) -> None:
        """Render text using QPainter."""
        if not self.painter:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Apply text style
        if style.font:
            self.painter.setFont(style.font)
        else:
            font = QFont("Arial", int(style.font_size))
            font.setWeight(style.font_weight)
            self.painter.setFont(font)
        
        # Set text color
        if style.fill_color:
            self.painter.setPen(QPen(style.fill_color))
        
        # Apply opacity
        if style.opacity < 1.0:
            self.painter.setOpacity(style.opacity)
        
        # Calculate text bounds for alignment
        font_metrics = QFontMetrics(self.painter.font())
        text_rect = font_metrics.boundingRect(text)
        
        # Adjust position based on alignment
        draw_pos = QPointF(position.x, position.y)
        if style.text_align == "center":
            draw_pos.setX(position.x - text_rect.width() / 2)
        elif style.text_align == "right":
            draw_pos.setX(position.x - text_rect.width())
        
        # Draw text
        self.painter.drawText(draw_pos, text)
    
    def render_path(self, path_data: str, style: RenderStyle) -> None:
        """Render a path using QPainter."""
        if not self.painter:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Convert SVG path to QPainterPath
        path = self._svg_path_to_qt_path(path_data)
        
        # Apply style
        self._apply_style(style)
        
        # Draw path
        if style.fill_color:
            self.painter.fillPath(path, QBrush(style.fill_color))
        
        if style.stroke_color and style.stroke_width > 0:
            self.painter.strokePath(path, QPen(style.stroke_color, style.stroke_width))
    
    def render_element(self, element, bounds: Rectangle, style: Dict[str, Any], context) -> None:
        """Render a generic element."""
        if not self.painter:
            return
        
        # Convert style dict to RenderStyle
        render_style = self._dict_to_render_style(style)
        
        # Default to rectangle rendering
        self.render_rectangle(bounds, render_style)
    
    def clear_region(self, bounds: Rectangle) -> None:
        """Clear a rectangular region."""
        if not self.painter:
            return
        
        rect = QRectF(bounds.x, bounds.y, bounds.width, bounds.height)
        self.painter.fillRect(rect, Qt.GlobalColor.transparent)
    
    def save_state(self) -> None:
        """Save current rendering state."""
        if self.painter:
            self.painter.save()
    
    def restore_state(self) -> None:
        """Restore previous rendering state."""
        if self.painter:
            self.painter.restore()
    
    def set_clip_region(self, bounds: Rectangle) -> None:
        """Set clipping region."""
        if self.painter:
            rect = QRectF(bounds.x, bounds.y, bounds.width, bounds.height)
            self.painter.setClipRect(rect)
    
    def clear_clip_region(self) -> None:
        """Clear clipping region."""
        if self.painter:
            self.painter.setClipping(False)
    
    def cleanup(self) -> None:
        """Clean up canvas resources."""
        if self.painter:
            self.painter.end()
            self.painter = None
        
        self.buffer_pixmap = None
        self.paint_device = None
        self.state_stack.clear()
    
    def _apply_style(self, style: RenderStyle) -> None:
        """Apply rendering style to painter."""
        if not self.painter:
            return
        
        # Set pen for stroke
        if style.stroke_color and style.stroke_width > 0:
            pen = QPen(style.stroke_color, style.stroke_width)
            pen.setStyle(style.stroke_style)
            pen.setCapStyle(style.stroke_cap)
            pen.setJoinStyle(style.stroke_join)
            self.painter.setPen(pen)
        else:
            self.painter.setPen(Qt.PenStyle.NoPen)
        
        # Set brush for fill
        if style.fill_color:
            if style.gradient:
                brush = QBrush(style.gradient)
            else:
                brush = QBrush(style.fill_color, style.fill_style)
            self.painter.setBrush(brush)
        else:
            self.painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Set opacity
        if style.opacity < 1.0:
            self.painter.setOpacity(style.opacity)
        
        # Set composition mode
        self.painter.setCompositionMode(style.blend_mode)
    
    def _apply_transformations(self, style: RenderStyle, center: Point) -> None:
        """Apply transformations to painter."""
        if not self.painter:
            return
        
        # Apply rotation
        if style.rotation != 0:
            self.painter.translate(center.x, center.y)
            self.painter.rotate(math.degrees(style.rotation))
            self.painter.translate(-center.x, -center.y)
        
        # Apply scaling
        if style.scale_x != 1.0 or style.scale_y != 1.0:
            self.painter.translate(center.x, center.y)
            self.painter.scale(style.scale_x, style.scale_y)
            self.painter.translate(-center.x, -center.y)
    
    def _svg_path_to_qt_path(self, path_data: str) -> QPainterPath:
        """Convert SVG path data to QPainterPath."""
        # This is a simplified implementation
        # In practice, you'd need a full SVG path parser
        path = QPainterPath()
        
        # Basic implementation for simple paths
        commands = path_data.split()
        i = 0
        current_pos = QPointF(0, 0)
        
        while i < len(commands):
            command = commands[i]
            
            if command == 'M':  # MoveTo
                x, y = float(commands[i + 1]), float(commands[i + 2])
                current_pos = QPointF(x, y)
                path.moveTo(current_pos)
                i += 3
            elif command == 'L':  # LineTo
                x, y = float(commands[i + 1]), float(commands[i + 2])
                current_pos = QPointF(x, y)
                path.lineTo(current_pos)
                i += 3
            elif command == 'Z':  # ClosePath
                path.closeSubpath()
                i += 1
            else:
                i += 1
        
        return path
    
    def _dict_to_render_style(self, style_dict: Dict[str, Any]) -> RenderStyle:
        """Convert style dictionary to RenderStyle."""
        style = RenderStyle.default()
        
        # Map common style properties
        if 'fill_color' in style_dict:
            style.fill_color = QColor(style_dict['fill_color'])
        if 'stroke_color' in style_dict:
            style.stroke_color = QColor(style_dict['stroke_color'])
        if 'stroke_width' in style_dict:
            style.stroke_width = float(style_dict['stroke_width'])
        if 'opacity' in style_dict:
            style.opacity = float(style_dict['opacity'])
        
        return style


class SVGRenderer(RendererBackend):
    """SVG-based renderer for scalable vector graphics output."""
    
    def __init__(self, target_widget: QWidget):
        super().__init__(target_widget)
        self.svg_generator: Optional[QSvgGenerator] = None
        self.painter: Optional[QPainter] = None
        self.svg_elements: List[str] = []
        self.current_id = 0
        
    def begin_render(self, context) -> None:
        """Begin SVG rendering session."""
        if self.rendering_active:
            return
        
        self.rendering_active = True
        self.current_context = context
        self.reset_metrics()
        
        # Setup SVG generator
        self.svg_generator = QSvgGenerator()
        self.svg_generator.setSize(self.target_widget.size())
        self.svg_generator.setViewBox(self.target_widget.rect())
        
        # Create temporary file or in-memory buffer
        # For now, we'll collect SVG elements
        self.svg_elements = []
        self.current_id = 0
        
        start_time = time.time()
        self.performance_metrics['render_start'] = start_time
    
    def end_render(self) -> None:
        """End SVG rendering session."""
        if not self.rendering_active:
            return
        
        # Generate complete SVG
        svg_content = self._generate_svg_content()
        
        # For now, we'll just store the SVG content
        # In practice, you'd render it to the widget or save to file
        
        # Update metrics
        end_time = time.time()
        if 'render_start' in self.performance_metrics:
            self.performance_metrics['render_time'] = end_time - self.performance_metrics['render_start']
        
        self.rendering_active = False
        self.current_context = None
        self.svg_generator = None
    
    def render_rectangle(self, bounds: Rectangle, style: RenderStyle) -> None:
        """Render a rectangle as SVG."""
        if not self.rendering_active:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate SVG rectangle element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<rect x="{bounds.x}" y="{bounds.y}" '
            f'width="{bounds.width}" height="{bounds.height}" '
            f'style="{svg_style}" id="rect_{self.current_id}"/>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_circle(self, center: Point, radius: float, style: RenderStyle) -> None:
        """Render a circle as SVG."""
        if not self.rendering_active:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate SVG circle element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<circle cx="{center.x}" cy="{center.y}" r="{radius}" '
            f'style="{svg_style}" id="circle_{self.current_id}"/>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_polygon(self, points: List[Point], style: RenderStyle) -> None:
        """Render a polygon as SVG."""
        if not self.rendering_active or len(points) < 3:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate points string
        points_str = " ".join(f"{p.x},{p.y}" for p in points)
        
        # Generate SVG polygon element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<polygon points="{points_str}" '
            f'style="{svg_style}" id="polygon_{self.current_id}"/>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_line(self, start: Point, end: Point, style: RenderStyle) -> None:
        """Render a line as SVG."""
        if not self.rendering_active:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate SVG line element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<line x1="{start.x}" y1="{start.y}" x2="{end.x}" y2="{end.y}" '
            f'style="{svg_style}" id="line_{self.current_id}"/>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_text(self, text: str, position: Point, style: RenderStyle) -> None:
        """Render text as SVG."""
        if not self.rendering_active:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate SVG text element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<text x="{position.x}" y="{position.y}" '
            f'style="{svg_style}" id="text_{self.current_id}">{text}</text>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_path(self, path_data: str, style: RenderStyle) -> None:
        """Render a path as SVG."""
        if not self.rendering_active:
            return
        
        self.performance_metrics['primitive_count'] += 1
        
        # Generate SVG path element
        svg_style = self._render_style_to_svg_style(style)
        svg_element = (
            f'<path d="{path_data}" '
            f'style="{svg_style}" id="path_{self.current_id}"/>'
        )
        
        self.svg_elements.append(svg_element)
        self.current_id += 1
    
    def render_element(self, element, bounds: Rectangle, style: Dict[str, Any], context) -> None:
        """Render a generic element as SVG."""
        if not self.rendering_active:
            return
        
        # Convert style dict to RenderStyle
        render_style = self._dict_to_render_style(style)
        
        # Default to rectangle rendering
        self.render_rectangle(bounds, render_style)
    
    def clear_region(self, bounds: Rectangle) -> None:
        """Clear a rectangular region (SVG doesn't support this directly)."""
        # SVG doesn't have a direct clear operation
        # We could add a white rectangle or use masking
        pass
    
    def save_state(self) -> None:
        """Save current rendering state."""
        # Add SVG group start
        self.svg_elements.append(f'<g id="group_{self.current_id}">')
        self.current_id += 1
    
    def restore_state(self) -> None:
        """Restore previous rendering state."""
        # Add SVG group end
        self.svg_elements.append('</g>')
    
    def set_clip_region(self, bounds: Rectangle) -> None:
        """Set clipping region using SVG clipPath."""
        clip_id = f"clip_{self.current_id}"
        self.current_id += 1
        
        # Define clip path
        clip_def = (
            f'<defs><clipPath id="{clip_id}">'
            f'<rect x="{bounds.x}" y="{bounds.y}" '
            f'width="{bounds.width}" height="{bounds.height}"/>'
            f'</clipPath></defs>'
        )
        
        self.svg_elements.append(clip_def)
        self.svg_elements.append(f'<g clip-path="url(#{clip_id})">')
    
    def clear_clip_region(self) -> None:
        """Clear clipping region."""
        self.svg_elements.append('</g>')
    
    def cleanup(self) -> None:
        """Clean up SVG resources."""
        self.svg_elements.clear()
        self.svg_generator = None
        self.current_id = 0
    
    def _render_style_to_svg_style(self, style: RenderStyle) -> str:
        """Convert RenderStyle to SVG style string."""
        style_parts = []
        
        # Fill
        if style.fill_color:
            style_parts.append(f"fill:{style.fill_color.name()}")
        else:
            style_parts.append("fill:none")
        
        # Stroke
        if style.stroke_color and style.stroke_width > 0:
            style_parts.append(f"stroke:{style.stroke_color.name()}")
            style_parts.append(f"stroke-width:{style.stroke_width}")
        else:
            style_parts.append("stroke:none")
        
        # Opacity
        if style.opacity < 1.0:
            style_parts.append(f"opacity:{style.opacity}")
        
        # Font (for text elements)
        if style.font:
            style_parts.append(f"font-family:{style.font.family()}")
            style_parts.append(f"font-size:{style.font.pointSize()}px")
        
        return ";".join(style_parts)
    
    def _generate_svg_content(self) -> str:
        """Generate complete SVG content."""
        widget_size = self.target_widget.size()
        svg_header = (
            f'<svg width="{widget_size.width()}" height="{widget_size.height()}" '
            f'viewBox="0 0 {widget_size.width()} {widget_size.height()}" '
            f'xmlns="http://www.w3.org/2000/svg">'
        )
        
        svg_footer = '</svg>'
        
        return svg_header + "\n".join(self.svg_elements) + svg_footer
    
    def _dict_to_render_style(self, style_dict: Dict[str, Any]) -> RenderStyle:
        """Convert style dictionary to RenderStyle."""
        style = RenderStyle.default()
        
        # Map common style properties
        if 'fill_color' in style_dict:
            if isinstance(style_dict['fill_color'], str):
                style.fill_color = QColor(style_dict['fill_color'])
            elif isinstance(style_dict['fill_color'], QColor):
                style.fill_color = style_dict['fill_color']
        
        if 'stroke_color' in style_dict:
            if isinstance(style_dict['stroke_color'], str):
                style.stroke_color = QColor(style_dict['stroke_color'])
            elif isinstance(style_dict['stroke_color'], QColor):
                style.stroke_color = style_dict['stroke_color']
        
        if 'stroke_width' in style_dict:
            style.stroke_width = float(style_dict['stroke_width'])
        
        if 'opacity' in style_dict:
            style.opacity = float(style_dict['opacity'])
        
        return style


class RendererFactory:
    """Factory for creating renderer backends."""
    
    @staticmethod
    def create_renderer(backend_type: str, target_widget: QWidget) -> RendererBackend:
        """Create a renderer backend of the specified type."""
        if backend_type.lower() == 'canvas':
            return CanvasRenderer(target_widget)
        elif backend_type.lower() == 'svg':
            return SVGRenderer(target_widget)
        else:
            raise ValueError(f"Unknown renderer backend: {backend_type}")
    
    @staticmethod
    def get_available_backends() -> List[str]:
        """Get list of available renderer backends."""
        return ['canvas', 'svg']


class RenderingPerformanceProfiler:
    """Profiler for renderer performance analysis."""
    
    def __init__(self):
        self.metrics = {
            'render_times': [],
            'primitive_counts': [],
            'memory_usage': [],
            'frame_rates': []
        }
    
    def start_frame(self) -> None:
        """Start timing a frame."""
        self.frame_start_time = time.time()
    
    def end_frame(self, primitive_count: int) -> None:
        """End timing a frame."""
        if hasattr(self, 'frame_start_time'):
            render_time = time.time() - self.frame_start_time
            self.metrics['render_times'].append(render_time)
            self.metrics['primitive_counts'].append(primitive_count)
            
            # Calculate frame rate
            if render_time > 0:
                fps = 1.0 / render_time
                self.metrics['frame_rates'].append(fps)
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Get average performance metrics."""
        if not self.metrics['render_times']:
            return {}
        
        return {
            'avg_render_time': sum(self.metrics['render_times']) / len(self.metrics['render_times']),
            'avg_primitive_count': sum(self.metrics['primitive_counts']) / len(self.metrics['primitive_counts']),
            'avg_frame_rate': sum(self.metrics['frame_rates']) / len(self.metrics['frame_rates']) if self.metrics['frame_rates'] else 0
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        for key in self.metrics:
            self.metrics[key].clear()