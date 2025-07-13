import asyncio
import pytest
from datetime import datetime, timedelta

from torematrix.core.events.event_types import Event, DocumentEventTypes
from torematrix.core.events.monitoring import (
    PerformanceMonitor, EventMetrics, HandlerMetrics,
    PerformanceSnapshot
)

@pytest.fixture
def monitor():
    return PerformanceMonitor()

@pytest.fixture
def test_event():
    return Event(
        event_type=DocumentEventTypes.PROCESSING_STARTED.value,
        payload={"document_id": "test123"}
    )

def test_record_event_processing(monitor, test_event):
    monitor.record_event_processing(test_event, 0.1)
    monitor.record_event_processing(test_event, 0.2)
    
    metrics = monitor.get_event_metrics(test_event.event_type)
    event_metrics = metrics[test_event.event_type]
    
    assert event_metrics.count == 2
    assert event_metrics.total_processing_time == 0.3
    assert event_metrics.max_processing_time == 0.2
    assert event_metrics.error_count == 0
    assert isinstance(event_metrics.last_occurrence, datetime)

def test_record_event_processing_with_error(monitor, test_event):
    monitor.record_event_processing(test_event, 0.1, success=False)
    
    metrics = monitor.get_event_metrics(test_event.event_type)
    event_metrics = metrics[test_event.event_type]
    
    assert event_metrics.count == 1
    assert event_metrics.error_count == 1

def test_record_handler_execution(monitor):
    handler_name = "test_handler"
    monitor.record_handler_execution(handler_name, 0.1)
    monitor.record_handler_execution(handler_name, 0.2)
    
    metrics = monitor.get_handler_metrics(handler_name)
    handler_metrics = metrics[handler_name]
    
    assert handler_metrics.success_count == 2
    assert handler_metrics.error_count == 0
    assert handler_metrics.total_execution_time == 0.3
    assert handler_metrics.max_execution_time == 0.2

def test_record_handler_execution_with_error(monitor):
    handler_name = "test_handler"
    monitor.record_handler_execution(handler_name, 0.1, success=False)
    
    metrics = monitor.get_handler_metrics(handler_name)
    handler_metrics = metrics[handler_name]
    
    assert handler_metrics.success_count == 0
    assert handler_metrics.error_count == 1

def test_get_total_metrics(monitor, test_event):
    monitor.record_event_processing(test_event, 0.1)
    monitor.record_event_processing(test_event, 0.2, success=False)
    
    total_metrics = monitor.get_total_metrics()
    
    assert total_metrics["total_events"] == 2
    assert total_metrics["total_errors"] == 1
    assert total_metrics["total_processing_time"] == 0.3
    assert total_metrics["error_rate"] == 0.5
    assert total_metrics["average_processing_time"] == 0.15
    assert "events_per_second" in total_metrics

@pytest.mark.asyncio
async def test_snapshot_collection(monitor):
    event_queue = asyncio.Queue()
    await event_queue.put("test")  # Add item to queue
    
    # Create a snapshot
    snapshot = PerformanceSnapshot(
        events_processed=10,
        total_processing_time=1.0,
        error_count=1,
        queue_size=1,
        memory_usage_mb=100.0
    )
    monitor.snapshots.append(snapshot)
    
    # Test getting performance trend
    trend = monitor.get_performance_trend(duration=timedelta(minutes=1))
    assert len(trend) == 1
    assert trend[0].events_processed == 10
    assert trend[0].total_processing_time == 1.0
    assert trend[0].error_count == 1
    assert trend[0].queue_size == 1
    assert trend[0].memory_usage_mb == 100.0

def test_metrics_calculations():
    event_metrics = EventMetrics(event_type="test")
    event_metrics.count = 2
    event_metrics.total_processing_time = 0.3
    
    assert event_metrics.average_processing_time == 0.15
    
    handler_metrics = HandlerMetrics(handler_name="test")
    handler_metrics.success_count = 2
    handler_metrics.error_count = 1
    handler_metrics.total_execution_time = 0.6
    
    assert handler_metrics.average_execution_time == 0.2

def test_empty_metrics():
    event_metrics = EventMetrics(event_type="test")
    assert event_metrics.average_processing_time == 0.0
    
    handler_metrics = HandlerMetrics(handler_name="test")
    assert handler_metrics.average_execution_time == 0.0