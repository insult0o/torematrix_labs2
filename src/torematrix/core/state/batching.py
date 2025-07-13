"""
Update batching system for 60fps performance optimization.
"""

import asyncio
import time
import threading
from typing import Any, Dict, List, Optional, Callable, Set, Deque
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import weakref


class BatchPriority(Enum):
    """Priority levels for batched updates."""
    IMMEDIATE = 0    # Process immediately, no batching
    HIGH = 1        # Process within 4ms (240fps)
    NORMAL = 2      # Process within 16ms (60fps)
    LOW = 3         # Process within 33ms (30fps)
    BACKGROUND = 4  # Process when idle


@dataclass
class StateUpdate:
    """Represents a state update operation."""
    id: str
    path: str
    value: Any
    operation: str = "set"  # "set", "merge", "delete", "array_push", "array_remove"
    timestamp: float = field(default_factory=time.time)
    priority: BatchPriority = BatchPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    
    @property
    def age_ms(self) -> float:
        """Get age of update in milliseconds."""
        return (time.time() - self.timestamp) * 1000


@dataclass
class BatchStats:
    """Statistics for update batching."""
    total_updates: int = 0
    batched_updates: int = 0
    immediate_updates: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time_ms: float = 0.0
    dropped_updates: int = 0
    late_updates: int = 0
    
    def update_stats(self, batch_size: int, processing_time_ms: float):
        """Update batch statistics."""
        self.batched_updates += batch_size
        self.total_updates += batch_size
        
        # Calculate rolling average
        if self.avg_batch_size == 0:
            self.avg_batch_size = batch_size
            self.avg_processing_time_ms = processing_time_ms
        else:
            self.avg_batch_size = (self.avg_batch_size * 0.9) + (batch_size * 0.1)
            self.avg_processing_time_ms = (self.avg_processing_time_ms * 0.9) + (processing_time_ms * 0.1)


class UpdateBatcher:
    """
    High-performance update batching system for 60fps performance.
    
    Batches state updates to minimize re-renders and maintain smooth UI performance.
    Supports priority-based scheduling and dependency resolution.
    """
    
    def __init__(
        self,
        target_fps: int = 60,
        max_batch_size: int = 1000,
        enable_priority_scheduling: bool = True,
        enable_dependency_resolution: bool = True
    ):
        self.target_fps = target_fps
        self.frame_time_ms = 1000.0 / target_fps  # 16.67ms for 60fps
        self.max_batch_size = max_batch_size
        self.enable_priority_scheduling = enable_priority_scheduling
        self.enable_dependency_resolution = enable_dependency_resolution
        
        # Update queues by priority
        self._update_queues: Dict[BatchPriority, deque] = {
            priority: deque() for priority in BatchPriority
        }
        
        # Batching state
        self._batch_timers: Dict[BatchPriority, Optional[asyncio.Task]] = {
            priority: None for priority in BatchPriority
        }
        
        # Processing callbacks
        self._update_processors: List[Callable[[List[StateUpdate]], None]] = []
        
        # Performance tracking
        self._stats = BatchStats()
        self._processing_times: deque = deque(maxlen=100)
        
        # Threading
        self._lock = threading.RLock()
        
        # Deduplication and conflict resolution
        self._pending_by_path: Dict[str, StateUpdate] = {}
        self._conflicting_updates: Set[str] = set()
        
        # Frame timing
        self._last_frame_time = time.time()
        self._frame_budget_ms = self.frame_time_ms * 0.8  # Use 80% of frame time
        
        # Adaptive batching
        self._adaptive_batching = True
        self._recent_frame_times: deque = deque(maxlen=10)
        
        # Running state
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
    
    def add_update(
        self,
        update: StateUpdate,
        deduplicate: bool = True,
        merge_conflicts: bool = True
    ):
        """
        Add a state update to the appropriate batch queue.
        
        Args:
            update: State update to batch
            deduplicate: Whether to deduplicate updates by path
            merge_conflicts: Whether to merge conflicting updates
        """
        with self._lock:
            # Handle deduplication
            if deduplicate and update.path in self._pending_by_path:
                existing_update = self._pending_by_path[update.path]
                
                if merge_conflicts:
                    # Merge updates for the same path
                    merged_update = self._merge_updates(existing_update, update)
                    self._pending_by_path[update.path] = merged_update
                    
                    # Replace in queue
                    self._replace_update_in_queue(existing_update, merged_update)
                    return
                else:
                    # Mark as conflicting
                    self._conflicting_updates.add(update.path)
            
            # Add to appropriate queue
            priority = update.priority
            self._update_queues[priority].append(update)
            self._pending_by_path[update.path] = update
            
            # Schedule processing based on priority
            if priority == BatchPriority.IMMEDIATE:
                # Process immediately
                asyncio.create_task(self._process_immediate_update(update))
            else:
                # Schedule batched processing
                self._schedule_batch_processing(priority)
    
    def _merge_updates(self, existing: StateUpdate, new: StateUpdate) -> StateUpdate:
        """Merge two updates for the same path."""
        # Use the newer update as base but combine metadata
        merged_metadata = {**existing.metadata, **new.metadata}
        
        # Use higher priority
        merged_priority = min(existing.priority, new.priority, key=lambda p: p.value)
        
        # Combine dependencies
        merged_dependencies = existing.dependencies | new.dependencies
        
        return StateUpdate(
            id=new.id,  # Use newer ID
            path=new.path,
            value=new.value,  # Use newer value
            operation=new.operation,  # Use newer operation
            timestamp=new.timestamp,  # Use newer timestamp
            priority=merged_priority,
            metadata=merged_metadata,
            dependencies=merged_dependencies
        )
    
    def _replace_update_in_queue(self, old_update: StateUpdate, new_update: StateUpdate):
        """Replace an update in the appropriate queue."""
        priority = old_update.priority
        queue = self._update_queues[priority]
        
        # Find and replace the old update
        for i, update in enumerate(queue):
            if update.id == old_update.id:
                queue[i] = new_update
                break
    
    def _schedule_batch_processing(self, priority: BatchPriority):
        """Schedule batch processing for a priority level."""
        if self._batch_timers[priority] is not None:
            return  # Already scheduled
        
        # Calculate timeout based on priority and adaptive factors
        timeout_ms = self._calculate_batch_timeout(priority)
        
        self._batch_timers[priority] = asyncio.create_task(
            self._process_batch_after_timeout(priority, timeout_ms)
        )
    
    def _calculate_batch_timeout(self, priority: BatchPriority) -> float:
        """Calculate optimal batch timeout for priority level."""
        base_timeouts = {
            BatchPriority.HIGH: 4.0,      # 240fps
            BatchPriority.NORMAL: self.frame_time_ms,  # 60fps
            BatchPriority.LOW: 33.0,      # 30fps
            BatchPriority.BACKGROUND: 100.0  # 10fps
        }
        
        base_timeout = base_timeouts.get(priority, self.frame_time_ms)
        
        if not self._adaptive_batching:
            return base_timeout
        
        # Adapt based on recent performance
        if self._recent_frame_times:
            avg_frame_time = sum(self._recent_frame_times) / len(self._recent_frame_times)
            
            # If we're running slow, increase timeouts
            if avg_frame_time > self.frame_time_ms * 1.2:
                return base_timeout * 1.5
            # If we're running fast, decrease timeouts
            elif avg_frame_time < self.frame_time_ms * 0.8:
                return base_timeout * 0.8
        
        return base_timeout
    
    async def _process_batch_after_timeout(self, priority: BatchPriority, timeout_ms: float):
        """Process batch after timeout expires."""
        try:
            await asyncio.sleep(timeout_ms / 1000.0)
            await self._process_priority_queue(priority)
        except asyncio.CancelledError:
            pass
        finally:
            with self._lock:
                self._batch_timers[priority] = None
    
    async def _process_immediate_update(self, update: StateUpdate):
        """Process an immediate priority update."""
        start_time = time.perf_counter()
        
        try:
            for processor in self._update_processors:
                processor([update])
            
            self._stats.immediate_updates += 1
            self._stats.total_updates += 1
            
        except Exception as e:
            print(f"Error processing immediate update: {e}")
        
        finally:
            processing_time = (time.perf_counter() - start_time) * 1000
            self._processing_times.append(processing_time)
            
            with self._lock:
                if update.path in self._pending_by_path:
                    del self._pending_by_path[update.path]
    
    async def _process_priority_queue(self, priority: BatchPriority):
        """Process all updates in a priority queue."""
        with self._lock:
            if not self._update_queues[priority]:
                return
            
            # Get batch of updates
            batch = []
            queue = self._update_queues[priority]
            
            while queue and len(batch) < self.max_batch_size:
                update = queue.popleft()
                
                # Check if update is still valid (not superseded)
                if update.path in self._pending_by_path:
                    current_update = self._pending_by_path[update.path]
                    if current_update.id == update.id:
                        batch.append(update)
                        del self._pending_by_path[update.path]
        
        if not batch:
            return
        
        # Resolve dependencies if enabled
        if self.enable_dependency_resolution:
            batch = self._resolve_dependencies(batch)
        
        # Process the batch
        start_time = time.perf_counter()
        
        try:
            for processor in self._update_processors:
                processor(batch)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            self._stats.update_stats(len(batch), processing_time)
            self._processing_times.append(processing_time)
            
            # Track frame timing
            current_time = time.time()
            frame_time = (current_time - self._last_frame_time) * 1000
            self._recent_frame_times.append(frame_time)
            self._last_frame_time = current_time
            
        except Exception as e:
            print(f"Error processing batch: {e}")
    
    def _resolve_dependencies(self, updates: List[StateUpdate]) -> List[StateUpdate]:
        """Resolve update dependencies and return sorted list."""
        if not any(update.dependencies for update in updates):
            return updates  # No dependencies to resolve
        
        # Build dependency graph
        update_by_path = {update.path: update for update in updates}
        resolved = []
        processing = set()
        processed = set()
        
        def resolve_update(update: StateUpdate):
            if update.path in processed:
                return
            
            if update.path in processing:
                # Circular dependency - process anyway
                resolved.append(update)
                processed.add(update.path)
                return
            
            processing.add(update.path)
            
            # Process dependencies first
            for dep_path in update.dependencies:
                if dep_path in update_by_path:
                    resolve_update(update_by_path[dep_path])
            
            resolved.append(update)
            processed.add(update.path)
            processing.remove(update.path)
        
        # Resolve all updates
        for update in updates:
            resolve_update(update)
        
        return resolved
    
    def add_update_processor(self, processor: Callable[[List[StateUpdate]], None]):
        """
        Add a processor for batched updates.
        
        Args:
            processor: Function that processes a batch of updates
        """
        self._update_processors.append(processor)
    
    def remove_update_processor(self, processor: Callable[[List[StateUpdate]], None]):
        """Remove an update processor."""
        try:
            self._update_processors.remove(processor)
        except ValueError:
            pass
    
    async def flush_all_batches(self):
        """Flush all pending batches immediately."""
        tasks = []
        
        with self._lock:
            for priority in BatchPriority:
                if self._update_queues[priority]:
                    tasks.append(self._process_priority_queue(priority))
                
                # Cancel existing timers
                if self._batch_timers[priority]:
                    self._batch_timers[priority].cancel()
                    self._batch_timers[priority] = None
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def flush_priority(self, priority: BatchPriority):
        """Flush pending batch for specific priority."""
        with self._lock:
            if self._batch_timers[priority]:
                self._batch_timers[priority].cancel()
                self._batch_timers[priority] = None
        
        await self._process_priority_queue(priority)
    
    def set_target_fps(self, fps: int):
        """Update target FPS and recalculate frame timing."""
        self.target_fps = fps
        self.frame_time_ms = 1000.0 / fps
        self._frame_budget_ms = self.frame_time_ms * 0.8
    
    def set_batch_timeout(self, timeout_ms: float):
        """Set custom batch timeout (overrides adaptive batching)."""
        self.frame_time_ms = timeout_ms
        self._adaptive_batching = False
    
    def enable_adaptive_batching(self, enabled: bool = True):
        """Enable or disable adaptive batching based on performance."""
        self._adaptive_batching = enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching performance statistics."""
        with self._lock:
            queue_sizes = {
                priority.name: len(queue) 
                for priority, queue in self._update_queues.items()
            }
            
            avg_processing_time = 0
            if self._processing_times:
                avg_processing_time = sum(self._processing_times) / len(self._processing_times)
            
            return {
                'stats': {
                    'total_updates': self._stats.total_updates,
                    'batched_updates': self._stats.batched_updates,
                    'immediate_updates': self._stats.immediate_updates,
                    'avg_batch_size': self._stats.avg_batch_size,
                    'avg_processing_time_ms': avg_processing_time,
                    'dropped_updates': self._stats.dropped_updates,
                    'late_updates': self._stats.late_updates
                },
                'queues': {
                    'sizes': queue_sizes,
                    'total_pending': sum(queue_sizes.values()),
                    'pending_paths': len(self._pending_by_path),
                    'conflicting_paths': len(self._conflicting_updates)
                },
                'performance': {
                    'target_fps': self.target_fps,
                    'frame_time_ms': self.frame_time_ms,
                    'frame_budget_ms': self._frame_budget_ms,
                    'adaptive_batching': self._adaptive_batching,
                    'avg_recent_frame_time_ms': (
                        sum(self._recent_frame_times) / len(self._recent_frame_times)
                        if self._recent_frame_times else 0
                    )
                }
            }
    
    async def start_background_processing(self):
        """Start background processing for low-priority updates."""
        if self._running:
            return
        
        self._running = True
        self._background_task = asyncio.create_task(self._background_processing_loop())
    
    async def stop_background_processing(self):
        """Stop background processing."""
        self._running = False
        
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            finally:
                self._background_task = None
    
    async def _background_processing_loop(self):
        """Background processing loop for low-priority updates."""
        while self._running:
            try:
                # Process background updates when system is idle
                if self._update_queues[BatchPriority.BACKGROUND]:
                    # Check if we have spare time in this frame
                    current_time = time.time()
                    time_since_last_frame = (current_time - self._last_frame_time) * 1000
                    
                    if time_since_last_frame < self._frame_budget_ms:
                        await self._process_priority_queue(BatchPriority.BACKGROUND)
                
                await asyncio.sleep(0.01)  # 10ms interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Background processing error: {e}")
                await asyncio.sleep(0.1)
    
    def clear_all_queues(self):
        """Clear all pending updates."""
        with self._lock:
            for queue in self._update_queues.values():
                queue.clear()
            
            self._pending_by_path.clear()
            self._conflicting_updates.clear()
            
            # Cancel all timers
            for priority, timer in self._batch_timers.items():
                if timer:
                    timer.cancel()
                    self._batch_timers[priority] = None
    
    async def shutdown(self):
        """Shutdown the update batcher."""
        # Stop background processing
        await self.stop_background_processing()
        
        # Flush all pending updates
        await self.flush_all_batches()
        
        # Clear queues
        self.clear_all_queues()