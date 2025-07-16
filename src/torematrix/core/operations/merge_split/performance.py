"""
Performance Optimization Components for Merge/Split Operations.

This module provides caching, memory optimization, and asynchronous processing
capabilities to ensure efficient handling of large document processing tasks.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import asyncio
import threading
import weakref
import pickle
import hashlib
from collections import OrderedDict, defaultdict
from functools import wraps, lru_cache
import psutil
import logging

from ..core.elements import Element
from ..core.metadata import Metadata


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    HYBRID = "hybrid"  # Combination of strategies


class ProcessingPriority(Enum):
    """Processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CacheEntry:
    """Cache entry with metadata for optimization."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    
    def __post_init__(self):
        """Calculate entry size after initialization."""
        self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value."""
        try:
            return len(pickle.dumps(self.value))
        except:
            return 1024  # Default size estimate
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access metadata."""
        self.last_accessed = time.time()
        self.access_count += 1


class CoordinateCache:
    """
    High-performance cache for coordinate calculations and transformations.
    
    Optimized for frequent lookups of element positions, bounding boxes,
    and geometric calculations common in merge/split operations.
    """
    
    def __init__(self, 
                 max_size: int = 10000,
                 max_memory_mb: int = 50,
                 strategy: CacheStrategy = CacheStrategy.HYBRID,
                 default_ttl: float = 3600.0):
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.access_counts: Dict[str, int] = defaultdict(int)
        self.size_bytes = 0
        
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'memory_usage_mb': 0.0,
            'average_lookup_time_ms': 0.0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        start_time = time.time()
        
        with self.lock:
            self.metrics['total_requests'] += 1
            
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if entry.is_expired():
                    self._remove_entry(key)
                    self.metrics['misses'] += 1
                    return None
                
                # Update access metadata
                entry.touch()
                self.access_counts[key] += 1
                
                # Move to end for LRU
                if self.strategy in [CacheStrategy.LRU, CacheStrategy.HYBRID]:
                    self.cache.move_to_end(key)
                
                self.metrics['hits'] += 1
                self._update_lookup_time(time.time() - start_time)
                return entry.value
            
            self.metrics['misses'] += 1
            self._update_lookup_time(time.time() - start_time)
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        with self.lock:
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl or self.default_ttl
            )
            
            # Check if we need to evict entries
            self._ensure_capacity(entry.size_bytes)
            
            # Add new entry
            self.cache[key] = entry
            self.size_bytes += entry.size_bytes
            self._update_memory_metrics()
            
            self.logger.debug(f"Cached {key} ({entry.size_bytes} bytes)")
    
    def remove(self, key: str) -> bool:
        """
        Remove entry from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if entry was removed
        """
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.access_counts.clear()
            self.size_bytes = 0
            self._update_memory_metrics()
            self.logger.info("Cache cleared")
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        with self.lock:
            total = self.metrics['total_requests']
            if total == 0:
                return 0.0
            return (self.metrics['hits'] / total) * 100.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                **self.metrics,
                'size': len(self.cache),
                'hit_rate_percent': self.get_hit_rate(),
                'size_bytes': self.size_bytes
            }
    
    # Cache key generation utilities
    
    @staticmethod
    def element_bounds_key(element_id: str, page_number: int) -> str:
        """Generate cache key for element bounds."""
        return f"bounds:{element_id}:{page_number}"
    
    @staticmethod
    def transformation_key(element_id: str, transform_params: Dict[str, Any]) -> str:
        """Generate cache key for coordinate transformations."""
        params_hash = hashlib.md5(str(sorted(transform_params.items())).encode()).hexdigest()
        return f"transform:{element_id}:{params_hash}"
    
    @staticmethod
    def intersection_key(element_id1: str, element_id2: str) -> str:
        """Generate cache key for element intersection calculations."""
        # Ensure consistent ordering
        ids = sorted([element_id1, element_id2])
        return f"intersection:{ids[0]}:{ids[1]}"
    
    # Private methods
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache and update metrics."""
        if key in self.cache:
            entry = self.cache[key]
            self.size_bytes -= entry.size_bytes
            del self.cache[key]
            if key in self.access_counts:
                del self.access_counts[key]
    
    def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry."""
        # Check size limit
        while len(self.cache) >= self.max_size:
            self._evict_entry()
        
        # Check memory limit
        max_memory_bytes = self.max_memory_mb * 1024 * 1024
        while (self.size_bytes + new_entry_size) > max_memory_bytes:
            if not self.cache:  # Prevent infinite loop
                break
            self._evict_entry()
    
    def _evict_entry(self) -> None:
        """Evict an entry based on the configured strategy."""
        if not self.cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            key = next(iter(self.cache))  # First item (oldest)
        elif self.strategy == CacheStrategy.LFU:
            key = min(self.access_counts, key=self.access_counts.get)
        elif self.strategy == CacheStrategy.TTL:
            # Find expired entries first
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            key = expired_keys[0] if expired_keys else next(iter(self.cache))
        else:  # HYBRID
            # Check for expired entries first
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            if expired_keys:
                key = expired_keys[0]
            else:
                # Use LRU for non-expired entries
                key = next(iter(self.cache))
        
        self._remove_entry(key)
        self.metrics['evictions'] += 1
    
    def _update_memory_metrics(self) -> None:
        """Update memory usage metrics."""
        self.metrics['memory_usage_mb'] = self.size_bytes / (1024 * 1024)
    
    def _update_lookup_time(self, time_seconds: float) -> None:
        """Update average lookup time."""
        time_ms = time_seconds * 1000
        current_avg = self.metrics['average_lookup_time_ms']
        total_requests = self.metrics['total_requests']
        
        if total_requests > 1:
            self.metrics['average_lookup_time_ms'] = ((current_avg * (total_requests - 1)) + time_ms) / total_requests
        else:
            self.metrics['average_lookup_time_ms'] = time_ms


class MemoryOptimizer:
    """
    Memory optimization utilities for large document processing.
    
    Provides lazy loading, memory monitoring, and automatic cleanup
    to prevent memory issues during intensive operations.
    """
    
    def __init__(self, 
                 memory_limit_mb: int = 500,
                 warning_threshold: float = 0.8,
                 cleanup_threshold: float = 0.9):
        self.memory_limit_mb = memory_limit_mb
        self.warning_threshold = warning_threshold
        self.cleanup_threshold = cleanup_threshold
        
        self.lazy_objects: Dict[str, weakref.ref] = {}
        self.cleanup_callbacks: List[Callable[[], None]] = []
        
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Memory monitoring
        self.monitoring_enabled = True
        self.last_memory_check = time.time()
        self.check_interval = 5.0  # seconds
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for memory cleanup."""
        with self.lock:
            self.cleanup_callbacks.append(callback)
    
    def create_lazy_loader(self, loader_id: str, load_func: Callable[[], Any]) -> Callable[[], Any]:
        """
        Create a lazy loader for expensive objects.
        
        Args:
            loader_id: Unique identifier for the loader
            load_func: Function to load the object
            
        Returns:
            Lazy loading function
        """
        def lazy_load():
            with self.lock:
                # Check if object is already loaded
                if loader_id in self.lazy_objects:
                    obj_ref = self.lazy_objects[loader_id]
                    obj = obj_ref()
                    if obj is not None:
                        return obj
                
                # Load object
                obj = load_func()
                
                # Store weak reference
                self.lazy_objects[loader_id] = weakref.ref(obj)
                
                # Check memory usage
                self._check_memory_usage()
                
                return obj
        
        return lazy_load
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage information."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024
            }
        except:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0}
    
    def should_cleanup(self) -> bool:
        """Check if memory cleanup is needed."""
        memory_usage = self.get_memory_usage()
        current_mb = memory_usage['rss_mb']
        
        return current_mb > (self.memory_limit_mb * self.cleanup_threshold)
    
    def force_cleanup(self) -> Dict[str, int]:
        """Force memory cleanup and return statistics."""
        with self.lock:
            cleanup_stats = {
                'lazy_objects_cleaned': 0,
                'callbacks_executed': 0,
                'memory_before_mb': self.get_memory_usage()['rss_mb']
            }
            
            # Clean up lazy objects
            dead_refs = []
            for loader_id, obj_ref in self.lazy_objects.items():
                if obj_ref() is None:
                    dead_refs.append(loader_id)
            
            for loader_id in dead_refs:
                del self.lazy_objects[loader_id]
                cleanup_stats['lazy_objects_cleaned'] += 1
            
            # Execute cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                    cleanup_stats['callbacks_executed'] += 1
                except Exception as e:
                    self.logger.warning(f"Cleanup callback failed: {e}")
            
            cleanup_stats['memory_after_mb'] = self.get_memory_usage()['rss_mb']
            cleanup_stats['memory_freed_mb'] = cleanup_stats['memory_before_mb'] - cleanup_stats['memory_after_mb']
            
            self.logger.info(f"Memory cleanup completed: {cleanup_stats}")
            return cleanup_stats
    
    def _check_memory_usage(self) -> None:
        """Check memory usage and trigger cleanup if needed."""
        if not self.monitoring_enabled:
            return
        
        current_time = time.time()
        if (current_time - self.last_memory_check) < self.check_interval:
            return
        
        self.last_memory_check = current_time
        
        memory_usage = self.get_memory_usage()
        current_mb = memory_usage['rss_mb']
        
        if current_mb > (self.memory_limit_mb * self.warning_threshold):
            self.logger.warning(f"High memory usage: {current_mb:.1f}MB (limit: {self.memory_limit_mb}MB)")
            
            if current_mb > (self.memory_limit_mb * self.cleanup_threshold):
                self.force_cleanup()


class AsyncProcessor:
    """
    Asynchronous processing manager for heavy operations.
    
    Enables non-blocking execution of expensive merge/split operations
    with priority queuing and progress tracking.
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 100):
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.workers: List[asyncio.Task] = []
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        self.running = False
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_processing_time_ms': 0.0,
            'queue_full_count': 0
        }
    
    async def start(self) -> None:
        """Start the async processor."""
        async with self.lock:
            if self.running:
                return
            
            self.running = True
            
            # Start worker tasks
            for i in range(self.max_workers):
                worker = asyncio.create_task(self._worker(f"worker-{i}"))
                self.workers.append(worker)
            
            self.logger.info(f"Started async processor with {self.max_workers} workers")
    
    async def stop(self) -> None:
        """Stop the async processor."""
        async with self.lock:
            if not self.running:
                return
            
            self.running = False
            
            # Cancel all workers
            for worker in self.workers:
                worker.cancel()
            
            # Wait for workers to finish
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
            
            # Cancel active tasks
            for task in self.active_tasks.values():
                task.cancel()
            
            self.active_tasks.clear()
            
            self.logger.info("Stopped async processor")
    
    async def submit_task(self, 
                         task_id: str,
                         func: Callable,
                         args: Tuple = (),
                         kwargs: Dict[str, Any] = None,
                         priority: ProcessingPriority = ProcessingPriority.NORMAL,
                         callback: Optional[Callable] = None) -> bool:
        """
        Submit a task for async processing.
        
        Args:
            task_id: Unique task identifier
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Task priority
            callback: Optional completion callback
            
        Returns:
            True if task was queued successfully
        """
        if not self.running:
            return False
        
        task_data = {
            'task_id': task_id,
            'func': func,
            'args': args or (),
            'kwargs': kwargs or {},
            'priority': priority,
            'callback': callback,
            'submitted_at': time.time()
        }
        
        try:
            await self.task_queue.put(task_data)
            self.metrics['tasks_submitted'] += 1
            self.logger.debug(f"Submitted task {task_id} with priority {priority.name}")
            return True
        except asyncio.QueueFull:
            self.metrics['queue_full_count'] += 1
            self.logger.warning(f"Task queue full, could not submit task {task_id}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active task.
        
        Args:
            task_id: Task to cancel
            
        Returns:
            True if task was cancelled
        """
        async with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.cancel()
                del self.active_tasks[task_id]
                return True
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get processing queue status."""
        return {
            'running': self.running,
            'queue_size': self.task_queue.qsize(),
            'max_queue_size': self.queue_size,
            'active_tasks': len(self.active_tasks),
            'worker_count': len(self.workers),
            **self.metrics
        }
    
    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine for processing tasks."""
        self.logger.debug(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Get task from queue
                task_data = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                task_id = task_data['task_id']
                start_time = time.time()
                
                try:
                    # Create and track task
                    task = asyncio.create_task(
                        self._execute_task(task_data)
                    )
                    
                    async with self.lock:
                        self.active_tasks[task_id] = task
                    
                    # Execute task
                    result = await task
                    
                    # Update metrics
                    processing_time = (time.time() - start_time) * 1000
                    self._update_processing_time(processing_time)
                    self.metrics['tasks_completed'] += 1
                    
                    # Execute callback if provided
                    if task_data['callback']:
                        try:
                            await task_data['callback'](result)
                        except Exception as e:
                            self.logger.warning(f"Task callback failed for {task_id}: {e}")
                    
                    self.logger.debug(f"Completed task {task_id} in {processing_time:.2f}ms")
                    
                except asyncio.CancelledError:
                    self.logger.debug(f"Task {task_id} was cancelled")
                    raise
                except Exception as e:
                    self.metrics['tasks_failed'] += 1
                    self.logger.error(f"Task {task_id} failed: {e}")
                finally:
                    # Remove from active tasks
                    async with self.lock:
                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]
                    
                    # Mark task as done
                    self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Check running flag again
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
        
        self.logger.debug(f"Worker {worker_name} stopped")
    
    async def _execute_task(self, task_data: Dict[str, Any]) -> Any:
        """Execute a single task."""
        func = task_data['func']
        args = task_data['args']
        kwargs = task_data['kwargs']
        
        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    def _update_processing_time(self, time_ms: float) -> None:
        """Update average processing time metric."""
        current_avg = self.metrics['average_processing_time_ms']
        completed = self.metrics['tasks_completed']
        
        if completed > 1:
            self.metrics['average_processing_time_ms'] = ((current_avg * (completed - 1)) + time_ms) / completed
        else:
            self.metrics['average_processing_time_ms'] = time_ms


# Decorator for caching expensive function results
def cache_result(cache: CoordinateCache, ttl: Optional[float] = None):
    """
    Decorator to cache function results.
    
    Args:
        cache: Cache instance to use
        ttl: Time to live for cached results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.put(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global instances for easy access
_coordinate_cache: Optional[CoordinateCache] = None
_memory_optimizer: Optional[MemoryOptimizer] = None
_async_processor: Optional[AsyncProcessor] = None


def get_coordinate_cache() -> CoordinateCache:
    """Get global coordinate cache instance."""
    global _coordinate_cache
    if _coordinate_cache is None:
        _coordinate_cache = CoordinateCache()
    return _coordinate_cache


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance."""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer


def get_async_processor() -> AsyncProcessor:
    """Get global async processor instance."""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncProcessor()
    return _async_processor