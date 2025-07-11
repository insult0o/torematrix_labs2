#!/usr/bin/env python3
"""
Unit tests for TextExtractionService.

Tests the text extraction functionality that consolidates multiple
extraction methods from the original codebase.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.services.text_extraction_service import (
    TextExtractionService,
    ExtractionResult
)
from core.services.coordinate_mapping_service import (
    CoordinateMappingService,
    Coordinates,
    CoordinateSystem
)
from core.models.unified_document_model import UnifiedDocument


@pytest.mark.unit
class TestTextExtractionService:
    """Test cases for TextExtractionService."""
    
    def test_initialization(self, coordinate_service):
        """Test service initialization."""
        service = TextExtractionService(coordinate_service)
        
        assert service is not None
        assert service.coordinate_service == coordinate_service
        assert service.extraction_cache == {}
        assert service.stats["extractions_performed"] == 0
    
    @patch('fitz.open')
    def test_extract_text_basic(self, mock_fitz_open, text_extraction_service, sample_document):
        """Test basic text extraction functionality."""
        # Mock PyMuPDF document
        mock_doc = Mock()
        mock_page = Mock()
        
        # Setup page text
        mock_page.get_text.return_value = "Sample document text content."
        mock_page.get_text.side_effect = None  # Reset side_effect
        
        # Setup text dict for coordinates
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "chars": [
                                        {"bbox": [10, 10, 20, 20], "c": "S"},
                                        {"bbox": [20, 10, 30, 20], "c": "a"},
                                        {"bbox": [30, 10, 40, 20], "c": "m"},
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Setup document mock
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc
        
        # Perform extraction
        result = text_extraction_service.extract_text(sample_document)
        
        # Verify result
        assert isinstance(result, ExtractionResult)
        assert result.extraction_method == "pymupdf"
        assert len(result.pages) == 1
        assert result.pages[0]["page"] == 1
        assert result.character_count > 0
        assert result.extraction_time > 0
    
    @patch('fitz.open')
    def test_extract_page_text(self, mock_fitz_open, text_extraction_service, sample_document):
        """Test single page text extraction."""
        # Mock PyMuPDF document and page
        mock_doc = Mock()
        mock_page = Mock()
        
        mock_page.get_text.return_value = "Page 1 content"
        mock_page.get_text.side_effect = [
            "Page 1 content",  # First call for plain text
            {  # Second call for coordinates
                "blocks": [
                    {
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "chars": [
                                            {"bbox": [10, 10, 20, 20], "c": "P"},
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc
        
        # Extract page text
        page_data = text_extraction_service.extract_page_text(sample_document, 1)
        
        # Verify result
        assert page_data["page"] == 1
        assert "text" in page_data
        assert "coordinates" in page_data
        assert "metadata" in page_data
    
    def test_extract_text_caching(self, text_extraction_service, sample_document):
        """Test that extraction results are cached properly."""
        # Mock the actual extraction method
        text_extraction_service._perform_extraction = Mock(return_value=ExtractionResult(
            text="Cached content",
            extraction_method="pymupdf"
        ))
        
        # First extraction
        result1 = text_extraction_service.extract_text(sample_document)
        
        # Second extraction (should use cache)
        result2 = text_extraction_service.extract_text(sample_document)
        
        # Verify caching
        assert text_extraction_service._perform_extraction.call_count == 1
        assert text_extraction_service.stats["cache_hits"] == 1
        assert result1.text == result2.text
    
    @patch('fitz.open')
    def test_search_text_in_document(self, mock_fitz_open, text_extraction_service, sample_document):
        """Test text search functionality."""
        # Mock extraction result
        mock_extraction_result = ExtractionResult(
            text="This is a test document. Test again.",
            pages=[
                {
                    "page": 1,
                    "text": "This is a test document. Test again.",
                    "coordinates": {
                        "10": {"bbox": [100, 100, 110, 120]},  # 't' in 'test'
                        "27": {"bbox": [200, 100, 210, 120]}   # 'T' in 'Test'
                    }
                }
            ]
        )
        
        text_extraction_service.extract_text = Mock(return_value=mock_extraction_result)
        
        # Search for text
        results = text_extraction_service.search_text_in_document(
            sample_document, "test", case_sensitive=False
        )
        
        # Verify search results
        assert len(results) == 2  # Should find "test" and "Test"
        
        for result in results:
            assert "text" in result
            assert "page" in result
            assert "character_index" in result
            assert "coordinates" in result
            assert "context" in result
    
    def test_get_text_at_coordinates(self, text_extraction_service, sample_document):
        """Test getting text at specific coordinates."""
        # Mock coordinate service
        mock_text_position = Mock()
        mock_text_position.character_index = 10
        text_extraction_service.coordinate_service.pdf_to_text_position = Mock(
            return_value=mock_text_position
        )
        
        # Mock page extraction
        text_extraction_service.extract_page_text = Mock(return_value={
            "text": "This is sample text content for testing coordinates."
        })
        
        # Test coordinates
        coordinates = Coordinates(x=100, y=100, width=50, height=20, page=1)
        
        # Get text at coordinates
        text = text_extraction_service.get_text_at_coordinates(sample_document, coordinates)
        
        # Verify result
        assert text is not None
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_extraction_result_class(self):
        """Test ExtractionResult dataclass functionality."""
        result = ExtractionResult(
            text="Test content",
            extraction_method="test_method",
            extraction_confidence=0.95,
            character_count=12,
            word_count=2
        )
        
        assert result.text == "Test content"
        assert result.extraction_method == "test_method"
        assert result.extraction_confidence == 0.95
        assert result.character_count == 12
        assert result.word_count == 2
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    @patch('fitz.open')
    def test_content_analysis(self, mock_fitz_open, text_extraction_service, sample_document):
        """Test content analysis for tables, images, and diagrams."""
        # Mock document with content
        mock_doc = Mock()
        mock_page = Mock()
        
        # Setup page with table-like content
        mock_page.get_text.return_value = "Column1\tColumn2\nValue1\tValue2\n"
        mock_page.get_images.return_value = [
            (1, 0, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")
        ]
        mock_page.get_image_bbox = Mock(return_value=Mock(x0=10, y0=10, x1=110, y1=110))
        mock_page.get_drawings.return_value = [Mock() for _ in range(15)]  # Many drawings = diagram
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc
        
        # Extract with content analysis
        result = text_extraction_service.extract_text(
            sample_document, 
            include_content_analysis=True
        )
        
        # Verify content analysis
        assert len(result.tables) > 0  # Should detect table from tab characters
        assert len(result.images) > 0  # Should detect image
        assert len(result.diagrams) > 0  # Should detect diagram from many drawings
    
    def test_error_handling(self, text_extraction_service, sample_document):
        """Test error handling in text extraction."""
        # Mock extraction to raise an exception
        with patch('fitz.open', side_effect=Exception("File not found")):
            result = text_extraction_service.extract_text(sample_document)
            
            # Should return error result
            assert result.extraction_method == "failed"
            assert len(result.errors) > 0
            assert "File not found" in result.errors[0]
    
    def test_invalid_page_number(self, text_extraction_service, sample_document):
        """Test handling of invalid page numbers."""
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=1)  # Only 1 page
            mock_fitz.return_value = mock_doc
            
            # Try to extract page 2 (doesn't exist)
            page_data = text_extraction_service.extract_page_text(sample_document, 2)
            
            # Should return error
            assert "error" in page_data
            assert "Invalid page number" in page_data["error"]
    
    def test_cache_management(self, text_extraction_service):
        """Test cache management functionality."""
        # Add some test data to cache
        test_result = ExtractionResult(text="Test")
        text_extraction_service.extraction_cache["test_key"] = test_result
        
        # Clear cache
        text_extraction_service.clear_cache()
        
        # Verify cache is empty
        assert len(text_extraction_service.extraction_cache) == 0
    
    def test_performance_statistics(self, text_extraction_service):
        """Test performance statistics tracking."""
        # Initial stats
        initial_stats = text_extraction_service.get_performance_stats()
        assert initial_stats["extractions_performed"] == 0
        assert initial_stats["cache_hits"] == 0
        assert initial_stats["cache_misses"] == 0
        
        # Simulate some operations
        text_extraction_service.stats["extractions_performed"] = 5
        text_extraction_service.stats["cache_hits"] = 2
        text_extraction_service.stats["cache_misses"] = 3
        text_extraction_service.stats["total_characters_extracted"] = 1000
        
        # Check updated stats
        updated_stats = text_extraction_service.get_performance_stats()
        assert updated_stats["extractions_performed"] == 5
        assert updated_stats["cache_hits"] == 2
        assert updated_stats["cache_misses"] == 3
        assert updated_stats["cache_hit_rate"] == 0.4  # 2/(2+3)


@pytest.mark.performance
class TestTextExtractionPerformance:
    """Performance tests for text extraction service."""
    
    def test_large_document_extraction_performance(self, text_extraction_service, performance_timer):
        """Test extraction performance with large documents."""
        # Create a mock document with many pages
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=100)  # 100 pages
            
            # Mock pages with substantial content
            mock_page = Mock()
            mock_page.get_text.return_value = "Page content " * 1000  # Large page
            mock_page.get_text.side_effect = [
                "Page content " * 1000,
                {"blocks": []}  # Empty blocks for coordinates
            ]
            mock_page.rect.width = 612
            mock_page.rect.height = 792
            mock_page.get_images.return_value = []
            mock_page.get_drawings.return_value = []
            
            mock_doc.__getitem__ = Mock(return_value=mock_page)
            mock_fitz.return_value = mock_doc
            
            document = UnifiedDocument(
                id="large_doc",
                file_path="/test/large.pdf"
            )
            
            # Time the extraction
            performance_timer.start()
            result = text_extraction_service.extract_text(
                document, 
                page_range=(1, 10),  # Extract first 10 pages
                include_coordinates=False  # Skip coordinates for speed
            )
            performance_timer.stop()
            
            # Verify performance
            assert performance_timer.elapsed < 2.0  # Should complete in under 2 seconds
            assert result.character_count > 0
            assert len(result.pages) == 10
    
    def test_coordinate_extraction_performance(self, text_extraction_service, performance_timer):
        """Test performance of coordinate extraction."""
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=1)
            
            # Create mock page with many characters
            chars = [
                {"bbox": [i*10, 10, (i+1)*10, 20], "c": chr(65 + (i % 26))}
                for i in range(1000)  # 1000 characters
            ]
            
            mock_page = Mock()
            mock_page.get_text.side_effect = [
                "A" * 1000,  # Text content
                {  # Character coordinates
                    "blocks": [
                        {
                            "lines": [
                                {
                                    "spans": [
                                        {"chars": chars}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
            mock_page.rect.width = 612
            mock_page.rect.height = 792
            
            mock_doc.__getitem__ = Mock(return_value=mock_page)
            mock_fitz.return_value = mock_doc
            
            document = UnifiedDocument(
                id="coord_test",
                file_path="/test/coord.pdf"
            )
            
            # Time coordinate extraction
            performance_timer.start()
            result = text_extraction_service.extract_text(
                document,
                include_coordinates=True
            )
            performance_timer.stop()
            
            # Verify performance and accuracy
            assert performance_timer.elapsed < 1.0  # Should be fast
            assert len(result.character_coordinates) > 0
    
    def test_cache_performance_benefits(self, text_extraction_service, performance_timer):
        """Test that caching provides performance benefits."""
        with patch('fitz.open') as mock_fitz:
            # Setup mock that simulates slow file access
            mock_doc = Mock()
            mock_page = Mock()
            mock_page.get_text.return_value = "Cached content"
            mock_page.get_text.side_effect = [
                "Cached content",
                {"blocks": []}
            ]
            mock_page.rect.width = 612
            mock_page.rect.height = 792
            mock_page.get_images.return_value = []
            mock_page.get_drawings.return_value = []
            
            mock_doc.__len__ = Mock(return_value=1)
            mock_doc.__getitem__ = Mock(return_value=mock_page)
            mock_fitz.return_value = mock_doc
            
            document = UnifiedDocument(
                id="cache_test",
                file_path="/test/cache.pdf"
            )
            
            # First extraction (cache miss)
            performance_timer.start()
            result1 = text_extraction_service.extract_text(document)
            performance_timer.stop()
            first_time = performance_timer.elapsed
            
            # Second extraction (cache hit)
            performance_timer.start()
            result2 = text_extraction_service.extract_text(document)
            performance_timer.stop()
            second_time = performance_timer.elapsed
            
            # Cache hit should be much faster
            assert second_time < first_time / 10  # At least 10x faster
            assert result1.text == result2.text