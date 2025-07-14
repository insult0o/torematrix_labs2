"""
Update Optimization System for Reactive Components.

This module provides optimization strategies to minimize unnecessary re-renders
through memoization, caching, and intelligent update detection.
"""

import hashlib
import weakref
from functools import wraps, lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
from dataclasses import dataclass, field
import threading
import time

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class MemoizationEntry:
    """Entry in memoization cache."""
    
    result: Any
    timestamp: float
    hit_count: int = 0
    dependencies: Set[str] = field(default_factory=set)
    
    def is_valid(self, max_age: Optional[float] = None) -> bool:
        """Check if entry is still valid."""
        if max_age is not None:
            age = time.time() - self.timestamp
            return age <= max_age
        return True


class ComponentMemoizer:
    """Memoization system for component renders."""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize memoizer."""
        self.max_entries = max_entries
        self._cache: Dict[str, MemoizationEntry] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def memoize(
        self,
        key: str,
        compute_func: Callable[[], T],
        dependencies: Optional[Set[str]] = None,
        max_age: Optional[float] = None
    ) -> T:
        """Memoize a computation result."""
        with self._lock:
            # Check cache
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_valid(max_age):
                    # Cache hit
                    entry.hit_count += 1
                    self._stats["hits"] += 1
                    self._update_access_order(key)
                    return entry.result
            
            # Cache miss
            self._stats["misses"] += 1
            
            # Compute result
            result = compute_func()
            
            # Store in cache
            entry = MemoizationEntry(
                result=result,
                timestamp=time.time(),
                dependencies=dependencies or set()
            )
            
            self._cache[key] = entry
            self._update_access_order(key)
            
            # Evict if needed
            self._evict_if_needed()
            
            return result
    
    def invalidate(self, key: Optional[str] = None, dependency: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        with self._lock:
            if key:
                # Invalidate specific key
                if key in self._cache:
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
            elif dependency:
                # Invalidate all entries with dependency
                keys_to_remove = [
                    k for k, entry in self._cache.items()
                    if dependency in entry.dependencies
                ]
                for k in keys_to_remove:
                    del self._cache[k]
                    if k in self._access_order:
                        self._access_order.remove(k)
            else:
                # Clear all
                self._cache.clear()
                self._access_order.clear()
    
    def _update_access_order(self, key: str) -> None:
        """Update LRU access order."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if cache is full."""
        while len(self._cache) > self.max_entries:
            if self._access_order:
                lru_key = self._access_order.pop(0)
                del self._cache[lru_key]
                self._stats["evictions"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memoization statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / max(1, total)
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": round(hit_rate, 3),
                "cache_size": len(self._cache),
                "max_entries": self.max_entries
            }


def memoize_render(
    max_age: Optional[float] = None,
    dependencies: Optional[List[str]] = None
) -> Callable[[F], F]:
    """Decorator to memoize render functions."""
    def decorator(func: F) -> F:
        memoizer = ComponentMemoizer()
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            key_parts = [
                func.__name__,
                str(id(self)),
                repr(args),
                repr(sorted(kwargs.items()))
            ]
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Get dependencies
            deps = set(dependencies) if dependencies else set()
            
            # Memoize
            return memoizer.memoize(
                key=key,
                compute_func=lambda: func(self, *args, **kwargs),
                dependencies=deps,
                max_age=max_age
            )
        
        # Attach memoizer for inspection
        wrapper.memoizer = memoizer
        return wrapper
    
    return decorator


class RenderOptimizer:
    """Optimizes rendering through various strategies."""
    
    def __init__(self):
        """Initialize render optimizer."""
        self._should_update_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._prop_checksums: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._skip_counts: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def should_component_update(
        self,
        widget: QWidget,
        new_props: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> bool:
        """Determine if component should update."""
        with self._lock:
            # Get cached decision
            cache_key = self._get_cache_key(widget, new_props, new_state)
            
            if widget in self._should_update_cache:
                cached = self._should_update_cache[widget]
                if cached.get("key") == cache_key:
                    # Same props/state, return cached decision
                    widget_type = widget.__class__.__name__
                    self._skip_counts[widget_type] = self._skip_counts.get(widget_type, 0) + 1
                    return cached["should_update"]
            
            # Compute decision
            should_update = self._compute_should_update(widget, new_props, new_state)
            
            # Cache decision
            self._should_update_cache[widget] = {
                "key": cache_key,
                "should_update": should_update
            }
            
            return should_update
    
    def _get_cache_key(
        self,
        widget: QWidget,
        props: Dict[str, Any],
        state: Dict[str, Any]
    ) -> str:
        """Generate cache key for props/state combination."""
        # Create stable representation
        props_str = repr(sorted(props.items()))
        state_str = repr(sorted(state.items()))
        combined = f"{props_str}:{state_str}"
        
        # Generate checksum
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _compute_should_update(
        self,
        widget: QWidget,
        new_props: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> bool:
        """Compute whether component should update."""
        # Get previous checksums
        if widget not in self._prop_checksums:
            # First render
            self._prop_checksums[widget] = {
                "props": self._checksum_dict(new_props),
                "state": self._checksum_dict(new_state)
            }
            return True
        
        prev_checksums = self._prop_checksums[widget]
        
        # Check props
        new_props_checksum = self._checksum_dict(new_props)
        if new_props_checksum != prev_checksums.get("props"):
            self._prop_checksums[widget]["props"] = new_props_checksum
            return True
        
        # Check state
        new_state_checksum = self._checksum_dict(new_state)
        if new_state_checksum != prev_checksums.get("state"):
            self._prop_checksums[widget]["state"] = new_state_checksum
            return True
        
        return False
    
    def _checksum_dict(self, d: Dict[str, Any]) -> str:
        """Generate checksum for dictionary."""
        # Sort for stable ordering
        sorted_items = sorted(d.items())
        content = repr(sorted_items)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        with self._lock:
            total_skips = sum(self._skip_counts.values())
            
            return {
                "total_skips": total_skips,
                "skips_by_component": dict(self._skip_counts),
                "cached_widgets": len(self._should_update_cache)
            }


class UpdateBatcher:
    """Batches multiple updates into single render cycles."""
    
    def __init__(self):
        """Initialize update batcher."""
        self._pending_updates: Dict[int, List[Tuple[str, Any]]] = {}
        self._update_callbacks: Dict[int, Callable] = {}
        self._lock = threading.RLock()
    
    def batch_update(
        self,
        widget: QWidget,
        updates: List[Tuple[str, Any]],
        callback: Optional[Callable] = None
    ) -> None:
        """Batch updates for a widget."""
        widget_id = id(widget)
        
        with self._lock:
            if widget_id not in self._pending_updates:
                self._pending_updates[widget_id] = []
            
            self._pending_updates[widget_id].extend(updates)
            
            if callback:
                self._update_callbacks[widget_id] = callback
    
    def flush_updates(self, widget: Optional[QWidget] = None) -> Dict[int, List[Tuple[str, Any]]]:
        """Flush pending updates."""
        with self._lock:
            if widget:
                widget_id = id(widget)
                updates = self._pending_updates.pop(widget_id, [])
                callback = self._update_callbacks.pop(widget_id, None)
                
                if callback and updates:
                    callback()
                
                return {widget_id: updates} if updates else {}
            else:
                # Flush all
                all_updates = dict(self._pending_updates)
                all_callbacks = dict(self._update_callbacks)
                
                self._pending_updates.clear()
                self._update_callbacks.clear()
                
                # Execute callbacks
                for widget_id, callback in all_callbacks.items():
                    if widget_id in all_updates and all_updates[widget_id]:
                        callback()
                
                return all_updates
    
    def has_pending_updates(self, widget: Optional[QWidget] = None) -> bool:
        """Check if there are pending updates."""
        with self._lock:
            if widget:
                return id(widget) in self._pending_updates
            return bool(self._pending_updates)


# Smart update detection
@lru_cache(maxsize=1000)
def _deep_equal(a: Any, b: Any) -> bool:
    """Deep equality check with caching."""
    if type(a) != type(b):
        return False
    
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(_deep_equal(x, y) for x, y in zip(a, b))
    
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_deep_equal(a[k], b[k]) for k in a.keys())
    
    return a == b


class SmartUpdateDetector:
    """Intelligent update detection with deep comparison."""
    
    def __init__(self):
        """Initialize detector."""
        self._previous_values: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
    
    def has_changed(self, widget: QWidget, key: str, value: Any) -> bool:
        """Check if value has changed for widget."""
        if widget not in self._previous_values:
            self._previous_values[widget] = {}
        
        prev_values = self._previous_values[widget]
        
        if key not in prev_values:
            # First time seeing this key
            prev_values[key] = value
            return True
        
        # Deep comparison
        prev_value = prev_values[key]
        has_changed = not _deep_equal(prev_value, value)
        
        if has_changed:
            prev_values[key] = value
        
        return has_changed
    
    def track_values(self, widget: QWidget, values: Dict[str, Any]) -> Set[str]:
        """Track multiple values and return changed keys."""
        changed_keys = set()
        
        for key, value in values.items():
            if self.has_changed(widget, key, value):
                changed_keys.add(key)
        
        return changed_keys


# Global instances
_render_optimizer: Optional[RenderOptimizer] = None
_update_batcher: Optional[UpdateBatcher] = None
_smart_detector: Optional[SmartUpdateDetector] = None


def get_render_optimizer() -> RenderOptimizer:
    """Get the global render optimizer."""
    global _render_optimizer
    if _render_optimizer is None:
        _render_optimizer = RenderOptimizer()
    return _render_optimizer


def get_update_batcher() -> UpdateBatcher:
    """Get the global update batcher."""
    global _update_batcher
    if _update_batcher is None:
        _update_batcher = UpdateBatcher()
    return _update_batcher


def get_smart_detector() -> SmartUpdateDetector:
    """Get the global smart update detector."""
    global _smart_detector
    if _smart_detector is None:
        _smart_detector = SmartUpdateDetector()
    return _smart_detector