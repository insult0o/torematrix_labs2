"""
Event Bus integration for bidirectional state synchronization.
"""

from typing import Dict, Any, Callable, Optional, Set
import logging
import time
from dataclasses import dataclass
from ...events.event_bus import EventBus
from ...events.event_types import Event

logger = logging.getLogger(__name__)


@dataclass
class StateUpdateEvent(Event):
    """Event for requesting state updates."""
    event_type: str = "STATE_UPDATE_REQUEST"
    payload: Dict[str, Any] = None
    path: str = ""
    value: Any = None
    
    def __post_init__(self):
        if self.payload is None:
            self.payload = {'path': self.path, 'value': self.value}


@dataclass  
class StateChangeEvent(Event):
    """Event emitted when state changes."""
    event_type: str = "STATE_CHANGED"
    payload: Dict[str, Any] = None
    action: Any = None
    state_before: Dict[str, Any] = None
    state_after: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.payload is None:
            self.payload = {
                'action': self.action,
                'state_before': self.state_before,
                'state_after': self.state_after
            }


class EventBusIntegration:
    """
    Bidirectional integration between state management and Event Bus.
    
    Features:
    - State changes trigger events
    - Events can trigger state updates
    - Selective event filtering
    - Event replay for state reconstruction
    """
    
    def __init__(self, event_bus: EventBus, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Event Bus integration.
        
        Args:
            event_bus: Event Bus instance to integrate with
            config: Configuration options
        """
        self.event_bus = event_bus
        self.config = config or {}
        self._action_handlers: Dict[str, Callable] = {}
        self._subscriptions: Set[str] = set()
        self._sync_enabled = True
        self._stats = {
            'events_sent': 0,
            'events_received': 0,
            'sync_errors': 0,
            'last_sync': None
        }
    
    def create_middleware(self):
        """
        Create middleware for Event Bus integration.
        
        Returns:
            Middleware function that integrates with the store
        """
        def middleware(store):
            # Set up event subscriptions
            self._setup_subscriptions(store)
            
            def next_middleware(next_dispatch):
                def dispatch(action):
                    # Dispatch action normally
                    result = next_dispatch(action)
                    
                    if self._sync_enabled:
                        try:
                            # Emit state change event
                            self._emit_state_change_event(store, action)
                            self._stats['events_sent'] += 1
                            self._stats['last_sync'] = time.time()
                        except Exception as e:
                            logger.error(f"Error emitting state change event: {e}")
                            self._stats['sync_errors'] += 1
                    
                    return result
                return dispatch
            return next_middleware
        return middleware
    
    def _setup_subscriptions(self, store):
        """Set up Event Bus subscriptions for state updates."""
        # Subscribe to state update requests
        if "STATE_UPDATE_REQUEST" not in self._subscriptions:
            self.event_bus.subscribe(
                "STATE_UPDATE_REQUEST",
                lambda event: self._handle_state_update_request(store, event)
            )
            self._subscriptions.add("STATE_UPDATE_REQUEST")
        
        # Subscribe to other configured events
        event_mappings = self.config.get('event_mappings', {})
        for event_type, handler_name in event_mappings.items():
            if event_type not in self._subscriptions:
                handler = self._action_handlers.get(handler_name)
                if handler:
                    self.event_bus.subscribe(
                        event_type,
                        lambda event, h=handler: self._handle_external_event(store, event, h)
                    )
                    self._subscriptions.add(event_type)
    
    def _emit_state_change_event(self, store, action):
        """Emit an event when state changes."""
        # Get state before and after (simplified - would need actual before state)
        state_after = store.get_state()
        
        event = StateChangeEvent(
            action=action,
            state_before={},  # Would need to track this properly
            state_after=state_after,
            timestamp=time.time()
        )
        
        self.event_bus.publish(event)
        logger.debug(f"Emitted state change event for action: {action.type}")
    
    def _handle_state_update_request(self, store, event: StateUpdateEvent):
        """Handle external requests to update state."""
        try:
            self._stats['events_received'] += 1
            
            # Create action from event
            action = self._create_action_from_event(event)
            
            if action:
                # Temporarily disable sync to avoid loops
                self._sync_enabled = False
                try:
                    store.dispatch(action)
                finally:
                    self._sync_enabled = True
                
                logger.debug(f"Handled state update request: {event.path}")
            
        except Exception as e:
            logger.error(f"Error handling state update request: {e}")
            self._stats['sync_errors'] += 1
    
    def _handle_external_event(self, store, event: Event, handler: Callable):
        """Handle external events with custom handlers."""
        try:
            self._stats['events_received'] += 1
            
            # Call custom handler
            action = handler(event)
            
            if action:
                # Temporarily disable sync to avoid loops
                self._sync_enabled = False
                try:
                    store.dispatch(action)
                finally:
                    self._sync_enabled = True
                
                logger.debug(f"Handled external event: {event.type}")
            
        except Exception as e:
            logger.error(f"Error handling external event: {e}")
            self._stats['sync_errors'] += 1
    
    def _create_action_from_event(self, event: StateUpdateEvent):
        """Create a state action from an event."""
        # This would depend on your action structure
        # Simplified implementation
        class StateUpdateAction:
            def __init__(self, path: str, value: Any):
                self.type = "UPDATE_STATE"
                self.payload = {'path': path, 'value': value}
        
        return StateUpdateAction(event.path, event.value)
    
    def register_action_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for converting events to actions.
        
        Args:
            event_type: Type of event to handle
            handler: Function that converts event to action
        """
        self._action_handlers[event_type] = handler
        logger.debug(f"Registered action handler for event type: {event_type}")
    
    def sync_with_event_bus(self, store):
        """
        Set up bidirectional synchronization between store and Event Bus.
        
        Args:
            store: Store instance to sync with
        """
        # This would set up more comprehensive sync
        self._setup_subscriptions(store)
        
        # Optionally replay events to rebuild state
        if self.config.get('replay_on_sync', False):
            self._replay_events(store)
        
        logger.info("Event Bus synchronization established")
    
    def _replay_events(self, store):
        """Replay events to rebuild state."""
        # This would replay events from Event Bus history
        # Implementation depends on Event Bus capabilities
        pass
    
    def enable_sync(self):
        """Enable bidirectional synchronization."""
        self._sync_enabled = True
        logger.debug("Event Bus sync enabled")
    
    def disable_sync(self):
        """Disable bidirectional synchronization."""
        self._sync_enabled = False
        logger.debug("Event Bus sync disabled")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        return dict(self._stats)
    
    def cleanup(self):
        """Clean up subscriptions and resources."""
        for event_type in self._subscriptions:
            # Unsubscribe from events
            # Note: EventBus would need an unsubscribe method
            pass
        
        self._subscriptions.clear()
        self._action_handlers.clear()
        logger.debug("Event Bus integration cleaned up")