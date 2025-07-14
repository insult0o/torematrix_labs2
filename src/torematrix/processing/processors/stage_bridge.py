"""
Bridge between pipeline stages and processor system.

This module provides the ProcessorStage class that integrates the processor
plugin system with the pipeline stage framework.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Import ProcessorStage from the pipeline stages module
from ..pipeline.stages import ProcessorStage

logger = logging.getLogger(__name__)


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
        processor=processor_name,
        dependencies=dependencies or [],
        config=processor_config or {},
        **stage_kwargs
    )
    
    return ProcessorStage(stage_config)


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