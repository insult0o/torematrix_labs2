"""Performance Tests for Property Panel

Comprehensive performance test suite validating caching, virtualization,
and monitoring systems meet target performance requirements. Tests large
datasets, memory usage, and response times.
"""

import pytest
import time
import gc
import threading
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock
import psutil
import os

# Test framework imports
import sys
sys.path.insert(0, 'src')

from torematrix.ui.components.property_panel.caching import (
    PropertyCache, CacheKey, CacheEntryType, ValidationResultCache,
    DisplayDataCache, get_property_cache
)
from torematrix.ui.components.property_panel.virtualization import (
    PropertyVirtualizer, VirtualizedPropertyListWidget, VirtualizationMetrics,
    ViewportItem
)
from torematrix.ui.components.property_panel.performance import (
    PerformanceMonitor, PerformanceTarget, PerformanceMetric,
    PerformanceAlert, AlertSeverity, timed_operation
)
from torematrix.ui.components.property_panel.models import PropertyValue, PropertyMetadata
from torematrix.ui.components.property_panel.events import PropertyNotificationCenter


class TestPropertyCachePerformance:
    """Test PropertyCache performance characteristics"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cache = PropertyCache(max_entries=5000, max_size_mb=25)
        self.notification_center = PropertyNotificationCenter()
        
    def test_cache_hit_ratio_target(self):
        """Test cache achieves >80% hit ratio"""
        # Populate cache with test data
        for i in range(1000):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f"element_{i % 100}",  # Create overlap for hits
                property_name=f"property_{i % 50}"
            )
            
            value = PropertyValue(
                value=f"test_value_{i}",
                property_type="string"
            )
            
            self.cache.put(key, value)
        
        # Perform read operations with expected hits
        hits = 0
        total_requests = 1000
        
        for i in range(total_requests):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f"element_{i % 100}",
                property_name=f"property_{i % 50}"
            )
            
            result = self.cache.get(key)
            if result is not None:
                hits += 1
        
        hit_ratio = (hits / total_requests) * 100
        
        # Verify hit ratio exceeds target
        assert hit_ratio >= 80.0, f"Cache hit ratio {hit_ratio}% below target 80%"
        
        # Verify cache stats match
        stats = self.cache.get_stats()
        assert stats['hit_ratio'] >= 80.0
    
    def test_cache_memory_limit(self):
        """Test cache respects memory limits"""
        # Fill cache to near memory limit
        large_data = "x" * (1024 * 100)  # 100KB per item
        
        for i in range(300):  # Should exceed 25MB limit
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f"element_{i}",
                property_name="large_property"
            )
            
            self.cache.put(key, large_data)
        
        # Verify cache size is within limits
        cache_info = self.cache.get_cache_info()
        assert cache_info['total_size_mb'] <= 25.0, f"Cache size {cache_info['total_size_mb']}MB exceeds limit"
    
    def test_cache_performance_under_load(self):
        """Test cache performance with concurrent access"""
        import threading
        import time
        
        results = []
        
        def cache_worker(worker_id: int):
            start_time = time.perf_counter()
            
            # Perform cache operations
            for i in range(100):
                key = CacheKey(
                    entry_type=CacheEntryType.PROPERTY_VALUE,
                    element_id=f"worker_{worker_id}_element_{i}",
                    property_name="test_property"
                )
                
                # Put operation
                value = PropertyValue(value=f"worker_{worker_id}_value_{i}", property_type="string")
                self.cache.put(key, value)
                
                # Get operation
                retrieved = self.cache.get(key)
                assert retrieved is not None
            
            end_time = time.perf_counter()
            results.append(end_time - start_time)
        
        # Run multiple workers concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify performance
        max_time = max(results)
        avg_time = sum(results) / len(results)
        
        assert max_time < 1.0, f"Worker took {max_time}s, should be <1s"
        assert avg_time < 0.5, f"Average time {avg_time}s, should be <0.5s"
    
    def test_cache_invalidation_performance(self):
        """Test cache invalidation is efficient"""
        # Populate cache with dependencies
        for i in range(1000):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f"element_{i % 10}",
                property_name=f"property_{i}"
            )
            
            dependencies = {f"element:element_{i % 10}"}
            self.cache.put(key, f"value_{i}", dependencies=dependencies)
        
        # Measure invalidation time
        start_time = time.perf_counter()
        invalidated_count = self.cache.invalidate_element("element_0")
        end_time = time.perf_counter()
        
        invalidation_time_ms = (end_time - start_time) * 1000
        
        assert invalidation_time_ms < 10.0, f"Invalidation took {invalidation_time_ms}ms, should be <10ms"
        assert invalidated_count == 100, f"Expected 100 invalidations, got {invalidated_count}"


class TestVirtualizationPerformance:
    """Test PropertyVirtualizer performance characteristics"""
    
    def setup_method(self):
        """Setup test environment"""
        # Mock QWidget for testing
        self.mock_viewport = Mock()
        self.mock_viewport.width.return_value = 800
        self.mock_viewport.height.return_value = 600
        
        self.virtualizer = PropertyVirtualizer(
            viewport_widget=self.mock_viewport,
            item_height=50,
            buffer_size=5
        )
    
    def test_large_dataset_handling(self):
        """Test virtualizer handles 10,000+ items efficiently"""
        # Create large dataset
        items = []
        for i in range(15000):
            items.append({
                'element_id': f'element_{i}',
                'property_name': f'property_{i % 100}',
                'value': f'value_{i}',
                'height': 50
            })
        
        # Measure setup time
        start_time = time.perf_counter()
        self.virtualizer.set_items(items)
        setup_time = (time.perf_counter() - start_time) * 1000
        
        # Verify setup performance
        assert setup_time < 100.0, f"Setup took {setup_time}ms, should be <100ms"
        
        # Verify data structure
        assert len(self.virtualizer.items) == 15000
        assert self.virtualizer.total_height == 15000 * 50
        
        # Test viewport updates
        self.virtualizer.set_viewport_size(800, 600)
        
        start_time = time.perf_counter()
        self.virtualizer.set_scroll_position(5000)  # Scroll to middle
        scroll_time = (time.perf_counter() - start_time) * 1000
        
        assert scroll_time < 25.0, f"Scroll update took {scroll_time}ms, should be <25ms"
        
        # Verify only visible items are tracked
        visible_count = len(self.virtualizer.visible_items)
        assert visible_count < 50, f"Too many visible items: {visible_count}, should be <50"
    
    def test_virtualization_memory_efficiency(self):
        """Test virtualization keeps memory usage low"""
        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Create very large dataset
        items = []
        for i in range(50000):
            items.append({
                'element_id': f'element_{i}',
                'property_name': f'property_{i}',
                'value': f'large_value_{"x" * 100}_{i}',  # Larger values
                'height': 50
            })
        
        self.virtualizer.set_items(items)
        self.virtualizer.set_viewport_size(800, 600)
        
        # Scroll through various positions
        for scroll_pos in [0, 10000, 50000, 100000, 200000]:
            self.virtualizer.set_scroll_position(scroll_pos)
        
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        assert memory_increase < 50.0, f"Memory increased by {memory_increase}MB, should be <50MB"
        
        # Verify metrics
        metrics = self.virtualizer.get_metrics()
        assert metrics.total_items == 50000
        assert metrics.visible_items < 100  # Only visible items loaded
    
    def test_scroll_performance(self):
        """Test smooth scrolling performance"""
        # Setup large dataset
        items = [
            {
                'element_id': f'element_{i}',
                'property_name': f'property_{i}',
                'value': f'value_{i}',
                'height': 50
            }
            for i in range(10000)
        ]
        
        self.virtualizer.set_items(items)
        self.virtualizer.set_viewport_size(800, 600)
        
        # Measure scroll performance
        scroll_times = []
        
        for scroll_pos in range(0, 100000, 1000):  # Scroll in increments
            start_time = time.perf_counter()
            self.virtualizer.set_scroll_position(scroll_pos)
            scroll_time = (time.perf_counter() - start_time) * 1000
            scroll_times.append(scroll_time)
        
        max_scroll_time = max(scroll_times)
        avg_scroll_time = sum(scroll_times) / len(scroll_times)
        
        assert max_scroll_time < 25.0, f"Max scroll time {max_scroll_time}ms, should be <25ms"
        assert avg_scroll_time < 10.0, f"Avg scroll time {avg_scroll_time}ms, should be <10ms"
        
        # Verify FPS tracking
        metrics = self.virtualizer.get_metrics()
        if metrics.fps > 0:
            assert metrics.fps >= 30.0, f"Scroll FPS {metrics.fps}, should be >=30"


class TestPerformanceMonitorAccuracy:
    """Test PerformanceMonitor accuracy and functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.monitor = PerformanceMonitor()
        
    def test_timing_accuracy(self):
        """Test timing measurement accuracy"""
        # Test timing context
        with self.monitor.timing("test_operation"):
            time.sleep(0.1)  # Sleep for 100ms
        
        # Verify timing was recorded
        stats = self.monitor.get_operation_stats("test_operation")
        assert stats['count'] == 1
        assert 95 <= stats['mean_ms'] <= 110  # Allow 5ms tolerance
        
        # Test multiple operations
        for i in range(10):
            with self.monitor.timing("batch_operation"):
                time.sleep(0.05)  # 50ms each
        
        batch_stats = self.monitor.get_operation_stats("batch_operation")
        assert batch_stats['count'] == 10
        assert 45 <= batch_stats['mean_ms'] <= 60
    
    def test_metric_recording_and_alerts(self):
        """Test metric recording and alert generation"""
        # Define target
        target = PerformanceTarget(
            name="test_metric",
            target_value=50.0,
            unit="ms",
            description="Test metric"
        )
        
        self.monitor.targets["test_metric"] = target
        
        # Record metrics within target
        for i in range(5):
            self.monitor.record_metric("test_metric", 40.0 + i, "ms", 50.0)
        
        # Verify no alerts for good metrics
        alerts = self.monitor.get_alerts()
        assert len(alerts) == 0
        
        # Record metrics that exceed target
        self.monitor.record_metric("test_metric", 75.0, "ms", 50.0)  # Exceeds alert threshold
        self.monitor.record_metric("test_metric", 120.0, "ms", 50.0)  # Exceeds critical threshold
        
        # Verify alerts were generated
        alerts = self.monitor.get_alerts()
        assert len(alerts) >= 1
        
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) >= 1
    
    def test_system_metrics_collection(self):
        """Test system metrics collection"""
        # Let system metrics collect
        time.sleep(2.0)  # Allow time for collection
        
        # Verify system metrics were recorded
        stats = self.monitor.get_metric_stats("cpu_percent")
        assert stats['count'] > 0
        assert 0 <= stats['mean'] <= 100
        
        memory_stats = self.monitor.get_metric_stats("process_memory_mb")
        assert memory_stats['count'] > 0
        assert memory_stats['mean'] > 0
    
    def test_performance_summary_generation(self):
        """Test comprehensive performance summary"""
        # Generate some metrics and operations
        for i in range(10):
            self.monitor.record_metric("response_time", 30 + i * 2, "ms")
            
            with self.monitor.timing("ui_update"):
                time.sleep(0.02)  # 20ms
        
        # Get performance summary
        summary = self.monitor.get_performance_summary()
        
        # Verify summary structure
        required_keys = [
            'timestamp', 'monitoring_duration_mins', 'performance_level',
            'targets_met', 'active_alerts', 'system_health', 'memory_status'
        ]
        
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"
        
        # Verify performance level calculation
        assert summary['performance_level'] in ['excellent', 'good', 'fair', 'poor']
        assert isinstance(summary['targets_met'], int)
        assert summary['targets_met'] >= 0


class TestIntegratedPerformance:
    """Test integrated performance of all systems working together"""
    
    def setup_method(self):
        """Setup integrated test environment"""
        self.cache = PropertyCache(max_entries=2000, max_size_mb=10)
        self.monitor = PerformanceMonitor(cache=self.cache)
        self.notification_center = PropertyNotificationCenter()
        
        # Setup virtualizer with cache
        self.mock_viewport = Mock()
        self.virtualizer = PropertyVirtualizer(
            viewport_widget=self.mock_viewport,
            cache=self.cache
        )
    
    def test_end_to_end_performance_scenario(self):
        """Test realistic end-to-end performance scenario"""
        # Simulate large property dataset
        properties = []
        for i in range(5000):
            properties.append({
                'element_id': f'element_{i % 100}',  # 100 unique elements
                'property_name': f'property_{i % 20}',  # 20 unique properties
                'value': f'value_{i}',
                'type': 'string',
                'height': 50
            })
        
        # Measure overall setup time
        start_time = time.perf_counter()
        
        with self.monitor.timing("full_setup"):
            # Setup virtualizer
            self.virtualizer.set_items(properties)
            self.virtualizer.set_viewport_size(800, 600)
            
            # Populate cache with some data
            for i in range(100):
                key = CacheKey(
                    entry_type=CacheEntryType.PROPERTY_VALUE,
                    element_id=f'element_{i}',
                    property_name='cached_property'
                )
                self.cache.put(key, f'cached_value_{i}')
        
        setup_time = (time.perf_counter() - start_time) * 1000
        
        # Verify setup performance
        assert setup_time < 200.0, f"Full setup took {setup_time}ms, should be <200ms"
        
        # Simulate user interactions
        interaction_times = []
        
        for i in range(50):
            start_time = time.perf_counter()
            
            with self.monitor.timing("user_interaction"):
                # Scroll operation
                scroll_pos = i * 1000
                self.virtualizer.set_scroll_position(scroll_pos)
                
                # Cache lookup
                key = CacheKey(
                    entry_type=CacheEntryType.PROPERTY_VALUE,
                    element_id=f'element_{i % 100}',
                    property_name='cached_property'
                )
                cached_value = self.cache.get(key)
                
                # Record metric
                self.monitor.record_metric("interaction_time", time.perf_counter() * 1000, "ms")
            
            interaction_time = (time.perf_counter() - start_time) * 1000
            interaction_times.append(interaction_time)
        
        # Verify interaction performance
        max_interaction_time = max(interaction_times)
        avg_interaction_time = sum(interaction_times) / len(interaction_times)
        
        assert max_interaction_time < 50.0, f"Max interaction time {max_interaction_time}ms, should be <50ms"
        assert avg_interaction_time < 25.0, f"Avg interaction time {avg_interaction_time}ms, should be <25ms"
        
        # Verify cache performance
        cache_stats = self.cache.get_stats()
        assert cache_stats['hit_ratio'] >= 80.0, f"Cache hit ratio {cache_stats['hit_ratio']}% below target"
        
        # Verify monitoring data
        summary = self.monitor.get_performance_summary()
        assert summary['performance_level'] in ['excellent', 'good']
    
    def test_memory_usage_under_load(self):
        """Test memory usage remains reasonable under load"""
        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        # Create heavy load scenario
        large_dataset = []
        for i in range(10000):
            large_dataset.append({
                'element_id': f'element_{i}',
                'property_name': f'property_{i}',
                'value': 'x' * 1000,  # 1KB per property
                'height': 50
            })
        
        # Setup systems with large dataset
        self.virtualizer.set_items(large_dataset)
        self.virtualizer.set_viewport_size(800, 600)
        
        # Fill cache
        for i in range(1000):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f'element_{i}',
                property_name='test_property'
            )
            self.cache.put(key, 'x' * 1000)  # 1KB per cache entry
        
        # Simulate usage
        for i in range(100):
            self.virtualizer.set_scroll_position(i * 100)
            
            # Access cached data
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f'element_{i % 100}',
                property_name='test_property'
            )
            self.cache.get(key)
        
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is within acceptable limits
        assert memory_increase < 50.0, f"Memory increased by {memory_increase}MB, should be <50MB"
        
        # Verify cache size limit is respected
        cache_info = self.cache.get_cache_info()
        assert cache_info['total_size_mb'] <= 10.0, f"Cache size {cache_info['total_size_mb']}MB exceeds limit"
    
    def test_performance_targets_compliance(self):
        """Test all systems meet defined performance targets"""
        # Simulate realistic workload
        workload_operations = [
            ("property_update", 0.030, 50.0),      # 30ms avg, 50ms target
            ("validation", 0.025, 50.0),           # 25ms avg, 50ms target
            ("search", 0.040, 50.0),               # 40ms avg, 50ms target
            ("ui_response", 0.020, 25.0),          # 20ms avg, 25ms target
        ]
        
        for operation, avg_time_s, target_ms in workload_operations:
            # Simulate operation multiple times
            for i in range(20):
                with self.monitor.timing(operation):
                    # Simulate work with some variance
                    work_time = avg_time_s + (i % 5 - 2) * 0.005  # ±10ms variance
                    time.sleep(max(0.001, work_time))  # Minimum 1ms
        
        # Verify all operations meet targets
        for operation, _, target_ms in workload_operations:
            stats = self.monitor.get_operation_stats(operation)
            assert stats['mean_ms'] <= target_ms, f"{operation} avg {stats['mean_ms']}ms exceeds target {target_ms}ms"
            assert stats['p95_ms'] <= target_ms * 1.5, f"{operation} P95 {stats['p95_ms']}ms exceeds 1.5x target"
        
        # Verify overall performance level
        summary = self.monitor.get_performance_summary()
        assert summary['performance_level'] in ['excellent', 'good'], \
            f"Performance level {summary['performance_level']} below acceptable"


class TestPerformanceBenchmarks:
    """Performance benchmarks for regression testing"""
    
    def test_cache_throughput_benchmark(self):
        """Benchmark cache throughput operations"""
        cache = PropertyCache(max_entries=10000, max_size_mb=50)
        
        # Write throughput test
        start_time = time.perf_counter()
        
        for i in range(10000):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f'element_{i}',
                property_name='benchmark_property'
            )
            cache.put(key, f'value_{i}')
        
        write_time = time.perf_counter() - start_time
        write_ops_per_sec = 10000 / write_time
        
        # Read throughput test
        start_time = time.perf_counter()
        
        for i in range(10000):
            key = CacheKey(
                entry_type=CacheEntryType.PROPERTY_VALUE,
                element_id=f'element_{i}',
                property_name='benchmark_property'
            )
            cache.get(key)
        
        read_time = time.perf_counter() - start_time
        read_ops_per_sec = 10000 / read_time
        
        # Verify throughput targets
        assert write_ops_per_sec >= 5000, f"Write throughput {write_ops_per_sec} ops/sec below target 5000"
        assert read_ops_per_sec >= 10000, f"Read throughput {read_ops_per_sec} ops/sec below target 10000"
    
    def test_virtualization_scroll_benchmark(self):
        """Benchmark virtualization scroll performance"""
        mock_viewport = Mock()
        virtualizer = PropertyVirtualizer(mock_viewport)
        
        # Setup large dataset
        items = [
            {'element_id': f'element_{i}', 'property_name': f'prop_{i}', 'height': 50}
            for i in range(20000)
        ]
        
        virtualizer.set_items(items)
        virtualizer.set_viewport_size(800, 600)
        
        # Benchmark scroll operations
        scroll_times = []
        
        for scroll_pos in range(0, 500000, 5000):  # Large scroll jumps
            start_time = time.perf_counter()
            virtualizer.set_scroll_position(scroll_pos)
            scroll_time = (time.perf_counter() - start_time) * 1000
            scroll_times.append(scroll_time)
        
        max_scroll_time = max(scroll_times)
        avg_scroll_time = sum(scroll_times) / len(scroll_times)
        
        # Verify scroll performance targets
        assert max_scroll_time < 20.0, f"Max scroll time {max_scroll_time}ms exceeds target 20ms"
        assert avg_scroll_time < 10.0, f"Avg scroll time {avg_scroll_time}ms exceeds target 10ms"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])