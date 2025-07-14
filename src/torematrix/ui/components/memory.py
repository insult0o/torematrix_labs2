"""
Memory Management Utilities for Reactive Components.

This module provides memory management tools including weak references,
circular reference prevention, and memory leak detection.
"""

import weakref
import gc
import sys
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union, Callable
from collections import defaultdict
from dataclasses import dataclass, field
import logging
import tracemalloc
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot."""
    
    timestamp: datetime
    total_memory: int  # bytes
    component_count: int
    reference_count: int
    gc_stats: Dict[str, Any]
    top_allocations: List[Tuple[str, int]]
    
    def memory_mb(self) -> float:
        """Get memory usage in MB."""
        return self.total_memory / (1024 * 1024)


class WeakRefManager:
    """Manages weak references to prevent memory leaks."""
    
    def __init__(self):
        """Initialize the weak reference manager."""
        self._refs: Dict[int, weakref.ref] = {}
        self._callbacks: Dict[int, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        
    def create_ref(self, obj: Any, callback: Optional[Callable] = None) -> weakref.ref:
        """
        Create a weak reference to an object.
        
        Args:
            obj: Object to reference
            callback: Optional cleanup callback
            
        Returns:
            Weak reference to the object
        """
        with self._lock:
            obj_id = id(obj)
            
            # Create cleanup callback
            def cleanup(ref):
                with self._lock:
                    if obj_id in self._refs:
                        del self._refs[obj_id]
                    if obj_id in self._callbacks:
                        for cb in self._callbacks[obj_id]:
                            try:
                                cb()
                            except Exception as e:
                                logger.error(f"Error in cleanup callback: {e}")
                        del self._callbacks[obj_id]
                    
                    if callback:
                        try:
                            callback(ref)
                        except Exception as e:
                            logger.error(f"Error in user callback: {e}")
            
            # Create weak reference
            ref = weakref.ref(obj, cleanup)
            self._refs[obj_id] = ref
            
            return ref
    
    def add_cleanup_callback(self, obj: Any, callback: Callable) -> None:
        """Add a cleanup callback for when object is garbage collected."""
        with self._lock:
            obj_id = id(obj)
            self._callbacks[obj_id].append(callback)
    
    def get_ref(self, obj_id: int) -> Optional[Any]:
        """Get object from weak reference by ID."""
        with self._lock:
            ref = self._refs.get(obj_id)
            if ref:
                return ref()
            return None
    
    def get_active_count(self) -> int:
        """Get count of active weak references."""
        with self._lock:
            count = 0
            for ref in self._refs.values():
                if ref() is not None:
                    count += 1
            return count


class CircularReferenceDetector:
    """Detects and helps prevent circular references."""
    
    def __init__(self):
        """Initialize the detector."""
        self._relationships: Dict[int, Set[int]] = defaultdict(set)
        self._lock = threading.RLock()
        
    def add_relationship(self, parent: Any, child: Any) -> bool:
        """
        Add a parent-child relationship and check for cycles.
        
        Args:
            parent: Parent object
            child: Child object
            
        Returns:
            True if relationship is safe, False if it creates a cycle
        """
        with self._lock:
            parent_id = id(parent)
            child_id = id(child)
            
            # Check if this would create a cycle
            if self._creates_cycle(parent_id, child_id):
                logger.warning(f"Circular reference detected: {parent.__class__.__name__} -> {child.__class__.__name__}")
                return False
            
            # Add relationship
            self._relationships[parent_id].add(child_id)
            return True
    
    def remove_relationship(self, parent: Any, child: Any) -> None:
        """Remove a parent-child relationship."""
        with self._lock:
            parent_id = id(parent)
            child_id = id(child)
            
            if parent_id in self._relationships:
                self._relationships[parent_id].discard(child_id)
                if not self._relationships[parent_id]:
                    del self._relationships[parent_id]
    
    def clear_relationships(self, obj: Any) -> None:
        """Clear all relationships for an object."""
        with self._lock:
            obj_id = id(obj)
            
            # Remove as parent
            if obj_id in self._relationships:
                del self._relationships[obj_id]
            
            # Remove as child
            for parent_id, children in list(self._relationships.items()):
                if obj_id in children:
                    children.discard(obj_id)
                    if not children:
                        del self._relationships[parent_id]
    
    def _creates_cycle(self, parent_id: int, child_id: int) -> bool:
        """Check if adding relationship would create a cycle."""
        # DFS to check if child can reach parent
        visited = set()
        stack = [child_id]
        
        while stack:
            current = stack.pop()
            if current == parent_id:
                return True
            
            if current in visited:
                continue
                
            visited.add(current)
            stack.extend(self._relationships.get(current, []))
        
        return False


class MemoryLeakDetector:
    """Detects potential memory leaks in components."""
    
    def __init__(self):
        """Initialize the detector."""
        self._component_registry: weakref.WeakSet = weakref.WeakSet()
        self._snapshots: List[MemorySnapshot] = []
        self._tracking_enabled = False
        self._lock = threading.RLock()
        self._process = psutil.Process(os.getpid())
        
    def start_tracking(self) -> None:
        """Start memory tracking."""
        with self._lock:
            if not self._tracking_enabled:
                tracemalloc.start()
                self._tracking_enabled = True
                logger.info("Memory tracking started")
    
    def stop_tracking(self) -> None:
        """Stop memory tracking."""
        with self._lock:
            if self._tracking_enabled:
                tracemalloc.stop()
                self._tracking_enabled = False
                logger.info("Memory tracking stopped")
    
    def register_component(self, component: Any) -> None:
        """Register a component for memory tracking."""
        with self._lock:
            self._component_registry.add(component)
    
    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        with self._lock:
            # Get memory info
            memory_info = self._process.memory_info()
            total_memory = memory_info.rss
            
            # Get component count
            component_count = len(self._component_registry)
            
            # Get reference counts
            reference_count = len(gc.get_objects())
            
            # Get GC stats
            gc_stats = {
                'collections': gc.get_count(),
                'collected': gc.collect(),
                'uncollectable': len(gc.garbage)
            }
            
            # Get top allocations if tracking
            top_allocations = []
            if self._tracking_enabled:
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')[:10]
                top_allocations = [(str(stat), stat.size) for stat in top_stats]
            
            # Create snapshot
            snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                total_memory=total_memory,
                component_count=component_count,
                reference_count=reference_count,
                gc_stats=gc_stats,
                top_allocations=top_allocations
            )
            
            self._snapshots.append(snapshot)
            return snapshot
    
    def check_for_leaks(self, threshold_mb: float = 10.0) -> List[str]:
        """
        Check for potential memory leaks.
        
        Args:
            threshold_mb: Memory increase threshold in MB
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        with self._lock:
            if len(self._snapshots) < 2:
                return warnings
            
            # Compare recent snapshots
            recent = self._snapshots[-5:]
            if len(recent) < 2:
                return warnings
            
            first = recent[0]
            last = recent[-1]
            
            # Check memory growth
            memory_increase = (last.total_memory - first.total_memory) / (1024 * 1024)
            if memory_increase > threshold_mb:
                warnings.append(
                    f"Memory increased by {memory_increase:.2f} MB "
                    f"({first.memory_mb():.2f} MB -> {last.memory_mb():.2f} MB)"
                )
            
            # Check component growth
            component_increase = last.component_count - first.component_count
            if component_increase > 100:
                warnings.append(
                    f"Component count increased by {component_increase} "
                    f"({first.component_count} -> {last.component_count})"
                )
            
            # Check reference growth
            ref_increase = last.reference_count - first.reference_count
            if ref_increase > 10000:
                warnings.append(
                    f"Reference count increased by {ref_increase} "
                    f"({first.reference_count} -> {last.reference_count})"
                )
            
            # Check uncollectable objects
            if last.gc_stats['uncollectable'] > 0:
                warnings.append(
                    f"Found {last.gc_stats['uncollectable']} uncollectable objects"
                )
        
        return warnings
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get a detailed memory report."""
        with self._lock:
            if not self._snapshots:
                return {"error": "No snapshots available"}
            
            latest = self._snapshots[-1]
            
            report = {
                "timestamp": latest.timestamp.isoformat(),
                "memory_mb": latest.memory_mb(),
                "component_count": latest.component_count,
                "reference_count": latest.reference_count,
                "gc_stats": latest.gc_stats,
                "snapshot_count": len(self._snapshots),
            }
            
            # Add growth metrics if we have history
            if len(self._snapshots) > 1:
                first = self._snapshots[0]
                report["growth"] = {
                    "memory_mb": latest.memory_mb() - first.memory_mb(),
                    "components": latest.component_count - first.component_count,
                    "references": latest.reference_count - first.reference_count,
                    "duration": str(latest.timestamp - first.timestamp)
                }
            
            # Add top allocations
            if latest.top_allocations:
                report["top_allocations"] = [
                    {"location": loc, "size_kb": size / 1024}
                    for loc, size in latest.top_allocations[:5]
                ]
            
            return report


# Global instances
_weak_ref_manager = WeakRefManager()
_circular_ref_detector = CircularReferenceDetector()
_memory_leak_detector = MemoryLeakDetector()


def get_weak_ref_manager() -> WeakRefManager:
    """Get the global weak reference manager."""
    return _weak_ref_manager


def get_circular_ref_detector() -> CircularReferenceDetector:
    """Get the global circular reference detector."""
    return _circular_ref_detector


def get_memory_leak_detector() -> MemoryLeakDetector:
    """Get the global memory leak detector."""
    return _memory_leak_detector


class MemoryManagedMixin:
    """Mixin to add memory management capabilities to components."""
    
    def __init__(self, *args, **kwargs):
        """Initialize memory management."""
        super().__init__(*args, **kwargs)
        
        # Register with memory leak detector
        detector = get_memory_leak_detector()
        detector.register_component(self)
        
        # Track child references
        self._child_refs: List[weakref.ref] = []
        self._parent_ref: Optional[weakref.ref] = None
        
    def add_child(self, child: Any) -> bool:
        """
        Add a child component with circular reference checking.
        
        Args:
            child: Child component to add
            
        Returns:
            True if child was added, False if it would create a cycle
        """
        # Check for circular references
        detector = get_circular_ref_detector()
        if not detector.add_relationship(self, child):
            return False
        
        # Create weak reference
        ref_manager = get_weak_ref_manager()
        
        def cleanup():
            detector.remove_relationship(self, child)
        
        child_ref = ref_manager.create_ref(child, lambda r: cleanup())
        self._child_refs.append(child_ref)
        
        # Keep a strong reference in the child to its weak ref
        # This prevents immediate collection in tests
        if hasattr(child, '_weak_self_ref'):
            child._weak_self_ref = child_ref
        
        # Set parent reference in child
        if hasattr(child, '_parent_ref'):
            child._parent_ref = ref_manager.create_ref(self)
        
        return True
    
    def remove_child(self, child: Any) -> None:
        """Remove a child component."""
        # Remove relationship
        detector = get_circular_ref_detector()
        detector.remove_relationship(self, child)
        
        # Remove weak reference
        self._child_refs = [ref for ref in self._child_refs if ref() != child]
    
    def get_children(self) -> List[Any]:
        """Get all active child components."""
        return [child for ref in self._child_refs if (child := ref()) is not None]
    
    def get_parent(self) -> Optional[Any]:
        """Get parent component if any."""
        if self._parent_ref:
            return self._parent_ref()
        return None
    
    def cleanup_memory(self) -> None:
        """Clean up memory resources."""
        # Clear circular reference tracking
        detector = get_circular_ref_detector()
        detector.clear_relationships(self)
        
        # Clear child references
        self._child_refs.clear()
        self._parent_ref = None