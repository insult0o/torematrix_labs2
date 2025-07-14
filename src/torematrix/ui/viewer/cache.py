"""
Advanced caching system for coordinate transformations.

This module provides high-performance caching with LRU eviction,
memory management, and performance monitoring.
"""

from typing import Dict, Optional, Any, Tuple, List, Generic, TypeVar
from dataclasses import dataclass
import time
import threading
from collections import OrderedDict
import weakref
import gc

from .transformations import AffineTransformation

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    timestamp: float
    access_count: int
    size: int
    last_access: float
    
    def __post_init__(self):
        """Initialize access time."""
        if not hasattr(self, 'last_access'):
            self.last_access = self.timestamp


class CacheStatistics:
    """Cache performance statistics."""
    
    def __init__(self):
        """Initialize statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.memory_usage = 0
        self.start_time = time.time()
        self.reset_time = time.time()
        
    def hit(self):
        """Record cache hit."""
        self.hits += 1
        
    def miss(self):
        """Record cache miss."""
        self.misses += 1
        
    def evict(self):
        """Record cache eviction."""
        self.evictions += 1
        
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
        
    def requests_per_second(self) -> float:
        """Calculate requests per second."""
        elapsed = time.time() - self.start_time
        total = self.hits + self.misses
        return total / elapsed if elapsed > 0 else 0.0
        
    def reset(self):
        """Reset statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.reset_time = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'memory_usage': self.memory_usage,
            'hit_rate': self.hit_rate(),
            'requests_per_second': self.requests_per_second(),
            'uptime': time.time() - self.start_time
        }


class TransformationCache:
    """High-performance transformation cache with smart eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory: int = 100 * 1024 * 1024):  # 100MB
        """Initialize transformation cache."""
        self._cache: OrderedDict[str, CacheEntry[AffineTransformation]] = OrderedDict()
        self._max_size = max_size
        self._max_memory = max_memory
        self._current_memory = 0
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        
        # Cache optimization settings
        self._access_threshold = 2  # Minimum accesses before considering for retention
        self._age_threshold = 300.0  # 5 minutes
        self._cleanup_interval = 60.0  # 1 minute
        self._last_cleanup = time.time()
        
        # Weak references for memory management
        self._weak_refs: Dict[str, weakref.ref] = {}
        
    def get(self, key: str) -> Optional[AffineTransformation]:
        """Get transformation from cache."""
        with self._lock:
            self._maybe_cleanup()
            
            if key in self._cache:
                entry = self._cache[key]
                entry.access_count += 1
                entry.last_access = time.time()
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                
                self._stats.hit()
                return entry.value
            else:
                self._stats.miss()
                return None
    
    def set(self, key: str, value: AffineTransformation, size: Optional[int] = None):
        """Set transformation in cache."""
        with self._lock:
            if size is None:
                size = self._estimate_size(value)
            
            # Check if we need to evict before adding
            while (len(self._cache) >= self._max_size or 
                   self._current_memory + size > self._max_memory):
                if not self._evict_lru():
                    break  # No more items to evict
            
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory -= old_entry.size
            
            # Add new entry
            current_time = time.time()
            entry = CacheEntry(value, current_time, 1, size, current_time)
            self._cache[key] = entry
            self._current_memory += size
            
            self._stats.memory_usage = self._current_memory
            
            # Create weak reference for memory management
            self._weak_refs[key] = weakref.ref(value)
    
    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_memory -= entry.size
                self._stats.memory_usage = self._current_memory
                
                # Remove weak reference
                self._weak_refs.pop(key, None)
                
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
            self._stats.memory_usage = 0
            self._weak_refs.clear()
            gc.collect()  # Force garbage collection
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = self._stats.to_dict()
            stats.update({
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'max_memory': self._max_memory,
                'current_memory': self._current_memory,
                'memory_utilization': self._current_memory / self._max_memory,
                'avg_entry_size': self._current_memory / len(self._cache) if self._cache else 0
            })
            return stats
    
    def optimize(self):
        """Optimize cache by removing old or unused entries."""
        with self._lock:
            current_time = time.time()
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                # Remove old entries with low access count
                age = current_time - entry.timestamp
                if (age > self._age_threshold and 
                    entry.access_count < self._access_threshold):
                    keys_to_remove.append(key)
                
                # Remove entries with dead weak references
                weak_ref = self._weak_refs.get(key)
                if weak_ref and weak_ref() is None:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.invalidate(key)
                
            # Force garbage collection after optimization
            gc.collect()
    
    def resize(self, max_size: int, max_memory: int):
        """Resize cache limits."""
        with self._lock:
            self._max_size = max_size
            self._max_memory = max_memory
            
            # Evict if necessary
            while (len(self._cache) > self._max_size or 
                   self._current_memory > self._max_memory):
                if not self._evict_lru():
                    break
    
    def get_memory_usage(self) -> int:
        """Get current memory usage."""
        return self._current_memory
    
    def get_cache_size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self._cache:
            return False
        
        # Find LRU entry
        lru_key = None
        lru_access_time = float('inf')
        
        for key, entry in self._cache.items():
            if entry.last_access < lru_access_time:
                lru_access_time = entry.last_access
                lru_key = key
        
        if lru_key:
            entry = self._cache.pop(lru_key)
            self._current_memory -= entry.size
            self._stats.evict()
            self._weak_refs.pop(lru_key, None)
            return True
        
        return False
    
    def _estimate_size(self, value: AffineTransformation) -> int:
        """Estimate size of transformation in bytes."""
        # Rough estimate: 9 floats (3x3 matrix) + overhead
        matrix_size = 9 * 8  # 64-bit floats
        object_overhead = 200  # Python object overhead
        return matrix_size + object_overhead
    
    def _maybe_cleanup(self):
        """Maybe perform cleanup if interval has passed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = current_time
            # Perform cleanup in background to avoid blocking
            threading.Thread(target=self.optimize, daemon=True).start()


class CoordinateCache:
    """Specialized cache for coordinate transformations."""
    
    def __init__(self, max_entries: int = 50000):
        """Initialize coordinate cache."""
        self._cache: Dict[Tuple[float, float, str], Tuple[float, float]] = {}
        self._max_entries = max_entries
        self._access_order: List[Tuple[float, float, str]] = []
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        
        # Spatial indexing for nearby point queries
        self._spatial_index: Dict[Tuple[int, int], List[Tuple[float, float, str]]] = {}
        self._grid_size = 100.0  # Grid size for spatial indexing
    
    def get_transformed_point(self, x: float, y: float, transform_key: str) -> Optional[Tuple[float, float]]:
        """Get transformed point from cache."""
        with self._lock:
            key = (x, y, transform_key)
            
            if key in self._cache:
                # Update access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                
                self._stats.hit()
                return self._cache[key]
            else:
                self._stats.miss()
                return None
    
    def set_transformed_point(self, x: float, y: float, transform_key: str, 
                            result_x: float, result_y: float):
        """Set transformed point in cache."""
        with self._lock:
            key = (x, y, transform_key)
            
            # Evict if necessary
            while len(self._cache) >= self._max_entries:
                if not self._evict_lru():
                    break
            
            # Add to cache
            self._cache[key] = (result_x, result_y)
            self._access_order.append(key)
            
            # Update spatial index
            self._update_spatial_index(key, True)
    
    def get_nearby_points(self, x: float, y: float, radius: float, 
                         transform_key: str) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Get nearby cached points within radius."""
        with self._lock:
            nearby = []
            
            # Calculate grid bounds
            grid_x = int(x // self._grid_size)
            grid_y = int(y // self._grid_size)
            
            # Check surrounding grid cells
            for gx in range(grid_x - 1, grid_x + 2):
                for gy in range(grid_y - 1, grid_y + 2):
                    grid_key = (gx, gy)
                    if grid_key in self._spatial_index:
                        for cached_key in self._spatial_index[grid_key]:
                            if cached_key[2] == transform_key:  # Same transform
                                # Check distance
                                dx = cached_key[0] - x
                                dy = cached_key[1] - y
                                distance = (dx * dx + dy * dy) ** 0.5
                                
                                if distance <= radius:
                                    result = self._cache.get(cached_key)
                                    if result:
                                        nearby.append(((cached_key[0], cached_key[1]), result))
            
            return nearby
    
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
                self._update_spatial_index(key, False)
    
    def clear(self):
        """Clear coordinate cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._spatial_index.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = self._stats.to_dict()
            stats.update({
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'memory_usage': len(self._cache) * 40,  # Rough estimate
                'spatial_grid_cells': len(self._spatial_index)
            })
            return stats
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self._access_order:
            return False
        
        lru_key = self._access_order.pop(0)
        self._cache.pop(lru_key, None)
        self._update_spatial_index(lru_key, False)
        self._stats.evict()
        return True
    
    def _update_spatial_index(self, key: Tuple[float, float, str], add: bool):
        """Update spatial index for a key."""
        grid_x = int(key[0] // self._grid_size)
        grid_y = int(key[1] // self._grid_size)
        grid_key = (grid_x, grid_y)
        
        if add:
            if grid_key not in self._spatial_index:
                self._spatial_index[grid_key] = []
            if key not in self._spatial_index[grid_key]:
                self._spatial_index[grid_key].append(key)
        else:
            if grid_key in self._spatial_index:
                if key in self._spatial_index[grid_key]:
                    self._spatial_index[grid_key].remove(key)
                if not self._spatial_index[grid_key]:
                    del self._spatial_index[grid_key]


class CacheManager:
    """Manages multiple caches with global policies."""
    
    def __init__(self):
        """Initialize cache manager."""
        self._caches: Dict[str, Any] = {}
        self._global_stats = CacheStatistics()
        self._lock = threading.RLock()
        
        # Global cache policies
        self._global_memory_limit = 500 * 1024 * 1024  # 500MB
        self._cleanup_interval = 120.0  # 2 minutes
        self._last_cleanup = time.time()
        
        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def register_cache(self, name: str, cache: Any):
        """Register a cache with the manager."""
        with self._lock:
            self._caches[name] = cache
    
    def unregister_cache(self, name: str):
        """Unregister a cache from the manager."""
        with self._lock:
            self._caches.pop(name, None)
    
    def get_cache(self, name: str) -> Optional[Any]:
        """Get a registered cache."""
        with self._lock:
            return self._caches.get(name)
    
    def clear_all(self):
        """Clear all registered caches."""
        with self._lock:
            for cache in self._caches.values():
                if hasattr(cache, 'clear'):
                    cache.clear()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global cache statistics."""
        with self._lock:
            total_memory = 0
            total_entries = 0
            
            cache_stats = {}
            for name, cache in self._caches.items():
                if hasattr(cache, 'get_stats'):
                    stats = cache.get_stats()
                    cache_stats[name] = stats
                    total_memory += stats.get('memory_usage', 0)
                    total_entries += stats.get('entries', 0)
            
            return {
                'total_memory': total_memory,
                'total_entries': total_entries,
                'global_memory_limit': self._global_memory_limit,
                'memory_utilization': total_memory / self._global_memory_limit,
                'cache_count': len(self._caches),
                'cache_stats': cache_stats
            }
    
    def optimize_all(self):
        """Optimize all registered caches."""
        with self._lock:
            for cache in self._caches.values():
                if hasattr(cache, 'optimize'):
                    cache.optimize()
    
    def _cleanup_worker(self):
        """Background cleanup worker."""
        while True:
            time.sleep(self._cleanup_interval)
            
            try:
                # Check global memory usage
                stats = self.get_global_stats()
                if stats['memory_utilization'] > 0.8:  # 80% threshold
                    self.optimize_all()
                    
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                # Log error but don't crash the worker
                print(f"Cache cleanup error: {e}")


# Global cache manager instance
cache_manager = CacheManager()