"""
Document ingestion system for TORE Matrix V3.

This package provides comprehensive file upload, validation, and processing
capabilities for 15+ document formats via Unstructured.io integration.
"""

from .models import FileMetadata, FileStatus, FileType, UploadResult, UploadSession
from .queue_config import QueueConfig, RetryPolicy, WorkerConfig, QueueHealthConfig, PriorityConfig
from .queue_manager import QueueManager, JobInfo, QueueStats
from .progress import ProgressTracker, FileProgress, SessionProgress
from .processors import DocumentProcessor, BatchProcessor, ProcessingResult, BatchResult

__all__ = [
    # Models
    "FileMetadata",
    "FileStatus", 
    "FileType",
    "UploadResult",
    "UploadSession",
    
    # Queue Configuration
    "QueueConfig",
    "RetryPolicy", 
    "WorkerConfig",
    "QueueHealthConfig",
    "PriorityConfig",
    
    # Queue Management
    "QueueManager",
    "JobInfo",
    "QueueStats",
    
    # Progress Tracking
    "ProgressTracker",
    "FileProgress",
    "SessionProgress",
    
    # Processing
    "DocumentProcessor",
    "BatchProcessor",
    "ProcessingResult",
    "BatchResult",
]