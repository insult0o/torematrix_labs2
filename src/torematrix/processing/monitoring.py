"""
Monitoring Service Module

Comprehensive monitoring for the processing system with Prometheus metrics,
health checks, and performance tracking.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass, field
from collections import defaultdict
import json
import time

# Prometheus metrics (optional dependency)
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Mock classes if prometheus_client not available
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def info(self, *args, **kwargs):
            pass
    
    Counter = Histogram = Gauge = Info = MockMetric
    PROMETHEUS_AVAILABLE = False

from ..core.events import EventBus, Event

logger = logging.getLogger(__name__)

# Prometheus metrics
TASK_COUNTER = Counter(
    'torematrix_tasks_total',
    'Total number of processing tasks',
    ['processor', 'status']
)

TASK_DURATION = Histogram(
    'torematrix_task_duration_seconds',
    'Task processing duration',
    ['processor'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0]
)

PIPELINE_DURATION = Histogram(
    'torematrix_pipeline_duration_seconds',
    'Pipeline execution duration',
    ['pipeline_name'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0]
)

ACTIVE_TASKS = Gauge(
    'torematrix_active_tasks',
    'Number of currently active tasks'
)

QUEUE_SIZE = Gauge(
    'torematrix_queue_size',
    'Current queue size',
    ['queue_type']
)

RESOURCE_USAGE = Gauge(
    'torematrix_resource_usage_percent',
    'Resource usage percentage',
    ['resource_type']
)

SYSTEM_INFO = Info(
    'torematrix_system',
    'System information'
)

PIPELINE_STATUS = Gauge(
    'torematrix_pipeline_status',
    'Pipeline status (1=running, 0=stopped)',
    ['pipeline_name', 'status']
)

ERROR_RATE = Gauge(
    'torematrix_error_rate',
    'Error rate over time window',
    ['component']
)

@dataclass
class MetricsSummary:
    """Summary of system metrics."""
    timestamp: datetime
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    average_task_duration: float
    active_pipelines: int
    resource_usage: Dict[str, float]
    queue_depths: Dict[str, int]
    error_rate: float
    throughput: float  # tasks per second

@dataclass
class Alert:
    """Alert definition."""
    id: str
    level: str  # info, warning, critical
    message: str
    component: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)

class MonitoringService:
    """
    Comprehensive monitoring for the processing system.
    
    Features:
    - Prometheus metrics collection
    - Real-time performance tracking
    - Health checks and alerts
    - Historical data analysis
    - Custom metric collection
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        components: Dict[str, Any],
        metrics_interval: float = 60.0,
        alert_handlers: Optional[List[Callable]] = None
    ):
        self.event_bus = event_bus
        self.components = components
        self.metrics_interval = metrics_interval
        self.alert_handlers = alert_handlers or []
        
        # Metrics storage
        self.metrics_history: List[MetricsSummary] = []
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.error_log: List[Dict[str, Any]] = []
        self.alerts: List[Alert] = []
        
        # Health checks
        self.health_checks: Dict[str, bool] = {}
        self.last_health_check: Optional[datetime] = None
        
        # Performance tracking
        self.performance_stats: Dict[str, List[float]] = defaultdict(list)
        
        # Custom metrics
        self.custom_metrics: Dict[str, Any] = {}
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start monitoring service."""
        if self._running:
            return
        
        self._running = True
        
        # Subscribe to events
        await self._subscribe_to_events()
        
        # Start monitoring tasks
        self._tasks = [
            asyncio.create_task(self._collect_metrics_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._alert_processor_loop())
        ]
        
        # Set system info
        if PROMETHEUS_AVAILABLE:
            SYSTEM_INFO.info({
                'version': '3.0.0',
                'environment': 'production',
                'monitoring_enabled': 'true',
                'prometheus_available': 'true'
            })
        
        logger.info("Monitoring service started")
        await self._emit_alert("info", "monitoring", "Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._emit_alert("info", "monitoring", "Monitoring service stopped")
        logger.info("Monitoring service stopped")
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        events_to_monitor = [
            "task_submitted",
            "task_started", 
            "task_completed",
            "task_failed",
            "pipeline_started",
            "pipeline_completed",
            "pipeline_failed",
            "worker_error",
            "resource_warning",
            "system_started"
        ]
        
        for event_type in events_to_monitor:
            await self.event_bus.subscribe(
                event_type,
                lambda e: asyncio.create_task(self._handle_event(e))
            )
    
    async def _handle_event(self, event: Event):
        """Handle monitoring events."""
        event_type = event.get("type", "unknown")
        event_data = event.get("data", {})
        
        async with self._lock:
            self.event_counts[event_type] += 1
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            if event_type == "task_completed":
                processor = event_data.get("processor", "unknown")
                TASK_COUNTER.labels(processor=processor, status="success").inc()
                
                duration = event_data.get("duration")
                if duration:
                    TASK_DURATION.labels(processor=processor).observe(duration)
            
            elif event_type == "task_failed":
                processor = event_data.get("processor", "unknown")
                TASK_COUNTER.labels(processor=processor, status="failure").inc()
                
                # Log error
                await self._log_error(event_type, event_data)
            
            elif event_type == "pipeline_started":
                pipeline_name = event_data.get("pipeline_name", "unknown")
                PIPELINE_STATUS.labels(
                    pipeline_name=pipeline_name, 
                    status="running"
                ).set(1)
            
            elif event_type == "pipeline_completed":
                pipeline_name = event_data.get("pipeline_name", "unknown")
                duration = event_data.get("duration", 0)
                
                PIPELINE_STATUS.labels(
                    pipeline_name=pipeline_name, 
                    status="running"
                ).set(0)
                PIPELINE_STATUS.labels(
                    pipeline_name=pipeline_name, 
                    status="completed"
                ).set(1)
                
                if duration:
                    PIPELINE_DURATION.labels(pipeline_name=pipeline_name).observe(duration)
            
            elif event_type == "resource_warning":
                await self._emit_alert("warning", "resources", str(event_data))
                logger.warning(f"Resource warning: {event_data}")
    
    async def _log_error(self, event_type: str, event_data: Dict[str, Any]):
        """Log error for analysis."""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": event_data
        }
        
        async with self._lock:
            self.error_log.append(error_entry)
            
            # Limit error log size
            if len(self.error_log) > 1000:
                self.error_log = self.error_log[-1000:]
    
    async def _collect_metrics_loop(self):
        """Periodically collect system metrics."""
        while self._running:
            try:
                metrics = await self._collect_metrics()
                
                async with self._lock:
                    self.metrics_history.append(metrics)
                    
                    # Update Prometheus gauges
                    if PROMETHEUS_AVAILABLE:
                        ACTIVE_TASKS.set(metrics.active_pipelines)
                        
                        for resource, usage in metrics.resource_usage.items():
                            RESOURCE_USAGE.labels(resource_type=resource).set(usage)
                        
                        for queue, depth in metrics.queue_depths.items():
                            QUEUE_SIZE.labels(queue_type=queue).set(depth)
                        
                        ERROR_RATE.labels(component="overall").set(metrics.error_rate)
                
                # Limit history size (24 hours at 1min intervals)
                if len(self.metrics_history) > 1440:
                    self.metrics_history.pop(0)
                
                # Check for performance alerts
                await self._check_performance_alerts(metrics)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await self._emit_alert("warning", "monitoring", f"Metrics collection failed: {e}")
            
            await asyncio.sleep(self.metrics_interval)
    
    async def _collect_metrics(self) -> MetricsSummary:
        """Collect current system metrics."""
        # Get component stats
        worker_stats = {}
        pipeline_stats = {}
        resource_stats = {}
        
        try:
            if "workers" in self.components:
                worker_stats = await self._safe_get_stats(self.components["workers"])
            
            if "pipeline" in self.components:
                pipeline_stats = await self._safe_get_stats(self.components["pipeline"])
            
            if "resources" in self.components:
                resource_stats = self.components["resources"].get_current_usage()
        except Exception as e:
            logger.error(f"Error collecting component stats: {e}")
        
        # Calculate metrics
        total_tasks = worker_stats.get('completed_tasks', 0) + worker_stats.get('failed_tasks', 0)
        successful_tasks = worker_stats.get('completed_tasks', 0)
        failed_tasks = worker_stats.get('failed_tasks', 0)
        
        # Calculate rates
        error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Calculate throughput (tasks per second over last interval)
        throughput = 0.0
        if self.metrics_history:
            last_metrics = self.metrics_history[-1]
            time_delta = (datetime.utcnow() - last_metrics.timestamp).total_seconds()
            task_delta = total_tasks - last_metrics.total_tasks
            throughput = task_delta / time_delta if time_delta > 0 else 0.0
        
        return MetricsSummary(
            timestamp=datetime.utcnow(),
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            average_task_duration=worker_stats.get('average_processing_time', 0.0),
            active_pipelines=pipeline_stats.get('active_pipelines', 0),
            resource_usage=resource_stats,
            queue_depths={
                'regular': worker_stats.get('queued_tasks', 0),
                'priority': worker_stats.get('priority_queued_tasks', 0)
            },
            error_rate=error_rate,
            throughput=throughput
        )
    
    async def _safe_get_stats(self, component: Any) -> Dict[str, Any]:
        """Safely get stats from a component."""
        try:
            if hasattr(component, 'get_stats'):
                stats = component.get_stats()
                return stats if isinstance(stats, dict) else {}
            return {}
        except Exception as e:
            logger.error(f"Error getting stats from component: {e}")
            return {}
    
    async def _health_check_loop(self):
        """Perform periodic health checks."""
        while self._running:
            try:
                health_status = await self._perform_health_checks()
                
                async with self._lock:
                    self.health_checks = health_status
                    self.last_health_check = datetime.utcnow()
                
                # Emit health status
                await self.event_bus.emit({
                    "type": "health_check",
                    "data": health_status
                })
                
                # Check for health alerts
                if not health_status.get('overall', False):
                    await self._emit_alert(
                        "critical", 
                        "health", 
                        "System health check failed",
                        health_status
                    )
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await self._emit_alert("warning", "health", f"Health check failed: {e}")
            
            await asyncio.sleep(30.0)  # Check every 30 seconds
    
    async def _perform_health_checks(self) -> Dict[str, bool]:
        """Perform health checks on all components."""
        checks = {}
        
        # Check worker pool
        if "workers" in self.components:
            worker_stats = await self._safe_get_stats(self.components["workers"])
            checks['workers'] = worker_stats.get('active_workers', 0) > 0
        
        # Check resource usage
        if "resources" in self.components:
            resource_stats = self.components["resources"].get_current_usage()
            checks['resources'] = all(
                usage < 90.0 for usage in resource_stats.values()
            )
        
        # Check event bus
        checks['event_bus'] = hasattr(self.event_bus, 'is_healthy') and self.event_bus.is_healthy()
        
        # Check pipeline manager
        if "pipeline" in self.components:
            pipeline = self.components["pipeline"]
            if hasattr(pipeline, 'status'):
                checks['pipeline_manager'] = pipeline.status.value != "failed"
            else:
                checks['pipeline_manager'] = True
        
        # Overall health
        checks['overall'] = all(checks.values())
        
        return checks
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old data."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                async with self._lock:
                    now = datetime.utcnow()
                    
                    # Clean old alerts (keep 24 hours)
                    cutoff = now - timedelta(hours=24)
                    self.alerts = [
                        alert for alert in self.alerts 
                        if alert.timestamp > cutoff
                    ]
                    
                    # Clean old error logs (keep 24 hours)
                    self.error_log = [
                        error for error in self.error_log
                        if datetime.fromisoformat(error["timestamp"]) > cutoff
                    ]
                    
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _alert_processor_loop(self):
        """Process and dispatch alerts."""
        while self._running:
            try:
                # Process any pending alerts
                alerts_to_process = []
                
                async with self._lock:
                    # Get unprocessed alerts
                    alerts_to_process = [
                        alert for alert in self.alerts
                        if not alert.data.get("processed", False)
                    ]
                
                for alert in alerts_to_process:
                    for handler in self.alert_handlers:
                        try:
                            await handler(alert)
                        except Exception as e:
                            logger.error(f"Alert handler failed: {e}")
                    
                    # Mark as processed
                    alert.data["processed"] = True
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
    
    async def _check_performance_alerts(self, metrics: MetricsSummary):
        """Check for performance-related alerts."""
        # High error rate alert
        if metrics.error_rate > 0.1:  # 10% error rate
            await self._emit_alert(
                "warning", 
                "performance", 
                f"High error rate: {metrics.error_rate:.2%}",
                {"error_rate": metrics.error_rate}
            )
        
        # Low throughput alert
        if metrics.throughput < 0.1 and metrics.total_tasks > 0:  # Less than 0.1 tasks/sec
            await self._emit_alert(
                "warning",
                "performance", 
                f"Low throughput: {metrics.throughput:.2f} tasks/sec",
                {"throughput": metrics.throughput}
            )
        
        # High resource usage alerts
        for resource, usage in metrics.resource_usage.items():
            if usage > 90.0:
                await self._emit_alert(
                    "critical",
                    "resources",
                    f"High {resource} usage: {usage:.1f}%",
                    {"resource": resource, "usage": usage}
                )
    
    async def _emit_alert(
        self, 
        level: str, 
        component: str, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ):
        """Emit an alert."""
        alert = Alert(
            id=f"{component}_{int(time.time())}",
            level=level,
            message=message,
            component=component,
            timestamp=datetime.utcnow(),
            data=data or {}
        )
        
        async with self._lock:
            self.alerts.append(alert)
        
        # Emit event
        await self.event_bus.emit({
            "type": "alert",
            "data": {
                "level": level,
                "component": component,
                "message": message,
                "timestamp": alert.timestamp.isoformat()
            }
        })
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            "status": "healthy" if self.health_checks.get('overall', False) else "unhealthy",
            "checks": self.health_checks,
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "monitoring_enabled": self._running
        }
    
    async def get_metrics_summary(
        self,
        duration: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get metrics summary for the specified duration."""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        # Filter by duration if specified
        if duration:
            cutoff = datetime.utcnow() - duration
            relevant_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff
            ]
        else:
            relevant_metrics = self.metrics_history
        
        if not relevant_metrics:
            return {"error": "No metrics in specified timeframe"}
        
        # Calculate aggregates
        latest = relevant_metrics[-1]
        
        return {
            "period": {
                "start": relevant_metrics[0].timestamp.isoformat(),
                "end": latest.timestamp.isoformat(),
                "duration_minutes": len(relevant_metrics)
            },
            "tasks": {
                "total": latest.total_tasks,
                "successful": latest.successful_tasks,
                "failed": latest.failed_tasks,
                "error_rate": latest.error_rate,
                "throughput": latest.throughput
            },
            "performance": {
                "average_duration": latest.average_task_duration,
                "active_pipelines": latest.active_pipelines
            },
            "resources": latest.resource_usage,
            "queues": latest.queue_depths,
            "health": self.get_health_status(),
            "alerts": {
                "total": len(self.alerts),
                "critical": len([a for a in self.alerts if a.level == "critical"]),
                "warnings": len([a for a in self.alerts if a.level == "warning"])
            }
        }
    
    def get_alerts(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by level."""
        alerts = self.alerts
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return [
            {
                "id": alert.id,
                "level": alert.level,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat(),
                "data": alert.data
            }
            for alert in alerts
        ]
    
    def add_alert_handler(self, handler: Callable):
        """Add custom alert handler."""
        self.alert_handlers.append(handler)
    
    def set_custom_metric(self, name: str, value: Any):
        """Set custom metric value."""
        self.custom_metrics[name] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_custom_metrics(self) -> Dict[str, Any]:
        """Get all custom metrics."""
        return self.custom_metrics.copy()

# Utility functions for metrics export

def export_prometheus_metrics() -> str:
    """Export Prometheus metrics in text format."""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus not available\n"
    
    from prometheus_client import generate_latest
    return generate_latest(REGISTRY).decode('utf-8')

async def create_monitoring_dashboard_data(
    monitoring_service: MonitoringService
) -> Dict[str, Any]:
    """Create data for monitoring dashboard."""
    metrics = await monitoring_service.get_metrics_summary()
    health = monitoring_service.get_health_status()
    alerts = monitoring_service.get_alerts()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "status": health["status"],
        "metrics": metrics,
        "health": health,
        "alerts": alerts,
        "custom_metrics": monitoring_service.get_custom_metrics()
    }