"""
Bridge between pipeline stages and processor system.

This module provides the ProcessorStage class that integrates the processor
plugin system with the pipeline stage framework.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..pipeline.stages import Stage, StageResult, StageStatus
from ..pipeline.config import StageConfig
from .base import BaseProcessor, ProcessorContext, ProcessorResult
from .registry import ProcessorRegistry, get_registry

logger = logging.getLogger(__name__)


class ProcessorStage(Stage):
    """
    Pipeline stage that executes a processor.
    
    This bridges the pipeline stage framework with the processor plugin system,
    allowing processors to be used as pipeline stages.
    """
    
    def __init__(self, config: StageConfig, processor_name: str, processor_config: Optional[Dict[str, Any]] = None):
        """
        Initialize processor stage.
        
        Args:
            config: Stage configuration
            processor_name: Name of processor to execute
            processor_config: Configuration for the processor
        """
        super().__init__(config)
        self.processor_name = processor_name
        self.processor_config = processor_config or {}
        self.processor: Optional[BaseProcessor] = None
        self.registry = get_registry()
    
    async def _initialize(self) -> None:
        """Initialize the processor stage."""
        try:
            # Get processor instance from registry
            self.processor = await self.registry.get_processor(
                self.processor_name, 
                self.processor_config
            )
            logger.info(f"Initialized processor stage: {self.name} -> {self.processor_name}")
        except Exception as e:
            logger.error(f"Failed to initialize processor {self.processor_name}: {e}")
            raise
    
    async def execute(self, context: 'PipelineContext') -> StageResult:
        """
        Execute the processor stage.
        
        Args:
            context: Pipeline execution context
            
        Returns:
            Stage execution result
        """
        start_time = datetime.utcnow()
        
        if not self.processor:
            raise RuntimeError(f"Processor not initialized: {self.processor_name}")
        
        try:
            # Convert pipeline context to processor context
            processor_context = self._create_processor_context(context)
            
            # Execute processor
            logger.debug(f"Executing processor: {self.processor_name}")
            processor_result = await self.processor.process(processor_context)
            
            # Convert processor result to stage result
            stage_result = processor_result.to_stage_result()
            stage_result.stage_name = self.name  # Override with stage name
            
            logger.info(f"Processor stage completed: {self.name} ({processor_result.status})")
            return stage_result
            
        except Exception as e:
            logger.error(f"Processor stage failed: {self.name} - {e}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=str(e)
            )
    
    def _create_processor_context(self, pipeline_context: 'PipelineContext') -> ProcessorContext:
        """
        Convert pipeline context to processor context.
        
        Args:
            pipeline_context: Pipeline execution context
            
        Returns:
            Processor context
        """
        # Extract document information from pipeline context
        file_path = pipeline_context.metadata.get('file_path', '')
        mime_type = pipeline_context.metadata.get('mime_type', '')
        
        # Get results from previous stages
        previous_results = {}
        if hasattr(pipeline_context, 'stage_results'):
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
    
    async def validate(self, context: 'PipelineContext') -> List[str]:
        """
        Validate stage configuration and processor availability.
        
        Args:
            context: Pipeline context
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check if processor is registered
        if self.processor_name not in self.registry.list_processors():
            errors.append(f"Processor not found: {self.processor_name}")
            return errors
        
        # Validate processor input if available
        if self.processor:
            processor_context = self._create_processor_context(context)
            processor_errors = await self.processor.validate_input(processor_context)
            errors.extend(processor_errors)
        
        return errors
    
    async def cleanup(self) -> None:
        """Clean up stage resources."""
        if self.processor:
            await self.processor.cleanup()
            self.processor = None
    
    def get_processor_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata about the processor."""
        if self.processor_name in self.registry.list_processors():
            metadata = self.registry.get_metadata(self.processor_name)
            return {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "capabilities": [cap.value for cap in metadata.capabilities],
                "supported_formats": metadata.supported_formats,
                "is_cpu_intensive": metadata.is_cpu_intensive,
                "is_memory_intensive": metadata.is_memory_intensive,
                "timeout_seconds": metadata.timeout_seconds
            }
        return None


def create_processor_stage(
    stage_name: str,
    processor_name: str,
    processor_config: Optional[Dict[str, Any]] = None,
    dependencies: Optional[List[str]] = None,
    **stage_kwargs
) -> ProcessorStage:
    """
    Factory function to create a processor stage.
    
    Args:
        stage_name: Name of the stage
        processor_name: Name of processor to execute
        processor_config: Configuration for the processor
        dependencies: List of stage dependencies
        **stage_kwargs: Additional stage configuration
        
    Returns:
        Configured processor stage
    """
    from ..pipeline.config import StageConfig, StageType
    
    stage_config = StageConfig(
        name=stage_name,
        type=StageType.PROCESSOR,
        dependencies=dependencies or [],
        **stage_kwargs
    )
    
    return ProcessorStage(stage_config, processor_name, processor_config)


# Convenience functions for common processor stages
def create_unstructured_stage(
    stage_name: str = "unstructured_extraction", 
    **kwargs
) -> ProcessorStage:
    """Create a stage for Unstructured.io processing."""
    return create_processor_stage(
        stage_name=stage_name,
        processor_name="unstructured_processor",
        **kwargs
    )


def create_metadata_stage(
    stage_name: str = "metadata_extraction",
    dependencies: Optional[List[str]] = None,
    **kwargs
) -> ProcessorStage:
    """Create a stage for metadata extraction."""
    return create_processor_stage(
        stage_name=stage_name,
        processor_name="metadata_extractor",
        dependencies=dependencies or ["unstructured_extraction"],
        **kwargs
    )


def create_validation_stage(
    stage_name: str = "validation",
    dependencies: Optional[List[str]] = None,
    validation_rules: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ProcessorStage:
    """Create a stage for document validation."""
    processor_config = {"validation_rules": validation_rules} if validation_rules else None
    
    return create_processor_stage(
        stage_name=stage_name,
        processor_name="validation_processor",
        processor_config=processor_config,
        dependencies=dependencies or ["unstructured_extraction", "metadata_extraction"],
        **kwargs
    )


def create_transformation_stage(
    stage_name: str = "transformation",
    transformations: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    **kwargs
) -> ProcessorStage:
    """Create a stage for content transformation."""
    processor_config = {"transformations": transformations} if transformations else None
    
    return create_processor_stage(
        stage_name=stage_name,
        processor_name="transformation_processor",
        processor_config=processor_config,
        dependencies=dependencies or ["unstructured_extraction"],
        **kwargs
    )