"""
Unstructured.io integration for TORE Matrix Labs V3.

This module provides async-compatible document parsing capabilities
for 15+ file formats using the Unstructured library.
"""

# Import Agent 1 components (conditionally)
try:
    from .client import UnstructuredClient
    from .config import (
        UnstructuredConfig,
        ParsingStrategy,
        OCRConfig,
        PreprocessingConfig,
        PerformanceConfig
    )
    _HAS_CLIENT = True
except ImportError:
    UnstructuredClient = None
    UnstructuredConfig = None
    ParsingStrategy = None
    OCRConfig = None
    PreprocessingConfig = None
    PerformanceConfig = None
    _HAS_CLIENT = False

# Import Agent 2 components (mappers)
try:
    from .mappers import ElementFactory, ElementMapper, MapperRegistry
    from .mappers import MetadataExtractor, MetadataNormalizer
    _HAS_MAPPERS = True
except ImportError:
    ElementFactory = None
    ElementMapper = None
    MapperRegistry = None
    MetadataExtractor = None
    MetadataNormalizer = None
    _HAS_MAPPERS = False

try:
    from .validators import ElementValidator, ValidationResult
    _HAS_VALIDATORS = True
except ImportError:
    ElementValidator = None
    ValidationResult = None
    _HAS_VALIDATORS = False

# Import Agent 3 components (optimization)
try:
    from .bridge import OptimizedInfrastructureBridge, BridgeFactory
    _HAS_OPTIMIZATION = True
except ImportError:
    OptimizedInfrastructureBridge = None
    BridgeFactory = None
    _HAS_OPTIMIZATION = False

from .exceptions import (
    UnstructuredError,
    UnstructuredTimeoutError,
    UnstructuredConnectionError,
    UnstructuredParsingError,
    UnstructuredConfigError,
    UnstructuredResourceError,
    UnstructuredMappingError,
    UnstructuredValidationError
)

__all__ = [
    # Exceptions (always available)
    "UnstructuredError",
    "UnstructuredTimeoutError",
    "UnstructuredConnectionError",
    "UnstructuredParsingError",
    "UnstructuredConfigError",
    "UnstructuredResourceError",
    "UnstructuredMappingError",
    "UnstructuredValidationError",
]

# Add client components if available
if _HAS_CLIENT:
    __all__.extend([
        "UnstructuredClient",
        "UnstructuredConfig",
        "ParsingStrategy",
        "OCRConfig",
        "PreprocessingConfig",
        "PerformanceConfig",
    ])

# Add mapper components if available
if _HAS_MAPPERS:
    __all__.extend([
        "ElementFactory",
        "ElementMapper",
        "MapperRegistry",
        "MetadataExtractor",
        "MetadataNormalizer",
    ])

# Add validator components if available
if _HAS_VALIDATORS:
    __all__.extend([
        "ElementValidator",
        "ValidationResult",
    ])

# Add optimization components if available
if _HAS_OPTIMIZATION:
    __all__.extend([
        "OptimizedInfrastructureBridge",
        "BridgeFactory",
    ])

__version__ = "0.1.0"