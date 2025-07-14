"""
Advanced memoization strategies for high-performance selectors.
"""

import time
import weakref
from typing import Any, Dict, Optional, Set, Callable, TypeVar
from dataclasses import dataclass
from collections import OrderedDict
from threading import RLock

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata for advanced eviction strategies."""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_estimate: int = 0
    
    def update_access(self):
        """Update access metadata."""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache:
    """
    Thread-safe LRU cache with size limits and TTL support.
    """
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[Any, CacheEntry] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: Any) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if self.ttl and (time.time() - entry.created_at) > self.ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access and move to end (most recent)
            entry.update_access()
            self._cache.move_to_end(key)
            self._hits += 1
            
            return entry.value
    
    def put(self, key: Any, value: Any, size_estimate: int = 0):
        """Put value in cache."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_estimate=size_estimate
            )
            
            self._cache[key] = entry
            
            # Evict old entries if over limit
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Remove oldest
    
    def invalidate(self, key: Any = None):
        """Invalidate cache entry or entire cache."""
        with self._lock:
            if key is None:
                self._cache.clear()
            elif key in self._cache:
                del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'utilization': len(self._cache) / self.max_size * 100
            }


class SmartCache:
    """
    Intelligent cache with multiple eviction strategies and memory pressure handling.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        strategy: str = 'lru'
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.strategy = strategy
        
        self._cache: Dict[Any, CacheEntry] = {}
        self._access_order: OrderedDict[Any, None] = OrderedDict()
        self._lock = RLock()
        
        self._total_memory = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: Any) -> Optional[Any]:
        """Get value with smart caching strategy."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            entry.update_access()
            
            # Update access order for LRU
            if self.strategy == 'lru':
                self._access_order.move_to_end(key)
            
            self._hits += 1
            return entry.value
    
    def put(self, key: Any, value: Any):
        """Put value with intelligent eviction."""
        with self._lock:
            # Estimate size
            size_estimate = self._estimate_size(value)
            
            # Remove existing if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._total_memory -= old_entry.size_estimate
                del self._cache[key]
                self._access_order.pop(key, None)
            
            # Check if we need to evict
            while (len(self._cache) >= self.max_size or 
                   self._total_memory + size_estimate > self.max_memory_bytes):
                if not self._evict_one():
                    break  # No more entries to evict
            
            # Add new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_estimate=size_estimate
            )
            
            self._cache[key] = entry
            self._access_order[key] = None
            self._total_memory += size_estimate
    
    def _evict_one(self) -> bool:
        """Evict one entry based on strategy."""
        if not self._cache:
            return False
        
        if self.strategy == 'lru':
            # Evict least recently used
            key = next(iter(self._access_order))
        elif self.strategy == 'lfu':
            # Evict least frequently used
            key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].access_count)
        else:
            # Default to oldest
            key = min(self._cache.keys(),
                     key=lambda k: self._cache[k].created_at)
        
        entry = self._cache[key]
        self._total_memory -= entry.size_estimate
        del self._cache[key]
        self._access_order.pop(key, None)
        self._evictions += 1
        
        return True
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            # Fallback estimate
            if isinstance(value, (list, tuple)):
                return len(value) * 8
            elif isinstance(value, dict):
                return len(value) * 16
            elif isinstance(value, str):
                return len(value)
            else:
                return 64  # Default estimate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_mb': self._total_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': hit_rate,
                'strategy': self.strategy
            }
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._total_memory = 0


class WeakrefCache:
    """
    Cache using weak references to prevent memory leaks with object references.
    """
    
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._cache: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._strong_refs: OrderedDict = OrderedDict()  # Keep some strong refs
        self._lock = RLock()
        
    def get(self, key: Any) -> Optional[Any]:
        """Get value from weak reference cache."""
        with self._lock:
            try:
                value = self._cache[key]
                # Move to end of strong refs if present
                if key in self._strong_refs:
                    self._strong_refs.move_to_end(key)
                return value
            except KeyError:
                return None
    
    def put(self, key: Any, value: Any, keep_strong: bool = False):
        """Put value in weak reference cache."""
        with self._lock:
            try:
                self._cache[key] = value
                
                if keep_strong:
                    self._strong_refs[key] = value
                    # Limit strong references
                    while len(self._strong_refs) > self.max_size // 4:
                        self._strong_refs.popitem(last=False)
                        
            except TypeError:
                # Value not weakly referenceable, skip
                pass
    
    def clear(self):
        """Clear cache."""
        with self._lock:
            self._cache.clear()
            self._strong_refs.clear()


class CacheManager:
    """
    Manager for multiple cache instances with different strategies.
    """
    
    def __init__(self):
        self._caches: Dict[str, Any] = {}
        self._default_cache = SmartCache(max_size=1000, strategy='lru')
    
    def get_cache(
        self,
        name: str,
        cache_type: str = 'smart',
        **kwargs
    ) -> Any:
        """Get or create a named cache."""
        if name not in self._caches:
            if cache_type == 'lru':
                self._caches[name] = LRUCache(**kwargs)
            elif cache_type == 'smart':
                self._caches[name] = SmartCache(**kwargs)
            elif cache_type == 'weakref':
                self._caches[name] = WeakrefCache(**kwargs)
            else:
                raise ValueError(f"Unknown cache type: {cache_type}")
        
        return self._caches[name]
    
    def get_default_cache(self) -> SmartCache:
        """Get the default cache instance."""
        return self._default_cache
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        stats = {'default': self._default_cache.get_stats()}
        
        for name, cache in self._caches.items():
            if hasattr(cache, 'get_stats'):
                stats[name] = cache.get_stats()
        
        return stats
    
    def clear_all(self):
        """Clear all caches."""
        self._default_cache.clear()
        for cache in self._caches.values():
            if hasattr(cache, 'clear'):
                cache.clear()


# Global cache manager instance
cache_manager = CacheManager()