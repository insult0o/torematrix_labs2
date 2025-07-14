"""
Comprehensive test suite for viewport management system.
Tests all classes and methods in src.torematrix.ui.viewer.viewport.
"""

import pytest
import time
import math
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.viewer.viewport import (
    ViewportState,
    ViewportInfo,
    ScreenInfo,
    ViewportManager
)
from src.torematrix.ui.viewer.coordinates import Point, Rectangle, CoordinateTransform


class TestViewportInfo:
    """Test ViewportInfo class functionality."""
    
    def test_viewport_info_creation(self):
        """Test viewport info creation."""
        size = Rectangle(0, 0, 800, 600)
        visible_bounds = Rectangle(10, 20, 780, 560)
        scale_factor = 1.5
        rotation_angle = math.pi / 4
        pan_offset = Point(50, 100)
        dpi_scale = 2.0
        
        info = ViewportInfo(
            size=size,
            visible_bounds=visible_bounds,
            scale_factor=scale_factor,
            rotation_angle=rotation_angle,
            pan_offset=pan_offset,
            dpi_scale=dpi_scale
        )
        
        assert info.size == size
        assert info.visible_bounds == visible_bounds
        assert info.scale_factor == scale_factor
        assert info.rotation_angle == rotation_angle
        assert info.pan_offset == pan_offset
        assert info.dpi_scale == dpi_scale
    
    def test_viewport_info_copy(self):
        """Test viewport info copying."""
        size = Rectangle(0, 0, 800, 600)
        visible_bounds = Rectangle(10, 20, 780, 560)
        pan_offset = Point(50, 100)
        
        original = ViewportInfo(
            size=size,
            visible_bounds=visible_bounds,
            scale_factor=1.5,
            pan_offset=pan_offset
        )
        
        copy = original.copy()
        
        # Should be equal but different objects
        assert copy.size.x == original.size.x
        assert copy.size.y == original.size.y
        assert copy.size.width == original.size.width
        assert copy.size.height == original.size.height
        assert copy.scale_factor == original.scale_factor
        assert copy.pan_offset.x == original.pan_offset.x
        assert copy.pan_offset.y == original.pan_offset.y
        
        # Should be different objects
        assert copy is not original
        assert copy.size is not original.size
        assert copy.pan_offset is not original.pan_offset


class TestScreenInfo:
    """Test ScreenInfo class functionality."""
    
    def test_screen_info_creation(self):
        """Test screen info creation."""
        screen_rect = Rectangle(0, 0, 1920, 1080)
        available_rect = Rectangle(0, 40, 1920, 1040)
        dpi = 96.0
        scale_factor = 1.5
        is_primary = True
        name = "Primary Monitor"
        
        info = ScreenInfo(
            screen_rect=screen_rect,
            available_rect=available_rect,
            dpi=dpi,
            scale_factor=scale_factor,
            is_primary=is_primary,
            name=name
        )
        
        assert info.screen_rect == screen_rect
        assert info.available_rect == available_rect
        assert info.dpi == dpi
        assert info.scale_factor == scale_factor
        assert info.is_primary == is_primary
        assert info.name == name
    
    def test_screen_info_copy(self):
        """Test screen info copying."""
        screen_rect = Rectangle(0, 0, 1920, 1080)
        available_rect = Rectangle(0, 40, 1920, 1040)
        
        original = ScreenInfo(
            screen_rect=screen_rect,
            available_rect=available_rect,
            dpi=96.0,
            scale_factor=1.5,
            is_primary=True,
            name="Test Monitor"
        )
        
        copy = original.copy()
        
        # Should be equal but different objects
        assert copy.screen_rect.x == original.screen_rect.x
        assert copy.available_rect.width == original.available_rect.width
        assert copy.dpi == original.dpi
        assert copy.scale_factor == original.scale_factor
        assert copy.is_primary == original.is_primary
        assert copy.name == original.name
        
        # Should be different objects
        assert copy is not original
        assert copy.screen_rect is not original.screen_rect


class TestViewportManager:
    """Test ViewportManager class functionality."""
    
    @pytest.fixture
    def viewport_manager(self):
        """Create a viewport manager for testing."""
        with patch('src.torematrix.ui.viewer.viewport.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.devicePixelRatio.return_value = 1.0
            mock_screen.name.return_value = "Test Screen"
            
            mock_app.instance.return_value = mock_app
            mock_app.primaryScreen.return_value = mock_screen
            
            manager = ViewportManager()
            yield manager
    
    def test_viewport_manager_initialization(self, viewport_manager):
        """Test viewport manager initialization."""
        assert viewport_manager._state == ViewportState.IDLE
        assert viewport_manager._viewport_info.size.width == 800
        assert viewport_manager._viewport_info.size.height == 600
        assert viewport_manager._viewport_info.scale_factor == 1.0
        assert viewport_manager._clipping_enabled is True
    
    def test_initialize_viewport(self, viewport_manager):
        """Test viewport initialization."""
        from PyQt6.QtCore import QSize
        
        widget_size = QSize(1000, 800)
        document_bounds = Rectangle(0, 0, 2000, 1600)
        
        viewport_manager.initialize(widget_size, document_bounds)
        
        info = viewport_manager.get_viewport_info()
        assert info.size.width == 1000
        assert info.size.height == 800
        assert viewport_manager._document_bounds == document_bounds
        assert viewport_manager._coordinate_transform is not None
    
    def test_viewport_size_change(self, viewport_manager):
        """Test viewport size changes."""
        from PyQt6.QtCore import QSize
        
        # Initialize first
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        new_size = QSize(1200, 900)
        viewport_manager.set_viewport_size(new_size)
        
        info = viewport_manager.get_viewport_info()
        assert info.size.width == 1200
        assert info.size.height == 900
    
    def test_zoom_level_setting(self, viewport_manager):
        """Test zoom level setting."""
        from PyQt6.QtCore import QSize
        
        # Initialize first
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test simple zoom
        viewport_manager.set_zoom_level(2.0)
        info = viewport_manager.get_viewport_info()
        assert info.scale_factor == 2.0
        
        # Test zoom with center point
        center = Point(400, 300)
        viewport_manager.set_zoom_level(1.5, center)
        info = viewport_manager.get_viewport_info()
        assert info.scale_factor == 1.5
        
        # Test zoom bounds
        viewport_manager.set_zoom_level(0.001)  # Too small
        info = viewport_manager.get_viewport_info()
        assert info.scale_factor == 0.01  # Clamped to minimum
        
        viewport_manager.set_zoom_level(200.0)  # Too large
        info = viewport_manager.get_viewport_info()
        assert info.scale_factor == 100.0  # Clamped to maximum
    
    def test_pan_offset_setting(self, viewport_manager):
        """Test pan offset setting."""
        from PyQt6.QtCore import QSize
        
        # Initialize first
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test setting pan offset
        offset = Point(100, 200)
        viewport_manager.set_pan_offset(offset)
        
        info = viewport_manager.get_viewport_info()
        assert info.pan_offset.x == 100
        assert info.pan_offset.y == 200
        
        # Test pan by delta
        delta = Point(50, -100)
        viewport_manager.pan_by_delta(delta)
        
        info = viewport_manager.get_viewport_info()
        assert info.pan_offset.x == 150
        assert info.pan_offset.y == 100
    
    def test_rotation_setting(self, viewport_manager):
        """Test rotation setting."""
        from PyQt6.QtCore import QSize
        
        # Initialize first
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        angle = math.pi / 4  # 45 degrees
        viewport_manager.set_rotation(angle)
        
        info = viewport_manager.get_viewport_info()
        assert info.rotation_angle == angle
    
    def test_coordinate_transformations(self, viewport_manager):
        """Test coordinate transformations."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test document to screen transformation
        doc_point = Point(500, 500)  # Center of document
        screen_point = viewport_manager.document_to_screen(doc_point)
        
        # Should map to somewhere reasonable in screen space
        assert isinstance(screen_point, Point)
        assert not math.isnan(screen_point.x)
        assert not math.isnan(screen_point.y)
        
        # Test screen to document transformation (round trip)
        back_to_doc = viewport_manager.screen_to_document(screen_point)
        
        # Should be close to original (allowing for floating point errors)
        assert abs(back_to_doc.x - doc_point.x) < 1e-10
        assert abs(back_to_doc.y - doc_point.y) < 1e-10
    
    def test_rectangle_transformations(self, viewport_manager):
        """Test rectangle transformations."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test document rectangle to screen
        doc_rect = Rectangle(100, 200, 300, 400)
        screen_rect = viewport_manager.transform_rectangle_to_screen(doc_rect)
        
        assert isinstance(screen_rect, Rectangle)
        assert screen_rect.width > 0
        assert screen_rect.height > 0
        
        # Test screen rectangle to document (round trip)
        back_to_doc = viewport_manager.transform_rectangle_to_document(screen_rect)
        
        # Should be close to original
        assert abs(back_to_doc.x - doc_rect.x) < 1e-10
        assert abs(back_to_doc.y - doc_rect.y) < 1e-10
        assert abs(back_to_doc.width - doc_rect.width) < 1e-10
        assert abs(back_to_doc.height - doc_rect.height) < 1e-10
    
    def test_visibility_checks(self, viewport_manager):
        """Test visibility checking methods."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test point visibility
        center_point = Point(500, 500)
        assert viewport_manager.is_point_visible(center_point)
        
        far_point = Point(5000, 5000)
        # This might be visible depending on zoom/pan, so just test it doesn't crash
        viewport_manager.is_point_visible(far_point)
        
        # Test screen point in viewport
        screen_point = Point(400, 300)  # Should be in viewport
        assert viewport_manager.is_screen_point_in_viewport(screen_point)
        
        outside_point = Point(1000, 700)  # Outside viewport
        assert not viewport_manager.is_screen_point_in_viewport(outside_point)
        
        # Test rectangle visibility
        visible_rect = Rectangle(400, 400, 200, 200)
        viewport_manager.is_rectangle_visible(visible_rect)  # Should not crash
    
    def test_clipping_operations(self, viewport_manager):
        """Test viewport clipping operations."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Test clipping rectangle inside viewport
        inside_rect = Rectangle(100, 100, 200, 200)
        clipped = viewport_manager.clip_to_viewport(inside_rect)
        assert clipped == inside_rect
        
        # Test clipping rectangle partially outside
        partial_rect = Rectangle(700, 500, 200, 200)  # Extends beyond viewport
        clipped = viewport_manager.clip_to_viewport(partial_rect)
        assert clipped is not None
        assert clipped.x >= 0
        assert clipped.y >= 0
        assert clipped.x + clipped.width <= 800
        assert clipped.y + clipped.height <= 600
        
        # Test clipping rectangle completely outside
        outside_rect = Rectangle(1000, 1000, 200, 200)
        clipped = viewport_manager.clip_to_viewport(outside_rect)
        assert clipped is None
    
    def test_fit_document_to_viewport(self, viewport_manager):
        """Test fitting document to viewport."""
        from PyQt6.QtCore import QSize
        
        # Initialize with large document
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 2000, 1500))
        
        # Fit document to viewport
        viewport_manager.fit_document_to_viewport()
        
        info = viewport_manager.get_viewport_info()
        # Should have adjusted scale and pan to fit document
        assert info.scale_factor > 0
        assert info.scale_factor < 1.0  # Should be zoomed out
    
    def test_center_on_point(self, viewport_manager):
        """Test centering viewport on a point."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Center on a specific point
        target_point = Point(750, 250)
        viewport_manager.center_on_point(target_point)
        
        # The point should now be near the center of the screen
        screen_point = viewport_manager.document_to_screen(target_point)
        viewport_center = Point(400, 300)  # Center of 800x600 viewport
        
        # Should be close to viewport center
        distance = math.sqrt((screen_point.x - viewport_center.x)**2 + 
                           (screen_point.y - viewport_center.y)**2)
        assert distance < 10  # Allow some tolerance
    
    def test_dpi_awareness(self, viewport_manager):
        """Test DPI awareness functionality."""
        # Test getting DPI scale factor
        dpi_scale = viewport_manager.get_dpi_scale_factor()
        assert dpi_scale > 0
        
        # Test updating DPI awareness
        viewport_manager.update_dpi_awareness()  # Should not crash
    
    def test_performance_metrics(self, viewport_manager):
        """Test performance metrics collection."""
        from PyQt6.QtCore import QSize
        
        # Initialize and perform some operations
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Perform transformations to generate metrics
        for i in range(10):
            point = Point(i * 100, i * 50)
            viewport_manager.document_to_screen(point)
            viewport_manager.screen_to_document(point)
        
        metrics = viewport_manager.get_performance_metrics()
        
        assert 'viewport_updates' in metrics
        assert 'coordinate_transformations' in metrics
        assert 'cache_hits' in metrics
        assert 'cache_misses' in metrics
        assert 'average_transform_time' in metrics
        assert 'cache_size' in metrics
        assert 'cache_hit_rate' in metrics
        
        # Should have recorded some transformations
        assert metrics['coordinate_transformations'] > 0
    
    def test_cache_operations(self, viewport_manager):
        """Test cache operations."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Perform same transformation multiple times
        point = Point(500, 500)
        
        # First call should be cache miss
        result1 = viewport_manager.document_to_screen(point)
        
        # Second call should be cache hit
        result2 = viewport_manager.document_to_screen(point)
        
        # Results should be identical
        assert result1.x == result2.x
        assert result1.y == result2.y
        
        # Clear cache
        viewport_manager.clear_cache()
        
        metrics = viewport_manager.get_performance_metrics()
        assert metrics['cache_size'] == 0
    
    def test_state_management(self, viewport_manager):
        """Test viewport state management."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        # Track state changes
        state_changes = []
        viewport_manager.state_changed.connect(lambda state: state_changes.append(state))
        
        # Perform operations that change state
        viewport_manager.set_zoom_level(2.0)
        viewport_manager.set_pan_offset(Point(100, 200))
        
        # Should have recorded state changes
        assert len(state_changes) > 0
        assert ViewportState.ZOOMING in state_changes
        assert ViewportState.PANNING in state_changes
    
    def test_signal_emissions(self, viewport_manager):
        """Test signal emissions."""
        from PyQt6.QtCore import QSize
        
        # Track signal emissions
        viewport_changes = []
        screen_changes = []
        dpi_changes = []
        
        viewport_manager.viewport_changed.connect(lambda info: viewport_changes.append(info))
        viewport_manager.screen_changed.connect(lambda info: screen_changes.append(info))
        viewport_manager.dpi_changed.connect(lambda dpi: dpi_changes.append(dpi))
        
        # Initialize and perform operations
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        viewport_manager.set_zoom_level(1.5)
        viewport_manager.set_pan_offset(Point(50, 100))
        
        # Should have emitted viewport change signals
        assert len(viewport_changes) > 0
        
        # Test DPI change
        viewport_manager.update_dpi_awareness()
        
        # Might emit DPI changes depending on mock setup
    
    def test_edge_cases(self, viewport_manager):
        """Test edge cases and error conditions."""
        from PyQt6.QtCore import QSize
        
        # Test with very small viewport
        viewport_manager.initialize(QSize(1, 1), Rectangle(0, 0, 1000, 1000))
        
        # Should not crash
        point = Point(500, 500)
        result = viewport_manager.document_to_screen(point)
        assert isinstance(result, Point)
        
        # Test with very large document
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000000, 1000000))
        
        # Should not crash
        result = viewport_manager.document_to_screen(point)
        assert isinstance(result, Point)
        
        # Test with zero-size document
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 0, 0))
        
        # Should handle gracefully
        result = viewport_manager.document_to_screen(point)
        assert isinstance(result, Point)
    
    def test_visible_document_bounds(self, viewport_manager):
        """Test visible document bounds calculation."""
        from PyQt6.QtCore import QSize
        
        # Initialize viewport
        viewport_manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
        
        visible_bounds = viewport_manager.get_visible_document_bounds()
        
        assert isinstance(visible_bounds, Rectangle)
        assert visible_bounds.width > 0
        assert visible_bounds.height > 0
        
        # Change zoom and check again
        viewport_manager.set_zoom_level(2.0)
        
        new_visible_bounds = viewport_manager.get_visible_document_bounds()
        
        # At higher zoom, visible area should be smaller
        assert new_visible_bounds.width < visible_bounds.width
        assert new_visible_bounds.height < visible_bounds.height


class TestViewportIntegration:
    """Test viewport integration with other components."""
    
    def test_coordinate_transform_integration(self):
        """Test integration with coordinate transform system."""
        with patch('src.torematrix.ui.viewer.viewport.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.devicePixelRatio.return_value = 1.0
            mock_screen.name.return_value = "Test Screen"
            
            mock_app.instance.return_value = mock_app
            mock_app.primaryScreen.return_value = mock_screen
            
            manager = ViewportManager()
            
            from PyQt6.QtCore import QSize
            
            # Initialize with coordinate transform
            manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
            
            # Should have created coordinate transform
            assert manager._coordinate_transform is not None
            
            # Test that transformations work through both systems
            doc_point = Point(250, 750)
            
            # Transform through viewport manager
            screen_point1 = manager.document_to_screen(doc_point)
            
            # Transform through coordinate transform directly
            screen_point2 = manager._coordinate_transform.document_to_screen(doc_point)
            
            # Should be similar (viewport manager may apply additional DPI scaling)
            assert abs(screen_point1.x - screen_point2.x) < 100
            assert abs(screen_point1.y - screen_point2.y) < 100


class TestViewportPerformance:
    """Test viewport performance characteristics."""
    
    def test_transformation_performance(self):
        """Test transformation performance under load."""
        with patch('src.torematrix.ui.viewer.viewport.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.devicePixelRatio.return_value = 1.0
            mock_screen.name.return_value = "Test Screen"
            
            mock_app.instance.return_value = mock_app
            mock_app.primaryScreen.return_value = mock_screen
            
            manager = ViewportManager()
            
            from PyQt6.QtCore import QSize
            
            # Initialize viewport
            manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
            
            # Perform many transformations
            start_time = time.time()
            
            for i in range(1000):
                point = Point(i % 1000, (i * 2) % 1000)
                screen_point = manager.document_to_screen(point)
                doc_point = manager.screen_to_document(screen_point)
            
            end_time = time.time()
            
            # Should complete in reasonable time
            total_time = end_time - start_time
            assert total_time < 1.0  # Should be fast
            
            # Check performance metrics
            metrics = manager.get_performance_metrics()
            assert metrics['coordinate_transformations'] == 2000  # 1000 each direction
            assert metrics['cache_hit_rate'] >= 0.0
    
    def test_cache_performance(self):
        """Test cache performance."""
        with patch('src.torematrix.ui.viewer.viewport.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.devicePixelRatio.return_value = 1.0
            mock_screen.name.return_value = "Test Screen"
            
            mock_app.instance.return_value = mock_app
            mock_app.primaryScreen.return_value = mock_screen
            
            manager = ViewportManager()
            
            from PyQt6.QtCore import QSize
            
            # Initialize viewport
            manager.initialize(QSize(800, 600), Rectangle(0, 0, 1000, 1000))
            
            # Perform repeated transformations of same points
            points = [Point(i * 100, i * 50) for i in range(10)]
            
            # First pass - cache misses
            for point in points:
                manager.document_to_screen(point)
            
            # Second pass - should be cache hits
            for point in points:
                manager.document_to_screen(point)
            
            metrics = manager.get_performance_metrics()
            
            # Should have good cache hit rate
            assert metrics['cache_hits'] > 0
            assert metrics['cache_hit_rate'] > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])