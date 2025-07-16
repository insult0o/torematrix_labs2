"""
Metadata Merging Algorithms

Handles merging and splitting of element metadata with conflict resolution.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """Strategies for resolving metadata conflicts."""
    FIRST = "first"
    LAST = "last"
    AVERAGE = "average"
    MAJORITY = "majority"


class MetadataMerger:
    """Handles metadata merging and splitting operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".MetadataMerger")
    
    def merge_metadata(self, elements: List[Element]) -> Optional[ElementMetadata]:
        """Merge metadata from multiple elements."""
        if not elements:
            return None
        
        # Get all metadata objects
        metadata_list = [elem.metadata for elem in elements if elem.metadata]
        if not metadata_list:
            return None
        
        # Merge coordinates using coordinate processor
        from .coordinate_ops import CoordinateProcessor
        coord_processor = CoordinateProcessor()
        merged_coordinates = coord_processor.merge_coordinates(elements)
        
        # Merge confidence scores (average)
        merged_confidence = self._merge_confidence_scores(metadata_list)
        
        # Use page number from first element
        merged_page_number = self._get_first_value(metadata_list, "page_number")
        
        # Use detection method from first element
        merged_detection_method = self._get_first_value(metadata_list, "detection_method")
        
        return ElementMetadata(
            coordinates=merged_coordinates,
            confidence=merged_confidence,
            page_number=merged_page_number,
            detection_method=merged_detection_method
        )
    
    def split_metadata(self, element: Element, split_count: int) -> List[Optional[ElementMetadata]]:
        """Split metadata from a single element."""
        if not element.metadata or split_count <= 0:
            return [None] * split_count
        
        original_metadata = element.metadata
        
        # Split coordinates using coordinate processor
        from .coordinate_ops import CoordinateProcessor
        coord_processor = CoordinateProcessor()
        split_coordinates = coord_processor.split_coordinates(element, split_count)
        
        # Create metadata for each split
        split_metadata_list = []
        for i in range(split_count):
            # Adjust confidence slightly for splits
            confidence = original_metadata.confidence
            if confidence is not None:
                confidence = confidence * 0.95  # Slight reduction
            
            split_metadata = ElementMetadata(
                coordinates=split_coordinates[i] if i < len(split_coordinates) else None,
                confidence=confidence,
                page_number=original_metadata.page_number,
                detection_method=original_metadata.detection_method
            )
            split_metadata_list.append(split_metadata)
        
        return split_metadata_list
    
    def _merge_confidence_scores(self, metadata_list: List[ElementMetadata]) -> Optional[float]:
        """Merge confidence scores using average strategy."""
        confidence_scores = [meta.confidence for meta in metadata_list 
                           if meta.confidence is not None]
        
        if not confidence_scores:
            return None
        
        return sum(confidence_scores) / len(confidence_scores)
    
    def _get_first_value(self, metadata_list: List[ElementMetadata], attribute: str) -> Any:
        """Get the first non-None value for an attribute."""
        for meta in metadata_list:
            value = getattr(meta, attribute, None)
            if value is not None:
                return value
        return None