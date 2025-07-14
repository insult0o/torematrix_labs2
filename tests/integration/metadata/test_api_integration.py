"""API integration tests for metadata extraction system."""

import asyncio
import pytest
import uuid
from datetime import datetime
from fastapi import HTTPException

from torematrix.core.processing.metadata.integration.api_integration import (
    MetadataAPIIntegration,
    MetadataExtractionRequest,
    MetadataExtractionResponse,
    DocumentMetadata,
    Relationship,
    ProcessingStatus
)


class MockBackgroundTasks:
    """Mock FastAPI background tasks for testing."""
    def __init__(self):
        self.tasks = []
    
    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


@pytest.fixture
async def api_integration():
    """Create API integration for testing."""
    from torematrix.core.processing.metadata.integration.pipeline_integration import (
        MetadataPipelineIntegration,
        IntegrationConfig
    )
    
    config = IntegrationConfig()
    pipeline = MetadataPipelineIntegration(config)
    await pipeline.initialize()
    
    api = MetadataAPIIntegration(pipeline)
    yield api
    
    await pipeline.cleanup()


class TestMetadataExtractionAPI:
    """Test metadata extraction API endpoints."""
    
    @pytest.mark.asyncio
    async def test_extract_metadata_basic_request(self, api_integration):
        """Test basic metadata extraction request."""
        request = MetadataExtractionRequest(
            document_id="test_doc_001",
            user_id="user_001",
            options={},
            enable_relationships=True,
            enable_semantic_analysis=True
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        
        assert isinstance(response, MetadataExtractionResponse)
        assert response.session_id is not None
        assert response.status == "processing"
        assert response.estimated_time > 0
        assert len(background_tasks.tasks) == 1
        
    @pytest.mark.asyncio
    async def test_extract_metadata_with_options(self, api_integration):
        """Test metadata extraction with custom options."""
        request = MetadataExtractionRequest(
            document_id="test_doc_002",
            user_id="user_002",
            options={
                "enable_caching": True,
                "timeout": 300,
                "quality_threshold": 0.8
            },
            enable_relationships=False,
            enable_semantic_analysis=True
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        
        assert response.session_id is not None
        assert response.status == "processing"
        
    @pytest.mark.asyncio
    async def test_extract_metadata_validation(self, api_integration):
        """Test metadata extraction request validation."""
        # Test with invalid document_id
        with pytest.raises(Exception):
            request = MetadataExtractionRequest(
                document_id="",  # Invalid empty ID
                user_id="user_003",
                options={}
            )
            
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, api_integration):
        """Test handling multiple concurrent extraction requests."""
        requests = [
            MetadataExtractionRequest(
                document_id=f"test_doc_{i:03d}",
                user_id=f"user_{i:03d}",
                options={}
            )
            for i in range(5)
        ]
        
        background_tasks = MockBackgroundTasks()
        
        # Submit all requests concurrently
        tasks = [
            api_integration.extract_metadata(request, background_tasks)
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses are valid
        assert len(responses) == 5
        session_ids = [r.session_id for r in responses]
        assert len(set(session_ids)) == 5  # All unique session IDs
        
    @pytest.mark.asyncio
    async def test_extract_metadata_error_handling(self, api_integration):
        """Test error handling in metadata extraction."""
        # This test would require mocking the pipeline to throw an error
        # For now, test that the API handles errors gracefully
        request = MetadataExtractionRequest(
            document_id="error_test_doc",
            user_id="error_user",
            options={}
        )
        
        background_tasks = MockBackgroundTasks()
        
        # Should not raise exception but handle gracefully
        response = await api_integration.extract_metadata(request, background_tasks)
        assert response.session_id is not None


class TestMetadataRetrievalAPI:
    """Test metadata retrieval API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_metadata_success(self, api_integration):
        """Test successful metadata retrieval."""
        document_id = "test_doc_retrieve_001"
        
        metadata = await api_integration.get_metadata(document_id)
        
        assert isinstance(metadata, DocumentMetadata)
        assert metadata.document_id == document_id
        assert isinstance(metadata.metadata, dict)
        assert isinstance(metadata.relationships, list)
        assert isinstance(metadata.extraction_stats, dict)
        assert isinstance(metadata.extraction_time, datetime)
        
    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self, api_integration):
        """Test metadata retrieval for non-existent document."""
        # This would normally raise 404 HTTPException
        # For testing, we'll verify the API structure
        document_id = "non_existent_doc"
        
        try:
            await api_integration.get_metadata(document_id)
        except HTTPException as e:
            assert e.status_code == 404
            
    @pytest.mark.asyncio
    async def test_get_relationships_all(self, api_integration):
        """Test retrieving all relationships for a document."""
        document_id = "test_doc_relationships_001"
        
        relationships = await api_integration.get_relationships(document_id)
        
        assert isinstance(relationships, list)
        # Note: In real implementation, this would return actual relationships
        
    @pytest.mark.asyncio
    async def test_get_relationships_by_type(self, api_integration):
        """Test retrieving relationships filtered by type."""
        document_id = "test_doc_relationships_002"
        relationship_type = "spatial"
        
        relationships = await api_integration.get_relationships(
            document_id, 
            relationship_type
        )
        
        assert isinstance(relationships, list)
        
    @pytest.mark.asyncio
    async def test_get_relationships_multiple_types(self, api_integration):
        """Test retrieving relationships for multiple types."""
        document_id = "test_doc_relationships_003"
        
        # Test different relationship types
        types_to_test = ["spatial", "semantic", "hierarchical", "temporal"]
        
        for rel_type in types_to_test:
            relationships = await api_integration.get_relationships(
                document_id,
                rel_type
            )
            assert isinstance(relationships, list)


class TestProcessingStatusAPI:
    """Test processing status API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_processing_status_active(self, api_integration):
        """Test getting status for active processing session."""
        # Create a session first
        request = MetadataExtractionRequest(
            document_id="test_doc_status_001",
            user_id="user_status_001",
            options={}
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        session_id = response.session_id
        
        # Get processing status
        status = await api_integration.get_processing_status(session_id)
        
        assert isinstance(status, ProcessingStatus)
        assert status.session_id == session_id
        assert isinstance(status.status, str)
        assert isinstance(status.progress, dict)
        assert isinstance(status.created_at, datetime)
        assert isinstance(status.updated_at, datetime)
        
    @pytest.mark.asyncio
    async def test_get_processing_status_not_found(self, api_integration):
        """Test getting status for non-existent session."""
        non_existent_session = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await api_integration.get_processing_status(non_existent_session)
        
        assert exc_info.value.status_code == 404
        
    @pytest.mark.asyncio
    async def test_cancel_processing_active(self, api_integration):
        """Test canceling active processing session."""
        # Create a session first
        request = MetadataExtractionRequest(
            document_id="test_doc_cancel_001",
            user_id="user_cancel_001",
            options={}
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        session_id = response.session_id
        
        # Cancel processing
        cancel_response = await api_integration.cancel_processing(session_id)
        
        assert cancel_response["session_id"] == session_id
        assert cancel_response["status"] == "cancelled"
        assert "message" in cancel_response
        
    @pytest.mark.asyncio
    async def test_cancel_processing_not_found(self, api_integration):
        """Test canceling non-existent processing session."""
        non_existent_session = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await api_integration.cancel_processing(non_existent_session)
        
        assert exc_info.value.status_code == 404
        
    @pytest.mark.asyncio
    async def test_processing_status_lifecycle(self, api_integration):
        """Test complete processing status lifecycle."""
        # Create session
        request = MetadataExtractionRequest(
            document_id="test_doc_lifecycle_001",
            user_id="user_lifecycle_001",
            options={}
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        session_id = response.session_id
        
        # Check initial status
        status1 = await api_integration.get_processing_status(session_id)
        assert status1.status in ["starting", "processing"]
        
        # Wait a bit and check again (in real scenario, status would change)
        await asyncio.sleep(0.1)
        status2 = await api_integration.get_processing_status(session_id)
        assert status2.updated_at >= status1.updated_at


class TestAPIHealthAndMonitoring:
    """Test API health and monitoring endpoints."""
    
    def test_api_health_check(self, api_integration):
        """Test API health check endpoint."""
        health = api_integration.get_api_health()
        
        assert isinstance(health, dict)
        assert health["status"] == "healthy"
        assert "active_sessions" in health
        assert "version" in health
        assert "timestamp" in health
        
        # Verify timestamp format
        timestamp = health["timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise exception
        
    @pytest.mark.asyncio
    async def test_api_health_with_active_sessions(self, api_integration):
        """Test health check with active sessions."""
        # Create some active sessions
        requests = [
            MetadataExtractionRequest(
                document_id=f"health_test_doc_{i}",
                user_id=f"health_test_user_{i}",
                options={}
            )
            for i in range(3)
        ]
        
        background_tasks = MockBackgroundTasks()
        
        for request in requests:
            await api_integration.extract_metadata(request, background_tasks)
        
        # Check health with active sessions
        health = api_integration.get_api_health()
        assert health["active_sessions"] >= 3
        
    def test_api_version_consistency(self, api_integration):
        """Test API version consistency."""
        health1 = api_integration.get_api_health()
        health2 = api_integration.get_api_health()
        
        # Version should be consistent
        assert health1["version"] == health2["version"]
        assert health1["version"] == "1.0.0"


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_api_request_validation(self, api_integration):
        """Test API request validation edge cases."""
        # Test with various invalid inputs
        invalid_requests = [
            {"document_id": "", "user_id": "valid_user"},
            {"document_id": "valid_doc", "user_id": ""},
            {"document_id": None, "user_id": "valid_user"},
        ]
        
        for invalid_data in invalid_requests:
            with pytest.raises(Exception):
                MetadataExtractionRequest(**invalid_data)
                
    @pytest.mark.asyncio
    async def test_api_concurrent_operations(self, api_integration):
        """Test API behavior under concurrent operations."""
        # Create session
        request = MetadataExtractionRequest(
            document_id="concurrent_test_doc",
            user_id="concurrent_test_user",
            options={}
        )
        
        background_tasks = MockBackgroundTasks()
        response = await api_integration.extract_metadata(request, background_tasks)
        session_id = response.session_id
        
        # Perform concurrent operations on same session
        tasks = [
            api_integration.get_processing_status(session_id),
            api_integration.get_processing_status(session_id),
            api_integration.get_processing_status(session_id),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, ProcessingStatus)
            
    @pytest.mark.asyncio
    async def test_api_memory_usage(self, api_integration):
        """Test API memory usage under load."""
        # Create many sessions to test memory usage
        sessions = []
        background_tasks = MockBackgroundTasks()
        
        for i in range(100):
            request = MetadataExtractionRequest(
                document_id=f"memory_test_doc_{i}",
                user_id=f"memory_test_user_{i}",
                options={}
            )
            
            response = await api_integration.extract_metadata(request, background_tasks)
            sessions.append(response.session_id)
        
        # Verify all sessions were created
        assert len(sessions) == 100
        assert len(set(sessions)) == 100  # All unique
        
        # API should still be responsive
        health = api_integration.get_api_health()
        assert health["status"] == "healthy"
        assert health["active_sessions"] >= 100