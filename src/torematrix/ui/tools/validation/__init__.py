"""
Manual validation tools for document processing.

This package provides a comprehensive set of tools for manual validation
of document elements, including drawing interfaces, OCR integration,
and element creation wizards.
"""

# Core drawing system - Agent 1
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)

# Area selection tools (existing)
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
    # Drawing system - Agent 1
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
]

# Add area tools if available
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