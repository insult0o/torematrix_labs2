"""Advanced parsing modules for images and formulas."""

# Import modules that don't require external dependencies first
from .math_detector import MathDetector, MathComponent, FormulaStructure
from .caption_extractor import CaptionExtractor
from .latex_converter import LaTeXConverter, LaTeXResult
from .image_classifier import ImageClassifier, ImageType
from .language_detector import LanguageDetector

# Import OCR engine optionally (requires pytesseract/PIL)
try:
    from .ocr_engine import OCREngine, OCRResult, OCRConfiguration
    OCR_AVAILABLE = True
except (ImportError, ValueError) as e:
    # ImportError for missing packages, ValueError for numpy compatibility issues
    OCREngine = None
    OCRResult = None
    OCRConfiguration = None
    OCR_AVAILABLE = False

__all__ = [
    'MathDetector', 'MathComponent', 'FormulaStructure', 
    'CaptionExtractor',
    'LaTeXConverter', 'LaTeXResult',
    'ImageClassifier', 'ImageType',
    'LanguageDetector',
    'OCR_AVAILABLE'
]

if OCR_AVAILABLE:
    __all__.extend(['OCREngine', 'OCRResult', 'OCRConfiguration'])