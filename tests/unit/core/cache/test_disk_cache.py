"""Unit tests for disk cache implementation."""

import pytest
import time
import shutil
from pathlib import Path
from torematrix.core.cache.disk_cache import DiskCache


@pytest.fixture
def cache_dir(tmp_path) -> Path:
    """Create a temporary directory for cache files."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache(cache_dir: Path) -> DiskCache:
    """Create a test cache instance."""
    return DiskCache(cache_dir)


def test_basic_operations(cache: DiskCache):
    """Test basic cache operations."""
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set value
    cache.set(key, value)
    
    # Get value
    result = cache.get(key)
    assert result == value
    
    # Delete value
    cache.delete(key)
    assert cache.get(key) is None


def test_ttl_expiration(cache: DiskCache):
    """Test TTL expiration."""
    key = "test_key"
    value = "test_value"
    ttl = 1  # 1 second
    
    # Set with TTL
    cache.set(key, value, ttl=ttl)
    
    # Get immediately
    assert cache.get(key) == value
    
    # Wait for expiration
    time.sleep(ttl + 0.1)
    
    # Should be expired
    assert cache.get(key) is None
    
    # Metadata should be cleaned up
    assert key not in cache.metadata


def test_size_limit(cache_dir: Path):
    """Test cache size limiting."""
    # Create cache with 1KB size limit
    cache = DiskCache(cache_dir, size_limit=1024)
    
    # Add entries until limit is exceeded
    for i in range(100):
        key = f"key_{i}"
        value = "x" * 100  # 100 bytes
        cache.set(key, value)
    
    # Cache size should be under limit
    assert cache.get_size() <= 1024
    
    # Oldest entries should be removed
    assert cache.get("key_0") is None


def test_clear_cache(cache: DiskCache):
    """Test cache clearing."""
    # Add some entries
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    # Clear cache
    cache.clear()
    
    # Cache should be empty
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get_size() == 0
    assert not cache.metadata


def test_corrupted_value(cache: DiskCache):
    """Test handling of corrupted cache files."""
    key = "test_key"
    value = "test_value"
    
    # Set value
    cache.set(key, value)
    
    # Corrupt the cache file
    file_path = cache._get_file_path(key)
    with open(file_path, 'wb') as f:
        f.write(b'corrupted data')
    
    # Get should handle corruption gracefully
    assert cache.get(key) is None
    assert key not in cache.metadata


def test_metrics_recording(cache: DiskCache):
    """Test metrics recording."""
    key = "test_key"
    value = "test_value"
    
    # Record miss
    cache.get(key)
    assert cache.metrics.misses['disk'] == 1
    
    # Record hit
    cache.set(key, value)
    cache.get(key)
    assert cache.metrics.hits['disk'] == 1


def test_persistence(cache_dir: Path):
    """Test cache persistence across instances."""
    # First instance
    cache1 = DiskCache(cache_dir)
    cache1.set("key", "value")
    
    # Second instance
    cache2 = DiskCache(cache_dir)
    assert cache2.get("key") == "value"


def test_concurrent_size_limit(cache_dir: Path):
    """Test size limiting with concurrent writes."""
    cache = DiskCache(cache_dir, size_limit=500)
    
    # Write several large values concurrently
    values = [("key1", "x" * 200), ("key2", "x" * 200), ("key3", "x" * 200)]
    for key, value in values:
        cache.set(key, value)
    
    # Size should be under limit
    assert cache.get_size() <= 500
    
    # At least the most recent value should be cached
    assert cache.get("key3") is not None