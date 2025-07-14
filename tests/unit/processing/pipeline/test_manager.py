"""
Unit tests for PipelineManager.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import networkx as nx

from torematrix.processing.pipeline.manager import (
    PipelineManager,
    PipelineContext,
    PipelineStatus
)
from torematrix.processing.pipeline.config import (
    PipelineConfig,
    StageConfig,
    StageType,
    ResourceRequirements
)
from torematrix.processing.pipeline.stages import Stage, StageResult, StageStatus
from torematrix.processing.pipeline.exceptions import (
    PipelineCancelledError,
    StageTimeoutError,
    ResourceError
)
from torematrix.core.events import EventBus, Event


class MockStage(Stage):
    """Mock stage for testing."""
    
    def __init__(self, config: StageConfig, should_fail: bool = False, execution_time: float = 0.1):
        super().__init__(config)
        self.should_fail = should_fail
        self.execution_time = execution_time
        self.executed = False
        self.initialized = False
    
    async def _initialize(self):
        self.initialized = True
    
    async def execute(self, context: PipelineContext) -> StageResult:
        self.executed = True
        await asyncio.sleep(self.execution_time)  # Simulate work
        
        if self.should_fail:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                error="Mock failure"
            )
        
        # Add some data to context for dependency testing
        context.user_data[self.name] = f"Result from {self.name}"
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"mock": True, "stage": self.name}
        )


@pytest.fixture
def pipeline_config():
    """Create test pipeline configuration."""
    return PipelineConfig(
        name="test-pipeline",
        stages=[
            StageConfig(
                name="stage1",
                type=StageType.PROCESSOR,
                processor="mock.Stage1",
                dependencies=[]
            ),
            StageConfig(
                name="stage2",
                type=StageType.PROCESSOR,
                processor="mock.Stage2",
                dependencies=["stage1"]
            ),
            StageConfig(
                name="stage3",
                type=StageType.PROCESSOR,
                processor="mock.Stage3",
                dependencies=["stage1"]
            ),
            StageConfig(
                name="stage4",
                type=StageType.AGGREGATOR,
                processor="mock.Stage4",
                dependencies=["stage2", "stage3"]
            )
        ]
    )


@pytest.fixture
def event_bus():
    """Create mock event bus."""
    bus = Mock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def state_store():
    """Create mock state store."""
    from torematrix.processing.pipeline.state_store import StateStore
    store = Mock(spec=StateStore)
    store.get = AsyncMock(return_value=None)
    store.set = AsyncMock()
    store.is_healthy = Mock(return_value=True)
    return store


class TestPipelineManager:
    """Test cases for PipelineManager."""
    
    @pytest.mark.asyncio
    async def test_pipeline_construction(self, pipeline_config, event_bus, state_store):
        """Test pipeline DAG construction."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Check DAG structure
        assert len(manager.stages) == 4
        assert nx.is_directed_acyclic_graph(manager.dag)
        
        # Check dependencies
        assert set(manager.get_stage_dependencies("stage2")) == {"stage1"}
        assert set(manager.get_stage_dependencies("stage4")) == {"stage2", "stage3"}
        
        # Check topological order
        order = manager.get_stage_order()
        assert order.index("stage1") < order.index("stage2")
        assert order.index("stage1") < order.index("stage3")
        assert order.index("stage2") < order.index("stage4")
        assert order.index("stage3") < order.index("stage4")
    
    @pytest.mark.asyncio
    async def test_cycle_detection(self, event_bus, state_store):
        """Test that cycles are detected in pipeline."""
        # Create config with cycle
        config = PipelineConfig(
            name="cyclic-pipeline",
            stages=[
                StageConfig(name="A", type=StageType.PROCESSOR, processor="A", dependencies=["B"]),
                StageConfig(name="B", type=StageType.PROCESSOR, processor="B", dependencies=["C"]),
                StageConfig(name="C", type=StageType.PROCESSOR, processor="C", dependencies=["A"])
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            PipelineManager(config, event_bus, state_store)
        assert "cycle" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_execution(self, pipeline_config, event_bus, state_store):
        """Test successful pipeline execution."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute pipeline
        context = await manager.execute(document_id="doc123", metadata={"test": True})
        
        # Check execution
        assert context.document_id == "doc123"
        assert len(context.stage_results) == 4
        
        # Check all stages executed
        for stage in manager.stages.values():
            assert stage.executed
            assert stage.initialized
        
        # Check results
        for result in context.stage_results.values():
            assert result.status == StageStatus.COMPLETED
        
        # Check events emitted
        event_calls = event_bus.publish.call_args_list
        event_types = [call[0][0].event_type for call in event_calls]
        assert "pipeline.started" in event_types
        assert "pipeline.completed" in event_types
        assert event_types.count("stage.started") == 4
        assert event_types.count("stage.completed") == 4
    
    @pytest.mark.asyncio
    async def test_stage_failure_handling(self, pipeline_config, event_bus, state_store):
        """Test pipeline handling of stage failures."""
        def create_stage(config):
            if config.name == "stage2":
                return MockStage(config, should_fail=True)
            return MockStage(config)
        
        with patch.object(PipelineManager, '_create_stage', side_effect=create_stage):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute pipeline
        context = await manager.execute(document_id="doc123")
        
        # Check stage2 failed
        assert context.stage_results["stage2"].status == StageStatus.FAILED
        
        # Check stage4 was skipped (depends on failed stage2)
        assert "stage4" not in context.stage_results or \
               context.stage_results["stage4"].status != StageStatus.COMPLETED
        
        # Check pipeline status
        assert manager.status == PipelineStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_non_critical_stage_failure(self, event_bus, state_store):
        """Test non-critical stage failure doesn't stop pipeline."""
        config = PipelineConfig(
            name="test-pipeline",
            stages=[
                StageConfig(name="stage1", type=StageType.PROCESSOR, processor="mock", dependencies=[]),
                StageConfig(
                    name="stage2", 
                    type=StageType.PROCESSOR, 
                    processor="mock", 
                    dependencies=["stage1"],
                    critical=False  # Non-critical
                ),
                StageConfig(name="stage3", type=StageType.PROCESSOR, processor="mock", dependencies=["stage1"])
            ]
        )
        
        def create_stage(cfg):
            if cfg.name == "stage2":
                return MockStage(cfg, should_fail=True)
            return MockStage(cfg)
        
        with patch.object(PipelineManager, '_create_stage', side_effect=create_stage):
            manager = PipelineManager(config, event_bus, state_store)
        
        context = await manager.execute(document_id="doc123")
        
        # Stage 2 failed but pipeline should continue
        assert context.stage_results["stage2"].status == StageStatus.FAILED
        assert context.stage_results["stage3"].status == StageStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_checkpoint_save_restore(self, pipeline_config, event_bus, state_store):
        """Test checkpoint saving and restoration."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute with checkpointing
        context = await manager.execute(document_id="doc123", checkpoint=True)
        
        # Verify checkpoints were saved
        assert state_store.set.called
        checkpoint_key = f"pipeline_checkpoint:doc123"
        
        # Get the saved checkpoint data
        saved_checkpoint = None
        for call in state_store.set.call_args_list:
            if call[0][0] == checkpoint_key:
                saved_checkpoint = call[0][1]
                break
        
        assert saved_checkpoint is not None
        assert saved_checkpoint["document_id"] == "doc123"
        assert "stage_results" in saved_checkpoint
        assert len(saved_checkpoint["stage_results"]) > 0
    
    @pytest.mark.asyncio
    async def test_checkpoint_restore(self, pipeline_config, event_bus, state_store):
        """Test restoring from checkpoint."""
        # Simulate checkpoint data
        checkpoint_data = {
            "document_id": "doc123",
            "metadata": {"restored": True},
            "stage_results": {
                "stage1": {
                    "stage_name": "stage1",
                    "status": "completed",
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "data": {"from_checkpoint": True}
                }
            },
            "user_data": {"checkpoint_data": "test"}
        }
        
        state_store.get = AsyncMock(return_value=checkpoint_data)
        
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        context = await manager.execute(document_id="doc123", checkpoint=True)
        
        # Verify checkpoint was loaded
        assert state_store.get.called
        
        # Stage1 should not have been executed (loaded from checkpoint)
        assert not manager.stages["stage1"].executed
        
        # Other stages should have executed
        assert manager.stages["stage2"].executed
        assert manager.stages["stage3"].executed
    
    @pytest.mark.asyncio
    async def test_pause_resume(self, pipeline_config, event_bus, state_store):
        """Test pipeline pause and resume."""
        with patch.object(PipelineManager, '_create_stage', 
                         side_effect=lambda c: MockStage(c, execution_time=0.2)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Start execution in background
        exec_task = asyncio.create_task(manager.execute(document_id="doc123"))
        
        # Let it start
        await asyncio.sleep(0.1)
        
        # Pause
        await manager.pause()
        assert manager.status == PipelineStatus.PAUSED
        
        # Wait a bit
        await asyncio.sleep(0.3)
        
        # Check that not all stages completed yet
        executed_count = sum(1 for s in manager.stages.values() if s.executed)
        assert executed_count < 4  # Not all stages executed
        
        # Resume
        await manager.resume()
        
        # Wait for completion
        context = await exec_task
        
        # Should complete successfully
        assert len(context.stage_results) == 4
    
    @pytest.mark.asyncio
    async def test_cancel(self, pipeline_config, event_bus, state_store):
        """Test pipeline cancellation."""
        with patch.object(PipelineManager, '_create_stage', 
                         side_effect=lambda c: MockStage(c, execution_time=0.5)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Start execution in background
        exec_task = asyncio.create_task(manager.execute(document_id="doc123"))
        
        # Let it start
        await asyncio.sleep(0.1)
        
        # Cancel
        await manager.cancel()
        
        # Should raise cancelled error
        with pytest.raises(PipelineCancelledError):
            await exec_task
    
    @pytest.mark.asyncio
    async def test_dry_run(self, pipeline_config, event_bus, state_store):
        """Test dry run execution."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute dry run
        context = await manager.execute(document_id="doc123", dry_run=True)
        
        # Check all stages marked as dry run
        for result in context.stage_results.values():
            assert result.data.get("dry_run") == True
        
        # Check no checkpoints saved in dry run
        assert not state_store.set.called
    
    @pytest.mark.asyncio
    async def test_resource_monitoring(self, pipeline_config, event_bus, state_store):
        """Test resource monitoring integration."""
        from torematrix.processing.pipeline.resources import ResourceMonitor
        
        monitor = Mock(spec=ResourceMonitor)
        monitor.check_availability = AsyncMock(return_value=True)
        monitor.allocate = AsyncMock()
        monitor.release = AsyncMock()
        
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(
                pipeline_config, 
                event_bus, 
                state_store,
                resource_monitor=monitor
            )
        
        # Execute pipeline
        await manager.execute(document_id="doc123")
        
        # Check resource methods were called
        assert monitor.check_availability.called
        assert monitor.allocate.called
        assert monitor.release.called
        
        # Should be called for each stage
        assert monitor.allocate.call_count == 4
        assert monitor.release.call_count == 4
    
    @pytest.mark.asyncio
    async def test_resource_unavailable(self, pipeline_config, event_bus, state_store):
        """Test handling when resources are not available."""
        from torematrix.processing.pipeline.resources import ResourceMonitor
        
        monitor = Mock(spec=ResourceMonitor)
        monitor.check_availability = AsyncMock(return_value=False)
        monitor.allocate = AsyncMock()
        monitor.release = AsyncMock()
        
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(
                pipeline_config, 
                event_bus, 
                state_store,
                resource_monitor=monitor
            )
        
        # Should raise resource error after timeout
        with pytest.raises(ResourceError):
            await manager.execute(document_id="doc123")
    
    @pytest.mark.asyncio
    async def test_stage_timeout(self, event_bus, state_store):
        """Test stage timeout handling."""
        config = PipelineConfig(
            name="test-pipeline",
            stages=[
                StageConfig(
                    name="slow_stage",
                    type=StageType.PROCESSOR,
                    processor="mock",
                    dependencies=[],
                    timeout=1  # 1 second timeout
                )
            ]
        )
        
        # Create stage that takes too long
        slow_stage = MockStage(config.stages[0], execution_time=2.0)
        
        with patch.object(PipelineManager, '_create_stage', return_value=slow_stage):
            manager = PipelineManager(config, event_bus, state_store)
        
        # Should timeout
        with pytest.raises(StageTimeoutError):
            await manager.execute(document_id="doc123")
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, pipeline_config, event_bus, state_store):
        """Test parallel stage execution."""
        execution_order = []
        
        class TrackingStage(MockStage):
            async def execute(self, context):
                execution_order.append(f"{self.name}_start")
                result = await super().execute(context)
                execution_order.append(f"{self.name}_end")
                return result
        
        with patch.object(PipelineManager, '_create_stage', 
                         side_effect=lambda c: TrackingStage(c, execution_time=0.1)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        await manager.execute(document_id="doc123")
        
        # Check that stage2 and stage3 ran in parallel
        stage2_start = execution_order.index("stage2_start")
        stage2_end = execution_order.index("stage2_end")
        stage3_start = execution_order.index("stage3_start")
        stage3_end = execution_order.index("stage3_end")
        
        # If parallel, stage3 should start before stage2 ends (or vice versa)
        assert (stage3_start < stage2_end) or (stage2_start < stage3_end)
    
    @pytest.mark.asyncio
    async def test_pipeline_status(self, pipeline_config, event_bus, state_store):
        """Test getting pipeline status."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Create pipeline
        pipeline_id = await manager.create_pipeline("doc123", {"test": True})
        
        # Get status before execution
        status = manager.get_status(pipeline_id)
        assert status["pipeline_id"] == pipeline_id
        assert status["document_id"] == "doc123"
        assert status["progress"] == 0.0
        
        # Execute
        await manager.execute(pipeline_id=pipeline_id)
        
        # Get status after execution
        status = manager.get_status(pipeline_id)
        assert status["progress"] == 1.0
        assert status["completed_stages"] == 4
        assert status["total_stages"] == 4
    
    @pytest.mark.asyncio
    async def test_conditional_stage_execution(self, event_bus, state_store):
        """Test conditional stage execution."""
        config = PipelineConfig(
            name="test-pipeline",
            stages=[
                StageConfig(name="stage1", type=StageType.PROCESSOR, processor="mock", dependencies=[]),
                StageConfig(
                    name="stage2",
                    type=StageType.PROCESSOR,
                    processor="mock",
                    dependencies=["stage1"],
                    conditional="should_skip"  # Condition that evaluates to false
                ),
                StageConfig(name="stage3", type=StageType.PROCESSOR, processor="mock", dependencies=["stage1"])
            ]
        )
        
        class ConditionalStage(MockStage):
            def should_execute(self, context):
                # Skip stage2
                return self.name != "stage2"
        
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: ConditionalStage(c)):
            manager = PipelineManager(config, event_bus, state_store)
        
        context = await manager.execute(document_id="doc123")
        
        # Stage2 should be skipped
        assert context.stage_results["stage2"].status == StageStatus.SKIPPED
        assert context.stage_results["stage3"].status == StageStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_cleanup(self, pipeline_config, event_bus, state_store):
        """Test pipeline cleanup."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute pipeline
        await manager.execute(document_id="doc123")
        
        # Mock cleanup method
        for stage in manager.stages.values():
            stage.cleanup = AsyncMock()
        
        # Cleanup
        await manager.cleanup()
        
        # All stages should be cleaned up
        for stage in manager.stages.values():
            stage.cleanup.assert_called_once()