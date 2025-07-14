"""
Cache management for document processing optimization.
"""

import time
import hashlib
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hit_rate: float
    entries: int
    memory_usage_mb: float
    disk_usage_mb: float
    total_requests: int
    hits: int
    misses: int


class CacheManager:
    """Multi-level cache manager for document processing."""
    
    def __init__(self, 
                 memory_cache_mb: int = 512,
                 disk_cache_mb: int = 2048,
                 default_ttl: int = 3600):
        self.memory_cache_mb = memory_cache_mb
        self.disk_cache_mb = disk_cache_mb
        self.default_ttl = default_ttl
        
        # In-memory cache (LRU)
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry)
        self._memory_access_order: List[str] = []
        
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "memory_size": 0,
            "disk_size": 0
        }
        
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then disk)."""
        async with self._lock:
            # Check memory cache first
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                
                if time.time() < expiry:
                    # Update access order for LRU
                    if key in self._memory_access_order:
                        self._memory_access_order.remove(key)
                    self._memory_access_order.append(key)
                    
                    self._stats["hits"] += 1
                    return value
                else:
                    # Expired, remove from cache
                    del self._memory_cache[key]
                    if key in self._memory_access_order:
                        self._memory_access_order.remove(key)
            
            # Memory cache miss
            self._stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        async with self._lock:
            # Add to memory cache
            self._memory_cache[key] = (value, expiry)
            
            # Update access order
            if key in self._memory_access_order:
                self._memory_access_order.remove(key)
            self._memory_access_order.append(key)
            
            # Check memory limits and evict if necessary
            await self._evict_if_needed()
    
    async def _evict_if_needed(self) -> None:
        """Evict least recently used items if memory limit exceeded."""
        # Simple heuristic: if we have too many items, remove oldest 10%
        max_items = self.memory_cache_mb * 10  # Rough estimate
        
        while len(self._memory_cache) > max_items and self._memory_access_order:
            oldest_key = self._memory_access_order.pop(0)
            if oldest_key in self._memory_cache:
                del self._memory_cache[oldest_key]
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
            if key in self._memory_access_order:
                self._memory_access_order.remove(key)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._memory_cache.clear()
            self._memory_access_order.clear()
            self._stats = {"hits": 0, "misses": 0, "memory_size": 0, "disk_size": 0}
    
    async def get_combined_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / max(total_requests, 1)
            
            # Estimate memory usage (rough)
            memory_usage_mb = len(self._memory_cache) * 0.1  # Rough estimate
            
            return CacheStats(
                hit_rate=hit_rate,
                entries=len(self._memory_cache),
                memory_usage_mb=memory_usage_mb,
                disk_usage_mb=0,  # Not implemented in this simple version
                total_requests=total_requests,
                hits=self._stats["hits"],
                misses=self._stats["misses"]
            )


class DocumentCache:
    """Specialized cache for parsed document elements."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def _generate_document_key(self, file_path: Path, parsing_strategy: str, config_hash: str) -> str:
        """Generate cache key for document."""
        # Include file modification time and size to detect changes
        stat = file_path.stat()
        file_info = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        
        combined = f"{file_info}:{parsing_strategy}:{config_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    async def get_parsed_elements(self, 
                                file_path: Path,
                                parsing_strategy: str,
                                config_hash: str) -> Optional[List[Any]]:
        """Get cached parsed elements for document."""
        key = self._generate_document_key(file_path, parsing_strategy, config_hash)
        return await self.cache_manager.get(key)
    
    async def store_parsed_elements(self,
                                  file_path: Path,
                                  parsing_strategy: str,
                                  config_hash: str,
                                  elements: List[Any],
                                  ttl: Optional[int] = None) -> None:
        """Store parsed elements in cache."""
        key = self._generate_document_key(file_path, parsing_strategy, config_hash)
        await self.cache_manager.set(key, elements, ttl)
    
    async def invalidate_document(self, file_path: Path) -> None:
        """Invalidate all cached entries for a document."""
        # This would require tracking keys by file path
        # For now, we don't implement this in the simple version
        pass