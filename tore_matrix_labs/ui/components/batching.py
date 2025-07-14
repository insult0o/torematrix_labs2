"""
State Change Batching System for Reactive Components.

This module provides efficient batching of state changes to minimize re-renders
and improve performance.
"""

import threading
import time
import asyncio
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum, auto
import logging
from contextlib import contextmanager
import weakref

logger = logging.getLogger(__name__)


class UpdatePriority(Enum):
    """Priority levels for state updates."""
    
    IMMEDIATE = auto()  # Process immediately, no batching
    HIGH = auto()       # Process in next batch
    NORMAL = auto()     # Standard batching
    LOW = auto()        # Can be delayed longer
    IDLE = auto()       # Process when idle


@dataclass
class StateChange:
    """Represents a single state change."""
    
    store_id: str
    key: str
    value: Any
    timestamp: float
    priority: UpdatePriority = UpdatePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        """Make hashable for deduplication."""
        return hash((self.store_id, self.key))


@dataclass
class BatchedUpdate:
    """Represents a batch of updates to be processed."""
    
    changes: List[StateChange]
    callback: Callable[[List[StateChange]], None]
    timestamp: float
    priority: UpdatePriority
    
    def merge_with(self, other: 'BatchedUpdate') -> 'BatchedUpdate':
        """Merge another batch into this one."""
        # Keep only the latest change for each key
        changes_by_key = {(c.store_id, c.key): c for c in self.changes}
        for change in other.changes:
            key = (change.store_id, change.key)
            if key not in changes_by_key or change.timestamp > changes_by_key[key].timestamp:
                changes_by_key[key] = change
        
        return BatchedUpdate(
            changes=list(changes_by_key.values()),
            callback=self.callback,
            timestamp=min(self.timestamp, other.timestamp),
            priority=min(self.priority, other.priority, key=lambda p: p.value)
        )


class BatchingStrategy:
    """Base class for batching strategies."""
    
    def should_flush(self, batch: BatchedUpdate, current_time: float) -> bool:
        """Determine if a batch should be flushed."""
        raise NotImplementedError
    
    def get_delay(self, priority: UpdatePriority) -> float:
        """Get delay in seconds for a priority level."""
        raise NotImplementedError


class TimeBatchingStrategy(BatchingStrategy):
    """Batching strategy based on time windows."""
    
    def __init__(
        self,
        immediate_delay: float = 0.0,
        high_delay: float = 0.016,  # ~60 FPS
        normal_delay: float = 0.050,  # ~20 FPS
        low_delay: float = 0.100,
        idle_delay: float = 0.500,
        max_batch_size: int = 100
    ):
        """Initialize time-based batching strategy."""
        self.delays = {
            UpdatePriority.IMMEDIATE: immediate_delay,
            UpdatePriority.HIGH: high_delay,
            UpdatePriority.NORMAL: normal_delay,
            UpdatePriority.LOW: low_delay,
            UpdatePriority.IDLE: idle_delay
        }
        self.max_batch_size = max_batch_size
    
    def should_flush(self, batch: BatchedUpdate, current_time: float) -> bool:
        """Check if batch should be flushed based on time."""
        delay = self.get_delay(batch.priority)
        time_elapsed = current_time - batch.timestamp
        
        return (
            time_elapsed >= delay or
            len(batch.changes) >= self.max_batch_size or
            batch.priority == UpdatePriority.IMMEDIATE
        )
    
    def get_delay(self, priority: UpdatePriority) -> float:
        """Get delay for priority level."""
        return self.delays.get(priority, self.delays[UpdatePriority.NORMAL])


class AdaptiveBatchingStrategy(BatchingStrategy):
    """Adaptive batching that adjusts based on load."""
    
    def __init__(self, base_strategy: BatchingStrategy):
        """Initialize adaptive strategy."""
        self.base_strategy = base_strategy
        self.recent_flush_times: deque = deque(maxlen=100)
        self.load_factor = 1.0
        
    def should_flush(self, batch: BatchedUpdate, current_time: float) -> bool:
        """Adaptively determine if batch should be flushed."""
        # Update load factor based on recent activity
        self._update_load_factor()
        
        # Adjust base strategy decision
        base_decision = self.base_strategy.should_flush(batch, current_time)
        
        if base_decision:
            return True
        
        # Additional adaptive logic
        adjusted_delay = self.get_delay(batch.priority)
        time_elapsed = current_time - batch.timestamp
        
        return time_elapsed >= adjusted_delay
    
    def get_delay(self, priority: UpdatePriority) -> float:
        """Get adaptively adjusted delay."""
        base_delay = self.base_strategy.get_delay(priority)
        return base_delay * self.load_factor
    
    def record_flush(self, timestamp: float) -> None:
        """Record a flush event for adaptation."""
        self.recent_flush_times.append(timestamp)
    
    def _update_load_factor(self) -> None:
        """Update load factor based on recent activity."""
        if len(self.recent_flush_times) < 2:
            return
        
        # Calculate average time between flushes
        intervals = []
        for i in range(1, len(self.recent_flush_times)):
            interval = self.recent_flush_times[i] - self.recent_flush_times[i-1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Adjust load factor
        if avg_interval < 0.010:  # Very high frequency
            self.load_factor = min(2.0, self.load_factor * 1.1)
        elif avg_interval > 0.100:  # Low frequency
            self.load_factor = max(0.5, self.load_factor * 0.9)
        else:
            self.load_factor = 1.0


class BatchProcessor:
    """Processes batched state changes."""
    
    def __init__(
        self,
        strategy: Optional[BatchingStrategy] = None,
        worker_thread: bool = True
    ):
        """
        Initialize batch processor.
        
        Args:
            strategy: Batching strategy to use
            worker_thread: Whether to use a worker thread
        """
        self.strategy = strategy or TimeBatchingStrategy()
        self.batches: Dict[int, BatchedUpdate] = {}
        self.pending_changes: List[StateChange] = []
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread = None
        self._flush_event = threading.Event()
        
        if worker_thread:
            self.start()
    
    def start(self) -> None:
        """Start the batch processor."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="BatchProcessor"
            )
            self._worker_thread.start()
    
    def stop(self) -> None:
        """Stop the batch processor."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._flush_event.set()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
    
    def add_change(
        self,
        store_id: str,
        key: str,
        value: Any,
        priority: UpdatePriority = UpdatePriority.NORMAL,
        callback: Optional[Callable[[List[StateChange]], None]] = None
    ) -> None:
        """Add a state change to be batched."""
        change = StateChange(
            store_id=store_id,
            key=key,
            value=value,
            timestamp=time.time(),
            priority=priority
        )
        
        with self._lock:
            if priority == UpdatePriority.IMMEDIATE:
                # Process immediately
                if callback:
                    callback([change])
            else:
                # Add to batch
                batch_key = hash((store_id, callback))
                
                if batch_key not in self.batches:
                    self.batches[batch_key] = BatchedUpdate(
                        changes=[change],
                        callback=callback or self._default_callback,
                        timestamp=change.timestamp,
                        priority=priority
                    )
                else:
                    # Merge with existing batch
                    existing = self.batches[batch_key]
                    new_batch = BatchedUpdate(
                        changes=[change],
                        callback=callback or self._default_callback,
                        timestamp=change.timestamp,
                        priority=priority
                    )
                    self.batches[batch_key] = existing.merge_with(new_batch)
                
                # Signal worker if high priority
                if priority == UpdatePriority.HIGH:
                    self._flush_event.set()
    
    def flush(self, force: bool = False) -> None:
        """Flush pending batches."""
        current_time = time.time()
        
        with self._lock:
            batches_to_flush = []
            
            for batch_key, batch in list(self.batches.items()):
                if force or self.strategy.should_flush(batch, current_time):
                    batches_to_flush.append(batch)
                    del self.batches[batch_key]
        
        # Process batches outside lock
        for batch in batches_to_flush:
            try:
                batch.callback(batch.changes)
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
            
            # Record flush for adaptive strategies
            if isinstance(self.strategy, AdaptiveBatchingStrategy):
                self.strategy.record_flush(current_time)
    
    @contextmanager
    def batch_context(self):
        """Context manager for explicit batching."""
        # Suspend automatic flushing
        old_running = self._running
        self._running = False
        
        try:
            yield self
        finally:
            # Restore and flush
            self._running = old_running
            self.flush(force=True)
    
    def _worker_loop(self) -> None:
        """Worker thread loop for processing batches."""
        while self._running:
            try:
                # Wait for signal or timeout
                min_delay = min(
                    self.strategy.get_delay(p)
                    for p in UpdatePriority
                )
                self._flush_event.wait(timeout=min_delay)
                self._flush_event.clear()
                
                # Process batches
                self.flush()
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
    
    def _default_callback(self, changes: List[StateChange]) -> None:
        """Default callback that logs changes."""
        logger.debug(f"Processing {len(changes)} batched changes")


class DebouncedUpdater:
    """Debounces rapid updates to the same value."""
    
    def __init__(
        self,
        callback: Callable[[Any], None],
        delay: float = 0.1,
        max_wait: float = 1.0
    ):
        """
        Initialize debounced updater.
        
        Args:
            callback: Function to call with debounced value
            delay: Delay before calling callback
            max_wait: Maximum time to wait before forcing update
        """
        self.callback = callback
        self.delay = delay
        self.max_wait = max_wait
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._last_value = None
        self._first_call_time: Optional[float] = None
    
    def update(self, value: Any) -> None:
        """Update with debouncing."""
        with self._lock:
            current_time = time.time()
            self._last_value = value
            
            # Track first call time
            if self._first_call_time is None:
                self._first_call_time = current_time
            
            # Check if we've waited too long
            if current_time - self._first_call_time >= self.max_wait:
                self._flush()
                return
            
            # Cancel existing timer
            if self._timer:
                self._timer.cancel()
            
            # Schedule new timer
            self._timer = threading.Timer(self.delay, self._flush)
            self._timer.daemon = True
            self._timer.start()
    
    def _flush(self) -> None:
        """Flush the debounced value."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            
            value = self._last_value
            self._last_value = None
            self._first_call_time = None
        
        if value is not None:
            try:
                self.callback(value)
            except Exception as e:
                logger.error(f"Error in debounced callback: {e}")
    
    def cancel(self) -> None:
        """Cancel pending updates."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._last_value = None
            self._first_call_time = None


# Global batch processor
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get or create the global batch processor."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor(worker_thread=False)
    return _batch_processor


def batch_state_change(
    store_id: str,
    key: str,
    value: Any,
    priority: UpdatePriority = UpdatePriority.NORMAL,
    callback: Optional[Callable[[List[StateChange]], None]] = None
) -> None:
    """Add a state change to the global batch processor."""
    processor = get_batch_processor()
    processor.add_change(store_id, key, value, priority, callback)