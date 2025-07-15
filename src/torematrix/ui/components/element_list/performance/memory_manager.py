"""
Memory Management System for Element Tree View

Provides intelligent memory optimization and cleanup for large datasets.
"""

from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import weakref
import gc
import psutil
import time
import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum

from ..models.tree_node import TreeNode


class MemoryPriority(Enum):
    """Memory priority levels."""
    CRITICAL = 5    # Never evict
    HIGH = 4       # Evict only under severe pressure
    NORMAL = 3     # Standard eviction candidate
    LOW = 2        # Prefer to evict
    DISPOSABLE = 1 # Evict first


@dataclass
class MemoryEntry:
    """Represents a memory entry in the cache."""
    data: Any
    size_bytes: int
    last_accessed: float
    access_count: int = 0
    priority: MemoryPriority = MemoryPriority.NORMAL
    creation_time: float = field(default_factory=time.time)
    refs: int = 0
    
    def touch(self) -> None:
        """Mark as recently accessed."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def age(self) -> float:
        """Get age in seconds."""
        return time.time() - self.creation_time
    
    def time_since_access(self) -> float:
        """Get time since last access."""
        return time.time() - self.last_accessed


class MemoryPool:
    """Manages memory allocation and deallocation."""
    
    def __init__(self, max_size_mb: int = 100):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.entries: OrderedDict[str, MemoryEntry] = OrderedDict()
        self.size_by_priority: Dict[MemoryPriority, int] = defaultdict(int)
        self.lock = threading.RLock()
    
    def add(self, key: str, data: Any, size_bytes: int = None, 
            priority: MemoryPriority = MemoryPriority.NORMAL) -> bool:
        """Add data to memory pool."""
        if size_bytes is None:
            size_bytes = self._estimate_size(data)
        
        with self.lock:
            # Remove existing entry if present
            if key in self.entries:
                self.remove(key)
            
            # Check if we have space
            if self.current_size + size_bytes > self.max_size_bytes:
                if not self._make_space(size_bytes):
                    return False  # Couldn't make enough space
            
            # Add entry
            entry = MemoryEntry(
                data=data,
                size_bytes=size_bytes,
                last_accessed=time.time(),
                priority=priority
            )
            
            self.entries[key] = entry
            self.current_size += size_bytes
            self.size_by_priority[priority] += size_bytes
            
            return True
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from memory pool."""
        with self.lock:
            entry = self.entries.get(key)
            if entry:
                entry.touch()
                # Move to end (most recently used)
                self.entries.move_to_end(key)
                return entry.data
            return None
    
    def remove(self, key: str) -> bool:
        """Remove data from memory pool."""
        with self.lock:
            entry = self.entries.pop(key, None)
            if entry:
                self.current_size -= entry.size_bytes
                self.size_by_priority[entry.priority] -= entry.size_bytes
                return True
            return False
    
    def _make_space(self, needed_bytes: int) -> bool:
        """Make space by evicting entries."""
        with self.lock:
            # Try to evict by priority order
            for priority in [MemoryPriority.DISPOSABLE, MemoryPriority.LOW, 
                           MemoryPriority.NORMAL, MemoryPriority.HIGH]:
                
                if self.current_size + needed_bytes <= self.max_size_bytes:
                    return True
                
                # Evict entries of this priority (oldest first)
                to_remove = []
                for key, entry in self.entries.items():
                    if entry.priority == priority:
                        to_remove.append(key)
                
                # Sort by last accessed time (oldest first)
                to_remove.sort(key=lambda k: self.entries[k].last_accessed)
                
                for key in to_remove:
                    self.remove(key)
                    if self.current_size + needed_bytes <= self.max_size_bytes:
                        return True
            
            # If still no space, evict HIGH priority items
            if self.current_size + needed_bytes > self.max_size_bytes:
                for key in list(self.entries.keys()):
                    entry = self.entries[key]
                    if entry.priority != MemoryPriority.CRITICAL:
                        self.remove(key)
                        if self.current_size + needed_bytes <= self.max_size_bytes:
                            return True
            
            return self.current_size + needed_bytes <= self.max_size_bytes
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data object."""
        try:
            import sys
            return sys.getsizeof(data)
        except:
            return 1024  # Default estimate
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self.lock:
            return {
                'total_size_mb': self.current_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'usage_percent': (self.current_size / self.max_size_bytes) * 100,
                'entry_count': len(self.entries),
                'size_by_priority': {
                    priority.name: size / (1024 * 1024) 
                    for priority, size in self.size_by_priority.items()
                }
            }
    
    def clear(self) -> None:
        """Clear all entries."""
        with self.lock:
            self.entries.clear()
            self.current_size = 0
            self.size_by_priority.clear()


class NodeMemoryTracker:
    """Tracks memory usage of tree nodes."""
    
    def __init__(self):
        self.node_sizes: Dict[str, int] = {}
        self.node_refs: Dict[str, int] = {}
        self.node_children: Dict[str, Set[str]] = defaultdict(set)
        self.total_tracked = 0
    
    def track_node(self, node_id: str, size_bytes: int, parent_id: str = None) -> None:
        """Track memory usage of a node."""
        old_size = self.node_sizes.get(node_id, 0)
        self.node_sizes[node_id] = size_bytes
        self.total_tracked += size_bytes - old_size
        
        if parent_id:
            self.node_children[parent_id].add(node_id)
    
    def untrack_node(self, node_id: str) -> None:
        """Stop tracking a node."""
        size = self.node_sizes.pop(node_id, 0)
        self.total_tracked -= size
        self.node_refs.pop(node_id, None)
        
        # Remove from parent's children
        for children in self.node_children.values():
            children.discard(node_id)
        
        # Remove as parent
        self.node_children.pop(node_id, None)
    
    def add_reference(self, node_id: str) -> None:
        """Add reference to node."""
        self.node_refs[node_id] = self.node_refs.get(node_id, 0) + 1
    
    def remove_reference(self, node_id: str) -> None:
        """Remove reference from node."""
        if node_id in self.node_refs:
            self.node_refs[node_id] -= 1
            if self.node_refs[node_id] <= 0:
                self.node_refs.pop(node_id)
    
    def get_reference_count(self, node_id: str) -> int:
        """Get reference count for node."""
        return self.node_refs.get(node_id, 0)
    
    def get_node_size(self, node_id: str) -> int:
        """Get size of node."""
        return self.node_sizes.get(node_id, 0)
    
    def get_subtree_size(self, node_id: str) -> int:
        """Get total size of node and its subtree."""
        total = self.get_node_size(node_id)
        for child_id in self.node_children.get(node_id, set()):
            total += self.get_subtree_size(child_id)
        return total
    
    def get_unreferenced_nodes(self) -> List[str]:
        """Get nodes with no references."""
        return [node_id for node_id in self.node_sizes.keys() 
                if self.get_reference_count(node_id) == 0]


class MemoryMonitor:
    """Monitors system and application memory usage."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = self.get_memory_info()
        self.peak_memory = self.baseline_memory
        self.memory_history: List[Tuple[float, Dict[str, float]]] = []
        self.max_history = 100
    
    def get_memory_info(self) -> Dict[str, float]:
        """Get current memory information."""
        try:
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'percent': self.process.memory_percent(),
                'system_available_mb': system_memory.available / (1024 * 1024),
                'system_percent': system_memory.percent
            }
        except:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 
                   'system_available_mb': 0, 'system_percent': 0}
    
    def update(self) -> Dict[str, float]:
        """Update memory monitoring."""
        current_memory = self.get_memory_info()
        
        # Update peak
        if current_memory['rss_mb'] > self.peak_memory['rss_mb']:
            self.peak_memory = current_memory
        
        # Add to history
        self.memory_history.append((time.time(), current_memory))
        if len(self.memory_history) > self.max_history:
            self.memory_history.pop(0)
        
        return current_memory
    
    def get_memory_growth(self) -> float:
        """Get memory growth since baseline."""
        current = self.get_memory_info()
        return current['rss_mb'] - self.baseline_memory['rss_mb']
    
    def is_memory_pressure(self, threshold_percent: float = 80.0) -> bool:
        """Check if under memory pressure."""
        current = self.get_memory_info()
        return current['system_percent'] > threshold_percent
    
    def get_memory_trend(self, window_minutes: int = 5) -> float:
        """Get memory trend over time window."""
        if len(self.memory_history) < 2:
            return 0.0
        
        cutoff_time = time.time() - (window_minutes * 60)
        recent_history = [(t, m) for t, m in self.memory_history if t >= cutoff_time]
        
        if len(recent_history) < 2:
            return 0.0
        
        # Calculate trend (MB per minute)
        start_memory = recent_history[0][1]['rss_mb']
        end_memory = recent_history[-1][1]['rss_mb']
        time_diff = recent_history[-1][0] - recent_history[0][0]
        
        if time_diff > 0:
            return (end_memory - start_memory) / (time_diff / 60.0)
        return 0.0


class MemoryManager(QObject):
    """Main memory management system."""
    
    # Signals
    memoryPressureDetected = pyqtSignal(float)  # usage_percent
    memoryCleanupStarted = pyqtSignal()
    memoryCleanupCompleted = pyqtSignal(int, float)  # freed_mb, new_usage_percent
    lowMemoryWarning = pyqtSignal(float)  # available_mb
    
    def __init__(self, max_cache_mb: int = 100, parent=None):
        super().__init__(parent)
        
        # Components
        self.memory_pool = MemoryPool(max_cache_mb)
        self.node_tracker = NodeMemoryTracker()
        self.monitor = MemoryMonitor()
        
        # Configuration
        self.cleanup_threshold = 80.0  # Cleanup when usage > 80%
        self.critical_threshold = 90.0  # Critical cleanup when > 90%
        self.min_cleanup_interval = 5000  # 5 seconds
        self.auto_cleanup_enabled = True
        
        # State
        self.last_cleanup_time = 0
        self.cleanup_in_progress = False
        self.weak_refs: Dict[str, weakref.ref] = {}
        
        # Timers
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self._monitor_memory)
        self.monitoring_timer.start(1000)  # Monitor every second
        
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._scheduled_cleanup)
        self.cleanup_timer.start(10000)  # Cleanup check every 10 seconds
    
    def cache_data(self, key: str, data: Any, size_hint: int = None,
                   priority: MemoryPriority = MemoryPriority.NORMAL) -> bool:
        """Cache data in memory pool."""
        return self.memory_pool.add(key, data, size_hint, priority)
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data."""
        return self.memory_pool.get(key)
    
    def remove_cached_data(self, key: str) -> bool:
        """Remove cached data."""
        return self.memory_pool.remove(key)
    
    def track_node_memory(self, node: TreeNode) -> None:
        """Track memory usage of a node."""
        if not node.element:
            return
        
        node_id = node.element.id
        size = self._estimate_node_size(node)
        parent_id = node.parent().element.id if node.parent() and node.parent().element else None
        
        self.node_tracker.track_node(node_id, size, parent_id)
        
        # Create weak reference
        self.weak_refs[node_id] = weakref.ref(node, lambda: self._on_node_deleted(node_id))
    
    def untrack_node_memory(self, node_id: str) -> None:
        """Stop tracking node memory."""
        self.node_tracker.untrack_node(node_id)
        self.weak_refs.pop(node_id, None)
    
    def add_node_reference(self, node_id: str) -> None:
        """Add reference to node."""
        self.node_tracker.add_reference(node_id)
    
    def remove_node_reference(self, node_id: str) -> None:
        """Remove reference from node."""
        self.node_tracker.remove_reference(node_id)
    
    def cleanup_memory(self, aggressive: bool = False) -> Tuple[int, float]:
        """Perform memory cleanup."""
        if self.cleanup_in_progress:
            return 0, 0.0
        
        self.cleanup_in_progress = True
        self.memoryCleanupStarted.emit()
        
        try:
            initial_usage = self.monitor.get_memory_info()['rss_mb']
            
            # 1. Clean up unreferenced nodes
            unreferenced = self.node_tracker.get_unreferenced_nodes()
            for node_id in unreferenced:
                self.remove_cached_data(node_id)
                self.untrack_node_memory(node_id)
            
            # 2. Clean up memory pool if aggressive or under pressure
            if aggressive or self.monitor.is_memory_pressure():
                self._cleanup_memory_pool(aggressive)
            
            # 3. Force garbage collection
            gc.collect()
            
            # 4. Update monitoring
            final_usage = self.monitor.update()['rss_mb']
            freed_mb = initial_usage - final_usage
            
            self.memoryCleanupCompleted.emit(int(freed_mb), final_usage)
            return int(freed_mb), final_usage
            
        finally:
            self.cleanup_in_progress = False
            self.last_cleanup_time = time.time()
    
    def _cleanup_memory_pool(self, aggressive: bool) -> None:
        """Clean up memory pool."""
        if aggressive:
            # Remove all but critical entries
            to_remove = []
            for key, entry in self.memory_pool.entries.items():
                if entry.priority != MemoryPriority.CRITICAL:
                    to_remove.append(key)
            
            for key in to_remove:
                self.memory_pool.remove(key)
        else:
            # Remove entries based on age and access patterns
            current_time = time.time()
            to_remove = []
            
            for key, entry in self.memory_pool.entries.items():
                # Remove if old and not accessed recently
                if (entry.age() > 300 and  # Older than 5 minutes
                    entry.time_since_access() > 60 and  # Not accessed in 1 minute
                    entry.priority in [MemoryPriority.DISPOSABLE, MemoryPriority.LOW]):
                    to_remove.append(key)
            
            for key in to_remove:
                self.memory_pool.remove(key)
    
    def _monitor_memory(self) -> None:
        """Monitor memory usage."""
        memory_info = self.monitor.update()
        
        # Check for memory pressure
        if memory_info['system_percent'] > self.cleanup_threshold:
            self.memoryPressureDetected.emit(memory_info['system_percent'])
            
            if self.auto_cleanup_enabled:
                # Check if enough time has passed since last cleanup
                if time.time() - self.last_cleanup_time > self.min_cleanup_interval / 1000.0:
                    aggressive = memory_info['system_percent'] > self.critical_threshold
                    self.cleanup_memory(aggressive)
        
        # Check for low available memory
        if memory_info['system_available_mb'] < 500:  # Less than 500MB available
            self.lowMemoryWarning.emit(memory_info['system_available_mb'])
    
    def _scheduled_cleanup(self) -> None:
        """Perform scheduled cleanup."""
        if not self.auto_cleanup_enabled or self.cleanup_in_progress:
            return
        
        # Clean up unreferenced nodes
        unreferenced = self.node_tracker.get_unreferenced_nodes()
        if unreferenced:
            for node_id in unreferenced[:10]:  # Limit to 10 per cycle
                self.remove_cached_data(node_id)
                self.untrack_node_memory(node_id)
        
        # Clean up old cache entries
        current_time = time.time()
        to_remove = []
        
        for key, entry in list(self.memory_pool.entries.items())[:20]:  # Limit check
            if (entry.priority == MemoryPriority.DISPOSABLE and
                entry.time_since_access() > 120):  # 2 minutes for disposable
                to_remove.append(key)
        
        for key in to_remove:
            self.memory_pool.remove(key)
    
    def _on_node_deleted(self, node_id: str) -> None:
        """Handle node deletion via weak reference."""
        self.untrack_node_memory(node_id)
        self.remove_cached_data(node_id)
    
    def _estimate_node_size(self, node: TreeNode) -> int:
        """Estimate memory size of a node."""
        size = 200  # Base node overhead
        
        if node.element:
            # Add element data size
            if hasattr(node.element, 'text') and node.element.text:
                size += len(node.element.text) * 2  # Unicode overhead
            
            if hasattr(node.element, 'metadata') and node.element.metadata:
                size += len(str(node.element.metadata))
            
            size += 100  # Element object overhead
        
        # Add children overhead
        size += node.child_count() * 8  # Pointer overhead
        
        return size
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        pool_stats = self.memory_pool.get_memory_usage()
        system_stats = self.monitor.get_memory_info()
        
        return {
            'cache': pool_stats,
            'system': system_stats,
            'nodes': {
                'tracked_count': len(self.node_tracker.node_sizes),
                'total_size_mb': self.node_tracker.total_tracked / (1024 * 1024),
                'unreferenced_count': len(self.node_tracker.get_unreferenced_nodes())
            },
            'monitoring': {
                'baseline_mb': self.monitor.baseline_memory['rss_mb'],
                'peak_mb': self.monitor.peak_memory['rss_mb'],
                'growth_mb': self.monitor.get_memory_growth(),
                'trend_mb_per_min': self.monitor.get_memory_trend()
            }
        }
    
    def configure_memory_management(self, **kwargs) -> None:
        """Configure memory management parameters."""
        if 'cleanup_threshold' in kwargs:
            self.cleanup_threshold = kwargs['cleanup_threshold']
        if 'critical_threshold' in kwargs:
            self.critical_threshold = kwargs['critical_threshold']
        if 'auto_cleanup_enabled' in kwargs:
            self.auto_cleanup_enabled = kwargs['auto_cleanup_enabled']
        if 'min_cleanup_interval' in kwargs:
            self.min_cleanup_interval = kwargs['min_cleanup_interval']
    
    def force_cleanup(self) -> None:
        """Force immediate aggressive cleanup."""
        self.cleanup_memory(aggressive=True)