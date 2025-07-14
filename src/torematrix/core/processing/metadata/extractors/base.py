"""Base extractor interface and framework for metadata extraction."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Set
import asyncio
import logging
from datetime import datetime

from ..types import (
    ExtractionContext, ExtractorConfig, MetadataValidationResult,
    ExtractionMethod, MetadataDict, ExtractorResult
)
from ..schema import BaseMetadata


logger = logging.getLogger(__name__)


class ExtractorError(Exception):
    """Base exception for extractor errors."""
    pass


class ExtractionTimeoutError(ExtractorError):
    """Raised when extraction exceeds timeout."""
    pass


class ValidationError(ExtractorError):
    """Raised when metadata validation fails."""
    pass


class BaseExtractor(ABC):
    """Base interface for all metadata extractors."""
    
    def __init__(self, config: ExtractorConfig):
        """Initialize base extractor.
        
        Args:
            config: Extractor configuration
        """
        self.config = config
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._supported_methods: Set[ExtractionMethod] = set()
        self._extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "average_duration": 0.0
        }
    
    @abstractmethod
    async def extract(
        self,
        document: Any,  # ProcessedDocument from processing system
        context: ExtractionContext
    ) -> ExtractorResult:
        """Extract metadata from document.
        
        Args:
            document: The document to extract metadata from
            context: Extraction context with processing hints
            
        Returns:
            Dictionary containing extracted metadata
            
        Raises:
            ExtractorError: If extraction fails
            ExtractionTimeoutError: If extraction times out
        """
        pass
    
    @abstractmethod
    def validate_metadata(self, metadata: MetadataDict) -> MetadataValidationResult:
        """Validate extracted metadata.
        
        Args:
            metadata: The metadata dictionary to validate
            
        Returns:
            Validation result with errors and confidence
        """
        pass
    
    @abstractmethod
    def get_supported_extraction_methods(self) -> List[ExtractionMethod]:
        """Return list of supported extraction methods.
        
        Returns:
            List of extraction methods this extractor supports
        """
        pass
    
    def get_confidence_factors(self) -> List[str]:
        """Return factors used for confidence scoring.
        
        Returns:
            List of confidence factor names
        """
        return [
            "extraction_method",
            "data_quality", 
            "validation_result",
            "source_reliability"
        ]
    
    async def extract_with_validation(
        self,
        document: Any,
        context: ExtractionContext
    ) -> Dict[str, Any]:
        """Extract metadata with built-in validation and error handling.
        
        Args:
            document: Document to process
            context: Extraction context
            
        Returns:
            Dictionary with extracted metadata and validation results
        """
        start_time = datetime.utcnow()
        
        try:
            # Update statistics
            self._extraction_stats["total_extractions"] += 1
            
            # Perform extraction with timeout
            extraction_task = asyncio.create_task(
                self.extract(document, context)
            )
            
            if self.config.timeout_seconds:
                try:
                    result = await asyncio.wait_for(
                        extraction_task,
                        timeout=self.config.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise ExtractionTimeoutError(
                        f"Extraction timed out after {self.config.timeout_seconds}s"
                    )
            else:
                result = await extraction_task
            
            # Validate extracted metadata
            validation_result = self.validate_metadata(result)
            
            # Apply confidence threshold filtering
            if validation_result.confidence_score < self.config.confidence_threshold:
                self.logger.warning(
                    f"Extracted metadata confidence {validation_result.confidence_score} "
                    f"below threshold {self.config.confidence_threshold}"
                )
            
            # Update success statistics
            self._extraction_stats["successful_extractions"] += 1
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._update_average_duration(duration)
            
            return {
                "metadata": result,
                "validation": validation_result,
                "extraction_info": {
                    "extractor": self.name,
                    "duration_seconds": duration,
                    "timestamp": start_time,
                    "success": True
                }
            }
            
        except Exception as e:
            # Update failure statistics
            self._extraction_stats["failed_extractions"] += 1
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.error(f"Extraction failed: {str(e)}", exc_info=True)
            
            return {
                "metadata": {},
                "validation": MetadataValidationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    validation_errors=[str(e)]
                ),
                "extraction_info": {
                    "extractor": self.name,
                    "duration_seconds": duration,
                    "timestamp": start_time,
                    "success": False,
                    "error": str(e)
                }
            }
    
    def _update_average_duration(self, duration: float) -> None:
        """Update running average of extraction duration."""
        total = self._extraction_stats["total_extractions"]
        current_avg = self._extraction_stats["average_duration"]
        
        # Calculate new average
        new_avg = ((current_avg * (total - 1)) + duration) / total
        self._extraction_stats["average_duration"] = new_avg
    
    async def extract_with_retry(
        self,
        document: Any,
        context: ExtractionContext,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract metadata with retry logic.
        
        Args:
            document: Document to process
            context: Extraction context
            max_retries: Maximum retry attempts (uses config if None)
            
        Returns:
            Extraction result with metadata and validation
        """
        max_retries = max_retries or self.config.retry_attempts
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.extract_with_validation(document, context)
                
                # Return on successful extraction
                if result["extraction_info"]["success"]:
                    if attempt > 0:
                        self.logger.info(f"Extraction succeeded on attempt {attempt + 1}")
                    return result
                    
                # If extraction failed but didn't raise, treat as error for retry
                last_error = result["extraction_info"].get("error", "Unknown extraction failure")
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
        
        # All retries exhausted
        self.logger.error(f"All {max_retries + 1} extraction attempts failed")
        return {
            "metadata": {},
            "validation": MetadataValidationResult(
                is_valid=False,
                confidence_score=0.0,
                validation_errors=[f"Extraction failed after {max_retries + 1} attempts: {last_error}"]
            ),
            "extraction_info": {
                "extractor": self.name,
                "timestamp": datetime.utcnow(),
                "success": False,
                "error": f"Max retries exceeded: {last_error}",
                "attempts": max_retries + 1
            }
        }
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get extraction performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        total = self._extraction_stats["total_extractions"]
        successful = self._extraction_stats["successful_extractions"]
        failed = self._extraction_stats["failed_extractions"]
        
        return {
            "extractor_name": self.name,
            "total_extractions": total,
            "successful_extractions": successful,
            "failed_extractions": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "failure_rate": failed / total if total > 0 else 0.0,
            "average_duration_seconds": self._extraction_stats["average_duration"],
            "configuration": self.config.dict()
        }
    
    def reset_statistics(self) -> None:
        """Reset extraction statistics."""
        self._extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "average_duration": 0.0
        }
    
    def is_enabled(self) -> bool:
        """Check if extractor is enabled in configuration.
        
        Returns:
            True if extractor is enabled
        """
        return self.config.enabled
    
    def supports_method(self, method: ExtractionMethod) -> bool:
        """Check if extractor supports a specific extraction method.
        
        Args:
            method: Extraction method to check
            
        Returns:
            True if method is supported
        """
        return method in self.get_supported_extraction_methods()
    
    def get_extractor_info(self) -> Dict[str, Any]:
        """Get comprehensive extractor information.
        
        Returns:
            Dictionary with extractor details
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
            "enabled": self.is_enabled(),
            "supported_methods": [method.value for method in self.get_supported_extraction_methods()],
            "confidence_factors": self.get_confidence_factors(),
            "configuration": self.config.dict(),
            "statistics": self.get_extraction_statistics()
        }


class ExtractorRegistry:
    """Registry for managing metadata extractors."""
    
    def __init__(self):
        """Initialize extractor registry."""
        self._extractors: Dict[str, BaseExtractor] = {}
        self._extractor_classes: Dict[str, Type[BaseExtractor]] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def register_extractor(
        self,
        name: str,
        extractor: BaseExtractor
    ) -> None:
        """Register a metadata extractor.
        
        Args:
            name: Unique name for the extractor
            extractor: Extractor instance
        """
        if name in self._extractors:
            self.logger.warning(f"Overwriting existing extractor: {name}")
        
        self._extractors[name] = extractor
        self._extractor_classes[name] = extractor.__class__
        
        self.logger.info(f"Registered extractor: {name}")
    
    def unregister_extractor(self, name: str) -> None:
        """Unregister a metadata extractor.
        
        Args:
            name: Name of extractor to remove
        """
        if name in self._extractors:
            del self._extractors[name]
            del self._extractor_classes[name]
            self.logger.info(f"Unregistered extractor: {name}")
        else:
            self.logger.warning(f"Extractor not found for unregistration: {name}")
    
    def get_extractor(self, name: str) -> Optional[BaseExtractor]:
        """Get extractor by name.
        
        Args:
            name: Name of extractor
            
        Returns:
            Extractor instance or None if not found
        """
        return self._extractors.get(name)
    
    def get_enabled_extractors(self) -> Dict[str, BaseExtractor]:
        """Get all enabled extractors.
        
        Returns:
            Dictionary of enabled extractors
        """
        return {
            name: extractor
            for name, extractor in self._extractors.items()
            if extractor.is_enabled()
        }
    
    def get_extractors_by_method(
        self,
        method: ExtractionMethod
    ) -> Dict[str, BaseExtractor]:
        """Get extractors that support a specific method.
        
        Args:
            method: Extraction method to filter by
            
        Returns:
            Dictionary of matching extractors
        """
        return {
            name: extractor
            for name, extractor in self._extractors.items()
            if extractor.supports_method(method) and extractor.is_enabled()
        }
    
    def list_extractors(self) -> List[str]:
        """Get list of registered extractor names.
        
        Returns:
            List of extractor names
        """
        return list(self._extractors.keys())
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive registry information.
        
        Returns:
            Dictionary with registry details
        """
        return {
            "total_extractors": len(self._extractors),
            "enabled_extractors": len(self.get_enabled_extractors()),
            "extractor_details": {
                name: extractor.get_extractor_info()
                for name, extractor in self._extractors.items()
            }
        }