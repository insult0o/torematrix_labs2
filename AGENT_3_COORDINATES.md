# AGENT 3 COORDINATES - Zoom, Pan & Rotation Optimization

## 🎯 Your Mission
You are **Agent 3** implementing the **Zoom, Pan & Rotation Optimization** system for the Document Viewer Coordinate Mapping. You will build high-performance interactive transformations with advanced caching and smooth animations.

## 📋 Your Assignment
**Sub-Issue #151**: [Coordinate Mapping Sub-Issue #18.3: Zoom, Pan & Rotation Optimization](https://github.com/insult0o/torematrix_labs2/issues/151)

## 🚀 What You're Building
A high-performance interactive transformation system with:
- Optimized zoom, pan, and rotation transformations
- Advanced coordinate caching with smart invalidation
- Smooth animation and interpolation support
- Real-time performance monitoring and prediction

## 📁 Files to Create

### Primary Implementation Files
```
src/torematrix/ui/viewer/zoom.py
src/torematrix/ui/viewer/pan.py
src/torematrix/ui/viewer/rotation.py
src/torematrix/ui/viewer/cache.py
```

### Test Files
```
tests/unit/viewer/test_zoom.py
tests/unit/viewer/test_pan.py
tests/unit/viewer/test_rotation.py
tests/unit/viewer/test_cache.py
```

## 🔧 Technical Implementation Details

### 1. Zoom Transformation (`src/torematrix/ui/viewer/zoom.py`)
```python
from typing import Tuple, Optional, List, Dict, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QWheelEvent
import math
import time

from .coordinates import CoordinateMapper
from .transformations import AffineTransformation
from .cache import TransformationCache
from ..utils.geometry import Point, Rect

@dataclass
class ZoomState:
    """Current zoom state with constraints."""
    level: float
    min_zoom: float
    max_zoom: float
    center: Point
    smooth_factor: float = 0.1

class ZoomManager(QObject):
    """High-performance zoom transformation manager."""
    
    # Signals
    zoom_changed = pyqtSignal(float)  # zoom_level
    zoom_started = pyqtSignal(Point)  # zoom_center
    zoom_finished = pyqtSignal(float)  # final_zoom
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        super().__init__()
        self.coordinate_mapper = coordinate_mapper
        self._zoom_state = ZoomState(1.0, 0.1, 10.0, Point(0, 0))
        self._transformation_cache = TransformationCache()
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._animate_zoom)
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        self._zoom_history: List[Tuple[float, float]] = []  # (timestamp, zoom_level)
        
    def zoom_to_level(self, level: float, center: Optional[Point] = None) -> bool:
        """Zoom to specific level with optional center point."""
        if not self._validate_zoom_level(level):
            return False
            
        old_level = self._zoom_state.level
        self._zoom_state.level = self._clamp_zoom_level(level)
        
        if center:
            self._zoom_state.center = center
            
        # Update coordinate mapper with new zoom
        self._update_coordinate_mapper()
        
        # Emit signals
        self.zoom_changed.emit(self._zoom_state.level)
        
        # Update performance metrics
        self._update_performance_metrics('zoom_to_level', old_level, self._zoom_state.level)
        
        return True
        
    def zoom_in(self, factor: float = 1.2, center: Optional[Point] = None) -> bool:
        """Zoom in by factor."""
        return self.zoom_to_level(self._zoom_state.level * factor, center)
        
    def zoom_out(self, factor: float = 1.2, center: Optional[Point] = None) -> bool:
        """Zoom out by factor."""
        return self.zoom_to_level(self._zoom_state.level / factor, center)
        
    def zoom_to_fit(self, rect: Rect, margin: float = 0.1) -> bool:
        """Zoom to fit rectangle with margin."""
        # Calculate zoom level to fit rectangle
        viewport_size = self._get_viewport_size()
        if not viewport_size:
            return False
            
        zoom_x = viewport_size.width / (rect.width * (1 + margin))
        zoom_y = viewport_size.height / (rect.height * (1 + margin))
        zoom_level = min(zoom_x, zoom_y)
        
        center = rect.center
        return self.zoom_to_level(zoom_level, center)
        
    def smooth_zoom_to_level(self, target_level: float, center: Optional[Point] = None, 
                           duration: float = 0.3) -> bool:
        """Smooth animated zoom to target level."""
        if not self._validate_zoom_level(target_level):
            return False
            
        self._start_smooth_zoom(target_level, center, duration)
        return True
        
    def handle_wheel_event(self, event: QWheelEvent, sensitivity: float = 0.1) -> bool:
        """Handle mouse wheel zoom events."""
        delta = event.angleDelta().y() / 120.0  # Standard wheel delta
        zoom_factor = 1.0 + (delta * sensitivity)
        
        # Get zoom center from event position
        center = Point(event.position().x(), event.position().y())
        
        return self.zoom_to_level(self._zoom_state.level * zoom_factor, center)
        
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_state.level
        
    def get_zoom_bounds(self) -> Tuple[float, float]:
        """Get zoom level bounds."""
        return (self._zoom_state.min_zoom, self._zoom_state.max_zoom)
        
    def set_zoom_bounds(self, min_zoom: float, max_zoom: float):
        """Set zoom level bounds."""
        self._zoom_state.min_zoom = min_zoom
        self._zoom_state.max_zoom = max_zoom
        
        # Clamp current zoom if necessary
        if self._zoom_state.level < min_zoom or self._zoom_state.level > max_zoom:
            self.zoom_to_level(self._clamp_zoom_level(self._zoom_state.level))
            
    def get_zoom_transformation(self) -> AffineTransformation:
        """Get current zoom transformation."""
        cache_key = f"zoom_{self._zoom_state.level}_{self._zoom_state.center.x}_{self._zoom_state.center.y}"
        
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create zoom transformation
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
        self._transformation_cache.set(cache_key, transform)
        return transform
        
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get zoom performance metrics."""
        return self._performance_metrics.copy()
        
    def predict_zoom_performance(self, target_level: float) -> float:
        """Predict performance for zoom level."""
        # Analyze zoom history to predict performance
        if len(self._zoom_history) < 2:
            return 1.0  # Default prediction
            
        # Calculate performance based on zoom complexity
        zoom_complexity = abs(math.log(target_level) - math.log(self._zoom_state.level))
        base_performance = 1.0 / (1.0 + zoom_complexity * 0.1)
        
        return base_performance
        
    def _validate_zoom_level(self, level: float) -> bool:
        """Validate zoom level."""
        return self._zoom_state.min_zoom <= level <= self._zoom_state.max_zoom
        
    def _clamp_zoom_level(self, level: float) -> float:
        """Clamp zoom level to valid range."""
        return max(self._zoom_state.min_zoom, min(self._zoom_state.max_zoom, level))
        
    def _update_coordinate_mapper(self):
        """Update coordinate mapper with new zoom."""
        zoom_transform = self.get_zoom_transformation()
        # Update coordinate mapper transformation
        
    def _start_smooth_zoom(self, target_level: float, center: Optional[Point], duration: float):
        """Start smooth zoom animation."""
        self._animation_target = target_level
        self._animation_start_level = self._zoom_state.level
        self._animation_start_time = time.time()
        self._animation_duration = duration
        
        if center:
            self._zoom_state.center = center
            
        self._animation_timer.start(16)  # ~60 FPS
        
    def _animate_zoom(self):
        """Animate zoom transition."""
        current_time = time.time()
        elapsed = current_time - self._animation_start_time
        
        if elapsed >= self._animation_duration:
            # Animation complete
            self._zoom_state.level = self._animation_target
            self._animation_timer.stop()
            self.zoom_finished.emit(self._zoom_state.level)
        else:
            # Interpolate zoom level
            progress = elapsed / self._animation_duration
            # Use easing function for smooth animation
            eased_progress = self._ease_in_out_cubic(progress)
            
            self._zoom_state.level = self._animation_start_level + (
                self._animation_target - self._animation_start_level
            ) * eased_progress
            
        self._update_coordinate_mapper()
        self.zoom_changed.emit(self._zoom_state.level)
        
    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic easing function."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
            
    def _update_performance_metrics(self, operation: str, old_level: float, new_level: float):
        """Update performance metrics."""
        timestamp = time.time()
        self._zoom_history.append((timestamp, new_level))
        
        # Keep only recent history
        cutoff_time = timestamp - 10.0  # 10 seconds
        self._zoom_history = [(ts, level) for ts, level in self._zoom_history if ts > cutoff_time]
        
        # Calculate metrics
        zoom_change = abs(new_level - old_level)
        self._performance_metrics[operation] = zoom_change
        
    def _get_viewport_size(self) -> Optional[Size]:
        """Get viewport size for zoom calculations."""
        # Get from viewport manager
        return None  # Placeholder
```

### 2. Pan Transformation (`src/torematrix/ui/viewer/pan.py`)
```python
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QMouseEvent
import time

from .coordinates import CoordinateMapper
from .transformations import AffineTransformation
from .cache import TransformationCache
from ..utils.geometry import Point, Rect

@dataclass
class PanState:
    """Current pan state with momentum."""
    offset: Point
    velocity: Point
    momentum_factor: float = 0.95
    min_velocity: float = 0.1

class PanManager(QObject):
    """High-performance pan transformation manager."""
    
    # Signals
    pan_changed = pyqtSignal(Point)  # offset
    pan_started = pyqtSignal(Point)  # start_position
    pan_finished = pyqtSignal(Point)  # final_offset
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        super().__init__()
        self.coordinate_mapper = coordinate_mapper
        self._pan_state = PanState(Point(0, 0), Point(0, 0))
        self._transformation_cache = TransformationCache()
        
        # Momentum animation
        self._momentum_timer = QTimer()
        self._momentum_timer.timeout.connect(self._animate_momentum)
        
        # Pan tracking
        self._pan_start_position: Optional[Point] = None
        self._pan_last_position: Optional[Point] = None
        self._pan_last_time: float = 0.0
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        
    def start_pan(self, position: Point):
        """Start pan operation."""
        self._pan_start_position = position
        self._pan_last_position = position
        self._pan_last_time = time.time()
        
        # Stop momentum
        self._momentum_timer.stop()
        self._pan_state.velocity = Point(0, 0)
        
        self.pan_started.emit(position)
        
    def update_pan(self, position: Point):
        """Update pan during drag."""
        if not self._pan_start_position or not self._pan_last_position:
            return
            
        # Calculate pan delta
        delta = Point(
            position.x - self._pan_last_position.x,
            position.y - self._pan_last_position.y
        )
        
        # Update offset
        self._pan_state.offset = Point(
            self._pan_state.offset.x + delta.x,
            self._pan_state.offset.y + delta.y
        )
        
        # Calculate velocity for momentum
        current_time = time.time()
        time_delta = current_time - self._pan_last_time
        
        if time_delta > 0:
            self._pan_state.velocity = Point(
                delta.x / time_delta,
                delta.y / time_delta
            )
            
        self._pan_last_position = position
        self._pan_last_time = current_time
        
        # Update coordinate mapper
        self._update_coordinate_mapper()
        
        self.pan_changed.emit(self._pan_state.offset)
        
    def finish_pan(self):
        """Finish pan operation with momentum."""
        if not self._pan_start_position:
            return
            
        # Start momentum animation if velocity is significant
        velocity_magnitude = math.sqrt(
            self._pan_state.velocity.x ** 2 + self._pan_state.velocity.y ** 2
        )
        
        if velocity_magnitude > self._pan_state.min_velocity:
            self._momentum_timer.start(16)  # ~60 FPS
        else:
            self.pan_finished.emit(self._pan_state.offset)
            
        self._pan_start_position = None
        self._pan_last_position = None
        
    def pan_to_offset(self, offset: Point, animated: bool = False):
        """Pan to specific offset."""
        if animated:
            self._start_smooth_pan(offset)
        else:
            self._pan_state.offset = offset
            self._update_coordinate_mapper()
            self.pan_changed.emit(offset)
            
    def pan_by_delta(self, delta: Point):
        """Pan by delta amount."""
        new_offset = Point(
            self._pan_state.offset.x + delta.x,
            self._pan_state.offset.y + delta.y
        )
        self.pan_to_offset(new_offset)
        
    def get_pan_offset(self) -> Point:
        """Get current pan offset."""
        return self._pan_state.offset
        
    def get_pan_transformation(self) -> AffineTransformation:
        """Get current pan transformation."""
        cache_key = f"pan_{self._pan_state.offset.x}_{self._pan_state.offset.y}"
        
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create pan transformation
        transform = AffineTransformation.translation(
            self._pan_state.offset.x, self._pan_state.offset.y
        )
        
        # Cache the transformation
        self._transformation_cache.set(cache_key, transform)
        return transform
        
    def is_panning(self) -> bool:
        """Check if currently panning."""
        return self._pan_start_position is not None
        
    def has_momentum(self) -> bool:
        """Check if momentum animation is active."""
        return self._momentum_timer.isActive()
        
    def stop_momentum(self):
        """Stop momentum animation."""
        self._momentum_timer.stop()
        self._pan_state.velocity = Point(0, 0)
        
    def _animate_momentum(self):
        """Animate momentum decay."""
        # Apply momentum decay
        self._pan_state.velocity = Point(
            self._pan_state.velocity.x * self._pan_state.momentum_factor,
            self._pan_state.velocity.y * self._pan_state.momentum_factor
        )
        
        # Update offset
        self._pan_state.offset = Point(
            self._pan_state.offset.x + self._pan_state.velocity.x / 60.0,  # 60 FPS
            self._pan_state.offset.y + self._pan_state.velocity.y / 60.0
        )
        
        # Check if momentum should stop
        velocity_magnitude = math.sqrt(
            self._pan_state.velocity.x ** 2 + self._pan_state.velocity.y ** 2
        )
        
        if velocity_magnitude < self._pan_state.min_velocity:
            self._momentum_timer.stop()
            self._pan_state.velocity = Point(0, 0)
            self.pan_finished.emit(self._pan_state.offset)
        else:
            self._update_coordinate_mapper()
            self.pan_changed.emit(self._pan_state.offset)
            
    def _update_coordinate_mapper(self):
        """Update coordinate mapper with new pan."""
        pan_transform = self.get_pan_transformation()
        # Update coordinate mapper transformation
        
    def _start_smooth_pan(self, target_offset: Point):
        """Start smooth pan animation."""
        # Implementation for smooth animated panning
        pass
```

### 3. Rotation Transformation (`src/torematrix/ui/viewer/rotation.py`)
```python
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import math
import time

from .coordinates import CoordinateMapper
from .transformations import AffineTransformation
from .cache import TransformationCache
from ..utils.geometry import Point, Rect

@dataclass
class RotationState:
    """Current rotation state."""
    angle: float  # In radians
    center: Point
    snap_angle: float = math.pi / 12  # 15 degrees
    snap_threshold: float = 0.1

class RotationManager(QObject):
    """High-performance rotation transformation manager."""
    
    # Signals
    rotation_changed = pyqtSignal(float)  # angle
    rotation_started = pyqtSignal(Point)  # center
    rotation_finished = pyqtSignal(float)  # final_angle
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        super().__init__()
        self.coordinate_mapper = coordinate_mapper
        self._rotation_state = RotationState(0.0, Point(0, 0))
        self._transformation_cache = TransformationCache()
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        
    def rotate_to_angle(self, angle: float, center: Optional[Point] = None) -> bool:
        """Rotate to specific angle."""
        normalized_angle = self._normalize_angle(angle)
        
        # Apply snapping if enabled
        if self._should_snap(normalized_angle):
            normalized_angle = self._snap_angle(normalized_angle)
            
        old_angle = self._rotation_state.angle
        self._rotation_state.angle = normalized_angle
        
        if center:
            self._rotation_state.center = center
            
        # Update coordinate mapper
        self._update_coordinate_mapper()
        
        self.rotation_changed.emit(normalized_angle)
        
        # Update performance metrics
        self._update_performance_metrics('rotate_to_angle', old_angle, normalized_angle)
        
        return True
        
    def rotate_by_delta(self, delta_angle: float, center: Optional[Point] = None) -> bool:
        """Rotate by delta angle."""
        new_angle = self._rotation_state.angle + delta_angle
        return self.rotate_to_angle(new_angle, center)
        
    def rotate_to_cardinal(self, cardinal: str) -> bool:
        """Rotate to cardinal direction (north, east, south, west)."""
        cardinal_angles = {
            'north': 0.0,
            'east': math.pi / 2,
            'south': math.pi,
            'west': 3 * math.pi / 2
        }
        
        angle = cardinal_angles.get(cardinal.lower())
        if angle is None:
            return False
            
        return self.rotate_to_angle(angle)
        
    def smooth_rotate_to_angle(self, target_angle: float, center: Optional[Point] = None, 
                              duration: float = 0.5) -> bool:
        """Smooth animated rotation to target angle."""
        self._start_smooth_rotation(target_angle, center, duration)
        return True
        
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
        self._rotation_state.center = center
        
    def get_rotation_transformation(self) -> AffineTransformation:
        """Get current rotation transformation."""
        cache_key = f"rotation_{self._rotation_state.angle}_{self._rotation_state.center.x}_{self._rotation_state.center.y}"
        
        cached_transform = self._transformation_cache.get(cache_key)
        if cached_transform:
            return cached_transform
            
        # Create rotation transformation
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
        
    def reset_rotation(self):
        """Reset rotation to 0 degrees."""
        self.rotate_to_angle(0.0)
        
    def enable_angle_snapping(self, enabled: bool):
        """Enable or disable angle snapping."""
        # Implementation for angle snapping control
        pass
        
    def set_snap_angle(self, snap_angle: float):
        """Set snap angle in radians."""
        self._rotation_state.snap_angle = snap_angle
        
    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to [0, 2π] range."""
        return angle % (2 * math.pi)
        
    def _should_snap(self, angle: float) -> bool:
        """Check if angle should snap to grid."""
        snap_angle = self._rotation_state.snap_angle
        remainder = angle % snap_angle
        
        return (remainder < self._rotation_state.snap_threshold or 
                remainder > snap_angle - self._rotation_state.snap_threshold)
                
    def _snap_angle(self, angle: float) -> float:
        """Snap angle to nearest grid point."""
        snap_angle = self._rotation_state.snap_angle
        return round(angle / snap_angle) * snap_angle
        
    def _update_coordinate_mapper(self):
        """Update coordinate mapper with new rotation."""
        rotation_transform = self.get_rotation_transformation()
        # Update coordinate mapper transformation
        
    def _start_smooth_rotation(self, target_angle: float, center: Optional[Point], duration: float):
        """Start smooth rotation animation."""
        # Implementation for smooth animated rotation
        pass
        
    def _update_performance_metrics(self, operation: str, old_angle: float, new_angle: float):
        """Update performance metrics."""
        angle_change = abs(new_angle - old_angle)
        self._performance_metrics[operation] = angle_change
```

### 4. Advanced Caching System (`src/torematrix/ui/viewer/cache.py`)
```python
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass
import time
import threading
from collections import OrderedDict

from .transformations import AffineTransformation

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    timestamp: float
    access_count: int
    size: int

class TransformationCache:
    """High-performance transformation cache with smart eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory: int = 100 * 1024 * 1024):  # 100MB
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._max_memory = max_memory
        self._current_memory = 0
        self._lock = threading.RLock()
        
        # Cache statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage': 0
        }
        
    def get(self, key: str) -> Optional[AffineTransformation]:
        """Get transformation from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                entry.access_count += 1
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                
                self._stats['hits'] += 1
                return entry.value
            else:
                self._stats['misses'] += 1
                return None
                
    def set(self, key: str, value: AffineTransformation, size: Optional[int] = None):
        """Set transformation in cache."""
        with self._lock:
            if size is None:
                size = self._estimate_size(value)
                
            # Check if we need to evict
            while (len(self._cache) >= self._max_size or 
                   self._current_memory + size > self._max_memory):
                self._evict_lru()
                
            # Add new entry
            entry = CacheEntry(value, time.time(), 1, size)
            self._cache[key] = entry
            self._current_memory += size
            
            self._stats['memory_usage'] = self._current_memory
            
    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_memory -= entry.size
                self._stats['memory_usage'] = self._current_memory
                return True
            return False
            
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        with self._lock:
            keys_to_remove = []
            for key in self._cache:
                if pattern in key:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                self.invalidate(key)
                
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self._stats['memory_usage'] = 0
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            hit_rate = 0.0
            if self._stats['hits'] + self._stats['misses'] > 0:
                hit_rate = self._stats['hits'] / (self._stats['hits'] + self._stats['misses'])
                
            return {
                **self._stats,
                'hit_rate': hit_rate,
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'max_memory': self._max_memory
            }
            
    def optimize(self):
        """Optimize cache by removing old entries."""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 300  # 5 minutes
            
            keys_to_remove = []
            for key, entry in self._cache.items():
                if entry.timestamp < cutoff_time and entry.access_count < 2:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                self.invalidate(key)
                
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._current_memory -= entry.size
            self._stats['evictions'] += 1
            
    def _estimate_size(self, value: AffineTransformation) -> int:
        """Estimate size of transformation in bytes."""
        # Rough estimate: 9 floats (3x3 matrix) + overhead
        return 9 * 8 + 100  # 64-bit floats + object overhead

class CoordinateCache:
    """Specialized cache for coordinate transformations."""
    
    def __init__(self, max_entries: int = 10000):
        self._cache: Dict[Tuple[float, float, str], Tuple[float, float]] = {}
        self._max_entries = max_entries
        self._access_order: List[Tuple[float, float, str]] = []
        self._lock = threading.RLock()
        
    def get_transformed_point(self, x: float, y: float, transform_key: str) -> Optional[Tuple[float, float]]:
        """Get transformed point from cache."""
        with self._lock:
            key = (x, y, transform_key)
            if key in self._cache:
                # Update access order
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None
            
    def set_transformed_point(self, x: float, y: float, transform_key: str, 
                            result_x: float, result_y: float):
        """Set transformed point in cache."""
        with self._lock:
            key = (x, y, transform_key)
            
            # Evict if necessary
            while len(self._cache) >= self._max_entries:
                lru_key = self._access_order.pop(0)
                self._cache.pop(lru_key, None)
                
            self._cache[key] = (result_x, result_y)
            self._access_order.append(key)
            
    def invalidate_transform(self, transform_key: str):
        """Invalidate all entries for a transform."""
        with self._lock:
            keys_to_remove = []
            for key in self._cache:
                if key[2] == transform_key:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                self._cache.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
                    
    def clear(self):
        """Clear coordinate cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'memory_usage': len(self._cache) * 40  # Rough estimate
            }
```

## 🧪 Testing Requirements

### 1. Zoom Tests (`tests/unit/viewer/test_zoom.py`)
```python
import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QWheelEvent

from src.torematrix.ui.viewer.zoom import ZoomManager, ZoomState
from src.torematrix.ui.viewer.coordinates import CoordinateMapper
from src.torematrix.utils.geometry import Point, Rect

class TestZoomManager:
    def test_zoom_to_level(self):
        """Test zoom to specific level."""
        
    def test_zoom_bounds(self):
        """Test zoom level bounds enforcement."""
        
    def test_zoom_animation(self):
        """Test smooth zoom animation."""
        
    def test_zoom_performance(self):
        """Test zoom performance and caching."""
        
    def test_wheel_event_handling(self):
        """Test mouse wheel zoom handling."""
        
    def test_zoom_to_fit(self):
        """Test zoom to fit rectangle."""
```

### 2. Pan Tests (`tests/unit/viewer/test_pan.py`)
```python
import pytest
from unittest.mock import Mock
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QMouseEvent

from src.torematrix.ui.viewer.pan import PanManager, PanState
from src.torematrix.utils.geometry import Point

class TestPanManager:
    def test_pan_operations(self):
        """Test basic pan operations."""
        
    def test_pan_momentum(self):
        """Test pan momentum animation."""
        
    def test_pan_performance(self):
        """Test pan performance and caching."""
        
    def test_mouse_event_handling(self):
        """Test mouse event pan handling."""
```

### 3. Rotation Tests (`tests/unit/viewer/test_rotation.py`)
```python
import pytest
from unittest.mock import Mock
import math

from src.torematrix.ui.viewer.rotation import RotationManager, RotationState
from src.torematrix.utils.geometry import Point

class TestRotationManager:
    def test_rotation_operations(self):
        """Test basic rotation operations."""
        
    def test_angle_snapping(self):
        """Test angle snapping functionality."""
        
    def test_rotation_performance(self):
        """Test rotation performance and caching."""
        
    def test_cardinal_directions(self):
        """Test rotation to cardinal directions."""
```

### 4. Cache Tests (`tests/unit/viewer/test_cache.py`)
```python
import pytest
from unittest.mock import Mock
import time

from src.torematrix.ui.viewer.cache import TransformationCache, CoordinateCache
from src.torematrix.ui.viewer.transformations import AffineTransformation

class TestTransformationCache:
    def test_cache_operations(self):
        """Test basic cache operations."""
        
    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        
    def test_cache_performance(self):
        """Test cache performance metrics."""
        
    def test_memory_management(self):
        """Test memory usage management."""
```

## 🎯 Success Criteria

### Core Functionality
- [ ] ZoomManager with smooth zoom operations
- [ ] PanManager with momentum support
- [ ] RotationManager with angle snapping
- [ ] Advanced caching system with LRU eviction
- [ ] Performance monitoring and prediction

### Performance Requirements
- [ ] Zoom operations in <5ms
- [ ] Pan momentum at 60fps
- [ ] Rotation transformations in <2ms
- [ ] Cache hit rate >80%
- [ ] Memory usage <100MB

### User Experience
- [ ] Smooth zoom animations
- [ ] Natural pan momentum
- [ ] Angle snapping to common angles
- [ ] Real-time performance feedback

## 🔗 Integration Points

### From Agent 1 (Core Transformation Engine)
- Use `CoordinateMapper` for base coordinate system
- Utilize `AffineTransformation` for all transformations
- Apply geometric utilities for calculations

### From Agent 2 (Viewport & Screen Mapping)
- Use viewport bounds for optimization
- Apply screen coordinate conversions
- Integrate with DPI scaling

### For Agent 4 (Multi-Page Integration)
- Provide optimized transformation APIs
- Export performance monitoring tools
- Supply caching framework

## 📊 Performance Targets
- Zoom transformation: <5ms per operation
- Pan momentum: 60fps sustained
- Rotation transformation: <2ms per operation
- Cache lookup: <0.1ms per access
- Memory usage: <100MB for cache

## 🛠️ Development Workflow

### Phase 1: Core Optimizations (Days 3-4)
1. Implement zoom optimization with caching
2. Add pan momentum system
3. Create rotation with angle snapping
4. Build advanced caching framework

### Phase 2: Performance Tuning (Days 3-4)
1. Add performance monitoring
2. Optimize cache algorithms
3. Implement prediction systems
4. Add comprehensive testing

## 🚀 Getting Started

1. **Create your feature branch**: `git checkout -b feature/coordinates-optimization-agent3-issue151`
2. **Verify branch**: `git branch --show-current`
3. **Start with zoom manager**: Build high-performance zoom system
4. **Add pan momentum**: Implement smooth panning with momentum
5. **Create rotation system**: Add rotation with angle snapping
6. **Build caching**: Create advanced caching framework
7. **Test and optimize**: Ensure performance targets are met

## 📝 Implementation Notes

### Key Architecture Decisions
- Use Qt timers for smooth animations
- Implement LRU caching for transformations
- Pre-compute common transformation matrices
- Use threading for cache operations
- Monitor performance metrics in real-time

### Dependencies on Previous Agents
- Agent 1: Core coordinate transformation engine
- Agent 2: Viewport management for bounds optimization
- Complete integration with existing coordinate system

## 🎯 Communication Protocol

- **Daily Progress**: Comment on Issue #151 with performance metrics
- **Integration**: Coordinate with other agents via main issue #18
- **Performance**: Report benchmark results and optimization gains
- **Blockers**: Tag @insult0o for immediate assistance

## 📚 Reference Materials

- [Qt Animation Framework](https://doc.qt.io/qt-6/qtcore-animation-overview.html)
- [LRU Cache Implementation](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Computer Graphics Transformations](https://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/transforming-points-and-vectors)
- [Performance Optimization Techniques](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)

**Good luck, Agent 3! You're building the high-performance heart of the coordinate system, enabling smooth and responsive user interactions with advanced caching and optimization.**