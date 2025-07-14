"""
Adapters to harmonize APIs between components.

These adapters provide a consistent interface regardless of the underlying
implementation differences.
"""

from typing import Dict, Any, Optional, List, Callable
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventBusAdapter:
    """
    Adapter for EventBus that provides consistent API regardless of implementation.
    Handles both emit() and publish() patterns.
    """
    
    def __init__(self, event_bus):
        """Initialize with actual EventBus instance."""
        self.event_bus = event_bus
        self._started = False
        
        # Detect which method to use
        if hasattr(event_bus, 'publish'):
            self._publish_method = event_bus.publish
        elif hasattr(event_bus, 'emit'):
            self._publish_method = event_bus.emit
        else:
            raise ValueError("EventBus must have either publish() or emit() method")
    
    async def emit(self, event_type: str, data: Dict[str, Any], priority: str = "normal"):
        """
        Emit an event using consistent API.
        
        Args:
            event_type: Type of event (e.g., "document.uploaded")
            data: Event payload data
            priority: Event priority (immediate, normal, deferred)
        """
        # Start event bus if needed
        if not self._started and hasattr(self.event_bus, 'start'):
            await self.event_bus.start()
            self._started = True
        
        # Create event in the format expected by the actual implementation
        if hasattr(self.event_bus, 'publish'):
            # New format with Event class
            from torematrix.core.events import Event, EventPriority
            
            # Map priority strings to enum if needed
            priority_map = {
                "immediate": EventPriority.IMMEDIATE,
                "normal": EventPriority.NORMAL,
                "deferred": EventPriority.DEFERRED
            }
            
            event = Event(
                event_type=event_type,
                payload=data,
                priority=priority_map.get(priority, EventPriority.NORMAL),
                timestamp=datetime.utcnow()
            )
            await self._publish_method(event)
        else:
            # Old format with dict
            event = {
                "type": event_type,
                "data": data,
                "priority": priority,
                "timestamp": datetime.utcnow()
            }
            await self._publish_method(event)
    
    def subscribe(self, pattern: str, handler: Callable):
        """Subscribe to events with pattern matching."""
        return self.event_bus.subscribe(pattern, handler)
    
    def unsubscribe(self, pattern: str, handler: Callable):
        """Unsubscribe from events."""
        if hasattr(self.event_bus, 'unsubscribe'):
            return self.event_bus.unsubscribe(pattern, handler)
    
    async def stop(self):
        """Stop the event bus if needed."""
        if hasattr(self.event_bus, 'stop'):
            await self.event_bus.stop()


class StorageAdapter:
    """
    Adapter for storage layer that provides consistent API.
    Handles different storage backend implementations.
    """
    
    def __init__(self, storage_backend):
        """Initialize with actual storage backend."""
        self.storage = storage_backend
        
    async def save_element(self, element: Dict[str, Any]) -> str:
        """
        Save an element using consistent API.
        
        Args:
            element: Element data to save
            
        Returns:
            Element ID
        """
        # Determine which method to use
        if hasattr(self.storage, 'create'):
            return await self.storage.create(element)
        elif hasattr(self.storage, 'save'):
            return await self.storage.save(element)
        elif hasattr(self.storage, 'insert'):
            return await self.storage.insert(element)
        else:
            raise ValueError("Storage must have create(), save(), or insert() method")
    
    async def get_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get an element by ID."""
        if hasattr(self.storage, 'get'):
            return await self.storage.get(element_id)
        elif hasattr(self.storage, 'find_by_id'):
            return await self.storage.find_by_id(element_id)
        elif hasattr(self.storage, 'read'):
            return await self.storage.read(element_id)
        else:
            raise ValueError("Storage must have get(), find_by_id(), or read() method")
    
    async def query_elements(self, filter_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query elements with filter."""
        if hasattr(self.storage, 'query'):
            return await self.storage.query(filter_dict)
        elif hasattr(self.storage, 'find'):
            return await self.storage.find(filter_dict)
        elif hasattr(self.storage, 'search'):
            return await self.storage.search(filter_dict)
        else:
            raise ValueError("Storage must have query(), find(), or search() method")
    
    async def update_element(self, element_id: str, updates: Dict[str, Any]) -> bool:
        """Update an element."""
        if hasattr(self.storage, 'update'):
            return await self.storage.update(element_id, updates)
        elif hasattr(self.storage, 'modify'):
            return await self.storage.modify(element_id, updates)
        else:
            # Fallback: get, update, save
            element = await self.get_element(element_id)
            if element:
                element.update(updates)
                await self.save_element(element)
                return True
            return False
    
    async def delete_element(self, element_id: str) -> bool:
        """Delete an element."""
        if hasattr(self.storage, 'delete'):
            return await self.storage.delete(element_id)
        elif hasattr(self.storage, 'remove'):
            return await self.storage.remove(element_id)
        else:
            raise ValueError("Storage must have delete() or remove() method")


class StateAdapter:
    """
    Adapter for state management that provides consistent API.
    Handles both Redux-style and simple state stores.
    """
    
    def __init__(self, state_store):
        """Initialize with actual state store."""
        self.store = state_store
        self._is_redux_style = hasattr(state_store, 'dispatch')
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state."""
        if hasattr(self.store, 'get_state'):
            return self.store.get_state()
        elif hasattr(self.store, 'state'):
            return self.store.state
        else:
            return {}
    
    async def update_state(self, updates: Dict[str, Any]):
        """Update state with new values."""
        if self._is_redux_style:
            # Redux style with actions
            from torematrix.core.state import create_action
            action = create_action("UPDATE_STATE", updates)
            await self.store.dispatch(action)
        elif hasattr(self.store, 'update'):
            # Simple update method
            await self.store.update(updates)
        elif hasattr(self.store, 'set_state'):
            # Set state method
            current = self.get_state()
            current.update(updates)
            self.store.set_state(current)
        else:
            raise ValueError("State store must support dispatch(), update(), or set_state()")
    
    def subscribe(self, callback: Callable):
        """Subscribe to state changes."""
        if hasattr(self.store, 'subscribe'):
            return self.store.subscribe(callback)
        elif hasattr(self.store, 'on_change'):
            return self.store.on_change(callback)
        elif hasattr(self.store, 'add_listener'):
            return self.store.add_listener(callback)
    
    def select(self, path: str, default=None):
        """Select value from state by path."""
        if hasattr(self.store, 'select'):
            return self.store.select(path)
        else:
            # Manual path traversal
            state = self.get_state()
            parts = path.split('.')
            value = state
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            
            return value


class ConfigAdapter:
    """
    Adapter for configuration that provides consistent API.
    """
    
    def __init__(self, config_manager):
        """Initialize with actual config manager."""
        self.config = config_manager
    
    def get(self, key: str, default=None):
        """Get configuration value by key."""
        if hasattr(self.config, 'get'):
            return self.config.get(key, default=default)
        elif hasattr(self.config, 'get_value'):
            return self.config.get_value(key, default)
        elif hasattr(self.config, '__getitem__'):
            try:
                # Navigate nested keys
                parts = key.split('.')
                value = self.config
                for part in parts:
                    value = value[part]
                return value
            except (KeyError, TypeError):
                return default
        else:
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        if hasattr(self.config, 'set'):
            self.config.set(key, value)
        elif hasattr(self.config, 'set_value'):
            self.config.set_value(key, value)
        elif hasattr(self.config, '__setitem__'):
            # Navigate nested keys
            parts = key.split('.')
            if len(parts) == 1:
                self.config[key] = value
            else:
                # Create nested structure
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
    
    def load_from_dict(self, config_dict: Dict[str, Any]):
        """Load configuration from dictionary."""
        if hasattr(self.config, 'load_from_dict'):
            self.config.load_from_dict(config_dict)
        elif hasattr(self.config, 'update'):
            self.config.update(config_dict)
        elif hasattr(self.config, 'merge'):
            self.config.merge(config_dict)
        else:
            # Manual update
            for key, value in config_dict.items():
                self.set(key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        if hasattr(self.config, 'to_dict'):
            return self.config.to_dict()
        elif hasattr(self.config, 'as_dict'):
            return self.config.as_dict()
        elif isinstance(self.config, dict):
            return dict(self.config)
        else:
            # Try to extract all config
            return {
                key: self.get(key)
                for key in dir(self.config)
                if not key.startswith('_')
            }