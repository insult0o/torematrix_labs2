import pytest
import asyncio
from typing import List, Optional, Dict
from dataclasses import dataclass

from torematrix.core.events.event_bus import EventBus
from torematrix.core.events.event_types import Event, EventHandler
from torematrix.core.events.middleware import EventMiddleware

# Example domain events for testing
@dataclass
class DocumentCreated(Event):
    doc_id: str
    title: str
    page_count: int

@dataclass
class PageProcessed(Event):
    doc_id: str
    page_num: int
    text: str

@dataclass
class DocumentCompleted(Event):
    doc_id: str
    total_pages: int
    processing_time: float

# Example components that communicate via events
class DocumentProcessor:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.processed_pages: Dict[str, List[str]] = {}
        
        # Subscribe to events
        self.event_bus.subscribe(DocumentCreated, self.handle_document_created)
        self.event_bus.subscribe(PageProcessed, self.handle_page_processed)
    
    async def handle_document_created(self, event: DocumentCreated):
        """Initialize processing for a new document"""
        self.processed_pages[event.doc_id] = []
        
        # Simulate processing each page
        for page_num in range(event.page_count):
            text = f"Page {page_num} content"
            await self.event_bus.publish(PageProcessed(
                doc_id=event.doc_id,
                page_num=page_num,
                text=text
            ))

    async def handle_page_processed(self, event: PageProcessed):
        """Track processed pages and check for completion"""
        doc_pages = self.processed_pages[event.doc_id]
        doc_pages.append(event.text)
        
        # Check if document is complete
        original_event = await self.event_bus.get_event(DocumentCreated, 
                                                      lambda e: e.doc_id == event.doc_id)
        if original_event and len(doc_pages) == original_event.page_count:
            await self.event_bus.publish(DocumentCompleted(
                doc_id=event.doc_id,
                total_pages=len(doc_pages),
                processing_time=1.5  # Simulated time
            ))

class DocumentValidator:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.completed_docs: List[str] = []
        
        # Subscribe to completion events
        self.event_bus.subscribe(DocumentCompleted, self.handle_document_completed)
    
    async def handle_document_completed(self, event: DocumentCompleted):
        """Validate and track completed documents"""
        self.completed_docs.append(event.doc_id)

# Test metrics middleware
class MetricsMiddleware(EventMiddleware):
    def __init__(self):
        self.event_counts: Dict[str, int] = {}
    
    async def before_publish(self, event: Event):
        event_type = event.__class__.__name__
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
    async def after_publish(self, event: Event):
        pass

@pytest.fixture
async def event_bus():
    """Create event bus with metrics middleware"""
    metrics = MetricsMiddleware()
    bus = EventBus([metrics])
    yield bus
    await bus.shutdown()

@pytest.fixture
def processor(event_bus):
    """Create document processor component"""
    return DocumentProcessor(event_bus)

@pytest.fixture
def validator(event_bus):
    """Create document validator component"""
    return DocumentValidator(event_bus)

@pytest.mark.asyncio
async def test_document_processing_flow(
    event_bus: EventBus,
    processor: DocumentProcessor,
    validator: DocumentValidator
):
    """Test complete document processing flow between components"""
    doc_id = "test-doc-1"
    
    # Create new document
    await event_bus.publish(DocumentCreated(
        doc_id=doc_id,
        title="Test Document",
        page_count=3
    ))
    
    # Wait for processing to complete
    await asyncio.sleep(0.1)
    
    # Verify processor state
    assert len(processor.processed_pages[doc_id]) == 3
    assert all("Page" in text for text in processor.processed_pages[doc_id])
    
    # Verify validator received completion
    assert doc_id in validator.completed_docs
    
    # Verify metrics
    metrics = event_bus.middleware[0]
    assert metrics.event_counts["DocumentCreated"] == 1
    assert metrics.event_counts["PageProcessed"] == 3
    assert metrics.event_counts["DocumentCompleted"] == 1

@pytest.mark.asyncio
async def test_event_replay(
    event_bus: EventBus,
    processor: DocumentProcessor
):
    """Test replaying events for debugging"""
    doc_id = "test-doc-2"
    
    # Create and process document
    await event_bus.publish(DocumentCreated(
        doc_id=doc_id,
        title="Test Document 2",
        page_count=2
    ))
    
    await asyncio.sleep(0.1)
    
    # Get all events for the document
    events = await event_bus.get_events(
        lambda e: hasattr(e, 'doc_id') and e.doc_id == doc_id
    )
    
    # Verify event sequence
    assert len(events) == 4  # Created + 2 pages + Completed
    assert isinstance(events[0], DocumentCreated)
    assert isinstance(events[1], PageProcessed)
    assert isinstance(events[2], PageProcessed)
    assert isinstance(events[3], DocumentCompleted)

@pytest.mark.asyncio
async def test_error_handling(event_bus: EventBus):
    """Test error handling in event processing"""
    error_received = False
    
    # Handler that raises an error
    async def error_handler(event: Event):
        raise ValueError("Test error")
    
    # Error callback
    def on_error(event: Event, error: Exception):
        nonlocal error_received
        error_received = True
        assert isinstance(error, ValueError)
    
    # Subscribe with error callback
    event_bus.subscribe(DocumentCreated, error_handler, on_error=on_error)
    
    # Publish event that will cause error
    await event_bus.publish(DocumentCreated(
        doc_id="error-doc",
        title="Error Test",
        page_count=1
    ))
    
    await asyncio.sleep(0.1)
    assert error_received