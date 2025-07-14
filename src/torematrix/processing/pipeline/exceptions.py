"""
Pipeline-specific exceptions.
"""

from typing import Optional, List, Dict, Any


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class PipelineConfigError(PipelineError):
    """Raised when pipeline configuration is invalid."""
    pass


class PipelineExecutionError(PipelineError):
    """Raised when pipeline execution fails."""
    
    def __init__(
        self, 
        message: str, 
        stage_name: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.stage_name = stage_name
        self.original_error = original_error


class StageDependencyError(PipelineError):
    """Raised when stage dependencies are not met."""
    
    def __init__(
        self, 
        stage_name: str, 
        missing_dependencies: List[str]
    ):
        self.stage_name = stage_name
        self.missing_dependencies = missing_dependencies
        message = f"Stage '{stage_name}' missing dependencies: {', '.join(missing_dependencies)}"
        super().__init__(message)


class StageTimeoutError(PipelineError):
    """Raised when a stage execution times out."""
    
    def __init__(self, stage_name: str, timeout: int):
        self.stage_name = stage_name
        self.timeout = timeout
        message = f"Stage '{stage_name}' timed out after {timeout} seconds"
        super().__init__(message)


class ResourceError(PipelineError):
    """Raised when resource requirements cannot be met."""
    
    def __init__(
        self, 
        message: str, 
        required: Dict[str, Any],
        available: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.required = required
        self.available = available


class CyclicDependencyError(PipelineConfigError):
    """Raised when pipeline contains cyclic dependencies."""
    
    def __init__(self, cycles: List[List[str]]):
        self.cycles = cycles
        message = f"Pipeline contains cyclic dependencies: {cycles}"
        super().__init__(message)


class CheckpointError(PipelineError):
    """Raised when checkpoint operations fail."""
    pass


class PipelineCancelledError(PipelineError):
    """Raised when pipeline execution is cancelled."""
    pass