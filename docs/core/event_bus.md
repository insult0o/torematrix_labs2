# Event Bus System

The Event Bus is a core infrastructure component that provides a centralized communication system for TORE Matrix Labs V3. It enables loose coupling between components through an asynchronous event-driven architecture.

## Architecture Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Producer   │──▶ │  Event Bus   │──▶ │  Subscriber  │
└──────────────┘    └──────────────┘    └──────────────┘
                          │
                    ┌──────────────┐
                    │  Middleware  │
                    └──────────────┘
```

### Key Components

1. **Event Bus**: Central message broker that handles event publishing and subscription
2. **Events**: Strongly typed messages with payload data
3. **Handlers**: Async functions that process specific event types
4. **Middleware**: Pluggable components for cross-cutting concerns

## Usage Examples

### 1. Basic Event Publishing and Subscription

```python
from torematrix.core.events.event_bus import EventBus
from torematrix.core.events.event_types import Event
from dataclasses import dataclass

# Define an event
@dataclass
class UserLoggedIn(Event):
    user_id: str
    timestamp: datetime

# Create event bus
event_bus = EventBus()

# Define handler
async def handle_login(event: UserLoggedIn):
    print(f"User {event.user_id} logged in at {event.timestamp}")

# Subscribe to events
event_bus.subscribe(UserLoggedIn, handle_login)

# Publish event
await event_bus.publish(UserLoggedIn(
    user_id="user123",
    timestamp=datetime.now()
))
```

### 2. Using Middleware

```python
from torematrix.core.events.middleware import EventMiddleware

class LoggingMiddleware(EventMiddleware):
    async def before_publish(self, event: Event):
        print(f"Publishing event: {event.__class__.__name__}")
        
    async def after_publish(self, event: Event):
        print(f"Published event: {event.__class__.__name__}")

# Create bus with middleware
event_bus = EventBus([LoggingMiddleware()])
```

### 3. Error Handling

```python
# Define error callback
def on_error(event: Event, error: Exception):
    print(f"Error processing {event}: {error}")

# Subscribe with error handling
event_bus.subscribe(
    UserLoggedIn,
    handle_login,
    on_error=on_error
)
```

### 4. Event Filtering and Querying

```python
# Subscribe with filter
event_bus.subscribe(
    UserLoggedIn,
    handle_login,
    filter_fn=lambda e: e.user_id.startswith("admin")
)

# Query past events
admin_logins = await event_bus.get_events(
    lambda e: isinstance(e, UserLoggedIn) and 
             e.user_id.startswith("admin")
)
```

## Best Practices

1. **Event Design**
   - Make events immutable using @dataclass(frozen=True)
   - Include only necessary data in event payloads
   - Use clear, descriptive event names

2. **Handler Design**
   - Keep handlers focused and single-purpose
   - Handle errors gracefully
   - Avoid long-running operations in handlers

3. **Performance**
   - Use event filtering to reduce unnecessary processing
   - Consider event batching for high-volume scenarios
   - Monitor event processing metrics

4. **Testing**
   - Unit test individual handlers
   - Use integration tests for event flows
   - Test error handling scenarios

## Common Patterns

### 1. Request-Response

```python
@dataclass
class QueryUser(Event):
    user_id: str
    response_topic: str

@dataclass
class UserResponse(Event):
    user_id: str
    user_data: dict

async def handle_query(event: QueryUser):
    user_data = await fetch_user(event.user_id)
    await event_bus.publish(UserResponse(
        user_id=event.user_id,
        user_data=user_data
    ), topic=event.response_topic)
```

### 2. Event Sourcing

```python
@dataclass
class EntityCreated(Event):
    entity_id: str
    data: dict

@dataclass
class EntityUpdated(Event):
    entity_id: str
    changes: dict

# Rebuild entity state from events
async def rebuild_entity(entity_id: str):
    events = await event_bus.get_events(
        lambda e: hasattr(e, 'entity_id') and 
                 e.entity_id == entity_id
    )
    return reduce(apply_event, events, {})
```

### 3. Event Workflows

```python
@dataclass
class WorkflowStarted(Event):
    workflow_id: str
    steps: List[str]

@dataclass
class StepCompleted(Event):
    workflow_id: str
    step: str

async def handle_step(event: WorkflowStarted):
    for step in event.steps:
        # Process step
        await process_step(step)
        # Signal completion
        await event_bus.publish(StepCompleted(
            workflow_id=event.workflow_id,
            step=step
        ))
```

## Monitoring and Debugging

The Event Bus includes built-in support for monitoring and debugging:

1. **Metrics Collection**
   - Event counts by type
   - Processing time statistics
   - Error rates

2. **Event Replay**
   - Store and replay events for debugging
   - Analyze event sequences
   - Test different handler configurations

3. **Middleware Hooks**
   - Add custom logging
   - Collect performance metrics
   - Implement circuit breakers

## Advanced Features

1. **Priority Levels**
   - Immediate: Process right away
   - Normal: Standard queue
   - Deferred: Background processing

2. **Event Persistence**
   - Optional event storage
   - Event replay capability
   - Historical analysis

3. **Pub/Sub Topics**
   - Event categorization
   - Selective subscription
   - Broadcast capabilities