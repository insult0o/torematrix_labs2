"""
Base Operation Classes for Merge/Split Operations

Provides abstract base classes and result types for all merge/split operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from torematrix.core.models.element import Element


class OperationStatus(Enum):
    """Status of an operation."""
    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationResult:
    """Base result class for all operations."""
    operation_id: str
    status: OperationStatus
    elements: List[Element] = field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Check if operation was successful."""
        return self.status == OperationStatus.COMPLETED and self.error_message is None
    
    @property
    def element_count(self) -> int:
        """Get count of resulting elements."""
        return len(self.elements)


class BaseOperation(ABC):
    """Abstract base class for all merge/split operations."""
    
    def __init__(self, operation_id: Optional[str] = None):
        self.operation_id = operation_id or str(uuid.uuid4())
        self.status = OperationStatus.PENDING
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate operation parameters and preconditions.
        
        Returns:
            bool: True if operation is valid, False otherwise
        """
        """Validate operation parameters and preconditions."""
        pass
    
    @abstractmethod
    def execute(self) -> OperationResult:
        """
        Execute the operation.
        
        Returns:
            OperationResult: Result of the operation
        """
        """Execute the operation."""
        pass
    
    @abstractmethod
    def preview(self) -> OperationResult:
        """
        Generate a preview of the operation without executing it.
        
        Returns:
            OperationResult: Preview of the operation result
        """
        """Generate a preview of the operation without executing it."""
        pass
    
    @abstractmethod
    def can_rollback(self) -> bool:
        """
        Check if the operation can be rolled back.
        
        Returns:
            bool: True if operation can be rolled back
        """
        """Check if the operation can be rolled back."""
        pass
    
    @abstractmethod
    def rollback(self) -> bool:
        """
        Roll back the operation.
        
        Returns:
            bool: True if rollback was successful
        """
        """Roll back the operation."""
        pass
    
    def _start_execution(self) -> None:
        """Mark the start of operation execution."""
        self.status = OperationStatus.RUNNING
        self._start_time = datetime.now()
    
    def _end_execution(self, status: OperationStatus) -> None:
        """Mark the end of operation execution."""
        self.status = status
        self._end_time = datetime.now()
    
    @property
    def execution_time_ms(self) -> float:
        """Get execution time in milliseconds."""
        if self._start_time is None:
            return 0.0
        
        end_time = self._end_time or datetime.now()
        return (end_time - self._start_time).total_seconds() * 1000
    
    def get_operation_info(self) -> Dict[str, Any]:
        """Get information about the operation."""
        return {
            "operation_id": self.operation_id,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "end_time": self._end_time.isoformat() if self._end_time else None,
        }


@dataclass
class OperationError(Exception):
    """Base exception for operation errors."""
    operation_id: str
    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"Operation {self.operation_id} failed: {self.message} ({self.error_code})"


@dataclass
class ValidationError(OperationError):
    """Exception for validation errors."""
    pass


@dataclass
class ExecutionError(OperationError):
    """Exception for execution errors."""
    pass
        return (end_time - self._start_time).total_seconds() * 1000
