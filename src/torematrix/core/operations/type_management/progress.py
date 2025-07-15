"""Operation Progress Tracking

Real-time progress monitoring for bulk operations with callbacks,
persistence, and detailed progress analytics.
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from uuid import uuid4


class ProgressPhase(Enum):
    """Phases of operation progress"""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationProgress:
    """Progress information for an operation"""
    operation_id: str
    operation_type: str = "unknown"
    phase: ProgressPhase = ProgressPhase.INITIALIZING
    
    # Item-level progress
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    
    # Batch-level progress
    current_batch: int = 0
    total_batches: int = 0
    
    # Time tracking
    start_time: datetime = field(default_factory=datetime.now)
    last_update_time: datetime = field(default_factory=datetime.now)
    estimated_completion_time: Optional[datetime] = None
    
    # Performance metrics
    items_per_second: float = 0.0
    percentage: float = 0.0
    elapsed_seconds: float = 0.0
    remaining_seconds: Optional[float] = None
    
    # Status information
    current_item_id: Optional[str] = None
    current_operation: str = ""
    status_message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Memory and resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def update_percentage(self):
        """Update percentage based on processed items"""
        if self.total_items > 0:
            self.percentage = (self.processed_items / self.total_items) * 100
        else:
            self.percentage = 0.0
    
    def update_timing(self):
        """Update timing calculations"""
        now = datetime.now()
        self.elapsed_seconds = (now - self.start_time).total_seconds()
        self.last_update_time = now
        
        # Calculate items per second
        if self.elapsed_seconds > 0:
            self.items_per_second = self.processed_items / self.elapsed_seconds
        
        # Estimate remaining time
        if self.items_per_second > 0 and self.total_items > self.processed_items:
            remaining_items = self.total_items - self.processed_items
            self.remaining_seconds = remaining_items / self.items_per_second
            self.estimated_completion_time = now + timedelta(seconds=self.remaining_seconds)
    
    def add_error(self, error: str):
        """Add error message"""
        self.errors.append(f"[{datetime.now()}] {error}")
    
    def add_warning(self, warning: str):
        """Add warning message"""
        self.warnings.append(f"[{datetime.now()}] {warning}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'phase': self.phase.value,
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'successful_items': self.successful_items,
            'failed_items': self.failed_items,
            'skipped_items': self.skipped_items,
            'current_batch': self.current_batch,
            'total_batches': self.total_batches,
            'percentage': self.percentage,
            'elapsed_seconds': self.elapsed_seconds,
            'remaining_seconds': self.remaining_seconds,
            'items_per_second': self.items_per_second,
            'estimated_completion_time': self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
            'current_operation': self.current_operation,
            'status_message': self.status_message,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


# Type alias for progress callbacks
ProgressCallback = Callable[[OperationProgress], None]


@dataclass
class ProgressSubscription:
    """Subscription to progress updates"""
    subscription_id: str
    operation_id: str
    callback: ProgressCallback
    update_frequency: float = 1.0  # seconds
    last_update: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class ProgressTracker:
    """Progress tracking system with real-time updates and callbacks"""
    
    def __init__(self):
        """Initialize progress tracker"""
        # Active progress tracking
        self.active_progress: Dict[str, OperationProgress] = {}
        self.progress_history: Dict[str, List[OperationProgress]] = {}
        
        # Subscription management
        self.subscriptions: Dict[str, ProgressSubscription] = {}
        self.operation_subscribers: Dict[str, Set[str]] = {}
        
        # Background update thread
        self._update_thread: Optional[threading.Thread] = None
        self._running = False
        self._update_lock = threading.Lock()
        
        # Performance tracking
        self.tracker_stats = {
            'total_operations': 0,
            'active_operations': 0,
            'total_updates': 0,
            'average_update_frequency': 0.0
        }
        
        # Start background update thread
        self.start_background_updates()
    
    def start_operation(self, 
                       operation_id: str, 
                       operation_type: str,
                       total_items: int = 0) -> OperationProgress:
        """Start tracking progress for an operation
        
        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation being tracked
            total_items: Total number of items to process
            
        Returns:
            OperationProgress object for the operation
        """
        with self._update_lock:
            progress = OperationProgress(
                operation_id=operation_id,
                operation_type=operation_type,
                total_items=total_items,
                phase=ProgressPhase.INITIALIZING
            )
            
            self.active_progress[operation_id] = progress
            self.progress_history[operation_id] = [progress]
            
            # Update stats
            self.tracker_stats['total_operations'] += 1
            self.tracker_stats['active_operations'] = len(self.active_progress)
            
        return progress
    
    def update_progress(self, 
                       operation_id: str, 
                       progress: OperationProgress) -> bool:
        """Update progress for an operation
        
        Args:
            operation_id: Operation identifier
            progress: Updated progress information
            
        Returns:
            True if update was successful
        """
        if operation_id not in self.active_progress:
            return False
        
        with self._update_lock:
            # Update timing calculations
            progress.update_timing()
            progress.update_percentage()
            
            # Store updated progress
            self.active_progress[operation_id] = progress
            
            # Add to history
            if operation_id in self.progress_history:
                self.progress_history[operation_id].append(progress)
            
            # Update stats
            self.tracker_stats['total_updates'] += 1
            
        # Notify subscribers
        self._notify_subscribers(operation_id, progress)
        
        return True
    
    def complete_operation(self, 
                          operation_id: str, 
                          final_status: ProgressPhase = ProgressPhase.COMPLETED):
        """Mark operation as completed
        
        Args:
            operation_id: Operation identifier
            final_status: Final status of the operation
        """
        if operation_id not in self.active_progress:
            return
        
        with self._update_lock:
            progress = self.active_progress[operation_id]
            progress.phase = final_status
            progress.update_timing()
            progress.update_percentage()
            
            # Final notification
            self._notify_subscribers(operation_id, progress)
            
            # Move to history only
            del self.active_progress[operation_id]
            
            # Update stats
            self.tracker_stats['active_operations'] = len(self.active_progress)
    
    def get_progress(self, operation_id: str) -> Optional[OperationProgress]:
        """Get current progress for an operation
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            OperationProgress if found, None otherwise
        """
        return self.active_progress.get(operation_id)
    
    def list_active_operations(self) -> List[OperationProgress]:
        """Get list of all active operations
        
        Returns:
            List of active OperationProgress objects
        """
        with self._update_lock:
            return list(self.active_progress.values())
    
    def get_operation_history(self, operation_id: str) -> List[OperationProgress]:
        """Get progress history for an operation
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            List of OperationProgress snapshots
        """
        return self.progress_history.get(operation_id, [])
    
    def subscribe_to_progress(self, 
                             operation_id: str, 
                             callback: ProgressCallback,
                             update_frequency: float = 1.0) -> str:
        """Subscribe to progress updates for an operation
        
        Args:
            operation_id: Operation identifier to subscribe to
            callback: Function to call with progress updates
            update_frequency: Minimum seconds between updates
            
        Returns:
            Subscription ID for managing the subscription
        """
        subscription_id = str(uuid4())
        
        subscription = ProgressSubscription(
            subscription_id=subscription_id,
            operation_id=operation_id,
            callback=callback,
            update_frequency=update_frequency
        )
        
        with self._update_lock:
            self.subscriptions[subscription_id] = subscription
            
            if operation_id not in self.operation_subscribers:
                self.operation_subscribers[operation_id] = set()
            self.operation_subscribers[operation_id].add(subscription_id)
        
        return subscription_id
    
    def unsubscribe_from_progress(self, subscription_id: str) -> bool:
        """Unsubscribe from progress updates
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            True if unsubscription was successful
        """
        if subscription_id not in self.subscriptions:
            return False
        
        with self._update_lock:
            subscription = self.subscriptions[subscription_id]
            operation_id = subscription.operation_id
            
            # Remove from subscriptions
            del self.subscriptions[subscription_id]
            
            # Remove from operation subscribers
            if operation_id in self.operation_subscribers:
                self.operation_subscribers[operation_id].discard(subscription_id)
                if not self.operation_subscribers[operation_id]:
                    del self.operation_subscribers[operation_id]
        
        return True
    
    def start_background_updates(self):
        """Start background thread for periodic updates"""
        if self._running:
            return
        
        self._running = True
        self._update_thread = threading.Thread(
            target=self._background_update_loop,
            daemon=True
        )
        self._update_thread.start()
    
    def stop_background_updates(self):
        """Stop background update thread"""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
    
    def get_tracker_statistics(self) -> Dict[str, Any]:
        """Get progress tracker statistics
        
        Returns:
            Dictionary with tracker statistics
        """
        with self._update_lock:
            return {
                **self.tracker_stats,
                'active_subscriptions': len(self.subscriptions),
                'total_history_entries': sum(len(h) for h in self.progress_history.values())
            }
    
    def cleanup_old_history(self, max_age_hours: int = 24):
        """Clean up old progress history entries
        
        Args:
            max_age_hours: Maximum age of history entries to keep
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._update_lock:
            operations_to_remove = []
            
            for operation_id, history in self.progress_history.items():
                # Keep only recent entries
                recent_entries = [
                    entry for entry in history
                    if entry.start_time > cutoff_time
                ]
                
                if recent_entries:
                    self.progress_history[operation_id] = recent_entries
                else:
                    operations_to_remove.append(operation_id)
            
            # Remove operations with no recent history
            for operation_id in operations_to_remove:
                del self.progress_history[operation_id]
    
    def _notify_subscribers(self, operation_id: str, progress: OperationProgress):
        """Notify subscribers of progress update"""
        if operation_id not in self.operation_subscribers:
            return
        
        current_time = datetime.now()
        subscribers_to_notify = []
        
        # Find subscribers ready for update
        for subscription_id in self.operation_subscribers[operation_id]:
            if subscription_id in self.subscriptions:
                subscription = self.subscriptions[subscription_id]
                
                # Check if enough time has passed since last update
                time_since_update = (current_time - subscription.last_update).total_seconds()
                if time_since_update >= subscription.update_frequency:
                    subscribers_to_notify.append(subscription)
        
        # Notify subscribers
        for subscription in subscribers_to_notify:
            try:
                subscription.callback(progress)
                subscription.last_update = current_time
            except Exception as e:
                # Log error and deactivate subscription
                subscription.is_active = False
                print(f"Error in progress callback: {e}")
    
    def _background_update_loop(self):
        """Background thread loop for periodic updates"""
        while self._running:
            try:
                # Update timing for all active operations
                with self._update_lock:
                    for progress in self.active_progress.values():
                        progress.update_timing()
                        progress.update_percentage()
                
                # Sleep for update interval
                time.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                print(f"Error in background update loop: {e}")
                time.sleep(1.0)
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop_background_updates()


# Global progress tracker instance
_global_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance
    
    Returns:
        Global ProgressTracker instance
    """
    global _global_progress_tracker
    if _global_progress_tracker is None:
        _global_progress_tracker = ProgressTracker()
    return _global_progress_tracker


# Convenience functions for common progress operations

def start_operation_progress(operation_id: str, 
                           operation_type: str,
                           total_items: int = 0) -> OperationProgress:
    """Start tracking progress for an operation (convenience function)"""
    tracker = get_progress_tracker()
    return tracker.start_operation(operation_id, operation_type, total_items)


def update_operation_progress(operation_id: str, progress: OperationProgress) -> bool:
    """Update operation progress (convenience function)"""
    tracker = get_progress_tracker()
    return tracker.update_progress(operation_id, progress)


def complete_operation_progress(operation_id: str, 
                              final_status: ProgressPhase = ProgressPhase.COMPLETED):
    """Complete operation progress (convenience function)"""
    tracker = get_progress_tracker()
    return tracker.complete_operation(operation_id, final_status)


def subscribe_to_operation_progress(operation_id: str, 
                                  callback: ProgressCallback,
                                  update_frequency: float = 1.0) -> str:
    """Subscribe to operation progress (convenience function)"""
    tracker = get_progress_tracker()
    return tracker.subscribe_to_progress(operation_id, callback, update_frequency)