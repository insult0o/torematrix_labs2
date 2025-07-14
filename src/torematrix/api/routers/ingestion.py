"""
Document Ingestion API Endpoints

FastAPI router providing REST endpoints for file uploads, session management,
and status tracking. Integrates with Agent 1's UploadManager and Agent 2's QueueManager.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime
import uuid
import logging

# Import dependencies that will be provided by other agents
from ...ingestion.models import FileMetadata, FileStatus, UploadResult, UploadSession
from ...core.auth import get_current_user, User  # Will be implemented
from ...core.dependencies import get_upload_manager, get_queue_manager  # Will be implemented
from ..models import (
    CreateSessionRequest,
    UploadResponse,
    BatchUploadResponse,
    SessionResponse,
    FileStatusResponse,
    SessionStatusResponse,
    QueueStatsResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

# Response models for single file uploads
class FileUploadResponse(BaseModel):
    """Response for single file upload."""
    file_id: str
    filename: str
    status: str
    size: int
    mime_type: str
    validation_status: str
    errors: List[str] = Field(default_factory=list)
    queue_job_id: Optional[str] = None


@router.post("/sessions", response_model=SessionResponse)
async def create_upload_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    upload_manager = Depends(get_upload_manager)  # Type from Agent 1
) -> SessionResponse:
    """
    Create a new upload session for organizing related file uploads.
    
    Sessions allow grouping files together and tracking their collective progress.
    """
    try:
        # Create session using Agent 1's upload manager
        session = await upload_manager.create_session(current_user.id)
        
        # Store additional metadata if provided
        if request.name:
            session.metadata["name"] = request.name
        session.metadata.update(request.metadata)
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            created_at=session.created_at,
            metadata=session.metadata
        )
    except Exception as e:
        logger.error(f"Failed to create upload session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create upload session")


@router.post("/sessions/{session_id}/upload", response_model=FileUploadResponse)
async def upload_file(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    validate_content: bool = Query(True, description="Perform content validation"),
    auto_process: bool = Query(True, description="Automatically queue for processing"),
    priority: bool = Query(False, description="Use priority queue"),
    current_user: User = Depends(get_current_user),
    upload_manager = Depends(get_upload_manager),  # From Agent 1
    queue_manager = Depends(get_queue_manager)     # From Agent 2
) -> FileUploadResponse:
    """
    Upload a single file to an existing session.
    
    The file is validated, stored, and optionally queued for processing.
    Returns upload status and any validation errors.
    """
    try:
        # Verify session ownership
        session = upload_manager.get_session(session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Upload file using Agent 1's upload manager
        result = await upload_manager.upload_file(
            session_id=session_id,
            file=file,
            validate_content=validate_content
        )
        
        # Prepare response
        response = FileUploadResponse(
            file_id=result.file_id,
            filename=result.filename,
            status="uploaded",
            size=result.size,
            mime_type=result.mime_type,
            validation_status=result.validation_status,
            errors=result.errors
        )
        
        # Queue for processing if requested and validation passed
        if auto_process and result.validation_status in ["valid", "warning"]:
            # Create file metadata for queue
            file_metadata = FileMetadata(
                file_id=result.file_id,
                filename=result.filename,
                file_type=_detect_file_type(result.mime_type),
                mime_type=result.mime_type,
                size=result.size,
                hash=result.hash,
                upload_session_id=session_id,
                uploaded_by=current_user.id,
                uploaded_at=datetime.utcnow(),
                storage_key=result.storage_key,
                status=FileStatus.UPLOADED,
                validation_errors=result.errors,
                document_metadata=result.metadata
            )
            
            # Queue in background using Agent 2's queue manager
            background_tasks.add_task(
                queue_file_for_processing,
                file_metadata,
                queue_manager,
                priority
            )
            
            response.status = "queued"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.post("/sessions/{session_id}/upload-batch", response_model=BatchUploadResponse)
async def upload_batch(
    session_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    validate_content: bool = Query(True),
    auto_process: bool = Query(True),
    priority: bool = Query(False),
    current_user: User = Depends(get_current_user),
    upload_manager = Depends(get_upload_manager),
    queue_manager = Depends(get_queue_manager)
) -> BatchUploadResponse:
    """
    Upload multiple files in a batch to an existing session.
    
    Files are processed concurrently for efficiency. Each file is validated
    individually and optionally queued for processing.
    """
    try:
        # Verify session
        session = upload_manager.get_session(session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Upload files concurrently using Agent 1's batch upload
        results = await upload_manager.upload_batch(
            session_id=session_id,
            files=files,
            max_concurrent=5  # Limit concurrent uploads
        )
        
        # Prepare response data
        uploaded_files = []
        failed_files = []
        files_to_queue = []
        
        for result in results:
            file_response = FileUploadResponse(
                file_id=result.file_id,
                filename=result.filename,
                status="uploaded" if result.validation_status != "failed" else "failed",
                size=result.size,
                mime_type=result.mime_type,
                validation_status=result.validation_status,
                errors=result.errors
            )
            
            if result.validation_status == "failed":
                failed_files.append(file_response)
            else:
                uploaded_files.append(file_response)
                
                # Prepare for queuing if auto-processing enabled
                if auto_process:
                    file_metadata = FileMetadata(
                        file_id=result.file_id,
                        filename=result.filename,
                        file_type=_detect_file_type(result.mime_type),
                        mime_type=result.mime_type,
                        size=result.size,
                        hash=result.hash,
                        upload_session_id=session_id,
                        uploaded_by=current_user.id,
                        uploaded_at=datetime.utcnow(),
                        storage_key=result.storage_key,
                        status=FileStatus.UPLOADED,
                        validation_errors=result.errors,
                        document_metadata=result.metadata
                    )
                    files_to_queue.append(file_metadata)
        
        # Queue for processing in background if any valid files
        if files_to_queue:
            background_tasks.add_task(
                queue_batch_for_processing,
                files_to_queue,
                queue_manager,
                priority
            )
        
        return BatchUploadResponse(
            session_id=session_id,
            total_files=len(files),
            uploaded_files=uploaded_files,
            failed_files=failed_files,
            batch_queued=len(files_to_queue) > 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload batch to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Batch upload failed")


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    upload_manager = Depends(get_upload_manager),
    queue_manager = Depends(get_queue_manager)
) -> SessionStatusResponse:
    """
    Get detailed status of an upload session including all files.
    
    Returns comprehensive information about session progress,
    individual file statuses, and processing results.
    """
    try:
        # Verify session
        session = upload_manager.get_session(session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get file statuses with queue information
        file_statuses = []
        processed_count = 0
        failed_count = 0
        
        for file_result in session.files:
            # Get processing status from queue if available
            job_status = None
            if hasattr(file_result, 'queue_job_id') and file_result.queue_job_id:
                job_info = await queue_manager.get_job_status(file_result.queue_job_id)
                if job_info:
                    job_status = job_info.status.value
                    if job_info.status.value == "finished":
                        processed_count += 1
                    elif job_info.status.value == "failed":
                        failed_count += 1
            
            file_statuses.append(FileStatusResponse(
                file_id=file_result.file_id,
                filename=file_result.filename,
                status=job_status or file_result.validation_status,
                size=file_result.size,
                upload_status=file_result.validation_status,
                processing_status=job_status,
                errors=file_result.errors
            ))
        
        # Calculate overall progress
        total_files = len(session.files)
        overall_progress = (processed_count + failed_count) / total_files if total_files > 0 else 0
        
        return SessionStatusResponse(
            session_id=session.session_id,
            status=session.status,
            total_files=total_files,
            processed_files=processed_count,
            failed_files=failed_count,
            overall_progress=overall_progress,
            created_at=session.created_at,
            files=file_statuses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session status")


@router.get("/files/{file_id}/status", response_model=FileStatusResponse)
async def get_file_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    queue_manager = Depends(get_queue_manager)
) -> FileStatusResponse:
    """
    Get status of a specific file by ID.
    
    Returns detailed information about the file's upload, validation,
    and processing status.
    """
    try:
        # Get file metadata from database
        file_metadata = await get_file_metadata(file_id, current_user.id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get processing status from queue
        job_status = None
        if file_metadata.queue_job_id:
            job_info = await queue_manager.get_job_status(file_metadata.queue_job_id)
            if job_info:
                job_status = job_info.status.value
        
        return FileStatusResponse(
            file_id=file_metadata.file_id,
            filename=file_metadata.filename,
            status=job_status or file_metadata.status.value,
            size=file_metadata.size,
            upload_status=file_metadata.status.value,
            processing_status=job_status,
            errors=file_metadata.validation_errors + file_metadata.processing_errors,
            processed_at=file_metadata.processed_at,
            processing_time=file_metadata.processing_time,
            extracted_elements=file_metadata.extracted_elements
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file status for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file status")


@router.post("/files/{file_id}/retry")
async def retry_file_processing(
    file_id: str,
    priority: bool = Query(False),
    current_user: User = Depends(get_current_user),
    queue_manager = Depends(get_queue_manager)
) -> Dict[str, Any]:
    """
    Retry processing for a failed file.
    
    Requeues the file for processing, optionally with priority.
    Only works for files that have failed processing.
    """
    try:
        # Get file metadata
        file_metadata = await get_file_metadata(file_id, current_user.id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_metadata.status != FileStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail="Only failed files can be retried"
            )
        
        # Retry using Agent 2's queue manager
        if file_metadata.queue_job_id:
            new_job_id = await queue_manager.retry_failed_job(file_metadata.queue_job_id)
            if new_job_id:
                return {"status": "retried", "job_id": new_job_id}
        
        # Re-queue if no existing job
        file_metadata.status = FileStatus.UPLOADED
        file_metadata.processing_errors = []
        
        job_id = await queue_manager.enqueue_file(file_metadata, priority=priority)
        
        return {"status": "requeued", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry file processing")


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_statistics(
    current_user: User = Depends(get_current_user),
    queue_manager = Depends(get_queue_manager)
) -> QueueStatsResponse:
    """
    Get queue statistics and worker information.
    
    Returns current queue depths, processing rates, and worker status
    for monitoring system performance.
    """
    try:
        stats = await queue_manager.get_queue_stats()
        
        return QueueStatsResponse(
            queues=stats,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve queue statistics")


# Helper functions for background tasks
async def queue_file_for_processing(
    file_metadata: FileMetadata,
    queue_manager,
    priority: bool = False
):
    """Queue a single file for processing."""
    try:
        job_id = await queue_manager.enqueue_file(file_metadata, priority=priority)
        file_metadata.queue_job_id = job_id
        await save_file_metadata(file_metadata)
        logger.info(f"Queued file {file_metadata.file_id} with job ID {job_id}")
    except Exception as e:
        logger.error(f"Failed to queue file {file_metadata.file_id}: {e}")


async def queue_batch_for_processing(
    files: List[FileMetadata],
    queue_manager,
    priority: bool = False
):
    """Queue a batch of files for processing."""
    try:
        job_ids = await queue_manager.enqueue_batch(files, priority=priority)
        
        # Update metadata with job IDs
        for file_metadata, job_id in zip(files, job_ids):
            file_metadata.queue_job_id = job_id
            await save_file_metadata(file_metadata)
        
        logger.info(f"Queued batch of {len(files)} files")
    except Exception as e:
        logger.error(f"Failed to queue batch: {e}")


def _detect_file_type(mime_type: str) -> str:
    """Detect file type from MIME type."""
    mime_map = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
        "application/msword": "word",
        "text/plain": "text",
        "text/html": "html",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "spreadsheet",
        "application/vnd.ms-excel": "spreadsheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "presentation",
        "application/vnd.ms-powerpoint": "presentation",
        "image/jpeg": "image",
        "image/png": "image",
        "image/gif": "image"
    }
    return mime_map.get(mime_type, "other")


# Database functions - simple in-memory storage for now
_file_metadata_store = {}

async def get_file_metadata(file_id: str, user_id: str) -> Optional[FileMetadata]:
    """Get file metadata from storage."""
    try:
        metadata = _file_metadata_store.get(file_id)
        if metadata and metadata.uploaded_by == user_id:
            return metadata
        return None
    except Exception as e:
        logger.error(f"Error retrieving file metadata for {file_id}: {e}")
        return None


async def save_file_metadata(file_metadata: FileMetadata) -> None:
    """Save file metadata to storage."""
    try:
        _file_metadata_store[file_metadata.file_id] = file_metadata
        logger.debug(f"Saved metadata for file {file_metadata.file_id}")
    except Exception as e:
        logger.error(f"Error saving file metadata: {e}")
        raise