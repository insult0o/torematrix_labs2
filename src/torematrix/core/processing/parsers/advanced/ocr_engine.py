"""Multi-engine OCR wrapper with optimization and fallback support."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import io
import base64

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class OCRConfiguration:
    """Configuration for OCR engine."""
    engine: str = "tesseract"  # tesseract, easyocr, paddleocr
    languages: List[str] = None
    confidence_threshold: float = 0.6
    preprocess: bool = True
    dpi: int = 300
    psm: int = 6  # Tesseract Page Segmentation Mode
    oem: int = 3  # Tesseract OCR Engine Mode
    enhance_contrast: bool = True
    denoise: bool = True
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ['en']


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    text: str
    confidence: float
    language: str
    word_confidences: List[float]
    bounding_boxes: List[Tuple[int, int, int, int]]
    character_count: int = 0
    word_count: int = 0
    line_count: int = 0
    
    def __post_init__(self):
        self.character_count = len(self.text)
        self.word_count = len(self.text.split()) if self.text else 0
        self.line_count = len(self.text.splitlines()) if self.text else 0


class OCREngine:
    """Multi-engine OCR wrapper with optimization and fallback support."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = OCRConfiguration(**(config or {}))
        self.logger = logging.getLogger("torematrix.parsers.ocr")
        
        # Initialize available engines
        self.available_engines = []
        if TESSERACT_AVAILABLE:
            self.available_engines.append("tesseract")
        if EASYOCR_AVAILABLE:
            self.available_engines.append("easyocr")
        
        if not self.available_engines:
            self.logger.warning("No OCR engines available. OCR functionality will be limited.")
        
        # Initialize EasyOCR reader if available
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(self.config.languages, gpu=False)
            except Exception as e:
                self.logger.warning(f"Failed to initialize EasyOCR: {e}")
        
        self.logger.info(f"OCR Engine initialized with engines: {self.available_engines}")

    async def extract_text(self, image_data: Union[str, bytes, Path, Any]) -> OCRResult:
        """Extract text with confidence scoring and fallback engines.
        
        Args:
            image_data: Image data (path, bytes, PIL Image, or base64 string)
            
        Returns:
            OCRResult with extracted text and metadata
        """
        try:
            # Load and preprocess image
            pil_image = await self._load_image(image_data)
            if pil_image is None:
                return OCRResult("", 0.0, "unknown", [], [])
            
            if self.config.preprocess:
                pil_image = await self._preprocess_image(pil_image)
            
            # Try primary engine first
            primary_engine = self.config.engine if self.config.engine in self.available_engines else self.available_engines[0] if self.available_engines else None
            
            if primary_engine:
                try:
                    result = await self._extract_with_engine(pil_image, primary_engine)
                    if result.confidence >= self.config.confidence_threshold:
                        return result
                except Exception as e:
                    self.logger.warning(f"Primary OCR engine {primary_engine} failed: {e}")
            
            # Try fallback engines
            for engine_name in self.available_engines:
                if engine_name != primary_engine:
                    try:
                        result = await self._extract_with_engine(pil_image, engine_name)
                        if result.confidence >= self.config.confidence_threshold:
                            return result
                    except Exception as e:
                        self.logger.warning(f"Fallback OCR engine {engine_name} failed: {e}")
            
            # Return best available result even if below threshold
            if 'result' in locals():
                return result
            else:
                return OCRResult("", 0.0, "unknown", [], [])
                
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {e}")
            return OCRResult("", 0.0, "unknown", [], [])

    async def _load_image(self, image_data: Union[str, bytes, Path, Any]) -> Optional[Image.Image]:
        """Load image from various sources."""
        try:
            if isinstance(image_data, (str, Path)):
                # File path or base64 string
                path_str = str(image_data)
                if path_str.startswith('data:image'):
                    # Data URL
                    base64_data = path_str.split(',')[1]
                    image_bytes = base64.b64decode(base64_data)
                    return Image.open(io.BytesIO(image_bytes))
                elif path_str.startswith('/') or Path(path_str).exists():
                    # File path
                    return Image.open(path_str)
                else:
                    # Assume base64 string
                    image_bytes = base64.b64decode(path_str)
                    return Image.open(io.BytesIO(image_bytes))
            
            elif isinstance(image_data, bytes):
                # Raw bytes
                return Image.open(io.BytesIO(image_data))
            
            elif hasattr(image_data, 'read'):
                # File-like object
                return Image.open(image_data)
            
            elif hasattr(image_data, 'save'):
                # Already a PIL Image
                return image_data
            
            else:
                self.logger.error(f"Unsupported image data type: {type(image_data)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load image: {e}")
            return None

    async def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Optimize image for OCR."""
        try:
            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Enhance contrast if enabled
            if self.config.enhance_contrast:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)
            
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Denoise if enabled
            if self.config.denoise:
                image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Resize if too small (min 300 DPI equivalent)
            width, height = image.size
            if width < 600 or height < 600:
                scale_factor = max(600 / width, 600 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            self.logger.warning(f"Image preprocessing failed: {e}")
            return image

    async def _extract_with_engine(self, image: Image.Image, engine: str) -> OCRResult:
        """Extract text using specific OCR engine."""
        if engine == "tesseract":
            return await self._extract_with_tesseract(image)
        elif engine == "easyocr":
            return await self._extract_with_easyocr(image)
        else:
            raise ValueError(f"Unsupported OCR engine: {engine}")

    async def _extract_with_tesseract(self, image: Image.Image) -> OCRResult:
        """Extract text using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract is not available")
        
        try:
            # Configure Tesseract
            config = f'--oem {self.config.oem} --psm {self.config.psm} -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?()[]{}:;-+*/=<>@#$%^&_|\\`~"\' '
            
            # Get text and confidence data
            text = pytesseract.image_to_string(image, lang='+'.join(self.config.languages), config=config)
            
            # Get detailed data with bounding boxes and confidences
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, 
                                           lang='+'.join(self.config.languages), config=config)
            
            # Extract word-level confidences and bounding boxes
            word_confidences = []
            bounding_boxes = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 0:  # Valid confidence
                    word_confidences.append(int(conf) / 100.0)
                    bounding_boxes.append((
                        data['left'][i],
                        data['top'][i],
                        data['left'][i] + data['width'][i],
                        data['top'][i] + data['height'][i]
                    ))
            
            # Calculate overall confidence
            overall_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
            
            return OCRResult(
                text=text.strip(),
                confidence=overall_confidence,
                language=self.config.languages[0],
                word_confidences=word_confidences,
                bounding_boxes=bounding_boxes
            )
            
        except Exception as e:
            self.logger.error(f"Tesseract OCR failed: {e}")
            raise

    async def _extract_with_easyocr(self, image: Image.Image) -> OCRResult:
        """Extract text using EasyOCR."""
        if not EASYOCR_AVAILABLE or self.easyocr_reader is None:
            raise RuntimeError("EasyOCR is not available")
        
        try:
            # Convert PIL image to numpy array
            import numpy as np
            image_array = np.array(image)
            
            # Run EasyOCR
            results = self.easyocr_reader.readtext(image_array, paragraph=False)
            
            # Process results
            text_parts = []
            word_confidences = []
            bounding_boxes = []
            
            for (bbox, text, confidence) in results:
                if confidence >= 0.1:  # Filter very low confidence
                    text_parts.append(text)
                    word_confidences.append(confidence)
                    
                    # Convert bbox to standard format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    bounding_boxes.append((
                        int(min(x_coords)),
                        int(min(y_coords)),
                        int(max(x_coords)),
                        int(max(y_coords))
                    ))
            
            # Combine text
            full_text = ' '.join(text_parts)
            
            # Calculate overall confidence
            overall_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
            
            return OCRResult(
                text=full_text,
                confidence=overall_confidence,
                language=self.config.languages[0],
                word_confidences=word_confidences,
                bounding_boxes=bounding_boxes
            )
            
        except Exception as e:
            self.logger.error(f"EasyOCR failed: {e}")
            raise

    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines."""
        return self.available_engines.copy()

    def is_engine_available(self, engine: str) -> bool:
        """Check if specific OCR engine is available."""
        return engine in self.available_engines

    async def benchmark_engines(self, test_image: Image.Image) -> Dict[str, Dict[str, Any]]:
        """Benchmark all available OCR engines on a test image."""
        results = {}
        
        for engine in self.available_engines:
            try:
                import time
                start_time = time.time()
                
                result = await self._extract_with_engine(test_image, engine)
                
                processing_time = time.time() - start_time
                
                results[engine] = {
                    "text_length": len(result.text),
                    "confidence": result.confidence,
                    "word_count": result.word_count,
                    "processing_time": processing_time,
                    "success": True
                }
                
            except Exception as e:
                results[engine] = {
                    "error": str(e),
                    "success": False
                }
        
        return results