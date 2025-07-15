"""
Coordinate Operations for Merge/Split

Handles coordinate calculations and transformations for merge/split operations.
"""

from typing import List, Optional, Tuple
import logging

from torematrix.core.models.element import Element
from torematrix.core.models.coordinates import Coordinates

logger = logging.getLogger(__name__)


class CoordinateProcessor:
    """Processes coordinates for merge/split operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".CoordinateProcessor")
    
    def merge_coordinates(self, elements: List[Element]) -> Optional[Coordinates]:
        """Merge coordinates from multiple elements."""
        elements_with_coords = [
            elem for elem in elements
            if elem.metadata and elem.metadata.coordinates
        ]
        
        if not elements_with_coords:
            return None
        
        # Merge layout bboxes
        merged_layout_bbox = self._merge_layout_bboxes(elements_with_coords)
        
        # Use coordinate system from first element
        coord_system = elements_with_coords[0].metadata.coordinates.coordinate_system
        
        return Coordinates(
            layout_bbox=merged_layout_bbox,
            coordinate_system=coord_system or "pixel"
        )
    
    def split_coordinates(self, element: Element, split_count: int) -> List[Optional[Coordinates]]:
        """Split coordinates for a single element."""
        if not element.metadata or not element.metadata.coordinates:
            return [None] * split_count
        
        original_coords = element.metadata.coordinates
        
        if not original_coords.layout_bbox:
            return [None] * split_count
        
        # Calculate split coordinates
        split_coords = []
        left, top, right, bottom = original_coords.layout_bbox
        width = right - left
        segment_width = width / split_count
        
        for i in range(split_count):
            segment_left = left + (segment_width * i)
            segment_right = segment_left + segment_width
            segment_bbox = [segment_left, top, segment_right, bottom]
            
            coords = Coordinates(
                layout_bbox=segment_bbox,
                coordinate_system=original_coords.coordinate_system or "pixel"
            )
            split_coords.append(coords)
        
        return split_coords
    
    def _merge_layout_bboxes(self, elements: List[Element]) -> Optional[List[float]]:
        """Merge layout bounding boxes from multiple elements."""
        bboxes = []
        for elem in elements:
            if (elem.metadata and elem.metadata.coordinates and 
                elem.metadata.coordinates.layout_bbox):
                bboxes.append(elem.metadata.coordinates.layout_bbox)
        
        if not bboxes:
            return None
        
        # Calculate union of all bounding boxes
        min_left = min(bbox[0] for bbox in bboxes)
        min_top = min(bbox[1] for bbox in bboxes)
        max_right = max(bbox[2] for bbox in bboxes)
        max_bottom = max(bbox[3] for bbox in bboxes)
        
        return [min_left, min_top, max_right, max_bottom]