"""
Render Batching System for Reactive Components.

This module provides efficient render batching to minimize UI updates
and improve performance by coalescing multiple changes into single render passes.
"""

import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from .diffing import DiffPatch, WidgetDiffer, DiffOperation

import logging

logger = logging.getLogger(__name__)


class RenderPriority(Enum):
    """Priority levels for render operations."""
    
    CRITICAL = auto()    # User input, animations
    HIGH = auto()        # Visible UI changes
    NORMAL = auto()      # Standard updates
    LOW = auto()         # Background updates
    IDLE = auto()        # When system is idle


@dataclass
class RenderTask:
    """Represents a render task to be executed."""
    
    widget: weakref.ref[QWidget]
    patches: List[DiffPatch]
    priority: RenderPriority = RenderPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    callback: Optional[Callable[[], None]] = None
    
    def get_widget(self) -> Optional[QWidget]:
        """Get widget if still alive."""
        return self.widget() if self.widget else None
    
    def __lt__(self, other):
        """Compare for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class BatchStatistics:
    """Statistics for render batching performance."""
    
    total_batches: int = 0
    total_renders: int = 0
    patches_applied: int = 0
    average_batch_size: float = 0.0
    average_batch_time: float = 0.0
    frame_drops: int = 0
    last_batch_time: float = 0.0


class RenderScheduler(QObject):
    """Schedules and coordinates render operations."""
    
    # Signals
    batch_started = pyqtSignal()
    batch_completed = pyqtSignal(int)  # patches applied
    frame_dropped = pyqtSignal()
    
    def __init__(self, target_fps: int = 60):
        """Initialize render scheduler."""
        super().__init__()
        
        self.target_fps = target_fps
        self.frame_time = 1000 / target_fps  # ms
        
        self._render_timer = QTimer()
        self._render_timer.timeout.connect(self._process_batch)
        self._render_timer.setInterval(int(self.frame_time))
        
        self._tasks: Dict[int, RenderTask] = {}
        self._task_queue: deque[RenderTask] = deque()
        self._lock = threading.RLock()
        self._statistics = BatchStatistics()
        self._last_frame_time = time.time()
        
        # Start render loop
        self._render_timer.start()
    
    def schedule_render(
        self,
        widget: QWidget,
        patches: List[DiffPatch],
        priority: RenderPriority = RenderPriority.NORMAL,
        callback: Optional[Callable[[], None]] = None
    ) -> None:
        """Schedule a render task."""
        with self._lock:
            widget_id = id(widget)
            
            # Check if task already exists for this widget
            if widget_id in self._tasks:
                existing = self._tasks[widget_id]
                # Merge patches
                existing.patches.extend(patches)
                # Upgrade priority if needed
                if priority.value < existing.priority.value:
                    existing.priority = priority
                return
            
            # Create new task
            task = RenderTask(
                widget=weakref.ref(widget),
                patches=patches,
                priority=priority,
                callback=callback
            )
            
            self._tasks[widget_id] = task
            self._task_queue.append(task)
    
    def _process_batch(self) -> None:
        """Process a batch of render tasks."""
        start_time = time.time()
        
        # Check for frame drops
        frame_interval = start_time - self._last_frame_time
        if frame_interval > self.frame_time * 2 / 1000:  # Missed frame
            self._statistics.frame_drops += 1
            self.frame_dropped.emit()
        
        self._last_frame_time = start_time
        
        # Get tasks to process
        tasks = self._get_batch_tasks()
        if not tasks:
            return
        
        self.batch_started.emit()
        
        # Process tasks
        patches_applied = 0
        for task in tasks:
            widget = task.get_widget()
            if widget:
                try:
                    # Apply patches
                    for patch in task.patches:
                        patch.apply()
                        patches_applied += 1
                    
                    # Call callback
                    if task.callback:
                        task.callback()
                        
                except Exception as e:
                    logger.error(f"Error applying render patches: {e}")
        
        # Update statistics
        batch_time = time.time() - start_time
        self._update_statistics(len(tasks), patches_applied, batch_time)
        
        self.batch_completed.emit(patches_applied)
    
    def _get_batch_tasks(self) -> List[RenderTask]:
        """Get tasks for current batch."""
        with self._lock:
            if not self._task_queue:
                return []
            
            # Sort by priority
            sorted_tasks = sorted(self._task_queue)
            
            # Calculate batch size based on time budget
            time_budget = self.frame_time * 0.8 / 1000  # 80% of frame time
            batch_tasks = []
            
            for task in sorted_tasks:
                # Always include critical tasks
                if task.priority == RenderPriority.CRITICAL:
                    batch_tasks.append(task)
                # Check time budget for others
                elif self._estimate_task_time(task) < time_budget:
                    batch_tasks.append(task)
                    time_budget -= self._estimate_task_time(task)
                else:
                    break
            
            # Remove processed tasks
            for task in batch_tasks:
                self._task_queue.remove(task)
                widget_id = id(task.get_widget()) if task.get_widget() else None
                if widget_id and widget_id in self._tasks:
                    del self._tasks[widget_id]
            
            return batch_tasks
    
    def _estimate_task_time(self, task: RenderTask) -> float:
        """Estimate time to process a task."""
        # Simple heuristic based on patch count
        base_time = 0.001  # 1ms base
        per_patch_time = 0.0002  # 0.2ms per patch
        return base_time + (len(task.patches) * per_patch_time)
    
    def _update_statistics(
        self,
        batch_size: int,
        patches_applied: int,
        batch_time: float
    ) -> None:
        """Update performance statistics."""
        stats = self._statistics
        
        stats.total_batches += 1
        stats.total_renders += batch_size
        stats.patches_applied += patches_applied
        stats.last_batch_time = batch_time
        
        # Update averages
        stats.average_batch_size = (
            (stats.average_batch_size * (stats.total_batches - 1) + batch_size)
            / stats.total_batches
        )
        stats.average_batch_time = (
            (stats.average_batch_time * (stats.total_batches - 1) + batch_time)
            / stats.total_batches
        )
    
    def get_statistics(self) -> BatchStatistics:
        """Get current statistics."""
        return self._statistics
    
    def set_target_fps(self, fps: int) -> None:
        """Update target FPS."""
        self.target_fps = fps
        self.frame_time = 1000 / fps
        self._render_timer.setInterval(int(self.frame_time))
    
    def pause(self) -> None:
        """Pause render batching."""
        self._render_timer.stop()
    
    def resume(self) -> None:
        """Resume render batching."""
        self._render_timer.start()
    
    def flush(self) -> None:
        """Flush all pending renders immediately."""
        tasks = []
        with self._lock:
            tasks = list(self._task_queue)
            self._task_queue.clear()
            self._tasks.clear()
        
        # Process all tasks
        for task in tasks:
            widget = task.get_widget()
            if widget:
                for patch in task.patches:
                    patch.apply()


class RenderBatcher:
    """Main render batching coordinator."""
    
    def __init__(self):
        """Initialize render batcher."""
        self._scheduler = RenderScheduler()
        self._differ = get_widget_differ()
        self._widget_states: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._memoization_cache: Dict[Tuple[int, ...], bool] = {}
    
    def request_render(
        self,
        widget: QWidget,
        priority: RenderPriority = RenderPriority.NORMAL
    ) -> None:
        """Request a widget render."""
        # Get current state
        current_state = self._capture_widget_state(widget)
        
        # Check if render needed
        if not self._should_render(widget, current_state):
            return
        
        # Generate patches
        old_state = self._widget_states.get(widget, {})
        patches = self._differ.diff_properties(widget, old_state, current_state)
        
        if patches:
            # Schedule render
            self._scheduler.schedule_render(widget, patches, priority)
            
            # Update state
            self._widget_states[widget] = current_state
    
    def batch_update(
        self,
        widgets: List[QWidget],
        priority: RenderPriority = RenderPriority.NORMAL
    ) -> None:
        """Batch update multiple widgets."""
        for widget in widgets:
            self.request_render(widget, priority)
    
    def _capture_widget_state(self, widget: QWidget) -> Dict[str, Any]:
        """Capture current widget state."""
        state = {}
        
        # Common properties
        state["enabled"] = widget.isEnabled()
        state["visible"] = widget.isVisible()
        state["geometry"] = widget.geometry()
        
        # Widget-specific properties
        if hasattr(widget, "text"):
            state["text"] = widget.text()
        if hasattr(widget, "value"):
            state["value"] = widget.value()
        
        return state
    
    def _should_render(self, widget: QWidget, state: Dict[str, Any]) -> bool:
        """Check if widget needs rendering using memoization."""
        # Create cache key from state
        state_items = sorted(state.items())
        cache_key = (id(widget), hash(tuple(state_items)))
        
        # Check memoization cache
        if cache_key in self._memoization_cache:
            return self._memoization_cache[cache_key]
        
        # Check if state changed
        old_state = self._widget_states.get(widget)
        should_render = old_state != state
        
        # Cache result
        if len(self._memoization_cache) < 10000:  # Limit cache size
            self._memoization_cache[cache_key] = should_render
        
        return should_render
    
    def invalidate_memoization(self, widget: Optional[QWidget] = None) -> None:
        """Invalidate memoization cache."""
        if widget:
            # Clear entries for specific widget
            widget_id = id(widget)
            keys_to_remove = [
                key for key in self._memoization_cache
                if key[0] == widget_id
            ]
            for key in keys_to_remove:
                del self._memoization_cache[key]
        else:
            # Clear entire cache
            self._memoization_cache.clear()
    
    def get_scheduler(self) -> RenderScheduler:
        """Get the render scheduler."""
        return self._scheduler
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        scheduler_stats = self._scheduler.get_statistics()
        
        return {
            "scheduler": {
                "total_batches": scheduler_stats.total_batches,
                "total_renders": scheduler_stats.total_renders,
                "patches_applied": scheduler_stats.patches_applied,
                "average_batch_size": scheduler_stats.average_batch_size,
                "average_batch_time_ms": scheduler_stats.average_batch_time * 1000,
                "frame_drops": scheduler_stats.frame_drops,
                "target_fps": self._scheduler.target_fps
            },
            "memoization": {
                "cache_size": len(self._memoization_cache),
                "widget_states": len(self._widget_states)
            }
        }


# Global render batcher
_render_batcher: Optional[RenderBatcher] = None


def get_render_batcher() -> RenderBatcher:
    """Get the global render batcher."""
    global _render_batcher
    if _render_batcher is None:
        _render_batcher = RenderBatcher()
    return _render_batcher


def schedule_render(
    widget: QWidget,
    priority: RenderPriority = RenderPriority.NORMAL
) -> None:
    """Schedule a widget render."""
    batcher = get_render_batcher()
    batcher.request_render(widget, priority)


def batch_render(
    widgets: List[QWidget],
    priority: RenderPriority = RenderPriority.NORMAL
) -> None:
    """Batch render multiple widgets."""
    batcher = get_render_batcher()
    batcher.batch_update(widgets, priority)