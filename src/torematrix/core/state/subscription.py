"""
Smart subscription management for efficient state updates.
"""

import asyncio
import weakref
import threading
from typing import Any, Dict, List, Set, Callable, Optional, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import time
import fnmatch


class SubscriptionType(Enum):
    """Types of state subscriptions."""
    PATH = "path"           # Subscribe to specific state path
    SELECTOR = "selector"   # Subscribe to selector changes
    PATTERN = "pattern"     # Subscribe to path patterns (wildcards)
    DEEP = "deep"          # Subscribe to path and all children
    CHANGE = "change"      # Subscribe to any state change


@dataclass
class StateChange:
    """Represents a state change event."""
    path: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)
    change_type: str = "update"  # "update", "add", "remove"
    
    @property
    def has_actual_change(self) -> bool:
        """Check if this represents an actual value change."""
        return self.old_value != self.new_value


@dataclass
class Subscription:
    """Individual subscription record."""
    id: str
    subscription_type: SubscriptionType
    path: str
    callback: Callable
    selector: Optional[Any] = None
    options: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_notified: float = 0.0
    notification_count: int = 0
    is_active: bool = True
    
    def should_notify(self, change: StateChange) -> bool:
        """Check if this subscription should be notified of a change."""
        if not self.is_active:
            return False
        
        if self.subscription_type == SubscriptionType.PATH:
            return change.path == self.path
        
        elif self.subscription_type == SubscriptionType.PATTERN:
            return fnmatch.fnmatch(change.path, self.path)
        
        elif self.subscription_type == SubscriptionType.DEEP:
            return change.path.startswith(self.path)
        
        elif self.subscription_type == SubscriptionType.CHANGE:
            return True
        
        return False


class SubscriptionManager:
    """
    High-performance subscription management system.
    
    Provides granular state subscriptions with optimization for
    large numbers of subscribers and frequent updates.
    """
    
    def __init__(
        self,
        batch_notifications: bool = True,
        batch_timeout_ms: float = 5.0,
        max_notification_queue: int = 10000
    ):
        self.batch_notifications = batch_notifications
        self.batch_timeout_ms = batch_timeout_ms
        self.max_notification_queue = max_notification_queue
        
        # Subscription storage
        self._subscriptions: Dict[str, Subscription] = {}
        self._subscriptions_by_path: Dict[str, Set[str]] = defaultdict(set)
        self._subscriptions_by_pattern: Dict[str, Set[str]] = defaultdict(set)
        self._subscriptions_by_selector: Dict[Any, Set[str]] = defaultdict(set)
        
        # Notification queue and batching
        self._notification_queue: deque = deque(maxlen=max_notification_queue)
        self._batch_timer: Optional[asyncio.Task] = None
        self._pending_notifications: Dict[str, StateChange] = {}
        
        # Performance tracking
        self._notification_stats = {
            'total_notifications': 0,
            'batched_notifications': 0,
            'notification_times': deque(maxlen=1000),
            'queue_overflows': 0
        }
        
        # Threading
        self._lock = threading.RLock()
        self._notification_lock = threading.RLock()
        
        # Cleanup
        self._last_cleanup = time.time()
        self._cleanup_interval = 300.0  # 5 minutes
        
        # Weak references for automatic cleanup
        self._weak_callbacks: weakref.WeakSet = weakref.WeakSet()
    
    def subscribe_to_path(
        self,
        path: str,
        callback: Callable[[StateChange], None],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Subscribe to changes at a specific state path.
        
        Args:
            path: State path to monitor (e.g., 'document.metadata.title')
            callback: Function to call when path changes
            options: Additional subscription options
            
        Returns:
            Subscription ID for unsubscribing
        """
        return self._create_subscription(
            subscription_type=SubscriptionType.PATH,
            path=path,
            callback=callback,
            options=options or {}
        )
    
    def subscribe_to_pattern(
        self,
        pattern: str,
        callback: Callable[[StateChange], None],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Subscribe to changes matching a path pattern.
        
        Args:
            pattern: Path pattern with wildcards (e.g., 'elements.*.status')
            callback: Function to call when pattern matches
            options: Additional subscription options
            
        Returns:
            Subscription ID for unsubscribing
        """
        return self._create_subscription(
            subscription_type=SubscriptionType.PATTERN,
            path=pattern,
            callback=callback,
            options=options or {}
        )
    
    def subscribe_to_deep_path(
        self,
        path: str,
        callback: Callable[[StateChange], None],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Subscribe to changes at a path and all its children.
        
        Args:
            path: Base path to monitor deeply
            callback: Function to call when path or children change
            options: Additional subscription options
            
        Returns:
            Subscription ID for unsubscribing
        """
        return self._create_subscription(
            subscription_type=SubscriptionType.DEEP,
            path=path,
            callback=callback,
            options=options or {}
        )
    
    def subscribe_to_selector(
        self,
        selector: Any,
        callback: Callable[[Any, Any], None],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Subscribe to changes in a selector result.
        
        Args:
            selector: Selector to monitor
            callback: Function to call when selector result changes
            options: Additional subscription options
            
        Returns:
            Subscription ID for unsubscribing
        """
        selector_path = getattr(selector, 'name', str(id(selector)))
        
        subscription_id = self._create_subscription(
            subscription_type=SubscriptionType.SELECTOR,
            path=selector_path,
            callback=callback,
            selector=selector,
            options=options or {}
        )
        
        with self._lock:
            self._subscriptions_by_selector[selector].add(subscription_id)
        
        return subscription_id
    
    def subscribe_to_any_change(
        self,
        callback: Callable[[StateChange], None],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Subscribe to any state change.
        
        Args:
            callback: Function to call on any state change
            options: Additional subscription options
            
        Returns:
            Subscription ID for unsubscribing
        """
        return self._create_subscription(
            subscription_type=SubscriptionType.CHANGE,
            path="*",
            callback=callback,
            options=options or {}
        )
    
    def _create_subscription(
        self,
        subscription_type: SubscriptionType,
        path: str,
        callback: Callable,
        selector: Any = None,
        options: Dict[str, Any] = None
    ) -> str:
        """Create and register a new subscription."""
        subscription_id = f"{subscription_type.value}_{path}_{id(callback)}_{time.time()}"
        
        subscription = Subscription(
            id=subscription_id,
            subscription_type=subscription_type,
            path=path,
            callback=callback,
            selector=selector,
            options=options or {}
        )
        
        with self._lock:
            self._subscriptions[subscription_id] = subscription
            
            # Index by type for efficient lookup
            if subscription_type == SubscriptionType.PATH:
                self._subscriptions_by_path[path].add(subscription_id)
            elif subscription_type == SubscriptionType.PATTERN:
                self._subscriptions_by_pattern[path].add(subscription_id)
            elif subscription_type == SubscriptionType.DEEP:
                self._subscriptions_by_path[path].add(subscription_id)
        
        # Keep weak reference for automatic cleanup
        self._weak_callbacks.add(callback)
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from state changes.
        
        Args:
            subscription_id: ID returned from subscribe method
            
        Returns:
            True if subscription was found and removed
        """
        with self._lock:
            if subscription_id not in self._subscriptions:
                return False
            
            subscription = self._subscriptions[subscription_id]
            
            # Remove from indexes
            if subscription.subscription_type == SubscriptionType.PATH:
                self._subscriptions_by_path[subscription.path].discard(subscription_id)
                if not self._subscriptions_by_path[subscription.path]:
                    del self._subscriptions_by_path[subscription.path]
            
            elif subscription.subscription_type == SubscriptionType.PATTERN:
                self._subscriptions_by_pattern[subscription.path].discard(subscription_id)
                if not self._subscriptions_by_pattern[subscription.path]:
                    del self._subscriptions_by_pattern[subscription.path]
            
            elif subscription.subscription_type == SubscriptionType.SELECTOR:
                if subscription.selector in self._subscriptions_by_selector:
                    self._subscriptions_by_selector[subscription.selector].discard(subscription_id)
                    if not self._subscriptions_by_selector[subscription.selector]:
                        del self._subscriptions_by_selector[subscription.selector]
            
            # Remove main subscription
            del self._subscriptions[subscription_id]
            
            return True
    
    def notify_state_change(self, changes: Union[StateChange, List[StateChange]]):
        """
        Notify subscribers of state changes.
        
        Args:
            changes: Single change or list of changes
        """
        if isinstance(changes, StateChange):
            changes = [changes]
        
        start_time = time.perf_counter()
        
        try:
            if self.batch_notifications:
                self._add_to_batch(changes)
            else:
                self._notify_immediately(changes)
        
        finally:
            # Track notification performance
            notification_time = (time.perf_counter() - start_time) * 1000
            with self._notification_lock:
                self._notification_stats['notification_times'].append(notification_time)
                self._notification_stats['total_notifications'] += len(changes)
    
    def _add_to_batch(self, changes: List[StateChange]):
        """Add changes to notification batch."""
        with self._notification_lock:
            for change in changes:
                # Only keep the latest change per path
                self._pending_notifications[change.path] = change
            
            # Schedule batch flush if not already scheduled
            if self._batch_timer is None:
                self._batch_timer = asyncio.create_task(self._flush_batch_after_timeout())
    
    async def _flush_batch_after_timeout(self):
        """Flush notification batch after timeout."""
        try:
            await asyncio.sleep(self.batch_timeout_ms / 1000.0)
            await self.flush_batch()
        except asyncio.CancelledError:
            pass
        finally:
            with self._notification_lock:
                self._batch_timer = None
    
    async def flush_batch(self):
        """Flush pending notification batch immediately."""
        with self._notification_lock:
            if not self._pending_notifications:
                return
            
            changes = list(self._pending_notifications.values())
            self._pending_notifications.clear()
            
            # Cancel timeout timer
            if self._batch_timer:
                self._batch_timer.cancel()
                self._batch_timer = None
            
            self._notification_stats['batched_notifications'] += len(changes)
        
        self._notify_immediately(changes)
    
    def _notify_immediately(self, changes: List[StateChange]):
        """Notify subscribers immediately."""
        for change in changes:
            if not change.has_actual_change:
                continue
            
            notified_subscriptions = set()
            
            with self._lock:
                # Notify path-specific subscriptions
                path_subscribers = self._subscriptions_by_path.get(change.path, set())
                for sub_id in path_subscribers:
                    if sub_id in self._subscriptions:
                        subscription = self._subscriptions[sub_id]
                        if subscription.should_notify(change):
                            self._notify_subscription(subscription, change)
                            notified_subscriptions.add(sub_id)
                
                # Notify pattern subscriptions
                for pattern, sub_ids in self._subscriptions_by_pattern.items():
                    if fnmatch.fnmatch(change.path, pattern):
                        for sub_id in sub_ids:
                            if sub_id not in notified_subscriptions and sub_id in self._subscriptions:
                                subscription = self._subscriptions[sub_id]
                                if subscription.should_notify(change):
                                    self._notify_subscription(subscription, change)
                                    notified_subscriptions.add(sub_id)
                
                # Notify deep path subscriptions
                for path in self._subscriptions_by_path:
                    if change.path.startswith(path + ".") or change.path == path:
                        for sub_id in self._subscriptions_by_path[path]:
                            if sub_id not in notified_subscriptions and sub_id in self._subscriptions:
                                subscription = self._subscriptions[sub_id]
                                if (subscription.subscription_type == SubscriptionType.DEEP and 
                                    subscription.should_notify(change)):
                                    self._notify_subscription(subscription, change)
                                    notified_subscriptions.add(sub_id)
                
                # Notify global change subscriptions
                for sub_id, subscription in self._subscriptions.items():
                    if (sub_id not in notified_subscriptions and 
                        subscription.subscription_type == SubscriptionType.CHANGE):
                        self._notify_subscription(subscription, change)
    
    def _notify_subscription(self, subscription: Subscription, change: StateChange):
        """Notify a single subscription."""
        try:
            subscription.callback(change)
            subscription.last_notified = time.time()
            subscription.notification_count += 1
        
        except Exception as e:
            # Handle dead callbacks
            if "weakly-referenced object no longer exists" in str(e):
                subscription.is_active = False
            else:
                print(f"Subscription callback error: {e}")
    
    def notify_selector_change(self, selector: Any, old_value: Any, new_value: Any):
        """
        Notify subscribers of selector value changes.
        
        Args:
            selector: The selector that changed
            old_value: Previous selector value
            new_value: New selector value
        """
        if selector not in self._subscriptions_by_selector:
            return
        
        with self._lock:
            for sub_id in self._subscriptions_by_selector[selector]:
                if sub_id in self._subscriptions:
                    subscription = self._subscriptions[sub_id]
                    try:
                        subscription.callback(old_value, new_value)
                        subscription.last_notified = time.time()
                        subscription.notification_count += 1
                    except Exception as e:
                        if "weakly-referenced object no longer exists" in str(e):
                            subscription.is_active = False
                        else:
                            print(f"Selector subscription callback error: {e}")
    
    def cleanup_dead_subscriptions(self) -> int:
        """
        Clean up inactive subscriptions.
        
        Returns:
            Number of subscriptions cleaned up
        """
        cleaned_count = 0
        
        with self._lock:
            dead_subscription_ids = [
                sub_id for sub_id, subscription in self._subscriptions.items()
                if not subscription.is_active
            ]
            
            for sub_id in dead_subscription_ids:
                if self.unsubscribe(sub_id):
                    cleaned_count += 1
        
        return cleaned_count
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics."""
        with self._lock, self._notification_lock:
            active_subscriptions = sum(
                1 for sub in self._subscriptions.values() if sub.is_active
            )
            
            avg_notification_time = 0
            if self._notification_stats['notification_times']:
                avg_notification_time = sum(self._notification_stats['notification_times']) / \
                                      len(self._notification_stats['notification_times'])
            
            return {
                'total_subscriptions': len(self._subscriptions),
                'active_subscriptions': active_subscriptions,
                'inactive_subscriptions': len(self._subscriptions) - active_subscriptions,
                'subscriptions_by_type': self._count_by_type(),
                'total_notifications': self._notification_stats['total_notifications'],
                'batched_notifications': self._notification_stats['batched_notifications'],
                'avg_notification_time_ms': avg_notification_time,
                'pending_notifications': len(self._pending_notifications),
                'batch_enabled': self.batch_notifications,
                'batch_timeout_ms': self.batch_timeout_ms
            }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count subscriptions by type."""
        counts = defaultdict(int)
        for subscription in self._subscriptions.values():
            if subscription.is_active:
                counts[subscription.subscription_type.value] += 1
        return dict(counts)
    
    def get_subscription_details(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a subscription."""
        with self._lock:
            if subscription_id not in self._subscriptions:
                return None
            
            subscription = self._subscriptions[subscription_id]
            
            return {
                'id': subscription.id,
                'type': subscription.subscription_type.value,
                'path': subscription.path,
                'is_active': subscription.is_active,
                'created_at': subscription.created_at,
                'last_notified': subscription.last_notified,
                'notification_count': subscription.notification_count,
                'options': subscription.options,
                'has_selector': subscription.selector is not None
            }
    
    def enable_batching(self, enabled: bool = True):
        """Enable or disable notification batching."""
        self.batch_notifications = enabled
    
    def set_batch_timeout(self, timeout_ms: float):
        """Set notification batch timeout."""
        self.batch_timeout_ms = timeout_ms
    
    def clear_all_subscriptions(self):
        """Clear all subscriptions."""
        with self._lock:
            self._subscriptions.clear()
            self._subscriptions_by_path.clear()
            self._subscriptions_by_pattern.clear()
            self._subscriptions_by_selector.clear()
    
    async def shutdown(self):
        """Shutdown subscription manager and cleanup resources."""
        # Flush any pending notifications
        await self.flush_batch()
        
        # Clear all subscriptions
        self.clear_all_subscriptions()
        
        # Cancel batch timer
        with self._notification_lock:
            if self._batch_timer:
                self._batch_timer.cancel()
                self._batch_timer = None