"""Base processor interface for TORE Matrix V3.

This module defines the abstract base class and core interfaces that all
document processors must implement. It provides a standardized way to
process documents with lifecycle management, error handling, and monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
from pydantic import BaseModel, Field

# Import pipeline types for conversion
try:
    from ..pipeline.stages import StageResult
except ImportError:
    # Define minimal StageResult for conversion if pipeline not available
    @dataclass
    class StageResult:
        stage_name: str
        status: 'StageStatus'
        start_time: datetime
        end_time: Optional[datetime] = None
        data: Dict[str, Any] = field(default_factory=dict)
        error: Optional[str] = None
        metrics: Dict[str, float] = field(default_factory=dict)

logger = logging.getLogger(__name__)


class ProcessorCapability(str, Enum):
    """Capabilities that processors can advertise."""
    TEXT_EXTRACTION = "text_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    TABLE_EXTRACTION = "table_extraction"
    IMAGE_EXTRACTION = "image_extraction"
    OCR = "ocr"
    LANGUAGE_DETECTION = "language_detection"
    TRANSLATION = "translation"
    PII_DETECTION = "pii_detection"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"


class ProcessorPriority(int, Enum):
    """Processor execution priority."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class StageStatus(str, Enum):
    """Status of a processing stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessorMetadata:
    """Metadata about a processor."""
    name: str
    version: str
    description: str
    author: str = ""
    capabilities: List[ProcessorCapability] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: ProcessorPriority = ProcessorPriority.NORMAL
    
    # Performance characteristics
    is_cpu_intensive: bool = False
    is_memory_intensive: bool = False
    is_io_intensive: bool = False
    requires_gpu: bool = False
    
    # Operational metadata
    max_file_size_mb: Optional[int] = None
    timeout_seconds: int = 300
    retry_count: int = 3
    concurrent_limit: int = 10


@dataclass
class ProcessorContext:
    """Context passed to processors during execution."""
    document_id: str
    file_path: str
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_results: Dict[str, Any] = field(default_factory=dict)
    pipeline_context: Optional[Any] = None
    
    # Execution control
    is_dry_run: bool = False
    timeout: Optional[float] = None
    
    def get_previous_result(self, processor_name: str) -> Optional[Any]:
        """Get result from a previous processor."""
        return self.previous_results.get(processor_name)


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Stage duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class ProcessorResult:
    """Result from processor execution."""
    processor_name: str
    status: StageStatus
    start_time: datetime
    end_time: datetime
    
    # Results
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Processing duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    def to_stage_result(self) -> StageResult:
        """Convert to pipeline stage result."""
        return StageResult(
            stage_name=self.processor_name,
            status=self.status,
            start_time=self.start_time,
            end_time=self.end_time,
            data=self.extracted_data,
            error="; ".join(self.errors) if self.errors else None,
            metrics=self.metrics
        )


class BaseProcessor(ABC):
    """
    Abstract base class for all document processors.
    
    Processors must implement the process method and can optionally
    override other lifecycle methods.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False
        self._metrics: Dict[str, float] = {}
    
    @classmethod
    @abstractmethod
    def get_metadata(cls) -> ProcessorMetadata:
        """Get processor metadata."""
        pass
    
    async def initialize(self) -> None:
        """
        Initialize the processor.
        
        Called once before first use. Override _initialize for
        processor-specific initialization.
        """
        if self._initialized:
            return
        
        metadata = self.get_metadata()
        logger.info(f"Initializing processor: {metadata.name} v{metadata.version}")
        
        try:
            await self._initialize()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize processor {metadata.name}: {e}")
            raise
    
    async def _initialize(self) -> None:
        """Override for processor-specific initialization."""
        pass
    
    @abstractmethod
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """
        Process a document.
        
        Args:
            context: Processing context with document information
            
        Returns:
            Processing result with extracted data
        """
        pass
    
    async def validate_input(self, context: ProcessorContext) -> List[str]:
        """
        Validate input before processing.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        metadata = self.get_metadata()
        
        # Check supported formats
        if metadata.supported_formats:
            # Extract format from mime type or file extension
            format_supported = any(
                fmt in context.mime_type or 
                context.file_path.endswith(f".{fmt}")
                for fmt in metadata.supported_formats
            )
            if not format_supported:
                errors.append(
                    f"Unsupported format. Supported: {metadata.supported_formats}"
                )
        
        # Check file size
        if metadata.max_file_size_mb:
            # Would check actual file size here
            pass
        
        # Processor-specific validation
        errors.extend(await self._validate_input(context))
        
        return errors
    
    async def _validate_input(self, context: ProcessorContext) -> List[str]:
        """Override for processor-specific validation."""
        return []
    
    async def cleanup(self) -> None:
        """
        Clean up processor resources.
        
        Called when processor is being shut down.
        """
        if self._initialized:
            logger.info(f"Cleaning up processor: {self.get_metadata().name}")
            await self._cleanup()
            self._initialized = False
    
    async def _cleanup(self) -> None:
        """Override for processor-specific cleanup."""
        pass
    
    def get_metrics(self) -> Dict[str, float]:
        """Get processor metrics."""
        return self._metrics.copy()
    
    def update_metric(self, name: str, value: float) -> None:
        """Update a metric value."""
        self._metrics[name] = value
    
    def increment_metric(self, name: str, delta: float = 1.0) -> None:
        """Increment a metric value."""
        self._metrics[name] = self._metrics.get(name, 0.0) + delta
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health status information
        """
        return {
            "healthy": self._initialized,
            "name": self.get_metadata().name,
            "metrics": self.get_metrics()
        }


class ProcessorException(Exception):
    """Base exception for processor errors."""
    pass


class ProcessorInitializationError(ProcessorException):
    """Raised when processor initialization fails."""
    pass


class ProcessorExecutionError(ProcessorException):
    """Raised when processor execution fails."""
    pass


class ProcessorTimeoutError(ProcessorException):
    """Raised when processor execution times out."""
    pass