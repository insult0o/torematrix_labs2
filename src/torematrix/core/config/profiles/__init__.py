"""
Configuration profiles and inheritance system.

This module provides profile management, environment-specific configurations,
and inheritance capabilities.
"""

from .manager import ProfileManager
from .resolver import ProfileResolver
from .inheritance import InheritanceResolver

__all__ = [
    'ProfileManager',
    'ProfileResolver',
    'InheritanceResolver'
]