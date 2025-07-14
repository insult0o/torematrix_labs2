"""
Comprehensive integration test for Issue #8 - Processing Pipeline Architecture.

Tests the compatibility, interoperability, and flow between all components:
- Agent 1: Pipeline Manager & DAG Architecture
- Agent 2: Processor Plugin System
- Agent 3: Worker Pool & Progress Tracking
- Agent 4: Integration & Monitoring
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import json
import yaml
from datetime import datetime
import logging

# Import all major components
from torematrix.processing.pipeline import (
    PipelineManager,
    PipelineConfig,
    StageConfig,
    StageType,
    create_pipeline_from_template
)
from torematrix.processing.processors import (
    ProcessorRegistry,
    BaseProcessor,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    get_registry
)
from torematrix.processing.workers import (
    WorkerPool,
    WorkerConfig,
    Task,
    TaskPriority,
    ResourceLimits
)
from torematrix.processing.progress import (
    ProgressTracker,
    ProgressEvent,
    ProgressEventType
)
from torematrix.processing.monitoring import (
    MonitoringService,
    MetricType
)
from torematrix.processing.integration import (
    ProcessingSystem,
    ProcessingSystemConfig
)
from torematrix.core.events import EventBus, Event
from torematrix.core.state import StateStore

logger = logging.getLogger(__name__)


class TestProcessorForIntegration(BaseProcessor):
    """Test processor for integration testing."""
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Simple processing that adds metadata."""
        await asyncio.sleep(0.1)  # Simulate work
        
        return ProcessorResult(
            processor_name="test_processor",
            success=True,
            data={
                "processed": True,
                "timestamp": datetime.utcnow().isoformat(),
                "input_data": context.data
            },
            metadata={
                "duration": 0.1,
                "test": True
            }
        )
    
    def get_capabilities(self) -> List[ProcessorCapability]:
        return [ProcessorCapability.TEXT_EXTRACTION]


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for the complete pipeline system."""
    
    @pytest.fixture
    async def event_bus(self):
        """Create event bus for testing."""
        return EventBus()
    
    @pytest.fixture
    async def state_store(self):
        """Create state store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir))
            yield store
    
    @pytest.fixture
    async def monitoring_service(self, event_bus):
        """Create monitoring service."""
        service = MonitoringService(event_bus)
        await service.start()
        yield service
        await service.stop()
    
    @pytest.fixture
    async def worker_pool(self, event_bus):
        """Create worker pool."""
        config = WorkerConfig(
            max_workers=4,
            worker_type="async",
            resource_limits=ResourceLimits(
                max_cpu_percent=80.0,
                max_memory_mb=1024
            )
        )
        pool = WorkerPool(config, event_bus)
        await pool.start()
        yield pool
        await pool.stop()
    
    @pytest.fixture
    async def progress_tracker(self, event_bus):
        """Create progress tracker."""
        tracker = ProgressTracker(event_bus)
        return tracker
    
    @pytest.fixture
    def processor_registry(self):
        """Setup processor registry with test processor."""
        registry = get_registry()
        registry.register("test_processor", TestProcessorForIntegration)
        return registry
    
    @pytest.mark.asyncio
    async def test_full_pipeline_flow(
        self,
        event_bus,
        state_store,
        monitoring_service,
        worker_pool,
        progress_tracker,
        processor_registry
    ):
        """Test complete pipeline flow from start to finish."""
        # Create pipeline configuration
        config = PipelineConfig(
            name="integration-test-pipeline",
            stages=[
                StageConfig(
                    name="validation",
                    type=StageType.VALIDATOR,
                    processor="DocumentValidator",
                    timeout=30.0
                ),
                StageConfig(
                    name="extraction",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    dependencies=["validation"],
                    timeout=60.0
                ),
                StageConfig(
                    name="aggregation",
                    type=StageType.AGGREGATOR,
                    dependencies=["extraction"],
                    timeout=30.0
                )
            ],
            max_parallel_stages=2,
            checkpoint_enabled=True
        )
        
        # Create pipeline manager
        pipeline_manager = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Track events
        events_received = []
        
        async def event_handler(event: Event):
            events_received.append(event)
            logger.info(f"Event received: {event.type} - {event.data}")
        
        event_bus.subscribe("pipeline.*", event_handler)
        event_bus.subscribe("stage.*", event_handler)
        event_bus.subscribe("progress.*", event_handler)
        
        # Execute pipeline
        context = await pipeline_manager.execute(
            document_id="test-doc-001",
            metadata={"test": True, "source": "integration_test"}
        )
        
        # Verify execution completed
        assert context.pipeline_id
        assert len(context.stage_results) == 3
        assert all(r.status.value == "completed" for r in context.stage_results.values())
        
        # Verify events were emitted
        event_types = [e.type for e in events_received]
        assert "pipeline.started" in event_types
        assert "pipeline.completed" in event_types
        assert "stage.started" in event_types
        assert "stage.completed" in event_types
        
        # Verify monitoring captured metrics
        metrics = monitoring_service.get_metrics_summary()
        assert metrics.total_pipelines_run > 0
        assert metrics.total_stages_executed >= 3
        
        # Verify progress tracking
        progress = progress_tracker.get_pipeline_progress(context.pipeline_id)
        assert progress is not None
        assert progress["completed"] == True
        assert progress["total_stages"] == 3
        assert progress["completed_stages"] == 3
    
    @pytest.mark.asyncio
    async def test_processor_worker_integration(
        self,
        worker_pool,
        processor_registry,
        event_bus
    ):
        """Test processor execution through worker pool."""
        # Create processor context
        context = ProcessorContext(
            document_id="test-doc-002",
            data={"content": "Test document content"},
            metadata={"format": "text"}
        )
        
        # Create task for processor
        task = Task(
            id="test-task-001",
            processor_name="test_processor",
            context=context,
            priority=TaskPriority.NORMAL
        )
        
        # Submit to worker pool
        result = await worker_pool.submit(task)
        
        # Verify result
        assert result.success == True
        assert result.data["processed"] == True
        assert "timestamp" in result.data
        assert result.data["input_data"]["content"] == "Test document content"
    
    @pytest.mark.asyncio
    async def test_checkpoint_recovery(
        self,
        event_bus,
        state_store,
        processor_registry
    ):
        """Test pipeline checkpoint and recovery functionality."""
        # Create pipeline with checkpoint enabled
        config = PipelineConfig(
            name="checkpoint-test-pipeline",
            stages=[
                StageConfig(
                    name="stage1",
                    type=StageType.PROCESSOR,
                    processor="test_processor"
                ),
                StageConfig(
                    name="stage2",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    dependencies=["stage1"]
                ),
                StageConfig(
                    name="stage3",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    dependencies=["stage2"]
                )
            ],
            checkpoint_enabled=True
        )
        
        # Create first pipeline manager
        pipeline1 = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Start execution
        context = await pipeline1.execute(
            document_id="test-doc-003",
            metadata={"checkpoint_test": True}
        )
        
        pipeline_id = context.pipeline_id
        
        # Verify checkpoint was saved
        checkpoint = await state_store.get_checkpoint(pipeline_id)
        assert checkpoint is not None
        assert len(checkpoint["completed_stages"]) == 3
        
        # Create new pipeline manager and resume
        pipeline2 = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Resume from checkpoint
        resumed_context = await pipeline2.resume(pipeline_id)
        assert resumed_context is not None
        assert resumed_context.pipeline_id == pipeline_id
        assert len(resumed_context.stage_results) == 3
    
    @pytest.mark.asyncio
    async def test_resource_management(
        self,
        event_bus,
        state_store,
        monitoring_service,
        processor_registry
    ):
        """Test resource management across pipeline execution."""
        # Create resource-intensive pipeline
        config = PipelineConfig(
            name="resource-test-pipeline",
            stages=[
                StageConfig(
                    name=f"stage{i}",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    resources={
                        "cpu_cores": 0.5,
                        "memory_mb": 256
                    }
                ) for i in range(5)
            ],
            max_parallel_stages=3,  # Limit parallelism
            max_memory_mb=1024,     # Set memory limit
            max_cpu_cores=2.0       # Set CPU limit
        )
        
        pipeline = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Track resource events
        resource_events = []
        
        async def resource_handler(event: Event):
            if event.type.startswith("resource."):
                resource_events.append(event)
        
        event_bus.subscribe("resource.*", resource_handler)
        
        # Execute pipeline
        context = await pipeline.execute(
            document_id="test-doc-004",
            metadata={"resource_test": True}
        )
        
        # Verify resource limits were respected
        metrics = monitoring_service.get_metrics_summary()
        assert metrics.peak_memory_mb <= 1024
        assert metrics.peak_cpu_percent <= 80.0  # Assuming 2 cores = ~50% of 4-core system
        
        # Verify stages completed successfully
        assert all(r.status.value == "completed" for r in context.stage_results.values())
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        event_bus,
        state_store,
        processor_registry
    ):
        """Test error handling and recovery mechanisms."""
        
        class FailingProcessor(BaseProcessor):
            """Processor that fails on first attempt."""
            attempt_count = 0
            
            async def process(self, context: ProcessorContext) -> ProcessorResult:
                FailingProcessor.attempt_count += 1
                if FailingProcessor.attempt_count < 2:
                    raise Exception("Simulated failure")
                
                return ProcessorResult(
                    processor_name="failing_processor",
                    success=True,
                    data={"recovered": True}
                )
        
        # Register failing processor
        processor_registry.register("failing_processor", FailingProcessor)
        
        # Create pipeline with retry configuration
        config = PipelineConfig(
            name="error-test-pipeline",
            stages=[
                StageConfig(
                    name="failing_stage",
                    type=StageType.PROCESSOR,
                    processor="failing_processor",
                    retry_count=2,
                    retry_delay=0.1
                )
            ]
        )
        
        pipeline = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Track error events
        error_events = []
        
        async def error_handler(event: Event):
            if "error" in event.type or "failed" in event.type:
                error_events.append(event)
        
        event_bus.subscribe("*", error_handler)
        
        # Execute pipeline
        context = await pipeline.execute(
            document_id="test-doc-005",
            metadata={"error_test": True}
        )
        
        # Verify recovery succeeded
        assert context.stage_results["failing_stage"].status.value == "completed"
        assert context.stage_results["failing_stage"].data["recovered"] == True
        
        # Verify error was logged
        assert len(error_events) >= 1
    
    @pytest.mark.asyncio
    async def test_pipeline_templates(
        self,
        event_bus,
        state_store,
        processor_registry
    ):
        """Test pipeline template system."""
        # Test standard document pipeline template
        standard_config = create_pipeline_from_template(
            "standard",
            enable_ocr=True,
            enable_translation=True,
            target_language="es"
        )
        
        assert standard_config.name == "standard-document-pipeline"
        stage_names = [s.name for s in standard_config.stages]
        assert "validation" in stage_names
        assert "extraction" in stage_names
        assert "ocr" in stage_names
        assert "translation" in stage_names
        
        # Test batch processing template
        batch_config = create_pipeline_from_template(
            "batch",
            batch_size=50,
            parallel_workers=8
        )
        
        assert batch_config.name == "batch-processing-pipeline"
        assert any(s.config.get("batch_size") == 50 for s in batch_config.stages)
        
        # Test QA pipeline template
        qa_config = create_pipeline_from_template(
            "qa",
            min_text_quality=0.95,
            report_format="json"
        )
        
        assert qa_config.name == "qa-pipeline"
        assert any(s.name == "quality_analysis" for s in qa_config.stages)
    
    @pytest.mark.asyncio
    async def test_processing_system_integration(
        self,
        event_bus,
        state_store
    ):
        """Test the complete ProcessingSystem integration."""
        # Create processing system configuration
        config = ProcessingSystemConfig(
            worker_pool_size=4,
            max_concurrent_pipelines=2,
            enable_monitoring=True,
            enable_checkpoints=True,
            checkpoint_interval=60
        )
        
        # Create processing system
        system = ProcessingSystem(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Start the system
        await system.start()
        
        try:
            # Process a document
            pipeline_id = await system.process_document(
                document_path=Path("/tmp/test-doc.pdf"),
                metadata={
                    "source": "integration_test",
                    "priority": "high"
                },
                pipeline_template="standard"
            )
            
            assert pipeline_id is not None
            
            # Check system status
            status = system.get_status()
            assert status["state"] == "running"
            assert status["pipelines"]["active"] >= 0
            assert status["workers"]["available"] <= 4
            
            # Get pipeline status
            pipeline_status = system.get_pipeline_status(pipeline_id)
            assert pipeline_status is not None
            assert "progress" in pipeline_status
            
            # Check monitoring metrics
            metrics = system.get_metrics()
            assert "pipelines_total" in metrics
            assert "stages_total" in metrics
            assert "processing_duration_seconds" in metrics
            
        finally:
            # Stop the system
            await system.stop()
    
    @pytest.mark.asyncio
    async def test_performance_metrics(
        self,
        event_bus,
        state_store,
        monitoring_service,
        processor_registry
    ):
        """Test performance meets Issue #8 success metrics."""
        # Create high-performance pipeline
        config = PipelineConfig(
            name="performance-test-pipeline",
            stages=[
                StageConfig(
                    name=f"processor{i}",
                    type=StageType.PROCESSOR,
                    processor="test_processor",
                    timeout=5.0
                ) for i in range(10)
            ],
            max_parallel_stages=5,
            checkpoint_enabled=False  # Disable for performance
        )
        
        pipeline = PipelineManager(
            config=config,
            event_bus=event_bus,
            state_store=state_store
        )
        
        # Execute multiple pipelines concurrently
        start_time = datetime.utcnow()
        
        tasks = []
        for i in range(10):
            task = pipeline.execute(
                document_id=f"perf-test-{i}",
                metadata={"batch": i}
            )
            tasks.append(task)
        
        # Wait for all to complete
        contexts = await asyncio.gather(*tasks)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Verify performance metrics
        assert all(len(ctx.stage_results) == 10 for ctx in contexts)
        assert duration < 30.0  # Should complete in under 30 seconds
        
        # Check monitoring metrics
        metrics = monitoring_service.get_metrics_summary()
        avg_duration = metrics.average_pipeline_duration
        assert avg_duration < 3.0  # Average should be under 3 seconds
        
        # Verify concurrent execution
        assert metrics.peak_concurrent_pipelines >= 5


@pytest.mark.integration
class TestComponentCompatibility:
    """Test compatibility between all components."""
    
    @pytest.mark.asyncio
    async def test_event_bus_communication(self):
        """Test all components communicate properly via EventBus."""
        event_bus = EventBus()
        events_by_component = {
            "pipeline": [],
            "processor": [],
            "worker": [],
            "progress": [],
            "monitoring": []
        }
        
        # Subscribe to all event types
        async def track_events(event: Event):
            for component, events in events_by_component.items():
                if event.type.startswith(component):
                    events.append(event)
        
        event_bus.subscribe("*", track_events)
        
        # Emit events from each component
        await event_bus.emit(Event(type="pipeline.started", data={"id": "p1"}))
        await event_bus.emit(Event(type="processor.executed", data={"name": "proc1"}))
        await event_bus.emit(Event(type="worker.task_started", data={"task": "t1"}))
        await event_bus.emit(Event(type="progress.updated", data={"percent": 50}))
        await event_bus.emit(Event(type="monitoring.metric", data={"cpu": 45.5}))
        
        # Verify all components received events
        assert len(events_by_component["pipeline"]) == 1
        assert len(events_by_component["processor"]) == 1
        assert len(events_by_component["worker"]) == 1
        assert len(events_by_component["progress"]) == 1
        assert len(events_by_component["monitoring"]) == 1
    
    @pytest.mark.asyncio
    async def test_data_flow_compatibility(self):
        """Test data structures flow correctly between components."""
        # Test ProcessorContext flows through pipeline → worker → processor
        context = ProcessorContext(
            document_id="flow-test-001",
            data={"test": "data"},
            metadata={"source": "test"}
        )
        
        # Verify context can be serialized/deserialized (for checkpointing)
        import pickle
        serialized = pickle.dumps(context)
        deserialized = pickle.loads(serialized)
        assert deserialized.document_id == context.document_id
        assert deserialized.data == context.data
        
        # Test StageResult flows back through processor → worker → pipeline
        result = ProcessorResult(
            processor_name="test",
            success=True,
            data={"processed": True}
        )
        
        # Verify result maintains data integrity
        assert result.processor_name == "test"
        assert result.success == True
        assert result.data["processed"] == True


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"])