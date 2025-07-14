"""
Core Store implementation for state management.

This module provides the central Store class that manages application state,
handles action dispatching, and notifies subscribers of state changes.
"""

import threading
import time
from typing import Dict, Any, Callable, List, Optional
from functools import reduce
import logging
from copy import deepcopy

from .types import (
    State, StoreConfig, MiddlewareType, SubscriberType, 
    UnsubscribeType, StateChange
)
from .actions import Action, ActionValidator, init_store
from .reducers import create_root_reducer

logger = logging.getLogger(__name__)


class Store:
    """
    Central state store implementing Redux pattern.
    
    The Store manages application state and provides methods to:
    - Dispatch actions to update state
    - Subscribe to state changes
    - Add middleware for action processing
    - Get current state snapshot
    """
    
    def __init__(self, config: StoreConfig):
        """
        Initialize the Store.
        
        Args:
            config: Store configuration including initial state, reducer, and middleware
        """
        self._lock = threading.RLock()
        self._state = config.initial_state or {}
        self._reducer = config.reducer or create_root_reducer()
        self._subscribers: List[SubscriberType] = []
        self._middleware: List[MiddlewareType] = []
        self._event_bus = config.event_bus
        self._is_dispatching = False
        self._action_history: List[Action] = []
        
        # Setup middleware
        if config.middleware:
            for middleware in config.middleware:
                self.add_middleware(middleware)
        
        # Compose dispatch chain
        self._dispatch = self._create_dispatch_chain()
        
        # Initialize store
        self.dispatch(init_store())
    
    def dispatch(self, action: Action) -> Action:
        """
        Dispatch an action to update state.
        
        Args:
            action: Action to dispatch
            
        Returns:
            The dispatched action
            
        Raises:
            RuntimeError: If dispatch is called while already dispatching
            ValueError: If action is invalid
        """
        # Validate action
        ActionValidator.validate(action)
        
        # Prevent recursive dispatching
        if self._is_dispatching:
            raise RuntimeError("Cannot dispatch while dispatching")
        
        # Dispatch through middleware chain
        return self._dispatch(action)
    
    def get_state(self) -> State:
        """
        Get current state snapshot.
        
        Returns:
            Deep copy of current state
        """
        with self._lock:
            return deepcopy(self._state)
    
    def subscribe(self, callback: SubscriberType) -> UnsubscribeType:
        """
        Subscribe to state changes.
        
        Args:
            callback: Function to call when state changes
            
        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.append(callback)
        
        # Return unsubscribe function
        def unsubscribe():
            with self._lock:
                try:
                    self._subscribers.remove(callback)
                except ValueError:
                    pass  # Already unsubscribed
        
        return unsubscribe
    
    def add_middleware(self, middleware: MiddlewareType) -> None:
        """
        Add middleware to the store.
        
        Middleware must be added before first dispatch.
        
        Args:
            middleware: Middleware function
            
        Raises:
            RuntimeError: If middleware is added after dispatching
        """
        if self._action_history:
            raise RuntimeError("Cannot add middleware after dispatching actions")
        
        self._middleware.append(middleware)
        self._dispatch = self._create_dispatch_chain()
    
    def replace_reducer(self, reducer: Callable) -> None:
        """
        Replace the root reducer.
        
        Useful for hot reloading and code splitting.
        
        Args:
            reducer: New root reducer
        """
        with self._lock:
            self._reducer = reducer
            # Dispatch a special action to initialize new reducer
            self.dispatch(Action(type="@@REDUCER_REPLACED"))
    
    def _create_dispatch_chain(self) -> Callable:
        """Create the middleware dispatch chain."""
        # Base dispatch function
        def base_dispatch(action: Action) -> Action:
            return self._base_dispatch(action)
        
        # Build middleware chain
        chain = base_dispatch
        for middleware in reversed(self._middleware):
            middleware_func = middleware(self)
            chain = middleware_func(chain)
        
        return chain
    
    def _base_dispatch(self, action: Action) -> Action:
        """
        Base dispatch implementation.
        
        This is the core dispatch logic that:
        1. Updates state through reducer
        2. Notifies subscribers
        3. Emits events to event bus
        """
        with self._lock:
            self._is_dispatching = True
            
            try:
                # Save previous state
                prev_state = self._state
                
                # Update state through reducer
                self._state = self._reducer(self._state, action)
                
                # Record action in history
                self._action_history.append(action)
                
                # Create state change event
                state_change = StateChange(
                    old_state=prev_state,
                    new_state=self._state,
                    action=action,
                    timestamp=time.time()
                )
                
                # Only notify if state actually changed
                if state_change.has_changed:
                    self._notify_subscribers()
                    self._emit_state_change(state_change)
                
                return action
                
            finally:
                self._is_dispatching = False
    
    def _notify_subscribers(self) -> None:
        """Notify all subscribers of state change."""
        # Get current subscribers (copy to avoid issues if subscriber list changes)
        subscribers = list(self._subscribers)
        current_state = self._state
        
        # Notify each subscriber
        for subscriber in subscribers:
            try:
                subscriber(current_state)
            except Exception as e:
                logger.error(f"Error in subscriber: {e}")
    
    def _emit_state_change(self, state_change: StateChange) -> None:
        """Emit state change event to event bus if configured."""
        if self._event_bus:
            try:
                # Import here to avoid circular dependency
                from ..events import Event as EventBusEvent
                
                # Create state change event
                event = EventBusEvent(
                    event_type="STATE_CHANGED",
                    payload={
                        'old_state': state_change.old_state,
                        'new_state': state_change.new_state,
                        'action': {
                            'type': str(state_change.action.type),
                            'payload': state_change.action.payload
                        }
                    }
                )
                
                # Publish to event bus
                self._event_bus.publish(event)
                
            except Exception as e:
                logger.error(f"Error emitting state change: {e}")
    
    # Convenience methods for common operations
    
    def select(self, selector: Callable[[State], Any]) -> Any:
        """
        Select data from state using a selector function.
        
        Args:
            selector: Function that extracts data from state
            
        Returns:
            Selected data
        """
        return selector(self.get_state())
    
    def get_action_history(self) -> List[Action]:
        """
        Get action history.
        
        Returns:
            List of all dispatched actions
        """
        with self._lock:
            return list(self._action_history)
    
    def clear_action_history(self) -> None:
        """Clear action history."""
        with self._lock:
            self._action_history.clear()
    
    @property
    def is_dispatching(self) -> bool:
        """Check if currently dispatching."""
        return self._is_dispatching
    
    def __repr__(self) -> str:
        """String representation of store."""
        return f"<Store subscribers={len(self._subscribers)} middleware={len(self._middleware)}>"