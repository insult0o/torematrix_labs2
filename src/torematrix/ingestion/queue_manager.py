"""
Queue manager for document processing pipeline.

This module provides Redis/RQ-based queue management with job tracking,
retry mechanisms, and batch processing capabilities.
"""

import asyncio
import logging
import pickle
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json

import redis.asyncio as redis
from rq import Queue, Job, Worker, Connection
from rq.job import JobStatus
from rq.exceptions import NoSuchJobError

from .queue_config import QueueConfig, RetryPolicy
from .models import FileMetadata, FileStatus
from ..core.events import EventBus, ProcessingEvent, ProcessingEventTypes

logger = logging.getLogger(__name__)


@dataclass
class JobInfo:
    """Information about a queued job."""
    job_id: str
    file_id: str
    queue_name: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    progress: float = 0.0
    current_step: str = "queued"


@dataclass
class QueueStats:
    """Statistics for queue monitoring."""
    queue_name: str
    size: int
    jobs_queued: int
    jobs_started: int
    jobs_finished: int
    jobs_failed: int
    jobs_deferred: int
    average_processing_time: float
    failed_job_rate: float


class QueueManager:
    """Manages document processing queues with Redis/RQ."""
    
    def __init__(
        self,
        config: QueueConfig,
        event_bus: Optional[EventBus] = None
    ):
        self.config = config
        self.event_bus = event_bus or EventBus()
        self._redis_client: Optional[redis.Redis] = None
        self._sync_redis_client: Optional[redis.Redis] = None
        self._queues: Dict[str, Queue] = {}
        self._jobs: Dict[str, JobInfo] = {}
        self._retry_policies: Dict[str, RetryPolicy] = {}
        self._workers: Dict[str, Worker] = {}
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize Redis connection and queues."""
        try:
            # Async Redis client for monitoring
            self._redis_client = await redis.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_max_connections,
                socket_timeout=self.config.redis_socket_timeout,
                decode_responses=True
            )
            
            # Sync Redis client for RQ
            import redis as sync_redis
            self._sync_redis_client = sync_redis.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_connection_pool_size,
                socket_timeout=self.config.redis_socket_timeout,
                decode_responses=True
            )
            
            # Test connection
            await self._redis_client.ping()
            
            # Create queues
            with Connection(self._sync_redis_client):
                self._queues["default"] = Queue(
                    self.config.default_queue_name,
                    connection=self._sync_redis_client
                )
                self._queues["priority"] = Queue(
                    self.config.priority_queue_name,
                    connection=self._sync_redis_client
                )
                self._queues["failed"] = Queue(
                    self.config.failed_queue_name,
                    connection=self._sync_redis_client,
                    is_async=False
                )
            
            logger.info("Queue manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize queue manager: {e}")
            raise
    
    async def enqueue_file(
        self,
        file_metadata: FileMetadata,
        priority: bool = False,
        retry_policy: Optional[RetryPolicy] = None,
        delay: Optional[timedelta] = None
    ) -> str:
        """
        Enqueue a file for processing.
        
        Args:
            file_metadata: File metadata to process
            priority: Whether to use priority queue
            retry_policy: Custom retry policy for this job
            delay: Optional delay before processing
            
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        queue_name = "priority" if priority else "default"
        queue = self._queues[queue_name]
        
        # Prepare job data
        job_data = {
            "file_id": file_metadata.file_id,
            "file_path": file_metadata.storage_key,
            "metadata": file_metadata.dict()
        }
        
        try:
            with Connection(self._sync_redis_client):
                # Enqueue job with optional delay
                if delay:
                    job = queue.enqueue_in(
                        delay,
                        "torematrix.ingestion.processors.process_document",
                        args=(job_data,),
                        job_id=job_id,
                        timeout=self.config.job_timeout,
                        result_ttl=self.config.result_ttl,
                        failure_ttl=self.config.failure_ttl,
                        meta={
                            "file_id": file_metadata.file_id,
                            "retry_count": 0,
                            "enqueued_at": datetime.utcnow().isoformat(),
                            "priority": priority
                        }
                    )
                else:
                    job = queue.enqueue(
                        "torematrix.ingestion.processors.process_document",
                        args=(job_data,),
                        job_id=job_id,
                        timeout=self.config.job_timeout,
                        result_ttl=self.config.result_ttl,
                        failure_ttl=self.config.failure_ttl,
                        meta={
                            "file_id": file_metadata.file_id,
                            "retry_count": 0,
                            "enqueued_at": datetime.utcnow().isoformat(),
                            "priority": priority
                        }
                    )
            
            # Track job locally
            job_info = JobInfo(
                job_id=job_id,
                file_id=file_metadata.file_id,
                queue_name=queue_name,
                status=job.get_status(),
                created_at=datetime.utcnow(),
                current_step="queued"
            )
            self._jobs[job_id] = job_info
            
            # Store retry policy if provided
            if retry_policy:
                self._retry_policies[job_id] = retry_policy
            
            # Emit event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_ENQUEUED.value,
                file_id=file_metadata.file_id,
                job_id=job_id,
                queue_name=queue_name,
                data={"queue": queue_name, "priority": priority, "delayed": delay is not None}
            ))
            
            logger.info(f"Enqueued file {file_metadata.file_id} as job {job_id} in {queue_name} queue")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue file {file_metadata.file_id}: {e}")
            raise
    
    async def enqueue_batch(
        self,
        files: List[FileMetadata],
        priority: bool = False,
        batch_id: Optional[str] = None
    ) -> List[str]:
        """
        Enqueue multiple files as a batch.
        
        Args:
            files: List of file metadata to process
            priority: Whether to use priority queue
            batch_id: Optional batch identifier
            
        Returns:
            List of job IDs
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())
            
        job_ids = []
        
        try:
            # Split into sub-batches based on config
            for i in range(0, len(files), self.config.batch_size):
                batch = files[i:i + self.config.batch_size]
                
                # Create batch job data
                batch_data = {
                    "batch_id": batch_id,
                    "files": [f.dict() for f in batch],
                    "batch_index": i // self.config.batch_size,
                    "total_batches": (len(files) + self.config.batch_size - 1) // self.config.batch_size
                }
                
                queue = self._queues["priority" if priority else "default"]
                
                with Connection(self._sync_redis_client):
                    job = queue.enqueue(
                        "torematrix.ingestion.processors.process_batch",
                        args=(batch_data,),
                        timeout=self.config.batch_timeout,
                        result_ttl=self.config.result_ttl,
                        failure_ttl=self.config.failure_ttl,
                        meta={
                            "batch_id": batch_id,
                            "file_count": len(batch),
                            "batch_index": i // self.config.batch_size
                        }
                    )
                
                job_ids.append(job.id)
            
            # Emit batch event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.BATCH_ENQUEUED.value,
                batch_id=batch_id,
                data={
                    "job_ids": job_ids,
                    "file_count": len(files),
                    "batch_count": len(job_ids),
                    "priority": priority
                }
            ))
            
            logger.info(f"Enqueued batch {batch_id} with {len(files)} files in {len(job_ids)} sub-batches")
            return job_ids
            
        except Exception as e:
            logger.error(f"Failed to enqueue batch {batch_id}: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get current status of a job."""
        try:
            job_info = self._jobs.get(job_id)
            if not job_info:
                return None
            
            # Update from Redis
            with Connection(self._sync_redis_client):
                try:
                    job = Job.fetch(job_id, connection=self._sync_redis_client)
                    
                    job_info.status = job.get_status()
                    job_info.started_at = job.started_at
                    job_info.ended_at = job.ended_at
                    
                    if job.is_finished:
                        job_info.result = job.result
                        job_info.current_step = "completed"
                    elif job.is_failed:
                        job_info.error = str(job.exc_info) if job.exc_info else "Unknown error"
                        job_info.current_step = "failed"
                    elif job.is_started:
                        job_info.current_step = "processing"
                    
                    # Update progress from job meta if available
                    if hasattr(job, 'meta') and job.meta:
                        job_info.progress = job.meta.get('progress', job_info.progress)
                        job_info.retry_count = job.meta.get('retry_count', job_info.retry_count)
                    
                except NoSuchJobError:
                    logger.warning(f"Job {job_id} not found in Redis")
                    return None
            
            return job_info
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None
    
    async def retry_failed_job(self, job_id: str) -> Optional[str]:
        """
        Retry a failed job with backoff policy.
        
        Args:
            job_id: ID of the failed job to retry
            
        Returns:
            New job ID if retried, None if not eligible for retry
        """
        job_info = self._jobs.get(job_id)
        if not job_info or job_info.status != JobStatus.FAILED:
            logger.warning(f"Job {job_id} is not eligible for retry")
            return None
        
        # Get retry policy
        retry_policy = self._retry_policies.get(job_id, RetryPolicy())
        
        if not retry_policy.should_retry(job_info.retry_count + 1):
            logger.warning(f"Job {job_id} exceeded max retries or is not retryable")
            return None
        
        try:
            with Connection(self._sync_redis_client):
                # Get original job data
                original_job = Job.fetch(job_id, connection=self._sync_redis_client)
                
                # Calculate delay
                delay = retry_policy.get_delay(job_info.retry_count + 1)
                
                # Create new job with delay
                new_job = self._queues["default"].enqueue_in(
                    timedelta(seconds=delay),
                    original_job.func_name,
                    args=original_job.args,
                    kwargs=original_job.kwargs,
                    timeout=self.config.job_timeout,
                    result_ttl=self.config.result_ttl,
                    failure_ttl=self.config.failure_ttl,
                    meta={
                        **original_job.meta,
                        "retry_count": job_info.retry_count + 1,
                        "original_job_id": job_id,
                        "retry_delay": delay
                    }
                )
            
            # Update tracking
            new_job_info = JobInfo(
                job_id=new_job.id,
                file_id=job_info.file_id,
                queue_name="default",
                status=new_job.get_status(),
                created_at=datetime.utcnow(),
                retry_count=job_info.retry_count + 1,
                current_step="queued"
            )
            self._jobs[new_job.id] = new_job_info
            
            # Transfer retry policy
            if job_id in self._retry_policies:
                self._retry_policies[new_job.id] = self._retry_policies[job_id]
            
            # Emit retry event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_RETRIED.value,
                job_id=new_job.id,
                file_id=job_info.file_id,
                retry_count=new_job_info.retry_count,
                data={
                    "original_job_id": job_id,
                    "retry_count": new_job_info.retry_count,
                    "delay": delay
                }
            ))
            
            logger.info(f"Retried job {job_id} as {new_job.id} with {delay}s delay")
            return new_job.id
            
        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        try:
            with Connection(self._sync_redis_client):
                job = Job.fetch(job_id, connection=self._sync_redis_client)
                job.cancel()
            
            # Update local tracking
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.CANCELED
                self._jobs[job_id].current_step = "cancelled"
            
            # Emit cancellation event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.JOB_CANCELLED.value,
                job_id=job_id,
                file_id=self._jobs.get(job_id, JobInfo("", "", "", JobStatus.CANCELED, datetime.utcnow())).file_id
            ))
            
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, QueueStats]:
        """Get comprehensive statistics for all queues."""
        stats = {}
        
        try:
            with Connection(self._sync_redis_client):
                for name, queue in self._queues.items():
                    # Get basic queue counts
                    jobs_queued = len(queue)
                    jobs_started = queue.started_job_registry.count
                    jobs_finished = queue.finished_job_registry.count
                    jobs_failed = queue.failed_job_registry.count
                    jobs_deferred = queue.deferred_job_registry.count
                    
                    # Calculate metrics
                    total_jobs = jobs_finished + jobs_failed
                    failed_rate = jobs_failed / total_jobs if total_jobs > 0 else 0.0
                    
                    # Calculate average processing time
                    avg_time = 0.0
                    if jobs_finished > 0:
                        # Sample recent jobs for timing
                        recent_jobs = queue.finished_job_registry.get_job_ids()[-10:]
                        times = []
                        for job_id in recent_jobs:
                            try:
                                job = Job.fetch(job_id, connection=self._sync_redis_client)
                                if job.started_at and job.ended_at:
                                    duration = (job.ended_at - job.started_at).total_seconds()
                                    times.append(duration)
                            except:
                                continue
                        
                        if times:
                            avg_time = sum(times) / len(times)
                    
                    stats[name] = QueueStats(
                        queue_name=name,
                        size=jobs_queued,
                        jobs_queued=jobs_queued,
                        jobs_started=jobs_started,
                        jobs_finished=jobs_finished,
                        jobs_failed=jobs_failed,
                        jobs_deferred=jobs_deferred,
                        average_processing_time=avg_time,
                        failed_job_rate=failed_rate
                    )
                
                # Add worker info
                workers = Worker.all(connection=self._sync_redis_client)
                worker_stats = {
                    "total": len(workers),
                    "busy": sum(1 for w in workers if w.state == "busy"),
                    "idle": sum(1 for w in workers if w.state == "idle"),
                    "workers": [
                        {
                            "name": w.name,
                            "state": w.state,
                            "current_job": w.get_current_job_id(),
                            "queues": [q.name for q in w.queues]
                        }
                        for w in workers
                    ]
                }
                stats["workers"] = worker_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Clean up old finished/failed jobs.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        cleaned = 0
        
        try:
            with Connection(self._sync_redis_client):
                for queue in self._queues.values():
                    # Clean finished jobs
                    for job_id in queue.finished_job_registry.get_job_ids():
                        try:
                            job = Job.fetch(job_id, connection=self._sync_redis_client)
                            if job.ended_at and job.ended_at.replace(tzinfo=None) < cutoff:
                                job.delete()
                                if job_id in self._jobs:
                                    del self._jobs[job_id]
                                if job_id in self._retry_policies:
                                    del self._retry_policies[job_id]
                                cleaned += 1
                        except NoSuchJobError:
                            continue
                    
                    # Clean failed jobs
                    for job_id in queue.failed_job_registry.get_job_ids():
                        try:
                            job = Job.fetch(job_id, connection=self._sync_redis_client)
                            if job.ended_at and job.ended_at.replace(tzinfo=None) < cutoff:
                                job.delete()
                                if job_id in self._jobs:
                                    del self._jobs[job_id]
                                if job_id in self._retry_policies:
                                    del self._retry_policies[job_id]
                                cleaned += 1
                        except NoSuchJobError:
                            continue
            
            logger.info(f"Cleaned up {cleaned} old jobs")
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0
    
    async def shutdown(self):
        """Gracefully shutdown the queue manager."""
        logger.info("Shutting down queue manager...")
        
        # Set shutdown flag
        self._shutdown_event.set()
        
        # Close Redis connections
        if self._redis_client:
            await self._redis_client.close()
        
        if self._sync_redis_client:
            self._sync_redis_client.close()
        
        logger.info("Queue manager shutdown complete")
    
    def get_job_count(self, queue_name: str = "default") -> int:
        """Get the number of jobs in a queue."""
        if queue_name not in self._queues:
            return 0
        return len(self._queues[queue_name])
    
    def is_healthy(self) -> bool:
        """Check if the queue manager is healthy."""
        try:
            if not self._sync_redis_client:
                return False
            
            # Test Redis connection
            self._sync_redis_client.ping()
            
            # Check if any queues are too full
            for queue in self._queues.values():
                if len(queue) > 1000:  # Configurable threshold
                    return False
            
            return True
            
        except Exception:
            return False