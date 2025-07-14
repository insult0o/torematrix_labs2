"""
Unit tests for QueueManager.

Tests Redis/RQ integration, job enqueuing, retries, and batch processing.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

import redis.asyncio as redis
from rq import Queue, Job
from rq.job import JobStatus

from torematrix.ingestion.queue_manager import QueueManager, JobInfo, QueueStats
from torematrix.ingestion.queue_config import QueueConfig, RetryPolicy
from torematrix.ingestion.models import FileMetadata, FileStatus, FileType
from torematrix.core.events import EventBus, ProcessingEvent


@pytest.fixture
def queue_config():
    """Create test queue configuration."""
    return QueueConfig(
        redis_url="redis://localhost:6379/0",
        batch_size=5,
        max_retries=3,
        job_timeout=300,
        enable_metrics=True
    )


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
async def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock(spec=redis.Redis)
    mock.ping = AsyncMock(return_value=True)
    mock.hgetall = AsyncMock(return_value={})
    mock.hset = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    mock.sadd = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.close = AsyncMock()
    return mock


@pytest.fixture
async def mock_sync_redis():
    """Create mock synchronous Redis client for RQ."""
    mock = Mock()
    mock.ping = Mock(return_value=True)
    mock.close = Mock()
    return mock


@pytest.fixture
async def mock_event_bus():
    """Create mock event bus."""
    mock = AsyncMock(spec=EventBus)
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
async def queue_manager(queue_config, mock_redis, mock_sync_redis, mock_event_bus):
    """Create QueueManager instance with mocked dependencies."""
    manager = QueueManager(queue_config, mock_event_bus)
    
    # Mock Redis clients
    manager._redis_client = mock_redis
    manager._sync_redis_client = mock_sync_redis
    
    # Mock queues
    mock_default_queue = Mock(spec=Queue)
    mock_default_queue.enqueue = Mock()
    mock_default_queue.enqueue_in = Mock()
    mock_default_queue.__len__ = Mock(return_value=0)
    mock_default_queue.count = 0
    mock_default_queue.started_job_registry = Mock(count=0)
    mock_default_queue.finished_job_registry = Mock(count=0, get_job_ids=Mock(return_value=[]))
    mock_default_queue.failed_job_registry = Mock(count=0, get_job_ids=Mock(return_value=[]))
    mock_default_queue.deferred_job_registry = Mock(count=0)
    
    mock_priority_queue = Mock(spec=Queue)
    mock_priority_queue.enqueue = Mock()
    mock_priority_queue.enqueue_in = Mock()
    mock_priority_queue.__len__ = Mock(return_value=0)
    mock_priority_queue.count = 0
    mock_priority_queue.started_job_registry = Mock(count=0)
    mock_priority_queue.finished_job_registry = Mock(count=0, get_job_ids=Mock(return_value=[]))
    mock_priority_queue.failed_job_registry = Mock(count=0, get_job_ids=Mock(return_value=[]))
    mock_priority_queue.deferred_job_registry = Mock(count=0)
    
    manager._queues = {
        "default": mock_default_queue,
        "priority": mock_priority_queue,
        "failed": Mock(spec=Queue)
    }
    
    return manager


class TestQueueManager:
    """Test cases for QueueManager."""
    
    async def test_initialization(self, queue_config, mock_event_bus):
        """Test QueueManager initialization."""
        manager = QueueManager(queue_config, mock_event_bus)
        
        assert manager.config == queue_config
        assert manager.event_bus == mock_event_bus
        assert manager._redis_client is None
        assert manager._sync_redis_client is None
        assert len(manager._queues) == 0
        assert len(manager._jobs) == 0
    
    @patch('redis.asyncio.from_url')
    @patch('redis.from_url')
    @patch('torematrix.ingestion.queue_manager.Connection')
    @patch('torematrix.ingestion.queue_manager.Queue')
    async def test_initialize_success(
        self, 
        mock_queue_class,
        mock_connection,
        mock_sync_redis_from_url,
        mock_async_redis_from_url,
        queue_config,
        mock_event_bus
    ):
        """Test successful initialization with Redis."""
        # Setup mocks
        mock_async_redis = AsyncMock()
        mock_async_redis.ping = AsyncMock(return_value=True)
        mock_async_redis_from_url.return_value = mock_async_redis
        
        mock_sync_redis = Mock()
        mock_sync_redis_from_url.return_value = mock_sync_redis
        
        mock_queue_instance = Mock(spec=Queue)
        mock_queue_class.return_value = mock_queue_instance
        
        manager = QueueManager(queue_config, mock_event_bus)
        
        # Test initialization
        await manager.initialize()
        
        # Verify Redis clients were created
        mock_async_redis_from_url.assert_called_once_with(
            queue_config.redis_url,
            max_connections=queue_config.redis_max_connections,
            socket_timeout=queue_config.redis_socket_timeout,
            decode_responses=True
        )
        
        mock_sync_redis_from_url.assert_called_once_with(
            queue_config.redis_url,
            max_connections=queue_config.redis_connection_pool_size,
            socket_timeout=queue_config.redis_socket_timeout,
            decode_responses=True
        )
        
        # Verify queues were created
        assert len(manager._queues) == 3
        assert "default" in manager._queues
        assert "priority" in manager._queues
        assert "failed" in manager._queues
    
    async def test_enqueue_file_default_queue(self, queue_manager, sample_file_metadata):
        """Test enqueueing a file to the default queue."""
        # Setup mock job
        mock_job = Mock(spec=Job)
        mock_job.id = "job-123"
        mock_job.get_status.return_value = JobStatus.QUEUED
        
        queue_manager._queues["default"].enqueue.return_value = mock_job
        
        # Enqueue file
        with patch('torematrix.ingestion.queue_manager.Connection'):
            job_id = await queue_manager.enqueue_file(sample_file_metadata)
        
        # Verify job was enqueued
        assert job_id == "job-123"
        assert job_id in queue_manager._jobs
        
        # Verify job info
        job_info = queue_manager._jobs[job_id]
        assert job_info.file_id == sample_file_metadata.file_id
        assert job_info.queue_name == "default"
        assert job_info.status == JobStatus.QUEUED
        
        # Verify event was emitted
        queue_manager.event_bus.publish.assert_called_once()
        event_call = queue_manager.event_bus.publish.call_args[0][0]
        assert event_call.file_id == sample_file_metadata.file_id
        assert event_call.job_id == job_id
    
    async def test_enqueue_file_priority_queue(self, queue_manager, sample_file_metadata):
        """Test enqueueing a file to the priority queue."""
        # Setup mock job
        mock_job = Mock(spec=Job)
        mock_job.id = "job-priority-123"
        mock_job.get_status.return_value = JobStatus.QUEUED
        
        queue_manager._queues["priority"].enqueue.return_value = mock_job
        
        # Enqueue file with priority
        with patch('torematrix.ingestion.queue_manager.Connection'):
            job_id = await queue_manager.enqueue_file(sample_file_metadata, priority=True)
        
        # Verify job was enqueued to priority queue
        assert job_id == "job-priority-123"
        job_info = queue_manager._jobs[job_id]
        assert job_info.queue_name == "priority"
    
    async def test_enqueue_file_with_delay(self, queue_manager, sample_file_metadata):
        """Test enqueueing a file with delay."""
        # Setup mock job
        mock_job = Mock(spec=Job)
        mock_job.id = "job-delayed-123"
        mock_job.get_status.return_value = JobStatus.DEFERRED
        
        queue_manager._queues["default"].enqueue_in.return_value = mock_job
        
        # Enqueue file with delay
        delay = timedelta(minutes=5)
        with patch('torematrix.ingestion.queue_manager.Connection'):
            job_id = await queue_manager.enqueue_file(sample_file_metadata, delay=delay)
        
        # Verify delayed enqueue was called
        queue_manager._queues["default"].enqueue_in.assert_called_once()
        args = queue_manager._queues["default"].enqueue_in.call_args
        assert args[0][0] == delay  # First argument should be the delay
    
    async def test_enqueue_batch(self, queue_manager, sample_file_metadata):
        """Test enqueueing a batch of files."""
        # Create multiple files
        files = []
        for i in range(7):  # More than batch_size (5)
            file_metadata = FileMetadata(
                file_id=f"file-{i}",
                filename=f"test_{i}.pdf",
                file_type=FileType.PDF,
                mime_type="application/pdf",
                size=1024,
                hash=f"hash-{i}",
                upload_session_id="session-123",
                uploaded_by="user-123",
                uploaded_at=datetime.utcnow(),
                storage_key=f"/storage/test_{i}.pdf",
                status=FileStatus.UPLOADED
            )
            files.append(file_metadata)
        
        # Setup mock jobs
        mock_jobs = []
        for i in range(2):  # Should create 2 batch jobs (5 + 2 files)
            mock_job = Mock(spec=Job)
            mock_job.id = f"batch-job-{i}"
            mock_jobs.append(mock_job)
        
        queue_manager._queues["default"].enqueue.side_effect = mock_jobs
        
        # Enqueue batch
        with patch('torematrix.ingestion.queue_manager.Connection'):
            job_ids = await queue_manager.enqueue_batch(files)
        
        # Verify correct number of batch jobs created
        assert len(job_ids) == 2
        assert queue_manager._queues["default"].enqueue.call_count == 2
        
        # Verify batch event was emitted
        queue_manager.event_bus.publish.assert_called_once()
    
    async def test_get_job_status_not_found(self, queue_manager):
        """Test getting job status for non-existent job."""
        result = await queue_manager.get_job_status("non-existent-job")
        assert result is None
    
    @patch('torematrix.ingestion.queue_manager.Job.fetch')
    async def test_get_job_status_success(self, mock_job_fetch, queue_manager):
        """Test getting job status for existing job."""
        # Setup existing job info
        job_id = "test-job-123"
        job_info = JobInfo(
            job_id=job_id,
            file_id="file-123",
            queue_name="default",
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        queue_manager._jobs[job_id] = job_info
        
        # Setup mock RQ job
        mock_rq_job = Mock(spec=Job)
        mock_rq_job.get_status.return_value = JobStatus.FINISHED
        mock_rq_job.is_finished = True
        mock_rq_job.is_failed = False
        mock_rq_job.started_at = datetime.utcnow()
        mock_rq_job.ended_at = datetime.utcnow()
        mock_rq_job.result = {"status": "success"}
        
        mock_job_fetch.return_value = mock_rq_job
        
        with patch('torematrix.ingestion.queue_manager.Connection'):
            result = await queue_manager.get_job_status(job_id)
        
        # Verify updated job info
        assert result is not None
        assert result.status == JobStatus.FINISHED
        assert result.result == {"status": "success"}
    
    @patch('torematrix.ingestion.queue_manager.Job.fetch')
    async def test_retry_failed_job(self, mock_job_fetch, queue_manager):
        """Test retrying a failed job."""
        # Setup failed job
        job_id = "failed-job-123"
        job_info = JobInfo(
            job_id=job_id,
            file_id="file-123",
            queue_name="default",
            status=JobStatus.FAILED,
            created_at=datetime.utcnow(),
            retry_count=0
        )
        queue_manager._jobs[job_id] = job_info
        
        # Setup retry policy
        retry_policy = RetryPolicy(max_attempts=3, initial_delay=60)
        queue_manager._retry_policies[job_id] = retry_policy
        
        # Setup mock original job
        mock_original_job = Mock(spec=Job)
        mock_original_job.func_name = "process_document"
        mock_original_job.args = ({"file_id": "file-123"},)
        mock_original_job.kwargs = {}
        mock_original_job.meta = {"retry_count": 0}
        
        mock_job_fetch.return_value = mock_original_job
        
        # Setup mock new job
        mock_new_job = Mock(spec=Job)
        mock_new_job.id = "retry-job-123"
        mock_new_job.get_status.return_value = JobStatus.DEFERRED
        
        queue_manager._queues["default"].enqueue_in.return_value = mock_new_job
        
        # Retry the job
        with patch('torematrix.ingestion.queue_manager.Connection'):
            new_job_id = await queue_manager.retry_failed_job(job_id)
        
        # Verify retry was successful
        assert new_job_id == "retry-job-123"
        assert new_job_id in queue_manager._jobs
        
        # Verify new job info
        new_job_info = queue_manager._jobs[new_job_id]
        assert new_job_info.retry_count == 1
        
        # Verify retry event was emitted
        queue_manager.event_bus.publish.assert_called_once()
    
    async def test_retry_failed_job_max_retries_exceeded(self, queue_manager):
        """Test retry fails when max retries exceeded."""
        # Setup job with max retries
        job_id = "max-retry-job-123"
        job_info = JobInfo(
            job_id=job_id,
            file_id="file-123",
            queue_name="default",
            status=JobStatus.FAILED,
            created_at=datetime.utcnow(),
            retry_count=3  # Already at max
        )
        queue_manager._jobs[job_id] = job_info
        
        # Setup retry policy
        retry_policy = RetryPolicy(max_attempts=3)
        queue_manager._retry_policies[job_id] = retry_policy
        
        # Attempt retry
        result = await queue_manager.retry_failed_job(job_id)
        
        # Should return None (no retry)
        assert result is None
    
    @patch('torematrix.ingestion.queue_manager.Job.fetch')
    async def test_cancel_job(self, mock_job_fetch, queue_manager):
        """Test cancelling a job."""
        job_id = "cancel-job-123"
        
        # Setup job info
        job_info = JobInfo(
            job_id=job_id,
            file_id="file-123",
            queue_name="default",
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        queue_manager._jobs[job_id] = job_info
        
        # Setup mock job
        mock_job = Mock(spec=Job)
        mock_job.cancel = Mock()
        mock_job_fetch.return_value = mock_job
        
        # Cancel the job
        with patch('torematrix.ingestion.queue_manager.Connection'):
            result = await queue_manager.cancel_job(job_id)
        
        # Verify cancellation
        assert result is True
        mock_job.cancel.assert_called_once()
        
        # Verify job status updated
        assert queue_manager._jobs[job_id].status == JobStatus.CANCELED
        
        # Verify event was emitted
        queue_manager.event_bus.publish.assert_called_once()
    
    @patch('torematrix.ingestion.queue_manager.Worker.all')
    async def test_get_queue_stats(self, mock_worker_all, queue_manager):
        """Test getting queue statistics."""
        # Setup mock workers
        mock_workers = [
            Mock(name="worker-1", state="busy"),
            Mock(name="worker-2", state="idle")
        ]
        mock_worker_all.return_value = mock_workers
        
        # Get stats
        with patch('torematrix.ingestion.queue_manager.Connection'):
            stats = await queue_manager.get_queue_stats()
        
        # Verify stats structure
        assert "default" in stats
        assert "priority" in stats
        assert "workers" in stats
        
        # Verify worker stats
        worker_stats = stats["workers"]
        assert worker_stats["total"] == 2
        assert worker_stats["busy"] == 1
        assert worker_stats["idle"] == 1
    
    @patch('torematrix.ingestion.queue_manager.Job.fetch')
    async def test_cleanup_old_jobs(self, mock_job_fetch, queue_manager):
        """Test cleaning up old jobs."""
        # Setup old job
        old_time = datetime.utcnow() - timedelta(days=10)
        mock_old_job = Mock(spec=Job)
        mock_old_job.ended_at = old_time
        mock_old_job.delete = Mock()
        
        # Setup recent job
        recent_time = datetime.utcnow() - timedelta(hours=1)
        mock_recent_job = Mock(spec=Job)
        mock_recent_job.ended_at = recent_time
        mock_recent_job.delete = Mock()
        
        # Setup queue registries
        queue_manager._queues["default"].finished_job_registry.get_job_ids.return_value = ["old-job", "recent-job"]
        queue_manager._queues["default"].failed_job_registry.get_job_ids.return_value = []
        queue_manager._queues["priority"].finished_job_registry.get_job_ids.return_value = []
        queue_manager._queues["priority"].failed_job_registry.get_job_ids.return_value = []
        
        def job_fetch_side_effect(job_id, connection):
            if job_id == "old-job":
                return mock_old_job
            elif job_id == "recent-job":
                return mock_recent_job
        
        mock_job_fetch.side_effect = job_fetch_side_effect
        
        # Cleanup old jobs
        with patch('torematrix.ingestion.queue_manager.Connection'):
            cleaned_count = await queue_manager.cleanup_old_jobs(days=7)
        
        # Verify only old job was deleted
        assert cleaned_count == 1
        mock_old_job.delete.assert_called_once()
        mock_recent_job.delete.assert_not_called()
    
    async def test_shutdown(self, queue_manager):
        """Test graceful shutdown."""
        await queue_manager.shutdown()
        
        # Verify shutdown flag is set
        assert queue_manager._shutdown_event.is_set()
        
        # Verify Redis clients are closed
        queue_manager._redis_client.close.assert_called_once()
    
    async def test_get_job_count(self, queue_manager):
        """Test getting job count for a queue."""
        # Test default queue
        count = queue_manager.get_job_count("default")
        assert count == 0  # Mock returns 0
        
        # Test non-existent queue
        count = queue_manager.get_job_count("non-existent")
        assert count == 0
    
    async def test_is_healthy(self, queue_manager):
        """Test health check."""
        # Test healthy state
        assert queue_manager.is_healthy() is True
        queue_manager._sync_redis_client.ping.assert_called_once()
        
        # Test unhealthy state (no Redis client)
        queue_manager._sync_redis_client = None
        assert queue_manager.is_healthy() is False


class TestRetryPolicy:
    """Test cases for RetryPolicy."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(
            backoff_type="exponential",
            initial_delay=60,
            max_delay=3600,
            jitter=False
        )
        
        assert policy.get_delay(1) == 60
        assert policy.get_delay(2) == 120
        assert policy.get_delay(3) == 240
        assert policy.get_delay(4) == 480
    
    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        policy = RetryPolicy(
            backoff_type="linear",
            initial_delay=60,
            max_delay=3600,
            jitter=False
        )
        
        assert policy.get_delay(1) == 60
        assert policy.get_delay(2) == 120
        assert policy.get_delay(3) == 180
        assert policy.get_delay(4) == 240
    
    def test_fixed_backoff(self):
        """Test fixed backoff calculation."""
        policy = RetryPolicy(
            backoff_type="fixed",
            initial_delay=60,
            max_delay=3600,
            jitter=False
        )
        
        assert policy.get_delay(1) == 60
        assert policy.get_delay(2) == 60
        assert policy.get_delay(3) == 60
        assert policy.get_delay(4) == 60
    
    def test_max_delay_limit(self):
        """Test maximum delay limit is enforced."""
        policy = RetryPolicy(
            backoff_type="exponential",
            initial_delay=60,
            max_delay=300,
            jitter=False
        )
        
        # Should be capped at max_delay
        assert policy.get_delay(10) == 300
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        policy = RetryPolicy(max_attempts=3)
        
        # Should retry within limits
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False  # At max
        assert policy.should_retry(4) is False  # Exceeded max
        
        # Should not retry certain error types
        assert policy.should_retry(1, "validation_error") is False
        assert policy.should_retry(1, "format_not_supported") is False
        assert policy.should_retry(1, "permission_denied") is False
        
        # Should retry other error types
        assert policy.should_retry(1, "network_error") is True
        assert policy.should_retry(1, "timeout_error") is True