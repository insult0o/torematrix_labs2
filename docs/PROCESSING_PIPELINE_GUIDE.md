# TORE Matrix Labs V3 - Processing Pipeline Guide

## Overview

The TORE Matrix V3 Processing Pipeline is a comprehensive document processing system designed for enterprise-scale document ingestion, transformation, and analysis. It features async architecture, plugin-based processors, resource management, and production-ready monitoring.

## Quick Start

### Basic Usage

```python
import asyncio
from pathlib import Path
from torematrix.processing import ProcessingSystem, create_default_config

async def main():
    # Create configuration
    config = create_default_config()
    
    # Initialize and use processing system
    async with ProcessingSystem(config).processing_context() as system:
        # Process a document
        pipeline_id = await system.process_document(
            document_path=Path("document.pdf"),
            metadata={"priority": "high", "source": "upload"}
        )
        
        # Monitor progress
        status = system.get_pipeline_status(pipeline_id)
        print(f"Pipeline {pipeline_id}: {status}")
        
        # Get system metrics
        metrics = system.get_system_metrics()
        print(f"System health: {metrics}")

# Run the example
asyncio.run(main())
```

### Docker Quick Start

```bash
# Clone repository
git clone https://github.com/torematrix/torematrix_labs2
cd torematrix_labs2

# Start with Docker Compose
docker-compose -f deployment/docker/docker-compose.yml up -d

# Process a document via API
curl -X POST http://localhost:8000/process \
     -F "file=@document.pdf" \
     -F "pipeline=default"

# Check health
curl http://localhost:8000/health

# View metrics
curl http://localhost:9090/metrics
```

## Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ ProcessingSystem│◄──►│ PipelineManager │◄──►│ WorkerPool      │
│                 │    │                 │    │                 │
│ - Integration   │    │ - DAG Execution │    │ - Async Workers │
│ - Health Checks │    │ - Checkpointing │    │ - Thread Pool   │
│ - Metrics       │    │ - Event Emission│    │ - Task Queue    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ MonitoringService│    │ProcessorRegistry│    │ ResourceMonitor │
│                 │    │                 │    │                 │
│ - Prometheus    │    │ - Plugin System │    │ - CPU/Memory    │
│ - Health Checks │    │ - Dynamic Load  │    │ - Throttling    │
│ - Alerting      │    │ - Dependencies  │    │ - Allocation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Document Submission** → ProcessingSystem receives document
2. **Pipeline Creation** → PipelineManager creates execution plan
3. **Stage Execution** → Stages executed in dependency order
4. **Processor Invocation** → Workers execute processors on stages
5. **Progress Tracking** → Real-time updates via EventBus
6. **Result Collection** → Aggregated results returned
7. **Monitoring** → Metrics collected and exposed

## Configuration

### System Configuration

```python
from torematrix.processing import ProcessingSystemConfig
from torematrix.processing.pipeline.config import PipelineConfig, StageConfig, StageType
from torematrix.processing.workers.config import WorkerConfig, ResourceLimits

# Pipeline configuration
pipeline_config = PipelineConfig(
    name="custom_pipeline",
    stages=[
        StageConfig(
            name="validation",
            type=StageType.VALIDATOR,
            processor="validation_processor",
            dependencies=[]
        ),
        StageConfig(
            name="extraction", 
            type=StageType.PROCESSOR,
            processor="unstructured_processor",
            dependencies=["validation"]
        ),
        StageConfig(
            name="analysis",
            type=StageType.PROCESSOR,
            processor="analysis_processor",
            dependencies=["extraction"]
        )
    ]
)

# Worker configuration
worker_config = WorkerConfig(
    async_workers=4,
    thread_workers=2,
    max_queue_size=1000,
    default_timeout=300.0
)

# Resource limits
resource_limits = ResourceLimits(
    max_cpu_percent=80.0,
    max_memory_percent=75.0,
    max_disk_io_mbps=100.0
)

# System configuration
config = ProcessingSystemConfig(
    pipeline_config=pipeline_config,
    worker_config=worker_config,
    resource_limits=resource_limits,
    monitoring_enabled=True,
    state_persistence_enabled=True
)
```

### Pre-built Configurations

```python
from torematrix.processing import (
    create_default_config,
    create_high_throughput_config,
    create_memory_efficient_config
)

# Default balanced configuration
config = create_default_config()

# High throughput (more workers, higher resource limits)
config = create_high_throughput_config()

# Memory efficient (fewer workers, lower memory usage)
config = create_memory_efficient_config()
```

## Processor Development

### Creating Custom Processors

```python
from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus
)
from datetime import datetime

class CustomProcessor(BaseProcessor):
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="custom_processor",
            version="1.0.0",
            description="Custom document processor",
            capabilities=[
                ProcessorCapability.TEXT_EXTRACTION,
                ProcessorCapability.METADATA_EXTRACTION
            ],
            supported_formats=["pdf", "docx", "txt"],
            timeout_seconds=120
        )
    
    async def _initialize(self) -> None:
        """Initialize processor resources."""
        # Setup connections, models, etc.
        pass
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process the document."""
        start_time = datetime.utcnow()
        
        try:
            # Your processing logic here
            with open(context.file_path, 'rb') as f:
                content = f.read()
            
            # Extract data
            extracted_data = {
                "text": content.decode('utf-8', errors='ignore'),
                "size": len(content),
                "format": context.mime_type
            }
            
            return ProcessorResult(
                processor_name=self.get_metadata().name,
                status=StageStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                extracted_data=extracted_data
            )
            
        except Exception as e:
            return ProcessorResult(
                processor_name=self.get_metadata().name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                errors=[str(e)]
            )

# Register the processor
from torematrix.processing import get_registry
registry = get_registry()
registry.register(CustomProcessor)
```

### Processor Best Practices

1. **Async Operations**: Use async/await for I/O operations
2. **Error Handling**: Catch and report errors appropriately
3. **Resource Management**: Clean up resources in `_cleanup()`
4. **Progress Updates**: Report progress for long-running operations
5. **Validation**: Validate inputs in `_validate_input()`
6. **Metrics**: Track performance metrics

## Monitoring and Observability

### Health Checks

```python
# Get system health
health = system.get_health_status()
print(f"System healthy: {health['healthy']}")
print(f"Services: {health['services']}")

# Individual component health
if health['services']['worker_pool']['healthy']:
    print("Worker pool is healthy")
```

### Metrics Collection

```python
# Get system metrics
metrics = system.get_system_metrics()
print(f"Active workers: {metrics['workers']['active_workers']}")
print(f"CPU usage: {metrics['resources']['cpu']}%")
print(f"Completed tasks: {metrics['workers']['completed_tasks']}")

# Get performance metrics (if monitoring enabled)
perf_metrics = await system.get_performance_metrics()
print(f"Throughput: {perf_metrics['tasks']['throughput']} tasks/sec")
print(f"Error rate: {perf_metrics['tasks']['error_rate']}")
```

### Prometheus Integration

The system automatically exports metrics to Prometheus:

```
# HELP torematrix_tasks_total Total number of processing tasks
# TYPE torematrix_tasks_total counter
torematrix_tasks_total{processor="unstructured_processor",status="success"} 150.0

# HELP torematrix_task_duration_seconds Task processing duration
# TYPE torematrix_task_duration_seconds histogram
torematrix_task_duration_seconds_bucket{processor="unstructured_processor",le="1.0"} 45.0

# HELP torematrix_resource_usage_percent Resource usage percentage
# TYPE torematrix_resource_usage_percent gauge
torematrix_resource_usage_percent{resource_type="cpu"} 65.5
```

### Grafana Dashboards

Pre-built Grafana dashboards are included:

- **System Overview**: High-level metrics and health
- **Pipeline Performance**: Throughput, latency, error rates
- **Resource Utilization**: CPU, memory, disk usage
- **Worker Pool Status**: Active workers, queue depths
- **Processor Metrics**: Per-processor performance

## Deployment

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  torematrix-pipeline:
    image: torematrix/pipeline:v3.0.0
    ports:
      - "8000:8000"  # API
      - "9090:9090"  # Metrics
    environment:
      - ASYNC_WORKERS=4
      - MAX_CPU_PERCENT=80
      - POSTGRES_HOST=postgres
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    depends_on:
      - postgres
      - redis
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: torematrix-pipeline
spec:
  replicas: 3
  selector:
    matchLabels:
      app: torematrix-pipeline
  template:
    metadata:
      labels:
        app: torematrix-pipeline
    spec:
      containers:
      - name: pipeline
        image: torematrix/pipeline:v3.0.0
        ports:
        - containerPort: 8000
        - containerPort: 9090
        env:
        - name: ASYNC_WORKERS
          value: "4"
        - name: POSTGRES_HOST
          value: "postgres-service"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TOREMATRIX_ENV` | Environment (development/production) | production |
| `TOREMATRIX_LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `ASYNC_WORKERS` | Number of async workers | 4 |
| `THREAD_WORKERS` | Number of thread workers | 2 |
| `MAX_CPU_PERCENT` | Maximum CPU usage | 80.0 |
| `MAX_MEMORY_PERCENT` | Maximum memory usage | 75.0 |
| `PROMETHEUS_ENABLED` | Enable Prometheus metrics | true |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `REDIS_HOST` | Redis host | localhost |

## Performance Tuning

### Worker Configuration

```python
# CPU-intensive workloads
worker_config = WorkerConfig(
    async_workers=2,      # Fewer async workers
    thread_workers=8,     # More thread workers
    process_workers=4     # Use process workers
)

# I/O-intensive workloads
worker_config = WorkerConfig(
    async_workers=8,      # More async workers
    thread_workers=2,     # Fewer thread workers
    process_workers=0     # No process workers needed
)
```

### Resource Optimization

```python
# High-performance configuration
resource_limits = ResourceLimits(
    max_cpu_percent=90.0,     # Higher CPU usage
    max_memory_percent=85.0,  # Higher memory usage
    max_disk_io_mbps=200.0    # Higher I/O throughput
)

# Conservative configuration
resource_limits = ResourceLimits(
    max_cpu_percent=50.0,     # Lower CPU usage
    max_memory_percent=40.0,  # Lower memory usage
    max_disk_io_mbps=50.0     # Lower I/O throughput
)
```

### Pipeline Optimization

1. **Parallel Stages**: Design stages to run in parallel when possible
2. **Caching**: Implement result caching for expensive operations
3. **Batching**: Process multiple documents in batches
4. **Resource Scheduling**: Balance resource usage across stages

## Testing

### Unit Testing

```python
import pytest
from torematrix.processing import ProcessingSystem, create_default_config

@pytest.mark.asyncio
async def test_document_processing():
    config = create_default_config()
    
    async with ProcessingSystem(config).processing_context() as system:
        pipeline_id = await system.process_document(
            document_path=Path("test_document.pdf")
        )
        
        status = system.get_pipeline_status(pipeline_id)
        assert status["status"] == "completed"
```

### Performance Testing

```python
import pytest
from torematrix.processing.tests.performance import PerformanceTester

@pytest.mark.performance
async def test_throughput():
    config = create_high_throughput_config()
    
    async with ProcessingSystem(config).processing_context() as system:
        tester = PerformanceTester(system)
        
        metrics = await tester.run_throughput_test(
            documents=test_documents,
            concurrent_limit=10
        )
        
        assert metrics.throughput > 5.0  # 5 docs/second
        assert metrics.error_rate < 0.05  # < 5% error rate
```

### Integration Testing

```python
@pytest.mark.integration
async def test_full_pipeline():
    # Test complete pipeline with real components
    config = create_default_config()
    
    async with ProcessingSystem(config).processing_context() as system:
        # Test multiple document types
        results = await asyncio.gather(*[
            system.process_document(Path(f"test_{i}.pdf"))
            for i in range(10)
        ])
        
        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)
```

## Troubleshooting

### Common Issues

#### High Memory Usage
- Reduce `max_memory_percent` in resource limits
- Decrease number of concurrent workers
- Enable memory monitoring and alerts

#### Slow Processing
- Increase worker count for I/O-bound tasks
- Optimize processor implementations
- Check resource bottlenecks

#### Failed Health Checks
- Check component initialization order
- Verify external dependencies (database, Redis)
- Review application logs

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger('torematrix').setLevel(logging.DEBUG)

# Get detailed system status
system_metrics = system.get_system_metrics()
health_status = system.get_health_status()

# Check specific component
worker_stats = system.worker_pool.get_stats()
pipeline_stats = system.pipeline_manager.get_stats()
```

### Log Analysis

```bash
# View application logs
docker logs torematrix-pipeline

# Filter for errors
docker logs torematrix-pipeline 2>&1 | grep ERROR

# Monitor real-time logs
docker logs -f torematrix-pipeline
```

## API Reference

### ProcessingSystem

Main interface for the processing pipeline system.

#### Methods

- `initialize()` - Initialize all components
- `shutdown()` - Gracefully shutdown system
- `process_document(path, pipeline, metadata)` - Process a document
- `get_pipeline_status(pipeline_id)` - Get pipeline execution status
- `get_system_metrics()` - Get system-wide metrics
- `get_health_status()` - Get health check results

### MonitoringService

Comprehensive monitoring and metrics collection.

#### Methods

- `start()` - Start monitoring service
- `stop()` - Stop monitoring service
- `get_metrics_summary(duration)` - Get aggregated metrics
- `get_alerts(level)` - Get system alerts
- `add_alert_handler(handler)` - Add custom alert handler

### ProcessorRegistry

Dynamic processor plugin system.

#### Methods

- `register(processor_class)` - Register a processor
- `get_processor(name, config)` - Get processor instance
- `list_processors()` - List registered processors
- `find_by_capability(capability)` - Find processors by capability

## Support

### Community

- **GitHub**: https://github.com/torematrix/torematrix_labs2
- **Issues**: https://github.com/torematrix/torematrix_labs2/issues
- **Discussions**: https://github.com/torematrix/torematrix_labs2/discussions

### Enterprise Support

Contact enterprise@torematrix.labs for:
- Custom processor development
- Performance optimization
- Production deployment assistance
- SLA-backed support

---

*This guide covers TORE Matrix Labs V3 Processing Pipeline v3.0.0*