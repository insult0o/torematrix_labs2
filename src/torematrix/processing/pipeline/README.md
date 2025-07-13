# Pipeline Processing Module

This module provides a flexible, DAG-based document processing pipeline for TORE Matrix V3.

## Overview

The pipeline module enables:
- **DAG-based execution** - Define complex processing workflows with dependencies
- **Async processing** - Fully async/await compatible for high performance
- **Resource management** - Monitor and limit CPU/memory usage
- **Checkpoint support** - Resume processing from failures
- **Parallel execution** - Run independent stages concurrently
- **Plugin architecture** - Extensible with custom processors

## Architecture

```
┌─────────────────┐
│ PipelineManager │ ◄── Orchestrates execution
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│   DAG Engine    │ ◄── Manages dependencies
└───────┬─────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────┐
│     Stages      │ ──► │  Processors  │ (from Agent 2)
└───────┬─────────┘     └──────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────┐
│ Resource Monitor│ ──► │ Worker Pool  │ (from Agent 3)
└─────────────────┘     └──────────────┘
```

## Key Components

### PipelineManager
The main orchestrator that:
- Builds and validates the pipeline DAG
- Executes stages in topological order
- Manages checkpoints and recovery
- Emits events for progress tracking

### Stage System
Stages are the building blocks of pipelines:
- `ProcessorStage` - Document processing operations
- `ValidationStage` - Data validation and quality checks
- `RouterStage` - Conditional routing logic
- `AggregatorStage` - Result aggregation

### Resource Monitoring
Tracks system resources to prevent overload:
- CPU and memory usage monitoring
- Resource allocation per stage
- Configurable limits and throttling

### Configuration
Pipelines are configured using Pydantic models:
- Type-safe configuration
- YAML/JSON support
- Validation at load time

## Usage Examples

### Creating a Simple Pipeline

```python
from torematrix.processing.pipeline import (
    PipelineConfig, StageConfig, StageType,
    PipelineManager
)

# Define pipeline configuration
config = PipelineConfig(
    name="document-pipeline",
    stages=[
        StageConfig(
            name="validation",
            type=StageType.VALIDATOR,
            processor="DocumentValidator"
        ),
        StageConfig(
            name="extraction",
            type=StageType.PROCESSOR,
            processor="TextExtractor",
            dependencies=["validation"]
        ),
        StageConfig(
            name="enrichment",
            type=StageType.PROCESSOR,
            processor="MetadataEnricher",
            dependencies=["extraction"]
        )
    ]
)

# Create and execute pipeline
manager = PipelineManager(config, event_bus, state_store)
context = await manager.execute(document_id="doc123")
```

### Using Pipeline Templates

```python
from torematrix.processing.pipeline import create_pipeline_from_template

# Create standard document processing pipeline
config = create_pipeline_from_template(
    "standard",
    enable_ocr=True,
    enable_translation=True,
    target_language="es"
)

manager = PipelineManager(config, event_bus)
```

### Resource-Aware Execution

```python
from torematrix.processing.pipeline import ResourceMonitor

# Create resource monitor
monitor = ResourceMonitor(
    max_cpu_percent=80.0,
    max_memory_percent=75.0
)

# Pipeline will respect resource limits
manager = PipelineManager(
    config, 
    event_bus,
    resource_monitor=monitor
)
```

### Checkpoint and Recovery

```python
# Enable checkpointing
context = await manager.execute(
    document_id="doc123",
    checkpoint=True
)

# If pipeline fails, it will resume from last checkpoint
# on next execution
```

## Pipeline Templates

Pre-configured templates for common workflows:

### Standard Document Pipeline
- Document validation
- Content extraction
- Text processing
- Optional: OCR, translation, PII removal
- Result aggregation

### Batch Processing Pipeline
- Batch validation
- Parallel batch extraction
- Batch result aggregation

### Quality Assurance Pipeline
- High-resolution extraction
- Quality analysis
- Conditional enhancement
- Final validation
- QA report generation

## Events

The pipeline emits events for monitoring:
- `pipeline.started` - Pipeline execution began
- `pipeline.completed` - Pipeline finished successfully
- `pipeline.failed` - Pipeline execution failed
- `stage.started` - Stage execution began
- `stage.completed` - Stage finished successfully
- `stage.failed` - Stage execution failed

## Error Handling

Comprehensive error handling with:
- Stage-level retry logic
- Critical vs non-critical failures
- Timeout management
- Resource exhaustion handling
- Graceful cancellation

## Testing

The module includes comprehensive tests:
- Unit tests for all components
- Integration tests for pipeline execution
- Performance tests for throughput
- Resource limit tests

Run tests with:
```bash
pytest tests/unit/processing/pipeline/ -v
```

## Integration with Other Agents

- **Agent 2**: Processors are executed as pipeline stages
- **Agent 3**: Stages run in the worker pool with progress tracking
- **Agent 4**: Monitoring integration provides metrics and health checks