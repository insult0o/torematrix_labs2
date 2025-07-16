"""
Merge/Split Operations Module

Core functionality for merging and splitting document elements.
"""

from .base_operation import BaseOperation, OperationResult, OperationStatus
from .merge import MergeOperation, MergeResult
from .split import SplitOperation, SplitResult
from .validation import OperationValidator, ValidationResult

__all__ = [
    "BaseOperation",
    "OperationResult", 
    "OperationStatus",
    "MergeOperation",
    "MergeResult",
    "SplitOperation", 
    "SplitResult",
    "OperationValidator",
    "ValidationResult",
]