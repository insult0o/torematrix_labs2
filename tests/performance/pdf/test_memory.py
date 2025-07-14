"""
Memory Management Tests for PDF.js Performance Optimization.

This module tests the memory management system including memory pools,
cache management, and memory pressure handling.
"""
import pytest
import time
import gc
import threading
from unittest.mock import Mock, patch, MagicMock
from collections import OrderedDict

from src.torematrix.integrations.pdf.memory import (
    MemoryManager, MemoryPool, MemoryStats, MemoryPressureLevel
)
from src.torematrix.integrations.pdf.performance import PerformanceConfig


class TestMemoryPool:
    """Test memory pool functionality."""
    
    def test_memory_pool_initialization(self):
        """Test memory pool initialization."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        assert pool.block_size == 1024
        assert pool.max_blocks == 10
        assert len(pool.available_blocks) == 0
        assert len(pool.allocated_blocks) == 0
        assert pool.next_id == 0
    
    def test_memory_allocation(self):
        """Test memory allocation."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Allocate memory
        block_id, block = pool.allocate(512)
        
        assert isinstance(block_id, int)
        assert isinstance(block, bytearray)
        assert len(block) == 1024  # Should use standard block size
        assert block_id in pool.allocated_blocks
        assert pool.allocations == 1
        assert pool.pool_misses == 1
    
    def test_memory_deallocation(self):
        """Test memory deallocation."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Allocate and deallocate
        block_id, block = pool.allocate(512)
        success = pool.deallocate(block_id)
        
        assert success
        assert block_id not in pool.allocated_blocks
        assert len(pool.available_blocks) == 1  # Should be returned to pool
        assert pool.deallocations == 1
    
    def test_memory_pool_reuse(self):
        """Test memory pool reuse."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Allocate and deallocate to populate pool
        block_id, block = pool.allocate(512)
        pool.deallocate(block_id)
        
        # Allocate again - should reuse from pool
        block_id2, block2 = pool.allocate(512)
        
        assert pool.pool_hits == 1
        assert len(pool.available_blocks) == 0  # Block taken from pool
        assert len(pool.allocated_blocks) == 1
    
    def test_large_allocation(self):
        """Test large allocation that exceeds block size."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Allocate larger than block size
        block_id, block = pool.allocate(2048)
        
        assert len(block) == 2048  # Should create exact size
        assert block_id in pool.allocated_blocks
        
        # Deallocate - should not be returned to pool
        pool.deallocate(block_id)
        assert len(pool.available_blocks) == 0  # Too large for pool
    
    def test_pool_statistics(self):
        """Test pool statistics."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Perform some operations
        block_id1, _ = pool.allocate(512)
        block_id2, _ = pool.allocate(512)
        pool.deallocate(block_id1)
        block_id3, _ = pool.allocate(512)  # Should hit pool
        
        stats = pool.get_statistics()
        
        assert stats['allocations'] == 3
        assert stats['deallocations'] == 1
        assert stats['pool_hits'] == 1
        assert stats['pool_misses'] == 2
        assert stats['hit_rate'] == 1/3  # 1 hit out of 3 allocations
    
    def test_cleanup_old_blocks(self):
        """Test cleanup of old allocated blocks."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        
        # Allocate blocks and set old timestamps
        block_id1, _ = pool.allocate(512)
        block_id2, _ = pool.allocate(512)
        
        # Make one block old
        pool.block_usage[block_id1] = time.time() - 400  # 400 seconds ago
        
        # Cleanup blocks older than 300 seconds
        cleaned = pool.cleanup_old_blocks(max_age_seconds=300)
        
        assert cleaned == 1
        assert block_id1 not in pool.allocated_blocks
        assert block_id2 in pool.allocated_blocks
    
    def test_pool_capacity_limits(self):
        """Test pool capacity limits."""
        pool = MemoryPool(block_size=1024, max_blocks=2)
        
        # Fill pool to capacity
        block_id1, _ = pool.allocate(512)
        block_id2, _ = pool.allocate(512)
        block_id3, _ = pool.allocate(512)
        
        pool.deallocate(block_id1)
        pool.deallocate(block_id2)
        pool.deallocate(block_id3)
        
        # Should only have 2 blocks in pool due to max_blocks limit
        assert len(pool.available_blocks) == 2
    
    def test_thread_safety(self):
        """Test thread safety of memory pool."""
        pool = MemoryPool(block_size=1024, max_blocks=10)
        results = []
        
        def allocate_and_deallocate():
            for i in range(10):
                block_id, block = pool.allocate(512)
                results.append(block_id)
                pool.deallocate(block_id)
        
        # Run concurrent allocations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=allocate_and_deallocate)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Check that all operations completed
        assert len(results) == 30  # 3 threads * 10 operations each
        assert len(set(results)) == 30  # All IDs should be unique


class TestMemoryManager:
    """Test memory manager functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(
            cache_size_mb=100,
            memory_pressure_threshold=0.8,
            gc_threshold_mb=50
        )
    
    @pytest.fixture
    def memory_manager(self, config):
        """Create test memory manager."""
        manager = MemoryManager(config)
        
        # Mock process to avoid system dependencies
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=50 * 1024 * 1024)  # 50MB
        mock_process.cpu_percent.return_value = 25.0
        manager.process = mock_process
        
        # Mock system memory
        manager.system_memory = Mock()
        manager.system_memory.total = 8 * 1024 * 1024 * 1024  # 8GB
        manager.system_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
        
        return manager
    
    def test_memory_manager_initialization(self, memory_manager):
        """Test memory manager initialization."""
        assert memory_manager.config is not None
        assert len(memory_manager.memory_pools) == 3  # small, medium, large
        assert len(memory_manager.page_cache) == 0
        assert len(memory_manager.page_access_times) == 0
        assert memory_manager.cleanup_timer is not None
    
    def test_memory_pool_selection(self, memory_manager):
        """Test memory pool selection based on size."""
        # Test small pool selection
        pool_name = memory_manager._choose_memory_pool(32 * 1024)  # 32KB
        assert pool_name == 'small'
        
        # Test medium pool selection
        pool_name = memory_manager._choose_memory_pool(512 * 1024)  # 512KB
        assert pool_name == 'medium'
        
        # Test large pool selection
        pool_name = memory_manager._choose_memory_pool(2 * 1024 * 1024)  # 2MB
        assert pool_name == 'large'
    
    def test_page_memory_allocation(self, memory_manager):
        """Test page memory allocation."""
        # Allocate memory for a page
        result = memory_manager.allocate_page_memory(1, 1024 * 1024)  # 1MB
        
        assert result is not None
        block_id, block = result
        assert isinstance(block_id, int)
        assert isinstance(block, bytearray)
        assert 1 in memory_manager.page_memory_usage
        assert 1 in memory_manager.page_access_times
        assert 1 in memory_manager.weak_references
    
    def test_page_memory_deallocation(self, memory_manager):
        """Test page memory deallocation."""
        # Allocate then deallocate
        result = memory_manager.allocate_page_memory(1, 1024 * 1024)
        assert result is not None
        
        block_id, block = result
        success = memory_manager.deallocate_page_memory(1, block_id)
        
        assert success
        assert 1 not in memory_manager.page_memory_usage
        assert 1 not in memory_manager.page_access_times
        assert 1 not in memory_manager.weak_references
    
    def test_page_cache_operations(self, memory_manager):
        """Test page cache operations."""
        # Add page to cache
        page_data = {'content': 'test page', 'rendered': True}
        memory_manager.add_page_to_cache(1, page_data)
        
        assert 1 in memory_manager.page_cache
        assert memory_manager.page_cache[1] == page_data
        assert 1 in memory_manager.page_access_times
        
        # Get page from cache
        retrieved_data = memory_manager.get_page_from_cache(1)
        assert retrieved_data == page_data
        
        # Remove page from cache
        success = memory_manager.remove_page_from_cache(1)
        assert success
        assert 1 not in memory_manager.page_cache
        assert 1 not in memory_manager.page_access_times
    
    def test_lru_eviction(self, memory_manager):
        """Test LRU eviction strategy."""
        # Add pages to cache
        for i in range(10):
            page_data = {'content': f'page {i}', 'size': 1024}
            memory_manager.add_page_to_cache(i, page_data)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Make some pages older
        for i in range(5):
            memory_manager.page_access_times[i] = time.time() - 100
        
        # Evict 3 oldest pages
        memory_manager._evict_old_pages(3)
        
        # Check that oldest pages were evicted
        assert 0 not in memory_manager.page_cache
        assert 1 not in memory_manager.page_cache
        assert 2 not in memory_manager.page_cache
        assert 5 in memory_manager.page_cache  # Should still be present
        assert 9 in memory_manager.page_cache  # Should still be present
    
    def test_memory_pressure_calculation(self, memory_manager):
        """Test memory pressure level calculation."""
        # Test different pressure levels
        test_cases = [
            (0.5, MemoryPressureLevel.LOW),
            (0.65, MemoryPressureLevel.MEDIUM),
            (0.85, MemoryPressureLevel.HIGH),
            (0.95, MemoryPressureLevel.CRITICAL)
        ]
        
        for usage_percent, expected_level in test_cases:
            level = memory_manager._calculate_pressure_level(usage_percent)
            assert level == expected_level
    
    def test_memory_stats_collection(self, memory_manager):
        """Test memory statistics collection."""
        # Add some cached pages
        for i in range(5):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Update memory stats
        memory_manager._update_memory_stats()
        stats = memory_manager.get_memory_stats()
        
        assert isinstance(stats, MemoryStats)
        assert stats.total_memory_mb > 0
        assert stats.used_memory_mb > 0
        assert stats.available_memory_mb > 0
        assert isinstance(stats.pressure_level, MemoryPressureLevel)
    
    def test_cleanup_operations(self, memory_manager):
        """Test cleanup operations."""
        # Add pages with different ages
        for i in range(10):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
            
            # Make some pages old
            if i < 5:
                memory_manager.page_access_times[i] = time.time() - 400
        
        # Test cleanup old pages
        cleaned = memory_manager.cleanup_old_pages(max_age_seconds=300)
        assert cleaned == 5  # Should clean 5 old pages
        
        # Test emergency cleanup
        cleanup_stats = memory_manager.emergency_cleanup()
        assert isinstance(cleanup_stats, dict)
        assert 'pages_cleaned' in cleanup_stats
        assert 'pool_blocks_freed' in cleanup_stats
        assert 'gc_collections' in cleanup_stats
    
    def test_memory_leak_detection(self, memory_manager):
        """Test memory leak detection."""
        # Add pages and simulate some being leaked
        for i in range(10):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
            
            # Simulate old access times for some pages
            if i < 5:
                memory_manager.page_access_times[i] = time.time() - 400
        
        # Count leaked objects
        leaked_count = memory_manager._count_leaked_objects()
        assert leaked_count == 5  # Should detect 5 potentially leaked objects
    
    def test_scheduled_cleanup(self, memory_manager):
        """Test scheduled cleanup based on pressure levels."""
        # Mock cleanup methods
        memory_manager.emergency_cleanup = Mock(return_value={'pages_cleaned': 5})
        memory_manager.cleanup_old_pages = Mock(return_value=3)
        
        # Test cleanup for different pressure levels
        test_cases = [
            (MemoryPressureLevel.CRITICAL, 'emergency_cleanup'),
            (MemoryPressureLevel.HIGH, 'cleanup_old_pages'),
            (MemoryPressureLevel.MEDIUM, 'cleanup_old_pages'),
            (MemoryPressureLevel.LOW, 'cleanup_old_pages')
        ]
        
        for pressure_level, expected_method in test_cases:
            memory_manager.current_stats.pressure_level = pressure_level
            memory_manager._perform_scheduled_cleanup()
            
            if expected_method == 'emergency_cleanup':
                memory_manager.emergency_cleanup.assert_called()
            else:
                memory_manager.cleanup_old_pages.assert_called()
    
    def test_cache_statistics(self, memory_manager):
        """Test cache statistics."""
        # Add pages with different sizes
        for i in range(5):
            page_data = {'content': f'page {i}' * 100}  # Variable size
            memory_manager.add_page_to_cache(i, page_data)
            memory_manager.page_memory_usage[i] = (i + 1) * 0.5  # MB
        
        # Get cache statistics
        stats = memory_manager.get_cache_stats()
        
        assert stats['cached_pages'] == 5
        assert stats['total_cache_memory_mb'] == 7.5  # 0.5 + 1.0 + 1.5 + 2.0 + 2.5
        assert stats['average_page_size_mb'] == 1.5
        assert stats['oldest_page_age'] >= 0
        assert stats['newest_page_age'] >= 0
    
    def test_pool_statistics(self, memory_manager):
        """Test memory pool statistics."""
        # Perform some operations on pools
        memory_manager.allocate_page_memory(1, 32 * 1024)    # small pool
        memory_manager.allocate_page_memory(2, 512 * 1024)   # medium pool
        memory_manager.allocate_page_memory(3, 2 * 1024 * 1024)  # large pool
        
        # Get pool statistics
        stats = memory_manager.get_pool_stats()
        
        assert 'small' in stats
        assert 'medium' in stats
        assert 'large' in stats
        
        # Check that small pool has activity
        assert stats['small']['allocated_blocks'] > 0
        assert stats['medium']['allocated_blocks'] > 0
        assert stats['large']['allocated_blocks'] > 0
    
    def test_config_updates(self, memory_manager):
        """Test configuration updates."""
        # Create new config
        new_config = PerformanceConfig(
            cache_size_mb=200,
            memory_pressure_threshold=0.9,
            gc_threshold_mb=100
        )
        
        # Update config
        memory_manager.update_config(new_config)
        
        assert memory_manager.config.cache_size_mb == 200
        assert memory_manager.config.memory_pressure_threshold == 0.9
        assert memory_manager.config.gc_threshold_mb == 100
        
        # Check that thresholds were updated
        assert memory_manager.pressure_thresholds[MemoryPressureLevel.HIGH] == 0.9
    
    def test_memory_manager_lifecycle(self, memory_manager):
        """Test memory manager lifecycle."""
        # Start memory manager
        memory_manager.start()
        assert memory_manager.cleanup_timer.isActive()
        
        # Add some data
        for i in range(3):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Stop memory manager
        memory_manager.stop()
        assert not memory_manager.cleanup_timer.isActive()
        
        # Cleanup
        memory_manager.cleanup()
        assert len(memory_manager.page_cache) == 0
        assert len(memory_manager.page_access_times) == 0
        assert len(memory_manager.page_memory_usage) == 0
    
    def test_memory_usage_tracking(self, memory_manager):
        """Test memory usage tracking."""
        # Track memory usage for different operations
        initial_usage = memory_manager.page_memory_usage.copy()
        
        # Allocate memory for pages
        for i in range(5):
            size = (i + 1) * 1024 * 1024  # 1MB, 2MB, 3MB, 4MB, 5MB
            memory_manager.allocate_page_memory(i, size)
        
        # Check memory usage tracking
        assert len(memory_manager.page_memory_usage) == 5
        assert memory_manager.page_memory_usage[0] == 1.0  # 1MB
        assert memory_manager.page_memory_usage[4] == 5.0  # 5MB
        
        # Deallocate some memory
        memory_manager.deallocate_page_memory(0, 0)  # Mock block_id
        memory_manager.deallocate_page_memory(1, 1)  # Mock block_id
        
        # Check that usage tracking was updated
        assert 0 not in memory_manager.page_memory_usage
        assert 1 not in memory_manager.page_memory_usage
        assert 2 in memory_manager.page_memory_usage


class TestMemoryIntegration:
    """Test memory system integration scenarios."""
    
    def test_high_memory_pressure_scenario(self):
        """Test high memory pressure scenario."""
        config = PerformanceConfig(
            cache_size_mb=50,
            memory_pressure_threshold=0.7
        )
        memory_manager = MemoryManager(config)
        
        # Mock high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=200 * 1024 * 1024)  # 200MB
        mock_process.cpu_percent.return_value = 80.0
        memory_manager.process = mock_process
        
        # Add many pages to trigger pressure
        for i in range(100):
            page_data = {'content': f'large page {i}' * 1000}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Update memory stats
        memory_manager._update_memory_stats()
        stats = memory_manager.get_memory_stats()
        
        # Should detect high pressure
        assert stats.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]
        
        # Should have limited cache size due to eviction
        assert len(memory_manager.page_cache) < 100
    
    def test_concurrent_memory_operations(self):
        """Test concurrent memory operations."""
        config = PerformanceConfig(cache_size_mb=100)
        memory_manager = MemoryManager(config)
        
        # Mock process
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=50 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 25.0
        memory_manager.process = mock_process
        
        results = []
        errors = []
        
        def worker_function(worker_id):
            try:
                for i in range(10):
                    page_num = worker_id * 10 + i
                    page_data = {'content': f'worker {worker_id} page {i}'}
                    
                    # Add to cache
                    memory_manager.add_page_to_cache(page_num, page_data)
                    
                    # Allocate memory
                    result = memory_manager.allocate_page_memory(page_num, 1024 * 1024)
                    if result:
                        results.append((worker_id, page_num, result[0]))
                    
                    # Small delay
                    time.sleep(0.001)
                    
                    # Cleanup some entries
                    if i % 3 == 0:
                        memory_manager.remove_page_from_cache(page_num)
                        if result:
                            memory_manager.deallocate_page_memory(page_num, result[0])
                            
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run concurrent workers
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker_function, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0  # No errors should occur
        assert len(results) > 0  # Some operations should succeed
        
        # Check that memory structures are consistent
        assert len(memory_manager.page_cache) >= 0
        assert len(memory_manager.page_memory_usage) >= 0
    
    def test_memory_fragmentation_handling(self):
        """Test memory fragmentation handling."""
        config = PerformanceConfig(cache_size_mb=100)
        memory_manager = MemoryManager(config)
        
        # Allocate and deallocate memory in fragmented pattern
        allocated_blocks = []
        
        # Phase 1: Allocate many small blocks
        for i in range(20):
            result = memory_manager.allocate_page_memory(i, 64 * 1024)  # 64KB
            if result:
                allocated_blocks.append((i, result[0]))
        
        # Phase 2: Deallocate every other block
        for i in range(0, 20, 2):
            memory_manager.deallocate_page_memory(i, allocated_blocks[i][1])
        
        # Phase 3: Allocate larger blocks
        large_blocks = []
        for i in range(20, 25):
            result = memory_manager.allocate_page_memory(i, 256 * 1024)  # 256KB
            if result:
                large_blocks.append((i, result[0]))
        
        # Check pool statistics
        pool_stats = memory_manager.get_pool_stats()
        
        # Should have activity in pools
        assert pool_stats['small']['allocations'] > 0
        assert pool_stats['medium']['allocations'] > 0
        
        # Should have some fragmentation handling
        assert pool_stats['small']['deallocations'] > 0
    
    def test_memory_monitoring_integration(self):
        """Test memory monitoring integration."""
        config = PerformanceConfig(
            cache_size_mb=100,
            memory_pressure_threshold=0.8
        )
        memory_manager = MemoryManager(config)
        
        # Mock process with varying memory usage
        mock_process = Mock()
        memory_manager.process = mock_process
        
        # Track memory changes over time
        memory_history = []
        
        memory_levels = [50, 75, 90, 110, 95, 70, 60]  # MB
        
        for memory_mb in memory_levels:
            mock_process.memory_info.return_value = Mock(rss=memory_mb * 1024 * 1024)
            
            # Update stats
            memory_manager._update_memory_stats()
            stats = memory_manager.get_memory_stats()
            
            memory_history.append({
                'memory_mb': memory_mb,
                'pressure_level': stats.pressure_level,
                'usage_percent': stats.usage_percent
            })
        
        # Check that pressure levels changed appropriately
        pressure_changes = [entry['pressure_level'] for entry in memory_history]
        
        # Should have different pressure levels
        assert len(set(pressure_changes)) > 1
        
        # Should detect high pressure at 110MB
        high_pressure_entry = memory_history[3]  # 110MB
        assert high_pressure_entry['pressure_level'] in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]
    
    def test_memory_optimization_cascade(self):
        """Test memory optimization cascade effects."""
        config = PerformanceConfig(
            cache_size_mb=50,
            memory_pressure_threshold=0.7
        )
        memory_manager = MemoryManager(config)
        
        # Mock process with high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=150 * 1024 * 1024)  # 150MB
        mock_process.cpu_percent.return_value = 70.0
        memory_manager.process = mock_process
        
        # Add pages to cache
        for i in range(50):
            page_data = {'content': f'page {i}' * 100}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Perform emergency cleanup
        cleanup_stats = memory_manager.emergency_cleanup()
        
        # Check cleanup effects
        assert cleanup_stats['pages_cleaned'] > 0
        assert cleanup_stats['gc_collections'] >= 0
        
        # Cache should be reduced
        assert len(memory_manager.page_cache) < 50
        
        # Memory usage should be lower
        cache_stats = memory_manager.get_cache_stats()
        assert cache_stats['total_cache_memory_mb'] < 50  # Should be less than before


if __name__ == '__main__':
    pytest.main([__file__, '-v'])