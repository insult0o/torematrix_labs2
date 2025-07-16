"""
UI Resources for merge/split operations.

This package provides styling and icon resources for the merge/split
UI components with comprehensive theming support.
"""

from .styles import merge_split_styles
from .icons import get_icon, IconType

__all__ = [
    'merge_split_styles',
    'get_icon', 
    'IconType'
]