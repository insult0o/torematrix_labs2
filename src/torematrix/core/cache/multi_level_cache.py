"""Multi-level caching system implementation."""

import hashlib
import pickle
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from pathlib import Path

from cachetools import TTLCache
import diskcache
import redis

from .cache_metrics import CacheMetrics
from .cache_config import CacheConfig


class MultiLevelCache:
    """Multi-level caching system supporting memory, disk, Redis, and object storage."""

    def __init__(self, config: CacheConfig):
        # L1: Memory cache with TTL
        self.memory_cache = TTLCache(
            maxsize=config.memory_cache_size,  # e.g., 1000 items
            ttl=config.memory_cache_ttl        # e.g., 3600 seconds
        )
        
        # L2: Disk cache
        self.disk_cache = diskcache.Cache(
            directory=config.disk_cache_path,
            size_limit=config.disk_cache_size  # e.g., 10GB
        )
        
        # L3: Redis cache (optional)
        self.redis_cache = None
        if config.use_redis:
            self.redis_cache = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=False  # Store binary data
            )
        
        # L4: Object storage (optional)
        self.object_storage = None
        if config.use_object_storage:
            self.object_storage = ObjectStorageCache(config.s3_config)

        # Initialize metrics
        self.metrics = CacheMetrics()
    
    def get(self, key: str, cache_levels: List[str] = None) -> Optional[Any]:
        """Get item from cache, checking each level."""
        if cache_levels is None:
            cache_levels = ['memory', 'disk', 'redis', 'object']
        
        # L1: Check memory cache
        if 'memory' in cache_levels:
            if value := self.memory_cache.get(key):
                self.metrics.record_hit('memory')
                return value
            self.metrics.record_miss('memory')
        
        # L2: Check disk cache
        if 'disk' in cache_levels:
            if value := self.disk_cache.get(key):
                self.metrics.record_hit('disk')
                # Promote to memory cache
                self.memory_cache[key] = value
                return value
            self.metrics.record_miss('disk')
        
        # L3: Check Redis
        if 'redis' in cache_levels and self.redis_cache:
            if cached_data := self.redis_cache.get(key):
                value = pickle.loads(cached_data)
                self.metrics.record_hit('redis')
                # Promote to faster caches
                self._promote_to_faster_caches(key, value, ['memory', 'disk'])
                return value
            self.metrics.record_miss('redis')
        
        # L4: Check object storage
        if 'object' in cache_levels and self.object_storage:
            if value := self.object_storage.get(key):
                self.metrics.record_hit('object')
                # Promote to all faster caches
                self._promote_to_faster_caches(key, value, ['memory', 'disk', 'redis'])
                return value
            self.metrics.record_miss('object')
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            cache_levels: List[str] = None) -> None:
        """Set item in specified cache levels."""
        if cache_levels is None:
            cache_levels = self._determine_cache_levels(value)
        
        # L1: Memory cache
        if 'memory' in cache_levels:
            self.memory_cache[key] = value
        
        # L2: Disk cache
        if 'disk' in cache_levels:
            self.disk_cache.set(key, value, expire=ttl)
        
        # L3: Redis cache
        if 'redis' in cache_levels and self.redis_cache:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis_cache.setex(key, ttl, serialized)
            else:
                self.redis_cache.set(key, serialized)
        
        # L4: Object storage (for large/long-term items)
        if 'object' in cache_levels and self.object_storage:
            self.object_storage.put(key, value, ttl=ttl)
    
    def _promote_to_faster_caches(self, key: str, value: Any, 
                                levels: List[str]) -> None:
        """Promote item to faster cache levels."""
        if 'memory' in levels:
            self.memory_cache[key] = value
        
        if 'disk' in levels:
            self.disk_cache.set(key, value)
        
        if 'redis' in levels and self.redis_cache:
            self.redis_cache.set(key, pickle.dumps(value))
    
    def _determine_cache_levels(self, value: Any) -> List[str]:
        """Determine which cache levels to use based on value characteristics."""
        size = self._estimate_size(value)
        
        if size < 1_000_000:  # < 1MB
            return ['memory', 'disk', 'redis']
        elif size < 100_000_000:  # < 100MB
            return ['disk', 'redis', 'object']
        else:  # Large files
            return ['object']
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        if hasattr(value, '__sizeof__'):
            return value.__sizeof__()
        return len(pickle.dumps(value))