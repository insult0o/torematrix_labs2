"""
Selection Tools for Document Viewer Overlay.

This module provides various selection tools for document element selection
including pointer, rectangle, lasso, and element-aware selection tools with
comprehensive infrastructure for state management, events, and geometry.
"""

# Core infrastructure
from .base import SelectionTool, ToolState, SelectionResult, ToolRegistry
from .geometry import SelectionGeometry, HitTesting
from .state import ToolStateManager, MultiToolStateManager, StateTransition, StateSnapshot
from .cursor import CursorManager, CursorType, CursorTheme, CursorStack, get_global_cursor_manager
from .events import (
    EventType, EventPriority, ToolEvent, MouseEvent, KeyEvent, WheelEvent,
    StateEvent, SelectionEvent, OperationEvent, CustomEvent, EventFilter,
    EventHandler, EventDispatcher, EventRecorder, get_global_event_dispatcher,
    create_mouse_event, create_key_event, create_state_event, create_selection_event
)
from .registry import (
    AdvancedToolRegistry, ToolMetadata, ToolInstance, ToolFactory, ToolCategory,
    ToolCapability, get_global_tool_registry
)

# Tool implementations (if they exist)
try:
    from .pointer import PointerTool
except ImportError:
    PointerTool = None

try:
    from .rectangle import RectangleTool
except ImportError:
    RectangleTool = None

try:
    from .lasso import LassoTool
except ImportError:
    LassoTool = None

try:
    from .element_aware import ElementAwareTool
except ImportError:
    ElementAwareTool = None

try:
    from .multi_select import MultiSelectTool
except ImportError:
    MultiSelectTool = None

# Additional components (if they exist)
try:
    from .animations import ToolAnimationManager
except ImportError:
    ToolAnimationManager = None

try:
    from .preview import SelectionPreview
except ImportError:
    SelectionPreview = None

try:
    from .actions import SelectionActions
except ImportError:
    SelectionActions = None

try:
    from .shortcuts import ToolShortcuts
except ImportError:
    ToolShortcuts = None

try:
    from .feedback import VisualFeedback
except ImportError:
    VisualFeedback = None

# Core exports (always available)
__all__ = [
    # Base classes and types
    'SelectionTool',
    'ToolState',
    'SelectionResult',
    'ToolRegistry',
    
    # Geometry and hit testing
    'SelectionGeometry',
    'HitTesting',
    
    # State management
    'ToolStateManager',
    'MultiToolStateManager',
    'StateTransition',
    'StateSnapshot',
    
    # Cursor management
    'CursorManager',
    'CursorType',
    'CursorTheme',
    'CursorStack',
    'get_global_cursor_manager',
    
    # Event system
    'EventType',
    'EventPriority',
    'ToolEvent',
    'MouseEvent',
    'KeyEvent',
    'WheelEvent',
    'StateEvent',
    'SelectionEvent',
    'OperationEvent',
    'CustomEvent',
    'EventFilter',
    'EventHandler',
    'EventDispatcher',
    'EventRecorder',
    'get_global_event_dispatcher',
    'create_mouse_event',
    'create_key_event',
    'create_state_event',
    'create_selection_event',
    
    # Advanced registry
    'AdvancedToolRegistry',
    'ToolMetadata',
    'ToolInstance',
    'ToolFactory',
    'ToolCategory',
    'ToolCapability',
    'get_global_tool_registry',
]

# Add tool implementations if available
if PointerTool is not None:
    __all__.append('PointerTool')

if RectangleTool is not None:
    __all__.append('RectangleTool')

if LassoTool is not None:
    __all__.append('LassoTool')

if ElementAwareTool is not None:
    __all__.append('ElementAwareTool')

if MultiSelectTool is not None:
    __all__.append('MultiSelectTool')

if ToolAnimationManager is not None:
    __all__.append('ToolAnimationManager')

if SelectionPreview is not None:
    __all__.append('SelectionPreview')

if SelectionActions is not None:
    __all__.append('SelectionActions')

if ToolShortcuts is not None:
    __all__.append('ToolShortcuts')

if VisualFeedback is not None:
    __all__.append('VisualFeedback')