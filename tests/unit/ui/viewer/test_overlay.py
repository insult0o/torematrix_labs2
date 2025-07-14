"""
Unit tests for overlay rendering engine.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QRect

from src.torematrix.ui.viewer.overlay import (
    OverlayEngine, OverlayManager, RenderBackend, ViewportInfo, RenderContext
)
from src.torematrix.ui.viewer.coordinates import Rectangle, Point
from src.torematrix.ui.viewer.layers import LayerType


class TestOverlayEngine:
    """Test overlay rendering engine."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    @pytest.fixture
    def engine(self, widget):
        """Create test overlay engine."""
        return OverlayEngine(widget, RenderBackend.CANVAS)
    
    def test_engine_initialization(self, engine):
        """Test overlay engine initialization."""
        assert engine.parent_widget is not None
        assert engine.layer_manager is not None
        assert engine.current_backend == RenderBackend.CANVAS
        assert engine.viewport_info is not None
        assert engine.performance_metrics is not None
        assert not engine.is_rendering
    
    def test_set_backend(self, engine):
        """Test backend switching."""
        # Test Canvas backend
        engine.set_backend(RenderBackend.CANVAS)
        assert engine.current_backend == RenderBackend.CANVAS
        assert engine.renderer_backend is not None
        
        # Test SVG backend
        engine.set_backend(RenderBackend.SVG)
        assert engine.current_backend == RenderBackend.SVG
        assert engine.renderer_backend is not None
        
        # Test invalid backend
        with pytest.raises(ValueError):
            engine.set_backend("invalid")
    
    def test_viewport_management(self, engine):
        """Test viewport management."""
        bounds = Rectangle(0, 0, 800, 600)
        center = Point(400, 300)
        
        engine.set_viewport(bounds, zoom_level=1.5, center=center)
        
        viewport = engine.get_viewport()
        assert viewport is not None
        assert viewport.bounds == bounds
        assert viewport.zoom_level == 1.5
        assert viewport.center == center
    
    def test_layer_management(self, engine):
        """Test layer creation and management."""
        # Create layer
        layer = engine.create_layer("test_layer", z_index=5)
        assert layer is not None
        assert layer.name == "test_layer"
        assert layer.get_z_index() == 5
        
        # Get layer
        retrieved = engine.get_layer("test_layer")
        assert retrieved == layer
        
        # Get all layers
        all_layers = engine.get_all_layers()
        assert len(all_layers) == 1
        assert all_layers[0] == layer
        
        # Remove layer
        removed = engine.remove_layer("test_layer")
        assert removed
        assert engine.get_layer("test_layer") is None
    
    def test_element_management(self, engine):
        """Test element management."""
        # Create test element
        element = Mock()
        element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        element.is_visible.return_value = True
        element.get_z_index.return_value = 1
        
        # Create layer
        layer = engine.create_layer("test_layer")
        
        # Add element
        added = engine.add_element("test_layer", element)
        assert added
        
        # Remove element
        removed = engine.remove_element("test_layer", element)
        assert removed
        
        # Test with non-existent layer
        added = engine.add_element("missing_layer", element)
        assert not added
    
    def test_coordinate_transformations(self, engine):
        """Test coordinate transformations."""
        # Set up viewport and document bounds
        engine.set_viewport(Rectangle(0, 0, 800, 600), zoom_level=2.0)
        engine.set_document_bounds(Rectangle(0, 0, 400, 300))
        
        # Test transformations
        doc_point = Point(100, 100)
        screen_point = engine.document_to_screen(doc_point)
        back_to_doc = engine.screen_to_document(screen_point)
        
        # Should be approximately equal (allowing for floating point errors)
        assert abs(back_to_doc.x - doc_point.x) < 0.001
        assert abs(back_to_doc.y - doc_point.y) < 0.001
    
    def test_hit_testing(self, engine):
        """Test hit testing functionality."""
        # Create test element
        element = Mock()
        element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        element.is_visible.return_value = True
        element.get_z_index.return_value = 1
        
        # Create layer and add element
        layer = engine.create_layer("test_layer")
        engine.add_element("test_layer", element)
        
        # Test hit testing
        hit_point = Point(50, 50)  # Inside element
        hit_elements = engine.hit_test(hit_point)
        assert len(hit_elements) == 1
        assert hit_elements[0] == element
        
        # Test miss
        miss_point = Point(200, 200)  # Outside element
        hit_elements = engine.hit_test(miss_point)
        assert len(hit_elements) == 0
    
    def test_visible_elements(self, engine):
        """Test visible elements detection."""
        # Set up viewport
        engine.set_viewport(Rectangle(0, 0, 800, 600))
        
        # Create visible element
        visible_element = Mock()
        visible_element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        visible_element.is_visible.return_value = True
        visible_element.get_z_index.return_value = 1
        
        # Create invisible element
        invisible_element = Mock()
        invisible_element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        invisible_element.is_visible.return_value = False
        invisible_element.get_z_index.return_value = 1
        
        # Create out-of-viewport element
        out_of_viewport_element = Mock()
        out_of_viewport_element.get_bounds.return_value = Rectangle(1000, 1000, 100, 100)
        out_of_viewport_element.is_visible.return_value = True
        out_of_viewport_element.get_z_index.return_value = 1
        
        # Create layer and add elements
        layer = engine.create_layer("test_layer")
        engine.add_element("test_layer", visible_element)
        engine.add_element("test_layer", invisible_element)
        engine.add_element("test_layer", out_of_viewport_element)
        
        # Get visible elements
        visible_elements = engine.get_visible_elements()
        assert len(visible_elements) == 1
        assert visible_elements[0] == visible_element
    
    def test_performance_metrics(self, engine):
        """Test performance metrics collection."""
        metrics = engine.get_performance_metrics()
        
        assert 'render_times' in metrics
        assert 'frame_count' in metrics
        assert 'last_fps' in metrics
        assert 'memory_usage' in metrics
        
        # Simulate some rendering
        engine.performance_metrics['render_times'] = [16.67, 16.67, 16.67]
        engine.performance_metrics['frame_count'] = 3
        
        metrics = engine.get_performance_metrics()
        assert metrics['frame_count'] == 3
    
    def test_rendering_lifecycle(self, engine):
        """Test rendering lifecycle."""
        # Mock renderer
        engine.renderer_backend = Mock()
        engine.renderer_backend.begin_render = Mock()
        engine.renderer_backend.end_render = Mock()
        engine.renderer_backend.save_state = Mock()
        engine.renderer_backend.restore_state = Mock()
        engine.renderer_backend.set_clip_region = Mock()
        
        # Mock viewport
        engine.viewport_info = ViewportInfo(
            bounds=Rectangle(0, 0, 800, 600),
            zoom_level=1.0,
            center=Point(400, 300)
        )
        
        # Test render scheduling
        engine.schedule_render()
        assert engine.render_scheduled
        
        # Test immediate render
        engine.render_now()
        engine.renderer_backend.begin_render.assert_called_once()
        engine.renderer_backend.end_render.assert_called_once()
    
    def test_layer_invalidation(self, engine):
        """Test layer invalidation."""
        # Create test layer
        layer = engine.create_layer("test_layer")
        
        # Mock layer bounds
        layer.get_bounds = Mock(return_value=Rectangle(0, 0, 100, 100))
        
        # Test layer invalidation
        engine.invalidate_layer("test_layer")
        assert len(engine.dirty_regions) > 0
    
    def test_element_invalidation(self, engine):
        """Test element invalidation."""
        # Create test element
        element = Mock()
        element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        
        # Test element invalidation
        engine.invalidate_element(element)
        assert len(engine.dirty_regions) > 0
    
    def test_render_statistics(self, engine):
        """Test render statistics."""
        # Create test layer and element
        layer = engine.create_layer("test_layer")
        element = Mock()
        element.get_bounds.return_value = Rectangle(10, 10, 100, 100)
        element.is_visible.return_value = True
        engine.add_element("test_layer", element)
        
        # Get statistics
        stats = engine.get_render_statistics()
        
        assert stats['total_layers'] == 1
        assert stats['total_elements'] == 1
        assert 'test_layer' in stats['layer_details']
        assert stats['layer_details']['test_layer']['element_count'] == 1
    
    def test_pipeline_integration(self, engine):
        """Test pipeline integration."""
        # Mock renderer backend
        engine.renderer_backend = Mock()
        
        # Set up viewport
        engine.set_viewport(Rectangle(0, 0, 800, 600))
        
        # Enable pipeline
        engine.enable_pipeline(True)
        assert engine.use_pipeline
        assert engine.render_pipeline is not None
        
        # Test pipeline render scheduling
        engine.schedule_pipeline_render()
        
        # Get pipeline performance
        pipeline_perf = engine.get_pipeline_performance()
        assert isinstance(pipeline_perf, dict)
        
        # Disable pipeline
        engine.enable_pipeline(False)
        assert not engine.use_pipeline
        assert engine.render_pipeline is None
    
    def test_enhanced_statistics(self, engine):
        """Test enhanced statistics with pipeline."""
        # Create test layer
        layer = engine.create_layer("test_layer")
        
        # Mock renderer backend
        engine.renderer_backend = Mock()
        
        # Set up viewport
        engine.set_viewport(Rectangle(0, 0, 800, 600))
        
        # Enable pipeline
        engine.enable_pipeline(True)
        
        # Get statistics
        stats = engine.get_render_statistics()
        
        assert 'use_pipeline' in stats
        assert stats['use_pipeline'] == True
        assert 'pipeline_metrics' in stats
        assert 'pipeline_frame_history' in stats
    
    def test_performance_hooks(self, engine):
        """Test performance hooks functionality."""
        # Track hook calls
        hook_calls = []
        
        def test_hook(event_type, data):
            hook_calls.append((event_type, data))
        
        # Add hook
        engine.add_performance_hook('test_hook', test_hook)
        
        # Trigger performance update
        engine._update_performance_metrics(16.67)
        
        # Check hook was called
        assert len(hook_calls) == 1
        assert hook_calls[0][0] == 'render_complete'
        assert 'render_time' in hook_calls[0][1]
        assert hook_calls[0][1]['render_time'] == 16.67
        
        # Remove hook
        engine.remove_performance_hook('test_hook')
        
        # Trigger update again
        engine._update_performance_metrics(16.67)
        
        # Should still be only one call
        assert len(hook_calls) == 1
    
    def test_cleanup(self, engine):
        """Test cleanup functionality."""
        # Create some resources
        engine.create_layer("test_layer")
        engine.renderer_backend = Mock()
        engine.renderer_backend.cleanup = Mock()
        
        # Set up viewport and enable pipeline
        engine.set_viewport(Rectangle(0, 0, 800, 600))
        engine.enable_pipeline(True)
        
        # Cleanup
        engine.cleanup()
        
        # Verify cleanup
        engine.renderer_backend.cleanup.assert_called_once()
        assert not engine.render_timer.isActive()
        assert engine.render_pipeline is None
        assert not engine.use_pipeline


class TestOverlayManager:
    """Test overlay manager."""
    
    @pytest.fixture
    def manager(self):
        """Create test overlay manager."""
        return OverlayManager()
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    def test_engine_creation(self, manager, widget):
        """Test overlay engine creation."""
        engine = manager.create_engine("test_engine", widget, RenderBackend.CANVAS)
        
        assert engine is not None
        assert manager.active_engine == "test_engine"
        assert manager.get_engine("test_engine") == engine
    
    def test_active_engine_management(self, manager, widget):
        """Test active engine management."""
        # Create multiple engines
        engine1 = manager.create_engine("engine1", widget, RenderBackend.CANVAS)
        engine2 = manager.create_engine("engine2", widget, RenderBackend.SVG)
        
        # Test active engine switching
        assert manager.active_engine == "engine1"  # First created is active
        
        manager.set_active_engine("engine2")
        assert manager.active_engine == "engine2"
        assert manager.get_active_engine() == engine2
        
        # Test invalid engine
        result = manager.set_active_engine("invalid")
        assert not result
        assert manager.active_engine == "engine2"  # Unchanged
    
    def test_engine_removal(self, manager, widget):
        """Test engine removal."""
        # Create engines
        engine1 = manager.create_engine("engine1", widget, RenderBackend.CANVAS)
        engine2 = manager.create_engine("engine2", widget, RenderBackend.SVG)
        
        # Mock cleanup
        engine1.cleanup = Mock()
        engine2.cleanup = Mock()
        
        # Remove non-active engine
        removed = manager.remove_engine("engine2")
        assert removed
        engine2.cleanup.assert_called_once()
        assert manager.get_engine("engine2") is None
        assert manager.active_engine == "engine1"  # Unchanged
        
        # Remove active engine
        removed = manager.remove_engine("engine1")
        assert removed
        engine1.cleanup.assert_called_once()
        assert manager.active_engine is None
    
    def test_cleanup(self, manager, widget):
        """Test manager cleanup."""
        # Create engines
        engine1 = manager.create_engine("engine1", widget, RenderBackend.CANVAS)
        engine2 = manager.create_engine("engine2", widget, RenderBackend.SVG)
        
        # Mock cleanup
        engine1.cleanup = Mock()
        engine2.cleanup = Mock()
        
        # Cleanup manager
        manager.cleanup()
        
        # Verify cleanup
        engine1.cleanup.assert_called_once()
        engine2.cleanup.assert_called_once()
        assert len(manager.engines) == 0
        assert manager.active_engine is None


class TestRenderContext:
    """Test render context."""
    
    def test_context_creation(self):
        """Test render context creation."""
        viewport = ViewportInfo(
            bounds=Rectangle(0, 0, 800, 600),
            zoom_level=1.0,
            center=Point(400, 300)
        )
        
        context = RenderContext(
            viewport=viewport,
            coordinate_transform=None,
            dirty_regions=[Rectangle(0, 0, 100, 100)],
            performance_metrics={}
        )
        
        assert context.viewport == viewport
        assert len(context.dirty_regions) == 1
        assert context.timestamp > 0


class TestViewportInfo:
    """Test viewport information."""
    
    def test_viewport_creation(self):
        """Test viewport creation."""
        bounds = Rectangle(0, 0, 800, 600)
        center = Point(400, 300)
        
        viewport = ViewportInfo(
            bounds=bounds,
            zoom_level=2.0,
            center=center,
            rotation=0.5
        )
        
        assert viewport.bounds == bounds
        assert viewport.zoom_level == 2.0
        assert viewport.center == center
        assert viewport.rotation == 0.5
        assert viewport.last_updated > 0


class TestRendererIntegration:
    """Test renderer integration with overlay system."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    def test_canvas_renderer_integration(self, widget):
        """Test canvas renderer integration."""
        from src.torematrix.ui.viewer.renderer import CanvasRenderer
        from src.torematrix.ui.viewer.coordinates import Rectangle
        
        # Create renderer
        renderer = CanvasRenderer(widget)
        
        # Test basic properties
        assert renderer.target_widget == widget
        assert renderer.current_context is None
        assert not renderer.rendering_active
        
        # Test performance metrics
        metrics = renderer.get_performance_metrics()
        assert 'primitive_count' in metrics
        assert 'render_time' in metrics
    
    def test_svg_renderer_integration(self, widget):
        """Test SVG renderer integration."""
        from src.torematrix.ui.viewer.renderer import SVGRenderer
        from src.torematrix.ui.viewer.coordinates import Rectangle
        
        # Create renderer
        renderer = SVGRenderer(widget)
        
        # Test basic properties
        assert renderer.target_widget == widget
        assert renderer.current_context is None
        assert not renderer.rendering_active
        
        # Test SVG elements
        assert renderer.svg_elements == []
        assert renderer.current_id == 0


class TestCoordinateIntegration:
    """Test coordinate system integration."""
    
    def test_coordinate_transformation(self):
        """Test coordinate transformation integration."""
        from src.torematrix.ui.viewer.coordinates import CoordinateTransform, Rectangle, Point
        
        # Create transformation
        doc_bounds = Rectangle(0, 0, 1000, 1000)
        viewport_bounds = Rectangle(0, 0, 800, 600)
        transform = CoordinateTransform(doc_bounds, viewport_bounds, 1.0)
        
        # Test transformation
        doc_point = Point(500, 500)
        screen_point = transform.document_to_screen(doc_point)
        back_to_doc = transform.screen_to_document(screen_point)
        
        # Should be approximately equal
        assert abs(back_to_doc.x - doc_point.x) < 0.01
        assert abs(back_to_doc.y - doc_point.y) < 0.01
    
    def test_rectangle_operations(self):
        """Test rectangle operations."""
        from src.torematrix.ui.viewer.coordinates import Rectangle
        
        rect1 = Rectangle(0, 0, 100, 100)
        rect2 = Rectangle(50, 50, 100, 100)
        
        # Test intersection
        intersection = rect1.intersection(rect2)
        assert intersection.x == 50
        assert intersection.y == 50
        assert intersection.width == 50
        assert intersection.height == 50
        
        # Test union
        union = rect1.union(rect2)
        assert union.x == 0
        assert union.y == 0
        assert union.width == 150
        assert union.height == 150


class TestPipelineIntegration:
    """Test pipeline integration."""
    
    def test_pipeline_components(self):
        """Test pipeline components without PyQt6."""
        # Test that pipeline concepts work
        from src.torematrix.ui.viewer.coordinates import Rectangle
        
        # Simulate pipeline concepts
        viewport = Rectangle(0, 0, 800, 600)
        dirty_regions = [Rectangle(0, 0, 100, 100), Rectangle(50, 50, 100, 100)]
        
        # Test dirty region merging logic
        merged_region = dirty_regions[0].union(dirty_regions[1])
        assert merged_region.x == 0
        assert merged_region.y == 0
        assert merged_region.width == 150
        assert merged_region.height == 150
        
        # Test viewport intersection
        intersects = viewport.intersects(merged_region)
        assert intersects == True


if __name__ == "__main__":
    pytest.main([__file__])