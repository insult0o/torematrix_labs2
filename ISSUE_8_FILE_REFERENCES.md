# Issue #8 - File References for All Agents

## Agent 1 - Core Pipeline Manager & DAG Architecture

### Primary Files to Create
```
src/torematrix/processing/pipeline/
├── __init__.py
├── manager.py          # Main PipelineManager class
├── stages.py           # Stage abstract class and implementations
├── config.py           # Configuration models (Pydantic)
├── dag.py              # DAG utilities and validation
└── exceptions.py       # Pipeline-specific exceptions

tests/
├── test_pipeline_manager.py
├── test_pipeline_stages.py
└── test_pipeline_dag.py
```

### Files to Read
```
# Your instructions
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md

# Dependencies to understand
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/client.py
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/config.py

# Project context
/home/insulto/torematrix_labs2/CLAUDE.md
```

### Interfaces You Export
- `PipelineManager` class
- `Stage` abstract class  
- `PipelineContext` dataclass
- `StageResult` dataclass
- `PipelineConfig` model

---

## Agent 2 - Processor Plugin System & Interface

### Primary Files to Create
```
src/torematrix/processing/processors/
├── __init__.py
├── base.py             # BaseProcessor abstract class
├── registry.py         # ProcessorRegistry for dynamic loading
├── utils.py            # Common processor utilities
├── exceptions.py       # Processor-specific exceptions
└── builtin/            # Built-in processors
    ├── __init__.py
    ├── unstructured.py # Wrapper for Unstructured.io
    ├── validator.py    # Document validation
    ├── metadata.py     # Metadata extraction
    └── example.py      # Example custom processor

tests/
├── test_processors_base.py
├── test_processor_registry.py
└── test_builtin_processors.py
```

### Files to Read
```
# Your instructions
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md

# Unstructured.io integration to wrap
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/client.py
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/config.py
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/exceptions.py
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/utils.py

# Project context
/home/insulto/torematrix_labs2/CLAUDE.md
```

### Interfaces You Export
- `BaseProcessor` abstract class
- `ProcessorRegistry` class
- `ProcessorContext` dataclass
- `ProcessorResult` dataclass
- `ProcessorMetadata` dataclass
- `ProcessorCapability` enum

---

## Agent 3 - Worker Pool & Progress Tracking

### Primary Files to Create
```
src/torematrix/processing/workers/
├── __init__.py
├── pool.py             # WorkerPool implementation
├── progress.py         # ProgressTracker for real-time updates
├── resources.py        # ResourceMonitor for system resources
├── config.py           # Worker configuration models
├── exceptions.py       # Worker-specific exceptions
└── utils.py            # Worker utilities

tests/
├── test_worker_pool.py
├── test_progress_tracking.py
├── test_resource_management.py
└── test_worker_integration.py
```

### Files to Read
```
# Your instructions
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md

# To understand processor requirements
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_PIPELINE.md (ProcessorMetadata section)

# Project context
/home/insulto/torematrix_labs2/CLAUDE.md
```

### Interfaces You Export
- `WorkerPool` class
- `ProgressTracker` class
- `ResourceMonitor` class
- `WorkerConfig` model
- `ResourceLimits` model
- Task submission API
- Progress event structure

---

## Agent 4 - Integration, Monitoring & Testing

### Primary Files to Create
```
src/torematrix/processing/
├── integration.py      # ProcessingSystem main integration
├── monitoring.py       # MonitoringService with Prometheus
└── __init__.py         # Public API exports

tests/
├── test_pipeline_integration.py    # End-to-end tests
├── test_pipeline_performance.py    # Performance benchmarks
├── test_monitoring.py              # Monitoring tests
└── fixtures/                       # Test documents and data
    ├── test_documents/
    └── test_configs/

deployment/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── kubernetes/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── monitoring/
    ├── prometheus.yml
    └── grafana-dashboard.json
```

### Files to Read
```
# Your instructions
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_4_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md

# All other agents' instructions to understand components
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_PIPELINE.md
/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_PIPELINE.md

# Existing systems to integrate with
/home/insulto/torematrix_labs2/src/torematrix/ingestion/models.py
/home/insulto/torematrix_labs2/src/torematrix/ingestion/upload_manager.py
/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/client.py

# Project context
/home/insulto/torematrix_labs2/CLAUDE.md
```

### Interfaces You Export
- `ProcessingSystem` class (main entry point)
- `MonitoringService` class
- `ProcessingSystemConfig` model
- Health check endpoints
- Metrics endpoints

---

## Shared Dependencies

### Core Modules (All Agents Should Know About)
```
src/torematrix/core/
├── events.py           # EventBus for async communication
├── state.py            # StateStore for persistence
└── exceptions.py       # Base exception classes
```

### Common Patterns

1. **Event Structure**
```python
Event(
    type: str,              # e.g., "task_completed"
    data: Dict[str, Any],   # Event-specific data
    timestamp: datetime     # When event occurred
)
```

2. **Async Context Managers**
```python
async with ProcessingSystem(config) as system:
    await system.process_document(path)
```

3. **Error Handling**
```python
try:
    result = await processor.process(context)
except ProcessorError as e:
    # Handle processor-specific errors
except Exception as e:
    # Handle unexpected errors
```

---

## File Creation Order

### Phase 1 (Parallel Development)
- Agent 1: Create config.py → stages.py → dag.py → manager.py
- Agent 2: Create base.py → registry.py → builtin processors
- Agent 3: Create config.py → resources.py → progress.py → pool.py
- Agent 4: Set up test framework and monitoring base

### Phase 2 (Integration)
- Agent 4: Create integration.py once other components exist
- All: Add integration tests
- Agent 4: Create deployment configurations

### Phase 3 (Polish)
- All: Complete test coverage
- Agent 4: Performance benchmarks
- All: Documentation updates

---

## Testing Files

### Unit Test Structure
```python
# tests/test_component.py
import pytest
from torematrix.processing.component import Component

class TestComponent:
    @pytest.fixture
    def component(self):
        return Component(config)
    
    def test_initialization(self, component):
        assert component is not None
    
    @pytest.mark.asyncio
    async def test_async_operation(self, component):
        result = await component.async_method()
        assert result is not None
```

### Integration Test Structure
```python
# tests/test_integration.py
import pytest
from torematrix.processing.integration import ProcessingSystem

@pytest.mark.integration
class TestProcessingIntegration:
    @pytest.fixture
    async def system(self):
        system = ProcessingSystem(test_config)
        await system.initialize()
        yield system
        await system.shutdown()
```

---

## GitHub Issue References

- Parent Issue: #8 (Processing Pipeline Architecture)
- Agent 1 Issue: #88 (Core Pipeline Manager & DAG Architecture)
- Agent 2 Issue: #90 (Processor Plugin System & Interface)
- Agent 3 Issue: #91 (Worker Pool & Progress Tracking)
- Agent 4 Issue: #92 (Integration, Monitoring & Testing)

Each agent should read their specific issue for additional context and requirements.