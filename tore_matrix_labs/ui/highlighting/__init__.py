"""
Advanced Highlighting System for TORE Matrix Labs

This module provides a comprehensive highlighting system with:
- Precise coordinate mapping between text and PDF
- Multi-box rendering for complex text layouts
- Real-time position tracking and synchronization
- Automated testing and validation
- Pure yellow color scheme for optimal readability
"""

from .highlighting_engine import HighlightingEngine
from .coordinate_mapper import CoordinateMapper
from .multi_box_renderer import MultiBoxRenderer
from .position_tracker import PositionTracker
from .highlight_style import HighlightStyle
from .test_harness import HighlightingTestHarness, TestCase, TestResult

__all__ = [
    'HighlightingEngine',
    'CoordinateMapper',
    'MultiBoxRenderer',
    'PositionTracker',
    'HighlightStyle',
    'HighlightingTestHarness',
    'TestCase',
    'TestResult'
]

__version__ = '1.0.0'
__author__ = 'TORE Matrix Labs'
__description__ = 'Advanced highlighting system with precise coordinate mapping and multi-box rendering'