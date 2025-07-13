"""
Resource monitoring for pipeline execution.

Tracks CPU, memory, and GPU usage to ensure pipeline doesn't exceed system capabilities.
"""

import asyncio
import psutil
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

from .config import ResourceRequirements

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: int
    memory_percent: float
    gpu_memory_mb: Optional[int] = None
    gpu_percent: Optional[float] = None


class ResourceMonitor:
    """
    Monitors system resources and manages allocation for pipeline stages.
    
    Tracks CPU, memory, and GPU usage to ensure pipeline doesn't
    exceed system capabilities.
    """
    
    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 80.0,
        update_interval: float = 1.0,
        history_size: int = 60
    ):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.update_interval = update_interval
        
        # Resource tracking
        self.history: deque[ResourceUsage] = deque(maxlen=history_size)
        self.current_usage: Optional[ResourceUsage] = None
        self.allocated_resources: Dict[str, ResourceRequirements] = {}
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start resource monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitor started")
    
    async def stop(self):
        """Stop resource monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect resource usage
                usage = await self._collect_usage()
                
                async with self._lock:
                    self.current_usage = usage
                    self.history.append(usage)
                
                # Log if usage is high
                if usage.cpu_percent > self.max_cpu_percent:
                    logger.warning(f"High CPU usage: {usage.cpu_percent:.1f}%")
                if usage.memory_percent > self.max_memory_percent:
                    logger.warning(f"High memory usage: {usage.memory_percent:.1f}%")
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _collect_usage(self) -> ResourceUsage:
        """Collect current resource usage."""
        # Run CPU collection in thread pool as it can block
        loop = asyncio.get_event_loop()
        cpu_percent = await loop.run_in_executor(
            None, 
            psutil.cpu_percent, 
            self.update_interval
        )
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        # GPU monitoring would go here (using pynvml or similar)
        # For now, just placeholder values
        gpu_memory_mb = None
        gpu_percent = None
        
        # Try to get GPU info if available
        try:
            # This would use pynvml or torch.cuda if available
            # import pynvml
            # pynvml.nvmlInit()
            # handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            # mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            # gpu_memory_mb = mem_info.used // (1024 * 1024)
            # gpu_percent = (mem_info.used / mem_info.total) * 100
            pass
        except:
            pass
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_mb=memory.used // (1024 * 1024),
            memory_percent=memory.percent,
            gpu_memory_mb=gpu_memory_mb,
            gpu_percent=gpu_percent
        )
    
    async def check_availability(self, requirements: ResourceRequirements) -> bool:
        """
        Check if required resources are available.
        
        Args:
            requirements: Resource requirements to check
            
        Returns:
            True if resources are available
        """
        if not self.current_usage:
            return True  # No data yet, assume available
        
        # Calculate available resources
        cpu_available = 100.0 - self.current_usage.cpu_percent
        memory_available_mb = psutil.virtual_memory().available // (1024 * 1024)
        
        # Check CPU
        cpu_required_percent = requirements.cpu_cores * 100.0 / psutil.cpu_count()
        if cpu_required_percent > cpu_available:
            logger.debug(f"Insufficient CPU: need {cpu_required_percent:.1f}%, have {cpu_available:.1f}%")
            return False
        
        # Check memory
        if requirements.memory_mb > memory_available_mb:
            logger.debug(f"Insufficient memory: need {requirements.memory_mb}MB, have {memory_available_mb}MB")
            return False
        
        # Check if we'd exceed limits with allocation
        allocated_cpu = sum(
            r.cpu_cores * 100.0 / psutil.cpu_count() 
            for r in self.allocated_resources.values()
        )
        allocated_memory = sum(r.memory_mb for r in self.allocated_resources.values())
        
        projected_cpu = self.current_usage.cpu_percent + allocated_cpu + cpu_required_percent
        if projected_cpu > self.max_cpu_percent:
            logger.debug(f"Would exceed CPU limit: {projected_cpu:.1f}% > {self.max_cpu_percent}%")
            return False
        
        memory_total_mb = psutil.virtual_memory().total // (1024 * 1024)
        projected_memory_percent = (
            (self.current_usage.memory_mb + allocated_memory + requirements.memory_mb) 
            / memory_total_mb * 100
        )
        if projected_memory_percent > self.max_memory_percent:
            logger.debug(f"Would exceed memory limit: {projected_memory_percent:.1f}% > {self.max_memory_percent}%")
            return False
        
        # GPU checks
        if requirements.gpu_required:
            # Check if GPU is available
            try:
                import torch
                if not torch.cuda.is_available():
                    logger.debug("GPU required but not available")
                    return False
                
                # Check GPU memory if specified
                if requirements.gpu_memory_mb and self.current_usage.gpu_memory_mb is not None:
                    # Simple check - would need proper GPU memory tracking
                    pass
                    
            except ImportError:
                # No torch available, check other ways
                logger.debug("GPU required but torch not available")
                return False
        
        return True
    
    async def allocate(self, stage_name: str, requirements: ResourceRequirements):
        """Allocate resources for a stage."""
        async with self._lock:
            self.allocated_resources[stage_name] = requirements
            logger.debug(f"Allocated resources for {stage_name}: CPU={requirements.cpu_cores}, Memory={requirements.memory_mb}MB")
    
    async def release(self, stage_name: str):
        """Release resources allocated to a stage."""
        async with self._lock:
            if stage_name in self.allocated_resources:
                released = self.allocated_resources.pop(stage_name)
                logger.debug(f"Released resources for {stage_name}: CPU={released.cpu_cores}, Memory={released.memory_mb}MB")
    
    def get_allocated_totals(self) -> ResourceRequirements:
        """Get total allocated resources."""
        total_cpu = sum(r.cpu_cores for r in self.allocated_resources.values())
        total_memory = sum(r.memory_mb for r in self.allocated_resources.values())
        any_gpu = any(r.gpu_required for r in self.allocated_resources.values())
        total_gpu_memory = sum(
            r.gpu_memory_mb or 0 
            for r in self.allocated_resources.values() 
            if r.gpu_required
        )
        
        return ResourceRequirements(
            cpu_cores=total_cpu,
            memory_mb=total_memory,
            gpu_required=any_gpu,
            gpu_memory_mb=total_gpu_memory if any_gpu else None
        )
    
    def get_usage_history(self, minutes: int = 5) -> List[ResourceUsage]:
        """Get resource usage history."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [u for u in self.history if u.timestamp > cutoff]
    
    def get_average_usage(self, minutes: int = 5) -> Optional[ResourceUsage]:
        """Get average resource usage over time period."""
        history = self.get_usage_history(minutes)
        if not history:
            return None
        
        avg_cpu = sum(u.cpu_percent for u in history) / len(history)
        avg_memory = sum(u.memory_mb for u in history) / len(history)
        avg_memory_percent = sum(u.memory_percent for u in history) / len(history)
        
        # Average GPU stats if available
        gpu_history = [u for u in history if u.gpu_memory_mb is not None]
        avg_gpu_memory = None
        avg_gpu_percent = None
        if gpu_history:
            avg_gpu_memory = int(sum(u.gpu_memory_mb for u in gpu_history) / len(gpu_history))
            avg_gpu_percent = sum(u.gpu_percent for u in gpu_history) / len(gpu_history)
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=avg_cpu,
            memory_mb=int(avg_memory),
            memory_percent=avg_memory_percent,
            gpu_memory_mb=avg_gpu_memory,
            gpu_percent=avg_gpu_percent
        )
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage as a dictionary."""
        if not self.current_usage:
            return {}
        
        usage = {
            "cpu": self.current_usage.cpu_percent,
            "memory": self.current_usage.memory_percent,
            "memory_mb": self.current_usage.memory_mb
        }
        
        if self.current_usage.gpu_percent is not None:
            usage["gpu"] = self.current_usage.gpu_percent
            usage["gpu_memory_mb"] = self.current_usage.gpu_memory_mb
        
        return usage
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resource monitor statistics."""
        allocated = self.get_allocated_totals()
        
        return {
            "current_usage": self.get_current_usage(),
            "allocated_stages": len(self.allocated_resources),
            "allocated_resources": {
                "cpu_cores": allocated.cpu_cores,
                "memory_mb": allocated.memory_mb,
                "gpu_required": allocated.gpu_required
            },
            "limits": {
                "max_cpu_percent": self.max_cpu_percent,
                "max_memory_percent": self.max_memory_percent
            },
            "history_size": len(self.history)
        }