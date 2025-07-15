"""
Merge/Split Algorithms Package

Algorithm implementations for merge and split operations.
"""

from .text_merging import MergeStrategy, TextMerger
from .metadata_merge import ConflictResolution, MetadataConflict, MetadataMergeEngine
from .text_splitting import SplitStrategy, TextSplitter

__all__ = [
    # Text merging
    "MergeStrategy",
    "TextMerger",
    
    # Metadata merging
    "ConflictResolution", 
    "MetadataConflict",
    "MetadataMergeEngine",
    
    # Text splitting
    "SplitStrategy",
    "TextSplitter",
]