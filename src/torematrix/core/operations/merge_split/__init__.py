"""
Merge/Split Operations Module

This module provides core functionality for merging and splitting document elements,
including algorithms for coordinate processing, metadata management, and element manipulation.
"""

from .base_operation import BaseOperation, OperationResult, OperationStatus
from .merge import MergeOperation, MergeResult
from .split import SplitOperation, SplitResult
from .validation import OperationValidator, ValidationResult

__all__ = [
    # Base classes
    "BaseOperation",
    "OperationResult", 
    "OperationStatus",
    
    # Merge operations
    "MergeOperation",
    "MergeResult",
    
    # Split operations
    "SplitOperation", 
    "SplitResult",
    
    # Validation
    "OperationValidator",
    "ValidationResult",
]