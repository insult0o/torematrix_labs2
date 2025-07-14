# Pipeline Architecture Coordination Guide

## Overview
This guide coordinates the parallel development of Issue #8 (Processing Pipeline Architecture) by 4 agents. Each agent owns a specific component while maintaining clear interfaces for integration.

## Agent Responsibilities

### Agent 1: Core Pipeline Manager & DAG Architecture
- **Primary Files**:
  - `src/torematrix/processing/pipeline/manager.py`
  - `src/torematrix/processing/pipeline/stages.py`
  - `src/torematrix/processing/pipeline/config.py`
- **Key Interfaces**: PipelineManager, Stage, PipelineContext
- **Dependencies**: EventBus, StateStore from core

### Agent 2: Processor Plugin System & Interface
- **Primary Files**:
  - `src/torematrix/processing/processors/base.py`
  - `src/torematrix/processing/processors/registry.py`
  - `src/torematrix/processing/processors/builtin/`
- **Key Interfaces**: BaseProcessor, ProcessorRegistry, ProcessorContext
- **Dependencies**: None (foundational component)

### Agent 3: Worker Pool & Progress Tracking
- **Primary Files**:
  - `src/torematrix/processing/workers/pool.py`
  - `src/torematrix/processing/workers/progress.py`
  - `src/torematrix/processing/workers/resources.py`
- **Key Interfaces**: WorkerPool, ProgressTracker, ResourceMonitor
- **Dependencies**: EventBus, Processor interfaces from Agent 2

### Agent 4: Integration, Monitoring & Testing
- **Primary Files**:
  - `src/torematrix/processing/integration.py`
  - `src/torematrix/processing/monitoring.py`
  - `tests/test_pipeline_*.py`
- **Key Interfaces**: ProcessingSystem, MonitoringService
- **Dependencies**: All components from Agents 1-3

## Shared Interfaces

### 1. Event System (All Agents)
```python
# Events emitted by pipeline components
- pipeline_started(pipeline_id, document_id)
- pipeline_completed(pipeline_id, status, duration)
- stage_started(pipeline_id, stage_name)
- stage_completed(pipeline_id, stage_name, result)
- task_submitted(task_id, processor, priority)
- task_progress(task_id, progress_data)
- resource_warning(resource_type, usage_percent)
```

### 2. Processor Context (Agent 1 → Agent 2)
```python
@dataclass
class ProcessorContext:
    document_id: str
    file_path: str
    mime_type: str
    metadata: Dict[str, Any]
    previous_results: Dict[str, Any]
    pipeline_context: Optional[Any]
```

### 3. Task Submission (Agent 1 → Agent 3)
```python
async def submit_task(
    processor_name: str,
    context: ProcessorContext,
    processor_func: Callable,
    priority: ProcessorPriority,
    timeout: Optional[float]
) -> str:
    """Returns task_id"""
```

### 4. Progress Updates (Agent 3 → All)
```python
# Via EventBus
Event(type="task_progress", data={
    "task_id": str,
    "progress": float,  # 0.0 to 1.0
    "message": str,
    "current_step": str,
    "estimated_remaining": float
})
```

## Development Timeline

### Phase 1: Foundation (Parallel)
- **Agent 1**: Implement core pipeline manager and DAG
- **Agent 2**: Create processor interface and registry
- **Agent 3**: Build worker pool and resource monitoring
- **Agent 4**: Set up testing framework and monitoring base

### Phase 2: Integration Points
- **Agent 1 + 2**: Connect processor registry to pipeline stages
- **Agent 1 + 3**: Wire pipeline execution through worker pool
- **Agent 3 + 2**: Implement processor execution in workers
- **Agent 4**: Create integration tests for all connections

### Phase 3: Enhancement
- **All Agents**: Add comprehensive error handling
- **Agent 3**: Implement advanced resource management
- **Agent 4**: Complete monitoring and alerting
- **All**: Performance optimization based on profiling

### Phase 4: Production Readiness
- **Agent 4**: Final integration and deployment configs
- **All**: Documentation and API finalization
- **Agent 4**: Load testing and benchmarking
- **All**: Bug fixes and polish

## Communication Protocol

### 1. Interface Changes
If you need to change a shared interface:
1. Document the proposed change
2. Note which agents are affected
3. Provide migration path if needed
4. Update this coordination guide

### 2. Blocking Issues
If blocked by another agent's work:
1. Implement a mock/stub temporarily
2. Document what you need from the other agent
3. Continue with other tasks
4. Integration test once unblocked

### 3. Progress Updates
Regular status should include:
- Completed components
- Current work in progress
- Any interface changes
- Blocking issues
- Test coverage

## Testing Strategy

### Unit Testing (Each Agent)
- Test your components in isolation
- Mock external dependencies
- Aim for 90%+ coverage
- Focus on edge cases

### Integration Testing (Agent 4 leads)
- Test component interactions
- Verify event flow
- Check resource management
- Validate error propagation

### Performance Testing (Agent 4)
- Benchmark throughput
- Measure latency
- Monitor resource usage
- Identify bottlenecks

## Code Style Guidelines

### Consistency Requirements
- Type hints for all public methods
- Comprehensive docstrings
- Async/await for I/O operations
- Proper exception handling
- Logging at appropriate levels

### Naming Conventions
- Classes: PascalCase (PipelineManager)
- Functions: snake_case (process_document)
- Constants: UPPER_SNAKE_CASE
- Private: Leading underscore (_internal_method)

## Common Pitfalls to Avoid

1. **Circular Dependencies**: Keep dependencies unidirectional
2. **Blocking Operations**: Always use async for I/O
3. **Resource Leaks**: Proper cleanup in finally blocks
4. **Race Conditions**: Use appropriate locking
5. **Tight Coupling**: Communicate via interfaces only

## Success Criteria

### Functional Requirements
- ✓ Process 15+ document formats
- ✓ Support parallel execution
- ✓ Handle failures gracefully
- ✓ Provide real-time progress
- ✓ Scale horizontally

### Performance Requirements
- ✓ Process 100+ documents concurrently
- ✓ < 30 second average latency
- ✓ < 5% failure rate
- ✓ 99.9% uptime

### Quality Requirements
- ✓ 90%+ test coverage
- ✓ Comprehensive monitoring
- ✓ Full API documentation
- ✓ Production deployment ready

## Quick Reference

### Key Files
```
src/torematrix/processing/
├── pipeline/
│   ├── manager.py      (Agent 1)
│   ├── stages.py       (Agent 1)
│   └── config.py       (Agent 1)
├── processors/
│   ├── base.py         (Agent 2)
│   ├── registry.py     (Agent 2)
│   └── builtin/        (Agent 2)
├── workers/
│   ├── pool.py         (Agent 3)
│   ├── progress.py     (Agent 3)
│   └── resources.py    (Agent 3)
├── integration.py      (Agent 4)
└── monitoring.py       (Agent 4)
```

### Test Commands
```bash
# Run all tests
pytest tests/test_pipeline_*.py -v

# Run specific agent tests
pytest tests/test_pipeline_manager.py -v     # Agent 1
pytest tests/test_processors.py -v           # Agent 2
pytest tests/test_workers.py -v              # Agent 3
pytest tests/test_integration.py -v          # Agent 4

# Run with coverage
pytest --cov=torematrix.processing tests/
```

Remember: Clear communication and well-defined interfaces are key to successful parallel development!