# Event Bus System - Technical Documentation

The Event Bus system provides a robust, asynchronous, and type-safe communication layer between components in the TORE Matrix V3 platform. It follows a publish-subscribe pattern with support for middleware, performance monitoring, and strong typing.

## Core Components

### EventBus

The main event bus implementation that provides:
- Asynchronous event publishing and handling
- Dynamic handler registration
- Middleware support
- Performance monitoring
- Error handling and resilience

```python
# Initialize and start the event bus
bus = EventBus()
await bus.start()

# Subscribe to events
bus.subscribe("document.processing.started", handler)

# Publish events
await bus.publish(Event(
    event_type="document.processing.started",
    payload={"document_id": "doc123"}
))

# Monitor performance
metrics = bus.get_metrics()
```

### Event Types

A type-safe event system with specific event types for document processing:

```python
# Base event type with core attributes
Event(
    event_type="test_event",
    payload={"key": "value"},
    priority=EventPriority.NORMAL,
    correlation_id="corr123",
    metadata={"version": "1.0"}
)

# Document-specific event
DocumentEvent(
    event_type=DocumentEventTypes.PROCESSING_STARTED,
    payload={"format": "pdf"},
    document_id="doc123",
    page_numbers=[1, 2, 3]
)

# Validation event
ValidationEvent(
    event_type=DocumentEventTypes.VALIDATION_REQUIRED,
    document_id="doc123",
    validation_type="ocr",
    validation_status="pending"
)

# Error event
ErrorEvent(
    event_type=DocumentEventTypes.ERROR_OCCURRED,
    document_id="doc123",
    error_type="processing_error",
    error_message="Failed to process"
)
```

### Middleware System

Pluggable middleware system for event processing:

```python
# Validation middleware
bus.add_middleware(ValidationMiddleware())

# Logging middleware with custom level
bus.add_middleware(LoggingMiddleware(log_level=logging.INFO))

# Metrics collection
metrics_middleware = MetricsMiddleware()
bus.add_middleware(metrics_middleware)
metrics = metrics_middleware.get_metrics()

# Event filtering
bus.add_middleware(FilterMiddleware(
    event_types=[DocumentEventTypes.PROCESSING_STARTED]
))
```

### Performance Monitoring

Comprehensive metrics collection:

```python
# Get metrics for event bus
metrics = bus.get_metrics()

# Event metrics
event_metrics = metrics["events"]
total_events = metrics["total"]["total_events"]
error_rate = metrics["total"]["error_rate"]

# Handler performance
handler_metrics = metrics["handlers"]
handler_success = handler_metrics["handler_name"].success_count
avg_execution = handler_metrics["handler_name"].average_execution_time

# Queue monitoring
queue_size = metrics["queue_size"]
```

## Usage Examples

### Basic Event Handling

```python
async def process_document(event: DocumentEvent):
    doc_id = event.document_id
    try:
        # Process document
        await process_pages(event.page_numbers)
        
        # Publish success event
        await bus.publish(DocumentEvent(
            event_type=DocumentEventTypes.PROCESSING_COMPLETED,
            document_id=doc_id,
            payload={"status": "success"}
        ))
    except Exception as e:
        # Publish error event
        await bus.publish(ErrorEvent(
            event_type=DocumentEventTypes.ERROR_OCCURRED,
            document_id=doc_id,
            error_type="processing_error",
            error_message=str(e)
        ))

# Subscribe to processing events
bus.subscribe(
    DocumentEventTypes.PROCESSING_STARTED, 
    process_document
)
```

### Using Middleware for Validation

```python
class SchemaValidationMiddleware(BaseMiddleware):
    async def process(self, event: Event) -> Optional[Event]:
        if not self.validate_schema(event.payload):
            return None
        return event
        
    def validate_schema(self, payload: Dict) -> bool:
        # Implement schema validation
        pass

# Add middleware to bus
bus.add_middleware(SchemaValidationMiddleware())
```

### Performance Monitoring

```python
# Start performance monitoring
bus = EventBus()
await bus.start()  # Also starts metrics collection

# Process some events
for doc_id in documents:
    await bus.publish(DocumentEvent(
        event_type=DocumentEventTypes.PROCESSING_STARTED,
        document_id=doc_id
    ))

# Get performance metrics
metrics = bus.get_metrics()
print(f"Processed {metrics['total']['total_events']} events")
print(f"Error rate: {metrics['total']['error_rate']:.2%}")
print(f"Average processing time: {metrics['total']['average_processing_time']:.2f}s")
```

## Best Practices

1. **Event Types**
   - Use specific event types from `DocumentEventTypes`
   - Include relevant metadata and correlation IDs
   - Follow the event naming convention: `domain.action.state`

2. **Error Handling**
   - Always handle exceptions in event handlers
   - Use `ErrorEvent` for error reporting
   - Include detailed error information

3. **Performance**
   - Monitor metrics regularly
   - Set appropriate handler timeouts
   - Use middleware for filtering when possible

4. **Middleware**
   - Keep middleware functions lightweight
   - Order middleware by priority
   - Use validation middleware early in the chain

5. **Testing**
   - Write tests for event handlers
   - Mock long-running operations
   - Verify metrics in tests

## Architecture Notes

1. **Async Implementation**
   - Built on `asyncio` for non-blocking operation
   - Uses queue for event buffering
   - Supports both sync and async handlers

2. **Type Safety**
   - Full type hints support
   - Event type validation
   - Payload schema validation (via middleware)

3. **Monitoring**
   - Real-time metrics collection
   - Performance tracking
   - Memory usage monitoring
   - Queue size tracking

4. **Reliability**
   - Error isolation per handler
   - Middleware error handling
   - Queue overflow protection
   - Clean shutdown support