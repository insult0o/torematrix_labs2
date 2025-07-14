"""
Unit tests for ingestion API endpoints.

Tests all REST API endpoints for file uploads, session management,
and status tracking with comprehensive mocking.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
import tempfile
import os
from io import BytesIO

# Import the modules we're testing
from torematrix.api.routers.ingestion import router
from torematrix.ingestion.models import FileMetadata, FileStatus, UploadResult, UploadSession


class MockUser:
    """Mock user for authentication."""
    def __init__(self, user_id: str = "user-123"):
        self.id = user_id


class MockUploadManager:
    """Mock upload manager for testing."""
    
    def __init__(self):
        self.sessions = {}
        self.create_session = AsyncMock()
        self.upload_file = AsyncMock()
        self.upload_batch = AsyncMock()
        self.get_session = Mock()
    
    def setup_session(self, session_id: str, user_id: str):
        """Setup a mock session."""
        session = UploadSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            status="active",
            files=[],
            metadata={}
        )
        self.sessions[session_id] = session
        self.get_session.return_value = session
        return session


class MockQueueManager:
    """Mock queue manager for testing."""
    
    def __init__(self):
        self.enqueue_file = AsyncMock()
        self.enqueue_batch = AsyncMock()
        self.get_job_status = AsyncMock()
        self.get_queue_stats = AsyncMock()
        self.retry_failed_job = AsyncMock()


@pytest.fixture
def mock_upload_manager():
    """Provide mock upload manager."""
    return MockUploadManager()


@pytest.fixture
def mock_queue_manager():
    """Provide mock queue manager."""
    return MockQueueManager()


@pytest.fixture
def mock_user():
    """Provide mock user."""
    return MockUser()


@pytest.fixture
def client():
    """Provide test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def test_create_session_success(self, client, mock_upload_manager, mock_user):
        """Test successful session creation."""
        # Setup mock
        session = UploadSession(
            session_id="session-123",
            user_id="user-123",
            created_at=datetime.utcnow(),
            status="active",
            metadata={}
        )
        mock_upload_manager.create_session.return_value = session
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.post(
                    "/api/v1/ingestion/sessions",
                    json={"name": "Test Session", "metadata": {"tag": "test"}}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-123"
        assert data["user_id"] == "user-123"
        assert data["status"] == "active"
        mock_upload_manager.create_session.assert_called_once_with("user-123")
    
    def test_create_session_failure(self, client, mock_upload_manager, mock_user):
        """Test session creation failure."""
        mock_upload_manager.create_session.side_effect = Exception("Database error")
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.post(
                    "/api/v1/ingestion/sessions",
                    json={"name": "Test Session"}
                )
        
        assert response.status_code == 500
        assert "Failed to create upload session" in response.json()["detail"]


class TestFileUploadEndpoints:
    """Test file upload endpoints."""
    
    def test_upload_file_success(self, client, mock_upload_manager, mock_queue_manager, mock_user):
        """Test successful file upload."""
        # Setup session
        session = mock_upload_manager.setup_session("session-123", "user-123")
        
        # Setup upload result
        upload_result = UploadResult(
            file_id="file-123",
            filename="test.pdf",
            size=1024,
            mime_type="application/pdf",
            hash="abc123",
            validation_status="valid",
            errors=[],
            metadata={},
            storage_key="/path/to/file"
        )
        mock_upload_manager.upload_file.return_value = upload_result
        
        # Setup queue
        mock_queue_manager.enqueue_file.return_value = "job-123"
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
                with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                    with patch("torematrix.api.routers.ingestion.queue_file_for_processing"):
                        # Create test file
                        test_content = b"PDF content"
                        response = client.post(
                            "/api/v1/ingestion/sessions/session-123/upload",
                            files={"file": ("test.pdf", BytesIO(test_content), "application/pdf")},
                            params={"auto_process": "true"}
                        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "file-123"
        assert data["filename"] == "test.pdf"
        assert data["status"] == "queued"  # Because auto_process=true
        assert data["validation_status"] == "valid"
    
    def test_upload_file_validation_failed(self, client, mock_upload_manager, mock_user):
        """Test file upload with validation failure."""
        session = mock_upload_manager.setup_session("session-123", "user-123")
        
        upload_result = UploadResult(
            file_id="file-123",
            filename="test.exe",
            size=1024,
            mime_type="application/x-executable",
            hash="abc123",
            validation_status="failed",
            errors=["File type not allowed"],
            metadata={},
            storage_key="/path/to/file"
        )
        mock_upload_manager.upload_file.return_value = upload_result
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.post(
                    "/api/v1/ingestion/sessions/session-123/upload",
                    files={"file": ("test.exe", BytesIO(b"content"), "application/x-executable")}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation_status"] == "failed"
        assert "File type not allowed" in data["errors"]
        assert data["status"] == "uploaded"  # Not queued due to validation failure
    
    def test_upload_file_session_not_found(self, client, mock_upload_manager, mock_user):
        """Test upload to non-existent session."""
        mock_upload_manager.get_session.return_value = None
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.post(
                    "/api/v1/ingestion/sessions/nonexistent/upload",
                    files={"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
                )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"
    
    def test_upload_batch_success(self, client, mock_upload_manager, mock_queue_manager, mock_user):
        """Test successful batch upload."""
        session = mock_upload_manager.setup_session("session-123", "user-123")
        
        # Setup batch results
        results = [
            UploadResult(
                file_id=f"file-{i}",
                filename=f"test{i}.pdf",
                size=1024,
                mime_type="application/pdf",
                hash=f"hash{i}",
                validation_status="valid",
                errors=[],
                metadata={},
                storage_key=f"/path/to/file{i}"
            )
            for i in range(3)
        ]
        mock_upload_manager.upload_batch.return_value = results
        mock_queue_manager.enqueue_batch.return_value = ["job-1", "job-2", "job-3"]
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
                with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                    with patch("torematrix.api.routers.ingestion.queue_batch_for_processing"):
                        files = [
                            ("files", ("test1.pdf", BytesIO(b"content1"), "application/pdf")),
                            ("files", ("test2.pdf", BytesIO(b"content2"), "application/pdf")),
                            ("files", ("test3.pdf", BytesIO(b"content3"), "application/pdf"))
                        ]
                        response = client.post(
                            "/api/v1/ingestion/sessions/session-123/upload-batch",
                            files=files
                        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 3
        assert len(data["uploaded_files"]) == 3
        assert len(data["failed_files"]) == 0
        assert data["batch_queued"] is True


class TestStatusEndpoints:
    """Test status and monitoring endpoints."""
    
    def test_get_session_status(self, client, mock_upload_manager, mock_queue_manager, mock_user):
        """Test getting session status."""
        # Setup session with files
        session = mock_upload_manager.setup_session("session-123", "user-123")
        session.files = [
            UploadResult(
                file_id="file-1",
                filename="test1.pdf",
                size=1024,
                mime_type="application/pdf",
                hash="hash1",
                validation_status="valid",
                errors=[],
                metadata={},
                storage_key="/path/to/file1"
            ),
            UploadResult(
                file_id="file-2",
                filename="test2.pdf",
                size=2048,
                mime_type="application/pdf",
                hash="hash2",
                validation_status="valid",
                errors=[],
                metadata={},
                storage_key="/path/to/file2"
            )
        ]
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
                with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                    response = client.get("/api/v1/ingestion/sessions/session-123/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-123"
        assert data["total_files"] == 2
        assert len(data["files"]) == 2
    
    def test_get_file_status(self, client, mock_queue_manager, mock_user):
        """Test getting individual file status."""
        # Mock file metadata
        file_metadata = FileMetadata(
            file_id="file-123",
            filename="test.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            size=1024,
            hash="abc123",
            upload_session_id="session-123",
            uploaded_by="user-123",
            uploaded_at=datetime.utcnow(),
            storage_key="/path/to/file",
            status=FileStatus.PROCESSED,
            processed_at=datetime.utcnow(),
            processing_time=30.5,
            extracted_elements=25
        )
        
        with patch("torematrix.api.routers.ingestion.get_file_metadata", return_value=file_metadata):
            with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
                with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                    response = client.get("/api/v1/ingestion/files/file-123/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "file-123"
        assert data["filename"] == "test.pdf"
        assert data["processing_time"] == 30.5
        assert data["extracted_elements"] == 25
    
    def test_retry_file_processing(self, client, mock_queue_manager, mock_user):
        """Test retrying failed file processing."""
        # Mock failed file
        file_metadata = FileMetadata(
            file_id="file-123",
            filename="test.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            size=1024,
            hash="abc123",
            upload_session_id="session-123",
            uploaded_by="user-123",
            uploaded_at=datetime.utcnow(),
            storage_key="/path/to/file",
            status=FileStatus.FAILED,
            queue_job_id="job-failed"
        )
        
        mock_queue_manager.retry_failed_job.return_value = "job-retry-1"
        
        with patch("torematrix.api.routers.ingestion.get_file_metadata", return_value=file_metadata):
            with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
                with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                    response = client.post("/api/v1/ingestion/files/file-123/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "retried"
        assert data["job_id"] == "job-retry-1"
    
    def test_get_queue_stats(self, client, mock_queue_manager, mock_user):
        """Test getting queue statistics."""
        stats = {
            "default": {
                "count": 10,
                "jobs": {"queued": 10, "started": 5, "finished": 100, "failed": 2}
            },
            "priority": {
                "count": 2,
                "jobs": {"queued": 2, "started": 1, "finished": 50, "failed": 0}
            },
            "workers": {
                "total": 5,
                "busy": 3,
                "idle": 2
            }
        }
        mock_queue_manager.get_queue_stats.return_value = stats
        
        with patch("torematrix.api.routers.ingestion.get_queue_manager", return_value=mock_queue_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.get("/api/v1/ingestion/queue/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "queues" in data
        assert "timestamp" in data
        assert data["queues"] == stats


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_unauthorized_access(self, client):
        """Test requests without proper authentication."""
        with patch("torematrix.api.routers.ingestion.get_current_user", side_effect=Exception("Unauthorized")):
            response = client.post("/api/v1/ingestion/sessions", json={})
        
        assert response.status_code == 500  # FastAPI will convert the exception
    
    def test_invalid_session_id_format(self, client, mock_upload_manager, mock_user):
        """Test using invalid session ID format."""
        mock_upload_manager.get_session.return_value = None
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.get("/api/v1/ingestion/sessions/invalid-id/status")
        
        assert response.status_code == 404
    
    def test_file_upload_without_file(self, client, mock_upload_manager, mock_user):
        """Test upload endpoint without file."""
        session = mock_upload_manager.setup_session("session-123", "user-123")
        
        with patch("torematrix.api.routers.ingestion.get_upload_manager", return_value=mock_upload_manager):
            with patch("torematrix.api.routers.ingestion.get_current_user", return_value=mock_user):
                response = client.post("/api/v1/ingestion/sessions/session-123/upload")
        
        assert response.status_code == 422  # Validation error


class TestHelperFunctions:
    """Test utility and helper functions."""
    
    def test_detect_file_type(self):
        """Test MIME type to file type detection."""
        from torematrix.api.routers.ingestion import _detect_file_type
        
        assert _detect_file_type("application/pdf") == "pdf"
        assert _detect_file_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "word"
        assert _detect_file_type("text/plain") == "text"
        assert _detect_file_type("unknown/type") == "other"
    
    @pytest.mark.asyncio
    async def test_queue_file_for_processing(self, mock_queue_manager):
        """Test background task for queuing files."""
        from torematrix.api.routers.ingestion import queue_file_for_processing
        
        file_metadata = FileMetadata(
            file_id="file-123",
            filename="test.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            size=1024,
            hash="abc123",
            upload_session_id="session-123",
            uploaded_by="user-123",
            uploaded_at=datetime.utcnow(),
            storage_key="/path/to/file"
        )
        
        mock_queue_manager.enqueue_file.return_value = "job-123"
        
        with patch("torematrix.api.routers.ingestion.save_file_metadata"):
            await queue_file_for_processing(file_metadata, mock_queue_manager, priority=False)
        
        mock_queue_manager.enqueue_file.assert_called_once_with(file_metadata, priority=False)


if __name__ == "__main__":
    pytest.main([__file__])