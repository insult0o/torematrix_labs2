"""Cache configuration model."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class CacheConfig:
    """Configuration for multi-level cache system."""
    
    # Memory cache settings
    memory_cache_size: int = 1000  # Number of items
    memory_cache_ttl: int = 3600   # Seconds
    
    # Disk cache settings
    disk_cache_path: Path = Path("/var/cache/torematrix")
    disk_cache_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    
    # Redis settings
    use_redis: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Object storage settings
    use_object_storage: bool = False
    s3_config: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # Cache policies
    default_ttl: int = 86400  # 24 hours
    compression_threshold: int = 1_000_000  # 1MB
    promote_on_hit: bool = True