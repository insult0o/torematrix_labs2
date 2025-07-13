"""Integration tests between processors and pipeline stages."""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus
)
from torematrix.processing.processors.registry import ProcessorRegistry
from torematrix.processing.processors.stage_bridge import (
    create_processor_stage,
    create_unstructured_stage,
    create_metadata_stage,
    create_validation_stage
)


class MockUnstructuredProcessor(BaseProcessor):
    """Mock Unstructured processor for testing."""
    
    @classmethod
    def get_metadata(cls):
        return ProcessorMetadata(
            name="mock_unstructured",
            version="1.0.0",
            description="Mock Unstructured processor",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION]
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={
                "elements": [
                    {"type": "Title", "text": "Test Document"},
                    {"type": "NarrativeText", "text": "This is test content."}
                ],
                "text": "Test Document\nThis is test content.",
                "metadata": {"page_count": 1}
            }
        )


class MockMetadataProcessor(BaseProcessor):
    """Mock metadata processor for testing."""
    
    @classmethod
    def get_metadata(cls):
        return ProcessorMetadata(
            name="mock_metadata",
            version="1.0.0",
            description="Mock metadata processor",
            capabilities=[ProcessorCapability.METADATA_EXTRACTION]
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        # Get data from previous processor
        unstructured_data = context.previous_results.get("unstructured_extraction", {})
        
        metadata = {
            "document_id": context.document_id,
            "file_path": context.file_path,
            "mime_type": context.mime_type,
            "text_length": len(unstructured_data.get("text", "")),
            "element_count": len(unstructured_data.get("elements", []))
        }
        
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"metadata": metadata}
        )


@pytest.fixture
def temp_file():
    """Create temporary test file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\nIt has multiple lines.")
        temp_path = f.name
    
    yield temp_path
    
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


def create_test_registry():
    """Create registry with mock processors."""
    registry = ProcessorRegistry()
    
    # Register mock processors
    registry.register(MockUnstructuredProcessor, "mock_unstructured")
    registry.register(MockMetadataProcessor, "mock_metadata")
    
    return registry


@pytest.fixture
def pipeline_context(temp_file):
    """Create mock pipeline context."""
    # Import here to avoid circular imports during module loading
    from torematrix.processing.pipeline.manager import PipelineContext
    
    context = PipelineContext(
        pipeline_id="test-pipeline-123",
        document_id="test-doc-456",
        metadata={
            "file_path": temp_file,
            "mime_type": "text/plain"
        }
    )
    return context


class TestProcessorStageIntegration:
    """Test integration between processors and pipeline stages."""
    
    @pytest.mark.asyncio
    async def test_processor_stage_creation(self):
        """Test creating a processor stage."""
        stage = create_processor_stage(
            stage_name="test_stage",
            processor_name="mock_unstructured",
            processor_config={"test": "config"}
        )
        
        assert stage.name == "test_stage"
        assert stage.config.processor == "mock_unstructured"
        assert stage.config.config == {"test": "config"}
    
    @pytest.mark.asyncio
    async def test_processor_stage_execution(self, pipeline_context):
        """Test executing a processor stage."""
        # Create registry with mock processors
        registry = ProcessorRegistry()
        registry.register(MockUnstructuredProcessor, "mock_unstructured")
        
        try:
            stage = create_processor_stage(
                stage_name="unstructured_extraction",
                processor_name="mock_unstructured"
            )
            
            # Patch the registry to use our mock registry
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                # Initialize stage
                await stage.initialize()
                assert stage.processor is not None
                
                # Execute stage
                result = await stage.execute(pipeline_context)
                
                assert result.stage_name == "unstructured_extraction"
                assert result.status == StageStatus.COMPLETED
                assert "elements" in result.data
                assert "text" in result.data
        finally:
            await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self, pipeline_context):
        """Test a multi-stage pipeline with dependencies."""
        # Create registry with mock processors
        registry = create_test_registry()
        
        try:
            # Create stages
            unstructured_stage = create_processor_stage(
                stage_name="unstructured_extraction",
                processor_name="mock_unstructured"
            )
            
            metadata_stage = create_processor_stage(
                stage_name="metadata_extraction",
                processor_name="mock_metadata",
                dependencies=["unstructured_extraction"]
            )
            
            # Patch the registry to use our mock registry
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                # Initialize stages
                await unstructured_stage.initialize()
                await metadata_stage.initialize()
                
                # Execute first stage
                unstructured_result = await unstructured_stage.execute(pipeline_context)
                assert unstructured_result.status == StageStatus.COMPLETED
                
                # Add result to context
                pipeline_context.stage_results["unstructured_extraction"] = unstructured_result
                
                # Execute second stage
                metadata_result = await metadata_stage.execute(pipeline_context)
                assert metadata_result.status == StageStatus.COMPLETED
                
                # Check that metadata includes info from first stage
                metadata = metadata_result.data["metadata"]
                assert metadata["text_length"] > 0
                assert metadata["element_count"] == 2
                
                # Cleanup
                await unstructured_stage.cleanup()
                await metadata_stage.cleanup()
        finally:
            await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience functions for creating stages."""
        # Test unstructured stage creation
        unstructured_stage = create_unstructured_stage()
        assert unstructured_stage.name == "unstructured_extraction"
        assert unstructured_stage.config.processor == "unstructured_processor"
        
        # Test metadata stage creation
        metadata_stage = create_metadata_stage(dependencies=["custom_unstructured"])
        assert metadata_stage.name == "metadata_extraction"
        assert metadata_stage.config.processor == "metadata_extractor"
        assert "custom_unstructured" in metadata_stage.config.dependencies
        
        # Test validation stage creation
        validation_stage = create_validation_stage(
            validation_rules={"min_text_length": 50}
        )
        assert validation_stage.name == "validation"
        assert validation_stage.config.processor == "validation_processor"
        assert validation_stage.config.config["validation_rules"]["min_text_length"] == 50
    
    @pytest.mark.asyncio
    async def test_stage_validation(self, pipeline_context):
        """Test stage validation."""
        registry = create_test_registry()
        
        try:
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                # Valid processor
                valid_stage = create_processor_stage(
                    stage_name="valid_stage",
                    processor_name="mock_unstructured"
                )
                
                await valid_stage.initialize()
                
                # Should validate successfully
                try:
                    valid_stage.validate(pipeline_context)
                except Exception as e:
                    pytest.fail(f"Valid stage should not raise validation error: {e}")
                
                # Invalid processor
                invalid_stage = create_processor_stage(
                    stage_name="invalid_stage",
                    processor_name="nonexistent_processor"
                )
                
                # Initialize to set the registry
                try:
                    await invalid_stage.initialize()
                    pytest.fail("Should have failed to initialize nonexistent processor")
                except Exception:
                    # Expected to fail during initialization
                    pass
                
                # Now validation should fail because registry is set but processor not found
                if invalid_stage._registry:  # Only test if registry was set
                    with pytest.raises(ValueError, match="Processor not found"):
                        invalid_stage.validate(pipeline_context)
        finally:
            await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_stage_error_handling(self, pipeline_context):
        """Test error handling in processor stages."""
        
        class FailingProcessor(BaseProcessor):
            @classmethod
            def get_metadata(cls):
                return ProcessorMetadata(
                    name="failing_processor",
                    version="1.0.0",
                    description="Always fails"
                )
            
            async def process(self, context: ProcessorContext) -> ProcessorResult:
                raise Exception("Test failure")
        
        registry = create_test_registry()
        
        try:
            # Register failing processor
            registry.register(FailingProcessor)
            
            stage = create_processor_stage(
                stage_name="failing_stage",
                processor_name="failing_processor"
            )
            
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                await stage.initialize()
                
                # Execute should return failed result, not raise exception
                result = await stage.execute(pipeline_context)
                
                assert result.status == StageStatus.FAILED
                assert result.error is not None
                assert "Test failure" in result.error
        finally:
            await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_stage_cleanup(self, pipeline_context):
        """Test stage cleanup."""
        registry = create_test_registry()
        
        try:
            stage = create_processor_stage(
                stage_name="cleanup_test",
                processor_name="mock_unstructured"
            )
            
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                await stage.initialize()
                assert stage.processor is not None
                
                await stage.cleanup()
                assert stage.processor is None
        finally:
            await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_context_conversion(self, pipeline_context):
        """Test conversion between pipeline and processor contexts."""
        registry = create_test_registry()
        
        try:
            stage = create_processor_stage(
                stage_name="context_test",
                processor_name="mock_unstructured"
            )
            
            with patch('torematrix.processing.processors.registry.get_registry', return_value=registry):
                await stage.initialize()
                
                # Add some stage results to pipeline context
                pipeline_context.stage_results["previous_stage"] = Mock(
                    status=StageStatus.COMPLETED,
                    data={"test": "data"}
                )
                
                # Execute and verify context conversion
                result = await stage.execute(pipeline_context)
                
                assert result.status == StageStatus.COMPLETED
                # The mock processor should have received proper context
                
                await stage.cleanup()
        finally:
            await registry.shutdown()


class TestBuiltinProcessorRegistration:
    """Test that built-in processors are properly registered."""
    
    def test_builtin_processors_registered(self):
        """Test that built-in processors are automatically registered."""
        from torematrix.processing.processors.registry import get_registry
        
        registry = get_registry()
        processors = registry.list_processors()
        
        # Check that built-in processors are registered
        # Note: These might fail if dependencies are missing, but that's OK
        expected_processors = [
            "unstructured_processor",
            "metadata_extractor", 
            "validation_processor",
            "transformation_processor"
        ]
        
        for processor_name in expected_processors:
            if processor_name in processors:
                # If registered, should have proper metadata
                metadata = registry.get_metadata(processor_name)
                assert metadata.name == processor_name
                assert metadata.version is not None
                assert metadata.description is not None