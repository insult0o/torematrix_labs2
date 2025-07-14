# Document Ingestion System

This module implements the core upload manager and file validation system for TORE Matrix V3.

## Components

### Models (`models.py`)
- `FileMetadata`: Complete file metadata for tracking throughout the pipeline
- `FileStatus`: Enum for file processing status stages
- `FileType`: Enum for supported file types
- `UploadResult`: Result of a file upload operation
- `UploadSession`: Session for managing multi-file uploads

### Storage (`storage.py`)
- `StorageBackend`: Abstract base class for storage implementations
- `LocalFileStorage`: Local filesystem storage
- `S3Storage`: AWS S3 and S3-compatible storage
- `StorageManager`: Manages multiple backends with fallback support

### Validators (`validators.py`)
- `FileValidator`: Base validator interface
- `MimeTypeValidator`: Validates MIME type matches file extension
- `FileSizeValidator`: Validates file size constraints
- `ContentValidator`: Validates file content is readable
- `SecurityValidator`: Checks for security threats
- `HashValidator`: Calculates file hashes
- `CompositeValidator`: Runs multiple validators

### Upload Manager (`upload_manager.py`)
- `UploadManager`: Core class for handling file uploads
- Session-based upload management
- Concurrent upload support
- Integration with Unstructured.io for content validation
- Metadata extraction

## Usage

```python
from torematrix.ingestion import UploadManager
from torematrix.ingestion.storage import LocalFileStorage

# Create storage backend
storage = LocalFileStorage("/path/to/uploads")

# Create upload manager
manager = UploadManager(storage=storage)

# Create upload session
session = await manager.create_session(user_id="user123")

# Upload file
result = await manager.upload_file(
    session_id=session.session_id,
    file=upload_file,
    validate_content=True
)

# Check result
if result.validation_status == "valid":
    print(f"File uploaded: {result.file_id}")
else:
    print(f"Validation errors: {result.errors}")
```

## File Validation

The system performs comprehensive validation:

1. **Basic Validation**
   - File extension checking
   - File size limits
   - Empty file detection

2. **MIME Type Validation**
   - Verifies MIME type matches extension
   - Detects file type spoofing

3. **Content Validation**
   - PDF: Checks for encryption, corruption
   - Images: Verifies image integrity
   - Archives: Checks for corruption
   - Text: Encoding detection

4. **Security Validation**
   - Dangerous file type detection
   - Double extension detection
   - Script file detection

## Storage Abstraction

Supports multiple storage backends:

- **Local Storage**: Files stored on local filesystem
- **S3 Storage**: AWS S3 or compatible (MinIO, etc.)
- **Fallback Support**: Automatic failover between backends

## Integration with Unstructured.io

When configured with an Unstructured client:

- Deep content validation
- Metadata extraction
- Document structure analysis
- Language detection

## Testing

Comprehensive test coverage includes:

- Unit tests for all components
- Mock external dependencies
- Concurrent operation testing
- Error handling scenarios

Run tests:
```bash
pytest tests/unit/ingestion/
```

## Configuration

```python
from torematrix.ingestion.upload_manager import UploadManagerConfig

config = UploadManagerConfig(
    max_file_size=100 * 1024 * 1024,  # 100MB
    allowed_extensions=[".pdf", ".docx", ".txt"],
    validate_content=True,
    extract_metadata=True
)
```

## Dependencies

- `pydantic`: Data validation
- `aiofiles`: Async file operations
- `python-magic`: MIME type detection
- `fastapi`: Upload file handling
- Optional: `aioboto3` for S3 storage
- Optional: Various file parsing libraries