"""
State Subscription Manager for Reactive Components.

This module provides automatic state subscription and management for reactive UI components,
ensuring efficient state propagation and memory safety.
"""

import weakref
from typing import Any, Callable, Dict, Optional, Set, Type, Union, List, Tuple
from functools import wraps
import threading
from dataclasses import dataclass, field
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents a single state subscription."""
    
    component_ref: weakref.ref
    selector: Callable[[Dict[str, Any]], Any]
    callback: Callable[[Any], None]
    store_id: str
    property_name: Optional[str] = None
    last_value: Any = None
    active: bool = True
    
    def __hash__(self):
        """Make subscription hashable for set operations."""
        return hash((id(self.component_ref), id(self.selector), self.store_id))
    
    def __eq__(self, other):
        """Check subscription equality."""
        if not isinstance(other, Subscription):
            return False
        return (
            self.component_ref == other.component_ref and
            self.selector == other.selector and
            self.store_id == other.store_id
        )


class SubscriptionManager:
    """Manages state subscriptions for all reactive components."""
    
    def __init__(self):
        """Initialize the subscription manager."""
        self._subscriptions: Dict[str, Set[Subscription]] = {}
        self._component_subscriptions: Dict[int, Set[Subscription]] = {}
        self._lock = threading.RLock()
        self._stores: Dict[str, Any] = {}
        self._suspended = False
        
    def register_store(self, store_id: str, store: Any) -> None:
        """Register a state store with the manager."""
        with self._lock:
            self._stores[store_id] = store
            if store_id not in self._subscriptions:
                self._subscriptions[store_id] = set()
    
    def subscribe(
        self,
        component: Any,
        store_id: str,
        selector: Callable[[Dict[str, Any]], Any],
        callback: Optional[Callable[[Any], None]] = None,
        property_name: Optional[str] = None
    ) -> Subscription:
        """
        Subscribe a component to state changes.
        
        Args:
            component: The component instance
            store_id: ID of the state store
            selector: Function to select state slice
            callback: Optional callback for state changes
            property_name: Optional property to bind to
            
        Returns:
            The created subscription
        """
        with self._lock:
            # Create weak reference to component
            component_ref = weakref.ref(component, self._create_cleanup_callback(component))
            
            # Default callback updates component property
            if callback is None and property_name:
                def default_callback(value):
                    comp = component_ref()
                    if comp:
                        setattr(comp, property_name, value)
                callback = default_callback
            elif callback is None:
                def default_callback(value):
                    comp = component_ref()
                    if comp and hasattr(comp, 'update'):
                        comp.update()
                callback = default_callback
            
            # Create subscription
            subscription = Subscription(
                component_ref=component_ref,
                selector=selector,
                callback=callback,
                store_id=store_id,
                property_name=property_name
            )
            
            # Track subscription
            self._subscriptions[store_id].add(subscription)
            
            component_id = id(component)
            if component_id not in self._component_subscriptions:
                self._component_subscriptions[component_id] = set()
            self._component_subscriptions[component_id].add(subscription)
            
            # Get initial value
            if store_id in self._stores:
                try:
                    state = self._get_store_state(store_id)
                    initial_value = selector(state)
                    subscription.last_value = initial_value
                    callback(initial_value)
                except Exception as e:
                    logger.error(f"Error getting initial subscription value: {e}")
            
            return subscription
    
    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove a specific subscription."""
        with self._lock:
            subscription.active = False
            self._subscriptions[subscription.store_id].discard(subscription)
            
            # Clean up component tracking
            component = subscription.component_ref()
            if component:
                component_id = id(component)
                if component_id in self._component_subscriptions:
                    self._component_subscriptions[component_id].discard(subscription)
                    if not self._component_subscriptions[component_id]:
                        del self._component_subscriptions[component_id]
    
    def unsubscribe_component(self, component: Any) -> None:
        """Remove all subscriptions for a component."""
        with self._lock:
            component_id = id(component)
            if component_id in self._component_subscriptions:
                subscriptions = list(self._component_subscriptions[component_id])
                for subscription in subscriptions:
                    self.unsubscribe(subscription)
    
    def notify_change(self, store_id: str, state: Dict[str, Any]) -> None:
        """Notify subscribers of state changes."""
        if self._suspended:
            return
            
        with self._lock:
            if store_id not in self._subscriptions:
                return
            
            # Process subscriptions
            dead_subscriptions = []
            
            for subscription in self._subscriptions[store_id]:
                if not subscription.active:
                    continue
                    
                component = subscription.component_ref()
                if component is None:
                    dead_subscriptions.append(subscription)
                    continue
                
                try:
                    # Calculate new value
                    new_value = subscription.selector(state)
                    
                    # Only notify if value changed
                    if new_value != subscription.last_value:
                        subscription.last_value = new_value
                        subscription.callback(new_value)
                        
                except Exception as e:
                    logger.error(f"Error in subscription callback: {e}")
            
            # Clean up dead subscriptions
            for subscription in dead_subscriptions:
                self.unsubscribe(subscription)
    
    def get_subscriptions_for_component(self, component: Any) -> List[Subscription]:
        """Get all subscriptions for a component."""
        with self._lock:
            component_id = id(component)
            return list(self._component_subscriptions.get(component_id, []))
    
    def get_subscription_count(self, store_id: Optional[str] = None) -> int:
        """Get count of active subscriptions."""
        with self._lock:
            if store_id:
                return len(self._subscriptions.get(store_id, []))
            return sum(len(subs) for subs in self._subscriptions.values())
    
    @contextmanager
    def suspend_notifications(self):
        """Temporarily suspend all notifications."""
        with self._lock:
            old_suspended = self._suspended
            self._suspended = True
        try:
            yield
        finally:
            with self._lock:
                self._suspended = old_suspended
    
    def _create_cleanup_callback(self, component: Any) -> Callable:
        """Create cleanup callback for when component is garbage collected."""
        component_id = id(component)
        
        def cleanup(ref):
            with self._lock:
                if component_id in self._component_subscriptions:
                    subscriptions = list(self._component_subscriptions[component_id])
                    for subscription in subscriptions:
                        self._subscriptions[subscription.store_id].discard(subscription)
                    del self._component_subscriptions[component_id]
        
        return cleanup
    
    def _get_store_state(self, store_id: str) -> Dict[str, Any]:
        """Get current state from a store."""
        store = self._stores.get(store_id)
        if store is None:
            return {}
        
        # Try different methods to get state
        if hasattr(store, 'get_state'):
            return store.get_state()
        elif hasattr(store, 'state'):
            return store.state
        elif isinstance(store, dict):
            return store
        else:
            return {}


# Global subscription manager instance
_subscription_manager = SubscriptionManager()


def get_subscription_manager() -> SubscriptionManager:
    """Get the global subscription manager instance."""
    return _subscription_manager


def bind_state(
    store_id: str,
    selector: Union[str, Callable[[Dict[str, Any]], Any]],
    property_name: Optional[str] = None
):
    """
    Decorator to automatically bind component property to state.
    
    Args:
        store_id: ID of the state store
        selector: State selector function or property path
        property_name: Property to bind to (defaults to method name)
    """
    def decorator(func):
        # Convert string selector to function
        if isinstance(selector, str):
            def string_selector(state):
                keys = selector.split('.')
                value = state
                for key in keys:
                    value = value.get(key, None)
                    if value is None:
                        break
                return value
            actual_selector = string_selector
        else:
            actual_selector = selector
        
        # Store binding info
        func._state_binding = {
            'store_id': store_id,
            'selector': actual_selector,
            'property_name': property_name or func.__name__
        }
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def connect_state(component_class: Type) -> Type:
    """
    Class decorator to automatically connect state bindings.
    
    Processes all @bind_state decorators and sets up subscriptions
    during component initialization.
    """
    original_init = component_class.__init__
    
    def new_init(self, *args, **kwargs):
        # Call original init
        original_init(self, *args, **kwargs)
        
        # Set up state bindings
        manager = get_subscription_manager()
        
        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, '_state_binding'):
                binding = attr._state_binding
                manager.subscribe(
                    component=self,
                    store_id=binding['store_id'],
                    selector=binding['selector'],
                    property_name=binding['property_name']
                )
    
    component_class.__init__ = new_init
    
    # Add cleanup method if not present
    if not hasattr(component_class, '__del__'):
        def __del__(self):
            manager = get_subscription_manager()
            manager.unsubscribe_component(self)
        component_class.__del__ = __del__
    
    return component_class


class StateSubscriptionMixin:
    """Mixin to add state subscription capabilities to components."""
    
    def subscribe_to_state(
        self,
        store_id: str,
        selector: Union[str, Callable[[Dict[str, Any]], Any]],
        callback: Optional[Callable[[Any], None]] = None,
        property_name: Optional[str] = None
    ) -> Subscription:
        """Subscribe to state changes."""
        manager = get_subscription_manager()
        
        # Convert string selector
        if isinstance(selector, str):
            keys = selector.split('.')
            def string_selector(state):
                value = state
                for key in keys:
                    value = value.get(key, None)
                    if value is None:
                        break
                return value
            actual_selector = string_selector
        else:
            actual_selector = selector
        
        return manager.subscribe(
            component=self,
            store_id=store_id,
            selector=actual_selector,
            callback=callback,
            property_name=property_name
        )
    
    def unsubscribe_all(self):
        """Unsubscribe from all state subscriptions."""
        manager = get_subscription_manager()
        manager.unsubscribe_component(self)
    
    def get_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions for this component."""
        manager = get_subscription_manager()
        return manager.get_subscriptions_for_component(self)