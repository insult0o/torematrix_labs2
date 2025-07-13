import logging
import pytest
from torematrix.core.events.event_types import Event, DocumentEventTypes
from torematrix.core.events.middleware import (
    ValidationMiddleware, LoggingMiddleware,
    MetricsMiddleware, FilterMiddleware
)

@pytest.fixture
def test_event():
    return Event(
        event_type=DocumentEventTypes.PROCESSING_STARTED.value,
        payload={"document_id": "test123"}
    )

@pytest.mark.asyncio
async def test_validation_middleware():
    middleware = ValidationMiddleware()
    
    # Valid event
    event = Event(event_type="test", payload={})
    result = await middleware(event)
    assert result == event
    
    # Invalid event type
    event = Event(event_type="", payload={})
    result = await middleware(event)
    assert result is None
    
    # Invalid payload
    event = Event(event_type="test", payload="not a dict")  # type: ignore
    result = await middleware(event)
    assert result is None

@pytest.mark.asyncio
async def test_logging_middleware(caplog):
    middleware = LoggingMiddleware(log_level=logging.INFO)
    event = Event(event_type="test", payload={})
    
    with caplog.at_level(logging.INFO):
        result = await middleware(event)
        assert "Processing event: test" in caplog.text
    
    assert result == event

@pytest.mark.asyncio
async def test_metrics_middleware():
    middleware = MetricsMiddleware()
    
    # Process normal event
    event1 = Event(
        event_type=DocumentEventTypes.PROCESSING_STARTED.value,
        payload={}
    )
    await middleware(event1)
    
    # Process error event
    event2 = Event(
        event_type=DocumentEventTypes.ERROR_OCCURRED.value,
        payload={"error_type": "validation_error"}
    )
    await middleware(event2)
    
    metrics = middleware.get_metrics()
    assert metrics["event_counts"][DocumentEventTypes.PROCESSING_STARTED.value] == 1
    assert metrics["event_counts"][DocumentEventTypes.ERROR_OCCURRED.value] == 1
    assert metrics["error_counts"]["validation_error"] == 1
    assert metrics["total_events"] == 2
    assert metrics["total_errors"] == 1

@pytest.mark.asyncio
async def test_filter_middleware():
    allowed_types = [DocumentEventTypes.PROCESSING_STARTED.value]
    middleware = FilterMiddleware(allowed_types)
    
    # Allowed event type
    event1 = Event(
        event_type=DocumentEventTypes.PROCESSING_STARTED.value,
        payload={}
    )
    result1 = await middleware(event1)
    assert result1 == event1
    
    # Filtered event type
    event2 = Event(
        event_type=DocumentEventTypes.ERROR_OCCURRED.value,
        payload={}
    )
    result2 = await middleware(event2)
    assert result2 is None

@pytest.mark.asyncio
async def test_middleware_exception_handling():
    class FailingMiddleware(ValidationMiddleware):
        async def process(self, event: Event) -> Event:
            raise Exception("Test error")
    
    middleware = FailingMiddleware()
    event = Event(event_type="test", payload={})
    result = await middleware(event)
    assert result is None