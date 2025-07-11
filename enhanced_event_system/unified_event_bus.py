#!/usr/bin/env python3
"""
Unified Event Bus for TORE Matrix Labs V1 Enhancement

This module provides a modern event bus system that enhances the existing V1
PyQt signal system with V2-style event architecture while maintaining full
backward compatibility.
"""

import logging
import threading
import weakref
from typing import Dict, List, Callable, Optional, Any, Set
from collections import defaultdict, deque
from datetime import datetime
import time
from queue import Queue, PriorityQueue
from concurrent.futures import ThreadPoolExecutor

from .event_types_v1 import EventTypeV1, V1EventData, EventPriority


class EventSubscription:
    """Represents an event subscription with metadata."""
    
    def __init__(self, 
                 subscriber_id: str,
                 callback: Callable[[V1EventData], None],
                 event_types: Set[EventTypeV1],
                 priority: EventPriority = EventPriority.NORMAL,
                 once: bool = False):
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.event_types = event_types
        self.priority = priority
        self.once = once
        self.created_at = datetime.now()
        self.call_count = 0
        self.last_called = None
    
    def should_handle(self, event: V1EventData) -> bool:
        """Check if this subscription should handle the event."""
        return event.event_type in self.event_types
    
    def call(self, event: V1EventData) -> None:
        """Call the subscription callback."""
        try:
            self.callback(event)
            self.call_count += 1
            self.last_called = datetime.now()
        except Exception as e:
            logging.error(f"Error in event callback {self.subscriber_id}: {e}")


class UnifiedEventBus:
    """
    Enhanced event bus with V2 patterns for V1 system.
    
    Provides modern event architecture while maintaining compatibility
    with existing V1 PyQt signal system.
    """
    
    def __init__(self, enable_async: bool = True, max_workers: int = 4):
        """Initialize the unified event bus."""
        self.logger = logging.getLogger(__name__)
        
        # Event subscriptions
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.event_type_subscriptions: Dict[EventTypeV1, List[str]] = defaultdict(list)
        
        # Threading and async processing
        self.enable_async = enable_async
        self.event_queue = PriorityQueue()
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers) if enable_async else None
        self.processing_thread = None
        self.shutdown_event = threading.Event()
        
        # Event processing state
        self.processing_lock = threading.RLock()
        self.is_processing = False
        
        # Performance and debugging
        self.event_history: deque = deque(maxlen=1000)
        self.performance_stats = {
            'events_published': 0,
            'events_processed': 0,
            'average_processing_time': 0.0,
            'failed_events': 0,
            'active_subscriptions': 0
        }
        
        # V1 compatibility
        self.qt_signal_adapters: Dict[str, Any] = {}
        
        if enable_async:
            self._start_processing_thread()
        
        self.logger.info("Unified Event Bus initialized")
    
    def subscribe(self, 
                  event_type: EventTypeV1,
                  callback: Callable[[V1EventData], None],
                  subscriber_id: Optional[str] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  once: bool = False) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            subscriber_id: Optional unique ID for subscriber
            priority: Processing priority
            once: If True, unsubscribe after first event
            
        Returns:
            Subscription ID
        """
        if subscriber_id is None:
            subscriber_id = f"subscriber_{id(callback)}_{int(time.time() * 1000000)}"
        
        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            callback=callback,
            event_types={event_type},
            priority=priority,
            once=once
        )
        
        with self.processing_lock:
            self.subscriptions[subscriber_id] = subscription
            self.event_type_subscriptions[event_type].append(subscriber_id)
            self.performance_stats['active_subscriptions'] = len(self.subscriptions)
        
        self.logger.debug(f"Subscribed {subscriber_id} to {event_type.value}")
        return subscriber_id
    
    def subscribe_multiple(self,
                          event_types: List[EventTypeV1],
                          callback: Callable[[V1EventData], None],
                          subscriber_id: Optional[str] = None,
                          priority: EventPriority = EventPriority.NORMAL) -> str:
        """Subscribe to multiple event types with single callback."""
        if subscriber_id is None:
            subscriber_id = f"multi_subscriber_{id(callback)}_{int(time.time() * 1000000)}"
        
        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            callback=callback,
            event_types=set(event_types),
            priority=priority
        )
        
        with self.processing_lock:
            self.subscriptions[subscriber_id] = subscription
            for event_type in event_types:
                self.event_type_subscriptions[event_type].append(subscriber_id)
            self.performance_stats['active_subscriptions'] = len(self.subscriptions)
        
        self.logger.debug(f"Subscribed {subscriber_id} to {len(event_types)} event types")
        return subscriber_id
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscriber_id: ID of subscriber to remove
            
        Returns:
            True if unsubscribed successfully
        """
        with self.processing_lock:
            if subscriber_id not in self.subscriptions:
                return False
            
            subscription = self.subscriptions[subscriber_id]
            
            # Remove from event type mappings
            for event_type in subscription.event_types:
                if subscriber_id in self.event_type_subscriptions[event_type]:
                    self.event_type_subscriptions[event_type].remove(subscriber_id)
            
            # Remove subscription
            del self.subscriptions[subscriber_id]
            self.performance_stats['active_subscriptions'] = len(self.subscriptions)
        
        self.logger.debug(f"Unsubscribed {subscriber_id}")
        return True
    
    def publish(self, 
                event_type: EventTypeV1,
                sender: str = "unknown",
                data: Optional[Dict[str, Any]] = None,
                priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Publish an event.
        
        Args:
            event_type: Type of event to publish
            sender: ID of event sender
            data: Event data
            priority: Event priority
            
        Returns:
            Event ID
        """
        event = V1EventData(
            event_type=event_type,
            sender=sender,
            priority=priority,
            data=data or {}
        )
        
        return self.publish_event(event)
    
    def publish_event(self, event: V1EventData) -> str:
        """
        Publish a complete event object.
        
        Args:
            event: Event to publish
            
        Returns:
            Event ID
        """
        self.performance_stats['events_published'] += 1
        
        if self.enable_async:
            # Add to priority queue for async processing
            priority_value = (5 - event.priority.value, event.timestamp.timestamp())
            self.event_queue.put((priority_value, event))
        else:
            # Process synchronously
            self._process_event(event)
        
        # Add to history
        self.event_history.append({
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'sender': event.sender,
            'timestamp': event.timestamp,
            'processed': event.processed
        })
        
        self.logger.debug(f"Published event {event.event_type.value} from {event.sender}")
        return event.event_id
    
    def _process_event(self, event: V1EventData) -> None:
        """Process a single event."""
        start_time = time.time()
        
        try:
            # Get subscribers for this event type
            subscriber_ids = self.event_type_subscriptions.get(event.event_type, [])
            
            if not subscriber_ids:
                self.logger.debug(f"No subscribers for event {event.event_type.value}")
                return
            
            # Sort subscribers by priority
            subscribers = []
            for sub_id in subscriber_ids:
                if sub_id in self.subscriptions:
                    subscription = self.subscriptions[sub_id]
                    if subscription.should_handle(event):
                        subscribers.append(subscription)
            
            subscribers.sort(key=lambda s: s.priority.value, reverse=True)
            
            # Call subscribers
            for subscription in subscribers:
                try:
                    subscription.call(event)
                    
                    # Remove if it's a one-time subscription
                    if subscription.once:
                        self.unsubscribe(subscription.subscriber_id)
                        
                except Exception as e:
                    self.logger.error(f"Error processing event {event.event_type.value} "
                                    f"for subscriber {subscription.subscriber_id}: {e}")
                    self.performance_stats['failed_events'] += 1
            
            # Mark event as processed
            processing_time = time.time() - start_time
            event.mark_processed(processing_time)
            
            # Update performance stats
            self.performance_stats['events_processed'] += 1
            current_avg = self.performance_stats['average_processing_time']
            processed_count = self.performance_stats['events_processed']
            self.performance_stats['average_processing_time'] = (
                (current_avg * (processed_count - 1) + processing_time) / processed_count
            )
            
        except Exception as e:
            self.logger.error(f"Error processing event {event.event_type.value}: {e}")
            event.mark_processed(time.time() - start_time, str(e))
            self.performance_stats['failed_events'] += 1
    
    def _start_processing_thread(self):
        """Start the async event processing thread."""
        def process_events():
            while not self.shutdown_event.is_set():
                try:
                    # Get event from queue with timeout
                    try:
                        priority, event = self.event_queue.get(timeout=1.0)
                        self._process_event(event)
                        self.event_queue.task_done()
                    except:
                        continue  # Timeout or queue empty
                        
                except Exception as e:
                    self.logger.error(f"Error in event processing thread: {e}")
        
        self.processing_thread = threading.Thread(target=process_events, daemon=True)
        self.processing_thread.start()
        self.logger.debug("Event processing thread started")
    
    def shutdown(self):
        """Shutdown the event bus."""
        self.logger.info("Shutting down event bus")
        
        if self.enable_async:
            self.shutdown_event.set()
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
            
            if self.thread_pool:
                self.thread_pool.shutdown(wait=True)
        
        # Clear subscriptions
        with self.processing_lock:
            self.subscriptions.clear()
            self.event_type_subscriptions.clear()
        
        self.logger.info("Event bus shutdown complete")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """Get subscription information for debugging."""
        with self.processing_lock:
            subscriptions_info = {}
            for sub_id, subscription in self.subscriptions.items():
                subscriptions_info[sub_id] = {
                    'event_types': [et.value for et in subscription.event_types],
                    'priority': subscription.priority.value,
                    'call_count': subscription.call_count,
                    'created_at': subscription.created_at.isoformat(),
                    'last_called': subscription.last_called.isoformat() if subscription.last_called else None
                }
        
        return {
            'total_subscriptions': len(self.subscriptions),
            'event_type_counts': {et.value: len(subs) for et, subs in self.event_type_subscriptions.items()},
            'subscriptions': subscriptions_info
        }
    
    def clear_event_history(self):
        """Clear the event history."""
        self.event_history.clear()
        self.logger.debug("Event history cleared")
    
    def get_event_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent event history."""
        history = list(self.event_history)
        if limit:
            history = history[-limit:]
        return history


# Global event bus instance for V1 system
_global_event_bus: Optional[UnifiedEventBus] = None


def get_global_event_bus() -> UnifiedEventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = UnifiedEventBus()
    return _global_event_bus


def shutdown_global_event_bus():
    """Shutdown the global event bus."""
    global _global_event_bus
    if _global_event_bus:
        _global_event_bus.shutdown()
        _global_event_bus = None


# Convenience alias for V1 compatibility
V1EventBus = UnifiedEventBus