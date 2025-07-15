"""Performance Monitoring and Optimization

Comprehensive performance monitoring system for property panel operations
with automatic optimization, profiling, and performance alerts. Tracks
response times, memory usage, and system resources.
"""

import time
import gc
import threading
import psutil
import tracemalloc
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import statistics
import weakref
import sys

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex

from .caching import PropertyCache
from .virtualization import VirtualizationMetrics


class PerformanceLevel(Enum):
    """Performance levels for optimization"""
    EXCELLENT = "excellent"  # >90% targets met
    GOOD = "good"           # >75% targets met  
    FAIR = "fair"           # >50% targets met
    POOR = "poor"           # <50% targets met


class AlertSeverity(Enum):
    """Performance alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceTarget:
    """Performance target definition"""
    name: str
    target_value: float
    unit: str
    description: str
    alert_threshold: float = 1.2  # Alert when value exceeds target by this factor
    critical_threshold: float = 2.0  # Critical alert threshold


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    target: Optional[float] = None
    meets_target: bool = True
    
    def __post_init__(self):
        """Calculate if metric meets target"""
        if self.target is not None:
            self.meets_target = self.value <= self.target


@dataclass
class PerformanceAlert:
    """Performance alert"""
    metric_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    target: Optional[float] = None
    
    def is_recent(self, seconds: int = 300) -> bool:
        """Check if alert is recent (within specified seconds)"""
        return (datetime.now() - self.timestamp).total_seconds() < seconds


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, monitor: 'PerformanceMonitor'):
        self.operation_name = operation_name
        self.monitor = monitor
        self.start_time = 0.0
        self.memory_start = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.memory_start = current
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        duration_ms = (end_time - self.start_time) * 1000
        
        memory_delta = 0
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            memory_delta = current - self.memory_start
        
        self.monitor.record_operation(self.operation_name, duration_ms, memory_delta)


class MemoryProfiler:
    """Memory usage profiler"""
    
    def __init__(self):
        self.snapshots: List[Any] = []
        self.is_profiling = False
    
    def start_profiling(self):
        """Start memory profiling"""
        if not self.is_profiling:
            tracemalloc.start()
            self.is_profiling = True
    
    def stop_profiling(self):
        """Stop memory profiling"""
        if self.is_profiling:
            tracemalloc.stop()
            self.is_profiling = False
    
    def take_snapshot(self, label: str = "") -> Dict[str, Any]:
        """Take memory snapshot"""
        if not self.is_profiling:
            return {}
        
        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics('lineno')
        
        # Get top memory consumers
        top_stats = []
        for stat in stats[:10]:
            top_stats.append({
                'filename': stat.traceback.format()[-1] if stat.traceback.format() else 'unknown',
                'size_mb': stat.size / (1024 * 1024),
                'count': stat.count
            })
        
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        
        snapshot_data = {
            'label': label,
            'timestamp': datetime.now(),
            'current_mb': current_memory / (1024 * 1024),
            'peak_mb': peak_memory / (1024 * 1024),
            'top_allocations': top_stats
        }
        
        self.snapshots.append(snapshot_data)
        return snapshot_data
    
    def get_memory_growth(self) -> float:
        """Get memory growth since first snapshot"""
        if len(self.snapshots) < 2:
            return 0.0
        
        first = self.snapshots[0]['current_mb']
        last = self.snapshots[-1]['current_mb']
        return last - first
    
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        if len(self.snapshots) < 3:
            return []
        
        # Look for consistent memory growth
        recent_snapshots = self.snapshots[-5:]  # Last 5 snapshots
        growth_rates = []
        
        for i in range(1, len(recent_snapshots)):
            prev_mb = recent_snapshots[i-1]['current_mb']
            curr_mb = recent_snapshots[i]['current_mb']
            growth = curr_mb - prev_mb
            growth_rates.append(growth)
        
        # Check if consistently growing
        if all(rate > 0 for rate in growth_rates):
            avg_growth = sum(growth_rates) / len(growth_rates)
            if avg_growth > 1.0:  # Growing by more than 1MB per snapshot
                return [{
                    'type': 'memory_leak',
                    'avg_growth_mb': avg_growth,
                    'total_growth_mb': sum(growth_rates),
                    'snapshots_analyzed': len(growth_rates)
                }]
        
        return []


class PerformanceMonitor(QObject):
    """Comprehensive performance monitoring system"""
    
    # Performance signals
    metric_recorded = pyqtSignal(PerformanceMetric)
    alert_triggered = pyqtSignal(PerformanceAlert)
    performance_report = pyqtSignal(dict)
    optimization_suggested = pyqtSignal(str, dict)  # optimization_type, details
    
    def __init__(self, cache: Optional[PropertyCache] = None):
        super().__init__()
        
        # Configuration
        self.cache = cache
        self.monitoring_enabled = True
        self.profiling_enabled = False
        
        # Performance targets
        self.targets = {
            'property_update_ms': PerformanceTarget(
                name='Property Update Time',
                target_value=50.0,
                unit='ms',
                description='Time to update property value'
            ),
            'validation_ms': PerformanceTarget(
                name='Validation Time',
                target_value=50.0,
                unit='ms',
                description='Time to validate property value'
            ),
            'search_ms': PerformanceTarget(
                name='Search Time',
                target_value=50.0,
                unit='ms',
                description='Time to search properties'
            ),
            'memory_usage_mb': PerformanceTarget(
                name='Memory Usage',
                target_value=50.0,
                unit='MB',
                description='Total memory usage'
            ),
            'ui_response_ms': PerformanceTarget(
                name='UI Response Time',
                target_value=25.0,
                unit='ms',
                description='UI element response time'
            )
        }
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.operation_timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.alerts: List[PerformanceAlert] = []
        self.max_alerts = 100
        
        # System monitoring
        self.system_stats = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_io': {'read_mb': 0.0, 'write_mb': 0.0},
            'network_io': {'sent_mb': 0.0, 'recv_mb': 0.0}
        }
        
        # Memory profiler
        self.memory_profiler = MemoryProfiler()
        
        # Thread-safe operations
        self.mutex = QMutex()
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_system_metrics)
        self.monitor_timer.start(1000)  # Collect metrics every second
        
        # Report timer
        self.report_timer = QTimer()
        self.report_timer.timeout.connect(self._generate_performance_report)
        self.report_timer.start(30000)  # Generate report every 30 seconds
        
        # Garbage collection monitoring
        self.gc_stats = {'collections': 0, 'collected': 0, 'uncollectable': 0}
        self._setup_gc_monitoring()
    
    def start_profiling(self):
        """Start memory profiling"""
        self.profiling_enabled = True
        self.memory_profiler.start_profiling()
        self.memory_profiler.take_snapshot("profiling_start")
    
    def stop_profiling(self):
        """Stop memory profiling"""
        if self.profiling_enabled:
            self.memory_profiler.take_snapshot("profiling_end")
            self.memory_profiler.stop_profiling()
            self.profiling_enabled = False
    
    def timing(self, operation_name: str) -> TimingContext:
        """Get timing context for operation"""
        return TimingContext(operation_name, self)
    
    def record_metric(self, name: str, value: float, unit: str = "",
                     target: Optional[float] = None) -> None:
        """Record performance metric"""
        if not self.monitoring_enabled:
            return
        
        self.mutex.lock()
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                target=target or self.targets.get(name, PerformanceTarget("", 0, "", "")).target_value
            )
            
            self.metrics[name].append(metric)
            self.metric_recorded.emit(metric)
            
            # Check for alerts
            self._check_metric_alerts(metric)
            
        finally:
            self.mutex.unlock()
    
    def record_operation(self, operation_name: str, duration_ms: float, memory_delta: int = 0) -> None:
        """Record operation timing and memory usage"""
        if not self.monitoring_enabled:
            return
        
        self.mutex.lock()
        try:
            timing_data = {
                'timestamp': datetime.now(),
                'duration_ms': duration_ms,
                'memory_delta_mb': memory_delta / (1024 * 1024) if memory_delta else 0
            }
            
            self.operation_timings[operation_name].append(timing_data)
            
            # Record as metric
            self.record_metric(f"{operation_name}_ms", duration_ms, "ms")
            
            if memory_delta != 0:
                self.record_metric(f"{operation_name}_memory_mb", 
                                 abs(memory_delta) / (1024 * 1024), "MB")
        
        finally:
            self.mutex.unlock()
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics:
            return {}
        
        values = [m.value for m in self.metrics[metric_name]]
        if not values:
            return {}
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'recent_avg': statistics.mean(values[-10:]) if len(values) >= 10 else statistics.mean(values)
        }
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        if operation_name not in self.operation_timings:
            return {}
        
        timings = self.operation_timings[operation_name]
        durations = [t['duration_ms'] for t in timings]
        
        if not durations:
            return {}
        
        stats = {
            'count': len(durations),
            'mean_ms': statistics.mean(durations),
            'median_ms': statistics.median(durations),
            'min_ms': min(durations),
            'max_ms': max(durations),
            'p95_ms': self._percentile(durations, 95),
            'p99_ms': self._percentile(durations, 99)
        }
        
        # Memory statistics if available
        memory_deltas = [t['memory_delta_mb'] for t in timings if t['memory_delta_mb'] != 0]
        if memory_deltas:
            stats.update({
                'memory_mean_mb': statistics.mean(memory_deltas),
                'memory_max_mb': max(memory_deltas),
                'memory_total_mb': sum(memory_deltas)
            })
        
        return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_duration_mins': self._get_monitoring_duration_minutes(),
            'performance_level': self._calculate_performance_level(),
            'targets_met': self._count_targets_met(),
            'active_alerts': len([a for a in self.alerts if a.is_recent()]),
            'system_health': self._assess_system_health(),
            'cache_performance': self._get_cache_performance(),
            'memory_status': self._get_memory_status(),
            'top_operations': self._get_top_operations(),
            'recommendations': self._generate_recommendations()
        }
        
        return summary
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None, 
                  recent_only: bool = True) -> List[PerformanceAlert]:
        """Get performance alerts"""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if recent_only:
            alerts = [a for a in alerts if a.is_recent()]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Trigger performance optimization"""
        optimizations = []
        
        # Memory optimization
        if self._should_trigger_gc():
            collected = self._force_garbage_collection()
            optimizations.append({
                'type': 'garbage_collection',
                'collected_objects': collected,
                'description': 'Forced garbage collection to free memory'
            })
        
        # Cache optimization
        if self.cache:
            cache_stats = self.cache.get_stats()
            if cache_stats.get('hit_ratio', 0) < 70:  # Low hit ratio
                # Suggest cache tuning
                optimizations.append({
                    'type': 'cache_tuning',
                    'current_hit_ratio': cache_stats.get('hit_ratio', 0),
                    'description': 'Cache hit ratio is low, consider adjusting cache size or TTL'
                })
        
        # Memory leak detection
        if self.profiling_enabled:
            leaks = self.memory_profiler.detect_memory_leaks()
            if leaks:
                optimizations.append({
                    'type': 'memory_leak_detected',
                    'leaks': leaks,
                    'description': 'Potential memory leaks detected'
                })
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'optimizations_applied': len(optimizations),
            'optimizations': optimizations,
            'memory_freed_mb': sum(opt.get('collected_objects', 0) for opt in optimizations if opt['type'] == 'garbage_collection') / (1024 * 1024)
        }
        
        return result
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU usage
            self.system_stats['cpu_percent'] = psutil.cpu_percent()
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_stats['memory_percent'] = memory.percent
            
            # Process-specific memory
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            self.record_metric('process_memory_mb', process_memory_mb, 'MB')
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.system_stats['disk_io'] = {
                    'read_mb': disk_io.read_bytes / (1024 * 1024),
                    'write_mb': disk_io.write_bytes / (1024 * 1024)
                }
            
            # Record system metrics
            self.record_metric('cpu_percent', self.system_stats['cpu_percent'], '%')
            self.record_metric('system_memory_percent', self.system_stats['memory_percent'], '%')
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
    
    def _check_metric_alerts(self, metric: PerformanceMetric):
        """Check if metric triggers any alerts"""
        if metric.target is None:
            return
        
        target_info = self.targets.get(metric.name.replace('_ms', '').replace('_mb', '').replace('_percent', ''))
        if not target_info:
            return
        
        # Check alert thresholds
        alert_threshold = metric.target * target_info.alert_threshold
        critical_threshold = metric.target * target_info.critical_threshold
        
        severity = None
        if metric.value >= critical_threshold:
            severity = AlertSeverity.CRITICAL
        elif metric.value >= alert_threshold:
            severity = AlertSeverity.WARNING
        
        if severity:
            alert = PerformanceAlert(
                metric_name=metric.name,
                severity=severity,
                message=f"{metric.name} ({metric.value:.1f}{metric.unit}) exceeds target ({metric.target:.1f}{metric.unit})",
                value=metric.value,
                target=metric.target
            )
            
            self.alerts.append(alert)
            
            # Limit alerts list size
            if len(self.alerts) > self.max_alerts:
                self.alerts.pop(0)
            
            self.alert_triggered.emit(alert)
    
    def _calculate_performance_level(self) -> PerformanceLevel:
        """Calculate overall performance level"""
        targets_met = self._count_targets_met()
        total_targets = len(self.targets)
        
        if total_targets == 0:
            return PerformanceLevel.GOOD
        
        success_rate = targets_met / total_targets
        
        if success_rate >= 0.9:
            return PerformanceLevel.EXCELLENT
        elif success_rate >= 0.75:
            return PerformanceLevel.GOOD
        elif success_rate >= 0.5:
            return PerformanceLevel.FAIR
        else:
            return PerformanceLevel.POOR
    
    def _count_targets_met(self) -> int:
        """Count how many performance targets are being met"""
        targets_met = 0
        
        for target_name, target_info in self.targets.items():
            metric_name = f"{target_name}_ms" if "ms" in target_info.unit else f"{target_name}_{target_info.unit.lower()}"
            
            if metric_name in self.metrics:
                recent_metrics = list(self.metrics[metric_name])[-10:]  # Last 10 measurements
                if recent_metrics:
                    avg_value = sum(m.value for m in recent_metrics) / len(recent_metrics)
                    if avg_value <= target_info.target_value:
                        targets_met += 1
        
        return targets_met
    
    def _assess_system_health(self) -> str:
        """Assess overall system health"""
        cpu = self.system_stats['cpu_percent']
        memory = self.system_stats['memory_percent']
        
        if cpu > 80 or memory > 80:
            return "poor"
        elif cpu > 60 or memory > 60:
            return "fair"
        elif cpu > 40 or memory > 40:
            return "good"
        else:
            return "excellent"
    
    def _get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        if not self.cache:
            return {"enabled": False}
        
        stats = self.cache.get_stats()
        info = self.cache.get_cache_info()
        
        return {
            "enabled": True,
            "hit_ratio": stats.get('hit_ratio', 0.0),
            "total_requests": stats.get('total_requests', 0),
            "cache_size_mb": info.get('total_size_mb', 0.0),
            "entry_count": info.get('total_entries', 0),
            "performance": "excellent" if stats.get('hit_ratio', 0) > 80 else
                          "good" if stats.get('hit_ratio', 0) > 60 else
                          "fair" if stats.get('hit_ratio', 0) > 40 else "poor"
        }
    
    def _get_memory_status(self) -> Dict[str, Any]:
        """Get memory usage status"""
        if self.profiling_enabled:
            growth = self.memory_profiler.get_memory_growth()
            leaks = self.memory_profiler.detect_memory_leaks()
        else:
            growth = 0.0
            leaks = []
        
        return {
            "profiling_enabled": self.profiling_enabled,
            "growth_mb": growth,
            "potential_leaks": len(leaks),
            "gc_collections": self.gc_stats['collections'],
            "gc_collected": self.gc_stats['collected']
        }
    
    def _get_top_operations(self) -> List[Dict[str, Any]]:
        """Get top slowest operations"""
        operations = []
        
        for op_name, timings in self.operation_timings.items():
            if not timings:
                continue
            
            stats = self.get_operation_stats(op_name)
            operations.append({
                'name': op_name,
                'mean_ms': stats.get('mean_ms', 0),
                'p95_ms': stats.get('p95_ms', 0),
                'count': stats.get('count', 0)
            })
        
        # Sort by P95 latency
        operations.sort(key=lambda x: x['p95_ms'], reverse=True)
        return operations[:10]  # Top 10 slowest
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Cache recommendations
        if self.cache:
            cache_stats = self.cache.get_stats()
            hit_ratio = cache_stats.get('hit_ratio', 0)
            
            if hit_ratio < 60:
                recommendations.append("Consider increasing cache size or TTL for better hit ratio")
            elif hit_ratio > 95:
                recommendations.append("Cache hit ratio is excellent, consider reducing cache size if memory is constrained")
        
        # Memory recommendations
        if self.profiling_enabled:
            leaks = self.memory_profiler.detect_memory_leaks()
            if leaks:
                recommendations.append("Memory leaks detected, review object lifecycle management")
        
        # System recommendations
        cpu = self.system_stats['cpu_percent']
        memory = self.system_stats['memory_percent']
        
        if cpu > 70:
            recommendations.append("High CPU usage detected, consider optimizing computation-heavy operations")
        
        if memory > 70:
            recommendations.append("High memory usage detected, consider enabling memory profiling and optimization")
        
        # Operation-specific recommendations
        slow_operations = [op for op in self._get_top_operations() if op['p95_ms'] > 100]
        if slow_operations:
            recommendations.append(f"Optimize slow operations: {', '.join(op['name'] for op in slow_operations[:3])}")
        
        return recommendations
    
    def _generate_performance_report(self):
        """Generate and emit performance report"""
        report = self.get_performance_summary()
        self.performance_report.emit(report)
    
    def _should_trigger_gc(self) -> bool:
        """Check if garbage collection should be triggered"""
        # Trigger GC if memory usage is high
        return self.system_stats['memory_percent'] > 70
    
    def _force_garbage_collection(self) -> int:
        """Force garbage collection and return collected count"""
        collected_before = sum(self.gc_stats.values())
        
        # Force collection for all generations
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        self.gc_stats['collected'] += collected
        return collected
    
    def _setup_gc_monitoring(self):
        """Setup garbage collection monitoring"""
        # Set up GC callbacks to track collections
        def gc_callback(phase, info):
            if phase == 'start':
                self.gc_stats['collections'] += 1
            elif phase == 'stop':
                self.gc_stats['collected'] += info.get('collected', 0)
                self.gc_stats['uncollectable'] += info.get('uncollectable', 0)
        
        # Note: gc.callbacks is not available in all Python versions
        # This is a placeholder for GC monitoring setup
    
    def _get_monitoring_duration_minutes(self) -> float:
        """Get monitoring duration in minutes"""
        if not self.metrics:
            return 0.0
        
        # Find earliest metric
        earliest_time = None
        for metric_deque in self.metrics.values():
            if metric_deque:
                first_metric_time = metric_deque[0].timestamp
                if earliest_time is None or first_metric_time < earliest_time:
                    earliest_time = first_metric_time
        
        if earliest_time:
            return (datetime.now() - earliest_time).total_seconds() / 60
        
        return 0.0
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_values[int(k)]
        
        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return d0 + d1


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _global_monitor
    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = PerformanceMonitor()
        return _global_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """Set global performance monitor instance"""
    global _global_monitor
    with _monitor_lock:
        _global_monitor = monitor


# Convenience decorators and functions

def timed_operation(operation_name: str):
    """Decorator for timing operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with monitor.timing(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def record_metric(name: str, value: float, unit: str = "") -> None:
    """Record performance metric to global monitor"""
    monitor = get_performance_monitor()
    monitor.record_metric(name, value, unit)


def start_performance_monitoring() -> PerformanceMonitor:
    """Start global performance monitoring"""
    monitor = get_performance_monitor()
    monitor.start_profiling()
    return monitor


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary from global monitor"""
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()