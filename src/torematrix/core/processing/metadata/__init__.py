"""Metadata extraction package initialization and exports."""

from .engine import MetadataExtractionEngine
from .schema import (
    MetadataSchema, DocumentMetadata, PageMetadata, 
    ElementMetadata, RelationshipMetadata, BaseMetadata
)
from .types import (
    MetadataType, LanguageCode, EncodingType, ExtractionMethod,
    ConfidenceLevel, ExtractionContext, MetadataValidationResult,
    ExtractorConfig, MetadataConfig
)
from .confidence import ConfidenceScorer
from .extractors import (
    BaseExtractor, ExtractorRegistry, DocumentMetadataExtractor, 
    PageMetadataExtractor, ExtractorError, ExtractionTimeoutError,
    ValidationError
)

__all__ = [
    # Core engine
    "MetadataExtractionEngine",
    
    # Schema definitions
    "MetadataSchema",
    "DocumentMetadata", 
    "PageMetadata",
    "ElementMetadata",
    "RelationshipMetadata",
    "BaseMetadata",
    
    # Type definitions
    "MetadataType",
    "LanguageCode",
    "EncodingType", 
    "ExtractionMethod",
    "ConfidenceLevel",
    "ExtractionContext",
    "MetadataValidationResult",
    "ExtractorConfig",
    "MetadataConfig",
    
    # Confidence scoring
    "ConfidenceScorer",
    
    # Extractors
    "BaseExtractor",
    "ExtractorRegistry",
    "DocumentMetadataExtractor",
    "PageMetadataExtractor",
    "ExtractorError",
    "ExtractionTimeoutError", 
    "ValidationError"
]

# Package metadata
__version__ = "1.0.0"
__author__ = "TORE Matrix Labs"
__description__ = "Core metadata extraction engine with pluggable extractors"