"""Comprehensive tests for base extractor classes."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.torematrix.core.processing.metadata.extractors import (
    BaseExtractor, ExtractorRegistry, ExtractorError, 
    ExtractionTimeoutError, ValidationError
)
from src.torematrix.core.processing.metadata import (
    ExtractorConfig, ExtractionContext, MetadataValidationResult,
    ExtractionMethod
)


class MockExtractor(BaseExtractor):
    """Mock extractor for testing base functionality."""
    
    def get_supported_extraction_methods(self):
        return [ExtractionMethod.DIRECT_PARSING, ExtractionMethod.HEURISTIC_ANALYSIS]
    
    async def extract(self, document, context):
        await asyncio.sleep(0.01)  # Simulate work
        return {
            "metadata_type": "test",
            "content": "test content",
            "extraction_method": ExtractionMethod.DIRECT_PARSING
        }
    
    def validate_metadata(self, metadata):
        is_valid = "content" in metadata and metadata["content"]
        confidence = 0.9 if is_valid else 0.1
        errors = [] if is_valid else ["Missing content"]
        
        return MetadataValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            validation_errors=errors
        )


class FailingExtractor(BaseExtractor):
    """Extractor that always fails for testing error handling."""
    
    def get_supported_extraction_methods(self):
        return [ExtractionMethod.HEURISTIC_ANALYSIS]
    
    async def extract(self, document, context):
        raise ExtractorError("Extraction always fails")
    
    def validate_metadata(self, metadata):
        return MetadataValidationResult(
            is_valid=False,
            confidence_score=0.0,
            validation_errors=["Always fails"]
        )


class SlowExtractor(BaseExtractor):
    """Extractor that takes a long time for timeout testing."""
    
    def get_supported_extraction_methods(self):
        return [ExtractionMethod.OCR_EXTRACTION]
    
    async def extract(self, document, context):
        await asyncio.sleep(2.0)  # Longer than typical timeout
        return {"metadata_type": "slow", "content": "slow content"}
    
    def validate_metadata(self, metadata):
        return MetadataValidationResult(
            is_valid=True,
            confidence_score=0.8
        )


class TestBaseExtractor:
    """Test suite for BaseExtractor class."""
    
    @pytest.fixture
    def extractor_config(self):
        """Create test extractor configuration."""
        return ExtractorConfig(
            enabled=True,
            confidence_threshold=0.5,
            timeout_seconds=1.0,
            retry_attempts=2
        )
    
    @pytest.fixture
    def mock_extractor(self, extractor_config):
        """Create mock extractor instance."""
        return MockExtractor(extractor_config)
    
    @pytest.fixture
    def extraction_context(self):
        """Create test extraction context."""
        return ExtractionContext(
            document_id="test_doc",
            extraction_timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def mock_document(self):
        """Create mock document."""
        return Mock(document_id="test_doc", content="test content")
    
    def test_base_extractor_initialization(self, extractor_config):
        """Test base extractor initialization."""
        extractor = MockExtractor(extractor_config)
        
        assert extractor.config == extractor_config
        assert extractor.name == "MockExtractor"
        assert extractor._extraction_stats["total_extractions"] == 0
    
    def test_get_confidence_factors(self, mock_extractor):
        """Test getting confidence factors."""
        factors = mock_extractor.get_confidence_factors()
        
        expected_factors = [
            "extraction_method", "data_quality", 
            "validation_result", "source_reliability"
        ]
        assert factors == expected_factors
    
    def test_supports_method(self, mock_extractor):
        """Test extraction method support checking."""
        assert mock_extractor.supports_method(ExtractionMethod.DIRECT_PARSING)
        assert mock_extractor.supports_method(ExtractionMethod.HEURISTIC_ANALYSIS)
        assert not mock_extractor.supports_method(ExtractionMethod.OCR_EXTRACTION)
    
    def test_is_enabled(self, extractor_config):
        """Test enabled status checking."""
        extractor = MockExtractor(extractor_config)
        assert extractor.is_enabled()
        
        extractor_config.enabled = False
        extractor = MockExtractor(extractor_config)
        assert not extractor.is_enabled()
    
    @pytest.mark.asyncio
    async def test_extract_with_validation_success(self, mock_extractor, mock_document, extraction_context):
        """Test successful extraction with validation."""
        result = await mock_extractor.extract_with_validation(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is True
        assert "metadata" in result
        assert "validation" in result
        assert result["metadata"]["content"] == "test content"
        assert result["validation"].is_valid is True
    
    @pytest.mark.asyncio
    async def test_extract_with_validation_failure(self, extractor_config, mock_document, extraction_context):
        """Test extraction failure handling."""
        failing_extractor = FailingExtractor(extractor_config)
        
        result = await failing_extractor.extract_with_validation(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is False
        assert "error" in result["extraction_info"]
        assert result["validation"].is_valid is False
    
    @pytest.mark.asyncio
    async def test_extract_with_validation_timeout(self, extractor_config, mock_document, extraction_context):
        """Test extraction timeout handling."""
        extractor_config.timeout_seconds = 0.1  # Very short timeout
        slow_extractor = SlowExtractor(extractor_config)
        
        result = await slow_extractor.extract_with_validation(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is False
        assert "timeout" in result["extraction_info"]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_extract_with_validation_no_timeout(self, extractor_config, mock_document, extraction_context):
        """Test extraction without timeout."""
        extractor_config.timeout_seconds = None
        extractor = MockExtractor(extractor_config)
        
        result = await extractor.extract_with_validation(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_with_validation_confidence_threshold(self, extractor_config, mock_document, extraction_context):
        """Test confidence threshold filtering."""
        extractor_config.confidence_threshold = 0.95  # Very high threshold
        extractor = MockExtractor(extractor_config)
        
        # Mock validation with lower confidence
        with patch.object(extractor, 'validate_metadata') as mock_validate:
            mock_validate.return_value = MetadataValidationResult(
                is_valid=True,
                confidence_score=0.8  # Below threshold
            )
            
            result = await extractor.extract_with_validation(mock_document, extraction_context)
            
            # Should still succeed but log warning
            assert result["extraction_info"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_with_retry_success_first_attempt(self, mock_extractor, mock_document, extraction_context):
        """Test retry logic with success on first attempt."""
        result = await mock_extractor.extract_with_retry(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is True
        # Should not have attempts field for first-try success
        assert "attempts" not in result["extraction_info"]
    
    @pytest.mark.asyncio
    async def test_extract_with_retry_success_after_failure(self, extractor_config, mock_document, extraction_context):
        """Test retry logic with success after initial failure."""
        extractor = MockExtractor(extractor_config)
        
        # Mock extract to fail first time, succeed second time
        call_count = 0
        original_extract = extractor.extract
        
        async def failing_then_succeeding_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExtractorError("First attempt fails")
            return await original_extract(*args, **kwargs)
        
        with patch.object(extractor, 'extract', side_effect=failing_then_succeeding_extract):
            result = await extractor.extract_with_retry(mock_document, extraction_context)
            
            assert result["extraction_info"]["success"] is True
            assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_extract_with_retry_all_attempts_fail(self, extractor_config, mock_document, extraction_context):
        """Test retry logic when all attempts fail."""
        extractor_config.retry_attempts = 2
        failing_extractor = FailingExtractor(extractor_config)
        
        result = await failing_extractor.extract_with_retry(mock_document, extraction_context)
        
        assert result["extraction_info"]["success"] is False
        assert result["extraction_info"]["attempts"] == 3  # Original + 2 retries
        assert "Max retries exceeded" in result["extraction_info"]["error"]
    
    @pytest.mark.asyncio
    async def test_extract_with_retry_exponential_backoff(self, extractor_config, mock_document, extraction_context):
        """Test exponential backoff in retry logic."""
        extractor_config.retry_attempts = 2
        failing_extractor = FailingExtractor(extractor_config)
        
        start_time = datetime.utcnow()
        
        with patch('asyncio.sleep') as mock_sleep:
            await failing_extractor.extract_with_retry(mock_document, extraction_context)
            
            # Should have called sleep with exponential backoff
            expected_calls = [((1,),), ((2,),)]  # 2^0, 2^1
            assert mock_sleep.call_args_list == expected_calls
    
    def test_get_extraction_statistics(self, mock_extractor):
        """Test extraction statistics tracking."""
        # Initially empty
        stats = mock_extractor.get_extraction_statistics()
        assert stats["total_extractions"] == 0
        assert stats["success_rate"] == 0.0
        
        # Simulate some extractions
        mock_extractor._extraction_stats.update({
            "total_extractions": 10,
            "successful_extractions": 8,
            "failed_extractions": 2,
            "average_duration": 1.5
        })
        
        stats = mock_extractor.get_extraction_statistics()
        assert stats["total_extractions"] == 10
        assert stats["successful_extractions"] == 8
        assert stats["failed_extractions"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["failure_rate"] == 0.2
        assert stats["average_duration_seconds"] == 1.5
    
    def test_reset_statistics(self, mock_extractor):
        """Test statistics reset."""
        # Set some statistics
        mock_extractor._extraction_stats.update({
            "total_extractions": 5,
            "successful_extractions": 3,
            "failed_extractions": 2,
            "average_duration": 2.0
        })
        
        # Reset
        mock_extractor.reset_statistics()
        
        stats = mock_extractor.get_extraction_statistics()
        assert stats["total_extractions"] == 0
        assert stats["successful_extractions"] == 0
        assert stats["failed_extractions"] == 0
        assert stats["average_duration_seconds"] == 0.0
    
    def test_get_extractor_info(self, mock_extractor):
        """Test extractor information retrieval."""
        info = mock_extractor.get_extractor_info()
        
        assert info["name"] == "MockExtractor"
        assert info["class"] == "MockExtractor"
        assert info["enabled"] is True
        assert "supported_methods" in info
        assert "confidence_factors" in info
        assert "configuration" in info
        assert "statistics" in info
    
    def test_update_average_duration(self, mock_extractor):
        """Test average duration calculation."""
        # First extraction
        mock_extractor._extraction_stats["total_extractions"] = 1
        mock_extractor._update_average_duration(2.0)
        assert mock_extractor._extraction_stats["average_duration"] == 2.0
        
        # Second extraction
        mock_extractor._extraction_stats["total_extractions"] = 2
        mock_extractor._update_average_duration(4.0)
        assert mock_extractor._extraction_stats["average_duration"] == 3.0  # (2.0 + 4.0) / 2
        
        # Third extraction
        mock_extractor._extraction_stats["total_extractions"] = 3
        mock_extractor._update_average_duration(3.0)
        assert mock_extractor._extraction_stats["average_duration"] == 3.0  # (2.0 + 4.0 + 3.0) / 3


class TestExtractorRegistry:
    """Test suite for ExtractorRegistry class."""
    
    @pytest.fixture
    def registry(self):
        """Create extractor registry."""
        return ExtractorRegistry()
    
    @pytest.fixture
    def mock_extractor(self):
        """Create mock extractor."""
        config = ExtractorConfig()
        return MockExtractor(config)
    
    @pytest.fixture
    def disabled_extractor(self):
        """Create disabled extractor."""
        config = ExtractorConfig(enabled=False)
        return MockExtractor(config)
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry._extractors) == 0
        assert len(registry._extractor_classes) == 0
    
    def test_register_extractor(self, registry, mock_extractor):
        """Test extractor registration."""
        registry.register_extractor("test_extractor", mock_extractor)
        
        assert "test_extractor" in registry._extractors
        assert registry._extractors["test_extractor"] == mock_extractor
        assert "test_extractor" in registry._extractor_classes
    
    def test_register_extractor_overwrite(self, registry, mock_extractor):
        """Test extractor overwrite registration."""
        config = ExtractorConfig()
        new_extractor = MockExtractor(config)
        
        # Register first extractor
        registry.register_extractor("test_extractor", mock_extractor)
        
        # Register with same name (should overwrite)
        registry.register_extractor("test_extractor", new_extractor)
        
        assert registry._extractors["test_extractor"] == new_extractor
    
    def test_unregister_extractor(self, registry, mock_extractor):
        """Test extractor unregistration."""
        registry.register_extractor("test_extractor", mock_extractor)
        registry.unregister_extractor("test_extractor")
        
        assert "test_extractor" not in registry._extractors
        assert "test_extractor" not in registry._extractor_classes
    
    def test_unregister_nonexistent_extractor(self, registry):
        """Test unregistering non-existent extractor."""
        # Should not raise exception
        registry.unregister_extractor("nonexistent")
    
    def test_get_extractor(self, registry, mock_extractor):
        """Test getting extractor by name."""
        registry.register_extractor("test_extractor", mock_extractor)
        
        retrieved = registry.get_extractor("test_extractor")
        assert retrieved == mock_extractor
        
        # Non-existent extractor
        assert registry.get_extractor("nonexistent") is None
    
    def test_get_enabled_extractors(self, registry, mock_extractor, disabled_extractor):
        """Test getting enabled extractors only."""
        registry.register_extractor("enabled_extractor", mock_extractor)
        registry.register_extractor("disabled_extractor", disabled_extractor)
        
        enabled = registry.get_enabled_extractors()
        
        assert "enabled_extractor" in enabled
        assert "disabled_extractor" not in enabled
        assert len(enabled) == 1
    
    def test_get_extractors_by_method(self, registry, mock_extractor):
        """Test getting extractors by extraction method."""
        registry.register_extractor("test_extractor", mock_extractor)
        
        # Method supported by mock extractor
        matching = registry.get_extractors_by_method(ExtractionMethod.DIRECT_PARSING)
        assert "test_extractor" in matching
        
        # Method not supported
        matching = registry.get_extractors_by_method(ExtractionMethod.OCR_EXTRACTION)
        assert len(matching) == 0
    
    def test_get_extractors_by_method_disabled(self, registry, disabled_extractor):
        """Test that disabled extractors are excluded from method filtering."""
        registry.register_extractor("disabled_extractor", disabled_extractor)
        
        matching = registry.get_extractors_by_method(ExtractionMethod.DIRECT_PARSING)
        assert len(matching) == 0  # Disabled extractor should not be included
    
    def test_list_extractors(self, registry, mock_extractor):
        """Test listing all extractors."""
        registry.register_extractor("extractor1", mock_extractor)
        registry.register_extractor("extractor2", mock_extractor)
        
        extractors = registry.list_extractors()
        assert "extractor1" in extractors
        assert "extractor2" in extractors
        assert len(extractors) == 2
    
    def test_get_registry_info(self, registry, mock_extractor, disabled_extractor):
        """Test getting comprehensive registry information."""
        registry.register_extractor("enabled_extractor", mock_extractor)
        registry.register_extractor("disabled_extractor", disabled_extractor)
        
        info = registry.get_registry_info()
        
        assert info["total_extractors"] == 2
        assert info["enabled_extractors"] == 1
        assert "extractor_details" in info
        assert "enabled_extractor" in info["extractor_details"]
        assert "disabled_extractor" in info["extractor_details"]


class TestExtractorErrors:
    """Test suite for extractor error classes."""
    
    def test_extractor_error(self):
        """Test ExtractorError exception."""
        error = ExtractorError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_extraction_timeout_error(self):
        """Test ExtractionTimeoutError exception."""
        error = ExtractionTimeoutError("Timeout occurred")
        assert str(error) == "Timeout occurred"
        assert isinstance(error, ExtractorError)
    
    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, ExtractorError)
    
    def test_error_inheritance(self):
        """Test error class inheritance."""
        # All custom errors should inherit from ExtractorError
        assert issubclass(ExtractionTimeoutError, ExtractorError)
        assert issubclass(ValidationError, ExtractorError)
        
        # ExtractorError should inherit from Exception
        assert issubclass(ExtractorError, Exception)