"""Parser type definitions and enumerations."""

from enum import Enum, IntEnum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class ElementType(Enum):
    """Supported document element types."""
    TABLE = "Table"
    LIST = "List"
    LIST_ITEM = "ListItem" 
    IMAGE = "Image"
    FIGURE = "Figure"
    FORMULA = "Formula"
    CODE_BLOCK = "CodeBlock"
    CODE = "Code"
    TITLE = "Title"
    HEADER = "Header"
    TEXT = "Text"
    NARRATIVE_TEXT = "NarrativeText"
    COMPOSITE_ELEMENT = "CompositeElement"
    FOOTNOTE = "Footnote"
    PAGE_BREAK = "PageBreak"
    UNKNOWN = "Unknown"


class ParserPriority(IntEnum):
    """Parser priority levels for selection."""
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5


class ConfidenceLevel(Enum):
    """Confidence levels for parsing results."""
    VERY_LOW = "very_low"     # 0.0 - 0.2
    LOW = "low"               # 0.2 - 0.4
    MEDIUM = "medium"         # 0.4 - 0.6
    HIGH = "high"             # 0.6 - 0.8
    VERY_HIGH = "very_high"   # 0.8 - 1.0


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"         # Fail on any validation error
    MODERATE = "moderate"     # Warn on minor errors, fail on major
    LENIENT = "lenient"       # Warn on errors, rarely fail


class ParserConfig(BaseModel):
    """Configuration for parser behavior."""
    
    # Performance settings
    max_processing_time: float = Field(default=30.0, description="Maximum processing time in seconds")
    max_memory_usage: int = Field(default=1024*1024*100, description="Maximum memory usage in bytes")
    enable_parallel: bool = Field(default=True, description="Enable parallel processing")
    
    # Quality settings
    min_confidence: float = Field(default=0.5, description="Minimum confidence threshold")
    validation_level: ValidationLevel = Field(default=ValidationLevel.MODERATE)
    enable_strict_typing: bool = Field(default=True, description="Enable strict type checking")
    
    # Caching settings
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    max_cache_size: int = Field(default=10000, description="Maximum cache entries")
    
    # Monitoring settings
    enable_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    collect_metrics: bool = Field(default=True, description="Collect detailed metrics")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Parser-specific settings
    parser_specific: Dict[str, Any] = Field(default_factory=dict, description="Parser-specific configuration")
    
    class Config:
        extra = "forbid"
        use_enum_values = True


class ProcessingHints(BaseModel):
    """Hints for optimizing element processing."""
    
    expected_type: Optional[ElementType] = None
    language_hint: Optional[str] = None
    quality_hint: Optional[str] = None  # "high", "medium", "low"
    complexity_hint: Optional[str] = None  # "simple", "complex"
    priority: ParserPriority = ParserPriority.MEDIUM
    
    # Element-specific hints
    table_hints: Optional[Dict[str, Any]] = None
    image_hints: Optional[Dict[str, Any]] = None
    code_hints: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"
        use_enum_values = True


class ParserCapabilities(BaseModel):
    """Parser capability definition."""
    
    supported_types: List[ElementType]
    supported_languages: List[str] = Field(default_factory=list)
    max_element_size: Optional[int] = None  # Maximum element size in bytes
    supports_batch: bool = True
    supports_async: bool = True
    confidence_range: tuple[float, float] = (0.0, 1.0)
    
    # Feature support
    supports_validation: bool = True
    supports_metadata_extraction: bool = True
    supports_structured_output: bool = True
    supports_export_formats: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"