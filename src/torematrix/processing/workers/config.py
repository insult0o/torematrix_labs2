"""Configuration models for worker pool and resource management."""

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
    
    def get_limit(self, resource_type: ResourceType) -> float:
        """Get the limit for a specific resource type."""
        if resource_type == ResourceType.CPU:
            return self.max_cpu_percent
        elif resource_type == ResourceType.MEMORY:
            return self.max_memory_percent
        elif resource_type == ResourceType.DISK_IO:
            return self.max_disk_io_mbps or float('inf')
        elif resource_type == ResourceType.NETWORK_IO:
            return self.max_network_io_mbps or float('inf')
        elif resource_type == ResourceType.GPU:
            return self.max_gpu_percent or float('inf')
        else:
            return float('inf')
    
    def get_warning_threshold(self, resource_type: ResourceType) -> float:
        """Get the warning threshold for a specific resource type."""
        if resource_type == ResourceType.CPU:
            return self.warning_cpu_percent
        elif resource_type == ResourceType.MEMORY:
            return self.warning_memory_percent
        elif resource_type == ResourceType.DISK_IO:
            return self.warning_disk_io_mbps or float('inf')
        else:
            return self.get_limit(resource_type) * 0.8  # Default to 80% of limit