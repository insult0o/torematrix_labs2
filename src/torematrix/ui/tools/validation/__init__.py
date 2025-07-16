"""
Manual validation tools for document processing.

<<<<<<< HEAD
This package provides tools for manual validation of document elements,
<<<<<<< HEAD
including drawing interfaces, area selection, and element creation workflows.
=======
including drawing interfaces and element creation workflows.
>>>>>>> origin/main
=======
This package provides a comprehensive set of tools for manual validation
of document elements, including drawing interfaces, area selection,
and element creation workflows.
>>>>>>> main
"""

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

<<<<<<< HEAD
<<<<<<< HEAD
# Agent 1 - Drawing state management (Issue #27/#238)
=======
# Core drawing system - Agent 1
>>>>>>> main
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)
<<<<<<< HEAD
=======
<<<<<<< HEAD
# Agent 1 - Core drawing state management (Issue #27)
=======
# Agent 1 - Drawing state management for manual validation (Issue #27)
>>>>>>> origin/main
try:
    from .drawing_state import (
        DrawingStateManager,
        DrawingMode,
        DrawingState,
        DrawingArea,
        DrawingSession
    )
    _drawing_available = True
except ImportError:
    _drawing_available = False
=======
>>>>>>> main

# Area selection tools (existing)
try:
    from .area_select import (
        ValidationAreaSelector as AdvancedAreaSelector,
        ValidationSelectionConfig,
    )
    from .shapes import (
        SelectionShape,
        RectangleShape,
        PolygonShape,
        FreehandShape,
        RectangleSelectionTool,
        PolygonSelectionTool,
        FreehandSelectionTool,
    )
    _area_tools_available = True
except ImportError:
    _area_tools_available = False
>>>>>>> origin/main

__all__ = [
    # Basic validation tools
    'ValidationAreaSelector',
    'AreaSelectionMode',
    'SelectionConstraint',
<<<<<<< HEAD
<<<<<<< HEAD
    # Drawing state management
=======
    # Drawing system - Agent 1
>>>>>>> main
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
<<<<<<< HEAD
]
=======
=======
>>>>>>> main
]

# Add area tools if available
if _area_tools_available:
    __all__.extend([
        # Advanced area selection
        'AdvancedAreaSelector',
        'ValidationSelectionConfig',
        
        # Shape tools
        'SelectionShape',
        'RectangleShape',
        'PolygonShape', 
        'FreehandShape',
        'RectangleSelectionTool',
        'PolygonSelectionTool',
        'FreehandSelectionTool',
    ])
>>>>>>> origin/main
