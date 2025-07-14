"""Worker pool implementation for concurrent document processing."""

from typing import Dict, List, Any, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
import logging
from enum import Enum
import uuid
import time

from .config import WorkerConfig, ResourceLimits, ResourceType
from .resources import ResourceMonitor
from .progress import ProgressTracker
from .exceptions import (
    WorkerPoolError, TaskError, TaskTimeoutError, 
    WorkerTimeoutError, ResourceError
)
from .utils import AsyncTimer, worker_task_wrapper, format_duration

logger = logging.getLogger(__name__)


class WorkerType(str, Enum):
    """Types of workers in the pool."""
    ASYNC = "async"
    THREAD = "thread"
    PROCESS = "process"


class WorkerStatus(str, Enum):
    """Worker status."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ProcessorPriority(int, Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class WorkerStats:
    """Statistics for a worker."""
    worker_id: str
    worker_type: WorkerType
    status: WorkerStatus
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    current_task: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average task processing time."""
        if self.tasks_completed == 0:
            return 0.0
        return self.total_processing_time / self.tasks_completed


@dataclass
class PoolStats:
    """Statistics for the entire worker pool."""
    total_workers: int
    active_workers: int
    idle_workers: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_wait_time: float
    average_processing_time: float
    resource_utilization: Dict[str, float]


@dataclass
class WorkerTask:
    """Represents a task to be executed by a worker."""
    task_id: str
    processor_name: str
    context: Any  # ProcessorContext - will be defined by Agent 2
    processor_func: Callable
    priority: ProcessorPriority
    timeout: float
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None
    
    @property
    def wait_time(self) -> Optional[float]:
        """Time task waited in queue before execution."""
        if not self.started_at:
            return None
        return (self.started_at - self.submitted_at).total_seconds()
    
    @property
    def processing_time(self) -> Optional[float]:
        """Time taken to process the task."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()


class WorkerPool:
    """
    Manages a pool of workers for concurrent document processing.
    
    Supports async, thread, and process workers with resource management.
    """
    
    def __init__(
        self,
        config: WorkerConfig,
        event_bus=None,
        resource_monitor: Optional[ResourceMonitor] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ):
        self.config = config
        self.event_bus = event_bus
        self.resource_monitor = resource_monitor
        self.progress_tracker = progress_tracker
        
        # Worker pools
        self.async_workers: List[asyncio.Task] = []
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self.process_pool: Optional[ProcessPoolExecutor] = None
        
        # Task management
        self.task_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.max_queue_size
        )
        self.priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=config.priority_queue_size
        )
        self.active_tasks: Dict[str, WorkerTask] = {}
        self.completed_tasks: List[WorkerTask] = []
        
        # Worker tracking
        self.worker_stats: Dict[str, WorkerStats] = {}
        self._worker_locks: Dict[str, asyncio.Lock] = {}
        
        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._start_time: Optional[datetime] = None
        
        # Statistics
        self._total_tasks_submitted = 0
        self._total_tasks_completed = 0
        self._total_tasks_failed = 0
    
    async def start(self):
        """Start the worker pool."""
        if self._running:
            logger.warning("Worker pool is already running")
            return
        
        self._running = True
        self._start_time = datetime.utcnow()
        logger.info(f"Starting worker pool with configuration: {self.config}")
        
        try:
            # Initialize thread pool
            if self.config.thread_workers > 0:
                self.thread_pool = ThreadPoolExecutor(
                    max_workers=self.config.thread_workers,
                    thread_name_prefix="torematrix-worker"
                )
                logger.info(f"Started {self.config.thread_workers} thread workers")
            
            # Initialize process pool
            if self.config.process_workers > 0:
                self.process_pool = ProcessPoolExecutor(
                    max_workers=self.config.process_workers,
                    mp_context=mp.get_context('spawn')
                )
                logger.info(f"Started {self.config.process_workers} process workers")
            
            # Start async workers
            for i in range(self.config.async_workers):
                worker_id = f"async-{i}"
                worker = asyncio.create_task(
                    self._async_worker(worker_id),
                    name=f"worker-{worker_id}"
                )
                self.async_workers.append(worker)
                self.worker_stats[worker_id] = WorkerStats(
                    worker_id=worker_id,
                    worker_type=WorkerType.ASYNC,
                    status=WorkerStatus.IDLE
                )
                self._worker_locks[worker_id] = asyncio.Lock()
            
            logger.info(f"Started {self.config.async_workers} async workers")
            
            # Start monitoring task
            asyncio.create_task(self._monitor_workers(), name="worker-monitor")
            
            # Emit started event
            if self.event_bus:
                from ...core.events.event_types import Event
                event = Event(
                    event_type="worker_pool_started",
                    payload={"config": self.config.dict()}
                )
                await self.event_bus.publish(event)
            
            logger.info("Worker pool started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start worker pool: {e}")
            await self.stop()
            raise WorkerPoolError(f"Failed to start worker pool: {e}")
    
    async def stop(self, timeout: float = 30.0):
        """Stop the worker pool gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping worker pool...")
        self._running = False
        self._shutdown_event.set()
        
        try:
            # Wait for active tasks to complete
            if self.active_tasks:
                logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
                await self._wait_for_active_tasks(timeout=timeout / 2)
            
            # Stop async workers
            if self.async_workers:
                logger.info("Stopping async workers...")
                for worker in self.async_workers:
                    worker.cancel()
                
                # Wait for workers to stop
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.async_workers, return_exceptions=True),
                        timeout=timeout / 2
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some async workers didn't stop gracefully")
                
                self.async_workers.clear()
            
            # Shutdown thread pool
            if self.thread_pool:
                logger.info("Shutting down thread pool...")
                self.thread_pool.shutdown(wait=True)
                self.thread_pool = None
            
            # Shutdown process pool
            if self.process_pool:
                logger.info("Shutting down process pool...")
                self.process_pool.shutdown(wait=True)
                self.process_pool = None
            
            # Emit stopped event
            if self.event_bus:
                from ...core.events.event_types import Event
                event = Event(
                    event_type="worker_pool_stopped",
                    payload={"uptime_seconds": self._get_uptime_seconds()}
                )
                await self.event_bus.publish(event)
            
            logger.info("Worker pool stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during worker pool shutdown: {e}")
    
    async def submit_task(
        self,
        processor_name: str,
        context: Any,  # ProcessorContext
        processor_func: Callable,
        priority: ProcessorPriority = ProcessorPriority.NORMAL,
        timeout: Optional[float] = None,
        required_resources: Optional[Dict[ResourceType, float]] = None
    ) -> str:
        """
        Submit a task to the worker pool.
        
        Returns task ID for tracking.
        """
        if not self._running:
            raise WorkerPoolError("Worker pool is not running")
        
        task_id = str(uuid.uuid4())
        
        # Check resource availability
        if required_resources and self.resource_monitor:
            available, reason = await self.resource_monitor.check_availability(
                required_resources
            )
            if not available:
                raise ResourceError(f"Insufficient resources for task: {reason}")
        
        # Create task
        task = WorkerTask(
            task_id=task_id,
            processor_name=processor_name,
            context=context,
            processor_func=processor_func,
            priority=priority,
            timeout=timeout or self.config.default_timeout,
            submitted_at=datetime.utcnow()
        )
        
        # Allocate resources if specified
        if required_resources and self.resource_monitor:
            allocated = await self.resource_monitor.allocate(task_id, required_resources)
            if not allocated:
                raise ResourceError(f"Failed to allocate resources for task {task_id}")
        
        # Add to appropriate queue
        try:
            if priority == ProcessorPriority.CRITICAL:
                await asyncio.wait_for(
                    self.priority_queue.put((priority.value, task)),
                    timeout=1.0
                )
            else:
                await asyncio.wait_for(
                    self.task_queue.put(task),
                    timeout=1.0
                )
        except asyncio.TimeoutError:
            # Release allocated resources
            if required_resources and self.resource_monitor:
                await self.resource_monitor.release(task_id)
            raise WorkerPoolError("Task queue is full, cannot submit task")
        
        self.active_tasks[task_id] = task
        self._total_tasks_submitted += 1
        
        # Start progress tracking
        if self.progress_tracker:
            await self.progress_tracker.start_task(
                task_id=task_id,
                processor_name=processor_name,
                document_id=getattr(context, 'document_id', 'unknown')
            )
        
        # Emit event
        if self.event_bus:
            from ...core.events.event_types import Event
            event = Event(
                event_type="task_submitted",
                payload={
                    "task_id": task_id,
                    "processor": processor_name,
                    "priority": priority.value
                }
            )
            await self.event_bus.publish(event)
        
        logger.debug(f"Submitted task {task_id} for processor {processor_name}")
        return task_id
    
    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get the result of a completed task."""
        if task_id not in self.active_tasks:
            # Check completed tasks
            for task in self.completed_tasks:
                if task.task_id == task_id:
                    if task.error:
                        raise TaskError(f"Task failed: {task.error}", task_id=task_id)
                    return task.result
            raise TaskError(f"Task {task_id} not found")
        
        # Wait for task to complete
        start_time = time.time()
        while task_id in self.active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                raise TaskTimeoutError(task_id, timeout)
            await asyncio.sleep(0.1)
        
        # Task should now be in completed tasks
        for task in self.completed_tasks:
            if task.task_id == task_id:
                if task.error:
                    raise TaskError(f"Task failed: {task.error}", task_id=task_id)
                return task.result
        
        raise TaskError(f"Task {task_id} completed but result not found")
    
    def get_pool_stats(self) -> PoolStats:
        """Get current pool statistics."""
        active_workers = sum(
            1 for stats in self.worker_stats.values()
            if stats.status == WorkerStatus.BUSY
        )
        idle_workers = sum(
            1 for stats in self.worker_stats.values()
            if stats.status == WorkerStatus.IDLE
        )
        
        # Calculate average times
        if self.completed_tasks:
            wait_times = [t.wait_time for t in self.completed_tasks if t.wait_time is not None]
            processing_times = [t.processing_time for t in self.completed_tasks if t.processing_time is not None]
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        else:
            avg_wait_time = 0.0
            avg_processing_time = 0.0
        
        # Resource utilization
        resource_utilization = {}
        if self.resource_monitor:
            current_usage = self.resource_monitor.get_current_usage()
            resource_utilization = {
                resource_type.value: usage
                for resource_type, usage in current_usage.items()
            }
        
        return PoolStats(
            total_workers=len(self.worker_stats),
            active_workers=active_workers,
            idle_workers=idle_workers,
            queued_tasks=self.task_queue.qsize() + self.priority_queue.qsize(),
            completed_tasks=self._total_tasks_completed,
            failed_tasks=self._total_tasks_failed,
            average_wait_time=avg_wait_time,
            average_processing_time=avg_processing_time,
            resource_utilization=resource_utilization
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics in dictionary format for compatibility."""
        pool_stats = self.get_pool_stats()
        return {
            "total_workers": pool_stats.total_workers,
            "active_workers": pool_stats.active_workers,
            "idle_workers": pool_stats.idle_workers,
            "queued_tasks": pool_stats.queued_tasks,
            "completed_tasks": pool_stats.completed_tasks,
            "failed_tasks": pool_stats.failed_tasks,
            "average_wait_time": pool_stats.average_wait_time,
            "average_processing_time": pool_stats.average_processing_time,
            "resource_utilization": pool_stats.resource_utilization
        }
    
    async def wait_for_completion(self, timeout: float = 60.0) -> bool:
        """
        Wait for all active tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed, False if timeout occurred
        """
        logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
        
        start_time = time.time()
        while self.active_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.5)
        
        completed = len(self.active_tasks) == 0
        if completed:
            logger.info("All active tasks completed successfully")
        else:
            logger.warning(f"{len(self.active_tasks)} tasks still active after {timeout}s timeout")
        
        return completed
    
    async def _async_worker(self, worker_id: str):
        """Async worker process."""
        logger.info(f"Starting async worker: {worker_id}")
        
        while self._running:
            task = None
            try:
                # Update status
                await self._update_worker_status(worker_id, WorkerStatus.IDLE)
                
                # Try priority queue first
                try:
                    _, task = await asyncio.wait_for(
                        self.priority_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    # Try regular queue
                    try:
                        task = await asyncio.wait_for(
                            self.task_queue.get(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue
                
                if task:
                    await self._process_task(worker_id, task)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                if task:
                    await self._handle_task_failure(task, e)
        
        await self._update_worker_status(worker_id, WorkerStatus.STOPPED)
        logger.info(f"Stopping async worker: {worker_id}")
    
    async def _process_task(self, worker_id: str, task: WorkerTask):
        """Process a single task."""
        task.started_at = datetime.utcnow()
        task.worker_id = worker_id
        
        # Update worker status
        await self._update_worker_status(worker_id, WorkerStatus.BUSY, task.task_id)
        
        logger.debug(f"Worker {worker_id} processing task {task.task_id}")
        
        async with AsyncTimer() as timer:
            try:
                # Execute the processor function
                result = await asyncio.wait_for(
                    self._execute_processor(task),
                    timeout=task.timeout
                )
                
                # Task completed successfully
                task.result = result
                task.completed_at = datetime.utcnow()
                await self._handle_task_completion(task, True)
                
                logger.debug(
                    f"Worker {worker_id} completed task {task.task_id} "
                    f"in {format_duration(timer.elapsed)}"
                )
                
            except asyncio.TimeoutError:
                error = f"Task timed out after {task.timeout}s"
                await self._handle_task_failure(task, TaskTimeoutError(task.task_id, task.timeout))
                logger.warning(f"Worker {worker_id} task {task.task_id} {error}")
                
            except Exception as e:
                await self._handle_task_failure(task, e)
                logger.error(f"Worker {worker_id} task {task.task_id} failed: {e}")
    
    async def _execute_processor(self, task: WorkerTask) -> Any:
        """Execute the processor function for a task."""
        # Update progress
        if self.progress_tracker:
            await self.progress_tracker.update_task(
                task.task_id, 0.1, "Starting processor execution"
            )
        
        # Execute processor
        if asyncio.iscoroutinefunction(task.processor_func):
            result = await task.processor_func(task.context)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool, task.processor_func, task.context
            )
        
        # Update progress
        if self.progress_tracker:
            await self.progress_tracker.update_task(
                task.task_id, 1.0, "Processor execution completed"
            )
        
        return result
    
    async def _handle_task_completion(self, task: WorkerTask, success: bool):
        """Handle task completion."""
        # Update statistics
        if task.worker_id in self.worker_stats:
            stats = self.worker_stats[task.worker_id]
            if success:
                stats.tasks_completed += 1
                self._total_tasks_completed += 1
            else:
                stats.tasks_failed += 1
                self._total_tasks_failed += 1
            
            if task.processing_time:
                stats.total_processing_time += task.processing_time
        
        # Complete progress tracking
        if self.progress_tracker:
            await self.progress_tracker.complete_task(
                task.task_id, success, task.error
            )
        
        # Release resources
        if self.resource_monitor:
            await self.resource_monitor.release(task.task_id)
        
        # Move task to completed
        self.active_tasks.pop(task.task_id, None)
        self.completed_tasks.append(task)
        
        # Limit completed tasks history
        if len(self.completed_tasks) > 1000:
            self.completed_tasks = self.completed_tasks[-500:]
        
        # Emit completion event
        if self.event_bus:
            from ...core.events.event_types import Event
            event = Event(
                event_type="task_completed" if success else "task_failed",
                payload={
                    "task_id": task.task_id,
                    "processor": task.processor_name,
                    "duration": task.processing_time,
                    "error": task.error if not success else None
                }
            )
            await self.event_bus.publish(event)
    
    async def _handle_task_failure(self, task: WorkerTask, error: Exception):
        """Handle task failure."""
        task.error = str(error)
        task.completed_at = datetime.utcnow()
        await self._handle_task_completion(task, False)
    
    async def _update_worker_status(
        self, 
        worker_id: str, 
        status: WorkerStatus, 
        current_task: Optional[str] = None
    ):
        """Update worker status."""
        if worker_id in self.worker_stats:
            async with self._worker_locks.get(worker_id, asyncio.Lock()):
                stats = self.worker_stats[worker_id]
                stats.status = status
                stats.current_task = current_task
                stats.last_heartbeat = datetime.utcnow()
    
    async def _monitor_workers(self):
        """Monitor worker health and emit heartbeat events."""
        while self._running:
            try:
                # Check for stale workers
                now = datetime.utcnow()
                stale_threshold = timedelta(seconds=self.config.worker_heartbeat_interval * 3)
                
                for worker_id, stats in self.worker_stats.items():
                    if now - stats.last_heartbeat > stale_threshold:
                        logger.warning(f"Worker {worker_id} appears stale")
                        await self._update_worker_status(worker_id, WorkerStatus.ERROR)
                
                # Emit heartbeat
                if self.event_bus:
                    from ...core.events.event_types import Event
                    event = Event(
                        event_type="worker_pool_heartbeat",
                        payload={
                            "stats": self.get_pool_stats().__dict__,
                            "worker_stats": {
                                worker_id: {
                                    "status": stats.status.value,
                                    "tasks_completed": stats.tasks_completed,
                                    "tasks_failed": stats.tasks_failed,
                                    "current_task": stats.current_task
                                }
                                for worker_id, stats in self.worker_stats.items()
                            }
                        }
                    )
                    await self.event_bus.publish(event)
                
                await asyncio.sleep(self.config.worker_heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Worker monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _wait_for_active_tasks(self, timeout: float):
        """Wait for active tasks to complete."""
        start_time = time.time()
        while self.active_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.5)
        
        if self.active_tasks:
            logger.warning(f"{len(self.active_tasks)} tasks still active after timeout")
    
    def _get_uptime_seconds(self) -> float:
        """Get worker pool uptime in seconds."""
        if not self._start_time:
            return 0.0
        return (datetime.utcnow() - self._start_time).total_seconds()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get worker pool statistics in dictionary format for integration compatibility.
        
        This method provides the same data as get_pool_stats() but in a dictionary
        format that's expected by the ProcessingSystem integration layer.
        """
        pool_stats = self.get_pool_stats()
        return {
            "total_workers": pool_stats.total_workers,
            "active_workers": pool_stats.active_workers,
            "idle_workers": pool_stats.idle_workers,
            "queued_tasks": pool_stats.queued_tasks,
            "completed_tasks": pool_stats.completed_tasks,
            "failed_tasks": pool_stats.failed_tasks,
            "average_wait_time": pool_stats.average_wait_time,
            "average_processing_time": pool_stats.average_processing_time,
            "resource_utilization": pool_stats.resource_utilization,
            "uptime_seconds": self._get_uptime_seconds(),
            "total_tasks_submitted": self._total_tasks_submitted
        }
    
    async def wait_for_completion(self, timeout: float = 60.0) -> bool:
        """
        Wait for all active tasks to complete.
        
        This method is used during system shutdown to ensure all active tasks
        complete before stopping the worker pool.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed within timeout, False otherwise
        """
        start_time = time.time()
        
        while self.active_tasks and (time.time() - start_time) < timeout:
            # Check every 100ms
            await asyncio.sleep(0.1)
        
        # Return True if no active tasks remain
        return len(self.active_tasks) == 0
    
    def __str__(self) -> str:
        """String representation of worker pool."""
        stats = self.get_pool_stats()
        return (
            f"WorkerPool("
            f"total_workers={stats.total_workers}, "
            f"active={stats.active_workers}, "
            f"queued={stats.queued_tasks}, "
            f"completed={stats.completed_tasks}"
            f")"
        )