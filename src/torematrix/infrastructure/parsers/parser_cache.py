from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional
import hashlib
import pickle
import diskcache
from cachetools import TTLCache
import redis

from .pdf_parser_base import ParseResult

@dataclass
class CacheConfig:
    """Configuration for the multi-level cache system."""
    memory_cache_size: int = 1000  # Number of items
    memory_cache_ttl: int = 3600   # 1 hour in seconds
    disk_cache_path: str = "/var/cache/torematrix"
    disk_cache_size: int = 10_737_418_240  # 10GB in bytes
    use_redis: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

class PDFParserCache:
    def __init__(self, config: CacheConfig = None):
        if config is None:
            config = CacheConfig()
            
        # L1: Memory cache with TTL
        self.memory_cache = TTLCache(
            maxsize=config.memory_cache_size,
            ttl=config.memory_cache_ttl
        )
        
        # L2: Disk cache
        self.disk_cache = diskcache.Cache(
            directory=config.disk_cache_path,
            size_limit=config.disk_cache_size
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
            
    def get(self, key: str) -> Optional[ParseResult]:
        """Get cached parsing result, checking each cache level."""
        # L1: Check memory cache
        if value := self.memory_cache.get(key):
            return value
            
        # L2: Check disk cache
        if value := self.disk_cache.get(key):
            # Promote to memory cache
            self.memory_cache[key] = value
            return value
            
        # L3: Check Redis if available
        if self.redis_cache:
            if cached_data := self.redis_cache.get(key):
                value = pickle.loads(cached_data)
                # Promote to faster caches
                self.memory_cache[key] = value
                self.disk_cache.set(key, value)
                return value
                
        return None
        
    def set(self, key: str, value: ParseResult, ttl: Optional[int] = None):
        """Set parsing result in all cache levels."""
        # L1: Memory cache
        self.memory_cache[key] = value
        
        # L2: Disk cache
        self.disk_cache.set(key, value, expire=ttl)
        
        # L3: Redis cache
        if self.redis_cache:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis_cache.setex(key, timedelta(seconds=ttl), serialized)
            else:
                self.redis_cache.set(key, serialized)
                
    def generate_key(self, file_path: Path, parser_name: str) -> str:
        """Generate cache key based on file content hash and parser."""
        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()[:8]
        return f"parse:{parser_name}:{file_path.name}:{file_hash}"
        
    def get_or_parse(self, file_path: Path, parser_name: str, 
                     parser_func) -> ParseResult:
        """Get parsed result from cache or parse document."""
        cache_key = self.generate_key(file_path, parser_name)
        
        # Check cache
        if cached := self.get(cache_key):
            return cached
            
        # Parse document
        result = parser_func(file_path)
        
        # Cache result with 24 hour TTL
        self.set(cache_key, result, ttl=86400)
        
        return result