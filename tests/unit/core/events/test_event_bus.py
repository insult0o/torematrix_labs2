import asyncio
import pytest
import pytest_asyncio
from typing import List, Optional

from torematrix.core.events.event_bus import EventBus
from torematrix.core.events.event_types import Event, EventPriority

@pytest_asyncio.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()

@pytest.mark.asyncio
async def test_subscribe_and_publish(event_bus: EventBus):
    received_events: List[Event] = []
    
    def handler(event: Event):
        received_events.append(event)
    
    event_bus.subscribe("test_event", handler)
    
    test_event = Event(event_type="test_event", payload={"key": "value"})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert len(received_events) == 1
    assert received_events[0].event_type == "test_event"
    assert received_events[0].payload == {"key": "value"}
    
    # Check metrics
    metrics = event_bus.get_metrics()
    assert metrics["events"]["test_event"].count == 1
    assert metrics["total"]["total_events"] == 1
    assert metrics["total"]["total_errors"] == 0

@pytest.mark.asyncio
async def test_multiple_handlers(event_bus: EventBus):
    received_count = 0
    
    def handler1(event: Event):
        nonlocal received_count
        received_count += 1
    
    def handler2(event: Event):
        nonlocal received_count
        received_count += 1
    
    event_bus.subscribe("test_event", handler1)
    event_bus.subscribe("test_event", handler2)
    
    test_event = Event(event_type="test_event", payload={})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.1)
    assert received_count == 2
    
    # Check handler metrics
    metrics = event_bus.get_metrics()
    assert metrics["handlers"]["handler1"].success_count + metrics["handlers"]["handler2"].success_count == 2

@pytest.mark.asyncio
async def test_unsubscribe(event_bus: EventBus):
    received_events: List[Event] = []
    
    def handler(event: Event):
        received_events.append(event)
    
    event_bus.subscribe("test_event", handler)
    event_bus.unsubscribe("test_event", handler)
    
    test_event = Event(event_type="test_event", payload={})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.1)
    assert len(received_events) == 0

@pytest.mark.asyncio
async def test_middleware(event_bus: EventBus):
    received_events: List[Event] = []
    
    def handler(event: Event):
        received_events.append(event)
    
    async def test_middleware(event: Event) -> Optional[Event]:
        if event.payload.get("pass"):
            return event
        return None
    
    event_bus.subscribe("test_event", handler)
    event_bus.add_middleware(test_middleware)
    
    # This event should be dropped by middleware
    event1 = Event(event_type="test_event", payload={"pass": False})
    await event_bus.publish(event1)
    
    # This event should pass through
    event2 = Event(event_type="test_event", payload={"pass": True})
    await event_bus.publish(event2)
    
    await asyncio.sleep(0.1)
    assert len(received_events) == 1
    assert received_events[0].payload["pass"] is True
    
    # Check middleware effect on metrics
    metrics = event_bus.get_metrics()
    assert metrics["total"]["total_events"] == 2
    assert metrics["events"]["test_event"].count == 2

@pytest.mark.asyncio
async def test_async_handler(event_bus: EventBus):
    received_events: List[Event] = []
    
    async def async_handler(event: Event):
        await asyncio.sleep(0.1)
        received_events.append(event)
    
    event_bus.subscribe("test_event", async_handler)
    
    test_event = Event(event_type="test_event", payload={})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.2)
    assert len(received_events) == 1
    
    # Check async handler execution time
    metrics = event_bus.get_metrics()
    handler_metrics = metrics["handlers"]["async_handler"]
    assert handler_metrics.total_execution_time >= 0.1

@pytest.mark.asyncio
async def test_error_handling(event_bus: EventBus):
    def failing_handler(event: Event):
        raise Exception("Test error")
    
    event_bus.subscribe("test_event", failing_handler)
    
    test_event = Event(event_type="test_event", payload={})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.1)  # Should not raise exception
    
    # Check error metrics
    metrics = event_bus.get_metrics()
    # Handler errors are tracked separately from event processing errors
    assert metrics["total"]["total_errors"] == 0  # No event processing errors
    assert metrics["handlers"]["failing_handler"].error_count == 1  # But handler failed

@pytest.mark.asyncio
async def test_no_handlers(event_bus: EventBus):
    test_event = Event(event_type="unknown_event", payload={})
    await event_bus.publish(test_event)
    
    await asyncio.sleep(0.1)  # Should not raise exception
    
    # Check metrics for unhandled event
    metrics = event_bus.get_metrics()
    assert metrics["total"]["total_events"] == 1

@pytest.mark.asyncio
async def test_metrics_collection(event_bus: EventBus):
    def handler(event: Event):
        pass
    
    event_bus.subscribe("test_event", handler)
    
    # Publish multiple events
    for i in range(5):
        await event_bus.publish(Event(event_type="test_event", payload={"index": i}))
    
    await asyncio.sleep(0.1)
    
    metrics = event_bus.get_metrics()
    
    # Check event metrics
    assert metrics["events"]["test_event"].count == 5
    assert metrics["events"]["test_event"].total_processing_time > 0
    
    # Check handler metrics
    assert metrics["handlers"]["handler"].success_count == 5
    assert metrics["handlers"]["handler"].error_count == 0
    
    # Check total metrics
    assert metrics["total"]["total_events"] == 5
    assert metrics["total"]["error_rate"] == 0.0
    assert metrics["total"]["average_processing_time"] > 0
    
    # Check queue metrics
    assert isinstance(metrics["queue_size"], int)