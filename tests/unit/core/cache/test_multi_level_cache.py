"""Unit tests for multi-level cache implementation."""

import pytest
from pathlib import Path
from datetime import timedelta
from typing import Dict, Any

from torematrix.core.cache.multi_level_cache import MultiLevelCache
from torematrix.core.cache.cache_config import CacheConfig


@pytest.fixture
def cache_config() -> CacheConfig:
    """Create a test cache configuration."""
    return CacheConfig(
        memory_cache_size=100,
        memory_cache_ttl=60,
        disk_cache_path=Path("/tmp/torematrix_test_cache"),
        disk_cache_size=1024 * 1024,  # 1MB
        use_redis=False,
        use_object_storage=False
    )


@pytest.fixture
def cache(cache_config: CacheConfig) -> MultiLevelCache:
    """Create a test cache instance."""
    return MultiLevelCache(cache_config)


def test_memory_cache_basic(cache: MultiLevelCache):
    """Test basic memory cache operations."""
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set value
    cache.set(key, value, cache_levels=['memory'])
    
    # Get value
    result = cache.get(key, cache_levels=['memory'])
    assert result == value
    
    # Check metrics
    assert cache.metrics.hits['memory'] == 1
    assert cache.metrics.misses['memory'] == 0


def test_memory_cache_miss(cache: MultiLevelCache):
    """Test memory cache miss."""
    result = cache.get("nonexistent_key", cache_levels=['memory'])
    assert result is None
    assert cache.metrics.misses['memory'] == 1


def test_disk_cache_basic(cache: MultiLevelCache):
    """Test basic disk cache operations."""
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set value
    cache.set(key, value, cache_levels=['disk'])
    
    # Get value
    result = cache.get(key, cache_levels=['disk'])
    assert result == value
    
    # Check metrics
    assert cache.metrics.hits['disk'] == 1
    assert cache.metrics.misses['disk'] == 0


def test_disk_cache_promotion(cache: MultiLevelCache):
    """Test promotion from disk to memory cache."""
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set in disk only
    cache.set(key, value, cache_levels=['disk'])
    
    # Get from both levels
    result = cache.get(key)
    assert result == value
    
    # Should now be in memory
    memory_result = cache.get(key, cache_levels=['memory'])
    assert memory_result == value
    assert cache.metrics.hits['memory'] == 1


def test_cache_ttl(cache: MultiLevelCache):
    """Test cache TTL functionality."""
    key = "test_key"
    value = {"data": "test_value"}
    ttl = 1  # 1 second
    
    # Set with TTL
    cache.set(key, value, ttl=ttl, cache_levels=['memory', 'disk'])
    
    # Get immediately
    result = cache.get(key)
    assert result == value
    
    # Wait for TTL
    import time
    time.sleep(ttl + 0.1)
    
    # Should be expired
    result = cache.get(key)
    assert result is None


def test_cache_levels_estimation(cache: MultiLevelCache):
    """Test automatic cache level determination."""
    # Small value
    small_value = "small"
    small_levels = cache._determine_cache_levels(small_value)
    assert set(small_levels) == {'memory', 'disk', 'redis'}
    
    # Medium value (generate ~2MB string)
    medium_value = "x" * (2 * 1024 * 1024)
    medium_levels = cache._determine_cache_levels(medium_value)
    assert set(medium_levels) == {'disk', 'redis', 'object'}
    
    # Large value (generate ~200MB string)
    large_value = "x" * (200 * 1024 * 1024)
    large_levels = cache._determine_cache_levels(large_value)
    assert large_levels == ['object']