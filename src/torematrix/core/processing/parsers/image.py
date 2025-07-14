"""Enhanced image parser with advanced OCR, classification, and caption extraction."""

import asyncio
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from torematrix_parser.src.torematrix.core.models.element import Element as UnifiedElement
from .base import BaseParser, ParserResult, ParserMetadata
from .types import ElementType, ParserCapabilities, ProcessingHints, ParserConfig
from .advanced import OCR_AVAILABLE
if OCR_AVAILABLE:
    from .advanced.ocr_engine import OCREngine, OCRResult, OCRConfiguration
else:
    OCREngine = None
    OCRResult = None
    OCRConfiguration = None
from .advanced.image_classifier import ImageClassifier, ImageType, ClassificationResult
from .advanced.caption_extractor import CaptionExtractor, CaptionData
from .advanced.language_detector import LanguageDetector, LanguageResult


@dataclass
class EnhancedImageMetadata:
    """Enhanced image metadata with OCR and classification."""
    # Basic image properties
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    dpi: Optional[int] = None
    aspect_ratio: Optional[float] = None
    
    # Classification results
    image_type: str = "unknown"
    classification_confidence: float = 0.0
    classification_features: Dict[str, Any] = None
    
    # OCR results
    has_text: bool = False
    ocr_text: Optional[str] = None
    ocr_confidence: float = 0.0
    text_language: Optional[str] = None
    word_count: int = 0
    character_count: int = 0
    
    # Caption information
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Processing metadata
    ocr_engine_used: str = "none"
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.classification_features is None:
            self.classification_features = {}


class ImageParser(BaseParser):
    """Advanced image parser with OCR, classification, and caption extraction."""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        super().__init__(config)
        
        # Initialize advanced components
        ocr_config = self.config.parser_specific.get('ocr', {})
        if OCR_AVAILABLE and OCREngine:
            self.ocr_engine = OCREngine(ocr_config)
        else:
            self.ocr_engine = None
            self.logger.warning("OCR engine not available - OCR functionality disabled")
        self.image_classifier = ImageClassifier()
        self.caption_extractor = CaptionExtractor()
        self.language_detector = LanguageDetector()
        
        # Configuration options
        self.enable_ocr = self.config.parser_specific.get('enable_ocr', True) and self.ocr_engine is not None
        self.enable_classification = self.config.parser_specific.get('enable_classification', True)
        self.enable_caption_extraction = self.config.parser_specific.get('enable_caption_extraction', True)
        self.enable_language_detection = self.config.parser_specific.get('enable_language_detection', True)
        
        self.min_ocr_confidence = self.config.parser_specific.get('min_ocr_confidence', 0.6)
        self.ocr_image_types = self.config.parser_specific.get('ocr_image_types', [
            'document', 'screenshot', 'chart', 'diagram', 'table_image', 'formula_image'
        ])
        
        self.logger = logging.getLogger("torematrix.parsers.enhanced_image")
    
    @property
    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[ElementType.IMAGE, ElementType.FIGURE],
            supported_languages=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar"],
            max_element_size=50 * 1024 * 1024,  # 50MB max image size
            supports_batch=True,
            supports_async=True,
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["json", "metadata", "ocr_text", "classification"],
            confidence_range=(0.0, 1.0)
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element is an image."""
        # Check element type
        if hasattr(element, 'type') and element.type in ["Image", "Figure"]:
            return True
        
        if hasattr(element, 'category') and element.category == "image":
            return True
        
        # Check for image indicators
        return self._has_image_indicators(element)
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse image with advanced OCR, classification, and caption extraction."""
        import time
        start_time = time.time()
        
        try:
            # Initialize metadata
            metadata = EnhancedImageMetadata()
            
            # Extract basic image properties
            await self._extract_basic_properties(element, metadata)
            
            # Extract captions and descriptive text
            caption_data = None
            if self.enable_caption_extraction:
                caption_data = self.caption_extractor.extract(element)
                await self._apply_caption_data(caption_data, metadata)
            
            # Classify image type
            classification_result = None
            if self.enable_classification:
                classification_result = await self._classify_image(element, metadata)
                await self._apply_classification_result(classification_result, metadata)
            
            # Perform OCR if appropriate
            ocr_result = None
            if self.enable_ocr and self._should_perform_ocr(metadata, hints):
                ocr_result = await self._perform_ocr(element, metadata)
                await self._apply_ocr_result(ocr_result, metadata)
            
            # Detect language of text content
            language_result = None
            if self.enable_language_detection and metadata.ocr_text:
                language_result = self.language_detector.detect_language(metadata.ocr_text)
                metadata.text_language = language_result.primary_language
            
            # Calculate processing time
            metadata.processing_time = time.time() - start_time
            
            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(
                metadata, classification_result, ocr_result, caption_data
            )
            
            # Generate warnings
            warnings = self._generate_warnings(metadata, ocr_result, classification_result)
            
            # Create export formats
            export_formats = self._create_export_formats(
                metadata, ocr_result, classification_result, caption_data
            )
            
            # Prepare structured data
            structured_data = self._create_structured_data(
                metadata, ocr_result, classification_result, caption_data
            )
            
            return ParserResult(
                success=True,
                data={
                    "image_metadata": metadata.__dict__,
                    "image_type": metadata.image_type,
                    "classification_confidence": metadata.classification_confidence,
                    "has_text": metadata.has_text,
                    "ocr_text": metadata.ocr_text,
                    "ocr_confidence": metadata.ocr_confidence,
                    "text_language": metadata.text_language,
                    "caption": metadata.caption,
                    "alt_text": metadata.alt_text,
                    "title": metadata.title,
                    "description": metadata.description,
                    "dimensions": {
                        "width": metadata.width,
                        "height": metadata.height,
                        "aspect_ratio": metadata.aspect_ratio
                    },
                    "format": metadata.format,
                    "size_bytes": metadata.size_bytes,
                    "processing_time": metadata.processing_time,
                    "ocr_engine_used": metadata.ocr_engine_used
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    validation_score=0.9 if not warnings else 0.7,
                    structure_quality=metadata.classification_confidence,
                    content_completeness=1.0 if metadata.ocr_text or metadata.caption else 0.5,
                    warnings=warnings,
                    element_metadata={
                        "image_processing": True,
                        "ocr_enabled": self.enable_ocr,
                        "classification_enabled": self.enable_classification,
                        "has_readable_text": metadata.has_text and metadata.ocr_confidence >= self.min_ocr_confidence
                    }
                ),
                validation_errors=self._validate_results(metadata),
                extracted_content=self._create_extracted_content(metadata),
                structured_data=structured_data,
                export_formats=export_formats
            )
            
        except Exception as e:
            self.logger.error(f"Enhanced image parsing failed: {e}")
            return self._create_failure_result(
                f"Image parsing failed: {str(e)}",
                validation_errors=[f"Image analysis error: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate enhanced image parsing result."""
        errors = []
        
        if not result.success:
            return ["Image parsing failed"]
        
        image_metadata = result.data.get("image_metadata")
        if not image_metadata:
            errors.append("No image metadata extracted")
        
        # Validate dimensions
        dimensions = result.data.get("dimensions", {})
        width = dimensions.get("width")
        height = dimensions.get("height")
        
        if width is not None and height is not None:
            if width <= 0 or height <= 0:
                errors.append("Invalid image dimensions")
        
        # Validate OCR results if OCR was performed
        if result.data.get("has_text"):
            ocr_confidence = result.data.get("ocr_confidence", 0.0)
            if ocr_confidence < self.min_ocr_confidence:
                errors.append(f"OCR confidence {ocr_confidence:.2f} below threshold {self.min_ocr_confidence}")
        
        # Validate classification
        if self.enable_classification:
            classification_confidence = result.data.get("classification_confidence", 0.0)
            if classification_confidence < 0.3:
                errors.append("Low image classification confidence")
        
        return errors
    
    async def _extract_basic_properties(self, element: UnifiedElement, metadata: EnhancedImageMetadata) -> None:
        """Extract basic image properties from element."""
        # Check element metadata for image info
        if hasattr(element, 'metadata') and element.metadata:
            elem_metadata = element.metadata
            metadata.width = elem_metadata.get('width')
            metadata.height = elem_metadata.get('height')
            metadata.format = elem_metadata.get('format')
            metadata.size_bytes = elem_metadata.get('file_size') or elem_metadata.get('size_bytes')
            metadata.dpi = elem_metadata.get('dpi')
        
        # Calculate aspect ratio if dimensions are available
        if metadata.width and metadata.height:
            metadata.aspect_ratio = metadata.width / metadata.height
        
        # Try to extract from text content if it contains image info
        if hasattr(element, 'text') and element.text:
            await self._parse_text_for_image_info(element.text, metadata)
    
    async def _parse_text_for_image_info(self, text: str, metadata: EnhancedImageMetadata) -> None:
        """Parse text content for image information."""
        import re
        
        # Look for dimension patterns
        dimension_patterns = [
            r'(\d+)\s*[x×]\s*(\d+)',
            r'width:\s*(\d+).*height:\s*(\d+)',
            r'(\d+)w\s*(\d+)h'
        ]
        
        for pattern in dimension_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if not metadata.width:
                    metadata.width = int(match.group(1))
                if not metadata.height:
                    metadata.height = int(match.group(2))
                break
        
        # Look for format information
        format_patterns = [
            r'\.(jpg|jpeg|png|gif|bmp|svg|webp|tiff?)',
            r'format:\s*(jpg|jpeg|png|gif|bmp|svg|webp|tiff?)'
        ]
        
        for pattern in format_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if not metadata.format:
                    metadata.format = match.group(1).lower()
                break
        
        # Update aspect ratio if dimensions were found
        if metadata.width and metadata.height and not metadata.aspect_ratio:
            metadata.aspect_ratio = metadata.width / metadata.height
    
    async def _apply_caption_data(self, caption_data: CaptionData, metadata: EnhancedImageMetadata) -> None:
        """Apply caption extraction results to metadata."""
        if caption_data.caption:
            metadata.caption = caption_data.caption
        if caption_data.alt_text:
            metadata.alt_text = caption_data.alt_text
        if caption_data.title:
            metadata.title = caption_data.title
        if caption_data.description:
            metadata.description = caption_data.description
    
    async def _classify_image(self, element: UnifiedElement, metadata: EnhancedImageMetadata) -> Optional[ClassificationResult]:
        """Classify the image type."""
        try:
            # Prepare metadata for classification
            classification_metadata = {
                'width': metadata.width,
                'height': metadata.height,
                'format': metadata.format,
                'aspect_ratio': metadata.aspect_ratio,
                'caption': metadata.caption,
                'alt_text': metadata.alt_text,
                'title': metadata.title
            }
            
            # Add element text if available
            if hasattr(element, 'text') and element.text:
                classification_metadata['text'] = element.text
            
            # Perform classification
            return await self.image_classifier.classify(element, classification_metadata)
            
        except Exception as e:
            self.logger.warning(f"Image classification failed: {e}")
            return None
    
    async def _apply_classification_result(self, classification_result: ClassificationResult, 
                                         metadata: EnhancedImageMetadata) -> None:
        """Apply classification results to metadata."""
        if classification_result:
            metadata.image_type = classification_result.image_type.value
            metadata.classification_confidence = classification_result.confidence
            metadata.classification_features = classification_result.features
    
    def _should_perform_ocr(self, metadata: EnhancedImageMetadata, hints: Optional[ProcessingHints]) -> bool:
        """Determine if OCR should be performed on this image."""
        # Check if OCR is disabled
        if not self.enable_ocr:
            return False
        
        # Check if image type suggests text content
        if metadata.image_type in self.ocr_image_types:
            return True
        
        # Check processing hints
        if hints and hints.image_hints:
            ocr_hint = hints.image_hints.get('perform_ocr')
            if ocr_hint is not None:
                return bool(ocr_hint)
        
        # Default behavior based on image type
        text_likely_types = ['document', 'screenshot', 'chart', 'diagram', 'table_image', 'formula_image']
        
        # Always OCR if we don't know the type yet
        if metadata.image_type == 'unknown':
            return True
        
        return metadata.image_type in text_likely_types
    
    async def _perform_ocr(self, element: UnifiedElement, metadata: EnhancedImageMetadata) -> Optional[OCRResult]:
        """Perform OCR on the image element."""
        try:
            # Try to get image data from element
            image_data = await self._extract_image_data(element)
            if not image_data:
                self.logger.warning("No image data available for OCR")
                return None
            
            # Perform OCR
            ocr_result = await self.ocr_engine.extract_text(image_data)
            
            # Update metadata with OCR engine info
            metadata.ocr_engine_used = self.ocr_engine.config.engine
            
            return ocr_result
            
        except Exception as e:
            self.logger.warning(f"OCR processing failed: {e}")
            return None
    
    async def _extract_image_data(self, element: UnifiedElement) -> Optional[Any]:
        """Extract image data from element for OCR processing."""
        # Check for image data in various formats
        if hasattr(element, 'image_data'):
            return element.image_data
        
        if hasattr(element, 'data') and element.data:
            return element.data
        
        # Check metadata for image path or data
        if hasattr(element, 'metadata') and element.metadata:
            for field in ['image_path', 'file_path', 'url', 'src']:
                if field in element.metadata:
                    return element.metadata[field]
        
        # Check if text contains base64 image data
        if hasattr(element, 'text') and element.text:
            text = element.text
            if text.startswith('data:image'):
                return text
            elif text.startswith('/') or '\\' in text:
                # Might be a file path
                return text
        
        return None
    
    async def _apply_ocr_result(self, ocr_result: OCRResult, metadata: EnhancedImageMetadata) -> None:
        """Apply OCR results to metadata."""
        if ocr_result:
            metadata.has_text = bool(ocr_result.text and ocr_result.confidence >= self.min_ocr_confidence)
            metadata.ocr_text = ocr_result.text
            metadata.ocr_confidence = ocr_result.confidence
            metadata.word_count = ocr_result.word_count
            metadata.character_count = ocr_result.character_count
    
    def _calculate_overall_confidence(self, metadata: EnhancedImageMetadata,
                                    classification_result: Optional[ClassificationResult],
                                    ocr_result: Optional[OCRResult],
                                    caption_data: Optional[CaptionData]) -> float:
        """Calculate overall confidence in image parsing."""
        confidence_factors = []
        
        # Metadata completeness (25%)
        metadata_score = 0.0
        if metadata.width and metadata.height:
            metadata_score += 0.4
        if metadata.format:
            metadata_score += 0.3
        if metadata.size_bytes:
            metadata_score += 0.3
        
        confidence_factors.append(metadata_score * 0.25)
        
        # Classification confidence (25%)
        if classification_result:
            confidence_factors.append(classification_result.confidence * 0.25)
        else:
            confidence_factors.append(0.5 * 0.25)  # Moderate confidence without classification
        
        # OCR confidence (25%)
        if ocr_result and self.enable_ocr:
            confidence_factors.append(ocr_result.confidence * 0.25)
        elif not self.enable_ocr:
            confidence_factors.append(0.8 * 0.25)  # High confidence when OCR disabled by choice
        else:
            confidence_factors.append(0.3 * 0.25)  # Lower confidence when OCR failed
        
        # Caption extraction confidence (25%)
        if caption_data:
            confidence_factors.append(caption_data.confidence * 0.25)
        else:
            confidence_factors.append(0.4 * 0.25)  # Moderate confidence without captions
        
        return sum(confidence_factors)
    
    def _generate_warnings(self, metadata: EnhancedImageMetadata,
                          ocr_result: Optional[OCRResult],
                          classification_result: Optional[ClassificationResult]) -> List[str]:
        """Generate warnings based on parsing results."""
        warnings = []
        
        # Image quality warnings
        if metadata.width and metadata.height:
            total_pixels = metadata.width * metadata.height
            if total_pixels < 10000:  # Very small image
                warnings.append("Image resolution is very low, may affect OCR accuracy")
        
        # OCR warnings
        if self.enable_ocr and ocr_result:
            if ocr_result.confidence < self.min_ocr_confidence:
                warnings.append(f"OCR confidence {ocr_result.confidence:.2f} below threshold")
            if len(ocr_result.text) < 5:
                warnings.append("Very little text detected")
        elif self.enable_ocr and not ocr_result:
            warnings.append("OCR processing failed")
        
        # Classification warnings
        if self.enable_classification and classification_result:
            if classification_result.confidence < 0.5:
                warnings.append("Low image classification confidence")
        elif self.enable_classification and not classification_result:
            warnings.append("Image classification failed")
        
        return warnings
    
    def _validate_results(self, metadata: EnhancedImageMetadata) -> List[str]:
        """Validate parsing results."""
        errors = []
        
        # Basic validation
        if not metadata.image_type or metadata.image_type == "unknown":
            errors.append("Could not determine image type")
        
        if metadata.width is not None and metadata.height is not None:
            if metadata.width <= 0 or metadata.height <= 0:
                errors.append("Invalid image dimensions")
        
        return errors
    
    def _create_extracted_content(self, metadata: EnhancedImageMetadata) -> str:
        """Create extracted content summary."""
        content_parts = []
        
        # Add image type
        content_parts.append(f"[Image: {metadata.image_type}]")
        
        # Add OCR text if available
        if metadata.ocr_text:
            content_parts.append(f"Text content: {metadata.ocr_text}")
        
        # Add caption if available
        if metadata.caption:
            content_parts.append(f"Caption: {metadata.caption}")
        
        # Add alt text if available
        if metadata.alt_text:
            content_parts.append(f"Alt text: {metadata.alt_text}")
        
        return '\n'.join(content_parts)
    
    def _create_structured_data(self, metadata: EnhancedImageMetadata,
                               ocr_result: Optional[OCRResult],
                               classification_result: Optional[ClassificationResult],
                               caption_data: Optional[CaptionData]) -> Dict[str, Any]:
        """Create structured data representation."""
        return {
            "type": "image",
            "image_type": metadata.image_type,
            "metadata": metadata.__dict__,
            "ocr": ocr_result.__dict__ if ocr_result else None,
            "classification": classification_result.__dict__ if classification_result else None,
            "captions": caption_data.__dict__ if caption_data else None
        }
    
    def _create_export_formats(self, metadata: EnhancedImageMetadata,
                              ocr_result: Optional[OCRResult],
                              classification_result: Optional[ClassificationResult],
                              caption_data: Optional[CaptionData]) -> Dict[str, Any]:
        """Create various export formats."""
        exports = {}
        
        # JSON format
        exports["json"] = {
            "image_metadata": metadata.__dict__,
            "ocr_results": ocr_result.__dict__ if ocr_result else None,
            "classification": classification_result.__dict__ if classification_result else None,
            "captions": caption_data.__dict__ if caption_data else None
        }
        
        # Metadata only format
        exports["metadata"] = metadata.__dict__
        
        # OCR text format
        if metadata.ocr_text:
            exports["ocr_text"] = {
                "text": metadata.ocr_text,
                "confidence": metadata.ocr_confidence,
                "language": metadata.text_language,
                "word_count": metadata.word_count
            }
        
        # Classification format
        if classification_result:
            exports["classification"] = {
                "type": metadata.image_type,
                "confidence": metadata.classification_confidence,
                "features": metadata.classification_features
            }
        
        return exports
    
    def _has_image_indicators(self, element: UnifiedElement) -> bool:
        """Check if element has image-like indicators."""
        if hasattr(element, 'text') and element.text:
            text = element.text.lower()
            
            # Look for image-related keywords
            image_keywords = [
                'image', 'figure', 'photo', 'picture', 'chart', 'graph',
                'diagram', 'screenshot', 'illustration', 'logo'
            ]
            
            if any(keyword in text for keyword in image_keywords):
                return True
            
            # Look for image file extensions
            if any(ext in text for ext in ['.jpg', '.png', '.gif', '.svg', '.bmp']):
                return True
        
        return False
    
    def get_priority(self, element: UnifiedElement) -> int:
        """Get parser priority for image elements."""
        if not self.can_parse(element):
            return 0
        
        priority = 50  # Base priority
        
        # Boost for explicit image elements
        if hasattr(element, 'type') and element.type in ["Image", "Figure"]:
            priority += 30
        
        # Boost for elements with image metadata
        if hasattr(element, 'metadata') and element.metadata:
            if any(key in element.metadata for key in ['width', 'height', 'format', 'image_data']):
                priority += 20
        
        return priority