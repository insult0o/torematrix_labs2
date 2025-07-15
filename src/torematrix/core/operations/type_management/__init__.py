"""Type Management Operations

Agent 3 implementation for bulk operations and management including:
- Bulk type changes with progress tracking
- Safe type conversions with data preservation 
- Type migrations and versioning
- Rollback and undo capabilities
- Performance optimization for large-scale operations
"""

from .bulk_operations import (
    BulkTypeOperationEngine, BulkOperationOptions, BulkOperationResult,
    BulkChangePreview, ElementChange, OperationStatus, ConflictResolution
)
from .conversions import (
    TypeConversionEngine, ConversionRule, ConversionAnalysis, ConversionResult,
    ConversionStrategy, ConversionRisk, DataMappingRule
)
from .progress import (
    ProgressTracker, OperationProgress, ProgressPhase, ProgressCallback,
    start_operation_progress, update_operation_progress, complete_operation_progress,
    subscribe_to_operation_progress, get_progress_tracker
)
from .rollback import (
    RollbackManager, RollbackOperation, RollbackAction, RollbackResult,
    RollbackState, OperationType
)

__all__ = [
    # Bulk Operations
    'BulkTypeOperationEngine',
    'BulkOperationOptions', 
    'BulkOperationResult',
    'BulkChangePreview',
    'ElementChange',
    'OperationStatus',
    'ConflictResolution',
    
    # Type Conversions
    'TypeConversionEngine',
    'ConversionRule',
    'ConversionAnalysis', 
    'ConversionResult',
    'ConversionStrategy',
    'ConversionRisk',
    'DataMappingRule',
    
    # Progress Tracking
    'ProgressTracker',
    'OperationProgress',
    'ProgressPhase',
    'ProgressCallback',
    'start_operation_progress',
    'update_operation_progress',
    'complete_operation_progress',
    'subscribe_to_operation_progress',
    'get_progress_tracker',
    
    # Rollback System
    'RollbackManager',
    'RollbackOperation',
    'RollbackAction',
    'RollbackResult',
    'RollbackState',
    'OperationType',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 3 - Bulk Operations & Management"
__description__ = "Comprehensive bulk operations system for type management"