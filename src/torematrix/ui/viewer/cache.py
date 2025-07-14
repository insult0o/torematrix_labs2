"""
Advanced caching system for coordinate transformations.

This module provides high-performance caching with LRU eviction,
memory management, and performance monitoring for the zoom, pan, and rotation system.
"""

from typing import Dict, Optional, Any, Tuple, List, Generic, TypeVar
from dataclasses import dataclass
import time
import threading
from collections import OrderedDict
import math

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
        
    def eviction(self):
        """Record cache eviction."""
        self.evictions += 1
        
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
        
    def get_uptime(self) -> float:
        """Get cache uptime in seconds."""
        return time.time() - self.start_time
        
    def reset(self):
        """Reset statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.reset_time = time.time()


class TransformationCache:
    """High-performance transformation cache with smart eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory: int = 100 * 1024 * 1024):  # 100MB
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._max_memory = max_memory
        self._current_memory = 0
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        
        # Performance optimization settings
        self._cleanup_threshold = 0.1  # Clean up when 10% full
        self._cleanup_batch_size = 100  # Clean up 100 entries at once
        
    def get(self, key: str) -> Optional[Any]:
        """Get transformation from cache."""
        with self._lock:
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
                
    def set(self, key: str, value: Any, size: Optional[int] = None):
        """Set transformation in cache."""
        with self._lock:
            if size is None:
                size = self._estimate_size(value)
                
            # Check if we need to evict
            while (len(self._cache) >= self._max_size or 
                   self._current_memory + size > self._max_memory):
                self._evict_lru()
                
            # Add new entry
            entry = CacheEntry(value, time.time(), 1, size, time.time())
            self._cache[key] = entry
            self._current_memory += size
            
            # Periodic cleanup
            if len(self._cache) % 100 == 0:
                self._cleanup_old_entries()
                
    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_memory -= entry.size
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
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'evictions': self._stats.evictions,
                'hit_rate': self._stats.get_hit_rate(),
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'memory_usage': self._current_memory,
                'max_memory': self._max_memory,
                'uptime': self._stats.get_uptime()
            }
            
    def optimize(self):
        """Optimize cache by removing old entries."""
        with self._lock:
            self._cleanup_old_entries()
            self._defragment_cache()
            
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._current_memory -= entry.size
            self._stats.eviction()
            
    def _cleanup_old_entries(self):
        """Clean up old, rarely accessed entries."""
        current_time = time.time()
        cutoff_time = current_time - 300  # 5 minutes
        
        keys_to_remove = []
        for key, entry in list(self._cache.items()):
            if entry.last_access < cutoff_time and entry.access_count < 2:
                keys_to_remove.append(key)
                if len(keys_to_remove) >= self._cleanup_batch_size:
                    break
                    
        for key in keys_to_remove:
            self.invalidate(key)
            
    def _defragment_cache(self):
        """Defragment cache to improve performance."""
        # Rebuild cache with most frequently accessed items first
        if len(self._cache) > self._max_size * 0.8:
            sorted_items = sorted(
                self._cache.items(),
                key=lambda item: (item[1].access_count, item[1].last_access),
                reverse=True
            )
            
            # Keep top 80% of items
            keep_count = int(len(sorted_items) * 0.8)
            new_cache = OrderedDict()
            new_memory = 0
            
            for key, entry in sorted_items[:keep_count]:
                new_cache[key] = entry
                new_memory += entry.size
                
            self._cache = new_cache
            self._current_memory = new_memory
            
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        # Rough estimates for common types
        if hasattr(value, 'matrix'):  # Transformation matrix
            return 9 * 8 + 100  # 64-bit floats + overhead
        elif isinstance(value, (int, float)):
            return 8
        elif isinstance(value, str):
            return len(value) * 2
        elif isinstance(value, (list, tuple)):
            return len(value) * 8 + 50
        else:
            return 100  # Default estimate


class CoordinateCache:
    """Specialized cache for coordinate transformations with spatial optimization."""
    
    def __init__(self, max_entries: int = 10000):
        self._cache: Dict[Tuple[float, float, str], Tuple[float, float]] = {}
        self._max_entries = max_entries
        self._access_order: List[Tuple[float, float, str]] = []
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        
        # Spatial optimization
        self._spatial_buckets: Dict[Tuple[int, int], List[Tuple[float, float, str]]] = {}
        self._bucket_size = 100.0  # Coordinate space bucket size
        
    def get_transformed_point(self, x: float, y: float, transform_key: str) -> Optional[Tuple[float, float]]:
        """Get transformed point from cache with spatial optimization."""
        with self._lock:
            key = (x, y, transform_key)
            
            # Direct lookup first
            if key in self._cache:
                self._update_access_order(key)
                self._stats.hit()
                return self._cache[key]
            
            # Try spatial lookup for nearby points
            result = self._spatial_lookup(x, y, transform_key)
            if result:
                self._stats.hit()
                return result
                
            self._stats.miss()
            return None
            
    def set_transformed_point(self, x: float, y: float, transform_key: str, 
                            result_x: float, result_y: float):
        """Set transformed point in cache with spatial indexing."""
        with self._lock:
            key = (x, y, transform_key)
            
            # Evict if necessary
            while len(self._cache) >= self._max_entries:
                self._evict_lru()
                
            self._cache[key] = (result_x, result_y)
            self._update_access_order(key)
            self._update_spatial_index(key)
            
    def _spatial_lookup(self, x: float, y: float, transform_key: str, 
                       tolerance: float = 1.0) -> Optional[Tuple[float, float]]:
        """Look up nearby cached transformations."""
        bucket = self._get_spatial_bucket(x, y)
        
        if bucket in self._spatial_buckets:
            for cached_key in self._spatial_buckets[bucket]:
                if cached_key[2] == transform_key:
                    cached_x, cached_y = cached_key[0], cached_key[1]
                    distance = math.sqrt((x - cached_x)**2 + (y - cached_y)**2)
                    
                    if distance <= tolerance:
                        # Interpolate result for better accuracy
                        cached_result = self._cache.get(cached_key)
                        if cached_result:
                            return self._interpolate_result(
                                x, y, cached_x, cached_y, cached_result
                            )
        
        return None
        
    def _interpolate_result(self, x: float, y: float, cached_x: float, cached_y: float,
                          cached_result: Tuple[float, float]) -> Tuple[float, float]:
        """Interpolate transformation result for nearby point."""
        # Simple linear interpolation for small distances
        dx = x - cached_x
        dy = y - cached_y
        
        # Assume linear transformation for small deltas
        result_x = cached_result[0] + dx
        result_y = cached_result[1] + dy
        
        return (result_x, result_y)
        
    def _get_spatial_bucket(self, x: float, y: float) -> Tuple[int, int]:
        """Get spatial bucket for coordinates."""
        bucket_x = int(x // self._bucket_size)
        bucket_y = int(y // self._bucket_size)
        return (bucket_x, bucket_y)
        
    def _update_spatial_index(self, key: Tuple[float, float, str]):
        """Update spatial index for key."""
        x, y, _ = key
        bucket = self._get_spatial_bucket(x, y)
        
        if bucket not in self._spatial_buckets:
            self._spatial_buckets[bucket] = []
            
        if key not in self._spatial_buckets[bucket]:
            self._spatial_buckets[bucket].append(key)
            
    def _update_access_order(self, key: Tuple[float, float, str]):
        """Update access order for LRU eviction."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            self._cache.pop(lru_key, None)
            
            # Remove from spatial index
            x, y, _ = lru_key
            bucket = self._get_spatial_bucket(x, y)
            if bucket in self._spatial_buckets:
                if lru_key in self._spatial_buckets[bucket]:
                    self._spatial_buckets[bucket].remove(lru_key)
                if not self._spatial_buckets[bucket]:
                    del self._spatial_buckets[bucket]
                    
            self._stats.eviction()
            
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
                    
                # Remove from spatial index
                x, y, _ = key
                bucket = self._get_spatial_bucket(x, y)
                if bucket in self._spatial_buckets:
                    if key in self._spatial_buckets[bucket]:
                        self._spatial_buckets[bucket].remove(key)
                    if not self._spatial_buckets[bucket]:
                        del self._spatial_buckets[bucket]
                        
    def clear(self):
        """Clear coordinate cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._spatial_buckets.clear()
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'memory_usage': len(self._cache) * 40,  # Rough estimate
                'hit_rate': self._stats.get_hit_rate(),
                'spatial_buckets': len(self._spatial_buckets),
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'evictions': self._stats.evictions
            }