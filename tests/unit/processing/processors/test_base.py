"""Unit tests for base processor interface."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any, List

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    ProcessorPriority,
    StageStatus,
    ProcessorException,
    ProcessorInitializationError
)


class TestProcessor(BaseProcessor):
    """Test processor implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.process_called = False
        self.initialize_called = False
        self.cleanup_called = False
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="test_processor",
            version="1.0.0",
            description="Test processor for unit tests",
            author="Test Author",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION],
            supported_formats=["txt", "pdf"],
            timeout_seconds=60
        )
    
    async def _initialize(self) -> None:
        self.initialize_called = True
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        self.process_called = True
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"test": "data"}
        )
    
    async def _cleanup(self) -> None:
        self.cleanup_called = True


class FailingProcessor(BaseProcessor):
    """Processor that fails during initialization."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="failing_processor",
            version="1.0.0",
            description="Processor that fails"
        )
    
    async def _initialize(self) -> None:
        raise Exception("Initialization failed")
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        raise Exception("Processing failed")


@pytest.fixture
def processor():
    """Create test processor instance."""
    return TestProcessor()


@pytest.fixture
def context():
    """Create test processing context."""
    return ProcessorContext(
        document_id="doc123",
        file_path="/tmp/test.txt",
        mime_type="text/plain",
        metadata={"test": "metadata"}
    )


class TestProcessorMetadata:
    """Test processor metadata."""
    
    def test_metadata_creation(self):
        """Test creating processor metadata."""
        metadata = ProcessorMetadata(
            name="test",
            version="1.0.0",
            description="Test processor",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION],
            supported_formats=["pdf", "txt"]
        )
        
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert ProcessorCapability.TEXT_EXTRACTION in metadata.capabilities
        assert "pdf" in metadata.supported_formats
        assert metadata.priority == ProcessorPriority.NORMAL
    
    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = ProcessorMetadata(
            name="test",
            version="1.0.0", 
            description="Test"
        )
        
        assert metadata.author == ""
        assert metadata.capabilities == []
        assert metadata.supported_formats == []
        assert metadata.timeout_seconds == 300
        assert metadata.retry_count == 3


class TestProcessorContext:
    """Test processor context."""
    
    def test_context_creation(self, context):
        """Test creating processor context."""
        assert context.document_id == "doc123"
        assert context.file_path == "/tmp/test.txt"
        assert context.mime_type == "text/plain"
        assert context.metadata["test"] == "metadata"
    
    def test_get_previous_result(self, context):
        """Test getting previous processor results."""
        context.previous_results = {
            "processor1": {"data": "result1"},
            "processor2": {"data": "result2"}
        }
        
        assert context.get_previous_result("processor1") == {"data": "result1"}
        assert context.get_previous_result("processor2") == {"data": "result2"}
        assert context.get_previous_result("nonexistent") is None


class TestProcessorResult:
    """Test processor result."""
    
    def test_result_creation(self):
        """Test creating processor result."""
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        result = ProcessorResult(
            processor_name="test",
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            extracted_data={"key": "value"},
            errors=["error1"],
            warnings=["warning1"]
        )
        
        assert result.processor_name == "test"
        assert result.status == StageStatus.COMPLETED
        assert result.extracted_data["key"] == "value"
        assert "error1" in result.errors
        assert "warning1" in result.warnings
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        result = ProcessorResult(
            processor_name="test",
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time
        )
        
        assert isinstance(result.duration, float)
        assert result.duration >= 0
    
    def test_to_stage_result(self):
        """Test conversion to stage result."""
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        result = ProcessorResult(
            processor_name="test",
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            extracted_data={"key": "value"},
            errors=["error1", "error2"]
        )
        
        stage_result = result.to_stage_result()
        
        assert stage_result.stage_name == "test"
        assert stage_result.status == StageStatus.COMPLETED
        assert stage_result.data == {"key": "value"}
        assert stage_result.error == "error1; error2"


class TestBaseProcessor:
    """Test base processor functionality."""
    
    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert not processor._initialized
        
        await processor.initialize()
        
        assert processor._initialized
        assert processor.initialize_called
        
        # Should not initialize again
        processor.initialize_called = False
        await processor.initialize()
        assert not processor.initialize_called
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test handling initialization failure."""
        processor = FailingProcessor()
        
        with pytest.raises(Exception, match="Initialization failed"):
            await processor.initialize()
        
        assert not processor._initialized
    
    @pytest.mark.asyncio
    async def test_process_method(self, processor, context):
        """Test process method."""
        await processor.initialize()
        result = await processor.process(context)
        
        assert processor.process_called
        assert isinstance(result, ProcessorResult)
        assert result.processor_name == "test_processor"
        assert result.status == StageStatus.COMPLETED
        assert result.extracted_data["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, processor):
        """Test processor cleanup."""
        await processor.initialize()
        assert processor._initialized
        
        await processor.cleanup()
        
        assert processor.cleanup_called
        assert not processor._initialized
    
    @pytest.mark.asyncio
    async def test_validate_input(self, processor, context):
        """Test input validation."""
        await processor.initialize()
        
        # Valid input
        errors = await processor.validate_input(context)
        assert len(errors) == 0
        
        # Invalid format
        context.mime_type = "application/unknown"
        context.file_path = "/tmp/test.unknown"
        errors = await processor.validate_input(context)
        assert len(errors) == 1
        assert "Unsupported format" in errors[0]
    
    def test_metrics_management(self, processor):
        """Test metrics functionality."""
        # Initial metrics should be empty
        metrics = processor.get_metrics()
        assert isinstance(metrics, dict)
        assert len(metrics) == 0
        
        # Update metrics
        processor.update_metric("test_metric", 5.0)
        processor.increment_metric("counter", 2.0)
        processor.increment_metric("counter", 3.0)
        
        metrics = processor.get_metrics()
        assert metrics["test_metric"] == 5.0
        assert metrics["counter"] == 5.0
    
    @pytest.mark.asyncio
    async def test_health_check(self, processor):
        """Test health check."""
        # Before initialization
        health = await processor.health_check()
        assert health["healthy"] is False
        assert health["name"] == "test_processor"
        
        # After initialization
        await processor.initialize()
        health = await processor.health_check()
        assert health["healthy"] is True
        assert "metrics" in health


class TestProcessorCapability:
    """Test processor capability enum."""
    
    def test_capability_values(self):
        """Test capability enum values."""
        assert ProcessorCapability.TEXT_EXTRACTION == "text_extraction"
        assert ProcessorCapability.METADATA_EXTRACTION == "metadata_extraction"
        assert ProcessorCapability.TABLE_EXTRACTION == "table_extraction"
        assert ProcessorCapability.VALIDATION == "validation"
    
    def test_capability_in_list(self):
        """Test capability membership in lists."""
        capabilities = [
            ProcessorCapability.TEXT_EXTRACTION,
            ProcessorCapability.VALIDATION
        ]
        
        assert ProcessorCapability.TEXT_EXTRACTION in capabilities
        assert ProcessorCapability.METADATA_EXTRACTION not in capabilities


class TestProcessorPriority:
    """Test processor priority enum."""
    
    def test_priority_ordering(self):
        """Test priority ordering."""
        assert ProcessorPriority.CRITICAL < ProcessorPriority.HIGH
        assert ProcessorPriority.HIGH < ProcessorPriority.NORMAL
        assert ProcessorPriority.NORMAL < ProcessorPriority.LOW
        assert ProcessorPriority.LOW < ProcessorPriority.BACKGROUND
    
    def test_priority_values(self):
        """Test priority numeric values."""
        assert ProcessorPriority.CRITICAL == 0
        assert ProcessorPriority.HIGH == 1
        assert ProcessorPriority.NORMAL == 2
        assert ProcessorPriority.LOW == 3
        assert ProcessorPriority.BACKGROUND == 4


class TestStageStatus:
    """Test stage status enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert StageStatus.PENDING == "pending"
        assert StageStatus.RUNNING == "running"
        assert StageStatus.COMPLETED == "completed"
        assert StageStatus.FAILED == "failed"
        assert StageStatus.CANCELLED == "cancelled"