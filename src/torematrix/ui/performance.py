"""Performance optimization utilities for ToreMatrix V3 UI.

This module provides performance monitoring, profiling, optimization utilities,
and memory management for maintaining smooth UI operations.
"""

from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import logging
import threading
import weakref
from pathlib import Path
import gc
import sys

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QIcon, QPixmap

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance optimization levels."""
    MINIMAL = "minimal"      # Basic optimizations
    BALANCED = "balanced"    # Good balance of features and performance
    MAXIMUM = "maximum"      # Maximum performance, may reduce some features


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    widget_creation_time: float = 0.0
    stylesheet_load_time: float = 0.0
    layout_time: float = 0.0
    paint_time: float = 0.0
    memory_usage_mb: float = 0.0
    widget_count: int = 0
    icon_cache_size: int = 0
    stylesheet_cache_size: int = 0


@dataclass
class OptimizationResult:
    """Result of an optimization operation."""
    success: bool
    time_saved_ms: float
    memory_saved_mb: float
    description: str
    recommendations: List[str]


class IconCache:
    """Intelligent icon caching system."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, QIcon] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_size = max_size
        self._access_times: Dict[str, float] = {}
    
    def get_icon(self, icon_path: str, size: Optional[int] = None) -> Optional[QIcon]:
        """Get icon from cache or load if not cached."""
        cache_key = f"{icon_path}:{size}" if size else icon_path
        
        if cache_key in self._cache:
            self._cache_hits += 1
            self._access_times[cache_key] = time.time()
            return self._cache[cache_key]
        
        # Cache miss - load icon
        self._cache_misses += 1
        icon = self._load_icon(icon_path, size)
        
        if icon and not icon.isNull():
            # Add to cache
            self._add_to_cache(cache_key, icon)
            return icon
        
        return None
    
    def _load_icon(self, icon_path: str, size: Optional[int] = None) -> Optional[QIcon]:
        """Load icon from file."""
        try:
            if Path(icon_path).exists():
                icon = QIcon(icon_path)
                if size:
                    # Pre-scale icon to requested size
                    pixmap = icon.pixmap(size, size)
                    icon = QIcon(pixmap)
                return icon
        except Exception as e:
            logger.error(f"Failed to load icon {icon_path}: {e}")
        
        return None
    
    def _add_to_cache(self, cache_key: str, icon: QIcon) -> None:
        """Add icon to cache with LRU eviction."""
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        self._cache[cache_key] = icon
        self._access_times[cache_key] = time.time()
    
    def _evict_oldest(self) -> None:
        """Evict least recently used icon."""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def clear(self) -> None:
        """Clear icon cache."""
        self._cache.clear()
        self._access_times.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate
        }


class StylesheetCache:
    """Stylesheet caching and optimization."""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._optimized_cache: Dict[str, str] = {}
        self._load_times: Dict[str, float] = {}
    
    def get_stylesheet(self, stylesheet_path: str, optimize: bool = True) -> Optional[str]:
        """Get stylesheet from cache or load and cache."""
        cache_key = f"{stylesheet_path}:{'opt' if optimize else 'raw'}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Load stylesheet
        start_time = time.time()
        stylesheet = self._load_stylesheet(stylesheet_path)
        load_time = time.time() - start_time
        
        if stylesheet:
            if optimize:
                stylesheet = self._optimize_stylesheet(stylesheet)
            
            self._cache[cache_key] = stylesheet
            self._load_times[stylesheet_path] = load_time
            
        return stylesheet
    
    def _load_stylesheet(self, stylesheet_path: str) -> Optional[str]:
        """Load stylesheet from file."""
        try:
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load stylesheet {stylesheet_path}: {e}")
            return None
    
    def _optimize_stylesheet(self, stylesheet: str) -> str:
        """Optimize stylesheet for better performance."""
        # Remove comments
        optimized = '\n'.join(
            line for line in stylesheet.split('\n')
            if not line.strip().startswith('/*') and not line.strip().startswith('//')
        )
        
        # Remove extra whitespace
        optimized = ' '.join(optimized.split())
        
        # Compress common patterns
        optimizations = {
            'margin: 0px 0px 0px 0px': 'margin: 0',
            'padding: 0px 0px 0px 0px': 'padding: 0',
            'border: 0px': 'border: none',
        }
        
        for old, new in optimizations.items():
            optimized = optimized.replace(old, new)
        
        return optimized
    
    def clear(self) -> None:
        """Clear stylesheet cache."""
        self._cache.clear()
        self._optimized_cache.clear()
        self._load_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "average_load_time": sum(self._load_times.values()) / len(self._load_times) if self._load_times else 0,
            "total_stylesheets": len(self._load_times)
        }


class PerformanceMonitor(QThread):
    """Background performance monitoring."""
    
    metrics_updated = pyqtSignal(PerformanceMetrics)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = False
        self._update_interval = 5.0  # seconds
        self._metrics = PerformanceMetrics()
    
    def start_monitoring(self, update_interval: float = 5.0) -> None:
        """Start performance monitoring."""
        self._update_interval = update_interval
        self._running = True
        self.start()
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._running = False
        self.quit()
        self.wait()
    
    def run(self) -> None:
        """Performance monitoring thread main loop."""
        while self._running:
            try:
                self._collect_metrics()
                self.metrics_updated.emit(self._metrics)
                self.msleep(int(self._update_interval * 1000))
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                self.msleep(1000)
    
    def _collect_metrics(self) -> None:
        """Collect current performance metrics."""
        import psutil
        import os
        
        # Memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        self._metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
        
        # Widget count
        app = QApplication.instance()
        if app:
            self._metrics.widget_count = len(app.allWidgets())
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current metrics snapshot."""
        self._collect_metrics()
        return self._metrics


class PerformanceOptimizer(BaseUIComponent):
    """Performance monitoring and optimization utilities."""
    
    # Signals
    optimization_completed = pyqtSignal(OptimizationResult)
    metrics_updated = pyqtSignal(PerformanceMetrics)
    performance_warning = pyqtSignal(str, float)  # warning_type, value
    
    # Performance targets
    PERFORMANCE_TARGETS = {
        'window_startup_time': 500,    # milliseconds
        'theme_switch_time': 200,      # milliseconds
        'layout_adapt_time': 100,      # milliseconds
        'memory_base_usage': 100,      # megabytes
        'icon_load_time': 50,          # milliseconds
    }
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Performance level
        self._performance_level = PerformanceLevel.BALANCED
        
        # Caching systems
        self._icon_cache = IconCache()
        self._stylesheet_cache = StylesheetCache()
        
        # Performance monitoring
        self._monitor = PerformanceMonitor(self)
        self._monitor.metrics_updated.connect(self.metrics_updated)
        
        # Profiling data
        self._profiling_data: Dict[str, List[float]] = {}
        self._widget_creation_times: Dict[str, float] = {}
        
        # Lazy loading registry
        self._lazy_components: Dict[str, Callable] = {}
        self._loaded_components: Set[str] = set()
        
        # Memory management
        self._memory_cleanup_timer = QTimer(self)
        self._memory_cleanup_timer.timeout.connect(self._perform_memory_cleanup)
    
    def _setup_component(self) -> None:
        """Setup the performance optimizer."""
        # Start performance monitoring
        self._monitor.start_monitoring()
        
        # Start memory cleanup timer (every 30 seconds)
        self._memory_cleanup_timer.start(30000)
        
        # Subscribe to relevant events
        self._event_bus.subscribe("ui.widget_created", self._handle_widget_created)
        self._event_bus.subscribe("ui.theme_changed", self._handle_theme_changed)
        
        logger.info("Performance optimizer initialized")
    
    def profile_widget_creation(self, widget_class: Type[QWidget]) -> Callable:
        """Decorator to profile widget creation time."""
        def decorator(create_func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = create_func(*args, **kwargs)
                creation_time = (time.time() - start_time) * 1000  # Convert to ms
                
                class_name = widget_class.__name__
                if class_name not in self._profiling_data:
                    self._profiling_data[class_name] = []
                
                self._profiling_data[class_name].append(creation_time)
                self._widget_creation_times[class_name] = creation_time
                
                # Check if creation time exceeds threshold
                if creation_time > 100:  # 100ms threshold
                    self.performance_warning.emit("slow_widget_creation", creation_time)
                
                return result
            return wrapper
        return decorator
    
    def optimize_stylesheet_loading(self, stylesheet_path: str) -> str:
        """Optimize stylesheet loading with caching."""
        start_time = time.time()
        
        stylesheet = self._stylesheet_cache.get_stylesheet(stylesheet_path, optimize=True)
        
        load_time = (time.time() - start_time) * 1000
        if load_time > 50:  # 50ms threshold
            self.performance_warning.emit("slow_stylesheet_load", load_time)
        
        return stylesheet or ""
    
    def cache_icon_renders(self, icon_name: str, sizes: List[int]) -> Dict[int, QIcon]:
        """Pre-cache icon renders for multiple sizes."""
        cached_icons = {}
        
        for size in sizes:
            icon = self._icon_cache.get_icon(icon_name, size)
            if icon:
                cached_icons[size] = icon
        
        return cached_icons
    
    def lazy_load_component(self, component_name: str, component_factory: Callable) -> None:
        """Register component for lazy loading."""
        self._lazy_components[component_name] = component_factory
    
    def load_component(self, component_name: str) -> Any:
        """Load a lazy-loaded component."""
        if component_name in self._loaded_components:
            return None  # Already loaded
        
        if component_name not in self._lazy_components:
            logger.warning(f"Lazy component '{component_name}' not registered")
            return None
        
        start_time = time.time()
        
        try:
            factory = self._lazy_components[component_name]
            component = factory()
            self._loaded_components.add(component_name)
            
            load_time = (time.time() - start_time) * 1000
            logger.debug(f"Lazy loaded component '{component_name}' in {load_time:.2f}ms")
            
            return component
            
        except Exception as e:
            logger.error(f"Failed to lazy load component '{component_name}': {e}")
            return None
    
    def monitor_memory_usage(self) -> Dict[str, float]:
        """Monitor current memory usage."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            usage = {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }
            
            # Check against thresholds
            if usage["rss_mb"] > self.PERFORMANCE_TARGETS["memory_base_usage"] * 2:
                self.performance_warning.emit("high_memory_usage", usage["rss_mb"])
            
            return usage
            
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return {}
        except Exception as e:
            logger.error(f"Memory monitoring error: {e}")
            return {}
    
    def _perform_memory_cleanup(self) -> None:
        """Perform periodic memory cleanup."""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clear unused caches
            self._cleanup_caches()
            
            # Log cleanup results
            if collected > 0:
                logger.debug(f"Memory cleanup: collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Memory cleanup error: {e}")
    
    def _cleanup_caches(self) -> None:
        """Clean up caches to free memory."""
        # Get cache stats before cleanup
        icon_stats = self._icon_cache.get_stats()
        
        # Clear caches if they're getting large
        if icon_stats["size"] > icon_stats["max_size"] * 0.8:
            # Clear least recently used items
            current_size = icon_stats["size"]
            target_size = icon_stats["max_size"] // 2
            
            for _ in range(current_size - target_size):
                self._icon_cache._evict_oldest()
    
    def set_performance_level(self, level: PerformanceLevel) -> None:
        """Set performance optimization level."""
        self._performance_level = level
        
        # Adjust caching based on performance level
        if level == PerformanceLevel.MINIMAL:
            self._icon_cache._max_size = 100
        elif level == PerformanceLevel.BALANCED:
            self._icon_cache._max_size = 500
        else:  # MAXIMUM
            self._icon_cache._max_size = 1000
        
        # Adjust monitoring frequency
        if level == PerformanceLevel.MAXIMUM:
            self._monitor._update_interval = 10.0  # Less frequent monitoring
        else:
            self._monitor._update_interval = 5.0
        
        logger.info(f"Performance level set to {level.value}")
    
    def get_performance_level(self) -> PerformanceLevel:
        """Get current performance level."""
        return self._performance_level
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self._monitor.get_current_metrics()
    
    def get_profiling_data(self) -> Dict[str, List[float]]:
        """Get widget creation profiling data."""
        return self._profiling_data.copy()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get all cache statistics."""
        return {
            "icon_cache": self._icon_cache.get_stats(),
            "stylesheet_cache": self._stylesheet_cache.get_stats(),
            "lazy_components": {
                "registered": len(self._lazy_components),
                "loaded": len(self._loaded_components)
            }
        }
    
    def benchmark_operation(self, operation_name: str, operation: Callable) -> float:
        """Benchmark an operation and return execution time in milliseconds."""
        start_time = time.time()
        
        try:
            operation()
        except Exception as e:
            logger.error(f"Benchmark operation '{operation_name}' failed: {e}")
            return -1
        
        execution_time = (time.time() - start_time) * 1000
        
        # Store benchmark result
        if operation_name not in self._profiling_data:
            self._profiling_data[operation_name] = []
        self._profiling_data[operation_name].append(execution_time)
        
        return execution_time
    
    def optimize_ui_performance(self) -> OptimizationResult:
        """Perform comprehensive UI performance optimization."""
        start_time = time.time()
        initial_memory = self.monitor_memory_usage().get("rss_mb", 0)
        
        optimizations = []
        
        try:
            # Clear unused caches
            self._cleanup_caches()
            optimizations.append("Cleaned up caches")
            
            # Force garbage collection
            collected = gc.collect()
            if collected > 0:
                optimizations.append(f"Collected {collected} objects")
            
            # Optimize widget hierarchy
            app = QApplication.instance()
            if app:
                widgets = app.allWidgets()
                orphaned_widgets = [w for w in widgets if w.parent() is None and not w.isVisible()]
                for widget in orphaned_widgets:
                    widget.deleteLater()
                
                if orphaned_widgets:
                    optimizations.append(f"Removed {len(orphaned_widgets)} orphaned widgets")
            
            # Calculate results
            end_time = time.time()
            final_memory = self.monitor_memory_usage().get("rss_mb", 0)
            
            time_saved = (end_time - start_time) * 1000
            memory_saved = initial_memory - final_memory
            
            result = OptimizationResult(
                success=True,
                time_saved_ms=time_saved,
                memory_saved_mb=max(0, memory_saved),
                description="UI performance optimization completed",
                recommendations=self._get_performance_recommendations()
            )
            
            self.optimization_completed.emit(result)
            return result
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return OptimizationResult(
                success=False,
                time_saved_ms=0,
                memory_saved_mb=0,
                description=f"Optimization failed: {e}",
                recommendations=[]
            )
    
    def _get_performance_recommendations(self) -> List[str]:
        """Get performance improvement recommendations."""
        recommendations = []
        
        # Check memory usage
        memory_usage = self.monitor_memory_usage().get("rss_mb", 0)
        if memory_usage > self.PERFORMANCE_TARGETS["memory_base_usage"] * 1.5:
            recommendations.append("Consider reducing widget complexity or implementing lazy loading")
        
        # Check cache hit rates
        icon_stats = self._icon_cache.get_stats()
        if icon_stats["hit_rate"] < 70:
            recommendations.append("Icon cache hit rate is low - consider pre-caching frequently used icons")
        
        # Check widget creation times
        slow_widgets = [
            name for name, times in self._profiling_data.items()
            if times and max(times) > 100
        ]
        if slow_widgets:
            recommendations.append(f"Slow widget creation detected: {', '.join(slow_widgets)}")
        
        return recommendations
    
    def _handle_widget_created(self, event_data: Dict[str, Any]) -> None:
        """Handle widget creation event."""
        widget_type = event_data.get("widget_type", "unknown")
        creation_time = event_data.get("creation_time", 0)
        
        if widget_type not in self._profiling_data:
            self._profiling_data[widget_type] = []
        
        self._profiling_data[widget_type].append(creation_time)
    
    def _handle_theme_changed(self, event_data: Dict[str, Any]) -> None:
        """Handle theme change event."""
        # Clear stylesheet cache when theme changes
        self._stylesheet_cache.clear()
        
        # Clear icon cache to reload themed icons
        self._icon_cache.clear()
    
    def cleanup(self) -> None:
        """Cleanup performance optimizer resources."""
        if self._monitor.isRunning():
            self._monitor.stop_monitoring()
        
        self._memory_cleanup_timer.stop()
        self._icon_cache.clear()
        self._stylesheet_cache.clear()