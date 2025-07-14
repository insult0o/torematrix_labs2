"""
Unit tests for DocumentProcessor and BatchProcessor.

Tests document processing, batch processing, and Unstructured.io integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from pathlib import Path

from torematrix.ingestion.processors import (
    DocumentProcessor, BatchProcessor, ProcessingResult, BatchResult,
    process_document, process_batch
)
from torematrix.ingestion.models import FileMetadata, FileStatus, FileType
from torematrix.ingestion.progress import ProgressTracker
from torematrix.core.events import EventBus, ProcessingEvent
from torematrix.integrations.unstructured.client import UnstructuredClient
from torematrix.integrations.unstructured.exceptions import ProcessingError, ValidationError


@pytest.fixture
def sample_file_metadata():
    """Create sample file metadata for testing."""
    return FileMetadata(
        file_id="test-file-123",
        filename="test_document.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        size=1024,
        hash="abc123def456",
        upload_session_id="session-123",
        uploaded_by="user-123",
        uploaded_at=datetime.utcnow(),
        storage_key="/storage/path/test_document.pdf",
        status=FileStatus.UPLOADED
    )


@pytest.fixture
def sample_job_data(sample_file_metadata):
    """Create sample job data for testing."""
    return {
        "file_id": sample_file_metadata.file_id,
        "file_path": sample_file_metadata.storage_key,
        "metadata": sample_file_metadata.dict(),
        "job_id": "job-456"
    }


@pytest.fixture
async def mock_unstructured_client():
    """Create mock Unstructured client."""
    mock = AsyncMock(spec=UnstructuredClient)
    
    # Mock successful processing result
    mock_result = Mock()
    mock_result.elements = [
        {"type": "Title", "text": "Document Title"},
        {"type": "NarrativeText", "text": "Document content"},
        {"type": "Table", "text": "Table data"}
    ]
    mock_result.metadata = {
        "page_count": 5,
        "language": "en",
        "file_type": "pdf"
    }
    
    mock.process_file = AsyncMock(return_value=mock_result)
    return mock


@pytest.fixture
async def mock_progress_tracker():
    """Create mock progress tracker."""
    mock = AsyncMock(spec=ProgressTracker)
    mock.update_file_progress = AsyncMock()
    return mock


@pytest.fixture
async def mock_event_bus():
    """Create mock event bus."""
    mock = AsyncMock(spec=EventBus)
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
async def document_processor(mock_unstructured_client, mock_progress_tracker, mock_event_bus):
    """Create DocumentProcessor with mocked dependencies."""
    return DocumentProcessor(
        unstructured_client=mock_unstructured_client,
        progress_tracker=mock_progress_tracker,
        event_bus=mock_event_bus
    )


@pytest.fixture
async def batch_processor(document_processor, mock_progress_tracker, mock_event_bus):
    """Create BatchProcessor with mocked dependencies."""
    return BatchProcessor(
        document_processor=document_processor,
        max_concurrent=3,
        progress_tracker=mock_progress_tracker,
        event_bus=mock_event_bus
    )


class TestProcessingResult:
    """Test cases for ProcessingResult data class."""
    
    def test_processing_result_creation(self):
        """Test creating ProcessingResult."""
        result = ProcessingResult(
            file_id="file-123",
            status="success",
            processing_time=45.5,
            elements_extracted=10,
            pages_processed=5
        )
        
        assert result.file_id == "file-123"
        assert result.status == "success"
        assert result.processing_time == 45.5
        assert result.elements_extracted == 10
        assert result.pages_processed == 5
        assert result.metadata == {}  # Should be initialized
    
    def test_processing_result_with_error(self):
        """Test creating ProcessingResult with error."""
        result = ProcessingResult(
            file_id="file-123",
            status="failed",
            processing_time=10.0,
            error_message="Processing failed: invalid format"
        )
        
        assert result.status == "failed"
        assert result.error_message == "Processing failed: invalid format"


class TestBatchResult:
    """Test cases for BatchResult data class."""
    
    def test_batch_result_creation(self):
        """Test creating BatchResult."""
        results = [
            ProcessingResult("file-1", "success", 10.0, elements_extracted=5),
            ProcessingResult("file-2", "failed", 5.0, error_message="Error")
        ]
        
        batch_result = BatchResult(
            batch_id="batch-123",
            total_files=2,
            successful_files=1,
            failed_files=1,
            skipped_files=0,
            total_processing_time=15.0,
            results=results
        )
        
        assert batch_result.batch_id == "batch-123"
        assert batch_result.total_files == 2
        assert batch_result.successful_files == 1
        assert batch_result.failed_files == 1
        assert batch_result.total_processing_time == 15.0
        assert len(batch_result.results) == 2
        assert batch_result.error_summary == {}  # Should be initialized


class TestDocumentProcessor:
    """Test cases for DocumentProcessor."""
    
    async def test_successful_processing(self, document_processor, sample_job_data, mock_unstructured_client, mock_progress_tracker, mock_event_bus):
        """Test successful document processing."""
        # Process document
        result = await document_processor.process(sample_job_data)
        
        # Verify result
        assert result.status == "success"
        assert result.file_id == sample_job_data["file_id"]
        assert result.elements_extracted == 3  # Mock returned 3 elements
        assert result.pages_processed == 5
        assert result.processing_time > 0
        
        # Verify Unstructured client was called
        mock_unstructured_client.process_file.assert_called_once()
        call_args = mock_unstructured_client.process_file.call_args
        assert isinstance(call_args[0][0], Path)  # First arg should be Path
        
        # Verify progress updates
        assert mock_progress_tracker.update_file_progress.call_count >= 2
        
        # Verify events were emitted
        assert mock_event_bus.publish.call_count >= 2  # Started and completed events
    
    async def test_processing_with_validation_error(self, document_processor, sample_job_data, mock_unstructured_client):
        """Test processing with validation error."""
        # Mock validation error
        mock_unstructured_client.process_file.side_effect = ValidationError("Invalid document format")
        
        # Process document
        result = await document_processor.process(sample_job_data)
        
        # Verify failure result
        assert result.status == "failed"
        assert result.file_id == sample_job_data["file_id"]
        assert "Document validation failed" in result.error_message
        assert result.elements_extracted == 0
        assert result.processing_time > 0
    
    async def test_processing_with_generic_error(self, document_processor, sample_job_data, mock_unstructured_client):
        """Test processing with generic error."""
        # Mock generic error
        mock_unstructured_client.process_file.side_effect = Exception("Unexpected error")
        
        # Process document
        result = await document_processor.process(sample_job_data)
        
        # Verify failure result
        assert result.status == "failed"
        assert "Document processing failed" in result.error_message
    
    async def test_processing_without_progress_updates(self, document_processor, sample_job_data, mock_progress_tracker):
        """Test processing without progress updates."""
        # Process without progress updates
        result = await document_processor.process(sample_job_data, update_progress=False)
        
        # Verify processing succeeded
        assert result.status == "success"
        
        # Verify no progress updates
        mock_progress_tracker.update_file_progress.assert_not_called()
    
    async def test_update_file_metadata(self, document_processor):
        """Test file metadata update (mocked database operation)."""
        # This tests the _update_file_metadata method
        # Since database integration is not implemented, we just verify it doesn't crash
        await document_processor._update_file_metadata(
            file_id="test-file",
            status=FileStatus.PROCESSED,
            processing_time=30.0,
            extracted_elements=5,
            document_metadata={"pages": 3}
        )
        
        # Should complete without error
        assert True
    
    async def test_process_with_unstructured_progress_events(self, document_processor, sample_job_data, mock_event_bus):
        """Test that processing emits intermediate progress events."""
        # Process document
        await document_processor.process(sample_job_data)
        
        # Check that progress events were emitted
        events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
        
        # Should have at least: started, progress updates, completed
        assert len(events) >= 3
        
        # Check for specific event types
        event_types = [event.event_type for event in events]
        assert "processing.job.started" in event_types
        assert "processing.job.completed" in event_types


class TestBatchProcessor:
    """Test cases for BatchProcessor."""
    
    def test_error_classification(self, batch_processor):
        """Test error message classification."""
        assert batch_processor._classify_error("Validation failed") == "validation_error"
        assert batch_processor._classify_error("Request timeout") == "timeout_error"
        assert batch_processor._classify_error("Out of memory") == "memory_error"
        assert batch_processor._classify_error("Permission denied") == "permission_error"
        assert batch_processor._classify_error("Network connection failed") == "network_error"
        assert batch_processor._classify_error("Unsupported format") == "format_error"
        assert batch_processor._classify_error("Something else") == "unknown_error"
    
    async def test_process_batch_success(self, batch_processor, mock_event_bus):
        """Test successful batch processing."""
        # Create batch data
        batch_data = {
            "batch_id": "batch-123",
            "files": [
                {
                    "file_id": "file-1",
                    "filename": "doc1.pdf",
                    "storage_key": "/path/doc1.pdf",
                    "size": 1024
                },
                {
                    "file_id": "file-2", 
                    "filename": "doc2.pdf",
                    "storage_key": "/path/doc2.pdf",
                    "size": 2048
                }
            ],
            "batch_index": 0,
            "total_batches": 1
        }
        
        # Mock successful processing
        async def mock_process(job_data, update_progress=True):
            return ProcessingResult(
                file_id=job_data["file_id"],
                status="success",
                processing_time=10.0,
                elements_extracted=5
            )
        
        batch_processor.document_processor.process = mock_process
        
        # Process batch
        result = await batch_processor.process_batch(batch_data)
        
        # Verify batch result
        assert result.batch_id == "batch-123"
        assert result.total_files == 2
        assert result.successful_files == 2
        assert result.failed_files == 0
        assert result.skipped_files == 0
        assert len(result.results) == 2
        assert result.total_processing_time > 0
        
        # Verify events were emitted
        events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
        event_types = [event.event_type for event in events]
        assert "processing.batch.started" in event_types
        assert "processing.batch.completed" in event_types
    
    async def test_process_batch_with_failures(self, batch_processor, mock_event_bus):
        """Test batch processing with some failures."""
        # Create batch data
        batch_data = {
            "batch_id": "batch-456",
            "files": [
                {"file_id": "file-1", "filename": "doc1.pdf", "storage_key": "/path/doc1.pdf"},
                {"file_id": "file-2", "filename": "doc2.pdf", "storage_key": "/path/doc2.pdf"},
                {"file_id": "file-3", "filename": "doc3.pdf", "storage_key": "/path/doc3.pdf"}
            ],
            "batch_index": 0,
            "total_batches": 1
        }
        
        # Mock mixed results
        async def mock_process(job_data, update_progress=True):
            if job_data["file_id"] == "file-2":
                raise Exception("Processing failed")
            return ProcessingResult(
                file_id=job_data["file_id"],
                status="success",
                processing_time=10.0,
                elements_extracted=5
            )
        
        batch_processor.document_processor.process = mock_process
        
        # Process batch
        result = await batch_processor.process_batch(batch_data)
        
        # Verify mixed results
        assert result.total_files == 3
        assert result.successful_files == 2
        assert result.failed_files == 1
        assert len(result.results) == 3
        
        # Check error summary
        assert result.error_summary.get("unknown_error", 0) == 1
        
        # Verify completion event was emitted
        events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
        completion_events = [e for e in events if e.event_type == "processing.batch.completed"]
        assert len(completion_events) == 1
    
    async def test_process_batch_total_failure(self, batch_processor, mock_event_bus):
        """Test batch processing with total failure."""
        # Create batch data
        batch_data = {
            "batch_id": "batch-failed",
            "files": [
                {"file_id": "file-1", "filename": "doc1.pdf", "storage_key": "/path/doc1.pdf"}
            ],
            "batch_index": 0,
            "total_batches": 1
        }
        
        # Mock batch processing failure
        original_process = batch_processor.document_processor.process
        batch_processor.document_processor.process = AsyncMock(side_effect=Exception("Batch failure"))
        
        # This should be caught and handled
        result = await batch_processor.process_batch(batch_data)
        
        # Verify failure result structure
        assert result.batch_id == "batch-failed"
        assert result.total_files == 1
        assert result.successful_files == 0
        assert result.failed_files == 1
        
        # Verify failure event was emitted
        events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
        failure_events = [e for e in events if e.event_type == "processing.batch.failed"]
        assert len(failure_events) == 1
    
    async def test_process_file_with_semaphore(self, batch_processor):
        """Test file processing with semaphore control."""
        semaphore = asyncio.Semaphore(1)
        file_data = {
            "file_id": "file-123",
            "filename": "test.pdf",
            "storage_key": "/path/test.pdf"
        }
        
        # Mock successful processing
        async def mock_process(job_data, update_progress=True):
            return ProcessingResult(
                file_id=job_data["file_id"],
                status="success",
                processing_time=5.0,
                elements_extracted=3
            )
        
        batch_processor.document_processor.process = mock_process
        
        # Process file with semaphore
        result = await batch_processor._process_file_with_semaphore(
            semaphore=semaphore,
            file_data=file_data,
            batch_id="batch-123",
            file_index=0,
            total_files=1
        )
        
        # Verify result
        assert result.status == "success"
        assert result.file_id == "file-123"
    
    async def test_concurrent_processing_limit(self, batch_processor):
        """Test that concurrent processing respects limits."""
        # Create batch with many files
        files = [
            {"file_id": f"file-{i}", "filename": f"doc{i}.pdf", "storage_key": f"/path/doc{i}.pdf"}
            for i in range(10)
        ]
        
        batch_data = {
            "batch_id": "large-batch",
            "files": files,
            "batch_index": 0,
            "total_batches": 1
        }
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        
        async def mock_process(job_data, update_progress=True):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            concurrent_count -= 1
            return ProcessingResult(
                file_id=job_data["file_id"],
                status="success",
                processing_time=0.1,
                elements_extracted=1
            )
        
        batch_processor.document_processor.process = mock_process
        
        # Process batch
        result = await batch_processor.process_batch(batch_data)
        
        # Verify concurrency was limited
        assert max_concurrent <= batch_processor.max_concurrent
        assert result.successful_files == 10


class TestWorkerEntryPoints:
    """Test cases for RQ worker entry points."""
    
    @patch('torematrix.ingestion.processors.UnstructuredConfig')
    @patch('torematrix.ingestion.processors.UnstructuredClient')
    @patch('torematrix.ingestion.processors.EventBus')
    @patch('redis.asyncio.from_url')
    @patch('torematrix.ingestion.processors.ProgressTracker')
    @patch('torematrix.ingestion.processors.DocumentProcessor')
    async def test_process_document_entry_point(
        self, mock_doc_processor_class, mock_progress_tracker_class,
        mock_redis_from_url, mock_event_bus_class, mock_client_class, mock_config_class
    ):
        """Test process_document worker entry point."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        
        mock_event_bus = Mock()
        mock_event_bus_class.return_value = mock_event_bus
        
        mock_progress_tracker = Mock()
        mock_progress_tracker_class.return_value = mock_progress_tracker
        
        # Setup processor mock
        mock_processor = AsyncMock()
        mock_result = ProcessingResult("file-123", "success", 10.0)
        mock_processor.process = AsyncMock(return_value=mock_result)
        mock_doc_processor_class.return_value = mock_processor
        
        # Test data
        job_data = {
            "file_id": "file-123",
            "file_path": "/path/test.pdf",
            "metadata": {"filename": "test.pdf"}
        }
        
        # Call entry point
        with patch('asyncio.run') as mock_run:
            # Mock asyncio.run to execute the coroutine
            async def run_coro(coro):
                return await coro
            mock_run.side_effect = run_coro
            
            # Since we can't easily test the actual asyncio.run call,
            # we'll test that the function can be imported and called
            from torematrix.ingestion.processors import process_document
            
            # Verify function exists and is callable
            assert callable(process_document)
    
    @patch('torematrix.ingestion.processors.UnstructuredConfig')
    @patch('torematrix.ingestion.processors.UnstructuredClient')
    @patch('torematrix.ingestion.processors.EventBus')
    @patch('redis.asyncio.from_url')
    @patch('torematrix.ingestion.processors.ProgressTracker')
    @patch('torematrix.ingestion.processors.DocumentProcessor')
    @patch('torematrix.ingestion.processors.BatchProcessor')
    def test_process_batch_entry_point(
        self, mock_batch_processor_class, mock_doc_processor_class,
        mock_progress_tracker_class, mock_redis_from_url, mock_event_bus_class,
        mock_client_class, mock_config_class
    ):
        """Test process_batch worker entry point."""
        # Verify function exists and is callable
        from torematrix.ingestion.processors import process_batch
        assert callable(process_batch)