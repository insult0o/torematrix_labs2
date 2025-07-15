"""Real-Time Performance Monitoring System

Comprehensive monitoring system for search operations that provides:
- Real-time performance tracking and alerting
- Resource utilization monitoring
- Bottleneck detection and analysis  
- Health checks and system diagnostics
- Performance trend analysis
"""

import asyncio
import logging
import time
import psutil
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Union
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitoringMetric(Enum):
    """Types of metrics to monitor"""
    RESPONSE_TIME = "response_time"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    QUEUE_SIZE = "queue_size"
    ACTIVE_CONNECTIONS = "active_connections"


@dataclass
class MetricValue:
    """A single metric measurement"""
    metric: MonitoringMetric
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def __post_init__(self):
        if not self.unit:
            # Set default units based on metric type
            if self.metric == MonitoringMetric.RESPONSE_TIME:
                self.unit = "ms"
            elif self.metric in [MonitoringMetric.CACHE_HIT_RATIO, MonitoringMetric.ERROR_RATE]:
                self.unit = "%"
            elif self.metric in [MonitoringMetric.MEMORY_USAGE, MonitoringMetric.CPU_USAGE]:
                self.unit = "%"
            elif self.metric == MonitoringMetric.THROUGHPUT:
                self.unit = "ops/sec"


@dataclass
class PerformanceAlert:
    """Performance alert information"""
    alert_id: str
    level: AlertLevel
    metric: MonitoringMetric
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    check_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class SystemStats:
    """Current system statistics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_threads: int
    open_files: int
    network_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'active_threads': self.active_threads,
            'open_files': self.open_files,
            'network_connections': self.network_connections
        }


class MetricThreshold:
    """Threshold configuration for metrics"""
    
    def __init__(self,
                 metric: MonitoringMetric,
                 warning_threshold: float,
                 error_threshold: float,
                 critical_threshold: float,
                 comparison: str = "greater"):  # "greater", "less", "equal"
        self.metric = metric
        self.warning_threshold = warning_threshold
        self.error_threshold = error_threshold
        self.critical_threshold = critical_threshold
        self.comparison = comparison
    
    def evaluate(self, value: float) -> Optional[AlertLevel]:
        """Evaluate if value crosses threshold"""
        if self.comparison == "greater":
            if value >= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value >= self.error_threshold:
                return AlertLevel.ERROR
            elif value >= self.warning_threshold:
                return AlertLevel.WARNING
        elif self.comparison == "less":
            if value <= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value <= self.error_threshold:
                return AlertLevel.ERROR
            elif value <= self.warning_threshold:
                return AlertLevel.WARNING
        
        return None


class HealthCheck(ABC):
    """Abstract health check interface"""
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Health check name"""
        pass


class SearchHealthCheck(HealthCheck):
    """Health check for search functionality"""
    
    def __init__(self, search_engine):
        self.search_engine = search_engine
    
    @property
    def name(self) -> str:
        return "search_functionality"
    
    async def check_health(self) -> HealthCheckResult:
        """Check if search is working properly"""
        start_time = time.time()
        
        try:
            # Perform a simple test search
            test_query = {"query": "test", "limit": 1}
            result = await self.search_engine.search(test_query)
            
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # > 1 second is concerning
                return HealthCheckResult(
                    check_name=self.name,
                    status="degraded",
                    message=f"Search response slow: {execution_time:.2f}s",
                    timestamp=datetime.now(),
                    execution_time=execution_time
                )
            
            return HealthCheckResult(
                check_name=self.name,
                status="healthy",
                message="Search functioning normally",
                timestamp=datetime.now(),
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheckResult(
                check_name=self.name,
                status="unhealthy",
                message=f"Search failed: {str(e)}",
                timestamp=datetime.now(),
                execution_time=execution_time,
                details={'error': str(e)}
            )


class CacheHealthCheck(HealthCheck):
    """Health check for cache functionality"""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    @property
    def name(self) -> str:
        return "cache_functionality"
    
    async def check_health(self) -> HealthCheckResult:
        """Check cache health"""
        start_time = time.time()
        
        try:
            # Check cache statistics
            stats = self.cache_manager.get_statistics()
            hit_ratio = stats.get('hit_ratio', 0)
            
            execution_time = time.time() - start_time
            
            if hit_ratio < 50:  # < 50% hit ratio
                return HealthCheckResult(
                    check_name=self.name,
                    status="degraded",
                    message=f"Low cache hit ratio: {hit_ratio:.1f}%",
                    timestamp=datetime.now(),
                    execution_time=execution_time,
                    details=stats
                )
            
            return HealthCheckResult(
                check_name=self.name,
                status="healthy",
                message=f"Cache performing well: {hit_ratio:.1f}% hit ratio",
                timestamp=datetime.now(),
                execution_time=execution_time,
                details=stats
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return HealthCheckResult(
                check_name=self.name,
                status="unhealthy",
                message=f"Cache check failed: {str(e)}",
                timestamp=datetime.now(),
                execution_time=execution_time,
                details={'error': str(e)}
            )


class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self):
        # Configuration
        self.monitoring_interval = 5.0  # seconds
        self.metric_retention_hours = 24
        self.alert_retention_hours = 72
        self.enable_system_monitoring = True
        
        # State
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._system_monitoring_thread: Optional[threading.Thread] = None
        
        # Data storage
        self._metrics: Dict[MonitoringMetric, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._alerts: deque = deque(maxlen=1000)
        self._health_checks: Dict[str, HealthCheck] = {}
        self._health_results: Dict[str, HealthCheckResult] = {}
        
        # Thresholds
        self._thresholds: Dict[MonitoringMetric, MetricThreshold] = {}
        self._setup_default_thresholds()
        
        # Callbacks
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        self._metric_callbacks: List[Callable[[MetricValue], None]] = []
        
        # System stats
        self._current_system_stats: Optional[SystemStats] = None
        self._system_stats_history: deque = deque(maxlen=100)
        
        logger.info("PerformanceMonitor initialized")
    
    def _setup_default_thresholds(self) -> None:
        """Setup default monitoring thresholds"""
        self._thresholds = {
            MonitoringMetric.RESPONSE_TIME: MetricThreshold(
                MonitoringMetric.RESPONSE_TIME,
                warning_threshold=200,    # 200ms
                error_threshold=500,      # 500ms
                critical_threshold=1000,  # 1s
                comparison="greater"
            ),
            MonitoringMetric.CACHE_HIT_RATIO: MetricThreshold(
                MonitoringMetric.CACHE_HIT_RATIO,
                warning_threshold=70,     # 70%
                error_threshold=50,       # 50%
                critical_threshold=30,    # 30%
                comparison="less"
            ),
            MonitoringMetric.MEMORY_USAGE: MetricThreshold(
                MonitoringMetric.MEMORY_USAGE,
                warning_threshold=80,     # 80%
                error_threshold=90,       # 90%
                critical_threshold=95,    # 95%
                comparison="greater"
            ),
            MonitoringMetric.CPU_USAGE: MetricThreshold(
                MonitoringMetric.CPU_USAGE,
                warning_threshold=70,     # 70%
                error_threshold=85,       # 85%
                critical_threshold=95,    # 95%
                comparison="greater"
            ),
            MonitoringMetric.ERROR_RATE: MetricThreshold(
                MonitoringMetric.ERROR_RATE,
                warning_threshold=5,      # 5%
                error_threshold=10,       # 10%
                critical_threshold=20,    # 20%
                comparison="greater"
            )
        }
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._running:
            logger.warning("Monitoring already running")
            return
        
        self._running = True
        
        # Start main monitoring loop
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start system monitoring thread
        if self.enable_system_monitoring:
            self._system_monitoring_thread = threading.Thread(
                target=self._system_monitoring_loop,
                daemon=True
            )
            self._system_monitoring_thread.start()
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        # System monitoring thread will stop when _running becomes False
        
        logger.info("Performance monitoring stopped")
    
    def record_metric(self, metric: MonitoringMetric, value: float, 
                     tags: Dict[str, str] = None) -> None:
        """Record a metric value"""
        metric_value = MetricValue(
            metric=metric,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        # Store metric
        self._metrics[metric].append(metric_value)
        
        # Check thresholds
        self._check_threshold(metric_value)
        
        # Notify callbacks
        for callback in self._metric_callbacks:
            try:
                callback(metric_value)
            except Exception as e:
                logger.error(f"Error in metric callback: {e}")
    
    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a health check"""
        self._health_checks[health_check.name] = health_check
        logger.debug(f"Added health check: {health_check.name}")
    
    def remove_health_check(self, name: str) -> None:
        """Remove a health check"""
        if name in self._health_checks:
            del self._health_checks[name]
            if name in self._health_results:
                del self._health_results[name]
            logger.debug(f"Removed health check: {name}")
    
    def set_threshold(self, threshold: MetricThreshold) -> None:
        """Set threshold for a metric"""
        self._thresholds[threshold.metric] = threshold
        logger.debug(f"Set threshold for {threshold.metric.value}")
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add alert callback"""
        self._alert_callbacks.append(callback)
    
    def add_metric_callback(self, callback: Callable[[MetricValue], None]) -> None:
        """Add metric callback"""
        self._metric_callbacks.append(callback)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values"""
        current_metrics = {}
        
        for metric_type, metric_values in self._metrics.items():
            if metric_values:
                latest = metric_values[-1]
                current_metrics[metric_type.value] = {
                    'value': latest.value,
                    'timestamp': latest.timestamp,
                    'unit': latest.unit,
                    'tags': latest.tags
                }
        
        return current_metrics
    
    def get_metric_history(self, metric: MonitoringMetric, 
                          hours: int = 1) -> List[MetricValue]:
        """Get metric history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if metric not in self._metrics:
            return []
        
        return [
            mv for mv in self._metrics[metric]
            if mv.timestamp >= cutoff_time
        ]
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get currently active alerts"""
        return [alert for alert in self._alerts if not alert.resolved]
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self._alerts
            if alert.timestamp >= cutoff_time
        ]
    
    async def get_health_status(self) -> Dict[str, HealthCheckResult]:
        """Get current health status"""
        return self._health_results.copy()
    
    def get_system_stats(self) -> Optional[SystemStats]:
        """Get current system statistics"""
        return self._current_system_stats
    
    def get_system_stats_history(self, hours: int = 1) -> List[SystemStats]:
        """Get system statistics history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            stats for stats in self._system_stats_history
            if stats.timestamp >= cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        summary = {
            'timestamp': datetime.now(),
            'monitoring_status': 'active' if self._running else 'inactive',
            'active_alerts': len(self.get_active_alerts()),
            'health_checks': {}
        }
        
        # Add health check summary
        for name, result in self._health_results.items():
            summary['health_checks'][name] = result.status
        
        # Add key metrics
        current_metrics = self.get_current_metrics()
        summary['key_metrics'] = current_metrics
        
        # Add system stats
        if self._current_system_stats:
            summary['system'] = self._current_system_stats.to_dict()
        
        return summary
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                # Run health checks
                await self._run_health_checks()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _run_health_checks(self) -> None:
        """Run all registered health checks"""
        for name, health_check in self._health_checks.items():
            try:
                result = await health_check.check_health()
                self._health_results[name] = result
                
                # Generate alerts for unhealthy checks
                if result.status in ['degraded', 'unhealthy']:
                    level = AlertLevel.ERROR if result.status == 'unhealthy' else AlertLevel.WARNING
                    self._create_alert(
                        f"health_check_{name}",
                        level,
                        MonitoringMetric.RESPONSE_TIME,  # Generic metric
                        0,  # No specific value
                        0,  # No threshold
                        f"Health check {name}: {result.message}"
                    )
                
            except Exception as e:
                logger.error(f"Error running health check {name}: {e}")
    
    def _system_monitoring_loop(self) -> None:
        """System monitoring loop (runs in separate thread)"""
        while self._running:
            try:
                # Collect system stats
                stats = self._collect_system_stats()
                self._current_system_stats = stats
                self._system_stats_history.append(stats)
                
                # Record as metrics
                self.record_metric(MonitoringMetric.CPU_USAGE, stats.cpu_percent)
                self.record_metric(MonitoringMetric.MEMORY_USAGE, stats.memory_percent)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_stats(self) -> SystemStats:
        """Collect current system statistics"""
        try:
            process = psutil.Process()
            
            return SystemStats(
                timestamp=datetime.now(),
                cpu_percent=process.cpu_percent(),
                memory_percent=process.memory_percent(),
                disk_usage_percent=psutil.disk_usage('/').percent,
                active_threads=threading.active_count(),
                open_files=len(process.open_files()),
                network_connections=len(psutil.net_connections())
            )
        except Exception as e:
            logger.error(f"Error collecting system stats: {e}")
            return SystemStats(
                timestamp=datetime.now(),
                cpu_percent=0,
                memory_percent=0,
                disk_usage_percent=0,
                active_threads=0,
                open_files=0
            )
    
    def _check_threshold(self, metric_value: MetricValue) -> None:
        """Check if metric value crosses threshold"""
        if metric_value.metric not in self._thresholds:
            return
        
        threshold = self._thresholds[metric_value.metric]
        alert_level = threshold.evaluate(metric_value.value)
        
        if alert_level:
            self._create_alert(
                f"{metric_value.metric.value}_{int(time.time())}",
                alert_level,
                metric_value.metric,
                metric_value.value,
                self._get_threshold_value(threshold, alert_level),
                f"{metric_value.metric.value} threshold exceeded: {metric_value.value}{metric_value.unit}",
                tags=metric_value.tags
            )
    
    def _get_threshold_value(self, threshold: MetricThreshold, level: AlertLevel) -> float:
        """Get threshold value for alert level"""
        if level == AlertLevel.WARNING:
            return threshold.warning_threshold
        elif level == AlertLevel.ERROR:
            return threshold.error_threshold
        elif level == AlertLevel.CRITICAL:
            return threshold.critical_threshold
        return 0.0
    
    def _create_alert(self, alert_id: str, level: AlertLevel, metric: MonitoringMetric,
                     current_value: float, threshold_value: float, message: str,
                     tags: Dict[str, str] = None) -> None:
        """Create and store alert"""
        alert = PerformanceAlert(
            alert_id=alert_id,
            level=level,
            metric=metric,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        self._alerts.append(alert)
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.warning(f"Performance alert: {message}")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old metrics and alerts"""
        cutoff_time = datetime.now() - timedelta(hours=self.metric_retention_hours)
        alert_cutoff_time = datetime.now() - timedelta(hours=self.alert_retention_hours)
        
        # Clean metrics
        for metric_type in self._metrics:
            metric_values = self._metrics[metric_type]
            while metric_values and metric_values[0].timestamp < cutoff_time:
                metric_values.popleft()
        
        # Clean alerts
        while self._alerts and self._alerts[0].timestamp < alert_cutoff_time:
            self._alerts.popleft()
        
        # Clean system stats
        while (self._system_stats_history and 
               self._system_stats_history[0].timestamp < cutoff_time):
            self._system_stats_history.popleft()


# Factory functions
def create_performance_monitor() -> PerformanceMonitor:
    """Create performance monitor with default configuration"""
    return PerformanceMonitor()


def create_search_health_check(search_engine) -> SearchHealthCheck:
    """Create search health check"""
    return SearchHealthCheck(search_engine)


def create_cache_health_check(cache_manager) -> CacheHealthCheck:
    """Create cache health check"""
    return CacheHealthCheck(cache_manager)