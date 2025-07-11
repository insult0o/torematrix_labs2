#!/usr/bin/env python3
"""
Event Types for V1 Enhanced Event System

Defines all event types and data structures for the enhanced V1 event system,
providing type safety and consistency across the application.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import uuid


class EventPriority(Enum):
    """Event priority levels for processing order."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventTypeV1(Enum):
    """Enhanced event types for V1 system with V2 patterns."""
    
    # Application Lifecycle Events
    APPLICATION_STARTED = "application_started"
    APPLICATION_CLOSING = "application_closing"
    APPLICATION_ERROR = "application_error"
    
    # Document Events
    DOCUMENT_SELECTED = "document_selected"
    DOCUMENT_LOADED = "document_loaded"
    DOCUMENT_PROCESSING_STARTED = "document_processing_started"
    DOCUMENT_PROCESSING_PROGRESS = "document_processing_progress"
    DOCUMENT_PROCESSING_COMPLETED = "document_processing_completed"
    DOCUMENT_PROCESSING_FAILED = "document_processing_failed"
    DOCUMENT_SAVED = "document_saved"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_STATE_CHANGED = "document_state_changed"
    
    # PDF Events
    PDF_PAGE_CHANGED = "pdf_page_changed"
    PDF_ZOOM_CHANGED = "pdf_zoom_changed"
    PDF_LOCATION_HIGHLIGHTED = "pdf_location_highlighted"
    PDF_TEXT_SELECTION_HIGHLIGHTED = "pdf_text_selection_highlighted"
    PDF_CURSOR_LOCATION_UPDATED = "pdf_cursor_location_updated"
    PDF_AREA_SELECTED = "pdf_area_selected"
    PDF_COORDINATE_MAPPED = "pdf_coordinate_mapped"
    
    # Validation Events
    MANUAL_VALIDATION_STARTED = "manual_validation_started"
    MANUAL_VALIDATION_COMPLETED = "manual_validation_completed"
    MANUAL_VALIDATION_CANCELLED = "manual_validation_cancelled"
    QA_VALIDATION_STARTED = "qa_validation_started"
    QA_VALIDATION_COMPLETED = "qa_validation_completed"
    PAGE_VALIDATION_STARTED = "page_validation_started"
    PAGE_VALIDATION_COMPLETED = "page_validation_completed"
    VALIDATION_ISSUE_DETECTED = "validation_issue_detected"
    VALIDATION_ISSUE_RESOLVED = "validation_issue_resolved"
    
    # Area Events
    AREA_SELECTED = "area_selected"
    AREA_CREATED = "area_created"
    AREA_MODIFIED = "area_modified"
    AREA_DELETED = "area_deleted"
    AREA_EXCLUDED = "area_excluded"
    AREA_INCLUDED = "area_included"
    AREA_HIGHLIGHTED = "area_highlighted"
    AREA_STORAGE_UPDATED = "area_storage_updated"
    
    # Project Events
    PROJECT_CREATED = "project_created"
    PROJECT_LOADED = "project_loaded"
    PROJECT_SAVED = "project_saved"
    PROJECT_CLOSED = "project_closed"
    PROJECT_STATE_CHANGED = "project_state_changed"
    PROJECT_BACKUP_CREATED = "project_backup_created"
    
    # UI Events
    TAB_CHANGED = "tab_changed"
    WIDGET_ACTIVATED = "widget_activated"
    WIDGET_DEACTIVATED = "widget_deactivated"
    STATUS_MESSAGE_CHANGED = "status_message_changed"
    PROGRESS_UPDATED = "progress_updated"
    THEME_CHANGED = "theme_changed"
    
    # Processing Events
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    QUALITY_ASSESSMENT_COMPLETED = "quality_assessment_completed"
    POST_PROCESSING_STARTED = "post_processing_started"
    POST_PROCESSING_COMPLETED = "post_processing_completed"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    WARNING_OCCURRED = "warning_occurred"
    CRITICAL_ERROR = "critical_error"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    
    # State Events
    STATE_SAVED = "state_saved"
    STATE_RESTORED = "state_restored"
    PROGRESS_SAVED = "progress_saved"
    PROGRESS_RESTORED = "progress_restored"
    
    # Performance Events
    PERFORMANCE_METRIC_UPDATED = "performance_metric_updated"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


@dataclass
class V1EventData:
    """Enhanced event data container with type safety."""
    
    # Event metadata
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventTypeV1 = EventTypeV1.APPLICATION_STARTED
    timestamp: datetime = field(default_factory=datetime.now)
    sender: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    
    # Event payload
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    processed: bool = False
    processing_time: Optional[float] = None
    error: Optional[str] = None
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data value with default fallback."""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """Set data value."""
        self.data[key] = value
    
    def has_data(self, key: str) -> bool:
        """Check if data key exists."""
        return key in self.data
    
    def mark_processed(self, processing_time: Optional[float] = None, error: Optional[str] = None):
        """Mark event as processed."""
        self.processed = True
        self.processing_time = processing_time
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'sender': self.sender,
            'priority': self.priority.value,
            'data': self.data,
            'processed': self.processed,
            'processing_time': self.processing_time,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'V1EventData':
        """Create from dictionary."""
        return cls(
            event_id=data.get('event_id', str(uuid.uuid4())),
            event_type=EventTypeV1(data.get('event_type', 'application_started')),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            sender=data.get('sender', 'unknown'),
            priority=EventPriority(data.get('priority', 2)),
            data=data.get('data', {}),
            processed=data.get('processed', False),
            processing_time=data.get('processing_time'),
            error=data.get('error')
        )


@dataclass
class DocumentEventData:
    """Specialized event data for document events."""
    
    document_id: str = ""
    document_name: str = ""
    file_path: str = ""
    page_number: Optional[int] = None
    page_count: Optional[int] = None
    processing_stage: str = ""
    quality_score: Optional[float] = None
    areas_count: Optional[int] = None
    validation_status: str = ""
    
    def to_event_data(self, event_type: EventTypeV1, sender: str = "document_processor") -> V1EventData:
        """Convert to V1EventData."""
        return V1EventData(
            event_type=event_type,
            sender=sender,
            data={
                'document_id': self.document_id,
                'document_name': self.document_name,
                'file_path': self.file_path,
                'page_number': self.page_number,
                'page_count': self.page_count,
                'processing_stage': self.processing_stage,
                'quality_score': self.quality_score,
                'areas_count': self.areas_count,
                'validation_status': self.validation_status
            }
        )


@dataclass
class PDFEventData:
    """Specialized event data for PDF events."""
    
    page_number: int = 1
    zoom_level: float = 1.0
    coordinates: Dict[str, float] = field(default_factory=dict)
    text_selection: str = ""
    area_type: str = ""
    area_id: Optional[str] = None
    highlight_type: str = "selection"
    
    def to_event_data(self, event_type: EventTypeV1, sender: str = "pdf_viewer") -> V1EventData:
        """Convert to V1EventData."""
        return V1EventData(
            event_type=event_type,
            sender=sender,
            data={
                'page_number': self.page_number,
                'zoom_level': self.zoom_level,
                'coordinates': self.coordinates,
                'text_selection': self.text_selection,
                'area_type': self.area_type,
                'area_id': self.area_id,
                'highlight_type': self.highlight_type
            }
        )


@dataclass
class ValidationEventData:
    """Specialized event data for validation events."""
    
    validation_type: str = ""  # manual, qa, page
    document_id: str = ""
    page_number: Optional[int] = None
    issues_count: int = 0
    resolved_count: int = 0
    quality_score: Optional[float] = None
    validation_status: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_event_data(self, event_type: EventTypeV1, sender: str = "validation_widget") -> V1EventData:
        """Convert to V1EventData."""
        return V1EventData(
            event_type=event_type,
            sender=sender,
            data={
                'validation_type': self.validation_type,
                'document_id': self.document_id,
                'page_number': self.page_number,
                'issues_count': self.issues_count,
                'resolved_count': self.resolved_count,
                'quality_score': self.quality_score,
                'validation_status': self.validation_status,
                'errors': self.errors,
                'corrections': self.corrections
            }
        )


@dataclass
class AreaEventData:
    """Specialized event data for area events."""
    
    area_id: str = ""
    area_type: str = ""
    page_number: int = 1
    coordinates: Dict[str, float] = field(default_factory=dict)
    excluded: bool = False
    area_name: str = ""
    area_description: str = ""
    confidence: Optional[float] = None
    
    def to_event_data(self, event_type: EventTypeV1, sender: str = "area_manager") -> V1EventData:
        """Convert to V1EventData."""
        return V1EventData(
            event_type=event_type,
            sender=sender,
            data={
                'area_id': self.area_id,
                'area_type': self.area_type,
                'page_number': self.page_number,
                'coordinates': self.coordinates,
                'excluded': self.excluded,
                'area_name': self.area_name,
                'area_description': self.area_description,
                'confidence': self.confidence
            }
        )


# Event Factory Functions
def create_document_event(event_type: EventTypeV1, document_data: DocumentEventData) -> V1EventData:
    """Create a document event."""
    return document_data.to_event_data(event_type)


def create_pdf_event(event_type: EventTypeV1, pdf_data: PDFEventData) -> V1EventData:
    """Create a PDF event."""
    return pdf_data.to_event_data(event_type)


def create_validation_event(event_type: EventTypeV1, validation_data: ValidationEventData) -> V1EventData:
    """Create a validation event."""
    return validation_data.to_event_data(event_type)


def create_area_event(event_type: EventTypeV1, area_data: AreaEventData) -> V1EventData:
    """Create an area event."""
    return area_data.to_event_data(event_type)


def create_simple_event(event_type: EventTypeV1, sender: str, data: Dict[str, Any] = None, 
                       priority: EventPriority = EventPriority.NORMAL) -> V1EventData:
    """Create a simple event with basic data."""
    return V1EventData(
        event_type=event_type,
        sender=sender,
        priority=priority,
        data=data or {}
    )