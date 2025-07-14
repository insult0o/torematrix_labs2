"""Unit tests for processor registry."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus
)
from torematrix.processing.processors.registry import ProcessorRegistry, get_registry
from torematrix.processing.processors.base import ProcessorException


class TestProcessor(BaseProcessor):
    """Test processor for registry tests."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.init_called = False
        self.cleanup_called = False
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="test_processor",
            version="1.0.0",
            description="Test processor",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION],
            supported_formats=["txt", "pdf"]
        )
    
    async def _initialize(self) -> None:
        self.init_called = True
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=context.document_id,  # Using for test
            end_time=context.document_id,
            extracted_data={"test": True}
        )
    
    async def _cleanup(self) -> None:
        self.cleanup_called = True


class AnotherTestProcessor(BaseProcessor):
    """Another test processor."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="another_processor",
            version="2.0.0",
            description="Another test processor",
            capabilities=[ProcessorCapability.METADATA_EXTRACTION],
            supported_formats=["pdf", "docx"]
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=context.document_id,
            end_time=context.document_id,
            extracted_data={"another": True}
        )


class ProcessorWithDependency(BaseProcessor):
    """Test processor with dependency injection."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._inject_test_service = None  # Will be injected
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="dependency_processor",
            version="1.0.0",
            description="Processor with dependency"
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=context.document_id,
            end_time=context.document_id,
            extracted_data={"service": str(self._inject_test_service)}
        )


@pytest.fixture
async def registry():
    """Create fresh processor registry."""
    return ProcessorRegistry()


@pytest.fixture
def test_context():
    """Create test context."""
    return ProcessorContext(
        document_id="doc123",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf"
    )


class TestProcessorRegistry:
    """Test cases for ProcessorRegistry."""
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry._processors) == 0
        assert len(registry._instances) == 0
        assert len(registry._metadata_cache) == 0
    
    def test_register_processor(self, registry):
        """Test processor registration."""
        registry.register(TestProcessor)
        
        assert "test_processor" in registry.list_processors()
        assert registry.get_metadata("test_processor").name == "test_processor"
        assert registry.get_metadata("test_processor").version == "1.0.0"
    
    def test_register_with_custom_name(self, registry):
        """Test registration with custom name."""
        registry.register(TestProcessor, name="custom_name")
        
        assert "custom_name" in registry.list_processors()
        assert "test_processor" not in registry.list_processors()
        assert registry.get_metadata("custom_name").name == "test_processor"  # Original metadata
    
    def test_register_overwrites_existing(self, registry):
        """Test that registration overwrites existing processor."""
        registry.register(TestProcessor)
        original_count = len(registry.list_processors())
        
        registry.register(TestProcessor)  # Register again
        
        assert len(registry.list_processors()) == original_count
        assert "test_processor" in registry.list_processors()
    
    def test_unregister_processor(self, registry):
        """Test processor unregistration."""
        registry.register(TestProcessor)
        assert "test_processor" in registry.list_processors()
        
        registry.unregister("test_processor")
        
        assert "test_processor" not in registry.list_processors()
        with pytest.raises(ProcessorException, match="Unknown processor"):
            registry.get_metadata("test_processor")
    
    def test_get_processor_class(self, registry):
        """Test getting processor class."""
        registry.register(TestProcessor)
        
        processor_class = registry.get_processor_class("test_processor")
        assert processor_class == TestProcessor
        
        with pytest.raises(ProcessorException, match="Unknown processor"):
            registry.get_processor_class("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_processor_instance(self, registry):
        """Test getting processor instance."""
        registry.register(TestProcessor)
        
        processor = await registry.get_processor("test_processor")
        
        assert isinstance(processor, TestProcessor)
        assert processor._initialized
        assert processor.init_called
    
    @pytest.mark.asyncio
    async def test_singleton_behavior(self, registry):
        """Test singleton behavior for same config."""
        registry.register(TestProcessor)
        
        config = {"key": "value"}
        proc1 = await registry.get_processor("test_processor", config)
        proc2 = await registry.get_processor("test_processor", config)
        
        # Should be same instance
        assert proc1 is proc2
        
        # Different config should create new instance
        proc3 = await registry.get_processor("test_processor", {"key": "different"})
        assert proc3 is not proc1
        assert proc3 is not proc2
    
    @pytest.mark.asyncio
    async def test_get_processor_with_config(self, registry):
        """Test getting processor with configuration."""
        registry.register(TestProcessor)
        
        config = {"test_config": "value"}
        processor = await registry.get_processor("test_processor", config)
        
        assert processor.config == config
    
    def test_dependency_injection(self, registry):
        """Test dependency injection."""
        registry.register(ProcessorWithDependency)
        
        # Register dependency
        mock_service = Mock()
        mock_service.name = "test_service"
        registry.register_dependency("test_service", mock_service)
        
        assert "test_service" in registry._dependencies
        assert registry._dependencies["test_service"] is mock_service
    
    @pytest.mark.asyncio
    async def test_dependency_injection_in_processor(self, registry):
        """Test that dependencies are injected into processors."""
        registry.register(ProcessorWithDependency)
        
        # Register dependency
        mock_service = Mock()
        mock_service.name = "test_service"
        registry.register_dependency("test_service", mock_service)
        
        processor = await registry.get_processor("dependency_processor")
        
        # Check that dependency was injected
        assert hasattr(processor, "test_service")
        assert processor.test_service is mock_service
    
    def test_find_by_capability(self, registry):
        """Test finding processors by capability."""
        registry.register(TestProcessor)
        registry.register(AnotherTestProcessor)
        
        text_processors = registry.find_by_capability(ProcessorCapability.TEXT_EXTRACTION)
        metadata_processors = registry.find_by_capability(ProcessorCapability.METADATA_EXTRACTION)
        
        assert "test_processor" in text_processors
        assert "another_processor" not in text_processors
        
        assert "another_processor" in metadata_processors
        assert "test_processor" not in metadata_processors
    
    def test_find_by_format(self, registry):
        """Test finding processors by format."""
        registry.register(TestProcessor)
        registry.register(AnotherTestProcessor)
        
        pdf_processors = registry.find_by_format("pdf")
        txt_processors = registry.find_by_format("txt")
        docx_processors = registry.find_by_format("docx")
        
        assert "test_processor" in pdf_processors
        assert "another_processor" in pdf_processors
        
        assert "test_processor" in txt_processors
        assert "another_processor" not in txt_processors
        
        assert "test_processor" not in docx_processors
        assert "another_processor" in docx_processors
    
    def test_load_hooks(self, registry):
        """Test load hooks."""
        hook_calls = []
        
        def load_hook(name, processor_class):
            hook_calls.append((name, processor_class))
        
        registry.add_load_hook(load_hook)
        registry.register(TestProcessor)
        
        assert len(hook_calls) == 1
        assert hook_calls[0][0] == "test_processor"
        assert hook_calls[0][1] == TestProcessor
    
    def test_unload_hooks(self, registry):
        """Test unload hooks."""
        hook_calls = []
        
        def unload_hook(name):
            hook_calls.append(name)
        
        registry.add_unload_hook(unload_hook)
        registry.register(TestProcessor)
        registry.unregister("test_processor")
        
        assert "test_processor" in hook_calls
    
    @pytest.mark.asyncio
    async def test_processor_context_manager(self, registry, test_context):
        """Test processor context manager."""
        registry.register(TestProcessor)
        
        async with registry.processor_context("test_processor") as processor:
            assert isinstance(processor, TestProcessor)
            assert processor._initialized
            
            result = await processor.process(test_context)
            assert result.status == StageStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_shutdown(self, registry):
        """Test registry shutdown."""
        registry.register(TestProcessor)
        registry.register(AnotherTestProcessor)
        
        # Create some instances
        proc1 = await registry.get_processor("test_processor")
        proc2 = await registry.get_processor("another_processor")
        
        assert len(registry._instances) > 0
        assert proc1._initialized
        assert proc2._initialized
        
        await registry.shutdown()
        
        # All instances should be cleaned up
        assert len(registry._instances) == 0
        assert proc1.cleanup_called
    
    @patch('importlib.import_module')
    def test_load_from_module(self, mock_import, registry):
        """Test loading processors from module."""
        # Mock module with processor class
        mock_module = Mock()
        mock_module.__dict__ = {
            'TestProcessor': TestProcessor,
            'NotAProcessor': str,  # Should be ignored
            'BaseProcessor': BaseProcessor  # Should be ignored (base class)
        }
        mock_import.return_value = mock_module
        
        # Mock inspect.getmembers to return our test data
        with patch('inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [
                ('TestProcessor', TestProcessor),
                ('NotAProcessor', str),
                ('BaseProcessor', BaseProcessor)
            ]
            
            registry.load_from_module("test.module")
            
            assert "test_processor" in registry.list_processors()
    
    @patch('importlib.import_module')
    def test_load_from_module_import_error(self, mock_import, registry):
        """Test handling import error when loading module."""
        mock_import.side_effect = ImportError("Module not found")
        
        with pytest.raises(ProcessorException, match="Cannot load module"):
            registry.load_from_module("nonexistent.module")
    
    @patch('pathlib.Path.glob')
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    def test_load_from_directory(self, mock_module_from_spec, mock_spec_from_file, mock_glob, registry):
        """Test loading processors from directory."""
        from pathlib import Path
        
        # Mock file list
        mock_file = Mock()
        mock_file.name = "test_processor.py"
        mock_file.stem = "test_processor"
        mock_glob.return_value = [mock_file]
        
        # Mock module loading
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec
        
        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module
        
        # Mock inspect.getmembers
        with patch('inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [('TestProcessor', TestProcessor)]
            
            registry.load_from_directory(Path("/test/dir"))
            
            assert "test_processor" in registry.list_processors()
    
    def test_global_registry(self):
        """Test global registry access."""
        registry = get_registry()
        assert isinstance(registry, ProcessorRegistry)
        
        # Should return same instance
        registry2 = get_registry()
        assert registry is registry2