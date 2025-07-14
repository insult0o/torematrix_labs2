"""Layout Performance Optimization for TORE Matrix Labs V3.

This module provides advanced performance optimization techniques for responsive
layouts including caching, lazy loading, memory management, and rendering optimization.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union, Tuple, NamedTuple
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import time
import weakref
import threading
import gc
import sys
from functools import lru_cache, wraps
from collections import defaultdict, deque
import psutil
import os

from PyQt6.QtWidgets import (
    QWidget, QLayout, QApplication, QGraphicsEffect, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    QObject, QTimer, QThread, QMutex, QWaitCondition, pyqtSignal,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize, QRect
)
from PyQt6.QtGui import QPainter, QPixmap, QPaintDevice

from ...core.events import EventBus
from ...core.config import ConfigurationManager

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance optimization levels."""
    MINIMAL = auto()     # Basic optimizations only
    STANDARD = auto()    # Standard optimizations
    AGGRESSIVE = auto()  # Aggressive optimizations, may affect features
    MAXIMUM = auto()     # Maximum optimizations, may affect quality


class OptimizationType(Enum):
    """Types of performance optimizations."""
    LAYOUT_CACHING = auto()
    WIDGET_POOLING = auto()
    LAZY_LOADING = auto()
    MEMORY_MANAGEMENT = auto()
    RENDER_OPTIMIZATION = auto()
    ANIMATION_THROTTLING = auto()
    EVENT_BATCHING = auto()


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    layout_calculation_time_ms: float = 0.0
    widget_creation_time_ms: float = 0.0
    rendering_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Counts
    total_layouts_calculated: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    widgets_created: int = 0
    widgets_destroyed: int = 0
    animations_active: int = 0
    
    # Rates (per second)
    layout_calculation_rate: float = 0.0
    animation_frame_rate: float = 0.0
    
    # Quality metrics
    frame_drops: int = 0
    layout_invalidations: int = 0
    memory_allocations: int = 0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.cache_hit_ratio = (
            self.cache_hits / max(1, self.cache_hits + self.cache_misses)
        )
        self.widgets_per_second = self.widgets_created / max(1, self.layout_calculation_time_ms / 1000)


class PerformanceProfiler:
    """Profiler for layout performance analysis."""
    
    def __init__(self, max_samples: int = 1000):
        self._max_samples = max_samples
        self._timing_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._memory_samples: deque = deque(maxlen=max_samples)
        self._active_timers: Dict[str, float] = {}
        self._mutex = threading.Lock()
        
        # Process monitoring
        self._process = psutil.Process(os.getpid())
        
    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        with self._mutex:
            self._active_timers[operation] = time.perf_counter()
    
    def end_timing(self, operation: str) -> float:
        """End timing an operation and return duration in milliseconds."""
        with self._mutex:
            if operation in self._active_timers:
                duration = (time.perf_counter() - self._active_timers[operation]) * 1000
                self._timing_data[operation].append(duration)
                del self._active_timers[operation]
                return duration
            return 0.0
    
    def record_memory_usage(self) -> float:
        """Record current memory usage and return in MB."""
        try:
            memory_mb = self._process.memory_info().rss / 1024 / 1024
            with self._mutex:
                self._memory_samples.append(memory_mb)
            return memory_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    
    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for a specific operation."""
        with self._mutex:
            if operation not in self._timing_data or not self._timing_data[operation]:
                return {}
            
            samples = list(self._timing_data[operation])
            
            return {
                'count': len(samples),
                'total_time_ms': sum(samples),
                'average_time_ms': sum(samples) / len(samples),
                'min_time_ms': min(samples),
                'max_time_ms': max(samples),
                'median_time_ms': sorted(samples)[len(samples) // 2],
                'p95_time_ms': sorted(samples)[int(len(samples) * 0.95)],
                'p99_time_ms': sorted(samples)[int(len(samples) * 0.99)]
            }
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        with self._mutex:
            if not self._memory_samples:
                return {}
            
            samples = list(self._memory_samples)
            
            return {
                'current_mb': samples[-1] if samples else 0.0,
                'average_mb': sum(samples) / len(samples),
                'min_mb': min(samples),
                'max_mb': max(samples),
                'growth_mb': samples[-1] - samples[0] if len(samples) > 1 else 0.0
            }
    
    def clear_data(self) -> None:
        """Clear all profiling data."""
        with self._mutex:
            self._timing_data.clear()
            self._memory_samples.clear()
            self._active_timers.clear()


def performance_timer(operation_name: str):
    """Decorator for automatic performance timing."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, '_profiler') and self._profiler:
                self._profiler.start_timing(operation_name)
                try:
                    result = func(self, *args, **kwargs)
                    return result
                finally:
                    self._profiler.end_timing(operation_name)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


class LayoutCache:
    """Advanced caching system for layout calculations."""
    
    def __init__(self, max_size: int = 200, ttl_seconds: float = 300.0):
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._access_order: deque = deque(maxlen=max_size)
        self._mutex = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        with self._mutex:
            if key in self._cache:
                value, timestamp = self._cache[key]
                
                # Check TTL
                if time.time() - timestamp <= self._ttl_seconds:
                    # Update access order
                    try:
                        self._access_order.remove(key)
                    except ValueError:
                        pass
                    self._access_order.append(key)
                    
                    self._hits += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put a value in cache."""
        with self._mutex:
            current_time = time.time()
            
            # Remove existing entry if present
            if key in self._cache:
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
            
            # Check if we need to evict
            while len(self._cache) >= self._max_size:
                oldest_key = self._access_order.popleft()
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
                    self._evictions += 1
            
            # Add new entry
            self._cache[key] = (value, current_time)
            self._access_order.append(key)
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        with self._mutex:
            if key in self._cache:
                del self._cache[key]
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._mutex:
            self._cache.clear()
            self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._mutex:
            total_requests = self._hits + self._misses
            hit_ratio = self._hits / max(1, total_requests)
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_ratio': hit_ratio,
                'memory_usage_estimate': sys.getsizeof(self._cache) + sum(
                    sys.getsizeof(k) + sys.getsizeof(v) for k, (v, _) in self._cache.items()
                )
            }


class WidgetPool:
    """Object pool for widget reuse to reduce allocation overhead."""
    
    def __init__(self, widget_factory: Callable[[], QWidget], max_size: int = 50):
        self._widget_factory = widget_factory
        self._max_size = max_size
        self._available_widgets: List[QWidget] = []
        self._in_use_widgets: Set[QWidget] = set()
        self._mutex = threading.Lock()
        
        # Statistics
        self._widgets_created = 0
        self._widgets_reused = 0
    
    def acquire_widget(self) -> QWidget:
        """Acquire a widget from the pool."""
        with self._mutex:
            if self._available_widgets:
                widget = self._available_widgets.pop()
                self._in_use_widgets.add(widget)
                self._widgets_reused += 1
                
                # Reset widget state
                self._reset_widget(widget)
                return widget
            else:
                # Create new widget
                widget = self._widget_factory()
                self._in_use_widgets.add(widget)
                self._widgets_created += 1
                return widget
    
    def release_widget(self, widget: QWidget) -> None:
        """Release a widget back to the pool."""
        with self._mutex:
            if widget in self._in_use_widgets:
                self._in_use_widgets.remove(widget)
                
                # Add to available pool if there's space
                if len(self._available_widgets) < self._max_size:
                    self._available_widgets.append(widget)
                    widget.setParent(None)  # Remove from layout
                    widget.hide()
                else:
                    # Pool is full, destroy widget
                    widget.deleteLater()
    
    def _reset_widget(self, widget: QWidget) -> None:
        """Reset widget state for reuse."""
        widget.setVisible(True)
        widget.setEnabled(True)
        widget.setStyleSheet("")
        widget.setToolTip("")
        
        # Reset size constraints
        widget.setMinimumSize(0, 0)
        widget.setMaximumSize(16777215, 16777215)  # Qt's default maximum
    
    def clear_pool(self) -> None:
        """Clear all widgets from the pool."""
        with self._mutex:
            for widget in self._available_widgets:
                widget.deleteLater()
            self._available_widgets.clear()
            
            # Note: in_use_widgets are managed by their owners
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        with self._mutex:
            return {
                'available': len(self._available_widgets),
                'in_use': len(self._in_use_widgets),
                'created': self._widgets_created,
                'reused': self._widgets_reused,
                'reuse_ratio': self._widgets_reused / max(1, self._widgets_created + self._widgets_reused)
            }


class LazyLoader:
    """Lazy loading system for widgets and content."""
    
    def __init__(self, viewport_margin: int = 100):
        self._viewport_margin = viewport_margin
        self._lazy_widgets: Dict[QWidget, Callable[[], None]] = {}
        self._loaded_widgets: Set[QWidget] = set()
        self._mutex = threading.Lock()
    
    def register_lazy_widget(self, widget: QWidget, loader: Callable[[], None]) -> None:
        """Register a widget for lazy loading."""
        with self._mutex:
            self._lazy_widgets[widget] = loader
    
    def unregister_lazy_widget(self, widget: QWidget) -> None:
        """Unregister a widget from lazy loading."""
        with self._mutex:
            self._lazy_widgets.pop(widget, None)
            self._loaded_widgets.discard(widget)
    
    def check_and_load_widgets(self, viewport_rect: QRect) -> List[QWidget]:
        """Check which widgets should be loaded based on viewport."""
        loaded_widgets = []
        
        with self._mutex:
            for widget, loader in list(self._lazy_widgets.items()):
                if widget in self._loaded_widgets:
                    continue
                
                widget_rect = widget.geometry()
                
                # Expand viewport by margin
                expanded_viewport = QRect(
                    viewport_rect.x() - self._viewport_margin,
                    viewport_rect.y() - self._viewport_margin,
                    viewport_rect.width() + 2 * self._viewport_margin,
                    viewport_rect.height() + 2 * self._viewport_margin
                )
                
                # Check if widget intersects with expanded viewport
                if widget_rect.intersects(expanded_viewport):
                    try:
                        loader()
                        self._loaded_widgets.add(widget)
                        loaded_widgets.append(widget)
                    except Exception as e:
                        logger.error(f"Error loading lazy widget: {e}")
        
        return loaded_widgets
    
    def unload_distant_widgets(self, viewport_rect: QRect) -> List[QWidget]:
        """Unload widgets that are far from the viewport."""
        unloaded_widgets = []
        unload_margin = self._viewport_margin * 3  # Larger margin for unloading
        
        with self._mutex:
            for widget in list(self._loaded_widgets):
                widget_rect = widget.geometry()
                
                # Calculate distance from viewport
                distance = self._calculate_distance_to_rect(widget_rect, viewport_rect)
                
                if distance > unload_margin:
                    # Unload widget content but keep structure
                    try:
                        self._unload_widget_content(widget)
                        self._loaded_widgets.discard(widget)
                        unloaded_widgets.append(widget)
                    except Exception as e:
                        logger.error(f"Error unloading widget: {e}")
        
        return unloaded_widgets
    
    def _calculate_distance_to_rect(self, rect1: QRect, rect2: QRect) -> float:
        """Calculate minimum distance between two rectangles."""
        if rect1.intersects(rect2):
            return 0.0
        
        # Calculate distances between edges
        dx = max(0, max(rect1.left() - rect2.right(), rect2.left() - rect1.right()))
        dy = max(0, max(rect1.top() - rect2.bottom(), rect2.top() - rect1.bottom()))
        
        return (dx * dx + dy * dy) ** 0.5
    
    def _unload_widget_content(self, widget: QWidget) -> None:
        """Unload widget content to free memory."""
        # This is a placeholder - specific implementations would depend on widget type
        # For example, could clear images, text content, etc.
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """Get lazy loading statistics."""
        with self._mutex:
            return {
                'registered': len(self._lazy_widgets),
                'loaded': len(self._loaded_widgets),
                'pending': len(self._lazy_widgets) - len(self._loaded_widgets)
            }


class MemoryOptimizer:
    """Memory optimization utilities for layout performance."""
    
    def __init__(self):
        self._weak_references: Set[weakref.ref] = set()
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_references)
        self._cleanup_timer.start(30000)  # Clean up every 30 seconds
    
    def register_for_cleanup(self, obj: QObject) -> None:
        """Register an object for memory cleanup."""
        def cleanup_callback(ref):
            self._weak_references.discard(ref)
        
        weak_ref = weakref.ref(obj, cleanup_callback)
        self._weak_references.add(weak_ref)
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics."""
        before_objects = len(gc.get_objects())
        before_memory = self._get_memory_usage()
        
        # Force collection
        collected = gc.collect()
        
        after_objects = len(gc.get_objects())
        after_memory = self._get_memory_usage()
        
        return {
            'objects_before': before_objects,
            'objects_after': after_objects,
            'objects_collected': before_objects - after_objects,
            'memory_before_mb': before_memory,
            'memory_after_mb': after_memory,
            'memory_freed_mb': before_memory - after_memory,
            'gc_collected': collected
        }
    
    def _cleanup_references(self) -> None:
        """Clean up dead weak references."""
        dead_refs = [ref for ref in self._weak_references if ref() is None]
        for ref in dead_refs:
            self._weak_references.discard(ref)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    
    def optimize_widget_memory(self, widget: QWidget) -> None:
        """Optimize memory usage for a specific widget."""
        # Clear pixmap cache if widget has one
        if hasattr(widget, 'pixmap') and widget.pixmap():
            # Store placeholder and clear actual pixmap
            widget.setProperty('_original_pixmap_size', widget.pixmap().size())
            widget.clear()
        
        # Clear style sheet cache
        widget.setStyleSheet("")
        
        # Remove tooltips and other string properties
        widget.setToolTip("")
        widget.setWhatsThis("")


class RenderOptimizer:
    """Rendering optimization for layout performance."""
    
    def __init__(self):
        self._render_cache: Dict[str, QPixmap] = {}
        self._cache_mutex = threading.Lock()
        self._max_cache_size = 50
    
    def cache_widget_render(self, widget: QWidget, cache_key: str) -> QPixmap:
        """Cache a widget's rendered appearance."""
        with self._cache_mutex:
            if cache_key in self._render_cache:
                return self._render_cache[cache_key]
            
            # Render widget to pixmap
            pixmap = QPixmap(widget.size())
            widget.render(pixmap)
            
            # Cache management
            if len(self._render_cache) >= self._max_cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._render_cache))
                del self._render_cache[oldest_key]
            
            self._render_cache[cache_key] = pixmap
            return pixmap
    
    def get_cached_render(self, cache_key: str) -> Optional[QPixmap]:
        """Get a cached render if available."""
        with self._cache_mutex:
            return self._render_cache.get(cache_key)
    
    def invalidate_render_cache(self, cache_key: str = None) -> None:
        """Invalidate render cache entries."""
        with self._cache_mutex:
            if cache_key:
                self._render_cache.pop(cache_key, None)
            else:
                self._render_cache.clear()
    
    def optimize_widget_rendering(self, widget: QWidget) -> None:
        """Optimize rendering for a specific widget."""
        # Disable effects during layout changes
        if hasattr(widget, '_layout_changing'):
            effects = widget.graphicsEffect()
            if effects:
                effects.setEnabled(False)
        
        # Use faster composition mode for overlapping widgets
        widget.setAttribute(Qt.WA_OpaquePaintEvent, True)


class PerformanceOptimizer(QObject):
    """Main performance optimization coordinator."""
    
    # Signals
    performance_warning = pyqtSignal(str, float)
    optimization_applied = pyqtSignal(str, dict)
    metrics_updated = pyqtSignal(PerformanceMetrics)
    
    def __init__(
        self,
        config_manager: ConfigurationManager,
        performance_level: PerformanceLevel = PerformanceLevel.STANDARD,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        self._config_manager = config_manager
        self._performance_level = performance_level
        
        # Core components
        self._profiler = PerformanceProfiler()
        self._layout_cache = LayoutCache()
        self._widget_pools: Dict[str, WidgetPool] = {}
        self._lazy_loader = LazyLoader()
        self._memory_optimizer = MemoryOptimizer()
        self._render_optimizer = RenderOptimizer()
        
        # Monitoring
        self._metrics = PerformanceMetrics()
        self._monitoring_timer = QTimer()
        self._monitoring_timer.timeout.connect(self._update_metrics)
        self._monitoring_timer.start(1000)  # Update metrics every second
        
        # Optimization flags
        self._optimizations_enabled: Set[OptimizationType] = set()
        self._initialize_optimizations()
        
        logger.debug(f"PerformanceOptimizer initialized with level: {performance_level.name}")
    
    def _initialize_optimizations(self) -> None:
        """Initialize optimizations based on performance level."""
        if self._performance_level >= PerformanceLevel.MINIMAL:
            self._optimizations_enabled.add(OptimizationType.LAYOUT_CACHING)
        
        if self._performance_level >= PerformanceLevel.STANDARD:
            self._optimizations_enabled.add(OptimizationType.WIDGET_POOLING)
            self._optimizations_enabled.add(OptimizationType.MEMORY_MANAGEMENT)
        
        if self._performance_level >= PerformanceLevel.AGGRESSIVE:
            self._optimizations_enabled.add(OptimizationType.LAZY_LOADING)
            self._optimizations_enabled.add(OptimizationType.RENDER_OPTIMIZATION)
            self._optimizations_enabled.add(OptimizationType.ANIMATION_THROTTLING)
        
        if self._performance_level >= PerformanceLevel.MAXIMUM:
            self._optimizations_enabled.add(OptimizationType.EVENT_BATCHING)
    
    @performance_timer("layout_calculation")
    def optimize_layout_calculation(self, calculation_func: Callable, *args, **kwargs) -> Any:
        """Optimize layout calculation with caching."""
        if OptimizationType.LAYOUT_CACHING not in self._optimizations_enabled:
            return calculation_func(*args, **kwargs)
        
        # Generate cache key
        cache_key = self._generate_layout_cache_key(*args, **kwargs)
        
        # Check cache
        cached_result = self._layout_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Calculate and cache
        result = calculation_func(*args, **kwargs)
        self._layout_cache.put(cache_key, result)
        
        return result
    
    def create_widget_pool(self, pool_name: str, widget_factory: Callable[[], QWidget]) -> WidgetPool:
        """Create a widget pool for performance optimization."""
        if OptimizationType.WIDGET_POOLING not in self._optimizations_enabled:
            # Return a dummy pool that just creates widgets
            class DummyPool:
                def acquire_widget(self):
                    return widget_factory()
                def release_widget(self, widget):
                    widget.deleteLater()
                def get_stats(self):
                    return {}
            return DummyPool()
        
        pool = WidgetPool(widget_factory)
        self._widget_pools[pool_name] = pool
        return pool
    
    def optimize_widget_for_viewport(self, widget: QWidget, viewport_rect: QRect) -> None:
        """Optimize widget based on viewport visibility."""
        if OptimizationType.LAZY_LOADING in self._optimizations_enabled:
            # Check if widget needs loading/unloading
            self._lazy_loader.check_and_load_widgets(viewport_rect)
            self._lazy_loader.unload_distant_widgets(viewport_rect)
        
        if OptimizationType.RENDER_OPTIMIZATION in self._optimizations_enabled:
            self._render_optimizer.optimize_widget_rendering(widget)
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Perform memory optimization and return statistics."""
        if OptimizationType.MEMORY_MANAGEMENT not in self._optimizations_enabled:
            return {}
        
        # Force garbage collection
        gc_stats = self._memory_optimizer.force_garbage_collection()
        
        # Clear caches if memory usage is high
        memory_usage = self._profiler.record_memory_usage()
        if memory_usage > 500:  # 500MB threshold
            self._layout_cache.clear()
            self._render_optimizer.invalidate_render_cache()
            
            logger.warning(f"High memory usage detected ({memory_usage:.1f}MB), clearing caches")
            self.performance_warning.emit("High memory usage", memory_usage)
        
        return gc_stats
    
    def _generate_layout_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key for layout calculations."""
        # Simple hash-based cache key generation
        key_data = str(args) + str(sorted(kwargs.items()))
        return str(hash(key_data))
    
    def _update_metrics(self) -> None:
        """Update performance metrics."""
        # Update profiler memory
        memory_usage = self._profiler.record_memory_usage()
        
        # Calculate CPU usage
        try:
            process = psutil.Process(os.getpid())
            cpu_usage = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cpu_usage = 0.0
        
        # Update metrics object
        self._metrics.memory_usage_mb = memory_usage
        self._metrics.cpu_usage_percent = cpu_usage
        
        # Get cache statistics
        cache_stats = self._layout_cache.get_stats()
        self._metrics.cache_hits = cache_stats.get('hits', 0)
        self._metrics.cache_misses = cache_stats.get('misses', 0)
        
        # Update widget pool statistics
        total_widgets_created = sum(
            pool.get_stats().get('created', 0) for pool in self._widget_pools.values()
        )
        self._metrics.widgets_created = total_widgets_created
        
        # Emit updated metrics
        self.metrics_updated.emit(self._metrics)
        
        # Check for performance warnings
        if memory_usage > 1000:  # 1GB warning threshold
            self.performance_warning.emit("Very high memory usage", memory_usage)
        
        if cpu_usage > 80:
            self.performance_warning.emit("High CPU usage", cpu_usage)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
            'metrics': self._metrics,
            'profiler': {
                'layout_calculation': self._profiler.get_operation_stats('layout_calculation'),
                'widget_creation': self._profiler.get_operation_stats('widget_creation'),
                'memory': self._profiler.get_memory_stats()
            },
            'cache': self._layout_cache.get_stats(),
            'widget_pools': {
                name: pool.get_stats() for name, pool in self._widget_pools.items()
            },
            'lazy_loader': self._lazy_loader.get_stats(),
            'optimizations_enabled': [opt.name for opt in self._optimizations_enabled],
            'performance_level': self._performance_level.name
        }
        
        return stats
    
    def set_performance_level(self, level: PerformanceLevel) -> None:
        """Change the performance optimization level."""
        self._performance_level = level
        self._optimizations_enabled.clear()
        self._initialize_optimizations()
        
        logger.info(f"Performance level changed to: {level.name}")
        self.optimization_applied.emit("performance_level_changed", {"level": level.name})
    
    def enable_optimization(self, optimization: OptimizationType) -> None:
        """Enable a specific optimization."""
        self._optimizations_enabled.add(optimization)
        logger.debug(f"Enabled optimization: {optimization.name}")
    
    def disable_optimization(self, optimization: OptimizationType) -> None:
        """Disable a specific optimization."""
        self._optimizations_enabled.discard(optimization)
        logger.debug(f"Disabled optimization: {optimization.name}")
    
    def clear_all_caches(self) -> None:
        """Clear all performance caches."""
        self._layout_cache.clear()
        self._render_optimizer.invalidate_render_cache()
        self._profiler.clear_data()
        
        logger.info("All performance caches cleared")
        self.optimization_applied.emit("caches_cleared", {})
    
    def get_profiler(self) -> PerformanceProfiler:
        """Get the performance profiler for external use."""
        return self._profiler


# Import QRect for type hints
from PyQt6.QtCore import QRect