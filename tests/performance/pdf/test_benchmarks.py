"""
Benchmarking Suite for PDF.js Performance Optimization.

This module provides comprehensive benchmarks for PDF.js performance
including load times, memory usage, rendering performance, and more.
"""
import pytest
import time
import statistics
import json
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, MagicMock
import concurrent.futures
import threading

from src.torematrix.integrations.pdf.performance import (
    PerformanceConfig, PerformanceMonitor, PerformanceOptimizer,
    PerformanceLevel, PerformanceMetrics
)
from src.torematrix.integrations.pdf.memory import MemoryManager
from src.torematrix.integrations.pdf.cache import CacheManager
from src.torematrix.integrations.pdf.metrics import MetricsCollector, TimingContext


@dataclass
class BenchmarkResult:
    """Benchmark result data structure."""
    name: str
    duration_ms: float
    memory_usage_mb: float
    throughput: float
    success_rate: float
    metadata: Dict[str, Any]


class BenchmarkRunner:
    """Benchmark runner for performance tests."""
    
    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.results: List[BenchmarkResult] = []
        self.metrics_collector = MetricsCollector()
    
    def run_benchmark(self, name: str, benchmark_func, *args, **kwargs) -> BenchmarkResult:
        """Run a benchmark function multiple times and collect results."""
        durations = []
        memory_usage = []
        successes = 0
        
        for i in range(self.iterations):
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            try:
                result = benchmark_func(*args, **kwargs)
                if result:
                    successes += 1
            except Exception as e:
                print(f"Benchmark {name} iteration {i} failed: {e}")
                continue
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            duration_ms = (end_time - start_time) * 1000
            memory_delta = end_memory - start_memory
            
            durations.append(duration_ms)
            memory_usage.append(memory_delta)
        
        # Calculate statistics
        avg_duration = statistics.mean(durations) if durations else 0
        avg_memory = statistics.mean(memory_usage) if memory_usage else 0
        throughput = self.iterations / (sum(durations) / 1000) if durations else 0
        success_rate = successes / self.iterations
        
        result = BenchmarkResult(
            name=name,
            duration_ms=avg_duration,
            memory_usage_mb=avg_memory,
            throughput=throughput,
            success_rate=success_rate,
            metadata={
                'iterations': self.iterations,
                'min_duration': min(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
                'p95_duration': self._percentile(durations, 95) if durations else 0,
                'p99_duration': self._percentile(durations, 99) if durations else 0
            }
        )
        
        self.results.append(result)
        return result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary."""
        if not self.results:
            return {}
        
        return {
            'total_benchmarks': len(self.results),
            'total_iterations': sum(r.metadata['iterations'] for r in self.results),
            'average_duration': statistics.mean([r.duration_ms for r in self.results]),
            'average_memory': statistics.mean([r.memory_usage_mb for r in self.results]),
            'average_throughput': statistics.mean([r.throughput for r in self.results]),
            'average_success_rate': statistics.mean([r.success_rate for r in self.results]),
            'results': [
                {
                    'name': r.name,
                    'duration_ms': r.duration_ms,
                    'memory_usage_mb': r.memory_usage_mb,
                    'throughput': r.throughput,
                    'success_rate': r.success_rate,
                    'metadata': r.metadata
                }
                for r in self.results
            ]
        }


class TestPerformanceBenchmarks:
    """Performance benchmarks for PDF.js optimization."""
    
    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner(iterations=50)  # Reduced for testing
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(
            cache_size_mb=100,
            max_preload_pages=5,
            performance_level=PerformanceLevel.MEDIUM,
            metrics_collection_interval=0.1
        )
    
    def test_memory_allocation_benchmark(self, benchmark_runner, config):
        """Benchmark memory allocation performance."""
        memory_manager = MemoryManager(config)
        
        def allocate_memory():
            """Allocate memory for a page."""
            page_size = 1024 * 1024  # 1MB
            result = memory_manager.allocate_page_memory(1, page_size)
            if result:
                memory_manager.deallocate_page_memory(1, result[0])
                return True
            return False
        
        result = benchmark_runner.run_benchmark('memory_allocation', allocate_memory)
        
        # Performance assertions
        assert result.success_rate > 0.95  # 95% success rate
        assert result.duration_ms < 10     # Less than 10ms per allocation
        assert result.throughput > 100     # More than 100 ops/sec
        
        print(f"Memory allocation benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} ops/sec")
    
    def test_cache_performance_benchmark(self, benchmark_runner, config):
        """Benchmark cache performance."""
        cache_manager = CacheManager(config)
        cache_manager.start()
        
        # Pre-populate cache
        for i in range(10):
            page_data = {'content': f'page {i}' * 100}
            cache_manager.memory_cache.put_page_render(i, page_data)
        
        def cache_operation():
            """Perform cache get operation."""
            import random
            page_num = random.randint(0, 9)
            data = cache_manager.memory_cache.get_page_render(page_num)
            return data is not None
        
        result = benchmark_runner.run_benchmark('cache_get', cache_operation)
        
        # Performance assertions
        assert result.success_rate > 0.8   # 80% hit rate (some misses expected)
        assert result.duration_ms < 1      # Less than 1ms per operation
        assert result.throughput > 1000    # More than 1000 ops/sec
        
        print(f"Cache get benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} ops/sec")
    
    def test_metrics_collection_benchmark(self, benchmark_runner):
        """Benchmark metrics collection performance."""
        collector = MetricsCollector()
        
        def collect_metrics():
            """Collect performance metrics."""
            import random
            collector.record_timing('test_metric', random.uniform(50, 150))
            collector.record_memory('memory_metric', random.uniform(10, 100))
            collector.record_count('count_metric', random.randint(1, 10))
            return True
        
        result = benchmark_runner.run_benchmark('metrics_collection', collect_metrics)
        
        # Performance assertions
        assert result.success_rate > 0.99  # 99% success rate
        assert result.duration_ms < 5      # Less than 5ms per collection
        assert result.throughput > 200     # More than 200 ops/sec
        
        print(f"Metrics collection benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} ops/sec")
    
    def test_performance_monitoring_benchmark(self, benchmark_runner, config):
        """Benchmark performance monitoring overhead."""
        monitor = PerformanceMonitor(config)
        
        # Mock process to avoid system dependencies
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=100 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 50.0
        monitor.process = mock_process
        
        # Mock cache manager
        monitor.cache_manager.get_statistics = Mock(return_value={
            'hit_rate': 0.85,
            'size_mb': 50.0,
            'cached_pages': 25
        })
        
        def monitor_metrics():
            """Collect monitoring metrics."""
            monitor._collect_metrics()
            return True
        
        result = benchmark_runner.run_benchmark('performance_monitoring', monitor_metrics)
        
        # Performance assertions
        assert result.success_rate > 0.95  # 95% success rate
        assert result.duration_ms < 50     # Less than 50ms per collection
        assert result.throughput > 20      # More than 20 collections/sec
        
        print(f"Performance monitoring benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} ops/sec")
    
    def test_large_document_simulation(self, benchmark_runner, config):
        """Benchmark large document handling."""
        # Simulate large document (100MB)
        large_config = PerformanceConfig(
            cache_size_mb=200,
            max_preload_pages=2,
            performance_level=PerformanceLevel.HIGH
        )
        
        memory_manager = MemoryManager(large_config)
        cache_manager = CacheManager(large_config)
        
        def process_large_page():
            """Process a large document page."""
            # Simulate large page (5MB)
            page_size = 5 * 1024 * 1024
            page_data = {'content': 'x' * (page_size // 2), 'size': page_size}
            
            # Allocate memory
            result = memory_manager.allocate_page_memory(1, page_size)
            if result:
                # Cache page
                cache_manager.memory_cache.put_page_render(1, page_data)
                
                # Deallocate
                memory_manager.deallocate_page_memory(1, result[0])
                return True
            return False
        
        result = benchmark_runner.run_benchmark('large_document', process_large_page)
        
        # Performance assertions (more lenient for large documents)
        assert result.success_rate > 0.90  # 90% success rate
        assert result.duration_ms < 100    # Less than 100ms per page
        assert result.throughput > 10      # More than 10 pages/sec
        
        print(f"Large document benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} pages/sec")
    
    def test_concurrent_access_benchmark(self, benchmark_runner, config):
        """Benchmark concurrent access performance."""
        cache_manager = CacheManager(config)
        cache_manager.start()
        
        # Pre-populate cache
        for i in range(20):
            page_data = {'content': f'page {i}' * 50}
            cache_manager.memory_cache.put_page_render(i, page_data)
        
        def concurrent_access():
            """Perform concurrent cache access."""
            import random
            import threading
            
            results = []
            
            def worker():
                for _ in range(5):
                    page_num = random.randint(0, 19)
                    data = cache_manager.memory_cache.get_page_render(page_num)
                    results.append(data is not None)
            
            # Run 5 concurrent workers
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            return len(results) > 0 and all(results)
        
        result = benchmark_runner.run_benchmark('concurrent_access', concurrent_access)
        
        # Performance assertions
        assert result.success_rate > 0.85  # 85% success rate
        assert result.duration_ms < 200    # Less than 200ms per batch
        assert result.throughput > 5       # More than 5 batches/sec
        
        print(f"Concurrent access benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} batches/sec")
    
    def test_memory_pressure_benchmark(self, benchmark_runner, config):
        """Benchmark memory pressure handling."""
        memory_manager = MemoryManager(config)
        
        # Mock high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=500 * 1024 * 1024)  # 500MB
        mock_process.cpu_percent.return_value = 80.0
        memory_manager.process = mock_process
        
        def handle_memory_pressure():
            """Handle memory pressure scenario."""
            # Add pages to trigger pressure
            for i in range(10):
                page_data = {'content': f'page {i}' * 1000}
                memory_manager.add_page_to_cache(i, page_data)
            
            # Perform cleanup
            cleanup_stats = memory_manager.emergency_cleanup()
            
            return cleanup_stats['pages_cleaned'] > 0
        
        result = benchmark_runner.run_benchmark('memory_pressure', handle_memory_pressure)
        
        # Performance assertions
        assert result.success_rate > 0.90  # 90% success rate
        assert result.duration_ms < 500    # Less than 500ms per cleanup
        assert result.throughput > 2       # More than 2 cleanups/sec
        
        print(f"Memory pressure benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} cleanups/sec")
    
    def test_optimization_application_benchmark(self, benchmark_runner, config):
        """Benchmark optimization application performance."""
        monitor = PerformanceMonitor(config)
        
        # Mock dependencies
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=200 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 60.0
        monitor.process = mock_process
        
        monitor.cache_manager.get_statistics = Mock(return_value={
            'hit_rate': 0.7,
            'size_mb': 80.0,
            'cached_pages': 40
        })
        
        def apply_optimization():
            """Apply performance optimization."""
            # Get recommendations
            recommendations = monitor.get_optimization_recommendations()
            
            # Apply first recommendation if available
            if recommendations:
                rec = recommendations[0]
                success = monitor.apply_optimization(rec['action'], {})
                return success
            
            return True
        
        result = benchmark_runner.run_benchmark('optimization_application', apply_optimization)
        
        # Performance assertions
        assert result.success_rate > 0.80  # 80% success rate
        assert result.duration_ms < 100    # Less than 100ms per optimization
        assert result.throughput > 10      # More than 10 optimizations/sec
        
        print(f"Optimization application benchmark: {result.duration_ms:.2f}ms avg, {result.throughput:.1f} ops/sec")


class TestStressBenchmarks:
    """Stress testing benchmarks."""
    
    def test_memory_stress_benchmark(self):
        """Stress test memory management."""
        config = PerformanceConfig(cache_size_mb=100)
        memory_manager = MemoryManager(config)
        
        # Mock process
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=50 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 25.0
        memory_manager.process = mock_process
        
        start_time = time.time()
        
        # Stress test: allocate and deallocate many pages
        for i in range(1000):
            page_data = {'content': f'stress page {i}' * 100}
            memory_manager.add_page_to_cache(i, page_data)
            
            # Allocate memory
            result = memory_manager.allocate_page_memory(i, 1024 * 1024)
            
            # Periodically clean up
            if i % 100 == 0:
                memory_manager.cleanup_old_pages(max_age_seconds=1)
            
            # Deallocate some memory
            if result and i % 10 == 0:
                memory_manager.deallocate_page_memory(i, result[0])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 30  # Should complete in under 30 seconds
        assert len(memory_manager.page_cache) > 0  # Should have cached pages
        
        # Get final statistics
        stats = memory_manager.get_cache_stats()
        pool_stats = memory_manager.get_pool_stats()
        
        print(f"Memory stress test: {total_time:.2f}s total, {stats['cached_pages']} cached pages")
        print(f"Pool stats: {pool_stats}")
    
    def test_cache_stress_benchmark(self):
        """Stress test cache management."""
        config = PerformanceConfig(cache_size_mb=50)
        cache_manager = CacheManager(config)
        cache_manager.start()
        
        start_time = time.time()
        
        # Stress test: many cache operations
        for i in range(2000):
            page_data = {'content': f'cache stress page {i}' * 50}
            
            # Put page render
            cache_manager.memory_cache.put_page_render(i, page_data)
            
            # Get page render
            retrieved = cache_manager.memory_cache.get_page_render(i)
            
            # Put page text
            text_data = f"Text for page {i}"
            cache_manager.memory_cache.put_page_text(i, text_data)
            
            # Get page text
            retrieved_text = cache_manager.memory_cache.get_page_text(i)
            
            # Periodically clear cache
            if i % 500 == 0:
                cache_manager.clear_cache(ratio=0.3)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 20  # Should complete in under 20 seconds
        
        # Get final statistics
        stats = cache_manager.get_statistics()
        
        print(f"Cache stress test: {total_time:.2f}s total")
        print(f"Cache stats: {stats}")
        
        # Check performance metrics
        assert stats['hit_rate'] > 0.5  # Should have some hits
    
    def test_concurrent_stress_benchmark(self):
        """Stress test concurrent operations."""
        config = PerformanceConfig(cache_size_mb=200)
        memory_manager = MemoryManager(config)
        cache_manager = CacheManager(config)
        
        # Mock process
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=100 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 50.0
        memory_manager.process = mock_process
        
        cache_manager.start()
        
        results = []
        errors = []
        
        def worker_thread(thread_id):
            """Worker thread for concurrent operations."""
            try:
                for i in range(100):
                    page_num = thread_id * 100 + i
                    
                    # Memory operations
                    page_data = {'content': f'thread {thread_id} page {i}'}
                    memory_manager.add_page_to_cache(page_num, page_data)
                    
                    # Cache operations
                    cache_manager.memory_cache.put_page_render(page_num, page_data)
                    retrieved = cache_manager.memory_cache.get_page_render(page_num)
                    
                    results.append((thread_id, page_num, retrieved is not None))
                    
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        start_time = time.time()
        
        # Run 10 concurrent threads
        threads = []
        for thread_id in range(10):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 60  # Should complete in under 60 seconds
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 1000  # All operations should complete
        
        # Check success rate
        success_rate = sum(1 for _, _, success in results if success) / len(results)
        assert success_rate > 0.8  # 80% success rate
        
        print(f"Concurrent stress test: {total_time:.2f}s total, {success_rate:.1%} success rate")


class TestPerformanceRegression:
    """Performance regression tests."""
    
    def test_baseline_performance(self):
        """Test baseline performance metrics."""
        config = PerformanceConfig(
            cache_size_mb=100,
            max_preload_pages=5,
            performance_level=PerformanceLevel.MEDIUM
        )
        
        # Test key performance metrics
        benchmarks = {
            'memory_allocation': self._benchmark_memory_allocation,
            'cache_access': self._benchmark_cache_access,
            'metrics_collection': self._benchmark_metrics_collection
        }
        
        baseline_targets = {
            'memory_allocation': {'duration_ms': 10, 'throughput': 100},
            'cache_access': {'duration_ms': 1, 'throughput': 1000},
            'metrics_collection': {'duration_ms': 5, 'throughput': 200}
        }
        
        results = {}
        
        for name, benchmark_func in benchmarks.items():
            runner = BenchmarkRunner(iterations=100)
            result = runner.run_benchmark(name, benchmark_func, config)
            results[name] = result
            
            # Check against baseline
            targets = baseline_targets[name]
            assert result.duration_ms <= targets['duration_ms'], f"{name} duration regression"
            assert result.throughput >= targets['throughput'], f"{name} throughput regression"
        
        # Save results for comparison
        summary = {
            'timestamp': time.time(),
            'results': {name: {
                'duration_ms': r.duration_ms,
                'throughput': r.throughput,
                'success_rate': r.success_rate
            } for name, r in results.items()}
        }
        
        print(f"Baseline performance: {json.dumps(summary, indent=2)}")
    
    def _benchmark_memory_allocation(self, config):
        """Benchmark memory allocation."""
        memory_manager = MemoryManager(config)
        
        # Mock process
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=50 * 1024 * 1024)
        mock_process.cpu_percent.return_value = 25.0
        memory_manager.process = mock_process
        
        result = memory_manager.allocate_page_memory(1, 1024 * 1024)
        if result:
            memory_manager.deallocate_page_memory(1, result[0])
            return True
        return False
    
    def _benchmark_cache_access(self, config):
        """Benchmark cache access."""
        cache_manager = CacheManager(config)
        cache_manager.start()
        
        # Pre-populate cache
        page_data = {'content': 'test page'}
        cache_manager.memory_cache.put_page_render(1, page_data)
        
        # Access cache
        result = cache_manager.memory_cache.get_page_render(1)
        return result is not None
    
    def _benchmark_metrics_collection(self, config):
        """Benchmark metrics collection."""
        collector = MetricsCollector()
        
        collector.record_timing('test_metric', 100.0)
        collector.record_memory('memory_metric', 50.0)
        collector.record_count('count_metric', 5)
        
        return True


if __name__ == '__main__':
    # Run performance benchmarks
    pytest.main([__file__, '-v', '-s'])  # -s to see print output