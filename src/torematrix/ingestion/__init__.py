"""
Document ingestion system for TORE Matrix V3.

This package provides comprehensive file upload, validation, and processing
capabilities for 15+ document formats via Unstructured.io integration.
"""

# Core models and configuration (no external dependencies)
from .models import FileMetadata, FileStatus, FileType, UploadResult, UploadSession
from .queue_config import QueueConfig, RetryPolicy, WorkerConfig, QueueHealthConfig, PriorityConfig

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
]

# Optional imports with dependencies
try:
    from .queue_manager import QueueManager, JobInfo, QueueStats
    __all__.extend(["QueueManager", "JobInfo", "QueueStats"])
except ImportError:
    pass

try:
    from .progress import ProgressTracker, FileProgress, SessionProgress
    __all__.extend(["ProgressTracker", "FileProgress", "SessionProgress"])
except ImportError:
    pass

try:
    from .processors import DocumentProcessor, BatchProcessor, ProcessingResult, BatchResult
    __all__.extend(["DocumentProcessor", "BatchProcessor", "ProcessingResult", "BatchResult"])
except ImportError:
    pass