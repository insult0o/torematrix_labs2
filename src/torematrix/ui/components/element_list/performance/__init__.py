"""
<<<<<<< HEAD
Performance Optimization Components for Element Tree View

This package provides comprehensive performance optimization features for handling
large datasets efficiently, including virtual scrolling, lazy loading, memory
management, and intelligent caching.

Key Components:
- VirtualScrollingEngine: Handles viewport-based rendering for large datasets
- LazyLoadingManager: On-demand loading of tree branches
- MemoryManager: Intelligent memory optimization and cleanup
- CacheManager: Advanced caching with multiple strategies

Performance Features:
- Virtual scrolling for 10K+ elements
- Lazy loading with priority queuing
- Memory pressure detection and cleanup
- Multi-strategy caching (LRU, Priority, Adaptive)
- Render optimization and batching
- Scroll performance optimization
- Memory usage monitoring and profiling
"""

from .virtual_scrolling import (
    VirtualScrollingEngine, ViewportManager, ItemRenderer,
    ScrollMetrics, RenderBatch, VirtualItemInfo
)
from .lazy_loading import (
    LazyLoadingManager, LoadingState, LoadingQueue, LoadRequest,
    PlaceholderNode, LoadWorker
)
from .memory_manager import (
    MemoryManager, MemoryPool, NodeMemoryTracker, MemoryMonitor,
    MemoryPriority, MemoryEntry
)
from .cache_manager import (
    CacheManager, CacheEntry, CacheStrategy, CacheType,
    LRUCache, PriorityCache, AdaptiveCache, CacheIndex,
    PersistentCache
)
=======
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
>>>>>>> origin/main

__all__ = [
    # Virtual Scrolling
    'VirtualScrollingEngine',
    'ViewportManager',
    'ItemRenderer',
<<<<<<< HEAD
    'ScrollMetrics',
    'RenderBatch',
    'VirtualItemInfo',
    
    # Lazy Loading
    'LazyLoadingManager',
    'LoadingState',
    'LoadingQueue',
    'LoadRequest',
    'PlaceholderNode',
    'LoadWorker',
    
    # Memory Management
    'MemoryManager',
    'MemoryPool',
    'NodeMemoryTracker',
    'MemoryMonitor',
    'MemoryPriority',
    'MemoryEntry',
    
    # Cache Management
    'CacheManager',
    'CacheEntry',
    'CacheStrategy',
    'CacheType',
    'LRUCache',
    'PriorityCache',
    'AdaptiveCache',
    'CacheIndex',
    'PersistentCache'
=======
    
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
>>>>>>> origin/main
]