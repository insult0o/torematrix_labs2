"""
File metadata models for the document ingestion system.

This module defines the core data structures used throughout the ingestion
pipeline, ensuring consistency across all components.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
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
    ARCHIVE = "archive"
    OTHER = "other"


class FileStatus(str, Enum):
    """File processing status stages."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class FileMetadata(BaseModel):
    """Complete file metadata for tracking throughout the pipeline."""
    
    # Identification
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Detected file type")
    mime_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    hash: str = Field(..., description="SHA-256 hash")
    
    # Upload information
    upload_session_id: str = Field(..., description="Associated upload session")
    uploaded_by: str = Field(..., description="User ID who uploaded the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    
    # Storage information
    storage_key: str = Field(..., description="Storage backend key/path")
    storage_backend: str = Field(default="local", description="Storage backend used")
    
    # Processing status
    status: FileStatus = Field(default=FileStatus.PENDING, description="Current processing status")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors if any")
    processing_errors: List[str] = Field(default_factory=list, description="Processing errors if any")
    
    # Extracted metadata
    document_metadata: Dict[str, Any] = Field(default_factory=dict, description="Document-specific metadata")
    page_count: Optional[int] = Field(None, description="Number of pages (if applicable)")
    word_count: Optional[int] = Field(None, description="Word count (if applicable)")
    language: Optional[str] = Field(None, description="Detected language")
    
    # Processing results
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    processing_time: Optional[float] = Field(None, description="Processing duration in seconds")
    extracted_elements: Optional[int] = Field(None, description="Number of extracted elements")
    
    # Queue information (for Agent 2)
    queue_job_id: Optional[str] = Field(None, description="Associated queue job ID")
    retry_count: int = Field(default=0, description="Number of processing attempts")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "document.pdf",
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "size": 1048576,
                "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "upload_session_id": "session-123",
                "uploaded_by": "user-456",
                "uploaded_at": "2024-01-15T10:30:00Z",
                "storage_key": "documents/2024/01/550e8400-e29b-41d4-a716-446655440000",
                "status": "uploaded"
            }
        }


class UploadResult(BaseModel):
    """Result of a file upload operation."""
    
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type")
    hash: str = Field(..., description="File content hash")
    validation_status: str = Field(..., description="Validation result: valid, warning, or failed")
    errors: List[str] = Field(default_factory=list, description="Validation errors if any")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted metadata")
    storage_key: str = Field(..., description="Storage location key")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "document.pdf",
                "size": 1048576,
                "mime_type": "application/pdf",
                "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "validation_status": "valid",
                "errors": [],
                "metadata": {"pages": 10, "author": "John Doe"},
                "storage_key": "documents/2024/01/550e8400-e29b-41d4-a716-446655440000"
            }
        }


class UploadSession(BaseModel):
    """Upload session for managing multi-file uploads."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User who created the session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    files: List[UploadResult] = Field(default_factory=list, description="Files in this session")
    total_size: int = Field(default=0, description="Total size of all files in bytes")
    status: str = Field(default="active", description="Session status: active, completed, expired")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "created_at": "2024-01-15T10:00:00Z",
                "files": [],
                "total_size": 0,
                "status": "active",
                "metadata": {"name": "Q1 Reports Upload"}
            }
        }
    
    def add_file(self, result: UploadResult) -> None:
        """Add a file to the session and update totals."""
        self.files.append(result)
        self.total_size += result.size
        self.updated_at = datetime.utcnow()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary statistics."""
        return {
            "session_id": self.session_id,
            "total_files": len(self.files),
            "total_size": self.total_size,
            "valid_files": sum(1 for f in self.files if f.validation_status == "valid"),
            "warning_files": sum(1 for f in self.files if f.validation_status == "warning"),
            "failed_files": sum(1 for f in self.files if f.validation_status == "failed"),
            "status": self.status
        }