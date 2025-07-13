"""Tests for the OCR engine."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

from torematrix.core.processing.parsers.advanced.ocr_engine import (
    OCREngine, OCRResult, OCRConfiguration
)


@pytest.fixture
def ocr_config():
    """Create test OCR configuration."""
    return {
        'engine': 'tesseract',
        'languages': ['en'],
        'confidence_threshold': 0.6,
        'preprocess': True,
        'dpi': 300
    }


@pytest.fixture
def ocr_engine(ocr_config):
    """Create OCR engine instance."""
    return OCREngine(ocr_config)


@pytest.fixture
def sample_image():
    """Create a sample PIL image."""
    # Create a simple white image with black text
    img = Image.new('RGB', (200, 100), color='white')
    return img


class TestOCRConfiguration:
    """Test OCR configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = OCRConfiguration()
        assert config.engine == "tesseract"
        assert config.languages == ['en']
        assert config.confidence_threshold == 0.6
        assert config.preprocess is True
        assert config.dpi == 300
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = OCRConfiguration(
            engine='easyocr',
            languages=['en', 'es'],
            confidence_threshold=0.8,
            preprocess=False,
            dpi=150
        )
        assert config.engine == 'easyocr'
        assert config.languages == ['en', 'es']
        assert config.confidence_threshold == 0.8
        assert config.preprocess is False
        assert config.dpi == 150


class TestOCREngine:
    """Test OCR engine functionality."""
    
    def test_initialization(self, ocr_config):
        """Test OCR engine initialization."""
        engine = OCREngine(ocr_config)
        assert engine.config.engine == 'tesseract'
        assert engine.config.languages == ['en']
        assert 'tesseract' in engine.available_engines or len(engine.available_engines) == 0
    
    def test_initialization_without_config(self):
        """Test initialization with default config."""
        engine = OCREngine()
        assert engine.config.engine == 'tesseract'
        assert engine.config.languages == ['en']
    
    @pytest.mark.asyncio
    async def test_load_image_from_pil(self, ocr_engine, sample_image):
        """Test loading PIL image."""
        loaded_image = await ocr_engine._load_image(sample_image)
        assert loaded_image is not None
        assert isinstance(loaded_image, Image.Image)
        assert loaded_image.size == (200, 100)
    
    @pytest.mark.asyncio
    async def test_load_image_from_bytes(self, ocr_engine, sample_image):
        """Test loading image from bytes."""
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        sample_image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        loaded_image = await ocr_engine._load_image(img_bytes)
        assert loaded_image is not None
        assert isinstance(loaded_image, Image.Image)
    
    @pytest.mark.asyncio
    async def test_load_image_from_base64(self, ocr_engine, sample_image):
        """Test loading image from base64 string."""
        import base64
        
        # Convert PIL image to base64
        img_bytes = io.BytesIO()
        sample_image.save(img_bytes, format='PNG')
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode()
        data_url = f"data:image/png;base64,{img_base64}"
        
        loaded_image = await ocr_engine._load_image(data_url)
        assert loaded_image is not None
        assert isinstance(loaded_image, Image.Image)
    
    @pytest.mark.asyncio
    async def test_load_image_invalid_data(self, ocr_engine):
        """Test loading invalid image data."""
        loaded_image = await ocr_engine._load_image("invalid_data")
        assert loaded_image is None
    
    @pytest.mark.asyncio
    async def test_preprocess_image(self, ocr_engine, sample_image):
        """Test image preprocessing."""
        processed_image = await ocr_engine._preprocess_image(sample_image)
        assert processed_image is not None
        assert isinstance(processed_image, Image.Image)
        
        # Should convert to grayscale
        assert processed_image.mode == 'L'
    
    @pytest.mark.asyncio
    async def test_preprocess_image_resize(self, ocr_engine):
        """Test image preprocessing with resizing."""
        # Create very small image
        small_image = Image.new('RGB', (50, 50), color='white')
        
        processed_image = await ocr_engine._preprocess_image(small_image)
        assert processed_image is not None
        
        # Should be resized
        assert processed_image.width >= 600 or processed_image.height >= 600
    
    @pytest.mark.skipif(True, reason="Requires tesseract installation")
    @pytest.mark.asyncio
    async def test_extract_with_tesseract(self, ocr_engine, sample_image):
        """Test OCR extraction with Tesseract (requires installation)."""
        if 'tesseract' not in ocr_engine.available_engines:
            pytest.skip("Tesseract not available")
        
        # Mock pytesseract functions
        with patch('torematrix.core.processing.parsers.advanced.ocr_engine.pytesseract') as mock_tess:
            mock_tess.image_to_string.return_value = "Sample text"
            mock_tess.image_to_data.return_value = {
                'conf': [85, 90, 80],
                'left': [10, 50, 90],
                'top': [10, 10, 10],
                'width': [30, 35, 40],
                'height': [20, 20, 20]
            }
            mock_tess.Output.DICT = 'dict'
            
            result = await ocr_engine._extract_with_tesseract(sample_image)
            
            assert isinstance(result, OCRResult)
            assert result.text == "Sample text"
            assert result.confidence > 0
            assert len(result.word_confidences) == 3
            assert len(result.bounding_boxes) == 3
    
    @pytest.mark.asyncio
    async def test_extract_text_no_engines(self, ocr_config):
        """Test text extraction when no OCR engines are available."""
        engine = OCREngine(ocr_config)
        engine.available_engines = []  # Simulate no engines available
        
        result = await engine.extract_text("test_image.jpg")
        
        assert isinstance(result, OCRResult)
        assert result.text == ""
        assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_extract_text_with_fallback(self, ocr_engine, sample_image):
        """Test text extraction with fallback engines."""
        # Mock primary engine failure and fallback success
        with patch.object(ocr_engine, '_extract_with_engine') as mock_extract:
            # First call (primary) fails, second call (fallback) succeeds
            mock_extract.side_effect = [
                Exception("Primary engine failed"),
                OCRResult("Fallback text", 0.7, "en", [0.7], [(0, 0, 10, 10)])
            ]
            
            result = await ocr_engine.extract_text(sample_image)
            
            assert result.text == "Fallback text"
            assert result.confidence == 0.7
    
    def test_get_available_engines(self, ocr_engine):
        """Test getting available engines."""
        engines = ocr_engine.get_available_engines()
        assert isinstance(engines, list)
        # Should return a copy, not the original list
        engines.append("fake_engine")
        assert "fake_engine" not in ocr_engine.available_engines
    
    def test_is_engine_available(self, ocr_engine):
        """Test checking engine availability."""
        if 'tesseract' in ocr_engine.available_engines:
            assert ocr_engine.is_engine_available('tesseract') is True
        
        assert ocr_engine.is_engine_available('nonexistent_engine') is False
    
    @pytest.mark.asyncio
    async def test_benchmark_engines(self, ocr_engine, sample_image):
        """Test engine benchmarking."""
        # Mock engine extraction
        with patch.object(ocr_engine, '_extract_with_engine') as mock_extract:
            mock_extract.return_value = OCRResult(
                "Test text", 0.8, "en", [0.8], [(0, 0, 10, 10)]
            )
            
            # Set available engines for testing
            ocr_engine.available_engines = ['tesseract']
            
            results = await ocr_engine.benchmark_engines(sample_image)
            
            assert isinstance(results, dict)
            if 'tesseract' in results:
                assert 'processing_time' in results['tesseract']
                assert 'confidence' in results['tesseract']
                assert 'success' in results['tesseract']


class TestOCRResult:
    """Test OCR result data structure."""
    
    def test_ocr_result_creation(self):
        """Test OCR result creation and automatic calculations."""
        result = OCRResult(
            text="Hello world test",
            confidence=0.85,
            language="en",
            word_confidences=[0.9, 0.8, 0.85],
            bounding_boxes=[(0, 0, 50, 20), (55, 0, 105, 20), (110, 0, 150, 20)]
        )
        
        assert result.text == "Hello world test"
        assert result.confidence == 0.85
        assert result.language == "en"
        assert result.character_count == 16  # Includes spaces
        assert result.word_count == 3
        assert result.line_count == 1
    
    def test_ocr_result_multiline(self):
        """Test OCR result with multiline text."""
        result = OCRResult(
            text="Line one\nLine two\nLine three",
            confidence=0.8,
            language="en",
            word_confidences=[],
            bounding_boxes=[]
        )
        
        assert result.line_count == 3
        assert result.word_count == 6
    
    def test_ocr_result_empty(self):
        """Test OCR result with empty text."""
        result = OCRResult(
            text="",
            confidence=0.0,
            language="unknown",
            word_confidences=[],
            bounding_boxes=[]
        )
        
        assert result.character_count == 0
        assert result.word_count == 0
        assert result.line_count == 0


@pytest.mark.integration
class TestOCREngineIntegration:
    """Integration tests for OCR engine."""
    
    @pytest.mark.asyncio
    async def test_real_ocr_extraction(self):
        """Test real OCR extraction if engines are available."""
        engine = OCREngine()
        
        # Create a simple test image with text
        img = Image.new('RGB', (200, 50), color='white')
        # In a real test, you'd draw text on the image
        
        # Only run if OCR engines are available
        if engine.available_engines:
            result = await engine.extract_text(img)
            
            # Basic checks - actual text depends on what's in the image
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert 0.0 <= result.confidence <= 1.0
        else:
            # If no engines available, should return empty result
            result = await engine.extract_text(img)
            assert result.text == ""
            assert result.confidence == 0.0