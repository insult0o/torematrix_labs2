"""
API Response Models and Request Schemas

Defines Pydantic models for all API requests and responses
to ensure type safety and auto-generated documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Supported file types for processing."""
    PDF = "pdf"
    WORD = "word"
    TEXT = "text"
    HTML = "html"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Processing status for files."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(str, Enum):
    """File validation status."""
    VALID = "valid"
    WARNING = "warning"
    FAILED = "failed"


# Request Models
class CreateSessionRequest(BaseModel):
    """Request to create upload session."""
    name: Optional[str] = Field(None, description="Session name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Response Models
class UploadResponse(BaseModel):
    """Response for file upload."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type")
    status: str = Field(..., description="Upload status")
    validation_status: ValidationStatus = Field(..., description="Validation result")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    queue_job_id: Optional[str] = Field(None, description="Queue job ID if auto-processed")


class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    session_id: str = Field(..., description="Upload session ID")
    total_files: int = Field(..., description="Total number of files")
    uploaded_files: List[UploadResponse] = Field(..., description="Successfully uploaded files")
    failed_files: List[UploadResponse] = Field(..., description="Failed file uploads")
    batch_queued: bool = Field(..., description="Whether batch was queued for processing")


class SessionResponse(BaseModel):
    """Response for session creation."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User who created the session")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(..., description="Session creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class FileStatusResponse(BaseModel):
    """Response for file status."""
    file_id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Current processing status")
    size: int = Field(..., description="File size in bytes")
    upload_status: str = Field(..., description="Upload validation status")
    processing_status: Optional[str] = Field(None, description="Processing queue status")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    processed_at: Optional[datetime] = Field(None, description="Processing completion time")
    processing_time: Optional[float] = Field(None, description="Processing duration in seconds")
    extracted_elements: Optional[int] = Field(None, description="Number of extracted elements")


class SessionStatusResponse(BaseModel):
    """Response for session status."""
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Session status")
    total_files: int = Field(..., description="Total files in session")
    processed_files: int = Field(..., description="Number of processed files")
    failed_files: int = Field(..., description="Number of failed files")
    overall_progress: float = Field(..., description="Overall progress percentage (0-1)")
    created_at: datetime = Field(..., description="Session creation time")
    files: List[FileStatusResponse] = Field(..., description="Individual file statuses")


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""
    queues: Dict[str, Dict[str, Any]] = Field(..., description="Queue statistics")
    timestamp: datetime = Field(..., description="Timestamp of statistics")


# WebSocket Message Models
class ProgressUpdate(BaseModel):
    """WebSocket progress update message."""
    type: str = Field(..., description="Message type")
    file_id: Optional[str] = Field(None, description="File ID for file-specific updates")
    session_id: Optional[str] = Field(None, description="Session ID for session updates")
    data: Dict[str, Any] = Field(..., description="Progress data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


# Error Response Models
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = "validation_error"
    message: str = Field(..., description="Validation error message")
    field_errors: List[Dict[str, str]] = Field(..., description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")