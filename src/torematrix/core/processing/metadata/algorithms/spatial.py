"""Spatial relationship algorithms for document elements.

This module provides algorithms for detecting spatial relationships between
document elements based on their coordinates and bounding boxes.
"""

import logging
import math
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ....models.element import UnifiedElement
from ..models.relationship import Relationship, RelationshipType

logger = logging.getLogger(__name__)


class SpatialRelationType(str, Enum):
    """Types of spatial relationships."""
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    OVERLAPS = "overlaps"
    ADJACENT_LEFT = "adjacent_left"
    ADJACENT_RIGHT = "adjacent_right"
    ADJACENT_TOP = "adjacent_top"
    ADJACENT_BOTTOM = "adjacent_bottom"
    ALIGNED_LEFT = "aligned_left"
    ALIGNED_RIGHT = "aligned_right"
    ALIGNED_TOP = "aligned_top"
    ALIGNED_BOTTOM = "aligned_bottom"
    ALIGNED_CENTER_HORIZONTAL = "aligned_center_horizontal"
    ALIGNED_CENTER_VERTICAL = "aligned_center_vertical"


@dataclass
class BoundingBox:
    """Bounding box representation."""
    left: float
    top: float
    right: float
    bottom: float
    
    @property
    def width(self) -> float:
        """Get width of bounding box."""
        return self.right - self.left
    
    @property
    def height(self) -> float:
        """Get height of bounding box."""
        return self.bottom - self.top
    
    @property
    def area(self) -> float:
        """Get area of bounding box."""
        return self.width * self.height
    
    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return (self.left + self.right) / 2
    
    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return (self.top + self.bottom) / 2
    
    def intersection_area(self, other: 'BoundingBox') -> float:
        """Calculate intersection area with another bounding box.
        
        Args:
            other: Another bounding box
            
        Returns:
            Area of intersection
        """
        left = max(self.left, other.left)
        top = max(self.top, other.top)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)
        
        if left < right and top < bottom:
            return (right - left) * (bottom - top)
        return 0.0
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union (IoU) with another bounding box.
        
        Args:
            other: Another bounding box
            
        Returns:
            IoU value between 0 and 1
        """
        intersection = self.intersection_area(other)
        union = self.area + other.area - intersection
        
        if union == 0:
            return 0.0
        return intersection / union
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate minimum distance to another bounding box.
        
        Args:
            other: Another bounding box
            
        Returns:
            Minimum distance between boxes
        """
        if self.intersection_area(other) > 0:
            return 0.0
        
        # Calculate horizontal and vertical gaps
        horizontal_gap = max(0, max(self.left - other.right, other.left - self.right))
        vertical_gap = max(0, max(self.top - other.bottom, other.top - self.bottom))
        
        return math.sqrt(horizontal_gap ** 2 + vertical_gap ** 2)


class SpatialAnalyzer:
    """Analyzer for spatial relationships between elements."""
    
    def __init__(self, config):
        """Initialize spatial analyzer.
        
        Args:
            config: Configuration object with spatial thresholds
        """
        self.config = config
        self.spatial_threshold = getattr(config, 'spatial_threshold', 10.0)
        self.alignment_threshold = getattr(config, 'alignment_threshold', 5.0)
        
    async def analyze_relationship(
        self, 
        element1: UnifiedElement, 
        element2: UnifiedElement
    ) -> List[Relationship]:
        """Analyze spatial relationship between two elements.
        
        Args:
            element1: First element
            element2: Second element
            
        Returns:
            List of detected spatial relationships
        """
        bbox1 = self._get_bounding_box(element1)
        bbox2 = self._get_bounding_box(element2)
        
        if not bbox1 or not bbox2:
            return []
        
        relationships = []
        
        # Check containment relationships
        containment_rel = self._analyze_containment(element1, element2, bbox1, bbox2)
        if containment_rel:
            relationships.append(containment_rel)
        
        # Check adjacency relationships
        adjacency_rels = self._analyze_adjacency(element1, element2, bbox1, bbox2)
        relationships.extend(adjacency_rels)
        
        # Check alignment relationships
        alignment_rels = self._analyze_alignment(element1, element2, bbox1, bbox2)
        relationships.extend(alignment_rels)
        
        # Check overlap relationships
        overlap_rel = self._analyze_overlap(element1, element2, bbox1, bbox2)
        if overlap_rel:
            relationships.append(overlap_rel)
        
        return relationships
    
    def _get_bounding_box(self, element: UnifiedElement) -> Optional[BoundingBox]:
        """Extract bounding box from element.
        
        Args:
            element: Element to extract bounding box from
            
        Returns:
            BoundingBox if coordinates exist, None otherwise
        """
        if not (element.metadata and element.metadata.coordinates):
            return None
        
        bbox = element.metadata.coordinates.layout_bbox
        if not bbox or len(bbox) < 4:
            return None
        
        return BoundingBox(
            left=bbox[0],
            top=bbox[1],
            right=bbox[2],
            bottom=bbox[3]
        )
    
    def _analyze_containment(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> Optional[Relationship]:
        """Analyze containment relationship between elements.
        
        Args:
            element1: First element
            element2: Second element
            bbox1: Bounding box of first element
            bbox2: Bounding box of second element
            
        Returns:
            Containment relationship if detected
        """
        # Check if bbox1 contains bbox2
        if (bbox1.left <= bbox2.left and
            bbox1.top <= bbox2.top and
            bbox1.right >= bbox2.right and
            bbox1.bottom >= bbox2.bottom and
            bbox1.area > bbox2.area):
            
            # Calculate how well element2 fits inside element1
            coverage = bbox2.area / bbox1.area
            confidence = min(0.95, 0.7 + coverage * 0.25)
            
            return Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_CONTAINS,
                confidence=confidence,
                metadata={
                    "coverage_ratio": coverage,
                    "spatial_type": SpatialRelationType.CONTAINS.value
                }
            )
        
        # Check if bbox2 contains bbox1
        if (bbox2.left <= bbox1.left and
            bbox2.top <= bbox1.top and
            bbox2.right >= bbox1.right and
            bbox2.bottom >= bbox1.bottom and
            bbox2.area > bbox1.area):
            
            coverage = bbox1.area / bbox2.area
            confidence = min(0.95, 0.7 + coverage * 0.25)
            
            return Relationship(
                source_id=element2.id,
                target_id=element1.id,
                relationship_type=RelationshipType.SPATIAL_CONTAINS,
                confidence=confidence,
                metadata={
                    "coverage_ratio": coverage,
                    "spatial_type": SpatialRelationType.CONTAINS.value
                }
            )
        
        return None
    
    def _analyze_adjacency(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> List[Relationship]:
        """Analyze adjacency relationship between elements.
        
        Args:
            element1: First element
            element2: Second element
            bbox1: Bounding box of first element
            bbox2: Bounding box of second element
            
        Returns:
            List of adjacency relationships
        """
        relationships = []
        distance = bbox1.distance_to(bbox2)
        
        if distance > self.spatial_threshold:
            return relationships
        
        # Check horizontal adjacency
        vertical_overlap = max(0, min(bbox1.bottom, bbox2.bottom) - max(bbox1.top, bbox2.top))
        min_height = min(bbox1.height, bbox2.height)
        
        if vertical_overlap > min_height * 0.5:  # Significant vertical overlap
            # Element2 is to the right of element1
            if bbox2.left >= bbox1.right - self.spatial_threshold:
                gap = bbox2.left - bbox1.right
                confidence = max(0.5, 1.0 - gap / self.spatial_threshold)
                
                relationships.append(Relationship(
                    source_id=element1.id,
                    target_id=element2.id,
                    relationship_type=RelationshipType.SPATIAL_ADJACENT,
                    confidence=confidence,
                    metadata={
                        "direction": "right",
                        "gap": gap,
                        "vertical_overlap": vertical_overlap / min_height,
                        "spatial_type": SpatialRelationType.ADJACENT_RIGHT.value
                    }
                ))
            
            # Element2 is to the left of element1
            elif bbox1.left >= bbox2.right - self.spatial_threshold:
                gap = bbox1.left - bbox2.right
                confidence = max(0.5, 1.0 - gap / self.spatial_threshold)
                
                relationships.append(Relationship(
                    source_id=element2.id,
                    target_id=element1.id,
                    relationship_type=RelationshipType.SPATIAL_ADJACENT,
                    confidence=confidence,
                    metadata={
                        "direction": "right",
                        "gap": gap,
                        "vertical_overlap": vertical_overlap / min_height,
                        "spatial_type": SpatialRelationType.ADJACENT_RIGHT.value
                    }
                ))
        
        # Check vertical adjacency
        horizontal_overlap = max(0, min(bbox1.right, bbox2.right) - max(bbox1.left, bbox2.left))
        min_width = min(bbox1.width, bbox2.width)
        
        if horizontal_overlap > min_width * 0.5:  # Significant horizontal overlap
            # Element2 is below element1
            if bbox2.top >= bbox1.bottom - self.spatial_threshold:
                gap = bbox2.top - bbox1.bottom
                confidence = max(0.5, 1.0 - gap / self.spatial_threshold)
                
                relationships.append(Relationship(
                    source_id=element1.id,
                    target_id=element2.id,
                    relationship_type=RelationshipType.SPATIAL_ADJACENT,
                    confidence=confidence,
                    metadata={
                        "direction": "bottom",
                        "gap": gap,
                        "horizontal_overlap": horizontal_overlap / min_width,
                        "spatial_type": SpatialRelationType.ADJACENT_BOTTOM.value
                    }
                ))
            
            # Element2 is above element1
            elif bbox1.top >= bbox2.bottom - self.spatial_threshold:
                gap = bbox1.top - bbox2.bottom
                confidence = max(0.5, 1.0 - gap / self.spatial_threshold)
                
                relationships.append(Relationship(
                    source_id=element2.id,
                    target_id=element1.id,
                    relationship_type=RelationshipType.SPATIAL_ADJACENT,
                    confidence=confidence,
                    metadata={
                        "direction": "bottom",
                        "gap": gap,
                        "horizontal_overlap": horizontal_overlap / min_width,
                        "spatial_type": SpatialRelationType.ADJACENT_BOTTOM.value
                    }
                ))
        
        return relationships
    
    def _analyze_alignment(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> List[Relationship]:
        """Analyze alignment relationship between elements.
        
        Args:
            element1: First element
            element2: Second element
            bbox1: Bounding box of first element
            bbox2: Bounding box of second element
            
        Returns:
            List of alignment relationships
        """
        relationships = []
        
        # Check horizontal alignments
        if abs(bbox1.left - bbox2.left) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.left - bbox2.left) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,  # Using adjacent for alignment
                confidence=confidence,
                metadata={
                    "alignment": "left",
                    "offset": abs(bbox1.left - bbox2.left),
                    "spatial_type": SpatialRelationType.ALIGNED_LEFT.value
                }
            ))
        
        if abs(bbox1.right - bbox2.right) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.right - bbox2.right) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,
                confidence=confidence,
                metadata={
                    "alignment": "right",
                    "offset": abs(bbox1.right - bbox2.right),
                    "spatial_type": SpatialRelationType.ALIGNED_RIGHT.value
                }
            ))
        
        if abs(bbox1.center_x - bbox2.center_x) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.center_x - bbox2.center_x) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,
                confidence=confidence,
                metadata={
                    "alignment": "center_horizontal",
                    "offset": abs(bbox1.center_x - bbox2.center_x),
                    "spatial_type": SpatialRelationType.ALIGNED_CENTER_HORIZONTAL.value
                }
            ))
        
        # Check vertical alignments
        if abs(bbox1.top - bbox2.top) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.top - bbox2.top) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,
                confidence=confidence,
                metadata={
                    "alignment": "top",
                    "offset": abs(bbox1.top - bbox2.top),
                    "spatial_type": SpatialRelationType.ALIGNED_TOP.value
                }
            ))
        
        if abs(bbox1.bottom - bbox2.bottom) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.bottom - bbox2.bottom) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,
                confidence=confidence,
                metadata={
                    "alignment": "bottom",
                    "offset": abs(bbox1.bottom - bbox2.bottom),
                    "spatial_type": SpatialRelationType.ALIGNED_BOTTOM.value
                }
            ))
        
        if abs(bbox1.center_y - bbox2.center_y) <= self.alignment_threshold:
            confidence = 1.0 - abs(bbox1.center_y - bbox2.center_y) / self.alignment_threshold
            relationships.append(Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_ADJACENT,
                confidence=confidence,
                metadata={
                    "alignment": "center_vertical",
                    "offset": abs(bbox1.center_y - bbox2.center_y),
                    "spatial_type": SpatialRelationType.ALIGNED_CENTER_VERTICAL.value
                }
            ))
        
        return relationships
    
    def _analyze_overlap(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> Optional[Relationship]:
        """Analyze overlap relationship between elements.
        
        Args:
            element1: First element
            element2: Second element
            bbox1: Bounding box of first element
            bbox2: Bounding box of second element
            
        Returns:
            Overlap relationship if detected
        """
        intersection_area = bbox1.intersection_area(bbox2)
        
        if intersection_area == 0:
            return None
        
        # Calculate overlap ratios
        overlap_ratio1 = intersection_area / bbox1.area
        overlap_ratio2 = intersection_area / bbox2.area
        max_overlap = max(overlap_ratio1, overlap_ratio2)
        
        # Only create overlap relationship if significant overlap (but not containment)
        if max_overlap > 0.1 and max_overlap < 0.9:
            iou = bbox1.iou(bbox2)
            confidence = min(0.9, 0.5 + iou * 0.4)
            
            return Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.SPATIAL_OVERLAPS,
                confidence=confidence,
                metadata={
                    "intersection_area": intersection_area,
                    "overlap_ratio_1": overlap_ratio1,
                    "overlap_ratio_2": overlap_ratio2,
                    "iou": iou,
                    "spatial_type": SpatialRelationType.OVERLAPS.value
                }
            )
        
        return None