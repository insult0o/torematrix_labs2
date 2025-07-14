"""
Selection Tools for Document Viewer Overlay.

This module provides various selection tools for document element selection
including pointer, rectangle, lasso, and element-aware selection tools.
"""

from .base import SelectionTool, ToolState, SelectionResult
from .pointer import PointerTool
from .rectangle import RectangleTool
from .lasso import LassoTool
from .element_aware import ElementAwareTool
from .multi_select import MultiSelectTool
from .animations import ToolAnimationManager
from .preview import SelectionPreview
from .actions import SelectionActions
from .shortcuts import ToolShortcuts
from .feedback import VisualFeedback

__all__ = [
    'SelectionTool',
    'ToolState',
    'SelectionResult',
    'PointerTool',
    'RectangleTool',
    'LassoTool',
    'ElementAwareTool',
    'MultiSelectTool',
    'ToolAnimationManager',
    'SelectionPreview',
    'SelectionActions',
    'ToolShortcuts',
    'VisualFeedback',
]