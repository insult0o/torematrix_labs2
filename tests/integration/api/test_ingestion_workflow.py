"""
Integration tests for complete ingestion workflow.

Tests the end-to-end document ingestion process including
file upload, processing, and progress tracking.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import json
from pathlib import Path

from torematrix.api.app import app
from torematrix.api.client.ingestion_client import IngestionClient


@pytest.fixture
def client():
    """Provide test client."""
    return TestClient(app)


@pytest.fixture
def temp_files():
    """Provide temporary test files."""
    files = []
    
    # Create PDF test file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.4\n%Test PDF content')
        files.append(Path(f.name))
    
    # Create text test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Test document content for processing')
        files.append(Path(f.name))
    
    yield files
    
    # Cleanup
    for file_path in files:
        file_path.unlink(missing_ok=True)


class TestCompleteIngestionWorkflow:
    """Test complete document ingestion workflow."""
    
    def test_session_creation_and_upload_workflow(self, client, temp_files):
        """Test creating session and uploading files."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_upload_manager") as mock_upload_mgr:
                with patch("torematrix.api.routers.ingestion.get_queue_manager") as mock_queue_mgr:
                    # Setup mocks
                    self._setup_workflow_mocks(mock_upload_mgr, mock_queue_mgr)
                    
                    # Step 1: Create session
                    session_response = client.post(
                        "/api/v1/ingestion/sessions",
                        json={"name": "Integration Test Session"}
                    )
                    assert session_response.status_code == 200
                    session_data = session_response.json()
                    session_id = session_data["session_id"]
                    
                    # Step 2: Upload files
                    upload_responses = []
                    for i, file_path in enumerate(temp_files):
                        with open(file_path, 'rb') as f:
                            response = client.post(
                                f"/api/v1/ingestion/sessions/{session_id}/upload",
                                files={"file": (file_path.name, f, "application/octet-stream")},
                                params={"auto_process": "true"}
                            )
                        assert response.status_code == 200
                        upload_responses.append(response.json())
                    
                    # Verify uploads
                    assert len(upload_responses) == 2
                    for response in upload_responses:
                        assert response["status"] == "queued"
                        assert response["validation_status"] == "valid"
                    
                    # Step 3: Check session status
                    status_response = client.get(f"/api/v1/ingestion/sessions/{session_id}/status")
                    assert status_response.status_code == 200
                    status_data = status_response.json()
                    assert status_data["total_files"] == 2
    
    def test_batch_upload_workflow(self, client, temp_files):
        """Test batch upload workflow."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_upload_manager") as mock_upload_mgr:
                with patch("torematrix.api.routers.ingestion.get_queue_manager") as mock_queue_mgr:
                    # Setup mocks
                    self._setup_workflow_mocks(mock_upload_mgr, mock_queue_mgr)
                    
                    # Create session
                    session_response = client.post(
                        "/api/v1/ingestion/sessions",
                        json={"name": "Batch Test Session"}
                    )
                    session_id = session_response.json()["session_id"]
                    
                    # Batch upload
                    files = []
                    for file_path in temp_files:
                        with open(file_path, 'rb') as f:
                            files.append(("files", (file_path.name, f.read(), "application/octet-stream")))
                    
                    response = client.post(
                        f"/api/v1/ingestion/sessions/{session_id}/upload-batch",
                        files=files
                    )
                    
                    assert response.status_code == 200
                    batch_data = response.json()
                    assert batch_data["total_files"] == 2
                    assert len(batch_data["uploaded_files"]) == 2
                    assert len(batch_data["failed_files"]) == 0
                    assert batch_data["batch_queued"] is True
    
    def test_file_status_and_retry_workflow(self, client):
        """Test file status checking and retry workflow."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_file_metadata") as mock_get_file:
                with patch("torematrix.api.routers.ingestion.get_queue_manager") as mock_queue_mgr:
                    # Mock file metadata
                    from torematrix.ingestion.models import FileMetadata, FileStatus
                    from datetime import datetime
                    
                    mock_file = FileMetadata(
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
                        processing_errors=["Timeout error"]
                    )
                    mock_get_file.return_value = mock_file
                    
                    # Mock queue manager
                    mock_queue_mgr.retry_failed_job = AsyncMock(return_value="job-retry-1")
                    
                    # Get file status
                    status_response = client.get("/api/v1/ingestion/files/file-123/status")
                    assert status_response.status_code == 200
                    status_data = status_response.json()
                    assert status_data["file_id"] == "file-123"
                    assert status_data["status"] == "failed"
                    
                    # Retry file
                    retry_response = client.post("/api/v1/ingestion/files/file-123/retry")
                    assert retry_response.status_code == 200
                    retry_data = retry_response.json()
                    assert retry_data["status"] == "retried"
                    assert retry_data["job_id"] == "job-retry-1"
    
    def test_queue_stats_endpoint(self, client):
        """Test queue statistics endpoint."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_queue_manager") as mock_queue_mgr:
                # Mock queue stats
                mock_stats = {
                    "default": {
                        "count": 15,
                        "jobs": {"queued": 10, "processing": 5, "completed": 100, "failed": 2}
                    },
                    "priority": {
                        "count": 3,
                        "jobs": {"queued": 3, "processing": 0, "completed": 50, "failed": 0}
                    },
                    "workers": {"total": 5, "busy": 2, "idle": 3}
                }
                mock_queue_mgr.get_queue_stats = AsyncMock(return_value=mock_stats)
                
                response = client.get("/api/v1/ingestion/queue/stats")
                assert response.status_code == 200
                
                data = response.json()
                assert "queues" in data
                assert "timestamp" in data
                assert data["queues"] == mock_stats
    
    def _setup_workflow_mocks(self, mock_upload_mgr, mock_queue_mgr):
        """Setup common mocks for workflow tests."""
        from torematrix.ingestion.models import UploadSession, UploadResult
        from datetime import datetime
        
        # Mock session
        session = UploadSession(
            session_id="session-123",
            user_id="user-123",
            created_at=datetime.utcnow(),
            status="active",
            files=[],
            metadata={}
        )
        
        # Mock upload manager
        mock_upload_mgr.create_session = AsyncMock(return_value=session)
        mock_upload_mgr.get_session = Mock(return_value=session)
        
        # Mock upload results
        def create_upload_result(filename):
            return UploadResult(
                file_id=f"file-{filename}",
                filename=filename,
                size=1024,
                mime_type="application/pdf",
                hash="abc123",
                validation_status="valid",
                errors=[],
                metadata={},
                storage_key=f"/path/to/{filename}"
            )
        
        mock_upload_mgr.upload_file = AsyncMock(side_effect=lambda sid, file, **kwargs: 
                                               create_upload_result(file.filename))
        
        mock_upload_mgr.upload_batch = AsyncMock(side_effect=lambda sid, files, **kwargs:
                                               [create_upload_result(f.filename) for f in files])
        
        # Mock queue manager
        mock_queue_mgr.enqueue_file = AsyncMock(return_value="job-123")
        mock_queue_mgr.enqueue_batch = AsyncMock(return_value=["job-1", "job-2"])


class TestWebSocketIntegration:
    """Test WebSocket integration for progress updates."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_flow(self):
        """Test WebSocket connection and message flow."""
        with patch("torematrix.api.websockets.progress.verify_websocket_token") as mock_verify:
            with patch("torematrix.api.websockets.progress.manager") as mock_manager:
                # Setup authentication
                from torematrix.core.auth import User
                mock_user = User(id="user-123", username="test", email="test@example.com")
                mock_verify.return_value = mock_user
                
                # Setup connection manager
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Test WebSocket endpoint
                from torematrix.api.websockets.progress import websocket_endpoint
                from unittest.mock import Mock
                
                mock_websocket = Mock()
                mock_websocket.accept = AsyncMock()
                mock_websocket.send_json = AsyncMock()
                mock_websocket.send_text = AsyncMock()
                mock_websocket.receive_text = AsyncMock(side_effect=["ping", asyncio.CancelledError()])
                
                try:
                    await websocket_endpoint(
                        mock_websocket,
                        "session-123",
                        "valid-token",
                        Mock(),  # event_bus
                        Mock()   # progress_tracker
                    )
                except asyncio.CancelledError:
                    pass  # Expected
                
                # Verify WebSocket was accepted and connected
                mock_websocket.accept.assert_called_once()
                mock_manager.connect.assert_called_once_with(mock_websocket, "session-123", "user-123")


class TestClientSDKIntegration:
    """Test client SDK integration with API."""
    
    @pytest.mark.asyncio
    async def test_client_sdk_workflow(self, temp_files):
        """Test complete workflow using client SDK."""
        with patch("aiohttp.ClientSession") as MockSession:
            # Mock session and responses
            mock_session = Mock()
            MockSession.return_value = mock_session
            
            # Mock responses
            def create_mock_response(data, status=200):
                response = Mock()
                response.json = AsyncMock(return_value=data)
                response.raise_for_status = Mock()
                response.__aenter__ = AsyncMock(return_value=response)
                response.__aexit__ = AsyncMock(return_value=None)
                return response
            
            # Session creation response
            session_data = {"session_id": "session-123", "status": "active"}
            mock_session.post.return_value = create_mock_response(session_data)
            
            # File upload response
            upload_data = {"file_id": "file-123", "status": "uploaded", "validation_status": "valid"}
            mock_session.post.return_value = create_mock_response(upload_data)
            
            # Status response
            status_data = {"total_files": 1, "processed_files": 0, "failed_files": 0}
            mock_session.get.return_value = create_mock_response(status_data)
            
            # Test client workflow
            client = IngestionClient("https://api.test.com", "test-key")
            
            async with client:
                # Create session
                session = await client.create_session(name="SDK Test")
                assert session["session_id"] == "session-123"
                
                # Upload file
                upload_result = await client.upload_file("session-123", temp_files[0])
                assert upload_result["file_id"] == "file-123"
                
                # Get status
                status = await client.get_session_status("session-123")
                assert status["total_files"] == 1


class TestErrorScenarios:
    """Test error handling in integration scenarios."""
    
    def test_authentication_error(self, client):
        """Test API behavior with authentication errors."""
        # Without proper mocking, endpoints should handle auth errors
        with patch("torematrix.api.routers.ingestion.get_current_user", 
                  side_effect=Exception("Unauthorized")):
            response = client.post("/api/v1/ingestion/sessions", json={})
            assert response.status_code == 500  # FastAPI converts to 500
    
    def test_upload_manager_error(self, client):
        """Test behavior when upload manager fails."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_upload_manager", 
                      side_effect=Exception("Service unavailable")):
                response = client.post("/api/v1/ingestion/sessions", json={})
                assert response.status_code == 500
    
    def test_invalid_session_access(self, client):
        """Test accessing non-existent session."""
        with patch("torematrix.api.routers.ingestion.get_current_user"):
            with patch("torematrix.api.routers.ingestion.get_upload_manager") as mock_mgr:
                mock_mgr.get_session = Mock(return_value=None)
                
                response = client.get("/api/v1/ingestion/sessions/nonexistent/status")
                assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__])