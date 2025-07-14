"""Comprehensive tests for DocumentMetadataExtractor."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.torematrix.core.processing.metadata.extractors import DocumentMetadataExtractor
from src.torematrix.core.processing.metadata import (
    ExtractorConfig, ExtractionContext, ExtractionMethod,
    LanguageCode, EncodingType
)


class TestDocumentMetadataExtractor:
    """Test suite for DocumentMetadataExtractor class."""
    
    @pytest.fixture
    def extractor_config(self):
        """Create test extractor configuration."""
        return ExtractorConfig(
            enabled=True,
            confidence_threshold=0.5,
            timeout_seconds=10.0
        )
    
    @pytest.fixture
    def document_extractor(self, extractor_config):
        """Create DocumentMetadataExtractor instance."""
        return DocumentMetadataExtractor(extractor_config)
    
    @pytest.fixture
    def extraction_context(self):
        """Create test extraction context."""
        return ExtractionContext(
            document_id="test_doc_123",
            extraction_timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def mock_document_basic(self):
        """Create basic mock document."""
        document = Mock()
        document.document_id = "test_doc_123"
        document.metadata = {
            "title": "Test Document Title",
            "author": "Test Author",
            "creation_date": "2023-01-01",
            "subject": "Test Subject"
        }
        document.pages = [Mock(), Mock()]  # 2 pages
        document.elements = [Mock() for _ in range(10)]  # 10 elements
        
        # Add text content to elements
        for i, element in enumerate(document.elements):
            element.text = f"Sample text content {i}" if i % 2 == 0 else None
        
        return document
    
    @pytest.fixture
    def mock_document_complete(self):
        """Create complete mock document with all properties."""
        document = Mock()
        document.document_id = "complete_doc"
        document.metadata = {
            "title": "Complete Test Document",
            "author": "Complete Author",
            "subject": "Complete Subject",
            "creator": "Test Creator",
            "producer": "Test Producer",
            "keywords": "test, document, metadata",
            "creation_date": datetime(2023, 1, 1, 12, 0, 0),
            "modification_date": datetime(2023, 6, 1, 15, 30, 0),
            "metadata_date": datetime(2023, 6, 1, 15, 35, 0)
        }
        document.pages = [Mock() for _ in range(5)]
        document.elements = [Mock() for _ in range(25)]
        document.file_size = 1024000
        document.file_format = "PDF"
        document.file_version = "1.4"
        document.is_encrypted = False
        document.has_signature = False
        document.permissions = {"can_print": True, "can_modify": False}
        
        # Add realistic text content
        text_content = [
            "This is a comprehensive test document with multiple paragraphs of text.",
            "It contains various types of content to test language detection.",
            "The document has proper structure and formatting.",
            None,  # Some elements without text
            "Additional content for completeness testing purposes."
        ]
        
        for i, element in enumerate(document.elements):
            element.text = text_content[i % len(text_content)]
        
        return document
    
    def test_extractor_initialization(self, extractor_config):
        """Test extractor initialization."""
        extractor = DocumentMetadataExtractor(extractor_config)
        
        assert extractor.config == extractor_config
        assert extractor.name == "DocumentMetadataExtractor"
    
    def test_get_supported_extraction_methods(self, document_extractor):
        """Test supported extraction methods."""
        methods = document_extractor.get_supported_extraction_methods()
        
        expected_methods = [
            ExtractionMethod.DIRECT_PARSING,
            ExtractionMethod.HEURISTIC_ANALYSIS,
            ExtractionMethod.HYBRID
        ]
        
        assert set(methods) == set(expected_methods)
    
    @pytest.mark.asyncio
    async def test_extract_basic_document(self, document_extractor, mock_document_basic, extraction_context):
        """Test basic document metadata extraction."""
        result = await document_extractor.extract(mock_document_basic, extraction_context)
        
        assert result["metadata_type"] == "document"
        assert result["extraction_method"] == ExtractionMethod.HYBRID
        assert result["title"] == "Test Document Title"
        assert result["author"] == "Test Author"
        assert result["subject"] == "Test Subject"
        assert result["page_count"] == 2
        assert result["total_elements"] == 10
    
    @pytest.mark.asyncio
    async def test_extract_complete_document(self, document_extractor, mock_document_complete, extraction_context):
        """Test complete document metadata extraction."""
        result = await document_extractor.extract(mock_document_complete, extraction_context)
        
        # Basic properties
        assert result["title"] == "Complete Test Document"
        assert result["author"] == "Complete Author"
        assert result["creator"] == "Test Creator"
        assert result["producer"] == "Test Producer"
        
        # Keywords
        assert "keywords" in result
        assert isinstance(result["keywords"], list)
        assert "test" in result["keywords"]
        
        # Dates
        assert result["creation_date"] == datetime(2023, 1, 1, 12, 0, 0)
        assert result["modification_date"] == datetime(2023, 6, 1, 15, 30, 0)
        
        # Structure
        assert result["page_count"] == 5
        assert result["total_elements"] == 25
        
        # File properties
        assert result["file_size_bytes"] == 1024000
        assert result["file_format"] == "PDF"
        assert result["file_version"] == "1.4"
        
        # Security
        assert result["is_encrypted"] is False
        assert result["has_digital_signature"] is False
        assert result["permissions"]["can_print"] is True
        assert result["permissions"]["can_modify"] is False
    
    @pytest.mark.asyncio
    async def test_extract_language_detection(self, document_extractor, extraction_context):
        """Test language detection functionality."""
        # Create document with English text
        document = Mock()
        document.metadata = {}
        document.pages = [Mock()]
        document.elements = [Mock() for _ in range(3)]
        document.elements[0].text = "This is a test document written in English language."
        document.elements[1].text = "It contains multiple sentences for proper language detection."
        document.elements[2].text = "The language detector should identify this as English."
        
        with patch('langdetect.detect_langs') as mock_detect:
            # Mock language detection result
            mock_lang = Mock()
            mock_lang.lang = 'en'
            mock_lang.prob = 0.95
            mock_detect.return_value = [mock_lang]
            
            result = await document_extractor.extract(document, extraction_context)
            
            assert result["language"] == LanguageCode.ENGLISH
            assert result["language_confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_extract_encoding_detection(self, document_extractor, extraction_context):
        """Test encoding detection functionality."""
        document = Mock()
        document.metadata = {}
        document.pages = [Mock()]
        document.elements = [Mock()]
        document.elements[0].text = "Test content for encoding detection"
        
        with patch('chardet.detect') as mock_detect:
            mock_detect.return_value = {
                'encoding': 'utf-8',
                'confidence': 0.99
            }
            
            result = await document_extractor.extract(document, extraction_context)
            
            assert result["encoding"] == EncodingType.UTF8
            assert result["encoding_confidence"] == 0.99
    
    @pytest.mark.asyncio
    async def test_extract_quality_metrics(self, document_extractor, mock_document_complete, extraction_context):
        """Test quality metrics calculation."""
        with patch('langdetect.detect_langs') as mock_detect:
            mock_lang = Mock()
            mock_lang.lang = 'en'
            mock_lang.prob = 0.90
            mock_detect.return_value = [mock_lang]
            
            result = await document_extractor.extract(mock_document_complete, extraction_context)
            
            assert "text_quality_score" in result
            assert "structure_quality_score" in result
            assert "overall_quality_score" in result
            
            # Should have reasonable quality scores
            assert 0.0 <= result["text_quality_score"] <= 1.0
            assert 0.0 <= result["structure_quality_score"] <= 1.0
            assert 0.0 <= result["overall_quality_score"] <= 1.0
    
    def test_validate_metadata_valid(self, document_extractor):
        """Test validation of valid metadata."""
        metadata = {
            "metadata_type": "document",
            "title": "Valid Document",
            "page_count": 5,
            "total_elements": 25,
            "language": LanguageCode.ENGLISH,
            "language_confidence": 0.9,
            "encoding": EncodingType.UTF8,
            "creation_date": datetime(2023, 1, 1),
            "modification_date": datetime(2023, 6, 1)
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True
        assert result.confidence_score > 0.7
        assert len(result.validation_errors) == 0
    
    def test_validate_metadata_missing_type(self, document_extractor):
        """Test validation with missing metadata type."""
        metadata = {
            "title": "Document without type",
            "page_count": 5
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Missing metadata_type field" in result.validation_errors
    
    def test_validate_metadata_wrong_type(self, document_extractor):
        """Test validation with wrong metadata type."""
        metadata = {
            "metadata_type": "page",  # Wrong type
            "title": "Wrong type document"
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Invalid metadata_type for document extractor" in result.validation_errors
    
    def test_validate_metadata_negative_page_count(self, document_extractor):
        """Test validation with negative page count."""
        metadata = {
            "metadata_type": "document",
            "page_count": -1
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is False
        assert "Page count cannot be negative" in result.validation_errors
    
    def test_validate_metadata_inconsistent_dates(self, document_extractor):
        """Test validation with inconsistent dates."""
        metadata = {
            "metadata_type": "document",
            "creation_date": datetime(2023, 6, 1),
            "modification_date": datetime(2023, 1, 1)  # Before creation
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True  # Not an error, just warning
        assert "Modification date is before creation date" in result.validation_warnings
    
    def test_validate_metadata_pages_no_elements(self, document_extractor):
        """Test validation with pages but no elements."""
        metadata = {
            "metadata_type": "document",
            "page_count": 5,
            "total_elements": 0
        }
        
        result = document_extractor.validate_metadata(metadata)
        
        assert result.is_valid is True  # Warning, not error
        assert "Document has pages but no elements" in result.validation_warnings
    
    def test_clean_text(self, document_extractor):
        """Test text cleaning functionality."""
        # Normal text
        assert document_extractor._clean_text("Normal text") == "Normal text"
        
        # Text with extra whitespace
        assert document_extractor._clean_text("  Text  with   spaces  ") == "Text with spaces"
        
        # Text with control characters
        assert document_extractor._clean_text("Text\x00with\x1fcontrol") == "Textwithcontrol"
        
        # Empty text
        assert document_extractor._clean_text("") is None
        assert document_extractor._clean_text(None) is None
        assert document_extractor._clean_text("   ") is None
    
    def test_extract_keywords(self, document_extractor):
        """Test keyword extraction."""
        # Comma-separated keywords
        keywords = document_extractor._extract_keywords("test, document, metadata")
        assert keywords == ["test", "document", "metadata"]
        
        # Semicolon-separated keywords
        keywords = document_extractor._extract_keywords("test; document; metadata")
        assert keywords == ["test", "document", "metadata"]
        
        # Mixed separators
        keywords = document_extractor._extract_keywords("test, document; metadata | processing")
        assert keywords == ["test", "document", "metadata", "processing"]
        
        # Empty keywords
        keywords = document_extractor._extract_keywords("")
        assert keywords == []
        
        # Keywords with extra spaces
        keywords = document_extractor._extract_keywords("  test  ,  document  ")
        assert keywords == ["test", "document"]
    
    def test_parse_date(self, document_extractor):
        """Test date parsing functionality."""
        # Datetime object (passthrough)
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert document_extractor._parse_date(dt) == dt
        
        # ISO format string
        assert document_extractor._parse_date("2023-01-01 12:00:00") == datetime(2023, 1, 1, 12, 0, 0)
        
        # Date only string
        assert document_extractor._parse_date("2023-01-01") == datetime(2023, 1, 1, 0, 0, 0)
        
        # US format
        assert document_extractor._parse_date("01/01/2023") == datetime(2023, 1, 1, 0, 0, 0)
        
        # Invalid date
        assert document_extractor._parse_date("invalid date") is None
        
        # None input
        assert document_extractor._parse_date(None) is None
    
    def test_detect_language_insufficient_text(self, document_extractor):
        """Test language detection with insufficient text."""
        language, confidence = document_extractor._detect_language("Hi")
        assert language == LanguageCode.UNKNOWN
        assert confidence == 0.0
    
    def test_detect_language_empty_text(self, document_extractor):
        """Test language detection with empty text."""
        language, confidence = document_extractor._detect_language("")
        assert language == LanguageCode.UNKNOWN
        assert confidence == 0.0
    
    @patch('langdetect.detect_langs')
    def test_detect_language_detection_failure(self, mock_detect, document_extractor):
        """Test language detection failure handling."""
        mock_detect.side_effect = Exception("Detection failed")
        
        language, confidence = document_extractor._detect_language("Some text content")
        assert language == LanguageCode.UNKNOWN
        assert confidence == 0.0
    
    def test_detect_encoding_empty_text(self, document_extractor):
        """Test encoding detection with empty text."""
        encoding, confidence = document_extractor._detect_encoding("")
        assert encoding == EncodingType.UTF8
        assert confidence == 0.5
    
    @patch('chardet.detect')
    def test_detect_encoding_detection_failure(self, mock_detect, document_extractor):
        """Test encoding detection failure handling."""
        mock_detect.side_effect = Exception("Detection failed")
        
        encoding, confidence = document_extractor._detect_encoding("Some text")
        assert encoding == EncodingType.UTF8
        assert confidence == 0.8  # Default fallback
    
    def test_extract_text_content_from_elements(self, document_extractor):
        """Test text content extraction from document elements."""
        document = Mock()
        document.elements = [Mock() for _ in range(3)]
        document.elements[0].text = "First element text"
        document.elements[1].text = "Second element text"
        document.elements[2].text = None  # No text
        
        text = document_extractor._extract_text_content(document)
        assert "First element text" in text
        assert "Second element text" in text
    
    def test_extract_text_content_from_document(self, document_extractor):
        """Test text content extraction from document text attribute."""
        document = Mock()
        document.text = "Direct document text content"
        # No elements attribute
        del document.elements
        
        text = document_extractor._extract_text_content(document)
        assert text == "Direct document text content"
    
    def test_extract_text_content_length_limit(self, document_extractor):
        """Test text content extraction length limit."""
        document = Mock()
        document.elements = [Mock()]
        # Create very long text (over 10000 chars)
        long_text = "a" * 15000
        document.elements[0].text = long_text
        
        text = document_extractor._extract_text_content(document)
        assert len(text) <= 10000  # Should be limited
    
    @pytest.mark.asyncio
    async def test_extract_structure_info_no_elements(self, document_extractor, extraction_context):
        """Test structure info extraction when document has no elements."""
        document = Mock()
        document.metadata = {}
        document.pages = [Mock()]
        # No elements attribute
        del document.elements
        
        result = await document_extractor.extract(document, extraction_context)
        
        assert result["page_count"] == 1
        assert result["total_elements"] == 0
    
    @pytest.mark.asyncio
    async def test_extract_file_properties_from_path(self, document_extractor, extraction_context):
        """Test file properties extraction from source path."""
        document = Mock()
        document.metadata = {}
        document.pages = [Mock()]
        document.elements = []
        document.source_path = "/path/to/document.pdf"
        
        result = await document_extractor.extract(document, extraction_context)
        
        assert result["file_format"] == "PDF"
    
    @pytest.mark.asyncio
    async def test_extract_with_minimal_document(self, document_extractor, extraction_context):
        """Test extraction with minimal document structure."""
        document = Mock()
        # Minimal document with no metadata
        document.metadata = {}
        
        result = await document_extractor.extract(document, extraction_context)
        
        # Should still return basic structure
        assert result["metadata_type"] == "document"
        assert "extraction_method" in result
        assert "page_count" in result