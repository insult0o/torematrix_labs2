"""
Pipeline processing module for TORE Matrix V3.

This module provides a flexible, DAG-based document processing pipeline
with async execution, resource management, and checkpoint support.
"""

from .config import (
    PipelineConfig,
    StageConfig,
    StageType,
    ResourceRequirements
)
from .manager import (
    PipelineManager,
    PipelineContext,
    PipelineStatus
)
from .stages import (
    Stage,
    StageResult,
    StageStatus,
    ProcessorStage,
    ValidationStage,
    RouterStage,
    AggregatorStage
)
from .resources import (
    ResourceMonitor,
    ResourceUsage
)
from .templates import (
    PipelineTemplate,
    StandardDocumentPipeline,
    BatchProcessingPipeline,
    QualityAssurancePipeline,
    get_template,
    list_templates,
    create_pipeline_from_template
)
from .exceptions import (
    PipelineError,
    PipelineConfigError,
    PipelineExecutionError,
    StageDependencyError,
    StageTimeoutError,
    ResourceError,
    CyclicDependencyError,
    CheckpointError,
    PipelineCancelledError
)

__all__ = [
    # Configuration
    'PipelineConfig',
    'StageConfig',
    'StageType',
    'ResourceRequirements',
    
    # Pipeline Manager
    'PipelineManager',
    'PipelineContext',
    'PipelineStatus',
    
    # Stages
    'Stage',
    'StageResult',
    'StageStatus',
    'ProcessorStage',
    'ValidationStage',
    'RouterStage',
    'AggregatorStage',
    
    # Resources
    'ResourceMonitor',
    'ResourceUsage',
    
    # Templates
    'PipelineTemplate',
    'StandardDocumentPipeline',
    'BatchProcessingPipeline',
    'QualityAssurancePipeline',
    'get_template',
    'list_templates',
    'create_pipeline_from_template',
    
    # Exceptions
    'PipelineError',
    'PipelineConfigError',
    'PipelineExecutionError',
    'StageDependencyError',
    'StageTimeoutError',
    'ResourceError',
    'CyclicDependencyError',
    'CheckpointError',
    'PipelineCancelledError'
]