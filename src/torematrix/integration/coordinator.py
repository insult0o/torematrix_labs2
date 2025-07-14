"""
Event Flow Coordinator for orchestrating component communication.

This module manages the event flow between all components, ensuring
proper sequencing and data transformation.
"""

from typing import Dict, Any, List, Optional, Callable, Set
import asyncio
from datetime import datetime
import logging
from enum import Enum

from .adapters import EventBusAdapter
from .transformer import DataTransformer

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Stages in the document processing pipeline."""
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    VALIDATING = "validating"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class EventFlowCoordinator:
    """
    Coordinates event flow between all system components.
    
    Manages the complete document processing lifecycle from upload
    to storage, ensuring proper event sequencing and data transformation.
    """
    
    def __init__(
        self,
        event_bus: EventBusAdapter,
        data_transformer: DataTransformer
    ):
        """
        Initialize coordinator.
        
        Args:
            event_bus: Adapted event bus for consistent API
            data_transformer: Data transformer for format conversion
        """
        self.event_bus = event_bus
        self.transformer = data_transformer
        
        # Track document processing state
        self.document_states: Dict[str, ProcessingStage] = {}
        self.document_data: Dict[str, Dict[str, Any]] = {}
        
        # Event handlers
        self.handlers: Dict[str, List[Callable]] = {}
        
        # Setup default flow
        self._setup_default_flow()
    
    def _setup_default_flow(self):
        """Setup the default document processing event flow."""
        # Document upload flow
        self.event_bus.subscribe("document.uploaded", self._handle_document_uploaded)
        self.event_bus.subscribe("document.queued", self._handle_document_queued)
        
        # Processing flow
        self.event_bus.subscribe("processing.started", self._handle_processing_started)
        self.event_bus.subscribe("unstructured.completed", self._handle_extraction_completed)
        self.event_bus.subscribe("pipeline.stage.completed", self._handle_stage_completed)
        
        # Storage flow
        self.event_bus.subscribe("storage.started", self._handle_storage_started)
        self.event_bus.subscribe("storage.completed", self._handle_storage_completed)
        
        # Error handling
        self.event_bus.subscribe("*.failed", self._handle_failure)
        self.event_bus.subscribe("*.error", self._handle_error)
    
    async def _handle_document_uploaded(self, event: Any):
        """Handle document upload event."""
        try:
            # Extract event data (handle both dict and object formats)
            if hasattr(event, 'payload'):
                data = event.payload
            else:
                data = event.get('data', {})
            
            # Normalize the data
            normalized = self.transformer.normalize_event_data(data)
            doc_id = normalized.get('id')
            
            if not doc_id:
                logger.error("Document uploaded without ID")
                return
            
            # Update state
            self.document_states[doc_id] = ProcessingStage.UPLOADED
            self.document_data[doc_id] = normalized
            
            logger.info(f"Document {doc_id} uploaded, queuing for processing")
            
            # Queue for processing
            await self.event_bus.emit(
                "document.queue",
                {
                    "id": doc_id,
                    "priority": normalized.get("priority", "normal"),
                    "metadata": normalized
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling document upload: {e}", exc_info=True)
            await self._emit_error(doc_id, "upload_handler", str(e))
    
    async def _handle_document_queued(self, event: Any):
        """Handle document queued event."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id:
            self.document_states[doc_id] = ProcessingStage.QUEUED
            
            # Trigger processing
            await self.event_bus.emit(
                "processing.start",
                {
                    "id": doc_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _handle_processing_started(self, event: Any):
        """Handle processing started event."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id:
            self.document_states[doc_id] = ProcessingStage.PROCESSING
            
            # Trigger unstructured extraction
            await self.event_bus.emit(
                "unstructured.extract",
                {
                    "id": doc_id,
                    "file_path": self.document_data[doc_id].get("file_path"),
                    "options": self.document_data[doc_id].get("extraction_options", {})
                }
            )
    
    async def _handle_extraction_completed(self, event: Any):
        """Handle extraction completion from Unstructured."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if not doc_id:
            return
        
        self.document_states[doc_id] = ProcessingStage.EXTRACTING
        
        # Get extracted elements
        elements = data.get('elements', [])
        
        # Transform from unstructured to pipeline format
        pipeline_elements = self.transformer.transform_document_batch(
            elements,
            from_format="unstructured",
            to_format="pipeline"
        )
        
        # Store transformed elements
        if doc_id in self.document_data:
            self.document_data[doc_id]['pipeline_elements'] = pipeline_elements
        
        # Trigger pipeline processing
        await self.event_bus.emit(
            "pipeline.process",
            {
                "id": doc_id,
                "elements": pipeline_elements,
                "pipeline_config": data.get("pipeline_config", {})
            }
        )
    
    async def _handle_stage_completed(self, event: Any):
        """Handle pipeline stage completion."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        stage_name = data.get('stage')
        
        if not doc_id:
            return
        
        logger.info(f"Stage {stage_name} completed for document {doc_id}")
        
        # Check if all stages completed
        if data.get('final_stage', False):
            self.document_states[doc_id] = ProcessingStage.TRANSFORMING
            
            # Get processed elements
            processed_elements = data.get('elements', [])
            
            # Transform to storage format
            storage_elements = self.transformer.transform_document_batch(
                processed_elements,
                from_format="pipeline",
                to_format="storage"
            )
            
            # Trigger storage
            await self.event_bus.emit(
                "storage.save",
                {
                    "id": doc_id,
                    "elements": storage_elements,
                    "metadata": self.document_data.get(doc_id, {})
                }
            )
    
    async def _handle_storage_started(self, event: Any):
        """Handle storage started event."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id:
            self.document_states[doc_id] = ProcessingStage.STORING
    
    async def _handle_storage_completed(self, event: Any):
        """Handle storage completion."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if not doc_id:
            return
        
        self.document_states[doc_id] = ProcessingStage.COMPLETED
        
        # Calculate processing time
        start_time = self.document_data.get(doc_id, {}).get('timestamp')
        if start_time:
            processing_time = (datetime.utcnow() - datetime.fromisoformat(start_time)).total_seconds()
        else:
            processing_time = 0
        
        # Emit completion event
        await self.event_bus.emit(
            "document.completed",
            {
                "id": doc_id,
                "status": "success",
                "processing_time": processing_time,
                "element_count": data.get('element_count', 0),
                "storage_location": data.get('location')
            },
            priority="immediate"
        )
        
        # Cleanup tracking data
        await self._cleanup_document(doc_id)
    
    async def _handle_failure(self, event: Any):
        """Handle any failure event."""
        data = self._extract_event_data(event)
        doc_id = data.get('id')
        
        if doc_id:
            self.document_states[doc_id] = ProcessingStage.FAILED
            
            # Emit document failed event
            await self.event_bus.emit(
                "document.failed",
                {
                    "id": doc_id,
                    "error": data.get('error', 'Unknown error'),
                    "stage": self._get_stage_from_event_type(event),
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority="immediate"
            )
    
    async def _handle_error(self, event: Any):
        """Handle any error event."""
        data = self._extract_event_data(event)
        logger.error(f"Error event received: {data}")
        
        # Log to monitoring system
        await self.event_bus.emit(
            "monitoring.error",
            {
                "source": "event_coordinator",
                "error": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _extract_event_data(self, event: Any) -> Dict[str, Any]:
        """Extract data from event regardless of format."""
        if hasattr(event, 'payload'):
            return event.payload
        elif hasattr(event, 'data'):
            return event.data
        elif isinstance(event, dict):
            return event.get('data', event)
        else:
            return {}
    
    def _get_stage_from_event_type(self, event: Any) -> str:
        """Extract stage name from event type."""
        if hasattr(event, 'event_type'):
            event_type = event.event_type
        elif isinstance(event, dict):
            event_type = event.get('type', '')
        else:
            event_type = str(event)
        
        # Extract stage from event type (e.g., "processing.failed" -> "processing")
        parts = event_type.split('.')
        if len(parts) > 0:
            return parts[0]
        return "unknown"
    
    async def _emit_error(self, doc_id: Optional[str], source: str, error: str):
        """Emit an error event."""
        await self.event_bus.emit(
            "coordinator.error",
            {
                "id": doc_id,
                "source": source,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            },
            priority="immediate"
        )
    
    async def _cleanup_document(self, doc_id: str):
        """Clean up document tracking data."""
        # Keep data for a short time for debugging
        await asyncio.sleep(60)  # 1 minute
        
        if doc_id in self.document_states:
            del self.document_states[doc_id]
        if doc_id in self.document_data:
            del self.document_data[doc_id]
    
    def register_custom_flow(self, event_pattern: str, handler: Callable):
        """
        Register a custom event handler for specific flows.
        
        Args:
            event_pattern: Event pattern to match (e.g., "custom.*")
            handler: Async function to handle the event
        """
        self.event_bus.subscribe(event_pattern, handler)
    
    def get_document_state(self, doc_id: str) -> Optional[ProcessingStage]:
        """Get current processing state of a document."""
        return self.document_states.get(doc_id)
    
    def get_active_documents(self) -> List[str]:
        """Get list of documents currently being processed."""
        return [
            doc_id for doc_id, state in self.document_states.items()
            if state not in [ProcessingStage.COMPLETED, ProcessingStage.FAILED]
        ]
    
    async def cancel_document(self, doc_id: str):
        """Cancel processing of a document."""
        if doc_id in self.document_states:
            await self.event_bus.emit(
                "document.cancel",
                {
                    "id": doc_id,
                    "reason": "User requested cancellation"
                },
                priority="immediate"
            )
            self.document_states[doc_id] = ProcessingStage.FAILED