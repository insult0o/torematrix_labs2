"""Reading order extractor for document layout analysis.

This module provides algorithms to determine the reading order of elements
in a document, including column detection and multi-language support.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from ....models.element import UnifiedElement
from ..algorithms.spatial import BoundingBox

logger = logging.getLogger(__name__)


class ReadingDirection(str, Enum):
    """Reading directions supported."""
    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"
    TOP_TO_BOTTOM = "ttb"
    BOTTOM_TO_TOP = "btt"


@dataclass
class Column:
    """Represents a column in the document layout."""
    left: float
    right: float
    elements: List[str]  # Element IDs
    confidence: float = 0.0
    
    @property
    def width(self) -> float:
        """Get column width."""
        return self.right - self.left
    
    @property
    def center(self) -> float:
        """Get column center X coordinate."""
        return (self.left + self.right) / 2


@dataclass
class ReadingOrder:
    """Represents the reading order of elements in a document."""
    ordered_elements: List[str]  # Element IDs in reading order
    columns: List[Column]
    reading_direction: ReadingDirection
    confidence: float
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PageLayout:
    """Represents page layout information."""
    width: float
    height: float
    margins: Dict[str, float] = None  # top, bottom, left, right
    
    def __post_init__(self):
        if self.margins is None:
            self.margins = {"top": 0, "bottom": 0, "left": 0, "right": 0}


@dataclass
class ReadingOrderConfig:
    """Configuration for reading order extraction."""
    column_gap_threshold: float = 20.0
    min_column_width: float = 50.0
    line_spacing_threshold: float = 15.0
    paragraph_spacing_threshold: float = 25.0
    alignment_tolerance: float = 5.0


class ColumnDetector:
    """Detects column structure in document layout."""
    
    def __init__(self, config: ReadingOrderConfig):
        """Initialize column detector.
        
        Args:
            config: Configuration for column detection
        """
        self.config = config
    
    def detect_columns(self, elements: List[UnifiedElement]) -> List[Column]:
        """Detect column structure from element positions.
        
        Args:
            elements: List of elements to analyze
            
        Returns:
            List of detected columns
        """
        if not elements:
            return []
        
        # Get bounding boxes for text elements only
        text_elements = [e for e in elements if self._is_text_element(e)]
        if not text_elements:
            return []
        
        bboxes = []
        element_ids = []
        
        for element in text_elements:
            bbox = self._get_bounding_box(element)
            if bbox:
                bboxes.append(bbox)
                element_ids.append(element.id)
        
        if not bboxes:
            return []
        
        # Find column boundaries using X-coordinate clustering
        x_starts = [bbox.left for bbox in bboxes]
        x_ends = [bbox.right for bbox in bboxes]
        
        # Cluster starting positions to find column starts
        column_starts = self._cluster_coordinates(x_starts)
        
        # Create columns based on clustered starts
        columns = []
        for i, start in enumerate(column_starts):
            # Find elements that start near this column start
            column_elements = []
            for j, bbox in enumerate(bboxes):
                if abs(bbox.left - start) <= self.config.alignment_tolerance:
                    column_elements.append(element_ids[j])
            
            if column_elements:
                # Determine column boundaries
                column_bboxes = [bboxes[element_ids.index(eid)] for eid in column_elements]
                left = min(bbox.left for bbox in column_bboxes)
                right = max(bbox.right for bbox in column_bboxes)
                
                # Only create column if it meets minimum width requirement
                if right - left >= self.config.min_column_width:
                    confidence = self._calculate_column_confidence(column_bboxes)
                    columns.append(Column(
                        left=left,
                        right=right,
                        elements=column_elements,
                        confidence=confidence
                    ))
        
        # Sort columns by left position
        columns.sort(key=lambda c: c.left)
        
        # Merge overlapping columns
        merged_columns = self._merge_overlapping_columns(columns)
        
        logger.debug(f"Detected {len(merged_columns)} columns")
        return merged_columns
    
    def _is_text_element(self, element: UnifiedElement) -> bool:
        """Check if element contains text content.
        
        Args:
            element: Element to check
            
        Returns:
            True if element has text content
        """
        return element.type in ['Text', 'Title', 'Header', 'Paragraph', 'List', 'ListItem']
    
    def _get_bounding_box(self, element: UnifiedElement) -> Optional[BoundingBox]:
        """Get bounding box from element.
        
        Args:
            element: Element to get bounding box from
            
        Returns:
            BoundingBox if available, None otherwise
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
    
    def _cluster_coordinates(self, coordinates: List[float]) -> List[float]:
        """Cluster coordinates to find distinct positions.
        
        Args:
            coordinates: List of coordinates to cluster
            
        Returns:
            List of cluster centers
        """
        if not coordinates:
            return []
        
        # Sort coordinates
        sorted_coords = sorted(set(coordinates))
        
        if len(sorted_coords) == 1:
            return sorted_coords
        
        # Simple clustering based on gaps
        clusters = []
        current_cluster = [sorted_coords[0]]
        
        for coord in sorted_coords[1:]:
            if coord - current_cluster[-1] <= self.config.column_gap_threshold:
                current_cluster.append(coord)
            else:
                # Finish current cluster and start new one
                clusters.append(statistics.mean(current_cluster))
                current_cluster = [coord]
        
        # Add final cluster
        clusters.append(statistics.mean(current_cluster))
        
        return clusters
    
    def _calculate_column_confidence(self, bboxes: List[BoundingBox]) -> float:
        """Calculate confidence score for column detection.
        
        Args:
            bboxes: Bounding boxes of elements in column
            
        Returns:
            Confidence score between 0 and 1
        """
        if len(bboxes) < 2:
            return 0.5
        
        # Check alignment consistency
        left_positions = [bbox.left for bbox in bboxes]
        alignment_variance = statistics.variance(left_positions) if len(left_positions) > 1 else 0
        
        # Lower variance means better alignment
        alignment_score = max(0, 1.0 - alignment_variance / 100.0)
        
        # Check for reasonable spacing between elements
        y_positions = [bbox.top for bbox in bboxes]
        y_positions.sort()
        
        spacing_score = 1.0
        if len(y_positions) > 1:
            spacings = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
            avg_spacing = statistics.mean(spacings)
            
            # Penalize extremely small or large spacings
            if avg_spacing < 5 or avg_spacing > 100:
                spacing_score = 0.5
        
        return (alignment_score + spacing_score) / 2
    
    def _merge_overlapping_columns(self, columns: List[Column]) -> List[Column]:
        """Merge overlapping columns.
        
        Args:
            columns: List of columns to merge
            
        Returns:
            List of merged columns
        """
        if len(columns) <= 1:
            return columns
        
        merged = []
        current = columns[0]
        
        for next_col in columns[1:]:
            # Check if columns overlap significantly
            overlap = min(current.right, next_col.right) - max(current.left, next_col.left)
            min_width = min(current.width, next_col.width)
            
            if overlap > min_width * 0.3:  # 30% overlap threshold
                # Merge columns
                new_left = min(current.left, next_col.left)
                new_right = max(current.right, next_col.right)
                new_elements = current.elements + next_col.elements
                new_confidence = (current.confidence + next_col.confidence) / 2
                
                current = Column(
                    left=new_left,
                    right=new_right,
                    elements=new_elements,
                    confidence=new_confidence
                )
            else:
                merged.append(current)
                current = next_col
        
        merged.append(current)
        return merged


class ReadingOrderExtractor:
    """Extract reading order from document layout."""
    
    def __init__(self, config: ReadingOrderConfig):
        """Initialize reading order extractor.
        
        Args:
            config: Configuration for reading order extraction
        """
        self.config = config
        self.column_detector = ColumnDetector(config)
    
    async def extract_reading_order(
        self, 
        elements: List[UnifiedElement],
        page_layout: PageLayout,
        reading_direction: ReadingDirection = ReadingDirection.LEFT_TO_RIGHT
    ) -> ReadingOrder:
        """Extract complete reading order for page.
        
        Args:
            elements: List of elements to order
            page_layout: Page layout information
            reading_direction: Primary reading direction
            
        Returns:
            Complete reading order
        """
        logger.debug(f"Extracting reading order for {len(elements)} elements")
        
        # Detect columns
        columns = self.column_detector.detect_columns(elements)
        
        # Order elements within each column
        ordered_elements = []
        
        if columns:
            # Multi-column layout
            for column in columns:
                column_elements = [e for e in elements if e.id in column.elements]
                ordered_column = self.order_within_column(column_elements, reading_direction)
                ordered_elements.extend(ordered_column)
        else:
            # Single column layout
            ordered_elements = self.order_within_column(elements, reading_direction)
        
        # Calculate overall confidence
        confidence = self._calculate_reading_order_confidence(
            elements, ordered_elements, columns
        )
        
        reading_order = ReadingOrder(
            ordered_elements=[e.id for e in ordered_elements],
            columns=columns,
            reading_direction=reading_direction,
            confidence=confidence,
            metadata={
                "page_width": page_layout.width,
                "page_height": page_layout.height,
                "num_columns": len(columns),
                "algorithm": "spatial_clustering"
            }
        )
        
        # Validate reading order
        validation_result = self.validate_reading_order(reading_order, elements)
        reading_order.metadata["validation"] = validation_result
        
        logger.debug(f"Reading order confidence: {confidence:.2f}")
        return reading_order
    
    def order_within_column(
        self, 
        elements: List[UnifiedElement],
        direction: ReadingDirection
    ) -> List[UnifiedElement]:
        """Order elements within a column.
        
        Args:
            elements: Elements to order
            direction: Reading direction
            
        Returns:
            Elements sorted by reading order
        """
        if not elements:
            return []
        
        # Filter elements with valid coordinates
        valid_elements = []
        for element in elements:
            bbox = self._get_bounding_box(element)
            if bbox:
                valid_elements.append((element, bbox))
        
        if not valid_elements:
            return elements
        
        # Sort based on reading direction
        if direction == ReadingDirection.LEFT_TO_RIGHT:
            # Sort by top-to-bottom, then left-to-right
            sorted_elements = sorted(
                valid_elements,
                key=lambda x: (x[1].top, x[1].left)
            )
        elif direction == ReadingDirection.RIGHT_TO_LEFT:
            # Sort by top-to-bottom, then right-to-left
            sorted_elements = sorted(
                valid_elements,
                key=lambda x: (x[1].top, -x[1].right)
            )
        elif direction == ReadingDirection.TOP_TO_BOTTOM:
            # Sort by left-to-right, then top-to-bottom
            sorted_elements = sorted(
                valid_elements,
                key=lambda x: (x[1].left, x[1].top)
            )
        else:  # BOTTOM_TO_TOP
            # Sort by left-to-right, then bottom-to-top
            sorted_elements = sorted(
                valid_elements,
                key=lambda x: (x[1].left, -x[1].bottom)
            )
        
        # Return just the elements
        ordered = [element for element, _ in sorted_elements]
        
        # Add elements without coordinates at the end
        elements_without_coords = [e for e in elements if e not in [elem for elem, _ in valid_elements]]
        ordered.extend(elements_without_coords)
        
        return ordered
    
    def validate_reading_order(
        self, 
        order: ReadingOrder,
        elements: List[UnifiedElement]
    ) -> Dict:
        """Validate reading order makes sense.
        
        Args:
            order: Reading order to validate
            elements: Original elements
            
        Returns:
            Validation result dictionary
        """
        validation = {
            "is_valid": True,
            "issues": [],
            "score": 1.0
        }
        
        # Check if all elements are included
        element_ids = {e.id for e in elements}
        ordered_ids = set(order.ordered_elements)
        
        if element_ids != ordered_ids:
            missing = element_ids - ordered_ids
            extra = ordered_ids - element_ids
            
            if missing:
                validation["issues"].append(f"Missing elements: {missing}")
                validation["is_valid"] = False
            
            if extra:
                validation["issues"].append(f"Extra elements: {extra}")
                validation["is_valid"] = False
        
        # Check for reasonable spatial progression
        spatial_score = self._validate_spatial_progression(order, elements)
        validation["spatial_score"] = spatial_score
        
        if spatial_score < 0.5:
            validation["issues"].append("Poor spatial progression")
            validation["score"] *= 0.7
        
        # Check column consistency
        if order.columns:
            column_score = self._validate_column_consistency(order)
            validation["column_score"] = column_score
            
            if column_score < 0.6:
                validation["issues"].append("Inconsistent column structure")
                validation["score"] *= 0.8
        
        return validation
    
    def _get_bounding_box(self, element: UnifiedElement) -> Optional[BoundingBox]:
        """Get bounding box from element."""
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
    
    def _calculate_reading_order_confidence(
        self,
        elements: List[UnifiedElement],
        ordered_elements: List[UnifiedElement],
        columns: List[Column]
    ) -> float:
        """Calculate confidence in reading order.
        
        Args:
            elements: Original elements
            ordered_elements: Ordered elements
            columns: Detected columns
            
        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.7
        
        # Boost confidence if we have clear column structure
        if columns and len(columns) > 1:
            avg_column_confidence = sum(c.confidence for c in columns) / len(columns)
            base_confidence += 0.2 * avg_column_confidence
        
        # Check spatial consistency
        spatial_consistency = self._check_spatial_consistency(ordered_elements)
        base_confidence *= spatial_consistency
        
        return min(0.95, base_confidence)
    
    def _check_spatial_consistency(self, ordered_elements: List[UnifiedElement]) -> float:
        """Check spatial consistency of ordered elements.
        
        Args:
            ordered_elements: Elements in reading order
            
        Returns:
            Consistency score between 0 and 1
        """
        if len(ordered_elements) < 2:
            return 1.0
        
        violations = 0
        total_checks = 0
        
        for i in range(len(ordered_elements) - 1):
            bbox1 = self._get_bounding_box(ordered_elements[i])
            bbox2 = self._get_bounding_box(ordered_elements[i + 1])
            
            if bbox1 and bbox2:
                total_checks += 1
                
                # Check if elements progress naturally
                # Element 2 should be to the right or below element 1
                if not (bbox2.left >= bbox1.left - 20 or bbox2.top >= bbox1.top - 10):
                    violations += 1
        
        if total_checks == 0:
            return 1.0
        
        consistency = 1.0 - (violations / total_checks)
        return max(0.0, consistency)
    
    def _validate_spatial_progression(
        self, 
        order: ReadingOrder, 
        elements: List[UnifiedElement]
    ) -> float:
        """Validate spatial progression of reading order.
        
        Args:
            order: Reading order to validate
            elements: Original elements
            
        Returns:
            Spatial progression score
        """
        element_dict = {e.id: e for e in elements}
        
        valid_progressions = 0
        total_progressions = 0
        
        for i in range(len(order.ordered_elements) - 1):
            elem1_id = order.ordered_elements[i]
            elem2_id = order.ordered_elements[i + 1]
            
            if elem1_id in element_dict and elem2_id in element_dict:
                elem1 = element_dict[elem1_id]
                elem2 = element_dict[elem2_id]
                
                bbox1 = self._get_bounding_box(elem1)
                bbox2 = self._get_bounding_box(elem2)
                
                if bbox1 and bbox2:
                    total_progressions += 1
                    
                    # Check if progression makes sense for reading direction
                    if order.reading_direction == ReadingDirection.LEFT_TO_RIGHT:
                        if bbox2.top >= bbox1.top - 5 and bbox2.left >= bbox1.left - 10:
                            valid_progressions += 1
                    elif order.reading_direction == ReadingDirection.RIGHT_TO_LEFT:
                        if bbox2.top >= bbox1.top - 5 and bbox2.right <= bbox1.right + 10:
                            valid_progressions += 1
        
        if total_progressions == 0:
            return 1.0
        
        return valid_progressions / total_progressions
    
    def _validate_column_consistency(self, order: ReadingOrder) -> float:
        """Validate column consistency.
        
        Args:
            order: Reading order with columns
            
        Returns:
            Column consistency score
        """
        if not order.columns:
            return 1.0
        
        # Check if elements in each column are contiguous in reading order
        total_score = 0.0
        
        for column in order.columns:
            if not column.elements:
                continue
            
            # Find positions of column elements in reading order
            positions = []
            for elem_id in column.elements:
                if elem_id in order.ordered_elements:
                    positions.append(order.ordered_elements.index(elem_id))
            
            if len(positions) < 2:
                total_score += 1.0
                continue
            
            # Check how contiguous the positions are
            positions.sort()
            gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            
            # Lower gaps are better
            column_score = max(0.0, 1.0 - avg_gap / 10.0)
            total_score += column_score
        
        return total_score / len(order.columns)