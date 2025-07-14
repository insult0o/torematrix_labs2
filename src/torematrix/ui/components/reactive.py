"""
Reactive Widget Base Classes for TORE Matrix Labs V3.

This module provides the foundational ReactiveWidget class that enables automatic
state subscription, efficient re-rendering, and memory management for UI components.
"""

from __future__ import annotations

import logging
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID, uuid4

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

try:
    from torematrix.core.events import Event, EventBus, EventPriority
    from torematrix.core.state import Action, Store
except ImportError:
    # For testing without full dependencies
    Event = EventBus = EventPriority = Action = Store = None

logger = logging.getLogger(__name__)

T = TypeVar("T")
W = TypeVar("W", bound="ReactiveWidget")


@dataclass
class ReactiveProperty:
    """Represents a reactive property with change tracking."""
    
    name: str
    value: Any
    type_hint: Type[Any]
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None
    dependencies: List[str] = field(default_factory=list)
    computed: bool = False
    setter: Optional[Callable[[Any], None]] = None
    getter: Optional[Callable[[], Any]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate property value."""
        if self.validator:
            return self.validator(value)
        return True
    
    def transform(self, value: Any) -> Any:
        """Transform property value."""
        if self.transformer:
            return self.transformer(value)
        return value


@dataclass
class StateBinding:
    """Represents a binding between a component property and state path."""
    
    property_name: str
    state_path: str
    transform: Optional[Callable[[Any], Any]] = None
    bidirectional: bool = False
    debounce_ms: int = 0
    
    def __hash__(self) -> int:
        return hash((self.property_name, self.state_path))


class ReactiveMetaclass(type(QWidget)):
    """
    Metaclass for ReactiveWidget that automatically injects reactive behavior.
    
    This metaclass:
    - Processes type hints to create reactive properties
    - Registers lifecycle hooks
    - Sets up property change tracking
    - Enables automatic state subscription
    """
    
    def __new__(
        mcs,
        name: str,
        bases: tuple,
        namespace: dict,
        **kwargs: Any
    ) -> ReactiveMetaclass:
        # Process type hints to identify reactive properties
        annotations = namespace.get("__annotations__", {})
        reactive_props: Dict[str, ReactiveProperty] = {}
        
        # Extract reactive properties from annotations
        for prop_name, prop_type in annotations.items():
            if not prop_name.startswith("_"):
                reactive_props[prop_name] = ReactiveProperty(
                    name=prop_name,
                    value=namespace.get(prop_name, None),
                    type_hint=prop_type
                )
        
        # Store reactive properties in class
        namespace["_reactive_properties"] = reactive_props
        
        # Create property descriptors for reactive properties
        for prop_name, prop_info in reactive_props.items():
            # Don't override if already has a descriptor
            if prop_name not in namespace or not hasattr(namespace[prop_name], '__get__'):
                namespace[prop_name] = mcs._create_property_descriptor(prop_name)
        
        # Process lifecycle methods
        lifecycle_methods = {
            "on_mount": namespace.get("on_mount"),
            "on_unmount": namespace.get("on_unmount"),
            "on_update": namespace.get("on_update"),
            "before_render": namespace.get("before_render"),
            "after_render": namespace.get("after_render"),
        }
        namespace["_lifecycle_methods"] = {
            k: v for k, v in lifecycle_methods.items() if v is not None
        }
        
        return super().__new__(mcs, name, bases, namespace, **kwargs)
    
    @staticmethod
    def _create_property_descriptor(prop_name: str) -> property:
        """Create a property descriptor for reactive property."""
        
        def getter(self: ReactiveWidget) -> Any:
            prop = self._reactive_properties.get(prop_name)
            if prop and prop.getter:
                return prop.getter()
            # Return from property values or use default from ReactiveProperty
            if prop_name in self._property_values:
                return self._property_values[prop_name]
            elif prop:
                return prop.value
            return None
        
        def setter(self: ReactiveWidget, value: Any) -> None:
            old_value = self._property_values.get(prop_name)
            prop = self._reactive_properties.get(prop_name)
            
            if prop:
                # Validate
                if not prop.validate(value):
                    raise ValueError(f"Invalid value for property {prop_name}: {value}")
                
                # Transform
                value = prop.transform(value)
                
                # Custom setter
                if prop.setter:
                    prop.setter(value)
            
            # Update value and notify
            self._property_values[prop_name] = value
            if old_value != value:
                self._on_property_changed(prop_name, old_value, value)
        
        return property(getter, setter)


class ReactiveWidget(QWidget, metaclass=ReactiveMetaclass):
    """
    Base class for reactive UI components in TORE Matrix Labs.
    
    Features:
    - Automatic state subscription and synchronization
    - Property change detection and notification
    - Lifecycle management (mount/unmount/update)
    - Efficient re-rendering with batching
    - Memory-safe cleanup mechanisms
    - Component composition support
    """
    
    # Signals
    property_changed = pyqtSignal(str, object, object)  # name, old_value, new_value
    state_changed = pyqtSignal(str, object)  # path, value
    lifecycle_event = pyqtSignal(str)  # event_name
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        component_id: Optional[str] = None,
        **kwargs: Any
    ):
        """Initialize reactive widget."""
        super().__init__(parent)
        
        # Component identification
        self._component_id = component_id or str(uuid4())
        self._component_type = self.__class__.__name__
        
        # Property management
        self._property_values: Dict[str, Any] = {}
        self._reactive_properties: Dict[str, ReactiveProperty] = getattr(
            self.__class__, "_reactive_properties", {}
        )
        
        # State management
        self._state_bindings: Set[StateBinding] = set()
        self._state_subscriptions: Dict[str, UUID] = {}
        self._store: Optional[Store] = None
        self._event_bus: Optional[EventBus] = None
        
        # Lifecycle management
        self._is_mounted = False
        self._is_updating = False
        self._update_batch: Set[str] = set()
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._process_update_batch)
        self._update_timer.setSingleShot(True)
        
        # Parent-child relationships
        self._reactive_children: List[weakref.ref[ReactiveWidget]] = []
        self._reactive_parent: Optional[weakref.ref[ReactiveWidget]] = None
        
        # Performance monitoring
        self._render_count = 0
        self._last_render_time = 0.0
        
        # Initialize properties from kwargs
        for key, value in kwargs.items():
            if key in self._reactive_properties:
                setattr(self, key, value)
        
        # Register with parent if reactive
        if parent and isinstance(parent, ReactiveWidget):
            self._reactive_parent = weakref.ref(parent)
            parent._register_child(self)
    
    @property
    def component_id(self) -> str:
        """Get component ID."""
        return self._component_id
    
    @property
    def is_mounted(self) -> bool:
        """Check if component is mounted."""
        return self._is_mounted
    
    def bind_state(
        self,
        state_path: str,
        property_name: str,
        transform: Optional[Callable[[Any], Any]] = None,
        bidirectional: bool = False,
        debounce_ms: int = 0
    ) -> None:
        """
        Bind a component property to a state path.
        
        Args:
            state_path: Path in state tree (e.g., "document.title")
            property_name: Name of component property
            transform: Optional transformation function
            bidirectional: Enable two-way binding
            debounce_ms: Debounce updates in milliseconds
        """
        binding = StateBinding(
            property_name=property_name,
            state_path=state_path,
            transform=transform,
            bidirectional=bidirectional,
            debounce_ms=debounce_ms
        )
        
        self._state_bindings.add(binding)
        
        # Subscribe to state changes if store available
        if self._store and self._is_mounted:
            self._subscribe_to_state_path(binding)
    
    def computed_property(
        self,
        name: str,
        dependencies: List[str],
        compute_func: Callable[..., Any]
    ) -> None:
        """
        Create a computed property from state dependencies.
        
        Args:
            name: Property name
            dependencies: List of state paths this property depends on
            compute_func: Function to compute property value
        """
        prop = ReactiveProperty(
            name=name,
            value=None,
            type_hint=Any,
            dependencies=dependencies,
            computed=True,
            getter=lambda: self._compute_property(name, dependencies, compute_func)
        )
        
        self._reactive_properties[name] = prop
        
        # Create property descriptor
        setattr(
            self.__class__,
            name,
            self.__class__._create_property_descriptor(name)
        )
    
    def on_state_change(
        self,
        path: str,
        callback: Callable[[Any], None],
        immediate: bool = True
    ) -> UUID:
        """
        Register callback for specific state changes.
        
        Args:
            path: State path to watch
            callback: Function to call on change
            immediate: Call immediately with current value
            
        Returns:
            Subscription ID
        """
        if not self._store:
            raise RuntimeError("No store connected to component")
        
        # Subscribe to state changes
        subscription_id = uuid4()
        
        def wrapped_callback(state: Any) -> None:
            value = self._get_state_value(path, state)
            callback(value)
        
        self._store.subscribe(wrapped_callback, path)
        self._state_subscriptions[path] = subscription_id
        
        # Call immediately if requested
        if immediate:
            current_value = self._get_state_value(path, self._store.get_state())
            callback(current_value)
        
        return subscription_id
    
    def update_state(self, path: str, value: Any) -> None:
        """
        Update state from component.
        
        Args:
            path: State path to update
            value: New value
        """
        if not self._store:
            raise RuntimeError("No store connected to component")
        
        # Create action for state update
        action = Action(
            type=f"UPDATE_{path.upper().replace('.', '_')}",
            payload={"path": path, "value": value}
        )
        
        self._store.dispatch(action)
    
    def force_update(self) -> None:
        """Force component re-render."""
        self._schedule_update()
    
    def mount(self) -> None:
        """Mount component and trigger lifecycle."""
        if self._is_mounted:
            return
        
        self._is_mounted = True
        
        # Connect to services
        self._connect_services()
        
        # Subscribe to state bindings
        for binding in self._state_bindings:
            self._subscribe_to_state_path(binding)
        
        # Lifecycle hook
        self._call_lifecycle_method("on_mount")
        self.lifecycle_event.emit("mount")
        
        # Mount children
        for child_ref in self._reactive_children:
            child = child_ref()
            if child:
                child.mount()
    
    def unmount(self) -> None:
        """Unmount component and cleanup."""
        if not self._is_mounted:
            return
        
        # Unmount children first
        for child_ref in self._reactive_children:
            child = child_ref()
            if child:
                child.unmount()
        
        # Lifecycle hook
        self._call_lifecycle_method("on_unmount")
        self.lifecycle_event.emit("unmount")
        
        # Cleanup subscriptions
        self._cleanup_subscriptions()
        
        # Disconnect from services
        self._disconnect_services()
        
        self._is_mounted = False
    
    # Private methods
    
    def _connect_services(self) -> None:
        """Connect to event bus and state store."""
        # Try to get services from parent or app
        parent = self.parent()
        while parent:
            if hasattr(parent, "_store"):
                self._store = parent._store
                self._event_bus = getattr(parent, "_event_bus", None)
                break
            parent = parent.parent()
    
    def _disconnect_services(self) -> None:
        """Disconnect from services."""
        self._store = None
        self._event_bus = None
    
    def _register_child(self, child: ReactiveWidget) -> None:
        """Register reactive child component."""
        self._reactive_children.append(weakref.ref(child))
    
    def _subscribe_to_state_path(self, binding: StateBinding) -> None:
        """Subscribe to state path for binding."""
        if not self._store:
            return
        
        def update_property(state: Any) -> None:
            value = self._get_state_value(binding.state_path, state)
            if binding.transform:
                value = binding.transform(value)
            
            # Update property without triggering state update
            self._property_values[binding.property_name] = value
            self.property_changed.emit(binding.property_name, None, value)
            self._schedule_update()
        
        self._store.subscribe(update_property, binding.state_path)
    
    def _get_state_value(self, path: str, state: Any) -> Any:
        """Get value from state by path."""
        parts = path.split(".")
        value = state
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _on_property_changed(
        self,
        name: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Handle property change."""
        # Emit signal
        self.property_changed.emit(name, old_value, new_value)
        
        # Check for bidirectional bindings
        for binding in self._state_bindings:
            if binding.property_name == name and binding.bidirectional:
                # Update state with debouncing if needed
                if binding.debounce_ms > 0:
                    # TODO: Implement debouncing
                    self.update_state(binding.state_path, new_value)
                else:
                    self.update_state(binding.state_path, new_value)
        
        # Schedule update
        self._schedule_update()
    
    def _schedule_update(self) -> None:
        """Schedule component update with batching."""
        if not self._is_mounted or self._is_updating:
            return
        
        # Add to update batch
        self._update_batch.add(self._component_id)
        
        # Start timer if not running
        if not self._update_timer.isActive():
            self._update_timer.start(5)  # 5ms batch window
    
    def _process_update_batch(self) -> None:
        """Process batched updates."""
        if not self._update_batch:
            return
        
        self._is_updating = True
        
        try:
            # Lifecycle hooks
            self._call_lifecycle_method("before_render")
            
            # Update component
            self._call_lifecycle_method("on_update")
            self.update()
            
            # Track render
            self._render_count += 1
            
            # Lifecycle hooks
            self._call_lifecycle_method("after_render")
            
        finally:
            self._is_updating = False
            self._update_batch.clear()
    
    def _call_lifecycle_method(self, method_name: str) -> None:
        """Call lifecycle method if exists."""
        methods = getattr(self.__class__, "_lifecycle_methods", {})
        method = methods.get(method_name)
        if method:
            method(self)
    
    def _cleanup_subscriptions(self) -> None:
        """Cleanup all state subscriptions."""
        # TODO: Implement subscription cleanup with store
        self._state_subscriptions.clear()
    
    def _compute_property(
        self,
        name: str,
        dependencies: List[str],
        compute_func: Callable[..., Any]
    ) -> Any:
        """Compute property value from dependencies."""
        if not self._store:
            return None
        
        # Get dependency values
        state = self._store.get_state()
        dep_values = [
            self._get_state_value(dep, state)
            for dep in dependencies
        ]
        
        # Compute value
        return compute_func(*dep_values)
    
    # Qt overrides
    
    def showEvent(self, event: Any) -> None:
        """Handle widget show event."""
        super().showEvent(event)
        if not self._is_mounted:
            self.mount()
    
    def hideEvent(self, event: Any) -> None:
        """Handle widget hide event."""
        super().hideEvent(event)
        # Don't unmount on hide, only on destroy
    
    def closeEvent(self, event: Any) -> None:
        """Handle widget close event."""
        self.unmount()
        super().closeEvent(event)