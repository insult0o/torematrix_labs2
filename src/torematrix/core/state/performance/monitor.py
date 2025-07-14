"""
Performance monitoring system for state management operations.
"""

import time
import asyncio
import threading
from typing import Any, Dict, List, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from contextlib import contextmanager
import weakref
import psutil
import gc

class PerformanceEntry(NamedTuple):
    """Single performance measurement entry."""
    name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: int
    memory_after: int
    thread_id: int
    metadata: Dict[str, Any]

@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    total_memory_delta: int = 0
    avg_memory_delta: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def update(self, entry: PerformanceEntry):
        """Update statistics with new entry."""
        self.call_count += 1
        self.total_time += entry.duration
        self.min_time = min(self.min_time, entry.duration)
        self.max_time = max(self.max_time, entry.duration)
        self.avg_time = self.total_time / self.call_count
        
        memory_delta = entry.memory_after - entry.memory_before
        self.total_memory_delta += memory_delta
        self.avg_memory_delta = self.total_memory_delta / self.call_count
        
        self.recent_times.append(entry.duration)
        
        # Calculate percentiles from recent times
        if self.recent_times:
            sorted_times = sorted(self.recent_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            
            self.p95_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
            self.p99_time = sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1]


class PerformanceMonitor:
    """
    High-performance monitor for state management operations.
    
    Tracks selector execution times, memory usage, and provides
    real-time performance metrics for optimization.
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        enable_memory_tracking: bool = True,
        enable_thread_tracking: bool = True
    ):
        self.max_entries = max_entries
        self.enable_memory_tracking = enable_memory_tracking
        self.enable_thread_tracking = enable_thread_tracking
        
        # Storage for performance data
        self._entries: deque = deque(maxlen=max_entries)
        self._stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self._active_measurements: Dict[str, Dict] = {}
        
        # Threading support
        self._lock = threading.RLock()
        
        # Memory tracking
        self._process = psutil.Process() if enable_memory_tracking else None
        
        # Performance alerts
        self._alert_thresholds: Dict[str, float] = {}
        self._alert_callbacks: List[Callable] = []
        
        # Real-time monitoring
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
    @contextmanager
    def measure(self, name: str, **metadata):
        """
        Context manager for measuring operation performance.
        
        Args:
            name: Name of the operation being measured
            **metadata: Additional metadata to store with measurement
            
        Example:
            with monitor.measure('selector_execution', selector_name='get_elements'):
                result = selector(state)
        """
        measurement_id = f"{name}_{time.time()}_{threading.get_ident()}"
        
        # Start measurement
        start_time = time.perf_counter()
        memory_before = self._get_memory_usage()
        thread_id = threading.get_ident() if self.enable_thread_tracking else 0
        
        with self._lock:
            self._active_measurements[measurement_id] = {
                'name': name,
                'start_time': start_time,
                'memory_before': memory_before,
                'thread_id': thread_id,
                'metadata': metadata
            }
        
        try:
            yield measurement_id
        finally:
            # End measurement
            end_time = time.perf_counter()
            memory_after = self._get_memory_usage()
            
            with self._lock:
                if measurement_id in self._active_measurements:
                    measurement = self._active_measurements.pop(measurement_id)
                    
                    entry = PerformanceEntry(
                        name=name,
                        start_time=measurement['start_time'],
                        end_time=end_time,
                        duration=end_time - measurement['start_time'],
                        memory_before=measurement['memory_before'],
                        memory_after=memory_after,
                        thread_id=measurement['thread_id'],
                        metadata=metadata
                    )
                    
                    self._add_entry(entry)
    
    def track_selector(self, selector_name: str):
        """
        Decorator to automatically track selector performance.
        
        Args:
            selector_name: Name of the selector for tracking
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                with self.measure(f'selector_{selector_name}', selector=selector_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def track_async_selector(self, selector_name: str):
        """
        Decorator to track async selector performance.
        
        Args:
            selector_name: Name of the async selector
            
        Returns:
            Async decorator function
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with self.measure(f'async_selector_{selector_name}', selector=selector_name):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _add_entry(self, entry: PerformanceEntry):
        """Add performance entry and update statistics."""
        self._entries.append(entry)
        
        # Update statistics
        if entry.name not in self._stats:
            self._stats[entry.name] = PerformanceStats(name=entry.name)
        
        self._stats[entry.name].update(entry)
        
        # Check for performance alerts
        self._check_alerts(entry)
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        if not self.enable_memory_tracking or not self._process:
            return 0
        
        try:
            return self._process.memory_info().rss
        except Exception:
            return 0
    
    def _check_alerts(self, entry: PerformanceEntry):
        """Check if entry triggers any performance alerts."""
        if entry.name in self._alert_thresholds:
            threshold = self._alert_thresholds[entry.name]
            if entry.duration > threshold:
                for callback in self._alert_callbacks:
                    try:
                        callback(entry, threshold)
                    except Exception:
                        pass  # Don't let alert callbacks break monitoring
    
    def set_alert_threshold(self, operation_name: str, threshold_ms: float):
        """
        Set performance alert threshold for an operation.
        
        Args:
            operation_name: Name of operation to monitor
            threshold_ms: Threshold in milliseconds
        """
        self._alert_thresholds[operation_name] = threshold_ms / 1000.0
    
    def add_alert_callback(self, callback: Callable[[PerformanceEntry, float], None]):
        """
        Add callback for performance alerts.
        
        Args:
            callback: Function called when threshold is exceeded
        """
        self._alert_callbacks.append(callback)
    
    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Args:
            operation_name: Specific operation to get stats for, or None for all
            
        Returns:
            Dictionary of performance statistics
        """
        with self._lock:
            if operation_name:
                if operation_name in self._stats:
                    stats = self._stats[operation_name]
                    return {
                        'name': stats.name,
                        'call_count': stats.call_count,
                        'total_time_ms': stats.total_time * 1000,
                        'avg_time_ms': stats.avg_time * 1000,
                        'min_time_ms': stats.min_time * 1000,
                        'max_time_ms': stats.max_time * 1000,
                        'p95_time_ms': stats.p95_time * 1000,
                        'p99_time_ms': stats.p99_time * 1000,
                        'avg_memory_delta_kb': stats.avg_memory_delta / 1024,
                        'total_memory_delta_kb': stats.total_memory_delta / 1024
                    }
                else:
                    return {}
            else:
                # Return stats for all operations
                all_stats = {}
                for name, stats in self._stats.items():
                    all_stats[name] = {
                        'call_count': stats.call_count,
                        'avg_time_ms': stats.avg_time * 1000,
                        'p95_time_ms': stats.p95_time * 1000,
                        'p99_time_ms': stats.p99_time * 1000,
                        'avg_memory_delta_kb': stats.avg_memory_delta / 1024
                    }
                return all_stats
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        with self._lock:
            report = {
                'summary': {
                    'total_operations': len(self._stats),
                    'total_measurements': len(self._entries),
                    'monitoring_active': self._monitoring_active,
                    'memory_tracking_enabled': self.enable_memory_tracking,
                    'thread_tracking_enabled': self.enable_thread_tracking
                },
                'operations': {},
                'alerts': {
                    'thresholds': {name: threshold * 1000 
                                 for name, threshold in self._alert_thresholds.items()},
                    'callback_count': len(self._alert_callbacks)
                },
                'system': self._get_system_stats()
            }
            
            # Add operation statistics
            for name, stats in self._stats.items():
                report['operations'][name] = {
                    'call_count': stats.call_count,
                    'total_time_ms': stats.total_time * 1000,
                    'avg_time_ms': stats.avg_time * 1000,
                    'min_time_ms': stats.min_time * 1000 if stats.min_time != float('inf') else 0,
                    'max_time_ms': stats.max_time * 1000,
                    'p95_time_ms': stats.p95_time * 1000,
                    'p99_time_ms': stats.p99_time * 1000,
                    'avg_memory_delta_kb': stats.avg_memory_delta / 1024,
                    'performance_grade': self._calculate_performance_grade(stats)
                }
            
            return report
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get current system performance statistics."""
        try:
            if self._process:
                memory_info = self._process.memory_info()
                cpu_percent = self._process.cpu_percent()
                
                return {
                    'memory_rss_mb': memory_info.rss / (1024 * 1024),
                    'memory_vms_mb': memory_info.vms / (1024 * 1024),
                    'cpu_percent': cpu_percent,
                    'thread_count': self._process.num_threads(),
                    'gc_counts': gc.get_count()
                }
            else:
                return {'monitoring_disabled': True}
        except Exception:
            return {'error': 'Failed to get system stats'}
    
    def _calculate_performance_grade(self, stats: PerformanceStats) -> str:
        """Calculate performance grade based on statistics."""
        # Simple grading based on average execution time
        avg_ms = stats.avg_time * 1000
        
        if avg_ms < 1:
            return 'A+'
        elif avg_ms < 5:
            return 'A'
        elif avg_ms < 10:
            return 'B'
        elif avg_ms < 50:
            return 'C'
        else:
            return 'D'
    
    async def start_real_time_monitoring(self, interval: float = 1.0):
        """
        Start real-time performance monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
    
    async def stop_real_time_monitoring(self):
        """Stop real-time performance monitoring."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            finally:
                self._monitoring_task = None
    
    async def _monitoring_loop(self, interval: float):
        """Real-time monitoring loop."""
        while self._monitoring_active:
            try:
                # Collect current metrics
                current_stats = self.get_performance_report()
                
                # Log performance issues
                for op_name, op_stats in current_stats['operations'].items():
                    if op_stats['performance_grade'] in ['C', 'D']:
                        print(f"Performance warning: {op_name} grade {op_stats['performance_grade']} "
                              f"(avg: {op_stats['avg_time_ms']:.2f}ms)")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def clear_stats(self):
        """Clear all performance statistics."""
        with self._lock:
            self._entries.clear()
            self._stats.clear()
            self._active_measurements.clear()
    
    def export_data(self, format: str = 'json') -> Any:
        """
        Export performance data in specified format.
        
        Args:
            format: Export format ('json', 'csv', 'summary')
            
        Returns:
            Exported data in requested format
        """
        if format == 'json':
            return self.get_performance_report()
        elif format == 'summary':
            return self._export_summary()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_summary(self) -> str:
        """Export human-readable summary."""
        report = self.get_performance_report()
        
        lines = [
            "Performance Summary",
            "=" * 50,
            f"Total Operations: {report['summary']['total_operations']}",
            f"Total Measurements: {report['summary']['total_measurements']}",
            "",
            "Operation Performance:",
            "-" * 30
        ]
        
        for name, stats in report['operations'].items():
            lines.append(
                f"{name:30} | {stats['call_count']:6} calls | "
                f"{stats['avg_time_ms']:6.2f}ms avg | Grade: {stats['performance_grade']}"
            )
        
        return "\n".join(lines)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()