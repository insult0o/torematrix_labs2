from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List

class EventPriority(Enum):
    IMMEDIATE = "immediate"
    NORMAL = "normal"
    DEFERRED = "deferred"

class DocumentEventTypes(Enum):
    PROCESSING_STARTED = "document.processing.started"
    PROCESSING_COMPLETED = "document.processing.completed"
    OCR_STARTED = "document.ocr.started"
    OCR_COMPLETED = "document.ocr.completed"
    LAYOUT_ANALYZED = "document.layout.analyzed"
    TABLE_EXTRACTED = "document.table.extracted"
    TEXT_EXTRACTED = "document.text.extracted"
    VALIDATION_REQUIRED = "document.validation.required"
    VALIDATION_COMPLETED = "document.validation.completed"
    ERROR_OCCURRED = "document.error.occurred"
    UI_STATE_CHANGED = "ui.state.changed"

@dataclass
class Event:
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_ids: List[str] = field(default_factory=list)

@dataclass
class DocumentEvent(Event):
    document_id: str = ""
    page_numbers: Optional[List[int]] = None

@dataclass
class ValidationEvent(DocumentEvent):
    validation_type: str = ""
    validation_status: str = ""
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ErrorEvent(DocumentEvent):
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False


# Queue and Processing Events for Agent 2
class ProcessingEventTypes(Enum):
    """Event types for document processing pipeline."""
    JOB_ENQUEUED = "processing.job.enqueued"
    JOB_STARTED = "processing.job.started"
    JOB_PROGRESS = "processing.job.progress"
    JOB_COMPLETED = "processing.job.completed"
    JOB_FAILED = "processing.job.failed"
    JOB_RETRIED = "processing.job.retried"
    JOB_CANCELLED = "processing.job.cancelled"
    
    BATCH_ENQUEUED = "processing.batch.enqueued"
    BATCH_STARTED = "processing.batch.started" 
    BATCH_PROGRESS = "processing.batch.progress"
    BATCH_COMPLETED = "processing.batch.completed"
    BATCH_FAILED = "processing.batch.failed"
    
    QUEUE_STATUS_CHANGED = "processing.queue.status_changed"
    WORKER_STATUS_CHANGED = "processing.worker.status_changed"
    
    PROGRESS_UPDATED = "processing.progress.updated"
    SESSION_PROGRESS_UPDATED = "processing.session.progress_updated"


@dataclass  
class ProcessingEvent(Event):
    """Event for processing pipeline operations."""
    file_id: Optional[str] = None
    job_id: Optional[str] = None
    batch_id: Optional[str] = None
    session_id: Optional[str] = None
    queue_name: Optional[str] = None
    worker_id: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    error: Optional[str] = None
    retry_count: Optional[int] = None
    processing_time: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)