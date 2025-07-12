"""Redis cache implementation."""

import pickle
from typing import Optional, Any, Dict, List
from datetime import timedelta

import redis
from redis.exceptions import RedisError

from .cache_metrics import CacheMetrics
from .cache_config import CacheConfig


class RedisCache:
    """Redis-based distributed cache implementation."""
    
    def __init__(self, config: CacheConfig):
        """Initialize Redis cache.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.metrics = CacheMetrics()
        
        # Initialize Redis connection
        self.redis = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=False,  # Keep binary data as is
            socket_timeout=2.0,      # Short timeout for better error handling
            retry_on_timeout=True,   # Retry on timeout
            socket_keepalive=True    # Keep connection alive
        )
        
        # Test connection
        try:
            self.redis.ping()
        except RedisError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            data = self.redis.get(key)
            if data is None:
                self.metrics.record_miss('redis')
                return None
                
            value = pickle.loads(data)
            self.metrics.record_hit('redis')
            return value
            
        except (RedisError, pickle.PickleError) as e:
            self.metrics.record_miss('redis')
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = pickle.dumps(value)
            
            if ttl:
                return bool(
                    self.redis.setex(
                        key,
                        timedelta(seconds=ttl),
                        serialized
                    )
                )
            else:
                return bool(self.redis.set(key, serialized))
                
        except (RedisError, pickle.PickleError):
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            return bool(self.redis.delete(key))
        except RedisError:
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return bool(self.redis.flushdb())
        except RedisError:
            return False
    
    def multi_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict mapping keys to values (missing keys omitted)
        """
        if not keys:
            return {}
            
        try:
            # Get multiple values in one call
            values = self.redis.mget(keys)
            
            results = {}
            for key, data in zip(keys, values):
                if data is None:
                    self.metrics.record_miss('redis')
                    continue
                    
                try:
                    value = pickle.loads(data)
                    results[key] = value
                    self.metrics.record_hit('redis')
                except pickle.PickleError:
                    self.metrics.record_miss('redis')
                    continue
                    
            return results
            
        except RedisError:
            self.metrics.record_miss('redis')
            return {}
    
    def multi_set(self, items: Dict[str, Any], 
                 ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache.
        
        Args:
            items: Dict mapping keys to values
            ttl: Time to live in seconds (applied to all items)
            
        Returns:
            True if all items were set successfully, False otherwise
        """
        if not items:
            return True
            
        try:
            # Serialize all values
            pipeline = self.redis.pipeline()
            
            for key, value in items.items():
                try:
                    serialized = pickle.dumps(value)
                    if ttl:
                        pipeline.setex(
                            key,
                            timedelta(seconds=ttl),
                            serialized
                        )
                    else:
                        pipeline.set(key, serialized)
                except pickle.PickleError:
                    continue
            
            # Execute all commands atomically
            results = pipeline.execute()
            return all(results)
            
        except RedisError:
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.redis.exists(key))
        except RedisError:
            return False
    
    def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, or None if key doesn't exist or has no TTL
        """
        try:
            ttl = self.redis.ttl(key)
            return ttl if ttl > 0 else None
        except RedisError:
            return None
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter by amount.
        
        Args:
            key: Counter key
            amount: Amount to increment by
            
        Returns:
            New counter value, or None on error
        """
        try:
            return self.redis.incr(key, amount)
        except RedisError:
            return None