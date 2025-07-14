"""
High-performance pan transformation manager with momentum.

This module provides optimized pan operations with smooth momentum,
gesture support, and performance monitoring for the document viewer.
"""

from typing import Tuple, Optional, List, Dict, Callable
from dataclasses import dataclass
import math
import time

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
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
class PanState:
    """Current pan state with momentum."""
    offset: Point
    velocity: Point
    momentum_factor: float = 0.95
    min_velocity: float = 0.1
    max_velocity: float = 2000.0
    
    def __post_init__(self):
        """Validate pan state."""
        self.momentum_factor = max(0.1, min(0.99, self.momentum_factor))
        self.min_velocity = max(0.01, self.min_velocity)


@dataclass
class PanConstraints:
    """Pan operation constraints."""
    bounds: Optional[Rect] = None
    enable_bounds_checking: bool = False
    elastic_bounds: bool = True
    elastic_factor: float = 0.3
    max_elastic_distance: float = 100.0


@dataclass
class PanPerformanceMetrics:
    """Pan performance tracking."""
    momentum_operations: int
    instant_operations: int
    average_velocity: float
    peak_velocity: float
    gesture_smoothness: float
    cache_efficiency: float
    
    def get_overall_score(self) -> float:
        """Calculate overall performance score (0-1)."""
        smoothness_score = min(1.0, self.gesture_smoothness / 100.0)
        cache_score = self.cache_efficiency
        velocity_score = min(1.0, self.average_velocity / 500.0)  # Optimal ~500px/s
        
        return (smoothness_score + cache_score + velocity_score) / 3.0


class PanManager(QObject):
    """High-performance pan transformation manager with advanced momentum."""
    
    # Signals
    pan_changed = pyqtSignal(Point)  # offset
    pan_started = pyqtSignal(Point)  # start_position
    pan_finished = pyqtSignal(Point)  # final_offset
    momentum_started = pyqtSignal(Point)  # velocity
    momentum_finished = pyqtSignal()
    performance_updated = pyqtSignal(dict)  # performance_metrics
    
    def __init__(self, coordinate_transform: Optional[CoordinateTransform] = None):
        super().__init__()
        self.coordinate_transform = coordinate_transform
        self._pan_state = PanState(Point(0, 0), Point(0, 0))
        self._constraints = PanConstraints()
        
        # High-performance caching
        self._transformation_cache = TransformationCache(max_size=300)
        self._coordinate_cache = CoordinateCache(max_entries=3000)
        
        # Momentum animation
        if QT_AVAILABLE:
            self._momentum_timer = QTimer()
            self._momentum_timer.timeout.connect(self._animate_momentum)
            self._smooth_pan_timer = QTimer()
            self._smooth_pan_timer.timeout.connect(self._animate_smooth_pan)
        else:
            self._momentum_timer = None
            self._smooth_pan_timer = None
            
        # Pan tracking state
        self._pan_start_position: Optional[Point] = None
        self._pan_last_position: Optional[Point] = None
        self._pan_last_time: float = 0.0
        self._pan_total_distance: float = 0.0
        self._pan_gesture_start_time: float = 0.0
        
        # Smooth pan animation
        self._smooth_pan_active = False
        self._smooth_pan_target: Optional[Point] = None
        self._smooth_pan_start: Optional[Point] = None
        self._smooth_pan_start_time: float = 0.0
        self._smooth_pan_duration: float = 0.3
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        self._velocity_history: List[Tuple[float, Point]] = []  # (timestamp, velocity)
        self._operation_times: List[float] = []
        self._gesture_quality_scores: List[float] = []
        
        # Optimization settings
        self._enable_momentum = True
        self._enable_gesture_prediction = True
        self._enable_performance_profiling = True
        self._momentum_frame_rate = 60  # FPS
        
    def start_pan(self, position: Point):
        """Start pan operation with gesture tracking."""
        start_time = time.time() if self._enable_performance_profiling else 0.0
        
        self._pan_start_position = position
        self._pan_last_position = position
        self._pan_last_time = time.time()
        self._pan_total_distance = 0.0
        self._pan_gesture_start_time = self._pan_last_time
        
        # Stop any active momentum or smooth pan
        self._stop_momentum()
        self._stop_smooth_pan()
        
        # Reset velocity
        self._pan_state.velocity = Point(0, 0)
        
        self.pan_started.emit(position)
        
        if self._enable_performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('start_pan', operation_time)
        
    def update_pan(self, position: Point):
        """Update pan during drag with optimized calculations."""
        if not self._pan_start_position or not self._pan_last_position:
            return
            
        start_time = time.time() if self._enable_performance_profiling else 0.0
        current_time = time.time()
        
        # Calculate pan delta
        delta = Point(
            position.x - self._pan_last_position.x,
            position.y - self._pan_last_position.y
        )
        
        # Update total gesture distance
        delta_distance = math.sqrt(delta.x * delta.x + delta.y * delta.y)
        self._pan_total_distance += delta_distance
        
        # Apply constraints if enabled
        if self._constraints.enable_bounds_checking:
            delta = self._apply_pan_constraints(delta)
        
        # Update offset with caching
        new_offset = Point(
            self._pan_state.offset.x + delta.x,
            self._pan_state.offset.y + delta.y
        )
        
        # Use coordinate cache for frequently accessed transformations
        cache_key = f"pan_delta_{delta.x:.1f}_{delta.y:.1f}"
        cached_offset = self._coordinate_cache.get_transformed_point(
            self._pan_state.offset.x, self._pan_state.offset.y, cache_key
        )
        
        if cached_offset:
            new_offset = Point(cached_offset[0], cached_offset[1])
        else:
            self._coordinate_cache.set_transformed_point(
                self._pan_state.offset.x, self._pan_state.offset.y, cache_key,
                new_offset.x, new_offset.y
            )
        
        self._pan_state.offset = new_offset
        
        # Calculate velocity for momentum with smoothing
        time_delta = current_time - self._pan_last_time
        if time_delta > 0:
            instant_velocity = Point(delta.x / time_delta, delta.y / time_delta)
            
            # Smooth velocity calculation to reduce jitter
            smoothing_factor = 0.7
            self._pan_state.velocity = Point(
                self._pan_state.velocity.x * smoothing_factor + instant_velocity.x * (1 - smoothing_factor),
                self._pan_state.velocity.y * smoothing_factor + instant_velocity.y * (1 - smoothing_factor)
            )
            
            # Clamp velocity to reasonable bounds
            velocity_magnitude = math.sqrt(
                self._pan_state.velocity.x ** 2 + self._pan_state.velocity.y ** 2
            )
            if velocity_magnitude > self._pan_state.max_velocity:
                factor = self._pan_state.max_velocity / velocity_magnitude
                self._pan_state.velocity = Point(
                    self._pan_state.velocity.x * factor,
                    self._pan_state.velocity.y * factor
                )
                
            # Record velocity for performance analysis
            self._velocity_history.append((current_time, self._pan_state.velocity))
            if len(self._velocity_history) > 50:  # Keep last 50 samples
                self._velocity_history = self._velocity_history[-25:]
            
        self._pan_last_position = position
        self._pan_last_time = current_time
        
        # Update coordinate transform
        self._update_coordinate_transform()
        
        self.pan_changed.emit(self._pan_state.offset)
        
        if self._enable_performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('update_pan', operation_time)
        
    def finish_pan(self):
        """Finish pan operation with momentum analysis."""
        if not self._pan_start_position:
            return
            
        start_time = time.time() if self._enable_performance_profiling else 0.0
        
        # Calculate gesture quality
        gesture_duration = time.time() - self._pan_gesture_start_time
        gesture_quality = self._calculate_gesture_quality(gesture_duration)
        self._gesture_quality_scores.append(gesture_quality)
        
        # Start momentum animation if velocity is significant
        velocity_magnitude = math.sqrt(
            self._pan_state.velocity.x ** 2 + self._pan_state.velocity.y ** 2
        )
        
        if (self._enable_momentum and 
            velocity_magnitude > self._pan_state.min_velocity and 
            self._momentum_timer is not None):
            self._start_momentum()
        else:
            self.pan_finished.emit(self._pan_state.offset)
            
        self._pan_start_position = None
        self._pan_last_position = None
        
        if self._enable_performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('finish_pan', operation_time)
        
    def pan_to_offset(self, offset: Point, animated: bool = False, duration: float = 0.3):
        """Pan to specific offset with optional animation."""
        if animated and self._smooth_pan_timer is not None:
            self._start_smooth_pan(offset, duration)
        else:
            old_offset = self._pan_state.offset
            self._pan_state.offset = offset
            
            # Apply constraints
            if self._constraints.enable_bounds_checking:
                self._pan_state.offset = self._apply_offset_constraints(self._pan_state.offset)
            
            self._update_coordinate_transform()
            self.pan_changed.emit(self._pan_state.offset)
            
    def pan_by_delta(self, delta: Point, animated: bool = False):
        """Pan by delta amount."""
        new_offset = Point(
            self._pan_state.offset.x + delta.x,
            self._pan_state.offset.y + delta.y
        )
        self.pan_to_offset(new_offset, animated)
        
    def get_pan_offset(self) -> Point:
        """Get current pan offset."""
        return self._pan_state.offset
        
    def get_pan_velocity(self) -> Point:
        """Get current pan velocity."""
        return self._pan_state.velocity
        
    def get_pan_transformation(self) -> Optional[AffineTransformation]:
        """Get current pan transformation with caching."""
        cache_key = f"pan_transform_{self._pan_state.offset.x:.3f}_{self._pan_state.offset.y:.3f}"
        
        # Try cache first
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create new pan transformation
        try:
            transform = AffineTransformation.translation(
                self._pan_state.offset.x, self._pan_state.offset.y
            )
            
            # Cache the transformation
            self._transformation_cache.set(cache_key, transform)
            return transform
        except Exception:
            # Fallback to identity transform
            return AffineTransformation.identity()
        
    def set_constraints(self, constraints: PanConstraints):
        """Set pan constraints."""
        self._constraints = constraints
        
        # Apply constraints to current offset if needed
        if self._constraints.enable_bounds_checking:
            new_offset = self._apply_offset_constraints(self._pan_state.offset)
            if new_offset.x != self._pan_state.offset.x or new_offset.y != self._pan_state.offset.y:
                self.pan_to_offset(new_offset)
        
    def is_panning(self) -> bool:
        """Check if currently panning."""
        return self._pan_start_position is not None
        
    def has_momentum(self) -> bool:
        """Check if momentum animation is active."""
        return self._momentum_timer is not None and self._momentum_timer.isActive()
        
    def is_smooth_panning(self) -> bool:
        """Check if smooth pan animation is active."""
        return self._smooth_pan_active
        
    def stop_momentum(self):
        """Stop momentum animation."""
        self._stop_momentum()
        
    def stop_all_animation(self):
        """Stop all pan animations."""
        self._stop_momentum()
        self._stop_smooth_pan()
        
    def get_performance_metrics(self) -> PanPerformanceMetrics:
        """Get comprehensive pan performance metrics."""
        cache_stats = self._transformation_cache.get_stats()
        coord_cache_stats = self._coordinate_cache.get_stats()
        
        # Calculate velocity statistics
        if self._velocity_history:
            velocities = [math.sqrt(v.x*v.x + v.y*v.y) for _, v in self._velocity_history]
            avg_velocity = sum(velocities) / len(velocities)
            peak_velocity = max(velocities)
        else:
            avg_velocity = 0.0
            peak_velocity = 0.0
            
        # Calculate gesture smoothness
        gesture_smoothness = sum(self._gesture_quality_scores) / len(self._gesture_quality_scores) if self._gesture_quality_scores else 50.0
        
        # Calculate cache efficiency
        cache_efficiency = (cache_stats['hit_rate'] + coord_cache_stats['hit_rate']) / 2
        
        momentum_ops = len([t for t in self._operation_times if t > 0.016])  # >16ms = momentum frame
        instant_ops = len(self._operation_times) - momentum_ops
        
        return PanPerformanceMetrics(
            momentum_operations=momentum_ops,
            instant_operations=instant_ops,
            average_velocity=avg_velocity,
            peak_velocity=peak_velocity,
            gesture_smoothness=gesture_smoothness,
            cache_efficiency=cache_efficiency
        )
        
    def optimize_performance(self):
        """Optimize pan performance."""
        # Optimize caches
        self._transformation_cache.optimize()
        
        # Clean old performance data
        current_time = time.time()
        cutoff_time = current_time - 30.0  # Keep last 30 seconds
        self._velocity_history = [
            (ts, velocity) for ts, velocity in self._velocity_history 
            if ts > cutoff_time
        ]
        
        # Keep only recent operation times and gesture scores
        if len(self._operation_times) > 100:
            self._operation_times = self._operation_times[-50:]
        if len(self._gesture_quality_scores) > 50:
            self._gesture_quality_scores = self._gesture_quality_scores[-25:]
            
    def _start_momentum(self):
        """Start momentum animation."""
        if self._momentum_timer is None:
            return
            
        self.momentum_started.emit(self._pan_state.velocity)
        self._momentum_timer.start(1000 // self._momentum_frame_rate)  # 60 FPS
        
    def _stop_momentum(self):
        """Stop momentum animation."""
        if self._momentum_timer is not None:
            self._momentum_timer.stop()
        self._pan_state.velocity = Point(0, 0)
        
    def _animate_momentum(self):
        """Animate momentum decay with physics simulation."""
        # Apply momentum decay
        self._pan_state.velocity = Point(
            self._pan_state.velocity.x * self._pan_state.momentum_factor,
            self._pan_state.velocity.y * self._pan_state.momentum_factor
        )
        
        # Calculate frame delta based on frame rate
        frame_delta = 1.0 / self._momentum_frame_rate
        
        # Update offset
        delta_offset = Point(
            self._pan_state.velocity.x * frame_delta,
            self._pan_state.velocity.y * frame_delta
        )
        
        # Apply constraints
        if self._constraints.enable_bounds_checking:
            delta_offset = self._apply_pan_constraints(delta_offset)
            
        self._pan_state.offset = Point(
            self._pan_state.offset.x + delta_offset.x,
            self._pan_state.offset.y + delta_offset.y
        )
        
        # Check if momentum should stop
        velocity_magnitude = math.sqrt(
            self._pan_state.velocity.x ** 2 + self._pan_state.velocity.y ** 2
        )
        
        if velocity_magnitude < self._pan_state.min_velocity:
            self._stop_momentum()
            self.momentum_finished.emit()
            self.pan_finished.emit(self._pan_state.offset)
        else:
            self._update_coordinate_transform()
            self.pan_changed.emit(self._pan_state.offset)
            
    def _start_smooth_pan(self, target_offset: Point, duration: float):
        """Start smooth pan animation."""
        if self._smooth_pan_timer is None:
            return
            
        self._smooth_pan_target = target_offset
        self._smooth_pan_start = self._pan_state.offset
        self._smooth_pan_start_time = time.time()
        self._smooth_pan_duration = duration
        self._smooth_pan_active = True
        
        self._smooth_pan_timer.start(16)  # ~60 FPS
        
    def _stop_smooth_pan(self):
        """Stop smooth pan animation."""
        if self._smooth_pan_timer is not None:
            self._smooth_pan_timer.stop()
        self._smooth_pan_active = False
        
    def _animate_smooth_pan(self):
        """Animate smooth pan transition."""
        if not self._smooth_pan_active or not self._smooth_pan_target or not self._smooth_pan_start:
            return
            
        current_time = time.time()
        elapsed = current_time - self._smooth_pan_start_time
        
        if elapsed >= self._smooth_pan_duration:
            # Animation complete
            self._pan_state.offset = self._smooth_pan_target
            self._stop_smooth_pan()
            self.pan_finished.emit(self._pan_state.offset)
        else:
            # Interpolate offset with easing
            progress = elapsed / self._smooth_pan_duration
            eased_progress = self._ease_out_cubic(progress)
            
            self._pan_state.offset = Point(
                self._smooth_pan_start.x + (self._smooth_pan_target.x - self._smooth_pan_start.x) * eased_progress,
                self._smooth_pan_start.y + (self._smooth_pan_target.y - self._smooth_pan_start.y) * eased_progress
            )
            
        self._update_coordinate_transform()
        self.pan_changed.emit(self._pan_state.offset)
        
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out function for smooth animation."""
        return 1 - pow(1 - t, 3)
        
    def _apply_pan_constraints(self, delta: Point) -> Point:
        """Apply constraints to pan delta."""
        if not self._constraints.enable_bounds_checking or not self._constraints.bounds:
            return delta
            
        new_offset = Point(
            self._pan_state.offset.x + delta.x,
            self._pan_state.offset.y + delta.y
        )
        
        constrained_offset = self._apply_offset_constraints(new_offset)
        
        return Point(
            constrained_offset.x - self._pan_state.offset.x,
            constrained_offset.y - self._pan_state.offset.y
        )
        
    def _apply_offset_constraints(self, offset: Point) -> Point:
        """Apply constraints to absolute offset."""
        if not self._constraints.enable_bounds_checking or not self._constraints.bounds:
            return offset
            
        bounds = self._constraints.bounds
        
        if self._constraints.elastic_bounds:
            # Elastic bounds with resistance
            constrained_x = self._apply_elastic_constraint(
                offset.x, bounds.left, bounds.right
            )
            constrained_y = self._apply_elastic_constraint(
                offset.y, bounds.top, bounds.bottom
            )
        else:
            # Hard bounds
            constrained_x = max(bounds.left, min(bounds.right, offset.x))
            constrained_y = max(bounds.top, min(bounds.bottom, offset.y))
            
        return Point(constrained_x, constrained_y)
        
    def _apply_elastic_constraint(self, value: float, min_bound: float, max_bound: float) -> float:
        """Apply elastic constraint to a single axis."""
        if min_bound <= value <= max_bound:
            return value
            
        if value < min_bound:
            overshoot = min_bound - value
            elastic_distance = min(overshoot * self._constraints.elastic_factor, 
                                 self._constraints.max_elastic_distance)
            return min_bound - elastic_distance
        else:
            overshoot = value - max_bound
            elastic_distance = min(overshoot * self._constraints.elastic_factor,
                                 self._constraints.max_elastic_distance)
            return max_bound + elastic_distance
            
    def _calculate_gesture_quality(self, duration: float) -> float:
        """Calculate gesture quality score (0-100)."""
        if duration <= 0 or self._pan_total_distance <= 0:
            return 50.0
            
        # Quality factors
        speed_consistency = self._calculate_speed_consistency()
        gesture_efficiency = min(100.0, (self._pan_total_distance / duration) / 10.0)  # pixels/second normalized
        duration_factor = min(100.0, 100.0 / max(1.0, duration))  # Prefer shorter gestures
        
        return (speed_consistency + gesture_efficiency + duration_factor) / 3.0
        
    def _calculate_speed_consistency(self) -> float:
        """Calculate speed consistency from velocity history."""
        if len(self._velocity_history) < 3:
            return 75.0
            
        # Calculate velocity variance (lower = more consistent)
        velocities = [math.sqrt(v.x*v.x + v.y*v.y) for _, v in self._velocity_history[-10:]]
        if not velocities:
            return 75.0
            
        mean_velocity = sum(velocities) / len(velocities)
        variance = sum((v - mean_velocity) ** 2 for v in velocities) / len(velocities)
        
        # Convert variance to quality score (0-100)
        consistency_score = max(0.0, 100.0 - (variance / 100.0))
        return min(100.0, consistency_score)
        
    def _update_coordinate_transform(self):
        """Update coordinate transform with new pan."""
        if self.coordinate_transform:
            pan_transform = self.get_pan_transformation()
            if pan_transform:
                self.coordinate_transform.set_pan_offset(self._pan_state.offset)
                
    def _update_performance_metrics(self, operation: str, operation_time: float):
        """Update performance metrics."""
        self._operation_times.append(operation_time)
        if len(self._operation_times) > 200:
            self._operation_times = self._operation_times[-100:]
            
        # Update operation-specific metrics
        self._performance_metrics[operation] = {
            'last_time': operation_time,
            'operations_count': self._performance_metrics.get(operation, {}).get('operations_count', 0) + 1
        }
        
        # Emit performance update
        if QT_AVAILABLE:
            self.performance_updated.emit(self._performance_metrics)