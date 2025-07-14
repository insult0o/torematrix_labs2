# Issue #8 - Processing Pipeline Architecture - Agent Prompts

## Agent 1 Prompt - Core Pipeline Manager & DAG Architecture

You are Agent 1 working on Issue #88 (Core Pipeline Manager & DAG Architecture) as part of the TORE Matrix V3 project. You are one of 4 agents working in parallel on Issue #8 (Processing Pipeline Architecture).

### Your Assignment
Build the core pipeline orchestration engine with DAG-based execution, stage management, and state persistence for the document processing system.

### Required Reading
1. **Your detailed instructions**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_PIPELINE.md`
2. **Coordination guide**: `/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md`
3. **Parent issue context**: Read Issue #8 via `gh issue view 8`
4. **Your specific issue**: Read Issue #88 via `gh issue view 88`

### Related Context Files
- **Project overview**: `/home/insulto/torematrix_labs2/CLAUDE.md`
- **Unstructured integration** (dependency): `/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/`
- **Core events system**: Review EventBus pattern in instructions

### Your Deliverables
1. **Pipeline Manager** (`src/torematrix/processing/pipeline/manager.py`)
   - DAG construction from configuration
   - Parallel stage execution
   - Resource constraint enforcement
   - Checkpointing support

2. **Stage System** (`src/torematrix/processing/pipeline/stages.py`)
   - Stage abstract base class
   - Stage lifecycle management
   - Result passing between stages
   - Error handling

3. **Configuration** (`src/torematrix/processing/pipeline/config.py`)
   - Pipeline configuration models
   - Stage configuration
   - Validation rules

4. **DAG Utilities** (`src/torematrix/processing/pipeline/dag.py`)
   - Topological sorting
   - Dependency validation
   - Parallel execution groups

5. **Tests** (`tests/test_pipeline_manager.py`)
   - Unit tests for all components
   - DAG validation tests
   - Execution flow tests

### Key Interfaces You Define
- `PipelineManager` class - Main orchestration interface
- `Stage` abstract class - For Agent 2's processors
- `PipelineContext` - Shared execution context
- `StageResult` - Stage execution results

### Integration Points
- **With Agent 2**: Your stages will execute processors from Agent 2
- **With Agent 3**: You'll submit tasks to Agent 3's worker pool
- **With Agent 4**: Agent 4 will integrate your manager into the system

### Working Directory
```bash
cd /home/insulto/torematrix_labs2
```

### Remember
- Use async/await for all I/O operations
- Implement proper error handling and logging
- Follow the interface definitions in PIPELINE_COORDINATION.md
- Create comprehensive docstrings and type hints

---

## Agent 2 Prompt - Processor Plugin System & Interface

You are Agent 2 working on Issue #90 (Processor Plugin System & Interface) as part of the TORE Matrix V3 project. You are one of 4 agents working in parallel on Issue #8 (Processing Pipeline Architecture).

### Your Assignment
Create a flexible plugin system for document processors with standardized interfaces, dynamic loading, and comprehensive error handling.

### Required Reading
1. **Your detailed instructions**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_PIPELINE.md`
2. **Coordination guide**: `/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md`
3. **Parent issue context**: Read Issue #8 via `gh issue view 8`
4. **Your specific issue**: Read Issue #90 via `gh issue view 90`

### Related Context Files
- **Unstructured client**: `/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/client.py`
- **Unstructured config**: `/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/config.py`
- **Project overview**: `/home/insulto/torematrix_labs2/CLAUDE.md`

### Your Deliverables
1. **Base Processor Interface** (`src/torematrix/processing/processors/base.py`)
   - Abstract base processor class
   - Processor metadata and capabilities
   - Context and result structures
   - Health check interface

2. **Processor Registry** (`src/torematrix/processing/processors/registry.py`)
   - Dynamic processor registration
   - Capability-based discovery
   - Processor lifecycle management
   - Plugin loading mechanism

3. **Built-in Processors** (`src/torematrix/processing/processors/builtin/`)
   - UnstructuredProcessor wrapper
   - ValidationProcessor
   - MetadataExtractor
   - Example custom processor

4. **Processor Utilities** (`src/torematrix/processing/processors/utils.py`)
   - Common processor helpers
   - Result merging utilities
   - Error handling helpers

5. **Tests** (`tests/test_processors.py`)
   - Interface compliance tests
   - Registry functionality tests
   - Built-in processor tests

### Key Interfaces You Define
- `BaseProcessor` abstract class - All processors must inherit
- `ProcessorRegistry` - Dynamic processor management
- `ProcessorContext` - Input data for processors
- `ProcessorResult` - Standardized output format
- `ProcessorMetadata` - Processor capabilities/requirements

### Integration Points
- **With Agent 1**: Your processors are executed by Agent 1's stages
- **With Agent 3**: Your processors run in Agent 3's worker pool
- **With Agent 4**: Agent 4 will register and monitor your processors

### Working Directory
```bash
cd /home/insulto/torematrix_labs2
```

### Remember
- Design for extensibility - third parties will create processors
- Include comprehensive capability discovery
- Support both sync and async processors
- Integrate the existing Unstructured.io client from Issue #6

---

## Agent 3 Prompt - Worker Pool & Progress Tracking

You are Agent 3 working on Issue #91 (Worker Pool & Progress Tracking) as part of the TORE Matrix V3 project. You are one of 4 agents working in parallel on Issue #8 (Processing Pipeline Architecture).

### Your Assignment
Implement the worker pool system for concurrent processor execution, resource management, and real-time progress tracking.

### Required Reading
1. **Your detailed instructions**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_PIPELINE.md`
2. **Coordination guide**: `/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md`
3. **Parent issue context**: Read Issue #8 via `gh issue view 8`
4. **Your specific issue**: Read Issue #91 via `gh issue view 91`

### Related Context Files
- **Event system example**: Review EventBus pattern in coordination guide
- **Project overview**: `/home/insulto/torematrix_labs2/CLAUDE.md`
- **Resource patterns**: Check processor metadata in Agent 2's instructions

### Your Deliverables
1. **Worker Pool** (`src/torematrix/processing/workers/pool.py`)
   - Multi-type workers (async/thread/process)
   - Task queue management
   - Priority queue support
   - Worker lifecycle management

2. **Progress Tracker** (`src/torematrix/processing/workers/progress.py`)
   - Real-time progress updates
   - Task-level tracking
   - Pipeline-level aggregation
   - Progress event emission

3. **Resource Monitor** (`src/torematrix/processing/workers/resources.py`)
   - System resource monitoring
   - Resource allocation/limits
   - Throttling mechanism
   - Resource warnings

4. **Worker Configuration** (`src/torematrix/processing/workers/config.py`)
   - Worker pool configuration
   - Resource limit settings
   - Timeout configuration

5. **Tests** (`tests/test_workers.py`)
   - Worker pool lifecycle tests
   - Resource management tests
   - Progress tracking accuracy tests
   - Concurrent execution tests

### Key Interfaces You Define
- `WorkerPool` - Main worker management interface
- `ProgressTracker` - Progress monitoring system
- `ResourceMonitor` - Resource management
- Task submission API (receives from Agent 1)
- Progress events (emit to EventBus)

### Integration Points
- **With Agent 1**: Receive task submissions from pipeline manager
- **With Agent 2**: Execute processors in your workers
- **With Agent 4**: Provide metrics and monitoring hooks

### Working Directory
```bash
cd /home/insulto/torematrix_labs2
```

### Remember
- Implement proper resource isolation
- Support graceful shutdown with task draining
- Emit detailed progress events for real-time tracking
- Handle worker failures without losing tasks

---

## Agent 4 Prompt - Integration, Monitoring & Testing

You are Agent 4 working on Issue #92 (Integration, Monitoring & Testing) as part of the TORE Matrix V3 project. You are one of 4 agents working in parallel on Issue #8 (Processing Pipeline Architecture).

### Your Assignment
Integrate all pipeline components from Agents 1-3, implement comprehensive monitoring with Prometheus, and create a robust testing framework for the entire system.

### Required Reading
1. **Your detailed instructions**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_4_PIPELINE.md`
2. **Coordination guide**: `/home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md`
3. **Parent issue context**: Read Issue #8 via `gh issue view 8`
4. **Your specific issue**: Read Issue #92 via `gh issue view 92`

### Component Instructions to Review
- **Agent 1's work**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_1_PIPELINE.md`
- **Agent 2's work**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_2_PIPELINE.md`
- **Agent 3's work**: `/home/insulto/torematrix_labs2/torematrix_storage/AGENT_3_PIPELINE.md`

### Related Context Files
- **Project overview**: `/home/insulto/torematrix_labs2/CLAUDE.md`
- **Ingestion system**: `/home/insulto/torematrix_labs2/src/torematrix/ingestion/` (for integration)
- **Unstructured integration**: `/home/insulto/torematrix_labs2/src/torematrix/integrations/unstructured/`

### Your Deliverables
1. **System Integration** (`src/torematrix/processing/integration.py`)
   - ProcessingSystem main class
   - Component initialization/wiring
   - Unified API interface
   - System lifecycle management

2. **Monitoring Service** (`src/torematrix/processing/monitoring.py`)
   - Prometheus metrics collection
   - Health check system
   - Performance tracking
   - Alert thresholds

3. **Integration Tests** (`tests/test_pipeline_integration.py`)
   - End-to-end processing tests
   - Component interaction tests
   - Failure scenario tests
   - System recovery tests

4. **Performance Tests** (`tests/test_pipeline_performance.py`)
   - Throughput benchmarks
   - Latency measurements
   - Resource efficiency tests
   - Scalability tests

5. **Monitoring Tests** (`tests/test_monitoring.py`)
   - Metrics accuracy tests
   - Health check validation
   - Alert threshold tests

6. **Deployment Configuration**
   - Docker configuration
   - Kubernetes manifests
   - Prometheus configuration
   - Grafana dashboards

### Key Responsibilities
- Wire up all components from Agents 1-3
- Create unified system interface
- Implement comprehensive monitoring
- Ensure production readiness
- Create integration test suite
- Document deployment process

### Integration Points
- **From Agent 1**: Integrate PipelineManager
- **From Agent 2**: Register all processors
- **From Agent 3**: Connect worker pool and monitoring
- **To Operations**: Provide monitoring/deployment

### Working Directory
```bash
cd /home/insulto/torematrix_labs2
```

### Testing Approach
1. Start with mocks/stubs if other agents aren't ready
2. Create integration tests as components become available
3. Focus on production scenarios and error conditions
4. Benchmark against success metrics in Issue #8

### Remember
- You're the final integration point - ensure everything works together
- Focus on observability and operational excellence
- Create comprehensive documentation for deployment
- Test failure scenarios thoroughly

---

## Quick Start for All Agents

### Initial Setup
```bash
# Navigate to project
cd /home/insulto/torematrix_labs2

# Read your specific instructions
cat /home/insulto/torematrix_labs2/torematrix_storage/AGENT_[1-4]_PIPELINE.md

# Read coordination guide
cat /home/insulto/torematrix_labs2/torematrix_storage/PIPELINE_COORDINATION.md

# Check your GitHub issue
gh issue view [88/90/91/92]

# Start development
mkdir -p src/torematrix/processing/[pipeline|processors|workers]
mkdir -p tests
```

### Communication
- If you need to change an interface, document it in your code
- Use clear docstrings explaining integration points
- Create examples showing how to use your components
- Test your interfaces thoroughly

### Success Criteria
- All tests pass with >90% coverage
- Components integrate smoothly
- Performance meets targets in Issue #8
- Production-ready with monitoring