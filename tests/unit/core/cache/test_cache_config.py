"""Unit tests for cache configuration."""

import pytest
from pathlib import Path
from torematrix.core.cache.cache_config import CacheConfig


def test_default_config():
    """Test default configuration values."""
    config = CacheConfig()
    
    assert config.memory_cache_size == 1000
    assert config.memory_cache_ttl == 3600
    assert config.disk_cache_path == Path("/var/cache/torematrix")
    assert config.disk_cache_size == 10 * 1024 * 1024 * 1024  # 10GB
    assert not config.use_redis
    assert not config.use_object_storage


def test_custom_config():
    """Test custom configuration values."""
    config = CacheConfig(
        memory_cache_size=500,
        memory_cache_ttl=1800,
        disk_cache_path=Path("/custom/cache/path"),
        disk_cache_size=5 * 1024 * 1024 * 1024,  # 5GB
        use_redis=True,
        redis_host="redis.example.com",
        redis_port=6380
    )
    
    assert config.memory_cache_size == 500
    assert config.memory_cache_ttl == 1800
    assert config.disk_cache_path == Path("/custom/cache/path")
    assert config.disk_cache_size == 5 * 1024 * 1024 * 1024
    assert config.use_redis
    assert config.redis_host == "redis.example.com"
    assert config.redis_port == 6380


def test_s3_config():
    """Test S3 configuration."""
    s3_config = {
        "bucket": "test-bucket",
        "prefix": "cache/",
        "region": "us-west-2"
    }
    
    config = CacheConfig(
        use_object_storage=True,
        s3_config=s3_config
    )
    
    assert config.use_object_storage
    assert config.s3_config["bucket"] == "test-bucket"
    assert config.s3_config["prefix"] == "cache/"
    assert config.s3_config["region"] == "us-west-2"