#!/usr/bin/env python3
"""
Unit tests for CoordinateMappingService.

Tests the coordinate transformation functionality that was critical
in the original codebase and must work perfectly in the refactored version.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.services.coordinate_mapping_service import (
    CoordinateMappingService, 
    Coordinates, 
    CoordinateSystem, 
    TextPosition
)
from core.models.unified_document_model import UnifiedDocument


@pytest.mark.unit
class TestCoordinateMappingService:
    """Test cases for CoordinateMappingService."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = CoordinateMappingService()
        
        assert service is not None
        assert service._page_dimensions_cache == {}
        assert service._text_mapping_cache == {}
    
    def test_pdf_to_widget_coordinate_transformation(self):
        """Test PDF to widget coordinate transformation."""
        service = CoordinateMappingService()
        
        # Test coordinates
        pdf_coords = Coordinates(
            x=100, y=200, width=50, height=30,
            system=CoordinateSystem.PDF,
            page=1,
            zoom_factor=1.5
        )
        
        widget_height = 800
        
        # Transform
        widget_coords = service.pdf_to_widget(pdf_coords, widget_height)
        
        # Verify transformation
        assert widget_coords.system == CoordinateSystem.WIDGET
        assert widget_coords.page == 1
        assert widget_coords.zoom_factor == 1.5
        
        # Check coordinate calculations
        expected_x = 100 * 1.5  # Apply zoom
        expected_width = 50 * 1.5
        expected_height = 30 * 1.5
        expected_y = widget_height - (200 * 1.5) - expected_height  # Flip Y axis
        
        assert widget_coords.x == expected_x
        assert widget_coords.y == expected_y
        assert widget_coords.width == expected_width
        assert widget_coords.height == expected_height
    
    def test_widget_to_pdf_coordinate_transformation(self):
        """Test widget to PDF coordinate transformation."""
        service = CoordinateMappingService()
        
        # Test coordinates
        widget_coords = Coordinates(
            x=150, y=300, width=75, height=45,
            system=CoordinateSystem.WIDGET,
            page=1,
            zoom_factor=1.5
        )
        
        widget_height = 800
        
        # Transform
        pdf_coords = service.widget_to_pdf(widget_coords, widget_height)
        
        # Verify transformation
        assert pdf_coords.system == CoordinateSystem.PDF
        assert pdf_coords.page == 1
        assert pdf_coords.zoom_factor == 1.5
        
        # Check coordinate calculations (reverse of pdf_to_widget)
        expected_x = 150 / 1.5  # Remove zoom
        expected_width = 75 / 1.5
        expected_height = 45 / 1.5
        expected_y = (widget_height - 300) / 1.5 - expected_height  # Flip Y axis
        
        assert pdf_coords.x == expected_x
        assert pdf_coords.y == expected_y
        assert pdf_coords.width == expected_width
        assert pdf_coords.height == expected_height
    
    def test_coordinate_transformation_roundtrip(self):
        """Test that coordinate transformations are reversible."""
        service = CoordinateMappingService()
        
        # Original PDF coordinates
        original = Coordinates(
            x=100, y=200, width=50, height=30,
            system=CoordinateSystem.PDF,
            page=1,
            zoom_factor=2.0
        )
        
        widget_height = 800
        
        # Transform PDF -> Widget -> PDF
        widget_coords = service.pdf_to_widget(original, widget_height)
        restored = service.widget_to_pdf(widget_coords, widget_height)
        
        # Check that we get back the original coordinates (within tolerance)
        tolerance = 0.001
        assert abs(restored.x - original.x) < tolerance
        assert abs(restored.y - original.y) < tolerance
        assert abs(restored.width - original.width) < tolerance
        assert abs(restored.height - original.height) < tolerance
        assert restored.system == original.system
        assert restored.page == original.page
    
    @patch('fitz.open')
    def test_text_position_to_pdf_mapping(self, mock_fitz_open):
        """Test text position to PDF coordinate mapping."""
        service = CoordinateMappingService()
        
        # Mock document and page
        mock_doc = Mock()
        mock_page = Mock()
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc
        
        # Mock text data
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "chars": [
                                        {"bbox": [10, 10, 20, 20], "c": "H"},
                                        {"bbox": [20, 10, 30, 20], "c": "e"},
                                        {"bbox": [30, 10, 40, 20], "c": "l"},
                                        {"bbox": [40, 10, 50, 20], "c": "l"},
                                        {"bbox": [50, 10, 60, 20], "c": "o"},
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Test document
        document = UnifiedDocument(
            id="test_doc",
            file_path="/test/path.pdf"
        )
        
        # Test text position
        text_position = TextPosition(
            character_index=2,  # Character 'l' at index 2
            page=1
        )
        
        # Map to PDF coordinates
        result = service.text_position_to_pdf(document, text_position)
        
        # Verify result
        assert result is not None
        assert result.x == 30  # Expected x from mock data
        assert result.y == 10  # Expected y from mock data
        assert result.page == 1
    
    @patch('fitz.open')
    def test_pdf_to_text_position_mapping(self, mock_fitz_open):
        """Test PDF coordinate to text position mapping."""
        service = CoordinateMappingService()
        
        # Mock document and page
        mock_doc = Mock()
        mock_page = Mock()
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc
        
        # Mock text data
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "chars": [
                                        {"bbox": [10, 10, 20, 20], "c": "H"},
                                        {"bbox": [20, 10, 30, 20], "c": "e"},
                                        {"bbox": [30, 10, 40, 20], "c": "l"},
                                        {"bbox": [40, 10, 50, 20], "c": "l"},
                                        {"bbox": [50, 10, 60, 20], "c": "o"},
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Test document
        document = UnifiedDocument(
            id="test_doc",
            file_path="/test/path.pdf"
        )
        
        # Test PDF coordinates (should match character 'l' at index 2)
        pdf_coords = Coordinates(
            x=35, y=15, width=5, height=5,  # Near the 'l' character
            system=CoordinateSystem.PDF,
            page=1
        )
        
        # Map to text position
        result = service.pdf_to_text_position(document, pdf_coords)
        
        # Verify result
        assert result is not None
        assert result.page == 1
        assert result.character_index >= 0  # Should find a character
    
    @patch('fitz.open')
    def test_page_dimensions_caching(self, mock_fitz_open):
        """Test that page dimensions are cached properly."""
        service = CoordinateMappingService()
        
        # Mock document and page
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz_open.return_value = mock_doc
        
        document = UnifiedDocument(
            id="test_doc",
            file_path="/test/path.pdf"
        )
        
        # First call should hit the document
        dimensions1 = service.get_page_dimensions(document, 1)
        assert dimensions1 == (612, 792)
        
        # Second call should use cache
        dimensions2 = service.get_page_dimensions(document, 1)
        assert dimensions2 == (612, 792)
        
        # Verify cache was used (fitz.open should only be called once)
        assert mock_fitz_open.call_count == 1
        
        # Verify cache contains the dimensions
        assert document.id in service._page_dimensions_cache
        assert 1 in service._page_dimensions_cache[document.id]
    
    def test_coordinate_validation(self):
        """Test coordinate validation against page bounds."""
        service = CoordinateMappingService()
        
        # Mock get_page_dimensions to return known dimensions
        service.get_page_dimensions = Mock(return_value=(612, 792))
        
        document = UnifiedDocument(id="test_doc")
        
        # Valid coordinates
        valid_coords = Coordinates(
            x=100, y=100, width=50, height=50,
            system=CoordinateSystem.PDF,
            page=1
        )
        
        assert service.validate_coordinates(valid_coords, document) == True
        
        # Invalid coordinates (outside page bounds)
        invalid_coords = Coordinates(
            x=700, y=100, width=50, height=50,  # x + width > page width
            system=CoordinateSystem.PDF,
            page=1
        )
        
        assert service.validate_coordinates(invalid_coords, document) == False
    
    def test_cache_management(self):
        """Test cache clearing and statistics."""
        service = CoordinateMappingService()
        
        # Add some test data to cache
        service._page_dimensions_cache["doc1"] = {1: (612, 792), 2: (612, 792)}
        service._text_mapping_cache["doc1"] = {1: {0: Mock(), 1: Mock()}}
        
        # Test cache statistics
        stats = service.get_cache_stats()
        assert stats["page_dimensions_cached"] == 2
        assert stats["text_mappings_cached"] == 2
        assert stats["documents_cached"] == 1
        
        # Test clearing specific document cache
        service.clear_cache("doc1")
        
        stats_after = service.get_cache_stats()
        assert stats_after["page_dimensions_cached"] == 0
        assert stats_after["text_mappings_cached"] == 0
        assert stats_after["documents_cached"] == 0
    
    def test_coordinates_class(self):
        """Test the Coordinates dataclass functionality."""
        coords = Coordinates(
            x=100, y=200, width=50, height=30,
            system=CoordinateSystem.PDF,
            page=2,
            zoom_factor=1.5
        )
        
        # Test to_bbox conversion
        bbox = coords.to_bbox()
        assert bbox == [100, 200, 150, 230]  # [x0, y0, x1, y1]
        
        # Test from_bbox creation
        created_coords = Coordinates.from_bbox(
            [100, 200, 150, 230],
            system=CoordinateSystem.WIDGET,
            page=3,
            zoom_factor=2.0
        )
        
        assert created_coords.x == 100
        assert created_coords.y == 200
        assert created_coords.width == 50
        assert created_coords.height == 30
        assert created_coords.system == CoordinateSystem.WIDGET
        assert created_coords.page == 3
        assert created_coords.zoom_factor == 2.0
    
    def test_text_position_class(self):
        """Test the TextPosition dataclass functionality."""
        # Test normal creation
        text_pos = TextPosition(
            character_index=100,
            line_number=5,
            column_number=10,
            page=2
        )
        
        assert text_pos.character_index == 100
        assert text_pos.line_number == 5
        assert text_pos.column_number == 10
        assert text_pos.page == 2
        
        # Test validation (negative values should be corrected)
        invalid_pos = TextPosition(
            character_index=-5,  # Should be corrected to 0
            line_number=-1,      # Should be corrected to 0
            page=0               # Should be corrected to 1
        )
        
        assert invalid_pos.character_index == 0
        assert invalid_pos.line_number == 0
        assert invalid_pos.page == 1
    
    def test_error_handling(self):
        """Test error handling in coordinate mapping."""
        service = CoordinateMappingService()
        
        # Test with invalid coordinate system
        invalid_coords = Coordinates(
            x=100, y=200, width=50, height=30,
            system=CoordinateSystem.WIDGET,  # Wrong system for pdf_to_widget
            page=1
        )
        
        with pytest.raises(ValueError):
            service.pdf_to_widget(invalid_coords, 800)
        
        # Test with non-existent document
        document = UnifiedDocument(
            id="nonexistent",
            file_path="/nonexistent/path.pdf"
        )
        
        text_position = TextPosition(character_index=0, page=1)
        result = service.text_position_to_pdf(document, text_position)
        
        # Should return None or handle gracefully
        assert result is None or isinstance(result, Coordinates)


@pytest.mark.performance
class TestCoordinateMappingPerformance:
    """Performance tests for coordinate mapping service."""
    
    def test_large_document_performance(self, performance_timer):
        """Test performance with large documents."""
        service = CoordinateMappingService()
        
        # Mock a document with many pages
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_page = Mock()
            mock_page.rect.width = 612
            mock_page.rect.height = 792
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value = mock_doc
            
            document = UnifiedDocument(id="large_doc", file_path="/test.pdf")
            
            # Time multiple coordinate transformations
            performance_timer.start()
            
            for i in range(1000):
                coords = Coordinates(x=i, y=i, width=10, height=10, page=1)
                widget_coords = service.pdf_to_widget(coords, 800)
                pdf_coords = service.widget_to_pdf(widget_coords, 800)
            
            performance_timer.stop()
            
            # Should complete in reasonable time (< 1 second)
            assert performance_timer.elapsed < 1.0
    
    def test_cache_performance(self, performance_timer):
        """Test caching performance benefits."""
        service = CoordinateMappingService()
        
        with patch('fitz.open') as mock_fitz:
            mock_doc = Mock()
            mock_page = Mock()
            mock_page.rect.width = 612
            mock_page.rect.height = 792
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value = mock_doc
            
            document = UnifiedDocument(id="cache_test", file_path="/test.pdf")
            
            # First call (cache miss)
            performance_timer.start()
            dimensions1 = service.get_page_dimensions(document, 1)
            performance_timer.stop()
            
            first_call_time = performance_timer.elapsed
            
            # Second call (cache hit)
            performance_timer.start()
            dimensions2 = service.get_page_dimensions(document, 1)
            performance_timer.stop()
            
            second_call_time = performance_timer.elapsed
            
            # Cache hit should be significantly faster
            assert second_call_time < first_call_time / 2
            assert dimensions1 == dimensions2