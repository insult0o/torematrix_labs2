"""Image parser with basic classification and metadata extraction."""

import asyncio
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from torematrix_parser.src.torematrix.core.models.element import Element as UnifiedElement
from .base import BaseParser, ParserResult, ParserMetadata
from .types import ElementType, ParserCapabilities, ProcessingHints


@dataclass
class ImageMetadata:
    """Image metadata structure."""
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    has_text: bool = False
    classification: str = "unknown"
    confidence: float = 0.0


class ImageParser(BaseParser):
    """Parser for image elements with basic analysis."""
    
    @property
    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[ElementType.IMAGE, ElementType.FIGURE],
            supports_batch=True,
            supports_async=True,
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["json", "metadata"]
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element is an image."""
        return (
            hasattr(element, 'type') and element.type in ["Image", "Figure"] or
            hasattr(element, 'category') and element.category == "image" or
            self._has_image_indicators(element)
        )
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse image with basic analysis."""
        try:
            # Extract image metadata
            image_metadata = await self._extract_image_metadata(element)
            
            # Classify image type
            classification = await self._classify_image(element, image_metadata)
            image_metadata.classification = classification
            
            # Extract any text content
            text_content = await self._extract_text_content(element)
            
            # Calculate confidence
            confidence = self._calculate_image_confidence(image_metadata, element)
            
            return ParserResult(
                success=True,
                data={
                    "image_metadata": image_metadata.__dict__,
                    "classification": classification,
                    "text_content": text_content,
                    "has_text": bool(text_content),
                    "dimensions": {
                        "width": image_metadata.width,
                        "height": image_metadata.height
                    },
                    "format": image_metadata.format,
                    "size": image_metadata.size_bytes
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    element_metadata={
                        "image_type": classification,
                        "has_content": bool(text_content or image_metadata.has_text)
                    }
                ),
                extracted_content=text_content or f"[Image: {classification}]",
                structured_data={
                    "type": "image",
                    "classification": classification,
                    "metadata": image_metadata.__dict__
                }
            )
            
        except Exception as e:
            return self._create_failure_result(
                f"Image parsing failed: {str(e)}",
                validation_errors=[f"Image analysis error: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate image parsing result."""
        errors = []
        
        if not result.success:
            return ["Image parsing failed"]
        
        image_metadata = result.data.get("image_metadata")
        if not image_metadata:
            errors.append("No image metadata extracted")
        
        classification = result.data.get("classification")
        if not classification or classification == "unknown":
            errors.append("Image classification failed")
        
        return errors
    
    async def _extract_image_metadata(self, element: UnifiedElement) -> ImageMetadata:
        """Extract basic image metadata."""
        metadata = ImageMetadata()
        
        # Check element metadata for image info
        if hasattr(element, 'metadata') and element.metadata:
            elem_metadata = element.metadata
            metadata.width = elem_metadata.get('width')
            metadata.height = elem_metadata.get('height')
            metadata.format = elem_metadata.get('format')
            metadata.size_bytes = elem_metadata.get('file_size')
        
        # Try to extract from text content if it contains image info
        if hasattr(element, 'text') and element.text:
            await self._parse_text_for_image_info(element.text, metadata)
        
        return metadata
    
    async def _parse_text_for_image_info(self, text: str, metadata: ImageMetadata) -> None:
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
                metadata.width = int(match.group(1))
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
                metadata.format = match.group(1).lower()
                break
    
    async def _classify_image(self, element: UnifiedElement, metadata: ImageMetadata) -> str:
        """Classify image type based on available information."""
        # Basic classification based on metadata and text
        
        if hasattr(element, 'text') and element.text:
            text = element.text.lower()
            
            # Look for classification hints in text
            if any(word in text for word in ['chart', 'graph', 'plot']):
                return "chart"
            elif any(word in text for word in ['diagram', 'flowchart', 'schematic']):
                return "diagram"
            elif any(word in text for word in ['photo', 'picture', 'image']):
                return "photograph"
            elif any(word in text for word in ['logo', 'icon', 'symbol']):
                return "logo"
            elif any(word in text for word in ['screenshot', 'screen', 'ui']):
                return "screenshot"
            elif any(word in text for word in ['map', 'location']):
                return "map"
        
        # Classify based on dimensions
        if metadata.width and metadata.height:
            aspect_ratio = metadata.width / metadata.height
            
            if 0.9 <= aspect_ratio <= 1.1:  # Nearly square
                return "icon"
            elif aspect_ratio > 2.0:  # Very wide
                return "banner"
            elif aspect_ratio < 0.5:  # Very tall
                return "portrait"
        
        # Default classification
        return "general"
    
    async def _extract_text_content(self, element: UnifiedElement) -> Optional[str]:
        """Extract any text content from image element."""
        text_content = []
        
        # Check if element has text
        if hasattr(element, 'text') and element.text:
            # Filter out metadata-like content
            text = element.text.strip()
            if not self._is_metadata_text(text):
                text_content.append(text)
        
        # Check for captions or alt text
        if hasattr(element, 'metadata') and element.metadata:
            caption = element.metadata.get('caption')
            alt_text = element.metadata.get('alt_text')
            
            if caption:
                text_content.append(f"Caption: {caption}")
            if alt_text:
                text_content.append(f"Alt text: {alt_text}")
        
        return '\n'.join(text_content) if text_content else None
    
    def _is_metadata_text(self, text: str) -> bool:
        """Check if text is just metadata (dimensions, format, etc.)."""
        import re
        
        # Patterns that indicate metadata rather than content
        metadata_patterns = [
            r'^\d+\s*[x×]\s*\d+$',  # Just dimensions
            r'^[a-zA-Z]+\.(jpg|png|gif)$',  # Just filename
            r'^\d+\s*(kb|mb|bytes?)$',  # Just file size
            r'^format:\s*\w+$'  # Just format info
        ]
        
        text_clean = text.strip().lower()
        return any(re.match(pattern, text_clean) for pattern in metadata_patterns)
    
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
    
    def _calculate_image_confidence(self, metadata: ImageMetadata, element: UnifiedElement) -> float:
        """Calculate confidence in image parsing."""
        confidence_factors = []
        
        # Metadata completeness (40%)
        metadata_score = 0.0
        if metadata.width and metadata.height:
            metadata_score += 0.3
        if metadata.format:
            metadata_score += 0.3
        if metadata.size_bytes:
            metadata_score += 0.2
        if metadata.classification != "unknown":
            metadata_score += 0.2
        
        confidence_factors.append(metadata_score)
        
        # Classification confidence (30%)
        if metadata.classification in ['chart', 'diagram', 'photograph']:
            confidence_factors.append(0.8)
        elif metadata.classification in ['logo', 'screenshot', 'icon']:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Content availability (30%)
        content_score = 0.5  # Base score
        if metadata.has_text:
            content_score += 0.3
        if hasattr(element, 'text') and element.text:
            content_score += 0.2
        
        confidence_factors.append(min(1.0, content_score))
        
        return sum(confidence_factors) / len(confidence_factors)