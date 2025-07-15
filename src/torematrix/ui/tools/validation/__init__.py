"""
Manual validation tools for document processing.

This package provides tools for manual validation of document elements,
including drawing interfaces and element creation workflows.
"""

# Agent 1 - Core drawing state management (Issue #27)
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)

# Agent 1 - Area selection tools (Issue #26)
try:
    from .area_select import (
        ValidationAreaSelector,
        AreaSelectionMode,
        SelectionConstraint,
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

__all__ = [
    # Drawing system - Agent 1 (Issue #27)
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
]

# Add area selection tools if available (Issue #26)
if _area_tools_available:
    __all__.extend([
        # Area selection
        'ValidationAreaSelector',
        'AreaSelectionMode',
        'SelectionConstraint',
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