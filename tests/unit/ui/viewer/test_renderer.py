"""
Unit tests for renderer backend system.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QRectF, QPointF, QSizeF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont

from src.torematrix.ui.viewer.renderer import (
    RendererBackend, CanvasRenderer, SVGRenderer, RenderStyle, RenderPrimitive,
    RendererFactory, RenderingPerformanceProfiler
)
from src.torematrix.ui.viewer.coordinates import Rectangle, Point


class TestRenderStyle:
    """Test render style configuration."""
    
    def test_default_style(self):
        """Test default style creation."""
        style = RenderStyle.default()
        
        assert style.fill_color is not None
        assert style.stroke_color is not None
        assert style.stroke_width == 1.0
        assert style.opacity == 1.0
        assert style.font is not None
    
    def test_custom_style(self):
        """Test custom style creation."""
        style = RenderStyle(
            fill_color=QColor(255, 0, 0),
            stroke_color=QColor(0, 255, 0),
            stroke_width=2.0,
            opacity=0.5,
            font_size=14.0
        )
        
        assert style.fill_color == QColor(255, 0, 0)
        assert style.stroke_color == QColor(0, 255, 0)
        assert style.stroke_width == 2.0
        assert style.opacity == 0.5
        assert style.font_size == 14.0


class TestCanvasRenderer:
    """Test canvas renderer implementation."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    @pytest.fixture
    def renderer(self, widget):
        """Create test canvas renderer."""
        return CanvasRenderer(widget)
    
    def test_renderer_initialization(self, renderer):
        """Test renderer initialization."""
        assert renderer.target_widget is not None
        assert renderer.painter is None
        assert not renderer.rendering_active
        assert renderer.performance_metrics is not None
        assert renderer.use_double_buffering
    
    def test_render_lifecycle(self, renderer):
        """Test rendering lifecycle."""
        # Mock context
        context = Mock()
        context.clear_background = True
        
        # Begin render
        renderer.begin_render(context)
        assert renderer.rendering_active
        assert renderer.painter is not None
        assert renderer.current_context == context
        
        # End render
        renderer.end_render()
        assert not renderer.rendering_active
        assert renderer.painter is None
        assert renderer.current_context is None
    
    def test_render_rectangle(self, renderer):
        """Test rectangle rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test rectangle and style
        bounds = Rectangle(10, 10, 100, 100)
        style = RenderStyle(
            fill_color=QColor(255, 0, 0),
            stroke_color=QColor(0, 255, 0),
            stroke_width=2.0
        )
        
        # Mock painter methods
        renderer.painter.fillRect = Mock()
        renderer.painter.drawRect = Mock()
        
        # Render rectangle
        renderer.render_rectangle(bounds, style)
        
        # Verify calls
        renderer.painter.fillRect.assert_called_once()
        renderer.painter.drawRect.assert_called_once()
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_circle(self, renderer):
        """Test circle rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test circle and style
        center = Point(50, 50)
        radius = 25.0
        style = RenderStyle(fill_color=QColor(255, 0, 0))
        
        # Mock painter methods
        renderer.painter.setBrush = Mock()
        renderer.painter.drawEllipse = Mock()
        
        # Render circle
        renderer.render_circle(center, radius, style)
        
        # Verify calls
        renderer.painter.setBrush.assert_called_once()
        renderer.painter.drawEllipse.assert_called_once()
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_polygon(self, renderer):
        """Test polygon rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test polygon and style
        points = [Point(10, 10), Point(50, 10), Point(30, 50)]
        style = RenderStyle(fill_color=QColor(255, 0, 0))
        
        # Mock painter methods
        renderer.painter.setBrush = Mock()
        renderer.painter.drawPolygon = Mock()
        
        # Render polygon
        renderer.render_polygon(points, style)
        
        # Verify calls
        renderer.painter.setBrush.assert_called_once()
        renderer.painter.drawPolygon.assert_called_once()
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_line(self, renderer):
        """Test line rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test line and style
        start = Point(10, 10)
        end = Point(100, 100)
        style = RenderStyle(stroke_color=QColor(0, 255, 0), stroke_width=3.0)
        
        # Mock painter methods
        renderer.painter.drawLine = Mock()
        
        # Render line
        renderer.render_line(start, end, style)
        
        # Verify calls
        renderer.painter.drawLine.assert_called_once()
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_text(self, renderer):
        """Test text rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test text and style
        text = "Hello, World!"
        position = Point(50, 50)
        style = RenderStyle(
            fill_color=QColor(0, 0, 0),
            font=QFont("Arial", 12)
        )
        
        # Mock painter methods
        renderer.painter.setFont = Mock()
        renderer.painter.setPen = Mock()
        renderer.painter.drawText = Mock()
        renderer.painter.font = Mock(return_value=QFont("Arial", 12))
        
        # Mock font metrics
        with patch('src.torematrix.ui.viewer.renderer.QFontMetrics') as mock_metrics:
            mock_metrics.return_value.boundingRect.return_value = Mock(width=Mock(return_value=100))
            
            # Render text
            renderer.render_text(text, position, style)
        
        # Verify calls
        renderer.painter.setFont.assert_called_once()
        renderer.painter.setPen.assert_called_once()
        renderer.painter.drawText.assert_called_once()
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_state_management(self, renderer):
        """Test state save/restore."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Mock painter methods
        renderer.painter.save = Mock()
        renderer.painter.restore = Mock()
        
        # Test state operations
        renderer.save_state()
        renderer.restore_state()
        
        # Verify calls
        renderer.painter.save.assert_called_once()
        renderer.painter.restore.assert_called_once()
        
        renderer.end_render()
    
    def test_clipping(self, renderer):
        """Test clipping region management."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Mock painter methods
        renderer.painter.setClipRect = Mock()
        renderer.painter.setClipping = Mock()
        
        # Test clipping
        clip_region = Rectangle(10, 10, 100, 100)
        renderer.set_clip_region(clip_region)
        renderer.clear_clip_region()
        
        # Verify calls
        renderer.painter.setClipRect.assert_called_once()
        renderer.painter.setClipping.assert_called_once_with(False)
        
        renderer.end_render()
    
    def test_clear_region(self, renderer):
        """Test region clearing."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Mock painter methods
        renderer.painter.fillRect = Mock()
        
        # Test clear region
        clear_region = Rectangle(10, 10, 100, 100)
        renderer.clear_region(clear_region)
        
        # Verify calls
        renderer.painter.fillRect.assert_called_once()
        
        renderer.end_render()
    
    def test_cleanup(self, renderer):
        """Test cleanup functionality."""
        # Setup some state
        context = Mock()
        renderer.begin_render(context)
        
        # Cleanup
        renderer.cleanup()
        
        # Verify cleanup
        assert renderer.painter is None
        assert renderer.buffer_pixmap is None
        assert renderer.paint_device is None
        assert len(renderer.state_stack) == 0


class TestSVGRenderer:
    """Test SVG renderer implementation."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    @pytest.fixture
    def renderer(self, widget):
        """Create test SVG renderer."""
        return SVGRenderer(widget)
    
    def test_renderer_initialization(self, renderer):
        """Test renderer initialization."""
        assert renderer.target_widget is not None
        assert renderer.svg_generator is None
        assert not renderer.rendering_active
        assert renderer.performance_metrics is not None
        assert len(renderer.svg_elements) == 0
    
    def test_render_lifecycle(self, renderer):
        """Test rendering lifecycle."""
        # Mock context
        context = Mock()
        
        # Begin render
        renderer.begin_render(context)
        assert renderer.rendering_active
        assert renderer.svg_generator is not None
        assert renderer.current_context == context
        
        # End render
        renderer.end_render()
        assert not renderer.rendering_active
        assert renderer.svg_generator is None
        assert renderer.current_context is None
    
    def test_render_rectangle(self, renderer):
        """Test rectangle rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test rectangle and style
        bounds = Rectangle(10, 10, 100, 100)
        style = RenderStyle(
            fill_color=QColor(255, 0, 0),
            stroke_color=QColor(0, 255, 0),
            stroke_width=2.0
        )
        
        # Render rectangle
        renderer.render_rectangle(bounds, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'rect' in svg_element
        assert 'x="10"' in svg_element
        assert 'y="10"' in svg_element
        assert 'width="100"' in svg_element
        assert 'height="100"' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_circle(self, renderer):
        """Test circle rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test circle and style
        center = Point(50, 50)
        radius = 25.0
        style = RenderStyle(fill_color=QColor(255, 0, 0))
        
        # Render circle
        renderer.render_circle(center, radius, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'circle' in svg_element
        assert 'cx="50"' in svg_element
        assert 'cy="50"' in svg_element
        assert 'r="25"' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_polygon(self, renderer):
        """Test polygon rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test polygon and style
        points = [Point(10, 10), Point(50, 10), Point(30, 50)]
        style = RenderStyle(fill_color=QColor(255, 0, 0))
        
        # Render polygon
        renderer.render_polygon(points, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'polygon' in svg_element
        assert 'points="10,10 50,10 30,50"' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_line(self, renderer):
        """Test line rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test line and style
        start = Point(10, 10)
        end = Point(100, 100)
        style = RenderStyle(stroke_color=QColor(0, 255, 0), stroke_width=3.0)
        
        # Render line
        renderer.render_line(start, end, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'line' in svg_element
        assert 'x1="10"' in svg_element
        assert 'y1="10"' in svg_element
        assert 'x2="100"' in svg_element
        assert 'y2="100"' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_text(self, renderer):
        """Test text rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test text and style
        text = "Hello, World!"
        position = Point(50, 50)
        style = RenderStyle(fill_color=QColor(0, 0, 0))
        
        # Render text
        renderer.render_text(text, position, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'text' in svg_element
        assert 'x="50"' in svg_element
        assert 'y="50"' in svg_element
        assert 'Hello, World!' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_render_path(self, renderer):
        """Test path rendering."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Create test path and style
        path_data = "M 10 10 L 50 10 L 30 50 Z"
        style = RenderStyle(fill_color=QColor(255, 0, 0))
        
        # Render path
        renderer.render_path(path_data, style)
        
        # Verify SVG element was created
        assert len(renderer.svg_elements) == 1
        svg_element = renderer.svg_elements[0]
        assert 'path' in svg_element
        assert f'd="{path_data}"' in svg_element
        assert renderer.performance_metrics['primitive_count'] == 1
        
        renderer.end_render()
    
    def test_state_management(self, renderer):
        """Test state save/restore with SVG groups."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Test state operations
        renderer.save_state()
        renderer.restore_state()
        
        # Verify SVG group elements were created
        assert len(renderer.svg_elements) == 2
        assert '<g id="group_' in renderer.svg_elements[0]
        assert '</g>' in renderer.svg_elements[1]
        
        renderer.end_render()
    
    def test_clipping(self, renderer):
        """Test clipping with SVG clipPath."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Test clipping
        clip_region = Rectangle(10, 10, 100, 100)
        renderer.set_clip_region(clip_region)
        renderer.clear_clip_region()
        
        # Verify SVG clipping elements were created
        assert len(renderer.svg_elements) == 3
        assert '<defs><clipPath' in renderer.svg_elements[0]
        assert '<g clip-path=' in renderer.svg_elements[1]
        assert '</g>' in renderer.svg_elements[2]
        
        renderer.end_render()
    
    def test_svg_generation(self, renderer):
        """Test complete SVG generation."""
        # Setup
        context = Mock()
        renderer.begin_render(context)
        
        # Add some elements
        renderer.render_rectangle(Rectangle(10, 10, 100, 100), RenderStyle.default())
        renderer.render_circle(Point(50, 50), 25, RenderStyle.default())
        
        # Generate SVG
        svg_content = renderer._generate_svg_content()
        
        # Verify SVG structure
        assert svg_content.startswith('<svg')
        assert svg_content.endswith('</svg>')
        assert 'rect' in svg_content
        assert 'circle' in svg_content
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg_content
        
        renderer.end_render()
    
    def test_cleanup(self, renderer):
        """Test cleanup functionality."""
        # Setup some state
        context = Mock()
        renderer.begin_render(context)
        renderer.render_rectangle(Rectangle(10, 10, 100, 100), RenderStyle.default())
        
        # Cleanup
        renderer.cleanup()
        
        # Verify cleanup
        assert len(renderer.svg_elements) == 0
        assert renderer.svg_generator is None
        assert renderer.current_id == 0


class TestRendererFactory:
    """Test renderer factory."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    def test_create_canvas_renderer(self, widget):
        """Test canvas renderer creation."""
        renderer = RendererFactory.create_renderer('canvas', widget)
        assert isinstance(renderer, CanvasRenderer)
        assert renderer.target_widget == widget
    
    def test_create_svg_renderer(self, widget):
        """Test SVG renderer creation."""
        renderer = RendererFactory.create_renderer('svg', widget)
        assert isinstance(renderer, SVGRenderer)
        assert renderer.target_widget == widget
    
    def test_invalid_renderer_type(self, widget):
        """Test invalid renderer type."""
        with pytest.raises(ValueError):
            RendererFactory.create_renderer('invalid', widget)
    
    def test_available_backends(self):
        """Test available backends listing."""
        backends = RendererFactory.get_available_backends()
        assert 'canvas' in backends
        assert 'svg' in backends
        assert len(backends) == 2


class TestRenderingPerformanceProfiler:
    """Test rendering performance profiler."""
    
    @pytest.fixture
    def profiler(self):
        """Create test profiler."""
        return RenderingPerformanceProfiler()
    
    def test_profiler_initialization(self, profiler):
        """Test profiler initialization."""
        assert 'render_times' in profiler.metrics
        assert 'primitive_counts' in profiler.metrics
        assert 'memory_usage' in profiler.metrics
        assert 'frame_rates' in profiler.metrics
        assert len(profiler.metrics['render_times']) == 0
    
    def test_frame_timing(self, profiler):
        """Test frame timing functionality."""
        # Start frame
        profiler.start_frame()
        assert hasattr(profiler, 'frame_start_time')
        
        # Simulate some work
        import time
        time.sleep(0.001)
        
        # End frame
        profiler.end_frame(primitive_count=10)
        
        # Verify metrics
        assert len(profiler.metrics['render_times']) == 1
        assert len(profiler.metrics['primitive_counts']) == 1
        assert len(profiler.metrics['frame_rates']) == 1
        
        assert profiler.metrics['render_times'][0] > 0
        assert profiler.metrics['primitive_counts'][0] == 10
        assert profiler.metrics['frame_rates'][0] > 0
    
    def test_average_metrics(self, profiler):
        """Test average metrics calculation."""
        # Add some frames
        for i in range(5):
            profiler.start_frame()
            time.sleep(0.001)
            profiler.end_frame(primitive_count=10 + i)
        
        # Get averages
        averages = profiler.get_average_metrics()
        
        assert 'avg_render_time' in averages
        assert 'avg_primitive_count' in averages
        assert 'avg_frame_rate' in averages
        
        assert averages['avg_render_time'] > 0
        assert averages['avg_primitive_count'] == 12.0  # (10+11+12+13+14)/5
        assert averages['avg_frame_rate'] > 0
    
    def test_reset_metrics(self, profiler):
        """Test metrics reset."""
        # Add some data
        profiler.start_frame()
        profiler.end_frame(primitive_count=10)
        
        # Verify data exists
        assert len(profiler.metrics['render_times']) == 1
        
        # Reset
        profiler.reset()
        
        # Verify reset
        assert len(profiler.metrics['render_times']) == 0
        assert len(profiler.metrics['primitive_counts']) == 0
        assert len(profiler.metrics['frame_rates']) == 0


if __name__ == "__main__":
    pytest.main([__file__])