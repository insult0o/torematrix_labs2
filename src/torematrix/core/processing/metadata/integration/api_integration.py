"""REST API integration for metadata extraction operations."""

from typing import Dict, List, Optional, Any
import asyncio
import uuid
import logging
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from torematrix.core.models.element import ProcessedDocument
from .pipeline_integration import MetadataPipelineIntegration, PipelineContext


class MetadataExtractionRequest(BaseModel):
    """Request model for metadata extraction."""
    document_id: str = Field(..., description="Unique document identifier")
    user_id: str = Field(..., description="User requesting extraction")
    options: Dict[str, Any] = Field(default_factory=dict, description="Extraction options")
    enable_relationships: bool = Field(default=True, description="Enable relationship detection")
    enable_semantic_analysis: bool = Field(default=True, description="Enable semantic analysis")


class MetadataExtractionResponse(BaseModel):
    """Response model for metadata extraction."""
    session_id: str = Field(..., description="Processing session identifier")
    status: str = Field(..., description="Processing status")
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")
    message: str = Field(..., description="Status message")


class DocumentMetadata(BaseModel):
    """Complete document metadata response."""
    document_id: str = Field(..., description="Document identifier")
    metadata: Dict[str, Any] = Field(..., description="Extracted metadata")
    relationships: List[Dict[str, Any]] = Field(..., description="Element relationships")
    extraction_stats: Dict[str, Any] = Field(..., description="Extraction statistics")
    extraction_time: datetime = Field(..., description="When extraction completed")


class Relationship(BaseModel):
    """Individual relationship model."""
    id: str = Field(..., description="Relationship identifier")
    source_element_id: str = Field(..., description="Source element ID")
    target_element_id: str = Field(..., description="Target element ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProcessingStatus(BaseModel):
    """Processing status response."""
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Current status")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    created_at: datetime = Field(..., description="Session creation time")
    updated_at: datetime = Field(..., description="Last update time")


class MetadataAPIIntegration:
    """REST API integration for metadata extraction operations."""
    
    def __init__(self, pipeline_integration: MetadataPipelineIntegration):
        self.pipeline = pipeline_integration
        self.logger = logging.getLogger(__name__)
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def extract_metadata(
        self, 
        request: MetadataExtractionRequest,
        background_tasks: BackgroundTasks
    ) -> MetadataExtractionResponse:
        """Extract metadata from document."""
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create pipeline context
            context = PipelineContext(
                document_id=request.document_id,
                user_id=request.user_id,
                session_id=session_id,
                processing_options=request.options,
                metadata={}
            )
            
            # Store session info
            self._active_sessions[session_id] = {
                "document_id": request.document_id,
                "user_id": request.user_id,
                "status": "starting",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Start background processing
            background_tasks.add_task(
                self._process_metadata_extraction,
                session_id,
                context
            )
            
            return MetadataExtractionResponse(
                session_id=session_id,
                status="processing",
                estimated_time=120,  # Agent 3's performance optimization should improve this
                message="Metadata extraction started successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start metadata extraction: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start metadata extraction: {str(e)}"
            )
            
    async def get_metadata(self, document_id: str) -> DocumentMetadata:
        """Get extracted metadata for document."""
        try:
            # This would typically query the storage system
            # For now, return sample data structure
            metadata = await self._retrieve_document_metadata(document_id)
            
            if not metadata:
                raise HTTPException(
                    status_code=404,
                    detail=f"Metadata not found for document: {document_id}"
                )
                
            return DocumentMetadata(**metadata)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to retrieve metadata: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve metadata: {str(e)}"
            )
            
    async def get_relationships(
        self, 
        document_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Relationship]:
        """Get element relationships for document."""
        try:
            relationships = await self._retrieve_document_relationships(
                document_id, 
                relationship_type
            )
            
            return [Relationship(**rel) for rel in relationships]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve relationships: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve relationships: {str(e)}"
            )
            
    async def get_processing_status(self, session_id: str) -> ProcessingStatus:
        """Get processing status for session."""
        try:
            if session_id not in self._active_sessions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session not found: {session_id}"
                )
                
            session_info = self._active_sessions[session_id]
            pipeline_status = await self.pipeline.get_processing_status(session_id)
            
            return ProcessingStatus(
                session_id=session_id,
                status=session_info["status"],
                progress=pipeline_status.get("progress", {}),
                created_at=session_info["created_at"],
                updated_at=session_info["updated_at"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get processing status: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get processing status: {str(e)}"
            )
            
    async def cancel_processing(self, session_id: str) -> Dict[str, str]:
        """Cancel metadata processing session."""
        try:
            if session_id not in self._active_sessions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session not found: {session_id}"
                )
                
            # Update session status
            self._active_sessions[session_id]["status"] = "cancelled"
            self._active_sessions[session_id]["updated_at"] = datetime.utcnow()
            
            return {
                "session_id": session_id,
                "status": "cancelled",
                "message": "Processing cancelled successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to cancel processing: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to cancel processing: {str(e)}"
            )
            
    async def _process_metadata_extraction(
        self, 
        session_id: str, 
        context: PipelineContext
    ):
        """Background task for metadata extraction."""
        try:
            # Update session status
            self._active_sessions[session_id]["status"] = "processing"
            self._active_sessions[session_id]["updated_at"] = datetime.utcnow()
            
            # Load document (this would come from storage system)
            document = await self._load_document(context.document_id)
            
            # Process through metadata pipeline
            result = await self.pipeline.process_document_with_metadata(
                document, 
                context
            )
            
            # Store results (this would go to storage system)
            await self._store_metadata_results(session_id, result)
            
            # Update session status
            self._active_sessions[session_id]["status"] = "completed"
            self._active_sessions[session_id]["updated_at"] = datetime.utcnow()
            
            self.logger.info(f"Metadata extraction completed for session: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed for session {session_id}: {e}")
            self._active_sessions[session_id]["status"] = "failed"
            self._active_sessions[session_id]["error"] = str(e)
            self._active_sessions[session_id]["updated_at"] = datetime.utcnow()
            
    async def _load_document(self, document_id: str) -> ProcessedDocument:
        """Load document from storage system."""
        # This would integrate with the storage system
        # For now, return a mock document
        from torematrix.core.models.element import ProcessedDocument
        
        return ProcessedDocument(
            id=document_id,
            elements=[],
            metadata={},
            processing_stats={}
        )
        
    async def _store_metadata_results(self, session_id: str, result):
        """Store metadata extraction results."""
        # This would integrate with Agent 2's graph storage
        from torematrix.core.processing.metadata.storage.graph_storage import GraphStorage
        
        storage = GraphStorage()
        await storage.store_document_metadata(
            document_id=result.document.id,
            metadata=result.metadata,
            relationships=result.relationships
        )
        
    async def _retrieve_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata from storage."""
        # This would query the storage system
        return {
            "document_id": document_id,
            "metadata": {"sample": "metadata"},
            "relationships": [],
            "extraction_stats": {"total_elements": 0},
            "extraction_time": datetime.utcnow()
        }
        
    async def _retrieve_document_relationships(
        self, 
        document_id: str, 
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve document relationships from storage."""
        # This would query Agent 2's relationship storage
        return []
        
    def get_api_health(self) -> Dict[str, Any]:
        """Get API health status."""
        return {
            "status": "healthy",
            "active_sessions": len(self._active_sessions),
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }