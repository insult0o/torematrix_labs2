"""
Reactive UI Components for TORE Matrix Labs V3.

This package provides reactive UI components with automatic state subscription,
efficient re-rendering, and comprehensive lifecycle management.
"""

# Export only the components, not the UI framework imports
__all__ = [
    # Core classes
    "ReactiveWidget",
    "ReactiveMetaclass", 
    "ReactiveProperty",
    "StateBinding",
    # Decorators
    "reactive_property",
    "bind_state",
    "computed",
    "watch",
    "lifecycle",
    "throttle",
    "debounce",
    "memoize",
    # Lifecycle management
    "LifecycleManager",
    "LifecycleMixin",
    "LifecyclePhase",
    "RenderMetrics",
    "get_lifecycle_manager",
    "with_lifecycle",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ["ReactiveWidget", "ReactiveMetaclass", "ReactiveProperty", "StateBinding"]:
        from .reactive import ReactiveWidget, ReactiveMetaclass, ReactiveProperty, StateBinding
        return globals()[name]
    elif name in ["reactive_property", "bind_state", "computed", "watch", "lifecycle", "throttle", "debounce", "memoize"]:
        from .decorators import reactive_property, bind_state, computed, watch, lifecycle, throttle, debounce, memoize
        return globals()[name]
    elif name in ["LifecycleManager", "LifecycleMixin", "LifecyclePhase", "RenderMetrics", "get_lifecycle_manager", "with_lifecycle"]:
        from .lifecycle import LifecycleManager, LifecycleMixin, LifecyclePhase, RenderMetrics, get_lifecycle_manager, with_lifecycle
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")