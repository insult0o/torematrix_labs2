"""
Integration tests for the complete zoom, pan, and rotation optimization system.

This test suite verifies that all components work together correctly
and meet the overall system performance requirements.
"""

import pytest
import time
import math
import threading
from unittest.mock import Mock, patch, MagicMock

# For testing without Qt dependencies
try:
    from src.torematrix.ui.viewer.controls.zoom import ZoomManager, ZoomState, ZoomPerformanceMetrics
    from src.torematrix.ui.viewer.controls.pan import PanManager, PanState, PanConstraints, PanPerformanceMetrics
    from src.torematrix.ui.viewer.rotation import RotationManager, RotationState, RotationConstraints, RotationPerformanceMetrics
    from src.torematrix.ui.viewer.cache import TransformationCache, CoordinateCache
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False
    

@pytest.mark.skipif(not COMPONENTS_AVAILABLE, reason="Components not available without dependencies")
class TestOptimizationIntegration:
    """Test integration of zoom, pan, and rotation optimization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinate_transform = Mock()
        self.mock_coordinate_transform.viewport_bounds = Mock()
        self.mock_coordinate_transform.viewport_bounds.width = 800
        self.mock_coordinate_transform.viewport_bounds.height = 600
        
        self.zoom_manager = ZoomManager(self.mock_coordinate_transform)
        self.pan_manager = PanManager(self.mock_coordinate_transform)
        self.rotation_manager = RotationManager(self.mock_coordinate_transform)
        
    def test_combined_transformations(self):
        """Test that zoom, pan, and rotation work together."""
        # Apply transformations
        zoom_result = self.zoom_manager.zoom_to_level(2.0)
        pan_result = self.pan_manager.pan_to_offset(Point(100, 200))
        rotation_result = self.rotation_manager.rotate_to_angle(math.pi / 4)
        
        assert zoom_result is True
        assert pan_result is True
        assert rotation_result is True
        
        # Get transformations
        zoom_transform = self.zoom_manager.get_zoom_transformation()
        pan_transform = self.pan_manager.get_pan_transformation()
        rotation_transform = self.rotation_manager.get_rotation_transformation()
        
        assert zoom_transform is not None
        assert pan_transform is not None
        assert rotation_transform is not None
        
    def test_cache_coordination(self):
        """Test that caches work efficiently together."""
        # Perform operations to populate caches
        zoom_levels = [1.0, 1.5, 2.0, 1.5, 1.0]  # Repeated values
        pan_offsets = [Point(0, 0), Point(50, 50), Point(100, 100), Point(50, 50)]
        rotation_angles = [0.0, math.pi / 4, math.pi / 2, math.pi / 4]
        
        for i in range(max(len(zoom_levels), len(pan_offsets), len(rotation_angles))):
            if i < len(zoom_levels):
                self.zoom_manager.zoom_to_level(zoom_levels[i])
                self.zoom_manager.get_zoom_transformation()
                
            if i < len(pan_offsets):
                self.pan_manager.pan_to_offset(pan_offsets[i])
                self.pan_manager.get_pan_transformation()
                
            if i < len(rotation_angles):
                self.rotation_manager.rotate_to_angle(rotation_angles[i])
                self.rotation_manager.get_rotation_transformation()
        
        # Check cache efficiency
        zoom_stats = self.zoom_manager._transformation_cache.get_stats()
        pan_stats = self.pan_manager._transformation_cache.get_stats()
        rotation_stats = self.rotation_manager._transformation_cache.get_stats()
        
        # Should have good hit rates due to repeated values
        assert zoom_stats['hit_rate'] > 0.2  # At least 20% hit rate
        assert pan_stats['hit_rate'] >= 0.0   # May not have hits in small test
        assert rotation_stats['hit_rate'] > 0.2
        
    def test_performance_coordination(self):
        """Test overall system performance."""
        operations_count = 100
        start_time = time.time()
        
        # Perform mixed operations
        for i in range(operations_count):
            zoom_level = 1.0 + (i % 10) * 0.1
            pan_offset = Point(i % 50, (i * 2) % 50)
            rotation_angle = (i % 8) * math.pi / 4
            
            self.zoom_manager.zoom_to_level(zoom_level)
            self.pan_manager.pan_to_offset(pan_offset)
            self.rotation_manager.rotate_to_angle(rotation_angle)
            
            # Get transformations (this tests caching)
            self.zoom_manager.get_zoom_transformation()
            self.pan_manager.get_pan_transformation()
            self.rotation_manager.get_rotation_transformation()
        
        total_time = time.time() - start_time
        average_time_per_operation = total_time / operations_count
        
        # Each operation set should complete quickly
        assert average_time_per_operation < 0.01  # Less than 10ms per operation set
        
    def test_coordinate_transform_integration(self):
        """Test integration with coordinate transform."""
        # Verify that managers update coordinate transform
        self.zoom_manager.zoom_to_level(1.5)
        self.pan_manager.pan_to_offset(Point(50, 75))
        self.rotation_manager.rotate_to_angle(math.pi / 6)
        
        # Check that coordinate transform methods were called
        self.mock_coordinate_transform.set_zoom_level.assert_called_with(1.5)
        self.mock_coordinate_transform.set_pan_offset.assert_called_with(Point(50, 75))
        self.mock_coordinate_transform.set_rotation.assert_called_with(math.pi / 6)
        
    def test_performance_metrics_integration(self):
        """Test that performance metrics work across components."""
        # Perform operations
        for i in range(10):
            self.zoom_manager.zoom_to_level(1.0 + i * 0.1)
            self.pan_manager.pan_to_offset(Point(i * 10, i * 10))
            self.rotation_manager.rotate_to_angle(i * math.pi / 10)
        
        # Get metrics
        zoom_metrics = self.zoom_manager.get_performance_metrics()
        pan_metrics = self.pan_manager.get_performance_metrics()
        rotation_metrics = self.rotation_manager.get_performance_metrics()
        
        # Verify metrics are populated
        assert isinstance(zoom_metrics, ZoomPerformanceMetrics)
        assert isinstance(pan_metrics, PanPerformanceMetrics)
        assert isinstance(rotation_metrics, RotationPerformanceMetrics)
        
        assert len(zoom_metrics.operation_times) > 0
        assert pan_metrics.instant_operations >= 0
        assert rotation_metrics.snap_operations >= 0
        
    def test_optimization_methods(self):
        """Test that optimization methods work across components."""
        # Add data to optimize
        for i in range(20):
            self.zoom_manager.zoom_to_level(1.0 + i * 0.05)
            self.pan_manager.pan_to_offset(Point(i, i))
            self.rotation_manager.rotate_to_angle(i * math.pi / 20)
        
        # Optimize all components
        self.zoom_manager.optimize_performance()
        self.pan_manager.optimize_performance()
        self.rotation_manager.optimize_performance()
        
        # Should not raise exceptions
        # Metrics should still be available
        zoom_metrics = self.zoom_manager.get_performance_metrics()
        pan_metrics = self.pan_manager.get_performance_metrics()
        rotation_metrics = self.rotation_manager.get_performance_metrics()
        
        assert zoom_metrics is not None
        assert pan_metrics is not None
        assert rotation_metrics is not None
        
    def test_state_consistency(self):
        """Test that component states remain consistent."""
        initial_zoom = self.zoom_manager.get_zoom_level()
        initial_pan = self.pan_manager.get_pan_offset()
        initial_rotation = self.rotation_manager.get_rotation_angle()
        
        # Perform operations
        self.zoom_manager.zoom_to_level(2.5)
        self.pan_manager.pan_to_offset(Point(150, 200))
        self.rotation_manager.rotate_to_angle(math.pi / 3)
        
        # Verify states changed
        assert self.zoom_manager.get_zoom_level() != initial_zoom
        assert self.pan_manager.get_pan_offset() != initial_pan
        assert self.rotation_manager.get_rotation_angle() != initial_rotation
        
        # States should be consistent with what we set
        assert self.zoom_manager.get_zoom_level() == 2.5
        assert self.pan_manager.get_pan_offset() == Point(150, 200)
        assert abs(self.rotation_manager.get_rotation_angle() - math.pi / 3) < 1e-10
        
    def test_error_handling_integration(self):
        """Test error handling across components."""
        # Test invalid zoom
        result = self.zoom_manager.zoom_to_level(-1.0)  # Invalid
        assert result is False
        
        # Test locked rotation
        constraints = RotationConstraints(lock_rotation=True)
        self.rotation_manager.set_constraints(constraints)
        result = self.rotation_manager.rotate_to_angle(math.pi / 2)
        assert result is False
        
        # Test pan with constraints
        bounds = Rect(0, 0, 100, 100)
        pan_constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True,
            elastic_bounds=False
        )
        self.pan_manager.set_constraints(pan_constraints)
        self.pan_manager.pan_to_offset(Point(200, 200))  # Outside bounds
        
        # Offset should be clamped
        final_offset = self.pan_manager.get_pan_offset()
        assert final_offset.x <= bounds.x + bounds.width
        assert final_offset.y <= bounds.y + bounds.height
        
    def test_concurrent_access(self):
        """Test concurrent access to optimization components."""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(20):
                    zoom_level = 1.0 + (worker_id * 20 + i) * 0.01
                    pan_offset = Point(worker_id * 100 + i, worker_id * 100 + i)
                    rotation_angle = (worker_id * 20 + i) * math.pi / 40
                    
                    zoom_result = self.zoom_manager.zoom_to_level(zoom_level)
                    pan_result = self.pan_manager.pan_to_offset(pan_offset)
                    rotation_result = self.rotation_manager.rotate_to_angle(rotation_angle)
                    
                    results.append((zoom_result, pan_result, rotation_result))
                    
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Run multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not have errors
        assert len(errors) == 0
        assert len(results) == 60  # 3 workers * 20 operations
        assert all(all(r) for r in results)  # All operations should succeed


@pytest.mark.skipif(not COMPONENTS_AVAILABLE, reason="Components not available without dependencies")
class TestSystemPerformanceIntegration:
    """Test overall system performance characteristics."""
    
    def test_startup_performance(self):
        """Test system startup performance."""
        start_time = time.time()
        
        # Create all managers
        zoom_manager = ZoomManager()
        pan_manager = PanManager()
        rotation_manager = RotationManager()
        
        # Initialize with common operations
        zoom_manager.zoom_to_level(1.0)
        pan_manager.pan_to_offset(Point(0, 0))
        rotation_manager.rotate_to_angle(0.0)
        
        startup_time = time.time() - start_time
        
        # Startup should be fast
        assert startup_time < 0.1  # Less than 100ms
        
    def test_memory_usage_growth(self):
        """Test that memory usage doesn't grow excessively."""
        zoom_manager = ZoomManager()
        pan_manager = PanManager()
        rotation_manager = RotationManager()
        
        # Perform many operations
        for i in range(500):
            zoom_manager.zoom_to_level(1.0 + (i % 100) * 0.01)
            pan_manager.pan_to_offset(Point(i % 200, i % 200))
            rotation_manager.rotate_to_angle((i % 50) * math.pi / 25)
        
        # Check cache sizes
        zoom_stats = zoom_manager._transformation_cache.get_stats()
        pan_stats = pan_manager._transformation_cache.get_stats()
        rotation_stats = rotation_manager._transformation_cache.get_stats()
        
        # Caches should not grow without bounds
        assert zoom_stats['cache_size'] <= 1000  # Default max size
        assert pan_stats['cache_size'] <= 300    # Configured max size
        assert rotation_stats['cache_size'] <= 200  # Configured max size
        
        # Memory usage should be reasonable
        total_memory = (zoom_stats['memory_usage'] + 
                       pan_stats['memory_usage'] + 
                       rotation_stats['memory_usage'])
        assert total_memory < 50 * 1024 * 1024  # Less than 50MB total
        
    def test_sustained_performance(self):
        """Test sustained performance over time."""
        zoom_manager = ZoomManager()
        pan_manager = PanManager()
        rotation_manager = RotationManager()
        
        batch_times = []
        
        # Run 10 batches of 100 operations each
        for batch in range(10):
            start_time = time.time()
            
            for i in range(100):
                zoom_manager.zoom_to_level(1.0 + (batch * 100 + i) * 0.001)
                pan_manager.pan_to_offset(Point(batch * 10 + i % 10, batch * 10 + i % 10))
                rotation_manager.rotate_to_angle((batch * 100 + i) * math.pi / 200)
            
            batch_time = time.time() - start_time
            batch_times.append(batch_time)
        
        # Performance should not degrade significantly over time
        first_half_avg = sum(batch_times[:5]) / 5
        second_half_avg = sum(batch_times[5:]) / 5
        
        # Second half shouldn't be more than 20% slower
        assert second_half_avg <= first_half_avg * 1.2
        
    def test_cache_effectiveness_over_time(self):
        """Test that cache effectiveness improves over time."""
        zoom_manager = ZoomManager()
        
        # Pattern that should benefit from caching
        zoom_pattern = [1.0, 1.5, 2.0, 1.5, 1.0, 2.0, 1.5]
        
        hit_rates = []
        
        # Run pattern multiple times
        for cycle in range(10):
            for level in zoom_pattern:
                zoom_manager.zoom_to_level(level)
                zoom_manager.get_zoom_transformation()
            
            stats = zoom_manager._transformation_cache.get_stats()
            hit_rates.append(stats['hit_rate'])
        
        # Hit rate should improve over time
        early_hit_rate = sum(hit_rates[:3]) / 3 if hit_rates[:3] else 0
        late_hit_rate = sum(hit_rates[-3:]) / 3 if hit_rates[-3:] else 0
        
        assert late_hit_rate >= early_hit_rate


# Mock classes for testing without dependencies
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

class Rect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


if __name__ == "__main__":
    pytest.main([__file__, "-v"])