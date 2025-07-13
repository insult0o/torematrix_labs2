"""
TORE Matrix V3 - Enterprise AI Document Processing Pipeline

A comprehensive document processing system with advanced parsing, 
extraction, and quality assurance capabilities.
"""

# Version info
__version__ = "3.0.0"
__author__ = "TORE Matrix Labs"
__email__ = "contact@torematrix.com"

# Core imports - making key components easily accessible
try:
    # Core infrastructure (Issues #1-5)
    from .core.events import EventBus, Event
    from .core.models import Element, ElementType
    from .core.state import Store as StateStore
    from .core.storage import StorageFactory
    from .core.config import ConfigManager
except ImportError as e:
    import warnings
    warnings.warn(f"Core components not fully available: {e}")

try:
    # Document processing (Issues #6-7)
    from .integrations.unstructured import UnstructuredClient
    from .ingestion import UploadManager, QueueManager
except ImportError as e:
    import warnings
    warnings.warn(f"Document processing components not available: {e}")

try:
    # Processing pipeline (Issue #8)
    from .processing.pipeline import (
        PipelineManager,
        PipelineConfig,
        create_pipeline_from_template
    )
    from .processing.processors import ProcessorRegistry, BaseProcessor
except ImportError as e:
    import warnings
    warnings.warn(f"Pipeline components not available: {e}")

# Integration system - the main entry point
from .integration import ToreMatrixSystem, SystemConfig, create_system

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    
    # Main system
    "ToreMatrixSystem",
    "SystemConfig", 
    "create_system",
    
    # Core components
    "EventBus",
    "Event",
    "Element",
    "ElementType",
    "StateStore",
    "StorageFactory",
    "ConfigManager",
    
    # Document processing
    "UnstructuredClient",
    "UploadManager",
    "QueueManager",
    
    # Pipeline
    "PipelineManager",
    "PipelineConfig",
    "create_pipeline_from_template",
    "ProcessorRegistry",
    "BaseProcessor"
]


def get_version():
    """Get the current version of TORE Matrix."""
    return __version__


def get_system_info():
    """Get system information."""
    return {
        "name": "TORE Matrix V3",
        "version": __version__,
        "author": __author__,
        "description": "Enterprise AI Document Processing Pipeline",
        "features": [
            "Multi-format document processing",
            "Advanced element extraction",
            "Quality assurance system",
            "Real-time progress tracking",
            "Scalable pipeline architecture"
        ]
    }