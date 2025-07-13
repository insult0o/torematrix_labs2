import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .event_types import Event

logger = logging.getLogger(__name__)

@dataclass
class EventMetrics:
    event_type: str
    count: int = 0
    total_processing_time: float = 0.0
    max_processing_time: float = 0.0
    error_count: int = 0
    last_occurrence: Optional[datetime] = None
    
    @property
    def average_processing_time(self) -> float:
        return self.total_processing_time / self.count if self.count > 0 else 0.0

@dataclass
class HandlerMetrics:
    handler_name: str
    success_count: int = 0
    error_count: int = 0
    total_execution_time: float = 0.0
    max_execution_time: float = 0.0
    
    @property
    def average_execution_time(self) -> float:
        total_count = self.success_count + self.error_count
        return self.total_execution_time / total_count if total_count > 0 else 0.0

@dataclass
class PerformanceSnapshot:
    timestamp: datetime = field(default_factory=datetime.now)
    events_processed: int = 0
    total_processing_time: float = 0.0
    error_count: int = 0
    queue_size: int = 0
    memory_usage_mb: float = 0.0

class PerformanceMonitor:
    def __init__(self):
        self.event_metrics: Dict[str, EventMetrics] = defaultdict(
            lambda: EventMetrics(event_type="unknown")
        )
        self.handler_metrics: Dict[str, HandlerMetrics] = defaultdict(
            lambda: HandlerMetrics(handler_name="unknown")
        )
        self.snapshots: List[PerformanceSnapshot] = []
        self._snapshot_interval = timedelta(minutes=1)
        self._last_snapshot = datetime.now()
        self._start_time = time.time()
    
    def record_event_processing(
        self,
        event: Event,
        processing_time: float,
        success: bool = True
    ) -> None:
        metrics = self.event_metrics[event.event_type]
        metrics.event_type = event.event_type
        metrics.count += 1
        metrics.total_processing_time += processing_time
        metrics.max_processing_time = max(metrics.max_processing_time, processing_time)
        if not success:
            metrics.error_count += 1
        metrics.last_occurrence = datetime.now()
    
    def record_handler_execution(
        self,
        handler_name: str,
        execution_time: float,
        success: bool = True
    ) -> None:
        metrics = self.handler_metrics[handler_name]
        metrics.handler_name = handler_name
        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
        metrics.total_execution_time += execution_time
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
    
    def get_event_metrics(self, event_type: Optional[str] = None) -> Dict[str, EventMetrics]:
        if event_type:
            return {event_type: self.event_metrics[event_type]}
        return dict(self.event_metrics)
    
    def get_handler_metrics(self, handler_name: Optional[str] = None) -> Dict[str, HandlerMetrics]:
        if handler_name:
            return {handler_name: self.handler_metrics[handler_name]}
        return dict(self.handler_metrics)
    
    def get_total_metrics(self) -> Dict[str, float]:
        total_events = sum(m.count for m in self.event_metrics.values())
        total_errors = sum(m.error_count for m in self.event_metrics.values())
        total_processing_time = sum(m.total_processing_time for m in self.event_metrics.values())
        
        return {
            "total_events": total_events,
            "total_errors": total_errors,
            "total_processing_time": total_processing_time,
            "events_per_second": total_events / (time.time() - self._start_time),
            "error_rate": (total_errors / total_events) if total_events > 0 else 0.0,
            "average_processing_time": (total_processing_time / total_events) if total_events > 0 else 0.0
        }
    
    async def start_snapshot_collection(
        self,
        event_queue: asyncio.Queue,
        interval_seconds: int = 60
    ) -> None:
        self._snapshot_interval = timedelta(seconds=interval_seconds)
        while True:
            await asyncio.sleep(interval_seconds)
            
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
            except ImportError:
                memory_mb = 0.0
                logger.warning("psutil not available for memory monitoring")
            
            snapshot = PerformanceSnapshot(
                events_processed=sum(m.count for m in self.event_metrics.values()),
                total_processing_time=sum(m.total_processing_time for m in self.event_metrics.values()),
                error_count=sum(m.error_count for m in self.event_metrics.values()),
                queue_size=event_queue.qsize(),
                memory_usage_mb=memory_mb
            )
            
            self.snapshots.append(snapshot)
            # Keep last hour of snapshots
            max_snapshots = 3600 // interval_seconds
            if len(self.snapshots) > max_snapshots:
                self.snapshots = self.snapshots[-max_snapshots:]
    
    def get_performance_trend(
        self,
        duration: timedelta = timedelta(minutes=5)
    ) -> List[PerformanceSnapshot]:
        cutoff = datetime.now() - duration
        return [s for s in self.snapshots if s.timestamp >= cutoff]