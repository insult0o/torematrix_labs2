"""Performance Monitoring and Metrics Collection

Comprehensive performance monitoring system for search and filter operations.
Tracks execution times, memory usage, cache performance, and provides
detailed analytics for optimization insights.
"""

import time
import psutil
import threading
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import weakref

from torematrix.ui.components.search.cache import get_cache_manager


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    TIMING = "timing"
    MEMORY = "memory"
    COUNT = "count"
    RATE = "rate"
    PERCENTAGE = "percentage"
    SIZE = "size"


@dataclass
class PerformanceMetric:
    """Single performance metric measurement"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp,
            'tags': self.tags,
            'context': self.context
        }


@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot"""
    timestamp: float = field(default_factory=time.time)
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_ratio: float = 0.0
    active_operations: int = 0
    avg_response_time_ms: float = 0.0
    queries_per_second: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_mb': self.memory_usage_mb,
            'cache_hit_ratio': self.cache_hit_ratio,
            'active_operations': self.active_operations,
            'avg_response_time_ms': self.avg_response_time_ms,
            'queries_per_second': self.queries_per_second
        }


@dataclass
class OperationMetrics:
    """Metrics for a specific operation"""
    operation_name: str
    total_executions: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_execution: Optional[float] = None
    
    def add_execution(self, duration_ms: float, success: bool = True) -> None:
        """Add execution measurement"""
        self.total_executions += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.avg_time_ms = self.total_time_ms / self.total_executions
        self.last_execution = time.time()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_executions == 0:
            return 0.0
        return (self.success_count / self.total_executions) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'operation_name': self.operation_name,
            'total_executions': self.total_executions,
            'total_time_ms': self.total_time_ms,
            'min_time_ms': self.min_time_ms if self.min_time_ms != float('inf') else 0,
            'max_time_ms': self.max_time_ms,
            'avg_time_ms': self.avg_time_ms,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_rate,
            'last_execution': self.last_execution
        }


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, monitor: 'PerformanceMonitor', 
                 tags: Optional[Dict[str, str]] = None):
        """Initialize timer
        
        Args:
            operation_name: Name of operation being timed
            monitor: Performance monitor instance
            tags: Optional tags for categorization
        """
        self.operation_name = operation_name
        self.monitor = monitor
        self.tags = tags or {}
        self.start_time = 0.0
        self.success = True
    
    def __enter__(self) -> 'PerformanceTimer':
        """Start timing"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing and record metric"""
        duration_ms = (time.time() - self.start_time) * 1000
        self.success = exc_type is None
        
        self.monitor.record_timing(
            self.operation_name, 
            duration_ms, 
            self.success,
            tags=self.tags
        )
    
    def mark_error(self) -> None:
        """Mark operation as failed"""
        self.success = False


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, history_size: int = 10000, snapshot_interval: float = 5.0):
        """Initialize performance monitor
        
        Args:
            history_size: Maximum number of metrics to keep in memory
            snapshot_interval: Interval between system snapshots in seconds
        """
        self.history_size = history_size
        self.snapshot_interval = snapshot_interval
        
        # Metric storage
        self._metrics: deque = deque(maxlen=history_size)
        self._operation_metrics: Dict[str, OperationMetrics] = {}
        self._snapshots: deque = deque(maxlen=int(3600 / snapshot_interval))  # 1 hour of snapshots
        
        # Rate tracking
        self._query_timestamps: deque = deque(maxlen=1000)
        self._response_times: deque = deque(maxlen=1000)
        
        # System monitoring
        self._process = psutil.Process()
        self._cache_manager = get_cache_manager()
        
        # Threading
        self._lock = threading.RLock()
        self._snapshot_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._metric_callbacks: List[Callable[[PerformanceMetric], None]] = []
        self._snapshot_callbacks: List[Callable[[PerformanceSnapshot], None]] = []
        
        # Start background monitoring
        self._start_monitoring()
        
        logger.info(f"PerformanceMonitor initialized: history_size={history_size}, "
                   f"snapshot_interval={snapshot_interval}s")
    
    def time_operation(self, operation_name: str, 
                      tags: Optional[Dict[str, str]] = None) -> PerformanceTimer:
        """Create timer for operation
        
        Args:
            operation_name: Name of operation to time
            tags: Optional tags for categorization
            
        Returns:
            Timer context manager
        """
        return PerformanceTimer(operation_name, self, tags)
    
    def record_timing(self, operation_name: str, duration_ms: float, 
                     success: bool = True, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric
        
        Args:
            operation_name: Name of operation
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            tags: Optional tags
        """
        with self._lock:
            # Create metric
            metric = PerformanceMetric(
                name=f"{operation_name}.duration",
                value=duration_ms,
                metric_type=MetricType.TIMING,
                tags=tags or {},
                context=operation_name
            )
            self._metrics.append(metric)
            
            # Update operation metrics
            if operation_name not in self._operation_metrics:
                self._operation_metrics[operation_name] = OperationMetrics(operation_name)
            
            self._operation_metrics[operation_name].add_execution(duration_ms, success)
            
            # Track for rate calculation
            current_time = time.time()
            self._query_timestamps.append(current_time)
            self._response_times.append(duration_ms)
            
            # Notify callbacks
            self._notify_metric_callbacks(metric)
    
    def record_count(self, name: str, count: int, 
                    tags: Optional[Dict[str, str]] = None) -> None:
        """Record count metric
        
        Args:
            name: Metric name
            count: Count value
            tags: Optional tags
        """
        metric = PerformanceMetric(
            name=name,
            value=float(count),
            metric_type=MetricType.COUNT,
            tags=tags or {}
        )
        
        with self._lock:
            self._metrics.append(metric)
            self._notify_metric_callbacks(metric)
    
    def record_memory_usage(self, context: str, size_mb: float,
                          tags: Optional[Dict[str, str]] = None) -> None:
        """Record memory usage metric
        
        Args:
            context: Context description
            size_mb: Memory size in MB
            tags: Optional tags
        """
        metric = PerformanceMetric(
            name="memory.usage",
            value=size_mb,
            metric_type=MetricType.MEMORY,
            tags=tags or {},
            context=context
        )
        
        with self._lock:
            self._metrics.append(metric)
            self._notify_metric_callbacks(metric)
    
    def record_cache_performance(self) -> None:
        """Record cache performance metrics"""
        try:
            cache_stats = self._cache_manager.get_global_stats()
            
            for cache_name, stats in cache_stats.items():
                tags = {'cache': cache_name}
                
                # Hit ratio
                self.record_metric(
                    f"cache.hit_ratio",
                    stats.hit_ratio * 100,
                    MetricType.PERCENTAGE,
                    tags=tags
                )
                
                # Size
                self.record_metric(
                    f"cache.size_mb",
                    stats.size_bytes / (1024 * 1024),
                    MetricType.SIZE,
                    tags=tags
                )
                
                # Entry count
                self.record_count(f"cache.entries", stats.entry_count, tags=tags)
                
        except Exception as e:
            logger.warning(f"Failed to record cache metrics: {e}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType,
                     tags: Optional[Dict[str, str]] = None, context: Optional[str] = None) -> None:
        """Record generic metric
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags
            context: Optional context
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            context=context
        )
        
        with self._lock:
            self._metrics.append(metric)
            self._notify_metric_callbacks(metric)
    
    def get_operation_metrics(self, operation_name: Optional[str] = None) -> Union[OperationMetrics, Dict[str, OperationMetrics]]:
        """Get operation metrics
        
        Args:
            operation_name: Specific operation name, or None for all
            
        Returns:
            Single operation metrics or all metrics
        """
        with self._lock:
            if operation_name:
                return self._operation_metrics.get(operation_name)
            return dict(self._operation_metrics)
    
    def get_recent_metrics(self, minutes: int = 5, 
                          metric_name: Optional[str] = None) -> List[PerformanceMetric]:
        """Get recent metrics
        
        Args:
            minutes: Number of minutes to look back
            metric_name: Optional metric name filter
            
        Returns:
            List of recent metrics
        """
        cutoff_time = time.time() - (minutes * 60)
        
        with self._lock:
            recent_metrics = [
                metric for metric in self._metrics
                if metric.timestamp >= cutoff_time
            ]
            
            if metric_name:
                recent_metrics = [
                    metric for metric in recent_metrics
                    if metric.name == metric_name
                ]
            
            return recent_metrics
    
    def get_performance_summary(self, minutes: int = 30) -> Dict[str, Any]:
        """Get performance summary
        
        Args:
            minutes: Time window in minutes
            
        Returns:
            Performance summary dictionary
        """
        with self._lock:
            recent_metrics = self.get_recent_metrics(minutes)
            
            # Group metrics by type
            timing_metrics = [m for m in recent_metrics if m.metric_type == MetricType.TIMING]
            memory_metrics = [m for m in recent_metrics if m.metric_type == MetricType.MEMORY]
            
            summary = {
                'time_window_minutes': minutes,
                'total_metrics': len(recent_metrics),
                'operations': {},
                'system': self._get_system_summary(),
                'cache': self._get_cache_summary(),
                'performance': {}
            }
            
            # Operation summaries
            for op_name, op_metrics in self._operation_metrics.items():
                if op_metrics.last_execution and (time.time() - op_metrics.last_execution) <= (minutes * 60):
                    summary['operations'][op_name] = op_metrics.to_dict()
            
            # Performance aggregates
            if timing_metrics:
                response_times = [m.value for m in timing_metrics]
                summary['performance'] = {
                    'avg_response_time_ms': statistics.mean(response_times),
                    'median_response_time_ms': statistics.median(response_times),
                    'p95_response_time_ms': self._percentile(response_times, 95),
                    'p99_response_time_ms': self._percentile(response_times, 99),
                    'total_operations': len(timing_metrics),
                    'operations_per_minute': len(timing_metrics) / minutes
                }
            
            return summary
    
    def get_system_snapshot(self) -> PerformanceSnapshot:
        """Get current system performance snapshot"""
        try:
            # CPU usage
            cpu_percent = self._process.cpu_percent()
            
            # Memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Cache performance
            cache_stats = self._cache_manager.get_global_stats()
            avg_hit_ratio = sum(stats.hit_ratio for stats in cache_stats.values()) / len(cache_stats) if cache_stats else 0
            
            # Recent performance
            avg_response_time = 0.0
            queries_per_second = 0.0
            
            if self._response_times:
                avg_response_time = statistics.mean(self._response_times)
            
            if len(self._query_timestamps) >= 2:
                time_span = self._query_timestamps[-1] - self._query_timestamps[0]
                if time_span > 0:
                    queries_per_second = len(self._query_timestamps) / time_span
            
            return PerformanceSnapshot(
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_mb,
                cache_hit_ratio=avg_hit_ratio * 100,
                active_operations=len(self._operation_metrics),
                avg_response_time_ms=avg_response_time,
                queries_per_second=queries_per_second
            )
            
        except Exception as e:
            logger.warning(f"Failed to create system snapshot: {e}")
            return PerformanceSnapshot()
    
    def add_metric_callback(self, callback: Callable[[PerformanceMetric], None]) -> None:
        """Add callback for new metrics"""
        self._metric_callbacks.append(callback)
    
    def add_snapshot_callback(self, callback: Callable[[PerformanceSnapshot], None]) -> None:
        """Add callback for system snapshots"""
        self._snapshot_callbacks.append(callback)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        snapshot = self.get_system_snapshot()
        recent_errors = self._count_recent_errors()
        
        # Determine health status
        status = "healthy"
        issues = []
        
        if snapshot.cpu_usage_percent > 80:
            status = "warning"
            issues.append(f"High CPU usage: {snapshot.cpu_usage_percent:.1f}%")
        
        if snapshot.memory_usage_mb > 500:  # 500MB threshold
            status = "warning"
            issues.append(f"High memory usage: {snapshot.memory_usage_mb:.1f}MB")
        
        if snapshot.cache_hit_ratio < 50:
            status = "warning"
            issues.append(f"Low cache hit ratio: {snapshot.cache_hit_ratio:.1f}%")
        
        if recent_errors > 10:
            status = "critical"
            issues.append(f"High error rate: {recent_errors} errors in last 5 minutes")
        
        return {
            'status': status,
            'issues': issues,
            'snapshot': snapshot.to_dict(),
            'last_updated': time.time()
        }
    
    def shutdown(self) -> None:
        """Shutdown monitoring"""
        self._shutdown_event.set()
        if self._snapshot_thread and self._snapshot_thread.is_alive():
            self._snapshot_thread.join(timeout=5.0)
        logger.info("PerformanceMonitor shutdown")
    
    def _start_monitoring(self) -> None:
        """Start background monitoring thread"""
        self._snapshot_thread = threading.Thread(
            target=self._snapshot_loop,
            name="PerformanceMonitor",
            daemon=True
        )
        self._snapshot_thread.start()
    
    def _snapshot_loop(self) -> None:
        """Background snapshot collection loop"""
        while not self._shutdown_event.is_set():
            try:
                snapshot = self.get_system_snapshot()
                
                with self._lock:
                    self._snapshots.append(snapshot)
                
                # Record cache metrics
                self.record_cache_performance()
                
                # Notify callbacks
                self._notify_snapshot_callbacks(snapshot)
                
            except Exception as e:
                logger.warning(f"Snapshot collection failed: {e}")
            
            # Wait for next interval
            self._shutdown_event.wait(self.snapshot_interval)
    
    def _get_system_summary(self) -> Dict[str, Any]:
        """Get system summary"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'process_memory_mb': self._process.memory_info().rss / (1024**2)
            }
        except:
            return {}
    
    def _get_cache_summary(self) -> Dict[str, Any]:
        """Get cache summary"""
        try:
            cache_stats = self._cache_manager.get_global_stats()
            return {
                cache_name: {
                    'hit_ratio': stats.hit_ratio,
                    'size_mb': stats.size_bytes / (1024**2),
                    'entries': stats.entry_count
                }
                for cache_name, stats in cache_stats.items()
            }
        except:
            return {}
    
    def _count_recent_errors(self, minutes: int = 5) -> int:
        """Count recent errors"""
        with self._lock:
            error_count = 0
            for op_metrics in self._operation_metrics.values():
                if (op_metrics.last_execution and 
                    (time.time() - op_metrics.last_execution) <= (minutes * 60)):
                    error_count += op_metrics.error_count
            return error_count
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100)
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]
    
    def _notify_metric_callbacks(self, metric: PerformanceMetric) -> None:
        """Notify metric callbacks"""
        for callback in self._metric_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.warning(f"Metric callback error: {e}")
    
    def _notify_snapshot_callbacks(self, snapshot: PerformanceSnapshot) -> None:
        """Notify snapshot callbacks"""
        for callback in self._snapshot_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                logger.warning(f"Snapshot callback error: {e}")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def time_operation(operation_name: str, tags: Optional[Dict[str, str]] = None) -> PerformanceTimer:
    """Convenience function for timing operations"""
    return get_performance_monitor().time_operation(operation_name, tags)


def record_timing(operation_name: str, duration_ms: float, success: bool = True,
                 tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function for recording timing"""
    get_performance_monitor().record_timing(operation_name, duration_ms, success, tags)


def shutdown_monitoring() -> None:
    """Shutdown global monitoring"""
    global _performance_monitor
    if _performance_monitor:
        _performance_monitor.shutdown()
        _performance_monitor = None