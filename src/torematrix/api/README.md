# TORE Matrix Labs V3 - API Module

## Overview

The API module provides REST endpoints and WebSocket connections for the TORE Matrix Labs V3 document ingestion system. It implements Agent 3's responsibilities for Issue #86: API Endpoints & WebSocket Progress.

## Features

### REST API Endpoints

- **Session Management**: Create and manage upload sessions
- **File Upload**: Single file and batch upload with validation
- **Progress Tracking**: Real-time status monitoring for files and sessions
- **Error Handling**: Comprehensive error responses and retry mechanisms
- **Queue Statistics**: Monitor processing queue status and worker health

### WebSocket Support

- **Real-time Updates**: Live progress notifications during processing
- **Connection Management**: Automatic connection lifecycle handling
- **Event Broadcasting**: Session-based message distribution
- **Error Recovery**: Graceful handling of connection failures

### Client SDK

- **Async Client**: Full-featured async client for Python applications
- **Simple Client**: Simplified synchronous interface for basic use cases
- **WebSocket Streaming**: Built-in progress update streaming
- **Error Handling**: Automatic retry and error recovery

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client SDK    │    │   REST API       │    │   WebSocket     │
│                 │    │   Endpoints      │    │   Handler       │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ IngestionClient │◄──►│ /sessions        │    │ /ws/progress    │
│ SimpleClient    │    │ /upload          │    │ ConnectionMgr   │
│ WebSocket       │    │ /status          │    │ EventHandlers   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Integration Layer     │
                    │                         │
                    │ ┌─────────┐ ┌─────────┐ │
                    │ │Agent 1  │ │Agent 2  │ │
                    │ │Upload   │ │Queue    │ │
                    │ │Manager  │ │Manager  │ │
                    │ └─────────┘ └─────────┘ │
                    └─────────────────────────┘
```

## API Endpoints

### Session Management

```http
POST /api/v1/ingestion/sessions
GET  /api/v1/ingestion/sessions/{session_id}/status
```

### File Upload

```http
POST /api/v1/ingestion/sessions/{session_id}/upload
POST /api/v1/ingestion/sessions/{session_id}/upload-batch
```

### File Status

```http
GET  /api/v1/ingestion/files/{file_id}/status
POST /api/v1/ingestion/files/{file_id}/retry
```

### Queue Monitoring

```http
GET /api/v1/ingestion/queue/stats
```

### WebSocket

```
WS /ws/progress/{session_id}?token={auth_token}
```

## Usage Examples

### Python Client SDK

```python
from torematrix.api.client import IngestionClient

async def upload_documents(files):
    async with IngestionClient("https://api.torematrix.com", "api-key") as client:
        # Create session
        session = await client.create_session(name="My Upload")
        session_id = session["session_id"]
        
        # Upload files
        if len(files) == 1:
            result = await client.upload_file(session_id, files[0])
        else:
            result = await client.upload_batch(session_id, files)
        
        # Wait for completion with progress updates
        def on_progress(update):
            print(f"Progress: {update}")
        
        final_status = await client.upload_and_wait(
            session_id, files, progress_callback=on_progress
        )
        
        return final_status
```

### Simple Client

```python
from torematrix.api.client import SimpleIngestionClient

client = SimpleIngestionClient("https://api.torematrix.com", "api-key")
result = client.upload_files(["doc1.pdf", "doc2.docx"], wait_for_completion=True)
print(f"Processed {result['processed_files']} files")
```

### Direct API Usage

```python
import httpx

# Create session
response = httpx.post("https://api.torematrix.com/api/v1/ingestion/sessions", 
                     json={"name": "Test Session"},
                     headers={"Authorization": "Bearer api-key"})
session_id = response.json()["session_id"]

# Upload file
with open("document.pdf", "rb") as f:
    response = httpx.post(
        f"https://api.torematrix.com/api/v1/ingestion/sessions/{session_id}/upload",
        files={"file": f},
        headers={"Authorization": "Bearer api-key"}
    )
```

## WebSocket Messages

### Connection

```json
{
  "type": "connected",
  "data": {
    "session_id": "session-123",
    "user_id": "user-456"
  },
  "timestamp": "2024-01-01T10:00:00Z"
}
```

### Progress Update

```json
{
  "type": "progress_update",
  "file_id": "file-123",
  "data": {
    "progress": 0.75,
    "current_step": "extracting"
  },
  "session_progress": {
    "overall_progress": 0.6,
    "processed_files": 2,
    "total_files": 5
  },
  "timestamp": "2024-01-01T10:05:00Z"
}
```

### Document Completion

```json
{
  "type": "document_completed",
  "file_id": "file-123",
  "data": {
    "processing_time": 30.5,
    "elements_extracted": 25
  },
  "timestamp": "2024-01-01T10:05:30Z"
}
```

## Error Handling

The API provides comprehensive error handling with structured error responses:

```json
{
  "error": "validation_error",
  "message": "File validation failed",
  "details": {
    "file_id": "file-123",
    "errors": ["File type not supported", "File too large"]
  },
  "timestamp": "2024-01-01T10:00:00Z"
}
```

Common error types:
- `validation_error`: File validation failures
- `authentication_error`: Invalid or missing authentication
- `not_found`: Resource not found
- `rate_limit_exceeded`: Too many requests
- `internal_server_error`: Server-side errors

## Configuration

The API module integrates with the broader TORE Matrix configuration system:

```python
from torematrix.core.dependencies import configure_dependencies
from torematrix.ingestion import UploadManager, QueueManager
from torematrix.core.events import EventBus

# Configure dependencies during application startup
configure_dependencies(
    upload_manager=upload_manager,
    queue_manager=queue_manager,
    event_bus=event_bus,
    progress_tracker=progress_tracker
)
```

## Testing

The module includes comprehensive test coverage:

```bash
# Run unit tests
pytest tests/unit/api/

# Run integration tests
pytest tests/integration/api/

# Run with coverage
pytest --cov=torematrix.api tests/
```

## Integration with Other Agents

### Agent 1 (Upload Manager)
- Uses `UploadManager` for file handling and validation
- Leverages `FileMetadata` and `UploadSession` models
- Integrates with storage abstraction layer

### Agent 2 (Queue Manager)
- Uses `QueueManager` for processing job management
- Subscribes to `EventBus` for real-time updates
- Leverages `ProgressTracker` for WebSocket notifications

### Agent 4 (Integration)
- Provides complete system integration
- Handles dependency injection and configuration
- Manages application lifecycle and health monitoring

## Production Considerations

### Security
- Implement proper authentication and authorization
- Use HTTPS for all API communications
- Validate and sanitize all input data
- Rate limiting to prevent abuse

### Performance
- Connection pooling for database access
- WebSocket connection limits and management
- File upload size limits and streaming
- Async processing for all I/O operations

### Monitoring
- Request/response logging
- Error tracking and alerting
- Performance metrics collection
- Health check endpoints

### Deployment
- Containerized deployment with Docker
- Load balancing for multiple instances
- Redis for WebSocket session management
- Persistent storage for file metadata

## Dependencies

- **FastAPI**: Web framework for REST API
- **WebSockets**: Real-time communication
- **aiohttp**: HTTP client for SDK
- **Pydantic**: Data validation and serialization
- **asyncio**: Async/await support throughout

## Future Enhancements

- GraphQL endpoint for complex queries
- File upload resumption for large files
- Advanced progress analytics and reporting
- Multi-tenant session isolation
- Enhanced error recovery mechanisms