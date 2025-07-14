"""
Performance Monitoring System for Reactive Components.

This module provides real-time performance tracking, profiling, and analysis
for reactive component rendering and updates.
"""

import time
import threading
import psutil
import os
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from contextlib import contextmanager
import weakref
import traceback

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import logging

logger = logging.getLogger(__name__)


@dataclass
class RenderMetrics:
    """Metrics for a single render operation."""
    
    widget_id: int
    widget_type: str
    start_time: float
    end_time: float
    duration: float
    patches_applied: int = 0
    memory_before: int = 0
    memory_after: int = 0
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return self.duration * 1000


@dataclass
class ComponentMetrics:
    """Aggregated metrics for a component type."""
    
    component_type: str
    render_count: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    error_count: int = 0
    memory_leaked: int = 0
    
    def update(self, metrics: RenderMetrics) -> None:
        """Update aggregated metrics."""
        self.render_count += 1
        self.total_time += metrics.duration
        self.average_time = self.total_time / self.render_count
        self.min_time = min(self.min_time, metrics.duration)
        self.max_time = max(self.max_time, metrics.duration)
        
        if metrics.error:
            self.error_count += 1
        
        memory_diff = metrics.memory_after - metrics.memory_before
        if memory_diff > 0:
            self.memory_leaked += memory_diff


@dataclass
class PerformanceSnapshot:
    """Snapshot of overall performance metrics."""
    
    timestamp: float
    fps: float
    cpu_percent: float
    memory_mb: float
    active_components: int
    render_queue_size: int
    frame_drops: int
    average_render_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "timestamp": self.timestamp,
            "fps": round(self.fps, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_mb": round(self.memory_mb, 2),
            "active_components": self.active_components,
            "render_queue_size": self.render_queue_size,
            "frame_drops": self.frame_drops,
            "average_render_time_ms": round(self.average_render_time * 1000, 2)
        }


class PerformanceMonitor(QObject):
    """Monitors and tracks performance of reactive components."""
    
    # Signals
    performance_warning = pyqtSignal(str)  # warning message
    performance_critical = pyqtSignal(str)  # critical message
    metrics_updated = pyqtSignal(dict)  # metrics dict
    
    def __init__(self):
        """Initialize performance monitor."""
        super().__init__()
        
        # Metrics storage
        self._render_metrics: deque[RenderMetrics] = deque(maxlen=1000)
        self._component_metrics: Dict[str, ComponentMetrics] = defaultdict(
            lambda: ComponentMetrics("")
        )
        self._performance_snapshots: deque[PerformanceSnapshot] = deque(maxlen=60)
        
        # Performance tracking
        self._frame_times: deque[float] = deque(maxlen=60)
        self._last_frame_time = time.time()
        self._frame_drops = 0
        self._active_renders: Set[int] = set()
        
        # System monitoring
        self._process = psutil.Process(os.getpid())
        self._monitoring_timer = QTimer()
        self._monitoring_timer.timeout.connect(self._update_performance_snapshot)
        self._monitoring_timer.start(1000)  # Update every second
        
        # Thresholds
        self.warning_thresholds = {
            "render_time_ms": 16.0,  # 60 FPS target
            "cpu_percent": 80.0,
            "memory_mb": 500.0,
            "frame_drops": 5
        }
        
        self.critical_thresholds = {
            "render_time_ms": 33.0,  # 30 FPS minimum
            "cpu_percent": 95.0,
            "memory_mb": 1000.0,
            "frame_drops": 10
        }
        
        self._lock = threading.RLock()
    
    @contextmanager
    def track_render(self, widget: Any):
        """Context manager to track render performance."""
        widget_id = id(widget)
        widget_type = widget.__class__.__name__
        
        # Get memory before
        memory_before = self._process.memory_info().rss
        
        metrics = RenderMetrics(
            widget_id=widget_id,
            widget_type=widget_type,
            start_time=time.time(),
            end_time=0.0,
            duration=0.0,
            memory_before=memory_before
        )
        
        with self._lock:
            self._active_renders.add(widget_id)
        
        try:
            yield metrics
        except Exception as e:
            metrics.error = str(e)
            logger.error(f"Error during render of {widget_type}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Complete metrics
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.memory_after = self._process.memory_info().rss
            
            with self._lock:
                self._active_renders.discard(widget_id)
                self._record_metrics(metrics)
    
    def track_frame(self) -> None:
        """Track frame timing."""
        current_time = time.time()
        frame_time = current_time - self._last_frame_time
        
        with self._lock:
            self._frame_times.append(frame_time)
            
            # Check for frame drop
            if frame_time > 0.033:  # >33ms is considered a drop
                self._frame_drops += 1
        
        self._last_frame_time = current_time
    
    def _record_metrics(self, metrics: RenderMetrics) -> None:
        """Record render metrics."""
        # Store individual metrics
        self._render_metrics.append(metrics)
        
        # Update component aggregates
        component_metrics = self._component_metrics[metrics.widget_type]
        component_metrics.component_type = metrics.widget_type
        component_metrics.update(metrics)
        
        # Check thresholds
        self._check_thresholds(metrics)
    
    def _check_thresholds(self, metrics: RenderMetrics) -> None:
        """Check if metrics exceed thresholds."""
        render_time_ms = metrics.duration_ms
        
        # Critical threshold
        if render_time_ms > self.critical_thresholds["render_time_ms"]:
            self.performance_critical.emit(
                f"Critical: {metrics.widget_type} render took {render_time_ms:.1f}ms"
            )
        # Warning threshold
        elif render_time_ms > self.warning_thresholds["render_time_ms"]:
            self.performance_warning.emit(
                f"Warning: {metrics.widget_type} render took {render_time_ms:.1f}ms"
            )
    
    def _update_performance_snapshot(self) -> None:
        """Update overall performance snapshot."""
        with self._lock:
            # Calculate FPS
            if self._frame_times:
                avg_frame_time = sum(self._frame_times) / len(self._frame_times)
                fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
            else:
                fps = 0.0
            
            # Get system metrics
            cpu_percent = self._process.cpu_percent()
            memory_mb = self._process.memory_info().rss / (1024 * 1024)
            
            # Calculate average render time
            recent_renders = list(self._render_metrics)[-100:]
            if recent_renders:
                avg_render_time = sum(r.duration for r in recent_renders) / len(recent_renders)
            else:
                avg_render_time = 0.0
            
            # Create snapshot
            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                fps=fps,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                active_components=len(self._active_renders),
                render_queue_size=0,  # To be set by render batcher
                frame_drops=self._frame_drops,
                average_render_time=avg_render_time
            )
            
            self._performance_snapshots.append(snapshot)
            
            # Check system thresholds
            self._check_system_thresholds(snapshot)
            
            # Emit metrics update
            self.metrics_updated.emit(snapshot.to_dict())
    
    def _check_system_thresholds(self, snapshot: PerformanceSnapshot) -> None:
        """Check system-wide thresholds."""
        # CPU threshold
        if snapshot.cpu_percent > self.critical_thresholds["cpu_percent"]:
            self.performance_critical.emit(
                f"Critical: CPU usage at {snapshot.cpu_percent:.1f}%"
            )
        elif snapshot.cpu_percent > self.warning_thresholds["cpu_percent"]:
            self.performance_warning.emit(
                f"Warning: CPU usage at {snapshot.cpu_percent:.1f}%"
            )
        
        # Memory threshold
        if snapshot.memory_mb > self.critical_thresholds["memory_mb"]:
            self.performance_critical.emit(
                f"Critical: Memory usage at {snapshot.memory_mb:.1f}MB"
            )
        elif snapshot.memory_mb > self.warning_thresholds["memory_mb"]:
            self.performance_warning.emit(
                f"Warning: Memory usage at {snapshot.memory_mb:.1f}MB"
            )
        
        # Frame drops
        if snapshot.frame_drops > self.critical_thresholds["frame_drops"]:
            self.performance_critical.emit(
                f"Critical: {snapshot.frame_drops} frame drops detected"
            )
    
    def get_component_report(self) -> Dict[str, Dict[str, Any]]:
        """Get performance report by component type."""
        with self._lock:
            report = {}
            
            for component_type, metrics in self._component_metrics.items():
                if metrics.render_count > 0:
                    report[component_type] = {
                        "render_count": metrics.render_count,
                        "average_time_ms": round(metrics.average_time * 1000, 2),
                        "min_time_ms": round(metrics.min_time * 1000, 2),
                        "max_time_ms": round(metrics.max_time * 1000, 2),
                        "total_time_ms": round(metrics.total_time * 1000, 2),
                        "error_count": metrics.error_count,
                        "memory_leaked_kb": round(metrics.memory_leaked / 1024, 2)
                    }
            
            return report
    
    def get_performance_history(self, seconds: int = 60) -> List[Dict[str, Any]]:
        """Get performance history for the last N seconds."""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - seconds
            
            history = []
            for snapshot in self._performance_snapshots:
                if snapshot.timestamp >= cutoff_time:
                    history.append(snapshot.to_dict())
            
            return history
    
    def get_bottlenecks(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Get top N performance bottlenecks."""
        with self._lock:
            # Sort components by average render time
            bottlenecks = []
            
            for component_type, metrics in self._component_metrics.items():
                if metrics.render_count > 0:
                    bottlenecks.append((
                        component_type,
                        metrics.average_time * 1000  # Convert to ms
                    ))
            
            # Sort by render time descending
            bottlenecks.sort(key=lambda x: x[1], reverse=True)
            
            return bottlenecks[:top_n]
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        with self._lock:
            self._render_metrics.clear()
            self._component_metrics.clear()
            self._performance_snapshots.clear()
            self._frame_times.clear()
            self._frame_drops = 0
    
    def set_threshold(
        self,
        metric: str,
        warning: float,
        critical: float
    ) -> None:
        """Set performance thresholds."""
        if metric in self.warning_thresholds:
            self.warning_thresholds[metric] = warning
            self.critical_thresholds[metric] = critical


class PerformanceProfiler:
    """Advanced profiling for performance optimization."""
    
    def __init__(self):
        """Initialize profiler."""
        self._profile_data: Dict[str, List[float]] = defaultdict(list)
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    @contextmanager
    def profile(self, operation: str):
        """Profile an operation."""
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            
            with self._lock:
                self._profile_data[operation].append(duration)
                self._call_counts[operation] += 1
    
    def get_profile_report(self) -> Dict[str, Dict[str, float]]:
        """Get profiling report."""
        with self._lock:
            report = {}
            
            for operation, durations in self._profile_data.items():
                if durations:
                    report[operation] = {
                        "call_count": self._call_counts[operation],
                        "total_time": sum(durations),
                        "average_time": sum(durations) / len(durations),
                        "min_time": min(durations),
                        "max_time": max(durations)
                    }
            
            return report
    
    def reset(self) -> None:
        """Reset profiling data."""
        with self._lock:
            self._profile_data.clear()
            self._call_counts.clear()


# Global instances
_performance_monitor: Optional[PerformanceMonitor] = None
_performance_profiler: Optional[PerformanceProfiler] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def get_performance_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    global _performance_profiler
    if _performance_profiler is None:
        _performance_profiler = PerformanceProfiler()
    return _performance_profiler


@contextmanager
def track_performance(widget: Any):
    """Track performance of a widget render."""
    monitor = get_performance_monitor()
    with monitor.track_render(widget) as metrics:
        yield metrics


@contextmanager
def profile_operation(operation: str):
    """Profile a specific operation."""
    profiler = get_performance_profiler()
    with profiler.profile(operation):
        yield