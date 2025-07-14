"""
Configuration system for unstructured integration.

This module provides Pydantic-based configuration models for all
unstructured integration components.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ParsingStrategy(str, Enum):
    """Document parsing strategies."""
    AUTO = "auto"
    HI_RES = "hi_res"
    FAST = "fast"
    OCR_ONLY = "ocr_only"


class OCRConfig(BaseModel):
    """OCR-specific configuration."""
    enabled: bool = True
    language: str = "eng"
    languages: List[str] = Field(default_factory=lambda: ["eng"])
    confidence_threshold: float = 0.7
    preprocessing: bool = True
    dpi: int = 300


class PreprocessingConfig(BaseModel):
    """Document preprocessing configuration."""
    clean_text: bool = True
    remove_headers: bool = False
    remove_footers: bool = False
    merge_sections: bool = True
    normalize_whitespace: bool = True


class PerformanceConfig(BaseModel):
    """Performance and resource configuration."""
    memory_limit_mb: int = 2048
    cache_size_mb: int = 512
    cache_ttl: int = 3600
    max_concurrent: int = 4
    timeout_seconds: int = 300
    chunk_size_mb: int = 100


class UnstructuredConfig(BaseModel):
    """Main configuration for unstructured integration."""
    
    # Parsing configuration
    strategy: ParsingStrategy = ParsingStrategy.AUTO
    include_page_breaks: bool = True
    include_metadata: bool = True
    
    # Component configurations
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    # File type specific settings
    pdf_extract_images: bool = True
    pdf_infer_table_structure: bool = True
    html_assemble_articles: bool = True
    
    # Output configuration
    output_format: str = "elements"
    skip_infer_table_types: List[str] = Field(default_factory=list)
    
    # Custom settings
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
    
    def model_dump_json(self, **kwargs) -> str:
        """Export configuration as JSON string."""
        return super().model_dump_json(**kwargs)
    
    @classmethod
    def create_development_config(cls) -> 'UnstructuredConfig':
        """Create configuration optimized for development."""
        return cls(
            strategy=ParsingStrategy.FAST,
            performance=PerformanceConfig(
                memory_limit_mb=1024,
                cache_size_mb=256,
                max_concurrent=2,
                timeout_seconds=120
            ),
            ocr=OCRConfig(
                enabled=False  # Faster development
            )
        )
    
    @classmethod
    def create_production_config(cls) -> 'UnstructuredConfig':
        """Create configuration optimized for production."""
        return cls(
            strategy=ParsingStrategy.HI_RES,
            performance=PerformanceConfig(
                memory_limit_mb=4096,
                cache_size_mb=1024,
                max_concurrent=8,
                timeout_seconds=600
            ),
            ocr=OCRConfig(
                enabled=True,
                confidence_threshold=0.8
            )
        )
    
    @classmethod
    def create_testing_config(cls) -> 'UnstructuredConfig':
        """Create configuration optimized for testing."""
        return cls(
            strategy=ParsingStrategy.FAST,
            performance=PerformanceConfig(
                memory_limit_mb=512,
                cache_size_mb=128,
                max_concurrent=1,
                timeout_seconds=60,
                cache_ttl=60
            ),
            ocr=OCRConfig(enabled=False)
        )