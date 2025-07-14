"""
High-performance zoom transformation manager.

This module provides optimized zoom operations with smooth animations,
caching, and performance monitoring for the document viewer.
"""

from typing import Tuple, Optional, List, Dict, Callable
from dataclasses import dataclass
import math
import time

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
    from PyQt6.QtGui import QWheelEvent
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Fallback signal class for testing
    class QObject:
        pass
    def pyqtSignal(*args):
        pass

from .coordinates import CoordinateTransform
from .transformations import AffineTransformation
from .cache import TransformationCache, CoordinateCache
from ...utils.geometry import Point, Rect, Size


@dataclass
class ZoomState:
    """Current zoom state with constraints."""
    level: float
    min_zoom: float
    max_zoom: float
    center: Point
    smooth_factor: float = 0.1
    
    def __post_init__(self):
        """Validate zoom state."""
        self.level = max(self.min_zoom, min(self.max_zoom, self.level))


@dataclass
class ZoomPerformanceMetrics:
    """Zoom performance tracking."""
    operation_times: List[float]
    cache_hit_rate: float
    smooth_operations: int
    instant_operations: int
    average_operation_time: float
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.operation_times:
            self.average_operation_time = sum(self.operation_times) / len(self.operation_times)
        else:
            self.average_operation_time = 0.0


class ZoomManager(QObject):
    """High-performance zoom transformation manager with advanced optimization."""
    
    # Signals
    zoom_changed = pyqtSignal(float)  # zoom_level
    zoom_started = pyqtSignal(Point)  # zoom_center
    zoom_finished = pyqtSignal(float)  # final_zoom
    performance_updated = pyqtSignal(dict)  # performance_metrics
    
    def __init__(self, coordinate_transform: Optional[CoordinateTransform] = None):
        super().__init__()
        self.coordinate_transform = coordinate_transform
        self._zoom_state = ZoomState(1.0, 0.1, 10.0, Point(0, 0))
        
        # High-performance caching
        self._transformation_cache = TransformationCache(max_size=500)
        self._coordinate_cache = CoordinateCache(max_entries=5000)
        
        # Animation system
        if QT_AVAILABLE:
            self._animation_timer = QTimer()
            self._animation_timer.timeout.connect(self._animate_zoom)
        else:
            self._animation_timer = None
            
        # Animation state
        self._animation_active = False
        self._animation_target = 1.0
        self._animation_start_level = 1.0
        self._animation_start_time = 0.0
        self._animation_duration = 0.3
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        self._zoom_history: List[Tuple[float, float]] = []  # (timestamp, zoom_level)
        self._operation_times: List[float] = []
        
        # Optimization settings
        self._cache_zoom_levels = True
        self._precompute_common_zooms = True
        self._performance_profiling = True
        
        # Pre-compute common zoom levels
        if self._precompute_common_zooms:
            self._precompute_transformations()
        
    def zoom_to_level(self, level: float, center: Optional[Point] = None, 
                     animated: bool = False) -> bool:
        """Zoom to specific level with optional center point and animation."""
        start_time = time.time() if self._performance_profiling else 0.0
        
        if not self._validate_zoom_level(level):
            return False
            
        old_level = self._zoom_state.level
        target_level = self._clamp_zoom_level(level)
        
        if center:
            self._zoom_state.center = center
            
        if animated and self._animation_timer is not None:
            return self._start_smooth_zoom(target_level, center)
        else:
            # Instant zoom
            self._zoom_state.level = target_level
            self._update_coordinate_transform()
            self.zoom_changed.emit(self._zoom_state.level)
            
        # Update performance metrics
        if self._performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('zoom_to_level', old_level, target_level, operation_time)
        
        return True
        
    def zoom_in(self, factor: float = 1.2, center: Optional[Point] = None, 
               animated: bool = False) -> bool:
        """Zoom in by factor."""
        return self.zoom_to_level(self._zoom_state.level * factor, center, animated)
        
    def zoom_out(self, factor: float = 1.2, center: Optional[Point] = None, 
                animated: bool = False) -> bool:
        """Zoom out by factor."""
        return self.zoom_to_level(self._zoom_state.level / factor, center, animated)
        
    def zoom_to_fit(self, rect: Rect, margin: float = 0.1, animated: bool = False) -> bool:
        """Zoom to fit rectangle with margin."""
        start_time = time.time() if self._performance_profiling else 0.0
        
        viewport_size = self._get_viewport_size()
        if not viewport_size:
            return False
            
        # Calculate optimal zoom level to fit rectangle
        zoom_x = viewport_size.width / (rect.width * (1 + margin))
        zoom_y = viewport_size.height / (rect.height * (1 + margin))
        zoom_level = min(zoom_x, zoom_y)
        
        center = rect.center
        result = self.zoom_to_level(zoom_level, center, animated)
        
        if self._performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('zoom_to_fit', self._zoom_state.level, zoom_level, operation_time)
            
        return result
        
    def smooth_zoom_to_level(self, target_level: float, center: Optional[Point] = None, 
                           duration: float = 0.3) -> bool:
        """Smooth animated zoom to target level."""
        if not self._validate_zoom_level(target_level):
            return False
            
        self._animation_duration = duration
        return self._start_smooth_zoom(target_level, center)
        
    def handle_wheel_event(self, event, sensitivity: float = 0.1) -> bool:
        """Handle mouse wheel zoom events with optimized processing."""
        if not QT_AVAILABLE:
            return False
            
        start_time = time.time() if self._performance_profiling else 0.0
        
        delta = event.angleDelta().y() / 120.0  # Standard wheel delta
        zoom_factor = 1.0 + (delta * sensitivity)
        
        # Get zoom center from event position
        center = Point(event.position().x(), event.position().y())
        
        # Use cache key for common zoom operations
        cache_key = f"wheel_zoom_{self._zoom_state.level:.3f}_{zoom_factor:.3f}"
        cached_level = self._transformation_cache.get(cache_key)
        
        if cached_level is not None:
            target_level = cached_level
        else:
            target_level = self._zoom_state.level * zoom_factor
            target_level = self._clamp_zoom_level(target_level)
            self._transformation_cache.set(cache_key, target_level)
        
        result = self.zoom_to_level(target_level, center)
        
        if self._performance_profiling:
            operation_time = time.time() - start_time
            self._update_performance_metrics('wheel_zoom', self._zoom_state.level, target_level, operation_time)
            
        return result
        
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_state.level
        
    def get_zoom_bounds(self) -> Tuple[float, float]:
        """Get zoom level bounds."""
        return (self._zoom_state.min_zoom, self._zoom_state.max_zoom)
        
    def set_zoom_bounds(self, min_zoom: float, max_zoom: float):
        """Set zoom level bounds with validation."""
        if min_zoom <= 0 or max_zoom <= min_zoom:
            raise ValueError("Invalid zoom bounds")
            
        self._zoom_state.min_zoom = min_zoom
        self._zoom_state.max_zoom = max_zoom
        
        # Clamp current zoom if necessary
        if self._zoom_state.level < min_zoom or self._zoom_state.level > max_zoom:
            self.zoom_to_level(self._clamp_zoom_level(self._zoom_state.level))
            
        # Invalidate cache for out-of-bounds zoom levels
        self._transformation_cache.invalidate_pattern("zoom_")
            
    def get_zoom_transformation(self) -> Optional[AffineTransformation]:
        """Get current zoom transformation with caching."""
        cache_key = f"zoom_transform_{self._zoom_state.level:.6f}_{self._zoom_state.center.x:.3f}_{self._zoom_state.center.y:.3f}"
        
        # Try cache first
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create new zoom transformation
        try:
            transform = AffineTransformation.scaling(self._zoom_state.level, self._zoom_state.level)
            
            # Apply center offset if needed
            if self._zoom_state.center.x != 0 or self._zoom_state.center.y != 0:
                center_transform = AffineTransformation.translation(
                    -self._zoom_state.center.x, -self._zoom_state.center.y
                )
                uncenter_transform = AffineTransformation.translation(
                    self._zoom_state.center.x, self._zoom_state.center.y
                )
                transform = uncenter_transform.compose(transform.compose(center_transform))
                
            # Cache the transformation
            if self._cache_zoom_levels:
                self._transformation_cache.set(cache_key, transform)
                
            return transform
        except Exception:
            # Fallback to identity transform
            return AffineTransformation.identity()
        
    def get_performance_metrics(self) -> ZoomPerformanceMetrics:
        """Get comprehensive zoom performance metrics."""
        cache_stats = self._transformation_cache.get_stats()
        coord_cache_stats = self._coordinate_cache.get_stats()
        
        smooth_ops = len([t for t in self._operation_times if t > 0.01])  # >10ms = smooth
        instant_ops = len(self._operation_times) - smooth_ops
        
        return ZoomPerformanceMetrics(
            operation_times=self._operation_times.copy(),
            cache_hit_rate=(cache_stats['hit_rate'] + coord_cache_stats['hit_rate']) / 2,
            smooth_operations=smooth_ops,
            instant_operations=instant_ops,
            average_operation_time=0.0  # Will be calculated in __post_init__
        )
        
    def predict_zoom_performance(self, target_level: float) -> float:
        """Predict performance for zoom level using historical data."""
        if len(self._zoom_history) < 3:
            return 1.0  # Default prediction
            
        # Calculate zoom complexity based on level change
        zoom_complexity = abs(math.log(target_level) - math.log(self._zoom_state.level))
        
        # Analyze historical performance for similar complexity
        similar_operations = [
            (time_taken, abs(math.log(level) - math.log(self._zoom_state.level)))
            for _, level, time_taken in self._zoom_history[-20:]  # Last 20 operations
            if abs(abs(math.log(level) - math.log(self._zoom_state.level)) - zoom_complexity) < 0.5
        ]
        
        if similar_operations:
            avg_time = sum(time_taken for time_taken, _ in similar_operations) / len(similar_operations)
            # Normalize to 0-1 performance score (1 = instant, 0 = slow)
            return max(0.0, min(1.0, 1.0 - (avg_time / 0.1)))  # 100ms = score 0
        
        # Base prediction on zoom complexity
        base_performance = 1.0 / (1.0 + zoom_complexity * 0.2)
        return max(0.1, min(1.0, base_performance))
        
    def optimize_performance(self):
        """Optimize zoom performance by cleaning caches and pre-computing."""
        # Optimize caches
        self._transformation_cache.optimize()
        
        # Pre-compute common zoom levels if enabled
        if self._precompute_common_zooms:
            self._precompute_transformations()
            
        # Clean old performance data
        current_time = time.time()
        cutoff_time = current_time - 60.0  # Keep last minute
        self._zoom_history = [
            (ts, level, time_taken) for ts, level, time_taken in self._zoom_history 
            if ts > cutoff_time
        ]
        
        # Keep only recent operation times
        if len(self._operation_times) > 100:
            self._operation_times = self._operation_times[-50:]
            
    def reset_performance_metrics(self):
        """Reset all performance tracking data."""
        self._zoom_history.clear()
        self._operation_times.clear()
        self._performance_metrics.clear()
        self._transformation_cache.clear()
        self._coordinate_cache.clear()
        
    def is_animating(self) -> bool:
        """Check if zoom animation is currently active."""
        return self._animation_active
        
    def stop_animation(self):
        """Stop any active zoom animation."""
        if self._animation_timer is not None:
            self._animation_timer.stop()
        self._animation_active = False
        
    def _validate_zoom_level(self, level: float) -> bool:
        """Validate zoom level against constraints."""
        return self._zoom_state.min_zoom <= level <= self._zoom_state.max_zoom
        
    def _clamp_zoom_level(self, level: float) -> float:
        """Clamp zoom level to valid range."""
        return max(self._zoom_state.min_zoom, min(self._zoom_state.max_zoom, level))
        
    def _update_coordinate_transform(self):
        """Update coordinate transform with new zoom."""
        if self.coordinate_transform:
            zoom_transform = self.get_zoom_transformation()
            if zoom_transform:
                # Update the coordinate transform's zoom level
                self.coordinate_transform.set_zoom_level(self._zoom_state.level)
                if self._zoom_state.center.x != 0 or self._zoom_state.center.y != 0:
                    # Update zoom center if specified
                    pass  # Coordinate transform will handle this
        
    def _start_smooth_zoom(self, target_level: float, center: Optional[Point]) -> bool:
        """Start smooth zoom animation."""
        if self._animation_timer is None:
            return False
            
        self._animation_target = self._clamp_zoom_level(target_level)
        self._animation_start_level = self._zoom_state.level
        self._animation_start_time = time.time()
        self._animation_active = True
        
        if center:
            self._zoom_state.center = center
            
        self.zoom_started.emit(self._zoom_state.center)
        self._animation_timer.start(16)  # ~60 FPS
        
        return True
        
    def _animate_zoom(self):
        """Animate zoom transition with easing."""
        if not self._animation_active:
            return
            
        current_time = time.time()
        elapsed = current_time - self._animation_start_time
        
        if elapsed >= self._animation_duration:
            # Animation complete
            self._zoom_state.level = self._animation_target
            self._animation_timer.stop()
            self._animation_active = False
            self.zoom_finished.emit(self._zoom_state.level)
        else:
            # Interpolate zoom level with easing
            progress = elapsed / self._animation_duration
            eased_progress = self._ease_in_out_cubic(progress)
            
            self._zoom_state.level = self._animation_start_level + (
                self._animation_target - self._animation_start_level
            ) * eased_progress
            
        self._update_coordinate_transform()
        self.zoom_changed.emit(self._zoom_state.level)
        
    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic easing function for smooth animation."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
            
    def _update_performance_metrics(self, operation: str, old_level: float, 
                                  new_level: float, operation_time: float):
        """Update performance metrics with new operation data."""
        timestamp = time.time()
        
        # Record operation time
        self._operation_times.append(operation_time)
        if len(self._operation_times) > 200:  # Keep last 200 operations
            self._operation_times = self._operation_times[-100:]
            
        # Record zoom history
        self._zoom_history.append((timestamp, new_level, operation_time))
        if len(self._zoom_history) > 100:  # Keep last 100 operations
            self._zoom_history = self._zoom_history[-50:]
        
        # Update operation-specific metrics
        zoom_change = abs(new_level - old_level)
        self._performance_metrics[operation] = {
            'last_time': operation_time,
            'last_change': zoom_change,
            'operations_count': self._performance_metrics.get(operation, {}).get('operations_count', 0) + 1
        }
        
        # Emit performance update
        if QT_AVAILABLE:
            self.performance_updated.emit(self._performance_metrics)
        
    def _get_viewport_size(self) -> Optional[Size]:
        """Get viewport size from coordinate transform."""
        if self.coordinate_transform:
            bounds = self.coordinate_transform.viewport_bounds
            return Size(bounds.width, bounds.height)
        return None
        
    def _precompute_transformations(self):
        """Pre-compute transformations for common zoom levels."""
        common_zoom_levels = [
            0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0
        ]
        
        for level in common_zoom_levels:
            if self._validate_zoom_level(level):
                cache_key = f"zoom_transform_{level:.6f}_0.000_0.000"
                if not self._transformation_cache.get(cache_key):
                    transform = AffineTransformation.scaling(level, level)
                    self._transformation_cache.set(cache_key, transform)