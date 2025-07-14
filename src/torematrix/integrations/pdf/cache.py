"""
Intelligent Caching System for PDF.js Performance Optimization.

This module provides advanced caching strategies including LRU cache,
page prefetching, and quality-based caching for optimal PDF performance.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import zlib
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class CacheQuality(Enum):
    """Cache quality levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"


class CacheType(Enum):
    """Cache entry types."""
    PAGE_RENDER = "page_render"
    PAGE_TEXT = "page_text"
    PAGE_METADATA = "page_metadata"
    THUMBNAIL = "thumbnail"
    SEARCH_INDEX = "search_index"


@dataclass
class CacheEntry:
    """Cache entry data structure."""
    key: str
    data: Any
    size_bytes: int
    cache_type: CacheType
    quality: CacheQuality
    access_count: int = 0
    last_access: float = 0
    creation_time: float = 0
    compression_ratio: float = 1.0
    
    def __post_init__(self):
        if self.last_access == 0:
            self.last_access = time.time()
        if self.creation_time == 0:
            self.creation_time = time.time()


class LRUCache:
    """
    LRU (Least Recently Used) cache implementation with size-based eviction.
    
    Provides efficient caching with automatic eviction based on access patterns
    and memory constraints.
    """
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size = 0
        self.lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_evictions': 0,
            'count_evictions': 0,
            'compressions': 0,
            'decompressions': 0
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get an entry from the cache."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                entry.access_count += 1
                entry.last_access = time.time()
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                
                self.stats['hits'] += 1
                return entry
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, data: Any, cache_type: CacheType, 
            quality: CacheQuality = CacheQuality.MEDIUM, 
            compress: bool = False) -> bool:
        """Put an entry into the cache."""
        with self.lock:
            # Calculate size
            size_bytes = self._calculate_size(data)
            
            # Compress if requested and beneficial
            compression_ratio = 1.0
            if compress and size_bytes > 1024:  # Only compress if > 1KB
                compressed_data = self._compress_data(data)
                if len(compressed_data) < size_bytes * 0.8:  # 20% compression minimum
                    data = compressed_data
                    compression_ratio = size_bytes / len(compressed_data)
                    size_bytes = len(compressed_data)
                    self.stats['compressions'] += 1
            
            # Create entry
            entry = CacheEntry(
                key=key,
                data=data,
                size_bytes=size_bytes,
                cache_type=cache_type,
                quality=quality,
                compression_ratio=compression_ratio
            )
            
            # Check if we need to evict
            if key in self.cache:
                # Update existing entry
                old_entry = self.cache[key]
                self.current_size -= old_entry.size_bytes
            
            # Evict if necessary
            self._evict_if_necessary(size_bytes)
            
            # Add new entry
            self.cache[key] = entry
            self.current_size += size_bytes
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove an entry from the cache."""
        with self.lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.current_size -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self.lock:
            self.cache.clear()
            self.current_size = 0
    
    def _evict_if_necessary(self, new_entry_size: int) -> None:
        """Evict entries if necessary to make room for new entry."""
        # Check size constraint
        while (self.current_size + new_entry_size > self.max_size_bytes and 
               len(self.cache) > 0):
            self._evict_lru()
            self.stats['size_evictions'] += 1
        
        # Check count constraint
        while len(self.cache) >= self.max_entries:
            self._evict_lru()
            self.stats['count_evictions'] += 1
    
    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self.cache:
            key, entry = self.cache.popitem(last=False)  # Remove first (oldest)
            self.current_size -= entry.size_bytes
            self.stats['evictions'] += 1
    
    def _calculate_size(self, data: Any) -> int:
        """Calculate the size of data in bytes."""
        if isinstance(data, (str, bytes)):
            return len(data)
        elif isinstance(data, dict):
            return len(json.dumps(data).encode('utf-8'))
        elif hasattr(data, '__sizeof__'):
            return data.__sizeof__()
        else:
            return len(str(data).encode('utf-8'))
    
    def _compress_data(self, data: Any) -> bytes:
        """Compress data using zlib."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, bytes):
            data = json.dumps(data).encode('utf-8')
        
        return zlib.compress(data, level=6)
    
    def _decompress_data(self, compressed_data: bytes) -> bytes:
        """Decompress data using zlib."""
        self.stats['decompressions'] += 1
        return zlib.decompress(compressed_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_accesses = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / max(1, total_accesses)
            
            return {
                'entries': len(self.cache),
                'size_bytes': self.current_size,
                'size_mb': self.current_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'utilization': self.current_size / self.max_size_bytes,
                'hit_rate': hit_rate,
                'total_accesses': total_accesses,
                **self.stats
            }
    
    def get_entries_by_type(self, cache_type: CacheType) -> List[CacheEntry]:
        """Get all entries of a specific type."""
        with self.lock:
            return [entry for entry in self.cache.values() if entry.cache_type == cache_type]
    
    def evict_by_type(self, cache_type: CacheType) -> int:
        """Evict all entries of a specific type."""
        with self.lock:
            keys_to_remove = [
                key for key, entry in self.cache.items() 
                if entry.cache_type == cache_type
            ]
            
            for key in keys_to_remove:
                self.remove(key)
            
            return len(keys_to_remove)
    
    def evict_by_quality(self, quality: CacheQuality) -> int:
        """Evict all entries of a specific quality."""
        with self.lock:
            keys_to_remove = [
                key for key, entry in self.cache.items() 
                if entry.quality == quality
            ]
            
            for key in keys_to_remove:
                self.remove(key)
            
            return len(keys_to_remove)


class PrefetchManager:
    """
    Intelligent prefetching system for PDF pages.
    
    Predicts which pages to load next based on user behavior
    and document structure.
    """
    
    def __init__(self, max_prefetch_pages: int = 5):
        self.max_prefetch_pages = max_prefetch_pages
        self.access_patterns: Dict[int, List[int]] = defaultdict(list)
        self.page_weights: Dict[int, float] = defaultdict(float)
        self.prefetch_queue: List[int] = []
        self.lock = threading.Lock()
        
        # Learning parameters
        self.pattern_window = 10  # Number of recent accesses to consider
        self.decay_factor = 0.9   # Weight decay for old patterns
    
    def record_access(self, page_number: int) -> None:
        """Record a page access for pattern learning."""
        with self.lock:
            # Update access patterns
            if len(self.access_patterns[page_number]) >= self.pattern_window:
                self.access_patterns[page_number].pop(0)
            self.access_patterns[page_number].append(int(time.time()))
            
            # Update page weights
            self.page_weights[page_number] = self.page_weights[page_number] * self.decay_factor + 1.0
            
            # Update prefetch queue
            self._update_prefetch_queue(page_number)
    
    def _update_prefetch_queue(self, current_page: int) -> None:
        """Update the prefetch queue based on current page."""
        candidates = []
        
        # Sequential prefetch (most common pattern)
        for i in range(1, self.max_prefetch_pages + 1):
            candidates.append((current_page + i, 1.0))
        
        # Reverse sequential (less common but useful)
        if current_page > 1:
            candidates.append((current_page - 1, 0.3))
        
        # Pattern-based prefetch
        for page, accesses in self.access_patterns.items():
            if page != current_page and len(accesses) >= 2:
                # Calculate access frequency
                recent_accesses = [a for a in accesses if time.time() - a < 300]  # 5 minutes
                if recent_accesses:
                    frequency = len(recent_accesses) / 300.0
                    candidates.append((page, frequency * 0.5))
        
        # Sort by score and take top candidates
        candidates.sort(key=lambda x: x[1], reverse=True)
        self.prefetch_queue = [page for page, _ in candidates[:self.max_prefetch_pages]]
    
    def get_prefetch_queue(self) -> List[int]:
        """Get the current prefetch queue."""
        with self.lock:
            return self.prefetch_queue.copy()
    
    def update_max_prefetch_pages(self, max_pages: int) -> None:
        """Update the maximum number of prefetch pages."""
        with self.lock:
            self.max_prefetch_pages = max_pages
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get prefetch statistics."""
        with self.lock:
            return {
                'tracked_pages': len(self.access_patterns),
                'prefetch_queue_size': len(self.prefetch_queue),
                'max_prefetch_pages': self.max_prefetch_pages,
                'total_page_weights': sum(self.page_weights.values()),
                'average_page_weight': sum(self.page_weights.values()) / max(1, len(self.page_weights))
            }


class MemoryCache(QObject):
    """
    High-level memory cache for PDF resources.
    
    Integrates LRU cache with intelligent prefetching and quality management.
    """
    
    # Signals
    cache_hit = pyqtSignal(str, str)  # key, cache_type
    cache_miss = pyqtSignal(str, str)  # key, cache_type
    cache_eviction = pyqtSignal(str, str, int)  # key, cache_type, size_bytes
    prefetch_triggered = pyqtSignal(list)  # page_numbers
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Initialize cache
        self.cache = LRUCache(
            max_size_mb=config.cache_size_mb,
            max_entries=config.cache_size_mb * 10  # Rough estimate
        )
        
        # Initialize prefetch manager
        self.prefetch_manager = PrefetchManager(config.max_preload_pages)
        
        # Quality management
        self.quality_mode = CacheQuality.MEDIUM
        self.quality_thresholds = {
            CacheQuality.LOW: 0.5,
            CacheQuality.MEDIUM: 0.7,
            CacheQuality.HIGH: 0.9,
            CacheQuality.LOSSLESS: 1.0
        }
        
        # Cache warming
        self.warming_enabled = False
        self.warming_timer = QTimer()
        self.warming_timer.timeout.connect(self._perform_cache_warming)
    
    def get_page_render(self, page_number: int, quality: CacheQuality = None) -> Optional[Any]:
        """Get a cached page render."""
        if quality is None:
            quality = self.quality_mode
        
        key = f"page_render_{page_number}_{quality.value}"
        entry = self.cache.get(key)
        
        if entry:
            self.cache_hit.emit(key, CacheType.PAGE_RENDER.value)
            self.prefetch_manager.record_access(page_number)
            
            # Decompress if needed
            if entry.compression_ratio > 1.0:
                return self.cache._decompress_data(entry.data)
            return entry.data
        
        self.cache_miss.emit(key, CacheType.PAGE_RENDER.value)
        return None
    
    def put_page_render(self, page_number: int, data: Any, quality: CacheQuality = None) -> bool:
        """Cache a page render."""
        if quality is None:
            quality = self.quality_mode
        
        key = f"page_render_{page_number}_{quality.value}"
        
        # Use compression for page renders
        success = self.cache.put(key, data, CacheType.PAGE_RENDER, quality, compress=True)
        
        if success:
            self.prefetch_manager.record_access(page_number)
            self._trigger_prefetch(page_number)
        
        return success
    
    def get_page_text(self, page_number: int) -> Optional[str]:
        """Get cached page text."""
        key = f"page_text_{page_number}"
        entry = self.cache.get(key)
        
        if entry:
            self.cache_hit.emit(key, CacheType.PAGE_TEXT.value)
            return entry.data
        
        self.cache_miss.emit(key, CacheType.PAGE_TEXT.value)
        return None
    
    def put_page_text(self, page_number: int, text: str) -> bool:
        """Cache page text."""
        key = f"page_text_{page_number}"
        return self.cache.put(key, text, CacheType.PAGE_TEXT, CacheQuality.LOSSLESS, compress=True)
    
    def get_page_metadata(self, page_number: int) -> Optional[Dict[str, Any]]:
        """Get cached page metadata."""
        key = f"page_metadata_{page_number}"
        entry = self.cache.get(key)
        
        if entry:
            self.cache_hit.emit(key, CacheType.PAGE_METADATA.value)
            return entry.data
        
        self.cache_miss.emit(key, CacheType.PAGE_METADATA.value)
        return None
    
    def put_page_metadata(self, page_number: int, metadata: Dict[str, Any]) -> bool:
        """Cache page metadata."""
        key = f"page_metadata_{page_number}"
        return self.cache.put(key, metadata, CacheType.PAGE_METADATA, CacheQuality.LOSSLESS, compress=True)
    
    def get_thumbnail(self, page_number: int, size: Tuple[int, int]) -> Optional[Any]:
        """Get cached thumbnail."""
        key = f"thumbnail_{page_number}_{size[0]}x{size[1]}"
        entry = self.cache.get(key)
        
        if entry:
            self.cache_hit.emit(key, CacheType.THUMBNAIL.value)
            return entry.data
        
        self.cache_miss.emit(key, CacheType.THUMBNAIL.value)
        return None
    
    def put_thumbnail(self, page_number: int, size: Tuple[int, int], data: Any) -> bool:
        """Cache thumbnail."""
        key = f"thumbnail_{page_number}_{size[0]}x{size[1]}"
        return self.cache.put(key, data, CacheType.THUMBNAIL, CacheQuality.MEDIUM, compress=True)
    
    def _trigger_prefetch(self, current_page: int) -> None:
        """Trigger prefetch for upcoming pages."""
        if not self.config.enable_lazy_loading:
            return
        
        prefetch_pages = self.prefetch_manager.get_prefetch_queue()
        if prefetch_pages:
            self.prefetch_triggered.emit(prefetch_pages)
    
    def _perform_cache_warming(self) -> None:
        """Perform cache warming operations."""
        # This would be implemented to pre-load commonly accessed pages
        pass
    
    def set_quality_mode(self, quality: CacheQuality) -> None:
        """Set the cache quality mode."""
        self.quality_mode = quality
        
        # If reducing quality, evict higher quality entries
        if quality in [CacheQuality.LOW, CacheQuality.MEDIUM]:
            self.cache.evict_by_quality(CacheQuality.HIGH)
            self.cache.evict_by_quality(CacheQuality.LOSSLESS)
    
    def clear_cache(self, ratio: float = 1.0) -> None:
        """Clear cache entries."""
        if ratio >= 1.0:
            self.cache.clear()
        else:
            # Clear a portion of the cache (oldest entries first)
            entries_to_remove = int(len(self.cache.cache) * ratio)
            keys_to_remove = list(self.cache.cache.keys())[:entries_to_remove]
            
            for key in keys_to_remove:
                self.cache.remove(key)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_stats = self.cache.get_statistics()
        prefetch_stats = self.prefetch_manager.get_statistics()
        
        return {
            'cache': cache_stats,
            'prefetch': prefetch_stats,
            'quality_mode': self.quality_mode.value,
            'warming_enabled': self.warming_enabled
        }
    
    def update_config(self, config) -> None:
        """Update cache configuration."""
        self.config = config
        self.prefetch_manager.update_max_prefetch_pages(config.max_preload_pages)
        
        # Update cache size if needed
        if config.cache_size_mb != self.cache.max_size_bytes / (1024 * 1024):
            self.cache.max_size_bytes = config.cache_size_mb * 1024 * 1024
            self.cache.max_entries = config.cache_size_mb * 10
    
    def cleanup(self) -> None:
        """Clean up cache resources."""
        self.warming_timer.stop()
        self.cache.clear()


class CacheManager:
    """
    High-level cache manager that orchestrates all caching operations.
    """
    
    def __init__(self, config):
        self.config = config
        self.memory_cache = MemoryCache(config)
        self.is_running = False
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'prefetch_requests': 0,
            'evictions': 0
        }
        
        # Connect signals
        self.memory_cache.cache_hit.connect(self._on_cache_hit)
        self.memory_cache.cache_miss.connect(self._on_cache_miss)
        self.memory_cache.cache_eviction.connect(self._on_cache_eviction)
        self.memory_cache.prefetch_triggered.connect(self._on_prefetch_triggered)
    
    def start(self) -> None:
        """Start cache manager."""
        self.is_running = True
    
    def stop(self) -> None:
        """Stop cache manager."""
        self.is_running = False
    
    def _on_cache_hit(self, key: str, cache_type: str) -> None:
        """Handle cache hit signal."""
        self.stats['cache_hits'] += 1
        self.stats['total_requests'] += 1
    
    def _on_cache_miss(self, key: str, cache_type: str) -> None:
        """Handle cache miss signal."""
        self.stats['cache_misses'] += 1
        self.stats['total_requests'] += 1
    
    def _on_cache_eviction(self, key: str, cache_type: str, size_bytes: int) -> None:
        """Handle cache eviction signal."""
        self.stats['evictions'] += 1
    
    def _on_prefetch_triggered(self, page_numbers: List[int]) -> None:
        """Handle prefetch trigger signal."""
        self.stats['prefetch_requests'] += len(page_numbers)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.get_statistics()
        
        total_requests = max(1, self.stats['total_requests'])
        hit_rate = self.stats['cache_hits'] / total_requests
        
        return {
            'hit_rate': hit_rate,
            'total_requests': self.stats['total_requests'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'prefetch_requests': self.stats['prefetch_requests'],
            'evictions': self.stats['evictions'],
            'memory_cache': memory_stats,
            'is_running': self.is_running
        }
    
    def set_quality_mode(self, quality: str) -> None:
        """Set cache quality mode."""
        quality_enum = CacheQuality(quality)
        self.memory_cache.set_quality_mode(quality_enum)
    
    def clear_cache(self, ratio: float = 1.0) -> None:
        """Clear cache."""
        self.memory_cache.clear_cache(ratio)
    
    def update_config(self, config) -> None:
        """Update cache configuration."""
        self.config = config
        self.memory_cache.update_config(config)
    
    def cleanup(self) -> None:
        """Clean up cache manager."""
        self.memory_cache.cleanup()