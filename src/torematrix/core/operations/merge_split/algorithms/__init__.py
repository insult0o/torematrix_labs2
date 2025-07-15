"""
Algorithms for Merge/Split Operations

This module contains the core algorithms for processing elements, coordinates,
metadata, and hierarchical relationships in merge/split operations.
"""

from .text_merging import TextMerger
from .coordinate_ops import CoordinateProcessor
from .metadata_merge import MetadataMerger
from .hierarchy_ops import HierarchyProcessor

__all__ = [
    "TextMerger",
    "CoordinateProcessor", 
    "MetadataMerger",
    "HierarchyProcessor",
]