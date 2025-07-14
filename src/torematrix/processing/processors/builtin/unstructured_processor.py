"""Unstructured.io processor implementation.

This module provides a processor that wraps the Unstructured.io library
for document parsing and content extraction.
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
from ....integrations.unstructured.client import UnstructuredClient
from ....integrations.unstructured.config import UnstructuredConfig

logger = logging.getLogger(__name__)


class UnstructuredProcessor(BaseProcessor):
    """Processor wrapping Unstructured.io for document parsing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client: Optional[UnstructuredClient] = None
        self._inject_unstructured_client: Optional[UnstructuredClient] = None
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="unstructured_processor",
            version="1.0.0",
            description="Document parsing using Unstructured.io",
            author="ToreMatrix",
            capabilities=[
                ProcessorCapability.TEXT_EXTRACTION,
                ProcessorCapability.METADATA_EXTRACTION,
                ProcessorCapability.TABLE_EXTRACTION,
                ProcessorCapability.IMAGE_EXTRACTION
            ],
            supported_formats=[
                "pdf", "docx", "doc", "txt", "html", "xml", 
                "md", "rst", "rtf", "odt", "pptx", "ppt",
                "xlsx", "xls", "csv", "tsv", "epub", "msg", "eml"
            ],
            is_cpu_intensive=True,
            is_memory_intensive=True,
            timeout_seconds=600,
            priority=ProcessorPriority.HIGH
        )
    
    async def _initialize(self) -> None:
        """Initialize Unstructured client."""
        if self._inject_unstructured_client:
            self.client = self._inject_unstructured_client
        else:
            # Create client from config
            unstructured_config = UnstructuredConfig(**self.config.get("unstructured", {}))
            self.client = UnstructuredClient(unstructured_config)
            await self.client.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process document using Unstructured."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.RUNNING,
            start_time=start_time,
            end_time=start_time  # Will be updated
        )
        
        try:
            # Validate input
            errors = await self.validate_input(context)
            if errors:
                result.errors = errors
                result.status = StageStatus.FAILED
                result.end_time = datetime.utcnow()
                return result
            
            # Process with Unstructured
            logger.info(f"Processing {context.file_path} with Unstructured")
            
            process_result = await self.client.process_file(
                file_path=context.file_path,
                strategy=self.config.get("strategy", "auto"),
                include_metadata=True,
                extract_images=self.config.get("extract_images", True),
                extract_tables=self.config.get("extract_tables", True)
            )
            
            # Extract results
            result.extracted_data = {
                "elements": [elem.dict() for elem in process_result.elements],
                "metadata": process_result.metadata,
                "text": process_result.text,
                "tables": process_result.tables,
                "images": process_result.images
            }
            
            result.metadata = {
                "element_count": len(process_result.elements),
                "page_count": process_result.metadata.get("page_count"),
                "language": process_result.metadata.get("language"),
                "file_type": process_result.metadata.get("file_type")
            }
            
            result.status = StageStatus.COMPLETED
            
            # Update metrics
            self.increment_metric("documents_processed")
            self.update_metric("last_process_time", result.duration)
            
        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
            self.increment_metric("documents_failed")
        
        result.end_time = datetime.utcnow()
        result.metrics = self.get_metrics()
        
        return result
    
    async def _cleanup(self) -> None:
        """Cleanup Unstructured client."""
        if self.client and not self._inject_unstructured_client:
            await self.client.close()