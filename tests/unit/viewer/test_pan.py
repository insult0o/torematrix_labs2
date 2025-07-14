"""
Comprehensive tests for the pan transformation manager.

This test suite ensures >95% coverage of the pan functionality
with performance validation and edge case handling.
"""

import pytest
import time
import math
import threading
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.viewer.pan import (
    PanManager,
    PanState,
    PanConstraints,
    PanPerformanceMetrics
)
from src.torematrix.ui.viewer.coordinates import CoordinateTransform
from src.torematrix.ui.viewer.transformations import AffineTransformation
from src.torematrix.utils.geometry import Point, Rect


class TestPanState:
    """Test PanState functionality."""
    
    def test_pan_state_creation(self):
        """Test pan state creation."""
        offset = Point(100, 200)
        velocity = Point(50, -25)
        state = PanState(offset, velocity)
        
        assert state.offset == offset
        assert state.velocity == velocity
        assert state.momentum_factor == 0.95
        assert state.min_velocity == 0.1
        assert state.max_velocity == 2000.0
        
    def test_pan_state_validation(self):
        """Test pan state validation in __post_init__."""
        offset = Point(0, 0)
        velocity = Point(0, 0)
        
        # Test clamping momentum factor
        state = PanState(offset, velocity, momentum_factor=1.5)  # > 0.99
        assert state.momentum_factor == 0.99
        
        state = PanState(offset, velocity, momentum_factor=0.05)  # < 0.1
        assert state.momentum_factor == 0.1
        
        # Test clamping min velocity
        state = PanState(offset, velocity, min_velocity=0.005)  # < 0.01
        assert state.min_velocity == 0.01


class TestPanConstraints:
    """Test PanConstraints functionality."""
    
    def test_pan_constraints_creation(self):
        """Test pan constraints creation."""
        bounds = Rect(0, 0, 1000, 800)
        constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True,
            elastic_bounds=True,
            elastic_factor=0.5,
            max_elastic_distance=50.0
        )
        
        assert constraints.bounds == bounds
        assert constraints.enable_bounds_checking is True
        assert constraints.elastic_bounds is True
        assert constraints.elastic_factor == 0.5
        assert constraints.max_elastic_distance == 50.0
        
    def test_pan_constraints_defaults(self):
        """Test pan constraints default values."""
        constraints = PanConstraints()
        
        assert constraints.bounds is None
        assert constraints.enable_bounds_checking is False
        assert constraints.elastic_bounds is True
        assert constraints.elastic_factor == 0.3
        assert constraints.max_elastic_distance == 100.0


class TestPanPerformanceMetrics:
    """Test PanPerformanceMetrics functionality."""
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation."""
        metrics = PanPerformanceMetrics(
            momentum_operations=10,
            instant_operations=20,
            average_velocity=150.0,
            peak_velocity=500.0,
            gesture_smoothness=85.0,
            cache_efficiency=0.8
        )
        
        assert metrics.momentum_operations == 10
        assert metrics.instant_operations == 20
        assert metrics.average_velocity == 150.0
        assert metrics.peak_velocity == 500.0
        assert metrics.gesture_smoothness == 85.0
        assert metrics.cache_efficiency == 0.8
        
    def test_performance_metrics_overall_score(self):
        """Test overall performance score calculation."""
        metrics = PanPerformanceMetrics(
            momentum_operations=10,
            instant_operations=20,
            average_velocity=500.0,  # Optimal velocity
            peak_velocity=800.0,
            gesture_smoothness=90.0,  # Good smoothness
            cache_efficiency=0.9     # High cache efficiency
        )
        
        score = metrics.get_overall_score()
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a good score


class TestPanManager:
    """Test PanManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinate_transform = Mock(spec=CoordinateTransform)
        self.pan_manager = PanManager(self.mock_coordinate_transform)
        
    def test_pan_manager_initialization(self):
        """Test pan manager initialization."""
        manager = PanManager()
        
        assert manager.get_pan_offset() == Point(0, 0)
        assert manager.get_pan_velocity() == Point(0, 0)
        assert not manager.is_panning()
        assert not manager.has_momentum()
        assert not manager.is_smooth_panning()
        
    def test_pan_manager_with_coordinate_transform(self):
        """Test pan manager with coordinate transform."""
        assert self.pan_manager.coordinate_transform == self.mock_coordinate_transform
        
    def test_start_pan(self):
        """Test starting pan operation."""
        start_position = Point(100, 200)
        
        with patch('time.time', return_value=1000.0):
            self.pan_manager.start_pan(start_position)
            
        assert self.pan_manager.is_panning()
        assert self.pan_manager._pan_start_position == start_position
        assert self.pan_manager._pan_last_position == start_position
        assert self.pan_manager.get_pan_velocity() == Point(0, 0)
        
    def test_update_pan(self):
        """Test updating pan during drag."""
        start_position = Point(100, 200)
        update_position = Point(150, 250)
        
        with patch('time.time', side_effect=[1000.0, 1000.1]):  # 0.1 second difference
            self.pan_manager.start_pan(start_position)
            self.pan_manager.update_pan(update_position)
            
        offset = self.pan_manager.get_pan_offset()
        assert offset.x == 50  # 150 - 100
        assert offset.y == 50  # 250 - 200
        
        velocity = self.pan_manager.get_pan_velocity()
        assert velocity.x > 0  # Should have positive x velocity
        assert velocity.y > 0  # Should have positive y velocity
        
    def test_update_pan_without_start(self):
        """Test updating pan without starting first."""
        update_position = Point(150, 250)
        
        # Should not crash or change state
        self.pan_manager.update_pan(update_position)
        
        assert not self.pan_manager.is_panning()
        assert self.pan_manager.get_pan_offset() == Point(0, 0)
        
    def test_finish_pan_with_momentum(self):
        """Test finishing pan with momentum."""
        start_position = Point(100, 200)
        end_position = Point(200, 300)
        
        # Enable momentum
        self.pan_manager._enable_momentum = True
        
        with patch('time.time', side_effect=[1000.0, 1000.05, 1000.1]):
            self.pan_manager.start_pan(start_position)
            self.pan_manager.update_pan(end_position)
            
            # Mock timer for momentum
            with patch.object(self.pan_manager, '_momentum_timer') as mock_timer:
                mock_timer.isActive.return_value = False
                self.pan_manager.finish_pan()
                
        assert not self.pan_manager.is_panning()
        
    def test_finish_pan_without_momentum(self):
        """Test finishing pan without momentum."""
        start_position = Point(100, 200)
        end_position = Point(105, 205)  # Small movement
        
        with patch('time.time', side_effect=[1000.0, 1000.05, 1000.1]):
            self.pan_manager.start_pan(start_position)
            self.pan_manager.update_pan(end_position)
            self.pan_manager.finish_pan()
            
        assert not self.pan_manager.is_panning()
        
    def test_pan_to_offset(self):
        """Test panning to specific offset."""
        target_offset = Point(300, 400)
        self.pan_manager.pan_to_offset(target_offset)
        
        assert self.pan_manager.get_pan_offset() == target_offset
        
    def test_pan_to_offset_animated(self):
        """Test animated pan to offset."""
        target_offset = Point(300, 400)
        
        with patch.object(self.pan_manager, '_start_smooth_pan') as mock_smooth:
            self.pan_manager.pan_to_offset(target_offset, animated=True, duration=0.5)
            mock_smooth.assert_called_once_with(target_offset, 0.5)
            
    def test_pan_by_delta(self):
        """Test panning by delta."""
        initial_offset = Point(100, 200)
        delta = Point(50, -30)
        
        self.pan_manager.pan_to_offset(initial_offset)
        self.pan_manager.pan_by_delta(delta)
        
        final_offset = self.pan_manager.get_pan_offset()
        assert final_offset.x == 150  # 100 + 50
        assert final_offset.y == 170  # 200 + (-30)
        
    def test_get_pan_transformation(self):
        """Test getting pan transformation."""
        offset = Point(100, 200)
        self.pan_manager.pan_to_offset(offset)
        
        transform = self.pan_manager.get_pan_transformation()
        
        assert transform is not None
        assert isinstance(transform, AffineTransformation)
        
    def test_get_pan_transformation_cached(self):
        """Test that pan transformations are cached."""
        offset = Point(100, 200)
        self.pan_manager.pan_to_offset(offset)
        
        # Get transformation twice
        transform1 = self.pan_manager.get_pan_transformation()
        transform2 = self.pan_manager.get_pan_transformation()
        
        # Should be the same object from cache
        assert transform1 is transform2
        
    def test_set_constraints(self):
        """Test setting pan constraints."""
        bounds = Rect(0, 0, 1000, 800)
        constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True
        )
        
        self.pan_manager.set_constraints(constraints)
        assert self.pan_manager._constraints == constraints
        
    def test_set_constraints_clamps_current_offset(self):
        """Test that setting constraints clamps current offset."""
        # Set offset outside future bounds
        self.pan_manager.pan_to_offset(Point(2000, 1500))
        
        # Set constraints that should clamp the offset
        bounds = Rect(0, 0, 1000, 800)
        constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True,
            elastic_bounds=False
        )
        
        self.pan_manager.set_constraints(constraints)
        
        # Offset should be clamped
        offset = self.pan_manager.get_pan_offset()
        assert offset.x <= bounds.right
        assert offset.y <= bounds.bottom
        
    def test_stop_momentum(self):
        """Test stopping momentum."""
        self.pan_manager._pan_state.velocity = Point(100, 200)
        self.pan_manager.stop_momentum()
        
        assert self.pan_manager.get_pan_velocity() == Point(0, 0)
        
    def test_stop_all_animation(self):
        """Test stopping all animations."""
        self.pan_manager._pan_state.velocity = Point(100, 200)
        self.pan_manager._smooth_pan_active = True
        
        self.pan_manager.stop_all_animation()
        
        assert self.pan_manager.get_pan_velocity() == Point(0, 0)
        assert not self.pan_manager.is_smooth_panning()
        
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        # Perform some pan operations
        self.pan_manager.start_pan(Point(0, 0))
        self.pan_manager.update_pan(Point(50, 50))
        self.pan_manager.finish_pan()
        
        metrics = self.pan_manager.get_performance_metrics()
        
        assert isinstance(metrics, PanPerformanceMetrics)
        assert metrics.momentum_operations >= 0
        assert metrics.instant_operations >= 0
        assert metrics.average_velocity >= 0.0
        assert metrics.peak_velocity >= 0.0
        assert 0.0 <= metrics.gesture_smoothness <= 100.0
        assert 0.0 <= metrics.cache_efficiency <= 1.0
        
    def test_optimize_performance(self):
        """Test performance optimization."""
        # Add some operations
        for i in range(10):
            self.pan_manager.start_pan(Point(i * 10, i * 10))
            self.pan_manager.update_pan(Point(i * 10 + 50, i * 10 + 50))
            self.pan_manager.finish_pan()
            
        # Should not raise any exceptions
        self.pan_manager.optimize_performance()
        
    def test_momentum_animation(self):
        """Test momentum animation."""
        # Set up momentum state
        self.pan_manager._pan_state.velocity = Point(100, 50)
        self.pan_manager._pan_state.momentum_factor = 0.9
        
        initial_velocity = self.pan_manager.get_pan_velocity()
        initial_offset = self.pan_manager.get_pan_offset()
        
        # Simulate one momentum frame
        self.pan_manager._animate_momentum()
        
        # Velocity should decay
        new_velocity = self.pan_manager.get_pan_velocity()
        assert abs(new_velocity.x) < abs(initial_velocity.x)
        assert abs(new_velocity.y) < abs(initial_velocity.y)
        
        # Offset should change
        new_offset = self.pan_manager.get_pan_offset()
        assert new_offset != initial_offset
        
    def test_momentum_stops_when_slow(self):
        """Test that momentum stops when velocity is too low."""
        # Set very low velocity
        self.pan_manager._pan_state.velocity = Point(0.05, 0.05)  # Below min_velocity
        
        with patch.object(self.pan_manager, '_momentum_timer') as mock_timer:
            self.pan_manager._animate_momentum()
            
            # Timer should be stopped
            mock_timer.stop.assert_called_once()
            
        # Velocity should be zero
        assert self.pan_manager.get_pan_velocity() == Point(0, 0)
        
    def test_smooth_pan_animation(self):
        """Test smooth pan animation."""
        start_offset = Point(0, 0)
        target_offset = Point(100, 200)
        
        self.pan_manager.pan_to_offset(start_offset)
        self.pan_manager._smooth_pan_target = target_offset
        self.pan_manager._smooth_pan_start = start_offset
        self.pan_manager._smooth_pan_start_time = time.time() - 0.1  # 0.1 seconds ago
        self.pan_manager._smooth_pan_duration = 0.5
        self.pan_manager._smooth_pan_active = True
        
        # Simulate animation frame
        self.pan_manager._animate_smooth_pan()
        
        # Should be somewhere between start and target
        current_offset = self.pan_manager.get_pan_offset()
        assert 0 < current_offset.x < 100
        assert 0 < current_offset.y < 200
        
    def test_smooth_pan_completion(self):
        """Test smooth pan animation completion."""
        target_offset = Point(100, 200)
        
        self.pan_manager._smooth_pan_target = target_offset
        self.pan_manager._smooth_pan_start = Point(0, 0)
        self.pan_manager._smooth_pan_start_time = time.time() - 1.0  # 1 second ago
        self.pan_manager._smooth_pan_duration = 0.5  # Should be complete
        self.pan_manager._smooth_pan_active = True
        
        with patch.object(self.pan_manager, '_smooth_pan_timer') as mock_timer:
            self.pan_manager._animate_smooth_pan()
            
            # Animation should be complete
            assert self.pan_manager.get_pan_offset() == target_offset
            assert not self.pan_manager.is_smooth_panning()
            mock_timer.stop.assert_called_once()
            
    def test_ease_out_cubic(self):
        """Test cubic ease-out function."""
        # Test edge cases
        assert self.pan_manager._ease_out_cubic(0.0) == 0.0
        assert self.pan_manager._ease_out_cubic(1.0) == 1.0
        
        # Test mid-point behavior
        mid_value = self.pan_manager._ease_out_cubic(0.5)
        assert 0.0 < mid_value < 1.0
        
        # Should ease out (slow at end)
        quarter = self.pan_manager._ease_out_cubic(0.25)
        three_quarter = self.pan_manager._ease_out_cubic(0.75)
        
        # Rate of change should be higher at the beginning
        assert quarter > 0.25 * three_quarter
        
    def test_apply_pan_constraints_no_bounds(self):
        """Test applying constraints without bounds."""
        constraints = PanConstraints(enable_bounds_checking=False)
        self.pan_manager.set_constraints(constraints)
        
        delta = Point(1000, 2000)
        result = self.pan_manager._apply_pan_constraints(delta)
        
        assert result == delta  # Should be unchanged
        
    def test_apply_pan_constraints_with_bounds(self):
        """Test applying constraints with bounds."""
        bounds = Rect(0, 0, 500, 400)
        constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True,
            elastic_bounds=False
        )
        self.pan_manager.set_constraints(constraints)
        
        # Set current offset near bounds
        self.pan_manager._pan_state.offset = Point(450, 350)
        
        # Try to pan beyond bounds
        delta = Point(100, 100)
        result = self.pan_manager._apply_pan_constraints(delta)
        
        # Delta should be reduced to respect bounds
        assert result.x < delta.x
        assert result.y < delta.y
        
    def test_apply_elastic_constraint(self):
        """Test elastic constraint application."""
        # Test value within bounds
        result = self.pan_manager._apply_elastic_constraint(50, 0, 100)
        assert result == 50
        
        # Test value below bounds
        result = self.pan_manager._apply_elastic_constraint(-20, 0, 100)
        assert result < 0  # Should be negative but closer to 0
        assert result > -20  # Should be less negative than input
        
        # Test value above bounds
        result = self.pan_manager._apply_elastic_constraint(120, 0, 100)
        assert result > 100  # Should be above bounds
        assert result < 120  # Should be less than input
        
    def test_calculate_gesture_quality(self):
        """Test gesture quality calculation."""
        # Set up gesture data
        self.pan_manager._pan_total_distance = 100.0
        self.pan_manager._velocity_history = [
            (1000.0, Point(50, 50)),
            (1000.1, Point(55, 55)),
            (1000.2, Point(60, 60))
        ]
        
        quality = self.pan_manager._calculate_gesture_quality(1.0)  # 1 second duration
        
        assert 0.0 <= quality <= 100.0
        
    def test_calculate_gesture_quality_edge_cases(self):
        """Test gesture quality calculation edge cases."""
        # Zero duration
        quality = self.pan_manager._calculate_gesture_quality(0.0)
        assert quality == 50.0  # Default value
        
        # Zero distance
        self.pan_manager._pan_total_distance = 0.0
        quality = self.pan_manager._calculate_gesture_quality(1.0)
        assert quality == 50.0  # Default value
        
    def test_calculate_speed_consistency(self):
        """Test speed consistency calculation."""
        # Set up consistent velocity history
        self.pan_manager._velocity_history = [
            (1000.0, Point(50, 50)),
            (1000.1, Point(50, 50)),
            (1000.2, Point(50, 50))
        ]
        
        consistency = self.pan_manager._calculate_speed_consistency()
        assert consistency > 90.0  # Should be very consistent
        
        # Set up inconsistent velocity history
        self.pan_manager._velocity_history = [
            (1000.0, Point(10, 10)),
            (1000.1, Point(100, 100)),
            (1000.2, Point(5, 5))
        ]
        
        consistency = self.pan_manager._calculate_speed_consistency()
        assert consistency < 50.0  # Should be inconsistent
        
    def test_calculate_speed_consistency_edge_cases(self):
        """Test speed consistency calculation edge cases."""
        # Empty history
        self.pan_manager._velocity_history = []
        consistency = self.pan_manager._calculate_speed_consistency()
        assert consistency == 75.0  # Default value
        
        # Insufficient history
        self.pan_manager._velocity_history = [(1000.0, Point(50, 50))]
        consistency = self.pan_manager._calculate_speed_consistency()
        assert consistency == 75.0  # Default value
        
    def test_update_coordinate_transform(self):
        """Test coordinate transform update."""
        offset = Point(100, 200)
        self.pan_manager.pan_to_offset(offset)
        
        # Should call set_pan_offset on coordinate transform
        self.mock_coordinate_transform.set_pan_offset.assert_called_with(offset)
        
    def test_update_performance_metrics(self):
        """Test performance metrics update."""
        operation_time = 0.005
        
        self.pan_manager._update_performance_metrics('test_operation', operation_time)
        
        assert len(self.pan_manager._operation_times) == 1
        assert self.pan_manager._operation_times[0] == operation_time
        assert 'test_operation' in self.pan_manager._performance_metrics


class TestPanManagerPerformance:
    """Test pan manager performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pan_manager = PanManager()
        
    def test_pan_operation_performance(self):
        """Test that pan operations meet performance targets."""
        start_time = time.time()
        
        # Perform 100 pan gestures
        for i in range(100):
            start_pos = Point(i, i)
            end_pos = Point(i + 50, i + 50)
            
            self.pan_manager.start_pan(start_pos)
            self.pan_manager.update_pan(end_pos)
            self.pan_manager.finish_pan()
            
        total_time = time.time() - start_time
        average_time = total_time / 300  # 3 operations per gesture
        
        # Should average less than 1ms per operation
        assert average_time < 0.001
        
    def test_momentum_frame_rate(self):
        """Test that momentum animation can maintain 60fps."""
        self.pan_manager._pan_state.velocity = Point(500, 300)
        
        frame_times = []
        
        # Simulate 60 momentum frames
        for _ in range(60):
            start_time = time.time()
            self.pan_manager._animate_momentum()
            frame_time = time.time() - start_time
            frame_times.append(frame_time)
            
        average_frame_time = sum(frame_times) / len(frame_times)
        
        # Each frame should take less than 16.67ms (60fps)
        assert average_frame_time < 0.0167
        
    def test_cache_efficiency(self):
        """Test cache efficiency with repeated patterns."""
        # Perform pan operations with repeated deltas
        deltas = [Point(10, 10), Point(-5, 5), Point(20, -10)]
        
        for _ in range(10):  # Repeat pattern 10 times
            for delta in deltas:
                self.pan_manager.pan_by_delta(delta)
                
        cache_stats = self.pan_manager._coordinate_cache.get_stats()
        
        # Should achieve reasonable hit rate
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hit_rate']
            assert hit_rate > 0.2  # At least 20% hit rate
            
    def test_memory_efficiency(self):
        """Test memory efficiency of pan operations."""
        # Perform many pan operations
        for i in range(1000):
            start_pos = Point(i, i)
            end_pos = Point(i + 10, i + 10)
            
            self.pan_manager.start_pan(start_pos)
            self.pan_manager.update_pan(end_pos)
            self.pan_manager.finish_pan()
            
        cache_stats = self.pan_manager._transformation_cache.get_stats()
        
        # Memory usage should be reasonable
        assert cache_stats['memory_usage'] < 5 * 1024 * 1024  # Less than 5MB


class TestPanManagerEdgeCases:
    """Test pan manager edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pan_manager = PanManager()
        
    def test_extreme_pan_distances(self):
        """Test handling of extreme pan distances."""
        # Very large pan distance
        start_pos = Point(0, 0)
        end_pos = Point(1e6, 1e6)
        
        self.pan_manager.start_pan(start_pos)
        self.pan_manager.update_pan(end_pos)
        
        # Should not crash
        offset = self.pan_manager.get_pan_offset()
        assert offset.x == 1e6
        assert offset.y == 1e6
        
    def test_rapid_pan_updates(self):
        """Test rapid pan updates."""
        start_pos = Point(0, 0)
        self.pan_manager.start_pan(start_pos)
        
        # Rapidly update pan position
        for i in range(100):
            pos = Point(i, i)
            self.pan_manager.update_pan(pos)
            
        # Should maintain consistency
        final_offset = self.pan_manager.get_pan_offset()
        assert final_offset.x == 99  # Last position - start position
        assert final_offset.y == 99
        
    def test_concurrent_pan_operations(self):
        """Test concurrent pan operations."""
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(50):
                    start_pos = Point(i, i)
                    end_pos = Point(i + 10, i + 10)
                    
                    manager = PanManager()  # Each thread gets its own manager
                    manager.start_pan(start_pos)
                    manager.update_pan(end_pos)
                    manager.finish_pan()
                    
                    results.append(manager.get_pan_offset())
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
        assert len(results) == 250  # 50 operations * 5 threads
        
    def test_pan_with_constraints_extreme_values(self):
        """Test pan with constraints and extreme values."""
        # Set very restrictive bounds
        bounds = Rect(-10, -10, 20, 20)
        constraints = PanConstraints(
            bounds=bounds,
            enable_bounds_checking=True,
            elastic_bounds=False
        )
        self.pan_manager.set_constraints(constraints)
        
        # Try to pan to extreme position
        extreme_offset = Point(10000, -5000)
        self.pan_manager.pan_to_offset(extreme_offset)
        
        # Should be clamped to bounds
        final_offset = self.pan_manager.get_pan_offset()
        assert bounds.left <= final_offset.x <= bounds.right
        assert bounds.top <= final_offset.y <= bounds.bottom
        
    def test_momentum_with_zero_velocity(self):
        """Test momentum animation with zero velocity."""
        self.pan_manager._pan_state.velocity = Point(0, 0)
        
        # Should stop immediately
        with patch.object(self.pan_manager, '_momentum_timer') as mock_timer:
            self.pan_manager._animate_momentum()
            mock_timer.stop.assert_called_once()
            
    def test_smooth_pan_without_target(self):
        """Test smooth pan animation without target."""
        self.pan_manager._smooth_pan_active = True
        self.pan_manager._smooth_pan_target = None
        
        # Should handle gracefully
        self.pan_manager._animate_smooth_pan()
        # Should not crash
        
    def test_velocity_clamping(self):
        """Test velocity clamping to max velocity."""
        start_pos = Point(0, 0)
        end_pos = Point(10000, 10000)  # Extreme distance
        
        with patch('time.time', side_effect=[1000.0, 1000.001]):  # Very short time
            self.pan_manager.start_pan(start_pos)
            self.pan_manager.update_pan(end_pos)
            
        velocity = self.pan_manager.get_pan_velocity()
        velocity_magnitude = math.sqrt(velocity.x ** 2 + velocity.y ** 2)
        
        # Should be clamped to max velocity
        assert velocity_magnitude <= self.pan_manager._pan_state.max_velocity


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.torematrix.ui.viewer.pan", "--cov-report=term-missing"])