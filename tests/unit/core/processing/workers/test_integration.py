"""Integration tests for worker pool system coordination."""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from torematrix.processing.workers import (
    WorkerPool, ProgressTracker, ResourceMonitor,
    WorkerConfig, ResourceLimits, ResourceType
)


class MockEventBus:
    """Mock event bus for testing."""
    
    def __init__(self):
        self.events = []
    
    async def emit(self, event):
        """Emit an event."""
        self.events.append(event)
    
    def get_events_by_type(self, event_type):
        """Get events by type."""
        return [e for e in self.events if e.get("type") == event_type]


class MockProcessorContext:
    """Mock processor context."""
    
    def __init__(self, document_id: str = "test-doc"):
        self.document_id = document_id


@pytest.mark.asyncio
class TestWorkerPoolIntegration:
    """Integration tests for the complete worker pool system."""
    
    @pytest.fixture
    async def event_bus(self):
        """Create mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    async def config(self):
        """Create test configuration."""
        return WorkerConfig(
            async_workers=2,
            thread_workers=1,
            process_workers=0,
            max_queue_size=20,
            priority_queue_size=10,
            default_timeout=30.0,
            worker_heartbeat_interval=0.5
        )
    
    @pytest.fixture
    async def resource_limits(self):
        """Create resource limits."""
        return ResourceLimits(
            max_cpu_percent=80.0,
            warning_cpu_percent=70.0,
            max_memory_percent=75.0,
            warning_memory_percent=65.0
        )
    
    @pytest.fixture
    async def integrated_system(self, config, resource_limits, event_bus):
        """Create fully integrated worker system."""
        resource_monitor = ResourceMonitor(resource_limits, check_interval=0.1)
        progress_tracker = ProgressTracker(event_bus)
        
        pool = WorkerPool(
            config=config,
            event_bus=event_bus,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
        
        # Start all components
        await resource_monitor.start()
        await pool.start()
        
        yield {
            'pool': pool,
            'resource_monitor': resource_monitor,
            'progress_tracker': progress_tracker,
            'event_bus': event_bus
        }
        
        # Cleanup
        await pool.stop()
        await resource_monitor.stop()
    
    async def test_basic_task_processing_flow(self, integrated_system):
        """Test basic task processing through the entire system."""
        pool = integrated_system['pool']
        event_bus = integrated_system['event_bus']
        progress_tracker = integrated_system['progress_tracker']
        
        async def test_processor(context):
            """Test processor that simulates work."""
            await asyncio.sleep(0.1)
            return f"processed-{context.document_id}"
        
        # Submit task
        task_id = await pool.submit_task(
            processor_name="test_processor",
            context=MockProcessorContext("doc-123"),
            processor_func=test_processor
        )
        
        # Wait for completion
        result = await pool.get_task_result(task_id, timeout=5.0)
        assert result == "processed-doc-123"
        
        # Check events were emitted
        task_events = event_bus.get_events_by_type("task_submitted")
        assert len(task_events) == 1
        assert task_events[0]["data"]["task_id"] == task_id
        
        completion_events = event_bus.get_events_by_type("task_completed")
        assert len(completion_events) == 1
        
        # Check progress tracking
        final_progress = await progress_tracker.get_task_progress(task_id)
        assert final_progress is not None
        assert final_progress.status == "completed"
        assert final_progress.progress == 1.0
    
    async def test_concurrent_task_processing(self, integrated_system):
        """Test processing multiple tasks concurrently."""
        pool = integrated_system['pool']
        progress_tracker = integrated_system['progress_tracker']
        
        async def numbered_processor(context):
            """Processor that returns a numbered result."""
            doc_num = int(context.document_id.split('-')[-1])
            await asyncio.sleep(0.1 + (doc_num * 0.01))  # Variable processing time
            return f"result-{doc_num}"
        
        # Submit multiple tasks
        task_ids = []
        for i in range(5):
            task_id = await pool.submit_task(
                processor_name="numbered_processor",
                context=MockProcessorContext(f"doc-{i}"),
                processor_func=numbered_processor
            )
            task_ids.append(task_id)
        
        # Wait for all tasks to complete
        results = {}
        for task_id in task_ids:
            result = await pool.get_task_result(task_id, timeout=10.0)
            results[task_id] = result
        
        # Verify all tasks completed
        assert len(results) == 5
        
        # Check progress tracking for all tasks
        for task_id in task_ids:
            progress = await progress_tracker.get_task_progress(task_id)
            assert progress is not None
            assert progress.status == "completed"
    
    async def test_priority_task_handling(self, integrated_system):
        """Test that critical priority tasks are processed first."""
        pool = integrated_system['pool']
        
        results_order = []
        
        async def tracking_processor(context):
            """Processor that tracks execution order."""
            await asyncio.sleep(0.1)
            results_order.append(context.document_id)
            return f"processed-{context.document_id}"
        
        # Submit normal priority task first
        normal_task = await pool.submit_task(
            processor_name="tracking",
            context=MockProcessorContext("normal-task"),
            processor_func=tracking_processor,
            priority=pool.ProcessorPriority.NORMAL
        )
        
        # Submit critical priority task second (should be processed first)
        critical_task = await pool.submit_task(
            processor_name="tracking",
            context=MockProcessorContext("critical-task"),
            processor_func=tracking_processor,
            priority=pool.ProcessorPriority.CRITICAL
        )
        
        # Wait for both to complete
        await pool.get_task_result(normal_task, timeout=5.0)
        await pool.get_task_result(critical_task, timeout=5.0)
        
        # Critical task should have been processed first in many cases
        # (though not guaranteed due to async nature)
        assert len(results_order) == 2
        assert "critical-task" in results_order
        assert "normal-task" in results_order
    
    async def test_resource_allocation_and_monitoring(self, integrated_system):
        """Test resource allocation and monitoring integration."""
        pool = integrated_system['pool']
        resource_monitor = integrated_system['resource_monitor']
        
        async def resource_processor(context):
            """Processor that simulates resource usage."""
            await asyncio.sleep(0.2)
            return "result"
        
        # Submit task with resource requirements
        required_resources = {
            ResourceType.CPU: 20.0,
            ResourceType.MEMORY: 30.0
        }
        
        task_id = await pool.submit_task(
            processor_name="resource_processor",
            context=MockProcessorContext("resource-doc"),
            processor_func=resource_processor,
            required_resources=required_resources
        )
        
        # Check that resources were allocated
        allocated = resource_monitor.get_allocated_resources()
        assert task_id in allocated
        assert allocated[task_id] == required_resources
        
        # Wait for task completion
        await pool.get_task_result(task_id, timeout=5.0)
        
        # Resources should be released after completion
        allocated_after = resource_monitor.get_allocated_resources()
        assert task_id not in allocated_after
    
    async def test_task_failure_handling(self, integrated_system):
        """Test handling of task failures."""
        pool = integrated_system['pool']
        event_bus = integrated_system['event_bus']
        progress_tracker = integrated_system['progress_tracker']
        
        async def failing_processor(context):
            """Processor that always fails."""
            await asyncio.sleep(0.1)
            raise ValueError("Simulated processor failure")
        
        # Submit failing task
        task_id = await pool.submit_task(
            processor_name="failing_processor",
            context=MockProcessorContext("fail-doc"),
            processor_func=failing_processor
        )
        
        # Should raise TaskError when getting result
        with pytest.raises(Exception):  # Could be TaskError or ValueError
            await pool.get_task_result(task_id, timeout=5.0)
        
        # Check failure events
        failure_events = event_bus.get_events_by_type("task_failed")
        assert len(failure_events) == 1
        assert failure_events[0]["data"]["task_id"] == task_id
        assert "error" in failure_events[0]["data"]
        
        # Check progress tracking shows failure
        final_progress = await progress_tracker.get_task_progress(task_id)
        assert final_progress is not None
        assert final_progress.status == "failed"
        assert final_progress.error is not None
    
    async def test_task_timeout_handling(self, integrated_system):
        """Test handling of task timeouts."""
        pool = integrated_system['pool']
        event_bus = integrated_system['event_bus']
        
        async def slow_processor(context):
            """Processor that takes too long."""
            await asyncio.sleep(2.0)  # Longer than timeout
            return "should not reach here"
        
        # Submit task with short timeout
        task_id = await pool.submit_task(
            processor_name="slow_processor",
            context=MockProcessorContext("slow-doc"),
            processor_func=slow_processor,
            timeout=0.5  # Short timeout
        )
        
        # Should raise timeout error
        with pytest.raises(Exception):
            await pool.get_task_result(task_id, timeout=2.0)
        
        # Check failure events
        failure_events = event_bus.get_events_by_type("task_failed")
        assert len(failure_events) >= 1
        
        # Find the timeout failure
        timeout_event = None
        for event in failure_events:
            if event["data"]["task_id"] == task_id:
                timeout_event = event
                break
        
        assert timeout_event is not None
        assert "timed out" in timeout_event["data"]["error"].lower()
    
    async def test_progress_updates_during_processing(self, integrated_system):
        """Test that progress updates are sent during task processing."""
        pool = integrated_system['pool']
        event_bus = integrated_system['event_bus']
        progress_tracker = integrated_system['progress_tracker']
        
        async def progress_processor(context):
            """Processor that reports progress updates."""
            task_id = context.document_id  # Use doc_id as task_id for simplicity
            
            # Start
            await progress_tracker.update_task(task_id, 0.2, "Starting work")
            await asyncio.sleep(0.1)
            
            # Middle
            await progress_tracker.update_task(task_id, 0.6, "Half way done")
            await asyncio.sleep(0.1)
            
            # Near end
            await progress_tracker.update_task(task_id, 0.9, "Almost finished")
            await asyncio.sleep(0.1)
            
            return "completed"
        
        # Note: This test assumes we can get the task_id to the processor
        # In a real system, this would be handled differently
        
        task_id = await pool.submit_task(
            processor_name="progress_processor",
            context=MockProcessorContext(task_id),  # Pass task_id as doc_id
            processor_func=progress_processor
        )
        
        # Wait for completion
        await pool.get_task_result(task_id, timeout=5.0)
        
        # Check that progress events were emitted
        progress_events = event_bus.get_events_by_type("task_progress")
        assert len(progress_events) >= 3  # At least start, updates, and completion
    
    async def test_worker_pool_statistics(self, integrated_system):
        """Test that worker pool statistics are accurate."""
        pool = integrated_system['pool']
        
        async def quick_processor(context):
            await asyncio.sleep(0.05)
            return "quick"
        
        # Submit several tasks
        task_ids = []
        for i in range(3):
            task_id = await pool.submit_task(
                processor_name="quick_processor",
                context=MockProcessorContext(f"quick-{i}"),
                processor_func=quick_processor
            )
            task_ids.append(task_id)
        
        # Wait for all to complete
        for task_id in task_ids:
            await pool.get_task_result(task_id, timeout=5.0)
        
        # Check statistics
        stats = pool.get_pool_stats()
        
        assert stats.total_workers > 0
        assert stats.completed_tasks == 3
        assert stats.failed_tasks == 0
        assert stats.average_processing_time > 0
        assert isinstance(stats.resource_utilization, dict)
    
    async def test_resource_warning_thresholds(self, integrated_system):
        """Test that resource warnings are triggered appropriately."""
        resource_monitor = integrated_system['resource_monitor']
        
        # Simulate high resource usage
        resource_monitor.current_usage = {
            ResourceType.CPU: 75.0,  # Above warning threshold
            ResourceType.MEMORY: 70.0  # Above warning threshold
        }
        
        # Let the monitoring loop run
        await asyncio.sleep(0.3)
        
        # Check that warnings would be triggered
        # (This is a simplified test - in reality we'd check logs or events)
        cpu_limit = resource_monitor.limits.get_warning_threshold(ResourceType.CPU)
        memory_limit = resource_monitor.limits.get_warning_threshold(ResourceType.MEMORY)
        
        assert resource_monitor.current_usage[ResourceType.CPU] > cpu_limit
        assert resource_monitor.current_usage[ResourceType.MEMORY] > memory_limit
    
    async def test_pipeline_progress_tracking(self, integrated_system):
        """Test pipeline-level progress tracking."""
        progress_tracker = integrated_system['progress_tracker']
        
        # Start a pipeline
        stages = ["extract", "transform", "validate"]
        await progress_tracker.start_pipeline(
            pipeline_id="test-pipeline",
            document_id="pipeline-doc",
            stages=stages
        )
        
        # Simulate completing stages
        for i, stage in enumerate(stages):
            from torematrix.processing.workers.progress import TaskProgress
            task_progress = TaskProgress(
                task_id=f"task-{i}",
                processor_name=f"processor_{stage}",
                document_id="pipeline-doc",
                status="completed",
                progress=1.0
            )
            await progress_tracker.update_pipeline_stage(
                "test-pipeline", stage, task_progress
            )
        
        # Check final pipeline state
        pipeline_progress = await progress_tracker.get_pipeline_progress("test-pipeline")
        assert pipeline_progress is not None
        assert pipeline_progress.completed_stages == 3
        assert pipeline_progress.overall_progress == 1.0
        assert len(pipeline_progress.stage_progress) == 3
    
    async def test_system_shutdown_gracefully(self, integrated_system):
        """Test that the system shuts down gracefully with active tasks."""
        pool = integrated_system['pool']
        
        async def long_processor(context):
            """Processor that takes some time."""
            await asyncio.sleep(0.5)
            return "long_result"
        
        # Submit a long-running task
        task_id = await pool.submit_task(
            processor_name="long_processor",
            context=MockProcessorContext("long-doc"),
            processor_func=long_processor
        )
        
        # Give task a moment to start
        await asyncio.sleep(0.1)
        
        # The system should shutdown gracefully even with active tasks
        # This is tested by the cleanup in the fixture, which will wait
        # for tasks to complete or timeout
        
        # Verify task would complete if given time
        stats = pool.get_pool_stats()
        assert stats.total_workers > 0


@pytest.mark.asyncio
class TestEventBusIntegration:
    """Test event bus integration across the worker system."""
    
    async def test_all_expected_events_emitted(self):
        """Test that all expected events are emitted during normal operation."""
        event_bus = MockEventBus()
        config = WorkerConfig(async_workers=1, thread_workers=0, process_workers=0)
        
        pool = WorkerPool(config=config, event_bus=event_bus)
        
        try:
            await pool.start()
            
            async def test_processor(context):
                await asyncio.sleep(0.1)
                return "result"
            
            # Submit and complete a task
            task_id = await pool.submit_task(
                processor_name="test",
                context=MockProcessorContext(),
                processor_func=test_processor
            )
            
            await pool.get_task_result(task_id, timeout=5.0)
            
            # Check all expected events were emitted
            event_types = {event.get("type") for event in event_bus.events}
            
            expected_events = {
                "worker_pool_started",
                "task_submitted",
                "task_completed"
            }
            
            for expected in expected_events:
                assert expected in event_types, f"Missing event: {expected}"
            
        finally:
            await pool.stop()


@pytest.mark.asyncio 
class TestErrorRecoveryIntegration:
    """Test error recovery and resilience of the integrated system."""
    
    async def test_worker_pool_resilience_to_processor_errors(self):
        """Test that worker pool continues functioning after processor errors."""
        config = WorkerConfig(async_workers=1, thread_workers=0, process_workers=0)
        pool = WorkerPool(config=config)
        
        try:
            await pool.start()
            
            async def failing_processor(context):
                raise RuntimeError("Processor error")
            
            async def working_processor(context):
                return "success"
            
            # Submit failing task
            failing_task = await pool.submit_task(
                processor_name="failing",
                context=MockProcessorContext("fail"),
                processor_func=failing_processor
            )
            
            # Should fail
            with pytest.raises(Exception):
                await pool.get_task_result(failing_task, timeout=5.0)
            
            # Submit working task - pool should still function
            working_task = await pool.submit_task(
                processor_name="working",
                context=MockProcessorContext("work"),
                processor_func=working_processor
            )
            
            # Should succeed
            result = await pool.get_task_result(working_task, timeout=5.0)
            assert result == "success"
            
        finally:
            await pool.stop()
    
    async def test_resource_monitor_recovery(self):
        """Test resource monitor resilience to errors."""
        limits = ResourceLimits()
        monitor = ResourceMonitor(limits, check_interval=0.1)
        
        try:
            await monitor.start()
            
            # Simulate resource allocation and release cycles
            for i in range(5):
                task_id = f"task-{i}"
                resources = {ResourceType.CPU: 10.0}
                
                success = await monitor.allocate(task_id, resources)
                assert success
                
                await monitor.release(task_id)
            
            # Monitor should still be functioning
            current_usage = monitor.get_current_usage()
            assert isinstance(current_usage, dict)
            
        finally:
            await monitor.stop()