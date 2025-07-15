"""
Merge/Split Operations UI Dialogs

Agent 2 implementation providing user interface components and dialogs
for merge/split operations with intuitive controls and preview capabilities.
"""

from .merge_dialog import MergeDialog, MergeDialogResult
from .split_dialog import SplitDialog, SplitDialogResult
from .components.element_preview import ElementPreview
from .components.metadata_resolver import MetadataConflictResolver
from .components.operation_preview import OperationPreview
from .components.validation_ui import ValidationWarnings

__all__ = [
    # Main dialogs
    "MergeDialog",
    "MergeDialogResult",
    "SplitDialog", 
    "SplitDialogResult",
    
    # UI components
    "ElementPreview",
    "MetadataConflictResolver",
    "OperationPreview",
    "ValidationWarnings",
]