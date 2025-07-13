"""Document validation processor implementation.

This module provides a processor for validating document content and structure
to ensure quality and completeness of processed documents.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from ..base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus,
    ProcessorPriority
)

logger = logging.getLogger(__name__)


class ValidationProcessor(BaseProcessor):
    """Processor for validating document content and structure."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="validation_processor",
            version="1.0.0",
            description="Validate document content and structure",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.VALIDATION],
            supported_formats=["*"],
            is_cpu_intensive=False,
            timeout_seconds=30,
            priority=ProcessorPriority.NORMAL
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Validate document."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            validation_results = []
            
            # Get validation rules from config
            validation_rules = self.config.get("validation_rules", {})
            
            # Basic file validation
            self._validate_file_properties(context, validation_results, validation_rules)
            
            # Content validation
            if "unstructured_processor" in context.previous_results:
                self._validate_unstructured_content(
                    context.previous_results["unstructured_processor"], 
                    validation_results, 
                    validation_rules
                )
            
            # Metadata validation
            if "metadata_extractor" in context.previous_results:
                self._validate_metadata(
                    context.previous_results["metadata_extractor"],
                    validation_results,
                    validation_rules
                )
            
            # Determine overall validation status
            error_count = sum(1 for r in validation_results if r["level"] == "error")
            warning_count = sum(1 for r in validation_results if r["level"] == "warning")
            
            result.extracted_data = {
                "validation_results": validation_results,
                "is_valid": error_count == 0,
                "validation_summary": {
                    "total_checks": len(validation_results),
                    "errors": error_count,
                    "warnings": warning_count,
                    "passed": len(validation_results) - error_count - warning_count
                }
            }
            
            result.metadata = {
                "valid": error_count == 0,
                "warning_count": warning_count,
                "error_count": error_count,
                "validation_score": self._calculate_validation_score(validation_results)
            }
            
            # Update metrics
            self.increment_metric("documents_validated")
            if error_count == 0:
                self.increment_metric("documents_passed")
            else:
                self.increment_metric("documents_failed_validation")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
        
        result.end_time = datetime.utcnow()
        return result
    
    def _validate_file_properties(
        self, 
        context: ProcessorContext, 
        results: List[Dict], 
        rules: Dict[str, Any]
    ) -> None:
        """Validate basic file properties."""
        # Check if file exists and is accessible
        try:
            import os
            if not os.path.exists(context.file_path):
                results.append({
                    "check": "file_exists",
                    "level": "error",
                    "message": f"File does not exist: {context.file_path}"
                })
                return
            
            # Check file size
            file_size = os.path.getsize(context.file_path)
            max_size = rules.get("max_file_size_mb", 100) * 1024 * 1024
            min_size = rules.get("min_file_size_bytes", 10)
            
            if file_size > max_size:
                results.append({
                    "check": "file_size_max",
                    "level": "error",
                    "message": f"File too large: {file_size / (1024*1024):.1f}MB > {max_size / (1024*1024)}MB"
                })
            elif file_size < min_size:
                results.append({
                    "check": "file_size_min",
                    "level": "warning",
                    "message": f"File very small: {file_size} bytes"
                })
            else:
                results.append({
                    "check": "file_size",
                    "level": "info",
                    "message": "File size is appropriate"
                })
                
        except Exception as e:
            results.append({
                "check": "file_access",
                "level": "error",
                "message": f"Cannot access file: {str(e)}"
            })
    
    def _validate_unstructured_content(
        self, 
        unstructured_result: Dict[str, Any], 
        results: List[Dict], 
        rules: Dict[str, Any]
    ) -> None:
        """Validate content extracted by Unstructured processor."""
        extracted_data = unstructured_result.get("extracted_data", {})
        elements = extracted_data.get("elements", [])
        text = extracted_data.get("text", "")
        
        # Check if any content was extracted
        if not elements:
            results.append({
                "check": "content_extraction",
                "level": "error",
                "message": "No content extracted from document"
            })
            return
        
        results.append({
            "check": "content_extraction",
            "level": "info", 
            "message": f"Successfully extracted {len(elements)} elements"
        })
        
        # Check text content length
        min_text_length = rules.get("min_text_length", 50)
        if len(text) < min_text_length:
            results.append({
                "check": "text_content",
                "level": "warning",
                "message": f"Document contains very little text: {len(text)} characters"
            })
        else:
            results.append({
                "check": "text_content",
                "level": "info",
                "message": f"Good text content: {len(text)} characters"
            })
        
        # Check for various element types
        element_types = set(elem.get("type", "unknown") for elem in elements)
        
        if "Title" not in element_types and "Header" not in element_types:
            results.append({
                "check": "document_structure",
                "level": "warning",
                "message": "No title or headers found - document may lack structure"
            })
        
        # Check for tables if expected
        if rules.get("expect_tables", False):
            tables = extracted_data.get("tables", [])
            if not tables:
                results.append({
                    "check": "table_content",
                    "level": "warning",
                    "message": "No tables found but tables were expected"
                })
        
        # Check for images if expected
        if rules.get("expect_images", False):
            images = extracted_data.get("images", [])
            if not images:
                results.append({
                    "check": "image_content",
                    "level": "warning",
                    "message": "No images found but images were expected"
                })
    
    def _validate_metadata(
        self, 
        metadata_result: Dict[str, Any], 
        results: List[Dict], 
        rules: Dict[str, Any]
    ) -> None:
        """Validate extracted metadata."""
        extracted_data = metadata_result.get("extracted_data", {})
        metadata = extracted_data.get("metadata", {})
        
        # Check required metadata fields
        required_fields = rules.get("required_metadata_fields", [
            "file_name", "file_size_bytes", "mime_type"
        ])
        
        for field in required_fields:
            if field not in metadata or metadata[field] is None:
                results.append({
                    "check": f"required_metadata_{field}",
                    "level": "error",
                    "message": f"Required metadata field missing: {field}"
                })
            else:
                results.append({
                    "check": f"required_metadata_{field}",
                    "level": "info",
                    "message": f"Required metadata field present: {field}"
                })
        
        # Check metadata quality score
        quality_score = metadata.get("overall_quality", 0)
        min_quality = rules.get("min_quality_score", 0.5)
        
        if quality_score < min_quality:
            results.append({
                "check": "metadata_quality",
                "level": "warning",
                "message": f"Low metadata quality score: {quality_score:.2f} < {min_quality}"
            })
        else:
            results.append({
                "check": "metadata_quality",
                "level": "info",
                "message": f"Good metadata quality score: {quality_score:.2f}"
            })
    
    def _calculate_validation_score(self, results: List[Dict]) -> float:
        """Calculate overall validation score (0.0 to 1.0)."""
        if not results:
            return 0.0
        
        total_checks = len(results)
        error_weight = -1.0
        warning_weight = -0.3
        info_weight = 1.0
        
        score = 0.0
        for result in results:
            level = result["level"]
            if level == "error":
                score += error_weight
            elif level == "warning":
                score += warning_weight
            elif level == "info":
                score += info_weight
        
        # Normalize to 0.0 - 1.0 range
        max_possible_score = total_checks * info_weight
        min_possible_score = total_checks * error_weight
        
        if max_possible_score == min_possible_score:
            return 1.0
        
        normalized_score = (score - min_possible_score) / (max_possible_score - min_possible_score)
        return max(0.0, min(1.0, normalized_score))