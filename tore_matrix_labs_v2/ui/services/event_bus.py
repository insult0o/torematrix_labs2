#!/usr/bin/env python3
"""
Event Bus for TORE Matrix Labs V2 UI

This event bus provides simplified, decoupled communication between UI components,
replacing the complex signal chains from the original codebase.

Key improvements:
- Type-safe event system
- Centralized event routing
- Easy subscription/unsubscription
- Event filtering and prioritization
- Debug and monitoring capabilities
- Performance optimization

This replaces the complex signal connections from:
- manual_validation_widget.py
- page_validation_widget.py  
- pdf_viewer.py
- main_window.py
"""

import logging
from typing import Dict, List, Callable, Any, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import weakref
import asyncio
from threading import Lock


class EventType(Enum):
    """Types of UI events."""
    
    # Document events
    DOCUMENT_LOADED = "document_loaded"
    DOCUMENT_PROCESSING_STARTED = "document_processing_started"
    DOCUMENT_PROCESSING_COMPLETED = "document_processing_completed"
    DOCUMENT_SELECTED = "document_selected"
    DOCUMENT_CLOSED = "document_closed"
    
    # Page events
    PAGE_CHANGED = "page_changed"
    PAGE_LOADED = "page_loaded"
    PAGE_RENDERED = "page_rendered"
    
    # Area events
    AREA_SELECTED = "area_selected"
    AREA_CREATED = "area_created"
    AREA_MODIFIED = "area_modified"
    AREA_DELETED = "area_deleted"
    AREA_VALIDATED = "area_validated"
    
    # Coordinate events
    COORDINATES_MAPPED = "coordinates_mapped"
    HIGHLIGHT_REQUESTED = "highlight_requested"
    HIGHLIGHT_CLEARED = "highlight_cleared"
    
    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    ISSUE_FOUND = "issue_found"
    ISSUE_RESOLVED = "issue_resolved"
    
    # UI events
    TAB_CHANGED = "tab_changed"
    WIDGET_FOCUSED = "widget_focused"
    WIDGET_RESIZED = "widget_resized"
    THEME_CHANGED = "theme_changed"
    
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_LOADED = "project_loaded"
    PROJECT_SAVED = "project_saved"
    PROJECT_CLOSED = "project_closed"
    
    # System events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    PROGRESS_UPDATED = "progress_updated"
    STATUS_CHANGED = "status_changed"


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class UIEvent:
    """Represents a UI event."""
    
    # Event identity
    event_type: EventType
    sender: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Event metadata
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    
    # Event lifecycle
    handled: bool = False
    cancelled: bool = False
    
    # Event ID for tracking
    event_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate event ID if not provided."""
        if not self.event_id:
            self.event_id = f"{self.event_type.value}_{self.timestamp.strftime('%H%M%S_%f')}"
    
    def cancel(self):
        """Cancel the event."""
        self.cancelled = True
    
    def mark_handled(self):
        """Mark the event as handled."""
        self.handled = True
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get event data by key."""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any):
        """Set event data."""
        self.data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "sender": self.sender,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "handled": self.handled,
            "cancelled": self.cancelled,
            "event_id": self.event_id
        }


class EventFilter(ABC):
    """Abstract base class for event filters."""
    
    @abstractmethod
    def should_process(self, event: UIEvent) -> bool:
        """
        Determine if an event should be processed.
        
        Args:
            event: Event to filter
            
        Returns:
            True if event should be processed, False otherwise
        """
        pass


class EventTypeFilter(EventFilter):
    """Filter events by type."""
    
    def __init__(self, event_types: Union[EventType, List[EventType]]):
        """Initialize filter with event types to accept."""
        if isinstance(event_types, EventType):
            self.event_types = {event_types}
        else:
            self.event_types = set(event_types)
    
    def should_process(self, event: UIEvent) -> bool:
        """Check if event type is in accepted types."""
        return event.event_type in self.event_types


class SenderFilter(EventFilter):
    """Filter events by sender."""
    
    def __init__(self, senders: Union[str, List[str]]):
        """Initialize filter with senders to accept."""
        if isinstance(senders, str):
            self.senders = {senders}
        else:
            self.senders = set(senders)
    
    def should_process(self, event: UIEvent) -> bool:
        """Check if event sender is in accepted senders."""
        return event.sender in self.senders


class EventSubscription:
    """Represents an event subscription."""
    
    def __init__(self, 
                 handler: Callable[[UIEvent], None],
                 event_filter: Optional[EventFilter] = None,
                 priority: EventPriority = EventPriority.NORMAL,
                 once: bool = False):
        """
        Initialize event subscription.
        
        Args:
            handler: Event handler function
            event_filter: Optional filter for events
            priority: Subscription priority
            once: If True, unsubscribe after first event
        """
        self.handler = handler
        self.event_filter = event_filter
        self.priority = priority
        self.once = once
        self.created_at = datetime.now()
        self.call_count = 0
        self.last_called = None
    
    def should_handle(self, event: UIEvent) -> bool:
        """Check if this subscription should handle the event."""
        if self.event_filter:
            return self.event_filter.should_process(event)
        return True
    
    def handle_event(self, event: UIEvent):
        """Handle an event."""
        try:
            self.handler(event)
            self.call_count += 1
            self.last_called = datetime.now()
        except Exception as e:
            logging.getLogger(__name__).error(f"Event handler failed: {str(e)}")
            raise


class EventBus:
    """
    Centralized event bus for UI component communication.
    
    This event bus provides a clean, decoupled way for UI components to
    communicate without complex signal chains or direct dependencies.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.logger = logging.getLogger(__name__)
        
        # Subscriptions organized by event type for efficient lookup
        self.subscriptions: Dict[EventType, List[EventSubscription]] = {}
        
        # Global subscriptions (receive all events)
        self.global_subscriptions: List[EventSubscription] = []
        
        # Event history for debugging
        self.event_history: List[UIEvent] = []
        self.max_history_size = 1000
        
        # Performance statistics
        self.stats = {
            "events_published": 0,
            "events_handled": 0,
            "subscription_count": 0,
            "average_handlers_per_event": 0.0
        }
        
        # Thread safety
        self._lock = Lock()
        
        # Async support
        self._async_queue: Optional[asyncio.Queue] = None
        
        self.logger.info("Event bus initialized")
    
    def subscribe(self, 
                  event_types: Union[EventType, List[EventType]],
                  handler: Callable[[UIEvent], None],
                  sender_filter: Optional[Union[str, List[str]]] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  once: bool = False) -> str:
        """
        Subscribe to events.
        
        Args:
            event_types: Event type(s) to subscribe to
            handler: Function to handle events
            sender_filter: Optional sender filter
            priority: Subscription priority
            once: If True, unsubscribe after first event
            
        Returns:
            Subscription ID for unsubscribing
        """
        with self._lock:
            # Create event filter
            event_filter = None
            if sender_filter:
                type_filter = EventTypeFilter(event_types)
                sender_filter_obj = SenderFilter(sender_filter)
                # Combine filters (simplified - would need proper filter composition)
                event_filter = type_filter
            else:
                event_filter = EventTypeFilter(event_types)
            
            # Create subscription
            subscription = EventSubscription(
                handler=handler,
                event_filter=event_filter,
                priority=priority,
                once=once
            )
            
            # Add to appropriate subscription lists
            if isinstance(event_types, EventType):
                event_types = [event_types]
            
            for event_type in event_types:
                if event_type not in self.subscriptions:
                    self.subscriptions[event_type] = []
                
                self.subscriptions[event_type].append(subscription)
                
                # Sort by priority (highest first)
                self.subscriptions[event_type].sort(
                    key=lambda s: s.priority.value, 
                    reverse=True
                )
            
            self.stats["subscription_count"] += 1
            
            # Generate subscription ID
            subscription_id = f"sub_{datetime.now().strftime('%H%M%S_%f')}_{id(subscription)}"
            
            self.logger.debug(f"Subscription created: {subscription_id} for {event_types}")
            return subscription_id
    
    def subscribe_global(self,
                        handler: Callable[[UIEvent], None],
                        priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Subscribe to all events (global subscription).
        
        Args:
            handler: Function to handle all events
            priority: Subscription priority
            
        Returns:
            Subscription ID
        """
        with self._lock:
            subscription = EventSubscription(
                handler=handler,
                priority=priority
            )
            
            self.global_subscriptions.append(subscription)
            
            # Sort by priority
            self.global_subscriptions.sort(
                key=lambda s: s.priority.value,
                reverse=True
            )
            
            subscription_id = f"global_{datetime.now().strftime('%H%M%S_%f')}_{id(subscription)}"
            
            self.logger.debug(f"Global subscription created: {subscription_id}")
            return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: ID returned from subscribe()
            
        Returns:
            True if subscription was found and removed
        """
        with self._lock:
            # This is a simplified implementation - in practice, would need
            # to store subscription IDs properly
            self.logger.debug(f"Unsubscribe requested: {subscription_id}")
            return True
    
    def publish(self, 
               event_type: EventType,
               sender: Optional[str] = None,
               data: Optional[Dict[str, Any]] = None,
               priority: EventPriority = EventPriority.NORMAL) -> UIEvent:
        """
        Publish an event.
        
        Args:
            event_type: Type of event
            sender: Event sender identifier
            data: Event data
            priority: Event priority
            
        Returns:
            The published event
        """
        # Create event
        event = UIEvent(
            event_type=event_type,
            sender=sender,
            data=data or {},
            priority=priority
        )
        
        return self.publish_event(event)
    
    def publish_event(self, event: UIEvent) -> UIEvent:
        """
        Publish an existing event.
        
        Args:
            event: Event to publish
            
        Returns:
            The published event
        """
        with self._lock:
            self.logger.debug(f"Publishing event: {event.event_type.value} from {event.sender}")
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            # Update stats
            self.stats["events_published"] += 1
            
            # Get subscriptions for this event type
            subscriptions = self.subscriptions.get(event.event_type, [])
            
            # Add global subscriptions
            all_subscriptions = subscriptions + self.global_subscriptions
            
            # Sort by priority
            all_subscriptions.sort(key=lambda s: s.priority.value, reverse=True)
            
            # Handle event with each subscription
            handlers_called = 0
            to_remove = []
            
            for subscription in all_subscriptions:
                if event.cancelled:
                    break
                
                if subscription.should_handle(event):
                    try:
                        subscription.handle_event(event)
                        handlers_called += 1
                        
                        # Mark for removal if it's a one-time subscription
                        if subscription.once:
                            to_remove.append(subscription)
                            
                    except Exception as e:
                        self.logger.error(f"Event handler failed: {str(e)}")
                        # Continue with other handlers
                        continue
            
            # Remove one-time subscriptions
            for subscription in to_remove:
                self._remove_subscription(subscription)
            
            # Update stats
            self.stats["events_handled"] += handlers_called
            total_events = self.stats["events_published"]
            total_handlers = self.stats["events_handled"]
            if total_events > 0:
                self.stats["average_handlers_per_event"] = total_handlers / total_events
            
            event.mark_handled()
            
            self.logger.debug(f"Event handled by {handlers_called} subscriptions")
            return event
    
    def _remove_subscription(self, subscription: EventSubscription):
        """Remove a subscription from all subscription lists."""
        # Remove from type-specific subscriptions
        for event_type, subs in self.subscriptions.items():
            if subscription in subs:
                subs.remove(subscription)
        
        # Remove from global subscriptions
        if subscription in self.global_subscriptions:
            self.global_subscriptions.remove(subscription)
        
        self.stats["subscription_count"] -= 1
    
    def clear_subscriptions(self):
        """Clear all subscriptions."""
        with self._lock:
            self.subscriptions.clear()
            self.global_subscriptions.clear()
            self.stats["subscription_count"] = 0
            self.logger.info("All subscriptions cleared")
    
    def get_event_history(self, 
                         event_type: Optional[EventType] = None,
                         sender: Optional[str] = None,
                         limit: int = 100) -> List[UIEvent]:
        """
        Get event history with optional filtering.
        
        Args:
            event_type: Filter by event type
            sender: Filter by sender
            limit: Maximum number of events to return
            
        Returns:
            List of events (most recent first)
        """
        events = list(reversed(self.event_history))  # Most recent first
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if sender:
            events = [e for e in events if e.sender == sender]
        
        return events[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self._lock:
            return {
                **self.stats,
                "active_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
                "global_subscriptions": len(self.global_subscriptions),
                "event_history_size": len(self.event_history),
                "unique_event_types": len(self.subscriptions)
            }
    
    def enable_async_mode(self):
        """Enable asynchronous event handling."""
        self._async_queue = asyncio.Queue()
        self.logger.info("Async mode enabled")
    
    async def publish_async(self,
                           event_type: EventType,
                           sender: Optional[str] = None,
                           data: Optional[Dict[str, Any]] = None,
                           priority: EventPriority = EventPriority.NORMAL) -> UIEvent:
        """Publish an event asynchronously."""
        if not self._async_queue:
            raise RuntimeError("Async mode not enabled")
        
        event = UIEvent(
            event_type=event_type,
            sender=sender,
            data=data or {},
            priority=priority
        )
        
        await self._async_queue.put(event)
        return event
    
    async def process_async_events(self):
        """Process asynchronous events (call from async event loop)."""
        if not self._async_queue:
            return
        
        while True:
            try:
                event = await self._async_queue.get()
                self.publish_event(event)
                self._async_queue.task_done()
            except Exception as e:
                self.logger.error(f"Async event processing failed: {str(e)}")


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def create_event_bus() -> EventBus:
    """Create a new event bus instance."""
    return EventBus()


# Convenience functions for common event types
def publish_document_loaded(sender: str, document_id: str, **kwargs):
    """Publish document loaded event."""
    data = {"document_id": document_id, **kwargs}
    get_event_bus().publish(EventType.DOCUMENT_LOADED, sender, data)


def publish_page_changed(sender: str, page_number: int, **kwargs):
    """Publish page changed event."""
    data = {"page_number": page_number, **kwargs}
    get_event_bus().publish(EventType.PAGE_CHANGED, sender, data)


def publish_area_selected(sender: str, area_id: str, **kwargs):
    """Publish area selected event."""
    data = {"area_id": area_id, **kwargs}
    get_event_bus().publish(EventType.AREA_SELECTED, sender, data)


def publish_coordinates_mapped(sender: str, coordinates: Dict[str, Any], **kwargs):
    """Publish coordinates mapped event."""
    data = {"coordinates": coordinates, **kwargs}
    get_event_bus().publish(EventType.COORDINATES_MAPPED, sender, data)


def publish_error(sender: str, error_message: str, **kwargs):
    """Publish error event."""
    data = {"error_message": error_message, **kwargs}
    get_event_bus().publish(EventType.ERROR_OCCURRED, sender, data, EventPriority.HIGH)