"""
Unit tests for ProgressTracker.

Tests Redis-based progress tracking for files and sessions.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from typing import Dict, Any

import redis.asyncio as redis

from torematrix.ingestion.progress import ProgressTracker, FileProgress, SessionProgress
from torematrix.core.events import EventBus, ProcessingEvent


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock(spec=redis.Redis)
    mock.hgetall = AsyncMock(return_value={})
    mock.hset = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    mock.sadd = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.scan_iter = AsyncMock(return_value=iter([]))
    mock.close = AsyncMock()
    return mock


@pytest.fixture
async def mock_event_bus():
    """Create mock event bus."""
    mock = AsyncMock(spec=EventBus)
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
async def progress_tracker(mock_redis, mock_event_bus):
    """Create ProgressTracker instance with mocked dependencies."""
    return ProgressTracker(
        redis_client=mock_redis,
        event_bus=mock_event_bus,
        key_prefix="test_progress"
    )


@pytest.fixture
def sample_files():
    """Create sample file data for testing."""
    return [
        {
            "file_id": "file-1",
            "filename": "document1.pdf",
            "size": 1024,
            "mime_type": "application/pdf"
        },
        {
            "file_id": "file-2", 
            "filename": "document2.docx",
            "size": 2048,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        {
            "file_id": "file-3",
            "filename": "spreadsheet.xlsx",
            "size": 4096,
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
    ]


class TestFileProgress:
    """Test cases for FileProgress data class."""
    
    def test_to_dict_conversion(self):
        """Test FileProgress to dictionary conversion."""
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()
        
        progress = FileProgress(
            file_id="test-file",
            filename="test.pdf",
            status="processing",
            progress=0.5,
            current_step="extracting",
            total_steps=5,
            completed_steps=2,
            session_id="session-123",
            size=1024,
            started_at=started_at,
            completed_at=completed_at
        )
        
        data = progress.to_dict()
        
        assert data["file_id"] == "test-file"
        assert data["progress"] == 0.5
        assert data["started_at"] == started_at.isoformat()
        assert data["completed_at"] == completed_at.isoformat()
    
    def test_from_dict_conversion(self):
        """Test creating FileProgress from dictionary."""
        started_at = datetime.utcnow()
        
        data = {
            "file_id": "test-file",
            "filename": "test.pdf",
            "status": "processing",
            "progress": 0.5,
            "current_step": "extracting",
            "total_steps": 5,
            "completed_steps": 2,
            "session_id": "session-123",
            "size": 1024,
            "processed_size": 512,
            "started_at": started_at.isoformat()
        }
        
        progress = FileProgress.from_dict(data)
        
        assert progress.file_id == "test-file"
        assert progress.progress == 0.5
        assert progress.started_at == started_at


class TestSessionProgress:
    """Test cases for SessionProgress data class."""
    
    def test_session_initialization(self):
        """Test SessionProgress initialization."""
        started_at = datetime.utcnow()
        
        session = SessionProgress(
            session_id="session-123",
            total_files=5,
            processed_files=2,
            failed_files=1,
            cancelled_files=0,
            total_size=10240,
            processed_size=4096,
            overall_progress=0.4,
            status="active",
            started_at=started_at
        )
        
        assert session.session_id == "session-123"
        assert session.total_files == 5
        assert session.overall_progress == 0.4
        assert session.files == {}  # Should be initialized as empty dict
    
    def test_to_dict_with_files(self):
        """Test SessionProgress to dictionary conversion with files."""
        started_at = datetime.utcnow()
        
        file_progress = FileProgress(
            file_id="file-1",
            filename="test.pdf",
            status="completed",
            progress=1.0,
            current_step="completed",
            total_steps=5,
            completed_steps=5,
            size=1024
        )
        
        session = SessionProgress(
            session_id="session-123",
            total_files=1,
            processed_files=1,
            failed_files=0,
            cancelled_files=0,
            total_size=1024,
            processed_size=1024,
            overall_progress=1.0,
            status="completed",
            started_at=started_at,
            files={"file-1": file_progress}
        )
        
        data = session.to_dict()
        
        assert data["session_id"] == "session-123"
        assert "files" in data
        assert "file-1" in data["files"]
        assert data["files"]["file-1"]["progress"] == 1.0


class TestProgressTracker:
    """Test cases for ProgressTracker."""
    
    async def test_init_session(self, progress_tracker, sample_files, mock_redis):
        """Test session initialization."""
        session_id = "test-session-123"
        user_id = "user-456"
        
        # Mock Redis operations
        mock_redis.hset = AsyncMock(return_value=True)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.sadd = AsyncMock(return_value=len(sample_files))
        
        # Initialize session
        session = await progress_tracker.init_session(
            session_id=session_id,
            files=sample_files,
            user_id=user_id
        )
        
        # Verify session properties
        assert session.session_id == session_id
        assert session.total_files == len(sample_files)
        assert session.total_size == sum(f["size"] for f in sample_files)
        assert session.status == "active"
        assert session.processed_files == 0
        
        # Verify Redis operations
        mock_redis.hset.assert_called()  # Session and files stored
        mock_redis.expire.assert_called()  # Expiry set
        mock_redis.sadd.assert_called()  # Files added to session set
        
        # Verify session is cached
        assert session_id in progress_tracker._session_cache
    
    async def test_init_file(self, progress_tracker, mock_redis):
        """Test individual file initialization."""
        session_id = "session-123"
        file_id = "file-456"
        filename = "test_document.pdf"
        size = 2048
        
        # Initialize file
        file_progress = await progress_tracker.init_file(
            session_id=session_id,
            file_id=file_id,
            filename=filename,
            size=size
        )
        
        # Verify file progress properties
        assert file_progress.file_id == file_id
        assert file_progress.filename == filename
        assert file_progress.size == size
        assert file_progress.session_id == session_id
        assert file_progress.status == "uploaded"
        assert file_progress.progress == 0.0
        assert file_progress.completed_steps == 1  # uploaded step done
        
        # Verify Redis storage
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
        
        # Verify file is cached
        assert file_id in progress_tracker._file_cache
    
    async def test_update_file_progress(self, progress_tracker, mock_redis, mock_event_bus):
        """Test updating file progress."""
        file_id = "file-123"
        session_id = "session-456"
        
        # Setup existing file progress
        file_progress = FileProgress(
            file_id=file_id,
            filename="test.pdf",
            status="uploaded",
            progress=0.0,
            current_step="uploaded",
            total_steps=5,
            completed_steps=1,
            session_id=session_id,
            size=1024
        )
        progress_tracker._file_cache[file_id] = file_progress
        
        # Mock get_file_progress to return cached data
        progress_tracker.get_file_progress = AsyncMock(return_value=file_progress)
        
        # Update progress
        updated_progress = await progress_tracker.update_file_progress(
            file_id=file_id,
            status="processing",
            current_step="extracting",
            completed_steps=3,
            job_id="job-789"
        )
        
        # Verify updates
        assert updated_progress is not None
        assert updated_progress.status == "processing"
        assert updated_progress.current_step == "extracting"
        assert updated_progress.completed_steps == 3
        assert updated_progress.progress == 3 / 5  # 3 out of 5 steps
        assert updated_progress.job_id == "job-789"
        
        # Verify Redis update
        mock_redis.hset.assert_called()
        
        # Verify event emission
        mock_event_bus.publish.assert_called()
        event_call = mock_event_bus.publish.call_args[0][0]
        assert event_call.file_id == file_id
    
    async def test_update_file_progress_with_completion(self, progress_tracker, mock_redis):
        """Test updating file progress to completion."""
        file_id = "file-123"
        
        # Setup existing file progress
        file_progress = FileProgress(
            file_id=file_id,
            filename="test.pdf",
            status="processing",
            progress=0.8,
            current_step="processing",
            total_steps=5,
            completed_steps=4,
            size=1024,
            started_at=datetime.utcnow()
        )
        progress_tracker._file_cache[file_id] = file_progress
        progress_tracker.get_file_progress = AsyncMock(return_value=file_progress)
        
        # Update to completion
        updated_progress = await progress_tracker.update_file_progress(
            file_id=file_id,
            status="completed",
            current_step="completed",
            progress=1.0,
            processing_time=45.5
        )
        
        # Verify completion updates
        assert updated_progress.status == "completed"
        assert updated_progress.progress == 1.0
        assert updated_progress.completed_at is not None
        assert updated_progress.processing_time == 45.5
    
    async def test_get_file_progress_from_redis(self, progress_tracker, mock_redis):
        """Test retrieving file progress from Redis."""
        file_id = "file-123"
        
        # Mock Redis data
        redis_data = {
            "filename": "test.pdf",
            "status": "processing",
            "progress": "0.5",
            "current_step": "extracting",
            "total_steps": "5",
            "completed_steps": "3",
            "session_id": "session-456",
            "size": "1024",
            "processed_size": "512",
            "job_id": "job-789",
            "retry_count": "0",
            "started_at": datetime.utcnow().isoformat()
        }
        mock_redis.hgetall.return_value = redis_data
        
        # Get file progress
        file_progress = await progress_tracker.get_file_progress(file_id)
        
        # Verify data conversion
        assert file_progress is not None
        assert file_progress.file_id == file_id
        assert file_progress.filename == "test.pdf"
        assert file_progress.status == "processing"
        assert file_progress.progress == 0.5
        assert file_progress.total_steps == 5
        assert file_progress.completed_steps == 3
        assert file_progress.size == 1024
        assert file_progress.processed_size == 512
        
        # Verify caching
        assert file_id in progress_tracker._file_cache
    
    async def test_get_file_progress_not_found(self, progress_tracker, mock_redis):
        """Test retrieving non-existent file progress."""
        file_id = "non-existent-file"
        
        # Mock empty Redis response
        mock_redis.hgetall.return_value = {}
        
        # Get file progress
        file_progress = await progress_tracker.get_file_progress(file_id)
        
        # Should return None
        assert file_progress is None
    
    async def test_get_session_progress(self, progress_tracker, mock_redis):
        """Test retrieving session progress."""
        session_id = "session-123"
        
        # Setup session in cache
        session = SessionProgress(
            session_id=session_id,
            total_files=3,
            processed_files=1,
            failed_files=0,
            cancelled_files=0,
            total_size=4096,
            processed_size=1024,
            overall_progress=0.33,
            status="active",
            started_at=datetime.utcnow()
        )
        progress_tracker._session_cache[session_id] = session
        
        # Mock file IDs for session
        file_ids = {"file-1", "file-2", "file-3"}
        mock_redis.smembers.return_value = file_ids
        
        # Mock file progress retrieval
        async def mock_get_file_progress(file_id):
            return FileProgress(
                file_id=file_id,
                filename=f"{file_id}.pdf",
                status="processed" if file_id == "file-1" else "processing",
                progress=1.0 if file_id == "file-1" else 0.5,
                current_step="completed" if file_id == "file-1" else "processing",
                total_steps=5,
                completed_steps=5 if file_id == "file-1" else 3,
                size=1024
            )
        
        progress_tracker.get_file_progress = mock_get_file_progress
        
        # Get session progress
        session_progress = await progress_tracker.get_session_progress(session_id)
        
        # Verify session data
        assert session_progress is not None
        assert session_progress.session_id == session_id
        assert len(session_progress.files) == 3
        assert "file-1" in session_progress.files
        assert session_progress.files["file-1"].status == "processed"
    
    async def test_get_session_summary(self, progress_tracker, mock_redis):
        """Test retrieving session summary."""
        session_id = "session-123"
        
        # Mock Redis session data
        redis_data = {
            "total_files": "5",
            "processed_files": "3",
            "failed_files": "1",
            "cancelled_files": "0",
            "total_size": "10240",
            "processed_size": "6144",
            "overall_progress": "0.6",
            "status": "active",
            "started_at": datetime.utcnow().isoformat()
        }
        mock_redis.hgetall.return_value = redis_data
        
        # Get session summary
        summary = await progress_tracker.get_session_summary(session_id)
        
        # Verify summary data
        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["total_files"] == 5
        assert summary["processed_files"] == 3
        assert summary["failed_files"] == 1
        assert summary["overall_progress"] == 0.6
        assert summary["status"] == "active"
    
    async def test_mark_session_complete(self, progress_tracker, mock_redis, mock_event_bus):
        """Test marking a session as complete."""
        session_id = "session-123"
        
        # Setup session
        session = SessionProgress(
            session_id=session_id,
            total_files=3,
            processed_files=2,
            failed_files=1,
            cancelled_files=0,
            total_size=4096,
            processed_size=3072,
            overall_progress=0.67,
            status="active",
            started_at=datetime.utcnow()
        )
        
        # Mock get_session_progress
        progress_tracker.get_session_progress = AsyncMock(return_value=session)
        
        # Mark session complete
        result = await progress_tracker.mark_session_complete(session_id)
        
        # Verify completion
        assert result is True
        assert session.completed_at is not None
        assert session.status == "partial_failure"  # Due to failed files
        
        # Verify Redis update
        mock_redis.hset.assert_called()
        
        # Verify event emission
        mock_event_bus.publish.assert_called()
    
    async def test_update_session_progress_calculation(self, progress_tracker, mock_redis):
        """Test session progress calculation from file progress."""
        session_id = "session-123"
        
        # Mock file IDs
        file_ids = {"file-1", "file-2", "file-3"}
        mock_redis.smembers.return_value = file_ids
        
        # Mock file progress data
        file_progress_data = {
            "file-1": FileProgress(
                file_id="file-1", filename="doc1.pdf", status="completed",
                progress=1.0, current_step="completed", total_steps=5, completed_steps=5,
                size=1024, processed_size=1024
            ),
            "file-2": FileProgress(
                file_id="file-2", filename="doc2.pdf", status="processing", 
                progress=0.6, current_step="processing", total_steps=5, completed_steps=3,
                size=2048, processed_size=1024
            ),
            "file-3": FileProgress(
                file_id="file-3", filename="doc3.pdf", status="failed",
                progress=0.4, current_step="failed", total_steps=5, completed_steps=2,
                size=1024, processed_size=0
            )
        }
        
        async def mock_get_file_progress(file_id):
            return file_progress_data.get(file_id)
        
        progress_tracker.get_file_progress = mock_get_file_progress
        
        # Update session progress
        await progress_tracker._update_session_progress(session_id)
        
        # Verify Redis was called with calculated values
        mock_redis.hset.assert_called()
        
        # Extract the call arguments
        call_args = mock_redis.hset.call_args
        session_key = call_args[0][0]
        mapping = call_args[1]["mapping"]
        
        # Verify calculated values
        assert mapping["processed_files"] == "1"  # Only file-1 completed
        assert mapping["failed_files"] == "1"     # file-3 failed
        assert float(mapping["overall_progress"]) == pytest.approx(0.67, rel=1e-2)  # (1.0 + 0.6 + 0.4) / 3
    
    async def test_error_handling(self, progress_tracker, mock_redis):
        """Test error handling in progress tracking."""
        # Mock Redis error
        mock_redis.hgetall.side_effect = Exception("Redis connection error")
        
        # Should handle error gracefully
        result = await progress_tracker.get_file_progress("test-file")
        assert result is None
        
        # Reset mock
        mock_redis.hgetall.side_effect = None
        mock_redis.hgetall.return_value = {}
        
        # Test update with non-existent file
        result = await progress_tracker.update_file_progress(
            file_id="non-existent",
            status="processing",
            current_step="processing"
        )
        assert result is None