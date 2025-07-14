"""Page-level metadata extractor with layout and content analysis."""

from typing import Dict, List, Any, Optional, Tuple
import statistics
from datetime import datetime

from ..types import (
    ExtractionContext, MetadataValidationResult, ExtractionMethod,
    ExtractorResult
)
from .base import BaseExtractor


class PageMetadataExtractor(BaseExtractor):
    """Extract page-level metadata including layout and content properties."""
    
    def get_supported_extraction_methods(self) -> List[ExtractionMethod]:
        """Return supported extraction methods."""
        return [
            ExtractionMethod.DIRECT_PARSING,
            ExtractionMethod.HEURISTIC_ANALYSIS,
            ExtractionMethod.OCR_EXTRACTION,
            ExtractionMethod.HYBRID
        ]
    
    async def extract(
        self,
        document: Any,
        context: ExtractionContext
    ) -> ExtractorResult:
        """Extract page-level metadata for all pages in document.
        
        Args:
            document: Document to extract metadata from
            context: Extraction context
            
        Returns:
            Dictionary containing page metadata for all pages
        """
        # For now, return metadata for first page as example
        # In practice, this would return metadata for all pages
        page_metadata = await self._extract_single_page_metadata(
            document, page_number=1, context=context
        )
        
        # Add metadata type
        page_metadata["metadata_type"] = "page"
        page_metadata["extraction_method"] = ExtractionMethod.HYBRID
        
        return page_metadata
    
    async def _extract_single_page_metadata(
        self,
        document: Any,
        page_number: int,
        context: ExtractionContext
    ) -> Dict[str, Any]:
        """Extract metadata for a single page.
        
        Args:
            document: Document containing the page
            page_number: Page number to extract (1-indexed)
            context: Extraction context
            
        Returns:
            Dictionary containing page metadata
        """
        metadata = {
            "page_number": page_number,
            "document_id": context.document_id
        }
        
        # Get page object
        page = self._get_page(document, page_number)
        if not page:
            return metadata
        
        # Extract page dimensions
        metadata.update(self._extract_page_dimensions(page))
        
        # Extract content metrics
        metadata.update(await self._extract_content_metrics(page))
        
        # Extract layout properties
        metadata.update(await self._extract_layout_properties(page))
        
        # Calculate quality metrics
        metadata.update(await self._calculate_page_quality(page, metadata))
        
        return metadata
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> MetadataValidationResult:
        """Validate extracted page metadata.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Validation result with confidence and errors
        """
        errors = []
        warnings = []
        confidence_factors = []
        
        # Validate required fields
        if not metadata.get("metadata_type"):
            errors.append("Missing metadata_type field")
        elif metadata["metadata_type"] != "page":
            errors.append("Invalid metadata_type for page extractor")
        
        # Validate page number
        page_number = metadata.get("page_number", 0)
        if page_number < 1:
            errors.append("Page number must be at least 1")
        confidence_factors.append(0.9 if page_number >= 1 else 0.1)
        
        # Validate document ID
        if not metadata.get("document_id"):
            errors.append("Missing document_id field")
            confidence_factors.append(0.1)
        else:
            confidence_factors.append(0.9)
        
        # Validate dimensions
        width = metadata.get("width")
        height = metadata.get("height")
        if width is not None and width <= 0:
            errors.append("Page width must be positive")
        if height is not None and height <= 0:
            errors.append("Page height must be positive")
        
        if width and height:
            # Check for reasonable aspect ratios
            aspect_ratio = width / height
            if 0.1 <= aspect_ratio <= 10:  # Reasonable range
                confidence_factors.append(0.9)
            else:
                warnings.append("Unusual page aspect ratio")
                confidence_factors.append(0.7)
        else:
            warnings.append("Missing page dimensions")
            confidence_factors.append(0.6)
        
        # Validate element counts
        element_count = metadata.get("element_count", 0)
        text_count = metadata.get("text_element_count", 0)
        image_count = metadata.get("image_element_count", 0)
        table_count = metadata.get("table_element_count", 0)
        
        if element_count < 0:
            errors.append("Element count cannot be negative")
        
        # Check consistency of element counts
        typed_total = text_count + image_count + table_count
        if typed_total > element_count:
            warnings.append("Sum of typed elements exceeds total element count")
            confidence_factors.append(0.6)
        elif element_count > 0:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)
        
        # Validate text metrics
        word_count = metadata.get("word_count", 0)
        char_count = metadata.get("character_count", 0)
        if word_count < 0:
            errors.append("Word count cannot be negative")
        if char_count < 0:
            errors.append("Character count cannot be negative")
        
        # Check word/character ratio
        if word_count > 0 and char_count > 0:
            avg_word_length = char_count / word_count
            if 1 <= avg_word_length <= 50:  # Reasonable range
                confidence_factors.append(0.9)
            else:
                warnings.append("Unusual average word length")
                confidence_factors.append(0.7)
        
        # Validate rotation
        rotation = metadata.get("rotation", 0)
        if rotation < 0 or rotation >= 360:
            errors.append("Rotation must be between 0 and 360 degrees")
        
        # Calculate overall confidence
        if confidence_factors:
            confidence_score = sum(confidence_factors) / len(confidence_factors)
        else:
            confidence_score = 0.5
        
        # Adjust confidence based on errors and warnings
        if errors:
            confidence_score *= 0.3
        elif warnings:
            confidence_score *= 0.8
        
        return MetadataValidationResult(
            is_valid=len(errors) == 0,
            confidence_score=max(0.0, min(1.0, confidence_score)),
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    def _get_page(self, document: Any, page_number: int) -> Optional[Any]:
        """Get page object from document.
        
        Args:
            document: Document object
            page_number: Page number (1-indexed)
            
        Returns:
            Page object or None if not found
        """
        if hasattr(document, 'pages') and document.pages:
            # Convert to 0-indexed
            page_index = page_number - 1
            if 0 <= page_index < len(document.pages):
                return document.pages[page_index]
        
        # If no separate pages, treat entire document as single page
        if page_number == 1:
            return document
        
        return None
    
    def _extract_page_dimensions(self, page: Any) -> Dict[str, Any]:
        """Extract page dimensions and orientation.
        
        Args:
            page: Page object
            
        Returns:
            Dictionary with dimension information
        """
        dimensions = {}
        
        # Extract width and height
        if hasattr(page, 'width'):
            dimensions["width"] = float(page.width)
        if hasattr(page, 'height'):
            dimensions["height"] = float(page.height)
        
        # Extract rotation
        if hasattr(page, 'rotation'):
            dimensions["rotation"] = float(page.rotation)
        else:
            dimensions["rotation"] = 0.0
        
        # Calculate aspect ratio if dimensions available
        width = dimensions.get("width")
        height = dimensions.get("height")
        if width and height:
            dimensions["aspect_ratio"] = width / height
            
            # Determine orientation
            if width > height:
                dimensions["orientation"] = "landscape"
            elif height > width:
                dimensions["orientation"] = "portrait"
            else:
                dimensions["orientation"] = "square"
        
        return dimensions
    
    async def _extract_content_metrics(self, page: Any) -> Dict[str, Any]:
        """Extract content metrics for the page.
        
        Args:
            page: Page object
            
        Returns:
            Dictionary with content metrics
        """
        metrics = {}
        
        # Initialize counters
        total_elements = 0
        text_elements = 0
        image_elements = 0
        table_elements = 0
        word_count = 0
        char_count = 0
        paragraph_count = 0
        
        # Extract from page elements
        if hasattr(page, 'elements'):
            elements = page.elements
        elif hasattr(page, 'blocks'):
            elements = page.blocks
        else:
            # Try to get elements from parent document
            elements = getattr(page, 'content', [])
        
        # Process elements
        for element in elements:
            total_elements += 1
            
            # Classify element type
            element_type = self._classify_element_type(element)
            if element_type == 'text':
                text_elements += 1
                
                # Extract text metrics
                text_content = self._get_element_text(element)
                if text_content:
                    words = text_content.split()
                    word_count += len(words)
                    char_count += len(text_content)
                    
                    # Count paragraphs (rough estimate)
                    paragraphs = text_content.split('\n\n')
                    paragraph_count += len(paragraphs)
                    
            elif element_type == 'image':
                image_elements += 1
            elif element_type == 'table':
                table_elements += 1
        
        # Store metrics
        metrics.update({
            "element_count": total_elements,
            "text_element_count": text_elements,
            "image_element_count": image_elements,
            "table_element_count": table_elements
        })
        
        if word_count > 0:
            metrics["word_count"] = word_count
        if char_count > 0:
            metrics["character_count"] = char_count
        if paragraph_count > 0:
            metrics["paragraph_count"] = paragraph_count
        
        return metrics
    
    async def _extract_layout_properties(self, page: Any) -> Dict[str, Any]:
        """Extract layout-related properties.
        
        Args:
            page: Page object
            
        Returns:
            Dictionary with layout properties
        """
        layout = {}
        
        # Detect columns
        column_info = self._detect_columns(page)
        if column_info:
            layout.update(column_info)
        
        # Detect header/footer
        header_footer = self._detect_header_footer(page)
        layout.update(header_footer)
        
        # Detect margin notes
        layout["has_margin_notes"] = self._detect_margin_notes(page)
        
        return layout
    
    async def _calculate_page_quality(
        self,
        page: Any,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate page quality metrics.
        
        Args:
            page: Page object
            metadata: Extracted metadata so far
            
        Returns:
            Dictionary with quality metrics
        """
        quality = {}
        
        # Text clarity score based on content metrics
        clarity_factors = []
        
        word_count = metadata.get("word_count", 0)
        char_count = metadata.get("character_count", 0)
        
        if word_count > 0 and char_count > 0:
            avg_word_length = char_count / word_count
            if 3 <= avg_word_length <= 15:  # Reasonable range
                clarity_factors.append(0.9)
            else:
                clarity_factors.append(0.6)
        else:
            clarity_factors.append(0.3)
        
        # Check element density
        element_count = metadata.get("element_count", 0)
        width = metadata.get("width", 1)
        height = metadata.get("height", 1)
        page_area = width * height
        
        if page_area > 0:
            element_density = element_count / (page_area / 10000)  # Normalize
            if 0.1 <= element_density <= 10:  # Reasonable range
                clarity_factors.append(0.9)
            else:
                clarity_factors.append(0.7)
        
        if clarity_factors:
            quality["text_clarity_score"] = sum(clarity_factors) / len(clarity_factors)
        
        # Layout quality score
        layout_factors = []
        
        # Check for reasonable element distribution
        text_count = metadata.get("text_element_count", 0)
        total_count = metadata.get("element_count", 1)
        
        if total_count > 0:
            text_ratio = text_count / total_count
            if 0.3 <= text_ratio <= 0.9:  # Good text/other ratio
                layout_factors.append(0.9)
            else:
                layout_factors.append(0.7)
        
        # Check for presence of structure indicators
        if metadata.get("has_header") or metadata.get("has_footer"):
            layout_factors.append(0.8)
        else:
            layout_factors.append(0.6)
        
        if layout_factors:
            quality["layout_quality_score"] = sum(layout_factors) / len(layout_factors)
        
        # OCR confidence (placeholder - would be calculated from actual OCR)
        if self._appears_to_be_ocr_content(page):
            quality["ocr_confidence"] = 0.8  # Placeholder
        
        return quality
    
    def _classify_element_type(self, element: Any) -> str:
        """Classify element type based on properties.
        
        Args:
            element: Element object
            
        Returns:
            Element type string
        """
        # Check element type attribute
        if hasattr(element, 'type'):
            element_type = str(element.type).lower()
            if 'text' in element_type or 'paragraph' in element_type:
                return 'text'
            elif 'image' in element_type or 'figure' in element_type:
                return 'image'
            elif 'table' in element_type:
                return 'table'
        
        # Check for text content
        if hasattr(element, 'text') and element.text:
            return 'text'
        
        # Check for image properties
        if hasattr(element, 'image') or hasattr(element, 'src'):
            return 'image'
        
        # Check for table properties
        if (hasattr(element, 'rows') or 
            hasattr(element, 'cells') or
            'table' in str(type(element)).lower()):
            return 'table'
        
        # Default to text
        return 'text'
    
    def _get_element_text(self, element: Any) -> Optional[str]:
        """Extract text content from element.
        
        Args:
            element: Element object
            
        Returns:
            Text content or None
        """
        if hasattr(element, 'text'):
            return element.text
        elif hasattr(element, 'content'):
            return str(element.content)
        elif hasattr(element, 'value'):
            return str(element.value)
        
        return None
    
    def _detect_columns(self, page: Any) -> Dict[str, Any]:
        """Detect column layout on page.
        
        Args:
            page: Page object
            
        Returns:
            Dictionary with column information
        """
        # Simplified column detection
        # In practice, this would analyze element positions
        
        # Check if page has column information
        if hasattr(page, 'columns'):
            return {"column_count": len(page.columns)}
        
        # Estimate from element positions (simplified)
        if hasattr(page, 'elements'):
            # Group elements by x-coordinate
            x_positions = []
            for element in page.elements:
                if hasattr(element, 'bbox') and element.bbox:
                    x_positions.append(element.bbox[0])  # x1 coordinate
            
            if x_positions:
                # Simple clustering by x-position
                sorted_x = sorted(set(x_positions))
                if len(sorted_x) >= 2:
                    # Check for distinct column separations
                    gaps = [sorted_x[i+1] - sorted_x[i] for i in range(len(sorted_x)-1)]
                    if gaps:
                        avg_gap = statistics.mean(gaps)
                        large_gaps = [g for g in gaps if g > avg_gap * 2]
                        column_count = len(large_gaps) + 1
                        return {"column_count": min(column_count, 4)}  # Max 4 columns
        
        return {"column_count": 1}  # Default single column
    
    def _detect_header_footer(self, page: Any) -> Dict[str, Any]:
        """Detect presence of headers and footers.
        
        Args:
            page: Page object
            
        Returns:
            Dictionary with header/footer flags
        """
        header_footer = {
            "has_header": False,
            "has_footer": False
        }
        
        # Check for explicit header/footer
        if hasattr(page, 'header') and page.header:
            header_footer["has_header"] = True
        if hasattr(page, 'footer') and page.footer:
            header_footer["has_footer"] = True
        
        # Detect from element positions
        if hasattr(page, 'elements') and hasattr(page, 'height'):
            page_height = page.height
            
            for element in page.elements:
                if hasattr(element, 'bbox') and element.bbox:
                    y1, y2 = element.bbox[1], element.bbox[3]
                    
                    # Check if element is in header area (top 10%)
                    if y2 > page_height * 0.9:
                        header_footer["has_header"] = True
                    
                    # Check if element is in footer area (bottom 10%)
                    if y1 < page_height * 0.1:
                        header_footer["has_footer"] = True
        
        return header_footer
    
    def _detect_margin_notes(self, page: Any) -> bool:
        """Detect presence of margin notes.
        
        Args:
            page: Page object
            
        Returns:
            True if margin notes detected
        """
        # Simplified margin note detection
        # In practice, this would analyze element positions relative to main content
        
        if hasattr(page, 'elements') and hasattr(page, 'width'):
            page_width = page.width
            main_content_elements = 0
            margin_elements = 0
            
            for element in page.elements:
                if hasattr(element, 'bbox') and element.bbox:
                    x1, x2 = element.bbox[0], element.bbox[2]
                    element_width = x2 - x1
                    
                    # Check if element is in margin (less than 60% of page width)
                    if element_width < page_width * 0.6:
                        margin_elements += 1
                    else:
                        main_content_elements += 1
            
            # If more than 20% of elements are in margins, likely has margin notes
            total_elements = main_content_elements + margin_elements
            if total_elements > 0:
                margin_ratio = margin_elements / total_elements
                return margin_ratio > 0.2
        
        return False
    
    def _appears_to_be_ocr_content(self, page: Any) -> bool:
        """Check if page appears to contain OCR-extracted content.
        
        Args:
            page: Page object
            
        Returns:
            True if appears to be OCR content
        """
        # Check for OCR indicators
        if hasattr(page, 'is_ocr') and page.is_ocr:
            return True
        
        # Check for OCR confidence attributes
        if hasattr(page, 'ocr_confidence'):
            return True
        
        # Check elements for OCR indicators
        if hasattr(page, 'elements'):
            for element in page.elements:
                if (hasattr(element, 'ocr_confidence') or
                    hasattr(element, 'confidence') or
                    'ocr' in str(type(element)).lower()):
                    return True
        
        return False