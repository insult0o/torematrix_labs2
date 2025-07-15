"""Type Management Operations

This package provides comprehensive type management operations including:
- Bulk type changes and modifications
- Type conversions with data preservation  
- Type migrations and versioning
- Batch processing for large-scale operations
- Progress tracking and rollback capabilities
- Performance optimization for enterprise workloads
"""

from .bulk_operations import (
    BulkTypeOperationEngine, BulkOperationOptions, BulkOperationResult,
    BulkChangePreview, ElementChange, OperationStatus, ConflictResolution
)
from .conversions import TypeConversionEngine, ConversionResult, ConversionAnalysis
from .progress import (
    ProgressTracker, OperationProgress, ProgressCallback, ProgressPhase,
    start_operation_progress, update_operation_progress, complete_operation_progress
)
from .rollback import RollbackManager, RollbackOperation, RollbackState

__all__ = [
    # Core engines
    'BulkTypeOperationEngine',
    'TypeConversionEngine', 
    'ProgressTracker',
    'RollbackManager',
    
    # Data classes
    'BulkOperationOptions',
    'BulkOperationResult',
    'BulkChangePreview',
    'ElementChange',
    'ConversionResult',
    'ConversionAnalysis',
    'OperationProgress',
    'RollbackOperation',
    
    # Enums and types
    'OperationStatus',
    'ConflictResolution',
    'ProgressPhase',
    'RollbackState',
    'ProgressCallback',
    
    # Functions
    'start_operation_progress',
    'update_operation_progress',
    'complete_operation_progress',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 3"
__description__ = "Bulk Operations & Management for Type System"