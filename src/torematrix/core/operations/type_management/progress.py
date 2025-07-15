"""Operation Progress Tracking

Real-time progress monitoring for type management operations.
Provides detailed tracking, notifications, and performance metrics.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Set
import json
from queue import Queue, Empty
import weakref

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Status of progress tracking"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressEvent(Enum):
    """Types of progress events"""
    STARTED = "started"
    PROGRESS_UPDATE = "progress_update"
    MILESTONE_REACHED = "milestone_reached"
    WARNING = "warning"
    ERROR = "error"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressMilestone:
    """Progress milestone marker"""
    milestone_id: str
    name: str
    description: str
    target_percentage: float
    reached: bool = False
    reached_at: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressMetrics:
    """Performance metrics for progress tracking"""
    items_per_second: float = 0.0
    average_item_time: float = 0.0
    peak_items_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    estimated_completion: Optional[datetime] = None
    time_remaining_seconds: float = 0.0
    efficiency_score: float = 0.0  # 0.0 to 1.0


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a point in time"""
    timestamp: datetime
    current_item: int
    total_items: int
    percentage: float
    status: ProgressStatus
    current_operation: str
    metrics: ProgressMetrics
    errors_count: int = 0
    warnings_count: int = 0


@dataclass
class OperationProgress:
    """Comprehensive progress information for an operation"""
    operation_id: str
    operation_name: str
    description: str
    total_items: int
    current_item: int = 0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    current_operation: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    milestones: List[ProgressMilestone] = field(default_factory=list)
    metrics: ProgressMetrics = field(default_factory=ProgressMetrics)
    events: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return min((self.current_item / self.total_items) * 100.0, 100.0)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate operation duration"""
        if not self.start_time:
            return 0.0
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
    
    @property
    def is_active(self) -> bool:
        """Check if operation is currently active"""
        return self.status in (ProgressStatus.INITIALIZING, ProgressStatus.RUNNING, ProgressStatus.PAUSED)
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.status in (ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED)
    
    def get_milestone_progress(self) -> Dict[str, bool]:
        """Get milestone completion status"""
        return {m.milestone_id: m.reached for m in self.milestones}


# Type alias for progress callback functions
ProgressCallback = Callable[[OperationProgress], None]


class ProgressTracker:
    """Real-time progress tracking system
    
    Provides comprehensive progress monitoring with:
    - Real-time progress updates
    - Performance metrics calculation
    - Milestone tracking
    - Event logging and notifications
    - Multi-operation support
    - Thread-safe operations
    """
    
    def __init__(self, max_history_entries: int = 1000):
        """Initialize progress tracker
        
        Args:
            max_history_entries: Maximum number of history entries to keep
        """
        self.max_history_entries = max_history_entries
        
        self._operations: Dict[str, OperationProgress] = {}
        self._callbacks: Dict[str, List[ProgressCallback]] = {}
        self._global_callbacks: List[ProgressCallback] = []
        self._history: Dict[str, List[ProgressSnapshot]] = {}
        self._lock = threading.RLock()
        self._event_queue = Queue()
        self._metrics_thread: Optional[threading.Thread] = None
        self._running = False
        
        self._start_metrics_thread()
        
        logger.info("ProgressTracker initialized")
    
    def create_operation(self, 
                        operation_id: str,
                        operation_name: str,
                        description: str,
                        total_items: int,
                        milestones: Optional[List[ProgressMilestone]] = None) -> OperationProgress:
        """Create a new operation for progress tracking
        
        Args:
            operation_id: Unique identifier for the operation
            operation_name: Human-readable name
            description: Operation description
            total_items: Total number of items to process
            milestones: Optional list of progress milestones
            
        Returns:
            OperationProgress object for tracking
            
        Raises:
            ValueError: If operation_id already exists
        """
        with self._lock:
            if operation_id in self._operations:
                raise ValueError(f"Operation {operation_id} already exists")
            
            progress = OperationProgress(
                operation_id=operation_id,
                operation_name=operation_name,
                description=description,
                total_items=total_items,
                milestones=milestones or []
            )
            
            self._operations[operation_id] = progress
            self._callbacks[operation_id] = []
            self._history[operation_id] = []
            
            logger.info(f"Created operation {operation_id}: {operation_name}")
            return progress
    
    def start_operation(self, operation_id: str) -> None:
        """Start tracking an operation
        
        Args:
            operation_id: ID of operation to start
            
        Raises:
            ValueError: If operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                raise ValueError(f"Operation {operation_id} not found")
            
            progress = self._operations[operation_id]
            progress.status = ProgressStatus.RUNNING
            progress.start_time = datetime.now()
            progress.last_update = datetime.now()
            
            self._add_event(operation_id, ProgressEvent.STARTED, {
                'total_items': progress.total_items,
                'milestones': len(progress.milestones)
            })
            
            self._notify_callbacks(operation_id, progress)
            logger.info(f"Started operation {operation_id}")
    
    def update_progress(self, 
                       operation_id: str,
                       current_item: int,
                       current_operation: str = "",
                       custom_data: Optional[Dict[str, Any]] = None) -> None:
        """Update operation progress
        
        Args:
            operation_id: ID of operation to update
            current_item: Current item number (0-based or 1-based)
            current_operation: Description of current operation
            custom_data: Additional custom data
            
        Raises:
            ValueError: If operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                raise ValueError(f"Operation {operation_id} not found")
            
            progress = self._operations[operation_id]
            progress.current_item = current_item
            progress.last_update = datetime.now()
            
            if current_operation:
                progress.current_operation = current_operation
            
            if custom_data:
                progress.custom_data.update(custom_data)
            
            # Update metrics
            self._update_metrics(progress)
            
            # Check milestones
            self._check_milestones(progress)
            
            # Add to history
            self._add_to_history(progress)
            
            self._add_event(operation_id, ProgressEvent.PROGRESS_UPDATE, {
                'current_item': current_item,
                'percentage': progress.percentage,
                'current_operation': current_operation
            })
            
            self._notify_callbacks(operation_id, progress)
    
    def complete_operation(self, 
                          operation_id: str,
                          success: bool = True,
                          final_message: str = "") -> None:
        """Mark operation as complete
        
        Args:
            operation_id: ID of operation to complete
            success: Whether operation completed successfully
            final_message: Optional final message
            
        Raises:
            ValueError: If operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                raise ValueError(f"Operation {operation_id} not found")
            
            progress = self._operations[operation_id]
            progress.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
            progress.end_time = datetime.now()
            progress.current_item = progress.total_items
            
            if final_message:
                progress.current_operation = final_message
            
            # Final metrics update
            self._update_metrics(progress)
            
            # Add to history
            self._add_to_history(progress)
            
            event_type = ProgressEvent.COMPLETED if success else ProgressEvent.FAILED
            self._add_event(operation_id, event_type, {
                'duration_seconds': progress.duration_seconds,
                'final_message': final_message
            })
            
            self._notify_callbacks(operation_id, progress)
            logger.info(f"Completed operation {operation_id}: {progress.status}")
    
    def cancel_operation(self, operation_id: str, reason: str = "") -> None:
        """Cancel an operation
        
        Args:
            operation_id: ID of operation to cancel
            reason: Optional cancellation reason
            
        Raises:
            ValueError: If operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                raise ValueError(f"Operation {operation_id} not found")
            
            progress = self._operations[operation_id]
            progress.status = ProgressStatus.CANCELLED
            progress.end_time = datetime.now()
            
            if reason:
                progress.current_operation = f"Cancelled: {reason}"
            
            self._add_event(operation_id, ProgressEvent.CANCELLED, {
                'reason': reason,
                'items_processed': progress.current_item
            })
            
            self._notify_callbacks(operation_id, progress)
            logger.info(f"Cancelled operation {operation_id}: {reason}")
    
    def add_warning(self, operation_id: str, warning: str) -> None:
        """Add warning to operation
        
        Args:
            operation_id: ID of operation
            warning: Warning message
        """
        with self._lock:
            if operation_id in self._operations:
                progress = self._operations[operation_id]
                progress.warnings.append(warning)
                
                self._add_event(operation_id, ProgressEvent.WARNING, {
                    'warning': warning,
                    'total_warnings': len(progress.warnings)
                })
                
                self._notify_callbacks(operation_id, progress)
    
    def add_error(self, operation_id: str, error: str) -> None:
        """Add error to operation
        
        Args:
            operation_id: ID of operation
            error: Error message
        """
        with self._lock:
            if operation_id in self._operations:
                progress = self._operations[operation_id]
                progress.errors.append(error)
                
                self._add_event(operation_id, ProgressEvent.ERROR, {
                    'error': error,
                    'total_errors': len(progress.errors)
                })
                
                self._notify_callbacks(operation_id, progress)
    
    def register_callback(self, 
                         operation_id: str, 
                         callback: ProgressCallback) -> None:
        """Register callback for operation progress updates
        
        Args:
            operation_id: ID of operation to monitor
            callback: Callback function to call on updates
        """
        with self._lock:
            if operation_id not in self._callbacks:
                self._callbacks[operation_id] = []
            self._callbacks[operation_id].append(callback)
    
    def register_global_callback(self, callback: ProgressCallback) -> None:
        """Register callback for all operation updates
        
        Args:
            callback: Callback function to call on all updates
        """
        with self._lock:
            self._global_callbacks.append(callback)
    
    def get_operation_progress(self, operation_id: str) -> Optional[OperationProgress]:
        """Get current progress for operation
        
        Args:
            operation_id: ID of operation
            
        Returns:
            OperationProgress if found, None otherwise
        """
        with self._lock:
            return self._operations.get(operation_id)
    
    def get_active_operations(self) -> List[str]:
        """Get list of active operation IDs"""
        with self._lock:
            return [op_id for op_id, progress in self._operations.items() if progress.is_active]
    
    def get_operation_history(self, operation_id: str) -> List[ProgressSnapshot]:
        """Get progress history for operation
        
        Args:
            operation_id: ID of operation
            
        Returns:
            List of progress snapshots
        """
        with self._lock:
            return self._history.get(operation_id, []).copy()
    
    def get_operation_summary(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for operation
        
        Args:
            operation_id: ID of operation
            
        Returns:
            Summary dictionary if found, None otherwise
        """
        with self._lock:
            if operation_id not in self._operations:
                return None
            
            progress = self._operations[operation_id]
            return {
                'operation_id': operation_id,
                'operation_name': progress.operation_name,
                'status': progress.status.value,
                'percentage': progress.percentage,
                'duration_seconds': progress.duration_seconds,
                'items_processed': progress.current_item,
                'total_items': progress.total_items,
                'errors_count': len(progress.errors),
                'warnings_count': len(progress.warnings),
                'milestones_reached': sum(1 for m in progress.milestones if m.reached),
                'total_milestones': len(progress.milestones),
                'items_per_second': progress.metrics.items_per_second,
                'estimated_completion': progress.metrics.estimated_completion
            }
    
    def cleanup_operation(self, operation_id: str) -> None:
        """Clean up operation data
        
        Args:
            operation_id: ID of operation to clean up
        """
        with self._lock:
            self._operations.pop(operation_id, None)
            self._callbacks.pop(operation_id, None)
            self._history.pop(operation_id, None)
            logger.debug(f"Cleaned up operation {operation_id}")
    
    def _update_metrics(self, progress: OperationProgress) -> None:
        """Update performance metrics for operation"""
        if not progress.start_time:
            return
        
        duration = (datetime.now() - progress.start_time).total_seconds()
        
        if duration > 0:
            # Calculate items per second
            progress.metrics.items_per_second = progress.current_item / duration
            
            # Update peak rate
            if progress.metrics.items_per_second > progress.metrics.peak_items_per_second:
                progress.metrics.peak_items_per_second = progress.metrics.items_per_second
            
            # Calculate average item time
            if progress.current_item > 0:
                progress.metrics.average_item_time = duration / progress.current_item
            
            # Estimate completion time
            if progress.metrics.items_per_second > 0:
                remaining_items = progress.total_items - progress.current_item
                remaining_seconds = remaining_items / progress.metrics.items_per_second
                progress.metrics.time_remaining_seconds = remaining_seconds
                progress.metrics.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
            
            # Calculate efficiency score (simplified)
            expected_rate = progress.total_items / 3600  # Assume 1 hour baseline
            if expected_rate > 0:
                progress.metrics.efficiency_score = min(progress.metrics.items_per_second / expected_rate, 1.0)
    
    def _check_milestones(self, progress: OperationProgress) -> None:
        """Check and mark reached milestones"""
        for milestone in progress.milestones:
            if not milestone.reached and progress.percentage >= milestone.target_percentage:
                milestone.reached = True
                milestone.reached_at = datetime.now()
                
                self._add_event(progress.operation_id, ProgressEvent.MILESTONE_REACHED, {
                    'milestone_id': milestone.milestone_id,
                    'milestone_name': milestone.name,
                    'target_percentage': milestone.target_percentage,
                    'actual_percentage': progress.percentage
                })
                
                logger.info(f"Milestone reached in {progress.operation_id}: {milestone.name}")
    
    def _add_to_history(self, progress: OperationProgress) -> None:
        """Add progress snapshot to history"""
        snapshot = ProgressSnapshot(
            timestamp=datetime.now(),
            current_item=progress.current_item,
            total_items=progress.total_items,
            percentage=progress.percentage,
            status=progress.status,
            current_operation=progress.current_operation,
            metrics=ProgressMetrics(
                items_per_second=progress.metrics.items_per_second,
                average_item_time=progress.metrics.average_item_time,
                peak_items_per_second=progress.metrics.peak_items_per_second,
                memory_usage_mb=progress.metrics.memory_usage_mb,
                cpu_usage_percent=progress.metrics.cpu_usage_percent,
                estimated_completion=progress.metrics.estimated_completion,
                time_remaining_seconds=progress.metrics.time_remaining_seconds,
                efficiency_score=progress.metrics.efficiency_score
            ),
            errors_count=len(progress.errors),
            warnings_count=len(progress.warnings)
        )
        
        history = self._history[progress.operation_id]
        history.append(snapshot)
        
        # Limit history size
        if len(history) > self.max_history_entries:
            history.pop(0)
    
    def _add_event(self, operation_id: str, event_type: ProgressEvent, data: Dict[str, Any]) -> None:
        """Add event to operation log"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type.value,
            'data': data
        }
        
        if operation_id in self._operations:
            self._operations[operation_id].events.append(event)
    
    def _notify_callbacks(self, operation_id: str, progress: OperationProgress) -> None:
        """Notify registered callbacks of progress update"""
        # Operation-specific callbacks
        for callback in self._callbacks.get(operation_id, []):
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback failed for {operation_id}: {e}")
        
        # Global callbacks
        for callback in self._global_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Global progress callback failed: {e}")
    
    def _start_metrics_thread(self) -> None:
        """Start background thread for metrics collection"""
        self._running = True
        self._metrics_thread = threading.Thread(target=self._metrics_worker, daemon=True)
        self._metrics_thread.start()
    
    def _metrics_worker(self) -> None:
        """Background worker for collecting system metrics"""
        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False
            logger.warning("psutil not available, system metrics disabled")
        
        while self._running:
            try:
                if has_psutil:
                    memory_info = psutil.virtual_memory()
                    cpu_percent = psutil.cpu_percent(interval=None)
                    
                    with self._lock:
                        for progress in self._operations.values():
                            if progress.is_active:
                                progress.metrics.memory_usage_mb = memory_info.used / (1024 * 1024)
                                progress.metrics.cpu_usage_percent = cpu_percent
                
                time.sleep(1.0)  # Update every second
                
            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def __del__(self):
        """Cleanup when tracker is destroyed"""
        self._running = False
        if self._metrics_thread and self._metrics_thread.is_alive():
            self._metrics_thread.join(timeout=1.0)