# AGENT 3 - IMAGE & FORMULA PARSERS

## 🎯 Your Mission
You are Agent 3, the Advanced Processing Specialist for the Document Element Parser system. Your role is to implement sophisticated parsers for images and mathematical formulas with OCR integration and LaTeX conversion.

## 📋 Your Assignment
Implement specialized parsers for images and mathematical formulas with OCR capabilities, caption extraction, formula recognition, and LaTeX conversion.

**Sub-Issue**: #99 - Image & Formula Parsers with OCR  
**Dependencies**: Agent 1 (Base Parser Framework)  
**Timeline**: Days 2-3 (parallel with Agent 2)

## 🏗️ Files You Will Create

```
src/torematrix/core/processing/parsers/
├── image.py                   # Image parser with OCR
├── formula.py                 # Mathematical formula parser
└── advanced/
    ├── __init__.py
    ├── ocr_engine.py          # OCR integration wrapper
    ├── math_detector.py       # Formula recognition algorithms
    ├── caption_extractor.py   # Image caption detection
    ├── latex_converter.py     # Math to LaTeX conversion
    ├── image_classifier.py    # Image type classification
    └── language_detector.py   # Multi-language text detection

tests/unit/core/processing/parsers/
├── test_image_parser.py       # Image parsing functionality
├── test_formula_parser.py     # Formula parsing functionality
└── advanced/
    ├── test_ocr_engine.py
    ├── test_math_detector.py
    ├── test_caption_extractor.py
    ├── test_latex_converter.py
    ├── test_image_classifier.py
    └── test_language_detector.py

tests/fixtures/parsers/
├── sample_images/
│   ├── charts/
│   │   ├── bar_chart.png
│   │   └── line_chart.jpg
│   ├── diagrams/
│   │   ├── flowchart.png
│   │   └── schematic.pdf
│   ├── documents/
│   │   ├── scanned_text.jpg
│   │   └── mixed_content.png
│   └── screenshots/
│       ├── ui_element.png
│       └── code_snippet.jpg
└── sample_formulas/
    ├── simple_equations.json
    ├── complex_expressions.json
    └── latex_examples.txt
```

## 💻 Technical Implementation

### 1. Image Parser (`image.py`)
```python
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import base64
from PIL import Image
from .base import BaseParser, ParserResult, ParserMetadata
from .advanced.ocr_engine import OCREngine
from .advanced.caption_extractor import CaptionExtractor
from .advanced.image_classifier import ImageClassifier

class ImageType(Enum):
    CHART = "chart"
    DIAGRAM = "diagram"
    PHOTO = "photo"
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    UNKNOWN = "unknown"

@dataclass
class ImageMetadata:
    width: int
    height: int
    format: str
    size_bytes: int
    has_text: bool
    text_language: Optional[str] = None
    dpi: Optional[int] = None

@dataclass
class OCRResult:
    text: str
    confidence: float
    language: str
    word_confidences: List[float]
    bounding_boxes: List[Tuple[int, int, int, int]]

class ImageParser(BaseParser):
    """Advanced image parser with OCR and classification."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ocr_engine = OCREngine(config.get('ocr', {}))
        self.caption_extractor = CaptionExtractor()
        self.classifier = ImageClassifier()
        self.min_ocr_confidence = config.get('min_ocr_confidence', 0.6)
        self.enable_ocr = config.get('enable_ocr', True)
    
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if element is an image."""
        return (element.type == "Image" or 
                element.category == "image" or
                self._has_image_data(element))
    
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse image with OCR and classification."""
        try:
            # Load and validate image
            image_data = self._load_image(element)
            image_metadata = self._extract_metadata(image_data)
            
            # Classify image type
            image_type = await self.classifier.classify(image_data)
            
            # Extract captions and alt text
            captions = self.caption_extractor.extract(element)
            
            # Perform OCR if enabled and likely to contain text
            ocr_result = None
            if self.enable_ocr and self._should_perform_ocr(image_type, image_metadata):
                ocr_result = await self.ocr_engine.extract_text(image_data)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(image_type, ocr_result, captions)
            
            return ParserResult(
                success=True,
                data={
                    "image_type": image_type.value,
                    "metadata": image_metadata,
                    "captions": captions,
                    "ocr_text": ocr_result.text if ocr_result else None,
                    "text_confidence": ocr_result.confidence if ocr_result else 0.0,
                    "language": ocr_result.language if ocr_result else None,
                    "has_readable_text": bool(ocr_result and ocr_result.confidence > self.min_ocr_confidence)
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_version=self.version,
                    warnings=self._generate_warnings(image_type, ocr_result)
                ),
                validation_errors=self.validate_image_data(image_data, ocr_result),
                extracted_content=ocr_result.text if ocr_result else None,
                structured_data=self._export_formats(image_data, ocr_result, captions)
            )
            
        except Exception as e:
            return ParserResult(
                success=False,
                data={},
                metadata=ParserMetadata(
                    confidence=0.0,
                    parser_version=self.version,
                    error_count=1,
                    warnings=[str(e)]
                ),
                validation_errors=[f"Image parsing failed: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate image parsing result."""
        errors = []
        
        if not result.success:
            return ["Image parsing failed"]
        
        # Validate image metadata
        metadata = result.data.get("metadata")
        if not metadata:
            errors.append("No image metadata found")
        elif metadata.width <= 0 or metadata.height <= 0:
            errors.append("Invalid image dimensions")
        
        # Validate OCR results if present
        if result.data.get("ocr_text"):
            confidence = result.data.get("text_confidence", 0.0)
            if confidence < self.min_ocr_confidence:
                errors.append(f"OCR confidence {confidence} below threshold {self.min_ocr_confidence}")
        
        return errors
    
    def _should_perform_ocr(self, image_type: ImageType, metadata: ImageMetadata) -> bool:
        """Determine if OCR should be performed."""
        # Skip OCR for photos unless they're very high resolution
        if image_type == ImageType.PHOTO and metadata.width < 1000:
            return False
        
        # Always OCR documents and screenshots
        if image_type in [ImageType.DOCUMENT, ImageType.SCREENSHOT]:
            return True
        
        # OCR charts and diagrams if they might have labels
        return image_type in [ImageType.CHART, ImageType.DIAGRAM]
```

### 2. Formula Parser (`formula.py`)
```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re
from .base import BaseParser, ParserResult, ParserMetadata
from .advanced.math_detector import MathDetector
from .advanced.latex_converter import LaTeXConverter

class FormulaType(Enum):
    INLINE = "inline"
    DISPLAY = "display"
    EQUATION = "equation"
    EXPRESSION = "expression"
    UNKNOWN = "unknown"

@dataclass
class MathComponent:
    type: str  # variable, operator, function, constant
    value: str
    position: int
    confidence: float

@dataclass
class FormulaStructure:
    components: List[MathComponent]
    variables: List[str]
    operators: List[str]
    functions: List[str]
    complexity_score: float

class FormulaParser(BaseParser):
    """Mathematical formula parser with LaTeX conversion."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.math_detector = MathDetector()
        self.latex_converter = LaTeXConverter()
        self.min_confidence = config.get('min_confidence', 0.7)
        self.validate_latex = config.get('validate_latex', True)
    
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if element contains mathematical formula."""
        return (element.type == "Formula" or
                element.category == "formula" or
                self._has_math_indicators(element))
    
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse mathematical formula with LaTeX conversion."""
        try:
            # Extract formula text
            formula_text = self._extract_formula_text(element)
            
            # Detect formula type and structure
            formula_type = self.math_detector.detect_type(formula_text)
            structure = await self.math_detector.analyze_structure(formula_text)
            
            # Convert to LaTeX
            latex_result = await self.latex_converter.convert(formula_text, formula_type)
            
            # Validate LaTeX if enabled
            latex_valid = True
            validation_errors = []
            if self.validate_latex:
                latex_valid, validation_errors = self.latex_converter.validate(latex_result.latex)
            
            # Generate human-readable description
            description = self._generate_description(structure)
            
            # Calculate confidence
            confidence = self._calculate_confidence(structure, latex_result, latex_valid)
            
            return ParserResult(
                success=True,
                data={
                    "formula_type": formula_type.value,
                    "original_text": formula_text,
                    "latex": latex_result.latex,
                    "description": description,
                    "structure": structure,
                    "complexity": structure.complexity_score,
                    "variables": structure.variables,
                    "operators": structure.operators,
                    "functions": structure.functions
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_version=self.version,
                    warnings=validation_errors if latex_valid else []
                ),
                validation_errors=validation_errors if not latex_valid else [],
                extracted_content=formula_text,
                structured_data=self._export_formats(formula_text, latex_result.latex, structure)
            )
            
        except Exception as e:
            return ParserResult(
                success=False,
                data={},
                metadata=ParserMetadata(
                    confidence=0.0,
                    parser_version=self.version,
                    error_count=1,
                    warnings=[str(e)]
                ),
                validation_errors=[f"Formula parsing failed: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate formula parsing result."""
        errors = []
        
        if not result.success:
            return ["Formula parsing failed"]
        
        # Validate LaTeX syntax
        latex = result.data.get("latex")
        if latex:
            if not self._is_valid_latex(latex):
                errors.append("Generated LaTeX contains syntax errors")
        else:
            errors.append("No LaTeX output generated")
        
        # Validate structure
        structure = result.data.get("structure")
        if not structure or not structure.components:
            errors.append("No formula structure detected")
        
        return errors
    
    def _generate_description(self, structure: FormulaStructure) -> str:
        """Generate human-readable description of formula."""
        parts = []
        
        if structure.variables:
            parts.append(f"Variables: {', '.join(structure.variables)}")
        
        if structure.functions:
            parts.append(f"Functions: {', '.join(structure.functions)}")
        
        if structure.operators:
            parts.append(f"Operations: {', '.join(set(structure.operators))}")
        
        complexity = "simple" if structure.complexity_score < 0.3 else \
                    "moderate" if structure.complexity_score < 0.7 else "complex"
        parts.append(f"Complexity: {complexity}")
        
        return "; ".join(parts)
```

### 3. OCR Engine (`advanced/ocr_engine.py`)
```python
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pytesseract
from PIL import Image

@dataclass
class OCRConfiguration:
    engine: str = "tesseract"  # tesseract, easyocr, paddleocr
    languages: List[str] = None
    confidence_threshold: float = 0.6
    preprocess: bool = True
    dpi: int = 300

class OCREngine:
    """Multi-engine OCR wrapper with optimization."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = OCRConfiguration(**(config or {}))
        self._initialize_engines()
    
    async def extract_text(self, image_data: Any) -> OCRResult:
        """Extract text with confidence scoring."""
        
        # Preprocess image if enabled
        if self.config.preprocess:
            image_data = self._preprocess_image(image_data)
        
        # Try primary engine
        try:
            result = await self._extract_with_tesseract(image_data)
            if result.confidence >= self.config.confidence_threshold:
                return result
        except Exception:
            pass
        
        # Fallback to alternative engines
        for engine_name in ["easyocr", "paddleocr"]:
            try:
                result = await self._extract_with_engine(image_data, engine_name)
                if result.confidence >= self.config.confidence_threshold:
                    return result
            except Exception:
                continue
        
        # Return best available result
        return result if 'result' in locals() else OCRResult("", 0.0, "unknown", [], [])
    
    def _preprocess_image(self, image_data: Any) -> Any:
        """Optimize image for OCR."""
        # Convert to grayscale
        # Adjust contrast and brightness
        # Remove noise
        # Resize if necessary
        return image_data
```

## 🧪 Testing Requirements

### Test Coverage Goals
- **>95% code coverage** for all image and formula parsing functionality
- **Multi-engine testing** with fallback verification
- **Performance benchmarks** for OCR and LaTeX conversion

### Key Test Scenarios
1. **Image Processing Tests**
   - Various image formats (PNG, JPG, PDF)
   - Different image types (charts, documents, photos)
   - Multi-language OCR accuracy
   - Caption extraction from metadata

2. **Formula Recognition Tests**
   - Simple and complex mathematical expressions
   - LaTeX validation and conversion
   - Formula component extraction
   - Error handling for malformed math

## 🔗 Integration Points

### With Agent 1 (Base Framework)
```python
from .base import BaseParser, ParserResult

class ImageParser(BaseParser):
    # Your implementation using OCR
```

### With Agent 2 (Table/List)
- Share OCR capabilities for table text extraction
- Coordinate on mixed content with embedded images

### With Agent 4 (Integration)
- Provide OCR caching strategies
- Performance optimization for batch image processing

## 🚀 GitHub Workflow

1. **Wait for Agent 1** completion of base framework
2. **Create Branch**: `feature/image-formula-parsers`
3. **Implement OCR integration** with multiple engines
4. **Add LaTeX conversion** with validation
5. **Comprehensive testing** with image fixtures
6. **Performance optimization** for large images
7. **Create PR** with OCR accuracy reports

## ✅ Success Criteria

- [ ] OCR integration with 3+ engines (Tesseract, EasyOCR, PaddleOCR)
- [ ] Image classification for 5+ types
- [ ] Caption and alt-text extraction
- [ ] Mathematical formula recognition with LaTeX output
- [ ] Multi-language OCR support
- [ ] Confidence scoring for all extractions
- [ ] Performance: <2s for standard images
- [ ] Formula validation with syntax checking
- [ ] Fallback strategies for OCR failures
- [ ] >95% test coverage with diverse image samples

**Your advanced parsers will unlock text and math from any visual content!**