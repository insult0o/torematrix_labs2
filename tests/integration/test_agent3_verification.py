"""Agent 3 Worker Pool & Progress Tracking - Post-Agent 1 Integration Verification."""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from torematrix.processing.workers import (
    WorkerPool, WorkerConfig, ProgressTracker, ResourceMonitor, ResourceLimits, ResourceType
)
from torematrix.processing.processors.base import ProcessorContext


class MockEventBus:
    """Mock event bus that doesn't require external dependencies."""
    
    def __init__(self):
        self.events = []
    
    async def publish(self, event):
        self.events.append(event)
    
    async def emit(self, event):
        self.events.append(event)


@pytest.mark.asyncio
class TestAgent3IntegrationVerification:
    """Verify Agent 3 components work correctly with Agent 1's interfaces."""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MockEventBus()
    
    @pytest_asyncio.fixture
    async def worker_system(self, mock_event_bus):
        """Create integrated worker system."""
        config = WorkerConfig(
            async_workers=2,
            thread_workers=1,
            process_workers=0,
            max_queue_size=20,
            default_timeout=30.0
        )
        
        resource_limits = ResourceLimits()
        resource_monitor = ResourceMonitor(resource_limits)
        progress_tracker = ProgressTracker(mock_event_bus)
        
        worker_pool = WorkerPool(
            config=config,
            event_bus=mock_event_bus,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
        
        # Start components
        await resource_monitor.start()
        await worker_pool.start()
        
        yield {
            'pool': worker_pool,
            'resource_monitor': resource_monitor,
            'progress_tracker': progress_tracker,
            'event_bus': mock_event_bus,
            'config': config
        }
        
        # Cleanup
        await worker_pool.stop()
        await resource_monitor.stop()
    
    async def test_integration_method_compatibility(self, worker_system):
        """Test that required integration methods exist and work correctly."""
        pool = worker_system['pool']
        
        # Test get_stats() method - required by integration.py line 258
        stats = pool.get_stats()
        assert isinstance(stats, dict)
        
        # Verify required keys for ProcessingSystem.get_system_metrics()
        required_keys = [
            'total_workers', 'active_workers', 'idle_workers',
            'queued_tasks', 'completed_tasks', 'failed_tasks',
            'average_wait_time', 'average_processing_time',
            'resource_utilization', 'uptime_seconds', 'total_tasks_submitted'
        ]
        for key in required_keys:
            assert key in stats, f"Missing required stat key: {key}"
        
        # Test wait_for_completion() method - required by integration.py line 151
        completion_result = await pool.wait_for_completion(timeout=1.0)
        assert isinstance(completion_result, bool)
        assert completion_result is True  # Should be True with no active tasks
    
    async def test_processor_context_compatibility(self, worker_system):
        """Test compatibility with Agent 2's ProcessorContext objects."""
        pool = worker_system['pool']
        
        # Create ProcessorContext as Agent 2 would
        context = ProcessorContext(
            document_id="agent2-doc-123",
            file_path="/path/to/document.pdf",
            mime_type="application/pdf",
            metadata={"source": "agent2", "priority": "high"},
            previous_results={"validation": {"status": "passed"}}
        )
        
        # Mock processor function that Agent 1 would submit
        async def agent1_processor(ctx):
            # Verify context compatibility
            assert hasattr(ctx, 'document_id')
            assert hasattr(ctx, 'file_path')
            assert hasattr(ctx, 'mime_type')
            assert hasattr(ctx, 'metadata')
            assert hasattr(ctx, 'previous_results')
            
            # Simulate processing
            await asyncio.sleep(0.1)
            return {
                "processed_by": "agent1_processor",
                "document_id": ctx.document_id,
                "metadata_keys": list(ctx.metadata.keys()),
                "has_previous_results": len(ctx.previous_results) > 0
            }
        
        # Submit task (how Agent 1 would use the worker pool)
        task_id = await pool.submit_task(
            processor_name="agent1_processor",
            context=context,
            processor_func=agent1_processor
        )
        
        # Get result
        result = await pool.get_task_result(task_id, timeout=10.0)
        
        # Verify result
        assert result["processed_by"] == "agent1_processor"
        assert result["document_id"] == "agent2-doc-123"
        assert "source" in result["metadata_keys"]
        assert result["has_previous_results"] is True
    
    async def test_resource_allocation_integration(self, worker_system):
        """Test resource management integration for pipeline stages."""
        resource_monitor = worker_system['resource_monitor']
        
        # Test resource requirements checking (used by pipeline stages)
        requirements = {
            ResourceType.CPU: 15.0,
            ResourceType.MEMORY: 25.0
        }
        
        # Check availability (called by PipelineManager._execute_stage)
        available, reason = await resource_monitor.check_availability(requirements)
        assert available is True
        assert reason is None
        
        # Allocate resources for stage
        stage_id = "test_stage_execution"
        allocation_success = await resource_monitor.allocate(stage_id, requirements)
        assert allocation_success is True
        
        # Verify allocation tracking
        allocated = resource_monitor.get_allocated_resources()
        assert stage_id in allocated
        assert allocated[stage_id] == requirements
        
        # Release resources after stage completion
        await resource_monitor.release(stage_id)
        
        # Verify release
        allocated_after = resource_monitor.get_allocated_resources()
        assert stage_id not in allocated_after
    
    async def test_progress_tracking_pipeline_integration(self, worker_system):
        """Test progress tracking for pipeline execution."""
        progress_tracker = worker_system['progress_tracker']
        
        # Start pipeline progress tracking
        pipeline_id = "test_pipeline_123"
        document_id = "pipeline_doc_456"
        stages = ["validation", "extraction", "transformation"]
        
        await progress_tracker.start_pipeline(
            pipeline_id=pipeline_id,
            document_id=document_id,
            stages=stages
        )
        
        # Verify pipeline tracking
        pipeline_progress = await progress_tracker.get_pipeline_progress(pipeline_id)
        assert pipeline_progress is not None
        assert pipeline_progress.pipeline_id == pipeline_id
        assert pipeline_progress.total_stages == len(stages)
        assert pipeline_progress.overall_progress == 0.0
        
        # Simulate stage completion
        from torematrix.processing.workers.progress import TaskProgress
        
        for i, stage_name in enumerate(stages):
            # Create task progress for stage
            task_progress = TaskProgress(
                task_id=f"task_{i}",
                processor_name=f"processor_{stage_name}",
                document_id=document_id,
                status="completed",
                progress=1.0,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            # Update pipeline stage
            await progress_tracker.update_pipeline_stage(
                pipeline_id, stage_name, task_progress
            )
        
        # Verify final pipeline state
        final_progress = await progress_tracker.get_pipeline_progress(pipeline_id)
        assert final_progress.completed_stages == len(stages)
        assert final_progress.overall_progress == 1.0
        assert len(final_progress.stage_progress) == len(stages)
    
    async def test_concurrent_pipeline_task_execution(self, worker_system):
        """Test handling multiple pipeline tasks concurrently."""
        pool = worker_system['pool']
        
        # Simulate multiple pipeline stages executing concurrently
        tasks = []
        contexts = []
        
        for i in range(3):
            context = ProcessorContext(
                document_id=f"pipeline_doc_{i}",
                file_path=f"/path/to/doc_{i}.pdf",
                mime_type="application/pdf",
                metadata={"stage": f"stage_{i}", "pipeline_id": "concurrent_test"}
            )
            contexts.append(context)
        
        # Submit tasks for different pipeline stages
        for i, context in enumerate(contexts):
            async def stage_processor(ctx, stage_num=i):
                # Simulate stage processing
                await asyncio.sleep(0.1 + (stage_num * 0.05))
                return {
                    "stage": f"stage_{stage_num}",
                    "document_id": ctx.document_id,
                    "processing_time": 0.1 + (stage_num * 0.05),
                    "status": "completed"
                }
            
            task_id = await pool.submit_task(
                processor_name=f"stage_processor_{i}",
                context=context,
                processor_func=stage_processor
            )
            tasks.append(task_id)
        
        # Wait for all stages to complete
        results = []
        for task_id in tasks:
            result = await pool.get_task_result(task_id, timeout=15.0)
            results.append(result)
        
        # Verify all stages completed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["stage"] == f"stage_{i}"
            assert result["status"] == "completed"
            assert f"pipeline_doc_{i}" in result["document_id"]
    
    async def test_event_bus_integration(self, worker_system):
        """Test event emission for pipeline coordination."""
        event_bus = worker_system['event_bus']
        pool = worker_system['pool']
        
        # Clear previous events
        event_bus.events.clear()
        
        # Submit a task to generate events
        context = ProcessorContext(
            document_id="event_test_doc",
            file_path="/path/to/event_test.pdf",
            mime_type="application/pdf"
        )
        
        async def event_processor(ctx):
            return {"events": "tested"}
        
        task_id = await pool.submit_task(
            processor_name="event_processor",
            context=context,
            processor_func=event_processor
        )
        
        # Wait for completion
        await pool.get_task_result(task_id, timeout=10.0)
        
        # Verify events were emitted
        events = event_bus.events
        assert len(events) > 0
        
        # Check for expected event types
        event_types = [event.get('type') if isinstance(event, dict) else getattr(event, 'event_type', None) for event in events]
        
        # Should have task submission and completion events
        has_submission = any('submit' in str(event_type).lower() for event_type in event_types)
        has_completion = any('complet' in str(event_type).lower() for event_type in event_types)
        
        assert has_submission or has_completion, f"Missing expected events. Got: {event_types}"
    
    async def test_system_metrics_compatibility(self, worker_system):
        """Test metrics format compatibility with ProcessingSystem."""
        pool = worker_system['pool']
        resource_monitor = worker_system['resource_monitor']
        progress_tracker = worker_system['progress_tracker']
        
        # Get metrics in the format expected by ProcessingSystem.get_system_metrics()
        worker_metrics = pool.get_stats()
        resource_metrics = resource_monitor.get_current_usage()
        progress_metrics = progress_tracker.get_statistics()
        
        # Verify worker metrics format
        assert isinstance(worker_metrics, dict)
        assert 'total_workers' in worker_metrics
        assert 'active_workers' in worker_metrics
        assert 'queued_tasks' in worker_metrics
        
        # Verify resource metrics format
        assert isinstance(resource_metrics, dict)
        # Should be empty or contain ResourceType enum values as keys
        
        # Verify progress metrics format
        assert isinstance(progress_metrics, dict)
        assert 'total_tasks' in progress_metrics
        
        # Test metrics aggregation (like ProcessingSystem.get_system_metrics does)
        system_metrics = {
            "workers": worker_metrics,
            "resources": resource_metrics,
            "progress": progress_metrics,
            "system": {"running": True}
        }
        
        assert "workers" in system_metrics
        assert "resources" in system_metrics
        assert "progress" in system_metrics
        assert "system" in system_metrics
    
    async def test_graceful_shutdown_integration(self, worker_system):
        """Test graceful shutdown process used by ProcessingSystem."""
        pool = worker_system['pool']
        
        # Submit a task that will complete quickly
        context = ProcessorContext(
            document_id="shutdown_test_doc",
            file_path="/path/to/shutdown_test.pdf",
            mime_type="application/pdf"
        )
        
        async def quick_processor(ctx):
            await asyncio.sleep(0.1)
            return {"shutdown": "tested"}
        
        task_id = await pool.submit_task(
            processor_name="quick_processor",
            context=context,
            processor_func=quick_processor
        )
        
        # Test wait_for_completion as used in ProcessingSystem.shutdown()
        # This should wait for the active task to complete
        completion_success = await pool.wait_for_completion(timeout=5.0)
        
        # The task should have completed by now
        assert completion_success is True
        
        # Verify task actually completed
        result = await pool.get_task_result(task_id, timeout=1.0)
        assert result["shutdown"] == "tested"


if __name__ == "__main__":
    # Run verification tests
    pytest.main([__file__, "-v"])