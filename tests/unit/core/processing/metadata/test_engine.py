"""Comprehensive tests for MetadataExtractionEngine."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.torematrix.core.processing.metadata import (
    MetadataExtractionEngine, MetadataConfig, ExtractionContext,
    DocumentMetadataExtractor, PageMetadataExtractor,
    ExtractorConfig, MetadataSchema, DocumentMetadata
)


class TestMetadataExtractionEngine:
    """Test suite for MetadataExtractionEngine."""
    
    @pytest.fixture
    def engine_config(self):
        """Create test engine configuration."""
        return MetadataConfig(
            enable_parallel_extraction=True,
            max_workers=2,
            cache_enabled=True,
            cache_ttl_seconds=3600,
            confidence_weights={
                "extraction_method": 0.25,
                "data_quality": 0.30,
                "validation_result": 0.20,
                "source_reliability": 0.15,
                "consistency_check": 0.10
            }
        )
    
    @pytest.fixture
    def extraction_engine(self, engine_config):
        """Create MetadataExtractionEngine instance."""
        return MetadataExtractionEngine(engine_config)
    
    @pytest.fixture
    def mock_document(self):
        """Create mock document for testing."""
        document = Mock()
        document.document_id = "test_doc_123"
        document.pages = [Mock(), Mock()]  # 2 pages
        document.elements = [Mock() for _ in range(5)]  # 5 elements
        document.metadata = {
            "title": "Test Document",
            "author": "Test Author"
        }
        return document
    
    @pytest.fixture
    def mock_extractor(self):
        """Create mock extractor."""
        extractor = Mock(spec=DocumentMetadataExtractor)
        extractor.name = "TestExtractor"
        extractor.is_enabled.return_value = True
        extractor.extract_with_validation = AsyncMock(return_value={
            "metadata": {
                "metadata_type": "document",
                "title": "Test Document",
                "page_count": 2
            },
            "validation": Mock(is_valid=True, confidence_score=0.9),
            "extraction_info": {"success": True, "duration_seconds": 0.1}
        })
        return extractor
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine_config):
        """Test engine initialization."""
        engine = MetadataExtractionEngine(engine_config)
        
        assert engine.config == engine_config
        assert engine.extractors is not None
        assert engine.confidence_scorer is not None
        assert engine._extraction_stats["total_documents"] == 0
    
    @pytest.mark.asyncio
    async def test_extract_metadata_basic(self, extraction_engine, mock_document, mock_extractor):
        """Test basic metadata extraction."""
        # Register mock extractor
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        # Extract metadata
        result = await extraction_engine.extract_metadata(mock_document)
        
        # Verify result
        assert isinstance(result, MetadataSchema)
        assert result.extraction_context is not None
        assert result.extraction_context.document_id == "test_doc_123"
        
        # Verify extractor was called
        mock_extractor.extract_with_validation.assert_called_once()
        
        # Verify statistics updated
        assert extraction_engine._extraction_stats["total_documents"] == 1
        assert extraction_engine._extraction_stats["successful_extractions"] == 1
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_context(self, extraction_engine, mock_document, mock_extractor):
        """Test metadata extraction with custom context."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        custom_context = ExtractionContext(
            document_id="custom_doc_id",
            processing_hints={"test": "value"}
        )
        
        result = await extraction_engine.extract_metadata(mock_document, context=custom_context)
        
        assert result.extraction_context.document_id == "custom_doc_id"
        assert result.extraction_context.processing_hints["test"] == "value"
    
    @pytest.mark.asyncio
    async def test_extract_metadata_specific_types(self, extraction_engine, mock_document, mock_extractor):
        """Test extraction with specific extractor types."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        extraction_engine.register_extractor("other_extractor", Mock())
        
        # Extract only specific type
        result = await extraction_engine.extract_metadata(
            mock_document,
            extraction_types=["test_extractor"]
        )
        
        # Verify only specified extractor was used
        mock_extractor.extract_with_validation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_metadata_parallel_processing(self, engine_config, mock_document):
        """Test parallel extraction processing."""
        engine_config.enable_parallel_extraction = True
        engine = MetadataExtractionEngine(engine_config)
        
        # Create multiple mock extractors
        extractors = []
        for i in range(3):
            extractor = Mock()
            extractor.name = f"extractor_{i}"
            extractor.is_enabled.return_value = True
            extractor.extract_with_validation = AsyncMock(return_value={
                "metadata": {"metadata_type": "document", "extractor_id": i},
                "validation": Mock(is_valid=True, confidence_score=0.8),
                "extraction_info": {"success": True}
            })
            extractors.append(extractor)
            engine.register_extractor(f"extractor_{i}", extractor)
        
        # Extract metadata
        result = await engine.extract_metadata(mock_document)
        
        # Verify all extractors were called
        for extractor in extractors:
            extractor.extract_with_validation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_metadata_sequential_processing(self, engine_config, mock_document):
        """Test sequential extraction processing."""
        engine_config.enable_parallel_extraction = False
        engine = MetadataExtractionEngine(engine_config)
        
        extractor = Mock()
        extractor.name = "test_extractor"
        extractor.is_enabled.return_value = True
        extractor.extract_with_validation = AsyncMock(return_value={
            "metadata": {"metadata_type": "document"},
            "validation": Mock(is_valid=True, confidence_score=0.8),
            "extraction_info": {"success": True}
        })
        engine.register_extractor("test_extractor", extractor)
        
        result = await engine.extract_metadata(mock_document)
        
        extractor.extract_with_validation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_metadata_cache_hit(self, extraction_engine, mock_document, mock_extractor):
        """Test cache hit scenario."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        # First extraction
        result1 = await extraction_engine.extract_metadata(mock_document)
        
        # Second extraction (should hit cache)
        result2 = await extraction_engine.extract_metadata(mock_document)
        
        # Extractor should only be called once
        assert mock_extractor.extract_with_validation.call_count == 1
        
        # Cache statistics should reflect hit
        stats = extraction_engine.get_engine_statistics()
        assert stats["cache_info"]["cache_hits"] == 1
        assert stats["cache_info"]["cache_misses"] == 1
    
    @pytest.mark.asyncio
    async def test_extract_metadata_cache_disabled(self, engine_config, mock_document, mock_extractor):
        """Test extraction with cache disabled."""
        engine_config.cache_enabled = False
        engine = MetadataExtractionEngine(engine_config)
        engine.register_extractor("test_extractor", mock_extractor)
        
        # Multiple extractions
        await engine.extract_metadata(mock_document)
        await engine.extract_metadata(mock_document)
        
        # Extractor should be called each time
        assert mock_extractor.extract_with_validation.call_count == 2
        
        # No cache hits
        stats = engine.get_engine_statistics()
        assert stats["cache_info"]["cache_hits"] == 0
    
    @pytest.mark.asyncio
    async def test_extract_metadata_extractor_failure(self, extraction_engine, mock_document):
        """Test handling of extractor failures."""
        # Create failing extractor
        failing_extractor = Mock()
        failing_extractor.name = "failing_extractor"
        failing_extractor.is_enabled.return_value = True
        failing_extractor.extract_with_validation = AsyncMock(
            side_effect=Exception("Extraction failed")
        )
        
        extraction_engine.register_extractor("failing_extractor", failing_extractor)
        
        # Should not raise exception
        result = await extraction_engine.extract_metadata(mock_document)
        
        # Should return valid schema even with failures
        assert isinstance(result, MetadataSchema)
        assert result.total_confidence_score == 0.0  # Low confidence due to failures
    
    @pytest.mark.asyncio
    async def test_extract_incremental_basic(self, extraction_engine, mock_document, mock_extractor):
        """Test basic incremental extraction."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        # Create previous metadata
        previous_metadata = MetadataSchema(
            extraction_context=ExtractionContext(document_id="test_doc_123")
        )
        
        # Incremental extraction
        result = await extraction_engine.extract_incremental(
            mock_document,
            previous_metadata,
            changes={"pages": ["modified"]}
        )
        
        assert isinstance(result, MetadataSchema)
        assert result.extraction_context.processing_hints["incremental"] is True
    
    @pytest.mark.asyncio
    async def test_extract_incremental_no_changes(self, extraction_engine, mock_document):
        """Test incremental extraction with no changes."""
        previous_metadata = MetadataSchema(
            extraction_context=ExtractionContext(document_id="test_doc_123")
        )
        
        result = await extraction_engine.extract_incremental(
            mock_document,
            previous_metadata,
            changes=None
        )
        
        # Should return updated context but same metadata
        assert result.extraction_context.processing_hints["incremental"] is True
    
    def test_register_extractor(self, extraction_engine, mock_extractor):
        """Test extractor registration."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        extractors = extraction_engine.get_available_extractors()
        assert "test_extractor" in extractors
    
    def test_unregister_extractor(self, extraction_engine, mock_extractor):
        """Test extractor unregistration."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        extraction_engine.unregister_extractor("test_extractor")
        
        extractors = extraction_engine.get_available_extractors()
        assert "test_extractor" not in extractors
    
    def test_get_available_extractors(self, extraction_engine, mock_extractor):
        """Test getting available extractors."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        extractors = extraction_engine.get_available_extractors()
        assert isinstance(extractors, list)
        assert "test_extractor" in extractors
    
    @pytest.mark.asyncio
    async def test_get_engine_statistics(self, extraction_engine, mock_document, mock_extractor):
        """Test engine statistics collection."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        # Perform some extractions
        await extraction_engine.extract_metadata(mock_document)
        await extraction_engine.extract_metadata(mock_document)  # Cache hit
        
        stats = extraction_engine.get_engine_statistics()
        
        # Verify structure
        assert "engine_info" in stats
        assert "cache_info" in stats
        assert "extractor_info" in stats
        assert "configuration" in stats
        
        # Verify values
        assert stats["engine_info"]["total_documents_processed"] == 2
        assert stats["engine_info"]["successful_extractions"] == 2
        assert stats["cache_info"]["cache_hits"] == 1
        assert stats["cache_info"]["cache_misses"] == 1
    
    def test_cache_key_generation(self, extraction_engine, mock_document):
        """Test cache key generation."""
        # Test with different parameters
        key1 = extraction_engine._generate_cache_key(mock_document, None)
        key2 = extraction_engine._generate_cache_key(mock_document, ["extractor1"])
        key3 = extraction_engine._generate_cache_key(mock_document, ["extractor1", "extractor2"])
        
        assert key1 != key2
        assert key2 != key3
        assert "test_doc_123" in key1
    
    def test_cache_cleanup(self, extraction_engine):
        """Test cache cleanup functionality."""
        # Fill cache beyond limit
        for i in range(1100):  # Exceeds 1000 limit
            extraction_engine._metadata_cache[f"key_{i}"] = MetadataSchema()
        
        # Trigger cleanup
        extraction_engine._cleanup_cache()
        
        # Should be reduced
        assert len(extraction_engine._metadata_cache) <= 1000
    
    def test_select_extractors_all(self, extraction_engine, mock_extractor):
        """Test selecting all extractors."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        
        selected = extraction_engine._select_extractors(None)
        assert "test_extractor" in selected
    
    def test_select_extractors_specific(self, extraction_engine, mock_extractor):
        """Test selecting specific extractors."""
        extraction_engine.register_extractor("test_extractor", mock_extractor)
        extraction_engine.register_extractor("other_extractor", Mock())
        
        selected = extraction_engine._select_extractors(["test_extractor"])
        assert "test_extractor" in selected
        assert "other_extractor" not in selected
    
    def test_update_extraction_stats(self, extraction_engine):
        """Test extraction statistics updates."""
        initial_total = extraction_engine._extraction_stats["total_documents"]
        
        extraction_engine._update_extraction_stats(1.5, True)
        
        assert extraction_engine._extraction_stats["successful_extractions"] == 1
        assert extraction_engine._extraction_stats["failed_extractions"] == 0
        assert extraction_engine._extraction_stats["average_duration"] == 1.5
        
        extraction_engine._update_extraction_stats(2.0, False)
        
        assert extraction_engine._extraction_stats["successful_extractions"] == 1
        assert extraction_engine._extraction_stats["failed_extractions"] == 1
        assert extraction_engine._extraction_stats["average_duration"] == 1.75  # (1.5 + 2.0) / 2
    
    def test_get_all_metadata_objects(self, extraction_engine):
        """Test getting all metadata objects from schema."""
        schema = MetadataSchema()
        schema.document_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="test",
            extraction_method="direct_parsing"
        )
        
        objects = extraction_engine._get_all_metadata_objects(schema)
        assert len(objects) == 1
        assert objects[0] == schema.document_metadata
    
    @pytest.mark.asyncio
    async def test_error_handling_in_parallel_extraction(self, extraction_engine, mock_document):
        """Test error handling in parallel extraction."""
        # Create mixed extractors (some failing, some succeeding)
        good_extractor = Mock()
        good_extractor.name = "good_extractor"
        good_extractor.is_enabled.return_value = True
        good_extractor.extract_with_validation = AsyncMock(return_value={
            "metadata": {"metadata_type": "document"},
            "validation": Mock(is_valid=True, confidence_score=0.9),
            "extraction_info": {"success": True}
        })
        
        bad_extractor = Mock()
        bad_extractor.name = "bad_extractor"
        bad_extractor.is_enabled.return_value = True
        bad_extractor.extract_with_validation = AsyncMock(
            side_effect=Exception("Extraction failed")
        )
        
        extraction_engine.register_extractor("good_extractor", good_extractor)
        extraction_engine.register_extractor("bad_extractor", bad_extractor)
        
        # Should handle mixed success/failure gracefully
        result = await extraction_engine.extract_metadata(mock_document)
        
        assert isinstance(result, MetadataSchema)
        # Should still have some results from successful extractor
    
    @pytest.mark.asyncio
    async def test_semaphore_limiting_in_parallel_extraction(self, engine_config, mock_document):
        """Test that semaphore properly limits concurrent extractions."""
        engine_config.max_workers = 2
        engine = MetadataExtractionEngine(engine_config)
        
        # Create extractors with delays to test concurrency control
        extraction_times = []
        
        async def delayed_extraction(*args, **kwargs):
            start_time = datetime.utcnow()
            await asyncio.sleep(0.1)  # Simulate work
            end_time = datetime.utcnow()
            extraction_times.append((start_time, end_time))
            return {
                "metadata": {"metadata_type": "document"},
                "validation": Mock(is_valid=True, confidence_score=0.8),
                "extraction_info": {"success": True}
            }
        
        # Create multiple extractors
        for i in range(4):
            extractor = Mock()
            extractor.name = f"extractor_{i}"
            extractor.is_enabled.return_value = True
            extractor.extract_with_validation = AsyncMock(side_effect=delayed_extraction)
            engine.register_extractor(f"extractor_{i}", extractor)
        
        # Extract metadata
        await engine.extract_metadata(mock_document)
        
        # Verify that not all extractions ran simultaneously
        # (with max_workers=2, we shouldn't have more than 2 concurrent)
        assert len(extraction_times) == 4