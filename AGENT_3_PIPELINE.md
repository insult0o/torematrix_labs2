# Agent 3 Instructions: Worker Pool & Progress Tracking

## Overview
You are Agent 3 working on Issue #8.3 (Worker Pool & Progress Tracking) as part of the Processing Pipeline Architecture. Your focus is implementing the worker pool system, resource management, and real-time progress tracking for document processing.

## Context
- Part of Issue #8: Processing Pipeline Architecture (V3 greenfield project)
- You're working alongside 3 other agents in parallel
- The worker pool manages concurrent processor execution
- Must provide real-time progress updates via EventBus

## Your Specific Tasks

### 1. Worker Pool Implementation (`src/torematrix/processing/workers/pool.py`)

```python
from typing import Dict, List, Any, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
import psutil
import logging
from enum import Enum
import uuid

from ...core.events import EventBus, Event
from ..processors.base import ProcessorContext, ProcessorResult, ProcessorPriority
from .config import WorkerConfig, ResourceLimits

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

class WorkerPool:
    """
    Manages a pool of workers for concurrent document processing.
    
    Supports async, thread, and process workers with resource management.
    """
    
    def __init__(
        self,
        config: WorkerConfig,
        event_bus: EventBus,
        resource_monitor: 'ResourceMonitor'
    ):
        self.config = config
        self.event_bus = event_bus
        self.resource_monitor = resource_monitor
        
        # Worker pools
        self.async_workers: List[asyncio.Task] = []
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self.process_pool: Optional[ProcessPoolExecutor] = None
        
        # Task management
        self.task_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.max_queue_size
        )
        self.priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, 'WorkerTask'] = {}
        
        # Worker tracking
        self.worker_stats: Dict[str, WorkerStats] = {}
        self._worker_locks: Dict[str, asyncio.Lock] = {}
        
        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the worker pool."""
        if self._running:
            return
            
        self._running = True
        logger.info(f"Starting worker pool with configuration: {self.config}")
        
        # Initialize thread pool
        if self.config.thread_workers > 0:
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.config.thread_workers,
                thread_name_prefix="torematrix-worker"
            )
        
        # Initialize process pool
        if self.config.process_workers > 0:
            self.process_pool = ProcessPoolExecutor(
                max_workers=self.config.process_workers,
                mp_context=mp.get_context('spawn')
            )
        
        # Start async workers
        for i in range(self.config.async_workers):
            worker_id = f"async-{i}"
            worker = asyncio.create_task(
                self._async_worker(worker_id)
            )
            self.async_workers.append(worker)
            self.worker_stats[worker_id] = WorkerStats(
                worker_id=worker_id,
                worker_type=WorkerType.ASYNC,
                status=WorkerStatus.IDLE
            )
        
        # Start monitoring task
        asyncio.create_task(self._monitor_workers())
        
        await self.event_bus.emit(Event(
            type="worker_pool_started",
            data={"config": self.config.dict()}
        ))
    
    async def submit_task(
        self,
        processor_name: str,
        context: ProcessorContext,
        processor_func: Callable,
        priority: ProcessorPriority = ProcessorPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> str:
        """
        Submit a task to the worker pool.
        
        Returns task ID for tracking.
        """
        task_id = str(uuid.uuid4())
        
        task = WorkerTask(
            task_id=task_id,
            processor_name=processor_name,
            context=context,
            processor_func=processor_func,
            priority=priority,
            timeout=timeout or self.config.default_timeout,
            submitted_at=datetime.utcnow()
        )
        
        # Check resource availability
        if not await self._check_resources(task):
            raise ResourceError("Insufficient resources for task")
        
        # Add to appropriate queue
        if priority == ProcessorPriority.CRITICAL:
            await self.priority_queue.put((priority.value, task))
        else:
            await self.task_queue.put(task)
        
        self.active_tasks[task_id] = task
        
        await self.event_bus.emit(Event(
            type="task_submitted",
            data={
                "task_id": task_id,
                "processor": processor_name,
                "priority": priority.value
            }
        ))
        
        return task_id
    
    async def _async_worker(self, worker_id: str):
        """Async worker process."""
        logger.info(f"Starting async worker: {worker_id}")
        
        while self._running:
            task = None
            try:
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
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                if task:
                    await self._handle_task_failure(task, e)
        
        logger.info(f"Stopping async worker: {worker_id}")
```

### 2. Progress Tracking System (`src/torematrix/processing/workers/progress.py`)

```python
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import statistics

from ...core.events import EventBus, Event

@dataclass
class TaskProgress:
    """Progress information for a single task."""
    task_id: str
    processor_name: str
    document_id: str
    status: str
    progress: float  # 0.0 to 1.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Detailed progress
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: int = 0
    
    # Performance metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task duration."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    @property
    def estimated_remaining(self) -> Optional[timedelta]:
        """Estimate remaining time based on progress."""
        if not self.started_at or self.progress <= 0:
            return None
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        if self.progress >= 1.0:
            return timedelta(seconds=0)
        
        total_estimated = elapsed / self.progress
        remaining = total_estimated - elapsed
        return timedelta(seconds=max(0, remaining))

@dataclass
class PipelineProgress:
    """Progress information for an entire pipeline."""
    pipeline_id: str
    document_id: str
    total_stages: int
    completed_stages: int = 0
    current_stage: Optional[str] = None
    overall_progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Stage details
    stage_progress: Dict[str, TaskProgress] = field(default_factory=dict)
    stage_order: List[str] = field(default_factory=list)
    
    def update_stage(self, stage_name: str, progress: TaskProgress):
        """Update progress for a specific stage."""
        self.stage_progress[stage_name] = progress
        
        # Recalculate overall progress
        if self.total_stages > 0:
            completed = sum(
                1 for p in self.stage_progress.values()
                if p.status == "completed"
            )
            in_progress = sum(
                p.progress for p in self.stage_progress.values()
                if p.status == "processing"
            )
            self.overall_progress = (completed + in_progress) / self.total_stages
            self.completed_stages = completed
    
    @property
    def estimated_completion(self) -> Optional[datetime]:
        """Estimate pipeline completion time."""
        if not self.started_at or self.overall_progress <= 0:
            return None
        
        if self.overall_progress >= 1.0:
            return self.completed_at or datetime.utcnow()
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        total_estimated = elapsed / self.overall_progress
        return self.started_at + timedelta(seconds=total_estimated)

class ProgressTracker:
    """
    Tracks and reports progress for all processing tasks.
    
    Provides real-time updates via EventBus and aggregated statistics.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
        # Progress tracking
        self.task_progress: Dict[str, TaskProgress] = {}
        self.pipeline_progress: Dict[str, PipelineProgress] = {}
        
        # Statistics
        self.task_stats: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        
        # Subscribe to worker events
        asyncio.create_task(self._subscribe_to_events())
    
    async def start_task(
        self,
        task_id: str,
        processor_name: str,
        document_id: str,
        total_steps: Optional[int] = None
    ):
        """Record task start."""
        async with self._lock:
            progress = TaskProgress(
                task_id=task_id,
                processor_name=processor_name,
                document_id=document_id,
                status="processing",
                progress=0.0,
                started_at=datetime.utcnow(),
                total_steps=total_steps
            )
            self.task_progress[task_id] = progress
        
        await self._emit_progress_update(task_id, progress)
    
    async def update_task(
        self,
        task_id: str,
        progress: float,
        message: str = "",
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None
    ):
        """Update task progress."""
        async with self._lock:
            if task_id not in self.task_progress:
                return
            
            task = self.task_progress[task_id]
            task.progress = max(0.0, min(1.0, progress))
            if message:
                task.message = message
            if current_step is not None:
                task.current_step = current_step
            if completed_steps is not None:
                task.completed_steps = completed_steps
            if cpu_usage is not None:
                task.cpu_usage = cpu_usage
            if memory_usage is not None:
                task.memory_usage = memory_usage
        
        await self._emit_progress_update(task_id, task)
    
    async def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Mark task as completed."""
        async with self._lock:
            if task_id not in self.task_progress:
                return
            
            task = self.task_progress[task_id]
            task.status = "completed" if success else "failed"
            task.progress = 1.0 if success else task.progress
            task.completed_at = datetime.utcnow()
            task.error = error
            
            # Update statistics
            if task.duration:
                duration_seconds = task.duration.total_seconds()
                self.task_stats[task.processor_name].append(duration_seconds)
        
        await self._emit_progress_update(task_id, task)
    
    async def _emit_progress_update(self, task_id: str, progress: TaskProgress):
        """Emit progress update event."""
        await self.event_bus.emit(Event(
            type="task_progress",
            data={
                "task_id": task_id,
                "progress": progress.dict()
            }
        ))
    
    def get_statistics(self, processor_name: Optional[str] = None) -> Dict[str, Any]:
        """Get processing statistics."""
        if processor_name:
            durations = self.task_stats.get(processor_name, [])
            if not durations:
                return {}
            
            return {
                "processor": processor_name,
                "total_tasks": len(durations),
                "average_duration": statistics.mean(durations),
                "median_duration": statistics.median(durations),
                "min_duration": min(durations),
                "max_duration": max(durations)
            }
        
        # Overall statistics
        all_durations = []
        for durations in self.task_stats.values():
            all_durations.extend(durations)
        
        if not all_durations:
            return {"total_tasks": 0}
        
        return {
            "total_tasks": len(all_durations),
            "processors": len(self.task_stats),
            "average_duration": statistics.mean(all_durations),
            "median_duration": statistics.median(all_durations),
            "min_duration": min(all_durations),
            "max_duration": max(all_durations)
        }
```

### 3. Resource Management (`src/torematrix/processing/workers/resources.py`)

```python
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import asyncio
import psutil
import logging
from datetime import datetime, timedelta

from .config import ResourceLimits, ResourceType

logger = logging.getLogger(__name__)

@dataclass
class ResourceSnapshot:
    """Point-in-time resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    active_tasks: int
    queued_tasks: int

class ResourceMonitor:
    """
    Monitors system resources and enforces limits.
    
    Provides resource allocation and throttling for the worker pool.
    """
    
    def __init__(
        self,
        limits: ResourceLimits,
        check_interval: float = 1.0
    ):
        self.limits = limits
        self.check_interval = check_interval
        
        # Resource tracking
        self.current_usage: Dict[ResourceType, float] = {}
        self.history: List[ResourceSnapshot] = []
        self.max_history_size = 300  # 5 minutes at 1s intervals
        
        # Allocation tracking
        self.allocated_resources: Dict[str, Dict[ResourceType, float]] = {}
        self._lock = asyncio.Lock()
        
        # Monitoring
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitoring started")
    
    async def stop(self):
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_task:
            await self._monitor_task
        logger.info("Resource monitoring stopped")
    
    async def check_availability(
        self,
        required: Dict[ResourceType, float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if required resources are available.
        
        Returns (available, reason_if_not).
        """
        async with self._lock:
            for resource_type, amount in required.items():
                current = self.current_usage.get(resource_type, 0)
                allocated = sum(
                    alloc.get(resource_type, 0)
                    for alloc in self.allocated_resources.values()
                )
                total_usage = current + allocated + amount
                
                limit = self._get_limit(resource_type)
                if total_usage > limit:
                    return False, f"Insufficient {resource_type}: {total_usage:.1f} > {limit:.1f}"
        
        return True, None
    
    async def allocate(
        self,
        task_id: str,
        resources: Dict[ResourceType, float]
    ) -> bool:
        """
        Allocate resources for a task.
        
        Returns True if allocation successful.
        """
        available, reason = await self.check_availability(resources)
        if not available:
            logger.warning(f"Resource allocation failed for {task_id}: {reason}")
            return False
        
        async with self._lock:
            self.allocated_resources[task_id] = resources
        
        logger.debug(f"Allocated resources for {task_id}: {resources}")
        return True
    
    async def release(self, task_id: str):
        """Release resources allocated to a task."""
        async with self._lock:
            if task_id in self.allocated_resources:
                released = self.allocated_resources.pop(task_id)
                logger.debug(f"Released resources for {task_id}: {released}")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        process = psutil.Process()
        
        while self._monitoring:
            try:
                # Collect metrics
                snapshot = await self._collect_snapshot(process)
                
                # Update current usage
                async with self._lock:
                    self.current_usage = {
                        ResourceType.CPU: snapshot.cpu_percent,
                        ResourceType.MEMORY: snapshot.memory_percent,
                        ResourceType.DISK_IO: (
                            snapshot.disk_io_read_mb + 
                            snapshot.disk_io_write_mb
                        )
                    }
                    
                    # Add to history
                    self.history.append(snapshot)
                    if len(self.history) > self.max_history_size:
                        self.history.pop(0)
                
                # Check for resource warnings
                await self._check_resource_warnings(snapshot)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _collect_snapshot(self, process: psutil.Process) -> ResourceSnapshot:
        """Collect current resource usage snapshot."""
        # CPU usage
        cpu_percent = process.cpu_percent(interval=None)
        
        # Memory usage
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        memory_percent = process.memory_percent()
        
        # Disk I/O
        try:
            io_counters = process.io_counters()
            disk_read_mb = io_counters.read_bytes / (1024 * 1024)
            disk_write_mb = io_counters.write_bytes / (1024 * 1024)
        except:
            disk_read_mb = disk_write_mb = 0
        
        # Network I/O (system-wide)
        net_io = psutil.net_io_counters()
        net_sent_mb = net_io.bytes_sent / (1024 * 1024)
        net_recv_mb = net_io.bytes_recv / (1024 * 1024)
        
        # Task counts
        active_tasks = len(self.allocated_resources)
        queued_tasks = 0  # TODO: Get from worker pool
        
        return ResourceSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_io_sent_mb=net_sent_mb,
            network_io_recv_mb=net_recv_mb,
            active_tasks=active_tasks,
            queued_tasks=queued_tasks
        )
```

### 4. Configuration Models (`src/torematrix/processing/workers/config.py`)

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional
from enum import Enum

class ResourceType(str, Enum):
    """Types of system resources."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    GPU = "gpu"

class WorkerConfig(BaseModel):
    """Configuration for the worker pool."""
    
    # Worker counts
    async_workers: int = Field(default=4, ge=1, description="Number of async workers")
    thread_workers: int = Field(default=2, ge=0, description="Number of thread workers")
    process_workers: int = Field(default=0, ge=0, description="Number of process workers")
    
    # Queue settings
    max_queue_size: int = Field(default=1000, ge=10, description="Maximum queue size")
    priority_queue_size: int = Field(default=100, ge=10, description="Priority queue size")
    
    # Timeouts
    default_timeout: float = Field(default=300.0, gt=0, description="Default task timeout in seconds")
    worker_heartbeat_interval: float = Field(default=10.0, gt=0, description="Worker heartbeat interval")
    
    # Resource limits
    max_concurrent_tasks: int = Field(default=50, ge=1, description="Maximum concurrent tasks")
    task_memory_limit_mb: int = Field(default=1024, ge=64, description="Memory limit per task")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "async_workers": 4,
                "thread_workers": 2,
                "process_workers": 0,
                "max_queue_size": 1000,
                "default_timeout": 300.0
            }
        }

class ResourceLimits(BaseModel):
    """Resource limits for the processing system."""
    
    # CPU limits (percentage)
    max_cpu_percent: float = Field(default=80.0, ge=10.0, le=100.0)
    warning_cpu_percent: float = Field(default=70.0, ge=10.0, le=100.0)
    
    # Memory limits (percentage)
    max_memory_percent: float = Field(default=75.0, ge=10.0, le=100.0)
    warning_memory_percent: float = Field(default=65.0, ge=10.0, le=100.0)
    
    # Disk I/O limits (MB/s)
    max_disk_io_mbps: Optional[float] = Field(default=None, ge=1.0)
    warning_disk_io_mbps: Optional[float] = Field(default=None, ge=1.0)
    
    # Network I/O limits (MB/s)
    max_network_io_mbps: Optional[float] = Field(default=None, ge=1.0)
    
    # GPU limits (if applicable)
    max_gpu_percent: Optional[float] = Field(default=None, ge=10.0, le=100.0)
    max_gpu_memory_mb: Optional[int] = Field(default=None, ge=100)
```

## Integration Points

### With Agent 1 (Pipeline Manager)
- Receive tasks from PipelineManager via `submit_task()`
- Report progress back through EventBus
- Respect resource constraints from pipeline config

### With Agent 2 (Processor Plugin)
- Execute processors using the worker pool
- Handle processor-specific resource requirements
- Manage processor timeouts and retries

### With Agent 4 (Integration)
- Provide metrics and monitoring endpoints
- Support health checks and diagnostics
- Enable performance profiling

## Testing Requirements

1. **Unit Tests**:
   - Worker pool lifecycle (start/stop/restart)
   - Task submission and execution
   - Resource allocation and limits
   - Progress tracking accuracy

2. **Integration Tests**:
   - Multi-worker coordination
   - Priority queue handling
   - Resource throttling
   - Event emission

3. **Performance Tests**:
   - Concurrent task handling
   - Resource utilization under load
   - Progress update frequency
   - Worker scaling

## Implementation Notes

1. **Worker Types**:
   - Async workers for I/O-bound tasks
   - Thread workers for CPU-bound Python code
   - Process workers for heavy CPU tasks (optional)

2. **Resource Management**:
   - Soft limits trigger warnings
   - Hard limits prevent new task allocation
   - Graceful degradation under load

3. **Progress Tracking**:
   - Real-time updates via EventBus
   - Aggregated statistics for monitoring
   - Historical data for analysis

4. **Error Handling**:
   - Worker failures don't crash the pool
   - Failed tasks can be retried
   - Comprehensive error reporting

## Dependencies
- Python 3.8+
- asyncio for async operations
- psutil for resource monitoring
- Standard library concurrent.futures

Remember: Focus on reliability, performance, and observability!