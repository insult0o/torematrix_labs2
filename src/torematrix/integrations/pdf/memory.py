"""
Memory Management System for PDF.js Performance Optimization.

This module provides intelligent memory management, including memory pools,
pressure detection, and automatic cleanup for optimal PDF handling.
"""
from __future__ import annotations

import gc
import os
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, OrderedDict
from enum import Enum

import psutil
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MemoryPressureLevel(Enum):
    """Memory pressure levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    cache_memory_mb: float
    pressure_level: MemoryPressureLevel
    gc_count: int
    leaked_objects: int
    
    @property
    def usage_percent(self) -> float:
        """Calculate memory usage percentage."""
        return (self.used_memory_mb / self.total_memory_mb) * 100 if self.total_memory_mb > 0 else 0


class MemoryPool:
    """
    Memory pool for efficient memory allocation and reuse.
    
    Manages memory blocks for PDF resources to reduce allocation overhead
    and improve performance for large documents.
    """
    
    def __init__(self, block_size: int = 1024 * 1024, max_blocks: int = 100):
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.available_blocks: List[bytearray] = []
        self.allocated_blocks: Dict[int, bytearray] = {}
        self.block_usage: Dict[int, float] = {}
        self.next_id = 0
        self.lock = threading.Lock()
        
        # Statistics
        self.allocations = 0
        self.deallocations = 0
        self.pool_hits = 0
        self.pool_misses = 0
    
    def allocate(self, size: int) -> Tuple[int, bytearray]:
        """Allocate a memory block."""
        with self.lock:
            self.allocations += 1
            
            # Check if we have a suitable block in the pool
            if self.available_blocks and size <= self.block_size:
                block = self.available_blocks.pop()
                block_id = self.next_id
                self.next_id += 1
                
                self.allocated_blocks[block_id] = block
                self.block_usage[block_id] = time.time()
                self.pool_hits += 1
                
                return block_id, block
            
            # Create new block
            if size > self.block_size:
                # Large allocation, create exact size
                block = bytearray(size)
            else:
                # Standard allocation
                block = bytearray(self.block_size)
            
            block_id = self.next_id
            self.next_id += 1
            
            self.allocated_blocks[block_id] = block
            self.block_usage[block_id] = time.time()
            self.pool_misses += 1
            
            return block_id, block
    
    def deallocate(self, block_id: int) -> bool:
        """Deallocate a memory block."""
        with self.lock:
            if block_id not in self.allocated_blocks:
                return False
            
            block = self.allocated_blocks.pop(block_id)
            self.block_usage.pop(block_id, None)
            self.deallocations += 1
            
            # Return to pool if it's standard size and we have room
            if len(block) == self.block_size and len(self.available_blocks) < self.max_blocks:
                # Clear the block
                block[:] = b'\x00' * len(block)
                self.available_blocks.append(block)
            
            return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory pool statistics."""
        with self.lock:
            return {
                'block_size': self.block_size,
                'max_blocks': self.max_blocks,
                'available_blocks': len(self.available_blocks),
                'allocated_blocks': len(self.allocated_blocks),
                'allocations': self.allocations,
                'deallocations': self.deallocations,
                'pool_hits': self.pool_hits,
                'pool_misses': self.pool_misses,
                'hit_rate': self.pool_hits / max(1, self.pool_hits + self.pool_misses)
            }
    
    def cleanup_old_blocks(self, max_age_seconds: float = 300) -> int:
        """Clean up old allocated blocks."""
        with self.lock:
            current_time = time.time()
            old_blocks = []
            
            for block_id, usage_time in self.block_usage.items():
                if current_time - usage_time > max_age_seconds:
                    old_blocks.append(block_id)
            
            cleaned = 0
            for block_id in old_blocks:
                if self.deallocate(block_id):
                    cleaned += 1
            
            return cleaned
    
    def clear_pool(self) -> None:
        """Clear the entire memory pool."""
        with self.lock:
            self.available_blocks.clear()
            self.allocated_blocks.clear()
            self.block_usage.clear()


class MemoryManager(QObject):
    """
    Advanced memory management system for PDF.js optimization.
    
    Provides intelligent memory monitoring, pressure detection,
    and automatic cleanup strategies for optimal performance.
    """
    
    # Signals
    memory_pressure_changed = pyqtSignal(MemoryPressureLevel)
    memory_stats_updated = pyqtSignal(MemoryStats)
    cleanup_performed = pyqtSignal(dict)  # cleanup_stats
    memory_leak_detected = pyqtSignal(dict)  # leak_info
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Memory monitoring
        self.process = psutil.Process()
        self.system_memory = psutil.virtual_memory()
        self.current_stats = MemoryStats(
            total_memory_mb=self.system_memory.total / (1024 * 1024),
            used_memory_mb=0,
            available_memory_mb=0,
            cache_memory_mb=0,
            pressure_level=MemoryPressureLevel.LOW,
            gc_count=0,
            leaked_objects=0
        )
        
        # Memory pools
        self.memory_pools: Dict[str, MemoryPool] = {
            'small': MemoryPool(block_size=64 * 1024, max_blocks=50),    # 64KB blocks
            'medium': MemoryPool(block_size=1024 * 1024, max_blocks=30),  # 1MB blocks
            'large': MemoryPool(block_size=4 * 1024 * 1024, max_blocks=10)  # 4MB blocks
        }
        
        # Page management
        self.page_cache: OrderedDict[int, Dict[str, Any]] = OrderedDict()
        self.page_access_times: Dict[int, float] = {}
        self.page_memory_usage: Dict[int, float] = {}
        
        # Leak detection
        self.object_tracker: Dict[str, Set[int]] = defaultdict(set)
        self.weak_references: Dict[int, weakref.ref] = {}
        
        # Cleanup scheduling
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._perform_scheduled_cleanup)
        self.last_cleanup = time.time()
        
        # Statistics
        self.cleanup_stats = {
            'total_cleanups': 0,
            'pages_cleaned': 0,
            'memory_freed_mb': 0,
            'gc_collections': 0
        }
        
        # Thresholds
        self.pressure_thresholds = {
            MemoryPressureLevel.MEDIUM: 0.6,
            MemoryPressureLevel.HIGH: 0.8,
            MemoryPressureLevel.CRITICAL: 0.9
        }
    
    def start(self) -> None:
        """Start memory management."""
        # Start cleanup timer (every 30 seconds)
        self.cleanup_timer.start(30000)
        
        # Initial memory check
        self._update_memory_stats()
    
    def stop(self) -> None:
        """Stop memory management."""
        self.cleanup_timer.stop()
    
    def _update_memory_stats(self) -> None:
        """Update memory statistics."""
        try:
            # Process memory info
            memory_info = self.process.memory_info()
            used_memory_mb = memory_info.rss / (1024 * 1024)
            
            # System memory info
            system_memory = psutil.virtual_memory()
            available_memory_mb = system_memory.available / (1024 * 1024)
            
            # Cache memory calculation
            cache_memory_mb = sum(
                len(self.page_cache) * 0.5,  # Estimate cache overhead
                *(pool.get_statistics()['allocated_blocks'] * pool.block_size / (1024 * 1024) 
                  for pool in self.memory_pools.values())
            )
            
            # Calculate pressure level
            usage_percent = used_memory_mb / self.current_stats.total_memory_mb
            pressure_level = self._calculate_pressure_level(usage_percent)
            
            # Update stats
            self.current_stats = MemoryStats(
                total_memory_mb=self.current_stats.total_memory_mb,
                used_memory_mb=used_memory_mb,
                available_memory_mb=available_memory_mb,
                cache_memory_mb=cache_memory_mb,
                pressure_level=pressure_level,
                gc_count=gc.get_count()[0],
                leaked_objects=self._count_leaked_objects()
            )
            
            # Emit signals
            self.memory_stats_updated.emit(self.current_stats)
            
            # Handle pressure changes
            if pressure_level != getattr(self, '_last_pressure_level', MemoryPressureLevel.LOW):
                self.memory_pressure_changed.emit(pressure_level)
                self._last_pressure_level = pressure_level
                
        except Exception as e:
            print(f"Memory stats update error: {e}")
    
    def _calculate_pressure_level(self, usage_percent: float) -> MemoryPressureLevel:
        """Calculate memory pressure level."""
        if usage_percent >= self.pressure_thresholds[MemoryPressureLevel.CRITICAL]:
            return MemoryPressureLevel.CRITICAL
        elif usage_percent >= self.pressure_thresholds[MemoryPressureLevel.HIGH]:
            return MemoryPressureLevel.HIGH
        elif usage_percent >= self.pressure_thresholds[MemoryPressureLevel.MEDIUM]:
            return MemoryPressureLevel.MEDIUM
        else:
            return MemoryPressureLevel.LOW
    
    def _count_leaked_objects(self) -> int:
        """Count potentially leaked objects."""
        leaked_count = 0
        current_time = time.time()
        
        # Check weak references
        for obj_id, weak_ref in list(self.weak_references.items()):
            if weak_ref() is None:
                # Object was garbage collected
                self.weak_references.pop(obj_id, None)
            elif current_time - self.page_access_times.get(obj_id, current_time) > 300:
                # Object hasn't been accessed in 5 minutes
                leaked_count += 1
        
        return leaked_count
    
    def allocate_page_memory(self, page_number: int, size: int) -> Optional[Tuple[int, bytearray]]:
        """Allocate memory for a PDF page."""
        # Choose appropriate pool
        pool_name = self._choose_memory_pool(size)
        pool = self.memory_pools[pool_name]
        
        try:
            block_id, block = pool.allocate(size)
            
            # Track page memory usage
            self.page_memory_usage[page_number] = size / (1024 * 1024)  # MB
            self.page_access_times[page_number] = time.time()
            
            # Create weak reference for leak detection
            self.weak_references[page_number] = weakref.ref(block)
            
            return block_id, block
            
        except Exception as e:
            print(f"Page memory allocation error: {e}")
            return None
    
    def deallocate_page_memory(self, page_number: int, block_id: int) -> bool:
        """Deallocate memory for a PDF page."""
        # Choose appropriate pool
        size = self.page_memory_usage.get(page_number, 0) * 1024 * 1024  # Convert to bytes
        pool_name = self._choose_memory_pool(int(size))
        pool = self.memory_pools[pool_name]
        
        try:
            success = pool.deallocate(block_id)
            
            if success:
                # Remove tracking
                self.page_memory_usage.pop(page_number, None)
                self.page_access_times.pop(page_number, None)
                self.weak_references.pop(page_number, None)
            
            return success
            
        except Exception as e:
            print(f"Page memory deallocation error: {e}")
            return False
    
    def _choose_memory_pool(self, size: int) -> str:
        """Choose appropriate memory pool based on size."""
        if size <= 64 * 1024:  # 64KB
            return 'small'
        elif size <= 1024 * 1024:  # 1MB
            return 'medium'
        else:
            return 'large'
    
    def add_page_to_cache(self, page_number: int, page_data: Dict[str, Any]) -> None:
        """Add a page to the memory cache."""
        self.page_cache[page_number] = page_data
        self.page_access_times[page_number] = time.time()
        
        # Check cache size limit
        max_cached_pages = self.config.cache_size_mb // 2  # Rough estimate
        if len(self.page_cache) > max_cached_pages:
            self._evict_old_pages(len(self.page_cache) - max_cached_pages)
    
    def get_page_from_cache(self, page_number: int) -> Optional[Dict[str, Any]]:
        """Get a page from the memory cache."""
        if page_number in self.page_cache:
            # Update access time
            self.page_access_times[page_number] = time.time()
            
            # Move to end (most recently used)
            page_data = self.page_cache.pop(page_number)
            self.page_cache[page_number] = page_data
            
            return page_data
        return None
    
    def remove_page_from_cache(self, page_number: int) -> bool:
        """Remove a page from the memory cache."""
        if page_number in self.page_cache:
            self.page_cache.pop(page_number)
            self.page_access_times.pop(page_number, None)
            return True
        return False
    
    def _evict_old_pages(self, count: int) -> None:
        """Evict old pages from cache using LRU strategy."""
        # Sort by access time (oldest first)
        sorted_pages = sorted(
            self.page_access_times.items(),
            key=lambda x: x[1]
        )
        
        evicted = 0
        for page_number, _ in sorted_pages:
            if evicted >= count:
                break
            
            if self.remove_page_from_cache(page_number):
                evicted += 1
    
    def cleanup_old_pages(self, max_age_seconds: float = 300) -> int:
        """Clean up old pages from cache."""
        current_time = time.time()
        old_pages = []
        
        for page_number, access_time in self.page_access_times.items():
            if current_time - access_time > max_age_seconds:
                old_pages.append(page_number)
        
        cleaned = 0
        for page_number in old_pages:
            if self.remove_page_from_cache(page_number):
                cleaned += 1
        
        return cleaned
    
    def emergency_cleanup(self) -> Dict[str, Any]:
        """Perform emergency memory cleanup."""
        cleanup_stats = {
            'pages_cleaned': 0,
            'memory_freed_mb': 0,
            'pool_blocks_freed': 0,
            'gc_collections': 0
        }
        
        # Clear half of the page cache
        pages_to_remove = len(self.page_cache) // 2
        if pages_to_remove > 0:
            # Remove oldest pages
            cleanup_stats['pages_cleaned'] = self._evict_old_pages(pages_to_remove)
        
        # Clean up memory pools
        for pool_name, pool in self.memory_pools.items():
            freed = pool.cleanup_old_blocks(max_age_seconds=60)  # More aggressive
            cleanup_stats['pool_blocks_freed'] += freed
        
        # Force garbage collection
        before_gc = gc.get_count()[0]
        gc.collect()
        after_gc = gc.get_count()[0]
        cleanup_stats['gc_collections'] = before_gc - after_gc
        
        # Update statistics
        self.cleanup_stats['total_cleanups'] += 1
        self.cleanup_stats['pages_cleaned'] += cleanup_stats['pages_cleaned']
        self.cleanup_stats['gc_collections'] += cleanup_stats['gc_collections']
        
        # Emit signal
        self.cleanup_performed.emit(cleanup_stats)
        
        return cleanup_stats
    
    def _perform_scheduled_cleanup(self) -> None:
        """Perform scheduled memory cleanup."""
        current_time = time.time()
        
        # Update memory stats
        self._update_memory_stats()
        
        # Perform cleanup based on pressure level
        if self.current_stats.pressure_level == MemoryPressureLevel.CRITICAL:
            self.emergency_cleanup()
        elif self.current_stats.pressure_level == MemoryPressureLevel.HIGH:
            self.cleanup_old_pages(max_age_seconds=180)  # 3 minutes
        elif self.current_stats.pressure_level == MemoryPressureLevel.MEDIUM:
            self.cleanup_old_pages(max_age_seconds=300)  # 5 minutes
        else:
            # Low pressure, just clean up very old pages
            self.cleanup_old_pages(max_age_seconds=600)  # 10 minutes
        
        # Clean up memory pools
        for pool in self.memory_pools.values():
            pool.cleanup_old_blocks()
        
        # Check for memory leaks
        leaked_objects = self._count_leaked_objects()
        if leaked_objects > 10:  # Threshold for leak detection
            self.memory_leak_detected.emit({
                'leaked_objects': leaked_objects,
                'total_tracked': len(self.weak_references),
                'timestamp': current_time
            })
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        self._update_memory_stats()
        return self.current_stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_pages': len(self.page_cache),
            'total_cache_memory_mb': sum(self.page_memory_usage.values()),
            'average_page_size_mb': sum(self.page_memory_usage.values()) / max(1, len(self.page_memory_usage)),
            'oldest_page_age': time.time() - min(self.page_access_times.values()) if self.page_access_times else 0,
            'newest_page_age': time.time() - max(self.page_access_times.values()) if self.page_access_times else 0
        }
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics."""
        return {
            pool_name: pool.get_statistics()
            for pool_name, pool in self.memory_pools.items()
        }
    
    def update_config(self, config) -> None:
        """Update memory management configuration."""
        self.config = config
        
        # Update pressure thresholds
        self.pressure_thresholds[MemoryPressureLevel.MEDIUM] = config.memory_pressure_threshold * 0.75
        self.pressure_thresholds[MemoryPressureLevel.HIGH] = config.memory_pressure_threshold
        self.pressure_thresholds[MemoryPressureLevel.CRITICAL] = config.memory_pressure_threshold * 1.125
    
    def cleanup(self) -> None:
        """Clean up memory manager resources."""
        self.stop()
        
        # Clear all caches
        self.page_cache.clear()
        self.page_access_times.clear()
        self.page_memory_usage.clear()
        self.weak_references.clear()
        
        # Clear memory pools
        for pool in self.memory_pools.values():
            pool.clear_pool()
        
        # Force garbage collection
        gc.collect()