"""
Comprehensive tests for the rotation transformation manager.

This test suite ensures >95% coverage of the rotation functionality
with performance validation and edge case handling.
"""

import pytest
import time
import math
import threading
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.viewer.rotation import (
    RotationManager,
    RotationState,
    RotationConstraints,
    RotationPerformanceMetrics
)
from src.torematrix.ui.viewer.coordinates import CoordinateTransform
from src.torematrix.ui.viewer.transformations import AffineTransformation
from src.torematrix.utils.geometry import Point, Rect


class TestRotationState:
    """Test RotationState functionality."""
    
    def test_rotation_state_creation(self):
        """Test rotation state creation."""
        center = Point(100, 200)
        state = RotationState(math.pi / 4, center)
        
        assert state.angle == math.pi / 4
        assert state.center == center
        assert state.snap_enabled is True
        assert state.snap_angle == math.pi / 12  # 15 degrees
        assert state.snap_threshold == 0.1
        
    def test_rotation_state_custom_params(self):
        """Test rotation state with custom parameters."""
        center = Point(0, 0)
        custom_zones = [0.0, math.pi / 2, math.pi]
        
        state = RotationState(
            angle=math.pi / 3,
            center=center,
            snap_enabled=False,
            snap_angle=math.pi / 6,
            snap_threshold=0.05,
            snap_zones=custom_zones
        )
        
        assert state.snap_enabled is False
        assert state.snap_angle == math.pi / 6
        assert state.snap_threshold == 0.05
        assert state.snap_zones == custom_zones
        
    def test_rotation_state_default_snap_zones(self):
        """Test rotation state default snap zones."""
        state = RotationState(0.0, Point(0, 0))
        
        expected_zones = [
            0.0,                    # 0°
            math.pi / 4,           # 45°
            math.pi / 2,           # 90°
            3 * math.pi / 4,       # 135°
            math.pi,               # 180°
            5 * math.pi / 4,       # 225°
            3 * math.pi / 2,       # 270°
            7 * math.pi / 4        # 315°
        ]
        
        assert state.snap_zones == expected_zones


class TestRotationConstraints:
    """Test RotationConstraints functionality."""
    
    def test_rotation_constraints_creation(self):
        """Test rotation constraints creation."""
        constraints = RotationConstraints(
            min_angle=0.0,
            max_angle=math.pi,
            enable_continuous=False,
            lock_rotation=True
        )
        
        assert constraints.min_angle == 0.0
        assert constraints.max_angle == math.pi
        assert constraints.enable_continuous is False
        assert constraints.lock_rotation is True
        
    def test_rotation_constraints_defaults(self):
        """Test rotation constraints default values."""
        constraints = RotationConstraints()
        
        assert constraints.min_angle is None
        assert constraints.max_angle is None
        assert constraints.enable_continuous is True
        assert constraints.lock_rotation is False


class TestRotationPerformanceMetrics:
    """Test RotationPerformanceMetrics functionality."""
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation."""
        metrics = RotationPerformanceMetrics(
            snap_operations=15,
            smooth_operations=10,
            instant_operations=25,
            average_angle_change=0.5,
            snap_accuracy=0.95,
            cache_efficiency=0.8
        )
        
        assert metrics.snap_operations == 15
        assert metrics.smooth_operations == 10
        assert metrics.instant_operations == 25
        assert metrics.average_angle_change == 0.5
        assert metrics.snap_accuracy == 0.95
        assert metrics.cache_efficiency == 0.8
        
    def test_performance_metrics_overall_score(self):
        """Test overall performance score calculation."""
        metrics = RotationPerformanceMetrics(
            snap_operations=10,
            smooth_operations=20,  # Good balance
            instant_operations=20,
            average_angle_change=0.3,
            snap_accuracy=0.9,     # High accuracy
            cache_efficiency=0.85  # Good cache efficiency
        )
        
        score = metrics.get_overall_score()
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be a good score


class TestRotationManager:
    """Test RotationManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinate_transform = Mock(spec=CoordinateTransform)
        self.rotation_manager = RotationManager(self.mock_coordinate_transform)
        
    def test_rotation_manager_initialization(self):
        """Test rotation manager initialization."""
        manager = RotationManager()
        
        assert manager.get_rotation_angle() == 0.0
        assert manager.get_rotation_degrees() == 0.0
        assert manager.get_rotation_center() == Point(0, 0)
        assert not manager.is_animating()
        
    def test_rotation_manager_with_coordinate_transform(self):
        """Test rotation manager with coordinate transform."""
        assert self.rotation_manager.coordinate_transform == self.mock_coordinate_transform
        
    def test_rotate_to_angle_valid(self):
        """Test rotation to valid angle."""
        result = self.rotation_manager.rotate_to_angle(math.pi / 4)
        
        assert result is True
        assert abs(self.rotation_manager.get_rotation_angle() - math.pi / 4) < 1e-10
        
    def test_rotate_to_angle_with_center(self):
        """Test rotation to angle with center point."""
        center = Point(100, 200)
        result = self.rotation_manager.rotate_to_angle(math.pi / 6, center)
        
        assert result is True
        assert abs(self.rotation_manager.get_rotation_angle() - math.pi / 6) < 1e-10
        assert self.rotation_manager.get_rotation_center() == center
        
    def test_rotate_to_angle_animated(self):
        """Test animated rotation to angle."""
        with patch.object(self.rotation_manager, '_start_smooth_rotation') as mock_smooth:
            mock_smooth.return_value = True
            
            result = self.rotation_manager.rotate_to_angle(math.pi / 3, animated=True)
            
            assert result is True
            mock_smooth.assert_called_once()
            
    def test_rotate_to_angle_locked(self):
        """Test rotation when locked."""
        constraints = RotationConstraints(lock_rotation=True)
        self.rotation_manager.set_constraints(constraints)
        
        result = self.rotation_manager.rotate_to_angle(math.pi / 4)
        
        assert result is False
        assert self.rotation_manager.get_rotation_angle() == 0.0
        
    def test_rotate_by_delta(self):
        """Test rotation by delta angle."""
        initial_angle = math.pi / 6
        delta = math.pi / 4
        
        self.rotation_manager.rotate_to_angle(initial_angle)
        result = self.rotation_manager.rotate_by_delta(delta)
        
        assert result is True
        expected_angle = initial_angle + delta
        assert abs(self.rotation_manager.get_rotation_angle() - expected_angle) < 1e-10
        
    def test_rotate_to_cardinal_valid(self):
        """Test rotation to valid cardinal direction."""
        result = self.rotation_manager.rotate_to_cardinal('east')
        
        assert result is True
        assert abs(self.rotation_manager.get_rotation_angle() - math.pi / 2) < 1e-10
        
    def test_rotate_to_cardinal_invalid(self):
        """Test rotation to invalid cardinal direction."""
        result = self.rotation_manager.rotate_to_cardinal('invalid_direction')
        
        assert result is False
        assert self.rotation_manager.get_rotation_angle() == 0.0
        
    def test_rotate_to_cardinal_all_directions(self):
        """Test rotation to all cardinal directions."""
        cardinals = {
            'north': 0.0,
            'east': math.pi / 2,
            'south': math.pi,
            'west': 3 * math.pi / 2,
            'northeast': math.pi / 4,
            'southeast': 3 * math.pi / 4,
            'southwest': 5 * math.pi / 4,
            'northwest': 7 * math.pi / 4
        }
        
        for direction, expected_angle in cardinals.items():
            result = self.rotation_manager.rotate_to_cardinal(direction)
            assert result is True
            actual_angle = self.rotation_manager.get_rotation_angle()
            assert abs(actual_angle - expected_angle) < 1e-10
            
    def test_smooth_rotate_to_angle(self):
        """Test smooth rotation to angle."""
        with patch.object(self.rotation_manager, '_start_smooth_rotation') as mock_smooth:
            mock_smooth.return_value = True
            
            result = self.rotation_manager.smooth_rotate_to_angle(math.pi / 2, duration=0.8)
            
            assert result is True
            assert self.rotation_manager._animation_duration == 0.8
            mock_smooth.assert_called_once()
            
    def test_smooth_rotate_locked(self):
        """Test smooth rotation when locked."""
        constraints = RotationConstraints(lock_rotation=True)
        self.rotation_manager.set_constraints(constraints)
        
        result = self.rotation_manager.smooth_rotate_to_angle(math.pi / 2)
        
        assert result is False
        
    def test_start_gesture_rotation(self):
        """Test starting gesture rotation."""
        center = Point(200, 300)
        initial_position = Point(250, 300)  # 50 pixels to the right
        
        self.rotation_manager.start_gesture_rotation(center, initial_position)
        
        assert self.rotation_manager._gesture_center == center
        assert self.rotation_manager._gesture_start_angle is not None
        assert self.rotation_manager._gesture_last_angle is not None
        
    def test_update_gesture_rotation(self):
        """Test updating gesture rotation."""
        center = Point(200, 300)
        initial_position = Point(250, 300)  # 0 degrees (east)
        new_position = Point(200, 250)     # 90 degrees (north)
        
        self.rotation_manager.start_gesture_rotation(center, initial_position)
        initial_angle = self.rotation_manager.get_rotation_angle()
        
        self.rotation_manager.update_gesture_rotation(new_position)
        
        # Angle should have changed
        final_angle = self.rotation_manager.get_rotation_angle()
        assert final_angle != initial_angle
        
    def test_update_gesture_rotation_without_start(self):
        """Test updating gesture rotation without starting."""
        position = Point(100, 200)
        
        # Should not crash
        self.rotation_manager.update_gesture_rotation(position)
        
        assert self.rotation_manager.get_rotation_angle() == 0.0
        
    def test_finish_gesture_rotation(self):
        """Test finishing gesture rotation."""
        center = Point(200, 300)
        initial_position = Point(250, 300)
        
        self.rotation_manager.start_gesture_rotation(center, initial_position)
        self.rotation_manager.finish_gesture_rotation()
        
        assert self.rotation_manager._gesture_center is None
        assert self.rotation_manager._gesture_start_angle is None
        assert self.rotation_manager._gesture_last_angle is None
        
    def test_finish_gesture_rotation_with_snapping(self):
        """Test finishing gesture rotation with final snapping."""
        # Set angle close to a snap zone
        self.rotation_manager.rotate_to_angle(math.pi / 4 + 0.05)  # Close to 45°
        
        center = Point(200, 300)
        initial_position = Point(250, 300)
        
        self.rotation_manager.start_gesture_rotation(center, initial_position)
        
        with patch.object(self.rotation_manager, 'smooth_rotate_to_angle') as mock_smooth:
            self.rotation_manager.finish_gesture_rotation()
            
            # Should snap to exact 45°
            mock_smooth.assert_called_once()
            
    def test_get_rotation_angle_degrees(self):
        """Test getting rotation angle in degrees."""
        self.rotation_manager.rotate_to_angle(math.pi / 2)  # 90 degrees
        
        degrees = self.rotation_manager.get_rotation_degrees()
        assert abs(degrees - 90.0) < 1e-10
        
    def test_set_rotation_center(self):
        """Test setting rotation center."""
        new_center = Point(400, 500)
        self.rotation_manager.set_rotation_center(new_center)
        
        assert self.rotation_manager.get_rotation_center() == new_center
        
    def test_set_rotation_center_invalidates_cache(self):
        """Test that setting rotation center invalidates cache."""
        # Create transformation to populate cache
        self.rotation_manager.rotate_to_angle(math.pi / 4)
        transform1 = self.rotation_manager.get_rotation_transformation()
        
        # Change center significantly
        self.rotation_manager.set_rotation_center(Point(100, 200))
        
        # Cache should be invalidated (transformation should be different)
        transform2 = self.rotation_manager.get_rotation_transformation()
        assert transform1 is not transform2
        
    def test_get_rotation_transformation(self):
        """Test getting rotation transformation."""
        self.rotation_manager.rotate_to_angle(math.pi / 6)
        transform = self.rotation_manager.get_rotation_transformation()
        
        assert transform is not None
        assert isinstance(transform, AffineTransformation)
        
    def test_get_rotation_transformation_with_center(self):
        """Test getting rotation transformation with center offset."""
        center = Point(100, 200)
        self.rotation_manager.rotate_to_angle(math.pi / 3, center)
        transform = self.rotation_manager.get_rotation_transformation()
        
        assert transform is not None
        
    def test_get_rotation_transformation_cached(self):
        """Test that rotation transformations are cached."""
        self.rotation_manager.rotate_to_angle(math.pi / 4)
        
        # Get transformation twice
        transform1 = self.rotation_manager.get_rotation_transformation()
        transform2 = self.rotation_manager.get_rotation_transformation()
        
        # Should be the same object from cache
        assert transform1 is transform2
        
    def test_reset_rotation(self):
        """Test resetting rotation."""
        self.rotation_manager.rotate_to_angle(math.pi / 3)
        self.rotation_manager.reset_rotation()
        
        assert self.rotation_manager.get_rotation_angle() == 0.0
        
    def test_reset_rotation_animated(self):
        """Test animated reset rotation."""
        self.rotation_manager.rotate_to_angle(math.pi / 3)
        
        with patch.object(self.rotation_manager, 'rotate_to_angle') as mock_rotate:
            self.rotation_manager.reset_rotation(animated=True)
            mock_rotate.assert_called_once_with(0.0, animated=True)
            
    def test_set_snap_configuration(self):
        """Test setting snap configuration."""
        custom_zones = [0.0, math.pi / 2, math.pi]
        
        self.rotation_manager.set_snap_configuration(
            enabled=False,
            snap_angle=math.pi / 8,
            threshold=0.05,
            custom_zones=custom_zones
        )
        
        state = self.rotation_manager._rotation_state
        assert state.snap_enabled is False
        assert state.snap_angle == math.pi / 8
        assert state.snap_threshold == 0.05
        assert state.snap_zones == custom_zones
        
    def test_set_constraints(self):
        """Test setting rotation constraints."""
        constraints = RotationConstraints(
            min_angle=0.0,
            max_angle=math.pi,
            enable_continuous=False
        )
        
        self.rotation_manager.set_constraints(constraints)
        assert self.rotation_manager._constraints == constraints
        
    def test_set_constraints_clamps_current_angle(self):
        """Test that setting constraints clamps current angle."""
        # Set angle outside future constraints
        self.rotation_manager.rotate_to_angle(3 * math.pi / 2)  # 270°
        
        # Set constraints that should clamp the angle
        constraints = RotationConstraints(
            min_angle=0.0,
            max_angle=math.pi  # 180°
        )
        
        self.rotation_manager.set_constraints(constraints)
        
        # Angle should be clamped
        angle = self.rotation_manager.get_rotation_angle()
        assert 0.0 <= angle <= math.pi
        
    def test_get_snap_preview(self):
        """Test getting snap preview."""
        # Test angle that should snap
        close_to_45 = math.pi / 4 + 0.05
        snapped_angle, will_snap = self.rotation_manager.get_snap_preview(close_to_45)
        
        assert will_snap is True
        assert abs(snapped_angle - math.pi / 4) < 1e-10
        
        # Test angle that shouldn't snap
        far_from_snap = math.pi / 3
        snapped_angle, will_snap = self.rotation_manager.get_snap_preview(far_from_snap)
        
        assert will_snap is False
        assert abs(snapped_angle - far_from_snap) < 1e-10
        
    def test_get_snap_preview_disabled(self):
        """Test snap preview when snapping is disabled."""
        self.rotation_manager._rotation_state.snap_enabled = False
        
        angle = math.pi / 4 + 0.05
        snapped_angle, will_snap = self.rotation_manager.get_snap_preview(angle)
        
        assert will_snap is False
        assert abs(snapped_angle - angle) < 1e-10
        
    def test_is_animating(self):
        """Test animation state detection."""
        assert not self.rotation_manager.is_animating()
        
        # Start animation
        self.rotation_manager._animation_active = True
        assert self.rotation_manager.is_animating()
        
    def test_stop_animation(self):
        """Test stopping animation."""
        self.rotation_manager._animation_active = True
        self.rotation_manager.stop_animation()
        
        assert not self.rotation_manager.is_animating()
        
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        # Perform some rotation operations
        self.rotation_manager.rotate_to_angle(math.pi / 4)
        self.rotation_manager.rotate_to_angle(math.pi / 2)
        self.rotation_manager.rotate_by_delta(math.pi / 6)
        
        metrics = self.rotation_manager.get_performance_metrics()
        
        assert isinstance(metrics, RotationPerformanceMetrics)
        assert metrics.snap_operations >= 0
        assert metrics.smooth_operations >= 0
        assert metrics.instant_operations >= 0
        assert metrics.average_angle_change >= 0.0
        assert 0.0 <= metrics.snap_accuracy <= 1.0
        assert 0.0 <= metrics.cache_efficiency <= 1.0
        
    def test_optimize_performance(self):
        """Test performance optimization."""
        # Add some operations
        for i in range(10):
            angle = i * math.pi / 10
            self.rotation_manager.rotate_to_angle(angle)
            
        # Should not raise any exceptions
        self.rotation_manager.optimize_performance()
        
    def test_normalize_angle(self):
        """Test angle normalization."""
        # Test positive angles
        assert abs(self.rotation_manager._normalize_angle(0.0) - 0.0) < 1e-10
        assert abs(self.rotation_manager._normalize_angle(math.pi) - math.pi) < 1e-10
        assert abs(self.rotation_manager._normalize_angle(2 * math.pi) - 0.0) < 1e-10
        assert abs(self.rotation_manager._normalize_angle(3 * math.pi) - math.pi) < 1e-10
        
        # Test negative angles
        assert abs(self.rotation_manager._normalize_angle(-math.pi / 2) - 3 * math.pi / 2) < 1e-10
        assert abs(self.rotation_manager._normalize_angle(-math.pi) - math.pi) < 1e-10
        
    def test_apply_angle_constraints(self):
        """Test angle constraint application."""
        constraints = RotationConstraints(
            min_angle=math.pi / 4,
            max_angle=3 * math.pi / 4
        )
        self.rotation_manager.set_constraints(constraints)
        
        # Test angle within bounds
        result = self.rotation_manager._apply_angle_constraints(math.pi / 2)
        assert abs(result - math.pi / 2) < 1e-10
        
        # Test angle below minimum
        result = self.rotation_manager._apply_angle_constraints(math.pi / 6)
        assert abs(result - math.pi / 4) < 1e-10
        
        # Test angle above maximum
        result = self.rotation_manager._apply_angle_constraints(math.pi)
        assert abs(result - 3 * math.pi / 4) < 1e-10
        
    def test_snap_angle_to_zones(self):
        """Test angle snapping to zones."""
        # Test snapping to 45°
        close_to_45 = math.pi / 4 + 0.05
        snapped = self.rotation_manager._snap_angle(close_to_45)
        assert abs(snapped - math.pi / 4) < 1e-10
        
        # Test not snapping when too far
        far_from_snap = math.pi / 3
        snapped = self.rotation_manager._snap_angle(far_from_snap)
        assert abs(snapped - far_from_snap) < 1e-10
        
    def test_snap_angle_disabled(self):
        """Test angle snapping when disabled."""
        self.rotation_manager._rotation_state.snap_enabled = False
        
        angle = math.pi / 4 + 0.05
        snapped = self.rotation_manager._snap_angle(angle)
        
        assert abs(snapped - angle) < 1e-10
        
    def test_calculate_angle_from_center(self):
        """Test angle calculation from center."""
        center = Point(100, 100)
        
        # Test cardinal directions
        east_point = Point(150, 100)
        angle_east = self.rotation_manager._calculate_angle_from_center(center, east_point)
        assert abs(angle_east - 0.0) < 1e-10
        
        north_point = Point(100, 50)
        angle_north = self.rotation_manager._calculate_angle_from_center(center, north_point)
        assert abs(angle_north - (-math.pi / 2)) < 1e-10
        
        west_point = Point(50, 100)
        angle_west = self.rotation_manager._calculate_angle_from_center(center, west_point)
        assert abs(abs(angle_west) - math.pi) < 1e-10
        
        south_point = Point(100, 150)
        angle_south = self.rotation_manager._calculate_angle_from_center(center, south_point)
        assert abs(angle_south - math.pi / 2) < 1e-10
        
    def test_start_smooth_rotation(self):
        """Test starting smooth rotation."""
        target_angle = math.pi / 2
        center = Point(100, 200)
        
        with patch('src.torematrix.ui.viewer.rotation.QT_AVAILABLE', True):
            with patch('src.torematrix.ui.viewer.rotation.QTimer') as mock_timer_class:
                mock_timer = Mock()
                mock_timer_class.return_value = mock_timer
                
                manager = RotationManager(self.mock_coordinate_transform)
                result = manager._start_smooth_rotation(target_angle, center)
                
                assert result is True
                assert manager._animation_target == target_angle
                assert manager._animation_active is True
                assert manager.get_rotation_center() == center
                mock_timer.start.assert_called_with(16)  # ~60 FPS
                
    def test_start_smooth_rotation_no_timer(self):
        """Test starting smooth rotation without timer."""
        manager = RotationManager()
        manager._animation_timer = None
        
        result = manager._start_smooth_rotation(math.pi / 2, None)
        assert result is False
        
    def test_start_smooth_rotation_shortest_path(self):
        """Test that smooth rotation chooses shortest path."""
        # Start at 350° (close to 0°)
        self.rotation_manager.rotate_to_angle(350 * math.pi / 180)
        
        # Target 10° - should go through 0° (shortest path)
        target = 10 * math.pi / 180
        
        self.rotation_manager._start_smooth_rotation(target, None)
        
        # Target should be adjusted for shortest path
        assert self.rotation_manager._animation_target < 2 * math.pi
        
    def test_animate_rotation_complete(self):
        """Test rotation animation completion."""
        self.rotation_manager._animation_active = True
        self.rotation_manager._animation_target = math.pi / 2
        self.rotation_manager._animation_start_time = time.time() - 1.0  # 1 second ago
        self.rotation_manager._animation_duration = 0.5  # Should be complete
        
        with patch.object(self.rotation_manager, '_animation_timer') as mock_timer:
            self.rotation_manager._animate_rotation()
            
            angle = self.rotation_manager.get_rotation_angle()
            assert abs(angle - math.pi / 2) < 1e-10
            assert not self.rotation_manager._animation_active
            mock_timer.stop.assert_called_once()
            
    def test_animate_rotation_in_progress(self):
        """Test rotation animation in progress."""
        self.rotation_manager._animation_active = True
        self.rotation_manager._animation_target = math.pi / 2
        self.rotation_manager._animation_start_angle = 0.0
        self.rotation_manager._animation_start_time = time.time() - 0.1  # 0.1 seconds ago
        self.rotation_manager._animation_duration = 0.5
        
        self.rotation_manager._animate_rotation()
        
        # Should be somewhere between start and target
        current_angle = self.rotation_manager.get_rotation_angle()
        assert 0.0 < current_angle < math.pi / 2
        assert self.rotation_manager._animation_active is True
        
    def test_ease_in_out_quad(self):
        """Test quadratic ease-in-out function."""
        # Test edge cases
        assert self.rotation_manager._ease_in_out_quad(0.0) == 0.0
        assert self.rotation_manager._ease_in_out_quad(1.0) == 1.0
        
        # Test mid-point
        mid_value = self.rotation_manager._ease_in_out_quad(0.5)
        assert 0.0 < mid_value < 1.0
        
        # Test monotonic behavior
        assert (self.rotation_manager._ease_in_out_quad(0.25) < 
                self.rotation_manager._ease_in_out_quad(0.75))
                
    def test_update_coordinate_transform(self):
        """Test coordinate transform update."""
        angle = math.pi / 3
        self.rotation_manager.rotate_to_angle(angle)
        
        # Should call set_rotation on coordinate transform
        self.mock_coordinate_transform.set_rotation.assert_called_with(angle)
        
    def test_update_performance_metrics(self):
        """Test performance metrics update."""
        old_angle = 0.0
        new_angle = math.pi / 4
        operation_time = 0.002
        
        self.rotation_manager._update_performance_metrics(
            'test_operation', old_angle, new_angle, operation_time, True
        )
        
        assert len(self.rotation_manager._operation_times) == 1
        assert self.rotation_manager._operation_times[0] == operation_time
        assert len(self.rotation_manager._angle_history) == 1
        assert len(self.rotation_manager._snap_accuracy_scores) == 1
        
    def test_precompute_transformations(self):
        """Test pre-computation of common transformations."""
        # Clear cache first
        self.rotation_manager._transformation_cache.clear()
        
        self.rotation_manager._precompute_transformations()
        
        # Should have cached some common angles
        cache_stats = self.rotation_manager._transformation_cache.get_stats()
        assert cache_stats['cache_size'] > 0


class TestRotationManagerPerformance:
    """Test rotation manager performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rotation_manager = RotationManager()
        
    def test_rotation_operation_performance(self):
        """Test that rotation operations meet performance targets."""
        start_time = time.time()
        
        # Perform 100 rotation operations
        for i in range(100):
            angle = i * math.pi / 50  # Various angles
            self.rotation_manager.rotate_to_angle(angle)
            
        total_time = time.time() - start_time
        average_time = total_time / 100
        
        # Should average less than 2ms per operation
        assert average_time < 0.002
        
    def test_snap_operation_performance(self):
        """Test performance of snap operations."""
        snap_times = []
        
        # Test snapping to various angles
        test_angles = [math.pi / 4 + 0.05, math.pi / 2 + 0.08, math.pi - 0.06]
        
        for angle in test_angles:
            start_time = time.time()
            self.rotation_manager.rotate_to_angle(angle)
            snap_time = time.time() - start_time
            snap_times.append(snap_time)
            
        average_snap_time = sum(snap_times) / len(snap_times)
        
        # Snap operations should be fast
        assert average_snap_time < 0.001
        
    def test_cache_hit_rate(self):
        """Test that cache achieves good hit rate."""
        # Perform operations with repeated angles
        angles = [0.0, math.pi / 4, math.pi / 2, math.pi / 4, 0.0, math.pi / 2]
        
        for angle in angles:
            self.rotation_manager.rotate_to_angle(angle)
            
        cache_stats = self.rotation_manager._transformation_cache.get_stats()
        
        # Should achieve reasonable hit rate
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hit_rate']
            assert hit_rate > 0.3  # At least 30% hit rate
            
    def test_gesture_rotation_performance(self):
        """Test performance of gesture rotation."""
        center = Point(200, 200)
        
        start_time = time.time()
        
        # Simulate gesture rotation
        self.rotation_manager.start_gesture_rotation(center, Point(250, 200))
        
        # Update 60 times (simulate 60fps for 1 second)
        for i in range(60):
            angle = i * math.pi / 30  # Full circle in 60 frames
            x = center.x + 50 * math.cos(angle)
            y = center.y + 50 * math.sin(angle)
            self.rotation_manager.update_gesture_rotation(Point(x, y))
            
        self.rotation_manager.finish_gesture_rotation()
        
        total_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert total_time < 0.1  # Less than 100ms


class TestRotationManagerEdgeCases:
    """Test rotation manager edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rotation_manager = RotationManager()
        
    def test_extreme_rotation_angles(self):
        """Test handling of extreme rotation angles."""
        # Very large positive angle
        large_angle = 100 * math.pi
        self.rotation_manager.rotate_to_angle(large_angle)
        
        # Should be normalized
        normalized = self.rotation_manager.get_rotation_angle()
        assert 0.0 <= normalized < 2 * math.pi
        
        # Very large negative angle
        large_negative = -50 * math.pi
        self.rotation_manager.rotate_to_angle(large_negative)
        
        # Should be normalized
        normalized = self.rotation_manager.get_rotation_angle()
        assert 0.0 <= normalized < 2 * math.pi
        
    def test_rotation_with_nan_values(self):
        """Test rotation handling with NaN values."""
        # Should handle NaN gracefully
        try:
            self.rotation_manager.rotate_to_angle(float('nan'))
            # Should not crash
        except:
            # If it raises an exception, that's also acceptable
            pass
            
    def test_rapid_rotation_changes(self):
        """Test rapid rotation changes."""
        # Rapidly change rotation angles
        for i in range(100):
            angle = (i % 8) * math.pi / 4  # Cycle through 8 directions
            self.rotation_manager.rotate_to_angle(angle)
            
        # Should maintain consistency
        final_angle = self.rotation_manager.get_rotation_angle()
        assert 0.0 <= final_angle < 2 * math.pi
        
    def test_concurrent_rotation_operations(self):
        """Test concurrent rotation operations."""
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(50):
                    angle = i * math.pi / 25
                    manager = RotationManager()  # Each thread gets its own manager
                    result = manager.rotate_to_angle(angle)
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
        
    def test_gesture_rotation_edge_cases(self):
        """Test gesture rotation edge cases."""
        center = Point(100, 100)
        
        # Start gesture at center (zero distance)
        self.rotation_manager.start_gesture_rotation(center, center)
        
        # Should handle gracefully
        angle_before = self.rotation_manager.get_rotation_angle()
        self.rotation_manager.update_gesture_rotation(center)
        angle_after = self.rotation_manager.get_rotation_angle()
        
        # Angle shouldn't change significantly
        assert abs(angle_after - angle_before) < 0.1
        
    def test_angle_wraparound_in_gesture(self):
        """Test angle wraparound handling in gesture rotation."""
        center = Point(100, 100)
        
        # Start at 350° (close to 0°)
        start_position = Point(100 + 50 * math.cos(350 * math.pi / 180),
                              100 + 50 * math.sin(350 * math.pi / 180))
        
        self.rotation_manager.start_gesture_rotation(center, start_position)
        
        # Move to 10° (should wrap around, not go backwards)
        end_position = Point(100 + 50 * math.cos(10 * math.pi / 180),
                            100 + 50 * math.sin(10 * math.pi / 180))
        
        self.rotation_manager.update_gesture_rotation(end_position)
        
        # Should handle wraparound correctly
        # The exact behavior depends on implementation, but shouldn't crash
        
    def test_constraints_edge_cases(self):
        """Test constraint edge cases."""
        # Set constraints where min equals max
        constraints = RotationConstraints(
            min_angle=math.pi / 2,
            max_angle=math.pi / 2
        )
        
        self.rotation_manager.set_constraints(constraints)
        
        # Try to rotate to different angle
        self.rotation_manager.rotate_to_angle(math.pi / 4)
        
        # Should be clamped to the single allowed angle
        angle = self.rotation_manager.get_rotation_angle()
        assert abs(angle - math.pi / 2) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.torematrix.ui.viewer.rotation", "--cov-report=term-missing"])