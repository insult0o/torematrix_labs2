"""Intelligent Search Result Caching

LRU cache for search results with intelligent invalidation, TTL support,
and performance monitoring for blazingly fast search operations.
"""

import hashlib
import json
import logging
import time
import weakref
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from torematrix.core.models.element import Element
from torematrix.ui.components.search.filters import Filter


logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_cache_time_ms: float = 0.0
    average_cache_time_ms: float = 0.0
    memory_usage_bytes: int = 0
    hit_ratio: float = 0.0


@dataclass
class CachedResults:
    """Cached search results with metadata"""
    cache_key: str
    results: List[Element]
    timestamp: float
    ttl: int
    query: str
    filters: List[Filter]
    result_count: int
    creation_time: datetime
    last_accessed: datetime
    access_count: int = 0
    memory_size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cached results are expired"""
        return time.time() - self.timestamp > self.ttl
    
    def update_access(self) -> None:
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass 
class CacheEntry:
    """Internal cache entry with metadata"""
    key: str
    value: CachedResults
    timestamp: float
    size_bytes: int
    access_count: int = 0
    
    def update_access(self) -> None:
        """Update access tracking"""
        self.access_count += 1
        self.value.update_access()


class LRUCache:
    """Memory-efficient LRU cache with TTL support"""
    
    def __init__(self, max_size: int, ttl: int = 300):
        """Initialize LRU cache
        
        Args:
            max_size: Maximum number of entries
            ttl: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.total_memory = 0
        self.eviction_count = 0
        
    def get(self, key: str) -> Optional[CachedResults]:
        """Get item, moving to end if found and valid
        
        Args:
            key: Cache key
            
        Returns:
            Cached results if found and valid, None otherwise
        """
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        
        # Check TTL
        if time.time() - entry.timestamp > self.ttl:
            self._evict(key)
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.update_access()
        
        return entry.value
    
    def put(self, key: str, value: CachedResults) -> None:
        """Put item, evicting oldest if necessary
        
        Args:
            key: Cache key
            value: Cached results to store
        """
        # Calculate memory size
        estimated_size = self._estimate_size(value)
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            size_bytes=estimated_size
        )
        
        # Evict if at capacity
        while len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self._evict(oldest_key)
        
        # Add new entry
        self.cache[key] = entry
        self.timestamps[key] = entry.timestamp
        self.total_memory += estimated_size
        
    def _evict(self, key: str) -> None:
        """Evict item from cache
        
        Args:
            key: Cache key to evict
        """
        if key in self.cache:
            entry = self.cache[key]
            self.total_memory -= entry.size_bytes
            del self.cache[key]
            del self.timestamps[key]
            self.eviction_count += 1
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
        self.total_memory = 0
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        return self.total_memory
    
    def _estimate_size(self, cached_results: CachedResults) -> int:
        """Estimate memory size of cached results
        
        Args:
            cached_results: Results to estimate
            
        Returns:
            Estimated size in bytes
        """
        # Base object size
        base_size = 1000  # Approximate overhead
        
        # Element content size estimation
        element_size = 0
        for element in cached_results.results:
            element_size += len(element.text) * 2  # Unicode chars
            element_size += 500  # Metadata overhead
        
        # Filter size estimation
        filter_size = len(cached_results.filters) * 200
        
        # Query size
        query_size = len(cached_results.query) * 2
        
        total_size = base_size + element_size + filter_size + query_size
        cached_results.memory_size_bytes = total_size
        
        return total_size


class CacheInvalidationManager:
    """Manages cache invalidation based on data changes"""
    
    def __init__(self, cache_manager: 'CacheManager'):
        """Initialize invalidation manager
        
        Args:
            cache_manager: Cache manager to invalidate
        """
        self.cache_manager = cache_manager
        self.element_cache_map: Dict[str, Set[str]] = {}  # element_id -> cache_keys
        self.dependency_graph: Dict[str, Set[str]] = {}  # cache_key -> dependent_keys
        
    def register_element_dependency(self, cache_key: str, element_ids: List[str]) -> None:
        """Register element dependencies for a cache key
        
        Args:
            cache_key: Cache key that depends on elements
            element_ids: List of element IDs this cache depends on
        """
        for element_id in element_ids:
            if element_id not in self.element_cache_map:
                self.element_cache_map[element_id] = set()
            self.element_cache_map[element_id].add(cache_key)
    
    def invalidate_element_caches(self, element_id: str) -> Set[str]:
        """Invalidate all caches that depend on an element
        
        Args:
            element_id: ID of changed element
            
        Returns:
            Set of invalidated cache keys
        """
        invalidated_keys = set()
        
        if element_id in self.element_cache_map:
            cache_keys = self.element_cache_map[element_id].copy()
            
            for cache_key in cache_keys:
                if self.cache_manager.invalidate_cache_key(cache_key):
                    invalidated_keys.add(cache_key)
                    
                    # Invalidate dependent caches
                    if cache_key in self.dependency_graph:
                        for dependent_key in self.dependency_graph[cache_key]:
                            if self.cache_manager.invalidate_cache_key(dependent_key):
                                invalidated_keys.add(dependent_key)
            
            # Clean up mappings
            self.element_cache_map[element_id].clear()
        
        return invalidated_keys
    
    def add_cache_dependency(self, cache_key: str, dependent_key: str) -> None:
        """Add dependency between cache keys
        
        Args:
            cache_key: Parent cache key
            dependent_key: Dependent cache key
        """
        if cache_key not in self.dependency_graph:
            self.dependency_graph[cache_key] = set()
        self.dependency_graph[cache_key].add(dependent_key)


class CacheManager:
    """Intelligent cache manager for search results with LRU eviction and TTL"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """Initialize cache manager
        
        Args:
            max_size: Maximum number of cached entries
            ttl: Time to live for cache entries in seconds
        """
        self.cache = LRUCache(max_size, ttl)
        self.stats = CacheStats()
        self.invalidation_manager = CacheInvalidationManager(self)
        
        # Cache configuration
        self.max_memory_mb = 100
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
        
        # Performance monitoring
        self.slow_query_threshold_ms = 100
        self.slow_queries: List[Tuple[str, float]] = []
        
        logger.info(f"CacheManager initialized: max_size={max_size}, ttl={ttl}s")
    
    async def get_cached_results(self, cache_key: str) -> Optional[CachedResults]:
        """Get results from cache if available and valid
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached results if found and valid, None otherwise
        """
        start_time = time.time()
        
        try:
            self.stats.total_requests += 1
            
            # Check if cleanup is needed
            if time.time() - self.last_cleanup > self.cleanup_interval:
                await self._cleanup_expired_entries()
            
            # Get from cache
            cached_results = self.cache.get(cache_key)
            
            if cached_results is not None:
                self.stats.cache_hits += 1
                cache_time = (time.time() - start_time) * 1000
                self.stats.total_cache_time_ms += cache_time
                self.stats.average_cache_time_ms = (
                    self.stats.total_cache_time_ms / self.stats.cache_hits
                )
                
                logger.debug(f"Cache HIT: {cache_key} ({cache_time:.2f}ms)")
                return cached_results
            else:
                self.stats.cache_misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None
        
        finally:
            self._update_hit_ratio()
    
    async def cache_results(self, cache_key: str, results: List[Element], 
                          query: str, filters: List[Filter]) -> None:
        """Cache search results with metadata
        
        Args:
            cache_key: Key to store results under
            results: Search results to cache
            query: Original search query
            filters: Applied filters
        """
        try:
            # Create cached results object
            cached_results = CachedResults(
                cache_key=cache_key,
                results=results,
                timestamp=time.time(),
                ttl=self.cache.ttl,
                query=query,
                filters=filters,
                result_count=len(results),
                creation_time=datetime.now(),
                last_accessed=datetime.now()
            )
            
            # Store in cache
            self.cache.put(cache_key, cached_results)
            
            # Register element dependencies for invalidation
            element_ids = [element.element_id for element in results]
            self.invalidation_manager.register_element_dependency(cache_key, element_ids)
            
            # Update statistics
            self._update_memory_usage()
            
            logger.debug(f"Cached results: {cache_key} ({len(results)} elements)")
            
        except Exception as e:
            logger.error(f"Error caching results for {cache_key}: {e}")
    
    async def invalidate_element_caches(self, element_id: str) -> None:
        """Invalidate caches when element changes
        
        Args:
            element_id: ID of changed element
        """
        try:
            invalidated_keys = self.invalidation_manager.invalidate_element_caches(element_id)
            self.stats.invalidations += len(invalidated_keys)
            
            if invalidated_keys:
                logger.debug(f"Invalidated {len(invalidated_keys)} caches for element {element_id}")
                
        except Exception as e:
            logger.error(f"Error invalidating caches for element {element_id}: {e}")
    
    def invalidate_cache_key(self, cache_key: str) -> bool:
        """Invalidate specific cache key
        
        Args:
            cache_key: Cache key to invalidate
            
        Returns:
            True if key was found and invalidated
        """
        if cache_key in self.cache.cache:
            self.cache._evict(cache_key)
            return True
        return False
    
    def generate_cache_key(self, query: str, filters: List[Filter]) -> str:
        """Generate stable cache key for query + filters
        
        Args:
            query: Search query string
            filters: List of applied filters
            
        Returns:
            Stable cache key string
        """
        # Create deterministic representation
        filter_data = []
        for filter_obj in filters:
            filter_repr = {
                'type': filter_obj.filter_type.value if hasattr(filter_obj, 'filter_type') else 'unknown',
                'field': getattr(filter_obj, 'field_name', ''),
                'operator': getattr(filter_obj, 'operator', ''),
                'value': str(getattr(filter_obj, 'value', ''))
            }
            filter_data.append(filter_repr)
        
        # Sort filters for consistent ordering
        filter_data.sort(key=lambda x: (x['type'], x['field'], x['operator'], x['value']))
        
        # Create cache key data
        cache_data = {
            'query': query.strip().lower(),
            'filters': filter_data
        }
        
        # Generate hash
        cache_json = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_json.encode()).hexdigest()[:16]
        
        return f"search_{cache_hash}"
    
    def get_cache_statistics(self) -> CacheStats:
        """Get comprehensive cache statistics
        
        Returns:
            Current cache statistics
        """
        self._update_memory_usage()
        self._update_hit_ratio()
        return self.stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information
        
        Returns:
            Dictionary with cache details
        """
        return {
            'cache_size': self.cache.size(),
            'max_size': self.cache.max_size,
            'memory_usage_mb': self.cache.memory_usage() / (1024 * 1024),
            'max_memory_mb': self.max_memory_mb,
            'ttl_seconds': self.cache.ttl,
            'eviction_count': self.cache.eviction_count,
            'stats': self.get_cache_statistics(),
            'slow_queries': self.slow_queries[-10:]  # Last 10 slow queries
        }
    
    async def warm_cache(self, popular_queries: List[Tuple[str, List[Filter]]]) -> None:
        """Warm cache with popular queries
        
        Args:
            popular_queries: List of (query, filters) tuples to pre-cache
        """
        logger.info(f"Warming cache with {len(popular_queries)} popular queries")
        
        for query, filters in popular_queries:
            cache_key = self.generate_cache_key(query, filters)
            
            # Only warm if not already cached
            if not await self.get_cached_results(cache_key):
                # This would trigger the actual search to populate cache
                # For now, we just log the intent
                logger.debug(f"Would warm cache for: {query}")
    
    async def clear_cache(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self.invalidation_manager.element_cache_map.clear()
        self.invalidation_manager.dependency_graph.clear()
        
        # Reset statistics
        self.stats = CacheStats()
        
        logger.info("Cache cleared")
    
    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.cache.items():
            if current_time - entry.timestamp > self.cache.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache._evict(key)
            self.stats.evictions += 1
        
        self.last_cleanup = current_time
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _update_memory_usage(self) -> None:
        """Update memory usage statistics"""
        self.stats.memory_usage_bytes = self.cache.memory_usage()
    
    def _update_hit_ratio(self) -> None:
        """Update cache hit ratio"""
        if self.stats.total_requests > 0:
            self.stats.hit_ratio = self.stats.cache_hits / self.stats.total_requests
        else:
            self.stats.hit_ratio = 0.0


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance
    
    Returns:
        Global CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def create_cache_manager(max_size: int = 1000, ttl: int = 300) -> CacheManager:
    """Create new cache manager instance
    
    Args:
        max_size: Maximum cache entries
        ttl: Time to live in seconds
        
    Returns:
        New CacheManager instance
    """
    return CacheManager(max_size=max_size, ttl=ttl)