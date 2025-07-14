"""
Core Pipeline Manager with DAG-based execution.

Manages document processing pipelines with support for parallel execution,
checkpointing, and resource management.
"""

from typing import Dict, List, Any, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import networkx as nx
from pydantic import BaseModel, Field
import logging
from enum import Enum
import uuid

from ...core.events import EventBus, Event
from .state_store import StateStore  # Temporary until core StateStore is available
from .stages import Stage, StageResult, StageStatus, ProcessorStage, ValidationStage, RouterStage, AggregatorStage
from .config import PipelineConfig, StageConfig, StageType
from .exceptions import (
    PipelineExecutionError, 
    StageDependencyError,
    StageTimeoutError,
    ResourceError,
    PipelineCancelledError
)
from .dag import build_dag, get_execution_order, get_parallel_groups

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
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoint_enabled: bool = True
    dry_run: bool = False
    
    def __post_init__(self):
        self.stage_results: Dict[str, StageResult] = {}
        self.created_at = datetime.utcnow()
        self.user_data: Dict[str, Any] = {}  # For passing data between stages


class PipelineManager:
    """
    Manages document processing pipelines with DAG-based execution.
    
    Supports parallel stage execution, checkpointing, and resource management.
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        event_bus: EventBus,
        state_store: Optional[StateStore] = None,
        resource_monitor: Optional['ResourceMonitor'] = None
    ):
        self.config = config
        self.event_bus = event_bus
        self.state_store = state_store or StateStore()  # Use temporary if not provided
        self.resource_monitor = resource_monitor
        
        # Pipeline state
        self.dag: nx.DiGraph = nx.DiGraph()
        self.stages: Dict[str, Stage] = {}
        self.status = PipelineStatus.IDLE
        self._lock = asyncio.Lock()
        
        # Execution control
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default
        self._cancel_event = asyncio.Event()
        
        # Active executions
        self._active_contexts: Dict[str, PipelineContext] = {}
        
        self._build_pipeline()
    
    def _build_pipeline(self):
        """Build the pipeline DAG from configuration."""
        # Build DAG
        self.dag = build_dag(self.config.stages)
        
        # Create stage instances
        for stage_config in self.config.stages:
            stage = self._create_stage(stage_config)
            self.stages[stage_config.name] = stage
        
        logger.info(f"Built pipeline '{self.config.name}' with {len(self.stages)} stages")
    
    def _create_stage(self, config: StageConfig) -> Stage:
        """Create a stage instance from configuration."""
        # Map stage types to classes
        stage_classes = {
            StageType.PROCESSOR: ProcessorStage,
            StageType.VALIDATOR: ValidationStage,
            StageType.ROUTER: RouterStage,
            StageType.AGGREGATOR: AggregatorStage,
            StageType.TRANSFORMER: ProcessorStage,  # Use ProcessorStage for now
        }
        
        stage_class = stage_classes.get(config.type, ProcessorStage)
        return stage_class(config)
    
    async def create_pipeline(
        self,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        pipeline_name: Optional[str] = None
    ) -> str:
        """
        Create a new pipeline execution instance.
        
        Args:
            document_id: Document to process
            metadata: Additional metadata
            pipeline_name: Optional pipeline name override
            
        Returns:
            Pipeline execution ID
        """
        pipeline_id = f"pipeline-{uuid.uuid4()}"
        
        context = PipelineContext(
            pipeline_id=pipeline_id,
            document_id=document_id,
            metadata=metadata or {},
            checkpoint_enabled=self.config.checkpoint_enabled
        )
        
        async with self._lock:
            self._active_contexts[pipeline_id] = context
        
        return pipeline_id
    
    async def execute(
        self,
        pipeline_id: Optional[str] = None,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        checkpoint: Optional[bool] = None,
        dry_run: bool = False
    ) -> PipelineContext:
        """
        Execute the pipeline for a document.
        
        Can either use an existing pipeline_id or create a new one.
        
        Args:
            pipeline_id: Existing pipeline ID (optional)
            document_id: Document to process (required if no pipeline_id)
            metadata: Additional metadata
            checkpoint: Enable checkpointing (overrides config)
            dry_run: Execute without side effects
            
        Returns:
            Pipeline execution context with results
        """
        # Get or create context
        if pipeline_id:
            async with self._lock:
                if pipeline_id not in self._active_contexts:
                    raise ValueError(f"Unknown pipeline ID: {pipeline_id}")
                context = self._active_contexts[pipeline_id]
        else:
            if not document_id:
                raise ValueError("Either pipeline_id or document_id must be provided")
            pipeline_id = await self.create_pipeline(document_id, metadata)
            context = self._active_contexts[pipeline_id]
        
        # Apply execution options
        if checkpoint is not None:
            context.checkpoint_enabled = checkpoint
        context.dry_run = dry_run
        
        # Check if already running
        async with self._lock:
            if self.status == PipelineStatus.RUNNING:
                raise RuntimeError("Pipeline already running")
            self.status = PipelineStatus.RUNNING
        
        try:
            # Emit start event
            await self.event_bus.publish(Event(
                event_type="pipeline.started",
                payload={"pipeline_id": context.pipeline_id, "document_id": context.document_id}
            ))
            
            # Check for existing checkpoint
            if context.checkpoint_enabled:
                await self._restore_checkpoint(context)
            
            # Execute stages
            await self._execute_pipeline(context)
            
            # Set final status
            if self._cancel_event.is_set():
                self.status = PipelineStatus.CANCELLED
            elif any(r.status == StageStatus.FAILED for r in context.stage_results.values()):
                self.status = PipelineStatus.FAILED
            else:
                self.status = PipelineStatus.COMPLETED
            
            # Emit completion event
            await self.event_bus.publish(Event(
                event_type="pipeline.completed",
                payload={
                    "pipeline_id": context.pipeline_id,
                    "status": self.status.value,
                    "duration": (datetime.utcnow() - context.created_at).total_seconds()
                }
            ))
            
        except Exception as e:
            self.status = PipelineStatus.FAILED
            logger.error(f"Pipeline failed: {e}")
            await self.event_bus.publish(Event(
                event_type="pipeline.failed",
                payload={"pipeline_id": context.pipeline_id, "error": str(e)}
            ))
            raise
        finally:
            # Reset control flags
            self._cancel_event.clear()
            async with self._lock:
                self.status = PipelineStatus.IDLE
        
        return context
    
    async def _execute_pipeline(self, context: PipelineContext):
        """Execute pipeline stages according to DAG."""
        # Get parallel execution groups
        parallel_groups = get_parallel_groups(self.dag)
        
        for group in parallel_groups:
            # Check if cancelled
            if self._cancel_event.is_set():
                raise PipelineCancelledError("Pipeline execution cancelled")
            
            # Wait if paused
            await self._pause_event.wait()
            
            # Filter stages that should execute
            stages_to_execute = []
            for stage_name in group:
                # Skip if already completed (from checkpoint)
                if stage_name in context.stage_results:
                    if context.stage_results[stage_name].status == StageStatus.COMPLETED:
                        continue
                
                # Check dependencies
                if not self._check_dependencies(stage_name, context):
                    logger.warning(f"Skipping {stage_name} due to failed dependencies")
                    continue
                
                # Check if stage should execute (conditions)
                stage = self.stages[stage_name]
                if not stage.should_execute(context):
                    logger.info(f"Skipping {stage_name} due to condition")
                    context.stage_results[stage_name] = StageResult(
                        stage_name=stage_name,
                        status=StageStatus.SKIPPED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow()
                    )
                    continue
                
                stages_to_execute.append(stage_name)
            
            # Execute stages in parallel (up to max_parallel_stages)
            if stages_to_execute:
                await self._execute_parallel_stages(stages_to_execute, context)
            
            # Save checkpoint after each group
            if context.checkpoint_enabled and not context.dry_run:
                await self._save_checkpoint(context)
    
    async def _execute_parallel_stages(
        self, 
        stage_names: List[str], 
        context: PipelineContext
    ):
        """Execute multiple stages in parallel."""
        # Limit parallel execution
        semaphore = asyncio.Semaphore(self.config.max_parallel_stages)
        
        async def execute_with_semaphore(stage_name: str):
            async with semaphore:
                await self._execute_stage(stage_name, context)
        
        # Execute all stages
        tasks = [execute_with_semaphore(name) for name in stage_names]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_stage(self, stage_name: str, context: PipelineContext):
        """Execute a single stage."""
        stage = self.stages[stage_name]
        
        # Check resources if monitor available
        if self.resource_monitor:
            requirements = stage.get_resource_requirements()
            max_wait = 60  # seconds
            start_wait = datetime.utcnow()
            
            while not await self.resource_monitor.check_availability(requirements):
                if (datetime.utcnow() - start_wait).total_seconds() > max_wait:
                    raise ResourceError(
                        f"Resources not available for stage {stage_name} after {max_wait}s",
                        required=requirements.model_dump()
                    )
                logger.debug(f"Waiting for resources for {stage_name}")
                await asyncio.sleep(1)
            
            # Allocate resources
            await self.resource_monitor.allocate(stage_name, requirements)
        
        logger.info(f"Executing stage: {stage_name}")
        start_time = datetime.utcnow()
        
        try:
            # Initialize stage if needed
            if not stage._initialized:
                await stage.initialize()
            
            # Emit stage start event
            await self.event_bus.publish(Event(
                event_type="stage.started",
                payload={"pipeline_id": context.pipeline_id, "stage": stage_name}
            ))
            
            # Execute with timeout
            timeout = stage.config.timeout * self.config.stage_timeout_multiplier
            
            if context.dry_run:
                result = await asyncio.wait_for(
                    stage.dry_run(context), 
                    timeout=timeout
                )
            else:
                result = await asyncio.wait_for(
                    stage.execute(context), 
                    timeout=timeout
                )
            
            # Store result
            context.stage_results[stage_name] = result
            
            # Emit stage completion event
            await self.event_bus.publish(Event(
                event_type="stage.completed",
                payload={
                    "pipeline_id": context.pipeline_id,
                    "stage": stage_name,
                    "duration": (datetime.utcnow() - start_time).total_seconds(),
                    "status": result.status.value
                }
            ))
            
        except asyncio.TimeoutError:
            error = StageTimeoutError(stage_name, int(timeout))
            logger.error(str(error))
            
            # Store failure result
            context.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(error)
            )
            
            # Emit failure event
            await self.event_bus.publish(Event(
                event_type="stage.failed",
                payload={
                    "pipeline_id": context.pipeline_id,
                    "stage": stage_name,
                    "error": str(error)
                }
            ))
            
            # Propagate if stage is critical
            if stage.config.critical:
                raise error
                
        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            
            # Store failure result
            context.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )
            
            # Emit failure event
            await self.event_bus.publish(Event(
                event_type="stage.failed",
                payload={
                    "pipeline_id": context.pipeline_id,
                    "stage": stage_name,
                    "error": str(e)
                }
            ))
            
            # Propagate if stage is critical
            if stage.config.critical:
                raise
        
        finally:
            # Release resources
            if self.resource_monitor:
                await self.resource_monitor.release(stage_name)
    
    def _check_dependencies(self, stage_name: str, context: PipelineContext) -> bool:
        """Check if all dependencies completed successfully."""
        for dependency in self.dag.predecessors(stage_name):
            if dependency not in context.stage_results:
                return False
            if context.stage_results[dependency].status != StageStatus.COMPLETED:
                return False
        return True
    
    async def _save_checkpoint(self, context: PipelineContext):
        """Save pipeline checkpoint to state store."""
        checkpoint_data = {
            "pipeline_id": context.pipeline_id,
            "document_id": context.document_id,
            "metadata": context.metadata,
            "user_data": context.user_data,
            "stage_results": {
                name: result.model_dump() for name, result in context.stage_results.items()
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
                # Convert ISO format strings back to datetime
                if 'start_time' in result_data:
                    result_data['start_time'] = datetime.fromisoformat(result_data['start_time'])
                if 'end_time' in result_data and result_data['end_time']:
                    result_data['end_time'] = datetime.fromisoformat(result_data['end_time'])
                
                context.stage_results[name] = StageResult(**result_data)
            
            # Restore metadata and user data
            context.metadata.update(checkpoint.get("metadata", {}))
            context.user_data.update(checkpoint.get("user_data", {}))
    
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
        return get_execution_order(self.dag)
    
    def get_stage_dependencies(self, stage_name: str) -> Set[str]:
        """Get dependencies for a stage."""
        return set(self.dag.predecessors(stage_name))
    
    def get_stage_dependents(self, stage_name: str) -> Set[str]:
        """Get stages that depend on this stage."""
        return set(self.dag.successors(stage_name))
    
    def get_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get status of a pipeline execution."""
        if pipeline_id not in self._active_contexts:
            return {"error": "Unknown pipeline ID"}
        
        context = self._active_contexts[pipeline_id]
        
        # Calculate progress
        total_stages = len(self.stages)
        completed_stages = sum(
            1 for r in context.stage_results.values() 
            if r.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
        )
        progress = completed_stages / total_stages if total_stages > 0 else 0
        
        return {
            "pipeline_id": pipeline_id,
            "document_id": context.document_id,
            "status": self.status.value,
            "progress": progress,
            "completed_stages": completed_stages,
            "total_stages": total_stages,
            "stage_results": {
                name: {
                    "status": result.status.value,
                    "duration": result.duration,
                    "error": result.error
                }
                for name, result in context.stage_results.items()
            },
            "created_at": context.created_at.isoformat(),
            "duration": (datetime.utcnow() - context.created_at).total_seconds()
        }
    
    def visualize_pipeline(self) -> Dict[str, Any]:
        """Generate a visual representation of the pipeline."""
        return {
            "nodes": [
                {
                    "id": node,
                    "type": self.stages[node].config.type.value,
                    "dependencies": list(self.dag.predecessors(node))
                }
                for node in self.dag.nodes()
            ],
            "edges": [
                {"from": u, "to": v} 
                for u, v in self.dag.edges()
            ],
            "execution_order": self.get_stage_order()
        }
    
    async def cleanup(self):
        """Clean up pipeline resources."""
        # Clean up all stages
        for stage in self.stages.values():
            await stage.cleanup()
        
        # Clear active contexts
        self._active_contexts.clear()