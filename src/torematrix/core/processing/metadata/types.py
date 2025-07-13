"""Type definitions and enums for metadata extraction system."""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import uuid


class MetadataType(str, Enum):
    """Types of metadata that can be extracted."""
    DOCUMENT = "document"
    PAGE = "page"
    ELEMENT = "element"
    RELATIONSHIP = "relationship"


class LanguageCode(str, Enum):
    """ISO 639-1 language codes for document language detection."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    UNKNOWN = "unknown"


class EncodingType(str, Enum):
    """Common text encodings for document processing."""
    UTF8 = "utf-8"
    UTF16 = "utf-16"
    UTF32 = "utf-32"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    CP1252 = "cp1252"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    """Methods used for metadata extraction."""
    DIRECT_PARSING = "direct_parsing"
    OCR_EXTRACTION = "ocr_extraction"
    HEURISTIC_ANALYSIS = "heuristic_analysis"
    ML_INFERENCE = "ml_inference"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted metadata."""
    VERY_HIGH = "very_high"  # >95%
    HIGH = "high"            # 85-95%
    MEDIUM = "medium"        # 70-85%
    LOW = "low"              # 50-70%
    VERY_LOW = "very_low"    # <50%


class ExtractionContext(BaseModel):
    """Context information for metadata extraction."""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    extraction_version: str = "1.0.0"
    extractor_chain: List[str] = Field(default_factory=list)
    processing_hints: Dict[str, Any] = Field(default_factory=dict)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"arbitrary_types_allowed": True}


class MetadataValidationResult(BaseModel):
    """Result of metadata validation."""
    is_valid: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExtractorConfig(BaseModel):
    """Configuration for metadata extractors."""
    enabled: bool = True
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    extraction_methods: List[ExtractionMethod] = Field(default_factory=list)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[float] = Field(default=30.0, gt=0)
    retry_attempts: int = Field(default=3, ge=0)
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        return v


class MetadataConfig(BaseModel):
    """Configuration for the metadata extraction engine."""
    enable_parallel_extraction: bool = True
    max_workers: int = Field(default=4, ge=1)
    cache_enabled: bool = True
    cache_ttl_seconds: int = Field(default=3600, ge=0)
    default_language: LanguageCode = LanguageCode.ENGLISH
    default_encoding: EncodingType = EncodingType.UTF8
    confidence_weights: Dict[str, float] = Field(default_factory=dict)
    extractor_configs: Dict[str, ExtractorConfig] = Field(default_factory=dict)
    
    @field_validator('confidence_weights')
    @classmethod
    def validate_confidence_weights(cls, v):
        if v and abs(sum(v.values()) - 1.0) > 1e-6:
            raise ValueError('Confidence weights must sum to 1.0')
        return v


# Type aliases for common metadata structures
MetadataDict = Dict[str, Any]
ExtractorResult = Dict[str, Any]
ConfidenceScores = Dict[str, float]