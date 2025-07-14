"""Performance tests for worker pool system."""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import as_completed

from torematrix.processing.workers import (
    WorkerPool, ProgressTracker, ResourceMonitor,
    WorkerConfig, ResourceLimits, ResourceType
)


class MockProcessorContext:
    """Mock processor context for testing."""
    
    def __init__(self, document_id: str = "test-doc"):
        self.document_id = document_id


class PerformanceTestSuite:
    """Base class for performance tests."""
    
    @staticmethod
    def measure_time(func):
        """Decorator to measure execution time."""
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            return result, end_time - start_time
        return wrapper
    
    @staticmethod
    def calculate_throughput(count: int, duration: float) -> float:
        """Calculate throughput in items per second."""
        return count / duration if duration > 0 else 0.0


@pytest.mark.performance
@pytest.mark.asyncio
class TestWorkerPoolPerformance(PerformanceTestSuite):
    """Performance tests for worker pool."""
    
    @pytest.fixture
    async def high_performance_config(self):
        """Create high-performance configuration."""
        return WorkerConfig(
            async_workers=8,
            thread_workers=4,
            process_workers=0,
            max_queue_size=5000,
            priority_queue_size=1000,
            default_timeout=60.0,
            worker_heartbeat_interval=5.0,
            max_concurrent_tasks=200
        )
    
    @pytest.fixture
    async def performance_pool(self, high_performance_config):
        """Create high-performance worker pool."""
        pool = WorkerPool(config=high_performance_config)
        await pool.start()
        yield pool
        await pool.stop()
    
    async def test_concurrent_task_throughput(self, performance_pool):
        """Test throughput with many concurrent tasks."""
        num_tasks = 100
        
        async def fast_processor(context):
            """Fast processor for throughput testing."""
            await asyncio.sleep(0.01)  # 10ms of simulated work
            return f"result-{context.document_id}"
        
        # Measure time to submit all tasks
        start_time = time.time()
        
        task_ids = []
        for i in range(num_tasks):
            task_id = await performance_pool.submit_task(
                processor_name="fast_processor",
                context=MockProcessorContext(f"doc-{i}"),
                processor_func=fast_processor
            )
            task_ids.append(task_id)
        
        submission_time = time.time() - start_time
        
        # Measure time to complete all tasks
        completion_start = time.time()
        
        results = []
        for task_id in task_ids:
            result = await performance_pool.get_task_result(task_id, timeout=30.0)
            results.append(result)
        
        completion_time = time.time() - completion_start
        total_time = time.time() - start_time
        
        # Calculate metrics
        submission_throughput = self.calculate_throughput(num_tasks, submission_time)
        completion_throughput = self.calculate_throughput(num_tasks, completion_time)
        overall_throughput = self.calculate_throughput(num_tasks, total_time)
        
        # Assertions
        assert len(results) == num_tasks
        assert submission_throughput > 500  # Should submit >500 tasks/sec
        assert completion_throughput > 50   # Should complete >50 tasks/sec
        assert overall_throughput > 30      # Overall >30 tasks/sec
        
        print(f"Submission throughput: {submission_throughput:.1f} tasks/sec")
        print(f"Completion throughput: {completion_throughput:.1f} tasks/sec")
        print(f"Overall throughput: {overall_throughput:.1f} tasks/sec")
    
    async def test_task_latency_distribution(self, performance_pool):
        """Test task latency distribution."""
        num_tasks = 50
        latencies = []
        
        async def latency_processor(context):
            """Processor for latency testing."""
            start_time = time.time()
            await asyncio.sleep(0.05)  # 50ms of work
            return time.time() - start_time
        
        # Submit tasks and measure individual latencies
        for i in range(num_tasks):
            submit_time = time.time()
            
            task_id = await performance_pool.submit_task(
                processor_name="latency_processor",
                context=MockProcessorContext(f"latency-{i}"),
                processor_func=latency_processor
            )
            
            result = await performance_pool.get_task_result(task_id, timeout=10.0)
            total_latency = time.time() - submit_time
            latencies.append(total_latency)
        
        # Calculate latency statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]
        
        # Assertions
        assert mean_latency < 0.2    # Mean latency < 200ms
        assert median_latency < 0.15 # Median latency < 150ms
        assert p95_latency < 0.3     # 95th percentile < 300ms
        assert p99_latency < 0.5     # 99th percentile < 500ms
        
        print(f"Mean latency: {mean_latency*1000:.1f}ms")
        print(f"Median latency: {median_latency*1000:.1f}ms")
        print(f"95th percentile: {p95_latency*1000:.1f}ms")
        print(f"99th percentile: {p99_latency*1000:.1f}ms")
    
    async def test_queue_performance_under_load(self, performance_pool):
        """Test queue performance under high load."""
        num_batches = 10
        batch_size = 20
        
        async def batch_processor(context):
            """Processor for batch testing."""
            batch_id = context.document_id.split('-')[1]
            await asyncio.sleep(0.02)  # 20ms work
            return f"batch-{batch_id}-complete"
        
        # Submit tasks in batches
        all_task_ids = []
        batch_times = []
        
        for batch in range(num_batches):
            batch_start = time.time()
            batch_task_ids = []
            
            for i in range(batch_size):
                task_id = await performance_pool.submit_task(
                    processor_name="batch_processor",
                    context=MockProcessorContext(f"batch-{batch}-{i}"),
                    processor_func=batch_processor
                )
                batch_task_ids.append(task_id)
            
            all_task_ids.extend(batch_task_ids)
            batch_times.append(time.time() - batch_start)
        
        # Wait for all tasks to complete
        completion_start = time.time()
        completed_count = 0
        
        for task_id in all_task_ids:
            await performance_pool.get_task_result(task_id, timeout=30.0)
            completed_count += 1
        
        completion_time = time.time() - completion_start
        
        # Analyze performance
        mean_batch_time = statistics.mean(batch_times)
        total_tasks = num_batches * batch_size
        overall_throughput = self.calculate_throughput(total_tasks, completion_time)
        
        # Assertions
        assert mean_batch_time < 0.1    # Batch submission < 100ms
        assert overall_throughput > 20  # Overall throughput > 20 tasks/sec
        assert completed_count == total_tasks
        
        print(f"Mean batch submission time: {mean_batch_time*1000:.1f}ms")
        print(f"Overall throughput: {overall_throughput:.1f} tasks/sec")
    
    async def test_memory_usage_under_load(self, performance_pool):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def memory_processor(context):
            """Processor that creates some temporary data."""
            # Create temporary data
            data = [i for i in range(1000)]
            await asyncio.sleep(0.01)
            return len(data)
        
        # Submit many tasks
        num_tasks = 200
        task_ids = []
        
        for i in range(num_tasks):
            task_id = await performance_pool.submit_task(
                processor_name="memory_processor",
                context=MockProcessorContext(f"mem-{i}"),
                processor_func=memory_processor
            )
            task_ids.append(task_id)
        
        # Wait for completion
        for task_id in task_ids:
            await performance_pool.get_task_result(task_id, timeout=30.0)
        
        # Force garbage collection and measure memory
        gc.collect()
        await asyncio.sleep(0.1)  # Let cleanup happen
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 100  # Less than 100MB growth
        
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Final memory: {final_memory:.1f}MB")
        print(f"Memory growth: {memory_growth:.1f}MB")
    
    async def test_priority_queue_performance(self, performance_pool):
        """Test priority queue handling performance."""
        num_critical = 20
        num_normal = 80
        
        async def priority_processor(context):
            """Processor for priority testing."""
            priority = context.document_id.split('-')[0]
            await asyncio.sleep(0.02)
            return f"processed-{priority}"
        
        # Submit mix of critical and normal tasks
        start_time = time.time()
        
        # Submit normal tasks first
        normal_tasks = []
        for i in range(num_normal):
            task_id = await performance_pool.submit_task(
                processor_name="priority_processor",
                context=MockProcessorContext(f"normal-{i}"),
                processor_func=priority_processor,
                priority=performance_pool.ProcessorPriority.NORMAL
            )
            normal_tasks.append(task_id)
        
        # Submit critical tasks (should jump queue)
        critical_tasks = []
        for i in range(num_critical):
            task_id = await performance_pool.submit_task(
                processor_name="priority_processor",
                context=MockProcessorContext(f"critical-{i}"),
                processor_func=priority_processor,
                priority=performance_pool.ProcessorPriority.CRITICAL
            )
            critical_tasks.append(task_id)
        
        submission_time = time.time() - start_time
        
        # Measure completion times
        critical_completion_start = time.time()
        
        # Complete critical tasks first
        for task_id in critical_tasks:
            await performance_pool.get_task_result(task_id, timeout=30.0)
        
        critical_completion_time = time.time() - critical_completion_start
        
        # Complete normal tasks
        normal_completion_start = time.time()
        for task_id in normal_tasks:
            await performance_pool.get_task_result(task_id, timeout=30.0)
        
        normal_completion_time = time.time() - normal_completion_start
        
        # Calculate metrics
        total_tasks = num_critical + num_normal
        submission_rate = self.calculate_throughput(total_tasks, submission_time)
        
        # Assertions
        assert submission_rate > 100  # Should submit >100 tasks/sec
        
        print(f"Submission rate: {submission_rate:.1f} tasks/sec")
        print(f"Critical completion time: {critical_completion_time:.2f}s")
        print(f"Normal completion time: {normal_completion_time:.2f}s")


@pytest.mark.performance
@pytest.mark.asyncio
class TestResourceMonitorPerformance(PerformanceTestSuite):
    """Performance tests for resource monitoring."""
    
    @pytest.fixture
    async def performance_monitor(self):
        """Create resource monitor for performance testing."""
        limits = ResourceLimits()
        monitor = ResourceMonitor(limits, check_interval=0.01)  # Fast monitoring
        await monitor.start()
        yield monitor
        await monitor.stop()
    
    async def test_resource_allocation_performance(self, performance_monitor):
        """Test performance of resource allocation operations."""
        num_allocations = 1000
        
        # Measure allocation performance
        start_time = time.time()
        
        task_ids = []
        for i in range(num_allocations):
            task_id = f"perf-task-{i}"
            resources = {
                ResourceType.CPU: 1.0,
                ResourceType.MEMORY: 2.0
            }
            
            success = await performance_monitor.allocate(task_id, resources)
            assert success
            task_ids.append(task_id)
        
        allocation_time = time.time() - start_time
        
        # Measure release performance
        release_start = time.time()
        
        for task_id in task_ids:
            await performance_monitor.release(task_id)
        
        release_time = time.time() - release_start
        
        # Calculate performance metrics
        allocation_rate = self.calculate_throughput(num_allocations, allocation_time)
        release_rate = self.calculate_throughput(num_allocations, release_time)
        
        # Assertions
        assert allocation_rate > 1000  # >1000 allocations/sec
        assert release_rate > 2000     # >2000 releases/sec
        
        print(f"Allocation rate: {allocation_rate:.1f} ops/sec")
        print(f"Release rate: {release_rate:.1f} ops/sec")
    
    async def test_monitoring_overhead(self, performance_monitor):
        """Test monitoring loop overhead."""
        # Let monitor run and collect data
        await asyncio.sleep(1.0)
        
        # Check history collection
        history = performance_monitor.get_resource_history(minutes=1)
        
        # Should have collected data without excessive overhead
        assert len(history) > 50  # At least 50 data points in 1 second
        assert len(history) < 200  # But not excessive
        
        # Check current usage is being updated
        current_usage = performance_monitor.get_current_usage()
        assert len(current_usage) > 0
        
        print(f"Collected {len(history)} data points in 1 second")


@pytest.mark.performance
@pytest.mark.asyncio
class TestProgressTrackerPerformance(PerformanceTestSuite):
    """Performance tests for progress tracking."""
    
    @pytest.fixture
    async def performance_tracker(self):
        """Create progress tracker for performance testing."""
        return ProgressTracker()
    
    async def test_progress_update_performance(self, performance_tracker):
        """Test performance of progress updates."""
        num_tasks = 500
        updates_per_task = 10
        
        # Start tasks
        task_ids = []
        for i in range(num_tasks):
            task_id = f"progress-task-{i}"
            await performance_tracker.start_task(
                task_id=task_id,
                processor_name="performance_test",
                document_id=f"doc-{i}"
            )
            task_ids.append(task_id)
        
        # Measure update performance
        start_time = time.time()
        
        for task_id in task_ids:
            for update in range(updates_per_task):
                progress = update / updates_per_task
                await performance_tracker.update_task(
                    task_id=task_id,
                    progress=progress,
                    message=f"Update {update}"
                )
        
        update_time = time.time() - start_time
        
        # Complete all tasks
        completion_start = time.time()
        
        for task_id in task_ids:
            await performance_tracker.complete_task(task_id, success=True)
        
        completion_time = time.time() - completion_start
        
        # Calculate performance
        total_updates = num_tasks * updates_per_task
        update_rate = self.calculate_throughput(total_updates, update_time)
        completion_rate = self.calculate_throughput(num_tasks, completion_time)
        
        # Assertions
        assert update_rate > 1000      # >1000 updates/sec
        assert completion_rate > 500   # >500 completions/sec
        
        print(f"Progress update rate: {update_rate:.1f} updates/sec")
        print(f"Task completion rate: {completion_rate:.1f} completions/sec")
    
    async def test_statistics_calculation_performance(self, performance_tracker):
        """Test performance of statistics calculation."""
        # Add statistics data
        num_processors = 50
        tasks_per_processor = 100
        
        for proc_id in range(num_processors):
            processor_name = f"processor_{proc_id}"
            # Simulate task durations
            durations = [0.1 + (i * 0.01) for i in range(tasks_per_processor)]
            performance_tracker.task_stats[processor_name] = durations
        
        # Measure statistics calculation performance
        start_time = time.time()
        
        # Calculate overall statistics
        overall_stats = performance_tracker.get_statistics()
        
        # Calculate per-processor statistics
        processor_stats = {}
        for proc_id in range(num_processors):
            processor_name = f"processor_{proc_id}"
            stats = performance_tracker.get_statistics(processor_name)
            processor_stats[processor_name] = stats
        
        calculation_time = time.time() - start_time
        
        # Verify results
        total_tasks = num_processors * tasks_per_processor
        assert overall_stats["total_tasks"] == total_tasks
        assert len(processor_stats) == num_processors
        
        # Performance assertion
        calculation_rate = self.calculate_throughput(num_processors + 1, calculation_time)
        assert calculation_rate > 10  # >10 calculations/sec
        
        print(f"Statistics calculation rate: {calculation_rate:.1f} calcs/sec")
        print(f"Processed {total_tasks} task records")


@pytest.mark.performance 
@pytest.mark.asyncio
class TestIntegratedSystemPerformance(PerformanceTestSuite):
    """Performance tests for the complete integrated system."""
    
    async def test_end_to_end_performance(self):
        """Test end-to-end system performance."""
        # High-performance configuration
        config = WorkerConfig(
            async_workers=6,
            thread_workers=2,
            max_queue_size=2000,
            priority_queue_size=500
        )
        
        # Set up integrated system
        resource_limits = ResourceLimits()
        resource_monitor = ResourceMonitor(resource_limits, check_interval=0.1)
        progress_tracker = ProgressTracker()
        
        pool = WorkerPool(
            config=config,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
        
        try:
            # Start all components
            await resource_monitor.start()
            await pool.start()
            
            # Performance test
            num_tasks = 200
            
            async def realistic_processor(context):
                """Realistic processor simulation."""
                # Simulate variable work
                doc_id = int(context.document_id.split('-')[-1])
                work_time = 0.02 + (doc_id % 10) * 0.005  # 20-65ms
                
                await asyncio.sleep(work_time)
                return f"processed-{context.document_id}"
            
            # Measure end-to-end performance
            start_time = time.time()
            
            # Submit all tasks
            task_ids = []
            for i in range(num_tasks):
                task_id = await pool.submit_task(
                    processor_name="realistic_processor",
                    context=MockProcessorContext(f"e2e-doc-{i}"),
                    processor_func=realistic_processor
                )
                task_ids.append(task_id)
            
            # Wait for all completions
            results = []
            for task_id in task_ids:
                result = await pool.get_task_result(task_id, timeout=60.0)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # Calculate metrics
            throughput = self.calculate_throughput(num_tasks, total_time)
            
            # Get system statistics
            pool_stats = pool.get_pool_stats()
            progress_stats = progress_tracker.get_statistics()
            
            # Assertions
            assert len(results) == num_tasks
            assert throughput > 10  # >10 tasks/sec end-to-end
            assert pool_stats.completed_tasks == num_tasks
            assert pool_stats.failed_tasks == 0
            
            print(f"End-to-end throughput: {throughput:.1f} tasks/sec")
            print(f"Average processing time: {pool_stats.average_processing_time:.3f}s")
            print(f"Average wait time: {pool_stats.average_wait_time:.3f}s")
            
        finally:
            await pool.stop()
            await resource_monitor.stop()
    
    async def test_scalability_with_worker_count(self):
        """Test how performance scales with worker count."""
        num_tasks = 100
        worker_counts = [1, 2, 4, 8]
        results = {}
        
        async def scaling_processor(context):
            """Processor for scaling tests."""
            await asyncio.sleep(0.05)  # 50ms of work
            return "scaled"
        
        for worker_count in worker_counts:
            config = WorkerConfig(
                async_workers=worker_count,
                thread_workers=0,
                max_queue_size=500
            )
            
            pool = WorkerPool(config=config)
            
            try:
                await pool.start()
                
                # Measure performance with this worker count
                start_time = time.time()
                
                task_ids = []
                for i in range(num_tasks):
                    task_id = await pool.submit_task(
                        processor_name="scaling_processor",
                        context=MockProcessorContext(f"scale-{i}"),
                        processor_func=scaling_processor
                    )
                    task_ids.append(task_id)
                
                # Wait for completion
                for task_id in task_ids:
                    await pool.get_task_result(task_id, timeout=30.0)
                
                completion_time = time.time() - start_time
                throughput = self.calculate_throughput(num_tasks, completion_time)
                
                results[worker_count] = {
                    'throughput': throughput,
                    'completion_time': completion_time
                }
                
            finally:
                await pool.stop()
        
        # Analyze scaling
        print("Scaling results:")
        for workers, metrics in results.items():
            print(f"  {workers} workers: {metrics['throughput']:.1f} tasks/sec")
        
        # Basic scaling assertion - more workers should generally be faster
        assert results[8]['throughput'] > results[1]['throughput']


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])