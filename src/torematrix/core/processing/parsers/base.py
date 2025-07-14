"""Abstract base class for document element parsers."""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from ...models.element import Element as UnifiedElement
from .types import ElementType, ParserConfig, ParserCapabilities, ProcessingHints
from .exceptions import (
    ParserError, ValidationError, UnsupportedElementError, 
    ProcessingTimeoutError, MemoryLimitError
)


@dataclass
class ParserMetadata:
    """Metadata for parser results."""
    
    confidence: float = 0.0
    parser_name: str = ""
    parser_version: str = "1.0.0"
    processing_time: float = 0.0
    memory_used: int = 0
    
    # Quality metrics
    validation_score: float = 0.0
    structure_quality: float = 0.0
    content_completeness: float = 0.0
    
    # Diagnostic information
    warnings: List[str] = field(default_factory=list)
    error_count: int = 0
    fallback_used: bool = False
    
    # Element-specific metadata
    element_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParserResult:
    """Result of parsing operation."""
    
    # Core result data
    success: bool
    data: Dict[str, Any]
    metadata: ParserMetadata
    
    # Validation and errors
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Extracted content
    extracted_content: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    
    # Export formats
    export_formats: Dict[str, Any] = field(default_factory=dict)
    
    def get_confidence_level(self) -> str:
        """Get human-readable confidence level."""
        conf = self.metadata.confidence
        if conf >= 0.8:
            return "very_high"
        elif conf >= 0.6:
            return "high"
        elif conf >= 0.4:
            return "medium"
        elif conf >= 0.2:
            return "low"
        else:
            return "very_low"
    
    def is_high_quality(self) -> bool:
        """Check if result meets high quality thresholds."""
        return (
            self.success and
            self.metadata.confidence >= 0.7 and
            len(self.validation_errors) == 0 and
            self.metadata.validation_score >= 0.8
        )


class BaseParser(ABC):
    """Abstract base class for all document element parsers."""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.logger = logging.getLogger(f"torematrix.parsers.{self.name.lower()}")
        
        # Performance tracking
        self._parse_count = 0
        self._total_time = 0.0
        self._error_count = 0
        
    @property
    @abstractmethod
    def capabilities(self) -> ParserCapabilities:
        """Return parser capabilities."""
        pass
    
    @abstractmethod
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if this parser can handle the given element.
        
        Args:
            element: The element to check
            
        Returns:
            True if parser can handle the element
        """
        pass
    
    @abstractmethod
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse the given element.
        
        Args:
            element: The element to parse
            hints: Optional processing hints
            
        Returns:
            ParserResult containing parsed data and metadata
            
        Raises:
            ParserError: If parsing fails
            UnsupportedElementError: If element type not supported
            ProcessingTimeoutError: If parsing times out
        """
        pass
    
    @abstractmethod
    def validate(self, result: ParserResult) -> List[str]:
        """Validate parsing result.
        
        Args:
            result: The result to validate
            
        Returns:
            List of validation error messages
        """
        pass
    
    def get_supported_types(self) -> List[ElementType]:
        """Get list of supported element types."""
        return self.capabilities.supported_types
    
    def get_priority(self, element: UnifiedElement) -> int:
        """Get parser priority for given element (higher = more preferred)."""
        if not self.can_parse(element):
            return 0
        
        # Default priority based on element type match
        if hasattr(element, 'type') and ElementType(element.type) in self.get_supported_types():
            return 50
        return 10
    
    async def parse_with_monitoring(self, element: UnifiedElement, 
                                   hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse element with performance monitoring and error handling."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Check if element is supported
            if not self.can_parse(element):
                raise UnsupportedElementError(
                    element.type if hasattr(element, 'type') else 'unknown',
                    self.name,
                    [t.value for t in self.get_supported_types()]
                )
            
            # Set up timeout
            timeout = hints.priority.value * 10 if hints else self.config.max_processing_time
            
            # Parse with timeout
            result = await asyncio.wait_for(
                self.parse(element, hints),
                timeout=timeout
            )
            
            # Update metadata
            result.metadata.parser_name = self.name
            result.metadata.parser_version = self.version
            result.metadata.processing_time = time.time() - start_time
            result.metadata.memory_used = self._get_memory_usage() - start_memory
            
            # Validate result
            validation_errors = self.validate(result)
            result.validation_errors.extend(validation_errors)
            
            # Update statistics
            self._parse_count += 1
            self._total_time += result.metadata.processing_time
            if not result.success:
                self._error_count += 1
            
            return result
            
        except asyncio.TimeoutError:
            self._error_count += 1
            raise ProcessingTimeoutError(timeout, self.name)
            
        except Exception as e:
            self._error_count += 1
            if isinstance(e, ParserError):
                raise
            
            # Wrap unexpected errors
            raise ParserError(
                f"Unexpected error in {self.name}: {str(e)}",
                parser_name=self.name,
                element_type=getattr(element, 'type', 'unknown')
            ) from e
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parser performance statistics."""
        return {
            "name": self.name,
            "version": self.version,
            "parse_count": self._parse_count,
            "total_time": self._total_time,
            "average_time": self._total_time / max(self._parse_count, 1),
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._parse_count, 1),
            "supported_types": [t.value for t in self.get_supported_types()]
        }
    
    def reset_statistics(self):
        """Reset performance statistics."""
        self._parse_count = 0
        self._total_time = 0.0
        self._error_count = 0
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0
    
    def _calculate_confidence(self, primary_confidence: float, *additional_factors: float) -> float:
        """Calculate overall confidence from multiple factors."""
        if not additional_factors:
            return max(0.0, min(1.0, primary_confidence))
        
        # Weighted average with primary confidence having 60% weight
        total_weight = 0.6 + 0.4  # primary + additional
        weighted_sum = 0.6 * primary_confidence
        
        additional_weight = 0.4 / len(additional_factors)
        for factor in additional_factors:
            weighted_sum += additional_weight * factor
        
        return max(0.0, min(1.0, weighted_sum / total_weight))
    
    def _create_success_result(self, data: Dict[str, Any], confidence: float = 1.0, 
                              metadata: Optional[Dict[str, Any]] = None) -> ParserResult:
        """Helper to create successful parser result."""
        return ParserResult(
            success=True,
            data=data,
            metadata=ParserMetadata(
                confidence=confidence,
                element_metadata=metadata or {}
            )
        )
    
    def _create_failure_result(self, error_message: str, 
                              validation_errors: Optional[List[str]] = None) -> ParserResult:
        """Helper to create failed parser result."""
        return ParserResult(
            success=False,
            data={},
            metadata=ParserMetadata(
                confidence=0.0,
                error_count=1,
                warnings=[error_message]
            ),
            validation_errors=validation_errors or [error_message]
        )