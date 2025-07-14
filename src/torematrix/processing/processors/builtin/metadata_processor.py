"""Metadata extraction processor implementation.

This module provides a processor for extracting and enriching document metadata
from various sources including file properties, content analysis, and previous
processor results.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import logging
from pathlib import Path

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


class MetadataExtractorProcessor(BaseProcessor):
    """Processor for extracting and enriching document metadata."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="metadata_extractor",
            version="1.0.0",
            description="Extract and enrich document metadata",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.METADATA_EXTRACTION],
            supported_formats=["*"],  # Supports all formats
            is_cpu_intensive=False,
            timeout_seconds=60,
            priority=ProcessorPriority.NORMAL
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Extract document metadata."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            # Extract basic file metadata
            file_path = Path(context.file_path)
            file_stats = file_path.stat()
            
            metadata = {
                "document_id": context.document_id,
                "file_path": context.file_path,
                "file_name": file_path.name,
                "file_extension": file_path.suffix,
                "mime_type": context.mime_type,
                "file_size_bytes": file_stats.st_size,
                "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                "created_time": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "processing_time": datetime.utcnow().isoformat()
            }
            
            # Add metadata from previous processors
            if "unstructured_processor" in context.previous_results:
                unstructured_result = context.previous_results["unstructured_processor"]
                if "metadata" in unstructured_result:
                    unstructured_meta = unstructured_result["metadata"]
                    metadata.update({
                        "page_count": unstructured_meta.get("page_count"),
                        "language": unstructured_meta.get("language"),
                        "file_type": unstructured_meta.get("file_type"),
                        "element_count": unstructured_meta.get("element_count")
                    })
                
                # Extract text statistics if available
                if "extracted_data" in unstructured_result:
                    extracted_data = unstructured_result["extracted_data"]
                    if "text" in extracted_data:
                        text = extracted_data["text"]
                        metadata.update({
                            "text_length": len(text),
                            "word_count": len(text.split()) if text else 0,
                            "line_count": text.count('\n') + 1 if text else 0
                        })
                    
                    if "tables" in extracted_data:
                        metadata["table_count"] = len(extracted_data["tables"])
                    
                    if "images" in extracted_data:
                        metadata["image_count"] = len(extracted_data["images"])
            
            # Add context metadata
            if context.metadata:
                metadata.update({f"context_{k}": v for k, v in context.metadata.items()})
            
            # Determine document category based on extension and content
            metadata["document_category"] = self._categorize_document(
                file_path.suffix, 
                metadata.get("text_length", 0),
                metadata.get("table_count", 0),
                metadata.get("image_count", 0)
            )
            
            # Calculate quality metrics
            metadata.update(self._calculate_quality_metrics(metadata))
            
            result.extracted_data = {"metadata": metadata}
            result.metadata = {
                "fields_extracted": len(metadata),
                "has_text_content": metadata.get("text_length", 0) > 0,
                "has_tables": metadata.get("table_count", 0) > 0,
                "has_images": metadata.get("image_count", 0) > 0
            }
            
            # Update metrics
            self.increment_metric("documents_processed")
            self.update_metric("average_fields_extracted", len(metadata))
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
            self.increment_metric("documents_failed")
        
        result.end_time = datetime.utcnow()
        return result
    
    def _categorize_document(
        self, 
        extension: str, 
        text_length: int, 
        table_count: int, 
        image_count: int
    ) -> str:
        """Categorize document based on properties."""
        extension = extension.lower()
        
        # Spreadsheet documents
        if extension in ['.xlsx', '.xls', '.csv', '.tsv']:
            return "spreadsheet"
        
        # Presentation documents
        if extension in ['.pptx', '.ppt']:
            return "presentation"
        
        # Email documents
        if extension in ['.msg', '.eml']:
            return "email"
        
        # Web documents
        if extension in ['.html', '.htm', '.xml']:
            return "web"
        
        # Code/markup documents
        if extension in ['.md', '.rst', '.tex']:
            return "markup"
        
        # Image-heavy documents
        if image_count > 5 and text_length < 1000:
            return "image_document"
        
        # Table-heavy documents
        if table_count > 3 and text_length < 5000:
            return "data_document"
        
        # Long text documents
        if text_length > 50000:
            return "long_document"
        
        # Default text document
        if text_length > 0:
            return "text_document"
        
        return "unknown"
    
    def _calculate_quality_metrics(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality metrics for the document."""
        quality_metrics = {}
        
        # Content completeness
        has_text = metadata.get("text_length", 0) > 0
        has_metadata = len([k for k in metadata.keys() if not k.startswith("context_")]) > 5
        
        quality_metrics["content_completeness"] = (
            (1.0 if has_text else 0.0) + 
            (1.0 if has_metadata else 0.0)
        ) / 2.0
        
        # Content richness (tables, images, text)
        content_types = sum([
            1 if metadata.get("text_length", 0) > 100 else 0,
            1 if metadata.get("table_count", 0) > 0 else 0,
            1 if metadata.get("image_count", 0) > 0 else 0
        ])
        quality_metrics["content_richness"] = content_types / 3.0
        
        # File size appropriateness (not too small, not too large)
        file_size_mb = metadata.get("file_size_mb", 0)
        if file_size_mb < 0.01:  # Less than 10KB
            quality_metrics["size_appropriateness"] = 0.3
        elif file_size_mb > 100:  # More than 100MB
            quality_metrics["size_appropriateness"] = 0.7
        else:
            quality_metrics["size_appropriateness"] = 1.0
        
        # Overall quality score
        quality_metrics["overall_quality"] = (
            quality_metrics["content_completeness"] * 0.4 +
            quality_metrics["content_richness"] * 0.4 +
            quality_metrics["size_appropriateness"] * 0.2
        )
        
        return quality_metrics