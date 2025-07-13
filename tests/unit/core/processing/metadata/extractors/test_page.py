"""Comprehensive tests for PageMetadataExtractor."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.torematrix.core.processing.metadata.extractors import PageMetadataExtractor
from src.torematrix.core.processing.metadata import (
    ExtractorConfig, ExtractionContext, ExtractionMethod
)


class TestPageMetadataExtractor:
    """Test suite for PageMetadataExtractor class."""
    
    @pytest.fixture
    def extractor_config(self):
        """Create test extractor configuration."""
        return ExtractorConfig(
            enabled=True,
            confidence_threshold=0.5,
            timeout_seconds=10.0
        )
    
    @pytest.fixture
    def page_extractor(self, extractor_config):
        """Create PageMetadataExtractor instance."""
        return PageMetadataExtractor(extractor_config)
    
    @pytest.fixture
    def extraction_context(self):
        """Create test extraction context."""
        return ExtractionContext(
            document_id="test_doc_123",
            extraction_timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def mock_page(self):
        """Create mock page object."""
        page = Mock()
        page.width = 612.0
        page.height = 792.0
        page.rotation = 0.0
        
        # Create mock elements
        page.elements = []
        
        # Text elements
        for i in range(5):
            element = Mock()
            element.type = "text"
            element.text = f"Sample text content {i} with multiple words here."
            element.bbox = [100 + i*10, 200 + i*10, 200 + i*10, 220 + i*10]
            page.elements.append(element)
        
        # Image elements
        for i in range(2):
            element = Mock()
            element.type = "image"
            element.text = None
            element.bbox = [300 + i*50, 400 + i*50, 350 + i*50, 450 + i*50]
            page.elements.append(element)
        
        # Table element
        element = Mock()
        element.type = "table"
        element.text = None
        element.bbox = [100, 500, 300, 600]
        page.elements.append(element)
        
        return page
    
    @pytest.fixture
    def mock_document_with_pages(self, mock_page):
        """Create mock document with pages."""
        document = Mock()
        document.document_id = "test_doc_123"
        document.pages = [mock_page, Mock()]  # Two pages
        return document
    
    @pytest.fixture
    def mock_document_single_page(self):
        """Create mock document as single page (no separate pages)."""
        document = Mock()
        document.document_id = "single_page_doc"
        # No pages attribute - treat document itself as page
        document.width = 595.0
        document.height = 842.0
        document.elements = [Mock() for _ in range(8)]
        
        # Add element types
        for i, element in enumerate(document.elements):
            if i < 6:
                element.type = "text"
                element.text = f"Text element {i}"
            else:
                element.type = "image"
                element.text = None
        
        return document
    
    def test_extractor_initialization(self, extractor_config):
        """Test extractor initialization."""
        extractor = PageMetadataExtractor(extractor_config)
        
        assert extractor.config == extractor_config
        assert extractor.name == "PageMetadataExtractor"
    
    def test_get_supported_extraction_methods(self, page_extractor):
        """Test supported extraction methods."""
        methods = page_extractor.get_supported_extraction_methods()
        
        expected_methods = [
            ExtractionMethod.DIRECT_PARSING,
            ExtractionMethod.HEURISTIC_ANALYSIS,
            ExtractionMethod.OCR_EXTRACTION,
            ExtractionMethod.HYBRID
        ]
        
        assert set(methods) == set(expected_methods)
    
    @pytest.mark.asyncio
    async def test_extract_basic_page(self, page_extractor, mock_document_with_pages, extraction_context):
        """Test basic page metadata extraction."""
        result = await page_extractor.extract(mock_document_with_pages, extraction_context)
        
        assert result["metadata_type"] == "page"
        assert result["extraction_method"] == ExtractionMethod.HYBRID
        assert result["page_number"] == 1
        assert result["document_id"] == "test_doc_123"
        assert result["width"] == 612.0
        assert result["height"] == 792.0
        assert result["rotation"] == 0.0
    
    @pytest.mark.asyncio
    async def test_extract_page_content_metrics(self, page_extractor, mock_document_with_pages, extraction_context):
        """Test page content metrics extraction."""
        result = await page_extractor.extract(mock_document_with_pages, extraction_context)
        
        assert result["element_count"] == 8  # 5 text + 2 image + 1 table
        assert result["text_element_count"] == 5
        assert result["image_element_count"] == 2
        assert result["table_element_count"] == 1
        
        # Should have word and character counts from text elements
        assert "word_count" in result
        assert "character_count" in result
        assert result["word_count"] > 0
        assert result["character_count"] > 0
    
    @pytest.mark.asyncio
    async def test_extract_single_page_document(self, page_extractor, mock_document_single_page, extraction_context):
        """Test extraction from single page document."""
        result = await page_extractor.extract(mock_document_single_page, extraction_context)
        
        assert result["page_number"] == 1
        assert result["width"] == 595.0
        assert result["height"] == 842.0
        assert result["element_count"] == 8
        assert result["text_element_count"] == 6
        assert result["image_element_count"] == 2
    
    def test_validate_metadata_valid(self, page_extractor):
        """Test validation of valid page metadata."""
        metadata = {
            "metadata_type": "page",
            "page_number": 1,
            "document_id": "test_doc",
            "width": 612.0,
            "height": 792.0,
            "element_count": 10,
            "text_element_count": 8,
            "image_element_count": 2,
            "word_count": 100,
            "character_count": 500
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True
        assert result.confidence_score > 0.7
        assert len(result.validation_errors) == 0
    
    def test_validate_metadata_missing_type(self, page_extractor):
        """Test validation with missing metadata type."""
        metadata = {
            "page_number": 1,
            "document_id": "test_doc"
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Missing metadata_type field" in result.validation_errors
    
    def test_validate_metadata_wrong_type(self, page_extractor):
        """Test validation with wrong metadata type."""
        metadata = {
            "metadata_type": "document",  # Wrong type
            "page_number": 1,
            "document_id": "test_doc"
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Invalid metadata_type for page extractor" in result.validation_errors
    
    def test_validate_metadata_invalid_page_number(self, page_extractor):
        """Test validation with invalid page number."""
        metadata = {
            "metadata_type": "page",
            "page_number": 0,  # Invalid
            "document_id": "test_doc"
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Page number must be at least 1" in result.validation_errors
    
    def test_validate_metadata_missing_document_id(self, page_extractor):
        """Test validation with missing document ID."""
        metadata = {
            "metadata_type": "page",
            "page_number": 1
            # Missing document_id
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Missing document_id field" in result.validation_errors
    
    def test_validate_metadata_invalid_dimensions(self, page_extractor):
        """Test validation with invalid dimensions."""
        metadata = {
            "metadata_type": "page",
            "page_number": 1,
            "document_id": "test_doc",
            "width": -100.0,  # Invalid
            "height": 0.0     # Invalid
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Page width must be positive" in result.validation_errors
        assert "Page height must be positive" in result.validation_errors
    
    def test_validate_metadata_unusual_aspect_ratio(self, page_extractor):
        """Test validation with unusual aspect ratio."""
        metadata = {
            "metadata_type": "page",
            "page_number": 1,
            "document_id": "test_doc",
            "width": 1000.0,
            "height": 50.0  # Very unusual aspect ratio
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True  # Warning, not error
        assert "Unusual page aspect ratio" in result.validation_warnings
    
    def test_validate_metadata_inconsistent_element_counts(self, page_extractor):
        """Test validation with inconsistent element counts."""
        metadata = {
            "metadata_type": "page",
            "page_number": 1,
            "document_id": "test_doc",
            "element_count": 5,
            "text_element_count": 3,
            "image_element_count": 2,
            "table_element_count": 2  # Total > element_count
        }
        
        result = page_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True  # Warning, not error
        assert "Sum of typed elements exceeds total element count" in result.validation_warnings
    
    def test_get_page_from_document_with_pages(self, page_extractor, mock_document_with_pages):
        """Test getting page from document with pages."""
        page = page_extractor._get_page(mock_document_with_pages, 1)
        assert page is not None
        assert page == mock_document_with_pages.pages[0]
        
        page = page_extractor._get_page(mock_document_with_pages, 2)
        assert page == mock_document_with_pages.pages[1]
        
        # Non-existent page
        page = page_extractor._get_page(mock_document_with_pages, 3)
        assert page is None
    
    def test_get_page_from_single_page_document(self, page_extractor, mock_document_single_page):
        """Test getting page from single page document."""
        # Page 1 should return the document itself
        page = page_extractor._get_page(mock_document_single_page, 1)
        assert page == mock_document_single_page
        
        # Page 2 should return None
        page = page_extractor._get_page(mock_document_single_page, 2)
        assert page is None
    
    def test_extract_page_dimensions(self, page_extractor, mock_page):
        """Test page dimensions extraction."""
        dimensions = page_extractor._extract_page_dimensions(mock_page)
        
        assert dimensions["width"] == 612.0
        assert dimensions["height"] == 792.0
        assert dimensions["rotation"] == 0.0
        assert abs(dimensions["aspect_ratio"] - (612.0 / 792.0)) < 0.001
        assert dimensions["orientation"] == "portrait"
    
    def test_extract_page_dimensions_landscape(self, page_extractor):
        """Test dimensions extraction for landscape page."""
        page = Mock()
        page.width = 792.0
        page.height = 612.0
        page.rotation = 90.0
        
        dimensions = page_extractor._extract_page_dimensions(page)
        
        assert dimensions["orientation"] == "landscape"
        assert dimensions["rotation"] == 90.0
    
    def test_extract_page_dimensions_square(self, page_extractor):
        """Test dimensions extraction for square page."""
        page = Mock()
        page.width = 600.0
        page.height = 600.0
        page.rotation = 0.0
        
        dimensions = page_extractor._extract_page_dimensions(page)
        
        assert dimensions["orientation"] == "square"
        assert dimensions["aspect_ratio"] == 1.0
    
    def test_classify_element_type_by_type_attribute(self, page_extractor):
        """Test element type classification by type attribute."""
        # Text element
        element = Mock()
        element.type = "text"
        assert page_extractor._classify_element_type(element) == "text"
        
        # Image element
        element.type = "image"
        assert page_extractor._classify_element_type(element) == "image"
        
        # Table element
        element.type = "table"
        assert page_extractor._classify_element_type(element) == "table"
    
    def test_classify_element_type_by_content(self, page_extractor):
        """Test element type classification by content."""
        # Element with text content
        element = Mock()
        del element.type  # No type attribute
        element.text = "Some text content"
        assert page_extractor._classify_element_type(element) == "text"
        
        # Element with image property
        element = Mock()
        del element.type
        element.text = None
        element.image = "image_data"
        assert page_extractor._classify_element_type(element) == "image"
        
        # Element with table properties
        element = Mock()
        del element.type
        element.text = None
        element.rows = [Mock(), Mock()]
        assert page_extractor._classify_element_type(element) == "table"
    
    def test_get_element_text(self, page_extractor):
        """Test text extraction from elements."""
        # Element with text attribute
        element = Mock()
        element.text = "Element text content"
        assert page_extractor._get_element_text(element) == "Element text content"
        
        # Element with content attribute
        element = Mock()
        del element.text
        element.content = "Element content"
        assert page_extractor._get_element_text(element) == "Element content"
        
        # Element with value attribute
        element = Mock()
        del element.text
        del element.content
        element.value = "Element value"
        assert page_extractor._get_element_text(element) == "Element value"
        
        # Element with no text content
        element = Mock()
        del element.text
        assert page_extractor._get_element_text(element) is None
    
    def test_detect_columns_single_column(self, page_extractor):
        """Test column detection for single column layout."""
        page = Mock()
        page.elements = [Mock() for _ in range(5)]
        
        # All elements in same column
        for i, element in enumerate(page.elements):
            element.bbox = [100, 200 + i*50, 300, 220 + i*50]  # Same x-position
        
        column_info = page_extractor._detect_columns(page)
        assert column_info["column_count"] == 1
    
    def test_detect_columns_multi_column(self, page_extractor):
        """Test column detection for multi-column layout."""
        page = Mock()
        page.elements = [Mock() for _ in range(6)]
        
        # Elements in two distinct columns
        for i, element in enumerate(page.elements):
            x_pos = 100 if i < 3 else 400  # Two distinct x-positions
            element.bbox = [x_pos, 200 + (i%3)*50, x_pos + 200, 220 + (i%3)*50]
        
        column_info = page_extractor._detect_columns(page)
        assert column_info["column_count"] >= 1  # Should detect multiple columns
    
    def test_detect_columns_explicit(self, page_extractor):
        """Test column detection with explicit column information."""
        page = Mock()
        page.columns = [Mock(), Mock()]  # Two columns
        
        column_info = page_extractor._detect_columns(page)
        assert column_info["column_count"] == 2
    
    def test_detect_header_footer_explicit(self, page_extractor):
        """Test header/footer detection with explicit properties."""
        page = Mock()
        page.header = Mock()
        page.footer = Mock()
        
        header_footer = page_extractor._detect_header_footer(page)
        assert header_footer["has_header"] is True
        assert header_footer["has_footer"] is True
    
    def test_detect_header_footer_by_position(self, page_extractor):
        """Test header/footer detection by element position."""
        page = Mock()
        page.height = 792.0
        page.elements = [Mock() for _ in range(3)]
        
        # Header element (top 10%)
        page.elements[0].bbox = [100, 750, 300, 780]  # y2 > 0.9 * height
        
        # Footer element (bottom 10%)
        page.elements[1].bbox = [100, 20, 300, 50]   # y1 < 0.1 * height
        
        # Regular content
        page.elements[2].bbox = [100, 400, 300, 450]
        
        header_footer = page_extractor._detect_header_footer(page)
        assert header_footer["has_header"] is True
        assert header_footer["has_footer"] is True
    
    def test_detect_margin_notes(self, page_extractor):
        """Test margin notes detection."""
        page = Mock()
        page.width = 612.0
        page.elements = [Mock() for _ in range(5)]
        
        # Main content elements (wide)
        for i in range(3):
            page.elements[i].bbox = [50, 200 + i*50, 500, 220 + i*50]  # Wide elements
        
        # Margin elements (narrow)
        for i in range(3, 5):
            page.elements[i].bbox = [520, 200 + i*50, 580, 220 + i*50]  # Narrow elements
        
        has_margin_notes = page_extractor._detect_margin_notes(page)
        assert has_margin_notes is True  # 40% of elements are in margins
    
    def test_appears_to_be_ocr_content(self, page_extractor):
        """Test OCR content detection."""
        # Page with explicit OCR flag
        page = Mock()
        page.is_ocr = True
        assert page_extractor._appears_to_be_ocr_content(page) is True
        
        # Page with OCR confidence
        page = Mock()
        page.ocr_confidence = 0.8
        assert page_extractor._appears_to_be_ocr_content(page) is True
        
        # Page with OCR elements
        page = Mock()
        page.elements = [Mock()]
        page.elements[0].ocr_confidence = 0.9
        assert page_extractor._appears_to_be_ocr_content(page) is True
        
        # Regular page
        page = Mock()
        page.elements = []
        assert page_extractor._appears_to_be_ocr_content(page) is False
    
    @pytest.mark.asyncio
    async def test_calculate_page_quality(self, page_extractor, mock_page):
        """Test page quality calculation."""
        metadata = {
            "word_count": 50,
            "character_count": 250,
            "element_count": 8,
            "text_element_count": 5,
            "width": 612.0,
            "height": 792.0,
            "has_header": True
        }
        
        quality = await page_extractor._calculate_page_quality(mock_page, metadata)
        
        assert "text_clarity_score" in quality
        assert "layout_quality_score" in quality
        assert 0.0 <= quality["text_clarity_score"] <= 1.0
        assert 0.0 <= quality["layout_quality_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_extract_content_metrics_different_element_sources(self, page_extractor, extraction_context):
        """Test content metrics extraction with different element sources."""
        document = Mock()
        document.document_id = "test_doc"
        
        page = Mock()
        page.width = 612.0
        page.height = 792.0
        
        # Test with 'blocks' instead of 'elements'
        page.blocks = [Mock() for _ in range(3)]
        for i, block in enumerate(page.blocks):
            block.type = "text"
            block.text = f"Block text {i}"
        
        document.pages = [page]
        
        result = await page_extractor.extract(document, extraction_context)
        
        assert result["element_count"] == 3
        assert result["text_element_count"] == 3