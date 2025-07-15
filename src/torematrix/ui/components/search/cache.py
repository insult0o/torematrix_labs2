"""Search Result Caching System

Intelligent caching system for search results with LRU eviction, TTL support,
and memory-aware cache management. Provides significant performance improvements
for repeated queries and filter operations.
"""

import time
import hashlib
import threading
import weakref
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union, Callable, Type
from datetime import datetime, timedelta
import logging

from torematrix.core.models.element import Element


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    
    @property
    def age_seconds(self) -> float:
        """Get age in seconds"""
        return time.time() - self.created_at
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl_seconds is None:
            return False
        return self.age_seconds > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access information"""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0
    hit_ratio: float = 0.0
    
    def update_hit_ratio(self) -> None:
        """Update hit ratio calculation"""
        total = self.hits + self.misses
        self.hit_ratio = (self.hits / total) if total > 0 else 0.0


class CacheEvictionPolicy:
    """Base class for cache eviction policies"""
    
    def select_eviction_candidates(self, entries: Dict[str, CacheEntry], 
                                 target_count: int) -> List[str]:
        """Select entries for eviction
        
        Args:
            entries: Current cache entries
            target_count: Number of entries to evict
            
        Returns:
            List of keys to evict
        """
        raise NotImplementedError


class LRUEvictionPolicy(CacheEvictionPolicy):
    """Least Recently Used eviction policy"""
    
    def select_eviction_candidates(self, entries: Dict[str, CacheEntry], 
                                 target_count: int) -> List[str]:
        """Select LRU entries for eviction"""
        # Sort by access time (oldest first)
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].accessed_at
        )
        
        return [key for key, _ in sorted_entries[:target_count]]


class LFUEvictionPolicy(CacheEvictionPolicy):
    """Least Frequently Used eviction policy"""
    
    def select_eviction_candidates(self, entries: Dict[str, CacheEntry], 
                                 target_count: int) -> List[str]:
        """Select LFU entries for eviction"""
        # Sort by access count (lowest first)
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: (x[1].access_count, x[1].accessed_at)
        )
        
        return [key for key, _ in sorted_entries[:target_count]]


class TTLEvictionPolicy(CacheEvictionPolicy):
    """Time-to-Live based eviction policy"""
    
    def select_eviction_candidates(self, entries: Dict[str, CacheEntry], 
                                 target_count: int) -> List[str]:
        """Select expired entries for eviction"""
        expired_keys = [
            key for key, entry in entries.items()
            if entry.is_expired
        ]
        
        # Return expired entries first, then fall back to LRU
        if len(expired_keys) >= target_count:
            return expired_keys[:target_count]
        
        # Need more entries, use LRU for remaining
        remaining_count = target_count - len(expired_keys)
        non_expired = {k: v for k, v in entries.items() if not v.is_expired}
        
        lru_policy = LRUEvictionPolicy()
        additional_keys = lru_policy.select_eviction_candidates(
            non_expired, remaining_count
        )
        
        return expired_keys + additional_keys


class SearchResultCache:
    """High-performance search result cache with intelligent eviction"""
    
    def __init__(self,
                 max_size_mb: int = 100,
                 max_entries: int = 10000,
                 default_ttl_seconds: Optional[float] = 300,  # 5 minutes
                 eviction_policy: Optional[CacheEvictionPolicy] = None):
        """Initialize cache
        
        Args:
            max_size_mb: Maximum cache size in MB
            max_entries: Maximum number of entries
            default_ttl_seconds: Default TTL in seconds (None = no expiration)
            eviction_policy: Eviction policy to use
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()
        
        self._entries: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
        
        # Tag index for efficient invalidation
        self._tag_index: Dict[str, Set[str]] = {}
        
        # Callbacks for cache events
        self._hit_callbacks: List[Callable[[str, Any], None]] = []
        self._miss_callbacks: List[Callable[[str], None]] = []
        self._eviction_callbacks: List[Callable[[str, CacheEntry], None]] = []
        
        logger.info(f"SearchResultCache initialized: max_size={max_size_mb}MB, "
                   f"max_entries={max_entries}, ttl={default_ttl_seconds}s")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        start_time = time.time()
        
        with self._lock:
            entry = self._entries.get(key)
            
            if entry is None:
                self._stats.misses += 1
                self._stats.update_hit_ratio()
                self._call_miss_callbacks(key)
                return None
            
            # Check expiration
            if entry.is_expired:
                self._remove_entry(key, entry)
                self._stats.misses += 1
                self._stats.update_hit_ratio()
                self._call_miss_callbacks(key)
                return None
            
            # Update access info
            entry.touch()
            
            # Update stats
            self._stats.hits += 1
            access_time_ms = (time.time() - start_time) * 1000
            self._update_avg_access_time(access_time_ms)
            self._stats.update_hit_ratio()
            
            self._call_hit_callbacks(key, entry.value)
            return entry.value
    
    def put(self, key: str, value: Any, 
            ttl_seconds: Optional[float] = None,
            tags: Optional[Set[str]] = None) -> None:
        """Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if None)
            tags: Tags for categorized invalidation
        """
        with self._lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Use default TTL if not specified
            if ttl_seconds is None:
                ttl_seconds = self.default_ttl_seconds
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds,
                tags=tags or set()
            )
            
            # Remove existing entry if present
            if key in self._entries:
                self._remove_entry(key, self._entries[key])
            
            # Check if we need to evict
            self._ensure_capacity(size_bytes)
            
            # Store entry
            self._entries[key] = entry
            self._stats.size_bytes += size_bytes
            self._stats.entry_count += 1
            
            # Update tag index
            for tag in entry.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(key)
    
    def remove(self, key: str) -> bool:
        """Remove specific key from cache
        
        Args:
            key: Key to remove
            
        Returns:
            True if key was found and removed
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry:
                self._remove_entry(key, entry)
                return True
            return False
    
    def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate all entries with specified tags
        
        Args:
            tags: Tags to invalidate
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = set()
            
            for tag in tags:
                if tag in self._tag_index:
                    keys_to_remove.update(self._tag_index[tag])
            
            # Remove entries
            for key in keys_to_remove:
                if key in self._entries:
                    self._remove_entry(key, self._entries[key])
            
            logger.info(f"Invalidated {len(keys_to_remove)} entries by tags: {tags}")
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._entries.clear()
            self._tag_index.clear()
            self._stats = CacheStats()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries
        
        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._entries.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                self._remove_entry(key, self._entries[key])
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=self._stats.entry_count,
                avg_access_time_ms=self._stats.avg_access_time_ms,
                hit_ratio=self._stats.hit_ratio
            )
    
    def create_key(self, *components) -> str:
        """Create cache key from components
        
        Args:
            components: Key components to hash
            
        Returns:
            SHA-256 hash of components
        """
        key_data = "|".join(str(c) for c in components)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def add_hit_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Add callback for cache hits"""
        self._hit_callbacks.append(callback)
    
    def add_miss_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for cache misses"""
        self._miss_callbacks.append(callback)
    
    def add_eviction_callback(self, callback: Callable[[str, CacheEntry], None]) -> None:
        """Add callback for cache evictions"""
        self._eviction_callbacks.append(callback)
    
    def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry"""
        # Check size limit
        while (self._stats.size_bytes + new_entry_size > self.max_size_bytes and 
               self._entries):
            self._evict_entries(1)
        
        # Check entry count limit
        while len(self._entries) >= self.max_entries and self._entries:
            self._evict_entries(1)
    
    def _evict_entries(self, count: int) -> None:
        """Evict specified number of entries"""
        if not self._entries:
            return
        
        keys_to_evict = self.eviction_policy.select_eviction_candidates(
            self._entries, count
        )
        
        for key in keys_to_evict:
            if key in self._entries:
                entry = self._entries[key]
                self._remove_entry(key, entry)
                self._stats.evictions += 1
                self._call_eviction_callbacks(key, entry)
    
    def _remove_entry(self, key: str, entry: CacheEntry) -> None:
        """Remove entry and update indices"""
        # Remove from main storage
        if key in self._entries:
            del self._entries[key]
        
        # Update stats
        self._stats.size_bytes -= entry.size_bytes
        self._stats.entry_count -= 1
        
        # Update tag index
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(key)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate size of cached value in bytes"""
        try:
            if isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(
                    self._calculate_size(k) + self._calculate_size(v)
                    for k, v in value.items()
                )
            elif isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, Element):
                # Estimate Element size
                return (
                    len(value.element_id.encode('utf-8')) +
                    len(value.text.encode('utf-8')) +
                    200  # Approximate size of other fields
                )
            else:
                # Fallback estimation
                return len(str(value).encode('utf-8'))
        except:
            return 1024  # Default 1KB estimate
    
    def _update_avg_access_time(self, access_time_ms: float) -> None:
        """Update average access time with exponential moving average"""
        alpha = 0.1  # Smoothing factor
        if self._stats.avg_access_time_ms == 0:
            self._stats.avg_access_time_ms = access_time_ms
        else:
            self._stats.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * self._stats.avg_access_time_ms
            )
    
    def _call_hit_callbacks(self, key: str, value: Any) -> None:
        """Call hit callbacks"""
        for callback in self._hit_callbacks:
            try:
                callback(key, value)
            except Exception as e:
                logger.warning(f"Hit callback error: {e}")
    
    def _call_miss_callbacks(self, key: str) -> None:
        """Call miss callbacks"""
        for callback in self._miss_callbacks:
            try:
                callback(key)
            except Exception as e:
                logger.warning(f"Miss callback error: {e}")
    
    def _call_eviction_callbacks(self, key: str, entry: CacheEntry) -> None:
        """Call eviction callbacks"""
        for callback in self._eviction_callbacks:
            try:
                callback(key, entry)
            except Exception as e:
                logger.warning(f"Eviction callback error: {e}")


class CacheManager:
    """Global cache manager for search operations"""
    
    def __init__(self):
        """Initialize cache manager"""
        # Different caches for different types of data
        self.search_results = SearchResultCache(
            max_size_mb=50,
            max_entries=5000,
            default_ttl_seconds=300  # 5 minutes
        )
        
        self.filter_results = SearchResultCache(
            max_size_mb=30,
            max_entries=3000,
            default_ttl_seconds=600  # 10 minutes
        )
        
        self.suggestions = SearchResultCache(
            max_size_mb=10,
            max_entries=1000,
            default_ttl_seconds=1800  # 30 minutes
        )
        
        self.metadata = SearchResultCache(
            max_size_mb=10,
            max_entries=2000,
            default_ttl_seconds=3600  # 1 hour
        )
        
        logger.info("CacheManager initialized with specialized caches")
    
    def invalidate_search_results(self, query_pattern: Optional[str] = None) -> None:
        """Invalidate search result caches"""
        if query_pattern:
            # Invalidate specific pattern
            tags = {f"query:{query_pattern}"}
            count = self.search_results.invalidate_by_tags(tags)
            logger.info(f"Invalidated {count} search results for pattern: {query_pattern}")
        else:
            # Clear all search results
            self.search_results.clear()
            logger.info("Cleared all search result caches")
    
    def invalidate_filter_results(self, filter_type: Optional[str] = None) -> None:
        """Invalidate filter result caches"""
        if filter_type:
            tags = {f"filter:{filter_type}"}
            count = self.filter_results.invalidate_by_tags(tags)
            logger.info(f"Invalidated {count} filter results for type: {filter_type}")
        else:
            self.filter_results.clear()
            logger.info("Cleared all filter result caches")
    
    def cleanup_all(self) -> Dict[str, int]:
        """Cleanup expired entries from all caches"""
        results = {
            'search_results': self.search_results.cleanup_expired(),
            'filter_results': self.filter_results.cleanup_expired(),
            'suggestions': self.suggestions.cleanup_expired(),
            'metadata': self.metadata.cleanup_expired()
        }
        
        total = sum(results.values())
        if total > 0:
            logger.info(f"Cleaned up {total} expired cache entries")
        
        return results
    
    def get_global_stats(self) -> Dict[str, CacheStats]:
        """Get statistics from all caches"""
        return {
            'search_results': self.search_results.get_stats(),
            'filter_results': self.filter_results.get_stats(),
            'suggestions': self.suggestions.get_stats(),
            'metadata': self.metadata.get_stats()
        }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def clear_all_caches() -> None:
    """Clear all caches globally"""
    manager = get_cache_manager()
    manager.search_results.clear()
    manager.filter_results.clear()
    manager.suggestions.clear()
    manager.metadata.clear()
    logger.info("Cleared all global caches")