"""
Unit tests for WebSocket progress handler.

Tests WebSocket connection management, event handling, and message broadcasting
with comprehensive mocking of dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

# Import the modules we're testing
from torematrix.api.websockets.progress import (
    ConnectionManager,
    ProgressWebSocket,
    manager,
    websocket_endpoint
)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.accept = AsyncMock()
        self.send_json = AsyncMock()
        self.send_text = AsyncMock()
        self.receive_text = AsyncMock()
        self.close = AsyncMock()


class MockEventBus:
    """Mock event bus for testing."""
    
    def __init__(self):
        self.subscribe = Mock()
        self.emit = AsyncMock()
        self.subscriptions = {}
    
    def setup_subscription(self, event_type, handler):
        """Setup subscription for testing."""
        self.subscriptions[event_type] = handler


class MockProgressTracker:
    """Mock progress tracker for testing."""
    
    def __init__(self):
        self.get_session_progress = AsyncMock()
        self.update_file_progress = AsyncMock()


class MockUser:
    """Mock user for authentication."""
    
    def __init__(self, user_id: str = "user-123"):
        self.id = user_id


@pytest.fixture
def mock_websocket():
    """Provide mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_event_bus():
    """Provide mock event bus."""
    return MockEventBus()


@pytest.fixture
def mock_progress_tracker():
    """Provide mock progress tracker."""
    return MockProgressTracker()


@pytest.fixture
def mock_user():
    """Provide mock user."""
    return MockUser()


class TestConnectionManager:
    """Test WebSocket connection management."""
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, mock_websocket):
        """Test connecting a WebSocket."""
        manager = ConnectionManager()
        
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        mock_websocket.accept.assert_called_once()
        assert "session-123" in manager._connections
        assert mock_websocket in manager._connections["session-123"]
        assert mock_websocket in manager._user_info
        assert manager._user_info[mock_websocket]["user_id"] == "user-123"
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(self, mock_websocket):
        """Test disconnecting a WebSocket."""
        manager = ConnectionManager()
        
        # First connect
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        # Then disconnect
        await manager.disconnect(mock_websocket)
        
        assert mock_websocket not in manager._user_info
        assert "session-123" not in manager._connections  # Should be cleaned up
    
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, mock_websocket):
        """Test broadcasting message to session."""
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        # Broadcast message
        message = {"type": "test", "data": {"progress": 0.5}}
        await manager.broadcast_to_session("session-123", message)
        
        mock_websocket.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_session(self):
        """Test broadcasting to session with no connections."""
        manager = ConnectionManager()
        
        # This should not raise an error
        message = {"type": "test", "data": {}}
        await manager.broadcast_to_session("nonexistent", message)
    
    @pytest.mark.asyncio
    async def test_send_to_user(self, mock_websocket):
        """Test sending message to specific user."""
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        # Send to user
        message = {"type": "user_message", "data": {}}
        await manager.send_to_user("user-123", message)
        
        mock_websocket.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_connection_failure_cleanup(self, mock_websocket):
        """Test cleanup when WebSocket send fails."""
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        # Make send_json fail
        mock_websocket.send_json.side_effect = Exception("Connection lost")
        
        # Broadcast should handle the failure and clean up
        message = {"type": "test", "data": {}}
        await manager.broadcast_to_session("session-123", message)
        
        # Connection should be cleaned up
        assert mock_websocket not in manager._user_info
    
    def test_get_connection_stats(self, mock_websocket):
        """Test getting connection statistics."""
        manager = ConnectionManager()
        
        # Add some connections
        asyncio.run(manager.connect(mock_websocket, "session-123", "user-123"))
        
        stats = manager.get_connection_stats()
        
        assert stats["total_connections"] == 1
        assert stats["active_sessions"] == 1
        assert "sessions" in stats
        assert stats["sessions"]["session-123"] == 1


class TestProgressWebSocket:
    """Test WebSocket progress handler."""
    
    @pytest.mark.asyncio
    async def test_start_event_subscriptions(self, mock_event_bus, mock_progress_tracker):
        """Test starting event subscriptions."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        await handler.start()
        
        # Should subscribe to all required events
        expected_events = [
            "progress_updated",
            "job_enqueued", 
            "document_processed",
            "document_failed",
            "batch_completed"
        ]
        
        assert mock_event_bus.subscribe.call_count == len(expected_events)
        for event in expected_events:
            mock_event_bus.subscribe.assert_any_call(event, handler._handle_progress_event)
    
    @pytest.mark.asyncio
    async def test_handle_connection_with_initial_progress(self, mock_websocket, mock_event_bus, mock_progress_tracker):
        """Test handling WebSocket connection with initial progress."""
        # Setup mock progress
        from torematrix.ingestion.progress import SessionProgress, FileProgress
        
        mock_progress = SessionProgress(
            session_id="session-123",
            total_files=2,
            processed_files=1,
            failed_files=0,
            total_size=2048,
            processed_size=1024,
            overall_progress=0.5,
            files={
                "file-1": FileProgress(
                    file_id="file-1",
                    filename="test1.pdf",
                    status="completed",
                    progress=1.0,
                    current_step="done",
                    total_steps=5,
                    completed_steps=5
                )
            }
        )
        mock_progress_tracker.get_session_progress.return_value = mock_progress
        
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock receive_text to simulate client ping and then disconnect
        mock_websocket.receive_text.side_effect = ["ping", asyncio.CancelledError()]
        
        with patch("torematrix.api.websockets.progress.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            try:
                await handler.handle_connection(mock_websocket, "session-123", "user-123")
            except asyncio.CancelledError:
                pass  # Expected when simulating disconnect
        
        # Should send initial progress
        assert mock_websocket.send_json.call_count >= 2  # Initial progress + connection ack
        
        # Check that initial progress was sent
        calls = mock_websocket.send_json.call_args_list
        initial_call = calls[0][0][0]  # First call, first argument
        assert initial_call["type"] == "initial_progress"
        assert "data" in initial_call
    
    @pytest.mark.asyncio
    async def test_handle_client_messages(self, mock_websocket, mock_event_bus, mock_progress_tracker):
        """Test handling different client message types."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Test ping/pong
        mock_websocket.receive_text.side_effect = ["ping", "get_file:file-123", asyncio.CancelledError()]
        
        with patch("torematrix.api.websockets.progress.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            with patch.object(handler, '_send_file_progress', new_callable=AsyncMock) as mock_send_file:
                try:
                    await handler.handle_connection(mock_websocket, "session-123", "user-123")
                except asyncio.CancelledError:
                    pass
        
        # Should respond to ping with pong
        mock_websocket.send_text.assert_called_with("pong")
        
        # Should handle get_file request
        mock_send_file.assert_called_once_with(mock_websocket, "session-123", "file-123")
    
    @pytest.mark.asyncio
    async def test_handle_progress_event(self, mock_event_bus, mock_progress_tracker):
        """Test handling progress update events."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock event
        from torematrix.core.events import ProcessingEvent
        event = ProcessingEvent(
            type="progress_updated",
            file_id="file-123",
            data={"progress": 0.7, "current_step": "processing"}
        )
        
        # Mock file session lookup
        with patch.object(handler, '_get_file_session', return_value={"session_id": "session-123"}):
            with patch("torematrix.api.websockets.progress.manager") as mock_manager:
                mock_manager.broadcast_to_session = AsyncMock()
                
                await handler._handle_progress_event(event)
        
        # Should broadcast update to session
        mock_manager.broadcast_to_session.assert_called_once()
        call_args = mock_manager.broadcast_to_session.call_args[0]
        assert call_args[0] == "session-123"  # session_id
        message = call_args[1]
        assert message["type"] == "progress_update"
        assert message["file_id"] == "file-123"
    
    @pytest.mark.asyncio
    async def test_handle_completion_event(self, mock_event_bus, mock_progress_tracker):
        """Test handling document completion events."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock event
        from torematrix.core.events import ProcessingEvent
        event = ProcessingEvent(
            type="document_processed",
            file_id="file-123",
            data={"processing_time": 30.5, "elements": 25}
        )
        
        with patch.object(handler, '_get_file_session', return_value={"session_id": "session-123"}):
            with patch("torematrix.api.websockets.progress.manager") as mock_manager:
                mock_manager.broadcast_to_session = AsyncMock()
                
                await handler._handle_completion_event(event)
        
        # Should update progress tracker
        mock_progress_tracker.update_file_progress.assert_called_once_with(
            "file-123",
            status="completed",
            current_step="done",
            completed_steps=5
        )
        
        # Should broadcast completion
        mock_manager.broadcast_to_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_failure_event(self, mock_event_bus, mock_progress_tracker):
        """Test handling document failure events."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock event with error
        from torematrix.core.events import ProcessingEvent
        event = ProcessingEvent(
            type="document_failed",
            file_id="file-123",
            error="Processing timeout"
        )
        
        with patch.object(handler, '_get_file_session', return_value={"session_id": "session-123"}):
            with patch("torematrix.api.websockets.progress.manager") as mock_manager:
                mock_manager.broadcast_to_session = AsyncMock()
                
                await handler._handle_failure_event(event)
        
        # Should update progress tracker with error
        mock_progress_tracker.update_file_progress.assert_called_once_with(
            "file-123",
            status="failed",
            current_step="error",
            completed_steps=0,
            error="Processing timeout"
        )
    
    @pytest.mark.asyncio
    async def test_send_file_progress(self, mock_websocket, mock_event_bus, mock_progress_tracker):
        """Test sending specific file progress."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock session progress with file
        from torematrix.ingestion.progress import SessionProgress, FileProgress
        
        file_progress = FileProgress(
            file_id="file-123",
            filename="test.pdf",
            status="processing",
            progress=0.6,
            current_step="extracting",
            total_steps=5,
            completed_steps=3
        )
        
        session_progress = SessionProgress(
            session_id="session-123",
            total_files=1,
            processed_files=0,
            failed_files=0,
            total_size=1024,
            processed_size=0,
            overall_progress=0.6,
            files={"file-123": file_progress}
        )
        
        mock_progress_tracker.get_session_progress.return_value = session_progress
        
        await handler._send_file_progress(mock_websocket, "session-123", "file-123")
        
        # Should send file progress
        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]
        assert message["type"] == "file_progress"
        assert message["file_id"] == "file-123"
        assert message["data"]["status"] == "processing"
        assert message["data"]["progress"] == 0.6
    
    @pytest.mark.asyncio
    async def test_serialize_progress(self, mock_event_bus, mock_progress_tracker):
        """Test progress serialization for JSON transmission."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        from torematrix.ingestion.progress import SessionProgress, FileProgress
        
        file_progress = FileProgress(
            file_id="file-123",
            filename="test.pdf",
            status="completed",
            progress=1.0,
            current_step="done",
            total_steps=5,
            completed_steps=5,
            started_at=datetime(2024, 1, 1, 10, 0, 0),
            completed_at=datetime(2024, 1, 1, 10, 5, 0)
        )
        
        session_progress = SessionProgress(
            session_id="session-123",
            total_files=1,
            processed_files=1,
            failed_files=0,
            total_size=1024,
            processed_size=1024,
            overall_progress=1.0,
            files={"file-123": file_progress}
        )
        
        result = handler._serialize_progress(session_progress)
        
        assert result["session_id"] == "session-123"
        assert result["total_files"] == 1
        assert result["overall_progress"] == 1.0
        assert "files" in result
        assert "file-123" in result["files"]
        
        file_data = result["files"]["file-123"]
        assert file_data["filename"] == "test.pdf"
        assert file_data["status"] == "completed"
        assert file_data["started_at"] == "2024-01-01T10:00:00"
        assert file_data["completed_at"] == "2024-01-01T10:05:00"


class TestWebSocketEndpoint:
    """Test WebSocket endpoint function."""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_unauthorized(self, mock_websocket):
        """Test WebSocket endpoint with invalid token."""
        with patch("torematrix.api.websockets.progress.verify_websocket_token", return_value=None):
            await websocket_endpoint(
                mock_websocket,
                "session-123",
                "invalid-token",
                None,  # event_bus
                None   # progress_tracker
            )
        
        mock_websocket.close.assert_called_once_with(code=4001, reason="Unauthorized")
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_authorized(self, mock_websocket, mock_user):
        """Test WebSocket endpoint with valid token."""
        mock_event_bus = MockEventBus()
        mock_progress_tracker = MockProgressTracker()
        
        with patch("torematrix.api.websockets.progress.verify_websocket_token", return_value=mock_user):
            with patch("torematrix.api.websockets.progress.ProgressWebSocket") as MockProgressWebSocket:
                mock_handler = Mock()
                mock_handler.start = AsyncMock()
                mock_handler.handle_connection = AsyncMock()
                MockProgressWebSocket.return_value = mock_handler
                
                await websocket_endpoint(
                    mock_websocket,
                    "session-123",
                    "valid-token",
                    mock_event_bus,
                    mock_progress_tracker
                )
        
        # Should create handler and start it
        MockProgressWebSocket.assert_called_once_with(mock_event_bus, mock_progress_tracker)
        mock_handler.start.assert_called_once()
        mock_handler.handle_connection.assert_called_once_with(mock_websocket, "session-123", mock_user.id)


class TestWebSocketHealth:
    """Test WebSocket health check."""
    
    @pytest.mark.asyncio
    async def test_websocket_health(self):
        """Test WebSocket health endpoint."""
        from torematrix.api.websockets.progress import websocket_health
        
        with patch("torematrix.api.websockets.progress.manager") as mock_manager:
            mock_manager.get_connection_stats.return_value = {
                "total_connections": 5,
                "active_sessions": 3
            }
            
            result = await websocket_health()
        
        assert result["status"] == "healthy"
        assert "connections" in result
        assert "timestamp" in result
        assert result["connections"]["total_connections"] == 5


class TestErrorHandling:
    """Test error handling in WebSocket operations."""
    
    @pytest.mark.asyncio
    async def test_connection_error_during_broadcast(self, mock_websocket):
        """Test handling connection errors during broadcast."""
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(mock_websocket, "session-123", "user-123")
        
        # Make send_json raise an exception
        mock_websocket.send_json.side_effect = ConnectionError("Connection lost")
        
        # Broadcast should handle the error gracefully
        message = {"type": "test", "data": {}}
        await manager.broadcast_to_session("session-123", message)
        
        # Connection should be cleaned up
        assert len(manager._connections) == 0
        assert len(manager._user_info) == 0
    
    @pytest.mark.asyncio
    async def test_event_handling_error_recovery(self, mock_event_bus, mock_progress_tracker):
        """Test error recovery in event handling."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Mock event
        from torematrix.core.events import ProcessingEvent
        event = ProcessingEvent(
            type="progress_updated",
            file_id="file-123",
            data={}
        )
        
        # Make _get_file_session raise an exception
        with patch.object(handler, '_get_file_session', side_effect=Exception("Database error")):
            # Should not raise exception, just log error
            await handler._handle_progress_event(event)
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_during_operation(self, mock_websocket, mock_event_bus, mock_progress_tracker):
        """Test handling WebSocket disconnect during operation."""
        handler = ProgressWebSocket(mock_event_bus, mock_progress_tracker)
        
        # Simulate disconnect during receive
        from fastapi import WebSocketDisconnect
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()
        
        with patch("torematrix.api.websockets.progress.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            # Should handle disconnect gracefully
            await handler.handle_connection(mock_websocket, "session-123", "user-123")
            
            # Should clean up connection
            mock_manager.disconnect.assert_called_once_with(mock_websocket)


if __name__ == "__main__":
    pytest.main([__file__])