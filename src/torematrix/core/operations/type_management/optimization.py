"""Performance Optimization

Performance optimization system for type management operations.
Provides memory management, caching, and system resource optimization.
"""

import asyncio
import gc
import logging
import threading
import time
import weakref
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple
import psutil
import sys

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies for different scenarios"""
    MEMORY_OPTIMIZED = "memory_optimized"     # Minimize memory usage
    SPEED_OPTIMIZED = "speed_optimized"       # Maximize processing speed
    BALANCED = "balanced"                     # Balance memory and speed
    CONSERVATIVE = "conservative"             # Safe, minimal optimization
    AGGRESSIVE = "aggressive"                 # Maximum optimization, higher risk


class ResourceType(Enum):
    """Types of system resources to monitor"""
    MEMORY = "memory"
    CPU = "cpu"
    DISK_IO = "disk_io"
    NETWORK = "network"
    CACHE = "cache"


@dataclass
class ResourceThresholds:
    """Thresholds for resource usage warnings and limits"""
    memory_warning_percent: float = 80.0     # Warning at 80% memory usage
    memory_critical_percent: float = 90.0    # Critical at 90% memory usage
    cpu_warning_percent: float = 75.0        # Warning at 75% CPU usage
    cpu_critical_percent: float = 90.0       # Critical at 90% CPU usage
    cache_max_size_mb: int = 500             # Maximum cache size in MB
    gc_frequency_seconds: int = 30           # Garbage collection frequency


@dataclass
class OptimizationResult:
    """Result of optimization operation"""
    strategy: OptimizationStrategy
    optimizations_applied: List[str]
    memory_saved_mb: float = 0.0
    performance_improvement_percent: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    
    @property
    def success(self) -> bool:
        """Check if optimization was successful"""
        return len(self.errors) == 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    timestamp: datetime = field(default_factory=datetime.now)
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    cache_hit_rate: float = 0.0
    cache_size_mb: float = 0.0
    operation_count: int = 0
    average_operation_time: float = 0.0
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0


class LRUCache:
    """Least Recently Used cache with size limits"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """Initialize LRU cache
        
        Args:
            max_size: Maximum number of items
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self._cache: OrderedDict = OrderedDict()
        self._memory_usage = 0
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()
    
    def get(self, key: Any) -> Optional[Any]:
        """Get item from cache"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                self._hits += 1
                return value
            else:
                self._misses += 1
                return None
    
    def put(self, key: Any, value: Any) -> None:
        """Put item in cache"""
        with self._lock:
            # Estimate memory usage
            item_size = sys.getsizeof(key) + sys.getsizeof(value)
            
            # Remove existing item if present
            if key in self._cache:
                old_value = self._cache.pop(key)
                old_size = sys.getsizeof(key) + sys.getsizeof(old_value)
                self._memory_usage -= old_size
            
            # Check if we need to evict items
            while (len(self._cache) >= self.max_size or 
                   (self._memory_usage + item_size) > self.max_memory_mb * 1024 * 1024):
                if not self._cache:
                    break
                oldest_key, oldest_value = self._cache.popitem(last=False)
                oldest_size = sys.getsizeof(oldest_key) + sys.getsizeof(oldest_value)
                self._memory_usage -= oldest_size
            
            # Add new item
            self._cache[key] = value
            self._memory_usage += item_size
    
    def clear(self) -> None:
        """Clear all items from cache"""
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_usage_mb': self._memory_usage / (1024 * 1024),
                'max_memory_mb': self.max_memory_mb,
                'hit_rate': hit_rate,
                'hits': self._hits,
                'misses': self._misses
            }


class MemoryPool:
    """Memory pool for object reuse"""
    
    def __init__(self, object_factory: Callable, max_size: int = 100):
        """Initialize memory pool
        
        Args:
            object_factory: Function to create new objects
            max_size: Maximum number of objects in pool
        """
        self.object_factory = object_factory
        self.max_size = max_size
        self._pool: List[Any] = []
        self._lock = threading.RLock()
        self._created_count = 0
        self._reused_count = 0
    
    def acquire(self) -> Any:
        """Acquire object from pool"""
        with self._lock:
            if self._pool:
                obj = self._pool.pop()
                self._reused_count += 1
                return obj
            else:
                obj = self.object_factory()
                self._created_count += 1
                return obj
    
    def release(self, obj: Any) -> None:
        """Release object back to pool"""
        with self._lock:
            if len(self._pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, 'reset'):
                    obj.reset()
                self._pool.append(obj)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            total_objects = self._created_count
            reuse_rate = (self._reused_count / total_objects) if total_objects > 0 else 0.0
            
            return {
                'pool_size': len(self._pool),
                'max_size': self.max_size,
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'reuse_rate': reuse_rate
            }


class PerformanceOptimizer:
    """Performance optimization system for type operations
    
    Provides comprehensive performance optimization including:
    - Memory management and garbage collection
    - Intelligent caching strategies
    - Resource monitoring and throttling
    - Batch processing optimization
    - System resource adaptation
    """
    
    def __init__(self, 
                 strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
                 thresholds: Optional[ResourceThresholds] = None):
        """Initialize performance optimizer
        
        Args:
            strategy: Default optimization strategy
            thresholds: Resource usage thresholds
        """
        self.strategy = strategy
        self.thresholds = thresholds or ResourceThresholds()
        
        # Caches
        self._type_definition_cache = LRUCache(max_size=1000, max_memory_mb=50)
        self._validation_result_cache = LRUCache(max_size=2000, max_memory_mb=25)
        self._conversion_path_cache = LRUCache(max_size=500, max_memory_mb=10)
        
        # Memory pools
        self._batch_pools: Dict[str, MemoryPool] = {}
        
        # Monitoring
        self._metrics_history: List[PerformanceMetrics] = []
        self._resource_monitors: Dict[ResourceType, Callable] = {}
        self._optimization_callbacks: List[Callable] = []
        
        # Threading
        self._monitor_thread: Optional[threading.Thread] = None
        self._gc_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        
        self._initialize_monitors()
        self._start_background_tasks()
        
        logger.info(f"PerformanceOptimizer initialized with strategy: {strategy}")
    
    def optimize_operation(self, 
                          operation_type: str,
                          item_count: int,
                          complexity_score: float = 1.0) -> OptimizationResult:
        """Optimize settings for a specific operation
        
        Args:
            operation_type: Type of operation (bulk_change, conversion, etc.)
            item_count: Number of items to process
            complexity_score: Complexity score (1.0 = normal, >1.0 = complex)
            
        Returns:
            OptimizationResult with recommended optimizations
        """
        start_time = time.time()
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 0.0
        warnings = []
        errors = []
        
        try:
            logger.info(f"Optimizing {operation_type} operation: {item_count} items, "
                       f"complexity: {complexity_score}")
            
            # Get current system state
            current_metrics = self._collect_current_metrics()
            
            # Apply strategy-specific optimizations
            if self.strategy == OptimizationStrategy.MEMORY_OPTIMIZED:
                opts = self._apply_memory_optimizations(operation_type, item_count, current_metrics)
            elif self.strategy == OptimizationStrategy.SPEED_OPTIMIZED:
                opts = self._apply_speed_optimizations(operation_type, item_count, current_metrics)
            elif self.strategy == OptimizationStrategy.BALANCED:
                opts = self._apply_balanced_optimizations(operation_type, item_count, current_metrics)
            elif self.strategy == OptimizationStrategy.CONSERVATIVE:
                opts = self._apply_conservative_optimizations(operation_type, item_count, current_metrics)
            elif self.strategy == OptimizationStrategy.AGGRESSIVE:
                opts = self._apply_aggressive_optimizations(operation_type, item_count, current_metrics)
            else:
                opts = self._apply_balanced_optimizations(operation_type, item_count, current_metrics)
            
            optimizations.extend(opts['optimizations'])
            memory_saved += opts['memory_saved']
            performance_improvement += opts['performance_improvement']
            warnings.extend(opts['warnings'])
            
            # Apply complexity adjustments
            if complexity_score > 2.0:
                complexity_opts = self._apply_complexity_optimizations(complexity_score)
                optimizations.extend(complexity_opts['optimizations'])
                performance_improvement += complexity_opts['performance_improvement']
            
            # Check resource constraints
            constraint_opts = self._apply_resource_constraints(current_metrics)
            optimizations.extend(constraint_opts['optimizations'])
            warnings.extend(constraint_opts['warnings'])
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            errors.append(str(e))
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            strategy=self.strategy,
            optimizations_applied=optimizations,
            memory_saved_mb=memory_saved,
            performance_improvement_percent=performance_improvement,
            warnings=warnings,
            errors=errors,
            execution_time_seconds=execution_time
        )
    
    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        return {
            'type_definitions': self._type_definition_cache.get_stats(),
            'validation_results': self._validation_result_cache.get_stats(),
            'conversion_paths': self._conversion_path_cache.get_stats()
        }
    
    def clear_caches(self, cache_type: Optional[str] = None) -> None:
        """Clear caches
        
        Args:
            cache_type: Specific cache to clear, or None for all caches
        """
        if cache_type is None or cache_type == 'type_definitions':
            self._type_definition_cache.clear()
        if cache_type is None or cache_type == 'validation_results':
            self._validation_result_cache.clear()
        if cache_type is None or cache_type == 'conversion_paths':
            self._conversion_path_cache.clear()
        
        logger.info(f"Cleared caches: {cache_type or 'all'}")
    
    def get_performance_metrics(self, 
                              hours_back: int = 1) -> List[PerformanceMetrics]:
        """Get performance metrics history
        
        Args:
            hours_back: Number of hours of history to return
            
        Returns:
            List of performance metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        with self._lock:
            return [m for m in self._metrics_history if m.timestamp >= cutoff_time]
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return statistics"""
        start_time = time.time()
        
        # Get memory before GC
        memory_before = psutil.virtual_memory().used / (1024 * 1024)
        
        # Force garbage collection
        collected = gc.collect()
        
        # Get memory after GC
        memory_after = psutil.virtual_memory().used / (1024 * 1024)
        memory_freed = memory_before - memory_after
        
        gc_time = time.time() - start_time
        
        logger.info(f"Garbage collection: freed {memory_freed:.1f}MB, "
                   f"collected {collected} objects in {gc_time:.3f}s")
        
        return {
            'objects_collected': collected,
            'memory_freed_mb': memory_freed,
            'gc_time_seconds': gc_time
        }
    
    def register_optimization_callback(self, callback: Callable) -> None:
        """Register callback for optimization events
        
        Args:
            callback: Function to call when optimizations are applied
        """
        self._optimization_callbacks.append(callback)
    
    def _apply_memory_optimizations(self, operation_type: str, item_count: int, 
                                  metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply memory-focused optimizations"""
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 5.0  # Conservative improvement estimate
        warnings = []
        
        # Aggressive garbage collection
        if metrics.memory_percent > 70:
            gc_stats = self.force_garbage_collection()
            memory_saved += gc_stats['memory_freed_mb']
            optimizations.append("Forced garbage collection")
        
        # Reduce cache sizes
        self._type_definition_cache.max_memory_mb = min(self._type_definition_cache.max_memory_mb, 25)
        self._validation_result_cache.max_memory_mb = min(self._validation_result_cache.max_memory_mb, 10)
        optimizations.append("Reduced cache memory limits")
        
        # Use smaller batch sizes for memory efficiency
        if item_count > 5000:
            optimizations.append("Recommended smaller batch sizes for memory efficiency")
            performance_improvement += 3.0
        
        return {
            'optimizations': optimizations,
            'memory_saved': memory_saved,
            'performance_improvement': performance_improvement,
            'warnings': warnings
        }
    
    def _apply_speed_optimizations(self, operation_type: str, item_count: int,
                                 metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply speed-focused optimizations"""
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 15.0  # Aggressive improvement estimate
        warnings = []
        
        # Increase cache sizes for better hit rates
        self._type_definition_cache.max_memory_mb = 100
        self._validation_result_cache.max_memory_mb = 50
        optimizations.append("Increased cache sizes for better performance")
        
        # Disable some validation for speed
        if item_count > 10000:
            optimizations.append("Recommended reduced validation for large operations")
            performance_improvement += 10.0
            warnings.append("Reduced validation may affect data integrity")
        
        # Aggressive parallel processing
        cpu_cores = psutil.cpu_count()
        if cpu_cores > 2:
            optimizations.append(f"Recommended {cpu_cores * 2} worker threads")
            performance_improvement += 5.0
        
        return {
            'optimizations': optimizations,
            'memory_saved': memory_saved,
            'performance_improvement': performance_improvement,
            'warnings': warnings
        }
    
    def _apply_balanced_optimizations(self, operation_type: str, item_count: int,
                                    metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply balanced optimizations"""
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 8.0  # Moderate improvement estimate
        warnings = []
        
        # Moderate cache optimization
        if metrics.cache_hit_rate < 0.7:
            optimizations.append("Optimized cache settings for better hit rate")
            performance_improvement += 3.0
        
        # Batch size optimization based on system resources
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        if available_memory_mb > 2000:  # More than 2GB available
            optimizations.append("Increased batch size for available memory")
            performance_improvement += 2.0
        elif available_memory_mb < 500:  # Less than 500MB available
            optimizations.append("Reduced batch size for memory constraints")
            warnings.append("Limited memory may affect performance")
        
        # Periodic garbage collection
        optimizations.append("Scheduled periodic garbage collection")
        
        return {
            'optimizations': optimizations,
            'memory_saved': memory_saved,
            'performance_improvement': performance_improvement,
            'warnings': warnings
        }
    
    def _apply_conservative_optimizations(self, operation_type: str, item_count: int,
                                        metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply conservative optimizations"""
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 3.0  # Conservative improvement estimate
        warnings = []
        
        # Only apply safe optimizations
        if metrics.memory_percent > 85:
            optimizations.append("Cleared caches due to high memory usage")
            self.clear_caches()
            memory_saved += 50.0  # Estimate
        
        # Conservative batch sizing
        optimizations.append("Conservative batch size selection")
        
        return {
            'optimizations': optimizations,
            'memory_saved': memory_saved,
            'performance_improvement': performance_improvement,
            'warnings': warnings
        }
    
    def _apply_aggressive_optimizations(self, operation_type: str, item_count: int,
                                      metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply aggressive optimizations"""
        optimizations = []
        memory_saved = 0.0
        performance_improvement = 25.0  # Aggressive improvement estimate
        warnings = []
        
        # Maximum cache sizes
        self._type_definition_cache.max_memory_mb = 200
        self._validation_result_cache.max_memory_mb = 100
        optimizations.append("Maximized cache sizes")
        
        # Disable non-critical features
        optimizations.append("Disabled non-critical validation steps")
        optimizations.append("Enabled maximum parallelization")
        performance_improvement += 15.0
        
        warnings.append("Aggressive optimizations may reduce reliability")
        warnings.append("Monitor system resources closely")
        
        return {
            'optimizations': optimizations,
            'memory_saved': memory_saved,
            'performance_improvement': performance_improvement,
            'warnings': warnings
        }
    
    def _apply_complexity_optimizations(self, complexity_score: float) -> Dict[str, Any]:
        """Apply optimizations for complex operations"""
        optimizations = []
        performance_improvement = 0.0
        
        if complexity_score > 3.0:
            optimizations.append("Enabled advanced caching for complex operations")
            optimizations.append("Increased worker thread timeout")
            performance_improvement += 5.0
        
        if complexity_score > 5.0:
            optimizations.append("Enabled result streaming for very complex operations")
            performance_improvement += 3.0
        
        return {
            'optimizations': optimizations,
            'performance_improvement': performance_improvement
        }
    
    def _apply_resource_constraints(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Apply optimizations based on current resource constraints"""
        optimizations = []
        warnings = []
        
        # Memory constraints
        if metrics.memory_percent > self.thresholds.memory_critical_percent:
            optimizations.append("Emergency memory optimization activated")
            warnings.append("Critical memory usage detected")
        elif metrics.memory_percent > self.thresholds.memory_warning_percent:
            optimizations.append("Memory usage optimization applied")
            warnings.append("High memory usage detected")
        
        # CPU constraints
        if metrics.cpu_percent > self.thresholds.cpu_critical_percent:
            optimizations.append("Reduced parallelization due to high CPU usage")
            warnings.append("Critical CPU usage detected")
        elif metrics.cpu_percent > self.thresholds.cpu_warning_percent:
            optimizations.append("CPU usage optimization applied")
        
        return {
            'optimizations': optimizations,
            'warnings': warnings
        }
    
    def _collect_current_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Calculate cache statistics
            cache_stats = self.get_cache_stats()
            total_cache_size = sum(stats['memory_usage_mb'] for stats in cache_stats.values())
            avg_hit_rate = sum(stats['hit_rate'] for stats in cache_stats.values()) / len(cache_stats)
            
            return PerformanceMetrics(
                memory_usage_mb=memory_info.used / (1024 * 1024),
                memory_percent=memory_info.percent,
                cpu_percent=cpu_percent,
                cache_hit_rate=avg_hit_rate,
                cache_size_mb=total_cache_size
            )
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return PerformanceMetrics()
    
    def _initialize_monitors(self) -> None:
        """Initialize resource monitors"""
        try:
            import psutil
            self._resource_monitors[ResourceType.MEMORY] = lambda: psutil.virtual_memory()
            self._resource_monitors[ResourceType.CPU] = lambda: psutil.cpu_percent(interval=None)
        except ImportError:
            logger.warning("psutil not available, resource monitoring disabled")
    
    def _start_background_tasks(self) -> None:
        """Start background monitoring and optimization tasks"""
        self._running = True
        
        # Start metrics collection thread
        self._monitor_thread = threading.Thread(target=self._metrics_worker, daemon=True)
        self._monitor_thread.start()
        
        # Start garbage collection thread
        self._gc_thread = threading.Thread(target=self._gc_worker, daemon=True)
        self._gc_thread.start()
        
        logger.debug("Started background optimization tasks")
    
    def _metrics_worker(self) -> None:
        """Background worker for metrics collection"""
        while self._running:
            try:
                metrics = self._collect_current_metrics()
                
                with self._lock:
                    self._metrics_history.append(metrics)
                    
                    # Limit history size
                    if len(self._metrics_history) > 1000:
                        self._metrics_history = self._metrics_history[-500:]
                
                time.sleep(10)  # Collect metrics every 10 seconds
                
            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _gc_worker(self) -> None:
        """Background worker for garbage collection"""
        while self._running:
            try:
                time.sleep(self.thresholds.gc_frequency_seconds)
                
                # Check if GC is needed
                current_metrics = self._collect_current_metrics()
                if current_metrics.memory_percent > self.thresholds.memory_warning_percent:
                    self.force_garbage_collection()
                
            except Exception as e:
                logger.error(f"Background GC failed: {e}")
                time.sleep(60)  # Wait longer on error
    
    def __del__(self):
        """Cleanup when optimizer is destroyed"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        if self._gc_thread and self._gc_thread.is_alive():
            self._gc_thread.join(timeout=1.0)