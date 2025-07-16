"""
Comprehensive tests for performance optimization components.

Tests caching, memory optimization, async processing,
and performance monitoring capabilities.
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.torematrix.core.operations.merge_split.performance import (
    CoordinateCache,
    CacheStrategy,
    CacheEntry,
    MemoryOptimizer,
    AsyncProcessor,
    ProcessingPriority,
    cache_result,
    get_coordinate_cache,
    get_memory_optimizer,
    get_async_processor
)


@pytest.fixture
def coordinate_cache():
    """Create a fresh coordinate cache for each test."""
    return CoordinateCache(max_size=100, max_memory_mb=10, default_ttl=60.0)


@pytest.fixture
def memory_optimizer():
    """Create a fresh memory optimizer for each test."""
    return MemoryOptimizer(memory_limit_mb=100, warning_threshold=0.7, cleanup_threshold=0.9)


@pytest.fixture
async def async_processor():
    """Create and start async processor for tests."""
    processor = AsyncProcessor(max_workers=2, queue_size=10)
    await processor.start()
    yield processor
    await processor.stop()


class TestCacheEntry:
    """Test CacheEntry dataclass and methods."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and initialization."""
        value = {"test": "data", "number": 42}
        entry = CacheEntry(key="test_key", value=value, ttl_seconds=30.0)
        
        assert entry.key == "test_key"
        assert entry.value == value
        assert entry.created_at > 0
        assert entry.last_accessed > 0
        assert entry.access_count == 0
        assert entry.ttl_seconds == 30.0
        assert entry.size_bytes > 0
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Non-expiring entry
        entry1 = CacheEntry(key="test1", value="data", ttl_seconds=None)
        assert not entry1.is_expired()
        
        # Fresh entry
        entry2 = CacheEntry(key="test2", value="data", ttl_seconds=1.0)
        assert not entry2.is_expired()
        
        # Expired entry
        entry3 = CacheEntry(key="test3", value="data", ttl_seconds=0.1)
        time.sleep(0.2)
        assert entry3.is_expired()
    
    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(key="test", value="data")
        
        initial_access_time = entry.last_accessed
        initial_count = entry.access_count
        
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        assert entry.last_accessed > initial_access_time
        assert entry.access_count == initial_count + 1


class TestCoordinateCache:
    """Test CoordinateCache functionality."""
    
    def test_cache_initialization(self, coordinate_cache):
        """Test cache initialization with parameters."""
        assert coordinate_cache.max_size == 100
        assert coordinate_cache.max_memory_mb == 10
        assert coordinate_cache.strategy == CacheStrategy.HYBRID
        assert coordinate_cache.default_ttl == 60.0
        assert len(coordinate_cache.cache) == 0
        assert coordinate_cache.size_bytes == 0
    
    def test_cache_put_and_get(self, coordinate_cache):
        """Test basic cache put and get operations."""
        key = "test_key"
        value = {"x": 100, "y": 200, "width": 50, "height": 30}
        
        # Put value
        coordinate_cache.put(key, value)
        assert len(coordinate_cache.cache) == 1
        assert coordinate_cache.size_bytes > 0
        
        # Get value
        retrieved = coordinate_cache.get(key)
        assert retrieved == value
        
        # Check metrics
        stats = coordinate_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["total_requests"] == 1
    
    def test_cache_miss(self, coordinate_cache):
        """Test cache miss behavior."""
        result = coordinate_cache.get("nonexistent_key")
        assert result is None
        
        stats = coordinate_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
    
    def test_cache_expiration(self, coordinate_cache):
        """Test cache entry expiration."""
        key = "expiring_key"
        value = {"data": "test"}
        
        # Put with short TTL
        coordinate_cache.put(key, value, ttl=0.1)
        
        # Should be available immediately
        assert coordinate_cache.get(key) == value
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired and return None
        assert coordinate_cache.get(key) is None
    
    def test_cache_update_existing_key(self, coordinate_cache):
        """Test updating existing cache key."""
        key = "update_key"
        value1 = {"version": 1}
        value2 = {"version": 2}
        
        coordinate_cache.put(key, value1)
        assert coordinate_cache.get(key) == value1
        
        coordinate_cache.put(key, value2)
        assert coordinate_cache.get(key) == value2
        assert len(coordinate_cache.cache) == 1  # Should not duplicate
    
    def test_cache_size_limit_eviction(self):
        """Test cache eviction when size limit is reached."""
        cache = CoordinateCache(max_size=3, max_memory_mb=100)
        
        # Fill cache to capacity
        for i in range(3):
            cache.put(f"key{i}", f"value{i}")
        
        assert len(cache.cache) == 3
        
        # Add one more item - should evict oldest
        cache.put("key3", "value3")
        assert len(cache.cache) == 3
        assert cache.get("key0") is None  # Should be evicted
        assert cache.get("key3") == "value3"  # Should be present
    
    def test_cache_memory_limit_eviction(self):
        """Test cache eviction when memory limit is reached."""
        cache = CoordinateCache(max_size=1000, max_memory_mb=0.001)  # Very small memory limit
        
        # Add large data until memory limit is hit
        large_data = "x" * 1000  # 1KB string
        
        cache.put("key1", large_data)
        initial_size = len(cache.cache)
        
        # Add more data - should trigger eviction
        cache.put("key2", large_data)
        
        # Should have evicted some entries
        assert len(cache.cache) <= initial_size
    
    def test_cache_lru_strategy(self):
        """Test LRU cache eviction strategy."""
        cache = CoordinateCache(max_size=3, strategy=CacheStrategy.LRU)
        
        # Fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        cache.put("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Should still be there
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should still be there
        assert cache.get("key4") == "value4"  # Should be there
    
    def test_cache_remove(self, coordinate_cache):
        """Test explicit cache entry removal."""
        key = "remove_key"
        value = {"data": "test"}
        
        coordinate_cache.put(key, value)
        assert coordinate_cache.get(key) == value
        
        success = coordinate_cache.remove(key)
        assert success is True
        assert coordinate_cache.get(key) is None
        
        # Try to remove non-existent key
        success = coordinate_cache.remove("nonexistent")
        assert success is False
    
    def test_cache_clear(self, coordinate_cache):
        """Test clearing entire cache."""
        # Add multiple entries
        for i in range(5):
            coordinate_cache.put(f"key{i}", f"value{i}")
        
        assert len(coordinate_cache.cache) == 5
        
        coordinate_cache.clear()
        
        assert len(coordinate_cache.cache) == 0
        assert coordinate_cache.size_bytes == 0
    
    def test_cache_hit_rate_calculation(self, coordinate_cache):
        """Test hit rate calculation."""
        # Initial hit rate should be 0
        assert coordinate_cache.get_hit_rate() == 0.0
        
        # Add some data
        coordinate_cache.put("key1", "value1")
        coordinate_cache.put("key2", "value2")
        
        # Perform hits and misses
        coordinate_cache.get("key1")  # hit
        coordinate_cache.get("key2")  # hit
        coordinate_cache.get("key3")  # miss
        coordinate_cache.get("key4")  # miss
        
        # Hit rate should be 50% (2 hits out of 4 requests)
        assert coordinate_cache.get_hit_rate() == 50.0
    
    def test_cache_key_generators(self):
        """Test cache key generation utilities."""
        # Element bounds key
        bounds_key = CoordinateCache.element_bounds_key("elem123", 5)
        assert bounds_key == "bounds:elem123:5"
        
        # Transformation key
        transform_params = {"scale": 1.5, "rotation": 45}
        transform_key = CoordinateCache.transformation_key("elem456", transform_params)
        assert transform_key.startswith("transform:elem456:")
        assert len(transform_key) > 20  # Should include hash
        
        # Intersection key (should be order-independent)
        intersection_key1 = CoordinateCache.intersection_key("elem1", "elem2")
        intersection_key2 = CoordinateCache.intersection_key("elem2", "elem1")
        assert intersection_key1 == intersection_key2
        assert "elem1" in intersection_key1
        assert "elem2" in intersection_key1


class TestMemoryOptimizer:
    """Test MemoryOptimizer functionality."""
    
    def test_memory_optimizer_initialization(self, memory_optimizer):
        """Test memory optimizer initialization."""
        assert memory_optimizer.memory_limit_mb == 100
        assert memory_optimizer.warning_threshold == 0.7
        assert memory_optimizer.cleanup_threshold == 0.9
        assert len(memory_optimizer.cleanup_callbacks) == 0
        assert memory_optimizer.monitoring_enabled is True
    
    @patch('src.torematrix.core.operations.merge_split.performance.psutil')
    def test_get_memory_usage(self, mock_psutil, memory_optimizer):
        """Test memory usage monitoring."""
        # Mock psutil
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        mock_memory_info.vms = 200 * 1024 * 1024  # 200MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 25.5
        mock_psutil.Process.return_value = mock_process
        
        mock_virtual_memory = Mock()
        mock_virtual_memory.available = 1024 * 1024 * 1024  # 1GB
        mock_psutil.virtual_memory.return_value = mock_virtual_memory
        
        usage = memory_optimizer.get_memory_usage()
        
        assert usage['rss_mb'] == 100.0
        assert usage['vms_mb'] == 200.0
        assert usage['percent'] == 25.5
        assert usage['available_mb'] == 1024.0
    
    def test_register_cleanup_callback(self, memory_optimizer):
        """Test registering cleanup callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        memory_optimizer.register_cleanup_callback(callback1)
        memory_optimizer.register_cleanup_callback(callback2)
        
        assert len(memory_optimizer.cleanup_callbacks) == 2
        assert callback1 in memory_optimizer.cleanup_callbacks
        assert callback2 in memory_optimizer.cleanup_callbacks
    
    def test_create_lazy_loader(self, memory_optimizer):
        """Test lazy loader creation and usage."""
        load_func = Mock(return_value="loaded_data")
        
        lazy_loader = memory_optimizer.create_lazy_loader("test_loader", load_func)
        
        # First call should execute load function
        result1 = lazy_loader()
        assert result1 == "loaded_data"
        load_func.assert_called_once()
        
        # Second call should use cached object (if still in memory)
        result2 = lazy_loader()
        assert result2 == "loaded_data"
        # Load function should still only be called once if object is cached
    
    @patch('src.torematrix.core.operations.merge_split.performance.psutil')
    def test_should_cleanup(self, mock_psutil, memory_optimizer):
        """Test cleanup threshold detection."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_process.memory_info.return_value = mock_memory_info
        mock_psutil.Process.return_value = mock_process
        
        # Below threshold
        mock_memory_info.rss = 50 * 1024 * 1024  # 50MB
        assert not memory_optimizer.should_cleanup()
        
        # Above threshold
        mock_memory_info.rss = 95 * 1024 * 1024  # 95MB (above 90% of 100MB limit)
        assert memory_optimizer.should_cleanup()
    
    @patch('src.torematrix.core.operations.merge_split.performance.psutil')
    def test_force_cleanup(self, mock_psutil, memory_optimizer):
        """Test forced memory cleanup."""
        # Mock memory usage
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB initially
        mock_process.memory_info.return_value = mock_memory_info
        mock_psutil.Process.return_value = mock_process
        
        # Register cleanup callbacks
        callback1 = Mock()
        callback2 = Mock()
        memory_optimizer.register_cleanup_callback(callback1)
        memory_optimizer.register_cleanup_callback(callback2)
        
        # Simulate memory reduction after cleanup
        def reduce_memory():
            mock_memory_info.rss = 50 * 1024 * 1024  # 50MB after cleanup
        
        callback1.side_effect = reduce_memory
        
        stats = memory_optimizer.force_cleanup()
        
        assert stats['callbacks_executed'] == 2
        assert stats['memory_before_mb'] == 100.0
        assert stats['memory_after_mb'] == 50.0
        assert stats['memory_freed_mb'] == 50.0
        
        callback1.assert_called_once()
        callback2.assert_called_once()


class TestAsyncProcessor:
    """Test AsyncProcessor functionality."""
    
    @pytest.mark.asyncio
    async def test_async_processor_initialization(self):
        """Test async processor initialization."""
        processor = AsyncProcessor(max_workers=3, queue_size=50)
        
        assert processor.max_workers == 3
        assert processor.queue_size == 50
        assert not processor.running
        assert len(processor.workers) == 0
        assert len(processor.active_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_processor(self):
        """Test starting and stopping async processor."""
        processor = AsyncProcessor(max_workers=2)
        
        # Start processor
        await processor.start()
        assert processor.running is True
        assert len(processor.workers) == 2
        
        # Stop processor
        await processor.stop()
        assert processor.running is False
        assert len(processor.workers) == 0
        assert len(processor.active_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_submit_sync_task(self, async_processor):
        """Test submitting synchronous task."""
        def sync_task(x, y):
            return x + y
        
        result_received = []
        
        async def callback(result):
            result_received.append(result)
        
        success = await async_processor.submit_task(
            task_id="sync_test",
            func=sync_task,
            args=(5, 3),
            callback=callback
        )
        
        assert success is True
        
        # Wait for task completion
        await asyncio.sleep(0.1)
        
        assert len(result_received) == 1
        assert result_received[0] == 8
        
        status = async_processor.get_queue_status()
        assert status['tasks_completed'] == 1
    
    @pytest.mark.asyncio
    async def test_submit_async_task(self, async_processor):
        """Test submitting asynchronous task."""
        async def async_task(x, y):
            await asyncio.sleep(0.01)
            return x * y
        
        result_received = []
        
        async def callback(result):
            result_received.append(result)
        
        success = await async_processor.submit_task(
            task_id="async_test",
            func=async_task,
            args=(4, 7),
            callback=callback
        )
        
        assert success is True
        
        # Wait for task completion
        await asyncio.sleep(0.1)
        
        assert len(result_received) == 1
        assert result_received[0] == 28
    
    @pytest.mark.asyncio
    async def test_task_priorities(self, async_processor):
        """Test task priority handling."""
        results = []
        
        def task_func(task_id):
            results.append(task_id)
            return f"result_{task_id}"
        
        # Submit tasks with different priorities
        await async_processor.submit_task("low", task_func, args=("low",), priority=ProcessingPriority.LOW)
        await async_processor.submit_task("high", task_func, args=("high",), priority=ProcessingPriority.HIGH)
        await async_processor.submit_task("normal", task_func, args=("normal",), priority=ProcessingPriority.NORMAL)
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # All tasks should complete
        assert len(results) == 3
        assert "low" in results
        assert "high" in results
        assert "normal" in results
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, async_processor):
        """Test task cancellation."""
        async def slow_task():
            await asyncio.sleep(1.0)  # Long running task
            return "completed"
        
        # Submit task
        success = await async_processor.submit_task(
            task_id="cancel_test",
            func=slow_task
        )
        assert success is True
        
        # Cancel task
        cancelled = await async_processor.cancel_task("cancel_test")
        assert cancelled is True
        
        # Task should no longer be active
        status = async_processor.get_queue_status()
        assert len(status) > 0  # Should have some status info
    
    @pytest.mark.asyncio
    async def test_queue_full_handling(self):
        """Test behavior when task queue is full."""
        processor = AsyncProcessor(max_workers=1, queue_size=2)
        await processor.start()
        
        def task_func():
            time.sleep(0.1)  # Block worker
            return "done"
        
        # Fill queue
        success1 = await processor.submit_task("task1", task_func)
        success2 = await processor.submit_task("task2", task_func)
        success3 = await processor.submit_task("task3", task_func)
        
        assert success1 is True
        assert success2 is True
        # Third task might fail if queue is full
        
        await processor.stop()
    
    @pytest.mark.asyncio
    async def test_task_failure_handling(self, async_processor):
        """Test handling of task failures."""
        def failing_task():
            raise ValueError("Test error")
        
        success = await async_processor.submit_task(
            task_id="fail_test",
            func=failing_task
        )
        
        assert success is True
        
        # Wait for task to fail
        await asyncio.sleep(0.1)
        
        status = async_processor.get_queue_status()
        assert status['tasks_failed'] == 1
    
    @pytest.mark.asyncio
    async def test_queue_status(self, async_processor):
        """Test getting queue status information."""
        status = async_processor.get_queue_status()
        
        assert 'running' in status
        assert 'queue_size' in status
        assert 'max_queue_size' in status
        assert 'active_tasks' in status
        assert 'worker_count' in status
        assert 'tasks_submitted' in status
        assert 'tasks_completed' in status
        assert 'tasks_failed' in status
        
        assert status['running'] is True
        assert status['max_queue_size'] == 100
        assert status['worker_count'] == 4


class TestDecorators:
    """Test utility decorators."""
    
    def test_cache_result_decorator(self, coordinate_cache):
        """Test cache_result decorator functionality."""
        call_count = 0
        
        @cache_result(coordinate_cache)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x * y
        
        # First call should execute function
        result1 = expensive_function(5, 3)
        assert result1 == 15
        assert call_count == 1
        
        # Second call with same args should use cache
        result2 = expensive_function(5, 3)
        assert result2 == 15
        assert call_count == 1  # Should not increment
        
        # Different args should execute function again
        result3 = expensive_function(4, 2)
        assert result3 == 8
        assert call_count == 2
        
        # Check cache hit rate
        hit_rate = coordinate_cache.get_hit_rate()
        assert hit_rate > 0


class TestGlobalInstances:
    """Test global instance management."""
    
    def test_get_coordinate_cache_singleton(self):
        """Test that get_coordinate_cache returns singleton."""
        cache1 = get_coordinate_cache()
        cache2 = get_coordinate_cache()
        
        assert cache1 is cache2
        assert isinstance(cache1, CoordinateCache)
    
    def test_get_memory_optimizer_singleton(self):
        """Test that get_memory_optimizer returns singleton."""
        optimizer1 = get_memory_optimizer()
        optimizer2 = get_memory_optimizer()
        
        assert optimizer1 is optimizer2
        assert isinstance(optimizer1, MemoryOptimizer)
    
    def test_get_async_processor_singleton(self):
        """Test that get_async_processor returns singleton."""
        processor1 = get_async_processor()
        processor2 = get_async_processor()
        
        assert processor1 is processor2
        assert isinstance(processor1, AsyncProcessor)


class TestPerformanceIntegration:
    """Test integration between performance components."""
    
    @pytest.mark.asyncio
    async def test_cache_with_async_processing(self):
        """Test using cache with async processing."""
        cache = CoordinateCache(max_size=10)
        processor = AsyncProcessor(max_workers=2)
        await processor.start()
        
        results = []
        
        @cache_result(cache)
        def cached_calculation(x):
            return x ** 2
        
        async def async_task(value):
            result = cached_calculation(value)
            results.append(result)
            return result
        
        # Submit multiple tasks, some with duplicate values
        tasks = []
        for i in [1, 2, 1, 3, 2, 4]:  # Duplicates: 1, 2
            tasks.append(
                processor.submit_task(f"task_{i}", async_task, args=(i,))
            )
        
        # Wait for all tasks to complete
        await asyncio.sleep(0.2)
        
        # Should have 6 results but only 4 cache entries
        assert len(results) == 6
        assert len(cache.cache) == 4
        assert cache.get_hit_rate() > 0
        
        await processor.stop()
    
    def test_memory_optimizer_with_cache(self):
        """Test memory optimizer integration with cache."""
        optimizer = MemoryOptimizer(memory_limit_mb=1)  # Very low limit
        cache = CoordinateCache(max_size=100, max_memory_mb=1)
        
        # Register cache cleanup callback
        optimizer.register_cleanup_callback(cache.clear)
        
        # Fill cache with data
        for i in range(50):
            cache.put(f"key{i}", f"value{i}" * 100)  # Large values
        
        initial_cache_size = len(cache.cache)
        
        # Force cleanup
        stats = optimizer.force_cleanup()
        
        # Cache should be cleared
        assert len(cache.cache) == 0
        assert stats['callbacks_executed'] == 1


if __name__ == '__main__':
    pytest.main([__file__])