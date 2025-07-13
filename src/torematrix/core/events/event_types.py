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