"""Tests for worker pool implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from torematrix.processing.workers.pool import (
    WorkerPool, WorkerType, WorkerStatus, ProcessorPriority,
    WorkerStats, PoolStats, WorkerTask
)
from torematrix.processing.workers.config import WorkerConfig, ResourceLimits, ResourceType
from torematrix.processing.workers.resources import ResourceMonitor
from torematrix.processing.workers.progress import ProgressTracker
from torematrix.processing.workers.exceptions import (
    WorkerPoolError, TaskError, TaskTimeoutError, ResourceError
)


class MockProcessorContext:
    """Mock processor context for testing."""
    
    def __init__(self, document_id: str = "test-doc"):
        self.document_id = document_id


class TestWorkerTask:
    """Test WorkerTask dataclass."""
    
    def test_create_worker_task(self):
        """Test creating worker task."""
        context = MockProcessorContext()
        submitted_at = datetime.utcnow()
        
        async def dummy_processor(ctx):
            return "result"
        
        task = WorkerTask(
            task_id="task-123",
            processor_name="test_processor",
            context=context,
            processor_func=dummy_processor,
            priority=ProcessorPriority.NORMAL,
            timeout=300.0,
            submitted_at=submitted_at
        )
        
        assert task.task_id == "task-123"
        assert task.processor_name == "test_processor"
        assert task.context == context
        assert task.processor_func == dummy_processor
        assert task.priority == ProcessorPriority.NORMAL
        assert task.timeout == 300.0
        assert task.submitted_at == submitted_at
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None
        assert task.worker_id is None
    
    def test_wait_time_property(self):
        """Test wait time calculation."""
        submitted_at = datetime.utcnow()
        started_at = submitted_at + timedelta(seconds=10)
        
        task = WorkerTask(
            task_id="task-123",
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=lambda x: x,
            priority=ProcessorPriority.NORMAL,
            timeout=300.0,
            submitted_at=submitted_at,
            started_at=started_at
        )
        
        wait_time = task.wait_time
        assert wait_time is not None
        assert abs(wait_time - 10.0) < 0.1
    
    def test_wait_time_no_start(self):
        """Test wait time when task hasn't started."""
        task = WorkerTask(
            task_id="task-123",
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=lambda x: x,
            priority=ProcessorPriority.NORMAL,
            timeout=300.0,
            submitted_at=datetime.utcnow()
        )
        
        assert task.wait_time is None
    
    def test_processing_time_property(self):
        """Test processing time calculation."""
        submitted_at = datetime.utcnow()
        started_at = submitted_at + timedelta(seconds=5)
        completed_at = started_at + timedelta(seconds=15)
        
        task = WorkerTask(
            task_id="task-123",
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=lambda x: x,
            priority=ProcessorPriority.NORMAL,
            timeout=300.0,
            submitted_at=submitted_at,
            started_at=started_at,
            completed_at=completed_at
        )
        
        processing_time = task.processing_time
        assert processing_time is not None
        assert abs(processing_time - 15.0) < 0.1


class TestWorkerStats:
    """Test WorkerStats dataclass."""
    
    def test_create_worker_stats(self):
        """Test creating worker statistics."""
        stats = WorkerStats(
            worker_id="worker-1",
            worker_type=WorkerType.ASYNC,
            status=WorkerStatus.IDLE,
            tasks_completed=10,
            tasks_failed=2,
            total_processing_time=120.5
        )
        
        assert stats.worker_id == "worker-1"
        assert stats.worker_type == WorkerType.ASYNC
        assert stats.status == WorkerStatus.IDLE
        assert stats.tasks_completed == 10
        assert stats.tasks_failed == 2
        assert stats.total_processing_time == 120.5
    
    def test_average_processing_time(self):
        """Test average processing time calculation."""
        stats = WorkerStats(
            worker_id="worker-1",
            worker_type=WorkerType.ASYNC,
            status=WorkerStatus.IDLE,
            tasks_completed=5,
            total_processing_time=100.0
        )
        
        assert stats.average_processing_time == 20.0
    
    def test_average_processing_time_no_tasks(self):
        """Test average processing time with no completed tasks."""
        stats = WorkerStats(
            worker_id="worker-1",
            worker_type=WorkerType.ASYNC,
            status=WorkerStatus.IDLE,
            tasks_completed=0,
            total_processing_time=0.0
        )
        
        assert stats.average_processing_time == 0.0


class TestWorkerPool:
    """Test WorkerPool class."""
    
    @pytest.fixture
    def config(self):
        """Create test worker configuration."""
        return WorkerConfig(
            async_workers=2,
            thread_workers=1,
            process_workers=0,
            max_queue_size=10,
            priority_queue_size=5,
            default_timeout=30.0,
            worker_heartbeat_interval=1.0
        )
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        return AsyncMock()
    
    @pytest.fixture
    def resource_monitor(self):
        """Create mock resource monitor."""
        monitor = Mock(spec=ResourceMonitor)
        monitor.check_availability = AsyncMock(return_value=(True, None))
        monitor.allocate = AsyncMock(return_value=True)
        monitor.release = AsyncMock()
        monitor.get_current_usage = Mock(return_value={})
        return monitor
    
    @pytest.fixture
    def progress_tracker(self):
        """Create mock progress tracker."""
        tracker = Mock(spec=ProgressTracker)
        tracker.start_task = AsyncMock()
        tracker.update_task = AsyncMock()
        tracker.complete_task = AsyncMock()
        return tracker
    
    @pytest.fixture
    def pool(self, config, event_bus, resource_monitor, progress_tracker):
        """Create test worker pool."""
        return WorkerPool(
            config=config,
            event_bus=event_bus,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
    
    def test_initialization(self, pool, config, event_bus, resource_monitor, progress_tracker):
        """Test worker pool initialization."""
        assert pool.config == config
        assert pool.event_bus == event_bus
        assert pool.resource_monitor == resource_monitor
        assert pool.progress_tracker == progress_tracker
        assert pool.async_workers == []
        assert pool.thread_pool is None
        assert pool.process_pool is None
        assert not pool._running
        assert pool._total_tasks_submitted == 0
        assert pool._total_tasks_completed == 0
        assert pool._total_tasks_failed == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, pool):
        """Test starting and stopping worker pool."""
        assert not pool._running
        
        # Start pool
        await pool.start()
        assert pool._running
        assert len(pool.async_workers) == 2  # From config
        assert pool.thread_pool is not None
        assert pool._start_time is not None
        
        # Give workers a moment to start
        await asyncio.sleep(0.1)
        
        # Stop pool
        await pool.stop()
        assert not pool._running
        assert len(pool.async_workers) == 0
        assert pool.thread_pool is None
    
    @pytest.mark.asyncio
    async def test_double_start(self, pool):
        """Test that starting an already running pool is safe."""
        await pool.start()
        
        # Starting again should not raise an error
        await pool.start()
        assert pool._running
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_submit_task_basic(self, pool):
        """Test basic task submission."""
        async def dummy_processor(context):
            return "test_result"
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="test_processor",
            context=MockProcessorContext(),
            processor_func=dummy_processor,
            priority=ProcessorPriority.NORMAL
        )
        
        assert isinstance(task_id, str)
        assert task_id in pool.active_tasks
        assert pool._total_tasks_submitted == 1
        
        # Check that progress tracking was started
        pool.progress_tracker.start_task.assert_called_once()
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_submit_task_pool_not_running(self, pool):
        """Test submitting task when pool is not running."""
        async def dummy_processor(context):
            return "result"
        
        with pytest.raises(WorkerPoolError, match="Worker pool is not running"):
            await pool.submit_task(
                processor_name="test",
                context=MockProcessorContext(),
                processor_func=dummy_processor
            )
    
    @pytest.mark.asyncio
    async def test_submit_task_with_resources(self, pool):
        """Test submitting task with resource requirements."""
        async def dummy_processor(context):
            return "result"
        
        await pool.start()
        
        required_resources = {
            ResourceType.CPU: 10.0,
            ResourceType.MEMORY: 20.0
        }
        
        task_id = await pool.submit_task(
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=dummy_processor,
            required_resources=required_resources
        )
        
        # Check resource allocation was attempted
        pool.resource_monitor.check_availability.assert_called_once_with(required_resources)
        pool.resource_monitor.allocate.assert_called_once_with(task_id, required_resources)
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_submit_task_insufficient_resources(self, pool):
        """Test submitting task when resources are insufficient."""
        pool.resource_monitor.check_availability.return_value = (False, "Insufficient CPU")
        
        async def dummy_processor(context):
            return "result"
        
        await pool.start()
        
        with pytest.raises(ResourceError, match="Insufficient resources"):
            await pool.submit_task(
                processor_name="test",
                context=MockProcessorContext(),
                processor_func=dummy_processor,
                required_resources={ResourceType.CPU: 100.0}
            )
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_submit_task_priority_queue(self, pool):
        """Test submitting critical priority task."""
        async def dummy_processor(context):
            return "result"
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="critical_task",
            context=MockProcessorContext(),
            processor_func=dummy_processor,
            priority=ProcessorPriority.CRITICAL
        )
        
        assert task_id in pool.active_tasks
        # Critical tasks should go to priority queue
        assert pool.priority_queue.qsize() > 0 or pool.task_queue.qsize() == 0
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_process_task_success(self, pool):
        """Test successful task processing."""
        result_value = "test_result"
        
        async def dummy_processor(context):
            await asyncio.sleep(0.1)  # Simulate work
            return result_value
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=dummy_processor
        )
        
        # Wait for task to complete
        await asyncio.sleep(0.5)
        
        # Task should be moved to completed
        assert task_id not in pool.active_tasks
        completed_task = next(
            (t for t in pool.completed_tasks if t.task_id == task_id), 
            None
        )
        assert completed_task is not None
        assert completed_task.result == result_value
        assert completed_task.error is None
        assert pool._total_tasks_completed == 1
        
        # Check progress tracking was completed
        pool.progress_tracker.complete_task.assert_called_with(task_id, True, None)
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_process_task_failure(self, pool):
        """Test task processing failure."""
        error_message = "Task failed"
        
        async def failing_processor(context):
            raise ValueError(error_message)
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="failing_task",
            context=MockProcessorContext(),
            processor_func=failing_processor
        )
        
        # Wait for task to fail
        await asyncio.sleep(0.5)
        
        # Task should be moved to completed with error
        assert task_id not in pool.active_tasks
        completed_task = next(
            (t for t in pool.completed_tasks if t.task_id == task_id), 
            None
        )
        assert completed_task is not None
        assert completed_task.result is None
        assert error_message in completed_task.error
        assert pool._total_tasks_failed == 1
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_process_task_timeout(self, pool):
        """Test task timeout handling."""
        async def slow_processor(context):
            await asyncio.sleep(1.0)  # Longer than timeout
            return "result"
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="slow_task",
            context=MockProcessorContext(),
            processor_func=slow_processor,
            timeout=0.1  # Very short timeout
        )
        
        # Wait for timeout
        await asyncio.sleep(0.5)
        
        # Task should have failed with timeout
        completed_task = next(
            (t for t in pool.completed_tasks if t.task_id == task_id), 
            None
        )
        assert completed_task is not None
        assert "timed out" in completed_task.error.lower()
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_get_task_result_success(self, pool):
        """Test getting successful task result."""
        result_value = "test_result"
        
        async def dummy_processor(context):
            return result_value
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=dummy_processor
        )
        
        # Get result (should wait for completion)
        result = await pool.get_task_result(task_id, timeout=1.0)
        assert result == result_value
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_get_task_result_failure(self, pool):
        """Test getting result for failed task."""
        async def failing_processor(context):
            raise ValueError("Task failed")
        
        await pool.start()
        
        task_id = await pool.submit_task(
            processor_name="failing",
            context=MockProcessorContext(),
            processor_func=failing_processor
        )
        
        # Getting result should raise the task error
        with pytest.raises(TaskError, match="Task failed"):
            await pool.get_task_result(task_id, timeout=1.0)
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_get_task_result_not_found(self, pool):
        """Test getting result for non-existent task."""
        with pytest.raises(TaskError, match="not found"):
            await pool.get_task_result("nonexistent-task")
    
    def test_get_pool_stats(self, pool):
        """Test getting pool statistics."""
        # Add some test data
        pool.worker_stats["worker-1"] = WorkerStats(
            worker_id="worker-1",
            worker_type=WorkerType.ASYNC,
            status=WorkerStatus.BUSY
        )
        pool.worker_stats["worker-2"] = WorkerStats(
            worker_id="worker-2",
            worker_type=WorkerType.ASYNC,
            status=WorkerStatus.IDLE
        )
        
        # Add completed task for timing stats
        completed_task = WorkerTask(
            task_id="completed",
            processor_name="test",
            context=MockProcessorContext(),
            processor_func=lambda x: x,
            priority=ProcessorPriority.NORMAL,
            timeout=300.0,
            submitted_at=datetime.utcnow() - timedelta(seconds=20),
            started_at=datetime.utcnow() - timedelta(seconds=15),
            completed_at=datetime.utcnow() - timedelta(seconds=5)
        )
        pool.completed_tasks.append(completed_task)
        
        stats = pool.get_pool_stats()
        
        assert isinstance(stats, PoolStats)
        assert stats.total_workers == 2
        assert stats.active_workers == 1
        assert stats.idle_workers == 1
        assert stats.completed_tasks == 0  # Pool totals not set in this test
        assert stats.failed_tasks == 0
        assert isinstance(stats.average_wait_time, float)
        assert isinstance(stats.average_processing_time, float)
    
    @pytest.mark.asyncio
    async def test_worker_status_updates(self, pool):
        """Test worker status updates."""
        await pool.start()
        
        # Workers should start as idle
        worker_ids = list(pool.worker_stats.keys())
        assert len(worker_ids) == 2  # From config
        
        for worker_id in worker_ids:
            stats = pool.worker_stats[worker_id]
            assert stats.status in [WorkerStatus.IDLE, WorkerStatus.BUSY]
            assert stats.worker_type == WorkerType.ASYNC
        
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_task_processing(self, pool):
        """Test processing multiple tasks concurrently."""
        async def numbered_processor(context):
            # Extract number from document_id for result
            doc_id = context.document_id
            number = int(doc_id.split('-')[-1])
            await asyncio.sleep(0.1)  # Simulate work
            return f"result-{number}"
        
        await pool.start()
        
        # Submit multiple tasks
        task_ids = []
        for i in range(5):
            task_id = await pool.submit_task(
                processor_name="numbered",
                context=MockProcessorContext(f"doc-{i}"),
                processor_func=numbered_processor
            )
            task_ids.append(task_id)
        
        # Wait for all tasks to complete
        await asyncio.sleep(1.0)
        
        # All tasks should be completed
        assert len(pool.completed_tasks) == 5
        assert len(pool.active_tasks) == 0
        
        # Check results
        results = {}
        for task in pool.completed_tasks:
            if task.task_id in task_ids:
                results[task.task_id] = task.result
        
        assert len(results) == 5
        
        await pool.stop()
    
    def test_string_representation(self, pool):
        """Test string representation of worker pool."""
        pool._total_tasks_completed = 10
        pool._total_tasks_failed = 2
        
        str_repr = str(pool)
        assert "WorkerPool" in str_repr
        assert "completed=10" in str_repr


@pytest.mark.asyncio
class TestWorkerPoolIntegration:
    """Integration tests for worker pool."""
    
    async def test_full_lifecycle_with_real_components(self):
        """Test worker pool with real resource monitor and progress tracker."""
        config = WorkerConfig(
            async_workers=1,
            thread_workers=0,
            process_workers=0,
            max_queue_size=5,
            default_timeout=10.0
        )
        
        # Create real components
        resource_limits = ResourceLimits()
        resource_monitor = ResourceMonitor(resource_limits, check_interval=0.1)
        progress_tracker = ProgressTracker()
        event_bus = AsyncMock()
        
        pool = WorkerPool(
            config=config,
            event_bus=event_bus,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
        
        try:
            # Start components
            await resource_monitor.start()
            await pool.start()
            
            # Submit and process a task
            async def test_processor(context):
                return f"processed-{context.document_id}"
            
            task_id = await pool.submit_task(
                processor_name="integration_test",
                context=MockProcessorContext("test-doc"),
                processor_func=test_processor
            )
            
            # Wait for completion
            result = await pool.get_task_result(task_id, timeout=5.0)
            assert result == "processed-test-doc"
            
            # Check statistics
            stats = pool.get_pool_stats()
            assert stats.completed_tasks == 1
            
            # Check progress tracking
            task_progress = await progress_tracker.get_task_progress(task_id)
            assert task_progress is not None
            assert task_progress.status == "completed"
            
        finally:
            # Cleanup
            await pool.stop()
            await resource_monitor.stop()
    
    async def test_resource_management_integration(self):
        """Test integration with resource management."""
        config = WorkerConfig(async_workers=1, thread_workers=0, process_workers=0)
        resource_limits = ResourceLimits(max_cpu_percent=50.0, max_memory_percent=50.0)
        resource_monitor = ResourceMonitor(resource_limits)
        
        pool = WorkerPool(
            config=config,
            resource_monitor=resource_monitor
        )
        
        try:
            await resource_monitor.start()
            await pool.start()
            
            # Submit task with resource requirements
            async def resource_task(context):
                return "result"
            
            task_id = await pool.submit_task(
                processor_name="resource_test",
                context=MockProcessorContext(),
                processor_func=resource_task,
                required_resources={
                    ResourceType.CPU: 10.0,
                    ResourceType.MEMORY: 15.0
                }
            )
            
            # Task should complete successfully
            result = await pool.get_task_result(task_id, timeout=5.0)
            assert result == "result"
            
        finally:
            await pool.stop()
            await resource_monitor.stop()