"""
Algorithms for Merge/Split Operations

Core algorithms for text merging, coordinate operations, metadata merging, and hierarchy operations.
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