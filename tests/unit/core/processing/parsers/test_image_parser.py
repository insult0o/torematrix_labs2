"""Tests for the enhanced image parser."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from torematrix.core.processing.parsers.image import ImageParser, EnhancedImageMetadata
from torematrix.core.processing.parsers.base import ParserResult
from torematrix.core.processing.parsers.types import ParserConfig, ElementType
from torematrix.core.processing.parsers.advanced.ocr_engine import OCRResult
from torematrix.core.processing.parsers.advanced.image_classifier import ClassificationResult, ImageType
from torematrix.core.processing.parsers.advanced.caption_extractor import CaptionData


@pytest.fixture
def parser_config():
    """Create a test parser configuration."""
    return ParserConfig(
        parser_specific={
            'enable_ocr': True,
            'enable_classification': True,
            'enable_caption_extraction': True,
            'enable_language_detection': True,
            'min_ocr_confidence': 0.6,
            'ocr_image_types': ['document', 'screenshot', 'chart', 'diagram']
        }
    )


@pytest.fixture
def image_parser(parser_config):
    """Create an image parser instance."""
    return ImageParser(parser_config)


@pytest.fixture
def mock_element():
    """Create a mock UnifiedElement."""
    element = Mock()
    element.type = "Image"
    element.text = "test_image.jpg 800x600"
    element.metadata = {
        'width': 800,
        'height': 600,
        'format': 'jpg',
        'size_bytes': 102400
    }
    return element


class TestImageParser:
    """Test cases for ImageParser."""
    
    def test_capabilities(self, image_parser):
        """Test parser capabilities."""
        capabilities = image_parser.capabilities
        
        assert ElementType.IMAGE in capabilities.supported_types
        assert ElementType.FIGURE in capabilities.supported_types
        assert capabilities.supports_async is True
        assert capabilities.supports_validation is True
        assert "ocr_text" in capabilities.supports_export_formats
        assert "classification" in capabilities.supports_export_formats
        assert len(capabilities.supported_languages) > 5
        
    def test_can_parse_image_element(self, image_parser, mock_element):
        """Test parsing image element type."""
        assert image_parser.can_parse(mock_element) is True
        
    def test_can_parse_figure_element(self, image_parser):
        """Test parsing figure element type."""
        element = Mock()
        element.type = "Figure"
        element.text = "figure1.png"
        
        assert image_parser.can_parse(element) is True
        
    def test_can_parse_image_category(self, image_parser):
        """Test parsing image category."""
        element = Mock()
        element.type = "Text"
        element.category = "image"
        element.text = "chart.png"
        
        assert image_parser.can_parse(element) is True
        
    def test_can_parse_image_indicators(self, image_parser):
        """Test parsing elements with image indicators."""
        element = Mock()
        element.type = "Text"
        element.text = "This diagram shows the process flow"
        
        assert image_parser.can_parse(element) is True
        
        # Test file extensions
        element.text = "screenshot.png shows the interface"
        assert image_parser.can_parse(element) is True
    
    def test_cannot_parse_non_image(self, image_parser):
        """Test rejecting non-image elements."""
        element = Mock()
        element.type = "Text"
        element.text = "This is just regular text without image content."
        
        assert image_parser.can_parse(element) is False
    
    @pytest.mark.asyncio
    async def test_parse_basic_image(self, image_parser, mock_element):
        """Test parsing a basic image element."""
        with patch.object(image_parser.caption_extractor, 'extract') as mock_caption, \
             patch.object(image_parser.image_classifier, 'classify') as mock_classify, \
             patch.object(image_parser, '_should_perform_ocr', return_value=False), \
             patch.object(image_parser, '_extract_image_data', return_value=None):
            
            # Setup mocks
            mock_caption.return_value = CaptionData(
                caption="Test image caption",
                confidence=0.8
            )
            
            mock_classify.return_value = ClassificationResult(
                image_type=ImageType.CHART,
                confidence=0.9,
                features={'width': 800, 'height': 600},
                reasoning=['Dimensions suggest chart'],
                metadata={}
            )
            
            result = await image_parser.parse(mock_element)
            
            assert result.success is True
            assert result.data["image_type"] == "chart"
            assert result.data["dimensions"]["width"] == 800
            assert result.data["dimensions"]["height"] == 600
            assert result.data["caption"] == "Test image caption"
            assert result.data["classification_confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_parse_image_with_ocr(self, image_parser, mock_element):
        """Test parsing an image with OCR enabled."""
        with patch.object(image_parser.caption_extractor, 'extract') as mock_caption, \
             patch.object(image_parser.image_classifier, 'classify') as mock_classify, \
             patch.object(image_parser, '_should_perform_ocr', return_value=True), \
             patch.object(image_parser, '_extract_image_data', return_value="test_image.jpg"), \
             patch.object(image_parser.ocr_engine, 'extract_text') as mock_ocr, \
             patch.object(image_parser.language_detector, 'detect_language') as mock_lang:
            
            # Setup mocks
            mock_caption.return_value = CaptionData(confidence=0.7)
            
            mock_classify.return_value = ClassificationResult(
                image_type=ImageType.DOCUMENT,
                confidence=0.85,
                features={},
                reasoning=['Document type detected'],
                metadata={}
            )
            
            mock_ocr.return_value = OCRResult(
                text="This is sample text from OCR",
                confidence=0.8,
                language="en",
                word_confidences=[0.9, 0.8, 0.7, 0.9, 0.8, 0.7],
                bounding_boxes=[(10, 10, 100, 30), (110, 10, 200, 30)],
                word_count=6,
                character_count=29
            )
            
            mock_lang.return_value = Mock(primary_language="en")
            
            result = await image_parser.parse(mock_element)
            
            assert result.success is True
            assert result.data["has_text"] is True
            assert result.data["ocr_text"] == "This is sample text from OCR"
            assert result.data["ocr_confidence"] == 0.8
            assert result.data["text_language"] == "en"
            assert result.data["image_type"] == "document"
    
    @pytest.mark.asyncio
    async def test_parse_with_processing_hints(self, image_parser, mock_element):
        """Test parsing with processing hints."""
        from torematrix.core.processing.parsers.types import ProcessingHints
        
        hints = ProcessingHints(
            image_hints={'perform_ocr': True}
        )
        
        with patch.object(image_parser.caption_extractor, 'extract') as mock_caption, \
             patch.object(image_parser.image_classifier, 'classify') as mock_classify, \
             patch.object(image_parser, '_extract_image_data', return_value="test_image.jpg"), \
             patch.object(image_parser.ocr_engine, 'extract_text') as mock_ocr:
            
            mock_caption.return_value = CaptionData(confidence=0.5)
            mock_classify.return_value = ClassificationResult(
                image_type=ImageType.PHOTO,
                confidence=0.8,
                features={},
                reasoning=[],
                metadata={}
            )
            
            mock_ocr.return_value = OCRResult(
                text="Photo caption text",
                confidence=0.7,
                language="en",
                word_confidences=[0.8, 0.7, 0.6],
                bounding_boxes=[]
            )
            
            result = await image_parser.parse(mock_element, hints)
            
            # Should perform OCR even for photo type due to hints
            assert result.data["has_text"] is True
            assert result.data["ocr_text"] == "Photo caption text"
    
    @pytest.mark.asyncio
    async def test_parse_failure_handling(self, image_parser):
        """Test parsing failure scenarios."""
        element = Mock()
        element.type = "Image"
        element.text = None
        element.metadata = {}
        
        # Force an exception during processing
        with patch.object(image_parser, '_extract_basic_properties', side_effect=Exception("Test error")):
            result = await image_parser.parse(element)
            
            assert result.success is False
            assert "Test error" in result.validation_errors[0]
    
    def test_validate_successful_result(self, image_parser):
        """Test validation of successful parsing result."""
        result = ParserResult(
            success=True,
            data={
                "image_metadata": {
                    "width": 800,
                    "height": 600,
                    "image_type": "chart"
                },
                "dimensions": {"width": 800, "height": 600},
                "has_text": True,
                "ocr_confidence": 0.8,
                "classification_confidence": 0.9
            },
            metadata=Mock(),
            validation_errors=[],
            extracted_content="",
            structured_data={}
        )
        
        errors = image_parser.validate(result)
        assert len(errors) == 0
    
    def test_validate_invalid_dimensions(self, image_parser):
        """Test validation with invalid dimensions."""
        result = ParserResult(
            success=True,
            data={
                "image_metadata": {"image_type": "chart"},
                "dimensions": {"width": -1, "height": 0},
                "classification_confidence": 0.9
            },
            metadata=Mock(),
            validation_errors=[],
            extracted_content="",
            structured_data={}
        )
        
        errors = image_parser.validate(result)
        assert "Invalid image dimensions" in errors
    
    def test_validate_low_ocr_confidence(self, image_parser):
        """Test validation with low OCR confidence."""
        result = ParserResult(
            success=True,
            data={
                "image_metadata": {"image_type": "document"},
                "dimensions": {"width": 800, "height": 600},
                "has_text": True,
                "ocr_confidence": 0.3,  # Below threshold
                "classification_confidence": 0.8
            },
            metadata=Mock(),
            validation_errors=[],
            extracted_content="",
            structured_data={}
        )
        
        errors = image_parser.validate(result)
        assert any("OCR confidence" in error and "below threshold" in error for error in errors)
    
    def test_should_perform_ocr_for_document_types(self, image_parser):
        """Test OCR decision for document-type images."""
        metadata = EnhancedImageMetadata()
        metadata.image_type = "document"
        
        assert image_parser._should_perform_ocr(metadata, None) is True
        
        metadata.image_type = "screenshot"
        assert image_parser._should_perform_ocr(metadata, None) is True
        
        metadata.image_type = "chart"
        assert image_parser._should_perform_ocr(metadata, None) is True
    
    def test_should_not_perform_ocr_for_photo_types(self, image_parser):
        """Test OCR decision for photo-type images."""
        metadata = EnhancedImageMetadata()
        metadata.image_type = "photo"
        
        assert image_parser._should_perform_ocr(metadata, None) is False
        
        metadata.image_type = "logo"
        assert image_parser._should_perform_ocr(metadata, None) is False
    
    def test_should_perform_ocr_when_disabled(self, image_parser):
        """Test OCR decision when OCR is disabled."""
        image_parser.enable_ocr = False
        metadata = EnhancedImageMetadata()
        metadata.image_type = "document"
        
        assert image_parser._should_perform_ocr(metadata, None) is False
    
    @pytest.mark.asyncio
    async def test_extract_basic_properties_from_metadata(self, image_parser):
        """Test extracting basic properties from element metadata."""
        element = Mock()
        element.metadata = {
            'width': 1024,
            'height': 768,
            'format': 'png',
            'size_bytes': 204800,
            'dpi': 150
        }
        element.text = None
        
        metadata = EnhancedImageMetadata()
        await image_parser._extract_basic_properties(element, metadata)
        
        assert metadata.width == 1024
        assert metadata.height == 768
        assert metadata.format == 'png'
        assert metadata.size_bytes == 204800
        assert metadata.dpi == 150
        assert metadata.aspect_ratio == pytest.approx(1024/768)
    
    @pytest.mark.asyncio
    async def test_extract_basic_properties_from_text(self, image_parser):
        """Test extracting basic properties from element text."""
        element = Mock()
        element.metadata = {}
        element.text = "image file: photo.jpg, dimensions: 1920x1080"
        
        metadata = EnhancedImageMetadata()
        await image_parser._extract_basic_properties(element, metadata)
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.format == 'jpg'
        assert metadata.aspect_ratio == pytest.approx(1920/1080)
    
    def test_calculate_overall_confidence(self, image_parser):
        """Test overall confidence calculation."""
        metadata = EnhancedImageMetadata()
        metadata.width = 800
        metadata.height = 600
        metadata.format = "png"
        metadata.size_bytes = 102400
        
        classification_result = ClassificationResult(
            image_type=ImageType.CHART,
            confidence=0.9,
            features={},
            reasoning=[],
            metadata={}
        )
        
        ocr_result = OCRResult(
            text="Sample text",
            confidence=0.8,
            language="en",
            word_confidences=[],
            bounding_boxes=[]
        )
        
        caption_data = CaptionData(
            caption="Test caption",
            confidence=0.7
        )
        
        confidence = image_parser._calculate_overall_confidence(
            metadata, classification_result, ocr_result, caption_data
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.6  # Should be reasonably high with good data
    
    def test_generate_warnings(self, image_parser):
        """Test warning generation."""
        metadata = EnhancedImageMetadata()
        metadata.width = 50
        metadata.height = 50  # Very small image
        
        ocr_result = OCRResult(
            text="a",  # Very little text
            confidence=0.3,  # Low confidence
            language="en",
            word_confidences=[],
            bounding_boxes=[]
        )
        
        classification_result = ClassificationResult(
            image_type=ImageType.UNKNOWN,
            confidence=0.2,  # Low confidence
            features={},
            reasoning=[],
            metadata={}
        )
        
        warnings = image_parser._generate_warnings(metadata, ocr_result, classification_result)
        
        assert len(warnings) > 0
        assert any("very low" in warning.lower() for warning in warnings)
        assert any("little text" in warning.lower() for warning in warnings)
        assert any("below threshold" in warning.lower() for warning in warnings)
    
    def test_create_extracted_content(self, image_parser):
        """Test extracted content creation."""
        metadata = EnhancedImageMetadata()
        metadata.image_type = "chart"
        metadata.ocr_text = "Sales data for Q3"
        metadata.caption = "Quarterly sales chart"
        metadata.alt_text = "Bar chart showing sales"
        
        content = image_parser._create_extracted_content(metadata)
        
        assert "[Image: chart]" in content
        assert "Text content: Sales data for Q3" in content
        assert "Caption: Quarterly sales chart" in content
        assert "Alt text: Bar chart showing sales" in content
    
    def test_create_export_formats(self, image_parser):
        """Test export format creation."""
        metadata = EnhancedImageMetadata()
        metadata.image_type = "document"
        metadata.ocr_text = "Document text"
        metadata.ocr_confidence = 0.9
        
        ocr_result = OCRResult(
            text="Document text",
            confidence=0.9,
            language="en",
            word_confidences=[],
            bounding_boxes=[]
        )
        
        classification_result = ClassificationResult(
            image_type=ImageType.DOCUMENT,
            confidence=0.85,
            features={},
            reasoning=[],
            metadata={}
        )
        
        exports = image_parser._create_export_formats(
            metadata, ocr_result, classification_result, None
        )
        
        assert "json" in exports
        assert "metadata" in exports
        assert "ocr_text" in exports
        assert "classification" in exports
        
        assert exports["ocr_text"]["text"] == "Document text"
        assert exports["classification"]["type"] == "document"
    
    def test_get_priority(self, image_parser):
        """Test parser priority calculation."""
        # High priority for explicit image elements
        element = Mock()
        element.type = "Image"
        element.metadata = {'width': 800, 'height': 600}
        
        with patch.object(image_parser, 'can_parse', return_value=True):
            priority = image_parser.get_priority(element)
            assert priority >= 100  # Base + image type + metadata boosts
        
        # Medium priority for figure elements
        element.type = "Figure"
        element.metadata = {}
        
        with patch.object(image_parser, 'can_parse', return_value=True):
            priority = image_parser.get_priority(element)
            assert 50 <= priority < 100
        
        # No priority for non-parseable elements
        with patch.object(image_parser, 'can_parse', return_value=False):
            priority = image_parser.get_priority(element)
            assert priority == 0
    
    def test_has_image_indicators(self, image_parser):
        """Test image indicator detection."""
        # Test with image keywords
        element = Mock()
        element.text = "This diagram shows the process"
        assert image_parser._has_image_indicators(element) is True
        
        element.text = "See the chart below"
        assert image_parser._has_image_indicators(element) is True
        
        # Test with file extensions
        element.text = "screenshot.png demonstrates the feature"
        assert image_parser._has_image_indicators(element) is True
        
        # Test without indicators
        element.text = "This is just regular text"
        assert image_parser._has_image_indicators(element) is False


@pytest.mark.integration
class TestImageParserIntegration:
    """Integration tests for ImageParser with real dependencies."""
    
    @pytest.mark.asyncio
    async def test_real_image_parsing_without_ocr(self):
        """Test parsing with real classifier and caption extractor."""
        parser = ImageParser()
        parser.enable_ocr = False  # Disable OCR for this test
        
        element = Mock()
        element.type = "Image"
        element.text = "chart_sales.png 800x600"
        element.metadata = {
            'width': 800,
            'height': 600,
            'format': 'png',
            'caption': 'Sales performance chart'
        }
        
        result = await parser.parse(element)
        
        # Should succeed with real components
        assert result.success is True
        assert result.data["dimensions"]["width"] == 800
        assert result.data["dimensions"]["height"] == 600
        assert result.data["format"] == "png"
        assert result.metadata.confidence > 0.0