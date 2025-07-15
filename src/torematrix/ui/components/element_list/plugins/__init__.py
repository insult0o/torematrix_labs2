"""
Plugin Architecture for Hierarchical Element List

This package provides extension points and plugin management for
customizing element list behavior and adding new functionality.
"""

from .plugin_manager import ElementListPluginManager
from .extension_points import ElementListExtensionPoints

__all__ = [
    'ElementListPluginManager',
    'ElementListExtensionPoints'
]