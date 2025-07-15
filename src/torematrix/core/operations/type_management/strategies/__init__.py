"""Type Management Operation Strategies

This package provides specialized strategies for type management operations:
- Safe conversion strategies with data preservation
- Data preservation techniques for type migrations
- Validation strategies for complex operations
- Performance optimization strategies for large-scale operations
"""

from .safe_conversion import SafeConversionStrategy, ConversionSafetyLevel
from .data_preservation import DataPreservationStrategy, PreservationMethod
from .validation_strategy import ValidationStrategy, ValidationLevel
from .performance_strategy import PerformanceStrategy, PerformanceMode

__all__ = [
    # Strategy classes
    'SafeConversionStrategy',
    'DataPreservationStrategy', 
    'ValidationStrategy',
    'PerformanceStrategy',
    
    # Enums
    'ConversionSafetyLevel',
    'PreservationMethod',
    'ValidationLevel', 
    'PerformanceMode',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 3"
__description__ = "Type Management Operation Strategies"