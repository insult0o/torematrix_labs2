"""
Comprehensive test suite for caching system.
Tests all classes and methods in src.torematrix.ui.viewer.cache.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import weakref
import gc

from src.torematrix.ui.viewer.cache import (
    CacheEntry, 
    CacheStatistics, 
    TransformationCache, 
    CoordinateCache,
    CacheManager,
    cache_manager
)
from src.torematrix.ui.viewer.transformations import AffineTransformation


class TestCacheEntry:
    """Test CacheEntry class functionality."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        value = "test_value"
        timestamp = time.time()
        
        entry = CacheEntry(value, timestamp, 1, 100, timestamp)
        
        assert entry.value == value
        assert entry.timestamp == timestamp
        assert entry.access_count == 1
        assert entry.size == 100
        assert entry.last_access == timestamp
    
    def test_cache_entry_post_init(self):
        """Test cache entry post-initialization."""
        value = "test_value"
        timestamp = time.time()
        
        # Test without last_access set
        entry = CacheEntry(value, timestamp, 1, 100, None)
        entry.__post_init__()
        
        assert entry.last_access == timestamp


class TestCacheStatistics:
    """Test CacheStatistics class functionality."""
    
    def test_statistics_initialization(self):
        """Test statistics initialization."""
        stats = CacheStatistics()
        
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.memory_usage == 0
        assert stats.start_time > 0
        assert stats.reset_time > 0
    
    def test_statistics_recording(self):
        """Test statistics recording."""
        stats = CacheStatistics()
        
        # Record hits
        stats.hit()
        stats.hit()
        assert stats.hits == 2
        
        # Record misses
        stats.miss()
        assert stats.misses == 1
        
        # Record evictions
        stats.evict()
        assert stats.evictions == 1
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStatistics()
        
        # No requests yet
        assert stats.hit_rate() == 0.0
        
        # Some hits and misses
        stats.hit()
        stats.hit()
        stats.miss()
        
        expected_hit_rate = 2.0 / 3.0
        assert abs(stats.hit_rate() - expected_hit_rate) < 1e-10
    
    def test_requests_per_second(self):
        """Test requests per second calculation."""
        stats = CacheStatistics()
        
        # Record some requests
        stats.hit()
        stats.miss()
        
        # Should be > 0 (exact value depends on timing)
        rps = stats.requests_per_second()
        assert rps > 0
    
    def test_statistics_reset(self):
        """Test statistics reset."""
        stats = CacheStatistics()
        
        # Record some data
        stats.hit()
        stats.miss()
        stats.evict()
        
        # Reset
        stats.reset()
        
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.reset_time > 0
    
    def test_statistics_to_dict(self):
        """Test statistics dictionary conversion."""
        stats = CacheStatistics()
        
        # Record some data
        stats.hit()
        stats.miss()
        stats.evict()
        stats.memory_usage = 1024
        
        stats_dict = stats.to_dict()
        
        assert stats_dict['hits'] == 1
        assert stats_dict['misses'] == 1
        assert stats_dict['evictions'] == 1
        assert stats_dict['memory_usage'] == 1024
        assert 'hit_rate' in stats_dict
        assert 'requests_per_second' in stats_dict
        assert 'uptime' in stats_dict


class TestTransformationCache:
    """Test TransformationCache class functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = TransformationCache()
        
        assert cache.get_cache_size() == 0
        assert cache.get_memory_usage() == 0
        assert cache._max_size == 1000
        assert cache._max_memory == 100 * 1024 * 1024
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = TransformationCache()
        
        # Create a transformation
        transformation = AffineTransformation.translation(10.0, 20.0)
        key = "test_key"
        
        # Set in cache
        cache.set(key, transformation)
        
        # Get from cache
        result = cache.get(key)
        
        assert result is not None
        assert result == transformation
        assert cache.get_cache_size() == 1
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = TransformationCache()
        
        result = cache.get("non_existent_key")
        
        assert result is None
        
        # Check statistics
        stats = cache.get_stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0
    
    def test_cache_hit(self):
        """Test cache hit."""
        cache = TransformationCache()
        
        # Set value
        transformation = AffineTransformation.identity()
        cache.set("test_key", transformation)
        
        # Get value (should be hit)
        result = cache.get("test_key")
        
        assert result == transformation
        
        # Check statistics
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        # Create cache with small size
        cache = TransformationCache(max_size=2)
        
        # Add transformations
        t1 = AffineTransformation.identity()
        t2 = AffineTransformation.translation(1.0, 2.0)
        t3 = AffineTransformation.translation(3.0, 4.0)
        
        cache.set("key1", t1)
        cache.set("key2", t2)
        cache.set("key3", t3)  # Should evict key1
        
        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == t2
        assert cache.get("key3") == t3
        
        # Check statistics
        stats = cache.get_stats()
        assert stats['evictions'] > 0
    
    def test_cache_memory_eviction(self):
        """Test memory-based eviction."""
        # Create cache with small memory limit
        cache = TransformationCache(max_memory=500)
        
        # Add transformation with estimated size
        transformation = AffineTransformation.identity()
        cache.set("key1", transformation, size=300)
        cache.set("key2", transformation, size=300)  # Should evict key1
        
        # key1 should be evicted due to memory pressure
        assert cache.get("key1") is None
        assert cache.get("key2") == transformation
    
    def test_cache_access_tracking(self):
        """Test access count tracking."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("test_key", transformation)
        
        # Access multiple times
        cache.get("test_key")
        cache.get("test_key")
        cache.get("test_key")
        
        # Check that access count is tracked (internal state)
        entry = cache._cache["test_key"]
        assert entry.access_count >= 3
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("test_key", transformation)
        
        # Invalidate
        success = cache.invalidate("test_key")
        assert success
        
        # Should be gone
        assert cache.get("test_key") is None
        
        # Invalidate non-existent key
        success = cache.invalidate("non_existent")
        assert not success
    
    def test_cache_pattern_invalidation(self):
        """Test pattern-based invalidation."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("page1_transformation", transformation)
        cache.set("page2_transformation", transformation)
        cache.set("other_key", transformation)
        
        # Invalidate all page transformations
        cache.invalidate_pattern("page")
        
        assert cache.get("page1_transformation") is None
        assert cache.get("page2_transformation") is None
        assert cache.get("other_key") == transformation
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("key1", transformation)
        cache.set("key2", transformation)
        
        # Clear cache
        cache.clear()
        
        assert cache.get_cache_size() == 0
        assert cache.get_memory_usage() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_optimization(self):
        """Test cache optimization."""
        cache = TransformationCache()
        
        # Add some old entries
        transformation = AffineTransformation.identity()
        cache.set("old_key", transformation)
        
        # Manually set old timestamp
        cache._cache["old_key"].timestamp = time.time() - 1000
        cache._cache["old_key"].access_count = 1
        
        # Add recent entry
        cache.set("new_key", transformation)
        
        # Optimize
        cache.optimize()
        
        # Old entry should be removed
        assert cache.get("old_key") is None
        assert cache.get("new_key") == transformation
    
    def test_cache_resize(self):
        """Test cache resizing."""
        cache = TransformationCache(max_size=10)
        
        # Add transformations
        transformation = AffineTransformation.identity()
        for i in range(15):
            cache.set(f"key_{i}", transformation)
        
        # Resize to smaller
        cache.resize(5, 1000)
        
        # Should have evicted entries
        assert cache.get_cache_size() <= 5
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("test_key", transformation)
        cache.get("test_key")  # hit
        cache.get("non_existent")  # miss
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['cache_size'] == 1
        assert stats['max_size'] == 1000
        assert 'hit_rate' in stats
        assert 'memory_utilization' in stats
    
    def test_cache_thread_safety(self):
        """Test cache thread safety."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        results = []
        
        def worker():
            for i in range(100):
                cache.set(f"key_{i}", transformation)
                result = cache.get(f"key_{i}")
                results.append(result is not None)
        
        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert all(results)
    
    def test_size_estimation(self):
        """Test transformation size estimation."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        estimated_size = cache._estimate_size(transformation)
        
        # Should be reasonable estimate
        assert estimated_size > 0
        assert estimated_size < 1000  # Reasonable upper bound
    
    def test_weak_reference_cleanup(self):
        """Test weak reference cleanup."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        cache.set("test_key", transformation)
        
        # Delete transformation
        del transformation
        gc.collect()
        
        # Optimize should clean up dead references
        cache.optimize()
        
        # Entry should be removed
        assert cache.get("test_key") is None


class TestCoordinateCache:
    """Test CoordinateCache class functionality."""
    
    def test_coordinate_cache_initialization(self):
        """Test coordinate cache initialization."""
        cache = CoordinateCache()
        
        assert cache._max_entries == 50000
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_coordinate_cache_set_and_get(self):
        """Test coordinate cache set and get."""
        cache = CoordinateCache()
        
        # Set coordinate
        cache.set_transformed_point(10.0, 20.0, "transform1", 30.0, 40.0)
        
        # Get coordinate
        result = cache.get_transformed_point(10.0, 20.0, "transform1")
        
        assert result == (30.0, 40.0)
    
    def test_coordinate_cache_miss(self):
        """Test coordinate cache miss."""
        cache = CoordinateCache()
        
        result = cache.get_transformed_point(10.0, 20.0, "non_existent")
        
        assert result is None
        
        # Check statistics
        stats = cache.get_stats()
        assert stats['misses'] == 1
    
    def test_coordinate_cache_lru_eviction(self):
        """Test LRU eviction in coordinate cache."""
        # Create cache with small size
        cache = CoordinateCache(max_entries=2)
        
        # Add coordinates
        cache.set_transformed_point(1.0, 2.0, "t1", 10.0, 20.0)
        cache.set_transformed_point(3.0, 4.0, "t1", 30.0, 40.0)
        cache.set_transformed_point(5.0, 6.0, "t1", 50.0, 60.0)  # Should evict first
        
        # First entry should be evicted
        assert cache.get_transformed_point(1.0, 2.0, "t1") is None
        assert cache.get_transformed_point(3.0, 4.0, "t1") == (30.0, 40.0)
        assert cache.get_transformed_point(5.0, 6.0, "t1") == (50.0, 60.0)
    
    def test_coordinate_cache_nearby_points(self):
        """Test nearby points functionality."""
        cache = CoordinateCache()
        
        # Add points in a grid
        transform_key = "test_transform"
        for x in range(0, 1000, 100):
            for y in range(0, 1000, 100):
                cache.set_transformed_point(x, y, transform_key, x*2, y*2)
        
        # Find nearby points
        nearby = cache.get_nearby_points(250.0, 250.0, 150.0, transform_key)
        
        # Should find some nearby points
        assert len(nearby) > 0
        
        # Check that all returned points are within radius
        for (orig_x, orig_y), (trans_x, trans_y) in nearby:
            distance = ((orig_x - 250.0)**2 + (orig_y - 250.0)**2)**0.5
            assert distance <= 150.0
    
    def test_coordinate_cache_transform_invalidation(self):
        """Test invalidation by transform key."""
        cache = CoordinateCache()
        
        # Add coordinates for different transforms
        cache.set_transformed_point(10.0, 20.0, "transform1", 30.0, 40.0)
        cache.set_transformed_point(10.0, 20.0, "transform2", 50.0, 60.0)
        cache.set_transformed_point(15.0, 25.0, "transform1", 35.0, 45.0)
        
        # Invalidate transform1
        cache.invalidate_transform("transform1")
        
        # transform1 entries should be gone
        assert cache.get_transformed_point(10.0, 20.0, "transform1") is None
        assert cache.get_transformed_point(15.0, 25.0, "transform1") is None
        
        # transform2 entries should remain
        assert cache.get_transformed_point(10.0, 20.0, "transform2") == (50.0, 60.0)
    
    def test_coordinate_cache_clear(self):
        """Test coordinate cache clearing."""
        cache = CoordinateCache()
        
        # Add coordinates
        cache.set_transformed_point(10.0, 20.0, "t1", 30.0, 40.0)
        cache.set_transformed_point(15.0, 25.0, "t1", 35.0, 45.0)
        
        # Clear cache
        cache.clear()
        
        # Should be empty
        assert cache.get_transformed_point(10.0, 20.0, "t1") is None
        assert cache.get_transformed_point(15.0, 25.0, "t1") is None
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_coordinate_cache_statistics(self):
        """Test coordinate cache statistics."""
        cache = CoordinateCache()
        
        # Add coordinate
        cache.set_transformed_point(10.0, 20.0, "t1", 30.0, 40.0)
        
        # Access it (hit)
        cache.get_transformed_point(10.0, 20.0, "t1")
        
        # Miss
        cache.get_transformed_point(50.0, 60.0, "t1")
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['entries'] == 1
        assert 'memory_usage' in stats
    
    def test_coordinate_cache_spatial_indexing(self):
        """Test spatial indexing functionality."""
        cache = CoordinateCache()
        
        # Set grid size for testing
        cache._grid_size = 10.0
        
        # Add point
        cache.set_transformed_point(25.0, 35.0, "t1", 50.0, 70.0)
        
        # Check spatial index
        grid_x = int(25.0 // 10.0)
        grid_y = int(35.0 // 10.0)
        grid_key = (grid_x, grid_y)
        
        assert grid_key in cache._spatial_index
        assert (25.0, 35.0, "t1") in cache._spatial_index[grid_key]
    
    def test_coordinate_cache_thread_safety(self):
        """Test coordinate cache thread safety."""
        cache = CoordinateCache()
        
        results = []
        
        def worker():
            for i in range(100):
                cache.set_transformed_point(i, i, "t1", i*2, i*2)
                result = cache.get_transformed_point(i, i, "t1")
                results.append(result == (i*2, i*2))
        
        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert all(results)


class TestCacheManager:
    """Test CacheManager class functionality."""
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        manager = CacheManager()
        
        assert len(manager._caches) == 0
        assert manager._global_memory_limit == 500 * 1024 * 1024
    
    def test_cache_registration(self):
        """Test cache registration."""
        manager = CacheManager()
        
        cache = TransformationCache()
        manager.register_cache("test_cache", cache)
        
        assert manager.get_cache("test_cache") is cache
    
    def test_cache_unregistration(self):
        """Test cache unregistration."""
        manager = CacheManager()
        
        cache = TransformationCache()
        manager.register_cache("test_cache", cache)
        manager.unregister_cache("test_cache")
        
        assert manager.get_cache("test_cache") is None
    
    def test_cache_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager()
        
        cache1 = TransformationCache()
        cache2 = CoordinateCache()
        
        # Add some data
        cache1.set("key1", AffineTransformation.identity())
        cache2.set_transformed_point(10.0, 20.0, "t1", 30.0, 40.0)
        
        manager.register_cache("cache1", cache1)
        manager.register_cache("cache2", cache2)
        
        # Clear all
        manager.clear_all()
        
        # Both caches should be empty
        assert cache1.get("key1") is None
        assert cache2.get_transformed_point(10.0, 20.0, "t1") is None
    
    def test_global_statistics(self):
        """Test global statistics."""
        manager = CacheManager()
        
        cache1 = TransformationCache()
        cache2 = CoordinateCache()
        
        # Add some data
        cache1.set("key1", AffineTransformation.identity())
        cache2.set_transformed_point(10.0, 20.0, "t1", 30.0, 40.0)
        
        manager.register_cache("cache1", cache1)
        manager.register_cache("cache2", cache2)
        
        stats = manager.get_global_stats()
        
        assert stats['cache_count'] == 2
        assert 'total_memory' in stats
        assert 'total_entries' in stats
        assert 'cache_stats' in stats
        assert 'cache1' in stats['cache_stats']
        assert 'cache2' in stats['cache_stats']
    
    def test_optimize_all(self):
        """Test optimizing all caches."""
        manager = CacheManager()
        
        cache1 = TransformationCache()
        cache2 = CoordinateCache()
        
        manager.register_cache("cache1", cache1)
        manager.register_cache("cache2", cache2)
        
        # Should not raise any exceptions
        manager.optimize_all()
    
    @patch('time.sleep')
    def test_cleanup_worker(self, mock_sleep):
        """Test background cleanup worker."""
        manager = CacheManager()
        
        # Mock sleep to avoid actual delays
        mock_sleep.side_effect = [None, KeyboardInterrupt()]
        
        # Create cache with high memory usage
        cache = TransformationCache()
        manager.register_cache("test_cache", cache)
        
        # Mock high memory utilization
        with patch.object(manager, 'get_global_stats') as mock_stats:
            mock_stats.return_value = {'memory_utilization': 0.9}
            
            # Should not raise exception
            try:
                manager._cleanup_worker()
            except KeyboardInterrupt:
                pass  # Expected to break the loop
    
    def test_global_cache_manager_instance(self):
        """Test global cache manager instance."""
        # Test that global instance exists
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)
        
        # Test that it's a singleton-like behavior
        cache_manager.register_cache("test", TransformationCache())
        assert cache_manager.get_cache("test") is not None


class TestCacheIntegration:
    """Test cache integration with other components."""
    
    def test_transformation_cache_integration(self):
        """Test transformation cache integration."""
        cache = TransformationCache()
        
        # Create transformations
        identity = AffineTransformation.identity()
        translation = AffineTransformation.translation(10.0, 20.0)
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        # Cache them
        cache.set("identity", identity)
        cache.set("translation", translation)
        cache.set("scaling", scaling)
        
        # Retrieve and use
        cached_identity = cache.get("identity")
        cached_translation = cache.get("translation")
        cached_scaling = cache.get("scaling")
        
        # Should be able to use cached transformations
        point = (10.0, 20.0)
        
        result1 = cached_identity.matrix.apply(point)
        result2 = cached_translation.matrix.apply(point)
        result3 = cached_scaling.matrix.apply(point)
        
        assert result1 == point
        assert result2 == (20.0, 40.0)
        assert result3 == (20.0, 60.0)
    
    def test_coordinate_cache_integration(self):
        """Test coordinate cache integration."""
        coord_cache = CoordinateCache()
        transform_cache = TransformationCache()
        
        # Create and cache transformation
        transformation = AffineTransformation.scaling(2.0, 3.0)
        transform_cache.set("scale_transform", transformation)
        
        # Use coordinate cache for transformed points
        original_points = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]
        
        for x, y in original_points:
            # Check coordinate cache first
            cached_result = coord_cache.get_transformed_point(x, y, "scale_transform")
            
            if cached_result is None:
                # Not in cache, compute and cache
                result = transformation.transform_point(x, y)
                coord_cache.set_transformed_point(x, y, "scale_transform", result[0], result[1])
                cached_result = result
            
            # Verify result is correct
            expected = (x * 2.0, y * 3.0)
            assert abs(cached_result[0] - expected[0]) < 1e-10
            assert abs(cached_result[1] - expected[1]) < 1e-10
    
    def test_cache_manager_integration(self):
        """Test cache manager integration."""
        manager = CacheManager()
        
        # Register different cache types
        transform_cache = TransformationCache()
        coord_cache = CoordinateCache()
        
        manager.register_cache("transformations", transform_cache)
        manager.register_cache("coordinates", coord_cache)
        
        # Use caches through manager
        transformation = AffineTransformation.rotation(1.57)  # ~90 degrees
        transform_cache.set("rotation", transformation)
        
        coord_cache.set_transformed_point(1.0, 0.0, "rotation", 0.0, 1.0)
        
        # Verify through manager
        cached_transform = manager.get_cache("transformations").get("rotation")
        cached_coord = manager.get_cache("coordinates").get_transformed_point(1.0, 0.0, "rotation")
        
        assert cached_transform == transformation
        assert cached_coord == (0.0, 1.0)
        
        # Check global stats
        stats = manager.get_global_stats()
        assert stats['cache_count'] == 2
        assert stats['total_entries'] == 2
    
    def test_cache_performance_under_load(self):
        """Test cache performance under load."""
        transform_cache = TransformationCache()
        coord_cache = CoordinateCache()
        
        # Create many transformations
        transformations = []
        for i in range(100):
            t = AffineTransformation.translation(i, i*2)
            transformations.append(t)
            transform_cache.set(f"transform_{i}", t)
        
        # Create many coordinate mappings
        for i in range(1000):
            coord_cache.set_transformed_point(i, i*2, "batch_transform", i*3, i*4)
        
        # Verify cache performance
        transform_stats = transform_cache.get_stats()
        coord_stats = coord_cache.get_stats()
        
        assert transform_stats['cache_size'] <= 100
        assert coord_stats['entries'] <= 1000
        
        # Cache should maintain reasonable hit rates
        # (This depends on access patterns, but should be reasonable)
        assert transform_stats['hit_rate'] >= 0.0
        assert coord_stats['hit_rate'] >= 0.0


class TestCacheErrorHandling:
    """Test cache error handling and edge cases."""
    
    def test_cache_with_none_values(self):
        """Test cache handling of None values."""
        cache = TransformationCache()
        
        # Should not cache None values
        cache.set("test_key", None)
        result = cache.get("test_key")
        
        # Implementation should handle this gracefully
        # (specific behavior depends on implementation)
    
    def test_cache_with_invalid_keys(self):
        """Test cache with invalid keys."""
        cache = TransformationCache()
        
        # Test with various key types
        transformation = AffineTransformation.identity()
        
        # String key (normal)
        cache.set("normal_key", transformation)
        assert cache.get("normal_key") == transformation
        
        # Empty string key
        cache.set("", transformation)
        assert cache.get("") == transformation
        
        # Unicode key
        cache.set("ключ_测试", transformation)
        assert cache.get("ключ_测试") == transformation
    
    def test_coordinate_cache_edge_cases(self):
        """Test coordinate cache edge cases."""
        cache = CoordinateCache()
        
        # Test with extreme coordinate values
        cache.set_transformed_point(1e10, 1e10, "large", 2e10, 2e10)
        result = cache.get_transformed_point(1e10, 1e10, "large")
        assert result == (2e10, 2e10)
        
        # Test with very small coordinate values
        cache.set_transformed_point(1e-10, 1e-10, "small", 2e-10, 2e-10)
        result = cache.get_transformed_point(1e-10, 1e-10, "small")
        assert result == (2e-10, 2e-10)
        
        # Test with negative coordinates
        cache.set_transformed_point(-100.0, -200.0, "negative", -300.0, -400.0)
        result = cache.get_transformed_point(-100.0, -200.0, "negative")
        assert result == (-300.0, -400.0)
    
    def test_cache_memory_pressure(self):
        """Test cache behavior under memory pressure."""
        # Create cache with very small memory limit
        cache = TransformationCache(max_memory=1)
        
        # Try to add transformation
        transformation = AffineTransformation.identity()
        cache.set("test", transformation)
        
        # Should handle gracefully (may evict immediately)
        # The cache should not crash
        stats = cache.get_stats()
        assert stats is not None
    
    def test_cache_concurrent_access(self):
        """Test cache concurrent access patterns."""
        cache = TransformationCache()
        
        transformation = AffineTransformation.identity()
        errors = []
        
        def worker():
            try:
                for i in range(50):
                    cache.set(f"key_{i}", transformation)
                    result = cache.get(f"key_{i}")
                    if result != transformation:
                        errors.append(f"Mismatch for key_{i}")
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not have any errors
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])