"""Processor monitoring and metrics collection.

This module provides comprehensive monitoring capabilities for processors,
including performance metrics, health checks, and alerting.
"""

from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import logging
from dataclasses import dataclass, field

from .base import BaseProcessor, ProcessorMetadata, ProcessorContext, ProcessorResult, StageStatus
from .registry import ProcessorRegistry

logger = logging.getLogger(__name__)


@dataclass
class ProcessorMetrics:
    """Metrics for a single processor."""
    name: str
    total_processed: int = 0
    total_failed: int = 0
    total_duration: float = 0.0
    
    # Recent performance (sliding window)
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Resource usage
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.total_processed + self.total_failed
        return self.total_processed / total if total > 0 else 0.0
    
    @property
    def average_duration(self) -> float:
        return self.total_duration / self.total_processed if self.total_processed > 0 else 0.0
    
    @property
    def recent_average_duration(self) -> float:
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)
    
    def record_success(self, duration: float):
        """Record successful processing."""
        self.total_processed += 1
        self.total_duration += duration
        self.recent_durations.append(duration)
    
    def record_failure(self):
        """Record failed processing."""
        self.total_failed += 1
        self.recent_failures.append(datetime.utcnow())
    
    def get_failure_rate(self, minutes: int = 5) -> float:
        """Get failure rate over recent time period."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent = sum(1 for t in self.recent_failures if t > cutoff)
        return recent / minutes


class ProcessorMonitor:
    """
    Monitors processor performance and health.
    
    Collects metrics, tracks performance trends, and provides
    insights for optimization.
    """
    
    def __init__(self, registry: ProcessorRegistry):
        self.registry = registry
        self.metrics: Dict[str, ProcessorMetrics] = defaultdict(ProcessorMetrics)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Alerts
        self._alert_handlers: List[Callable] = []
        self._alert_thresholds = {
            "failure_rate": 0.1,  # 10% failure rate
            "average_duration": 60.0,  # 60 second average
            "memory_mb": 1024,  # 1GB memory
        }
    
    async def start(self):
        """Start monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        
        # Register hooks with registry
        self.registry.add_load_hook(self._on_processor_loaded)
        
        logger.info("Processor monitor started")
    
    async def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Processor monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect metrics from all processors
                for name in self.registry.list_processors():
                    try:
                        processor = await self.registry.get_processor(name)
                        metrics = processor.get_metrics()
                        
                        # Update our metrics
                        proc_metrics = self.metrics[name]
                        proc_metrics.name = name
                        
                        # Check for alerts
                        await self._check_alerts(name, proc_metrics)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring processor {name}: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(10)
    
    def _on_processor_loaded(self, name: str, processor_class: type):
        """Handle new processor loaded."""
        self.metrics[name] = ProcessorMetrics(name=name)
    
    def record_processing(
        self,
        processor_name: str,
        success: bool,
        duration: float,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None
    ):
        """Record processing metrics."""
        metrics = self.metrics[processor_name]
        
        if success:
            metrics.record_success(duration)
        else:
            metrics.record_failure()
        
        # Update resource usage
        if memory_mb and memory_mb > metrics.peak_memory_mb:
            metrics.peak_memory_mb = memory_mb
        
        if cpu_percent and cpu_percent > metrics.peak_cpu_percent:
            metrics.peak_cpu_percent = cpu_percent
    
    async def _check_alerts(self, processor_name: str, metrics: ProcessorMetrics):
        """Check if alerts should be triggered."""
        alerts = []
        
        # Check failure rate
        failure_rate = metrics.get_failure_rate()
        if failure_rate > self._alert_thresholds["failure_rate"]:
            alerts.append({
                "type": "high_failure_rate",
                "processor": processor_name,
                "value": failure_rate,
                "threshold": self._alert_thresholds["failure_rate"]
            })
        
        # Check average duration
        avg_duration = metrics.recent_average_duration
        if avg_duration > self._alert_thresholds["average_duration"]:
            alerts.append({
                "type": "slow_processing",
                "processor": processor_name,
                "value": avg_duration,
                "threshold": self._alert_thresholds["average_duration"]
            })
        
        # Check memory usage
        if metrics.peak_memory_mb > self._alert_thresholds["memory_mb"]:
            alerts.append({
                "type": "high_memory_usage",
                "processor": processor_name,
                "value": metrics.peak_memory_mb,
                "threshold": self._alert_thresholds["memory_mb"]
            })
        
        # Trigger alerts
        for alert in alerts:
            await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger an alert."""
        logger.warning(f"Alert: {alert}")
        
        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler."""
        self._alert_handlers.append(handler)
    
    def set_alert_threshold(self, alert_type: str, threshold: float):
        """Set alert threshold."""
        self._alert_thresholds[alert_type] = threshold
    
    def get_processor_metrics(self, processor_name: str) -> Optional[ProcessorMetrics]:
        """Get metrics for a specific processor."""
        return self.metrics.get(processor_name)
    
    def get_all_metrics(self) -> Dict[str, ProcessorMetrics]:
        """Get all processor metrics."""
        return dict(self.metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all processors."""
        total_processed = sum(m.total_processed for m in self.metrics.values())
        total_failed = sum(m.total_failed for m in self.metrics.values())
        
        return {
            "processor_count": len(self.metrics),
            "total_processed": total_processed,
            "total_failed": total_failed,
            "overall_success_rate": total_processed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0.0,
            "processors": {
                name: {
                    "processed": metrics.total_processed,
                    "failed": metrics.total_failed,
                    "success_rate": metrics.success_rate,
                    "avg_duration": metrics.average_duration,
                    "recent_avg_duration": metrics.recent_average_duration
                }
                for name, metrics in self.metrics.items()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        unhealthy_processors = []
        warnings = []
        
        for name, metrics in self.metrics.items():
            # Check for unhealthy processors
            if metrics.success_rate < 0.8:  # Less than 80% success rate
                unhealthy_processors.append({
                    "name": name,
                    "success_rate": metrics.success_rate,
                    "issue": "low_success_rate"
                })
            
            # Check for slow processors
            if metrics.recent_average_duration > 30:  # More than 30 seconds
                warnings.append({
                    "name": name,
                    "avg_duration": metrics.recent_average_duration,
                    "issue": "slow_processing"
                })
        
        return {
            "healthy": len(unhealthy_processors) == 0,
            "processor_count": len(self.metrics),
            "unhealthy_processors": unhealthy_processors,
            "warnings": warnings,
            "last_check": datetime.utcnow().isoformat()
        }


# Decorators for automatic monitoring
def monitor_processor(monitor: ProcessorMonitor):
    """Decorator to automatically monitor processor execution."""
    def decorator(processor_class: Type[BaseProcessor]):
        original_process = processor_class.process
        
        async def monitored_process(self, context: ProcessorContext) -> ProcessorResult:
            start_time = datetime.utcnow()
            success = False
            
            try:
                result = await original_process(self, context)
                success = result.status == StageStatus.COMPLETED
                return result
            finally:
                duration = (datetime.utcnow() - start_time).total_seconds()
                monitor.record_processing(
                    self.get_metadata().name,
                    success,
                    duration
                )
        
        processor_class.process = monitored_process
        return processor_class
    
    return decorator


class ProcessorProfiler:
    """
    Profiler for detailed processor performance analysis.
    
    Provides insights into processor bottlenecks and optimization opportunities.
    """
    
    def __init__(self):
        self._profiles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._active_profiles: Dict[str, datetime] = {}
    
    async def start_profiling(self, processor_name: str, context: ProcessorContext):
        """Start profiling a processor execution."""
        profile_id = f"{processor_name}_{datetime.utcnow().timestamp()}"
        self._active_profiles[profile_id] = datetime.utcnow()
        
        return profile_id
    
    async def end_profiling(
        self, 
        profile_id: str, 
        result: ProcessorResult,
        memory_usage: Optional[float] = None,
        cpu_usage: Optional[float] = None
    ):
        """End profiling and record results."""
        if profile_id not in self._active_profiles:
            return
        
        start_time = self._active_profiles[profile_id]
        end_time = datetime.utcnow()
        
        profile_data = {
            "profile_id": profile_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration": (end_time - start_time).total_seconds(),
            "status": result.status,
            "errors": result.errors,
            "memory_mb": memory_usage,
            "cpu_percent": cpu_usage,
            "result_size": len(str(result.extracted_data))
        }
        
        processor_name = profile_id.split("_")[0]
        self._profiles[processor_name].append(profile_data)
        
        # Keep only recent profiles (last 100)
        if len(self._profiles[processor_name]) > 100:
            self._profiles[processor_name] = self._profiles[processor_name][-100:]
        
        del self._active_profiles[profile_id]
    
    def get_performance_insights(self, processor_name: str) -> Dict[str, Any]:
        """Get performance insights for a processor."""
        profiles = self._profiles.get(processor_name, [])
        if not profiles:
            return {"message": "No profiling data available"}
        
        durations = [p["duration"] for p in profiles]
        memory_usage = [p["memory_mb"] for p in profiles if p["memory_mb"]]
        
        return {
            "total_executions": len(profiles),
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "average_memory_mb": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
            "success_rate": sum(1 for p in profiles if p["status"] == StageStatus.COMPLETED) / len(profiles),
            "recent_trends": {
                "last_10_avg_duration": sum(durations[-10:]) / min(10, len(durations)),
                "duration_trend": "improving" if len(durations) > 10 and sum(durations[-5:]) < sum(durations[-10:-5]) else "stable"
            }
        }