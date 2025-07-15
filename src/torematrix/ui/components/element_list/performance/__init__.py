"""
Performance Optimization Module

This module provides performance optimizations for the hierarchical element list,
including virtual scrolling, lazy loading, memory management, and caching strategies.

Main Components:
- VirtualScrollingEngine: Efficient rendering of visible items only
- LazyLoadingManager: On-demand loading of tree branches
- MemoryManager: Efficient memory usage and cleanup
- CacheManager: Smart caching of rendered items and metadata
"""

from .virtual_scrolling import VirtualScrollingEngine, ViewportManager, ItemRenderer
from .lazy_loading import LazyLoadingManager, LoadingStrategy, BranchLoader
from .memory_manager import MemoryManager, ObjectPool, GarbageCollector
from .cache_manager import CacheManager, LRUCache, RenderCache

__all__ = [
    # Virtual Scrolling
    'VirtualScrollingEngine',
    'ViewportManager',
    'ItemRenderer',
    
    # Lazy Loading
    'LazyLoadingManager',
    'LoadingStrategy',
    'BranchLoader',
    
    # Memory Management
    'MemoryManager',
    'ObjectPool',
    'GarbageCollector',
    
    # Caching
    'CacheManager',
    'LRUCache',
    'RenderCache'
]