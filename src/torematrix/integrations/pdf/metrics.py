"""
Performance Metrics Collection System for PDF.js Optimization.

This module provides comprehensive metrics collection, analysis, and reporting
for PDF.js performance monitoring and optimization.
"""
from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MetricType(Enum):
    """Types of performance metrics."""
    TIMING = "timing"
    MEMORY = "memory"
    RENDER = "render"
    CACHE = "cache"
    NETWORK = "network"
    USER = "user"
    SYSTEM = "system"


class MetricSeverity(Enum):
    """Metric severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: Union[int, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class MetricSeries:
    """Series of metric data points."""
    name: str
    metric_type: MetricType
    unit: str
    points: List[MetricPoint] = field(default_factory=list)
    max_points: int = 1000
    
    def add_point(self, value: Union[int, float], metadata: Dict[str, Any] = None) -> None:
        """Add a new metric point."""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            metadata=metadata or {}
        )
        
        self.points.append(point)
        
        # Limit series length
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get the latest metric point."""
        return self.points[-1] if self.points else None
    
    def get_range(self, start_time: float, end_time: float) -> List[MetricPoint]:
        """Get metric points within time range."""
        return [
            point for point in self.points
            if start_time <= point.timestamp <= end_time
        ]
    
    def get_statistics(self, time_window: Optional[float] = None) -> Dict[str, float]:
        """Get statistical analysis of the metric series."""
        if not self.points:
            return {}
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = time.time() - time_window
            values = [p.value for p in self.points if p.timestamp >= cutoff_time]
        else:
            values = [p.value for p in self.points]
        
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99)
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


@dataclass
class PerformanceAlert:
    """Performance alert/warning."""
    metric_name: str
    severity: MetricSeverity
    message: str
    value: Union[int, float]
    threshold: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolution_time: Optional[float] = None


class MetricsCollector(QObject):
    """
    Comprehensive metrics collection system.
    
    Collects, stores, and analyzes performance metrics from various
    sources within the PDF.js integration.
    """
    
    # Signals
    metric_recorded = pyqtSignal(str, float, dict)  # metric_name, value, metadata
    alert_triggered = pyqtSignal(PerformanceAlert)  # alert
    alert_resolved = pyqtSignal(str)  # alert_id
    
    def __init__(self):
        super().__init__()
        
        # Metric storage
        self.metrics: Dict[str, MetricSeries] = {}
        self.alerts: Dict[str, PerformanceAlert] = {}
        
        # Configuration
        self.alert_thresholds: Dict[str, Dict[str, Union[int, float]]] = {
            'page_load_time': {'warning': 2000, 'error': 5000},  # ms
            'memory_usage': {'warning': 200, 'error': 500},      # MB
            'render_time': {'warning': 500, 'error': 1000},      # ms
            'cache_miss_rate': {'warning': 0.3, 'error': 0.5},  # ratio
            'cpu_usage': {'warning': 70, 'error': 90},           # percent
            'fps': {'warning': 30, 'error': 15}                 # frames per second
        }
        
        # Analysis
        self.analysis_window = 300  # 5 minutes
        self.trend_analysis_enabled = True
        
        # Built-in metrics
        self._initialize_built_in_metrics()
    
    def _initialize_built_in_metrics(self) -> None:
        """Initialize built-in metric series."""
        built_in_metrics = [
            ('page_load_time', MetricType.TIMING, 'ms'),
            ('memory_usage', MetricType.MEMORY, 'MB'),
            ('render_time', MetricType.RENDER, 'ms'),
            ('cache_hit_rate', MetricType.CACHE, 'ratio'),
            ('cache_miss_rate', MetricType.CACHE, 'ratio'),
            ('cpu_usage', MetricType.SYSTEM, 'percent'),
            ('fps', MetricType.RENDER, 'fps'),
            ('document_size', MetricType.MEMORY, 'MB'),
            ('pages_loaded', MetricType.USER, 'count'),
            ('network_latency', MetricType.NETWORK, 'ms'),
            ('gpu_memory', MetricType.SYSTEM, 'MB'),
            ('javascript_heap', MetricType.MEMORY, 'MB'),
            ('dom_nodes', MetricType.SYSTEM, 'count'),
            ('event_loop_lag', MetricType.SYSTEM, 'ms'),
            ('garbage_collections', MetricType.SYSTEM, 'count')
        ]
        
        for name, metric_type, unit in built_in_metrics:
            self.metrics[name] = MetricSeries(
                name=name,
                metric_type=metric_type,
                unit=unit
            )
    
    def record_metric(self, name: str, value: Union[int, float], 
                     metadata: Dict[str, Any] = None,
                     metric_type: MetricType = MetricType.TIMING,
                     unit: str = 'ms') -> None:
        """Record a metric value."""
        # Create metric series if it doesn't exist
        if name not in self.metrics:
            self.metrics[name] = MetricSeries(
                name=name,
                metric_type=metric_type,
                unit=unit
            )
        
        # Add the metric point
        self.metrics[name].add_point(value, metadata)
        
        # Check for alerts
        self._check_alerts(name, value)
        
        # Emit signal
        self.metric_recorded.emit(name, value, metadata or {})
    
    def record_timing(self, name: str, duration_ms: float, 
                     metadata: Dict[str, Any] = None) -> None:
        """Record a timing metric."""
        self.record_metric(name, duration_ms, metadata, MetricType.TIMING, 'ms')
    
    def record_memory(self, name: str, size_mb: float, 
                     metadata: Dict[str, Any] = None) -> None:
        """Record a memory metric."""
        self.record_metric(name, size_mb, metadata, MetricType.MEMORY, 'MB')
    
    def record_count(self, name: str, count: int, 
                    metadata: Dict[str, Any] = None) -> None:
        """Record a count metric."""
        self.record_metric(name, count, metadata, MetricType.USER, 'count')
    
    def record_percentage(self, name: str, percentage: float, 
                         metadata: Dict[str, Any] = None) -> None:
        """Record a percentage metric."""
        self.record_metric(name, percentage, metadata, MetricType.SYSTEM, 'percent')
    
    def record_ratio(self, name: str, ratio: float, 
                    metadata: Dict[str, Any] = None) -> None:
        """Record a ratio metric."""
        self.record_metric(name, ratio, metadata, MetricType.CACHE, 'ratio')
    
    def _check_alerts(self, metric_name: str, value: Union[int, float]) -> None:
        """Check if metric value triggers any alerts."""
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        alert_id = f"{metric_name}_alert"
        
        # Check for new alerts
        if 'error' in thresholds and value >= thresholds['error']:
            self._trigger_alert(alert_id, metric_name, MetricSeverity.ERROR, 
                              value, thresholds['error'])
        elif 'warning' in thresholds and value >= thresholds['warning']:
            self._trigger_alert(alert_id, metric_name, MetricSeverity.WARNING, 
                              value, thresholds['warning'])
        else:
            # Check if we can resolve an existing alert
            if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                self._resolve_alert(alert_id)
    
    def _trigger_alert(self, alert_id: str, metric_name: str, 
                      severity: MetricSeverity, value: Union[int, float], 
                      threshold: Union[int, float]) -> None:
        """Trigger a performance alert."""
        message = f"{metric_name} ({value}) exceeded {severity.value} threshold ({threshold})"
        
        alert = PerformanceAlert(
            metric_name=metric_name,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold
        )
        
        self.alerts[alert_id] = alert
        self.alert_triggered.emit(alert)
    
    def _resolve_alert(self, alert_id: str) -> None:
        """Resolve a performance alert."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = time.time()
            self.alert_resolved.emit(alert_id)
    
    def get_metric_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series by name."""
        return self.metrics.get(name)
    
    def get_metric_statistics(self, name: str, time_window: Optional[float] = None) -> Dict[str, float]:
        """Get statistics for a metric."""
        if name not in self.metrics:
            return {}
        
        return self.metrics[name].get_statistics(time_window)
    
    def get_all_metrics(self) -> Dict[str, MetricSeries]:
        """Get all metric series."""
        return self.metrics.copy()
    
    def get_metrics_by_type(self, metric_type: MetricType) -> Dict[str, MetricSeries]:
        """Get metrics by type."""
        return {
            name: series for name, series in self.metrics.items()
            if series.metric_type == metric_type
        }
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_history(self, time_window: Optional[float] = None) -> List[PerformanceAlert]:
        """Get alert history within time window."""
        if time_window is None:
            return list(self.alerts.values())
        
        cutoff_time = time.time() - time_window
        return [
            alert for alert in self.alerts.values()
            if alert.timestamp >= cutoff_time
        ]
    
    def analyze_trends(self, metric_name: str, time_window: float = 300) -> Dict[str, Any]:
        """Analyze trends for a metric."""
        if metric_name not in self.metrics:
            return {}
        
        series = self.metrics[metric_name]
        cutoff_time = time.time() - time_window
        points = [p for p in series.points if p.timestamp >= cutoff_time]
        
        if len(points) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend
        values = [p.value for p in points]
        timestamps = [p.timestamp for p in points]
        
        # Simple linear regression for trend
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Classify trend
        if abs(slope) < 0.001:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        # Calculate trend strength
        correlation = abs(slope) * (max(values) - min(values)) / (max(timestamps) - min(timestamps))
        
        return {
            'trend': trend,
            'slope': slope,
            'correlation': correlation,
            'data_points': len(points),
            'time_window': time_window,
            'latest_value': values[-1] if values else 0,
            'average_value': sum(values) / len(values) if values else 0
        }
    
    def get_performance_summary(self, time_window: float = 300) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'timestamp': time.time(),
            'time_window': time_window,
            'metrics': {},
            'alerts': {
                'active': len(self.get_active_alerts()),
                'total': len(self.alerts),
                'by_severity': defaultdict(int)
            },
            'trends': {}
        }
        
        # Collect metric summaries
        for name, series in self.metrics.items():
            stats = series.get_statistics(time_window)
            if stats:
                summary['metrics'][name] = {
                    'latest': series.get_latest().value if series.get_latest() else 0,
                    'statistics': stats,
                    'unit': series.unit,
                    'type': series.metric_type.value
                }
        
        # Collect alert summaries
        for alert in self.alerts.values():
            summary['alerts']['by_severity'][alert.severity.value] += 1
        
        # Collect trend analysis
        key_metrics = ['page_load_time', 'memory_usage', 'render_time', 'cache_hit_rate']
        for metric_name in key_metrics:
            if metric_name in self.metrics:
                summary['trends'][metric_name] = self.analyze_trends(metric_name, time_window)
        
        return summary
    
    def export_metrics(self, format: str = 'json', time_window: Optional[float] = None) -> str:
        """Export metrics data in specified format."""
        if format == 'json':
            return self._export_json(time_window)
        elif format == 'csv':
            return self._export_csv(time_window)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_json(self, time_window: Optional[float] = None) -> str:
        """Export metrics as JSON."""
        export_data = {
            'export_time': time.time(),
            'time_window': time_window,
            'metrics': {}
        }
        
        for name, series in self.metrics.items():
            if time_window:
                cutoff_time = time.time() - time_window
                points = [p for p in series.points if p.timestamp >= cutoff_time]
            else:
                points = series.points
            
            export_data['metrics'][name] = {
                'type': series.metric_type.value,
                'unit': series.unit,
                'points': [
                    {
                        'timestamp': p.timestamp,
                        'value': p.value,
                        'metadata': p.metadata
                    }
                    for p in points
                ]
            }
        
        return json.dumps(export_data, indent=2)
    
    def _export_csv(self, time_window: Optional[float] = None) -> str:
        """Export metrics as CSV."""
        lines = ['timestamp,metric_name,value,unit,type']
        
        for name, series in self.metrics.items():
            if time_window:
                cutoff_time = time.time() - time_window
                points = [p for p in series.points if p.timestamp >= cutoff_time]
            else:
                points = series.points
            
            for point in points:
                lines.append(f"{point.timestamp},{name},{point.value},{series.unit},{series.metric_type.value}")
        
        return '\n'.join(lines)
    
    def set_alert_threshold(self, metric_name: str, severity: str, threshold: Union[int, float]) -> None:
        """Set alert threshold for a metric."""
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        
        self.alert_thresholds[metric_name][severity] = threshold
    
    def clear_metrics(self, metric_name: Optional[str] = None) -> None:
        """Clear metrics data."""
        if metric_name:
            if metric_name in self.metrics:
                self.metrics[metric_name].points.clear()
        else:
            for series in self.metrics.values():
                series.points.clear()
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics_collector: MetricsCollector, metric_name: str, 
                 metadata: Dict[str, Any] = None):
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.metadata = metadata or {}
        self.start_time = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        # Add exception info to metadata if an exception occurred
        if exc_type:
            self.metadata['exception'] = {
                'type': exc_type.__name__,
                'message': str(exc_val) if exc_val else None
            }
        
        self.metrics_collector.record_timing(self.metric_name, duration_ms, self.metadata)


class PerformanceProfiler:
    """
    High-level performance profiler for PDF.js operations.
    
    Provides easy-to-use interface for profiling common PDF operations.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.active_timers: Dict[str, float] = {}
    
    def start_timer(self, operation_name: str) -> None:
        """Start timing an operation."""
        self.active_timers[operation_name] = time.time()
    
    def end_timer(self, operation_name: str, metadata: Dict[str, Any] = None) -> float:
        """End timing an operation and record the metric."""
        if operation_name not in self.active_timers:
            return 0
        
        duration_ms = (time.time() - self.active_timers.pop(operation_name)) * 1000
        self.metrics_collector.record_timing(operation_name, duration_ms, metadata)
        return duration_ms
    
    def time_operation(self, operation_name: str, metadata: Dict[str, Any] = None) -> TimingContext:
        """Create a timing context for an operation."""
        return TimingContext(self.metrics_collector, operation_name, metadata)
    
    def record_page_load(self, page_number: int, duration_ms: float, 
                        document_size_mb: float = 0) -> None:
        """Record page load performance."""
        metadata = {
            'page_number': page_number,
            'document_size_mb': document_size_mb
        }
        self.metrics_collector.record_timing('page_load_time', duration_ms, metadata)
    
    def record_render_performance(self, render_time_ms: float, page_count: int = 1) -> None:
        """Record render performance."""
        metadata = {'page_count': page_count}
        self.metrics_collector.record_timing('render_time', render_time_ms, metadata)
    
    def record_memory_usage(self, memory_mb: float, operation: str = 'general') -> None:
        """Record memory usage."""
        metadata = {'operation': operation}
        self.metrics_collector.record_memory('memory_usage', memory_mb, metadata)
    
    def record_cache_performance(self, hit_rate: float, total_requests: int) -> None:
        """Record cache performance."""
        metadata = {'total_requests': total_requests}
        self.metrics_collector.record_ratio('cache_hit_rate', hit_rate, metadata)
        self.metrics_collector.record_ratio('cache_miss_rate', 1.0 - hit_rate, metadata)
    
    def get_operation_stats(self, operation_name: str, time_window: float = 300) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        return self.metrics_collector.get_metric_statistics(operation_name, time_window)