"""
Interactive Features for Element Tree View

This package provides advanced interaction capabilities for the hierarchical element list,
including drag-and-drop, multi-selection, context menus, search/filtering, custom rendering,
keyboard navigation, and visual feedback.

Main Components:
- DragDropHandler: Comprehensive drag-and-drop with visual feedback and validation
- MultiSelectionHandler: Advanced selection with keyboard modifiers and range selection
- ContextMenuManager: Dynamic context menus with element-specific actions
- SearchFilterManager: Real-time search and filtering with multiple criteria
- RichElementDelegate: Custom delegates with rich rendering capabilities
- KeyboardNavigationHandler: Full keyboard navigation and shortcuts
- VisualFeedbackManager: Animations, transitions, and visual effects
"""

from .drag_drop import (
    DragDropHandler, DragDropValidator, DropIndicator, 
    DragDropMimeData
)
from .selection import (
    MultiSelectionHandler, SelectionTracker, SelectionRange
)
from .context_menu import (
    ContextMenuManager, MenuAction, MenuSection, 
    ActionFilter, ContextMenuBuilder
)
from .search_filter import (
    SearchFilterManager, SearchBar, SearchCriteria,
    ElementFilterProxyModel, SearchHighlighter, SearchNavigator
)
from .custom_delegates import (
    RichElementDelegate, MinimalElementDelegate, CompactElementDelegate,
    ElementColors, ConfidenceIndicator, ElementTypeIcon
)
from .keyboard_navigation import (
    KeyboardNavigationHandler, NavigationCommand, NavigationState,
    TypeAheadSearch, TreeNavigator
)
from .visual_feedback import (
    VisualFeedbackManager, AnimationConfig, HighlightEffect,
    PulseEffect, FlashEffect, LoadingIndicator, ProgressIndicator,
    TooltipAnimation
)

__all__ = [
    # Drag and Drop
    'DragDropHandler',
    'DragDropValidator', 
    'DropIndicator',
    'DragDropMimeData',
    
    # Selection
    'MultiSelectionHandler',
    'SelectionTracker',
    'SelectionRange',
    
    # Context Menus
    'ContextMenuManager',
    'MenuAction',
    'MenuSection',
    'ActionFilter',
    'ContextMenuBuilder',
    
    # Search and Filter
    'SearchFilterManager',
    'SearchBar',
    'SearchCriteria',
    'ElementFilterProxyModel',
    'SearchHighlighter',
    'SearchNavigator',
    
    # Custom Delegates
    'RichElementDelegate',
    'MinimalElementDelegate',
    'CompactElementDelegate',
    'ElementColors',
    'ConfidenceIndicator',
    'ElementTypeIcon',
    
    # Keyboard Navigation
    'KeyboardNavigationHandler',
    'NavigationCommand',
    'NavigationState',
    'TypeAheadSearch',
    'TreeNavigator',
    
    # Visual Feedback
    'VisualFeedbackManager',
    'AnimationConfig',
    'HighlightEffect',
    'PulseEffect',
    'FlashEffect',
    'LoadingIndicator',
    'ProgressIndicator',
    'TooltipAnimation'
]