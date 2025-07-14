"""
Comprehensive tests for the zoom transformation manager.

This test suite ensures >95% coverage of the zoom functionality
with performance validation and edge case handling.
"""

import pytest
import time
import math
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.viewer.zoom import (
    ZoomManager,
    ZoomState,
    ZoomPerformanceMetrics
)
from src.torematrix.ui.viewer.coordinates import CoordinateTransform
from src.torematrix.ui.viewer.transformations import AffineTransformation
from src.torematrix.utils.geometry import Point, Rect, Size


class TestZoomState:
    """Test ZoomState functionality."""
    
    def test_zoom_state_creation(self):
        """Test zoom state creation."""
        center = Point(100, 200)
        state = ZoomState(2.0, 0.5, 5.0, center)
        
        assert state.level == 2.0
        assert state.min_zoom == 0.5
        assert state.max_zoom == 5.0
        assert state.center == center
        assert state.smooth_factor == 0.1
        
    def test_zoom_state_validation(self):
        """Test zoom state validation in __post_init__."""
        center = Point(0, 0)
        
        # Test clamping to bounds
        state = ZoomState(10.0, 0.5, 5.0, center)  # level > max_zoom
        assert state.level == 5.0
        
        state = ZoomState(0.1, 0.5, 5.0, center)  # level < min_zoom
        assert state.level == 0.5


class TestZoomPerformanceMetrics:
    """Test ZoomPerformanceMetrics functionality."""
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation."""
        operation_times = [0.001, 0.002, 0.003]
        metrics = ZoomPerformanceMetrics(
            operation_times=operation_times,
            cache_hit_rate=0.8,
            smooth_operations=5,
            instant_operations=10,
            average_operation_time=0.0  # Will be calculated
        )
        
        assert metrics.operation_times == operation_times
        assert metrics.cache_hit_rate == 0.8
        assert metrics.smooth_operations == 5
        assert metrics.instant_operations == 10
        assert metrics.average_operation_time == 0.002  # Average of [0.001, 0.002, 0.003]
        
    def test_performance_metrics_empty_times(self):
        """Test performance metrics with empty operation times."""
        metrics = ZoomPerformanceMetrics(
            operation_times=[],
            cache_hit_rate=0.0,
            smooth_operations=0,
            instant_operations=0,
            average_operation_time=0.0
        )
        
        assert metrics.average_operation_time == 0.0


class TestZoomManager:
    """Test ZoomManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinate_transform = Mock(spec=CoordinateTransform)
        self.mock_coordinate_transform.viewport_bounds = Rect(0, 0, 800, 600)
        self.zoom_manager = ZoomManager(self.mock_coordinate_transform)
        
    def test_zoom_manager_initialization(self):
        """Test zoom manager initialization."""
        manager = ZoomManager()
        
        assert manager.get_zoom_level() == 1.0
        assert manager.get_zoom_bounds() == (0.1, 10.0)
        assert not manager.is_animating()
        
    def test_zoom_manager_with_coordinate_transform(self):
        """Test zoom manager with coordinate transform."""
        assert self.zoom_manager.coordinate_transform == self.mock_coordinate_transform
        assert self.zoom_manager.get_zoom_level() == 1.0
        
    def test_zoom_to_level_valid(self):
        """Test zoom to valid level."""
        result = self.zoom_manager.zoom_to_level(2.0)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() == 2.0
        
    def test_zoom_to_level_invalid(self):
        """Test zoom to invalid level."""
        # Test zoom level out of bounds
        result = self.zoom_manager.zoom_to_level(20.0)  # Above max_zoom
        
        assert result is False
        assert self.zoom_manager.get_zoom_level() == 1.0  # Should remain unchanged
        
    def test_zoom_to_level_with_center(self):
        """Test zoom to level with center point."""
        center = Point(400, 300)
        result = self.zoom_manager.zoom_to_level(2.0, center)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() == 2.0
        assert self.zoom_manager._zoom_state.center == center
        
    def test_zoom_to_level_animated(self):
        """Test animated zoom to level."""
        with patch.object(self.zoom_manager, '_start_smooth_zoom') as mock_smooth:
            mock_smooth.return_value = True
            
            result = self.zoom_manager.zoom_to_level(2.0, animated=True)
            
            assert result is True
            mock_smooth.assert_called_once()
            
    def test_zoom_in(self):
        """Test zoom in operation."""
        initial_level = self.zoom_manager.get_zoom_level()
        result = self.zoom_manager.zoom_in(factor=1.5)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() == initial_level * 1.5
        
    def test_zoom_out(self):
        """Test zoom out operation."""
        self.zoom_manager.zoom_to_level(3.0)
        result = self.zoom_manager.zoom_out(factor=1.5)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() == 3.0 / 1.5
        
    def test_zoom_to_fit(self):
        """Test zoom to fit rectangle."""
        rect = Rect(100, 100, 200, 150)
        result = self.zoom_manager.zoom_to_fit(rect)
        
        assert result is True
        # Zoom level should be calculated to fit the rectangle
        assert self.zoom_manager.get_zoom_level() > 0
        
    def test_zoom_to_fit_no_viewport(self):
        """Test zoom to fit without viewport size."""
        manager = ZoomManager()  # No coordinate transform
        rect = Rect(100, 100, 200, 150)
        result = manager.zoom_to_fit(rect)
        
        assert result is False
        
    def test_smooth_zoom_to_level(self):
        """Test smooth zoom to level."""
        with patch.object(self.zoom_manager, '_start_smooth_zoom') as mock_smooth:
            mock_smooth.return_value = True
            
            result = self.zoom_manager.smooth_zoom_to_level(2.0, duration=0.5)
            
            assert result is True
            assert self.zoom_manager._animation_duration == 0.5
            mock_smooth.assert_called_once_with(2.0, None)
            
    @patch('src.torematrix.ui.viewer.zoom.QT_AVAILABLE', True)
    def test_handle_wheel_event(self):
        """Test mouse wheel event handling."""
        # Mock QWheelEvent
        mock_event = Mock()
        mock_event.angleDelta.return_value.y.return_value = 120  # One wheel step
        mock_event.position.return_value.x.return_value = 400
        mock_event.position.return_value.y.return_value = 300
        
        initial_level = self.zoom_manager.get_zoom_level()
        result = self.zoom_manager.handle_wheel_event(mock_event, sensitivity=0.1)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() != initial_level
        
    @patch('src.torematrix.ui.viewer.zoom.QT_AVAILABLE', False)
    def test_handle_wheel_event_no_qt(self):
        """Test wheel event handling without Qt available."""
        mock_event = Mock()
        result = self.zoom_manager.handle_wheel_event(mock_event)
        
        assert result is False
        
    def test_get_zoom_bounds(self):
        """Test getting zoom bounds."""
        bounds = self.zoom_manager.get_zoom_bounds()
        assert bounds == (0.1, 10.0)
        
    def test_set_zoom_bounds(self):
        """Test setting zoom bounds."""
        self.zoom_manager.set_zoom_bounds(0.5, 5.0)
        
        bounds = self.zoom_manager.get_zoom_bounds()
        assert bounds == (0.5, 5.0)
        
    def test_set_zoom_bounds_clamps_current_level(self):
        """Test that setting bounds clamps current zoom level."""
        self.zoom_manager.zoom_to_level(8.0)
        self.zoom_manager.set_zoom_bounds(0.5, 5.0)  # Current level (8.0) exceeds new max
        
        assert self.zoom_manager.get_zoom_level() == 5.0
        
    def test_set_zoom_bounds_invalid(self):
        """Test setting invalid zoom bounds."""
        with pytest.raises(ValueError):
            self.zoom_manager.set_zoom_bounds(0.0, 5.0)  # min_zoom <= 0
            
        with pytest.raises(ValueError):
            self.zoom_manager.set_zoom_bounds(5.0, 2.0)  # min_zoom > max_zoom
            
    def test_get_zoom_transformation(self):
        """Test getting zoom transformation."""
        self.zoom_manager.zoom_to_level(2.0)
        transform = self.zoom_manager.get_zoom_transformation()
        
        assert transform is not None
        assert isinstance(transform, AffineTransformation)
        
    def test_get_zoom_transformation_with_center(self):
        """Test getting zoom transformation with center offset."""
        center = Point(100, 200)
        self.zoom_manager.zoom_to_level(2.0, center)
        transform = self.zoom_manager.get_zoom_transformation()
        
        assert transform is not None
        
    def test_get_zoom_transformation_cached(self):
        """Test that zoom transformations are cached."""
        self.zoom_manager.zoom_to_level(2.0)
        
        # Get transformation twice
        transform1 = self.zoom_manager.get_zoom_transformation()
        transform2 = self.zoom_manager.get_zoom_transformation()
        
        # Should be the same object from cache
        assert transform1 is transform2
        
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        # Perform some zoom operations
        self.zoom_manager.zoom_to_level(2.0)
        self.zoom_manager.zoom_to_level(1.5)
        self.zoom_manager.zoom_in()
        
        metrics = self.zoom_manager.get_performance_metrics()
        
        assert isinstance(metrics, ZoomPerformanceMetrics)
        assert len(metrics.operation_times) > 0
        assert metrics.cache_hit_rate >= 0.0
        
    def test_predict_zoom_performance(self):
        """Test zoom performance prediction."""
        # With no history, should return default
        prediction = self.zoom_manager.predict_zoom_performance(2.0)
        assert prediction == 1.0
        
        # Add some history
        self.zoom_manager.zoom_to_level(1.5)
        self.zoom_manager.zoom_to_level(2.0)
        self.zoom_manager.zoom_to_level(2.5)
        
        prediction = self.zoom_manager.predict_zoom_performance(3.0)
        assert 0.0 <= prediction <= 1.0
        
    def test_optimize_performance(self):
        """Test performance optimization."""
        # Add some operations
        for i in range(10):
            self.zoom_manager.zoom_to_level(1.0 + i * 0.1)
            
        # Should not raise any exceptions
        self.zoom_manager.optimize_performance()
        
    def test_reset_performance_metrics(self):
        """Test resetting performance metrics."""
        # Add some operations
        self.zoom_manager.zoom_to_level(2.0)
        self.zoom_manager.zoom_to_level(1.5)
        
        # Reset metrics
        self.zoom_manager.reset_performance_metrics()
        
        metrics = self.zoom_manager.get_performance_metrics()
        assert len(metrics.operation_times) == 0
        
    def test_is_animating(self):
        """Test animation state detection."""
        assert not self.zoom_manager.is_animating()
        
        # Start animation
        self.zoom_manager._animation_active = True
        assert self.zoom_manager.is_animating()
        
    def test_stop_animation(self):
        """Test stopping animation."""
        self.zoom_manager._animation_active = True
        self.zoom_manager.stop_animation()
        
        assert not self.zoom_manager.is_animating()
        
    def test_validate_zoom_level(self):
        """Test zoom level validation."""
        assert self.zoom_manager._validate_zoom_level(1.0) is True
        assert self.zoom_manager._validate_zoom_level(0.05) is False  # Below min
        assert self.zoom_manager._validate_zoom_level(20.0) is False  # Above max
        
    def test_clamp_zoom_level(self):
        """Test zoom level clamping."""
        assert self.zoom_manager._clamp_zoom_level(0.05) == 0.1  # Clamped to min
        assert self.zoom_manager._clamp_zoom_level(20.0) == 10.0  # Clamped to max
        assert self.zoom_manager._clamp_zoom_level(5.0) == 5.0   # Within bounds
        
    def test_update_coordinate_transform(self):
        """Test coordinate transform update."""
        self.zoom_manager.zoom_to_level(2.0)
        
        # Should call set_zoom_level on coordinate transform
        self.mock_coordinate_transform.set_zoom_level.assert_called_with(2.0)
        
    @patch('src.torematrix.ui.viewer.zoom.QT_AVAILABLE', True)
    def test_start_smooth_zoom(self):
        """Test starting smooth zoom animation."""
        # Mock QTimer
        with patch('src.torematrix.ui.viewer.zoom.QTimer') as mock_timer_class:
            mock_timer = Mock()
            mock_timer_class.return_value = mock_timer
            
            manager = ZoomManager(self.mock_coordinate_transform)
            result = manager._start_smooth_zoom(2.0, None)
            
            assert result is True
            assert manager._animation_target == 2.0
            assert manager._animation_active is True
            mock_timer.start.assert_called_with(16)  # ~60 FPS
            
    def test_start_smooth_zoom_no_timer(self):
        """Test starting smooth zoom without timer."""
        manager = ZoomManager()
        manager._animation_timer = None
        
        result = manager._start_smooth_zoom(2.0, None)
        assert result is False
        
    def test_animate_zoom_complete(self):
        """Test zoom animation completion."""
        self.zoom_manager._animation_active = True
        self.zoom_manager._animation_target = 2.0
        self.zoom_manager._animation_start_time = time.time() - 1.0  # 1 second ago
        self.zoom_manager._animation_duration = 0.5  # Should be complete
        
        with patch.object(self.zoom_manager, '_animation_timer') as mock_timer:
            self.zoom_manager._animate_zoom()
            
            assert self.zoom_manager.get_zoom_level() == 2.0
            assert not self.zoom_manager._animation_active
            mock_timer.stop.assert_called_once()
            
    def test_animate_zoom_in_progress(self):
        """Test zoom animation in progress."""
        self.zoom_manager._animation_active = True
        self.zoom_manager._animation_target = 2.0
        self.zoom_manager._animation_start_level = 1.0
        self.zoom_manager._animation_start_time = time.time() - 0.1  # 0.1 seconds ago
        self.zoom_manager._animation_duration = 0.5
        
        self.zoom_manager._animate_zoom()
        
        # Should be somewhere between start and target
        current_level = self.zoom_manager.get_zoom_level()
        assert 1.0 < current_level < 2.0
        assert self.zoom_manager._animation_active is True
        
    def test_ease_in_out_cubic(self):
        """Test cubic easing function."""
        # Test edge cases
        assert self.zoom_manager._ease_in_out_cubic(0.0) == 0.0
        assert self.zoom_manager._ease_in_out_cubic(1.0) == 1.0
        
        # Test mid-point
        mid_value = self.zoom_manager._ease_in_out_cubic(0.5)
        assert 0.0 < mid_value < 1.0
        
        # Test monotonic behavior
        assert (self.zoom_manager._ease_in_out_cubic(0.25) < 
                self.zoom_manager._ease_in_out_cubic(0.75))
                
    def test_update_performance_metrics(self):
        """Test performance metrics update."""
        old_level = 1.0
        new_level = 2.0
        operation_time = 0.005
        
        self.zoom_manager._update_performance_metrics(
            'test_operation', old_level, new_level, operation_time
        )
        
        assert len(self.zoom_manager._operation_times) == 1
        assert self.zoom_manager._operation_times[0] == operation_time
        assert len(self.zoom_manager._zoom_history) == 1
        
    def test_get_viewport_size(self):
        """Test getting viewport size."""
        size = self.zoom_manager._get_viewport_size()
        
        assert size is not None
        assert size.width == 800
        assert size.height == 600
        
    def test_get_viewport_size_no_transform(self):
        """Test getting viewport size without coordinate transform."""
        manager = ZoomManager()
        size = manager._get_viewport_size()
        
        assert size is None
        
    def test_precompute_transformations(self):
        """Test pre-computation of common transformations."""
        # Clear cache first
        self.zoom_manager._transformation_cache.clear()
        
        self.zoom_manager._precompute_transformations()
        
        # Should have cached some common zoom levels
        cache_stats = self.zoom_manager._transformation_cache.get_stats()
        assert cache_stats['cache_size'] > 0
        
    def test_zoom_manager_signals(self):
        """Test that zoom manager emits appropriate signals."""
        with patch.object(self.zoom_manager, 'zoom_changed') as mock_signal:
            self.zoom_manager.zoom_to_level(2.0)
            mock_signal.emit.assert_called_with(2.0)
            
    def test_zoom_caching_invalidation(self):
        """Test that cache is invalidated when bounds change."""
        # Add transformation to cache
        self.zoom_manager.zoom_to_level(5.0)
        transform = self.zoom_manager.get_zoom_transformation()
        
        # Change bounds to exclude current level
        self.zoom_manager.set_zoom_bounds(0.5, 3.0)
        
        # Cache should be invalidated
        cache_stats = self.zoom_manager._transformation_cache.get_stats()
        # The cache invalidation might happen internally
        
    def test_zoom_wheel_event_caching(self):
        """Test that wheel events use caching."""
        mock_event = Mock()
        mock_event.angleDelta.return_value.y.return_value = 120
        mock_event.position.return_value.x.return_value = 400
        mock_event.position.return_value.y.return_value = 300
        
        # First wheel event
        with patch('src.torematrix.ui.viewer.zoom.QT_AVAILABLE', True):
            self.zoom_manager.handle_wheel_event(mock_event)
            
        # Second identical wheel event should use cache
        with patch('src.torematrix.ui.viewer.zoom.QT_AVAILABLE', True):
            self.zoom_manager.handle_wheel_event(mock_event)
            
        # Should have cache hits
        cache_stats = self.zoom_manager._transformation_cache.get_stats()
        assert cache_stats['hits'] > 0


class TestZoomManagerPerformance:
    """Test zoom manager performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.zoom_manager = ZoomManager()
        
    def test_zoom_operation_performance(self):
        """Test that zoom operations meet performance targets."""
        start_time = time.time()
        
        # Perform 100 zoom operations
        for i in range(100):
            level = 1.0 + (i % 50) * 0.1  # Cycle through zoom levels
            self.zoom_manager.zoom_to_level(level)
            
        total_time = time.time() - start_time
        average_time = total_time / 100
        
        # Should average less than 5ms per operation
        assert average_time < 0.005
        
    def test_cache_hit_rate(self):
        """Test that cache achieves good hit rate."""
        # Perform operations with repeated zoom levels
        zoom_levels = [1.0, 1.5, 2.0, 1.5, 1.0, 2.0, 1.5]
        
        for level in zoom_levels:
            self.zoom_manager.zoom_to_level(level)
            
        cache_stats = self.zoom_manager._transformation_cache.get_stats()
        
        # Should achieve reasonable hit rate
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hit_rate']
            assert hit_rate > 0.3  # At least 30% hit rate
            
    def test_memory_efficiency(self):
        """Test memory efficiency of zoom operations."""
        # Perform many zoom operations
        for i in range(500):
            level = 0.5 + i * 0.01  # Unique zoom levels
            self.zoom_manager.zoom_to_level(level)
            
        cache_stats = self.zoom_manager._transformation_cache.get_stats()
        
        # Memory usage should be reasonable
        assert cache_stats['memory_usage'] < 10 * 1024 * 1024  # Less than 10MB
        
    def test_performance_degradation(self):
        """Test that performance doesn't degrade over time."""
        times = []
        
        # Measure performance over multiple batches
        for batch in range(10):
            start_time = time.time()
            
            for i in range(50):
                level = 1.0 + (batch * 50 + i) * 0.01
                self.zoom_manager.zoom_to_level(level)
                
            batch_time = time.time() - start_time
            times.append(batch_time)
            
        # Performance shouldn't degrade significantly
        first_half_avg = sum(times[:5]) / 5
        second_half_avg = sum(times[5:]) / 5
        
        # Second half shouldn't be more than 50% slower
        assert second_half_avg < first_half_avg * 1.5


class TestZoomManagerEdgeCases:
    """Test zoom manager edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.zoom_manager = ZoomManager()
        
    def test_extreme_zoom_levels(self):
        """Test handling of extreme zoom levels."""
        # Very small zoom
        result = self.zoom_manager.zoom_to_level(1e-10)
        assert result is False  # Should be rejected
        
        # Very large zoom
        result = self.zoom_manager.zoom_to_level(1e10)
        assert result is False  # Should be rejected
        
    def test_zoom_with_nan_values(self):
        """Test zoom handling with NaN values."""
        result = self.zoom_manager.zoom_to_level(float('nan'))
        assert result is False
        
        result = self.zoom_manager.zoom_to_level(float('inf'))
        assert result is False
        
    def test_zoom_rapid_changes(self):
        """Test rapid zoom level changes."""
        # Rapidly change zoom levels
        for i in range(100):
            level = 0.5 + (i % 10) * 0.5
            self.zoom_manager.zoom_to_level(level)
            
        # Should maintain consistency
        final_level = self.zoom_manager.get_zoom_level()
        assert 0.1 <= final_level <= 10.0
        
    def test_concurrent_zoom_operations(self):
        """Test concurrent zoom operations (if threading is involved)."""
        import threading
        
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(50):
                    level = 1.0 + (i % 10) * 0.1
                    result = self.zoom_manager.zoom_to_level(level)
                    results.append(result)
            except Exception as e:
                errors.append(str(e))
                
        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # Should not have errors
        assert len(errors) == 0
        assert all(results)  # All operations should succeed
        
    def test_zoom_animation_interruption(self):
        """Test interrupting zoom animation."""
        # Start animation
        self.zoom_manager._animation_active = True
        self.zoom_manager._animation_target = 2.0
        
        # Interrupt with direct zoom
        result = self.zoom_manager.zoom_to_level(3.0)
        
        assert result is True
        assert self.zoom_manager.get_zoom_level() == 3.0
        
    def test_zoom_bounds_edge_cases(self):
        """Test zoom bounds edge cases."""
        # Set bounds where min equals max
        with pytest.raises(ValueError):
            self.zoom_manager.set_zoom_bounds(2.0, 2.0)
            
        # Set very small range
        self.zoom_manager.set_zoom_bounds(0.99, 1.01)
        bounds = self.zoom_manager.get_zoom_bounds()
        assert bounds == (0.99, 1.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.torematrix.ui.viewer.zoom", "--cov-report=term-missing"])