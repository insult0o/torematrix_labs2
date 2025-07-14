"""
Event Bus integration for selection tools.

This module provides comprehensive integration with the application's
event bus system, enabling tools to publish and subscribe to events
for system-wide coordination and state synchronization.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle


logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels for processing order."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventType(Enum):
    """Selection tool event types."""
    # Tool lifecycle events
    TOOL_ACTIVATED = "tool_activated"
    TOOL_DEACTIVATED = "tool_deactivated"
    TOOL_CHANGED = "tool_changed"
    
    # Selection events
    SELECTION_STARTED = "selection_started"
    SELECTION_UPDATED = "selection_updated"
    SELECTION_COMPLETED = "selection_completed"
    SELECTION_CLEARED = "selection_cleared"
    SELECTION_CANCELLED = "selection_cancelled"
    
    # Element events
    ELEMENT_FOCUSED = "element_focused"
    ELEMENT_HOVERED = "element_hovered"
    ELEMENT_UNHOVERED = "element_unhovered"
    ELEMENT_SELECTED = "element_selected"
    ELEMENT_DESELECTED = "element_deselected"
    
    # Interaction events
    MOUSE_PRESSED = "mouse_pressed"
    MOUSE_MOVED = "mouse_moved"
    MOUSE_RELEASED = "mouse_released"
    MOUSE_DOUBLE_CLICKED = "mouse_double_clicked"
    KEY_PRESSED = "key_pressed"
    KEY_RELEASED = "key_released"
    
    # State synchronization events
    STATE_CHANGED = "state_changed"
    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    
    # Performance events
    PERFORMANCE_METRICS = "performance_metrics"
    MEMORY_WARNING = "memory_warning"
    
    # Error events
    TOOL_ERROR = "tool_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class ToolEvent:
    """Represents a selection tool event."""
    event_type: EventType
    source_tool: Optional[str] = None
    target_tool: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    event_id: str = field(default_factory=lambda: str(uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    propagate: bool = True
    processed: bool = False


class EventFilter:
    """Filter for event subscriptions."""
    
    def __init__(self, 
                 event_types: Optional[Set[EventType]] = None,
                 source_tools: Optional[Set[str]] = None,
                 target_tools: Optional[Set[str]] = None,
                 priority_threshold: EventPriority = EventPriority.LOW):
        self.event_types = event_types or set()
        self.source_tools = source_tools or set()
        self.target_tools = target_tools or set()
        self.priority_threshold = priority_threshold
    
    def matches(self, event: ToolEvent) -> bool:
        """Check if event matches this filter."""
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.source_tools and event.source_tool not in self.source_tools:
            return False
        
        if self.target_tools and event.target_tool not in self.target_tools:
            return False
        
        if event.priority.value < self.priority_threshold.value:
            return False
        
        return True


class EventSubscription:
    """Represents an event subscription."""
    
    def __init__(self, 
                 subscriber_id: str,
                 callback: Callable[[ToolEvent], None],
                 event_filter: Optional[EventFilter] = None,
                 one_shot: bool = False):
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.event_filter = event_filter or EventFilter()
        self.one_shot = one_shot
        self.subscription_id = str(uuid4())
        self.created_at = __import__('time').time()
        self.event_count = 0


class ToolEventBus(QObject):
    """
    Event bus for selection tools system.
    
    Provides centralized event management with filtering, priority handling,
    and performance monitoring for tool coordination.
    """
    
    # Signals for Qt integration
    event_published = pyqtSignal(object)  # ToolEvent
    subscription_added = pyqtSignal(str)  # subscription_id
    subscription_removed = pyqtSignal(str)  # subscription_id
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_history: List[ToolEvent] = []
        self._max_history_size = 1000
        
        # Performance monitoring
        self._event_stats: Dict[EventType, Dict[str, int]] = {}
        self._processing_times: Dict[EventType, List[float]] = {}
        
        # Event processing
        self._event_queue: List[ToolEvent] = []
        self._processing_timer = QTimer()
        self._processing_timer.setSingleShot(True)
        self._processing_timer.timeout.connect(self._process_event_queue)
        self._batch_processing_enabled = True
        self._batch_size = 10
        
        # Error handling
        self._error_handlers: Dict[str, Callable[[Exception, ToolEvent], None]] = {}
        self._failed_events: List[ToolEvent] = []
        
        logger.info("ToolEventBus initialized")
    
    def publish(self, event: ToolEvent, async_mode: bool = True) -> None:
        """
        Publish an event to all matching subscribers.
        
        Args:
            event: The event to publish
            async_mode: Whether to process asynchronously
        """
        try:
            # Add to history
            self._add_to_history(event)
            
            # Update statistics
            self._update_event_stats(event)
            
            # Emit Qt signal
            self.event_published.emit(event)
            
            if async_mode and self._batch_processing_enabled:
                # Add to queue for batch processing
                self._event_queue.append(event)
                if not self._processing_timer.isActive():
                    self._processing_timer.start(1)  # Process very quickly
            else:
                # Process immediately
                self._process_event(event)
            
            logger.debug(f"Published event: {event.event_type} from {event.source_tool}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            self._handle_event_error(e, event)
    
    def subscribe(self, 
                  subscriber_id: str,
                  callback: Callable[[ToolEvent], None],
                  event_filter: Optional[EventFilter] = None,
                  one_shot: bool = False) -> str:
        """
        Subscribe to events matching the filter.
        
        Args:
            subscriber_id: Unique identifier for the subscriber
            callback: Function to call when matching events occur
            event_filter: Filter to determine which events to receive
            one_shot: Whether to unsubscribe after first matching event
            
        Returns:
            Subscription ID for management
        """
        subscription = EventSubscription(subscriber_id, callback, event_filter, one_shot)
        self._subscriptions[subscription.subscription_id] = subscription
        
        self.subscription_added.emit(subscription.subscription_id)
        logger.debug(f"Added subscription for {subscriber_id}: {subscription.subscription_id}")
        
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was found and removed
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            self.subscription_removed.emit(subscription_id)
            logger.debug(f"Removed subscription: {subscription_id}")
            return True
        
        return False
    
    def unsubscribe_all(self, subscriber_id: str) -> int:
        """
        Remove all subscriptions for a subscriber.
        
        Args:
            subscriber_id: ID of subscriber to remove all subscriptions for
            
        Returns:
            Number of subscriptions removed
        """
        to_remove = [
            sub_id for sub_id, sub in self._subscriptions.items()
            if sub.subscriber_id == subscriber_id
        ]
        
        for sub_id in to_remove:
            self.unsubscribe(sub_id)
        
        logger.debug(f"Removed {len(to_remove)} subscriptions for {subscriber_id}")
        return len(to_remove)
    
    def _process_event_queue(self) -> None:
        """Process queued events in batches."""
        if not self._event_queue:
            return
        
        # Process a batch of events
        batch_size = min(self._batch_size, len(self._event_queue))
        batch = self._event_queue[:batch_size]
        self._event_queue = self._event_queue[batch_size:]
        
        for event in batch:
            self._process_event(event)
        
        # Schedule next batch if more events remain
        if self._event_queue:
            self._processing_timer.start(1)
    
    def _process_event(self, event: ToolEvent) -> None:
        """Process a single event through all matching subscriptions."""
        start_time = __import__('time').time()
        processed_count = 0
        
        try:
            # Sort subscriptions by priority
            matching_subscriptions = []
            for subscription in self._subscriptions.values():
                if subscription.event_filter.matches(event):
                    matching_subscriptions.append(subscription)
            
            # Process subscriptions
            for subscription in matching_subscriptions:
                try:
                    subscription.callback(event)
                    subscription.event_count += 1
                    processed_count += 1
                    
                    # Remove one-shot subscriptions
                    if subscription.one_shot:
                        self.unsubscribe(subscription.subscription_id)
                    
                    # Check if event propagation was stopped
                    if not event.propagate:
                        break
                
                except Exception as e:
                    logger.error(f"Error in event callback for {subscription.subscriber_id}: {e}")
                    self._handle_subscription_error(e, event, subscription)
            
            event.processed = True
            
            # Record processing time
            processing_time = __import__('time').time() - start_time
            if event.event_type not in self._processing_times:
                self._processing_times[event.event_type] = []
            self._processing_times[event.event_type].append(processing_time)
            
            # Keep only recent times for statistics
            if len(self._processing_times[event.event_type]) > 100:
                self._processing_times[event.event_type] = self._processing_times[event.event_type][-50:]
            
            logger.debug(f"Processed event {event.event_type} to {processed_count} subscribers in {processing_time:.3f}s")
        
        except Exception as e:
            logger.error(f"Failed to process event {event.event_type}: {e}")
            self._handle_event_error(e, event)
    
    def _add_to_history(self, event: ToolEvent) -> None:
        """Add event to history with size management."""
        self._event_history.append(event)
        
        # Maintain history size limit
        if len(self._event_history) > self._max_history_size:
            # Remove oldest 10% of events
            remove_count = self._max_history_size // 10
            self._event_history = self._event_history[remove_count:]
    
    def _update_event_stats(self, event: ToolEvent) -> None:
        """Update event statistics."""
        if event.event_type not in self._event_stats:
            self._event_stats[event.event_type] = {
                'count': 0,
                'source_tools': set(),
                'target_tools': set()
            }
        
        stats = self._event_stats[event.event_type]
        stats['count'] += 1
        
        if event.source_tool:
            stats['source_tools'].add(event.source_tool)
        
        if event.target_tool:
            stats['target_tools'].add(event.target_tool)
    
    def _handle_event_error(self, error: Exception, event: ToolEvent) -> None:
        """Handle event processing errors."""
        self._failed_events.append(event)
        
        # Try registered error handlers
        for handler_id, handler in self._error_handlers.items():
            try:
                handler(error, event)
            except Exception as e:
                logger.error(f"Error in error handler {handler_id}: {e}")
    
    def _handle_subscription_error(self, error: Exception, event: ToolEvent, subscription: EventSubscription) -> None:
        """Handle subscription callback errors."""
        logger.error(f"Subscription error for {subscription.subscriber_id}: {error}")
        
        # Could implement subscription error recovery here
        # For now, just log the error
    
    def register_error_handler(self, handler_id: str, handler: Callable[[Exception, ToolEvent], None]) -> None:
        """Register a global error handler."""
        self._error_handlers[handler_id] = handler
        logger.debug(f"Registered error handler: {handler_id}")
    
    def unregister_error_handler(self, handler_id: str) -> bool:
        """Unregister an error handler."""
        if handler_id in self._error_handlers:
            del self._error_handlers[handler_id]
            logger.debug(f"Unregistered error handler: {handler_id}")
            return True
        return False
    
    def get_event_history(self, 
                         event_types: Optional[Set[EventType]] = None,
                         since: Optional[float] = None,
                         limit: Optional[int] = None) -> List[ToolEvent]:
        """Get event history with optional filtering."""
        filtered_events = self._event_history
        
        if event_types:
            filtered_events = [e for e in filtered_events if e.event_type in event_types]
        
        if since:
            filtered_events = [e for e in filtered_events if e.timestamp >= since]
        
        if limit:
            filtered_events = filtered_events[-limit:]
        
        return filtered_events
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event statistics."""
        total_events = sum(stats['count'] for stats in self._event_stats.values())
        
        # Calculate average processing times
        avg_processing_times = {}
        for event_type, times in self._processing_times.items():
            if times:
                avg_processing_times[event_type.value] = sum(times) / len(times)
        
        return {
            'total_events': total_events,
            'event_types': {et.value: stats['count'] for et, stats in self._event_stats.items()},
            'active_subscriptions': len(self._subscriptions),
            'failed_events': len(self._failed_events),
            'average_processing_times': avg_processing_times,
            'queue_size': len(self._event_queue),
            'history_size': len(self._event_history)
        }
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.info("Cleared event history")
    
    def clear_statistics(self) -> None:
        """Clear event statistics."""
        self._event_stats.clear()
        self._processing_times.clear()
        self._failed_events.clear()
        logger.info("Cleared event statistics")


class ToolEventIntegration(QObject):
    """
    Integration layer for connecting selection tools to the event bus.
    
    Automatically handles event publishing and subscription for tools,
    providing seamless integration with the application event system.
    """
    
    def __init__(self, event_bus: ToolEventBus, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._event_bus = event_bus
        self._integrated_tools: Dict[str, SelectionTool] = {}
        self._tool_subscriptions: Dict[str, List[str]] = {}
        
        logger.info("ToolEventIntegration initialized")
    
    def integrate_tool(self, tool: SelectionTool) -> None:
        """
        Integrate a tool with the event bus.
        
        Sets up automatic event publishing for tool state changes and
        provides event subscription capabilities.
        """
        if tool.tool_id in self._integrated_tools:
            logger.warning(f"Tool {tool.tool_id} already integrated")
            return
        
        self._integrated_tools[tool.tool_id] = tool
        self._tool_subscriptions[tool.tool_id] = []
        
        # Connect tool signals to event publishing
        tool.state_changed.connect(lambda state: self._publish_tool_state_change(tool.tool_id, state))
        tool.selection_changed.connect(lambda result: self._publish_selection_change(tool.tool_id, result))
        
        # Subscribe to relevant events for the tool
        self._setup_tool_subscriptions(tool)
        
        # Publish tool integration event
        self._event_bus.publish(ToolEvent(
            event_type=EventType.TOOL_ACTIVATED,
            source_tool=tool.tool_id,
            data={'tool_name': tool.name, 'tool_type': type(tool).__name__}
        ))
        
        logger.info(f"Integrated tool with event bus: {tool.tool_id}")
    
    def remove_tool(self, tool_id: str) -> None:
        """Remove a tool from event bus integration."""
        if tool_id not in self._integrated_tools:
            return
        
        # Remove all subscriptions for this tool
        for subscription_id in self._tool_subscriptions[tool_id]:
            self._event_bus.unsubscribe(subscription_id)
        
        # Publish tool deactivation event
        self._event_bus.publish(ToolEvent(
            event_type=EventType.TOOL_DEACTIVATED,
            source_tool=tool_id
        ))
        
        # Clean up
        del self._integrated_tools[tool_id]
        del self._tool_subscriptions[tool_id]
        
        logger.info(f"Removed tool from event bus: {tool_id}")
    
    def _setup_tool_subscriptions(self, tool: SelectionTool) -> None:
        """Setup event subscriptions for a tool."""
        # Subscribe to configuration changes
        config_sub = self._event_bus.subscribe(
            tool.tool_id,
            lambda event: self._handle_config_change(tool, event),
            EventFilter(event_types={EventType.CONFIG_CHANGED})
        )
        self._tool_subscriptions[tool.tool_id].append(config_sub)
        
        # Subscribe to theme changes
        theme_sub = self._event_bus.subscribe(
            tool.tool_id,
            lambda event: self._handle_theme_change(tool, event),
            EventFilter(event_types={EventType.THEME_CHANGED})
        )
        self._tool_subscriptions[tool.tool_id].append(theme_sub)
        
        # Subscribe to tool change events (for coordination)
        tool_change_sub = self._event_bus.subscribe(
            tool.tool_id,
            lambda event: self._handle_tool_change(tool, event),
            EventFilter(event_types={EventType.TOOL_CHANGED})
        )
        self._tool_subscriptions[tool.tool_id].append(tool_change_sub)
    
    def _publish_tool_state_change(self, tool_id: str, state: ToolState) -> None:
        """Publish tool state change event."""
        self._event_bus.publish(ToolEvent(
            event_type=EventType.STATE_CHANGED,
            source_tool=tool_id,
            data={'new_state': state.value, 'timestamp': __import__('time').time()}
        ))
    
    def _publish_selection_change(self, tool_id: str, result: Optional[SelectionResult]) -> None:
        """Publish selection change event."""
        if result:
            event_type = EventType.SELECTION_COMPLETED
            data = {
                'element_count': len(result.elements),
                'selection_bounds': result.geometry.to_dict() if result.geometry else None,
                'tool_type': result.tool_type,
                'metadata': result.metadata
            }
        else:
            event_type = EventType.SELECTION_CLEARED
            data = {}
        
        self._event_bus.publish(ToolEvent(
            event_type=event_type,
            source_tool=tool_id,
            data=data
        ))
    
    def _handle_config_change(self, tool: SelectionTool, event: ToolEvent) -> None:
        """Handle configuration change events."""
        if 'config' in event.data:
            # Update tool configuration
            # This would depend on the actual tool configuration system
            logger.debug(f"Applying config change to tool {tool.tool_id}")
    
    def _handle_theme_change(self, tool: SelectionTool, event: ToolEvent) -> None:
        """Handle theme change events."""
        if 'theme' in event.data:
            # Update tool visual theme
            # This would depend on the actual theme system
            logger.debug(f"Applying theme change to tool {tool.tool_id}")
    
    def _handle_tool_change(self, tool: SelectionTool, event: ToolEvent) -> None:
        """Handle tool change events for coordination."""
        if event.source_tool != tool.tool_id:
            # Another tool became active, this tool should deactivate if needed
            if tool.get_state() == ToolState.ACTIVE:
                logger.debug(f"Tool {tool.tool_id} auto-deactivating due to tool change")
    
    def publish_mouse_event(self, tool_id: str, event_type: EventType, point: Point, modifiers: int = 0) -> None:
        """Publish mouse interaction events."""
        self._event_bus.publish(ToolEvent(
            event_type=event_type,
            source_tool=tool_id,
            data={
                'point': {'x': point.x, 'y': point.y},
                'modifiers': modifiers,
                'timestamp': __import__('time').time()
            }
        ))
    
    def publish_key_event(self, tool_id: str, event_type: EventType, key: int, modifiers: int = 0) -> None:
        """Publish keyboard interaction events."""
        self._event_bus.publish(ToolEvent(
            event_type=event_type,
            source_tool=tool_id,
            data={
                'key': key,
                'modifiers': modifiers,
                'timestamp': __import__('time').time()
            }
        ))
    
    def publish_performance_metrics(self, tool_id: str, metrics: Dict[str, Any]) -> None:
        """Publish performance metrics for monitoring."""
        self._event_bus.publish(ToolEvent(
            event_type=EventType.PERFORMANCE_METRICS,
            source_tool=tool_id,
            data=metrics,
            priority=EventPriority.LOW
        ))
    
    def get_integrated_tools(self) -> List[str]:
        """Get list of integrated tool IDs."""
        return list(self._integrated_tools.keys())
    
    def get_event_bus(self) -> ToolEventBus:
        """Get the underlying event bus."""
        return self._event_bus