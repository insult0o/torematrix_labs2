"""Integration tests for Pipeline Manager and Worker Pool interaction."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Import components
from torematrix.processing.pipeline.manager import PipelineManager, PipelineConfig, PipelineContext
from torematrix.processing.pipeline.config import StageConfig, StageType, ResourceRequirements
from torematrix.processing.workers.pool import WorkerPool
from torematrix.processing.workers.config import WorkerConfig, ResourceLimits
from torematrix.processing.workers.progress import ProgressTracker
from torematrix.processing.workers.resources import ResourceMonitor
from torematrix.processing.processors.base import ProcessorContext, ProcessorResult, ProcessorMetadata
from torematrix.processing.integration import ProcessingSystem, ProcessingSystemConfig


class MockEventBus:
    """Mock event bus for testing."""
    
    def __init__(self):
        self.events = []
    
    async def publish(self, event):
        """Publish an event."""
        self.events.append(event)
    
    async def emit(self, event):
        """Emit an event."""
        self.events.append(event)


class MockProcessor:
    """Mock processor for testing."""
    
    def __init__(self, name: str = "test_processor"):
        self.name = name
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Mock process method."""
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        return ProcessorResult(
            processor_name=self.name,
            status="completed",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"processed": True, "document_id": context.document_id},
            metadata={"processor": self.name}
        )


@pytest.mark.asyncio
class TestPipelineWorkerIntegration:
    """Integration tests for pipeline and worker pool."""
    
    @pytest.fixture
    async def event_bus(self):
        """Create mock event bus."""
        return MockEventBus()
    
    @pytest.fixture
    async def worker_config(self):
        """Create worker configuration."""
        return WorkerConfig(
            async_workers=2,
            thread_workers=1,
            process_workers=0,
            max_queue_size=10,
            default_timeout=30.0
        )
    
    @pytest.fixture
    async def resource_limits(self):
        """Create resource limits."""
        return ResourceLimits()
    
    @pytest.fixture
    async def pipeline_config(self):
        """Create pipeline configuration."""
        return PipelineConfig(
            name="test_pipeline",
            stages=[
                StageConfig(
                    name="process_stage",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    dependencies=[],
                    resources=ResourceRequirements()
                )
            ]
        )
    
    @pytest.fixture
    async def worker_pool(self, worker_config, event_bus, resource_limits):
        """Create and start worker pool."""
        resource_monitor = ResourceMonitor(resource_limits)
        progress_tracker = ProgressTracker(event_bus)
        
        pool = WorkerPool(
            config=worker_config,
            event_bus=event_bus,
            resource_monitor=resource_monitor,
            progress_tracker=progress_tracker
        )
        
        await resource_monitor.start()
        await pool.start()
        
        yield pool
        
        await pool.stop()
        await resource_monitor.stop()
    
    @pytest.fixture
    async def pipeline_manager(self, pipeline_config, event_bus):
        """Create pipeline manager."""
        # Mock state store for testing
        state_store = MagicMock()
        state_store.get = AsyncMock(return_value=None)
        state_store.set = AsyncMock()
        
        return PipelineManager(
            config=pipeline_config,
            event_bus=event_bus,
            state_store=state_store
        )
    
    async def test_worker_pool_integration_methods(self, worker_pool):
        """Test that worker pool has required integration methods."""
        # Test get_stats method
        stats = worker_pool.get_stats()
        assert isinstance(stats, dict)
        assert "total_workers" in stats
        assert "active_workers" in stats
        assert "queued_tasks" in stats
        assert "completed_tasks" in stats
        
        # Test wait_for_completion method
        completion_result = await worker_pool.wait_for_completion(timeout=1.0)
        assert isinstance(completion_result, bool)
    
    async def test_task_submission_with_processor_context(self, worker_pool):
        """Test submitting tasks with ProcessorContext objects."""
        # Create a ProcessorContext similar to what Agent 2 would provide
        context = ProcessorContext(
            document_id="test-doc-123",
            file_path="/path/to/test.pdf",
            mime_type="application/pdf",
            metadata={"source": "test"},
            previous_results={}
        )
        
        # Create a mock processor function
        async def mock_processor(ctx):
            assert isinstance(ctx, ProcessorContext)
            assert ctx.document_id == "test-doc-123"
            return {"status": "processed", "document_id": ctx.document_id}
        
        # Submit task
        task_id = await worker_pool.submit_task(
            processor_name="test_processor",
            context=context,
            processor_func=mock_processor
        )
        
        # Wait for completion and get result
        result = await worker_pool.get_task_result(task_id, timeout=10.0)
        
        assert result["status"] == "processed"
        assert result["document_id"] == "test-doc-123"
    
    async def test_pipeline_worker_end_to_end(self, worker_pool, pipeline_manager):
        """Test end-to-end pipeline execution with worker pool."""
        # Create a document processing pipeline
        document_id = "test-document"
        metadata = {"test": True}
        
        # Create pipeline instance
        pipeline_id = await pipeline_manager.create_pipeline(
            document_id=document_id,
            metadata=metadata
        )
        
        # Mock the stage execution to use our worker pool
        original_execute_stage = pipeline_manager._execute_stage
        
        async def mock_execute_stage(stage_name: str, context: PipelineContext):
            """Mock stage execution that uses the worker pool."""
            # Create ProcessorContext from PipelineContext
            processor_context = ProcessorContext(
                document_id=context.document_id,
                file_path=f"/path/to/{context.document_id}.pdf",
                mime_type="application/pdf",
                metadata=context.metadata,
                pipeline_context=context
            )
            
            # Submit to worker pool
            task_id = await worker_pool.submit_task(
                processor_name="test_processor",
                context=processor_context,
                processor_func=MockProcessor().process
            )
            
            # Get result
            result = await worker_pool.get_task_result(task_id, timeout=30.0)
            
            # Convert to stage result
            from torematrix.processing.pipeline.stages import StageResult, StageStatus
            context.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                data=result.extracted_data if hasattr(result, 'extracted_data') else result
            )
        
        # Replace the stage execution method
        pipeline_manager._execute_stage = mock_execute_stage
        
        try:
            # Execute pipeline
            result_context = await pipeline_manager.execute(pipeline_id=pipeline_id)
            
            # Verify results
            assert result_context.pipeline_id == pipeline_id
            assert result_context.document_id == document_id
            assert len(result_context.stage_results) > 0
            
            # Check that stage completed successfully
            stage_result = list(result_context.stage_results.values())[0]
            assert stage_result.status.value == "completed"
            
        finally:
            # Restore original method
            pipeline_manager._execute_stage = original_execute_stage
    
    async def test_resource_integration(self, worker_pool, resource_limits):
        """Test that worker pool integrates with resource monitoring."""
        # Get resource monitor from worker pool
        resource_monitor = worker_pool.resource_monitor
        assert resource_monitor is not None
        
        # Test resource allocation
        from torematrix.processing.workers.config import ResourceType
        
        resources = {
            ResourceType.CPU: 10.0,
            ResourceType.MEMORY: 20.0
        }
        
        # Check availability
        available, reason = await resource_monitor.check_availability(resources)
        assert available is True
        assert reason is None
        
        # Allocate resources
        success = await resource_monitor.allocate("test-task", resources)
        assert success is True
        
        # Release resources
        await resource_monitor.release("test-task")
    
    async def test_progress_tracking_integration(self, worker_pool):
        """Test that worker pool integrates with progress tracking."""
        progress_tracker = worker_pool.progress_tracker
        assert progress_tracker is not None
        
        # Test progress tracking for a task
        context = ProcessorContext(
            document_id="progress-test-doc",
            file_path="/path/to/progress.pdf",
            mime_type="application/pdf"
        )
        
        async def progress_processor(ctx):
            # Simulate progress updates
            await progress_tracker.update_task(
                task_id="progress-task",
                progress=0.5,
                message="Processing..."
            )
            return {"progress": "complete"}
        
        # Submit task
        task_id = await worker_pool.submit_task(
            processor_name="progress_processor",
            context=context,
            processor_func=progress_processor
        )
        
        # Wait for completion
        result = await worker_pool.get_task_result(task_id, timeout=10.0)
        
        # Check progress tracking
        final_progress = await progress_tracker.get_task_progress(task_id)
        assert final_progress is not None
        assert final_progress.status == "completed"
    
    async def test_concurrent_pipeline_execution(self, worker_pool):
        """Test concurrent execution of multiple pipeline-style tasks."""
        contexts = []
        task_ids = []
        
        # Create multiple processing contexts
        for i in range(5):
            context = ProcessorContext(
                document_id=f"concurrent-doc-{i}",
                file_path=f"/path/to/doc{i}.pdf",
                mime_type="application/pdf",
                metadata={"index": i}
            )
            contexts.append(context)
        
        # Submit all tasks
        for i, context in enumerate(contexts):
            async def numbered_processor(ctx, num=i):
                await asyncio.sleep(0.1)  # Simulate work
                return {"document": ctx.document_id, "number": num}
            
            task_id = await worker_pool.submit_task(
                processor_name=f"processor_{i}",
                context=context,
                processor_func=numbered_processor
            )
            task_ids.append(task_id)
        
        # Wait for all results
        results = []
        for task_id in task_ids:
            result = await worker_pool.get_task_result(task_id, timeout=30.0)
            results.append(result)
        
        # Verify all completed
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["number"] == i
            assert f"concurrent-doc-{i}" in result["document"]


@pytest.mark.asyncio
class TestProcessingSystemIntegration:
    """Test full processing system integration."""
    
    async def test_processing_system_initialization(self):
        """Test that ProcessingSystem can initialize with all components."""
        # Create minimal configuration
        config = ProcessingSystemConfig(
            pipeline_config=PipelineConfig(
                name="test_pipeline",
                stages=[
                    StageConfig(
                        name="test_stage",
                        type=StageType.PROCESSOR,
                        processor="test_processor"
                    )
                ]
            ),
            worker_config=WorkerConfig(
                async_workers=1,
                thread_workers=0,
                process_workers=0
            ),
            resource_limits=ResourceLimits(),
            monitoring_enabled=False,  # Disable monitoring for simpler test
            state_persistence_enabled=False  # Disable persistence for testing
        )
        
        # Create processing system
        system = ProcessingSystem(config)
        
        # Test initialization
        await system.initialize()
        
        try:
            # Verify components are initialized
            assert system._running is True
            assert system.worker_pool._running is True
            assert system.resource_monitor._monitoring is True
            
            # Test system metrics
            metrics = system.get_system_metrics()
            assert "workers" in metrics
            assert "resources" in metrics
            assert "progress" in metrics
            assert "system" in metrics
            
            # Test health status
            health = system.get_health_status()
            assert "healthy" in health
            assert "services" in health
            assert "worker_pool" in health["services"]
            assert "resource_monitor" in health["services"]
            
        finally:
            # Clean shutdown
            await system.shutdown()
            
            # Verify shutdown
            assert system._running is False
    
    async def test_wait_for_completion_integration(self):
        """Test wait_for_completion method in shutdown scenario."""
        config = ProcessingSystemConfig(
            pipeline_config=PipelineConfig(name="test", stages=[]),
            worker_config=WorkerConfig(async_workers=1),
            resource_limits=ResourceLimits(),
            monitoring_enabled=False,
            state_persistence_enabled=False
        )
        
        system = ProcessingSystem(config)
        await system.initialize()
        
        try:
            # Test wait_for_completion method exists and works
            completion_result = await system.worker_pool.wait_for_completion(timeout=1.0)
            assert isinstance(completion_result, bool)
            assert completion_result is True  # Should be True since no active tasks
            
        finally:
            await system.shutdown()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])