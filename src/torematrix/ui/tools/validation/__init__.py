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

# Agent 2 - OCR Service Integration (Issue #240)
try:
    from .ocr_service import (
        ValidationOCRService,
        OCRRequest,
        OCRResponse,
        OCRWorkerThread,
        OCREngine,
        OCRQualityAssessment,
        ImagePreprocessor
    )
    _ocr_service_available = True
except ImportError:
    _ocr_service_available = False

# Agent 3 - UI Components & User Experience (Issue #242)
try:
    from .wizard import (
        ValidationWizard,
        ValidationStep,
        StepStatus,
        WizardConfiguration
    )
    from .toolbar import (
        ValidationToolbar,
        ToolCategory,
        ToolConfiguration,
        ToolAction
    )
    from .ocr_dialog import (
        OCRDialog,
        OCRDialogConfiguration,
        OCRPreviewWidget,
        ConfidenceHighlighter
    )
    _ui_components_available = True
except ImportError:
    _ui_components_available = False

# Agent 4 - Integration & Testing (Issue #244)
try:
    from .integration import (
        ValidationToolsIntegration,
        ValidationMode,
        IntegrationStatus,
        ValidationSession,
        ValidationStatistics,
        create_validation_integration,
        get_integration_statistics
    )
    _integration_layer_available = True
except ImportError:
    _integration_layer_available = False

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

# Add OCR service components if available - Agent 2 (Issue #240)
if _ocr_service_available:
    __all__.extend([
        # OCR Service Integration - Agent 2
        'ValidationOCRService',
        'OCRRequest',
        'OCRResponse',
        'OCRWorkerThread',
        'OCREngine',
        'OCRQualityAssessment',
        'ImagePreprocessor',
    ])

# Add UI components if available - Agent 3 (Issue #242)
if _ui_components_available:
    __all__.extend([
        # Validation Wizard - Agent 3
        'ValidationWizard',
        'ValidationStep',
        'StepStatus',
        'WizardConfiguration',
        
        # Validation Toolbar - Agent 3
        'ValidationToolbar',
        'ToolCategory',
        'ToolConfiguration',
        'ToolAction',
        
        # OCR Dialog - Agent 3
        'OCRDialog',
        'OCRDialogConfiguration',
        'OCRPreviewWidget',
        'ConfidenceHighlighter',
    ])

# Add integration layer if available - Agent 4 (Issue #244)
if _integration_layer_available:
    __all__.extend([
        # Integration Layer - Agent 4
        'ValidationToolsIntegration',
        'ValidationMode',
        'IntegrationStatus',
        'ValidationSession',
        'ValidationStatistics',
        'create_validation_integration',
        'get_integration_statistics',
    ])
