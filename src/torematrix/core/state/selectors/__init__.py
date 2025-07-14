"""
Memoized selector system for efficient state access.

This module provides a reselect-inspired memoization system optimized for
high-performance state management with 10k+ elements.
"""

from .base import Selector, create_selector, ParametricSelector
from .factory import SelectorFactory
from .common import (
    get_document,
    get_elements,
    get_visible_elements,
    get_elements_by_type,
    get_element_count,
    get_validation_status
)

__all__ = [
    'Selector',
    'ParametricSelector', 
    'create_selector',
    'SelectorFactory',
    'get_document',
    'get_elements',
    'get_visible_elements',
    'get_elements_by_type',
    'get_element_count',
    'get_validation_status'
]