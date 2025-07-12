import pytest
from datetime import datetime
from torematrix.core.events.event_types import (
    Event, EventPriority, DocumentEventTypes, 
    DocumentEvent, ValidationEvent, ErrorEvent
)

def test_event_creation():
    event = Event(
        event_type="test_event",
        payload={"key": "value"},
        priority=EventPriority.NORMAL,
        source="test_source",
        id="test_id",
        correlation_id="test_correlation",
        metadata={"meta": "data"},
        trace_ids=["trace1", "trace2"]
    )
    
    assert event.event_type == "test_event"
    assert event.payload == {"key": "value"}
    assert isinstance(event.timestamp, datetime)
    assert event.priority == EventPriority.NORMAL
    assert event.source == "test_source"
    assert event.id == "test_id"
    assert event.correlation_id == "test_correlation"
    assert event.metadata == {"meta": "data"}
    assert event.trace_ids == ["trace1", "trace2"]

def test_event_priority_enum():
    assert EventPriority.IMMEDIATE.value == "immediate"
    assert EventPriority.NORMAL.value == "normal"
    assert EventPriority.DEFERRED.value == "deferred"
    
def test_event_default_values():
    event = Event(event_type="test", payload={})
    
    assert isinstance(event.timestamp, datetime)
    assert event.priority == EventPriority.NORMAL
    assert event.source is None
    assert event.id is None
    assert event.correlation_id is None
    assert event.metadata == {}
    assert event.trace_ids == []

def test_document_event_types():
    assert DocumentEventTypes.PROCESSING_STARTED.value == "document.processing.started"
    assert DocumentEventTypes.OCR_COMPLETED.value == "document.ocr.completed"
    assert DocumentEventTypes.VALIDATION_REQUIRED.value == "document.validation.required"

def test_document_event():
    event = DocumentEvent(
        event_type=DocumentEventTypes.PROCESSING_STARTED.value,
        payload={"format": "pdf"},
        document_id="doc123",
        page_numbers=[1, 2, 3]
    )
    
    assert event.document_id == "doc123"
    assert event.page_numbers == [1, 2, 3]
    assert event.event_type == DocumentEventTypes.PROCESSING_STARTED.value

def test_validation_event():
    event = ValidationEvent(
        event_type=DocumentEventTypes.VALIDATION_REQUIRED.value,
        payload={"format": "pdf"},
        document_id="doc123",
        validation_type="ocr",
        validation_status="pending",
        validation_errors=[{"code": "low_confidence", "page": 1}]
    )
    
    assert event.validation_type == "ocr"
    assert event.validation_status == "pending"
    assert len(event.validation_errors) == 1
    assert event.validation_errors[0]["code"] == "low_confidence"

def test_error_event():
    event = ErrorEvent(
        event_type=DocumentEventTypes.ERROR_OCCURRED.value,
        payload={"format": "pdf"},
        document_id="doc123",
        error_type="processing_error",
        error_message="Failed to process document",
        stack_trace="traceback...",
        recovery_attempted=True
    )
    
    assert event.error_type == "processing_error"
    assert event.error_message == "Failed to process document"
    assert event.stack_trace == "traceback..."
    assert event.recovery_attempted is True