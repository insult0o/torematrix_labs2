"""Progress Tracking System

Real-time progress tracking system for bulk operations with:
- Operation lifecycle management and state tracking
- Real-time progress updates with callbacks
- Phase management and progress estimation  
- Background update threads for non-blocking tracking
- Thread-safe progress operations
"""

import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class ProgressPhase(Enum):
    """Operation progress phases"""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    VALIDATING = "validating"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Type alias for progress callbacks
ProgressCallback = Callable[['OperationProgress'], None]


@dataclass
class OperationProgress:
    """Progress tracking for an operation"""
    
    operation_id: str
    operation_type: str
    phase: ProgressPhase = ProgressPhase.INITIALIZING
    current_item: int = 0
    total_items: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return min((self.current_item / self.total_items) * 100.0, 100.0)
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time"""
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    @property
    def estimated_total_time(self) -> timedelta:
        """Estimate total operation time"""
        if self.current_item == 0 or self.total_items == 0:
            return timedelta()
        
        elapsed = self.elapsed_time
        progress_ratio = self.current_item / self.total_items
        
        if progress_ratio > 0:
            estimated_total_seconds = elapsed.total_seconds() / progress_ratio
            return timedelta(seconds=estimated_total_seconds)
        
        return timedelta()
    
    @property
    def estimated_remaining_time(self) -> timedelta:
        """Estimate remaining operation time"""
        estimated_total = self.estimated_total_time
        elapsed = self.elapsed_time
        
        remaining = estimated_total - elapsed
        return remaining if remaining.total_seconds() > 0 else timedelta()
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.phase in (ProgressPhase.COMPLETED, ProgressPhase.FAILED, ProgressPhase.CANCELLED)


class ProgressTracker:
    """Thread-safe progress tracking system
    
    Manages progress tracking for multiple concurrent operations with:
    - Real-time progress updates
    - Subscriber notification system
    - Background update threads
    - Operation lifecycle management
    """
    
    def __init__(self):
        """Initialize progress tracker"""
        self.operations: Dict[str, OperationProgress] = {}
        self.subscribers: Dict[str, List[ProgressCallback]] = {}
        self._lock = threading.RLock()
        self._update_thread: Optional[threading.Thread] = None
        self._running = False
        
        logger.info("ProgressTracker initialized")
    
    def start_operation(self, 
                       operation_id: str, 
                       operation_type: str,
                       total_items: int = 0) -> OperationProgress:
        """Start tracking a new operation
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation being tracked
            total_items: Total number of items to process
            
        Returns:
            OperationProgress instance for the new operation
            
        Raises:
            ValueError: If operation ID already exists
        """
        with self._lock:
            if operation_id in self.operations:
                raise ValueError(f"Operation with ID '{operation_id}' already exists")
            
            progress = OperationProgress(
                operation_id=operation_id,
                operation_type=operation_type,
                total_items=total_items
            )
            
            self.operations[operation_id] = progress
            
            # Initialize subscriber list
            if operation_id not in self.subscribers:
                self.subscribers[operation_id] = []
            
            logger.info(f"Started tracking operation {operation_id} ({operation_type})")
            
            # Notify subscribers
            self._notify_subscribers(operation_id, progress)
            
            return progress
    
    def update_operation_progress(self, 
                                 operation_id: str,
                                 current_item: Optional[int] = None,
                                 phase: Optional[ProgressPhase] = None,
                                 message: str = "",
                                 details: Optional[Dict[str, Any]] = None) -> bool:
        """Update progress for an operation
        
        Args:
            operation_id: ID of operation to update
            current_item: Current item being processed
            phase: Current operation phase
            message: Progress message
            details: Additional progress details
            
        Returns:
            True if update was successful, False if operation not found
        """
        with self._lock:
            if operation_id not in self.operations:
                return False
            
            progress = self.operations[operation_id]
            
            if current_item is not None:
                progress.current_item = current_item
            
            if phase is not None:
                progress.phase = phase
            
            if message:
                progress.message = message
            
            if details:
                progress.details.update(details)
            
            progress.last_update = datetime.now()
            
            # Notify subscribers
            self._notify_subscribers(operation_id, progress)
            
            return True
    
    def complete_operation(self, 
                          operation_id: str,
                          final_phase: ProgressPhase,
                          message: str = "") -> bool:
        """Mark operation as complete
        
        Args:
            operation_id: ID of operation to complete
            final_phase: Final phase (COMPLETED, FAILED, or CANCELLED)
            message: Final message
            
        Returns:
            True if operation was marked complete, False if not found
        """
        with self._lock:
            if operation_id not in self.operations:
                return False
            
            progress = self.operations[operation_id]
            progress.phase = final_phase
            progress.end_time = datetime.now()
            progress.last_update = progress.end_time
            
            if message:
                progress.message = message
            
            logger.info(f"Operation {operation_id} completed with phase {final_phase}")
            
            # Final notification to subscribers
            self._notify_subscribers(operation_id, progress)
            
            return True
    
    def get_operation_progress(self, operation_id: str) -> Optional[OperationProgress]:
        """Get current progress for an operation
        
        Args:
            operation_id: ID of operation to get progress for
            
        Returns:
            OperationProgress if found, None otherwise
        """
        with self._lock:
            return self.operations.get(operation_id)
    
    def list_active_operations(self) -> List[str]:
        """List all active (non-complete) operation IDs
        
        Returns:
            List of active operation IDs
        """
        with self._lock:
            return [
                op_id for op_id, progress in self.operations.items()
                if not progress.is_complete
            ]
    
    def subscribe_to_operation(self, operation_id: str, callback: ProgressCallback):
        """Subscribe to progress updates for an operation
        
        Args:
            operation_id: ID of operation to subscribe to
            callback: Function to call on progress updates
        """
        with self._lock:
            if operation_id not in self.subscribers:
                self.subscribers[operation_id] = []
            
            if callback not in self.subscribers[operation_id]:
                self.subscribers[operation_id].append(callback)
                logger.debug(f"Added subscriber for operation {operation_id}")
    
    def unsubscribe_from_operation(self, operation_id: str, callback: ProgressCallback):
        """Unsubscribe from progress updates for an operation
        
        Args:
            operation_id: ID of operation to unsubscribe from
            callback: Callback function to remove
        """
        with self._lock:
            if operation_id in self.subscribers:
                try:
                    self.subscribers[operation_id].remove(callback)
                    logger.debug(f"Removed subscriber for operation {operation_id}")
                except ValueError:
                    pass  # Callback not in list
    
    def start_background_updates(self, update_interval: float = 0.1):
        """Start background thread for progress updates
        
        Args:
            update_interval: Interval between updates in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._update_thread = threading.Thread(
            target=self._background_update_loop,
            args=(update_interval,),
            daemon=True
        )
        self._update_thread.start()
        
        logger.info("Started background progress updates")
    
    def stop_background_updates(self):
        """Stop background update thread"""
        if not self._running:
            return
        
        self._running = False
        
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join()
        
        logger.info("Stopped background progress updates")
    
    def cleanup_completed_operations(self, keep_hours: int = 1):
        """Clean up completed operations older than specified hours
        
        Args:
            keep_hours: Number of hours to keep completed operations
        """
        cutoff_time = datetime.now() - timedelta(hours=keep_hours)
        
        with self._lock:
            to_remove = []
            
            for op_id, progress in self.operations.items():
                if (progress.is_complete and 
                    progress.end_time and 
                    progress.end_time < cutoff_time):
                    to_remove.append(op_id)
            
            for op_id in to_remove:
                del self.operations[op_id]
                self.subscribers.pop(op_id, None)
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} completed operations")
    
    def get_operation_statistics(self) -> Dict[str, Any]:
        """Get statistics about tracked operations
        
        Returns:
            Dictionary with operation statistics
        """
        with self._lock:
            total_ops = len(self.operations)
            active_ops = len(self.list_active_operations())
            completed_ops = 0
            failed_ops = 0
            operation_types = {}
            
            for progress in self.operations.values():
                # Count by final state
                if progress.phase == ProgressPhase.COMPLETED:
                    completed_ops += 1
                elif progress.phase == ProgressPhase.FAILED:
                    failed_ops += 1
                
                # Count by type
                op_type = progress.operation_type
                operation_types[op_type] = operation_types.get(op_type, 0) + 1
            
            return {
                "total_operations": total_ops,
                "active_operations": active_ops,
                "completed_operations": completed_ops,
                "failed_operations": failed_ops,
                "operation_types": operation_types
            }
    
    def _notify_subscribers(self, operation_id: str, progress: OperationProgress):
        """Notify subscribers of progress update"""
        subscribers = self.subscribers.get(operation_id, [])
        
        for callback in subscribers:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback for {operation_id}: {e}")
    
    def _background_update_loop(self, update_interval: float):
        """Background loop for periodic updates"""
        while self._running:
            try:
                # Notify subscribers of current progress
                with self._lock:
                    for op_id, progress in self.operations.items():
                        if not progress.is_complete:
                            self._notify_subscribers(op_id, progress)
                
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")


# Global progress tracker instance
_global_tracker: Optional[ProgressTracker] = None
_tracker_lock = threading.Lock()


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance (singleton)
    
    Returns:
        Global ProgressTracker instance
    """
    global _global_tracker
    
    if _global_tracker is None:
        with _tracker_lock:
            if _global_tracker is None:
                _global_tracker = ProgressTracker()
    
    return _global_tracker


# Convenience functions for module-level access

def start_operation_progress(operation_id: str, 
                           operation_type: str,
                           total_items: int = 0) -> OperationProgress:
    """Start tracking progress for an operation
    
    Args:
        operation_id: Unique identifier for the operation
        operation_type: Type of operation being tracked
        total_items: Total number of items to process
        
    Returns:
        OperationProgress instance for the new operation
    """
    tracker = get_progress_tracker()
    return tracker.start_operation(operation_id, operation_type, total_items)


def update_operation_progress(operation_id: str,
                            current_item: Optional[int] = None,
                            phase: Optional[ProgressPhase] = None,
                            message: str = "",
                            details: Optional[Dict[str, Any]] = None) -> bool:
    """Update progress for an operation
    
    Args:
        operation_id: ID of operation to update
        current_item: Current item being processed
        phase: Current operation phase
        message: Progress message
        details: Additional progress details
        
    Returns:
        True if update was successful, False if operation not found
    """
    tracker = get_progress_tracker()
    return tracker.update_operation_progress(
        operation_id, current_item, phase, message, details
    )


def complete_operation_progress(operation_id: str,
                               final_phase: ProgressPhase,
                               message: str = "") -> bool:
    """Mark operation as complete
    
    Args:
        operation_id: ID of operation to complete
        final_phase: Final phase (COMPLETED, FAILED, or CANCELLED)
        message: Final message
        
    Returns:
        True if operation was marked complete, False if not found
    """
    tracker = get_progress_tracker()
    return tracker.complete_operation(operation_id, final_phase, message)


def subscribe_to_operation_progress(operation_id: str, callback: ProgressCallback):
    """Subscribe to progress updates for an operation
    
    Args:
        operation_id: ID of operation to subscribe to
        callback: Function to call on progress updates
    """
    tracker = get_progress_tracker()
    tracker.subscribe_to_operation(operation_id, callback)