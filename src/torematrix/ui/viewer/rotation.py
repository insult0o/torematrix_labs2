"""
High-performance rotation transformation manager with angle snapping.

This module provides optimized rotation operations with smooth animations,
angle snapping, and performance monitoring for the document viewer.
"""

from typing import Tuple, Optional, List, Dict, Callable, Union
from dataclasses import dataclass
import math
import time

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    from PyQt6.QtGui import QMouseEvent
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Fallback classes for testing
    class QObject:
        pass
    def pyqtSignal(*args):
        pass

from .coordinates import CoordinateTransform
from .transformations import AffineTransformation
from .cache import TransformationCache, CoordinateCache
from ...utils.geometry import Point, Rect


@dataclass
class RotationState:
    """Current rotation state with snapping configuration."""
    angle: float  # In radians
    center: Point
    snap_enabled: bool = True
    snap_angle: float = math.pi / 12  # 15 degrees
    snap_threshold: float = 0.1  # Radians
    snap_zones: List[float] = None  # Custom snap angles
    
    def __post_init__(self):
        """Initialize default snap zones."""
        if self.snap_zones is None:
            # Default snap zones: 0°, 90°, 180°, 270°, and 45° increments
            self.snap_zones = [
                0.0,                    # 0°
                math.pi / 4,           # 45°
                math.pi / 2,           # 90°
                3 * math.pi / 4,       # 135°
                math.pi,               # 180°
                5 * math.pi / 4,       # 225°
                3 * math.pi / 2,       # 270°
                7 * math.pi / 4        # 315°
            ]


@dataclass
class RotationConstraints:
    """Rotation operation constraints."""
    min_angle: Optional[float] = None  # Minimum rotation angle
    max_angle: Optional[float] = None  # Maximum rotation angle
    enable_continuous: bool = True     # Allow continuous rotation (360°+)
    lock_rotation: bool = False        # Disable all rotation


@dataclass
class RotationPerformanceMetrics:
    """Rotation performance tracking."""
    snap_operations: int
    smooth_operations: int
    instant_operations: int
    average_angle_change: float
    snap_accuracy: float  # How often snapping hits intended target
    cache_efficiency: float
    
    def get_overall_score(self) -> float:
        """Calculate overall performance score (0-1)."""
        snap_score = min(1.0, self.snap_accuracy)
        cache_score = self.cache_efficiency
        operation_balance = min(1.0, self.smooth_operations / max(1, self.instant_operations))
        
        return (snap_score + cache_score + operation_balance) / 3.0


class RotationManager(QObject):
    """High-performance rotation transformation manager with advanced snapping."""
    
    # Signals
    rotation_changed = pyqtSignal(float)  # angle in radians
    rotation_started = pyqtSignal(Point)  # center
    rotation_finished = pyqtSignal(float)  # final_angle
    snap_triggered = pyqtSignal(float, float)  # from_angle, to_angle
    performance_updated = pyqtSignal(dict)  # performance_metrics
    
    def __init__(self, coordinate_transform: Optional[CoordinateTransform] = None):
        super().__init__()
        self.coordinate_transform = coordinate_transform
        self._rotation_state = RotationState(0.0, Point(0, 0))
        self._constraints = RotationConstraints()
        
        # High-performance caching
        self._transformation_cache = TransformationCache(max_size=200)
        self._coordinate_cache = CoordinateCache(max_entries=2000)
        
        # Animation system
        if QT_AVAILABLE:
            self._animation_timer = QTimer()
            self._animation_timer.timeout.connect(self._animate_rotation)
        else:
            self._animation_timer = None
            
        # Animation state
        self._animation_active = False
        self._animation_target = 0.0
        self._animation_start_angle = 0.0
        self._animation_start_time = 0.0
        self._animation_duration = 0.5
        
        # Gesture tracking for rotation input
        self._gesture_start_angle: Optional[float] = None
        self._gesture_last_angle: Optional[float] = None
        self._gesture_center: Optional[Point] = None
        self._gesture_start_time: float = 0.0
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        self._angle_history: List[Tuple[float, float]] = []  # (timestamp, angle)
        self._operation_times: List[float] = []
        self._snap_accuracy_scores: List[float] = []
        
        # Optimization settings
        self._enable_performance_profiling = True
        self._precompute_common_angles = True
        
        # Pre-compute common rotation angles
        if self._precompute_common_angles:
            self._precompute_transformations()
        
    def rotate_to_angle(self, angle: float, center: Optional[Point] = None, 
                       animated: bool = False) -> bool:
        """Rotate to specific angle with optional animation."""
        if self._constraints.lock_rotation:
            return False
            
        start_time = time.time() if self._enable_performance_profiling else 0.0
        
        # Normalize and constrain angle
        normalized_angle = self._normalize_angle(angle)
        constrained_angle = self._apply_angle_constraints(normalized_angle)
        
        # Apply snapping if enabled
        final_angle = constrained_angle
        snap_applied = False
        if self._rotation_state.snap_enabled:
            snapped_angle = self._snap_angle(constrained_angle)
            if snapped_angle != constrained_angle:
                final_angle = snapped_angle
                snap_applied = True
                self.snap_triggered.emit(constrained_angle, snapped_angle)
                
        old_angle = self._rotation_state.angle
        
        if center:
            self._rotation_state.center = center
            
        if animated and self._animation_timer is not None:
            return self._start_smooth_rotation(final_angle, center)
        else:
            # Instant rotation
            self._rotation_state.angle = final_angle
            self._update_coordinate_transform()
            self.rotation_changed.emit(self._rotation_state.angle)
            
        # Update performance metrics
        if self._enable_performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics(
                'snap_rotate' if snap_applied else 'rotate_to_angle', 
                old_angle, final_angle, operation_time, snap_applied
            )
        
        return True
        
    def rotate_by_delta(self, delta_angle: float, center: Optional[Point] = None, 
                       animated: bool = False) -> bool:
        """Rotate by delta angle."""
        new_angle = self._rotation_state.angle + delta_angle
        return self.rotate_to_angle(new_angle, center, animated)
        
    def rotate_to_cardinal(self, cardinal: str, animated: bool = False) -> bool:
        """Rotate to cardinal direction (north, east, south, west)."""
        cardinal_angles = {
            'north': 0.0,
            'east': math.pi / 2,
            'south': math.pi,
            'west': 3 * math.pi / 2,
            'northeast': math.pi / 4,
            'southeast': 3 * math.pi / 4,
            'southwest': 5 * math.pi / 4,
            'northwest': 7 * math.pi / 4
        }
        
        angle = cardinal_angles.get(cardinal.lower())
        if angle is None:
            return False
            
        return self.rotate_to_angle(angle, animated=animated)
        
    def smooth_rotate_to_angle(self, target_angle: float, center: Optional[Point] = None, 
                              duration: float = 0.5) -> bool:
        """Smooth animated rotation to target angle."""
        if self._constraints.lock_rotation:
            return False
            
        self._animation_duration = duration
        return self._start_smooth_rotation(target_angle, center)
        
    def start_gesture_rotation(self, center: Point, initial_position: Point):
        """Start gesture-based rotation."""
        self._gesture_center = center
        self._gesture_start_angle = self._calculate_angle_from_center(center, initial_position)
        self._gesture_last_angle = self._gesture_start_angle
        self._gesture_start_time = time.time()
        
        # Stop any active animation
        self._stop_rotation_animation()
        
        self.rotation_started.emit(center)
        
    def update_gesture_rotation(self, position: Point):
        """Update rotation during gesture."""
        if not self._gesture_center or self._gesture_start_angle is None:
            return
            
        start_time = time.time() if self._enable_performance_profiling else 0.0
        
        current_angle = self._calculate_angle_from_center(self._gesture_center, position)
        angle_delta = current_angle - self._gesture_last_angle
        
        # Handle angle wraparound
        if angle_delta > math.pi:
            angle_delta -= 2 * math.pi
        elif angle_delta < -math.pi:
            angle_delta += 2 * math.pi
            
        # Apply rotation delta
        self.rotate_by_delta(angle_delta, self._gesture_center)
        
        self._gesture_last_angle = current_angle
        
        if self._enable_performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('gesture_rotate', 
                                           self._rotation_state.angle - angle_delta, 
                                           self._rotation_state.angle, operation_time, False)
        
    def finish_gesture_rotation(self):
        """Finish gesture-based rotation with final snapping."""
        if not self._gesture_center:
            return
            
        # Apply final snapping if enabled
        if self._rotation_state.snap_enabled:
            final_angle = self._snap_angle(self._rotation_state.angle)
            if final_angle != self._rotation_state.angle:
                self.smooth_rotate_to_angle(final_angle, duration=0.2)
                
        self._gesture_center = None
        self._gesture_start_angle = None
        self._gesture_last_angle = None
        
        self.rotation_finished.emit(self._rotation_state.angle)
        
    def get_rotation_angle(self) -> float:
        """Get current rotation angle in radians."""
        return self._rotation_state.angle
        
    def get_rotation_degrees(self) -> float:
        """Get current rotation angle in degrees."""
        return math.degrees(self._rotation_state.angle)
        
    def get_rotation_center(self) -> Point:
        """Get rotation center."""
        return self._rotation_state.center
        
    def set_rotation_center(self, center: Point):
        """Set rotation center."""
        old_center = self._rotation_state.center
        self._rotation_state.center = center
        
        # Invalidate cache if center changed significantly
        if (abs(old_center.x - center.x) > 1.0 or 
            abs(old_center.y - center.y) > 1.0):
            self._transformation_cache.invalidate_pattern("rotation_")
        
    def get_rotation_transformation(self) -> Optional[AffineTransformation]:
        """Get current rotation transformation with caching."""
        cache_key = f"rotation_{self._rotation_state.angle:.6f}_{self._rotation_state.center.x:.3f}_{self._rotation_state.center.y:.3f}"
        
        # Try cache first
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create new rotation transformation
        try:
            transform = AffineTransformation.rotation(self._rotation_state.angle)
            
            # Apply center offset if needed
            if self._rotation_state.center.x != 0 or self._rotation_state.center.y != 0:
                center_transform = AffineTransformation.translation(
                    -self._rotation_state.center.x, -self._rotation_state.center.y
                )
                uncenter_transform = AffineTransformation.translation(
                    self._rotation_state.center.x, self._rotation_state.center.y
                )
                transform = uncenter_transform.compose(transform.compose(center_transform))
                
            # Cache the transformation
            self._transformation_cache.set(cache_key, transform)
            return transform
        except Exception:
            # Fallback to identity transform
            return AffineTransformation.identity()
        
    def reset_rotation(self, animated: bool = False):
        """Reset rotation to 0 degrees."""
        self.rotate_to_angle(0.0, animated=animated)
        
    def set_snap_configuration(self, enabled: bool = True, snap_angle: float = math.pi / 12,
                             threshold: float = 0.1, custom_zones: Optional[List[float]] = None):
        """Configure angle snapping behavior."""
        self._rotation_state.snap_enabled = enabled
        self._rotation_state.snap_angle = snap_angle
        self._rotation_state.snap_threshold = threshold
        
        if custom_zones is not None:
            self._rotation_state.snap_zones = custom_zones
            
    def set_constraints(self, constraints: RotationConstraints):
        """Set rotation constraints."""
        self._constraints = constraints
        
        # Apply constraints to current angle if needed
        if not self._constraints.lock_rotation:
            constrained_angle = self._apply_angle_constraints(self._rotation_state.angle)
            if constrained_angle != self._rotation_state.angle:
                self.rotate_to_angle(constrained_angle)
        
    def get_snap_preview(self, angle: float) -> Tuple[float, bool]:
        """Get preview of what angle would snap to."""
        if not self._rotation_state.snap_enabled:
            return angle, False
            
        normalized_angle = self._normalize_angle(angle)
        snapped_angle = self._snap_angle(normalized_angle)
        
        return snapped_angle, snapped_angle != normalized_angle
        
    def is_animating(self) -> bool:
        """Check if rotation animation is currently active."""
        return self._animation_active
        
    def stop_animation(self):
        """Stop any active rotation animation."""
        self._stop_rotation_animation()
        
    def get_performance_metrics(self) -> RotationPerformanceMetrics:
        """Get comprehensive rotation performance metrics."""
        cache_stats = self._transformation_cache.get_stats()
        coord_cache_stats = self._coordinate_cache.get_stats()
        
        # Categorize operations
        snap_ops = len([score for score in self._snap_accuracy_scores if score > 0])
        total_ops = len(self._operation_times)
        smooth_ops = len([t for t in self._operation_times if t > 0.02])  # >20ms = smooth
        instant_ops = total_ops - smooth_ops
        
        # Calculate average angle change
        if self._angle_history:
            angle_changes = []
            for i in range(1, len(self._angle_history)):
                prev_angle = self._angle_history[i-1][1]
                curr_angle = self._angle_history[i][1]
                change = abs(curr_angle - prev_angle)
                # Handle wraparound
                if change > math.pi:
                    change = 2 * math.pi - change
                angle_changes.append(change)
            avg_angle_change = sum(angle_changes) / len(angle_changes) if angle_changes else 0.0
        else:
            avg_angle_change = 0.0
            
        # Calculate snap accuracy
        snap_accuracy = sum(self._snap_accuracy_scores) / len(self._snap_accuracy_scores) if self._snap_accuracy_scores else 1.0
        
        # Calculate cache efficiency
        cache_efficiency = (cache_stats['hit_rate'] + coord_cache_stats['hit_rate']) / 2
        
        return RotationPerformanceMetrics(
            snap_operations=snap_ops,
            smooth_operations=smooth_ops,
            instant_operations=instant_ops,
            average_angle_change=avg_angle_change,
            snap_accuracy=snap_accuracy,
            cache_efficiency=cache_efficiency
        )
        
    def optimize_performance(self):
        """Optimize rotation performance."""
        # Optimize caches
        self._transformation_cache.optimize()
        
        # Clean old performance data
        current_time = time.time()
        cutoff_time = current_time - 60.0  # Keep last minute
        self._angle_history = [
            (ts, angle) for ts, angle in self._angle_history 
            if ts > cutoff_time
        ]
        
        # Keep only recent operation times and snap scores
        if len(self._operation_times) > 100:
            self._operation_times = self._operation_times[-50:]
        if len(self._snap_accuracy_scores) > 50:
            self._snap_accuracy_scores = self._snap_accuracy_scores[-25:]
            
    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to [0, 2π] range."""
        normalized = angle % (2 * math.pi)
        if normalized < 0:
            normalized += 2 * math.pi
        return normalized
        
    def _apply_angle_constraints(self, angle: float) -> float:
        """Apply angle constraints."""
        if self._constraints.min_angle is not None:
            angle = max(self._constraints.min_angle, angle)
        if self._constraints.max_angle is not None:
            angle = min(self._constraints.max_angle, angle)
            
        return angle
        
    def _snap_angle(self, angle: float) -> float:
        """Apply angle snapping logic."""
        if not self._rotation_state.snap_enabled:
            return angle
            
        # Check snap zones first
        for zone_angle in self._rotation_state.snap_zones:
            distance = abs(angle - zone_angle)
            # Handle wraparound distance
            distance = min(distance, 2 * math.pi - distance)
            
            if distance <= self._rotation_state.snap_threshold:
                return zone_angle
                
        # Check regular snap angle intervals
        snap_interval = self._rotation_state.snap_angle
        nearest_snap = round(angle / snap_interval) * snap_interval
        
        distance = abs(angle - nearest_snap)
        # Handle wraparound distance
        distance = min(distance, 2 * math.pi - distance)
        
        if distance <= self._rotation_state.snap_threshold:
            return self._normalize_angle(nearest_snap)
            
        return angle
        
    def _calculate_angle_from_center(self, center: Point, position: Point) -> float:
        """Calculate angle from center to position."""
        dx = position.x - center.x
        dy = position.y - center.y
        return math.atan2(dy, dx)
        
    def _start_smooth_rotation(self, target_angle: float, center: Optional[Point]) -> bool:
        """Start smooth rotation animation."""
        if self._animation_timer is None:
            return False
            
        self._animation_target = self._normalize_angle(target_angle)
        self._animation_start_angle = self._rotation_state.angle
        self._animation_start_time = time.time()
        self._animation_active = True
        
        if center:
            self._rotation_state.center = center
            
        # Choose shortest rotation path
        angle_diff = self._animation_target - self._animation_start_angle
        if angle_diff > math.pi:
            self._animation_target -= 2 * math.pi
        elif angle_diff < -math.pi:
            self._animation_target += 2 * math.pi
            
        self.rotation_started.emit(self._rotation_state.center)
        self._animation_timer.start(16)  # ~60 FPS
        
        return True
        
    def _stop_rotation_animation(self):
        """Stop rotation animation."""
        if self._animation_timer is not None:
            self._animation_timer.stop()
        self._animation_active = False
        
    def _animate_rotation(self):
        """Animate rotation transition with easing."""
        if not self._animation_active:
            return
            
        current_time = time.time()
        elapsed = current_time - self._animation_start_time
        
        if elapsed >= self._animation_duration:
            # Animation complete
            self._rotation_state.angle = self._normalize_angle(self._animation_target)
            self._stop_rotation_animation()
            self.rotation_finished.emit(self._rotation_state.angle)
        else:
            # Interpolate angle with easing
            progress = elapsed / self._animation_duration
            eased_progress = self._ease_in_out_quad(progress)
            
            interpolated_angle = self._animation_start_angle + (
                self._animation_target - self._animation_start_angle
            ) * eased_progress
            
            self._rotation_state.angle = self._normalize_angle(interpolated_angle)
            
        self._update_coordinate_transform()
        self.rotation_changed.emit(self._rotation_state.angle)
        
    def _ease_in_out_quad(self, t: float) -> float:
        """Quadratic ease-in-out function for smooth animation."""
        if t < 0.5:
            return 2 * t * t
        else:
            return -1 + (4 - 2 * t) * t
            
    def _update_coordinate_transform(self):
        """Update coordinate transform with new rotation."""
        if self.coordinate_transform:
            rotation_transform = self.get_rotation_transformation()
            if rotation_transform:
                self.coordinate_transform.set_rotation(self._rotation_state.angle)
                
    def _update_performance_metrics(self, operation: str, old_angle: float, 
                                  new_angle: float, operation_time: float, snap_applied: bool):
        """Update performance metrics."""
        timestamp = time.time()
        
        # Record operation time
        self._operation_times.append(operation_time)
        if len(self._operation_times) > 200:
            self._operation_times = self._operation_times[-100:]
            
        # Record angle history
        self._angle_history.append((timestamp, new_angle))
        if len(self._angle_history) > 100:
            self._angle_history = self._angle_history[-50:]
            
        # Record snap accuracy if applicable
        if snap_applied:
            # Calculate how close the snap was to the intended angle
            intended_angle = old_angle
            actual_angle = new_angle
            snap_accuracy = 1.0 - min(1.0, abs(actual_angle - intended_angle) / math.pi)
            self._snap_accuracy_scores.append(snap_accuracy)
            
        # Update operation-specific metrics
        angle_change = abs(new_angle - old_angle)
        if angle_change > math.pi:  # Handle wraparound
            angle_change = 2 * math.pi - angle_change
            
        self._performance_metrics[operation] = {
            'last_time': operation_time,
            'last_change': angle_change,
            'operations_count': self._performance_metrics.get(operation, {}).get('operations_count', 0) + 1
        }
        
        # Emit performance update
        if QT_AVAILABLE:
            self.performance_updated.emit(self._performance_metrics)
            
    def _precompute_transformations(self):
        """Pre-compute transformations for common rotation angles."""
        common_angles = [
            0.0,                    # 0°
            math.pi / 6,           # 30°
            math.pi / 4,           # 45°
            math.pi / 3,           # 60°
            math.pi / 2,           # 90°
            2 * math.pi / 3,       # 120°
            3 * math.pi / 4,       # 135°
            5 * math.pi / 6,       # 150°
            math.pi,               # 180°
            7 * math.pi / 6,       # 210°
            5 * math.pi / 4,       # 225°
            4 * math.pi / 3,       # 240°
            3 * math.pi / 2,       # 270°
            5 * math.pi / 3,       # 300°
            7 * math.pi / 4,       # 315°
            11 * math.pi / 6       # 330°
        ]
        
        center = Point(0, 0)  # Default center for pre-computation
        
        for angle in common_angles:
            cache_key = f"rotation_{angle:.6f}_0.000_0.000"
            if not self._transformation_cache.get(cache_key):
                transform = AffineTransformation.rotation(angle)
                self._transformation_cache.set(cache_key, transform)