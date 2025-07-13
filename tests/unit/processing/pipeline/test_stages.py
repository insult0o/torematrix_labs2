"""
Unit tests for pipeline stages.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from torematrix.processing.pipeline.stages import (
    Stage,
    StageResult,
    StageStatus,
    ProcessorStage,
    ValidationStage,
    RouterStage,
    AggregatorStage
)
from torematrix.processing.pipeline.config import StageConfig, StageType, ResourceRequirements
from torematrix.processing.pipeline.manager import PipelineContext


class ConcreteStage(Stage):
    """Concrete implementation for testing abstract Stage class."""
    
    async def _initialize(self):
        self.init_called = True
    
    async def execute(self, context: PipelineContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"test": True}
        )
    
    async def _cleanup(self):
        self.cleanup_called = True


class TestStageResult:
    """Test cases for StageResult."""
    
    def test_stage_result_creation(self):
        """Test creating stage result."""
        start = datetime.utcnow()
        end = datetime.utcnow()
        
        result = StageResult(
            stage_name="test_stage",
            status=StageStatus.COMPLETED,
            start_time=start,
            end_time=end,
            data={"output": "test"},
            metrics={"items_processed": 100}
        )
        
        assert result.stage_name == "test_stage"
        assert result.status == StageStatus.COMPLETED
        assert result.data["output"] == "test"
        assert result.metrics["items_processed"] == 100
    
    def test_duration_calculation(self):
        """Test duration property."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 0, 30)
        
        result = StageResult(
            stage_name="test",
            status=StageStatus.COMPLETED,
            start_time=start,
            end_time=end
        )
        
        assert result.duration == 30.0
    
    def test_duration_without_end_time(self):
        """Test duration when end time is not set."""
        result = StageResult(
            stage_name="test",
            status=StageStatus.RUNNING,
            start_time=datetime.utcnow()
        )
        
        assert result.duration is None
    
    def test_failed_result(self):
        """Test failed stage result."""
        result = StageResult(
            stage_name="test",
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            error="Test error message"
        )
        
        assert result.status == StageStatus.FAILED
        assert result.error == "Test error message"


class TestStage:
    """Test cases for Stage abstract class."""
    
    @pytest.fixture
    def stage_config(self):
        """Create test stage configuration."""
        return StageConfig(
            name="test_stage",
            type=StageType.PROCESSOR,
            processor="test.processor",
            timeout=300,
            resources=ResourceRequirements(cpu_cores=2.0, memory_mb=1024)
        )
    
    @pytest.fixture
    def pipeline_context(self):
        """Create test pipeline context."""
        return PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123",
            metadata={"test": True}
        )
    
    @pytest.mark.asyncio
    async def test_stage_initialization(self, stage_config):
        """Test stage initialization."""
        stage = ConcreteStage(stage_config)
        
        assert stage.name == "test_stage"
        assert stage.config == stage_config
        assert not stage._initialized
        
        await stage.initialize()
        
        assert stage._initialized
        assert hasattr(stage, 'init_called') and stage.init_called
        
        # Second initialization should be no-op
        stage.init_called = False
        await stage.initialize()
        assert not stage.init_called
    
    @pytest.mark.asyncio
    async def test_stage_execution(self, stage_config, pipeline_context):
        """Test stage execution."""
        stage = ConcreteStage(stage_config)
        
        result = await stage.execute(pipeline_context)
        
        assert result.stage_name == "test_stage"
        assert result.status == StageStatus.COMPLETED
        assert result.data["test"] is True
    
    @pytest.mark.asyncio
    async def test_dry_run(self, stage_config, pipeline_context):
        """Test dry run execution."""
        stage = ConcreteStage(stage_config)
        
        result = await stage.dry_run(pipeline_context)
        
        assert result.status == StageStatus.COMPLETED
        assert result.data["dry_run"] is True
    
    @pytest.mark.asyncio
    async def test_dry_run_validation_failure(self, stage_config, pipeline_context):
        """Test dry run with validation failure."""
        stage = ConcreteStage(stage_config)
        
        # Override validate to fail
        def failing_validate(context):
            raise ValueError("Validation failed")
        
        stage.validate = failing_validate
        
        result = await stage.dry_run(pipeline_context)
        
        assert result.status == StageStatus.FAILED
        assert "Validation failed" in result.error
    
    def test_validate_dependencies(self, stage_config, pipeline_context):
        """Test dependency validation."""
        # Add dependencies to config
        stage_config.dependencies = ["dep1", "dep2"]
        stage = ConcreteStage(stage_config)
        
        # No results - should fail
        with pytest.raises(ValueError, match="Missing dependency: dep1"):
            stage.validate(pipeline_context)
        
        # Add successful results
        pipeline_context.stage_results["dep1"] = StageResult(
            stage_name="dep1",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        pipeline_context.stage_results["dep2"] = StageResult(
            stage_name="dep2",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        
        # Should pass now
        stage.validate(pipeline_context)
        
        # Failed dependency
        pipeline_context.stage_results["dep2"].status = StageStatus.FAILED
        
        with pytest.raises(ValueError, match="did not complete successfully"):
            stage.validate(pipeline_context)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, stage_config):
        """Test stage cleanup."""
        stage = ConcreteStage(stage_config)
        
        # Initialize first
        await stage.initialize()
        assert stage._initialized
        
        # Cleanup
        await stage.cleanup()
        
        assert not stage._initialized
        assert hasattr(stage, 'cleanup_called') and stage.cleanup_called
    
    def test_get_resource_requirements(self, stage_config):
        """Test getting resource requirements."""
        stage = ConcreteStage(stage_config)
        
        resources = stage.get_resource_requirements()
        
        assert resources.cpu_cores == 2.0
        assert resources.memory_mb == 1024
    
    def test_should_execute(self, stage_config, pipeline_context):
        """Test conditional execution check."""
        stage = ConcreteStage(stage_config)
        
        # No condition - should execute
        assert stage.should_execute(pipeline_context) is True
        
        # With condition (placeholder implementation always returns True)
        stage_config.conditional = "some_condition"
        stage = ConcreteStage(stage_config)
        assert stage.should_execute(pipeline_context) is True


class TestProcessorStage:
    """Test cases for ProcessorStage."""
    
    @pytest.fixture
    def processor_config(self):
        """Create processor stage configuration."""
        return StageConfig(
            name="test_processor",
            type=StageType.PROCESSOR,
            processor="torematrix.processors.TestProcessor"
        )
    
    @pytest.mark.asyncio
    async def test_processor_execution(self, processor_config):
        """Test processor stage execution."""
        stage = ProcessorStage(processor_config)
        
        context = PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123"
        )
        
        result = await stage.execute(context)
        
        assert result.stage_name == "test_processor"
        assert result.status == StageStatus.COMPLETED
        assert result.data["processed"] is True
        assert result.data["document_id"] == "doc123"


class TestValidationStage:
    """Test cases for ValidationStage."""
    
    @pytest.fixture
    def validation_config(self):
        """Create validation stage configuration."""
        return StageConfig(
            name="test_validator",
            type=StageType.VALIDATOR,
            processor="torematrix.validators.TestValidator"
        )
    
    @pytest.mark.asyncio
    async def test_validation_execution(self, validation_config):
        """Test validation stage execution."""
        stage = ValidationStage(validation_config)
        
        context = PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123"
        )
        
        result = await stage.execute(context)
        
        assert result.stage_name == "test_validator"
        assert result.status == StageStatus.COMPLETED
        assert "validation_passed" in result.data


class TestRouterStage:
    """Test cases for RouterStage."""
    
    @pytest.fixture
    def router_config(self):
        """Create router stage configuration."""
        return StageConfig(
            name="test_router",
            type=StageType.ROUTER,
            processor="torematrix.routers.TestRouter"
        )
    
    @pytest.mark.asyncio
    async def test_router_execution(self, router_config):
        """Test router stage execution."""
        stage = RouterStage(router_config)
        
        context = PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123"
        )
        
        result = await stage.execute(context)
        
        assert result.stage_name == "test_router"
        assert result.status == StageStatus.COMPLETED
        assert "routing_decision" in result.data
        assert result.data["routing_decision"] == "default"


class TestAggregatorStage:
    """Test cases for AggregatorStage."""
    
    @pytest.fixture
    def aggregator_config(self):
        """Create aggregator stage configuration."""
        return StageConfig(
            name="test_aggregator",
            type=StageType.AGGREGATOR,
            processor="torematrix.aggregators.TestAggregator",
            dependencies=["stage1", "stage2"]
        )
    
    @pytest.mark.asyncio
    async def test_aggregator_execution(self, aggregator_config):
        """Test aggregator stage execution."""
        stage = AggregatorStage(aggregator_config)
        
        context = PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123"
        )
        
        # Add results from dependencies
        context.stage_results["stage1"] = StageResult(
            stage_name="stage1",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"result": "data1"}
        )
        context.stage_results["stage2"] = StageResult(
            stage_name="stage2",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"result": "data2"}
        )
        
        result = await stage.execute(context)
        
        assert result.stage_name == "test_aggregator"
        assert result.status == StageStatus.COMPLETED
        assert "aggregated" in result.data
        assert result.data["source_count"] == 2
        assert "stage1" in result.data["aggregated"]
        assert "stage2" in result.data["aggregated"]
    
    @pytest.mark.asyncio
    async def test_aggregator_with_failed_dependency(self, aggregator_config):
        """Test aggregator with failed dependency."""
        stage = AggregatorStage(aggregator_config)
        
        context = PipelineContext(
            pipeline_id="test-pipeline",
            document_id="doc123"
        )
        
        # Add one successful and one failed result
        context.stage_results["stage1"] = StageResult(
            stage_name="stage1",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"result": "data1"}
        )
        context.stage_results["stage2"] = StageResult(
            stage_name="stage2",
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            error="Failed"
        )
        
        result = await stage.execute(context)
        
        # Should only aggregate successful stages
        assert result.status == StageStatus.COMPLETED
        assert result.data["source_count"] == 1
        assert "stage1" in result.data["aggregated"]
        assert "stage2" not in result.data["aggregated"]