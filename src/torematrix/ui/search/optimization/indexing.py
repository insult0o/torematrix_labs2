"""Background Indexing Optimization

Non-blocking background indexing for large datasets with intelligent
batching, progress tracking, and performance monitoring to ensure
UI responsiveness during heavy indexing operations.
"""

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, AsyncIterator
from uuid import uuid4
import weakref

from torematrix.core.models.element import Element


logger = logging.getLogger(__name__)


class IndexingState(Enum):
    """States of indexing operations"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class IndexingPriority(Enum):
    """Priority levels for indexing tasks"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class IndexingConfig:
    """Configuration for background indexing"""
    batch_size: int = 100
    max_queue_size: int = 10000
    max_concurrent_batches: int = 2
    indexing_delay_ms: int = 10  # Delay between batches to avoid blocking UI
    memory_limit_mb: int = 200
    progress_update_interval: int = 50  # Update progress every N elements
    enable_incremental_indexing: bool = True
    enable_priority_queue: bool = True
    auto_optimize_index: bool = True
    checkpoint_interval: int = 1000  # Save progress every N elements


@dataclass
class IndexingTask:
    """Individual indexing task"""
    task_id: str
    elements: List[Element]
    priority: IndexingPriority = IndexingPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if task is completed"""
        return self.completed_at is not None
    
    @property
    def execution_time(self) -> Optional[timedelta]:
        """Get execution time if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class IndexingProgress:
    """Progress tracking for indexing operations"""
    total_elements: int = 0
    processed_elements: int = 0
    failed_elements: int = 0
    current_batch: int = 0
    total_batches: int = 0
    elements_per_second: float = 0.0
    estimated_completion: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_elements == 0:
            return 0.0
        return (self.processed_elements / self.total_elements) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total_processed = self.processed_elements + self.failed_elements
        if total_processed == 0:
            return 100.0
        return (self.processed_elements / total_processed) * 100.0


@dataclass
class IndexingResult:
    """Result of an indexing operation"""
    task_id: str
    success: bool
    processed_count: int
    failed_count: int
    execution_time: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class IndexingStatistics:
    """Statistics for indexing performance"""
    total_tasks_completed: int = 0
    total_elements_processed: int = 0
    total_elements_failed: int = 0
    average_elements_per_second: float = 0.0
    average_batch_time: float = 0.0
    total_indexing_time: float = 0.0
    peak_memory_usage_mb: float = 0.0
    index_size_mb: float = 0.0
    
    def update_from_result(self, result: IndexingResult) -> None:
        """Update statistics from indexing result"""
        self.total_tasks_completed += 1
        self.total_elements_processed += result.processed_count
        self.total_elements_failed += result.failed_count
        self.total_indexing_time += result.execution_time
        
        # Recalculate averages
        if self.total_tasks_completed > 0:
            self.average_batch_time = self.total_indexing_time / self.total_tasks_completed
        
        if result.execution_time > 0:
            elements_per_second = result.processed_count / result.execution_time
            if self.average_elements_per_second == 0:
                self.average_elements_per_second = elements_per_second
            else:
                # Exponential moving average
                self.average_elements_per_second = (
                    0.8 * self.average_elements_per_second + 0.2 * elements_per_second
                )


class BackgroundIndexer:
    """Non-blocking background indexing for large datasets"""
    
    def __init__(self, 
                 search_indexer,
                 config: Optional[IndexingConfig] = None):
        """Initialize background indexer
        
        Args:
            search_indexer: The search indexer to use for actual indexing
            config: Indexing configuration
        """
        self.search_indexer = search_indexer
        self.config = config or IndexingConfig()
        
        # State management
        self.state = IndexingState.IDLE
        self.state_lock = threading.RLock()
        
        # Task queues
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self.priority_queues: Dict[IndexingPriority, deque] = {
            priority: deque() for priority in IndexingPriority
        }
        
        # Progress tracking
        self.progress = IndexingProgress()
        self.statistics = IndexingStatistics()
        self.progress_callbacks: List[Callable[[IndexingProgress], None]] = []
        
        # Worker management
        self.worker_tasks: Set[asyncio.Task] = set()
        self.is_running = False
        self.should_stop = False
        
        # Performance monitoring
        self.performance_monitor_task: Optional[asyncio.Task] = None
        self.last_progress_update = time.time()
        self.processed_since_update = 0
        
        # Checkpointing
        self.last_checkpoint = time.time()
        self.checkpoint_data: Dict[str, Any] = {}
        
        logger.info(f"BackgroundIndexer initialized with batch_size={self.config.batch_size}")
    
    async def start(self) -> None:
        """Start background indexing workers"""
        with self.state_lock:
            if self.is_running:
                logger.warning("BackgroundIndexer is already running")
                return
            
            self.is_running = True
            self.should_stop = False
            self.state = IndexingState.RUNNING
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_batches):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.worker_tasks.add(worker_task)
        
        # Start performance monitoring
        self.performance_monitor_task = asyncio.create_task(self._performance_monitor_loop())
        
        logger.info(f"Started {len(self.worker_tasks)} indexing workers")
    
    async def stop(self) -> None:
        """Stop background indexing gracefully"""
        with self.state_lock:
            if not self.is_running:
                return
            
            self.should_stop = True
            self.state = IndexingState.STOPPING
        
        logger.info("Stopping background indexing...")
        
        # Wait for workers to finish current tasks
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            self.worker_tasks.clear()
        
        # Stop performance monitoring
        if self.performance_monitor_task:
            self.performance_monitor_task.cancel()
            try:
                await self.performance_monitor_task
            except asyncio.CancelledError:
                pass
        
        with self.state_lock:
            self.is_running = False
            self.state = IndexingState.IDLE
        
        logger.info("Background indexing stopped")
    
    async def queue_for_indexing(self, 
                                elements: List[Element],
                                priority: IndexingPriority = IndexingPriority.NORMAL,
                                metadata: Optional[Dict[str, Any]] = None) -> str:
        """Queue elements for background indexing
        
        Args:
            elements: Elements to index
            priority: Indexing priority
            metadata: Additional metadata
            
        Returns:
            Task ID for tracking
            
        Raises:
            RuntimeError: If indexer is not running
        """
        if not self.is_running:
            raise RuntimeError("BackgroundIndexer is not running")
        
        # Create indexing task
        task = IndexingTask(
            task_id=str(uuid4()),
            elements=elements,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Queue task based on priority
        if self.config.enable_priority_queue:
            self.priority_queues[priority].append(task)
        else:
            # Add to regular queue
            try:
                await self.task_queue.put(task)
            except asyncio.QueueFull:
                logger.warning(f"Task queue full, dropping task {task.task_id}")
                raise RuntimeError("Indexing queue is full")
        
        # Update progress tracking
        self.progress.total_elements += len(elements)
        self.progress.total_batches = (
            self.progress.total_elements // self.config.batch_size + 1
        )
        
        logger.debug(f"Queued {len(elements)} elements for indexing (task: {task.task_id})")
        
        return task.task_id
    
    async def queue_elements_batch(self, 
                                  elements: List[Element],
                                  batch_size: Optional[int] = None) -> List[str]:
        """Queue elements in optimized batches
        
        Args:
            elements: Elements to index
            batch_size: Custom batch size (uses config default if None)
            
        Returns:
            List of task IDs
        """
        batch_size = batch_size or self.config.batch_size
        task_ids = []
        
        # Split elements into batches
        for i in range(0, len(elements), batch_size):
            batch = elements[i:i + batch_size]
            task_id = await self.queue_for_indexing(batch)
            task_ids.append(task_id)
        
        logger.info(f"Queued {len(elements)} elements in {len(task_ids)} batches")
        
        return task_ids
    
    def get_indexing_progress(self) -> IndexingProgress:
        """Get current indexing progress
        
        Returns:
            Current IndexingProgress
        """
        # Update elements per second calculation
        current_time = time.time()
        time_delta = current_time - self.last_progress_update
        
        if time_delta > 0:
            self.progress.elements_per_second = self.processed_since_update / time_delta
            
            # Estimate completion time
            remaining_elements = self.progress.total_elements - self.progress.processed_elements
            if self.progress.elements_per_second > 0:
                remaining_seconds = remaining_elements / self.progress.elements_per_second
                self.progress.estimated_completion = (
                    datetime.now() + timedelta(seconds=remaining_seconds)
                )
        
        self.progress.last_updated = datetime.now()
        return self.progress
    
    def get_statistics(self) -> IndexingStatistics:
        """Get indexing statistics
        
        Returns:
            Current IndexingStatistics
        """
        return self.statistics
    
    def add_progress_callback(self, callback: Callable[[IndexingProgress], None]) -> None:
        """Add progress update callback
        
        Args:
            callback: Function to call with progress updates
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[IndexingProgress], None]) -> None:
        """Remove progress update callback
        
        Args:
            callback: Function to remove
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    async def pause(self) -> None:
        """Pause indexing operations"""
        with self.state_lock:
            if self.state == IndexingState.RUNNING:
                self.state = IndexingState.PAUSED
                logger.info("Background indexing paused")
    
    async def resume(self) -> None:
        """Resume indexing operations"""
        with self.state_lock:
            if self.state == IndexingState.PAUSED:
                self.state = IndexingState.RUNNING
                logger.info("Background indexing resumed")
    
    def is_idle(self) -> bool:
        """Check if indexer is idle (no pending tasks)
        
        Returns:
            True if idle, False otherwise
        """
        return (self.task_queue.empty() and 
                all(len(q) == 0 for q in self.priority_queues.values()))
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all queued tasks to complete
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if completed, False if timed out
        """
        start_time = time.time()
        
        while not self.is_idle():
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            await asyncio.sleep(0.1)
        
        return True
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop for processing indexing tasks
        
        Args:
            worker_id: Identifier for this worker
        """
        logger.debug(f"Worker {worker_id} started")
        
        while not self.should_stop:
            try:
                # Wait for task (with timeout to check stop condition)
                task = await self._get_next_task(timeout=1.0)
                
                if task is None:
                    continue  # Timeout, check stop condition again
                
                # Skip if paused
                if self.state == IndexingState.PAUSED:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process task
                result = await self._process_indexing_task(task, worker_id)
                
                # Update statistics
                self.statistics.update_from_result(result)
                
                # Update progress
                await self._update_progress(result)
                
                # Add delay to avoid blocking UI
                if self.config.indexing_delay_ms > 0:
                    await asyncio.sleep(self.config.indexing_delay_ms / 1000.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
                with self.state_lock:
                    self.state = IndexingState.ERROR
        
        logger.debug(f"Worker {worker_id} stopped")
    
    async def _get_next_task(self, timeout: float = 1.0) -> Optional[IndexingTask]:
        """Get next task from queue with priority support
        
        Args:
            timeout: Timeout for waiting for task
            
        Returns:
            Next IndexingTask or None if timeout
        """
        if self.config.enable_priority_queue:
            # Check priority queues first (highest priority first)
            for priority in reversed(list(IndexingPriority)):
                if self.priority_queues[priority]:
                    return self.priority_queues[priority].popleft()
        
        # Get from regular queue
        try:
            return await asyncio.wait_for(self.task_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    async def _process_indexing_task(self, task: IndexingTask, worker_id: str) -> IndexingResult:
        """Process a single indexing task
        
        Args:
            task: Task to process
            worker_id: ID of processing worker
            
        Returns:
            IndexingResult with processing details
        """
        task.started_at = datetime.now()
        start_time = time.time()
        
        result = IndexingResult(
            task_id=task.task_id,
            success=False,
            processed_count=0,
            failed_count=0,
            execution_time=0.0
        )
        
        try:
            logger.debug(f"Worker {worker_id} processing task {task.task_id} "
                        f"({len(task.elements)} elements)")
            
            # Process elements in smaller batches to avoid blocking
            batch_size = min(self.config.batch_size, len(task.elements))
            
            for i in range(0, len(task.elements), batch_size):
                batch = task.elements[i:i + batch_size]
                
                try:
                    # Index this batch
                    await self.search_indexer.index_elements(batch)
                    result.processed_count += len(batch)
                    
                    # Check if we should stop
                    if self.should_stop:
                        break
                    
                    # Brief pause between batches
                    await asyncio.sleep(0.001)
                    
                except Exception as e:
                    logger.error(f"Error indexing batch in task {task.task_id}: {e}")
                    result.failed_count += len(batch)
                    result.errors.append(f"Batch {i//batch_size}: {str(e)}")
            
            result.success = result.failed_count == 0
            task.completed_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            result.failed_count = len(task.elements)
            result.errors.append(f"Task processing failed: {str(e)}")
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result
    
    async def _update_progress(self, result: IndexingResult) -> None:
        """Update progress tracking and notify callbacks
        
        Args:
            result: Result from completed task
        """
        # Update progress counters
        self.progress.processed_elements += result.processed_count
        self.progress.failed_elements += result.failed_count
        self.progress.current_batch += 1
        
        # Track processed elements for rate calculation
        self.processed_since_update += result.processed_count
        
        # Update progress every N elements
        if (self.progress.processed_elements % self.config.progress_update_interval == 0 or
            self.progress.processed_elements >= self.progress.total_elements):
            
            current_time = time.time()
            time_delta = current_time - self.last_progress_update
            
            if time_delta > 0:
                self.progress.elements_per_second = self.processed_since_update / time_delta
                self.processed_since_update = 0
                self.last_progress_update = current_time
            
            # Notify callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        # Checkpoint if needed
        if (time.time() - self.last_checkpoint > self.config.checkpoint_interval and 
            self.config.checkpoint_interval > 0):
            await self._create_checkpoint()
    
    async def _create_checkpoint(self) -> None:
        """Create progress checkpoint"""
        self.checkpoint_data = {
            'progress': {
                'total_elements': self.progress.total_elements,
                'processed_elements': self.progress.processed_elements,
                'failed_elements': self.progress.failed_elements,
                'current_batch': self.progress.current_batch,
                'total_batches': self.progress.total_batches
            },
            'statistics': {
                'total_tasks_completed': self.statistics.total_tasks_completed,
                'total_elements_processed': self.statistics.total_elements_processed,
                'total_elements_failed': self.statistics.total_elements_failed,
                'total_indexing_time': self.statistics.total_indexing_time
            },
            'timestamp': datetime.now().isoformat()
        }
        
        self.last_checkpoint = time.time()
        logger.debug("Created indexing checkpoint")
    
    async def _performance_monitor_loop(self) -> None:
        """Monitor performance and optimize as needed"""
        while not self.should_stop:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Monitor memory usage
                memory_usage = self._estimate_memory_usage()
                self.statistics.peak_memory_usage_mb = max(
                    self.statistics.peak_memory_usage_mb,
                    memory_usage
                )
                
                # Trigger index optimization if enabled
                if (self.config.auto_optimize_index and 
                    self.statistics.total_elements_processed > 0 and
                    self.statistics.total_elements_processed % 10000 == 0):
                    await self._optimize_index()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB
        
        Returns:
            Estimated memory usage in megabytes
        """
        # Simple estimation based on queue sizes and processed elements
        queue_memory = len(self.task_queue._queue) * 1000  # Rough estimate per task
        
        # Add priority queue memory
        for priority_queue in self.priority_queues.values():
            queue_memory += len(priority_queue) * 1000
        
        return queue_memory / (1024 * 1024)
    
    async def _optimize_index(self) -> None:
        """Optimize search index for better performance"""
        try:
            if hasattr(self.search_indexer, 'optimize'):
                await self.search_indexer.optimize()
                logger.debug("Index optimization completed")
        except Exception as e:
            logger.error(f"Error optimizing index: {e}")


# Utility functions
async def create_background_indexer(search_indexer,
                                  batch_size: int = 100,
                                  max_concurrent_batches: int = 2) -> BackgroundIndexer:
    """Create and start a background indexer
    
    Args:
        search_indexer: Search indexer instance
        batch_size: Batch size for processing
        max_concurrent_batches: Maximum concurrent batches
        
    Returns:
        Started BackgroundIndexer
    """
    config = IndexingConfig(
        batch_size=batch_size,
        max_concurrent_batches=max_concurrent_batches
    )
    
    indexer = BackgroundIndexer(search_indexer, config)
    await indexer.start()
    
    return indexer


def create_performance_indexing_config() -> IndexingConfig:
    """Create indexing configuration optimized for performance
    
    Returns:
        Performance-optimized IndexingConfig
    """
    return IndexingConfig(
        batch_size=200,  # Larger batches for efficiency
        max_concurrent_batches=4,  # More parallelism
        indexing_delay_ms=5,  # Reduced delay for speed
        memory_limit_mb=500,  # Higher memory limit
        enable_incremental_indexing=True,
        enable_priority_queue=True,
        auto_optimize_index=True,
        checkpoint_interval=2000  # Less frequent checkpoints
    )


def create_responsive_indexing_config() -> IndexingConfig:
    """Create indexing configuration optimized for UI responsiveness
    
    Returns:
        Responsiveness-optimized IndexingConfig
    """
    return IndexingConfig(
        batch_size=50,  # Smaller batches for responsiveness
        max_concurrent_batches=1,  # Minimal parallelism
        indexing_delay_ms=50,  # Longer delays for UI
        memory_limit_mb=100,  # Conservative memory usage
        enable_incremental_indexing=True,
        enable_priority_queue=True,
        auto_optimize_index=False,  # Avoid optimization during indexing
        checkpoint_interval=500  # Frequent checkpoints
    )