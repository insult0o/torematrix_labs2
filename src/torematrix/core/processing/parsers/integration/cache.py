"""Intelligent caching system for parser results."""

import asyncio
import json
import hashlib
import pickle
import time
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ....models.element import Element as UnifiedElement
from ..base import ParserResult
from ..exceptions import CacheError


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    result: ParserResult
    timestamp: datetime
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600
    size_bytes: int = 0
    parser_used: str = ""
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.utcnow() > (self.timestamp + timedelta(seconds=self.ttl_seconds))
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_access = datetime.utcnow()


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    expired_entries: int = 0
    total_size_bytes: int = 0
    average_entry_size: float = 0.0
    hit_rate: float = 0.0
    memory_usage_mb: float = 0.0


class ParserCache:
    """Intelligent caching system with TTL and LRU eviction."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.cache")
        
        # Configuration
        self.max_size = config.get('max_size', 10000)
        self.default_ttl = config.get('default_ttl', 3600)  # 1 hour
        self.max_memory_mb = config.get('max_memory_mb', 100)  # 100MB
        self.cleanup_interval = config.get('cleanup_interval', 300)  # 5 minutes
        self.enable_persistence = config.get('enable_persistence', False)
        self.persistence_file = config.get('persistence_file', '/tmp/parser_cache.pkl')
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._key_to_element_type: Dict[str, str] = {}
        
        # Statistics
        self._stats = CacheStatistics()
        
        # Cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # Load from persistence if enabled
        if self.enable_persistence:
            self._load_from_persistence()
    
    async def get(self, element: UnifiedElement) -> Optional[ParserResult]:
        """Get cached result for element."""
        self._stats.total_requests += 1
        
        cache_key = self._generate_key(element)
        
        if cache_key not in self._cache:
            self._stats.cache_misses += 1
            return None
        
        entry = self._cache[cache_key]
        
        # Check if expired
        if entry.is_expired():
            await self._remove_entry(cache_key)
            self._stats.cache_misses += 1
            self._stats.expired_entries += 1
            return None
        
        # Update access statistics
        entry.update_access()
        self._update_access_order(cache_key)
        
        # Update hit rate
        self._stats.cache_hits += 1
        self._update_hit_rate()
        
        self.logger.debug(f"Cache hit for key: {cache_key[:16]}...")
        return entry.result
    
    async def set(self, element: UnifiedElement, result: ParserResult, 
                 ttl: Optional[int] = None, parser_used: str = "") -> None:
        """Cache parser result."""
        cache_key = self._generate_key(element)
        
        # Calculate entry size
        entry_size = self._calculate_size(result)
        
        # Check if we need to evict entries
        await self._ensure_capacity(entry_size)
        
        # Create cache entry
        entry = CacheEntry(
            result=result,
            timestamp=datetime.utcnow(),
            ttl_seconds=ttl or self.default_ttl,
            size_bytes=entry_size,
            parser_used=parser_used
        )
        
        # Store in cache
        self._cache[cache_key] = entry
        self._update_access_order(cache_key)
        self._key_to_element_type[cache_key] = getattr(element, 'type', 'unknown')
        
        # Update statistics
        self._stats.total_size_bytes += entry_size
        self._update_average_entry_size()
        
        self.logger.debug(f"Cached result for key: {cache_key[:16]}... (size: {entry_size} bytes)")
    
    async def invalidate(self, element: UnifiedElement) -> bool:
        """Invalidate cached result for element."""
        cache_key = self._generate_key(element)
        if cache_key in self._cache:
            await self._remove_entry(cache_key)
            return True
        return False
    
    async def invalidate_by_type(self, element_type: str) -> int:
        """Invalidate all cached results for a specific element type."""
        keys_to_remove = [
            key for key, cached_type in self._key_to_element_type.items()
            if cached_type == element_type
        ]
        
        for key in keys_to_remove:
            await self._remove_entry(key)
        
        return len(keys_to_remove)
    
    async def clear(self) -> None:
        """Clear all cached entries."""
        keys_to_remove = list(self._cache.keys())
        for key in keys_to_remove:
            await self._remove_entry(key)
        
        self.logger.info("Cache cleared")
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics."""
        stats = self._stats
        stats.memory_usage_mb = self._stats.total_size_bytes / (1024 * 1024)
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        stats = self.get_statistics()
        
        health = {
            "status": "healthy",
            "entries": len(self._cache),
            "hit_rate": stats.hit_rate,
            "memory_usage_mb": stats.memory_usage_mb,
            "expired_entries": await self._count_expired_entries()
        }
        
        # Check for issues
        if stats.memory_usage_mb > self.max_memory_mb * 0.9:  # 90% of limit
            health["status"] = "warning"
            health["issue"] = "High memory usage"
        
        if stats.hit_rate < 0.3:  # < 30% hit rate
            health["status"] = "warning" 
            health["issue"] = "Low hit rate"
        
        return health
    
    async def close(self) -> None:
        """Close cache and cleanup resources."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save to persistence if enabled
        if self.enable_persistence:
            await self._save_to_persistence()
        
        # Clear cache
        await self.clear()
        
        self.logger.info("Cache closed")
    
    def _generate_key(self, element: UnifiedElement) -> str:
        """Generate cache key for element."""
        # Create unique key based on element content and type
        key_data = {
            'type': getattr(element, 'type', 'unknown'),
            'text': getattr(element, 'text', ''),
            'metadata': getattr(element, 'metadata', {})
        }
        
        # Create hash
        content = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_size(self, result: ParserResult) -> int:
        """Calculate size of result in bytes."""
        try:
            # Serialize result to estimate size
            serialized = pickle.dumps(result)
            return len(serialized)
        except Exception:
            # Fallback estimation
            size = 0
            size += len(str(result.data)) * 2  # Rough estimate
            size += len(str(result.metadata)) * 2
            if result.extracted_content:
                size += len(result.extracted_content) * 2
            if result.structured_data:
                size += len(str(result.structured_data)) * 2
            return size
    
    async def _ensure_capacity(self, entry_size: int) -> None:
        """Ensure cache has capacity for new entry."""
        # Check memory limit
        while (self._stats.total_size_bytes + entry_size) > (self.max_memory_mb * 1024 * 1024):
            if not await self._evict_lru():
                break  # No more entries to evict
        
        # Check entry count limit
        while len(self._cache) >= self.max_size:
            if not await self._evict_lru():
                break  # No more entries to evict
    
    async def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self._access_order:
            return False
        
        # Find LRU entry
        lru_key = self._access_order[0]
        await self._remove_entry(lru_key)
        self._stats.evictions += 1
        
        self.logger.debug(f"Evicted LRU entry: {lru_key[:16]}...")
        return True
    
    async def _remove_entry(self, cache_key: str) -> None:
        """Remove entry from cache."""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            # Update statistics
            self._stats.total_size_bytes -= entry.size_bytes
            self._update_average_entry_size()
            
            # Remove from cache
            del self._cache[cache_key]
            
            # Remove from access order
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            
            # Remove from type mapping
            if cache_key in self._key_to_element_type:
                del self._key_to_element_type[cache_key]
    
    def _update_access_order(self, cache_key: str) -> None:
        """Update LRU access order."""
        # Remove from current position
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        
        # Add to end (most recently used)
        self._access_order.append(cache_key)
    
    def _update_hit_rate(self) -> None:
        """Update cache hit rate."""
        if self._stats.total_requests > 0:
            self._stats.hit_rate = self._stats.cache_hits / self._stats.total_requests
    
    def _update_average_entry_size(self) -> None:
        """Update average entry size."""
        if len(self._cache) > 0:
            self._stats.average_entry_size = self._stats.total_size_bytes / len(self._cache)
        else:
            self._stats.average_entry_size = 0.0
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task to remove expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_expired(self) -> int:
        """Remove all expired entries."""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            await self._remove_entry(key)
            self._stats.expired_entries += 1
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)
    
    async def _count_expired_entries(self) -> int:
        """Count expired entries without removing them."""
        count = 0
        for entry in self._cache.values():
            if entry.is_expired():
                count += 1
        return count
    
    def _load_from_persistence(self) -> None:
        """Load cache from persistent storage."""
        try:
            import os
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'rb') as f:
                    data = pickle.load(f)
                    self._cache = data.get('cache', {})
                    self._access_order = data.get('access_order', [])
                    self._key_to_element_type = data.get('key_to_element_type', {})
                    
                    # Update statistics
                    self._stats.total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
                    self._update_average_entry_size()
                    
                    self.logger.info(f"Loaded {len(self._cache)} entries from persistence")
        except Exception as e:
            self.logger.warning(f"Failed to load cache from persistence: {e}")
    
    async def _save_to_persistence(self) -> None:
        """Save cache to persistent storage."""
        try:
            data = {
                'cache': self._cache,
                'access_order': self._access_order,
                'key_to_element_type': self._key_to_element_type,
                'timestamp': datetime.utcnow()
            }
            
            with open(self.persistence_file, 'wb') as f:
                pickle.dump(data, f)
            
            self.logger.info(f"Saved {len(self._cache)} entries to persistence")
        except Exception as e:
            self.logger.warning(f"Failed to save cache to persistence: {e}")