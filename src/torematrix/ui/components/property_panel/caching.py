"""Property Caching System

Intelligent caching system for property values, validation results, and display
data to achieve <50ms response times and >80% cache hit ratios. Optimized for
large property sets with memory-efficient storage and automatic invalidation.
"""

import time
import weakref
from typing import Dict, Any, Optional, Tuple, Set, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
import hashlib
import pickle
import gc

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .models import PropertyValue, PropertyMetadata
from .events import PropertyNotificationCenter, PropertyEventType, PropertyEvent


class CacheEntryType(Enum):
    """Types of cache entries"""
    PROPERTY_VALUE = "property_value"
    VALIDATION_RESULT = "validation_result"
    DISPLAY_DATA = "display_data"
    COMPUTED_VALUE = "computed_value"
    METADATA = "metadata"


@dataclass
class CacheKey:
    """Immutable cache key with type safety"""
    entry_type: CacheEntryType
    element_id: str
    property_name: str
    context_hash: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation for cache key"""
        base = f"{self.entry_type.value}:{self.element_id}:{self.property_name}"
        if self.context_hash:
            base += f":{self.context_hash}"
        return base
    
    def __hash__(self) -> int:
        """Hash for use as dictionary key"""
        return hash(str(self))
    
    @classmethod
    def create_context_hash(cls, context: Dict[str, Any]) -> str:
        """Create hash from context dictionary"""
        if not context:
            return ""
        
        # Sort context for consistent hashing
        sorted_items = sorted(context.items())
        context_str = str(sorted_items)
        return hashlib.md5(context_str.encode()).hexdigest()[:8]


@dataclass
class CacheEntry:
    """Cache entry with metadata and expiration"""
    key: CacheKey
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    dependencies: Set[str] = field(default_factory=set)
    size_bytes: int = 0
    
    def __post_init__(self):
        """Calculate entry size after initialization"""
        self.size_bytes = self._calculate_size()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def access(self) -> Any:
        """Access cache entry and update metrics"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        return self.value
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value"""
        try:
            return len(pickle.dumps(self.value))
        except:
            # Fallback for non-picklable objects
            return len(str(self.value).encode('utf-8'))
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Size-based


class CacheStats:
    """Cache statistics and performance metrics"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all statistics"""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.size_limit_reached = 0
        self.total_entries = 0
        self.total_size_bytes = 0
        self.start_time = datetime.now()
    
    def record_hit(self):
        """Record cache hit"""
        self.hits += 1
    
    def record_miss(self):
        """Record cache miss"""
        self.misses += 1
    
    def record_eviction(self):
        """Record cache eviction"""
        self.evictions += 1
    
    def record_invalidation(self):
        """Record cache invalidation"""
        self.invalidations += 1
    
    def get_hit_ratio(self) -> float:
        """Get cache hit ratio as percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def get_runtime_seconds(self) -> float:
        """Get total runtime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        runtime = self.get_runtime_seconds()
        return {
            'hit_ratio': self.get_hit_ratio(),
            'total_requests': self.hits + self.misses,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'invalidations': self.invalidations,
            'total_entries': self.total_entries,
            'total_size_mb': self.total_size_bytes / (1024 * 1024),
            'runtime_seconds': runtime,
            'requests_per_second': (self.hits + self.misses) / runtime if runtime > 0 else 0
        }


class PropertyCache(QObject):
    """High-performance property cache with intelligent invalidation"""
    
    # Cache event signals
    cache_hit = pyqtSignal(str)  # cache_key
    cache_miss = pyqtSignal(str)  # cache_key
    cache_evicted = pyqtSignal(str, str)  # cache_key, reason
    cache_invalidated = pyqtSignal(str)  # cache_key
    stats_updated = pyqtSignal(dict)  # statistics
    
    def __init__(self, 
                 max_entries: int = 10000,
                 max_size_mb: int = 50,
                 default_ttl_seconds: Optional[int] = 300,
                 eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
                 notification_center: Optional[PropertyNotificationCenter] = None):
        super().__init__()
        
        # Configuration
        self.max_entries = max_entries
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.eviction_policy = eviction_policy
        
        # Cache storage
        self._cache: OrderedDict[CacheKey, CacheEntry] = OrderedDict()
        self._dependencies: Dict[str, Set[CacheKey]] = defaultdict(set)
        self._lock = RLock()
        
        # Statistics
        self.stats = CacheStats()
        
        # Event integration
        self.notification_center = notification_center
        if notification_center:
            self._setup_event_listeners()
        
        # Cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_expired)
        self._cleanup_timer.start(30000)  # Clean up every 30 seconds
        
        # Statistics timer
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._emit_stats)
        self._stats_timer.start(5000)  # Emit stats every 5 seconds
    
    def get(self, key: CacheKey, default: Any = None) -> Any:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self.stats.record_miss()
                self.cache_miss.emit(str(key))
                return default
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                self.stats.record_miss()
                self.cache_miss.emit(str(key))
                return default
            
            # Move to end for LRU
            if self.eviction_policy == EvictionPolicy.LRU:
                self._cache.move_to_end(key)
            
            # Record hit and return value
            value = entry.access()
            self.stats.record_hit()
            self.cache_hit.emit(str(key))
            return value
    
    def put(self, key: CacheKey, value: Any, 
            ttl_seconds: Optional[int] = None,
            dependencies: Optional[Set[str]] = None) -> None:
        """Put value in cache"""
        with self._lock:
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                dependencies=dependencies or set()
            )
            
            # Check size limits before adding
            if self._would_exceed_limits(entry):
                self._evict_to_make_space(entry.size_bytes)
            
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Add to cache
            self._cache[key] = entry
            
            # Update dependencies
            for dep in entry.dependencies:
                self._dependencies[dep].add(key)
            
            # Update statistics
            self.stats.total_entries = len(self._cache)
            self.stats.total_size_bytes = sum(e.size_bytes for e in self._cache.values())
    
    def invalidate(self, dependency: str) -> int:
        """Invalidate all cache entries with dependency"""
        with self._lock:
            if dependency not in self._dependencies:
                return 0
            
            # Get all keys with this dependency
            keys_to_remove = list(self._dependencies[dependency])
            
            # Remove entries
            for key in keys_to_remove:
                if key in self._cache:
                    self._remove_entry(key)
                    self.cache_invalidated.emit(str(key))
                    self.stats.record_invalidation()
            
            # Clean up dependency mapping
            del self._dependencies[dependency]
            
            return len(keys_to_remove)
    
    def invalidate_element(self, element_id: str) -> int:
        """Invalidate all cache entries for an element"""
        return self.invalidate(f"element:{element_id}")
    
    def invalidate_property(self, element_id: str, property_name: str) -> int:
        """Invalidate cache entries for a specific property"""
        return self.invalidate(f"property:{element_id}:{property_name}")
    
    def clear(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()
            self._dependencies.clear()
            self.stats.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current cache statistics"""
        with self._lock:
            return self.stats.get_summary()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self._lock:
            entries_by_type = defaultdict(int)
            size_by_type = defaultdict(int)
            
            for entry in self._cache.values():
                entry_type = entry.key.entry_type.value
                entries_by_type[entry_type] += 1
                size_by_type[entry_type] += entry.size_bytes
            
            return {
                'total_entries': len(self._cache),
                'total_size_mb': sum(e.size_bytes for e in self._cache.values()) / (1024 * 1024),
                'entries_by_type': dict(entries_by_type),
                'size_by_type_mb': {k: v / (1024 * 1024) for k, v in size_by_type.items()},
                'oldest_entry_age': self._get_oldest_entry_age(),
                'dependencies_count': len(self._dependencies)
            }
    
    def _setup_event_listeners(self):
        """Setup property event listeners for cache invalidation"""
        if not self.notification_center:
            return
        
        # Listen for property changes to invalidate cache
        self.notification_center.register_listener(
            PropertyEventType.VALUE_CHANGED,
            self._on_property_changed
        )
        
        # Listen for validation events
        self.notification_center.register_listener(
            PropertyEventType.VALIDATION_FAILED,
            self._on_validation_event
        )
    
    def _on_property_changed(self, event: PropertyEvent):
        """Handle property change events for cache invalidation"""
        # Invalidate related cache entries
        self.invalidate_property(event.element_id, event.property_name)
        
        # Also invalidate element-level caches
        self.invalidate_element(event.element_id)
    
    def _on_validation_event(self, event: PropertyEvent):
        """Handle validation events for cache invalidation"""
        # Invalidate validation-related cache entries
        self.invalidate(f"validation:{event.element_id}:{event.property_name}")
    
    def _would_exceed_limits(self, new_entry: CacheEntry) -> bool:
        """Check if adding entry would exceed cache limits"""
        current_size = sum(e.size_bytes for e in self._cache.values())
        would_exceed_size = (current_size + new_entry.size_bytes) > self.max_size_bytes
        would_exceed_count = len(self._cache) >= self.max_entries
        
        return would_exceed_size or would_exceed_count
    
    def _evict_to_make_space(self, needed_bytes: int) -> None:
        """Evict entries to make space"""
        if self.eviction_policy == EvictionPolicy.LRU:
            self._evict_lru(needed_bytes)
        elif self.eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu(needed_bytes)
        elif self.eviction_policy == EvictionPolicy.SIZE:
            self._evict_largest(needed_bytes)
        else:
            self._evict_expired()
    
    def _evict_lru(self, needed_bytes: int) -> None:
        """Evict least recently used entries"""
        freed_bytes = 0
        keys_to_remove = []
        
        # OrderedDict maintains insertion/access order
        for key in list(self._cache.keys()):
            keys_to_remove.append(key)
            freed_bytes += self._cache[key].size_bytes
            
            if freed_bytes >= needed_bytes:
                break
        
        # Remove selected entries
        for key in keys_to_remove:
            self._remove_entry(key)
            self.cache_evicted.emit(str(key), "LRU")
            self.stats.record_eviction()
    
    def _evict_lfu(self, needed_bytes: int) -> None:
        """Evict least frequently used entries"""
        # Sort by access count (ascending)
        entries_by_frequency = sorted(
            self._cache.items(),
            key=lambda x: x[1].access_count
        )
        
        freed_bytes = 0
        for key, entry in entries_by_frequency:
            self._remove_entry(key)
            self.cache_evicted.emit(str(key), "LFU")
            self.stats.record_eviction()
            freed_bytes += entry.size_bytes
            
            if freed_bytes >= needed_bytes:
                break
    
    def _evict_largest(self, needed_bytes: int) -> None:
        """Evict largest entries first"""
        # Sort by size (descending)
        entries_by_size = sorted(
            self._cache.items(),
            key=lambda x: x[1].size_bytes,
            reverse=True
        )
        
        freed_bytes = 0
        for key, entry in entries_by_size:
            self._remove_entry(key)
            self.cache_evicted.emit(str(key), "SIZE")
            self.stats.record_eviction()
            freed_bytes += entry.size_bytes
            
            if freed_bytes >= needed_bytes:
                break
    
    def _evict_expired(self) -> None:
        """Remove expired entries"""
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in keys_to_remove:
            self._remove_entry(key)
            self.cache_evicted.emit(str(key), "EXPIRED")
            self.stats.record_eviction()
    
    def _remove_entry(self, key: CacheKey) -> None:
        """Remove entry and update dependencies"""
        if key not in self._cache:
            return
        
        entry = self._cache[key]
        
        # Remove from dependencies
        for dep in entry.dependencies:
            if dep in self._dependencies:
                self._dependencies[dep].discard(key)
                if not self._dependencies[dep]:
                    del self._dependencies[dep]
        
        # Remove from cache
        del self._cache[key]
        
        # Update statistics
        self.stats.total_entries = len(self._cache)
        self.stats.total_size_bytes = sum(e.size_bytes for e in self._cache.values())
    
    def _cleanup_expired(self) -> None:
        """Periodic cleanup of expired entries"""
        with self._lock:
            self._evict_expired()
    
    def _emit_stats(self) -> None:
        """Emit cache statistics"""
        stats = self.get_stats()
        self.stats_updated.emit(stats)
    
    def _get_oldest_entry_age(self) -> float:
        """Get age of oldest cache entry in seconds"""
        if not self._cache:
            return 0.0
        
        oldest_entry = min(self._cache.values(), key=lambda e: e.created_at)
        return oldest_entry.get_age_seconds()


class ValidationResultCache:
    """Specialized cache for validation results"""
    
    def __init__(self, property_cache: PropertyCache):
        self.property_cache = property_cache
    
    def get_validation_result(self, element_id: str, property_name: str, 
                            value: Any, validation_context: Dict[str, Any] = None) -> Any:
        """Get cached validation result"""
        context_hash = CacheKey.create_context_hash(validation_context or {})
        value_hash = hashlib.md5(str(value).encode()).hexdigest()[:8]
        
        key = CacheKey(
            entry_type=CacheEntryType.VALIDATION_RESULT,
            element_id=element_id,
            property_name=property_name,
            context_hash=f"{value_hash}:{context_hash}"
        )
        
        return self.property_cache.get(key)
    
    def cache_validation_result(self, element_id: str, property_name: str,
                              value: Any, result: Any, validation_context: Dict[str, Any] = None,
                              ttl_seconds: int = 300) -> None:
        """Cache validation result"""
        context_hash = CacheKey.create_context_hash(validation_context or {})
        value_hash = hashlib.md5(str(value).encode()).hexdigest()[:8]
        
        key = CacheKey(
            entry_type=CacheEntryType.VALIDATION_RESULT,
            element_id=element_id,
            property_name=property_name,
            context_hash=f"{value_hash}:{context_hash}"
        )
        
        dependencies = {
            f"element:{element_id}",
            f"property:{element_id}:{property_name}",
            f"validation:{element_id}:{property_name}"
        }
        
        self.property_cache.put(key, result, ttl_seconds, dependencies)


class DisplayDataCache:
    """Specialized cache for display/rendering data"""
    
    def __init__(self, property_cache: PropertyCache):
        self.property_cache = property_cache
    
    def get_display_data(self, element_id: str, property_name: str,
                        display_context: Dict[str, Any] = None) -> Any:
        """Get cached display data"""
        context_hash = CacheKey.create_context_hash(display_context or {})
        
        key = CacheKey(
            entry_type=CacheEntryType.DISPLAY_DATA,
            element_id=element_id,
            property_name=property_name,
            context_hash=context_hash
        )
        
        return self.property_cache.get(key)
    
    def cache_display_data(self, element_id: str, property_name: str,
                          display_data: Any, display_context: Dict[str, Any] = None,
                          ttl_seconds: int = 600) -> None:
        """Cache display data"""
        context_hash = CacheKey.create_context_hash(display_context or {})
        
        key = CacheKey(
            entry_type=CacheEntryType.DISPLAY_DATA,
            element_id=element_id,
            property_name=property_name,
            context_hash=context_hash
        )
        
        dependencies = {
            f"element:{element_id}",
            f"property:{element_id}:{property_name}",
            f"display:{element_id}:{property_name}"
        }
        
        self.property_cache.put(key, display_data, ttl_seconds, dependencies)


# Global cache instance management
_global_cache: Optional[PropertyCache] = None
_cache_lock = RLock()


def get_property_cache() -> PropertyCache:
    """Get global property cache instance"""
    global _global_cache
    with _cache_lock:
        if _global_cache is None:
            _global_cache = PropertyCache()
        return _global_cache


def set_property_cache(cache: PropertyCache) -> None:
    """Set global property cache instance"""
    global _global_cache
    with _cache_lock:
        _global_cache = cache


def clear_global_cache() -> None:
    """Clear global property cache"""
    global _global_cache
    with _cache_lock:
        if _global_cache:
            _global_cache.clear()


# Convenience functions for common caching patterns

def cache_property_value(element_id: str, property_name: str, value: PropertyValue,
                        ttl_seconds: int = 300) -> None:
    """Cache property value with automatic dependencies"""
    cache = get_property_cache()
    
    key = CacheKey(
        entry_type=CacheEntryType.PROPERTY_VALUE,
        element_id=element_id,
        property_name=property_name
    )
    
    dependencies = {
        f"element:{element_id}",
        f"property:{element_id}:{property_name}"
    }
    
    cache.put(key, value, ttl_seconds, dependencies)


def get_cached_property_value(element_id: str, property_name: str) -> Optional[PropertyValue]:
    """Get cached property value"""
    cache = get_property_cache()
    
    key = CacheKey(
        entry_type=CacheEntryType.PROPERTY_VALUE,
        element_id=element_id,
        property_name=property_name
    )
    
    return cache.get(key)


def invalidate_property_cache(element_id: str, property_name: Optional[str] = None) -> int:
    """Invalidate property cache entries"""
    cache = get_property_cache()
    
    if property_name:
        return cache.invalidate_property(element_id, property_name)
    else:
        return cache.invalidate_element(element_id)