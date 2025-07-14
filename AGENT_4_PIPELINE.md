# Agent 4 Instructions: Integration, Monitoring & Testing

## Overview
You are Agent 4 working on Issue #8.4 (Integration, Monitoring & Testing) as part of the Processing Pipeline Architecture. Your focus is integrating all pipeline components, implementing comprehensive monitoring, and creating a robust testing framework.

## Context
- Part of Issue #8: Processing Pipeline Architecture (V3 greenfield project)
- You're working alongside 3 other agents in parallel
- You integrate components from Agents 1-3 into a cohesive system
- Must provide production-ready monitoring and observability

## Your Specific Tasks

### 1. Pipeline Integration (`src/torematrix/processing/integration.py`)

```python
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
import logging
from pathlib import Path

from .pipeline.manager import PipelineManager, PipelineConfig
from .processors.registry import ProcessorRegistry
from .workers.pool import WorkerPool, WorkerConfig
from .workers.progress import ProgressTracker
from .workers.resources import ResourceMonitor, ResourceLimits
from ..core.events import EventBus
from ..core.state import StateStore
from ..integrations.unstructured import UnstructuredProcessor

logger = logging.getLogger(__name__)

@dataclass
class ProcessingSystemConfig:
    """Configuration for the entire processing system."""
    pipeline_config: PipelineConfig
    worker_config: WorkerConfig
    resource_limits: ResourceLimits
    monitoring_enabled: bool = True
    state_persistence_enabled: bool = True
    state_store_path: Optional[Path] = None

class ProcessingSystem:
    """
    Main integration point for the document processing pipeline.
    
    Coordinates all components and provides a unified interface.
    """
    
    def __init__(self, config: ProcessingSystemConfig):
        self.config = config
        
        # Core components
        self.event_bus = EventBus()
        self.state_store = StateStore(
            persistence_enabled=config.state_persistence_enabled,
            storage_path=config.state_store_path
        )
        
        # Resource management
        self.resource_monitor = ResourceMonitor(
            limits=config.resource_limits
        )
        
        # Processing components
        self.processor_registry = ProcessorRegistry()
        self.progress_tracker = ProgressTracker(self.event_bus)
        
        self.worker_pool = WorkerPool(
            config=config.worker_config,
            event_bus=self.event_bus,
            resource_monitor=self.resource_monitor
        )
        
        self.pipeline_manager = PipelineManager(
            config=config.pipeline_config,
            event_bus=self.event_bus,
            state_store=self.state_store,
            resource_monitor=self.resource_monitor
        )
        
        # Monitoring
        self.monitoring = None
        if config.monitoring_enabled:
            from .monitoring import MonitoringService
            self.monitoring = MonitoringService(
                event_bus=self.event_bus,
                components={
                    "pipeline": self.pipeline_manager,
                    "workers": self.worker_pool,
                    "resources": self.resource_monitor,
                    "progress": self.progress_tracker
                }
            )
        
        self._running = False
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing processing system...")
        
        # Register built-in processors
        await self._register_processors()
        
        # Start core services
        await self.resource_monitor.start()
        await self.worker_pool.start()
        
        if self.monitoring:
            await self.monitoring.start()
        
        # Load persisted state
        if self.config.state_persistence_enabled:
            await self.state_store.load()
        
        self._running = True
        logger.info("Processing system initialized successfully")
    
    async def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("Shutting down processing system...")
        
        self._running = False
        
        # Stop accepting new work
        await self.pipeline_manager.pause_all()
        
        # Wait for active tasks to complete
        await self.worker_pool.wait_for_completion(timeout=60.0)
        
        # Shutdown components in order
        await self.worker_pool.stop()
        await self.resource_monitor.stop()
        
        if self.monitoring:
            await self.monitoring.stop()
        
        # Persist state
        if self.config.state_persistence_enabled:
            await self.state_store.save()
        
        logger.info("Processing system shutdown complete")
    
    async def process_document(
        self,
        document_path: Path,
        pipeline_name: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a document through the pipeline.
        
        Returns pipeline execution ID.
        """
        if not self._running:
            raise RuntimeError("Processing system not initialized")
        
        # Create pipeline context
        pipeline_id = await self.pipeline_manager.create_pipeline(
            pipeline_name=pipeline_name,
            document_path=document_path,
            metadata=metadata or {}
        )
        
        # Execute pipeline
        await self.pipeline_manager.execute(pipeline_id)
        
        return pipeline_id
    
    async def _register_processors(self):
        """Register all available processors."""
        # Unstructured.io processor
        unstructured_processor = UnstructuredProcessor()
        await self.processor_registry.register(
            "unstructured",
            unstructured_processor
        )
        
        # Register other built-in processors
        # ... add more as implemented
        
        logger.info(f"Registered {len(self.processor_registry)} processors")
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get current status of a pipeline execution."""
        return self.pipeline_manager.get_status(pipeline_id)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        return {
            "workers": self.worker_pool.get_stats(),
            "resources": self.resource_monitor.get_current_usage(),
            "pipelines": self.pipeline_manager.get_stats(),
            "processors": self.processor_registry.get_stats()
        }
```

### 2. Monitoring Service (`src/torematrix/processing/monitoring.py`)

```python
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass, field
from collections import defaultdict
import json

from prometheus_client import Counter, Histogram, Gauge, Info
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
    ['processor']
)

PIPELINE_DURATION = Histogram(
    'torematrix_pipeline_duration_seconds',
    'Pipeline execution duration',
    ['pipeline_name']
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

class MonitoringService:
    """
    Comprehensive monitoring for the processing system.
    
    Collects metrics, tracks performance, and provides observability.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        components: Dict[str, Any],
        metrics_interval: float = 60.0
    ):
        self.event_bus = event_bus
        self.components = components
        self.metrics_interval = metrics_interval
        
        # Metrics storage
        self.metrics_history: List[MetricsSummary] = []
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.error_log: List[Dict[str, Any]] = []
        
        # Health checks
        self.health_checks: Dict[str, bool] = {}
        self.last_health_check: Optional[datetime] = None
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
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
            asyncio.create_task(self._cleanup_loop())
        ]
        
        # Set system info
        SYSTEM_INFO.info({
            'version': '3.0.0',
            'environment': 'production',
            'processors': str(len(self.components['pipeline'].processor_registry))
        })
        
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
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
            "worker_error",
            "resource_warning"
        ]
        
        for event_type in events_to_monitor:
            await self.event_bus.subscribe(
                event_type,
                lambda e: asyncio.create_task(self._handle_event(e))
            )
    
    async def _handle_event(self, event: Event):
        """Handle monitoring events."""
        self.event_counts[event.type] += 1
        
        # Update Prometheus metrics
        if event.type == "task_completed":
            processor = event.data.get("processor", "unknown")
            TASK_COUNTER.labels(processor=processor, status="success").inc()
            
            duration = event.data.get("duration")
            if duration:
                TASK_DURATION.labels(processor=processor).observe(duration)
        
        elif event.type == "task_failed":
            processor = event.data.get("processor", "unknown")
            TASK_COUNTER.labels(processor=processor, status="failure").inc()
            
            # Log error
            self.error_log.append({
                "timestamp": datetime.utcnow(),
                "event": event.type,
                "data": event.data
            })
        
        elif event.type == "resource_warning":
            logger.warning(f"Resource warning: {event.data}")
    
    async def _collect_metrics_loop(self):
        """Periodically collect system metrics."""
        while self._running:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Update Prometheus gauges
                ACTIVE_TASKS.set(metrics.active_pipelines)
                
                for resource, usage in metrics.resource_usage.items():
                    RESOURCE_USAGE.labels(resource_type=resource).set(usage)
                
                for queue, depth in metrics.queue_depths.items():
                    QUEUE_SIZE.labels(queue_type=queue).set(depth)
                
                # Limit history size
                if len(self.metrics_history) > 1440:  # 24 hours at 1min intervals
                    self.metrics_history.pop(0)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            
            await asyncio.sleep(self.metrics_interval)
    
    async def _collect_metrics(self) -> MetricsSummary:
        """Collect current system metrics."""
        # Get component stats
        worker_stats = self.components['workers'].get_stats()
        pipeline_stats = self.components['pipeline'].get_stats()
        resource_stats = self.components['resources'].get_current_usage()
        
        # Calculate metrics
        total_tasks = worker_stats.get('completed_tasks', 0) + worker_stats.get('failed_tasks', 0)
        successful_tasks = worker_stats.get('completed_tasks', 0)
        failed_tasks = worker_stats.get('failed_tasks', 0)
        
        # Calculate rates
        error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Calculate throughput (tasks per second over last interval)
        if self.metrics_history:
            last_metrics = self.metrics_history[-1]
            time_delta = (datetime.utcnow() - last_metrics.timestamp).total_seconds()
            task_delta = total_tasks - last_metrics.total_tasks
            throughput = task_delta / time_delta if time_delta > 0 else 0.0
        else:
            throughput = 0.0
        
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
                'priority': 0  # TODO: Get from priority queue
            },
            error_rate=error_rate,
            throughput=throughput
        )
    
    async def _health_check_loop(self):
        """Perform periodic health checks."""
        while self._running:
            try:
                health_status = await self._perform_health_checks()
                self.health_checks = health_status
                self.last_health_check = datetime.utcnow()
                
                # Emit health status
                await self.event_bus.emit(Event(
                    type="health_check",
                    data=health_status
                ))
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            await asyncio.sleep(30.0)  # Check every 30 seconds
    
    async def _perform_health_checks(self) -> Dict[str, bool]:
        """Perform health checks on all components."""
        checks = {}
        
        # Check worker pool
        worker_stats = self.components['workers'].get_stats()
        checks['workers'] = worker_stats.get('active_workers', 0) > 0
        
        # Check resource usage
        resource_stats = self.components['resources'].get_current_usage()
        checks['resources'] = all(
            usage < 90.0 for usage in resource_stats.values()
        )
        
        # Check event bus
        checks['event_bus'] = self.event_bus.is_healthy()
        
        # Check state store
        checks['state_store'] = await self.components['pipeline'].state_store.is_healthy()
        
        # Overall health
        checks['overall'] = all(checks.values())
        
        return checks
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            "status": "healthy" if self.health_checks.get('overall', False) else "unhealthy",
            "checks": self.health_checks,
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None
        }
    
    def get_metrics_summary(
        self,
        duration: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get metrics summary for the specified duration."""
        if not self.metrics_history:
            return {}
        
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
            return {}
        
        # Calculate aggregates
        latest = relevant_metrics[-1]
        
        return {
            "period": {
                "start": relevant_metrics[0].timestamp.isoformat(),
                "end": latest.timestamp.isoformat()
            },
            "tasks": {
                "total": latest.total_tasks,
                "successful": latest.successful_tasks,
                "failed": latest.failed_tasks,
                "error_rate": latest.error_rate
            },
            "performance": {
                "average_duration": latest.average_task_duration,
                "throughput": latest.throughput
            },
            "resources": latest.resource_usage,
            "queues": latest.queue_depths
        }
```

### 3. Testing Framework (`tests/test_pipeline_integration.py`)

```python
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import time

from torematrix.processing.integration import ProcessingSystem, ProcessingSystemConfig
from torematrix.processing.pipeline.config import PipelineConfig, StageConfig
from torematrix.processing.workers.config import WorkerConfig, ResourceLimits
from torematrix.processing.pipeline.stages import StageStatus

class TestProcessingSystem:
    """Integration tests for the processing system."""
    
    @pytest.fixture
    async def processing_system(self, tmp_path):
        """Create a test processing system."""
        # Configure for testing
        pipeline_config = PipelineConfig(
            name="test_pipeline",
            stages=[
                StageConfig(
                    name="extraction",
                    processor="unstructured",
                    dependencies=[]
                ),
                StageConfig(
                    name="validation",
                    processor="validator",
                    dependencies=["extraction"]
                )
            ]
        )
        
        worker_config = WorkerConfig(
            async_workers=2,
            thread_workers=1,
            max_queue_size=100,
            default_timeout=30.0
        )
        
        resource_limits = ResourceLimits(
            max_cpu_percent=90.0,
            max_memory_percent=80.0
        )
        
        config = ProcessingSystemConfig(
            pipeline_config=pipeline_config,
            worker_config=worker_config,
            resource_limits=resource_limits,
            monitoring_enabled=True,
            state_persistence_enabled=True,
            state_store_path=tmp_path / "state"
        )
        
        system = ProcessingSystem(config)
        await system.initialize()
        
        yield system
        
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, processing_system):
        """Test system initializes all components."""
        assert processing_system._running
        assert processing_system.worker_pool._running
        assert processing_system.resource_monitor._monitoring
        assert processing_system.monitoring is not None
    
    @pytest.mark.asyncio
    async def test_document_processing(self, processing_system, tmp_path):
        """Test end-to-end document processing."""
        # Create test document
        test_doc = tmp_path / "test.pdf"
        test_doc.write_bytes(b"Test PDF content")
        
        # Process document
        pipeline_id = await processing_system.process_document(
            document_path=test_doc,
            metadata={"test": True}
        )
        
        assert pipeline_id is not None
        
        # Wait for processing
        await asyncio.sleep(2.0)
        
        # Check status
        status = processing_system.get_pipeline_status(pipeline_id)
        assert status["pipeline_id"] == pipeline_id
        assert status["status"] in ["completed", "running"]
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processing_system, tmp_path):
        """Test concurrent document processing."""
        # Create multiple test documents
        documents = []
        for i in range(5):
            doc = tmp_path / f"test_{i}.pdf"
            doc.write_bytes(f"Test content {i}".encode())
            documents.append(doc)
        
        # Process all documents concurrently
        pipeline_ids = await asyncio.gather(*[
            processing_system.process_document(doc)
            for doc in documents
        ])
        
        assert len(pipeline_ids) == 5
        assert len(set(pipeline_ids)) == 5  # All unique
        
        # Wait for processing
        await asyncio.sleep(3.0)
        
        # Check all completed
        for pipeline_id in pipeline_ids:
            status = processing_system.get_pipeline_status(pipeline_id)
            assert status["pipeline_id"] == pipeline_id
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, processing_system):
        """Test resource limit enforcement."""
        # Get current usage
        metrics = processing_system.get_system_metrics()
        initial_cpu = metrics["resources"].get("cpu", 0)
        
        # Simulate high resource usage
        processing_system.resource_monitor.current_usage["cpu"] = 95.0
        
        # Try to process document (should be throttled)
        with pytest.raises(Exception):  # ResourceError
            await processing_system.process_document(
                Path("/fake/document.pdf")
            )
    
    @pytest.mark.asyncio
    async def test_monitoring_metrics(self, processing_system):
        """Test monitoring metrics collection."""
        # Wait for metrics collection
        await asyncio.sleep(2.0)
        
        # Get metrics
        metrics = processing_system.monitoring.get_metrics_summary()
        
        assert "tasks" in metrics
        assert "performance" in metrics
        assert "resources" in metrics
    
    @pytest.mark.asyncio
    async def test_health_checks(self, processing_system):
        """Test health check functionality."""
        # Get health status
        health = processing_system.monitoring.get_health_status()
        
        assert health["status"] in ["healthy", "unhealthy"]
        assert "checks" in health
        assert health["checks"]["workers"] is True
        assert health["checks"]["resources"] is True
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, processing_system, tmp_path):
        """Test graceful shutdown with active tasks."""
        # Start processing
        doc = tmp_path / "test.pdf"
        doc.write_bytes(b"Test content")
        
        pipeline_id = await processing_system.process_document(doc)
        
        # Shutdown while processing
        await processing_system.shutdown()
        
        assert not processing_system._running
        assert not processing_system.worker_pool._running
```

### 4. Performance Testing (`tests/test_pipeline_performance.py`)

```python
import pytest
import asyncio
import time
from pathlib import Path
import statistics

from torematrix.processing.integration import ProcessingSystem

class TestPipelinePerformance:
    """Performance tests for the processing pipeline."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput(self, processing_system, benchmark_docs):
        """Test system throughput with multiple documents."""
        start_time = time.time()
        
        # Process 100 documents
        pipeline_ids = []
        for doc in benchmark_docs[:100]:
            pipeline_id = await processing_system.process_document(doc)
            pipeline_ids.append(pipeline_id)
        
        # Wait for completion
        completed = 0
        timeout = 300  # 5 minutes
        while completed < len(pipeline_ids) and time.time() - start_time < timeout:
            completed = sum(
                1 for pid in pipeline_ids
                if processing_system.get_pipeline_status(pid)["status"] == "completed"
            )
            await asyncio.sleep(1.0)
        
        duration = time.time() - start_time
        throughput = len(pipeline_ids) / duration
        
        assert throughput > 1.0  # At least 1 doc/second
        print(f"Throughput: {throughput:.2f} docs/second")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_latency(self, processing_system, benchmark_docs):
        """Test processing latency for individual documents."""
        latencies = []
        
        for doc in benchmark_docs[:20]:
            start = time.time()
            pipeline_id = await processing_system.process_document(doc)
            
            # Wait for completion
            while processing_system.get_pipeline_status(pipeline_id)["status"] != "completed":
                await asyncio.sleep(0.1)
            
            latency = time.time() - start
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        assert avg_latency < 30.0  # Average under 30 seconds
        assert p95_latency < 60.0  # 95% under 1 minute
        
        print(f"Average latency: {avg_latency:.2f}s")
        print(f"P95 latency: {p95_latency:.2f}s")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_resource_efficiency(self, processing_system, benchmark_docs):
        """Test resource usage efficiency."""
        # Get baseline
        baseline = processing_system.get_system_metrics()["resources"]
        
        # Process documents
        pipeline_ids = []
        for doc in benchmark_docs[:50]:
            pipeline_id = await processing_system.process_document(doc)
            pipeline_ids.append(pipeline_id)
        
        # Monitor resources during processing
        max_cpu = baseline.get("cpu", 0)
        max_memory = baseline.get("memory", 0)
        
        while any(
            processing_system.get_pipeline_status(pid)["status"] == "running"
            for pid in pipeline_ids
        ):
            metrics = processing_system.get_system_metrics()["resources"]
            max_cpu = max(max_cpu, metrics.get("cpu", 0))
            max_memory = max(max_memory, metrics.get("memory", 0))
            await asyncio.sleep(1.0)
        
        # Check efficiency
        assert max_cpu < 80.0  # CPU under 80%
        assert max_memory < 70.0  # Memory under 70%
        
        print(f"Peak CPU: {max_cpu:.1f}%")
        print(f"Peak Memory: {max_memory:.1f}%")
```

## Integration Points

### With Agent 1 (Pipeline Manager)
- Wire up PipelineManager with WorkerPool
- Connect state persistence
- Enable pipeline monitoring

### With Agent 2 (Processor Plugin)
- Register all processors with the system
- Configure processor-specific monitoring
- Enable dynamic processor loading

### With Agent 3 (Worker Pool)
- Integrate worker pool with monitoring
- Connect progress tracking to metrics
- Enable resource-based scaling

## Testing Requirements

1. **Integration Tests**:
   - Full system initialization and shutdown
   - End-to-end document processing
   - Component interaction verification
   - Error propagation testing

2. **Performance Tests**:
   - Throughput benchmarks (100+ docs)
   - Latency measurements (P50, P95, P99)
   - Resource efficiency validation
   - Scalability testing

3. **Monitoring Tests**:
   - Metrics accuracy verification
   - Health check validation
   - Alert threshold testing
   - Dashboard functionality

4. **Production Readiness**:
   - Load testing with realistic data
   - Failure recovery scenarios
   - Configuration validation
   - Deployment verification

## Implementation Notes

1. **Integration Strategy**:
   - Start with basic component wiring
   - Add monitoring incrementally
   - Build comprehensive test suite
   - Document all integration points

2. **Monitoring Focus**:
   - Real-time metrics with Prometheus
   - Comprehensive health checks
   - Error tracking and alerting
   - Performance profiling

3. **Testing Approach**:
   - Unit tests for each component
   - Integration tests for interactions
   - Performance tests for benchmarks
   - E2E tests for user workflows

4. **Production Considerations**:
   - Kubernetes deployment configs
   - Horizontal scaling support
   - Observability stack integration
   - Operational runbooks

## Dependencies
- pytest for testing framework
- prometheus_client for metrics
- Docker for integration testing
- Kubernetes manifests for deployment

Remember: Your work brings everything together - make it production-ready!