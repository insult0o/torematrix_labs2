# Agent 2 Instructions: Processor Plugin System & Interface

## Overview
You are Agent 2 working on Issue #8.2 (Processor Plugin System & Interface) as part of the Processing Pipeline Architecture. Your focus is creating a flexible plugin system for document processors with standardized interfaces, error handling, and monitoring.

## Context
- Part of Issue #8: Processing Pipeline Architecture (V3 greenfield project)
- You're working alongside 3 other agents in parallel
- The plugin system must support dynamic loading and hot-swapping of processors
- Must integrate with the Unstructured.io processor from Issue #6

## Your Specific Tasks

### 1. Processor Interface (`src/torematrix/processing/processors/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
from pydantic import BaseModel, Field

from ..pipeline.stages import StageResult, StageStatus

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
```

### 2. Plugin System (`src/torematrix/processing/processors/registry.py`)

```python
import importlib
import inspect
import asyncio
from typing import Dict, List, Type, Optional, Any, Callable
from pathlib import Path
import logging
from contextlib import asynccontextmanager

from .base import BaseProcessor, ProcessorMetadata, ProcessorCapability, ProcessorException

logger = logging.getLogger(__name__)

class ProcessorRegistry:
    """
    Registry for managing document processors.
    
    Supports dynamic loading, dependency injection, and lifecycle management.
    """
    
    def __init__(self):
        self._processors: Dict[str, Type[BaseProcessor]] = {}
        self._instances: Dict[str, BaseProcessor] = {}
        self._metadata_cache: Dict[str, ProcessorMetadata] = {}
        self._lock = asyncio.Lock()
        
        # Dependency injection
        self._dependencies: Dict[str, Any] = {}
        
        # Hooks
        self._load_hooks: List[Callable] = []
        self._unload_hooks: List[Callable] = []
    
    def register(
        self,
        processor_class: Type[BaseProcessor],
        name: Optional[str] = None
    ) -> None:
        """
        Register a processor class.
        
        Args:
            processor_class: Processor class to register
            name: Optional name override (uses metadata name by default)
        """
        metadata = processor_class.get_metadata()
        processor_name = name or metadata.name
        
        if processor_name in self._processors:
            logger.warning(f"Overwriting existing processor: {processor_name}")
        
        self._processors[processor_name] = processor_class
        self._metadata_cache[processor_name] = metadata
        
        logger.info(f"Registered processor: {processor_name} v{metadata.version}")
        
        # Call load hooks
        for hook in self._load_hooks:
            hook(processor_name, processor_class)
    
    def unregister(self, name: str) -> None:
        """Unregister a processor."""
        if name in self._processors:
            # Clean up instance if exists
            if name in self._instances:
                asyncio.create_task(self._cleanup_instance(name))
            
            del self._processors[name]
            del self._metadata_cache[name]
            
            # Call unload hooks
            for hook in self._unload_hooks:
                hook(name)
            
            logger.info(f"Unregistered processor: {name}")
    
    async def _cleanup_instance(self, name: str) -> None:
        """Clean up processor instance."""
        async with self._lock:
            if name in self._instances:
                await self._instances[name].cleanup()
                del self._instances[name]
    
    def get_processor_class(self, name: str) -> Type[BaseProcessor]:
        """Get processor class by name."""
        if name not in self._processors:
            raise ProcessorException(f"Unknown processor: {name}")
        return self._processors[name]
    
    async def get_processor(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseProcessor:
        """
        Get initialized processor instance.
        
        Uses singleton pattern - returns same instance for same name/config.
        
        Args:
            name: Processor name
            config: Processor configuration
            
        Returns:
            Initialized processor instance
        """
        async with self._lock:
            # Check if instance exists
            instance_key = f"{name}:{hash(str(config))}"
            
            if instance_key not in self._instances:
                # Create new instance
                processor_class = self.get_processor_class(name)
                instance = processor_class(config)
                
                # Inject dependencies
                await self._inject_dependencies(instance)
                
                # Initialize
                await instance.initialize()
                
                self._instances[instance_key] = instance
            
            return self._instances[instance_key]
    
    async def _inject_dependencies(self, processor: BaseProcessor) -> None:
        """Inject dependencies into processor."""
        # Look for dependency markers in processor
        for attr_name in dir(processor):
            if attr_name.startswith("_inject_"):
                dep_name = attr_name[8:]  # Remove _inject_ prefix
                if dep_name in self._dependencies:
                    setattr(processor, dep_name, self._dependencies[dep_name])
    
    def register_dependency(self, name: str, dependency: Any) -> None:
        """Register a dependency for injection."""
        self._dependencies[name] = dependency
    
    def list_processors(self) -> List[str]:
        """List all registered processors."""
        return list(self._processors.keys())
    
    def get_metadata(self, name: str) -> ProcessorMetadata:
        """Get processor metadata."""
        if name not in self._metadata_cache:
            raise ProcessorException(f"Unknown processor: {name}")
        return self._metadata_cache[name]
    
    def find_by_capability(
        self,
        capability: ProcessorCapability
    ) -> List[str]:
        """Find processors with specific capability."""
        results = []
        for name, metadata in self._metadata_cache.items():
            if capability in metadata.capabilities:
                results.append(name)
        return results
    
    def find_by_format(self, format: str) -> List[str]:
        """Find processors supporting specific format."""
        results = []
        for name, metadata in self._metadata_cache.items():
            if format in metadata.supported_formats:
                results.append(name)
        return results
    
    def load_from_module(self, module_path: str) -> None:
        """
        Load processors from a Python module.
        
        Args:
            module_path: Module path (e.g., 'torematrix.processors.custom')
        """
        try:
            module = importlib.import_module(module_path)
            
            # Find all processor classes in module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseProcessor) and 
                    obj != BaseProcessor):
                    self.register(obj)
                    
        except ImportError as e:
            logger.error(f"Failed to load module {module_path}: {e}")
            raise ProcessorException(f"Cannot load module: {module_path}")
    
    def load_from_directory(self, directory: Path) -> None:
        """
        Load processors from a directory of Python files.
        
        Args:
            directory: Directory containing processor modules
        """
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            module_name = py_file.stem
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find processor classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseProcessor) and 
                        obj != BaseProcessor):
                        self.register(obj)
    
    def add_load_hook(self, hook: Callable) -> None:
        """Add hook called when processor is loaded."""
        self._load_hooks.append(hook)
    
    def add_unload_hook(self, hook: Callable) -> None:
        """Add hook called when processor is unloaded."""
        self._unload_hooks.append(hook)
    
    async def shutdown(self) -> None:
        """Shutdown registry and cleanup all processors."""
        logger.info("Shutting down processor registry")
        
        # Cleanup all instances
        async with self._lock:
            cleanup_tasks = []
            for instance in self._instances.values():
                cleanup_tasks.append(instance.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self._instances.clear()
    
    @asynccontextmanager
    async def processor_context(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Context manager for using a processor."""
        processor = await self.get_processor(name, config)
        try:
            yield processor
        finally:
            # Cleanup is handled by registry
            pass

# Global registry instance
_registry = ProcessorRegistry()

def get_registry() -> ProcessorRegistry:
    """Get the global processor registry."""
    return _registry
```

### 3. Built-in Processors (`src/torematrix/processing/processors/builtin.py`)

```python
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus
)
from ...integrations.unstructured.client import UnstructuredClient
from ...integrations.unstructured.config import UnstructuredConfig

logger = logging.getLogger(__name__)

class UnstructuredProcessor(BaseProcessor):
    """Processor wrapping Unstructured.io for document parsing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client: Optional[UnstructuredClient] = None
        self._inject_unstructured_client: Optional[UnstructuredClient] = None
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="unstructured_processor",
            version="1.0.0",
            description="Document parsing using Unstructured.io",
            author="ToreMatrix",
            capabilities=[
                ProcessorCapability.TEXT_EXTRACTION,
                ProcessorCapability.METADATA_EXTRACTION,
                ProcessorCapability.TABLE_EXTRACTION,
                ProcessorCapability.IMAGE_EXTRACTION
            ],
            supported_formats=[
                "pdf", "docx", "doc", "txt", "html", "xml", 
                "md", "rst", "rtf", "odt", "pptx", "ppt",
                "xlsx", "xls", "csv", "tsv", "epub", "msg", "eml"
            ],
            is_cpu_intensive=True,
            is_memory_intensive=True,
            timeout_seconds=600
        )
    
    async def _initialize(self) -> None:
        """Initialize Unstructured client."""
        if self._inject_unstructured_client:
            self.client = self._inject_unstructured_client
        else:
            # Create client from config
            unstructured_config = UnstructuredConfig(**self.config.get("unstructured", {}))
            self.client = UnstructuredClient(unstructured_config)
            await self.client.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process document using Unstructured."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.RUNNING,
            start_time=start_time,
            end_time=start_time  # Will be updated
        )
        
        try:
            # Validate input
            errors = await self.validate_input(context)
            if errors:
                result.errors = errors
                result.status = StageStatus.FAILED
                result.end_time = datetime.utcnow()
                return result
            
            # Process with Unstructured
            logger.info(f"Processing {context.file_path} with Unstructured")
            
            process_result = await self.client.process_file(
                file_path=context.file_path,
                strategy=self.config.get("strategy", "auto"),
                include_metadata=True,
                extract_images=self.config.get("extract_images", True),
                extract_tables=self.config.get("extract_tables", True)
            )
            
            # Extract results
            result.extracted_data = {
                "elements": [elem.dict() for elem in process_result.elements],
                "metadata": process_result.metadata,
                "text": process_result.text,
                "tables": process_result.tables,
                "images": process_result.images
            }
            
            result.metadata = {
                "element_count": len(process_result.elements),
                "page_count": process_result.metadata.get("page_count"),
                "language": process_result.metadata.get("language"),
                "file_type": process_result.metadata.get("file_type")
            }
            
            result.status = StageStatus.COMPLETED
            
            # Update metrics
            self.increment_metric("documents_processed")
            self.update_metric("last_process_time", result.duration)
            
        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
            self.increment_metric("documents_failed")
        
        result.end_time = datetime.utcnow()
        result.metrics = self.get_metrics()
        
        return result
    
    async def _cleanup(self) -> None:
        """Cleanup Unstructured client."""
        if self.client and not self._inject_unstructured_client:
            await self.client.close()

class MetadataExtractorProcessor(BaseProcessor):
    """Processor for extracting and enriching document metadata."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="metadata_extractor",
            version="1.0.0",
            description="Extract and enrich document metadata",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.METADATA_EXTRACTION],
            supported_formats=["*"],  # Supports all formats
            is_cpu_intensive=False,
            timeout_seconds=60
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Extract document metadata."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            # Extract metadata from context and previous results
            metadata = {
                "document_id": context.document_id,
                "file_path": context.file_path,
                "mime_type": context.mime_type,
                "processing_time": datetime.utcnow().isoformat()
            }
            
            # Add metadata from previous processors
            if "unstructured_processor" in context.previous_results:
                unstructured_meta = context.previous_results["unstructured_processor"].get("metadata", {})
                metadata.update(unstructured_meta)
            
            # Add custom metadata extraction logic here
            # For example: file size, creation date, author, etc.
            
            result.extracted_data = {"metadata": metadata}
            result.metadata = {"fields_extracted": len(metadata)}
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
        
        result.end_time = datetime.utcnow()
        return result

class ValidationProcessor(BaseProcessor):
    """Processor for validating document content and structure."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="validation_processor",
            version="1.0.0",
            description="Validate document content and structure",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.VALIDATION],
            supported_formats=["*"],
            is_cpu_intensive=False,
            timeout_seconds=30
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Validate document."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            validation_results = []
            
            # Check if document was successfully parsed
            if "unstructured_processor" in context.previous_results:
                elements = context.previous_results["unstructured_processor"].get("elements", [])
                
                if not elements:
                    validation_results.append({
                        "level": "warning",
                        "message": "No content extracted from document"
                    })
                
                # Additional validation rules
                text_length = sum(len(elem.get("text", "")) for elem in elements)
                if text_length < 100:
                    validation_results.append({
                        "level": "warning",
                        "message": "Document contains very little text"
                    })
            
            result.extracted_data = {"validation_results": validation_results}
            result.metadata = {
                "valid": all(r["level"] != "error" for r in validation_results),
                "warning_count": sum(1 for r in validation_results if r["level"] == "warning"),
                "error_count": sum(1 for r in validation_results if r["level"] == "error")
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
        
        result.end_time = datetime.utcnow()
        return result

class TransformationProcessor(BaseProcessor):
    """Base processor for content transformation."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="transformation_processor",
            version="1.0.0",
            description="Transform document content",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.TRANSFORMATION],
            supported_formats=["*"],
            is_cpu_intensive=True,
            timeout_seconds=300
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Transform document content."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            # Get content from previous processor
            if "unstructured_processor" not in context.previous_results:
                raise ValueError("No content to transform")
            
            elements = context.previous_results["unstructured_processor"]["elements"]
            
            # Apply transformations based on config
            transformations = self.config.get("transformations", [])
            transformed_elements = elements.copy()
            
            for transform in transformations:
                if transform == "lowercase":
                    for elem in transformed_elements:
                        if "text" in elem:
                            elem["text"] = elem["text"].lower()
                elif transform == "remove_whitespace":
                    for elem in transformed_elements:
                        if "text" in elem:
                            elem["text"] = " ".join(elem["text"].split())
                # Add more transformations as needed
            
            result.extracted_data = {"elements": transformed_elements}
            result.metadata = {"transformations_applied": len(transformations)}
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
        
        result.end_time = datetime.utcnow()
        return result
```

### 4. Error Handling & Circuit Breaker (`src/torematrix/processing/processors/resilience.py`)

```python
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import logging

from .base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorResult,
    ProcessorException,
    ProcessorTimeoutError,
    StageStatus
)

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """
    Circuit breaker for processor fault tolerance.
    
    Prevents cascading failures by temporarily disabling
    failing processors.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_count = 0
        
        self._state_change_callbacks: List[Callable] = []
    
    def call_succeeded(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_count += 1
            if self.half_open_count >= self.half_open_requests:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def call_failed(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to new state."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.half_open_count = 0
            
            logger.info(f"Circuit breaker: {old_state.value} -> {new_state.value}")
            
            # Notify callbacks
            for callback in self._state_change_callbacks:
                callback(old_state, new_state)
    
    def add_state_change_callback(self, callback: Callable):
        """Add callback for state changes."""
        self._state_change_callbacks.append(callback)
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

class ResilientProcessor(BaseProcessor):
    """
    Wrapper that adds resilience features to any processor.
    
    Features:
    - Circuit breaker
    - Retry logic
    - Timeout enforcement
    - Fallback handling
    """
    
    def __init__(
        self,
        processor: BaseProcessor,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        fallback_processor: Optional[BaseProcessor] = None
    ):
        super().__init__(processor.config)
        self.processor = processor
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout or processor.get_metadata().timeout_seconds
        self.fallback_processor = fallback_processor
        
        # Metrics
        self._retry_metrics = deque(maxlen=100)
        self._timeout_metrics = deque(maxlen=100)
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        # This would be dynamically generated from wrapped processor
        raise NotImplementedError("Use wrapped processor metadata")
    
    async def initialize(self) -> None:
        """Initialize wrapped processor."""
        await self.processor.initialize()
        if self.fallback_processor:
            await self.fallback_processor.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process with resilience features."""
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN for {self.processor.get_metadata().name}")
            
            # Use fallback if available
            if self.fallback_processor:
                return await self.fallback_processor.process(context)
            
            # Return failure
            return ProcessorResult(
                processor_name=self.processor.get_metadata().name,
                status=StageStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                errors=["Circuit breaker is OPEN"]
            )
        
        # Try processing with retries
        last_error = None
        for attempt in range(self.retry_count):
            try:
                # Process with timeout
                result = await asyncio.wait_for(
                    self.processor.process(context),
                    timeout=self.timeout
                )
                
                # Success
                self.circuit_breaker.call_succeeded()
                return result
                
            except asyncio.TimeoutError:
                last_error = ProcessorTimeoutError(
                    f"Processor timed out after {self.timeout}s"
                )
                self._timeout_metrics.append(datetime.utcnow())
                logger.warning(f"Timeout on attempt {attempt + 1}")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except last attempt)
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                self._retry_metrics.append(datetime.utcnow())
        
        # All retries failed
        self.circuit_breaker.call_failed()
        
        # Try fallback
        if self.fallback_processor:
            logger.info("Using fallback processor")
            try:
                return await self.fallback_processor.process(context)
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        # Return failure
        return ProcessorResult(
            processor_name=self.processor.get_metadata().name,
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            errors=[str(last_error)] if last_error else ["Processing failed"]
        )
    
    async def cleanup(self) -> None:
        """Cleanup wrapped processors."""
        await self.processor.cleanup()
        if self.fallback_processor:
            await self.fallback_processor.cleanup()
    
    def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get resilience-related metrics."""
        now = datetime.utcnow()
        
        # Calculate retry rate (last minute)
        recent_retries = [
            t for t in self._retry_metrics
            if now - t < timedelta(minutes=1)
        ]
        
        # Calculate timeout rate (last minute)
        recent_timeouts = [
            t for t in self._timeout_metrics
            if now - t < timedelta(minutes=1)
        ]
        
        return {
            "circuit_breaker": self.circuit_breaker.get_state_info(),
            "retry_rate_per_minute": len(recent_retries),
            "timeout_rate_per_minute": len(recent_timeouts),
            "total_retries": len(self._retry_metrics),
            "total_timeouts": len(self._timeout_metrics)
        }

class ProcessorChain:
    """
    Chain multiple processors with fallback support.
    
    Tries processors in order until one succeeds.
    """
    
    def __init__(self, processors: List[BaseProcessor]):
        if not processors:
            raise ValueError("At least one processor required")
        
        self.processors = processors
    
    async def initialize(self):
        """Initialize all processors in chain."""
        for processor in self.processors:
            await processor.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process using chain of processors."""
        errors = []
        
        for i, processor in enumerate(self.processors):
            try:
                logger.info(f"Trying processor {i + 1}/{len(self.processors)}: {processor.get_metadata().name}")
                result = await processor.process(context)
                
                if result.status == StageStatus.COMPLETED:
                    return result
                
                errors.extend(result.errors)
                
            except Exception as e:
                errors.append(f"{processor.get_metadata().name}: {str(e)}")
                logger.error(f"Processor {processor.get_metadata().name} failed: {e}")
        
        # All processors failed
        return ProcessorResult(
            processor_name="processor_chain",
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            errors=errors
        )
    
    async def cleanup(self):
        """Cleanup all processors."""
        for processor in self.processors:
            await processor.cleanup()
```

### 5. Processor Monitoring (`src/torematrix/processing/processors/monitoring.py`)

```python
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import logging
from dataclasses import dataclass, field

from .base import BaseProcessor, ProcessorMetadata
from .registry import ProcessorRegistry

logger = logging.getLogger(__name__)

@dataclass
class ProcessorMetrics:
    """Metrics for a single processor."""
    name: str
    total_processed: int = 0
    total_failed: int = 0
    total_duration: float = 0.0
    
    # Recent performance (sliding window)
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Resource usage
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.total_processed + self.total_failed
        return self.total_processed / total if total > 0 else 0.0
    
    @property
    def average_duration(self) -> float:
        return self.total_duration / self.total_processed if self.total_processed > 0 else 0.0
    
    @property
    def recent_average_duration(self) -> float:
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)
    
    def record_success(self, duration: float):
        """Record successful processing."""
        self.total_processed += 1
        self.total_duration += duration
        self.recent_durations.append(duration)
    
    def record_failure(self):
        """Record failed processing."""
        self.total_failed += 1
        self.recent_failures.append(datetime.utcnow())
    
    def get_failure_rate(self, minutes: int = 5) -> float:
        """Get failure rate over recent time period."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent = sum(1 for t in self.recent_failures if t > cutoff)
        return recent / minutes

class ProcessorMonitor:
    """
    Monitors processor performance and health.
    
    Collects metrics, tracks performance trends, and provides
    insights for optimization.
    """
    
    def __init__(self, registry: ProcessorRegistry):
        self.registry = registry
        self.metrics: Dict[str, ProcessorMetrics] = defaultdict(ProcessorMetrics)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Alerts
        self._alert_handlers: List[Callable] = []
        self._alert_thresholds = {
            "failure_rate": 0.1,  # 10% failure rate
            "average_duration": 60.0,  # 60 second average
            "memory_mb": 1024,  # 1GB memory
        }
    
    async def start(self):
        """Start monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        
        # Register hooks with registry
        self.registry.add_load_hook(self._on_processor_loaded)
        
        logger.info("Processor monitor started")
    
    async def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Processor monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect metrics from all processors
                for name in self.registry.list_processors():
                    try:
                        processor = await self.registry.get_processor(name)
                        metrics = processor.get_metrics()
                        
                        # Update our metrics
                        proc_metrics = self.metrics[name]
                        proc_metrics.name = name
                        
                        # Check for alerts
                        await self._check_alerts(name, proc_metrics)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring processor {name}: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(10)
    
    def _on_processor_loaded(self, name: str, processor_class: type):
        """Handle new processor loaded."""
        self.metrics[name] = ProcessorMetrics(name=name)
    
    def record_processing(
        self,
        processor_name: str,
        success: bool,
        duration: float,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None
    ):
        """Record processing metrics."""
        metrics = self.metrics[processor_name]
        
        if success:
            metrics.record_success(duration)
        else:
            metrics.record_failure()
        
        # Update resource usage
        if memory_mb and memory_mb > metrics.peak_memory_mb:
            metrics.peak_memory_mb = memory_mb
        
        if cpu_percent and cpu_percent > metrics.peak_cpu_percent:
            metrics.peak_cpu_percent = cpu_percent
    
    async def _check_alerts(self, processor_name: str, metrics: ProcessorMetrics):
        """Check if alerts should be triggered."""
        alerts = []
        
        # Check failure rate
        failure_rate = metrics.get_failure_rate()
        if failure_rate > self._alert_thresholds["failure_rate"]:
            alerts.append({
                "type": "high_failure_rate",
                "processor": processor_name,
                "value": failure_rate,
                "threshold": self._alert_thresholds["failure_rate"]
            })
        
        # Check average duration
        avg_duration = metrics.recent_average_duration
        if avg_duration > self._alert_thresholds["average_duration"]:
            alerts.append({
                "type": "slow_processing",
                "processor": processor_name,
                "value": avg_duration,
                "threshold": self._alert_thresholds["average_duration"]
            })
        
        # Check memory usage
        if metrics.peak_memory_mb > self._alert_thresholds["memory_mb"]:
            alerts.append({
                "type": "high_memory_usage",
                "processor": processor_name,
                "value": metrics.peak_memory_mb,
                "threshold": self._alert_thresholds["memory_mb"]
            })
        
        # Trigger alerts
        for alert in alerts:
            await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger an alert."""
        logger.warning(f"Alert: {alert}")
        
        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler."""
        self._alert_handlers.append(handler)
    
    def set_alert_threshold(self, alert_type: str, threshold: float):
        """Set alert threshold."""
        self._alert_thresholds[alert_type] = threshold
    
    def get_processor_metrics(self, processor_name: str) -> Optional[ProcessorMetrics]:
        """Get metrics for a specific processor."""
        return self.metrics.get(processor_name)
    
    def get_all_metrics(self) -> Dict[str, ProcessorMetrics]:
        """Get all processor metrics."""
        return dict(self.metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all processors."""
        total_processed = sum(m.total_processed for m in self.metrics.values())
        total_failed = sum(m.total_failed for m in self.metrics.values())
        
        return {
            "processor_count": len(self.metrics),
            "total_processed": total_processed,
            "total_failed": total_failed,
            "overall_success_rate": total_processed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0.0,
            "processors": {
                name: {
                    "processed": metrics.total_processed,
                    "failed": metrics.total_failed,
                    "success_rate": metrics.success_rate,
                    "avg_duration": metrics.average_duration,
                    "recent_avg_duration": metrics.recent_average_duration
                }
                for name, metrics in self.metrics.items()
            }
        }

# Decorators for automatic monitoring
def monitor_processor(monitor: ProcessorMonitor):
    """Decorator to automatically monitor processor execution."""
    def decorator(processor_class: Type[BaseProcessor]):
        original_process = processor_class.process
        
        async def monitored_process(self, context: ProcessorContext) -> ProcessorResult:
            start_time = datetime.utcnow()
            success = False
            
            try:
                result = await original_process(self, context)
                success = result.status == StageStatus.COMPLETED
                return result
            finally:
                duration = (datetime.utcnow() - start_time).total_seconds()
                monitor.record_processing(
                    self.get_metadata().name,
                    success,
                    duration
                )
        
        processor_class.process = monitored_process
        return processor_class
    
    return decorator
```

### 6. Unit Tests (`tests/unit/processing/processors/test_registry.py`)

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus
)
from torematrix.processing.processors.registry import ProcessorRegistry
from torematrix.processing.processors.resilience import (
    CircuitBreaker,
    CircuitState,
    ResilientProcessor
)

class TestProcessor(BaseProcessor):
    """Test processor for unit tests."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="test_processor",
            version="1.0.0",
            description="Test processor",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION],
            supported_formats=["txt", "pdf"]
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"test": True}
        )

class FailingProcessor(BaseProcessor):
    """Test processor that always fails."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="failing_processor",
            version="1.0.0",
            description="Always fails"
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        raise Exception("Test failure")

@pytest.fixture
async def registry():
    """Create processor registry."""
    return ProcessorRegistry()

@pytest.fixture
async def test_context():
    """Create test context."""
    return ProcessorContext(
        document_id="doc123",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf"
    )

class TestProcessorRegistry:
    """Test cases for ProcessorRegistry."""
    
    async def test_register_processor(self, registry):
        """Test processor registration."""
        registry.register(TestProcessor)
        
        assert "test_processor" in registry.list_processors()
        assert registry.get_metadata("test_processor").name == "test_processor"
    
    async def test_get_processor_instance(self, registry):
        """Test getting processor instance."""
        registry.register(TestProcessor)
        
        processor = await registry.get_processor("test_processor")
        assert isinstance(processor, TestProcessor)
        assert processor._initialized
    
    async def test_singleton_behavior(self, registry):
        """Test singleton behavior for same config."""
        registry.register(TestProcessor)
        
        proc1 = await registry.get_processor("test_processor", {"key": "value"})
        proc2 = await registry.get_processor("test_processor", {"key": "value"})
        
        # Should be same instance
        assert proc1 is proc2
        
        # Different config should create new instance
        proc3 = await registry.get_processor("test_processor", {"key": "different"})
        assert proc3 is not proc1
    
    async def test_find_by_capability(self, registry):
        """Test finding processors by capability."""
        registry.register(TestProcessor)
        
        processors = registry.find_by_capability(ProcessorCapability.TEXT_EXTRACTION)
        assert "test_processor" in processors
        
        processors = registry.find_by_capability(ProcessorCapability.OCR)
        assert "test_processor" not in processors
    
    async def test_find_by_format(self, registry):
        """Test finding processors by format."""
        registry.register(TestProcessor)
        
        processors = registry.find_by_format("pdf")
        assert "test_processor" in processors
        
        processors = registry.find_by_format("docx")
        assert "test_processor" not in processors
    
    async def test_dependency_injection(self, registry):
        """Test dependency injection."""
        registry.register(TestProcessor)
        
        # Register dependency
        mock_client = Mock()
        registry.register_dependency("test_client", mock_client)
        
        processor = await registry.get_processor("test_processor")
        
        # Check if dependency would be injected
        # (would need to add _inject_test_client to TestProcessor)
    
    async def test_load_hook(self, registry):
        """Test load hooks."""
        hook_called = False
        def load_hook(name, processor_class):
            nonlocal hook_called
            hook_called = True
        
        registry.add_load_hook(load_hook)
        registry.register(TestProcessor)
        
        assert hook_called
    
    async def test_shutdown(self, registry):
        """Test registry shutdown."""
        registry.register(TestProcessor)
        
        processor = await registry.get_processor("test_processor")
        
        await registry.shutdown()
        
        # All instances should be cleaned up
        assert len(registry._instances) == 0

class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        cb = CircuitBreaker(failure_threshold=3)
        
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()
    
    def test_open_on_threshold(self):
        """Test circuit opens on failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record failures
        cb.call_failed()
        cb.call_failed()
        assert cb.state == CircuitState.CLOSED
        
        cb.call_failed()  # Third failure
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()
    
    def test_half_open_after_timeout(self):
        """Test circuit goes to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
        
        # Should immediately go to half-open
        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_close_on_success(self):
        """Test circuit closes on successful calls."""
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0,
            half_open_requests=2
        )
        
        # Open circuit
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
        
        # Go to half-open
        cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Successful calls
        cb.call_succeeded()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.call_succeeded()  # Second success
        assert cb.state == CircuitState.CLOSED

class TestResilientProcessor:
    """Test cases for ResilientProcessor."""
    
    async def test_successful_processing(self, test_context):
        """Test successful processing through resilient wrapper."""
        base_processor = TestProcessor()
        resilient = ResilientProcessor(base_processor)
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert resilient.circuit_breaker.state == CircuitState.CLOSED
    
    async def test_retry_on_failure(self, test_context):
        """Test retry logic."""
        base_processor = Mock(spec=BaseProcessor)
        base_processor.get_metadata.return_value = ProcessorMetadata(
            name="test",
            version="1.0",
            description="Test"
        )
        base_processor.process = AsyncMock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            ProcessorResult(
                processor_name="test",
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
        ])
        
        resilient = ResilientProcessor(
            base_processor,
            retry_count=3,
            retry_delay=0.01
        )
        
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert base_processor.process.call_count == 3
    
    async def test_circuit_breaker_integration(self, test_context):
        """Test circuit breaker integration."""
        base_processor = FailingProcessor()
        cb = CircuitBreaker(failure_threshold=2)
        resilient = ResilientProcessor(
            base_processor,
            circuit_breaker=cb,
            retry_count=1
        )
        
        # First failure
        result1 = await resilient.process(test_context)
        assert result1.status == StageStatus.FAILED
        assert cb.state == CircuitState.CLOSED
        
        # Second failure opens circuit
        result2 = await resilient.process(test_context)
        assert result2.status == StageStatus.FAILED
        assert cb.state == CircuitState.OPEN
        
        # Third attempt blocked by circuit
        result3 = await resilient.process(test_context)
        assert result3.status == StageStatus.FAILED
        assert "Circuit breaker is OPEN" in result3.errors
    
    async def test_timeout_handling(self, test_context):
        """Test timeout handling."""
        base_processor = Mock(spec=BaseProcessor)
        base_processor.get_metadata.return_value = ProcessorMetadata(
            name="test",
            version="1.0",
            description="Test"
        )
        
        # Simulate slow processing
        async def slow_process(context):
            await asyncio.sleep(1)
            return ProcessorResult(
                processor_name="test",
                status=StageStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
        
        base_processor.process = slow_process
        
        resilient = ResilientProcessor(
            base_processor,
            timeout=0.1,
            retry_count=1
        )
        
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.FAILED
        assert any("timed out" in err for err in result.errors)
```

## Dependencies You Can Use
- From Issue #6 (Unstructured.io Integration):
  - `UnstructuredClient` - Primary processor implementation
  - `UnstructuredConfig` - Configuration
  - Unstructured processing capabilities
- From Issue #8.1 (Pipeline Manager):
  - Stage interfaces and base classes
  - Pipeline context structures

## Important Notes
1. **Plugin Architecture**: Support dynamic loading and hot-swapping
2. **Standardized Interface**: All processors follow same interface
3. **Error Resilience**: Circuit breakers and retry logic
4. **Performance Monitoring**: Track metrics for optimization
5. **Dependency Injection**: Support for shared resources
6. **Async Throughout**: All processing must be async

## Testing Requirements
- Unit tests for registry operations
- Test processor lifecycle management
- Test circuit breaker states
- Test retry and timeout handling
- Mock processor implementations
- Test monitoring and metrics

## Coordination
- Agent 1's pipeline manager will execute your processors
- Agent 3 will monitor your processor metrics
- Agent 4 will integrate everything together

## Success Criteria
- [ ] Complete processor plugin interface
- [ ] Dynamic loading and registration working
- [ ] Circuit breaker implementation tested
- [ ] Built-in processors for common tasks
- [ ] Monitoring and metrics collection
- [ ] 90%+ test coverage

Start with the base processor interface, then implement the registry, add resilience features, and finally create the built-in processors. Focus on extensibility and reliability.