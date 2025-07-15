"""
Manual validation tools for document processing.

This package provides tools for manual validation of document elements,
including drawing interfaces and element creation workflows.
"""

# Agent 1 - Core drawing state management
from .drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)

__all__ = [
    # Drawing system - Agent 1
    'DrawingStateManager',
    'DrawingMode',
    'DrawingState',
    'DrawingArea',
    'DrawingSession',
]