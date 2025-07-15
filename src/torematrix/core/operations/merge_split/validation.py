"""
Validation Framework for Merge/Split Operations

Provides comprehensive validation for operation parameters, preconditions, and feasibility.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import logging

from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates
from torematrix.core.processing.metadata.algorithms.spatial import BoundingBox

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    level: ValidationLevel
    message: str
    code: str
    element_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error-level issue."""
        return self.level == ValidationLevel.ERROR


@dataclass
class ValidationResult:
    """Result of operation validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    
    def __post_init__(self):
        """Organize issues by level."""
        self.issues = [issue for issue in self.issues if issue.level == ValidationLevel.ERROR]
        self.warnings = [issue for issue in self.issues if issue.level == ValidationLevel.WARNING]
        self.info = [issue for issue in self.issues if issue.level == ValidationLevel.INFO]
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        if issue.level == ValidationLevel.ERROR:
            self.issues.append(issue)
            self.is_valid = False
        elif issue.level == ValidationLevel.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)
    
    def add_error(self, message: str, code: str, element_id: Optional[str] = None, 
                  details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error-level issue."""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            message=message,
            code=code,
            element_id=element_id,
            details=details or {}
        )
        self.add_issue(issue)
    
    def add_warning(self, message: str, code: str, element_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning-level issue."""
        issue = ValidationIssue(
            level=ValidationLevel.WARNING,
            message=message,
            code=code,
            element_id=element_id,
            details=details or {}
        )
        self.add_issue(issue)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return len(self.issues) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.has_errors:
            return "No errors found"
        
        return "; ".join([f"{issue.code}: {issue.message}" for issue in self.issues])


class OperationValidator:
    """Validator for merge/split operations."""
    
    # Compatible element types for merging
    MERGEABLE_TYPES = {
        "text", "title", "narrative_text", "paragraph", "header", "footer",
        "list_item", "table_cell", "caption", "footnote"
    }
    
    # Element types that can be split
    SPLITTABLE_TYPES = {
        "text", "narrative_text", "paragraph", "list_item", "table_cell"
    }
    
    # Minimum text length for splitting
    MIN_SPLIT_TEXT_LENGTH = 10
    
    # Maximum elements for merge operation
    MAX_MERGE_ELEMENTS = 50
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".OperationValidator")
    
    def validate_merge_operation(self, elements: List[Element]) -> ValidationResult:
        """
        Validate a merge operation.
        
        Args:
            elements: List of elements to merge
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Basic validation
        if not elements:
            result.add_error("No elements provided for merge", "MERGE_NO_ELEMENTS")
            return result
        
        if len(elements) < 2:
            result.add_error("At least 2 elements required for merge", "MERGE_INSUFFICIENT_ELEMENTS")
            return result
        
        if len(elements) > self.MAX_MERGE_ELEMENTS:
            result.add_error(
                f"Too many elements for merge (max: {self.MAX_MERGE_ELEMENTS})",
                "MERGE_TOO_MANY_ELEMENTS"
            )
            return result
        
        # Check for duplicate elements
        element_ids = [elem.element_id for elem in elements]
        if len(element_ids) != len(set(element_ids)):
            result.add_error("Duplicate elements in merge operation", "MERGE_DUPLICATE_ELEMENTS")
        
        # Validate element types
        self._validate_merge_compatibility(elements, result)
        
        # Validate coordinates
        self._validate_merge_coordinates(elements, result)
        
        # Validate content
        self._validate_merge_content(elements, result)
        
        # Validate spatial relationships
        self._validate_merge_spatial_relationships(elements, result)
        
        return result
    
    def validate_split_operation(self, element: Element, split_points: List[int]) -> ValidationResult:
        """
        Validate a split operation.
        
        Args:
            element: Element to split
            split_points: List of split positions
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Basic validation
        if not element:
            result.add_error("No element provided for split", "SPLIT_NO_ELEMENT")
            return result
        
        if not split_points:
            result.add_error("No split points provided", "SPLIT_NO_POINTS")
            return result
        
        # Validate element type
        if element.element_type not in self.SPLITTABLE_TYPES:
            result.add_error(
                f"Element type '{element.element_type}' cannot be split",
                "SPLIT_UNSUPPORTED_TYPE",
                element_id=element.element_id
            )
        
        # Validate text content
        if not element.text or len(element.text) < self.MIN_SPLIT_TEXT_LENGTH:
            result.add_error(
                f"Element text too short for splitting (min: {self.MIN_SPLIT_TEXT_LENGTH})",
                "SPLIT_TEXT_TOO_SHORT",
                element_id=element.element_id
            )
        
        # Validate split points
        self._validate_split_points(element, split_points, result)
        
        # Validate coordinates
        self._validate_split_coordinates(element, result)
        
        return result
    
    def _validate_merge_compatibility(self, elements: List[Element], result: ValidationResult) -> None:
        """Validate that elements are compatible for merging."""
        element_types = set(elem.element_type for elem in elements)
        
        # Check if all types are mergeable
        unmergeable_types = element_types - self.MERGEABLE_TYPES
        if unmergeable_types:
            result.add_error(
                f"Unmergeable element types: {list(unmergeable_types)}",
                "MERGE_INCOMPATIBLE_TYPES"
            )
        
        # Check if all elements have the same type (preferred)
        if len(element_types) > 1:
            result.add_warning(
                f"Merging different element types: {list(element_types)}",
                "MERGE_MIXED_TYPES"
            )
        
        # Check page consistency
        pages = set()
        for elem in elements:
            if elem.metadata and elem.metadata.page_number is not None:
                pages.add(elem.metadata.page_number)
        
        if len(pages) > 1:
            result.add_warning(
                f"Merging elements from different pages: {list(pages)}",
                "MERGE_CROSS_PAGE"
            )
    
    def _validate_merge_coordinates(self, elements: List[Element], result: ValidationResult) -> None:
        """Validate coordinates for merge operation."""
        elements_with_coords = [
            elem for elem in elements
            if elem.metadata and elem.metadata.coordinates
        ]
        
        if not elements_with_coords:
            result.add_warning("No coordinate information available", "MERGE_NO_COORDINATES")
            return
        
        # Check for valid bounding boxes
        for elem in elements_with_coords:
            coords = elem.metadata.coordinates
            if not coords.layout_bbox:
                result.add_warning(
                    f"Element {elem.element_id} has no layout bounding box",
                    "MERGE_NO_LAYOUT_BBOX",
                    element_id=elem.element_id
                )
    
    def _validate_merge_content(self, elements: List[Element], result: ValidationResult) -> None:
        """Validate content for merge operation."""
        for elem in elements:
            if not elem.text or elem.text.strip() == "":
                result.add_warning(
                    f"Element {elem.element_id} has no text content",
                    "MERGE_EMPTY_TEXT",
                    element_id=elem.element_id
                )
    
    def _validate_merge_spatial_relationships(self, elements: List[Element], result: ValidationResult) -> None:
        """Validate spatial relationships for merge operation."""
        elements_with_coords = [
            elem for elem in elements
            if elem.metadata and elem.metadata.coordinates and elem.metadata.coordinates.layout_bbox
        ]
        
        if len(elements_with_coords) < 2:
            return
        
        # Check if elements are spatially related (adjacent, overlapping, or contained)
        bboxes = []
        for elem in elements_with_coords:
            bbox_coords = elem.metadata.coordinates.layout_bbox
            bbox = BoundingBox(
                left=bbox_coords[0],
                top=bbox_coords[1],
                right=bbox_coords[2],
                bottom=bbox_coords[3]
            )
            bboxes.append((elem.element_id, bbox))
        
        # Check for spatial relationships
        has_relationship = False
        for i, (id1, bbox1) in enumerate(bboxes):
            for id2, bbox2 in bboxes[i+1:]:
                if (bbox1.intersects(bbox2) or 
                    bbox1.contains(bbox2) or 
                    bbox2.contains(bbox1) or
                    bbox1.is_adjacent_to(bbox2)):
                    has_relationship = True
                    break
            if has_relationship:
                break
        
        if not has_relationship:
            result.add_warning(
                "Elements do not appear to be spatially related",
                "MERGE_NO_SPATIAL_RELATIONSHIP"
            )
    
    def _validate_split_points(self, element: Element, split_points: List[int], 
                              result: ValidationResult) -> None:
        """Validate split points for split operation."""
        text_length = len(element.text) if element.text else 0
        
        # Check split points are within text bounds
        for i, point in enumerate(split_points):
            if point < 0 or point >= text_length:
                result.add_error(
                    f"Split point {i} ({point}) is out of bounds (0-{text_length})",
                    "SPLIT_POINT_OUT_OF_BOUNDS"
                )
        
        # Check split points are sorted
        if split_points != sorted(split_points):
            result.add_error(
                "Split points must be in ascending order",
                "SPLIT_POINTS_NOT_SORTED"
            )
        
        # Check for duplicate split points
        if len(split_points) != len(set(split_points)):
            result.add_error(
                "Duplicate split points found",
                "SPLIT_DUPLICATE_POINTS"
            )
        
        # Check minimum segment length
        prev_point = 0
        for i, point in enumerate(split_points):
            segment_length = point - prev_point
            if segment_length < 5:  # Minimum 5 characters per segment
                result.add_warning(
                    f"Split segment {i} is very short ({segment_length} chars)",
                    "SPLIT_SHORT_SEGMENT"
                )
            prev_point = point
        
        # Check final segment
        final_length = text_length - (split_points[-1] if split_points else 0)
        if final_length < 5:
            result.add_warning(
                f"Final split segment is very short ({final_length} chars)",
                "SPLIT_SHORT_FINAL_SEGMENT"
            )
    
    def _validate_split_coordinates(self, element: Element, result: ValidationResult) -> None:
        """Validate coordinates for split operation."""
        if not element.metadata or not element.metadata.coordinates:
            result.add_warning(
                "No coordinate information available for split",
                "SPLIT_NO_COORDINATES",
                element_id=element.element_id
            )
            return
        
        coords = element.metadata.coordinates
        if not coords.layout_bbox:
            result.add_warning(
                "No layout bounding box available for split",
                "SPLIT_NO_LAYOUT_BBOX",
                element_id=element.element_id
            )