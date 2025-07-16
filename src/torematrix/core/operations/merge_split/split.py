"""
Core Split Operations

Implements the SplitOperation class with split algorithm for dividing document elements.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import re

from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates
from .base_operation import BaseOperation, OperationResult, OperationStatus

logger = logging.getLogger(__name__)


@dataclass
class SplitResult(OperationResult):
    """Result of split operation."""
    split_elements: List[Element] = field(default_factory=list)
    original_element: Optional[Element] = None
    split_points: List[int] = field(default_factory=list)
    
    @property
    def split_successfully(self) -> bool:
        """Check if split was successful."""
        return self.success and len(self.split_elements) > 1


class SplitOperation(BaseOperation):
    """Core split operation for dividing a single element into multiple elements."""
    
    def __init__(self, element: Element, split_points: List[int], operation_id: Optional[str] = None):
        super().__init__(operation_id)
        self.element = element
        self.split_points = split_points or []
        self._split_elements: List[Element] = []
        self._original_element: Optional[Element] = None
        self.logger = logging.getLogger(__name__ + ".SplitOperation")
    
    def validate(self) -> bool:
        """Validate split operation parameters."""
        try:
            self.status = OperationStatus.VALIDATING
            
            # Basic validation
            if not self.element:
                self.logger.error("No element provided for split")
                return False
            
            if not self.split_points:
                self.logger.error("No split points provided")
                return False
            
            # Check element type is splittable
            splittable_types = {"text", "paragraph", "narrative_text"}
            if self.element.element_type not in splittable_types:
                self.logger.error(f"Element type '{self.element.element_type}' cannot be split")
                return False
            
            # Check text content
            if not self.element.text or len(self.element.text) < 10:
                self.logger.error("Element text too short for splitting")
                return False
            
            # Validate split points
            text_length = len(self.element.text)
            for point in self.split_points:
                if point < 0 or point >= text_length:
                    self.logger.error(f"Split point {point} is out of bounds (0-{text_length})")
                    return False
            
            # Check split points are sorted
            if self.split_points != sorted(self.split_points):
                self.logger.error("Split points must be in ascending order")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False
    
    def execute(self) -> OperationResult:
        """Execute the split operation."""
        try:
            self._start_execution()
            
            # Store original element for rollback
            self._original_element = self.element
            
            # Validate
            if not self.validate():
                self._end_execution(OperationStatus.FAILED)
                return SplitResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Validation failed",
                    execution_time_ms=self.execution_time_ms
                )
            
            # Perform the split
            self._split_elements = self._create_split_elements()
            
            if len(self._split_elements) < 2:
                self._end_execution(OperationStatus.FAILED)
                return SplitResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Failed to create split elements",
                    execution_time_ms=self.execution_time_ms
                )
            
            # Complete execution
            self._end_execution(OperationStatus.COMPLETED)
            
            return SplitResult(
                operation_id=self.operation_id,
                status=OperationStatus.COMPLETED,
                elements=self._split_elements,
                split_elements=self._split_elements,
                original_element=self._original_element,
                split_points=self.split_points.copy(),
                execution_time_ms=self.execution_time_ms
            )
            
        except Exception as e:
            self._end_execution(OperationStatus.FAILED)
            self.logger.error(f"Split execution failed: {str(e)}")
            return SplitResult(
                operation_id=self.operation_id,
                status=OperationStatus.FAILED,
                error_message=f"Execution error: {str(e)}",
                execution_time_ms=self.execution_time_ms
            )
    
    def preview(self) -> OperationResult:
        """Generate a preview of the split operation."""
        try:
            if self.validate():
                preview_elements = self._create_split_elements()
                return SplitResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.COMPLETED,
                    elements=preview_elements,
                    split_elements=preview_elements,
                    original_element=self.element,
                    split_points=self.split_points.copy(),
                    metadata={"preview": True}
                )
            else:
                return SplitResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Preview validation failed"
                )
        except Exception as e:
            return SplitResult(
                operation_id=self.operation_id,
                status=OperationStatus.FAILED,
                error_message=f"Preview error: {str(e)}"
            )
    
    def can_rollback(self) -> bool:
        """Check if the operation can be rolled back."""
        return (self.status == OperationStatus.COMPLETED and 
                self._original_element is not None and 
                len(self._split_elements) > 0)
    
    def rollback(self) -> bool:
        """Roll back the split operation."""
        if not self.can_rollback():
            return False
        
        try:
            # Restore original element
            self.element = self._original_element
            self._split_elements = []
            self.status = OperationStatus.PENDING
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False
    
    def _create_split_elements(self) -> List[Element]:
        """Create split elements from the original element."""
        if not self.element or not self.element.text:
            return []
        
        # Split text at specified points
        text_segments = self._split_text()
        
        if not text_segments:
            return []
        
        # Create elements for each segment
        split_elements = []
        for i, text_segment in enumerate(text_segments):
            if text_segment.strip():  # Only create non-empty elements
                split_element = self._create_split_element(text_segment, i, len(text_segments))
                split_elements.append(split_element)
        
        return split_elements
    
    def _split_text(self) -> List[str]:
        """Split text at specified points."""
        text = self.element.text
        segments = []
        
        # Split the text
        start = 0
        for point in self.split_points:
            if point > start:
                segments.append(text[start:point])
                start = point
        
        # Add remaining text
        if start < len(text):
            segments.append(text[start:])
        
        return segments
    
    def _create_split_element(self, text: str, index: int, total_segments: int) -> Element:
        """Create a split element from text segment."""
        # Generate new element ID
        split_id = str(uuid.uuid4())
        
        # Split metadata
        split_metadata = self._split_metadata(index, total_segments)
        
        # Create split element
        split_element = Element(
            element_id=split_id,
            element_type=self.element.element_type,
            text=text,
            metadata=split_metadata,
            parent_id=self.element.parent_id
        )
        
        return split_element
    
    def _split_metadata(self, index: int, total_segments: int) -> Optional[ElementMetadata]:
        """Split metadata for a segment."""
        if not self.element.metadata:
            return None
        
        original_meta = self.element.metadata
        
        # Split coordinates
        split_coords = self._split_coordinates(index, total_segments)
        
        # Adjust confidence (slightly lower for splits)
        confidence = original_meta.confidence
        if confidence is not None:
            confidence = confidence * 0.95  # Slight reduction due to splitting uncertainty
        
        return ElementMetadata(
            coordinates=split_coords,
            confidence=confidence,
            page_number=original_meta.page_number,
            detection_method=original_meta.detection_method
        )
    
    def _split_coordinates(self, index: int, total_segments: int) -> Optional[Coordinates]:
        """Split coordinates for a segment."""
        if not self.element.metadata or not self.element.metadata.coordinates:
            return None
        
        original_coords = self.element.metadata.coordinates
        
        if not original_coords.layout_bbox:
            return None
        
        # Calculate segment coordinates (assuming horizontal split)
        left, top, right, bottom = original_coords.layout_bbox
        width = right - left
        segment_width = width / total_segments
        
        segment_left = left + (segment_width * index)
        segment_right = segment_left + segment_width
        
        segment_bbox = [segment_left, top, segment_right, bottom]
        
        return Coordinates(
            layout_bbox=segment_bbox,
            coordinate_system=original_coords.coordinate_system or "pixel"
        )
    
    def find_optimal_split_points(self, target_segments: int = 2) -> List[int]:
        """Find optimal split points for dividing text."""
        if not self.element.text or target_segments <= 1:
            return []
        
        text = self.element.text
        
        # Find potential split points (sentence boundaries, paragraph breaks)
        potential_points = self._find_potential_split_points(text)
        
        if not potential_points:
            # Fall back to character-based splitting
            segment_length = len(text) // target_segments
            return [i * segment_length for i in range(1, target_segments)]
        
        # Select optimal points
        return self._select_optimal_points(potential_points, target_segments, len(text))
    
    def _find_potential_split_points(self, text: str) -> List[int]:
        """Find potential split points in text."""
        points = []
        
        # Sentence boundaries
        for match in re.finditer(r'[.!?]\s+[A-Z]', text):
            points.append(match.start() + 1)
        
        # Paragraph breaks
        for match in re.finditer(r'\n\s*\n', text):
            points.append(match.end())
        
        # Remove duplicates and sort
        return sorted(list(set(points)))
    
    def _select_optimal_points(self, potential_points: List[int], 
                              target_segments: int, text_length: int) -> List[int]:
        """Select optimal split points from potential points."""
        if len(potential_points) < target_segments - 1:
            return potential_points
        
        # Calculate ideal segment length
        ideal_segment_length = text_length / target_segments
        
        # Select points closest to ideal positions
        selected_points = []
        for i in range(1, target_segments):
            ideal_position = i * ideal_segment_length
            closest_point = min(potential_points, 
                               key=lambda p: abs(p - ideal_position))
            selected_points.append(closest_point)
            potential_points.remove(closest_point)
        
        return sorted(selected_points)