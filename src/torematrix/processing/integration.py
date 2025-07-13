"""
Processing System Integration Module

This module provides the main integration point for the document processing pipeline,
coordinating all components and providing a unified interface.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from .pipeline.manager import PipelineManager, PipelineConfig
from .processors.registry import ProcessorRegistry
from .workers.pool import WorkerPool, WorkerConfig
from .workers.progress import ProgressTracker
from .workers.resources import ResourceMonitor, ResourceLimits
from ..core.events.event_bus import EventBus
from .pipeline.state_store import StateStore
from ..integrations.unstructured.client import UnstructuredClient
from ..integrations.unstructured.config import UnstructuredConfig

logger = logging.getLogger(__name__)

@dataclass
class ProcessingSystemConfig:
    """Configuration for the entire processing system."""
    pipeline_config: PipelineConfig
    worker_config: WorkerConfig
    resource_limits: ResourceLimits
    monitoring_enabled: bool = True
    state_persistence_enabled: bool = True
    state_store_path: Optional[Path] = None
    unstructured_config: Optional[UnstructuredConfig] = None

class ProcessingSystem:
    """
    Main integration point for the document processing pipeline.
    
    Coordinates all components and provides a unified interface for:
    - Document processing through pipelines
    - Worker pool management
    - Progress tracking
    - Resource monitoring
    - System health checks
    """
    
    def __init__(self, config: ProcessingSystemConfig):
        self.config = config
        
        # Core components
        self.event_bus = EventBus()
        self.state_store = StateStore()
        
        # Resource management
        self.resource_monitor = ResourceMonitor(
            limits=config.resource_limits
        )
        
        # Processing components
        self.processor_registry = ProcessorRegistry()
        self.progress_tracker = ProgressTracker(None)  # Will set event_bus in initialize()
        
        self.worker_pool = WorkerPool(
            config=config.worker_config,
            event_bus=self.event_bus,
            resource_monitor=self.resource_monitor
        )
        
        self.pipeline_manager = PipelineManager(
            config=config.pipeline_config,
            event_bus=self.event_bus,
            state_store=self.state_store,
            resource_monitor=self.resource_monitor
        )
        
        # Monitoring
        self.monitoring = None
        if config.monitoring_enabled:
            from .monitoring import MonitoringService
            self.monitoring = MonitoringService(
                event_bus=self.event_bus,
                components={
                    "pipeline": self.pipeline_manager,
                    "workers": self.worker_pool,
                    "resources": self.resource_monitor,
                    "progress": self.progress_tracker
                }
            )
        
        self._running = False
        self._initialization_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize all components."""
        async with self._initialization_lock:
            if self._running:
                return
            
            logger.info("Initializing processing system...")
            
            try:
                # Set event bus for progress tracker now that event loop is running
                self.progress_tracker.event_bus = self.event_bus
                if hasattr(self.progress_tracker, '_subscribe_to_events'):
                    asyncio.create_task(self.progress_tracker._subscribe_to_events())
                
                # Register built-in processors
                await self._register_processors()
                
                # Start core services
                await self.resource_monitor.start()
                await self.worker_pool.start()
                
                if self.monitoring:
                    await self.monitoring.start()
                
                # Load persisted state (StateStore is ready to use)
                
                self._running = True
                logger.info("Processing system initialized successfully")
                
                # Emit system started event
                from ..core.events.event_types import Event
                event = Event(
                    event_type="system_started",
                    payload={
                        "config": self.config.dict() if hasattr(self.config, 'dict') else str(self.config),
                        "timestamp": str(asyncio.get_event_loop().time())
                    },
                    id=f"system_started_{int(asyncio.get_event_loop().time())}"
                )
                await self.event_bus.publish(event)
                
            except Exception as e:
                logger.error(f"Failed to initialize processing system: {e}")
                await self._cleanup_on_error()
                raise
    
    async def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("Shutting down processing system...")
        
        try:
            self._running = False
            
            # Stop accepting new work
            if hasattr(self.pipeline_manager, 'pause_all'):
                await self.pipeline_manager.pause_all()
            
            # Wait for active tasks to complete
            await self.worker_pool.wait_for_completion(timeout=60.0)
            
            # Shutdown components in order
            await self.worker_pool.stop(timeout=60.0)
            await self.resource_monitor.stop()
            
            if self.monitoring:
                await self.monitoring.stop()
            
            # Persist state (no specific save method needed for simple StateStore)
            
            # Cleanup processor registry
            await self.processor_registry.shutdown()
            
            logger.info("Processing system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
    
    async def process_document(
        self,
        document_path: Path,
        pipeline_name: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a document through the pipeline.
        
        Args:
            document_path: Path to the document to process
            pipeline_name: Name of the pipeline to use
            metadata: Additional metadata for processing
            
        Returns:
            Pipeline execution ID for tracking
            
        Raises:
            RuntimeError: If system not initialized
            ValueError: If document path invalid
        """
        if not self._running:
            raise RuntimeError("Processing system not initialized")
        
        if not document_path.exists():
            raise ValueError(f"Document not found: {document_path}")
        
        logger.info(f"Processing document: {document_path}")
        
        # Create pipeline context
        pipeline_id = await self.pipeline_manager.create_pipeline(
            document_id=str(document_path),
            metadata=metadata or {}
        )
        
        # Execute pipeline
        await self.pipeline_manager.execute(pipeline_id)
        
        return pipeline_id
    
    async def _register_processors(self):
        """Register all available processors."""
        from .processors.builtin import (
            UnstructuredProcessor,
            MetadataExtractorProcessor,
            ValidationProcessor,
            TransformationProcessor
        )
        
        # Register Unstructured.io processor
        if self.config.unstructured_config:
            unstructured_client = UnstructuredClient(self.config.unstructured_config)
            self.processor_registry.register_dependency(
                "unstructured_client", 
                unstructured_client
            )
        
        # Register built-in processors
        self.processor_registry.register(UnstructuredProcessor)
        self.processor_registry.register(MetadataExtractorProcessor)
        self.processor_registry.register(ValidationProcessor)
        self.processor_registry.register(TransformationProcessor)
        
        logger.info(f"Registered {len(self.processor_registry.list_processors())} processors")
    
    async def _cleanup_on_error(self):
        """Cleanup resources if initialization fails."""
        try:
            if self.monitoring:
                await self.monitoring.stop()
            if hasattr(self.worker_pool, '_running') and self.worker_pool._running:
                await self.worker_pool.stop()
            if hasattr(self.resource_monitor, '_monitoring') and self.resource_monitor._monitoring:
                await self.resource_monitor.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get current status of a pipeline execution."""
        return self.pipeline_manager.get_status(pipeline_id)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        return {
            "workers": self.worker_pool.get_stats(),
            "resources": self.resource_monitor.get_current_usage(),
            "pipelines": {"status": self.pipeline_manager.status.value},
            "processors": {
                "registered": len(self.processor_registry.list_processors()),
                "active": len(self.processor_registry._instances)
            },
            "progress": self.progress_tracker.get_statistics(),
            "system": {
                "running": self._running,
                "monitoring_enabled": self.config.monitoring_enabled
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        health_status = {
            "healthy": True,
            "services": {},
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        # Check core services
        health_status["services"]["worker_pool"] = {
            "healthy": getattr(self.worker_pool, '_running', False),
            "details": self.worker_pool.get_stats() if hasattr(self.worker_pool, 'get_stats') else {}
        }
        
        health_status["services"]["resource_monitor"] = {
            "healthy": getattr(self.resource_monitor, '_monitoring', False),
            "details": self.resource_monitor.get_current_usage()
        }
        
        health_status["services"]["pipeline_manager"] = {
            "healthy": self.pipeline_manager.status.value != "failed" if hasattr(self.pipeline_manager, 'status') else True,
            "details": {"status": getattr(self.pipeline_manager, 'status', 'unknown')}
        }
        
        # Check processor registry
        health_status["services"]["processor_registry"] = {
            "healthy": len(self.processor_registry.list_processors()) > 0,
            "details": {
                "registered_processors": len(self.processor_registry.list_processors()),
                "active_instances": len(self.processor_registry._instances)
            }
        }
        
        # Overall health
        health_status["healthy"] = all(
            service["healthy"] 
            for service in health_status["services"].values()
        )
        
        return health_status
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        if not self.monitoring:
            return {"error": "Monitoring not enabled"}
        
        return await self.monitoring.get_metrics_summary()
    
    @asynccontextmanager
    async def processing_context(self):
        """Context manager for using the processing system."""
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown()

# Helper functions for common configurations

def create_default_config(
    pipeline_name: str = "default",
    async_workers: int = 4,
    thread_workers: int = 2,
    max_cpu_percent: float = 80.0,
    max_memory_percent: float = 75.0
) -> ProcessingSystemConfig:
    """Create a default processing system configuration."""
    from .pipeline.config import PipelineConfig, StageConfig, StageType
    
    # Default pipeline with basic stages
    pipeline_config = PipelineConfig(
        name=pipeline_name,
        stages=[
            StageConfig(
                name="validation",
                type=StageType.VALIDATOR,
                processor="validation_processor",
                dependencies=[]
            ),
            StageConfig(
                name="extraction",
                type=StageType.PROCESSOR,
                processor="unstructured_processor",
                dependencies=["validation"]
            ),
            StageConfig(
                name="metadata",
                type=StageType.PROCESSOR,
                processor="metadata_extractor",
                dependencies=["extraction"]
            )
        ]
    )
    
    worker_config = WorkerConfig(
        async_workers=async_workers,
        thread_workers=thread_workers,
        max_queue_size=1000,
        default_timeout=300.0
    )
    
    resource_limits = ResourceLimits(
        max_cpu_percent=max_cpu_percent,
        max_memory_percent=max_memory_percent
    )
    
    return ProcessingSystemConfig(
        pipeline_config=pipeline_config,
        worker_config=worker_config,
        resource_limits=resource_limits,
        monitoring_enabled=True,
        state_persistence_enabled=True
    )

def create_high_throughput_config() -> ProcessingSystemConfig:
    """Create configuration optimized for high throughput."""
    return create_default_config(
        async_workers=8,
        thread_workers=4,
        max_cpu_percent=90.0,
        max_memory_percent=85.0
    )

def create_memory_efficient_config() -> ProcessingSystemConfig:
    """Create configuration optimized for memory efficiency."""
    return create_default_config(
        async_workers=2,
        thread_workers=1,
        max_cpu_percent=70.0,
        max_memory_percent=60.0
    )