"""
Processing module for TORE Matrix V3.

This module contains the document processing pipeline and related components.
"""

# Import workers module which has no external dependencies
from . import workers

__all__ = [
    'workers'
]

# Pipeline components will be imported on demand to avoid dependency issues
def get_pipeline_manager():
    """Import and return PipelineManager on demand."""
    from .pipeline.manager import PipelineManager
    return PipelineManager

def get_pipeline_config():
    """Import and return PipelineConfig on demand."""
    from .pipeline.config import PipelineConfig
    return PipelineConfig