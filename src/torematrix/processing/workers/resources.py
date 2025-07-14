"""Resource management and monitoring for worker pools."""

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
        
        # Process tracking
        self._process = psutil.Process()
        self._last_io_counters = None
        self._last_net_counters = None
        
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
            try:
                await asyncio.wait_for(self._monitor_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
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
                
                limit = self.limits.get_limit(resource_type)
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
    
    def get_current_usage(self) -> Dict[ResourceType, float]:
        """Get current resource usage."""
        return self.current_usage.copy()
    
    def get_allocated_resources(self) -> Dict[str, Dict[ResourceType, float]]:
        """Get currently allocated resources."""
        return self.allocated_resources.copy()
    
    def get_resource_history(
        self, 
        minutes: int = 5
    ) -> List[ResourceSnapshot]:
        """Get resource usage history for the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            snapshot for snapshot in self.history
            if snapshot.timestamp >= cutoff
        ]
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting resource monitoring loop")
        
        while self._monitoring:
            try:
                # Collect metrics
                snapshot = await self._collect_snapshot()
                
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
        
        logger.info("Resource monitoring loop stopped")
    
    async def _collect_snapshot(self) -> ResourceSnapshot:
        """Collect current resource usage snapshot."""
        # CPU usage
        cpu_percent = self._process.cpu_percent(interval=None)
        
        # Memory usage
        memory_info = self._process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        memory_percent = self._process.memory_percent()
        
        # Disk I/O
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        try:
            io_counters = self._process.io_counters()
            if self._last_io_counters:
                read_diff = io_counters.read_bytes - self._last_io_counters.read_bytes
                write_diff = io_counters.write_bytes - self._last_io_counters.write_bytes
                disk_read_mb = read_diff / (1024 * 1024) / self.check_interval
                disk_write_mb = write_diff / (1024 * 1024) / self.check_interval
            self._last_io_counters = io_counters
        except (AttributeError, OSError):
            # Some platforms don't support I/O counters
            pass
        
        # Network I/O (system-wide)
        net_sent_mb = 0.0
        net_recv_mb = 0.0
        try:
            net_io = psutil.net_io_counters()
            if self._last_net_counters:
                sent_diff = net_io.bytes_sent - self._last_net_counters.bytes_sent
                recv_diff = net_io.bytes_recv - self._last_net_counters.bytes_recv
                net_sent_mb = sent_diff / (1024 * 1024) / self.check_interval
                net_recv_mb = recv_diff / (1024 * 1024) / self.check_interval
            self._last_net_counters = net_io
        except (AttributeError, OSError):
            # Some platforms don't support network I/O counters
            pass
        
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
    
    async def _check_resource_warnings(self, snapshot: ResourceSnapshot):
        """Check for resource usage warnings."""
        # CPU warning
        cpu_threshold = self.limits.get_warning_threshold(ResourceType.CPU)
        if snapshot.cpu_percent > cpu_threshold:
            logger.warning(
                f"CPU usage high: {snapshot.cpu_percent:.1f}% > {cpu_threshold:.1f}%"
            )
        
        # Memory warning
        memory_threshold = self.limits.get_warning_threshold(ResourceType.MEMORY)
        if snapshot.memory_percent > memory_threshold:
            logger.warning(
                f"Memory usage high: {snapshot.memory_percent:.1f}% > {memory_threshold:.1f}%"
            )
        
        # Disk I/O warning (if configured)
        disk_io_threshold = self.limits.warning_disk_io_mbps
        if disk_io_threshold:
            total_disk_io = snapshot.disk_io_read_mb + snapshot.disk_io_write_mb
            if total_disk_io > disk_io_threshold:
                logger.warning(
                    f"Disk I/O high: {total_disk_io:.1f} MB/s > {disk_io_threshold:.1f} MB/s"
                )
    
    def __str__(self) -> str:
        """String representation of resource monitor."""
        return (
            f"ResourceMonitor("
            f"cpu={self.current_usage.get(ResourceType.CPU, 0):.1f}%, "
            f"memory={self.current_usage.get(ResourceType.MEMORY, 0):.1f}%, "
            f"active_tasks={len(self.allocated_resources)}"
            f")"
        )