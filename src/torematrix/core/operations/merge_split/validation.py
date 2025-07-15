"""
Operation Validation Framework

Provides comprehensive validation for merge/split operation parameters and preconditions.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of operation validation."""
    is_valid: bool
    issues: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, message: str, code: str = "VALIDATION_ERROR"):
        """Add an error message."""
        self.issues.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str, code: str = "VALIDATION_WARNING"):
        """Add a warning message."""
        self.warnings.append(message)
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.issues:
            return "No errors found"
        return "; ".join(self.issues)


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
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".OperationValidator")
    
    def validate_merge_operation(self, elements: List[Element]) -> ValidationResult:
        """Validate a merge operation."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation
        if not elements:
            result.add_error("No elements provided for merge")
            return result
        
        if len(elements) < 2:
            result.add_error("At least 2 elements required for merge")
            return result
        
        # Check element types
        element_types = {elem.element_type for elem in elements}
        if not element_types.issubset(self.MERGEABLE_TYPES):
            unmergeable = element_types - self.MERGEABLE_TYPES
            result.add_error(f"Unmergeable element types: {unmergeable}")
        
        # Check for mixed types
        if len(element_types) > 1:
            result.add_warning(f"Merging different element types: {element_types}")
        
        # Check text content
        empty_text_count = sum(1 for elem in elements if not elem.text or not elem.text.strip())
        if empty_text_count > 0:
            result.add_warning(f"{empty_text_count} elements have no text content")
        
        return result
    
    def validate_split_operation(self, element: Element, split_points: List[int]) -> ValidationResult:
        """Validate a split operation."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation
        if not element:
            result.add_error("No element provided for split")
            return result
        
        if not split_points:
            result.add_error("No split points provided")
            return result
        
        # Check element type
        if element.element_type not in self.SPLITTABLE_TYPES:
            result.add_error(f"Element type '{element.element_type}' cannot be split")
        
        # Check text content
        if not element.text or len(element.text) < 10:
            result.add_error("Element text too short for splitting")
        
        # Validate split points
        if element.text:
            text_length = len(element.text)
            for point in split_points:
                if point < 0 or point >= text_length:
                    result.add_error(f"Split point {point} is out of bounds (0-{text_length})")
        
        # Check split points are sorted
        if split_points != sorted(split_points):
            result.add_error("Split points must be in ascending order")
        
        return result