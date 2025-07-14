"""
Production monitoring and logging for selection tools.

This module provides comprehensive monitoring capabilities including
performance tracking, error reporting, usage analytics, and
health monitoring for production deployments.
"""

import logging
import psutil
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .base import SelectionTool, ToolState, SelectionResult
from .event_integration import ToolEvent, EventType


logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track."""
    COUNTER = "counter"          # Incrementing values
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Duration measurements


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class SystemHealth:
    """System health snapshot."""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    active_tools: int = 0
    selection_operations_per_second: float = 0.0
    error_rate: float = 0.0
    response_time_p95: float = 0.0
    
    def is_healthy(self) -> bool:
        """Check if system is in healthy state."""
        return (
            self.cpu_percent < 80.0 and
            self.memory_percent < 85.0 and
            self.error_rate < 0.05 and  # Less than 5% error rate
            self.response_time_p95 < 1000.0  # Less than 1 second P95
        )


@dataclass
class Alert:
    """System alert."""
    alert_id: str = field(default_factory=lambda: str(uuid4()))
    level: AlertLevel = AlertLevel.INFO
    title: str = ""
    message: str = ""
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    
    Thread-safe metrics collection with configurable retention
    and aggregation strategies.
    """
    
    def __init__(self, retention_hours: int = 24, max_points: int = 10000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self._retention_hours = retention_hours
        self._lock = threading.RLock()
        
        # Cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_old_metrics)
        self._cleanup_timer.start(3600000)  # Clean up every hour
        
        logger.debug("MetricsCollector initialized")
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        with self._lock:
            metric_key = f"{metric.name}:{':'.join(f'{k}={v}' for k, v in metric.tags.items())}"
            self._metrics[metric_key].append(metric)
    
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        metric = PerformanceMetric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            tags=tags or {},
            unit="ms"
        )
        self.record_metric(metric)
    
    def get_metrics(self, 
                   name_pattern: Optional[str] = None,
                   since: Optional[datetime] = None) -> Dict[str, List[PerformanceMetric]]:
        """Get metrics matching criteria."""
        with self._lock:
            result = {}
            
            for metric_key, metric_list in self._metrics.items():
                metric_name = metric_key.split(':')[0]
                
                if name_pattern and name_pattern not in metric_name:
                    continue
                
                filtered_metrics = []
                for metric in metric_list:
                    if since and metric.timestamp < since:
                        continue
                    filtered_metrics.append(metric)
                
                if filtered_metrics:
                    result[metric_key] = filtered_metrics
            
            return result
    
    def get_aggregated_metrics(self, 
                              name: str,
                              aggregation: str = "avg",
                              time_window_minutes: int = 5) -> Optional[float]:
        """Get aggregated metric value over time window."""
        since = datetime.now() - timedelta(minutes=time_window_minutes)
        metrics = self.get_metrics(name, since)
        
        if not metrics:
            return None
        
        all_values = []
        for metric_list in metrics.values():
            all_values.extend([m.value for m in metric_list])
        
        if not all_values:
            return None
        
        if aggregation == "avg":
            return sum(all_values) / len(all_values)
        elif aggregation == "sum":
            return sum(all_values)
        elif aggregation == "min":
            return min(all_values)
        elif aggregation == "max":
            return max(all_values)
        elif aggregation == "p95":
            sorted_values = sorted(all_values)
            idx = int(len(sorted_values) * 0.95)
            return sorted_values[min(idx, len(sorted_values) - 1)]
        else:
            return None
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)
        
        with self._lock:
            for metric_key, metric_list in self._metrics.items():
                # Remove old metrics
                while metric_list and metric_list[0].timestamp < cutoff_time:
                    metric_list.popleft()
        
        logger.debug("Cleaned up old metrics")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get metrics collection statistics."""
        with self._lock:
            total_metrics = sum(len(metric_list) for metric_list in self._metrics.values())
            metric_names = set(key.split(':')[0] for key in self._metrics.keys())
            
            return {
                'total_metrics': total_metrics,
                'unique_metric_names': len(metric_names),
                'metric_series': len(self._metrics),
                'retention_hours': self._retention_hours,
                'oldest_metric': min(
                    (metric_list[0].timestamp for metric_list in self._metrics.values() if metric_list),
                    default=None
                )
            }


class ToolMonitor(QObject):
    """
    Monitor for individual selection tools.
    
    Tracks tool-specific metrics, errors, and performance data.
    """
    
    # Signals
    metric_recorded = pyqtSignal(object)  # PerformanceMetric
    error_detected = pyqtSignal(str, str)  # tool_id, error_message
    performance_warning = pyqtSignal(str, str)  # tool_id, warning_message
    
    def __init__(self, tool: SelectionTool, metrics_collector: MetricsCollector):
        super().__init__()
        
        self._tool = tool
        self._metrics_collector = metrics_collector
        self._start_time = time.time()
        
        # Performance tracking
        self._operation_times: deque = deque(maxlen=1000)
        self._error_count = 0
        self._warning_count = 0
        self._selection_count = 0
        
        # Connect to tool signals
        self._connect_tool_signals()
        
        logger.debug(f"ToolMonitor initialized for {tool.tool_id}")
    
    def _connect_tool_signals(self) -> None:
        """Connect to tool signals for monitoring."""
        self._tool.selection_changed.connect(self._on_selection_changed)
        self._tool.state_changed.connect(self._on_state_changed)
        
        if hasattr(self._tool, 'error_occurred'):
            self._tool.error_occurred.connect(self._on_error_occurred)
    
    def _on_selection_changed(self, result: Optional[SelectionResult]) -> None:
        """Handle selection change events."""
        if result:
            self._selection_count += 1
            
            # Record selection metrics
            self._metrics_collector.record_counter(
                "tool.selections",
                tags={"tool_id": self._tool.tool_id, "tool_type": type(self._tool).__name__}
            )
            
            # Record element count
            element_count = len(result.elements) if result.elements else 0
            self._metrics_collector.record_gauge(
                "tool.selection.element_count",
                element_count,
                tags={"tool_id": self._tool.tool_id}
            )
    
    def _on_state_changed(self, state: ToolState) -> None:
        """Handle tool state changes."""
        self._metrics_collector.record_counter(
            "tool.state_changes",
            tags={"tool_id": self._tool.tool_id, "new_state": state.value}
        )
    
    def _on_error_occurred(self, error_message: str) -> None:
        """Handle tool errors."""
        self._error_count += 1
        
        self._metrics_collector.record_counter(
            "tool.errors",
            tags={"tool_id": self._tool.tool_id, "error_type": "tool_error"}
        )
        
        self.error_detected.emit(self._tool.tool_id, error_message)
        logger.error(f"Tool {self._tool.tool_id} error: {error_message}")
    
    def record_operation_time(self, operation: str, duration_ms: float) -> None:
        """Record operation timing."""
        self._operation_times.append(duration_ms)
        
        self._metrics_collector.record_timer(
            f"tool.operation.{operation}",
            duration_ms,
            tags={"tool_id": self._tool.tool_id}
        )
        
        # Check for performance warnings
        if duration_ms > 1000:  # Operations taking more than 1 second
            warning_msg = f"Slow operation {operation}: {duration_ms:.1f}ms"
            self.performance_warning.emit(self._tool.tool_id, warning_msg)
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tool statistics."""
        uptime = time.time() - self._start_time
        
        avg_operation_time = 0.0
        if self._operation_times:
            avg_operation_time = sum(self._operation_times) / len(self._operation_times)
        
        return {
            'tool_id': self._tool.tool_id,
            'tool_type': type(self._tool).__name__,
            'uptime_seconds': uptime,
            'selection_count': self._selection_count,
            'error_count': self._error_count,
            'warning_count': self._warning_count,
            'average_operation_time_ms': avg_operation_time,
            'current_state': self._tool.get_state().value if hasattr(self._tool, 'get_state') else "unknown"
        }


class SystemMonitor(QObject):
    """
    System-wide monitoring for selection tools.
    
    Provides health monitoring, alerting, and performance tracking
    for the entire selection tools system.
    """
    
    # Signals
    health_updated = pyqtSignal(object)  # SystemHealth
    alert_raised = pyqtSignal(object)   # Alert
    alert_resolved = pyqtSignal(str)    # alert_id
    
    def __init__(self, 
                 metrics_collector: MetricsCollector,
                 health_check_interval: int = 30,
                 alert_threshold_cpu: float = 80.0,
                 alert_threshold_memory: float = 85.0):
        super().__init__()
        
        self._metrics_collector = metrics_collector
        self._health_check_interval = health_check_interval
        self._alert_threshold_cpu = alert_threshold_cpu
        self._alert_threshold_memory = alert_threshold_memory
        
        # Tool monitors
        self._tool_monitors: Dict[str, ToolMonitor] = {}
        
        # Alert management
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        
        # Health monitoring
        self._current_health: Optional[SystemHealth] = None
        self._health_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        
        # Health check timer
        self._health_timer = QTimer()
        self._health_timer.timeout.connect(self._check_system_health)
        self._health_timer.start(health_check_interval * 1000)
        
        logger.info("SystemMonitor initialized")
    
    def register_tool(self, tool: SelectionTool) -> None:
        """Register a tool for monitoring."""
        if tool.tool_id not in self._tool_monitors:
            monitor = ToolMonitor(tool, self._metrics_collector)
            self._tool_monitors[tool.tool_id] = monitor
            
            # Connect to monitor signals
            monitor.error_detected.connect(self._handle_tool_error)
            monitor.performance_warning.connect(self._handle_performance_warning)
            
            logger.info(f"Registered tool for monitoring: {tool.tool_id}")
    
    def unregister_tool(self, tool_id: str) -> None:
        """Unregister a tool from monitoring."""
        if tool_id in self._tool_monitors:
            del self._tool_monitors[tool_id]
            logger.info(f"Unregistered tool from monitoring: {tool_id}")
    
    def _check_system_health(self) -> None:
        """Perform system health check."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Get tool metrics
            active_tools = len([m for m in self._tool_monitors.values()])
            
            # Calculate selection operations per second
            selection_rate = self._metrics_collector.get_aggregated_metrics(
                "tool.selections", "sum", 60
            ) or 0.0
            
            # Calculate error rate
            error_count = self._metrics_collector.get_aggregated_metrics(
                "tool.errors", "sum", 60
            ) or 0.0
            total_operations = selection_rate + error_count
            error_rate = error_count / total_operations if total_operations > 0 else 0.0
            
            # Calculate P95 response time
            response_time_p95 = self._metrics_collector.get_aggregated_metrics(
                "tool.operation", "p95", 60
            ) or 0.0
            
            # Create health snapshot
            health = SystemHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                active_tools=active_tools,
                selection_operations_per_second=selection_rate / 60,  # Per second
                error_rate=error_rate,
                response_time_p95=response_time_p95
            )
            
            self._current_health = health
            self._health_history.append(health)
            
            # Record system metrics
            self._record_system_metrics(health)
            
            # Check for alerts
            self._check_health_alerts(health)
            
            # Emit health update
            self.health_updated.emit(health)
            
        except Exception as e:
            logger.error(f"Failed to check system health: {e}")
    
    def _record_system_metrics(self, health: SystemHealth) -> None:
        """Record system metrics."""
        self._metrics_collector.record_gauge("system.cpu_percent", health.cpu_percent)
        self._metrics_collector.record_gauge("system.memory_percent", health.memory_percent)
        self._metrics_collector.record_gauge("system.memory_used_mb", health.memory_used_mb)
        self._metrics_collector.record_gauge("system.active_tools", health.active_tools)
        self._metrics_collector.record_gauge("system.selection_ops_per_second", health.selection_operations_per_second)
        self._metrics_collector.record_gauge("system.error_rate", health.error_rate)
        self._metrics_collector.record_gauge("system.response_time_p95", health.response_time_p95)
    
    def _check_health_alerts(self, health: SystemHealth) -> None:
        """Check for health-related alerts."""
        # CPU usage alert
        if health.cpu_percent > self._alert_threshold_cpu:
            self._raise_alert(
                AlertLevel.WARNING,
                "High CPU Usage",
                f"CPU usage is {health.cpu_percent:.1f}% (threshold: {self._alert_threshold_cpu}%)",
                "system.cpu",
                {"cpu_percent": health.cpu_percent}
            )
        else:
            self._resolve_alert("system.cpu")
        
        # Memory usage alert
        if health.memory_percent > self._alert_threshold_memory:
            self._raise_alert(
                AlertLevel.WARNING,
                "High Memory Usage",
                f"Memory usage is {health.memory_percent:.1f}% (threshold: {self._alert_threshold_memory}%)",
                "system.memory",
                {"memory_percent": health.memory_percent}
            )
        else:
            self._resolve_alert("system.memory")
        
        # High error rate alert
        if health.error_rate > 0.1:  # 10% error rate
            self._raise_alert(
                AlertLevel.ERROR,
                "High Error Rate",
                f"Error rate is {health.error_rate:.1%}",
                "system.error_rate",
                {"error_rate": health.error_rate}
            )
        else:
            self._resolve_alert("system.error_rate")
        
        # Slow response time alert
        if health.response_time_p95 > 2000:  # 2 seconds
            self._raise_alert(
                AlertLevel.WARNING,
                "Slow Response Time",
                f"P95 response time is {health.response_time_p95:.1f}ms",
                "system.response_time",
                {"response_time_p95": health.response_time_p95}
            )
        else:
            self._resolve_alert("system.response_time")
    
    def _raise_alert(self, 
                    level: AlertLevel,
                    title: str,
                    message: str,
                    source: str,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Raise a system alert."""
        # Check if alert already exists
        if source in self._active_alerts:
            return self._active_alerts[source].alert_id
        
        alert = Alert(
            level=level,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {}
        )
        
        self._active_alerts[source] = alert
        self._alert_history.append(alert)
        
        # Record alert metric
        self._metrics_collector.record_counter(
            "system.alerts",
            tags={"level": level.value, "source": source}
        )
        
        self.alert_raised.emit(alert)
        logger.warning(f"Alert raised: {title} - {message}")
        
        return alert.alert_id
    
    def _resolve_alert(self, source: str) -> bool:
        """Resolve an active alert."""
        if source in self._active_alerts:
            alert = self._active_alerts[source]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            
            del self._active_alerts[source]
            
            self.alert_resolved.emit(alert.alert_id)
            logger.info(f"Alert resolved: {alert.title}")
            
            return True
        
        return False
    
    def _handle_tool_error(self, tool_id: str, error_message: str) -> None:
        """Handle tool error notifications."""
        self._raise_alert(
            AlertLevel.ERROR,
            f"Tool Error: {tool_id}",
            error_message,
            f"tool.{tool_id}.error",
            {"tool_id": tool_id}
        )
    
    def _handle_performance_warning(self, tool_id: str, warning_message: str) -> None:
        """Handle tool performance warnings."""
        self._raise_alert(
            AlertLevel.WARNING,
            f"Performance Warning: {tool_id}",
            warning_message,
            f"tool.{tool_id}.performance",
            {"tool_id": tool_id}
        )
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health."""
        return self._current_health
    
    def get_health_history(self, 
                          hours: int = 1) -> List[SystemHealth]:
        """Get health history for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [h for h in self._health_history if h.timestamp >= cutoff_time]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, 
                         hours: int = 24,
                         level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get alert history."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        alerts = [a for a in self._alert_history if a.timestamp >= cutoff_time]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tool statistics."""
        stats = {}
        for tool_id, monitor in self._tool_monitors.items():
            stats[tool_id] = monitor.get_tool_statistics()
        return stats
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        metrics_stats = self._metrics_collector.get_statistics()
        
        return {
            'health': {
                'current': self._current_health.is_healthy() if self._current_health else False,
                'check_interval': self._health_check_interval,
                'history_size': len(self._health_history)
            },
            'alerts': {
                'active_count': len(self._active_alerts),
                'total_history': len(self._alert_history),
                'by_level': {
                    level.value: len([a for a in self._alert_history if a.level == level])
                    for level in AlertLevel
                }
            },
            'tools': {
                'monitored_count': len(self._tool_monitors),
                'active_count': len([m for m in self._tool_monitors.values()])
            },
            'metrics': metrics_stats
        }


class ProductionLogger:
    """
    Production logging configuration for selection tools.
    
    Provides structured logging with appropriate levels and formats
    for production environments.
    """
    
    @staticmethod
    def configure_production_logging(
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_structured: bool = True
    ) -> None:
        """Configure production logging."""
        # Create formatter
        if enable_structured:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        logging.getLogger('torematrix.ui.viewer.tools').setLevel(logging.INFO)
        
        logger.info("Production logging configured")
    
    @staticmethod
    def setup_error_reporting(
        error_handler: Optional[Callable[[Exception, Dict[str, Any]], None]] = None
    ) -> None:
        """Setup error reporting for production."""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            logger.critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
            if error_handler:
                try:
                    error_context = {
                        'exception_type': exc_type.__name__,
                        'exception_message': str(exc_value),
                        'timestamp': datetime.now().isoformat()
                    }
                    error_handler(exc_value, error_context)
                except Exception as e:
                    logger.error(f"Error in error handler: {e}")
        
        import sys
        sys.excepthook = handle_exception
        
        logger.info("Error reporting configured")