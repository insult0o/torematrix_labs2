"""Type Management Operations

This package provides comprehensive type management operations including:
- Bulk type changes and modifications
- Type conversions with data preservation  
- Type migrations and versioning
- Batch processing for large-scale operations
- Progress tracking and rollback capabilities
- Performance optimization for enterprise workloads
"""

from .bulk_operations import BulkTypeOperationEngine, BulkOperationOptions, BulkOperationResult
from .conversions import TypeConversionEngine, ConversionResult, ConversionAnalysis
from .migrations import TypeMigrationManager, MigrationResult, MigrationPlan
from .warnings import ConversionWarningSystem, WarningLevel, ConversionWarning
from .batch_processor import BatchProcessor, BatchResult, BatchOptions
from .progress import ProgressTracker, OperationProgress, ProgressCallback
from .rollback import RollbackManager, RollbackOperation, RollbackState
from .optimization import PerformanceOptimizer, OptimizationStrategy, OptimizationResult

__all__ = [
    # Core engines
    'BulkTypeOperationEngine',
    'TypeConversionEngine', 
    'TypeMigrationManager',
    'ConversionWarningSystem',
    'BatchProcessor',
    'ProgressTracker',
    'RollbackManager',
    'PerformanceOptimizer',
    
    # Data classes
    'BulkOperationOptions',
    'BulkOperationResult',
    'ConversionResult',
    'ConversionAnalysis',
    'MigrationResult',
    'MigrationPlan',
    'ConversionWarning',
    'BatchResult',
    'BatchOptions',
    'OperationProgress',
    'RollbackOperation',
    'RollbackState',
    'OptimizationResult',
    
    # Enums
    'WarningLevel',
    'ProgressCallback',
    'OptimizationStrategy',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 3"
__description__ = "Bulk Operations & Management for Type System"