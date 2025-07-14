"""Comprehensive observability system for metadata extraction."""

from typing import Dict, List, Optional, Any, Callable
import asyncio
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider


@dataclass
class MetricData:
    """Container for metric data."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TraceData:
    """Container for trace data."""
    operation_name: str
    span_id: str
    trace_id: str
    duration_ms: float
    status: str
    attributes: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Prometheus metrics collector for metadata extraction."""
    
    def __init__(self):
        # Extraction metrics
        self.extraction_requests_total = Counter(
            'metadata_extraction_requests_total',
            'Total number of metadata extraction requests',
            ['document_type', 'user_id', 'status']
        )
        
        self.extraction_duration_seconds = Histogram(
            'metadata_extraction_duration_seconds',
            'Time spent on metadata extraction',
            ['operation', 'document_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        
        self.metadata_fields_extracted = Histogram(
            'metadata_fields_extracted_total',
            'Number of metadata fields extracted per document',
            ['document_type', 'extraction_type'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500]
        )
        
        self.relationships_detected = Histogram(
            'relationships_detected_total',
            'Number of relationships detected per document',
            ['relationship_type', 'confidence_range'],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250]
        )
        
        # Performance metrics
        self.cache_hits_total = Counter(
            'metadata_cache_hits_total',
            'Number of cache hits',
            ['cache_type', 'operation']
        )
        
        self.cache_misses_total = Counter(
            'metadata_cache_misses_total',
            'Number of cache misses',
            ['cache_type', 'operation']
        )
        
        # System metrics
        self.active_extractions = Gauge(
            'metadata_active_extractions',
            'Number of currently active extractions'
        )
        
        self.memory_usage_bytes = Gauge(
            'metadata_memory_usage_bytes',
            'Memory usage in bytes',
            ['component']
        )
        
        self.error_rate = Gauge(
            'metadata_error_rate',
            'Error rate percentage',
            ['error_type', 'component']
        )
        
    def record_extraction_request(
        self, 
        document_type: str, 
        user_id: str, 
        status: str
    ):
        """Record metadata extraction request."""
        self.extraction_requests_total.labels(
            document_type=document_type,
            user_id=user_id,
            status=status
        ).inc()
        
    def record_extraction_duration(
        self, 
        operation: str, 
        document_type: str, 
        duration_seconds: float
    ):
        """Record extraction operation duration."""
        self.extraction_duration_seconds.labels(
            operation=operation,
            document_type=document_type
        ).observe(duration_seconds)
        
    def record_metadata_fields(
        self, 
        document_type: str, 
        extraction_type: str, 
        field_count: int
    ):
        """Record number of metadata fields extracted."""
        self.metadata_fields_extracted.labels(
            document_type=document_type,
            extraction_type=extraction_type
        ).observe(field_count)
        
    def record_relationships(
        self, 
        relationship_type: str, 
        confidence_range: str, 
        count: int
    ):
        """Record number of relationships detected."""
        self.relationships_detected.labels(
            relationship_type=relationship_type,
            confidence_range=confidence_range
        ).observe(count)


class DistributedTracer:
    """Distributed tracing for metadata extraction operations."""
    
    def __init__(self):
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(__name__)
        self.active_spans: Dict[str, trace.Span] = {}
        
    def start_extraction_trace(
        self, 
        operation_name: str, 
        document_id: str,
        **attributes
    ) -> str:
        """Start a new extraction trace."""
        span = self.tracer.start_span(
            operation_name,
            attributes={
                "document_id": document_id,
                "service.name": "metadata-extraction",
                **attributes
            }
        )
        
        span_id = f"{document_id}_{operation_name}_{int(time.time() * 1000)}"
        self.active_spans[span_id] = span
        
        return span_id
        
    def add_span_event(
        self, 
        span_id: str, 
        event_name: str, 
        **attributes
    ):
        """Add event to active span."""
        if span_id in self.active_spans:
            self.active_spans[span_id].add_event(
                event_name,
                attributes=attributes
            )
            
    def finish_span(
        self, 
        span_id: str, 
        status: str = "ok",
        **attributes
    ):
        """Finish active span."""
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            
            if attributes:
                span.set_attributes(attributes)
                
            if status != "ok":
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                
            span.end()
            del self.active_spans[span_id]


class StructuredLogger:
    """Structured logging for metadata extraction operations."""
    
    def __init__(self, component_name: str):
        self.logger = logging.getLogger(f"metadata.{component_name}")
        self.component_name = component_name
        
        # Configure structured logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def log_extraction_started(
        self, 
        document_id: str, 
        user_id: str, 
        **context
    ):
        """Log extraction started event."""
        self.logger.info(
            "Metadata extraction started",
            extra={
                "event_type": "extraction_started",
                "document_id": document_id,
                "user_id": user_id,
                "component": self.component_name,
                **context
            }
        )
        
    def log_extraction_completed(
        self, 
        document_id: str, 
        duration_ms: float,
        stats: Dict[str, Any]
    ):
        """Log extraction completed event."""
        self.logger.info(
            "Metadata extraction completed",
            extra={
                "event_type": "extraction_completed",
                "document_id": document_id,
                "duration_ms": duration_ms,
                "component": self.component_name,
                "extraction_stats": stats
            }
        )
        
    def log_extraction_error(
        self, 
        document_id: str, 
        error: str,
        **context
    ):
        """Log extraction error event."""
        self.logger.error(
            f"Metadata extraction failed: {error}",
            extra={
                "event_type": "extraction_error",
                "document_id": document_id,
                "error": error,
                "component": self.component_name,
                **context
            }
        )


class MetadataObservabilitySystem:
    """Comprehensive observability system for metadata extraction."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = MetricsCollector()
        self.tracer = DistributedTracer()
        self.logger = StructuredLogger("observability")
        
        self._performance_data: List[MetricData] = []
        self._trace_data: List[TraceData] = []
        self._error_rates: Dict[str, float] = {}
        
    async def initialize(self):
        """Initialize observability system."""
        # Start Prometheus metrics server
        if self.config.get("prometheus_enabled", True):
            port = self.config.get("prometheus_port", 8000)
            start_http_server(port)
            self.logger.logger.info(f"Prometheus metrics server started on port {port}")
            
        # Initialize background monitoring tasks
        asyncio.create_task(self._collect_performance_metrics())
        asyncio.create_task(self._calculate_error_rates())
        
        self.logger.logger.info("Metadata observability system initialized")
        
    def track_extraction_metrics(
        self,
        operation: str,
        duration: float,
        success: bool,
        metadata_count: int,
        document_type: str = "unknown",
        user_id: str = "unknown"
    ):
        """Track metadata extraction metrics."""
        # Record metrics
        status = "success" if success else "error"
        self.metrics.record_extraction_request(document_type, user_id, status)
        self.metrics.record_extraction_duration(operation, document_type, duration)
        
        if success:
            self.metrics.record_metadata_fields(
                document_type, 
                operation, 
                metadata_count
            )
            
        # Store performance data
        self._performance_data.append(MetricData(
            name=f"extraction_{operation}",
            value=duration,
            labels={
                "operation": operation,
                "document_type": document_type,
                "status": status
            }
        ))
        
        # Limit stored data to prevent memory growth
        if len(self._performance_data) > 10000:
            self._performance_data = self._performance_data[-5000:]
            
    def track_relationship_metrics(
        self,
        relationship_type: str,
        confidence: float,
        count: int
    ):
        """Track relationship detection metrics."""
        confidence_range = self._get_confidence_range(confidence)
        self.metrics.record_relationships(relationship_type, confidence_range, count)
        
    def track_cache_metrics(
        self,
        cache_type: str,
        operation: str,
        hit: bool
    ):
        """Track cache hit/miss metrics."""
        if hit:
            self.metrics.cache_hits_total.labels(
                cache_type=cache_type,
                operation=operation
            ).inc()
        else:
            self.metrics.cache_misses_total.labels(
                cache_type=cache_type,
                operation=operation
            ).inc()
            
    def start_extraction_trace(
        self,
        operation: str,
        document_id: str,
        **attributes
    ) -> str:
        """Start distributed trace for extraction operation."""
        return self.tracer.start_extraction_trace(
            f"metadata_extraction_{operation}",
            document_id,
            **attributes
        )
        
    def finish_extraction_trace(
        self,
        span_id: str,
        success: bool,
        **attributes
    ):
        """Finish extraction trace."""
        status = "ok" if success else "error"
        self.tracer.finish_span(span_id, status, **attributes)
        
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard."""
        return {
            "total_extractions": len(self._performance_data),
            "average_duration": self._calculate_average_duration(),
            "success_rate": self._calculate_success_rate(),
            "error_rates": self._error_rates,
            "recent_performance": self._get_recent_performance_trends(),
            "active_extractions": self.metrics.active_extractions._value._value
        }
        
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics for system monitoring."""
        return {
            "system_healthy": self._is_system_healthy(),
            "error_rate": self._get_overall_error_rate(),
            "average_response_time": self._calculate_average_duration(),
            "active_connections": self._get_active_connections(),
            "memory_usage": self._get_memory_usage(),
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def _collect_performance_metrics(self):
        """Background task to collect performance metrics."""
        while True:
            try:
                # Update active extractions gauge
                active_count = self._count_active_extractions()
                self.metrics.active_extractions.set(active_count)
                
                # Update memory usage
                memory_usage = self._get_memory_usage()
                for component, usage in memory_usage.items():
                    self.metrics.memory_usage_bytes.labels(
                        component=component
                    ).set(usage)
                    
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.logger.log_extraction_error("system", f"Performance collection error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _calculate_error_rates(self):
        """Background task to calculate error rates."""
        while True:
            try:
                # Calculate error rates by component
                for component in ["extraction", "relationships", "storage"]:
                    error_rate = self._calculate_component_error_rate(component)
                    self._error_rates[component] = error_rate
                    
                    self.metrics.error_rate.labels(
                        error_type="general",
                        component=component
                    ).set(error_rate)
                    
                await asyncio.sleep(60)  # Calculate every minute
                
            except Exception as e:
                self.logger.logger.error(f"Error rate calculation failed: {e}")
                await asyncio.sleep(120)
                
    def _get_confidence_range(self, confidence: float) -> str:
        """Get confidence range label."""
        if confidence >= 0.9:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        elif confidence >= 0.5:
            return "low"
        else:
            return "very_low"
            
    def _calculate_average_duration(self) -> float:
        """Calculate average extraction duration."""
        if not self._performance_data:
            return 0.0
            
        recent_data = self._performance_data[-100:]  # Last 100 extractions
        total_duration = sum(metric.value for metric in recent_data)
        return total_duration / len(recent_data)
        
    def _calculate_success_rate(self) -> float:
        """Calculate extraction success rate."""
        if not self._performance_data:
            return 1.0
            
        recent_data = self._performance_data[-100:]
        successful = sum(
            1 for metric in recent_data 
            if metric.labels.get("status") == "success"
        )
        return successful / len(recent_data)
        
    def _get_recent_performance_trends(self) -> List[Dict[str, Any]]:
        """Get recent performance trends."""
        if len(self._performance_data) < 10:
            return []
            
        # Group by 5-minute intervals
        trends = []
        recent_data = self._performance_data[-50:]  # Last 50 data points
        
        for i in range(0, len(recent_data), 10):
            batch = recent_data[i:i+10]
            if batch:
                avg_duration = sum(m.value for m in batch) / len(batch)
                success_count = sum(
                    1 for m in batch 
                    if m.labels.get("status") == "success"
                )
                
                trends.append({
                    "timestamp": batch[-1].timestamp.isoformat(),
                    "avg_duration": avg_duration,
                    "success_rate": success_count / len(batch)
                })
                
        return trends
        
    def _is_system_healthy(self) -> bool:
        """Check if system is healthy based on metrics."""
        error_rate = self._get_overall_error_rate()
        avg_duration = self._calculate_average_duration()
        
        return (
            error_rate < 0.05 and  # Less than 5% error rate
            avg_duration < 30.0     # Less than 30 seconds average
        )
        
    def _get_overall_error_rate(self) -> float:
        """Get overall system error rate."""
        if not self._error_rates:
            return 0.0
        return sum(self._error_rates.values()) / len(self._error_rates)
        
    def _count_active_extractions(self) -> int:
        """Count currently active extractions."""
        # This would integrate with actual processing system
        return len(self.tracer.active_spans)
        
    def _get_active_connections(self) -> int:
        """Get number of active connections."""
        # This would integrate with WebSocket manager
        return 0
        
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage by component."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "total": memory_info.rss,
            "extraction_engine": memory_info.rss * 0.3,  # Estimated
            "relationship_engine": memory_info.rss * 0.2,
            "cache": memory_info.rss * 0.1
        }
        
    def _calculate_component_error_rate(self, component: str) -> float:
        """Calculate error rate for specific component."""
        # Filter performance data by component
        component_data = [
            metric for metric in self._performance_data
            if component in metric.name
        ]
        
        if not component_data:
            return 0.0
            
        recent_data = component_data[-50:]  # Last 50 for this component
        error_count = sum(
            1 for metric in recent_data
            if metric.labels.get("status") == "error"
        )
        
        return error_count / len(recent_data) if recent_data else 0.0