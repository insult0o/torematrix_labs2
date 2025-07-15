"""
Manual validation tools for document processing.

This package provides tools for manual validation of document elements,
including drawing interfaces and element creation workflows.
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

# Agent 1 - Drawing state management for manual validation (Issue #27)
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

# Agent 2 - OCR service integration for manual validation (Issue #27)
try:
    from .ocr_service import (
        ValidationOCRService,
        ValidationOCRRequest,
        ValidationOCRResponse,
        OCRWorkerThread,
        OCREngine,
        OCRStatus,
        OCRValidationHelper
    )
    _ocr_available = True
except ImportError:
    _ocr_available = False

# Agent 1 + Agent 2 - Area selection tools (Issue #26)
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
    # Agent 2 - Advanced snapping algorithms
    from .snapping import (
        SnapEngine,
        SnapTarget,
        SnapResult,
        SnapType,
        SnapConfiguration,
        MagneticField,
        EdgeDetector,
    )
    _area_tools_available = True
except ImportError:
    _area_tools_available = False

__all__ = [
    # Basic validation tools
    'ValidationAreaSelector',
    'AreaSelectionMode',
    'SelectionConstraint',
]

# Add drawing state management if available (Issue #27)
if _drawing_available:
    __all__.extend([
        'DrawingStateManager',
        'DrawingMode',
        'DrawingState',
        'DrawingArea',
        'DrawingSession',
    ])

# Add OCR service integration if available (Issue #27)
if _ocr_available:
    __all__.extend([
        'ValidationOCRService',
        'ValidationOCRRequest',
        'ValidationOCRResponse',
        'OCRWorkerThread',
        'OCREngine',
        'OCRStatus',
        'OCRValidationHelper',
    ])

# Add area selection tools if available (Issue #26)
if _area_tools_available:
    __all__.extend([
        # Advanced area selection - Agent 1
        'AdvancedAreaSelector',
        'ValidationSelectionConfig',
        
        # Shape tools - Agent 1
        'SelectionShape',
        'RectangleShape',
        'PolygonShape', 
        'FreehandShape',
        'RectangleSelectionTool',
        'PolygonSelectionTool',
        'FreehandSelectionTool',
        
        # Snapping algorithms - Agent 2
        'SnapEngine',
        'SnapTarget',
        'SnapResult',
        'SnapType',
        'SnapConfiguration',
        'MagneticField',
        'EdgeDetector',
    ])
