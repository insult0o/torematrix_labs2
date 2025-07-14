"""
Element validation for mapped unstructured elements.

This module provides comprehensive validation for elements mapped
from unstructured.io to our unified element model.
"""

from dataclasses import dataclass
from typing import List
import logging

from torematrix.core.models.element import Element, ElementType

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of element validation with details."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self) -> bool:
        """Allow boolean evaluation based on validity."""
        return self.is_valid


class ElementValidator:
    """Validates mapped elements for completeness and correctness."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    def validate(self, element: Element) -> ValidationResult:
        """Validate a single element comprehensively."""
        errors = []
        warnings = []
        
        # Basic validation
        if not element.element_id:
            errors.append("Element has no ID")
        
        if not element.element_type:
            errors.append("Element has no type")
        
        # Content validation
        if element.element_type != ElementType.PAGE_BREAK:
            if not element.text or not element.text.strip():
                errors.append("Element has no text content")
        
        # Metadata validation
        if not element.metadata:
            warnings.append("Element has no metadata")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )