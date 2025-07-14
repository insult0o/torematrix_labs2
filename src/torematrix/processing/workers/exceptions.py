"""Worker pool and resource management exceptions."""

from typing import Optional, Dict, Any


class WorkerError(Exception):
    """Base exception for worker-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ResourceError(WorkerError):
    """Exception raised when resources are insufficient or unavailable."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, 
                 current_usage: Optional[float] = None, limit: Optional[float] = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class WorkerPoolError(WorkerError):
    """Exception raised for worker pool management errors."""
    pass


class TaskError(WorkerError):
    """Exception raised for task-related errors."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, 
                 processor_name: Optional[str] = None):
        super().__init__(message)
        self.task_id = task_id
        self.processor_name = processor_name


class TaskTimeoutError(TaskError):
    """Exception raised when a task times out."""
    
    def __init__(self, task_id: str, timeout: float):
        super().__init__(f"Task {task_id} timed out after {timeout}s")
        self.timeout = timeout


class WorkerTimeoutError(WorkerError):
    """Exception raised when a worker operation times out."""
    
    def __init__(self, worker_id: str, operation: str, timeout: float):
        super().__init__(f"Worker {worker_id} {operation} timed out after {timeout}s")
        self.worker_id = worker_id
        self.operation = operation
        self.timeout = timeout


class ProgressTrackingError(WorkerError):
    """Exception raised for progress tracking errors."""
    pass