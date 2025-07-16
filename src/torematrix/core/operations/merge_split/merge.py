"""
Core Merge Operations

<<<<<<< HEAD
Implements the MergeOperation class with merge algorithm for combining document elements.
=======
Implements the MergeOperation class for combining document elements.
>>>>>>> origin/main
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
<<<<<<< HEAD
from datetime import datetime
=======
>>>>>>> origin/main
import uuid
import logging

from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates
from .base_operation import BaseOperation, OperationResult, OperationStatus

logger = logging.getLogger(__name__)


@dataclass
class MergeResult(OperationResult):
    """Result of merge operation."""
    merged_element: Optional[Element] = None
    original_elements: List[Element] = field(default_factory=list)
    
    @property
    def merged_successfully(self) -> bool:
        """Check if merge was successful."""
        return self.success and self.merged_element is not None


class MergeOperation(BaseOperation):
    """Core merge operation for combining multiple elements into one."""
    
    def __init__(self, elements: List[Element], operation_id: Optional[str] = None):
        super().__init__(operation_id)
        self.elements = elements or []
        self._merged_element: Optional[Element] = None
        self._original_elements: List[Element] = []
        self.logger = logging.getLogger(__name__ + ".MergeOperation")
    
    def validate(self) -> bool:
        """Validate merge operation parameters."""
        try:
            self.status = OperationStatus.VALIDATING
            
            # Basic validation
            if not self.elements:
                self.logger.error("No elements provided for merge")
                return False
            
            if len(self.elements) < 2:
                self.logger.error("At least 2 elements required for merge")
                return False
            
            # Check element types are compatible
            element_types = {elem.element_type for elem in self.elements}
            compatible_types = {"text", "paragraph", "title", "narrative_text"}
            
            if not element_types.issubset(compatible_types):
                self.logger.error(f"Incompatible element types: {element_types}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False
    
    def execute(self) -> OperationResult:
        """Execute the merge operation."""
        try:
            self._start_execution()
            
            # Store original elements for rollback
            self._original_elements = self.elements.copy()
            
            # Validate
            if not self.validate():
                self._end_execution(OperationStatus.FAILED)
                return MergeResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Validation failed",
                    execution_time_ms=self.execution_time_ms
                )
            
            # Perform the merge
            self._merged_element = self._create_merged_element()
            
            if self._merged_element is None:
                self._end_execution(OperationStatus.FAILED)
                return MergeResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Failed to create merged element",
                    execution_time_ms=self.execution_time_ms
                )
            
            # Complete execution
            self._end_execution(OperationStatus.COMPLETED)
            
            return MergeResult(
                operation_id=self.operation_id,
                status=OperationStatus.COMPLETED,
                elements=[self._merged_element],
                merged_element=self._merged_element,
                original_elements=self._original_elements,
                execution_time_ms=self.execution_time_ms
            )
            
        except Exception as e:
            self._end_execution(OperationStatus.FAILED)
            self.logger.error(f"Merge execution failed: {str(e)}")
            return MergeResult(
                operation_id=self.operation_id,
                status=OperationStatus.FAILED,
                error_message=f"Execution error: {str(e)}",
                execution_time_ms=self.execution_time_ms
            )
    
    def preview(self) -> OperationResult:
        """Generate a preview of the merge operation."""
        try:
            if self.validate():
                preview_element = self._create_merged_element()
                return MergeResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.COMPLETED,
                    elements=[preview_element] if preview_element else [],
                    merged_element=preview_element,
                    original_elements=self.elements.copy(),
                    metadata={"preview": True}
                )
            else:
                return MergeResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    error_message="Preview validation failed"
                )
        except Exception as e:
            return MergeResult(
                operation_id=self.operation_id,
                status=OperationStatus.FAILED,
                error_message=f"Preview error: {str(e)}"
            )
    
    def can_rollback(self) -> bool:
        """Check if the operation can be rolled back."""
        return (self.status == OperationStatus.COMPLETED and 
                self._merged_element is not None and 
                len(self._original_elements) > 0)
    
    def rollback(self) -> bool:
        """Roll back the merge operation."""
        if not self.can_rollback():
            return False
        
        try:
            # Restore original elements
            self.elements = self._original_elements.copy()
            self._merged_element = None
            self.status = OperationStatus.PENDING
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False
    
    def _create_merged_element(self) -> Optional[Element]:
        """Create the merged element from input elements."""
        if not self.elements:
            return None
        
        # Generate new element ID
        merged_id = str(uuid.uuid4())
        
        # Merge text content with smart separators
        merged_text = self._merge_text_content()
        
        # Determine element type (use most common)
        merged_type = self._determine_merged_element_type()
        
        # Merge metadata
        merged_metadata = self._merge_metadata()
        
        # Determine parent ID
        parent_id = self._determine_parent_id()
        
        # Create merged element
        merged_element = Element(
            element_id=merged_id,
            element_type=merged_type,
            text=merged_text,
            metadata=merged_metadata,
            parent_id=parent_id
        )
        
        return merged_element
    
    def _merge_text_content(self) -> str:
        """Merge text content with smart separators."""
        texts = []
        
        for elem in self.elements:
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
        
        if not texts:
            return ""
        
        # Use smart separator logic
        result = texts[0]
        for i in range(1, len(texts)):
            separator = self._determine_separator(result, texts[i])
            result += separator + texts[i]
        
        return result
    
    def _determine_separator(self, prev_text: str, next_text: str) -> str:
        """Determine appropriate separator between text segments."""
        # If previous text ends with punctuation, use space
        if prev_text.endswith(('.', '!', '?', ':')):
            return " "
        
        # If next text starts with punctuation, no separator
        if next_text.startswith(('.', '!', '?', ',', ':', ';')):
            return ""
        
        # Default to space
        return " "
    
    def _determine_merged_element_type(self) -> str:
        """Determine element type for merged element."""
        # Count element types
        type_counts = {}
        for elem in self.elements:
            type_counts[elem.element_type] = type_counts.get(elem.element_type, 0) + 1
        
        # Return most common type
        return max(type_counts, key=type_counts.get)
    
    def _merge_metadata(self) -> Optional[ElementMetadata]:
        """Merge metadata from all elements."""
        metadata_list = [elem.metadata for elem in self.elements if elem.metadata]
        
        if not metadata_list:
            return None
        
        # Merge coordinates (bounding box union)
        merged_coords = self._merge_coordinates(metadata_list)
        
        # Use average confidence
        confidences = [meta.confidence for meta in metadata_list if meta.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        
        # Use first page number
        page_number = next((meta.page_number for meta in metadata_list if meta.page_number), None)
        
        # Use first detection method
        detection_method = next((meta.detection_method for meta in metadata_list if meta.detection_method), None)
        
        return ElementMetadata(
            coordinates=merged_coords,
            confidence=avg_confidence,
            page_number=page_number,
            detection_method=detection_method
        )
    
    def _merge_coordinates(self, metadata_list: List[ElementMetadata]) -> Optional[Coordinates]:
        """Merge coordinate information."""
        layout_bboxes = []
        
        for meta in metadata_list:
            if meta.coordinates and meta.coordinates.layout_bbox:
                layout_bboxes.append(meta.coordinates.layout_bbox)
        
        if not layout_bboxes:
            return None
        
        # Calculate bounding box union
        min_left = min(bbox[0] for bbox in layout_bboxes)
        min_top = min(bbox[1] for bbox in layout_bboxes)
        max_right = max(bbox[2] for bbox in layout_bboxes)
        max_bottom = max(bbox[3] for bbox in layout_bboxes)
        
        merged_bbox = [min_left, min_top, max_right, max_bottom]
        
        return Coordinates(
            layout_bbox=merged_bbox,
            coordinate_system="pixel"
        )
    
    def _determine_parent_id(self) -> Optional[str]:
        """Determine parent ID for merged element."""
        # Use parent ID of first element if all have same parent
        parent_ids = {elem.parent_id for elem in self.elements}
        
        if len(parent_ids) == 1:
            return list(parent_ids)[0]
        
        # If different parents, use None
        return None