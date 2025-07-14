"""
Document processors for the queue management system.

This module provides processors for individual documents and batches,
integrating with Unstructured.io for document processing and the event
system for progress tracking.
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import time

from .models import FileMetadata, FileStatus
from .progress import ProgressTracker
from ..core.events import EventBus, ProcessingEvent, ProcessingEventTypes
from ..integrations.unstructured.client import UnstructuredClient
from ..integrations.unstructured.exceptions import ProcessingError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of document processing."""
    file_id: str
    status: str  # success, failed, skipped
    processing_time: float
    elements_extracted: int = 0
    pages_processed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchResult:
    """Result of batch processing."""
    batch_id: str
    total_files: int
    successful_files: int
    failed_files: int
    skipped_files: int
    total_processing_time: float
    results: List[ProcessingResult]
    error_summary: Dict[str, int] = None
    
    def __post_init__(self):
        if self.error_summary is None:
            self.error_summary = {}


class DocumentProcessor:
    """Processes individual documents through Unstructured.io."""
    
    def __init__(
        self,
        unstructured_client: UnstructuredClient,
        progress_tracker: Optional[ProgressTracker] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.unstructured_client = unstructured_client
        self.progress_tracker = progress_tracker
        self.event_bus = event_bus or EventBus()
        
        # Processing configuration
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
    async def process(
        self,
        job_data: Dict[str, Any],
        update_progress: bool = True
    ) -> ProcessingResult:
        """
        Process a single document.
        
        Args:
            job_data: Job data containing file info and metadata
            update_progress: Whether to emit progress events
            
        Returns:
            ProcessingResult with processing details
        """
        file_id = job_data["file_id"]
        file_path = job_data["file_path"]
        metadata = FileMetadata(**job_data["metadata"])
        
        start_time = time.time()
        
        try:
            logger.info(f"Starting processing for file {file_id}")
            
            # Update progress: processing started
            if update_progress and self.progress_tracker:
                await self.progress_tracker.update_file_progress(
                    file_id=file_id,
                    status="processing",
                    current_step="processing",
                    completed_steps=3  # uploaded, validated, queued, now processing
                )
            
            # Emit processing started event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_STARTED.value,
                file_id=file_id,
                job_id=job_data.get("job_id"),
                data={
                    "filename": metadata.filename,
                    "file_type": metadata.file_type,
                    "size": metadata.size
                }
            ))
            
            # Process document with Unstructured.io
            result = await self._process_with_unstructured(
                file_path=Path(file_path),
                metadata=metadata,
                file_id=file_id
            )
            
            processing_time = time.time() - start_time
            
            # Create processing result
            processing_result = ProcessingResult(
                file_id=file_id,
                status="success",
                processing_time=processing_time,
                elements_extracted=len(result.elements) if result else 0,
                pages_processed=result.metadata.get("page_count", 0) if result else 0,
                metadata=result.metadata if result else {}
            )
            
            # Update progress: completed
            if update_progress and self.progress_tracker:
                await self.progress_tracker.update_file_progress(
                    file_id=file_id,
                    status="completed",
                    current_step="completed",
                    progress=1.0,
                    completed_steps=5,  # all steps done
                    processing_time=processing_time
                )
            
            # Update file metadata in database (would be implemented by Agent 1)
            await self._update_file_metadata(
                file_id=file_id,
                status=FileStatus.PROCESSED,
                processing_time=processing_time,
                extracted_elements=processing_result.elements_extracted,
                document_metadata=processing_result.metadata
            )
            
            # Emit completion event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_COMPLETED.value,
                file_id=file_id,
                job_id=job_data.get("job_id"),
                processing_time=processing_time,
                data={
                    "elements_extracted": processing_result.elements_extracted,
                    "pages_processed": processing_result.pages_processed,
                    "filename": metadata.filename
                }
            ))
            
            logger.info(
                f"Successfully processed file {file_id} in {processing_time:.2f}s "
                f"({processing_result.elements_extracted} elements)"
            )
            
            return processing_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Failed to process file {file_id}: {error_msg}")
            logger.error(traceback.format_exc())
            
            # Create failure result
            processing_result = ProcessingResult(
                file_id=file_id,
                status="failed",
                processing_time=processing_time,
                error_message=error_msg
            )
            
            # Update progress: failed
            if update_progress and self.progress_tracker:
                await self.progress_tracker.update_file_progress(
                    file_id=file_id,
                    status="failed",
                    current_step="failed",
                    error=error_msg,
                    processing_time=processing_time
                )
            
            # Update file metadata
            await self._update_file_metadata(
                file_id=file_id,
                status=FileStatus.FAILED,
                processing_time=processing_time,
                error=error_msg
            )
            
            # Emit failure event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_FAILED.value,
                file_id=file_id,
                job_id=job_data.get("job_id"),
                error=error_msg,
                processing_time=processing_time,
                data={"filename": metadata.filename}
            ))
            
            return processing_result
    
    async def _process_with_unstructured(
        self,
        file_path: Path,
        metadata: FileMetadata,
        file_id: str
    ):
        """Process file using Unstructured.io client."""
        try:
            # Emit progress update for processing step
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_PROGRESS.value,
                file_id=file_id,
                progress=0.5,
                data={"current_step": "extracting_content"}
            ))
            
            # Process with Unstructured.io
            result = await self.unstructured_client.process_file(
                file_path,
                strategy="auto",  # Let Unstructured choose the best strategy
                include_metadata=True,
                extract_images=True,
                extract_tables=True,
                chunking_strategy="by_title"  # Good default for most documents
            )
            
            # Emit progress update for completion
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_PROGRESS.value,
                file_id=file_id,
                progress=0.9,
                data={"current_step": "finalizing"}
            ))
            
            return result
            
        except ValidationError as e:
            logger.error(f"Validation error processing {file_id}: {e}")
            raise ProcessingError(f"Document validation failed: {e}")
        except Exception as e:
            logger.error(f"Unstructured processing error for {file_id}: {e}")
            raise ProcessingError(f"Document processing failed: {e}")
    
    async def _update_file_metadata(
        self,
        file_id: str,
        status: FileStatus,
        processing_time: float,
        extracted_elements: int = 0,
        document_metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Update file metadata in the database."""
        try:
            # This would integrate with Agent 1's database layer
            # For now, we'll just log the update
            update_data = {
                "status": status.value,
                "processed_at": datetime.utcnow().isoformat(),
                "processing_time": processing_time,
                "extracted_elements": extracted_elements
            }
            
            if document_metadata:
                update_data["document_metadata"] = document_metadata
                update_data["page_count"] = document_metadata.get("page_count")
                update_data["language"] = document_metadata.get("language")
            
            if error:
                update_data["processing_errors"] = [error]
            
            logger.debug(f"Would update file {file_id} metadata: {update_data}")
            
            # TODO: Integrate with Agent 1's database update mechanism
            # await database_client.update_file_metadata(file_id, update_data)
            
        except Exception as e:
            logger.error(f"Failed to update file metadata for {file_id}: {e}")


class BatchProcessor:
    """Processes batches of documents efficiently with concurrency control."""
    
    def __init__(
        self,
        document_processor: DocumentProcessor,
        max_concurrent: int = 5,
        progress_tracker: Optional[ProgressTracker] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.document_processor = document_processor
        self.max_concurrent = max_concurrent
        self.progress_tracker = progress_tracker
        self.event_bus = event_bus or EventBus()
        
    async def process_batch(
        self,
        batch_data: Dict[str, Any]
    ) -> BatchResult:
        """
        Process a batch of documents concurrently.
        
        Args:
            batch_data: Batch information with files to process
            
        Returns:
            BatchResult with summary of processing
        """
        batch_id = batch_data["batch_id"]
        files = batch_data["files"]
        batch_index = batch_data.get("batch_index", 0)
        total_batches = batch_data.get("total_batches", 1)
        
        start_time = time.time()
        results = []
        
        logger.info(
            f"Starting batch processing for batch {batch_id} "
            f"({batch_index + 1}/{total_batches}) with {len(files)} files"
        )
        
        try:
            # Emit batch started event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.BATCH_STARTED.value,
                batch_id=batch_id,
                data={
                    "file_count": len(files),
                    "batch_index": batch_index,
                    "total_batches": total_batches,
                    "max_concurrent": self.max_concurrent
                }
            ))
            
            # Process files concurrently with semaphore
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = []
            
            for i, file_data in enumerate(files):
                task = self._process_file_with_semaphore(
                    semaphore, 
                    file_data,
                    batch_id,
                    i,
                    len(files)
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle task exceptions
                    file_data = files[i]
                    error_result = ProcessingResult(
                        file_id=file_data["file_id"],
                        status="failed",
                        processing_time=0.0,
                        error_message=str(result)
                    )
                    processed_results.append(error_result)
                    logger.error(f"Task exception for file {file_data['file_id']}: {result}")
                else:
                    processed_results.append(result)
            
            total_processing_time = time.time() - start_time
            
            # Calculate batch statistics
            successful_files = sum(1 for r in processed_results if r.status == "success")
            failed_files = sum(1 for r in processed_results if r.status == "failed")
            skipped_files = sum(1 for r in processed_results if r.status == "skipped")
            
            # Create error summary
            error_summary = {}
            for result in processed_results:
                if result.error_message:
                    error_type = self._classify_error(result.error_message)
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1
            
            batch_result = BatchResult(
                batch_id=batch_id,
                total_files=len(files),
                successful_files=successful_files,
                failed_files=failed_files,
                skipped_files=skipped_files,
                total_processing_time=total_processing_time,
                results=processed_results,
                error_summary=error_summary
            )
            
            # Emit batch completion event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.BATCH_COMPLETED.value,
                batch_id=batch_id,
                processing_time=total_processing_time,
                data={
                    "total_files": len(files),
                    "successful_files": successful_files,
                    "failed_files": failed_files,
                    "batch_index": batch_index,
                    "total_batches": total_batches,
                    "avg_processing_time": total_processing_time / len(files) if files else 0
                }
            ))
            
            logger.info(
                f"Completed batch {batch_id}: {successful_files}/{len(files)} successful "
                f"in {total_processing_time:.2f}s"
            )
            
            return batch_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Batch processing failed: {str(e)}"
            
            logger.error(f"Batch {batch_id} processing error: {error_msg}")
            logger.error(traceback.format_exc())
            
            # Emit batch failure event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.BATCH_FAILED.value,
                batch_id=batch_id,
                error=error_msg,
                processing_time=processing_time,
                data={
                    "file_count": len(files),
                    "batch_index": batch_index
                }
            ))
            
            # Return failure result
            return BatchResult(
                batch_id=batch_id,
                total_files=len(files),
                successful_files=0,
                failed_files=len(files),
                skipped_files=0,
                total_processing_time=processing_time,
                results=[
                    ProcessingResult(
                        file_id=f["file_id"],
                        status="failed",
                        processing_time=0.0,
                        error_message=error_msg
                    )
                    for f in files
                ]
            )
    
    async def _process_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file_data: Dict[str, Any],
        batch_id: str,
        file_index: int,
        total_files: int
    ) -> ProcessingResult:
        """Process a single file with concurrency control."""
        async with semaphore:
            try:
                # Add batch context to job data
                job_data = {
                    "file_id": file_data["file_id"],
                    "file_path": file_data["storage_key"],
                    "metadata": file_data,
                    "batch_id": batch_id,
                    "batch_index": file_index,
                    "batch_total": total_files
                }
                
                # Emit progress for this file in the batch
                await self.event_bus.publish(ProcessingEvent(
                    event_type=ProcessingEventTypes.BATCH_PROGRESS.value,
                    batch_id=batch_id,
                    file_id=file_data["file_id"],
                    progress=(file_index + 1) / total_files,
                    data={
                        "current_file": file_index + 1,
                        "total_files": total_files,
                        "filename": file_data.get("filename", "unknown")
                    }
                ))
                
                # Process the file
                result = await self.document_processor.process(
                    job_data,
                    update_progress=True
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing file {file_data['file_id']} in batch: {e}")
                return ProcessingResult(
                    file_id=file_data["file_id"],
                    status="failed",
                    processing_time=0.0,
                    error_message=str(e)
                )
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error messages for summary reporting."""
        error_lower = error_message.lower()
        
        if "validation" in error_lower:
            return "validation_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory_error"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif "format" in error_lower or "unsupported" in error_lower:
            return "format_error"
        else:
            return "unknown_error"


# RQ worker entry points
def process_document(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    RQ worker entry point for single document processing.
    
    This function is called by RQ workers to process individual documents.
    It initializes the necessary components and runs the async processing.
    """
    async def _async_process():
        # Initialize components
        from ..integrations.unstructured.config import UnstructuredConfig
        from ..integrations.unstructured.client import UnstructuredClient
        from ..core.events import EventBus
        import redis.asyncio as redis
        
        # Get configuration (would come from environment/config)
        unstructured_config = UnstructuredConfig()
        redis_client = await redis.from_url("redis://localhost:6379/0")
        
        # Initialize components
        client = UnstructuredClient(unstructured_config)
        event_bus = EventBus()
        progress_tracker = ProgressTracker(redis_client, event_bus)
        processor = DocumentProcessor(client, progress_tracker, event_bus)
        
        try:
            # Process the document
            result = await processor.process(job_data)
            return result.__dict__
        finally:
            await redis_client.close()
    
    # Run the async processing
    return asyncio.run(_async_process())


def process_batch(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    RQ worker entry point for batch processing.
    
    This function is called by RQ workers to process document batches.
    """
    async def _async_process():
        # Initialize components
        from ..integrations.unstructured.config import UnstructuredConfig
        from ..integrations.unstructured.client import UnstructuredClient
        from ..core.events import EventBus
        import redis.asyncio as redis
        
        # Get configuration
        unstructured_config = UnstructuredConfig()
        redis_client = await redis.from_url("redis://localhost:6379/0")
        
        # Initialize components
        client = UnstructuredClient(unstructured_config)
        event_bus = EventBus()
        progress_tracker = ProgressTracker(redis_client, event_bus)
        doc_processor = DocumentProcessor(client, progress_tracker, event_bus)
        batch_processor = BatchProcessor(doc_processor, max_concurrent=3, progress_tracker=progress_tracker, event_bus=event_bus)
        
        try:
            # Process the batch
            result = await batch_processor.process_batch(batch_data)
            return result.__dict__
        finally:
            await redis_client.close()
    
    # Run the async processing
    return asyncio.run(_async_process())