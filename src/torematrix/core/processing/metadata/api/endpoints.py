"""REST API endpoints for metadata extraction operations."""

from typing import Dict, List, Optional, Any
import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse

from ..integration.api_integration import (
    MetadataAPIIntegration,
    MetadataExtractionRequest,
    MetadataExtractionResponse,
    DocumentMetadata,
    Relationship,
    ProcessingStatus
)
from ..monitoring.observability import MetadataObservabilitySystem


def create_metadata_router(
    api_integration: MetadataAPIIntegration,
    observability: MetadataObservabilitySystem
) -> APIRouter:
    """Create FastAPI router for metadata extraction endpoints."""
    
    router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])
    
    @router.post(
        "/extract",
        response_model=MetadataExtractionResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Extract metadata from document",
        description="Start metadata extraction process for a document"
    )
    async def extract_metadata(
        request: MetadataExtractionRequest,
        background_tasks: BackgroundTasks
    ) -> MetadataExtractionResponse:
        """Extract metadata from document."""
        try:
            # Track metrics
            span_id = observability.start_extraction_trace(
                "api_extract_request",
                request.document_id,
                user_id=request.user_id
            )
            
            # Submit extraction request
            response = await api_integration.extract_metadata(request, background_tasks)
            
            # Track success metrics
            observability.track_extraction_metrics(
                operation="api_extract",
                duration=0.1,  # API response time
                success=True,
                metadata_count=0,  # Will be updated when processing completes
                user_id=request.user_id
            )
            
            observability.finish_extraction_trace(span_id, True)
            
            return response
            
        except Exception as e:
            observability.finish_extraction_trace(span_id, False, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start metadata extraction: {str(e)}"
            )
    
    @router.get(
        "/{document_id}",
        response_model=DocumentMetadata,
        summary="Get document metadata",
        description="Retrieve extracted metadata for a document"
    )
    async def get_metadata(document_id: str) -> DocumentMetadata:
        """Get extracted metadata for document."""
        try:
            span_id = observability.start_extraction_trace(
                "api_get_metadata",
                document_id
            )
            
            metadata = await api_integration.get_metadata(document_id)
            
            observability.finish_extraction_trace(span_id, True)
            return metadata
            
        except HTTPException:
            observability.finish_extraction_trace(span_id, False)
            raise
        except Exception as e:
            observability.finish_extraction_trace(span_id, False, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve metadata: {str(e)}"
            )
    
    @router.get(
        "/{document_id}/relationships",
        response_model=List[Relationship],
        summary="Get document relationships",
        description="Retrieve element relationships for a document"
    )
    async def get_relationships(
        document_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Relationship]:
        """Get element relationships for document."""
        try:
            span_id = observability.start_extraction_trace(
                "api_get_relationships",
                document_id,
                relationship_type=relationship_type
            )
            
            relationships = await api_integration.get_relationships(
                document_id,
                relationship_type
            )
            
            observability.track_relationship_metrics(
                relationship_type or "all",
                1.0,  # Default confidence for API calls
                len(relationships)
            )
            
            observability.finish_extraction_trace(span_id, True)
            return relationships
            
        except Exception as e:
            observability.finish_extraction_trace(span_id, False, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve relationships: {str(e)}"
            )
    
    @router.get(
        "/sessions/{session_id}/status",
        response_model=ProcessingStatus,
        summary="Get processing status",
        description="Get status of metadata extraction session"
    )
    async def get_processing_status(session_id: str) -> ProcessingStatus:
        """Get processing status for session."""
        try:
            status_data = await api_integration.get_processing_status(session_id)
            return status_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get processing status: {str(e)}"
            )
    
    @router.post(
        "/sessions/{session_id}/cancel",
        summary="Cancel processing",
        description="Cancel metadata extraction session"
    )
    async def cancel_processing(session_id: str) -> Dict[str, str]:
        """Cancel metadata processing session."""
        try:
            result = await api_integration.cancel_processing(session_id)
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel processing: {str(e)}"
            )
    
    @router.get(
        "/health",
        summary="API health check",
        description="Get API health status and metrics"
    )
    def get_health() -> Dict[str, Any]:
        """Get API health status."""
        try:
            api_health = api_integration.get_api_health()
            system_health = observability.get_health_metrics()
            
            return {
                "api": api_health,
                "system": system_health,
                "overall_status": "healthy" if system_health["system_healthy"] else "unhealthy"
            }
            
        except Exception as e:
            return {
                "api": {"status": "error", "error": str(e)},
                "system": {"status": "error", "error": str(e)},
                "overall_status": "unhealthy"
            }
    
    @router.get(
        "/metrics",
        summary="Get system metrics",
        description="Get performance and monitoring metrics"
    )
    def get_metrics() -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            return observability.get_performance_dashboard_data()
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve metrics: {str(e)}"
            )
    
    @router.post(
        "/batch/extract",
        response_model=List[MetadataExtractionResponse],
        status_code=status.HTTP_202_ACCEPTED,
        summary="Batch metadata extraction",
        description="Start metadata extraction for multiple documents"
    )
    async def batch_extract_metadata(
        requests: List[MetadataExtractionRequest],
        background_tasks: BackgroundTasks
    ) -> List[MetadataExtractionResponse]:
        """Extract metadata for multiple documents."""
        try:
            if len(requests) > 100:  # Reasonable batch size limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Batch size too large (max 100 documents)"
                )
            
            responses = []
            
            for request in requests:
                span_id = observability.start_extraction_trace(
                    "api_batch_extract",
                    request.document_id,
                    user_id=request.user_id,
                    batch_size=len(requests)
                )
                
                try:
                    response = await api_integration.extract_metadata(request, background_tasks)
                    responses.append(response)
                    observability.finish_extraction_trace(span_id, True)
                    
                except Exception as e:
                    observability.finish_extraction_trace(span_id, False, error=str(e))
                    # Continue with other requests even if one fails
                    responses.append(MetadataExtractionResponse(
                        session_id="",
                        status="failed",
                        estimated_time=0,
                        message=f"Failed: {str(e)}"
                    ))
            
            return responses
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch extraction failed: {str(e)}"
            )
    
    @router.get(
        "/documents/{document_id}/summary",
        summary="Get document summary",
        description="Get comprehensive document metadata summary"
    )
    async def get_document_summary(document_id: str) -> Dict[str, Any]:
        """Get comprehensive document metadata summary."""
        try:
            # Get metadata and relationships
            metadata = await api_integration.get_metadata(document_id)
            relationships = await api_integration.get_relationships(document_id)
            
            # Build summary
            summary = {
                "document_id": document_id,
                "extraction_time": metadata.extraction_time,
                "total_metadata_fields": len(metadata.metadata),
                "total_relationships": len(relationships),
                "relationship_types": list(set(r.relationship_type for r in relationships)),
                "extraction_stats": metadata.extraction_stats,
                "structure_analysis": metadata.metadata.get("document_structure", {}),
                "semantic_summary": metadata.metadata.get("semantic_roles", {})
            }
            
            return summary
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate document summary: {str(e)}"
            )
    
    return router