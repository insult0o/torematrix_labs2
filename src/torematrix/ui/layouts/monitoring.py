"""Performance Monitoring Tools for TORE Matrix Labs V3.

This module provides comprehensive monitoring and analytics for layout performance,
including real-time metrics, historical analysis, bottleneck detection, and
performance visualization tools.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union, Tuple, NamedTuple
from enum import Enum, auto
from dataclasses import dataclass, field
import logging
import time
import json
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QPushButton, QGroupBox,
    QScrollArea, QFrame, QSplitter, QGridLayout
)
from PyQt6.QtCore import (
    QObject, QTimer, QThread, pyqtSignal, QMutex, QSize, QRect
)
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from .performance import PerformanceMetrics, PerformanceProfiler

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert levels for performance monitoring."""
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()
    EMERGENCY = auto()


class MetricType(Enum):
    """Types of metrics to monitor."""
    LAYOUT_TIME = auto()
    MEMORY_USAGE = auto()
    CPU_USAGE = auto()
    CACHE_HIT_RATIO = auto()
    FRAME_RATE = auto()
    WIDGET_COUNT = auto()
    ANIMATION_PERFORMANCE = auto()


@dataclass
class PerformanceAlert:
    """Performance alert data structure."""
    level: AlertLevel
    metric_type: MetricType
    message: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricThreshold:
    """Threshold configuration for metrics."""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: float
    comparison_operator: str = ">"  # ">", "<", ">=", "<="
    enabled: bool = True


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""
    timestamp: datetime
    duration_minutes: int
    summary: Dict[str, Any]
    detailed_metrics: Dict[str, List[float]]
    alerts_generated: List[PerformanceAlert]
    recommendations: List[str]
    bottlenecks_detected: List[Dict[str, Any]]


class MetricCollector:
    """Collects and aggregates performance metrics over time."""
    
    def __init__(self, max_samples: int = 3600):  # 1 hour at 1 sample/second
        self._max_samples = max_samples
        self._metrics_history: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=max_samples) 
            for metric_type in MetricType
        }
        self._timestamps: deque = deque(maxlen=max_samples)
        self._mutex = threading.Lock()
    
    def record_metric(self, metric_type: MetricType, value: float) -> None:
        """Record a metric value with timestamp."""
        with self._mutex:
            current_time = datetime.now()
            self._metrics_history[metric_type].append(value)
            
            # Only add timestamp if it's for the first metric to avoid duplicates
            if metric_type == MetricType.LAYOUT_TIME:
                self._timestamps.append(current_time)
    
    def get_recent_values(self, metric_type: MetricType, count: int = 60) -> List[float]:
        """Get the most recent values for a metric."""
        with self._mutex:
            history = self._metrics_history[metric_type]
            return list(history)[-count:] if history else []
    
    def get_metric_statistics(self, metric_type: MetricType) -> Dict[str, float]:
        """Get statistical analysis of a metric."""
        with self._mutex:
            values = list(self._metrics_history[metric_type])
            
            if not values:
                return {}
            
            return {
                'count': len(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'min': min(values),
                'max': max(values),
                'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
                'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
            }
    
    def detect_anomalies(self, metric_type: MetricType, z_threshold: float = 3.0) -> List[Tuple[int, float]]:
        """Detect anomalies using Z-score analysis."""
        with self._mutex:
            values = list(self._metrics_history[metric_type])
            
            if len(values) < 10:  # Need minimum samples for anomaly detection
                return []
            
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values)
            
            if std_dev == 0:
                return []
            
            anomalies = []
            for i, value in enumerate(values):
                z_score = abs((value - mean) / std_dev)
                if z_score > z_threshold:
                    anomalies.append((i, value))
            
            return anomalies
    
    def get_trend_analysis(self, metric_type: MetricType) -> Dict[str, Any]:
        """Analyze trends in metric values."""
        with self._mutex:
            values = list(self._metrics_history[metric_type])
            
            if len(values) < 10:
                return {'trend': 'insufficient_data'}
            
            # Simple linear regression for trend
            n = len(values)
            x = list(range(n))
            y = values
            
            x_mean = sum(x) / n
            y_mean = sum(y) / n
            
            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator
            
            # Determine trend direction
            if abs(slope) < 0.01:  # Threshold for "stable"
                trend = 'stable'
            elif slope > 0:
                trend = 'increasing'
            else:
                trend = 'decreasing'
            
            # Calculate correlation coefficient
            if len(values) > 1:
                correlation = statistics.correlation(x, y) if hasattr(statistics, 'correlation') else 0.0
            else:
                correlation = 0.0
            
            return {
                'trend': trend,
                'slope': slope,
                'correlation': correlation,
                'confidence': abs(correlation)
            }
    
    def clear_history(self) -> None:
        """Clear all metric history."""
        with self._mutex:
            for history in self._metrics_history.values():
                history.clear()
            self._timestamps.clear()


class AlertManager:
    """Manages performance alerts and notifications."""
    
    def __init__(self):
        self._thresholds: Dict[MetricType, MetricThreshold] = {}
        self._active_alerts: List[PerformanceAlert] = []
        self._alert_history: deque = deque(maxlen=1000)
        self._mutex = threading.Lock()
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize default threshold values."""
        default_thresholds = {
            MetricType.LAYOUT_TIME: MetricThreshold(
                MetricType.LAYOUT_TIME, 50.0, 100.0, 200.0, ">"
            ),
            MetricType.MEMORY_USAGE: MetricThreshold(
                MetricType.MEMORY_USAGE, 500.0, 1000.0, 2000.0, ">"
            ),
            MetricType.CPU_USAGE: MetricThreshold(
                MetricType.CPU_USAGE, 70.0, 85.0, 95.0, ">"
            ),
            MetricType.CACHE_HIT_RATIO: MetricThreshold(
                MetricType.CACHE_HIT_RATIO, 0.7, 0.5, 0.3, "<"
            ),
            MetricType.FRAME_RATE: MetricThreshold(
                MetricType.FRAME_RATE, 45.0, 30.0, 15.0, "<"
            )
        }
        
        self._thresholds.update(default_thresholds)
    
    def set_threshold(self, threshold: MetricThreshold) -> None:
        """Set or update a metric threshold."""
        with self._mutex:
            self._thresholds[threshold.metric_type] = threshold
    
    def check_metric(self, metric_type: MetricType, value: float) -> Optional[PerformanceAlert]:
        """Check metric against thresholds and generate alert if needed."""
        with self._mutex:
            if metric_type not in self._thresholds:
                return None
            
            threshold = self._thresholds[metric_type]
            if not threshold.enabled:
                return None
            
            alert_level = self._evaluate_threshold(value, threshold)
            if alert_level is None:
                # Check if we need to resolve an existing alert
                self._resolve_alerts(metric_type)
                return None
            
            # Create alert
            alert = PerformanceAlert(
                level=alert_level,
                metric_type=metric_type,
                message=self._generate_alert_message(metric_type, value, alert_level),
                value=value,
                threshold=self._get_threshold_for_level(threshold, alert_level),
                timestamp=datetime.now(),
                metadata={'threshold_config': threshold}
            )
            
            # Add to active alerts
            self._active_alerts.append(alert)
            self._alert_history.append(alert)
            
            return alert
    
    def _evaluate_threshold(self, value: float, threshold: MetricThreshold) -> Optional[AlertLevel]:
        """Evaluate value against threshold and return alert level."""
        op = threshold.comparison_operator
        
        def compare(val: float, thresh: float) -> bool:
            if op == ">":
                return val > thresh
            elif op == "<":
                return val < thresh
            elif op == ">=":
                return val >= thresh
            elif op == "<=":
                return val <= thresh
            return False
        
        if compare(value, threshold.emergency_threshold):
            return AlertLevel.EMERGENCY
        elif compare(value, threshold.critical_threshold):
            return AlertLevel.CRITICAL
        elif compare(value, threshold.warning_threshold):
            return AlertLevel.WARNING
        
        return None
    
    def _get_threshold_for_level(self, threshold: MetricThreshold, level: AlertLevel) -> float:
        """Get the threshold value for a specific alert level."""
        if level == AlertLevel.EMERGENCY:
            return threshold.emergency_threshold
        elif level == AlertLevel.CRITICAL:
            return threshold.critical_threshold
        elif level == AlertLevel.WARNING:
            return threshold.warning_threshold
        return 0.0
    
    def _generate_alert_message(self, metric_type: MetricType, value: float, level: AlertLevel) -> str:
        """Generate a human-readable alert message."""
        metric_name = metric_type.name.replace('_', ' ').title()
        level_name = level.name.lower()
        
        return f"{level_name.capitalize()} {metric_name}: {value:.2f}"
    
    def _resolve_alerts(self, metric_type: MetricType) -> None:
        """Resolve active alerts for a metric type when value returns to normal."""
        for alert in self._active_alerts:
            if alert.metric_type == metric_type and not alert.resolved:
                alert.resolved = True
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active (unresolved) alerts."""
        with self._mutex:
            return [alert for alert in self._active_alerts if not alert.resolved]
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._mutex:
            return [
                alert for alert in self._alert_history 
                if alert.timestamp >= cutoff_time
            ]
    
    def clear_resolved_alerts(self) -> int:
        """Clear resolved alerts and return count cleared."""
        with self._mutex:
            initial_count = len(self._active_alerts)
            self._active_alerts = [alert for alert in self._active_alerts if not alert.resolved]
            return initial_count - len(self._active_alerts)


class BottleneckDetector:
    """Detects performance bottlenecks in layout operations."""
    
    def __init__(self, metric_collector: MetricCollector):
        self._metric_collector = metric_collector
        self._bottleneck_patterns: Dict[str, Callable] = {}
        self._initialize_detection_patterns()
    
    def _initialize_detection_patterns(self) -> None:
        """Initialize bottleneck detection patterns."""
        self._bottleneck_patterns = {
            'slow_layout_calculation': self._detect_slow_layout,
            'memory_leak': self._detect_memory_leak,
            'cache_thrashing': self._detect_cache_thrashing,
            'cpu_spike': self._detect_cpu_spike,
            'widget_bloat': self._detect_widget_bloat
        }
    
    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect all types of bottlenecks."""
        bottlenecks = []
        
        for pattern_name, detector in self._bottleneck_patterns.items():
            try:
                result = detector()
                if result:
                    bottlenecks.append({
                        'type': pattern_name,
                        'severity': result.get('severity', 'medium'),
                        'description': result.get('description', ''),
                        'recommendations': result.get('recommendations', []),
                        'detected_at': datetime.now(),
                        'metrics': result.get('metrics', {})
                    })
            except Exception as e:
                logger.error(f"Error detecting {pattern_name}: {e}")
        
        return bottlenecks
    
    def _detect_slow_layout(self) -> Optional[Dict[str, Any]]:
        """Detect slow layout calculation patterns."""
        layout_times = self._metric_collector.get_recent_values(MetricType.LAYOUT_TIME, 30)
        
        if not layout_times or len(layout_times) < 10:
            return None
        
        avg_time = statistics.mean(layout_times)
        max_time = max(layout_times)
        
        if avg_time > 50 or max_time > 200:
            return {
                'severity': 'high' if avg_time > 100 else 'medium',
                'description': f'Layout calculations are slow (avg: {avg_time:.1f}ms, max: {max_time:.1f}ms)',
                'recommendations': [
                    'Enable layout caching',
                    'Reduce widget complexity',
                    'Use widget pooling',
                    'Consider lazy loading'
                ],
                'metrics': {
                    'average_time_ms': avg_time,
                    'max_time_ms': max_time,
                    'sample_count': len(layout_times)
                }
            }
        
        return None
    
    def _detect_memory_leak(self) -> Optional[Dict[str, Any]]:
        """Detect memory leak patterns."""
        memory_values = self._metric_collector.get_recent_values(MetricType.MEMORY_USAGE, 300)  # 5 minutes
        
        if len(memory_values) < 50:
            return None
        
        # Check for consistent upward trend
        trend_analysis = self._metric_collector.get_trend_analysis(MetricType.MEMORY_USAGE)
        
        if (trend_analysis.get('trend') == 'increasing' and 
            trend_analysis.get('confidence', 0) > 0.7):
            
            memory_growth = memory_values[-1] - memory_values[0]
            growth_rate = memory_growth / (len(memory_values) / 60)  # MB per minute
            
            if growth_rate > 1.0:  # Growing more than 1MB per minute
                return {
                    'severity': 'high' if growth_rate > 5.0 else 'medium',
                    'description': f'Memory usage increasing consistently ({growth_rate:.2f} MB/min)',
                    'recommendations': [
                        'Check for unreleased widget references',
                        'Clear layout caches periodically',
                        'Review widget lifecycle management',
                        'Use weak references where appropriate'
                    ],
                    'metrics': {
                        'growth_rate_mb_per_min': growth_rate,
                        'total_growth_mb': memory_growth,
                        'confidence': trend_analysis.get('confidence', 0)
                    }
                }
        
        return None
    
    def _detect_cache_thrashing(self) -> Optional[Dict[str, Any]]:
        """Detect cache thrashing patterns."""
        cache_ratios = self._metric_collector.get_recent_values(MetricType.CACHE_HIT_RATIO, 60)
        
        if not cache_ratios or len(cache_ratios) < 20:
            return None
        
        avg_ratio = statistics.mean(cache_ratios)
        std_dev = statistics.stdev(cache_ratios) if len(cache_ratios) > 1 else 0
        
        # Low hit ratio or high variance indicates thrashing
        if avg_ratio < 0.3 or std_dev > 0.2:
            return {
                'severity': 'medium',
                'description': f'Cache performance is poor (hit ratio: {avg_ratio:.2f}, variance: {std_dev:.2f})',
                'recommendations': [
                    'Increase cache size',
                    'Review cache key generation strategy',
                    'Check for excessive cache invalidation',
                    'Consider different caching strategy'
                ],
                'metrics': {
                    'average_hit_ratio': avg_ratio,
                    'variance': std_dev,
                    'sample_count': len(cache_ratios)
                }
            }
        
        return None
    
    def _detect_cpu_spike(self) -> Optional[Dict[str, Any]]:
        """Detect CPU usage spikes."""
        cpu_values = self._metric_collector.get_recent_values(MetricType.CPU_USAGE, 60)
        
        if not cpu_values or len(cpu_values) < 10:
            return None
        
        # Check for anomalies
        anomalies = self._metric_collector.detect_anomalies(MetricType.CPU_USAGE, z_threshold=2.5)
        
        if len(anomalies) > len(cpu_values) * 0.1:  # More than 10% anomalies
            avg_cpu = statistics.mean(cpu_values)
            max_cpu = max(cpu_values)
            
            return {
                'severity': 'high' if max_cpu > 90 else 'medium',
                'description': f'CPU usage spikes detected (avg: {avg_cpu:.1f}%, max: {max_cpu:.1f}%)',
                'recommendations': [
                    'Profile layout operations',
                    'Reduce animation complexity',
                    'Use background threads for heavy operations',
                    'Optimize widget rendering'
                ],
                'metrics': {
                    'average_cpu_percent': avg_cpu,
                    'max_cpu_percent': max_cpu,
                    'anomaly_count': len(anomalies),
                    'anomaly_ratio': len(anomalies) / len(cpu_values)
                }
            }
        
        return None
    
    def _detect_widget_bloat(self) -> Optional[Dict[str, Any]]:
        """Detect excessive widget creation."""
        widget_counts = self._metric_collector.get_recent_values(MetricType.WIDGET_COUNT, 60)
        
        if not widget_counts or len(widget_counts) < 10:
            return None
        
        current_count = widget_counts[-1]
        avg_count = statistics.mean(widget_counts)
        
        if current_count > 1000 or avg_count > 500:
            return {
                'severity': 'medium',
                'description': f'High widget count detected (current: {current_count}, avg: {avg_count:.0f})',
                'recommendations': [
                    'Use widget pooling',
                    'Implement virtual scrolling',
                    'Review widget hierarchy',
                    'Consider lazy widget creation'
                ],
                'metrics': {
                    'current_widget_count': current_count,
                    'average_widget_count': avg_count,
                    'max_widget_count': max(widget_counts)
                }
            }
        
        return None


class PerformanceMonitor(QObject):
    """Main performance monitoring system."""
    
    # Signals
    alert_generated = pyqtSignal(PerformanceAlert)
    bottleneck_detected = pyqtSignal(dict)
    metrics_collected = pyqtSignal(dict)
    report_generated = pyqtSignal(PerformanceReport)
    
    def __init__(
        self,
        profiler: PerformanceProfiler,
        config_manager: ConfigurationManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        self._profiler = profiler
        self._config_manager = config_manager
        
        # Core components
        self._metric_collector = MetricCollector()
        self._alert_manager = AlertManager()
        self._bottleneck_detector = BottleneckDetector(self._metric_collector)
        
        # Monitoring configuration
        self._monitoring_enabled = True
        self._collection_interval = 1000  # 1 second
        self._bottleneck_check_interval = 30000  # 30 seconds
        
        # Timers
        self._collection_timer = QTimer()
        self._collection_timer.timeout.connect(self._collect_metrics)
        
        self._bottleneck_timer = QTimer()
        self._bottleneck_timer.timeout.connect(self._check_bottlenecks)
        
        # Start monitoring
        self.start_monitoring()
        
        logger.debug("PerformanceMonitor initialized")
    
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring_enabled:
            self._collection_timer.start(self._collection_interval)
            self._bottleneck_timer.start(self._bottleneck_check_interval)
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._collection_timer.stop()
        self._bottleneck_timer.stop()
        logger.info("Performance monitoring stopped")
    
    def _collect_metrics(self) -> None:
        """Collect current performance metrics."""
        try:
            # Get memory usage
            memory_stats = self._profiler.get_memory_stats()
            if memory_stats:
                memory_mb = memory_stats.get('current_mb', 0)
                self._metric_collector.record_metric(MetricType.MEMORY_USAGE, memory_mb)
                
                # Check for alerts
                alert = self._alert_manager.check_metric(MetricType.MEMORY_USAGE, memory_mb)
                if alert:
                    self.alert_generated.emit(alert)
            
            # Get layout timing
            layout_stats = self._profiler.get_operation_stats('layout_calculation')
            if layout_stats and layout_stats.get('count', 0) > 0:
                avg_time = layout_stats.get('average_time_ms', 0)
                self._metric_collector.record_metric(MetricType.LAYOUT_TIME, avg_time)
                
                # Check for alerts
                alert = self._alert_manager.check_metric(MetricType.LAYOUT_TIME, avg_time)
                if alert:
                    self.alert_generated.emit(alert)
            
            # Emit collected metrics
            current_metrics = {
                'memory_mb': memory_mb if memory_stats else 0,
                'layout_time_ms': layout_stats.get('average_time_ms', 0) if layout_stats else 0,
                'timestamp': datetime.now()
            }
            self.metrics_collected.emit(current_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _check_bottlenecks(self) -> None:
        """Check for performance bottlenecks."""
        try:
            bottlenecks = self._bottleneck_detector.detect_bottlenecks()
            
            for bottleneck in bottlenecks:
                self.bottleneck_detected.emit(bottleneck)
                logger.warning(f"Bottleneck detected: {bottleneck['type']} - {bottleneck['description']}")
                
        except Exception as e:
            logger.error(f"Error checking bottlenecks: {e}")
    
    def generate_performance_report(self, duration_hours: int = 1) -> PerformanceReport:
        """Generate comprehensive performance report."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=duration_hours)
        
        # Collect metrics for all types
        detailed_metrics = {}
        summary = {}
        
        for metric_type in MetricType:
            values = self._metric_collector.get_recent_values(metric_type, duration_hours * 3600)
            if values:
                detailed_metrics[metric_type.name] = values
                stats = self._metric_collector.get_metric_statistics(metric_type)
                summary[metric_type.name] = stats
        
        # Get alerts from the period
        alerts = self._alert_manager.get_alert_history(duration_hours)
        
        # Detect bottlenecks
        bottlenecks = self._bottleneck_detector.detect_bottlenecks()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, alerts, bottlenecks)
        
        report = PerformanceReport(
            timestamp=end_time,
            duration_minutes=duration_hours * 60,
            summary=summary,
            detailed_metrics=detailed_metrics,
            alerts_generated=alerts,
            recommendations=recommendations,
            bottlenecks_detected=bottlenecks
        )
        
        self.report_generated.emit(report)
        return report
    
    def _generate_recommendations(
        self,
        summary: Dict[str, Any],
        alerts: List[PerformanceAlert],
        bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Analyze layout performance
        layout_stats = summary.get('LAYOUT_TIME', {})
        if layout_stats and layout_stats.get('mean', 0) > 50:
            recommendations.append("Consider enabling layout caching to improve calculation speed")
            recommendations.append("Review widget complexity and reduce unnecessary nesting")
        
        # Analyze memory usage
        memory_stats = summary.get('MEMORY_USAGE', {})
        if memory_stats and memory_stats.get('max', 0) > 1000:
            recommendations.append("Monitor for memory leaks and implement periodic cleanup")
            recommendations.append("Consider using widget pooling for frequently created widgets")
        
        # Analyze cache performance
        cache_stats = summary.get('CACHE_HIT_RATIO', {})
        if cache_stats and cache_stats.get('mean', 1) < 0.6:
            recommendations.append("Optimize cache strategy and increase cache size")
            recommendations.append("Review cache key generation for better hit rates")
        
        # Alert-based recommendations
        alert_types = {alert.metric_type for alert in alerts}
        if MetricType.CPU_USAGE in alert_types:
            recommendations.append("Profile CPU-intensive operations and optimize rendering")
        
        # Bottleneck-based recommendations
        for bottleneck in bottlenecks:
            recommendations.extend(bottleneck.get('recommendations', []))
        
        # Remove duplicates while preserving order
        unique_recommendations = []
        seen = set()
        for rec in recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)
        
        return unique_recommendations
    
    def set_monitoring_enabled(self, enabled: bool) -> None:
        """Enable or disable monitoring."""
        self._monitoring_enabled = enabled
        
        if enabled:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def set_collection_interval(self, interval_ms: int) -> None:
        """Set metrics collection interval."""
        self._collection_interval = max(100, interval_ms)  # Minimum 100ms
        
        if self._collection_timer.isActive():
            self._collection_timer.stop()
            self._collection_timer.start(self._collection_interval)
    
    def get_current_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        summary = {}
        
        for metric_type in MetricType:
            stats = self._metric_collector.get_metric_statistics(metric_type)
            if stats:
                summary[metric_type.name] = {
                    'current': self._metric_collector.get_recent_values(metric_type, 1)[-1:],
                    'average': stats.get('mean', 0),
                    'trend': self._metric_collector.get_trend_analysis(metric_type)
                }
        
        summary['active_alerts'] = len(self._alert_manager.get_active_alerts())
        summary['monitoring_enabled'] = self._monitoring_enabled
        
        return summary
    
    def clear_monitoring_data(self) -> None:
        """Clear all monitoring data."""
        self._metric_collector.clear_history()
        self._alert_manager.clear_resolved_alerts()
        logger.info("Monitoring data cleared")
    
    def export_monitoring_data(self, filepath: str) -> bool:
        """Export monitoring data to file."""
        try:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'metrics_summary': self.get_current_metrics_summary(),
                'active_alerts': [
                    {
                        'level': alert.level.name,
                        'metric_type': alert.metric_type.name,
                        'message': alert.message,
                        'value': alert.value,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in self._alert_manager.get_active_alerts()
                ],
                'recent_bottlenecks': self._bottleneck_detector.detect_bottlenecks()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Monitoring data exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting monitoring data: {e}")
            return False
    
    def get_alert_manager(self) -> AlertManager:
        """Get the alert manager for external configuration."""
        return self._alert_manager
    
    def get_metric_collector(self) -> MetricCollector:
        """Get the metric collector for external use."""
        return self._metric_collector