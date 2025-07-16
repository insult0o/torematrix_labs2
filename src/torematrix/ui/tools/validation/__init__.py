"""
Manual validation tools for document processing.

This package provides tools for manual validation of document elements,
including drawing interfaces and element creation workflows.
"""

# Agent 1 - Drawing state management for manual validation (Issue #27)
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)

# Agent 1 + Agent 2 - Area selection tools (Issue #26)
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

# Agent 2 - Merge/Split UI Components (Issue #235)
try:
    from .merge_dialog import MergeDialog
    from .split_dialog import SplitDialog
    from .components import (
        ElementPreview,
        MetadataConflictResolver,
        OperationPreview,
        ValidationWarnings
    )
    _merge_split_ui_available = True
except ImportError:
    _merge_split_ui_available = False

# Agent 2 - Interactive Hierarchy UI Tools (Issue #241)
try:
    from .hierarchy_tools import (
        HierarchyTreeWidget,
        HierarchyControlPanel,
        HierarchyMetricsWidget,
        HierarchyToolsWidget,
        HierarchyOperation,
        ValidationLevel,
        HierarchyMetrics
    )
    _hierarchy_tools_available = True
except ImportError:
    _hierarchy_tools_available = False

__all__ = [
    # Drawing state management - Agent 1 (Issue #27)
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
]

# Add area selection tools if available (Issue #26)
if _area_tools_available:
    __all__.extend([
        # Area selection - Agent 1
        'ValidationAreaSelector',
        'AreaSelectionMode',
        'SelectionConstraint',
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

# Add merge/split UI components if available - Agent 2 (Issue #235)
if _merge_split_ui_available:
    __all__.extend([
        # Merge/Split Dialogs - Agent 2
        'MergeDialog',
        'SplitDialog',
        
        # Common UI Components - Agent 2
        'ElementPreview',
        'MetadataConflictResolver',
        'OperationPreview',
        'ValidationWarnings',
    ])

# Add hierarchy UI tools if available - Agent 2 (Issue #241)
if _hierarchy_tools_available:
    __all__.extend([
        # Interactive Hierarchy UI Tools - Agent 2
        'HierarchyTreeWidget',
        'HierarchyControlPanel',
        'HierarchyMetricsWidget',
        'HierarchyToolsWidget',
        'HierarchyOperation',
        'ValidationLevel',
        'HierarchyMetrics',
    ])
