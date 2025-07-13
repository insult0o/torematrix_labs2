"""
Redis-based persistence backend.

This backend stores state in Redis, providing fast in-memory persistence
with optional durability and clustering support.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import gzip
import time
import hashlib

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

from .base import PersistenceBackend, PersistenceConfig

logger = logging.getLogger(__name__)


class RedisPersistenceBackend(PersistenceBackend):
    """
    Redis-based persistence backend.
    
    Stores state versions in Redis with support for:
    - Fast in-memory access
    - Optional compression
    - TTL for automatic cleanup
    - Clustering support
    """
    
    def __init__(
        self, 
        config: PersistenceConfig,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "torematrix:state",
        ttl: Optional[int] = None
    ):
        super().__init__(config)
        
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis backend requires 'redis' package. "
                "Install it with: pip install redis"
            )
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl  # Time to live in seconds
        self._redis_pool: Optional[aioredis.Redis] = None
        self._connection_lock = asyncio.Lock()
        
        # Key patterns
        self.state_key_pattern = f"{key_prefix}:states:{{version}}"
        self.metadata_key_pattern = f"{key_prefix}:metadata:{{version}}"
        self.index_key = f"{key_prefix}:index"
        self.latest_key = f"{key_prefix}:latest"
        
    async def _do_initialize(self) -> None:
        """Initialize the Redis connection."""
        try:
            # Parse Redis URL and create connection
            self._redis_pool = aioredis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=10.0,
                socket_timeout=10.0,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis_pool.ping()
            
            # Initialize index if it doesn't exist
            exists = await self._redis_pool.exists(self.index_key)
            if not exists:
                index_data = {
                    "versions": [],
                    "created_at": datetime.now().isoformat(),
                    "format_version": "1.0"
                }
                await self._redis_pool.set(
                    self.index_key, 
                    json.dumps(index_data).encode('utf-8'),
                    ex=self.ttl
                )
            
            logger.info(f"Redis persistence backend initialized at {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis backend: {e}")
            raise
    
    async def save_state(
        self, 
        state: Dict[str, Any], 
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save state to Redis.
        
        Args:
            state: The state data to save
            version: Version identifier for this state
            metadata: Optional metadata associated with this state
        """
        try:
            timestamp = time.time()
            
            # Serialize state
            state_json = json.dumps(state, ensure_ascii=False)
            state_data = state_json.encode('utf-8')
            compressed = False
            
            # Compress if enabled and data is large enough
            if self.config.compression_enabled and len(state_data) > 1024:
                compressed_data = gzip.compress(state_data)
                if len(compressed_data) < len(state_data):
                    state_data = compressed_data
                    compressed = True
            
            # Calculate checksum
            checksum = hashlib.sha256(state_data).hexdigest()
            
            # Prepare state record
            state_record = {
                "version": version,
                "timestamp": timestamp,
                "state_data": state_data,
                "compressed": compressed,
                "size_bytes": len(state_data),
                "checksum": checksum,
                "created_at": datetime.now().isoformat()
            }
            
            # Prepare metadata
            metadata_record = {
                "version": version,
                "timestamp": timestamp,
                "size_bytes": len(state_data),
                "compressed": compressed,
                "compression_ratio": len(compressed_data) / len(state_json.encode('utf-8')) if compressed else 1.0,
                "checksum": checksum,
                **(metadata or {})
            }
            
            async with self._connection_lock:
                # Use pipeline for atomic operations
                pipe = self._redis_pool.pipeline()
                
                # Save state
                state_key = self.state_key_pattern.format(version=version)
                pipe.set(
                    state_key,
                    json.dumps(state_record).encode('utf-8'),
                    ex=self.ttl
                )
                
                # Save metadata
                metadata_key = self.metadata_key_pattern.format(version=version)
                pipe.set(
                    metadata_key,
                    json.dumps(metadata_record).encode('utf-8'),
                    ex=self.ttl
                )
                
                # Update index
                await self._update_index_pipeline(pipe, version, timestamp)
                
                # Execute pipeline
                await pipe.execute()
            
            logger.debug(f"State version {version} saved to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state version {version} to Redis: {e}")
            raise
    
    async def load_state(self, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load state from Redis.
        
        Args:
            version: Specific version to load, or None for latest
            
        Returns:
            The loaded state data
        """
        try:
            if version is None:
                version = await self._get_latest_version()
                if version is None:
                    return {}
            
            state_key = self.state_key_pattern.format(version=version)
            
            async with self._connection_lock:
                state_data = await self._redis_pool.get(state_key)
                
            if state_data is None:
                raise ValueError(f"State version {version} not found")
            
            # Deserialize state record
            state_record = json.loads(state_data.decode('utf-8'))
            
            # Extract and decompress state data
            raw_state_data = state_record["state_data"]
            if isinstance(raw_state_data, str):
                # Handle base64 encoded data from JSON
                import base64
                raw_state_data = base64.b64decode(raw_state_data)
            elif isinstance(raw_state_data, dict):
                # Handle case where state_data is stored as bytes in JSON
                raw_state_data = bytes(raw_state_data["data"]) if "data" in raw_state_data else raw_state_data
            
            if state_record.get("compressed", False):
                state_json = gzip.decompress(raw_state_data).decode('utf-8')
            else:
                state_json = raw_state_data.decode('utf-8') if isinstance(raw_state_data, bytes) else raw_state_data
            
            state = json.loads(state_json)
            
            logger.debug(f"State version {version} loaded from Redis successfully")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state version {version} from Redis: {e}")
            raise
    
    async def list_versions(self) -> List[str]:
        """
        List all saved state versions.
        
        Returns:
            List of version identifiers, sorted by creation time
        """
        try:
            async with self._connection_lock:
                index_data = await self._redis_pool.get(self.index_key)
                
            if index_data is None:
                return []
            
            index = json.loads(index_data.decode('utf-8'))
            return index.get("versions", [])
            
        except Exception as e:
            logger.error(f"Failed to list versions from Redis: {e}")
            return []
    
    async def delete_version(self, version: str) -> bool:
        """
        Delete a specific state version.
        
        Args:
            version: Version identifier to delete
            
        Returns:
            True if version was deleted, False if it didn't exist
        """
        try:
            state_key = self.state_key_pattern.format(version=version)
            metadata_key = self.metadata_key_pattern.format(version=version)
            
            async with self._connection_lock:
                # Check if version exists
                exists = await self._redis_pool.exists(state_key)
                if not exists:
                    return False
                
                # Use pipeline for atomic deletion
                pipe = self._redis_pool.pipeline()
                
                # Delete state and metadata
                pipe.delete(state_key)
                pipe.delete(metadata_key)
                
                # Update index
                await self._remove_from_index_pipeline(pipe, version)
                
                # Execute pipeline
                results = await pipe.execute()
                
                # Check if state was actually deleted
                deleted = results[0] > 0
            
            logger.debug(f"State version {version} deleted from Redis: {deleted}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete state version {version} from Redis: {e}")
            return False
    
    async def get_metadata(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Metadata dict or None if version doesn't exist
        """
        try:
            metadata_key = self.metadata_key_pattern.format(version=version)
            
            async with self._connection_lock:
                metadata_data = await self._redis_pool.get(metadata_key)
                
            if metadata_data is None:
                return None
            
            return json.loads(metadata_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Failed to get metadata for version {version} from Redis: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources and close Redis connection."""
        if self._redis_pool:
            await self._redis_pool.close()
            self._redis_pool = None
        logger.debug("Redis persistence backend cleaned up")
    
    async def _update_index_pipeline(self, pipe, version: str, timestamp: float) -> None:
        """Update the index using a Redis pipeline."""
        # Get current index
        index_data = await self._redis_pool.get(self.index_key)
        if index_data:
            index = json.loads(index_data.decode('utf-8'))
        else:
            index = {"versions": [], "created_at": datetime.now().isoformat()}
        
        # Update versions list
        versions = index.get("versions", [])
        if version not in versions:
            versions.append(version)
            # Sort versions by timestamp (assuming version format includes timestamp)
            versions.sort()
        
        index["versions"] = versions
        index["latest_version"] = version
        index["last_updated"] = datetime.now().isoformat()
        
        # Update index in pipeline
        pipe.set(
            self.index_key,
            json.dumps(index).encode('utf-8'),
            ex=self.ttl
        )
        
        # Update latest version key
        pipe.set(self.latest_key, version.encode('utf-8'), ex=self.ttl)
    
    async def _remove_from_index_pipeline(self, pipe, version: str) -> None:
        """Remove a version from the index using a Redis pipeline."""
        # Get current index
        index_data = await self._redis_pool.get(self.index_key)
        if index_data:
            index = json.loads(index_data.decode('utf-8'))
        else:
            return  # Nothing to remove
        
        # Update versions list
        versions = index.get("versions", [])
        if version in versions:
            versions.remove(version)
        
        # Update latest version if needed
        current_latest = index.get("latest_version")
        if current_latest == version:
            index["latest_version"] = versions[-1] if versions else None
        
        index["versions"] = versions
        index["last_updated"] = datetime.now().isoformat()
        
        # Update index in pipeline
        pipe.set(
            self.index_key,
            json.dumps(index).encode('utf-8'),
            ex=self.ttl
        )
        
        # Update latest version key
        if index["latest_version"]:
            pipe.set(self.latest_key, index["latest_version"].encode('utf-8'), ex=self.ttl)
        else:
            pipe.delete(self.latest_key)
    
    async def _get_latest_version(self) -> Optional[str]:
        """Get the latest version from Redis."""
        try:
            latest_data = await self._redis_pool.get(self.latest_key)
            return latest_data.decode('utf-8') if latest_data else None
        except Exception:
            # Fallback to index
            index_data = await self._redis_pool.get(self.index_key)
            if index_data:
                index = json.loads(index_data.decode('utf-8'))
                return index.get("latest_version")
            return None
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            # Get all state keys
            state_pattern = self.state_key_pattern.format(version="*")
            state_keys = await self._redis_pool.keys(state_pattern)
            
            total_size = 0
            compressed_count = 0
            
            # Get sizes for all state keys
            if state_keys:
                pipe = self._redis_pool.pipeline()
                for key in state_keys:
                    pipe.memory_usage(key)
                
                sizes = await pipe.execute()
                total_size = sum(size for size in sizes if size is not None)
            
            # Get index info
            index_data = await self._redis_pool.get(self.index_key)
            latest_version = await self._get_latest_version()
            
            # Get Redis info
            info = await self._redis_pool.info('memory')
            redis_memory = info.get('used_memory', 0)
            
            return {
                "total_versions": len(state_keys),
                "total_size_bytes": total_size,
                "compressed_count": compressed_count,
                "redis_memory_usage": redis_memory,
                "redis_url": self.redis_url,
                "key_prefix": self.key_prefix,
                "latest_version": latest_version,
                "ttl": self.ttl
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats from Redis: {e}")
            return {}
    
    async def flush_all_versions(self) -> int:
        """
        Delete all state versions (useful for testing).
        
        Returns:
            Number of versions deleted
        """
        try:
            # Get all keys with our prefix
            pattern = f"{self.key_prefix}:*"
            keys = await self._redis_pool.keys(pattern)
            
            if not keys:
                return 0
            
            # Delete all keys
            deleted = await self._redis_pool.delete(*keys)
            
            logger.info(f"Flushed {deleted} keys from Redis")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to flush Redis keys: {e}")
            return 0
    
    async def set_ttl(self, version: str, ttl: int) -> bool:
        """
        Set TTL for a specific version.
        
        Args:
            version: Version identifier
            ttl: Time to live in seconds
            
        Returns:
            True if TTL was set successfully
        """
        try:
            state_key = self.state_key_pattern.format(version=version)
            metadata_key = self.metadata_key_pattern.format(version=version)
            
            pipe = self._redis_pool.pipeline()
            pipe.expire(state_key, ttl)
            pipe.expire(metadata_key, ttl)
            
            results = await pipe.execute()
            return all(results)
            
        except Exception as e:
            logger.error(f"Failed to set TTL for version {version}: {e}")
            return False