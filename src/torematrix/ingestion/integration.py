"""
System Integration Layer for Document Ingestion.

This module provides the main IngestionSystem class that coordinates all components
from Agents 1-3 and integrates with the Unstructured.io client from Issue #6.
"""

from typing import Optional, Dict, Any, List
import asyncio
from pathlib import Path
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from ..integrations.unstructured.client import UnstructuredClient
from ..integrations.unstructured.config import UnstructuredConfig
from ..core.events import EventBus
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class IngestionSettings:
    """Configuration for the ingestion system."""
    
    # Database settings
    database_url: str = "sqlite:///data/torematrix.db"
    
    # Upload settings
    upload_dir: str = "/tmp/torematrix/uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = None
    
    # Queue settings
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "document_processing"
    max_workers: int = 5
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Storage settings
    s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"
    
    def __post_init__(self):
        """Set default allowed extensions if not provided."""
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".pdf", ".docx", ".doc", ".odt", ".rtf", ".txt",
                ".html", ".xml", ".json", ".csv", ".xlsx", ".xls",
                ".pptx", ".ppt", ".epub", ".md", ".rst"
            ]


class MockUploadManager:
    """Mock upload manager for when Agent 1's component isn't available."""
    
    def __init__(self, upload_dir: Path, max_file_size: int = 100 * 1024 * 1024):
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size
        self._sessions = {}
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Using MockUploadManager - Agent 1 component not available")
    
    async def create_session(self, user_id: str) -> Dict[str, Any]:
        """Create upload session."""
        session = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "files": [],
            "status": "active"
        }
        self._sessions[session["session_id"]] = session
        return session
    
    async def upload_file(self, session_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Mock file upload."""
        file_id = str(uuid.uuid4())
        file_path = self.upload_dir / f"{file_id}_{filename}"
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        result = {
            "file_id": file_id,
            "filename": filename,
            "size": len(file_data),
            "mime_type": "application/octet-stream",
            "validation_status": "valid",
            "errors": [],
            "storage_key": str(file_path)
        }
        
        if session_id in self._sessions:
            self._sessions[session_id]["files"].append(result)
        
        return result


class MockQueueManager:
    """Mock queue manager for when Agent 2's component isn't available."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._jobs = {}
        logger.info("Using MockQueueManager - Agent 2 component not available")
    
    async def initialize(self):
        """Initialize mock queue."""
        pass
    
    async def enqueue_file(self, file_metadata: Dict[str, Any], priority: bool = False) -> str:
        """Mock file enqueuing."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "file_id": file_metadata.get("file_id"),
            "status": "queued",
            "created_at": datetime.utcnow()
        }
        
        # Emit job enqueued event
        await self.event_bus.emit({
            "type": "job_enqueued",
            "job_id": job_id,
            "file_id": file_metadata.get("file_id"),
            "data": {"priority": priority}
        })
        
        # Simulate processing after a delay
        asyncio.create_task(self._simulate_processing(job_id, file_metadata))
        
        return job_id
    
    async def _simulate_processing(self, job_id: str, file_metadata: Dict[str, Any]):
        """Simulate document processing."""
        await asyncio.sleep(2)  # Simulate processing time
        
        file_id = file_metadata.get("file_id")
        
        # Emit processing events
        await self.event_bus.emit({
            "type": "document_processing",
            "job_id": job_id,
            "file_id": file_id
        })
        
        await asyncio.sleep(3)  # More processing
        
        # Complete processing
        self._jobs[job_id]["status"] = "completed"
        await self.event_bus.emit({
            "type": "document_processed",
            "job_id": job_id,
            "file_id": file_id,
            "data": {
                "processing_time": 5.0,
                "element_count": 10
            }
        })
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        return self._jobs.get(job_id)
    
    async def shutdown(self):
        """Shutdown mock queue."""
        pass


class MockProgressTracker:
    """Mock progress tracker for when Agent 2's component isn't available."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._progress = {}
        logger.info("Using MockProgressTracker - Agent 2 component not available")
    
    async def init_file(self, session_id: str, file_id: str, filename: str, size: int):
        """Initialize file progress."""
        self._progress[file_id] = {
            "file_id": file_id,
            "session_id": session_id,
            "filename": filename,
            "size": size,
            "status": "pending",
            "progress": 0.0,
            "current_step": "waiting",
            "completed_steps": 0,
            "total_steps": 5
        }
    
    async def update_file_progress(self, file_id: str, status: str, current_step: str, 
                                 completed_steps: int, error: Optional[str] = None):
        """Update file progress."""
        if file_id in self._progress:
            progress_data = self._progress[file_id]
            progress_data.update({
                "status": status,
                "current_step": current_step,
                "completed_steps": completed_steps,
                "progress": completed_steps / progress_data["total_steps"]
            })
            
            if error:
                progress_data["error"] = error
            
            # Emit progress event
            await self.event_bus.emit({
                "type": "progress_updated",
                "file_id": file_id,
                "data": {
                    "status": status,
                    "progress": progress_data["progress"],
                    "current_step": current_step
                }
            })


class IngestionSystem:
    """
    Integrated document ingestion system.
    
    Coordinates all components from Agents 1-3 and integrates with 
    Unstructured.io client for document processing.
    """
    
    def __init__(self, settings: Optional[IngestionSettings] = None):
        self.settings = settings or IngestionSettings()
        self.event_bus = EventBus()
        self._initialized = False
        
        # Component instances
        self.unstructured_client: Optional[UnstructuredClient] = None
        self.upload_manager = None
        self.queue_manager = None
        self.progress_tracker = None
        self.websocket_handler = None
        
        # Mock flags for testing
        self._use_mocks = True  # Will be set to False when real components are available
        
    async def initialize(self):
        """Initialize all components."""
        if self._initialized:
            return
        
        logger.info("Initializing document ingestion system...")
        
        try:
            # Initialize Unstructured client from Issue #6
            await self._initialize_unstructured_client()
            
            # Initialize core components (with mocks if needed)
            await self._initialize_upload_manager()
            await self._initialize_queue_system()
            await self._initialize_progress_tracking()
            
            # Wire up event handlers
            self._wire_events()
            
            self._initialized = True
            logger.info("Document ingestion system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ingestion system: {e}")
            raise
    
    async def _initialize_unstructured_client(self):
        """Initialize Unstructured.io client."""
        try:
            config = UnstructuredConfig.from_env()
            self.unstructured_client = UnstructuredClient(config)
            await self.unstructured_client.initialize()
            logger.info("Unstructured.io client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Unstructured client: {e}")
            # Create mock client for testing
            self.unstructured_client = None
    
    async def _initialize_upload_manager(self):
        """Initialize upload manager (Agent 1's component)."""
        try:
            # Try to import Agent 1's upload manager
            from .upload_manager import UploadManager
            
            upload_dir = Path(self.settings.upload_dir)
            self.upload_manager = UploadManager(
                upload_dir=upload_dir,
                max_file_size=self.settings.max_file_size,
                unstructured_client=self.unstructured_client
            )
            logger.info("Agent 1's UploadManager initialized")
            self._use_mocks = False
            
        except ImportError:
            # Use mock if Agent 1's component isn't available
            upload_dir = Path(self.settings.upload_dir)
            self.upload_manager = MockUploadManager(
                upload_dir=upload_dir,
                max_file_size=self.settings.max_file_size
            )
    
    async def _initialize_queue_system(self):
        """Initialize queue system (Agent 2's components)."""
        try:
            # Try to import Agent 2's components
            from .queue_manager import QueueManager
            from .queue_config import QueueConfig
            
            config = QueueConfig(redis_url=self.settings.redis_url)
            self.queue_manager = QueueManager(config, self.event_bus)
            await self.queue_manager.initialize()
            
            # Initialize progress tracker
            from .progress import ProgressTracker
            redis_client = await self.queue_manager.get_redis_client()
            self.progress_tracker = ProgressTracker(redis_client, self.event_bus)
            
            logger.info("Agent 2's queue components initialized")
            
        except ImportError:
            # Use mocks if Agent 2's components aren't available
            self.queue_manager = MockQueueManager(self.event_bus)
            self.progress_tracker = MockProgressTracker(self.event_bus)
            await self.queue_manager.initialize()
    
    async def _initialize_progress_tracking(self):
        """Initialize WebSocket progress handler (Agent 3's component)."""
        try:
            # Try to import Agent 3's WebSocket handler
            from ..api.websockets.progress import ProgressWebSocket
            
            self.websocket_handler = ProgressWebSocket(
                self.event_bus,
                self.progress_tracker
            )
            await self.websocket_handler.start()
            logger.info("Agent 3's WebSocket handler initialized")
            
        except ImportError:
            logger.info("Agent 3's WebSocket handler not available - continuing without")
    
    def _wire_events(self):
        """Wire up event handlers between components."""
        # File upload events
        self.event_bus.subscribe("file_uploaded", self._handle_file_uploaded)
        
        # Queue events  
        self.event_bus.subscribe("job_enqueued", self._handle_job_enqueued)
        
        # Processing events
        self.event_bus.subscribe("document_processing", self._handle_processing_started)
        self.event_bus.subscribe("document_processed", self._handle_processing_completed)
        self.event_bus.subscribe("document_failed", self._handle_processing_failed)
        
        logger.info("Event handlers wired up")
    
    async def _handle_file_uploaded(self, event: Dict[str, Any]):
        """Handle file upload completion."""
        file_id = event.get("file_id")
        session_id = event.get("session_id")
        
        if not file_id or not session_id:
            return
        
        # Initialize progress tracking
        await self.progress_tracker.init_file(
            session_id=session_id,
            file_id=file_id,
            filename=event.get("filename", "unknown"),
            size=event.get("size", 0)
        )
        
        # Update progress
        await self.progress_tracker.update_file_progress(
            file_id=file_id,
            status="uploaded",
            current_step="validation",
            completed_steps=1
        )
    
    async def _handle_job_enqueued(self, event: Dict[str, Any]):
        """Handle job enqueued event."""
        file_id = event.get("file_id")
        if file_id:
            await self.progress_tracker.update_file_progress(
                file_id=file_id,
                status="queued",
                current_step="waiting",
                completed_steps=2
            )
    
    async def _handle_processing_started(self, event: Dict[str, Any]):
        """Handle processing started event."""
        file_id = event.get("file_id")
        if file_id:
            await self.progress_tracker.update_file_progress(
                file_id=file_id,
                status="processing",
                current_step="extracting",
                completed_steps=3
            )
    
    async def _handle_processing_completed(self, event: Dict[str, Any]):
        """Handle processing completed event."""
        file_id = event.get("file_id")
        if file_id:
            await self.progress_tracker.update_file_progress(
                file_id=file_id,
                status="completed",
                current_step="done",
                completed_steps=5
            )
    
    async def _handle_processing_failed(self, event: Dict[str, Any]):
        """Handle processing failed event."""
        file_id = event.get("file_id")
        error = event.get("error", "Unknown error")
        if file_id:
            await self.progress_tracker.update_file_progress(
                file_id=file_id,
                status="failed",
                current_step="error",
                completed_steps=0,
                error=error
            )
    
    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single document through the complete pipeline.
        
        This is a high-level interface that handles:
        1. File upload and validation
        2. Queue processing
        3. Document extraction with Unstructured.io
        4. Progress tracking
        
        Returns:
            Processing result with status and extracted data
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Create session
            session = await self.upload_manager.create_session("system")
            session_id = session["session_id"]
            
            # Read file data
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Upload file
            upload_result = await self.upload_manager.upload_file(
                session_id=session_id,
                file_data=file_data,
                filename=file_path.name
            )
            
            if upload_result["validation_status"] == "failed":
                return {
                    "success": False,
                    "error": "File validation failed",
                    "errors": upload_result["errors"]
                }
            
            # Emit upload event
            await self.event_bus.emit({
                "type": "file_uploaded",
                "file_id": upload_result["file_id"],
                "session_id": session_id,
                "filename": file_path.name,
                "size": upload_result["size"]
            })
            
            # Queue for processing
            job_id = await self.queue_manager.enqueue_file({
                "file_id": upload_result["file_id"],
                "filename": file_path.name,
                "storage_key": upload_result["storage_key"]
            })
            
            # Wait for processing to complete (with timeout)
            timeout = 300  # 5 minutes
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).total_seconds() < timeout:
                job_status = await self.queue_manager.get_job_status(job_id)
                if job_status and job_status["status"] in ["completed", "failed"]:
                    break
                await asyncio.sleep(1)
            
            final_status = await self.queue_manager.get_job_status(job_id)
            
            if final_status and final_status["status"] == "completed":
                return {
                    "success": True,
                    "file_id": upload_result["file_id"],
                    "job_id": job_id,
                    "processing_time": (datetime.utcnow() - start_time).total_seconds()
                }
            else:
                return {
                    "success": False,
                    "error": "Processing failed or timed out",
                    "job_status": final_status
                }
                
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrated components."""
        status = {
            "initialized": self._initialized,
            "using_mocks": self._use_mocks,
            "components": {}
        }
        
        # Check Unstructured.io client
        if self.unstructured_client:
            try:
                # Try to get a simple status from Unstructured
                formats = await self.unstructured_client.get_supported_formats()
                status["components"]["unstructured"] = {
                    "available": True,
                    "supported_formats": len(formats),
                    "status": "ready"
                }
            except Exception as e:
                status["components"]["unstructured"] = {
                    "available": False,
                    "error": str(e)
                }
        else:
            status["components"]["unstructured"] = {
                "available": False,
                "error": "Not initialized"
            }
        
        # Check upload manager
        status["components"]["upload_manager"] = {
            "available": self.upload_manager is not None,
            "type": "mock" if isinstance(self.upload_manager, MockUploadManager) else "real"
        }
        
        # Check queue manager
        status["components"]["queue_manager"] = {
            "available": self.queue_manager is not None,
            "type": "mock" if isinstance(self.queue_manager, MockQueueManager) else "real"
        }
        
        # Check progress tracker
        status["components"]["progress_tracker"] = {
            "available": self.progress_tracker is not None,
            "type": "mock" if isinstance(self.progress_tracker, MockProgressTracker) else "real"
        }
        
        # Check WebSocket handler
        status["components"]["websocket_handler"] = {
            "available": self.websocket_handler is not None
        }
        
        return status
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        logger.info("Shutting down document ingestion system...")
        
        if self.unstructured_client:
            await self.unstructured_client.close()
        
        if self.queue_manager:
            await self.queue_manager.shutdown()
        
        self._initialized = False
        logger.info("Document ingestion system shutdown complete")


# Convenience function for simple document processing
async def process_document_simple(file_path: Path, settings: Optional[IngestionSettings] = None) -> Dict[str, Any]:
    """
    Process a single document with default settings.
    
    This is a convenience function for simple use cases.
    """
    system = IngestionSystem(settings)
    try:
        await system.initialize()
        return await system.process_document(file_path)
    finally:
        await system.shutdown()