"""Processor Plugin System for TORE Matrix V3.

This module provides the plugin system for document processors, including
base interfaces, registry management, and built-in processors.
"""

from .base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    ProcessorPriority,
    ProcessorException,
    ProcessorInitializationError,
    ProcessorExecutionError,
    ProcessorTimeoutError,
)
from .registry import ProcessorRegistry, get_registry
from .resilience import CircuitBreaker, ResilientProcessor, ProcessorChain
from .monitoring import ProcessorMonitor, monitor_processor
# Pipeline bridge components - imported lazily to avoid dependencies
try:
    from .stage_bridge import (
        create_processor_stage,
        create_unstructured_stage,
        create_metadata_stage,
        create_validation_stage,
        create_transformation_stage
    )
    _PIPELINE_BRIDGE_AVAILABLE = True
except ImportError:
    _PIPELINE_BRIDGE_AVAILABLE = False
    
    # Provide stub functions if bridge is not available
    def create_processor_stage(*args, **kwargs):
        raise ImportError("Pipeline bridge not available - missing dependencies")
    
    def create_unstructured_stage(*args, **kwargs):
        raise ImportError("Pipeline bridge not available - missing dependencies")
        
    def create_metadata_stage(*args, **kwargs):
        raise ImportError("Pipeline bridge not available - missing dependencies")
        
    def create_validation_stage(*args, **kwargs):
        raise ImportError("Pipeline bridge not available - missing dependencies")
        
    def create_transformation_stage(*args, **kwargs):
        raise ImportError("Pipeline bridge not available - missing dependencies")

__all__ = [
    # Base interfaces
    "BaseProcessor",
    "ProcessorMetadata",
    "ProcessorContext", 
    "ProcessorResult",
    "ProcessorCapability",
    "ProcessorPriority",
    
    # Registry
    "ProcessorRegistry",
    "get_registry",
    
    # Resilience
    "CircuitBreaker",
    "ResilientProcessor", 
    "ProcessorChain",
    
    # Monitoring
    "ProcessorMonitor",
    "monitor_processor",
    
    # Pipeline Bridge (conditionally available)
    "create_processor_stage",
    "create_unstructured_stage",
    "create_metadata_stage",
    "create_validation_stage",
    "create_transformation_stage",
    
    # Exceptions
    "ProcessorException",
    "ProcessorInitializationError",
    "ProcessorExecutionError",
    "ProcessorTimeoutError",
]


def _register_builtin_processors():
    """Register built-in processors with the global registry."""
    registry = get_registry()
    
    try:
        # Import and register built-in processors
        from .builtin.unstructured_processor import UnstructuredProcessor
        from .builtin.metadata_processor import MetadataExtractorProcessor
        from .builtin.validation_processor import ValidationProcessor
        from .builtin.transformation_processor import TransformationProcessor
        
        registry.register(UnstructuredProcessor)
        registry.register(MetadataExtractorProcessor)
        registry.register(ValidationProcessor)
        registry.register(TransformationProcessor)
        
    except ImportError as e:
        # Don't fail if dependencies are missing
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Some built-in processors could not be loaded: {e}")


# Auto-register built-in processors when module is imported
_register_builtin_processors()