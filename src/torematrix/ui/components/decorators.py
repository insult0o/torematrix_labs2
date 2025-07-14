"""
Property binding decorators for ReactiveWidget components.

This module provides decorators that enable declarative property binding,
computed properties, and reactive behavior in UI components.
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, List, Optional, Type, TypeVar, Union, cast
from weakref import WeakKeyDictionary

# Avoid circular import - these will be imported at runtime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from torematrix.ui.components.reactive import ReactiveProperty, ReactiveWidget

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class PropertyDescriptor:
    """Base descriptor for reactive properties."""
    
    def __init__(
        self,
        name: str,
        default: Any = None,
        validator: Optional[Callable[[Any], bool]] = None,
        transformer: Optional[Callable[[Any], Any]] = None
    ):
        self.name = name
        self.default = default
        self.validator = validator
        self.transformer = transformer
        self._values: WeakKeyDictionary = WeakKeyDictionary()
    
    def __set_name__(self, owner: Type[Any], name: str) -> None:
        """Set descriptor name when attached to class."""
        self.name = name
    
    def __get__(self, instance: Any, owner: Type[Any]) -> Any:
        """Get property value."""
        if instance is None:
            return self
        
        return self._values.get(instance, self.default)
    
    def __set__(self, instance: Any, value: Any) -> None:
        """Set property value with validation and transformation."""
        # Validate
        if self.validator and not self.validator(value):
            raise ValueError(f"Invalid value for {self.name}: {value}")
        
        # Transform
        if self.transformer:
            value = self.transformer(value)
        
        # Get old value
        old_value = self._values.get(instance, self.default)
        
        # Set new value
        self._values[instance] = value
        
        # Notify change if different
        if hasattr(instance, "_on_property_changed") and old_value != value:
            instance._on_property_changed(self.name, old_value, value)


def reactive_property(
    default: Any = None,
    validator: Optional[Callable[[Any], bool]] = None,
    transformer: Optional[Callable[[Any], Any]] = None,
    type_hint: Optional[Type[Any]] = None
) -> PropertyDescriptor:
    """
    Decorator to create a reactive property.
    
    Args:
        default: Default value for the property
        validator: Optional validation function
        transformer: Optional transformation function
        type_hint: Optional type hint for the property
        
    Returns:
        Property descriptor
        
    Example:
        class MyWidget(ReactiveWidget):
            @reactive_property(default="", validator=lambda x: isinstance(x, str))
            def title(self) -> str:
                pass
    """
    frame = inspect.currentframe()
    if frame and frame.f_back:
        # Try to get property name from the stack
        for name, obj in frame.f_back.f_locals.items():
            if obj is reactive_property:
                return PropertyDescriptor(
                    name=name,
                    default=default,
                    validator=validator,
                    transformer=transformer
                )
    
    # Fallback: return descriptor without name (will be set by __set_name__)
    return PropertyDescriptor(
        name="",
        default=default,
        validator=validator,
        transformer=transformer
    )


def computed(
    *dependencies: str
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for computed properties that depend on state paths.
    
    Args:
        *dependencies: State paths this property depends on
        
    Returns:
        Decorator function
        
    Example:
        class MyWidget(ReactiveWidget):
            @computed("user.firstName", "user.lastName")
            def full_name(self, first: str, last: str) -> str:
                return f"{first} {last}"
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Store dependencies on the function
        func._computed_dependencies = list(dependencies)
        func._is_computed = True
        
        @functools.wraps(func)
        def wrapper(self: Any) -> T:
            # Register as computed property if not already done
            prop_name = func.__name__
            if prop_name not in self._reactive_properties:
                self.computed_property(
                    name=prop_name,
                    dependencies=list(dependencies),
                    compute_func=func
                )
            
            # Get current values and compute
            if hasattr(self, "_store") and self._store:
                state = self._store.get_state()
                dep_values = [
                    self._get_state_value(dep, state)
                    for dep in dependencies
                ]
                return func(self, *dep_values)
            
            return None
        
        return wrapper
    
    return decorator


def bind_state(
    path: str,
    transform: Optional[Callable[[Any], Any]] = None,
    bidirectional: bool = False,
    debounce: int = 0
) -> Callable[[F], F]:
    """
    Decorator to bind a property to a state path.
    
    Args:
        path: State path to bind to
        transform: Optional transformation function
        bidirectional: Enable two-way binding
        debounce: Debounce time in milliseconds
        
    Returns:
        Decorator function
        
    Example:
        class MyWidget(ReactiveWidget):
            @bind_state("document.title", bidirectional=True)
            def title(self) -> str:
                pass
    """
    def decorator(func: F) -> F:
        # Store binding info on the function
        func._state_binding = {
            "path": path,
            "transform": transform,
            "bidirectional": bidirectional,
            "debounce": debounce
        }
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Auto-bind on first access
            prop_name = func.__name__
            binding_key = f"_bound_{prop_name}"
            
            if not hasattr(self, binding_key):
                self.bind_state(
                    state_path=path,
                    property_name=prop_name,
                    transform=transform,
                    bidirectional=bidirectional,
                    debounce_ms=debounce
                )
                setattr(self, binding_key, True)
            
            return func(self, *args, **kwargs)
        
        return cast(F, wrapper)
    
    return decorator


def watch(
    *paths: str,
    immediate: bool = True
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """
    Decorator to watch state paths and call method on changes.
    
    Args:
        *paths: State paths to watch
        immediate: Call immediately with current values
        
    Returns:
        Decorator function
        
    Example:
        class MyWidget(ReactiveWidget):
            @watch("user.role", "app.theme")
            def on_user_or_theme_change(self, role: str, theme: str) -> None:
                # React to changes
                pass
    """
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        # Store watch info on the function
        func._watch_paths = list(paths)
        func._watch_immediate = immediate
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            # Auto-register watcher on first call
            watch_key = f"_watching_{func.__name__}"
            
            if not hasattr(self, watch_key) and self._is_mounted:
                # Register watchers for all paths
                for path in paths:
                    def make_callback(p: str) -> Callable[[Any], None]:
                        def callback(value: Any) -> None:
                            # Get all current values
                            if self._store:
                                state = self._store.get_state()
                                values = [
                                    self._get_state_value(watch_path, state)
                                    for watch_path in paths
                                ]
                                func(self, *values)
                        return callback
                    
                    self.on_state_change(
                        path,
                        make_callback(path),
                        immediate=immediate and path == paths[0]
                    )
                
                setattr(self, watch_key, True)
            
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def lifecycle(
    hook: str
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """
    Decorator to register lifecycle hook methods.
    
    Args:
        hook: Lifecycle hook name (mount, unmount, update, before_render, after_render)
        
    Returns:
        Decorator function
        
    Example:
        class MyWidget(ReactiveWidget):
            @lifecycle("mount")
            def setup_component(self) -> None:
                # Initialize component
                pass
    """
    valid_hooks = {"mount", "unmount", "update", "before_render", "after_render"}
    
    if hook not in valid_hooks:
        raise ValueError(f"Invalid lifecycle hook: {hook}. Must be one of {valid_hooks}")
    
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        # Store lifecycle info on the function
        func._lifecycle_hook = f"on_{hook}"
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            return func(self, *args, **kwargs)
        
        # Mark for metaclass processing
        wrapper._is_lifecycle_method = True
        
        return wrapper
    
    return decorator


def throttle(
    delay_ms: int
) -> Callable[[F], F]:
    """
    Decorator to throttle method calls.
    
    Args:
        delay_ms: Minimum delay between calls in milliseconds
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        last_call_time = {}
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            import time
            
            current_time = time.time() * 1000
            instance_id = id(self)
            
            if instance_id in last_call_time:
                time_since_last = current_time - last_call_time[instance_id]
                if time_since_last < delay_ms:
                    return None
            
            last_call_time[instance_id] = current_time
            return func(self, *args, **kwargs)
        
        return cast(F, wrapper)
    
    return decorator


def debounce(
    delay_ms: int
) -> Callable[[F], F]:
    """
    Decorator to debounce method calls.
    
    Args:
        delay_ms: Delay before executing in milliseconds
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        timers = {}
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            from PyQt6.QtCore import QTimer
            
            instance_id = id(self)
            
            # Cancel existing timer
            if instance_id in timers:
                timers[instance_id].stop()
                timers[instance_id].deleteLater()
            
            # Create new timer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: func(self, *args, **kwargs))
            timer.start(delay_ms)
            
            timers[instance_id] = timer
            
            return None
        
        return cast(F, wrapper)
    
    return decorator


def memoize(
    max_size: Optional[int] = None
) -> Callable[[F], F]:
    """
    Decorator to memoize method results.
    
    Args:
        max_size: Maximum cache size (None for unlimited)
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        cache = WeakKeyDictionary()
        
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Create cache key
            key = (args, tuple(sorted(kwargs.items())))
            
            # Get instance cache
            if self not in cache:
                cache[self] = {}
            
            instance_cache = cache[self]
            
            # Check cache
            if key in instance_cache:
                return instance_cache[key]
            
            # Compute and cache result
            result = func(self, *args, **kwargs)
            
            # Limit cache size if specified
            if max_size and len(instance_cache) >= max_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(instance_cache))
                del instance_cache[oldest_key]
            
            instance_cache[key] = result
            return result
        
        return cast(F, wrapper)
    
    return decorator