"""
Event System for Document Viewer Selection.
This module provides a comprehensive event system for selection changes,
mode changes, and other selection-related events with filtering and throttling.
"""
from __future__ import annotations

import asyncio
import time
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from .selection import SelectionState, SelectionMode


class EventType(Enum):
    """Types of selection events."""
    SELECTION_CHANGED = "selection_changed"
    SELECTION_CLEARED = "selection_cleared"
    ELEMENT_SELECTED = "element_selected"
    ELEMENT_DESELECTED = "element_deselected"
    MODE_CHANGED = "mode_changed"
    SELECTION_STARTED = "selection_started"
    SELECTION_ENDED = "selection_ended"
    SELECTION_CANCELLED = "selection_cancelled"
    HOVER_STARTED = "hover_started"
    HOVER_ENDED = "hover_ended"
    VALIDATION_FAILED = "validation_failed"


class EventPriority(Enum):
    """Priority levels for events."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class SelectionEvent:
    """Base class for selection events."""
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class SelectionChangedEvent(SelectionEvent):
    """Event for selection changes."""
    old_selection: Set[str] = field(default_factory=set)
    new_selection: Set[str] = field(default_factory=set)
    added_elements: Set[str] = field(default_factory=set)
    removed_elements: Set[str] = field(default_factory=set)
    selection_state: Optional[SelectionState] = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.added_elements and not self.removed_elements:
            self.added_elements = self.new_selection - self.old_selection
            self.removed_elements = self.old_selection - self.new_selection


@dataclass
class ElementEvent(SelectionEvent):
    """Event for individual element actions."""
    element_id: str = ""
    element_bounds: Optional[Dict[str, float]] = None
    element_type: Optional[str] = None


@dataclass
class ModeChangedEvent(SelectionEvent):
    """Event for selection mode changes."""
    old_mode: SelectionMode = SelectionMode.SINGLE
    new_mode: SelectionMode = SelectionMode.SINGLE


@dataclass
class ValidationEvent(SelectionEvent):
    """Event for validation failures."""
    validation_errors: List[str] = field(default_factory=list)
    failed_elements: List[str] = field(default_factory=list)


class EventFilter(ABC):
    """Abstract base class for event filters."""
    
    @abstractmethod
    def should_process(self, event: SelectionEvent) -> bool:
        """Determine if event should be processed."""
        pass


class EventTypeFilter(EventFilter):
    """Filter events by type."""
    
    def __init__(self, allowed_types: Set[EventType]):
        self.allowed_types = allowed_types
    
    def should_process(self, event: SelectionEvent) -> bool:
        return event.event_type in self.allowed_types


class EventPriorityFilter(EventFilter):
    """Filter events by priority."""
    
    def __init__(self, min_priority: EventPriority):
        self.min_priority = min_priority
    
    def should_process(self, event: SelectionEvent) -> bool:
        return event.priority.value >= self.min_priority.value


class EventSourceFilter(EventFilter):
    """Filter events by source."""
    
    def __init__(self, allowed_sources: Set[str]):
        self.allowed_sources = allowed_sources
    
    def should_process(self, event: SelectionEvent) -> bool:
        return event.source in self.allowed_sources or event.source is None


class EventThrottler:
    """Throttle events to prevent flooding."""
    
    def __init__(self, max_events_per_second: int = 60):
        self.max_events_per_second = max_events_per_second
        self.event_times = deque()
        self.throttled_events = {}
        self.min_interval = 1.0 / max_events_per_second
    
    def should_throttle(self, event: SelectionEvent) -> bool:
        """Check if event should be throttled."""
        now = time.time()
        
        # Clean old timestamps
        while self.event_times and self.event_times[0] < now - 1.0:
            self.event_times.popleft()
        
        # Check if we're at the limit
        if len(self.event_times) >= self.max_events_per_second:
            return True
        
        # Check minimum interval for same event type
        event_key = f"{event.event_type.value}_{event.source}"
        last_time = self.throttled_events.get(event_key, 0)
        
        if now - last_time < self.min_interval:
            return True
        
        # Record this event
        self.event_times.append(now)
        self.throttled_events[event_key] = now
        
        return False


class EventBuffer:
    """Buffer for batching events."""
    
    def __init__(self, max_size: int = 100, flush_interval: float = 0.1):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.buffer: List[SelectionEvent] = []
        self.last_flush = time.time()
        self.flush_callbacks: List[Callable] = []
    
    def add_event(self, event: SelectionEvent) -> None:
        """Add event to buffer."""
        self.buffer.append(event)
        
        # Check if we need to flush
        if (len(self.buffer) >= self.max_size or 
            time.time() - self.last_flush >= self.flush_interval):
            self.flush()
    
    def flush(self) -> List[SelectionEvent]:
        """Flush buffered events."""
        if not self.buffer:
            return []
        
        events = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = time.time()
        
        # Notify flush callbacks
        for callback in self.flush_callbacks:
            try:
                callback(events)
            except Exception as e:
                print(f"Error in flush callback: {e}")
        
        return events
    
    def add_flush_callback(self, callback: Callable) -> None:
        """Add callback for when buffer is flushed."""
        self.flush_callbacks.append(callback)


class EventListener:
    """Represents an event listener with metadata."""
    
    def __init__(self, callback: Callable, filters: List[EventFilter] = None, 
                 weak_ref: bool = True, priority: int = 0):
        self.callback_ref = weakref.ref(callback) if weak_ref else callback
        self.filters = filters or []
        self.weak_ref = weak_ref
        self.priority = priority
        self.call_count = 0
        self.last_called = 0
        self.total_time = 0
    
    def get_callback(self) -> Optional[Callable]:
        """Get the callback function."""
        if self.weak_ref:
            callback = self.callback_ref()
            return callback if callback is not None else None
        return self.callback_ref
    
    def should_process(self, event: SelectionEvent) -> bool:
        """Check if this listener should process the event."""
        return all(f.should_process(event) for f in self.filters)
    
    def invoke(self, event: SelectionEvent) -> None:
        """Invoke the callback with the event."""
        callback = self.get_callback()
        if callback is None:
            return
        
        start_time = time.time()
        try:
            callback(event)
            self.call_count += 1
            self.last_called = start_time
            self.total_time += time.time() - start_time
        except Exception as e:
            print(f"Error in event callback: {e}")
    
    def is_alive(self) -> bool:
        """Check if the listener is still valid."""
        if self.weak_ref:
            return self.callback_ref() is not None
        return True


class SelectionEventManager:
    """
    Comprehensive event management system for selection events.
    
    Provides event publishing, subscription, filtering, throttling, and batching
    capabilities for all selection-related events.
    """
    
    def __init__(self):
        self.listeners: Dict[EventType, List[EventListener]] = defaultdict(list)
        self.global_listeners: List[EventListener] = []
        self.event_history: List[SelectionEvent] = []
        self.max_history = 1000
        
        # Event processing components
        self.throttler = EventThrottler()
        self.buffer = EventBuffer()
        self.global_filters: List[EventFilter] = []
        
        # Statistics
        self.event_stats = {
            'total_events': 0,
            'throttled_events': 0,
            'buffered_events': 0,
            'failed_events': 0
        }
        
        # Async processing
        self.async_processing = False
        self.async_queue = asyncio.Queue() if asyncio.iscoroutinefunction else None
    
    def subscribe(self, event_type: EventType, callback: Callable, 
                  filters: List[EventFilter] = None, priority: int = 0) -> str:
        """Subscribe to a specific event type."""
        listener = EventListener(callback, filters, priority=priority)
        self.listeners[event_type].append(listener)
        
        # Sort by priority
        self.listeners[event_type].sort(key=lambda x: x.priority, reverse=True)
        
        return listener.callback_ref.__name__ if hasattr(listener.callback_ref, '__name__') else str(id(listener))
    
    def subscribe_global(self, callback: Callable, filters: List[EventFilter] = None, 
                        priority: int = 0) -> str:
        """Subscribe to all events."""
        listener = EventListener(callback, filters, priority=priority)
        self.global_listeners.append(listener)
        
        # Sort by priority
        self.global_listeners.sort(key=lambda x: x.priority, reverse=True)
        
        return str(id(listener))
    
    def unsubscribe(self, event_type: EventType, callback_or_id: Union[Callable, str]) -> bool:
        """Unsubscribe from an event type."""
        listeners = self.listeners.get(event_type, [])
        
        for i, listener in enumerate(listeners):
            callback = listener.get_callback()
            if (callback == callback_or_id or 
                str(id(listener)) == callback_or_id or
                (hasattr(callback, '__name__') and callback.__name__ == callback_or_id)):
                listeners.pop(i)
                return True
        
        return False
    
    def unsubscribe_global(self, callback_or_id: Union[Callable, str]) -> bool:
        """Unsubscribe from global events."""
        for i, listener in enumerate(self.global_listeners):
            callback = listener.get_callback()
            if (callback == callback_or_id or 
                str(id(listener)) == callback_or_id):
                self.global_listeners.pop(i)
                return True
        
        return False
    
    def publish(self, event: SelectionEvent) -> None:
        """Publish an event to all subscribers."""
        self.event_stats['total_events'] += 1
        
        # Apply global filters
        for filter_obj in self.global_filters:
            if not filter_obj.should_process(event):
                return
        
        # Check throttling
        if self.throttler.should_throttle(event):
            self.event_stats['throttled_events'] += 1
            return
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Process event
        try:
            self._process_event(event)
        except Exception as e:
            self.event_stats['failed_events'] += 1
            print(f"Error processing event: {e}")
    
    def _process_event(self, event: SelectionEvent) -> None:
        """Process an event through all listeners."""
        # Clean up dead listeners
        self._cleanup_dead_listeners()
        
        # Process global listeners first
        for listener in self.global_listeners:
            if listener.should_process(event):
                listener.invoke(event)
        
        # Process specific event type listeners
        for listener in self.listeners.get(event.event_type, []):
            if listener.should_process(event):
                listener.invoke(event)
    
    def _cleanup_dead_listeners(self) -> None:
        """Remove dead weak references."""
        for event_type in list(self.listeners.keys()):
            self.listeners[event_type] = [
                listener for listener in self.listeners[event_type] 
                if listener.is_alive()
            ]
        
        self.global_listeners = [
            listener for listener in self.global_listeners 
            if listener.is_alive()
        ]
    
    def add_global_filter(self, filter_obj: EventFilter) -> None:
        """Add a global event filter."""
        self.global_filters.append(filter_obj)
    
    def remove_global_filter(self, filter_obj: EventFilter) -> None:
        """Remove a global event filter."""
        if filter_obj in self.global_filters:
            self.global_filters.remove(filter_obj)
    
    def get_event_history(self, event_type: Optional[EventType] = None, 
                         limit: int = 100) -> List[SelectionEvent]:
        """Get event history, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self.event_history if e.event_type == event_type]
        else:
            filtered = self.event_history
        
        return filtered[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event system statistics."""
        stats = self.event_stats.copy()
        stats['active_listeners'] = sum(len(listeners) for listeners in self.listeners.values())
        stats['global_listeners'] = len(self.global_listeners)
        stats['history_size'] = len(self.event_history)
        
        # Add listener performance stats
        all_listeners = []
        for listeners in self.listeners.values():
            all_listeners.extend(listeners)
        all_listeners.extend(self.global_listeners)
        
        if all_listeners:
            stats['listener_performance'] = {
                'total_calls': sum(l.call_count for l in all_listeners),
                'average_time': sum(l.total_time for l in all_listeners) / len(all_listeners),
                'most_active': max(all_listeners, key=lambda l: l.call_count).call_count
            }
        
        return stats
    
    def clear_history(self) -> None:
        """Clear event history."""
        self.event_history.clear()
    
    def reset_statistics(self) -> None:
        """Reset event statistics."""
        self.event_stats = {
            'total_events': 0,
            'throttled_events': 0,
            'buffered_events': 0,
            'failed_events': 0
        }


class SelectionEventFactory:
    """Factory for creating selection events."""
    
    @staticmethod
    def create_selection_changed(old_selection: Set[str], new_selection: Set[str], 
                               selection_state: Optional[SelectionState] = None,
                               source: Optional[str] = None) -> SelectionChangedEvent:
        """Create a selection changed event."""
        return SelectionChangedEvent(
            event_type=EventType.SELECTION_CHANGED,
            old_selection=old_selection,
            new_selection=new_selection,
            selection_state=selection_state,
            source=source
        )
    
    @staticmethod
    def create_element_selected(element_id: str, source: Optional[str] = None) -> ElementEvent:
        """Create an element selected event."""
        return ElementEvent(
            event_type=EventType.ELEMENT_SELECTED,
            element_id=element_id,
            source=source
        )
    
    @staticmethod
    def create_element_deselected(element_id: str, source: Optional[str] = None) -> ElementEvent:
        """Create an element deselected event."""
        return ElementEvent(
            event_type=EventType.ELEMENT_DESELECTED,
            element_id=element_id,
            source=source
        )
    
    @staticmethod
    def create_mode_changed(old_mode: SelectionMode, new_mode: SelectionMode, 
                          source: Optional[str] = None) -> ModeChangedEvent:
        """Create a mode changed event."""
        return ModeChangedEvent(
            event_type=EventType.MODE_CHANGED,
            old_mode=old_mode,
            new_mode=new_mode,
            source=source
        )
    
    @staticmethod
    def create_validation_failed(errors: List[str], failed_elements: List[str], 
                               source: Optional[str] = None) -> ValidationEvent:
        """Create a validation failed event."""
        return ValidationEvent(
            event_type=EventType.VALIDATION_FAILED,
            validation_errors=errors,
            failed_elements=failed_elements,
            source=source,
            priority=EventPriority.HIGH
        )


# Global event manager instance
_global_event_manager = SelectionEventManager()


def get_event_manager() -> SelectionEventManager:
    """Get the global event manager instance."""
    return _global_event_manager


# Convenience functions
def publish_selection_changed(old_selection: Set[str], new_selection: Set[str], 
                            selection_state: Optional[SelectionState] = None,
                            source: Optional[str] = None) -> None:
    """Publish a selection changed event."""
    event = SelectionEventFactory.create_selection_changed(
        old_selection, new_selection, selection_state, source
    )
    _global_event_manager.publish(event)


def subscribe_to_selection_changes(callback: Callable, filters: List[EventFilter] = None) -> str:
    """Subscribe to selection change events."""
    return _global_event_manager.subscribe(EventType.SELECTION_CHANGED, callback, filters)


# Export main classes
__all__ = [
    'EventType',
    'EventPriority',
    'SelectionEvent',
    'SelectionChangedEvent',
    'ElementEvent',
    'ModeChangedEvent',
    'ValidationEvent',
    'EventFilter',
    'EventTypeFilter',
    'EventPriorityFilter',
    'EventSourceFilter',
    'EventThrottler',
    'EventBuffer',
    'EventListener',
    'SelectionEventManager',
    'SelectionEventFactory',
    'get_event_manager',
    'publish_selection_changed',
    'subscribe_to_selection_changes'
]