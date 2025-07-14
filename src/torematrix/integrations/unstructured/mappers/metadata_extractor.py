"""
Metadata extraction and normalization for unstructured elements.

This module handles extracting, converting, and normalizing metadata
from unstructured.io elements to our unified format.
"""

from typing import Any, Dict, Optional
import logging

from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts and normalizes metadata from unstructured elements."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    def extract(self, element: Any) -> ElementMetadata:
        """Extract all available metadata from unstructured element."""
        try:
            # Extract coordinates
            coordinates = self._extract_coordinates(element)
            
            # Extract confidence
            confidence = self._extract_confidence(element)
            
            # Extract detection method
            detection_method = self._extract_detection_method(element)
            
            # Extract page info
            page_number = self._extract_page_number(element)
            
            # Extract custom fields
            custom_fields = self._extract_custom_fields(element)
            
            return ElementMetadata(
                coordinates=coordinates,
                confidence=confidence,
                detection_method=detection_method,
                page_number=page_number,
                custom_fields=custom_fields
            )
            
        except Exception as e:
            self._logger.error(f"Failed to extract metadata: {e}")
            return ElementMetadata()
    
    def _extract_coordinates(self, element: Any) -> Optional[Coordinates]:
        """Extract bounding box coordinates."""
        if not hasattr(element, 'metadata') or not element.metadata:
            return None
        
        coords = getattr(element.metadata, 'coordinates', None)
        if not coords:
            return None
        
        layout_bbox = getattr(coords, 'layout_bbox', None)
        if layout_bbox:
            return Coordinates(layout_bbox=layout_bbox, system="pixel")
        
        return None
    
    def _extract_confidence(self, element: Any) -> float:
        """Extract confidence score."""
        if hasattr(element, 'detection_class_prob'):
            value = element.detection_class_prob
            if isinstance(value, (int, float)):
                return float(value) if value <= 1 else float(value) / 100.0
        
        return 1.0
    
    def _extract_detection_method(self, element: Any) -> str:
        """Extract detection method information."""
        if hasattr(element, 'detection_method'):
            return str(element.detection_method)
        
        element_type = type(element).__name__
        return f"unstructured_{element_type.lower()}"
    
    def _extract_page_number(self, element: Any) -> Optional[int]:
        """Extract page number."""
        if hasattr(element, 'metadata') and element.metadata:
            if hasattr(element.metadata, 'page_number'):
                page_num = element.metadata.page_number
                if isinstance(page_num, int):
                    return page_num
        
        return None
    
    def _extract_custom_fields(self, element: Any) -> Dict[str, Any]:
        """Extract custom/additional fields."""
        custom = {}
        
        # Add element type info
        custom['source_element_type'] = type(element).__name__
        
        # Extract text as HTML if available
        if hasattr(element, 'text_as_html') and element.text_as_html:
            custom['text_as_html'] = element.text_as_html
        
        return custom


class MetadataNormalizer:
    """Normalizes metadata across different element types and sources."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    def normalize(self, metadata: ElementMetadata, element_type: str) -> ElementMetadata:
        """Normalize metadata based on element type and consistency rules."""
        try:
            # Create normalized copy
            custom_fields = metadata.custom_fields.copy()
            
            # Type-specific normalization
            if element_type.lower() == 'table':
                custom_fields = self._normalize_table_metadata(custom_fields)
            elif element_type.lower() == 'image':
                custom_fields = self._normalize_image_metadata(custom_fields)
            
            # General normalization
            confidence = self._normalize_confidence(metadata.confidence)
            
            return ElementMetadata(
                coordinates=metadata.coordinates,
                confidence=confidence,
                detection_method=metadata.detection_method,
                page_number=metadata.page_number,
                languages=metadata.languages,
                custom_fields=custom_fields
            )
            
        except Exception as e:
            self._logger.error(f"Failed to normalize metadata: {e}")
            return metadata
    
    def _normalize_table_metadata(self, custom_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize table-specific metadata."""
        if 'table_info' not in custom_fields:
            custom_fields['table_info'] = {}
        
        return custom_fields
    
    def _normalize_image_metadata(self, custom_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize image-specific metadata."""
        if 'image_info' not in custom_fields:
            custom_fields['image_info'] = {}
        
        return custom_fields
    
    def _normalize_confidence(self, confidence: float) -> float:
        """Normalize confidence score to 0-1 range."""
        if confidence > 1.0:
            return confidence / 100.0
        elif confidence < 0.0:
            return 0.0
        return confidence