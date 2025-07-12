"""Unit tests for Redis cache implementation."""

import pickle
import pytest
from unittest.mock import Mock, patch
from redis.exceptions import RedisError

from torematrix.core.cache.redis_cache import RedisCache
from torematrix.core.cache.cache_config import CacheConfig


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch('redis.Redis') as mock:
        # Mock successful connection
        mock.return_value.ping.return_value = True
        yield mock


@pytest.fixture
def config():
    """Create a test configuration."""
    return CacheConfig(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        use_redis=True
    )


@pytest.fixture
def cache(mock_redis, config):
    """Create a test cache instance."""
    return RedisCache(config)


def test_connection_error(mock_redis, config):
    """Test connection error handling."""
    mock_redis.return_value.ping.side_effect = RedisError("Connection failed")
    
    with pytest.raises(ConnectionError):
        RedisCache(config)


def test_basic_operations(cache, mock_redis):
    """Test basic cache operations."""
    key = "test_key"
    value = {"data": "test_value"}
    serialized = pickle.dumps(value)
    
    # Mock get/set operations
    mock_redis.return_value.get.return_value = serialized
    mock_redis.return_value.set.return_value = True
    
    # Test set
    assert cache.set(key, value)
    mock_redis.return_value.set.assert_called_with(key, serialized)
    
    # Test get
    result = cache.get(key)
    assert result == value
    mock_redis.return_value.get.assert_called_with(key)
    
    # Test delete
    mock_redis.return_value.delete.return_value = 1
    assert cache.delete(key)
    mock_redis.return_value.delete.assert_called_with(key)


def test_ttl_operations(cache, mock_redis):
    """Test TTL functionality."""
    key = "test_key"
    value = "test_value"
    ttl = 60
    
    # Test set with TTL
    cache.set(key, value, ttl=ttl)
    mock_redis.return_value.setex.assert_called()
    
    # Test get TTL
    mock_redis.return_value.ttl.return_value = 50
    assert cache.ttl(key) == 50


def test_multi_operations(cache, mock_redis):
    """Test multi-get/set operations."""
    items = {
        "key1": "value1",
        "key2": "value2"
    }
    
    # Mock pipeline
    pipeline_mock = Mock()
    mock_redis.return_value.pipeline.return_value = pipeline_mock
    pipeline_mock.execute.return_value = [True, True]
    
    # Test multi_set
    assert cache.multi_set(items)
    assert pipeline_mock.set.call_count == 2
    
    # Mock mget
    serialized_values = [
        pickle.dumps("value1"),
        pickle.dumps("value2")
    ]
    mock_redis.return_value.mget.return_value = serialized_values
    
    # Test multi_get
    results = cache.multi_get(list(items.keys()))
    assert results == items
    mock_redis.return_value.mget.assert_called_with(list(items.keys()))


def test_error_handling(cache, mock_redis):
    """Test error handling."""
    key = "test_key"
    value = "test_value"
    
    # Test get with Redis error
    mock_redis.return_value.get.side_effect = RedisError()
    assert cache.get(key) is None
    
    # Test get with unpickling error
    mock_redis.return_value.get.side_effect = None
    mock_redis.return_value.get.return_value = b'invalid pickle data'
    assert cache.get(key) is None
    
    # Test set with Redis error
    mock_redis.return_value.set.side_effect = RedisError()
    assert not cache.set(key, value)


def test_metrics_recording(cache, mock_redis):
    """Test metrics recording."""
    key = "test_key"
    value = {"data": "test_value"}
    serialized = pickle.dumps(value)
    
    # Test hit
    mock_redis.return_value.get.return_value = serialized
    cache.get(key)
    assert cache.metrics.hits['redis'] == 1
    
    # Test miss
    mock_redis.return_value.get.return_value = None
    cache.get(key)
    assert cache.metrics.misses['redis'] == 1


def test_counter_operations(cache, mock_redis):
    """Test counter operations."""
    key = "counter"
    
    # Test increment
    mock_redis.return_value.incr.return_value = 1
    assert cache.incr(key) == 1
    mock_redis.return_value.incr.assert_called_with(key, 1)
    
    # Test increment by amount
    mock_redis.return_value.incr.return_value = 6
    assert cache.incr(key, 5) == 6
    mock_redis.return_value.incr.assert_called_with(key, 5)
    
    # Test increment error
    mock_redis.return_value.incr.side_effect = RedisError()
    assert cache.incr(key) is None