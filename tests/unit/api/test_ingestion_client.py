"""
Unit tests for ingestion client SDK.

Tests the client SDK for API interaction including HTTP requests,
WebSocket connections, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
import json
from pathlib import Path
import tempfile
import os

# Import the client SDK
from torematrix.api.client.ingestion_client import IngestionClient, SimpleIngestionClient


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    async def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=None,
                status=self.status_code
            )


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, messages=None):
        self.messages = messages or []
        self.sent_messages = []
        self.message_index = 0
    
    async def send(self, message):
        self.sent_messages.append(message)
    
    async def __aiter__(self):
        for message in self.messages:
            yield message
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def client():
    """Provide ingestion client."""
    return IngestionClient("https://api.test.com", "test-api-key")


@pytest.fixture
def mock_session():
    """Provide mock aiohttp session."""
    session = Mock(spec=aiohttp.ClientSession)
    session.post = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def temp_file():
    """Provide temporary test file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test file content")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    os.unlink(temp_path)


class TestIngestionClient:
    """Test the main ingestion client."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test client as async context manager."""
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = Mock()
            mock_session.close = AsyncMock()
            MockSession.return_value = mock_session
            
            async with client as c:
                assert c._session == mock_session
            
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, client, mock_session):
        """Test successful session creation."""
        # Setup mock response
        expected_response = {
            "session_id": "session-123",
            "user_id": "user-456",
            "status": "active",
            "created_at": "2024-01-01T10:00:00Z",
            "metadata": {"name": "Test Session"}
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.create_session(name="Test Session", metadata={"tag": "test"})
        
        assert result == expected_response
        mock_session.post.assert_called_once()
        
        # Check request parameters
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://api.test.com/api/v1/ingestion/sessions"
        assert call_args[1]["json"]["name"] == "Test Session"
        assert call_args[1]["json"]["metadata"]["tag"] == "test"
    
    @pytest.mark.asyncio
    async def test_create_session_error(self, client, mock_session):
        """Test session creation with server error."""
        mock_response = MockResponse({}, 500)
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        with pytest.raises(aiohttp.ClientResponseError):
            await client.create_session()
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, client, mock_session, temp_file):
        """Test successful file upload."""
        expected_response = {
            "file_id": "file-123",
            "filename": "test.txt",
            "status": "uploaded",
            "size": 17,
            "mime_type": "text/plain",
            "validation_status": "valid",
            "errors": []
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.upload_file(
            session_id="session-123",
            file_path=temp_file,
            validate_content=True,
            auto_process=True,
            priority=False
        )
        
        assert result == expected_response
        mock_session.post.assert_called_once()
        
        # Check URL and parameters
        call_args = mock_session.post.call_args
        assert "sessions/session-123/upload" in call_args[0][0]
        assert call_args[1]["params"]["validate_content"] == "true"
        assert call_args[1]["params"]["auto_process"] == "true"
        assert call_args[1]["params"]["priority"] == "false"
    
    @pytest.mark.asyncio
    async def test_upload_batch_success(self, client, mock_session, temp_file):
        """Test successful batch upload."""
        # Create additional temp files
        temp_files = [temp_file]
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'{i}.txt', delete=False) as f:
                f.write(f"Test file content {i}")
                temp_files.append(Path(f.name))
        
        try:
            expected_response = {
                "session_id": "session-123",
                "total_files": 3,
                "uploaded_files": [
                    {"file_id": f"file-{i}", "filename": f"test{i}.txt", "status": "uploaded"}
                    for i in range(3)
                ],
                "failed_files": [],
                "batch_queued": True
            }
            
            mock_response = MockResponse(expected_response)
            mock_session.post.return_value.__aenter__.return_value = mock_response
            client._session = mock_session
            
            result = await client.upload_batch(
                session_id="session-123",
                file_paths=temp_files
            )
            
            assert result == expected_response
            assert "upload-batch" in mock_session.post.call_args[0][0]
            
        finally:
            # Cleanup additional temp files
            for temp_path in temp_files[1:]:
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_get_session_status(self, client, mock_session):
        """Test getting session status."""
        expected_response = {
            "session_id": "session-123",
            "status": "active",
            "total_files": 2,
            "processed_files": 1,
            "failed_files": 0,
            "overall_progress": 0.5,
            "files": [
                {"file_id": "file-1", "status": "completed"},
                {"file_id": "file-2", "status": "processing"}
            ]
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.get_session_status("session-123")
        
        assert result == expected_response
        mock_session.get.assert_called_once()
        assert "sessions/session-123/status" in mock_session.get.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_get_file_status(self, client, mock_session):
        """Test getting file status."""
        expected_response = {
            "file_id": "file-123",
            "filename": "test.pdf",
            "status": "completed",
            "size": 1024,
            "processing_time": 30.5,
            "extracted_elements": 25
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.get_file_status("file-123")
        
        assert result == expected_response
        assert "files/file-123/status" in mock_session.get.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_retry_file(self, client, mock_session):
        """Test retrying failed file."""
        expected_response = {
            "status": "retried",
            "job_id": "job-retry-1"
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.retry_file("file-123", priority=True)
        
        assert result == expected_response
        call_args = mock_session.post.call_args
        assert "files/file-123/retry" in call_args[0][0]
        assert call_args[1]["params"]["priority"] == "true"
    
    @pytest.mark.asyncio
    async def test_get_queue_stats(self, client, mock_session):
        """Test getting queue statistics."""
        expected_response = {
            "queues": {
                "default": {"count": 10, "jobs": {"queued": 10, "processing": 5}},
                "priority": {"count": 2, "jobs": {"queued": 2, "processing": 1}}
            },
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        mock_response = MockResponse(expected_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        result = await client.get_queue_stats()
        
        assert result == expected_response
        assert "queue/stats" in mock_session.get.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_stream_progress(self, client):
        """Test WebSocket progress streaming."""
        progress_updates = []
        
        def on_update(data):
            progress_updates.append(data)
        
        # Mock WebSocket messages
        messages = [
            "pong",
            json.dumps({"type": "progress_update", "file_id": "file-123", "data": {"progress": 0.5}}),
            json.dumps({"type": "document_completed", "file_id": "file-123", "data": {}})
        ]
        
        mock_websocket = MockWebSocket(messages)
        
        with patch("websockets.connect", return_value=mock_websocket):
            # Run for a short time then cancel
            task = asyncio.create_task(client.stream_progress("session-123", on_update))
            await asyncio.sleep(0.1)  # Let it process some messages
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Should have received progress updates (excluding pong)
        assert len(progress_updates) >= 1
        assert progress_updates[0]["type"] == "progress_update"
    
    @pytest.mark.asyncio
    async def test_upload_and_wait_single_file(self, client, temp_file):
        """Test upload and wait for single file."""
        with patch.object(client, 'upload_file') as mock_upload:
            with patch.object(client, 'get_session_status') as mock_status:
                # Mock upload response
                mock_upload.return_value = {"file_id": "file-123", "status": "uploaded"}
                
                # Mock status responses - first processing, then completed
                mock_status.side_effect = [
                    {"total_files": 1, "processed_files": 0, "failed_files": 0},
                    {"total_files": 1, "processed_files": 1, "failed_files": 0}
                ]
                
                result = await client.upload_and_wait("session-123", [temp_file])
                
                assert result["processed_files"] == 1
                mock_upload.assert_called_once_with("session-123", temp_file)
                assert mock_status.call_count == 2
    
    @pytest.mark.asyncio
    async def test_upload_and_wait_batch(self, client, temp_file):
        """Test upload and wait for batch."""
        with patch.object(client, 'upload_batch') as mock_upload:
            with patch.object(client, 'get_session_status') as mock_status:
                # Mock upload response
                mock_upload.return_value = {"total_files": 2, "uploaded_files": []}
                
                # Mock status responses
                mock_status.side_effect = [
                    {"total_files": 2, "processed_files": 1, "failed_files": 0},
                    {"total_files": 2, "processed_files": 2, "failed_files": 0}
                ]
                
                result = await client.upload_and_wait("session-123", [temp_file, temp_file])
                
                assert result["processed_files"] == 2
                mock_upload.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_session(self, client):
        """Test waiting for session completion."""
        with patch.object(client, 'get_session_status') as mock_status:
            # Mock progression from processing to completed
            mock_status.side_effect = [
                {"total_files": 3, "processed_files": 1, "failed_files": 0},
                {"total_files": 3, "processed_files": 2, "failed_files": 0},
                {"total_files": 3, "processed_files": 2, "failed_files": 1}  # Completed
            ]
            
            result = await client.wait_for_session("session-123", poll_interval=0.01)
            
            assert result["processed_files"] + result["failed_files"] == 3
            assert mock_status.call_count == 3
    
    @pytest.mark.asyncio
    async def test_wait_for_session_timeout(self, client):
        """Test session wait with timeout."""
        with patch.object(client, 'get_session_status') as mock_status:
            # Always return processing status
            mock_status.return_value = {"total_files": 1, "processed_files": 0, "failed_files": 0}
            
            with pytest.raises(TimeoutError):
                await client.wait_for_session("session-123", timeout=0.1, poll_interval=0.01)


class TestSimpleIngestionClient:
    """Test the simplified synchronous client."""
    
    def test_upload_files_basic(self, temp_file):
        """Test basic file upload with simple client."""
        simple_client = SimpleIngestionClient("https://api.test.com", "test-key")
        
        with patch.object(simple_client.client, 'create_session') as mock_create:
            with patch.object(simple_client.client, 'upload_file') as mock_upload:
                # Mock session creation
                mock_create.return_value = {"session_id": "session-123"}
                
                # Mock file upload
                mock_upload.return_value = {"file_id": "file-123", "status": "uploaded"}
                
                result = simple_client.upload_files([temp_file], wait_for_completion=False)
                
                assert "session" in result
                assert "upload" in result
                mock_create.assert_called_once()
                mock_upload.assert_called_once()
    
    def test_upload_files_with_completion(self, temp_file):
        """Test file upload with wait for completion."""
        simple_client = SimpleIngestionClient("https://api.test.com", "test-key")
        
        with patch.object(simple_client.client, 'upload_and_wait') as mock_upload_wait:
            mock_upload_wait.return_value = {"total_files": 1, "processed_files": 1}
            
            result = simple_client.upload_files([temp_file], wait_for_completion=True)
            
            assert result["processed_files"] == 1
            mock_upload_wait.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, client, mock_session):
        """Test handling HTTP errors."""
        mock_response = MockResponse({"error": "Server error"}, 500)
        mock_session.post.return_value.__aenter__.return_value = mock_response
        client._session = mock_session
        
        with pytest.raises(aiohttp.ClientResponseError):
            await client.create_session()
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, client, mock_session):
        """Test handling network errors."""
        mock_session.post.side_effect = aiohttp.ClientConnectorError(
            connection_key=None, os_error=None
        )
        client._session = mock_session
        
        with pytest.raises(aiohttp.ClientConnectorError):
            await client.create_session()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_error(self, client):
        """Test WebSocket connection error handling."""
        def on_update(data):
            pass
        
        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                await client.stream_progress("session-123", on_update)
    
    @pytest.mark.asyncio
    async def test_invalid_file_path(self, client, mock_session):
        """Test upload with invalid file path."""
        client._session = mock_session
        
        with pytest.raises(FileNotFoundError):
            await client.upload_file("session-123", "/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self, client):
        """Test WebSocket with invalid JSON messages."""
        progress_updates = []
        
        def on_update(data):
            progress_updates.append(data)
        
        # Include invalid JSON message
        messages = [
            "invalid json",
            json.dumps({"type": "valid", "data": {}})
        ]
        
        mock_websocket = MockWebSocket(messages)
        
        with patch("websockets.connect", return_value=mock_websocket):
            # Should handle invalid JSON gracefully
            task = asyncio.create_task(client.stream_progress("session-123", on_update))
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Should only have processed valid messages
        assert len(progress_updates) == 1
        assert progress_updates[0]["type"] == "valid"


class TestClientConfiguration:
    """Test client configuration and initialization."""
    
    def test_client_initialization(self):
        """Test client initialization with parameters."""
        client = IngestionClient(
            base_url="https://api.example.com/",
            api_key="test-key-123",
            timeout=60,
            max_retries=5
        )
        
        assert client.base_url == "https://api.example.com"  # Should strip trailing slash
        assert client.api_key == "test-key-123"
        assert client.timeout == 60
        assert client.max_retries == 5
    
    @pytest.mark.asyncio
    async def test_session_headers(self, client):
        """Test that session includes correct headers."""
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = Mock()
            MockSession.return_value = mock_session
            
            async with client:
                pass
            
            # Check that session was created with correct headers
            MockSession.assert_called_once()
            call_kwargs = MockSession.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-api-key"


if __name__ == "__main__":
    pytest.main([__file__])