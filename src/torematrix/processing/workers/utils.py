"""Utility functions for worker pool management."""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_async_call(func: Callable[..., T], *args, **kwargs) -> Optional[T]:
    """
    Safely call a function that might be async or sync.
    
    Returns None if the function call fails.
    """
    try:
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return asyncio.create_task(result)
        return result
    except Exception as e:
        logger.error(f"Error calling {func.__name__}: {e}")
        return None


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    check_interval: float = 0.1
) -> bool:
    """
    Wait for a condition to become True.
    
    Returns True if condition is met, False if timeout.
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return True
        await asyncio.sleep(check_interval)
    
    return False


def format_duration(duration: Union[float, timedelta]) -> str:
    """Format duration for human-readable display."""
    if isinstance(duration, timedelta):
        total_seconds = duration.total_seconds()
    else:
        total_seconds = duration
    
    if total_seconds < 1:
        return f"{total_seconds * 1000:.0f}ms"
    elif total_seconds < 60:
        return f"{total_seconds:.1f}s"
    elif total_seconds < 3600:
        minutes = total_seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = total_seconds / 3600
        return f"{hours:.1f}h"


def format_bytes(bytes_count: float) -> str:
    """Format bytes for human-readable display."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f}PB"


def calculate_throughput(count: int, duration: Union[float, timedelta]) -> float:
    """Calculate throughput (items per second)."""
    if isinstance(duration, timedelta):
        duration_seconds = duration.total_seconds()
    else:
        duration_seconds = duration
    
    if duration_seconds <= 0:
        return 0.0
    
    return count / duration_seconds


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """Calculate exponential backoff delay."""
    import random
    
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # Add ±25% jitter
        jitter_amount = delay * 0.25
        delay += random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)


class AsyncTimer:
    """Simple async timer for measuring execution time."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed * 1000


def worker_task_wrapper(worker_id: str):
    """Decorator to wrap worker tasks with error handling and logging."""
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                logger.debug(f"Worker {worker_id} starting task: {func.__name__}")
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(
                    f"Worker {worker_id} completed task: {func.__name__} "
                    f"in {format_duration(duration)}"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Worker {worker_id} failed task: {func.__name__} "
                    f"after {format_duration(duration)}: {e}"
                )
                raise
        
        return wrapper
    return decorator


class ResourceUsageTracker:
    """Track resource usage over time."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.cpu_history = []
        self.memory_history = []
        self.timestamps = []
    
    def add_sample(self, cpu_percent: float, memory_percent: float):
        """Add a resource usage sample."""
        now = datetime.utcnow()
        
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)
        self.timestamps.append(now)
        
        # Keep only the last N samples
        if len(self.cpu_history) > self.window_size:
            self.cpu_history.pop(0)
            self.memory_history.pop(0)
            self.timestamps.pop(0)
    
    def get_average_cpu(self) -> float:
        """Get average CPU usage."""
        return sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0.0
    
    def get_average_memory(self) -> float:
        """Get average memory usage."""
        return sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0.0
    
    def get_peak_cpu(self) -> float:
        """Get peak CPU usage."""
        return max(self.cpu_history) if self.cpu_history else 0.0
    
    def get_peak_memory(self) -> float:
        """Get peak memory usage."""
        return max(self.memory_history) if self.memory_history else 0.0
    
    def get_recent_trend(self, minutes: int = 5) -> Dict[str, float]:
        """Get resource usage trend for the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_cpu = []
        recent_memory = []
        
        for i, timestamp in enumerate(self.timestamps):
            if timestamp >= cutoff:
                recent_cpu.append(self.cpu_history[i])
                recent_memory.append(self.memory_history[i])
        
        if not recent_cpu:
            return {"cpu_trend": 0.0, "memory_trend": 0.0}
        
        # Simple trend calculation (difference between first and last)
        cpu_trend = recent_cpu[-1] - recent_cpu[0] if len(recent_cpu) > 1 else 0.0
        memory_trend = recent_memory[-1] - recent_memory[0] if len(recent_memory) > 1 else 0.0
        
        return {
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "sample_count": len(recent_cpu)
        }