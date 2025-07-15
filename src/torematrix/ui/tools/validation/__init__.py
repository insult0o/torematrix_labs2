"""
Validation area selection tools for manual document correction.

This module provides specialized selection tools for the manual validation workflow,
allowing users to select areas in documents to create new elements or adjust boundaries.
"""

# Export public API
__all__ = [
    'ValidationAreaSelector',
    'AreaSelectionMode', 
    'SelectionConstraint'
]

from enum import Enum, auto

class AreaSelectionMode(Enum):
    """Modes for area selection during validation."""
    CREATE_NEW = auto()      # Create new element from selection
    ADJUST_BOUNDARY = auto() # Adjust existing element boundary
    EXCLUDE_AREA = auto()    # Mark area to exclude from processing
    MERGE_ELEMENTS = auto()  # Merge multiple elements
    SPLIT_ELEMENT = auto()   # Split element into multiple

class SelectionConstraint(Enum):
    """Constraints that can be applied to selections."""
    NONE = auto()
    ASPECT_RATIO = auto()
    FIXED_SIZE = auto()
    ALIGN_TO_GRID = auto()
    ALIGN_TO_ELEMENTS = auto()

class ValidationAreaSelector:
    """Main coordinator for area selection during manual validation."""
    
    def __init__(self, viewer, selection_manager, snapping_manager):
        self.viewer = viewer
        self.selection_manager = selection_manager
        self.snapping_manager = snapping_manager
        self.mode = AreaSelectionMode.CREATE_NEW
        
    def set_mode(self, mode):
        """Set the current selection mode."""
        self.mode = mode