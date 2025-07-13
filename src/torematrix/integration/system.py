"""
TORE Matrix V3 Processing System

This is the main integration class that connects all components together
into a cohesive document processing system.
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass

# Import adapters and coordinators
from .adapters import (
    EventBusAdapter,
    StorageAdapter,
    StateAdapter,
    ConfigAdapter
)
from .coordinator import EventFlowCoordinator, ProcessingStage
from .transformer import DataTransformer

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """System operational status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SystemConfig:
    """Configuration for the TORE Matrix system."""
    # Core settings
    name: str = "TORE Matrix V3"
    version: str = "3.0.0"
    
    # Component settings
    enable_monitoring: bool = True
    enable_checkpoints: bool = True
    checkpoint_interval: int = 60  # seconds
    
    # Processing settings
    max_concurrent_documents: int = 100
    processing_timeout: int = 300  # seconds
    retry_failed_documents: bool = True
    max_retries: int = 3
    
    # Storage settings
    storage_backend: str = "sqlite"
    storage_path: str = "./data/torematrix.db"
    
    # Worker settings
    worker_pool_size: int = 4
    worker_type: str = "async"  # async, thread, process
    
    # Pipeline settings
    default_pipeline: str = "standard"
    enable_ocr: bool = True
    enable_translation: bool = False
    
    # Resource limits
    max_memory_mb: int = 4096
    max_cpu_percent: float = 80.0


class ToreMatrixSystem:
    """
    Master integration class for TORE Matrix V3.
    
    This class orchestrates all components to provide a unified
    document processing system.
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize the TORE Matrix system.
        
        Args:
            config: System configuration (uses defaults if None)
        """
        self.config = config or SystemConfig()
        self.status = SystemStatus.INITIALIZING
        
        # Component instances (to be initialized)
        self.event_bus = None
        self.storage = None
        self.state = None
        self.config_manager = None
        self.pipeline = None
        self.ingestion = None
        self.unstructured = None
        self.monitoring = None
        
        # Integration components
        self.event_coordinator = None
        self.data_transformer = DataTransformer()
        
        # Tracking
        self._active_documents = set()
        self._start_time = None
        self._processed_count = 0
        
        logger.info(f"Initializing {self.config.name} v{self.config.version}")
    
    async def initialize(self):
        """
        Initialize all system components.
        
        This method sets up all components with proper dependency injection
        and ensures they can communicate with each other.
        """
        try:
            # 1. Initialize core infrastructure
            await self._initialize_core()
            
            # 2. Initialize document processing components
            await self._initialize_processing()
            
            # 3. Wire up event flows
            await self._setup_event_flows()
            
            # 4. Start monitoring if enabled
            if self.config.enable_monitoring:
                await self._start_monitoring()
            
            self.status = SystemStatus.RUNNING
            self._start_time = datetime.utcnow()
            
            logger.info("TORE Matrix system initialized successfully")
            
            # Emit system started event
            await self.event_bus.emit(
                "system.started",
                {
                    "version": self.config.version,
                    "config": self._get_config_summary()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}", exc_info=True)
            self.status = SystemStatus.ERROR
            raise
    
    async def _initialize_core(self):
        """Initialize core infrastructure components."""
        logger.info("Initializing core infrastructure...")
        
        # Initialize EventBus
        from torematrix.core.events import EventBus
        raw_event_bus = EventBus()
        self.event_bus = EventBusAdapter(raw_event_bus)
        
        # Initialize Configuration
        try:
            from torematrix.core.config import ConfigManager
            raw_config = ConfigManager()
        except:
            # Fallback to dict-based config
            raw_config = self._create_config_dict()
        
        self.config_manager = ConfigAdapter(raw_config)
        self._apply_configuration()
        
        # Initialize State Management
        try:
            from torematrix.core.state import Store
            raw_state = Store(initial_state={"documents": {}, "system": {}})
        except:
            # Fallback to simple state
            raw_state = {"documents": {}, "system": {}}
        
        self.state = StateAdapter(raw_state)
        
        # Initialize Storage
        await self._initialize_storage()
    
    async def _initialize_storage(self):
        """Initialize storage backend."""
        logger.info(f"Initializing storage backend: {self.config.storage_backend}")
        
        try:
            from torematrix.core.storage import StorageFactory, StorageConfig
            
            storage_config = StorageConfig(
                backend_type=self.config.storage_backend,
                connection_string=f"{self.config.storage_backend}:///{self.config.storage_path}"
            )
            
            raw_storage = StorageFactory.create_storage(storage_config)
        except:
            # Fallback to simple storage
            logger.warning("Using fallback storage implementation")
            raw_storage = self._create_fallback_storage()
        
        self.storage = StorageAdapter(raw_storage)
    
    async def _initialize_processing(self):
        """Initialize document processing components."""
        logger.info("Initializing processing components...")
        
        # Initialize Unstructured integration
        try:
            from torematrix.integrations.unstructured import UnstructuredClient
            self.unstructured = UnstructuredClient()
        except:
            logger.warning("Unstructured integration not available")
            self.unstructured = None
        
        # Initialize Ingestion system
        try:
            from torematrix.ingestion import UploadManager, QueueManager
            self.ingestion = {
                "upload": UploadManager(),
                "queue": QueueManager()
            }
        except:
            logger.warning("Ingestion system not available")
            self.ingestion = None
        
        # Initialize Pipeline
        try:
            from torematrix.processing.pipeline import (
                PipelineManager,
                create_pipeline_from_template
            )
            
            # Create pipeline configuration
            pipeline_config = create_pipeline_from_template(
                self.config.default_pipeline,
                enable_ocr=self.config.enable_ocr,
                enable_translation=self.config.enable_translation
            )
            
            # Create pipeline manager
            self.pipeline = PipelineManager(
                config=pipeline_config,
                event_bus=self.event_bus.event_bus,  # Use raw event bus
                state_store=self.state.store if hasattr(self.state, 'store') else None
            )
        except Exception as e:
            logger.warning(f"Pipeline initialization failed: {e}")
            self.pipeline = None
    
    async def _setup_event_flows(self):
        """Setup event flow coordination."""
        logger.info("Setting up event flows...")
        
        # Create event coordinator
        self.event_coordinator = EventFlowCoordinator(
            event_bus=self.event_bus,
            data_transformer=self.data_transformer
        )
        
        # Register system-level event handlers
        self.event_bus.subscribe("document.completed", self._handle_document_completed)
        self.event_bus.subscribe("document.failed", self._handle_document_failed)
        self.event_bus.subscribe("system.shutdown", self._handle_shutdown)
    
    async def _start_monitoring(self):
        """Start monitoring service."""
        try:
            from torematrix.processing.monitoring import MonitoringService
            self.monitoring = MonitoringService(self.event_bus.event_bus)
            await self.monitoring.start()
            logger.info("Monitoring service started")
        except:
            logger.warning("Monitoring service not available")
    
    def _apply_configuration(self):
        """Apply configuration to all components."""
        config_dict = {
            "system": {
                "name": self.config.name,
                "version": self.config.version
            },
            "storage": {
                "backend": self.config.storage_backend,
                "path": self.config.storage_path
            },
            "pipeline": {
                "default": self.config.default_pipeline,
                "max_parallel": self.config.worker_pool_size,
                "timeout": self.config.processing_timeout
            },
            "processing": {
                "max_concurrent": self.config.max_concurrent_documents,
                "enable_ocr": self.config.enable_ocr,
                "enable_translation": self.config.enable_translation
            },
            "resources": {
                "max_memory_mb": self.config.max_memory_mb,
                "max_cpu_percent": self.config.max_cpu_percent
            }
        }
        
        self.config_manager.load_from_dict(config_dict)
    
    # Document Processing Methods
    
    async def process_document(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        pipeline: Optional[str] = None,
        priority: str = "normal"
    ) -> str:
        """
        Process a document through the system.
        
        Args:
            file_path: Path to the document file
            metadata: Optional metadata for the document
            pipeline: Pipeline to use (defaults to configured pipeline)
            priority: Processing priority (immediate, high, normal, low)
            
        Returns:
            Document ID for tracking
        """
        if self.status != SystemStatus.RUNNING:
            raise RuntimeError(f"System is not running (status: {self.status})")
        
        # Generate document ID
        doc_id = self._generate_document_id()
        
        # Check concurrent limit
        if len(self._active_documents) >= self.config.max_concurrent_documents:
            raise RuntimeError(f"Maximum concurrent documents ({self.config.max_concurrent_documents}) reached")
        
        self._active_documents.add(doc_id)
        
        # Prepare metadata
        doc_metadata = {
            "id": doc_id,
            "file_path": str(file_path),
            "original_name": Path(file_path).name,
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline": pipeline or self.config.default_pipeline,
            "priority": priority,
            **(metadata or {})
        }
        
        # Emit document uploaded event to start processing
        await self.event_bus.emit(
            "document.uploaded",
            doc_metadata,
            priority=priority
        )
        
        logger.info(f"Document {doc_id} submitted for processing: {Path(file_path).name}")
        
        return doc_id
    
    async def process_batch(
        self,
        file_paths: List[Union[str, Path]],
        metadata: Optional[Dict[str, Any]] = None,
        pipeline: Optional[str] = None
    ) -> List[str]:
        """
        Process a batch of documents.
        
        Returns:
            List of document IDs
        """
        doc_ids = []
        
        for file_path in file_paths:
            try:
                doc_id = await self.process_document(
                    file_path=file_path,
                    metadata=metadata,
                    pipeline=pipeline
                )
                doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to submit {file_path}: {e}")
        
        return doc_ids
    
    def get_document_status(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a document."""
        state = self.event_coordinator.get_document_state(doc_id)
        
        if state:
            return {
                "id": doc_id,
                "status": state.value,
                "active": doc_id in self._active_documents
            }
        
        return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and statistics."""
        uptime = None
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "status": self.status.value,
            "version": self.config.version,
            "uptime_seconds": uptime,
            "active_documents": len(self._active_documents),
            "total_processed": self._processed_count,
            "configuration": self._get_config_summary()
        }
    
    async def pause(self):
        """Pause document processing."""
        if self.status == SystemStatus.RUNNING:
            self.status = SystemStatus.PAUSED
            await self.event_bus.emit("system.paused", {})
            logger.info("System paused")
    
    async def resume(self):
        """Resume document processing."""
        if self.status == SystemStatus.PAUSED:
            self.status = SystemStatus.RUNNING
            await self.event_bus.emit("system.resumed", {})
            logger.info("System resumed")
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        logger.info("Shutting down TORE Matrix system...")
        self.status = SystemStatus.STOPPING
        
        # Emit shutdown event
        await self.event_bus.emit("system.shutdown", {})
        
        # Wait for active documents to complete (with timeout)
        timeout = 30  # seconds
        start = datetime.utcnow()
        
        while self._active_documents and (datetime.utcnow() - start).total_seconds() < timeout:
            await asyncio.sleep(1)
        
        if self._active_documents:
            logger.warning(f"Shutting down with {len(self._active_documents)} active documents")
        
        # Stop components
        if self.monitoring:
            await self.monitoring.stop()
        
        await self.event_bus.stop()
        
        self.status = SystemStatus.STOPPED
        logger.info("System shutdown complete")
    
    # Event Handlers
    
    async def _handle_document_completed(self, event: Any):
        """Handle document completion."""
        data = self.event_coordinator._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id and doc_id in self._active_documents:
            self._active_documents.remove(doc_id)
            self._processed_count += 1
            
            logger.info(f"Document {doc_id} completed. Total processed: {self._processed_count}")
    
    async def _handle_document_failed(self, event: Any):
        """Handle document failure."""
        data = self.event_coordinator._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id and doc_id in self._active_documents:
            self._active_documents.remove(doc_id)
            
            # Check if we should retry
            if self.config.retry_failed_documents:
                retry_count = data.get('retry_count', 0)
                if retry_count < self.config.max_retries:
                    logger.info(f"Retrying document {doc_id} (attempt {retry_count + 1})")
                    # Re-emit upload event with retry count
                    metadata = data.get('metadata', {})
                    metadata['retry_count'] = retry_count + 1
                    
                    await self.event_bus.emit(
                        "document.uploaded",
                        metadata
                    )
    
    async def _handle_shutdown(self, event: Any):
        """Handle shutdown request."""
        await self.shutdown()
    
    # Helper Methods
    
    def _generate_document_id(self) -> str:
        """Generate unique document ID."""
        import uuid
        return f"doc_{uuid.uuid4().hex[:12]}"
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        return {
            "storage_backend": self.config.storage_backend,
            "default_pipeline": self.config.default_pipeline,
            "max_concurrent": self.config.max_concurrent_documents,
            "worker_pool_size": self.config.worker_pool_size,
            "enable_ocr": self.config.enable_ocr,
            "enable_monitoring": self.config.enable_monitoring
        }
    
    def _create_config_dict(self) -> Dict[str, Any]:
        """Create fallback configuration dictionary."""
        return {
            "system": {},
            "storage": {},
            "pipeline": {},
            "processing": {}
        }
    
    def _create_fallback_storage(self):
        """Create fallback storage implementation."""
        class FallbackStorage:
            def __init__(self):
                self.data = {}
            
            async def create(self, element):
                element_id = element.get('id', self._generate_id())
                self.data[element_id] = element
                return element_id
            
            async def get(self, element_id):
                return self.data.get(element_id)
            
            async def query(self, filter_dict):
                # Simple filtering
                results = []
                for item in self.data.values():
                    match = True
                    for key, value in filter_dict.items():
                        if item.get(key) != value:
                            match = False
                            break
                    if match:
                        results.append(item)
                return results
            
            async def update(self, element_id, updates):
                if element_id in self.data:
                    self.data[element_id].update(updates)
                    return True
                return False
            
            async def delete(self, element_id):
                if element_id in self.data:
                    del self.data[element_id]
                    return True
                return False
            
            def _generate_id(self):
                import uuid
                return str(uuid.uuid4())
        
        return FallbackStorage()


# Convenience function
async def create_system(config: Optional[SystemConfig] = None) -> ToreMatrixSystem:
    """
    Create and initialize a TORE Matrix system.
    
    Args:
        config: Optional system configuration
        
    Returns:
        Initialized ToreMatrixSystem instance
    """
    system = ToreMatrixSystem(config)
    await system.initialize()
    return system