# Agent 1 Instructions: Core Pipeline Manager & DAG Architecture

## Overview
You are Agent 1 working on Issue #8.1 (Core Pipeline Manager & DAG Architecture) as part of the Processing Pipeline Architecture. Your focus is building the foundation for a flexible, async document processing pipeline with DAG-based stage management.

## Context
- Part of Issue #8: Processing Pipeline Architecture (V3 greenfield project)
- You're working alongside 3 other agents in parallel
- The pipeline will orchestrate document processing through various stages
- Must support parallel execution, checkpointing, and resource management

## Your Specific Tasks

### 1. Pipeline Manager Core (`src/torematrix/processing/pipeline/manager.py`)

```python
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass
from datetime import datetime
import asyncio
import networkx as nx
from pydantic import BaseModel, Field
import logging
from enum import Enum

from ...core.events import EventBus, Event
from ...core.state import StateStore
from .stages import Stage, StageResult, StageStatus
from .config import PipelineConfig, StageConfig

logger = logging.getLogger(__name__)

class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PipelineContext:
    """Context passed through pipeline stages."""
    pipeline_id: str
    document_id: str
    metadata: Dict[str, Any]
    checkpoint_enabled: bool = True
    dry_run: bool = False
    
    def __post_init__(self):
        self.stage_results: Dict[str, StageResult] = {}
        self.created_at = datetime.utcnow()

class PipelineManager:
    """
    Manages document processing pipelines with DAG-based execution.
    
    Supports parallel stage execution, checkpointing, and resource management.
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        event_bus: EventBus,
        state_store: StateStore,
        resource_monitor: Optional['ResourceMonitor'] = None
    ):
        self.config = config
        self.event_bus = event_bus
        self.state_store = state_store
        self.resource_monitor = resource_monitor
        
        # Pipeline state
        self.dag = nx.DiGraph()
        self.stages: Dict[str, Stage] = {}
        self.status = PipelineStatus.IDLE
        self._lock = asyncio.Lock()
        
        # Execution control
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default
        self._cancel_event = asyncio.Event()
        
        self._build_pipeline()
    
    def _build_pipeline(self):
        """Build the pipeline DAG from configuration."""
        # Add stages as nodes
        for stage_config in self.config.stages:
            stage = self._create_stage(stage_config)
            self.stages[stage_config.name] = stage
            self.dag.add_node(stage_config.name, stage=stage)
        
        # Add dependencies as edges
        for stage_config in self.config.stages:
            for dependency in stage_config.dependencies:
                if dependency not in self.stages:
                    raise ValueError(f"Unknown dependency: {dependency}")
                self.dag.add_edge(dependency, stage_config.name)
        
        # Validate DAG
        if not nx.is_directed_acyclic_graph(self.dag):
            cycles = list(nx.simple_cycles(self.dag))
            raise ValueError(f"Pipeline contains cycles: {cycles}")
        
        logger.info(f"Built pipeline with {len(self.stages)} stages")
    
    def _create_stage(self, config: StageConfig) -> Stage:
        """Create a stage instance from configuration."""
        # This will be implemented to dynamically load stage classes
        # For now, return a placeholder
        from .stages import Stage
        return Stage(config)
    
    async def execute(
        self,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        checkpoint: bool = True,
        dry_run: bool = False
    ) -> PipelineContext:
        """
        Execute the pipeline for a document.
        
        Args:
            document_id: Document to process
            metadata: Additional metadata
            checkpoint: Enable checkpointing
            dry_run: Execute without side effects
            
        Returns:
            Pipeline execution context with results
        """
        async with self._lock:
            if self.status == PipelineStatus.RUNNING:
                raise RuntimeError("Pipeline already running")
            self.status = PipelineStatus.RUNNING
        
        context = PipelineContext(
            pipeline_id=f"pipeline-{document_id}-{datetime.utcnow().timestamp()}",
            document_id=document_id,
            metadata=metadata or {},
            checkpoint_enabled=checkpoint,
            dry_run=dry_run
        )
        
        try:
            # Emit start event
            await self.event_bus.emit(Event(
                type="pipeline.started",
                data={"pipeline_id": context.pipeline_id, "document_id": document_id}
            ))
            
            # Check for existing checkpoint
            if checkpoint:
                await self._restore_checkpoint(context)
            
            # Execute stages in topological order
            for stage_name in nx.topological_sort(self.dag):
                # Check if cancelled
                if self._cancel_event.is_set():
                    self.status = PipelineStatus.CANCELLED
                    break
                
                # Wait if paused
                await self._pause_event.wait()
                
                # Skip if already completed (from checkpoint)
                if stage_name in context.stage_results:
                    if context.stage_results[stage_name].status == StageStatus.COMPLETED:
                        continue
                
                # Check dependencies
                if not self._check_dependencies(stage_name, context):
                    logger.warning(f"Skipping {stage_name} due to failed dependencies")
                    continue
                
                # Check resources
                if self.resource_monitor:
                    await self._wait_for_resources(stage_name)
                
                # Execute stage
                await self._execute_stage(stage_name, context)
                
                # Save checkpoint
                if checkpoint and not dry_run:
                    await self._save_checkpoint(context)
            
            # Set final status
            if self._cancel_event.is_set():
                self.status = PipelineStatus.CANCELLED
            elif any(r.status == StageStatus.FAILED for r in context.stage_results.values()):
                self.status = PipelineStatus.FAILED
            else:
                self.status = PipelineStatus.COMPLETED
            
            # Emit completion event
            await self.event_bus.emit(Event(
                type="pipeline.completed",
                data={
                    "pipeline_id": context.pipeline_id,
                    "status": self.status,
                    "duration": (datetime.utcnow() - context.created_at).total_seconds()
                }
            ))
            
        except Exception as e:
            self.status = PipelineStatus.FAILED
            logger.error(f"Pipeline failed: {e}")
            await self.event_bus.emit(Event(
                type="pipeline.failed",
                data={"pipeline_id": context.pipeline_id, "error": str(e)}
            ))
            raise
        
        return context
    
    async def _execute_stage(self, stage_name: str, context: PipelineContext):
        """Execute a single stage."""
        stage = self.stages[stage_name]
        
        logger.info(f"Executing stage: {stage_name}")
        start_time = datetime.utcnow()
        
        try:
            # Emit stage start event
            await self.event_bus.emit(Event(
                type="stage.started",
                data={"pipeline_id": context.pipeline_id, "stage": stage_name}
            ))
            
            # Execute stage
            if context.dry_run:
                result = await stage.dry_run(context)
            else:
                result = await stage.execute(context)
            
            # Store result
            context.stage_results[stage_name] = result
            
            # Emit stage completion event
            await self.event_bus.emit(Event(
                type="stage.completed",
                data={
                    "pipeline_id": context.pipeline_id,
                    "stage": stage_name,
                    "duration": (datetime.utcnow() - start_time).total_seconds(),
                    "status": result.status.value
                }
            ))
            
        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            
            # Store failure result
            context.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status=StageStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=datetime.utcnow()
            )
            
            # Emit failure event
            await self.event_bus.emit(Event(
                type="stage.failed",
                data={
                    "pipeline_id": context.pipeline_id,
                    "stage": stage_name,
                    "error": str(e)
                }
            ))
            
            # Propagate if stage is critical
            if stage.config.critical:
                raise
    
    def _check_dependencies(self, stage_name: str, context: PipelineContext) -> bool:
        """Check if all dependencies completed successfully."""
        for dependency in self.dag.predecessors(stage_name):
            if dependency not in context.stage_results:
                return False
            if context.stage_results[dependency].status != StageStatus.COMPLETED:
                return False
        return True
    
    async def _wait_for_resources(self, stage_name: str):
        """Wait for required resources to be available."""
        stage = self.stages[stage_name]
        requirements = stage.get_resource_requirements()
        
        while not await self.resource_monitor.check_availability(requirements):
            logger.debug(f"Waiting for resources for {stage_name}")
            await asyncio.sleep(1)
    
    async def _save_checkpoint(self, context: PipelineContext):
        """Save pipeline checkpoint to state store."""
        checkpoint_data = {
            "pipeline_id": context.pipeline_id,
            "document_id": context.document_id,
            "metadata": context.metadata,
            "stage_results": {
                name: result.dict() for name, result in context.stage_results.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.state_store.set(
            f"pipeline_checkpoint:{context.document_id}",
            checkpoint_data,
            ttl=self.config.checkpoint_ttl
        )
    
    async def _restore_checkpoint(self, context: PipelineContext):
        """Restore pipeline checkpoint from state store."""
        checkpoint = await self.state_store.get(f"pipeline_checkpoint:{context.document_id}")
        
        if checkpoint:
            logger.info(f"Restoring checkpoint for document {context.document_id}")
            
            # Restore stage results
            for name, result_data in checkpoint.get("stage_results", {}).items():
                context.stage_results[name] = StageResult(**result_data)
            
            # Update metadata
            context.metadata.update(checkpoint.get("metadata", {}))
    
    async def pause(self):
        """Pause pipeline execution."""
        self._pause_event.clear()
        self.status = PipelineStatus.PAUSED
        logger.info("Pipeline paused")
    
    async def resume(self):
        """Resume pipeline execution."""
        self._pause_event.set()
        self.status = PipelineStatus.RUNNING
        logger.info("Pipeline resumed")
    
    async def cancel(self):
        """Cancel pipeline execution."""
        self._cancel_event.set()
        logger.info("Pipeline cancelled")
    
    def get_stage_order(self) -> List[str]:
        """Get topological order of stages."""
        return list(nx.topological_sort(self.dag))
    
    def get_stage_dependencies(self, stage_name: str) -> Set[str]:
        """Get dependencies for a stage."""
        return set(self.dag.predecessors(stage_name))
    
    def get_stage_dependents(self, stage_name: str) -> Set[str]:
        """Get stages that depend on this stage."""
        return set(self.dag.successors(stage_name))
    
    def visualize_pipeline(self) -> str:
        """Generate a visual representation of the pipeline."""
        # This could generate DOT format or other visualization
        return nx.to_dict_of_lists(self.dag)
```

### 2. Pipeline Configuration (`src/torematrix/processing/pipeline/config.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum

class StageType(str, Enum):
    """Types of pipeline stages."""
    PROCESSOR = "processor"
    VALIDATOR = "validator"
    TRANSFORMER = "transformer"
    ROUTER = "router"
    AGGREGATOR = "aggregator"

class ResourceRequirements(BaseModel):
    """Resource requirements for a stage."""
    cpu_cores: float = Field(1.0, ge=0.1, le=16.0)
    memory_mb: int = Field(512, ge=128, le=65536)
    gpu_required: bool = Field(False)
    gpu_memory_mb: Optional[int] = Field(None, ge=512)
    
    @validator('gpu_memory_mb')
    def validate_gpu_memory(cls, v, values):
        if values.get('gpu_required') and v is None:
            raise ValueError("GPU memory must be specified if GPU is required")
        return v

class StageConfig(BaseModel):
    """Configuration for a pipeline stage."""
    name: str = Field(..., min_length=1, max_length=64)
    type: StageType
    processor: str = Field(..., description="Processor class or module path")
    dependencies: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution settings
    timeout: int = Field(300, ge=1, le=3600, description="Timeout in seconds")
    retries: int = Field(3, ge=0, le=10)
    critical: bool = Field(True, description="Fail pipeline if stage fails")
    conditional: Optional[str] = Field(None, description="Condition expression")
    
    # Resource requirements
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    
    # Parallelism
    max_parallel: int = Field(1, ge=1, le=100)
    batch_size: Optional[int] = Field(None, ge=1, le=1000)

class PipelineConfig(BaseModel):
    """Configuration for a processing pipeline."""
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field("1.0.0")
    description: Optional[str] = None
    
    # Stages
    stages: List[StageConfig]
    
    # Global settings
    max_parallel_stages: int = Field(4, ge=1, le=20)
    checkpoint_enabled: bool = Field(True)
    checkpoint_ttl: int = Field(86400, description="Checkpoint TTL in seconds")
    
    # Resource limits
    max_memory_mb: int = Field(8192, ge=512)
    max_cpu_cores: float = Field(8.0, ge=1.0)
    
    # Timeouts
    global_timeout: int = Field(3600, ge=60, description="Global timeout in seconds")
    stage_timeout_multiplier: float = Field(1.0, ge=0.1, le=10.0)
    
    @validator('stages')
    def validate_stage_names(cls, stages):
        names = [s.name for s in stages]
        if len(names) != len(set(names)):
            raise ValueError("Stage names must be unique")
        return stages
    
    @validator('stages')
    def validate_dependencies(cls, stages):
        stage_names = {s.name for s in stages}
        for stage in stages:
            for dep in stage.dependencies:
                if dep not in stage_names:
                    raise ValueError(f"Unknown dependency {dep} in stage {stage.name}")
        return stages
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'PipelineConfig':
        """Load configuration from YAML file."""
        import yaml
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'PipelineConfig':
        """Load configuration from JSON file."""
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
```

### 3. Stage Management (`src/torematrix/processing/pipeline/stages.py`)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from .config import StageConfig, ResourceRequirements

logger = logging.getLogger(__name__)

class StageStatus(str, Enum):
    """Status of stage execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StageResult(BaseModel):
    """Result of stage execution."""
    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class Stage(ABC):
    """
    Abstract base class for pipeline stages.
    
    All stages must implement the execute method and can optionally
    override other lifecycle methods.
    """
    
    def __init__(self, config: StageConfig):
        self.config = config
        self.name = config.name
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the stage.
        
        Called once before first execution. Use for setting up
        connections, loading models, etc.
        """
        if self._initialized:
            return
        
        logger.info(f"Initializing stage: {self.name}")
        await self._initialize()
        self._initialized = True
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Stage-specific initialization logic."""
        pass
    
    @abstractmethod
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """
        Execute the stage processing.
        
        Args:
            context: Pipeline execution context
            
        Returns:
            Stage execution result
        """
        pass
    
    async def dry_run(self, context: 'PipelineContext') -> StageResult:
        """
        Perform a dry run of the stage.
        
        Default implementation calls validate() and returns success.
        Override for stage-specific dry run logic.
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate inputs
            self.validate(context)
            
            # Return success without executing
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data={"dry_run": True}
            )
            
        except Exception as e:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=f"Dry run validation failed: {str(e)}"
            )
    
    def validate(self, context: 'PipelineContext') -> None:
        """
        Validate stage inputs and configuration.
        
        Raises:
            ValueError: If validation fails
        """
        # Check required dependencies
        for dep in self.config.dependencies:
            if dep not in context.stage_results:
                raise ValueError(f"Missing dependency: {dep}")
            if context.stage_results[dep].status != StageStatus.COMPLETED:
                raise ValueError(f"Dependency {dep} did not complete successfully")
        
        # Stage-specific validation
        self._validate(context)
    
    def _validate(self, context: 'PipelineContext') -> None:
        """Override for stage-specific validation."""
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up stage resources.
        
        Called when pipeline is shutting down or stage is being replaced.
        """
        if self._initialized:
            logger.info(f"Cleaning up stage: {self.name}")
            await self._cleanup()
            self._initialized = False
    
    async def _cleanup(self) -> None:
        """Override for stage-specific cleanup."""
        pass
    
    def get_resource_requirements(self) -> ResourceRequirements:
        """Get resource requirements for this stage."""
        return self.config.resources
    
    def get_metrics(self) -> Dict[str, float]:
        """Get stage metrics for monitoring."""
        return {}
    
    def should_execute(self, context: 'PipelineContext') -> bool:
        """
        Check if stage should execute based on conditions.
        
        Returns:
            True if stage should execute, False to skip
        """
        if not self.config.conditional:
            return True
        
        # Evaluate condition expression
        # This would use a safe expression evaluator
        try:
            # Placeholder for expression evaluation
            return True
        except Exception as e:
            logger.warning(f"Condition evaluation failed for {self.name}: {e}")
            return False

class ProcessorStage(Stage):
    """Base class for document processor stages."""
    
    async def _initialize(self) -> None:
        """Initialize processor."""
        # Load processor based on config
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute document processing."""
        start_time = datetime.utcnow()
        
        try:
            # Get document from context
            document_id = context.document_id
            
            # Process document
            # This would call the actual processor
            result_data = {
                "processed": True,
                "document_id": document_id
            }
            
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"Processing failed in {self.name}: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )

class ValidationStage(Stage):
    """Base class for validation stages."""
    
    async def _initialize(self) -> None:
        """Initialize validator."""
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute validation."""
        # Implement validation logic
        pass

class RouterStage(Stage):
    """Base class for routing stages that direct pipeline flow."""
    
    async def _initialize(self) -> None:
        """Initialize router."""
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute routing logic."""
        # Implement routing based on conditions
        pass
```

### 4. Resource Monitoring (`src/torematrix/processing/pipeline/resources.py`)

```python
import asyncio
import psutil
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

from .config import ResourceRequirements

logger = logging.getLogger(__name__)

@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: int
    memory_percent: float
    gpu_memory_mb: Optional[int] = None
    gpu_percent: Optional[float] = None

class ResourceMonitor:
    """
    Monitors system resources and manages allocation for pipeline stages.
    
    Tracks CPU, memory, and GPU usage to ensure pipeline doesn't
    exceed system capabilities.
    """
    
    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 80.0,
        update_interval: float = 1.0,
        history_size: int = 60
    ):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.update_interval = update_interval
        
        # Resource tracking
        self.history: deque[ResourceUsage] = deque(maxlen=history_size)
        self.current_usage: Optional[ResourceUsage] = None
        self.allocated_resources: Dict[str, ResourceRequirements] = {}
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start resource monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitor started")
    
    async def stop(self):
        """Stop resource monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect resource usage
                usage = await self._collect_usage()
                
                async with self._lock:
                    self.current_usage = usage
                    self.history.append(usage)
                
                # Log if usage is high
                if usage.cpu_percent > self.max_cpu_percent:
                    logger.warning(f"High CPU usage: {usage.cpu_percent:.1f}%")
                if usage.memory_percent > self.max_memory_percent:
                    logger.warning(f"High memory usage: {usage.memory_percent:.1f}%")
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _collect_usage(self) -> ResourceUsage:
        """Collect current resource usage."""
        # Run CPU collection in thread pool as it can block
        loop = asyncio.get_event_loop()
        cpu_percent = await loop.run_in_executor(
            None, 
            psutil.cpu_percent, 
            self.update_interval
        )
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        # GPU monitoring would go here (using pynvml or similar)
        gpu_memory_mb = None
        gpu_percent = None
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_mb=memory.used // (1024 * 1024),
            memory_percent=memory.percent,
            gpu_memory_mb=gpu_memory_mb,
            gpu_percent=gpu_percent
        )
    
    async def check_availability(self, requirements: ResourceRequirements) -> bool:
        """
        Check if required resources are available.
        
        Args:
            requirements: Resource requirements to check
            
        Returns:
            True if resources are available
        """
        if not self.current_usage:
            return True  # No data yet, assume available
        
        # Calculate available resources
        cpu_available = 100.0 - self.current_usage.cpu_percent
        memory_available_mb = psutil.virtual_memory().available // (1024 * 1024)
        
        # Check CPU
        cpu_required_percent = requirements.cpu_cores * 100.0 / psutil.cpu_count()
        if cpu_required_percent > cpu_available:
            return False
        
        # Check memory
        if requirements.memory_mb > memory_available_mb:
            return False
        
        # Check if we'd exceed limits
        projected_cpu = self.current_usage.cpu_percent + cpu_required_percent
        if projected_cpu > self.max_cpu_percent:
            return False
        
        memory_total_mb = psutil.virtual_memory().total // (1024 * 1024)
        projected_memory_percent = (
            (self.current_usage.memory_mb + requirements.memory_mb) / memory_total_mb * 100
        )
        if projected_memory_percent > self.max_memory_percent:
            return False
        
        # GPU checks would go here
        if requirements.gpu_required:
            # Placeholder for GPU availability check
            pass
        
        return True
    
    async def allocate(self, stage_name: str, requirements: ResourceRequirements):
        """Allocate resources for a stage."""
        async with self._lock:
            self.allocated_resources[stage_name] = requirements
    
    async def release(self, stage_name: str):
        """Release resources allocated to a stage."""
        async with self._lock:
            self.allocated_resources.pop(stage_name, None)
    
    def get_allocated_totals(self) -> ResourceRequirements:
        """Get total allocated resources."""
        total_cpu = sum(r.cpu_cores for r in self.allocated_resources.values())
        total_memory = sum(r.memory_mb for r in self.allocated_resources.values())
        
        return ResourceRequirements(
            cpu_cores=total_cpu,
            memory_mb=total_memory
        )
    
    def get_usage_history(self, minutes: int = 5) -> List[ResourceUsage]:
        """Get resource usage history."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [u for u in self.history if u.timestamp > cutoff]
    
    def get_average_usage(self, minutes: int = 5) -> Optional[ResourceUsage]:
        """Get average resource usage over time period."""
        history = self.get_usage_history(minutes)
        if not history:
            return None
        
        avg_cpu = sum(u.cpu_percent for u in history) / len(history)
        avg_memory = sum(u.memory_mb for u in history) / len(history)
        avg_memory_percent = sum(u.memory_percent for u in history) / len(history)
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=avg_cpu,
            memory_mb=int(avg_memory),
            memory_percent=avg_memory_percent
        )
```

### 5. Pipeline Templates (`src/torematrix/processing/pipeline/templates.py`)

```python
from typing import Dict, Any
from .config import PipelineConfig, StageConfig, StageType

class PipelineTemplate:
    """Base class for pipeline templates."""
    
    @classmethod
    def create_config(cls, **kwargs) -> PipelineConfig:
        """Create pipeline configuration from template."""
        raise NotImplementedError

class StandardDocumentPipeline(PipelineTemplate):
    """Standard document processing pipeline template."""
    
    @classmethod
    def create_config(
        cls,
        name: str = "standard-document-pipeline",
        enable_ocr: bool = True,
        enable_translation: bool = False,
        **kwargs
    ) -> PipelineConfig:
        """Create standard document processing pipeline."""
        stages = [
            StageConfig(
                name="validation",
                type=StageType.VALIDATOR,
                processor="torematrix.processing.validators.DocumentValidator",
                dependencies=[],
                config={
                    "max_size_mb": kwargs.get("max_size_mb", 100),
                    "allowed_types": kwargs.get("allowed_types", [
                        "pdf", "docx", "txt", "html"
                    ])
                }
            ),
            StageConfig(
                name="extraction",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.UnstructuredProcessor",
                dependencies=["validation"],
                config={
                    "strategy": kwargs.get("extraction_strategy", "auto"),
                    "include_metadata": True
                }
            ),
            StageConfig(
                name="text_processing",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.TextProcessor",
                dependencies=["extraction"],
                config={
                    "normalize": True,
                    "remove_pii": kwargs.get("remove_pii", False)
                }
            )
        ]
        
        # Add OCR stage if enabled
        if enable_ocr:
            stages.append(StageConfig(
                name="ocr",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.OCRProcessor",
                dependencies=["extraction"],
                conditional="has_images",
                config={
                    "language": kwargs.get("ocr_language", "eng"),
                    "enhance": True
                }
            ))
        
        # Add translation stage if enabled
        if enable_translation:
            stages.append(StageConfig(
                name="translation",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.TranslationProcessor",
                dependencies=["text_processing"],
                config={
                    "target_language": kwargs.get("target_language", "en"),
                    "preserve_formatting": True
                }
            ))
        
        # Add final aggregation stage
        stages.append(StageConfig(
            name="aggregation",
            type=StageType.AGGREGATOR,
            processor="torematrix.processing.processors.ResultAggregator",
            dependencies=[s.name for s in stages[1:]],  # Depends on all processors
            config={
                "output_format": kwargs.get("output_format", "json")
            }
        ))
        
        return PipelineConfig(
            name=name,
            stages=stages,
            max_parallel_stages=kwargs.get("max_parallel_stages", 4),
            checkpoint_enabled=kwargs.get("checkpoint_enabled", True)
        )

# Template registry
PIPELINE_TEMPLATES = {
    "standard": StandardDocumentPipeline,
    # Add more templates here
}

def get_template(template_name: str) -> PipelineTemplate:
    """Get pipeline template by name."""
    if template_name not in PIPELINE_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    return PIPELINE_TEMPLATES[template_name]
```

### 6. Unit Tests (`tests/unit/processing/pipeline/test_manager.py`)

```python
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import networkx as nx

from torematrix.processing.pipeline.manager import (
    PipelineManager,
    PipelineContext,
    PipelineStatus
)
from torematrix.processing.pipeline.config import (
    PipelineConfig,
    StageConfig,
    StageType
)
from torematrix.processing.pipeline.stages import Stage, StageResult, StageStatus
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore

class MockStage(Stage):
    """Mock stage for testing."""
    
    def __init__(self, config: StageConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.executed = False
    
    async def _initialize(self):
        pass
    
    async def execute(self, context: PipelineContext) -> StageResult:
        self.executed = True
        
        if self.should_fail:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                error="Mock failure"
            )
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            data={"mock": True}
        )

@pytest.fixture
async def pipeline_config():
    """Create test pipeline configuration."""
    return PipelineConfig(
        name="test-pipeline",
        stages=[
            StageConfig(
                name="stage1",
                type=StageType.PROCESSOR,
                processor="mock.Stage1",
                dependencies=[]
            ),
            StageConfig(
                name="stage2",
                type=StageType.PROCESSOR,
                processor="mock.Stage2",
                dependencies=["stage1"]
            ),
            StageConfig(
                name="stage3",
                type=StageType.PROCESSOR,
                processor="mock.Stage3",
                dependencies=["stage1"]
            ),
            StageConfig(
                name="stage4",
                type=StageType.AGGREGATOR,
                processor="mock.Stage4",
                dependencies=["stage2", "stage3"]
            )
        ]
    )

@pytest.fixture
async def event_bus():
    """Create mock event bus."""
    bus = Mock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus

@pytest.fixture
async def state_store():
    """Create mock state store."""
    store = Mock(spec=StateStore)
    store.get = AsyncMock(return_value=None)
    store.set = AsyncMock()
    return store

class TestPipelineManager:
    """Test cases for PipelineManager."""
    
    async def test_pipeline_construction(self, pipeline_config, event_bus, state_store):
        """Test pipeline DAG construction."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Check DAG structure
        assert len(manager.stages) == 4
        assert nx.is_directed_acyclic_graph(manager.dag)
        
        # Check dependencies
        assert set(manager.get_stage_dependencies("stage2")) == {"stage1"}
        assert set(manager.get_stage_dependencies("stage4")) == {"stage2", "stage3"}
        
        # Check topological order
        order = manager.get_stage_order()
        assert order.index("stage1") < order.index("stage2")
        assert order.index("stage1") < order.index("stage3")
        assert order.index("stage2") < order.index("stage4")
        assert order.index("stage3") < order.index("stage4")
    
    async def test_cycle_detection(self, event_bus, state_store):
        """Test that cycles are detected in pipeline."""
        # Create config with cycle
        config = PipelineConfig(
            name="cyclic-pipeline",
            stages=[
                StageConfig(name="A", type=StageType.PROCESSOR, processor="A", dependencies=["B"]),
                StageConfig(name="B", type=StageType.PROCESSOR, processor="B", dependencies=["C"]),
                StageConfig(name="C", type=StageType.PROCESSOR, processor="C", dependencies=["A"])
            ]
        )
        
        with pytest.raises(ValueError, match="Pipeline contains cycles"):
            PipelineManager(config, event_bus, state_store)
    
    async def test_pipeline_execution(self, pipeline_config, event_bus, state_store):
        """Test successful pipeline execution."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute pipeline
        context = await manager.execute("doc123", {"test": True})
        
        # Check execution
        assert context.document_id == "doc123"
        assert len(context.stage_results) == 4
        
        # Check all stages executed
        for stage in manager.stages.values():
            assert stage.executed
        
        # Check events emitted
        event_calls = event_bus.emit.call_args_list
        event_types = [call[0][0].type for call in event_calls]
        assert "pipeline.started" in event_types
        assert "pipeline.completed" in event_types
        assert event_types.count("stage.started") == 4
        assert event_types.count("stage.completed") == 4
    
    async def test_stage_failure_handling(self, pipeline_config, event_bus, state_store):
        """Test pipeline handling of stage failures."""
        def create_stage(config):
            if config.name == "stage2":
                return MockStage(config, should_fail=True)
            return MockStage(config)
        
        with patch.object(PipelineManager, '_create_stage', side_effect=create_stage):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute pipeline
        context = await manager.execute("doc123")
        
        # Check stage2 failed
        assert context.stage_results["stage2"].status == StageStatus.FAILED
        
        # Check stage4 was skipped (depends on failed stage2)
        assert "stage4" not in context.stage_results or \
               context.stage_results["stage4"].status != StageStatus.COMPLETED
        
        # Check pipeline status
        assert manager.status == PipelineStatus.FAILED
    
    async def test_checkpoint_save_restore(self, pipeline_config, event_bus, state_store):
        """Test checkpoint saving and restoration."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute with checkpointing
        context = await manager.execute("doc123", checkpoint=True)
        
        # Verify checkpoints were saved
        assert state_store.set.called
        checkpoint_key = f"pipeline_checkpoint:doc123"
        saved_checkpoint = state_store.set.call_args[0][1]
        assert saved_checkpoint["document_id"] == "doc123"
        assert "stage_results" in saved_checkpoint
    
    async def test_pause_resume(self, pipeline_config, event_bus, state_store):
        """Test pipeline pause and resume."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Start execution in background
        exec_task = asyncio.create_task(manager.execute("doc123"))
        
        # Pause immediately
        await manager.pause()
        assert manager.status == PipelineStatus.PAUSED
        
        # Give time for pause to take effect
        await asyncio.sleep(0.1)
        
        # Resume
        await manager.resume()
        
        # Wait for completion
        context = await exec_task
        
        # Should complete successfully
        assert len(context.stage_results) == 4
    
    async def test_cancel(self, pipeline_config, event_bus, state_store):
        """Test pipeline cancellation."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Start execution in background
        exec_task = asyncio.create_task(manager.execute("doc123"))
        
        # Cancel immediately
        await manager.cancel()
        
        # Wait for completion
        context = await exec_task
        
        # Check cancelled
        assert manager.status == PipelineStatus.CANCELLED
    
    async def test_dry_run(self, pipeline_config, event_bus, state_store):
        """Test dry run execution."""
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(pipeline_config, event_bus, state_store)
        
        # Execute dry run
        context = await manager.execute("doc123", dry_run=True)
        
        # Check all stages marked as dry run
        for result in context.stage_results.values():
            assert result.data.get("dry_run") == True
        
        # Check no checkpoints saved in dry run
        assert not state_store.set.called
    
    async def test_resource_monitoring(self, pipeline_config, event_bus, state_store):
        """Test resource monitoring integration."""
        from torematrix.processing.pipeline.resources import ResourceMonitor
        
        monitor = Mock(spec=ResourceMonitor)
        monitor.check_availability = AsyncMock(return_value=True)
        
        with patch.object(PipelineManager, '_create_stage', side_effect=lambda c: MockStage(c)):
            manager = PipelineManager(
                pipeline_config, 
                event_bus, 
                state_store,
                resource_monitor=monitor
            )
        
        # Execute pipeline
        await manager.execute("doc123")
        
        # Check resource availability was checked
        assert monitor.check_availability.called
```

## Dependencies You Can Use
- From Issue #1 (Event Bus System):
  - `EventBus` - For pipeline events
  - `Event` - Event data structure
- From Issue #3 (State Management):
  - `StateStore` - For checkpoint storage
  - State persistence mechanisms

## Important Notes
1. **Async Architecture**: Everything must be async/await compatible
2. **DAG Validation**: Ensure no cycles in pipeline dependencies
3. **Resource Management**: Monitor and limit resource usage
4. **Checkpoint Support**: Enable resume from failure
5. **Dry Run Mode**: Support validation without execution
6. **Event Emission**: Emit events for all pipeline state changes

## Testing Requirements
- Unit tests for all components
- Test DAG construction and validation
- Test parallel execution scenarios
- Test failure handling and recovery
- Test resource monitoring
- Test checkpoint/resume functionality

## Coordination
- Agent 2 will create processor plugins that your pipeline executes
- Agent 3 will use your events for progress tracking
- Agent 4 will integrate all components together

## Success Criteria
- [ ] Complete pipeline manager with DAG execution
- [ ] Stage lifecycle management implemented
- [ ] Resource monitoring and limits working
- [ ] Checkpoint/resume functionality tested
- [ ] Dry run mode operational
- [ ] 90%+ test coverage

Start by implementing the pipeline manager, then the configuration system, stage management, and finally resource monitoring. Focus on clean abstractions and extensibility.