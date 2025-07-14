"""
Stage management for the pipeline system.

Provides abstract base classes and implementations for different stage types.
"""

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
        """Calculate stage execution duration in seconds."""
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
            # In real implementation, this would parse and evaluate
            # the condition against the context
            return True
        except Exception as e:
            logger.warning(f"Condition evaluation failed for {self.name}: {e}")
            return False


class ProcessorStage(Stage):
    """Stage that executes a document processor from the processor plugin system."""
    
    def __init__(self, config: StageConfig):
        super().__init__(config)
        self.processor = None
        self._registry = None
    
    async def _initialize(self) -> None:
        """Initialize processor from registry."""
        try:
            # Import registry on demand to avoid circular imports
            from ..processors.registry import get_registry
            self._registry = get_registry()
            
            # Get processor instance
            self.processor = await self._registry.get_processor(
                self.config.processor,
                self.config.config
            )
            logger.info(f"Initialized processor: {self.config.processor} for stage {self.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize processor {self.config.processor}: {e}")
            raise
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute document processing using the processor."""
        start_time = datetime.utcnow()
        
        if not self.processor:
            raise RuntimeError(f"Processor not initialized: {self.config.processor}")
        
        try:
            # Convert pipeline context to processor context
            processor_context = self._create_processor_context(context)
            
            # Execute processor
            logger.debug(f"Executing processor: {self.config.processor}")
            processor_result = await self.processor.process(processor_context)
            
            # Convert processor result to stage result
            stage_result = processor_result.to_stage_result()
            stage_result.stage_name = self.name  # Override with stage name
            
            logger.info(f"Processor stage completed: {self.name} ({processor_result.status})")
            return stage_result
            
        except Exception as e:
            logger.error(f"Processing failed in {self.name}: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )
    
    def _create_processor_context(self, pipeline_context: 'PipelineContext'):
        """Convert pipeline context to processor context."""
        from ..processors.base import ProcessorContext
        
        # Extract document information from pipeline context
        file_path = pipeline_context.metadata.get('file_path', '')
        mime_type = pipeline_context.metadata.get('mime_type', '')
        
        # Get results from previous stages
        previous_results = {}
        for stage_name, stage_result in pipeline_context.stage_results.items():
            if stage_result.status == StageStatus.COMPLETED:
                previous_results[stage_name] = stage_result.data
        
        return ProcessorContext(
            document_id=pipeline_context.document_id,
            file_path=file_path,
            mime_type=mime_type,
            metadata=pipeline_context.metadata.copy(),
            previous_results=previous_results,
            pipeline_context=pipeline_context
        )
    
    def _validate(self, context: 'PipelineContext') -> None:
        """Validate processor stage configuration."""
        super()._validate(context)
        
        # Check if processor is registered
        if self._registry and self.config.processor not in self._registry.list_processors():
            raise ValueError(f"Processor not found: {self.config.processor}")
    
    async def _cleanup(self) -> None:
        """Clean up processor resources."""
        if self.processor:
            await self.processor.cleanup()
            self.processor = None


class ValidationStage(Stage):
    """Base class for validation stages."""
    
    async def _initialize(self) -> None:
        """Initialize validator."""
        # Initialize validation rules
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute validation."""
        start_time = datetime.utcnow()
        
        try:
            # Implement validation logic
            # This would validate based on stage configuration
            validation_passed = True
            validation_errors = []
            
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED if validation_passed else StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data={
                    "validation_passed": validation_passed,
                    "errors": validation_errors
                }
            )
            
        except Exception as e:
            logger.error(f"Validation failed in {self.name}: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )


class RouterStage(Stage):
    """Base class for routing stages that direct pipeline flow."""
    
    async def _initialize(self) -> None:
        """Initialize router."""
        # Initialize routing rules
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute routing logic."""
        start_time = datetime.utcnow()
        
        try:
            # Implement routing based on conditions
            # This would evaluate routing rules and set context flags
            routing_decision = self._make_routing_decision(context)
            
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data={
                    "routing_decision": routing_decision
                }
            )
            
        except Exception as e:
            logger.error(f"Routing failed in {self.name}: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )
    
    def _make_routing_decision(self, context: 'PipelineContext') -> str:
        """Make routing decision based on context."""
        # Placeholder implementation
        return "default"


class AggregatorStage(Stage):
    """Base class for aggregator stages that combine results."""
    
    async def _initialize(self) -> None:
        """Initialize aggregator."""
        pass
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """Execute result aggregation."""
        start_time = datetime.utcnow()
        
        try:
            # Aggregate results from dependencies
            aggregated_data = {}
            for dep in self.config.dependencies:
                if dep in context.stage_results:
                    result = context.stage_results[dep]
                    if result.status == StageStatus.COMPLETED:
                        aggregated_data[dep] = result.data
            
            return StageResult(
                stage_name=self.name,
                status=StageStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data={
                    "aggregated": aggregated_data,
                    "source_count": len(aggregated_data)
                }
            )
            
        except Exception as e:
            logger.error(f"Aggregation failed in {self.name}: {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )