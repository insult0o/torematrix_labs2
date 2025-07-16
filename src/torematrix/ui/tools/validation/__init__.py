"""
Manual validation tools for document processing.

This package provides a comprehensive set of tools for manual validation
of document elements, including drawing interfaces, area selection,
hierarchy management, and element creation workflows.
"""

# Agent 1 - Drawing state management for manual validation (Issue #27)
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)

# Agent 1 - Area selection tools (Issue #26)
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

# Agent 2 - Interactive hierarchy tools (Issue #29.2)
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

# Agent 4 - Structure wizard and export system (Issue #245)
try:
    from .structure_wizard import (
        StructureWizard,
        StructureAnalyzer,
        StructureMethod,
        StructureResult,
        HeuristicWeights
    )
    from .export_system import (
        HierarchyExportWidget,
        ExportFormat,
        ExportOptions,
        ExportGenerator
    )
    _structure_wizard_available = True
except ImportError:
    _structure_wizard_available = False

__all__ = [
    # Drawing state management - Agent 1
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
    
    # Area selection tools - Agent 1
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
]

# Add hierarchy tools if available - Agent 2
if _hierarchy_tools_available:
    __all__.extend([
        # Hierarchy UI Tools - Agent 2 (Issue #29.2)
        'HierarchyTreeWidget',
        'HierarchyControlPanel', 
        'HierarchyMetricsWidget',
        'HierarchyToolsWidget',
        'HierarchyOperation',
        'ValidationLevel',
        'HierarchyMetrics'
    ])

# Add structure wizard and export tools if available - Agent 4
if _structure_wizard_available:
    __all__.extend([
        # Structure Wizard - Agent 4 (Issue #245)
        'StructureWizard',
        'StructureAnalyzer',
        'StructureMethod',
        'StructureResult',
        'HeuristicWeights',
        # Export System - Agent 4 (Issue #245)
        'HierarchyExportWidget',
        'ExportFormat',
        'ExportOptions',
        'ExportGenerator'
    ])