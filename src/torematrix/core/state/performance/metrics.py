"""
Metrics collection and analysis for state management performance.
"""

import time
import asyncio
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import threading
import weakref


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


@dataclass
class MetricValue:
    """Individual metric measurement."""
    timestamp: float
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def now(cls, value: Union[int, float], tags: Dict[str, str] = None) -> 'MetricValue':
        """Create metric value with current timestamp."""
        return cls(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )


@dataclass
class StateMetrics:
    """Comprehensive state management metrics."""
    
    # Selector metrics
    selector_execution_count: int = 0
    selector_cache_hits: int = 0
    selector_cache_misses: int = 0
    selector_avg_execution_time_ms: float = 0.0
    selector_max_execution_time_ms: float = 0.0
    
    # State update metrics
    state_update_count: int = 0
    state_update_avg_time_ms: float = 0.0
    state_size_bytes: int = 0
    
    # Subscription metrics
    active_subscriptions: int = 0
    subscription_notifications: int = 0
    subscription_avg_notification_time_ms: float = 0.0
    
    # Memory metrics
    memory_usage_mb: float = 0.0
    memory_growth_rate_mb_per_min: float = 0.0
    gc_collections: int = 0
    
    # Performance metrics
    frame_rate: float = 0.0
    dropped_frames: int = 0
    render_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'selector': {
                'execution_count': self.selector_execution_count,
                'cache_hits': self.selector_cache_hits,
                'cache_misses': self.selector_cache_misses,
                'cache_hit_rate': (
                    self.selector_cache_hits / 
                    (self.selector_cache_hits + self.selector_cache_misses) * 100
                    if (self.selector_cache_hits + self.selector_cache_misses) > 0 else 0
                ),
                'avg_execution_time_ms': self.selector_avg_execution_time_ms,
                'max_execution_time_ms': self.selector_max_execution_time_ms
            },
            'state': {
                'update_count': self.state_update_count,
                'avg_update_time_ms': self.state_update_avg_time_ms,
                'size_bytes': self.state_size_bytes,
                'size_mb': self.state_size_bytes / (1024 * 1024)
            },
            'subscriptions': {
                'active_count': self.active_subscriptions,
                'notifications': self.subscription_notifications,
                'avg_notification_time_ms': self.subscription_avg_notification_time_ms
            },
            'memory': {
                'usage_mb': self.memory_usage_mb,
                'growth_rate_mb_per_min': self.memory_growth_rate_mb_per_min,
                'gc_collections': self.gc_collections
            },
            'performance': {
                'frame_rate': self.frame_rate,
                'dropped_frames': self.dropped_frames,
                'render_time_ms': self.render_time_ms
            }
        }


class MetricsCollector:
    """
    High-performance metrics collection system for state management.
    
    Collects and aggregates performance metrics with minimal overhead.
    """
    
    def __init__(
        self,
        buffer_size: int = 10000,
        aggregation_interval: float = 1.0
    ):
        self.buffer_size = buffer_size
        self.aggregation_interval = aggregation_interval
        
        # Metric storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=buffer_size))
        self._aggregated_metrics: Dict[str, Any] = {}
        self._metric_types: Dict[str, MetricType] = {}
        
        # Threading
        self._lock = threading.RLock()
        
        # Aggregation
        self._last_aggregation = time.time()
        self._aggregation_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._metric_callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    def record_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """
        Record a counter metric (monotonically increasing).
        
        Args:
            name: Metric name
            value: Value to add (default 1)
            tags: Optional tags for the metric
        """
        self._record_metric(name, MetricType.COUNTER, value, tags)
    
    def record_gauge(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """
        Record a gauge metric (point-in-time value).
        
        Args:
            name: Metric name
            value: Current value
            tags: Optional tags for the metric
        """
        self._record_metric(name, MetricType.GAUGE, value, tags)
    
    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """
        Record a timer metric (duration measurement).
        
        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        self._record_metric(name, MetricType.TIMER, duration_ms, tags)
    
    def record_histogram(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """
        Record a histogram metric (distribution of values).
        
        Args:
            name: Metric name
            value: Value to record
            tags: Optional tags for the metric
        """
        self._record_metric(name, MetricType.HISTOGRAM, value, tags)
    
    def _record_metric(
        self, 
        name: str, 
        metric_type: MetricType, 
        value: Union[int, float], 
        tags: Dict[str, str] = None
    ):
        """Internal method to record a metric."""
        with self._lock:
            self._metric_types[name] = metric_type
            metric_value = MetricValue.now(value, tags)
            self._metrics[name].append(metric_value)
            
            # Trigger callbacks
            for callback in self._metric_callbacks.get(name, []):
                try:
                    callback(name, metric_value)
                except Exception:
                    pass  # Don't let callback errors break metrics
    
    def timer(self, name: str, tags: Dict[str, str] = None):
        """
        Context manager for timing operations.
        
        Args:
            name: Timer metric name
            tags: Optional tags for the metric
            
        Example:
            with collector.timer('selector_execution'):
                result = selector(state)
        """
        return TimerContext(self, name, tags)
    
    def increment(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Convenience method to increment a counter."""
        self.record_counter(name, value, tags)
    
    def set_gauge(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Convenience method to set a gauge value."""
        self.record_gauge(name, value, tags)
    
    def get_metric_summary(self, name: str) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Dictionary with metric summary
        """
        with self._lock:
            if name not in self._metrics:
                return {}
            
            values = [mv.value for mv in self._metrics[name]]
            metric_type = self._metric_types.get(name, MetricType.GAUGE)
            
            if not values:
                return {'name': name, 'type': metric_type.value, 'count': 0}
            
            summary = {
                'name': name,
                'type': metric_type.value,
                'count': len(values),
                'latest': values[-1],
                'first': values[0]
            }
            
            if metric_type in [MetricType.TIMER, MetricType.HISTOGRAM, MetricType.GAUGE]:
                summary.update({
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'sum': sum(values)
                })
                
                # Calculate percentiles
                sorted_values = sorted(values)
                summary.update({
                    'p50': self._percentile(sorted_values, 50),
                    'p95': self._percentile(sorted_values, 95),
                    'p99': self._percentile(sorted_values, 99)
                })
            
            elif metric_type == MetricType.COUNTER:
                summary.update({
                    'total': sum(values),
                    'rate_per_second': self._calculate_rate(name)
                })
            
            return summary
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def _calculate_rate(self, name: str) -> float:
        """Calculate rate per second for counter metrics."""
        with self._lock:
            if name not in self._metrics:
                return 0.0
            
            values = list(self._metrics[name])
            if len(values) < 2:
                return 0.0
            
            time_span = values[-1].timestamp - values[0].timestamp
            if time_span <= 0:
                return 0.0
            
            total_count = sum(mv.value for mv in values)
            return total_count / time_span
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get summary for all recorded metrics."""
        with self._lock:
            return {name: self.get_metric_summary(name) for name in self._metrics.keys()}
    
    def get_state_metrics(self) -> StateMetrics:
        """Get comprehensive state management metrics."""
        metrics = StateMetrics()
        
        # Selector metrics
        selector_exec = self.get_metric_summary('selector_execution_time')
        if selector_exec:
            metrics.selector_execution_count = selector_exec.get('count', 0)
            metrics.selector_avg_execution_time_ms = selector_exec.get('avg', 0.0)
            metrics.selector_max_execution_time_ms = selector_exec.get('max', 0.0)
        
        cache_hits = self.get_metric_summary('selector_cache_hits')
        cache_misses = self.get_metric_summary('selector_cache_misses')
        if cache_hits:
            metrics.selector_cache_hits = cache_hits.get('total', 0)
        if cache_misses:
            metrics.selector_cache_misses = cache_misses.get('total', 0)
        
        # State update metrics
        state_updates = self.get_metric_summary('state_update_time')
        if state_updates:
            metrics.state_update_count = state_updates.get('count', 0)
            metrics.state_update_avg_time_ms = state_updates.get('avg', 0.0)
        
        # Memory metrics
        memory = self.get_metric_summary('memory_usage')
        if memory:
            metrics.memory_usage_mb = memory.get('latest', 0.0)
        
        # Performance metrics
        frame_rate = self.get_metric_summary('frame_rate')
        if frame_rate:
            metrics.frame_rate = frame_rate.get('latest', 0.0)
        
        render_time = self.get_metric_summary('render_time')
        if render_time:
            metrics.render_time_ms = render_time.get('avg', 0.0)
        
        return metrics
    
    def add_metric_callback(self, metric_name: str, callback: Callable[[str, MetricValue], None]):
        """
        Add callback for metric events.
        
        Args:
            metric_name: Name of metric to watch
            callback: Function to call when metric is recorded
        """
        self._metric_callbacks[metric_name].append(callback)
    
    def remove_metric_callback(self, metric_name: str, callback: Callable):
        """Remove metric callback."""
        if metric_name in self._metric_callbacks:
            try:
                self._metric_callbacks[metric_name].remove(callback)
            except ValueError:
                pass
    
    async def start_aggregation(self):
        """Start background aggregation task."""
        if self._running:
            return
        
        self._running = True
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
    
    async def stop_aggregation(self):
        """Stop background aggregation task."""
        self._running = False
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
            finally:
                self._aggregation_task = None
    
    async def _aggregation_loop(self):
        """Background aggregation loop."""
        while self._running:
            try:
                await asyncio.sleep(self.aggregation_interval)
                self._aggregate_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Metrics aggregation error: {e}")
    
    def _aggregate_metrics(self):
        """Aggregate metrics for efficient querying."""
        current_time = time.time()
        
        with self._lock:
            # Simple aggregation - store current summaries
            for name in self._metrics.keys():
                self._aggregated_metrics[name] = self.get_metric_summary(name)
            
            self._last_aggregation = current_time
    
    def clear_metrics(self, metric_name: Optional[str] = None):
        """
        Clear metric data.
        
        Args:
            metric_name: Specific metric to clear, or None for all
        """
        with self._lock:
            if metric_name:
                if metric_name in self._metrics:
                    self._metrics[metric_name].clear()
                if metric_name in self._aggregated_metrics:
                    del self._aggregated_metrics[metric_name]
            else:
                self._metrics.clear()
                self._aggregated_metrics.clear()
                self._metric_types.clear()
    
    def export_metrics(self, format: str = 'json') -> Any:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ('json', 'prometheus', 'csv')
            
        Returns:
            Exported metrics data
        """
        if format == 'json':
            return {
                'metrics': self.get_all_metrics(),
                'state_metrics': self.get_state_metrics().to_dict(),
                'timestamp': time.time()
            }
        elif format == 'prometheus':
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, summary in self.get_all_metrics().items():
            metric_type = summary.get('type', 'gauge')
            
            # Convert metric name to Prometheus format
            prom_name = name.replace('.', '_').replace('-', '_')
            
            lines.append(f"# TYPE {prom_name} {metric_type}")
            
            if metric_type == 'counter':
                lines.append(f"{prom_name}_total {summary.get('total', 0)}")
            elif metric_type in ['gauge', 'timer', 'histogram']:
                lines.append(f"{prom_name} {summary.get('latest', 0)}")
                if 'avg' in summary:
                    lines.append(f"{prom_name}_avg {summary['avg']}")
                if 'p95' in summary:
                    lines.append(f"{prom_name}_p95 {summary['p95']}")
        
        return '\n'.join(lines)


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time = 0.0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.perf_counter() - self.start_time) * 1000  # Convert to ms
        self.collector.record_timer(self.name, duration, self.tags)


# Global metrics collector instance
metrics_collector = MetricsCollector()