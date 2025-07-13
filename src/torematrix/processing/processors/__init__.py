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
    
    # Exceptions
    "ProcessorException",
    "ProcessorInitializationError",
    "ProcessorExecutionError",
    "ProcessorTimeoutError",
]