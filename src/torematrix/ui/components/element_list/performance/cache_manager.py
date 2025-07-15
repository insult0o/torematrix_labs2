"""
Cache Management System for Element Tree View

Provides intelligent caching strategies for optimal performance.
"""

from typing import Dict, List, Optional, Set, Any, Tuple, Callable, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import time
import hashlib
import weakref
import json
import pickle
import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import os

from ..models.tree_node import TreeNode


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"           # Least Recently Used
    LFU = "lfu"           # Least Frequently Used
    FIFO = "fifo"         # First In, First Out
    LIFO = "lifo"         # Last In, First Out
    PRIORITY = "priority"  # Priority-based
    ADAPTIVE = "adaptive"  # Adaptive strategy


class CacheType(Enum):
    """Types of cache entries."""
    ELEMENT_DATA = "element_data"
    RENDER_DATA = "render_data"
    LAYOUT_DATA = "layout_data"
    METRICS_DATA = "metrics_data"
    INDEX_DATA = "index_data"
    SEARCH_RESULTS = "search_results"
    FILTERED_DATA = "filtered_data"


@dataclass
class CacheEntry:
    """Represents a cache entry."""
    key: str
    data: Any
    cache_type: CacheType
    size_bytes: int
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    hit_count: int = 0
    priority: int = 0
    ttl: Optional[float] = None  # Time to live in seconds
    tags: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    
    def touch(self) -> None:
        """Mark as accessed."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def hit(self) -> None:
        """Mark as cache hit."""
        self.hit_count += 1
        self.touch()
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def age(self) -> float:
        """Get age in seconds."""
        return time.time() - self.created_at
    
    def time_since_access(self) -> float:
        """Get time since last access."""
        return time.time() - self.last_accessed


class LRUCache:
    """Least Recently Used cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self.lock:
            entry = self.cache.get(key)
            if entry:
                if entry.is_expired():
                    self.cache.pop(key)
                    return None
                
                entry.hit()
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return entry
            return None
    
    def put(self, entry: CacheEntry) -> bool:
        """Put entry in cache."""
        with self.lock:
            # Remove existing entry
            if entry.key in self.cache:
                self.cache.pop(entry.key)
            
            # Evict if necessary
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)  # Remove oldest
            
            self.cache[entry.key] = entry
            return True
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            return self.cache.pop(key, None) is not None
    
    def clear(self) -> None:
        """Clear all entries."""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Get cache size."""
        return len(self.cache)
    
    def keys(self) -> List[str]:
        """Get all keys."""
        with self.lock:
            return list(self.cache.keys())


class PriorityCache:
    """Priority-based cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.priority_groups: Dict[int, Set[str]] = defaultdict(set)
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self.lock:
            entry = self.cache.get(key)
            if entry:
                if entry.is_expired():
                    self._remove_entry(key)
                    return None
                
                entry.hit()
                return entry
            return None
    
    def put(self, entry: CacheEntry) -> bool:
        """Put entry in cache."""
        with self.lock:
            # Remove existing entry
            if entry.key in self.cache:
                self._remove_entry(entry.key)
            
            # Evict if necessary
            while len(self.cache) >= self.max_size:
                self._evict_lowest_priority()
            
            self.cache[entry.key] = entry
            self.priority_groups[entry.priority].add(entry.key)
            return True
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and update priority groups."""
        entry = self.cache.pop(key, None)
        if entry:
            self.priority_groups[entry.priority].discard(key)
    
    def _evict_lowest_priority(self) -> None:
        """Evict entry with lowest priority."""
        if not self.cache:
            return
        
        # Find lowest priority with entries
        min_priority = min(p for p, keys in self.priority_groups.items() if keys)
        priority_group = self.priority_groups[min_priority]
        
        if priority_group:
            # Remove oldest entry in this priority group
            entries_in_group = [(k, self.cache[k]) for k in priority_group]
            entries_in_group.sort(key=lambda x: x[1].created_at)
            
            if entries_in_group:
                key_to_remove = entries_in_group[0][0]
                self._remove_entry(key_to_remove)
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries."""
        with self.lock:
            self.cache.clear()
            self.priority_groups.clear()


class AdaptiveCache:
    """Adaptive cache that switches strategies based on usage patterns."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.lru_cache = LRUCache(max_size)
        self.priority_cache = PriorityCache(max_size)
        self.current_strategy = CacheStrategy.LRU
        
        # Performance tracking
        self.lru_hits = 0
        self.lru_misses = 0
        self.priority_hits = 0
        self.priority_misses = 0
        
        self.evaluation_interval = 1000  # Evaluate every 1000 operations
        self.operation_count = 0
        
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from current cache."""
        with self.lock:
            self.operation_count += 1
            
            if self.current_strategy == CacheStrategy.LRU:
                entry = self.lru_cache.get(key)
                if entry:
                    self.lru_hits += 1
                else:
                    self.lru_misses += 1
            else:
                entry = self.priority_cache.get(key)
                if entry:
                    self.priority_hits += 1
                else:
                    self.priority_misses += 1
            
            # Evaluate strategy periodically
            if self.operation_count % self.evaluation_interval == 0:
                self._evaluate_strategy()
            
            return entry
    
    def put(self, entry: CacheEntry) -> bool:
        """Put entry in current cache."""
        with self.lock:
            if self.current_strategy == CacheStrategy.LRU:
                return self.lru_cache.put(entry)
            else:
                return self.priority_cache.put(entry)
    
    def _evaluate_strategy(self) -> None:
        """Evaluate and possibly switch cache strategy."""
        lru_hit_rate = self.lru_hits / max(self.lru_hits + self.lru_misses, 1)
        priority_hit_rate = self.priority_hits / max(self.priority_hits + self.priority_misses, 1)
        
        # Switch to better performing strategy
        if self.current_strategy == CacheStrategy.LRU:
            if priority_hit_rate > lru_hit_rate + 0.05:  # 5% threshold
                self._switch_to_priority()
        else:
            if lru_hit_rate > priority_hit_rate + 0.05:
                self._switch_to_lru()
    
    def _switch_to_lru(self) -> None:
        """Switch to LRU strategy."""
        self.current_strategy = CacheStrategy.LRU
        # Could migrate entries here if needed
    
    def _switch_to_priority(self) -> None:
        """Switch to priority strategy."""
        self.current_strategy = CacheStrategy.PRIORITY
        # Could migrate entries here if needed


class CacheIndex:
    """Maintains indexes for fast cache lookups."""
    
    def __init__(self):
        self.by_type: Dict[CacheType, Set[str]] = defaultdict(set)
        self.by_tag: Dict[str, Set[str]] = defaultdict(set)
        self.by_dependency: Dict[str, Set[str]] = defaultdict(set)
        self.lock = threading.RLock()
    
    def add_entry(self, entry: CacheEntry) -> None:
        """Add entry to indexes."""
        with self.lock:
            self.by_type[entry.cache_type].add(entry.key)
            
            for tag in entry.tags:
                self.by_tag[tag].add(entry.key)
            
            for dep in entry.dependencies:
                self.by_dependency[dep].add(entry.key)
    
    def remove_entry(self, entry: CacheEntry) -> None:
        """Remove entry from indexes."""
        with self.lock:
            self.by_type[entry.cache_type].discard(entry.key)
            
            for tag in entry.tags:
                self.by_tag[tag].discard(entry.key)
            
            for dep in entry.dependencies:
                self.by_dependency[dep].discard(entry.key)
    
    def find_by_type(self, cache_type: CacheType) -> Set[str]:
        """Find entries by type."""
        return self.by_type[cache_type].copy()
    
    def find_by_tag(self, tag: str) -> Set[str]:
        """Find entries by tag."""
        return self.by_tag[tag].copy()
    
    def find_by_dependency(self, dependency: str) -> Set[str]:
        """Find entries by dependency."""
        return self.by_dependency[dependency].copy()
    
    def clear(self) -> None:
        """Clear all indexes."""
        with self.lock:
            self.by_type.clear()
            self.by_tag.clear()
            self.by_dependency.clear()


class PersistentCache:
    """Persistent cache that survives application restarts."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
        self.lock = threading.RLock()
    
    def ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def save_entry(self, entry: CacheEntry) -> bool:
        """Save entry to disk."""
        try:
            with self.lock:
                cache_file = os.path.join(self.cache_dir, f"{entry.key}.cache")
                
                # Create serializable data
                cache_data = {
                    'key': entry.key,
                    'cache_type': entry.cache_type.value,
                    'size_bytes': entry.size_bytes,
                    'created_at': entry.created_at,
                    'last_accessed': entry.last_accessed,
                    'access_count': entry.access_count,
                    'hit_count': entry.hit_count,
                    'priority': entry.priority,
                    'ttl': entry.ttl,
                    'tags': list(entry.tags),
                    'dependencies': list(entry.dependencies)
                }
                
                # Save metadata
                with open(cache_file + '.meta', 'w') as f:
                    json.dump(cache_data, f)
                
                # Save data
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry.data, f)
                
                return True
        except Exception:
            return False
    
    def load_entry(self, key: str) -> Optional[CacheEntry]:
        """Load entry from disk."""
        try:
            with self.lock:
                cache_file = os.path.join(self.cache_dir, f"{key}.cache")
                meta_file = cache_file + '.meta'
                
                if not os.path.exists(cache_file) or not os.path.exists(meta_file):
                    return None
                
                # Load metadata
                with open(meta_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Load data
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                # Create entry
                entry = CacheEntry(
                    key=cache_data['key'],
                    data=data,
                    cache_type=CacheType(cache_data['cache_type']),
                    size_bytes=cache_data['size_bytes'],
                    created_at=cache_data['created_at'],
                    last_accessed=cache_data['last_accessed'],
                    access_count=cache_data['access_count'],
                    hit_count=cache_data['hit_count'],
                    priority=cache_data['priority'],
                    ttl=cache_data.get('ttl'),
                    tags=set(cache_data.get('tags', [])),
                    dependencies=set(cache_data.get('dependencies', []))
                )
                
                return entry
        except Exception:
            return None
    
    def remove_entry(self, key: str) -> bool:
        """Remove entry from disk."""
        try:
            with self.lock:
                cache_file = os.path.join(self.cache_dir, f"{key}.cache")
                meta_file = cache_file + '.meta'
                
                success = True
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                
                return success
        except Exception:
            return False


class CacheManager(QObject):
    """Main cache management system."""
    
    # Signals
    cacheHit = pyqtSignal(str, str)  # key, cache_type
    cacheMiss = pyqtSignal(str, str)  # key, cache_type
    cacheEvicted = pyqtSignal(str, str)  # key, cache_type
    cacheCleared = pyqtSignal(str)  # cache_type
    cacheStatisticsUpdated = pyqtSignal(dict)  # statistics
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 enable_persistence: bool = False, cache_dir: str = ".cache", parent=None):
        super().__init__(parent)
        
        self.max_size = max_size
        self.strategy = strategy
        self.enable_persistence = enable_persistence
        
        # Initialize cache implementation
        if strategy == CacheStrategy.LRU:
            self.cache = LRUCache(max_size)
        elif strategy == CacheStrategy.PRIORITY:
            self.cache = PriorityCache(max_size)
        elif strategy == CacheStrategy.ADAPTIVE:
            self.cache = AdaptiveCache(max_size)
        else:
            self.cache = LRUCache(max_size)  # Default
        
        # Components
        self.index = CacheIndex()
        self.persistent_cache = PersistentCache(cache_dir) if enable_persistence else None
        
        # Statistics
        self.statistics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'hit_rate': 0.0,
            'total_size_bytes': 0,
            'entries_by_type': defaultdict(int)
        }
        
        # Configuration
        self.auto_cleanup_enabled = True
        self.cleanup_interval = 30000  # 30 seconds
        self.max_entry_age = 3600  # 1 hour
        
        # Timers
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_expired)
        if self.auto_cleanup_enabled:
            self.cleanup_timer.start(self.cleanup_interval)
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_statistics)
        self.stats_timer.start(5000)  # Update stats every 5 seconds
    
    def get(self, key: str, cache_type: CacheType = None) -> Optional[Any]:
        """Get data from cache."""
        self.statistics['total_requests'] += 1
        
        entry = self.cache.get(key)
        if entry:
            self.statistics['hits'] += 1
            self.cacheHit.emit(key, entry.cache_type.value)
            return entry.data
        else:
            self.statistics['misses'] += 1
            cache_type_str = cache_type.value if cache_type else "unknown"
            self.cacheMiss.emit(key, cache_type_str)
            
            # Try persistent cache
            if self.persistent_cache:
                entry = self.persistent_cache.load_entry(key)
                if entry and not entry.is_expired():
                    # Put back in memory cache
                    self.cache.put(entry)
                    self.index.add_entry(entry)
                    return entry.data
            
            return None
    
    def put(self, key: str, data: Any, cache_type: CacheType = CacheType.ELEMENT_DATA,
            size_hint: int = None, priority: int = 0, ttl: float = None,
            tags: Set[str] = None, dependencies: Set[str] = None) -> bool:
        """Put data in cache."""
        if size_hint is None:
            size_hint = self._estimate_size(data)
        
        entry = CacheEntry(
            key=key,
            data=data,
            cache_type=cache_type,
            size_bytes=size_hint,
            priority=priority,
            ttl=ttl,
            tags=tags or set(),
            dependencies=dependencies or set()
        )
        
        # Add to memory cache
        success = self.cache.put(entry)
        if success:
            self.index.add_entry(entry)
            self.statistics['entries_by_type'][cache_type.value] += 1
            self.statistics['total_size_bytes'] += size_hint
            
            # Save to persistent cache
            if self.persistent_cache:
                self.persistent_cache.save_entry(entry)
        
        return success
    
    def remove(self, key: str) -> bool:
        """Remove data from cache."""
        entry = self.cache.get(key)
        if entry:
            self.index.remove_entry(entry)
            self.statistics['entries_by_type'][entry.cache_type.value] -= 1
            self.statistics['total_size_bytes'] -= entry.size_bytes
            
            success = self.cache.remove(key)
            if success:
                self.cacheEvicted.emit(key, entry.cache_type.value)
                
                # Remove from persistent cache
                if self.persistent_cache:
                    self.persistent_cache.remove_entry(key)
            
            return success
        return False
    
    def invalidate_by_type(self, cache_type: CacheType) -> int:
        """Invalidate all entries of a specific type."""
        keys_to_remove = self.index.find_by_type(cache_type)
        removed_count = 0
        
        for key in keys_to_remove:
            if self.remove(key):
                removed_count += 1
        
        if removed_count > 0:
            self.cacheCleared.emit(cache_type.value)
        
        return removed_count
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        keys_to_remove = self.index.find_by_tag(tag)
        removed_count = 0
        
        for key in keys_to_remove:
            if self.remove(key):
                removed_count += 1
        
        return removed_count
    
    def invalidate_by_dependency(self, dependency: str) -> int:
        """Invalidate all entries with a specific dependency."""
        keys_to_remove = self.index.find_by_dependency(dependency)
        removed_count = 0
        
        for key in keys_to_remove:
            if self.remove(key):
                removed_count += 1
        
        return removed_count
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.index.clear()
        
        # Reset statistics
        self.statistics['entries_by_type'].clear()
        self.statistics['total_size_bytes'] = 0
        
        self.cacheCleared.emit("all")
    
    def preload_data(self, key: str, data_provider: Callable[[], Any],
                    cache_type: CacheType = CacheType.ELEMENT_DATA,
                    priority: int = 0) -> None:
        """Preload data into cache."""
        if not self.get(key):  # Only preload if not already cached
            try:
                data = data_provider()
                self.put(key, data, cache_type, priority=priority)
            except Exception:
                pass  # Ignore preload failures
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data object."""
        try:
            import sys
            return sys.getsizeof(data)
        except:
            return 1024  # Default estimate
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries."""
        if hasattr(self.cache, 'cache'):
            # For caches that expose their internal cache dict
            cache_dict = self.cache.cache if hasattr(self.cache, 'cache') else {}
            expired_keys = []
            
            for key, entry in cache_dict.items():
                if entry.is_expired() or entry.age() > self.max_entry_age:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)
    
    def _update_statistics(self) -> None:
        """Update cache statistics."""
        total_requests = self.statistics['total_requests']
        if total_requests > 0:
            self.statistics['hit_rate'] = self.statistics['hits'] / total_requests
        
        self.cacheStatisticsUpdated.emit(self.statistics.copy())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        cache_stats = {
            'memory_cache_size': self.cache.size() if hasattr(self.cache, 'size') else 0,
            'max_size': self.max_size,
            'strategy': self.strategy.value,
            'persistence_enabled': self.enable_persistence
        }
        
        return {**self.statistics, **cache_stats}
    
    def configure_cache(self, **kwargs) -> None:
        """Configure cache parameters."""
        if 'auto_cleanup_enabled' in kwargs:
            self.auto_cleanup_enabled = kwargs['auto_cleanup_enabled']
            if self.auto_cleanup_enabled:
                self.cleanup_timer.start(self.cleanup_interval)
            else:
                self.cleanup_timer.stop()
        
        if 'cleanup_interval' in kwargs:
            self.cleanup_interval = kwargs['cleanup_interval']
            if self.auto_cleanup_enabled:
                self.cleanup_timer.start(self.cleanup_interval)
        
        if 'max_entry_age' in kwargs:
            self.max_entry_age = kwargs['max_entry_age']