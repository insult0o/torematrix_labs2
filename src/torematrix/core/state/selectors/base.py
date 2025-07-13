"""
Base selector implementation with memoization and dependency tracking.
"""

import time
import weakref
from typing import Any, Callable, Dict, List, Optional, TypeVar, Tuple, Union
from dataclasses import dataclass
from collections.abc import Hashable

T = TypeVar('T')


@dataclass(frozen=True)
class SelectorKey:
    """Immutable key for selector cache entries."""
    state_hash: int
    args_hash: int
    
    @classmethod
    def create(cls, state: Dict[str, Any], args: Tuple) -> 'SelectorKey':
        """Create a selector key from state and arguments."""
        # Create a shallow hash of relevant state parts
        state_str = str(sorted(state.items()))
        state_hash = hash(state_str)
        
        # Hash arguments if they're hashable
        try:
            args_hash = hash(args) if args else 0
        except TypeError:
            # Handle unhashable args by converting to string
            args_hash = hash(str(args))
            
        return cls(state_hash=state_hash, args_hash=args_hash)


class Selector:
    """
    High-performance memoized selector with dependency tracking.
    
    Provides reselect-style memoization with optimizations for large state trees.
    """
    
    def __init__(
        self,
        selector_fn: Callable,
        dependencies: Optional[List['Selector']] = None,
        name: Optional[str] = None
    ):
        self.selector_fn = selector_fn
        self.dependencies = dependencies or []
        self.name = name or f"selector_{id(self)}"
        
        # Memoization cache
        self._cache: Dict[SelectorKey, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_calls = 0
        
        # Performance tracking
        self._execution_times: List[float] = []
        self._max_cache_size = 100  # Prevent memory leaks
        
        # Weak reference tracking for subscribers
        self._subscribers: weakref.WeakSet = weakref.WeakSet()
    
    def __call__(self, state: Dict[str, Any], *args) -> Any:
        """Execute selector with memoization."""
        self._total_calls += 1
        
        # Create cache key
        cache_key = SelectorKey.create(state, args)
        
        # Check cache first
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]
        
        # Cache miss - compute result
        self._cache_misses += 1
        start_time = time.perf_counter()
        
        try:
            if self.dependencies:
                # Compute dependency results first
                dep_results = []
                for dep in self.dependencies:
                    if isinstance(dep, Selector):
                        dep_results.append(dep(state, *args))
                    else:
                        # Simple function dependency
                        dep_results.append(dep(state))
                
                # Call selector with dependency results
                if args:
                    result = self.selector_fn(*dep_results, *args)
                else:
                    result = self.selector_fn(*dep_results)
            else:
                # Direct selector call
                result = self.selector_fn(state, *args)
            
            # Cache the result
            self._cache[cache_key] = result
            
            # Limit cache size to prevent memory leaks
            if len(self._cache) > self._max_cache_size:
                # Remove oldest entries (simple FIFO)
                oldest_keys = list(self._cache.keys())[:-self._max_cache_size//2]
                for key in oldest_keys:
                    del self._cache[key]
            
            return result
            
        finally:
            execution_time = time.perf_counter() - start_time
            self._execution_times.append(execution_time)
            
            # Keep only recent execution times
            if len(self._execution_times) > 1000:
                self._execution_times = self._execution_times[-500:]
    
    def invalidate(self, state_path: Optional[str] = None):
        """Invalidate selector cache."""
        if state_path is None:
            # Full invalidation
            self._cache.clear()
        else:
            # Selective invalidation based on state path
            # For now, we do full invalidation, but this could be optimized
            # to only invalidate when specific state paths change
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get selector performance statistics."""
        total_calls = self._total_calls
        cache_hit_rate = (self._cache_hits / total_calls * 100) if total_calls > 0 else 0
        
        avg_time = 0
        max_time = 0
        min_time = 0
        
        if self._execution_times:
            avg_time = sum(self._execution_times) / len(self._execution_times)
            max_time = max(self._execution_times)
            min_time = min(self._execution_times)
        
        return {
            'name': self.name,
            'total_calls': total_calls,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self._cache),
            'avg_execution_time_ms': avg_time * 1000,
            'max_execution_time_ms': max_time * 1000,
            'min_execution_time_ms': min_time * 1000,
            'recent_executions': len(self._execution_times)
        }
    
    def subscribe(self, callback: Callable):
        """Subscribe to selector changes."""
        self._subscribers.add(callback)
        return lambda: self._subscribers.discard(callback)
    
    def notify_change(self):
        """Notify subscribers of selector changes."""
        for callback in self._subscribers:
            try:
                callback(self)
            except Exception:
                # Remove failed callback
                self._subscribers.discard(callback)


class ParametricSelector(Selector):
    """
    Selector that takes parameters for dynamic state queries.
    
    Useful for selectors that need to filter or transform state based on
    runtime parameters while still benefiting from memoization.
    """
    
    def __init__(
        self,
        selector_fn: Callable,
        dependencies: Optional[List[Selector]] = None,
        name: Optional[str] = None
    ):
        super().__init__(selector_fn, dependencies, name)
        # Parametric selectors have separate caches per parameter set
        self._param_caches: Dict[int, Dict[SelectorKey, Any]] = {}
    
    def __call__(self, state: Dict[str, Any], *args) -> Any:
        """Execute parametric selector with parameter-specific caching."""
        if not args:
            return super().__call__(state)
        
        # Create parameter-specific cache
        param_hash = hash(args)
        if param_hash not in self._param_caches:
            self._param_caches[param_hash] = {}
        
        # Use parameter-specific cache
        old_cache = self._cache
        self._cache = self._param_caches[param_hash]
        
        try:
            result = super().__call__(state, *args)
            return result
        finally:
            self._cache = old_cache


def create_selector(*dependencies, output_fn: Callable, name: Optional[str] = None) -> Selector:
    """
    Create a memoized selector with dependencies.
    
    Similar to reselect's createSelector, but optimized for Python and our use case.
    
    Args:
        *dependencies: Input selectors or functions
        output_fn: Function that computes the final result
        name: Optional name for debugging/profiling
        
    Returns:
        Memoized selector
        
    Example:
        get_visible_elements = create_selector(
            get_elements,
            lambda elements: [e for e in elements if e.get('visible', True)],
            name='get_visible_elements'
        )
    """
    return Selector(
        selector_fn=output_fn,
        dependencies=list(dependencies),
        name=name
    )


def create_parametric_selector(
    *dependencies,
    output_fn: Callable,
    name: Optional[str] = None
) -> ParametricSelector:
    """
    Create a parametric selector that accepts runtime parameters.
    
    Args:
        *dependencies: Input selectors or functions
        output_fn: Function that computes the final result
        name: Optional name for debugging/profiling
        
    Returns:
        Parametric memoized selector
    """
    return ParametricSelector(
        selector_fn=output_fn,
        dependencies=list(dependencies),
        name=name
    )