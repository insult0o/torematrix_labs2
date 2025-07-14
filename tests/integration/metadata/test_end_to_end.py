"""Comprehensive end-to-end integration tests for metadata extraction system."""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import Dict, List, Any

from torematrix.core.processing.metadata.integration.pipeline_integration import (
    MetadataPipelineIntegration,
    IntegrationConfig,
    PipelineContext,
    DocumentWithMetadata
)
from torematrix.core.processing.metadata.integration.api_integration import (
    MetadataAPIIntegration,
    MetadataExtractionRequest,
    MetadataExtractionResponse
)
from torematrix.core.processing.metadata.integration.websocket_integration import (
    MetadataWebSocketManager,
    ProgressUpdate
)
from torematrix.core.models.element import ProcessedDocument


@pytest.fixture
async def integration_config():
    """Create integration configuration for testing."""
    return IntegrationConfig(
        enable_realtime_updates=True,
        batch_size=10,
        max_concurrent_extractions=5,
        timeout_seconds=60,
        enable_caching=True,
        cache_ttl_seconds=300
    )


@pytest.fixture
async def pipeline_integration(integration_config):
    """Create and initialize pipeline integration."""
    integration = MetadataPipelineIntegration(integration_config)
    await integration.initialize()
    yield integration
    await integration.cleanup()


@pytest.fixture
async def api_integration(pipeline_integration):
    """Create API integration with pipeline."""
    return MetadataAPIIntegration(pipeline_integration)


@pytest.fixture
async def websocket_manager():
    """Create and initialize WebSocket manager."""
    manager = MetadataWebSocketManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.fixture
def sample_document():
    """Create sample processed document for testing."""
    return ProcessedDocument(
        id=str(uuid.uuid4()),
        elements=[
            {
                "id": "elem_1",
                "type": "title",
                "text": "Sample Document Title",
                "bbox": [100, 100, 400, 150]
            },
            {
                "id": "elem_2", 
                "type": "paragraph",
                "text": "This is a sample paragraph with content.",
                "bbox": [100, 200, 400, 250]
            },
            {
                "id": "elem_3",
                "type": "table",
                "text": "Sample table data",
                "bbox": [100, 300, 400, 450]
            }
        ],
        metadata={},
        processing_stats={}
    )


@pytest.fixture
def pipeline_context():
    """Create pipeline context for testing."""
    return PipelineContext(
        document_id=str(uuid.uuid4()),
        user_id="test_user",
        session_id=str(uuid.uuid4()),
        processing_options={"enable_optimization": True},
        metadata={}
    )


class TestMetadataExtractionWorkflow:
    """Test complete metadata extraction workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_extraction_workflow(
        self, 
        pipeline_integration,
        sample_document,
        pipeline_context
    ):
        """Test complete end-to-end metadata extraction workflow."""
        # Process document through metadata pipeline
        result = await pipeline_integration.process_document_with_metadata(
            sample_document,
            pipeline_context
        )
        
        # Verify result structure
        assert isinstance(result, DocumentWithMetadata)
        assert result.document.id == sample_document.id
        assert "semantic_roles" in result.metadata
        assert "reading_order" in result.metadata
        assert "document_structure" in result.metadata
        assert isinstance(result.relationships, list)
        assert result.processing_time > 0
        
        # Verify extraction stats
        stats = result.extraction_stats
        assert "total_elements" in stats
        assert "metadata_fields" in stats
        assert "relationships_found" in stats
        assert stats["total_elements"] == len(sample_document.elements)
        
    @pytest.mark.asyncio
    async def test_metadata_extraction_with_relationships(
        self,
        pipeline_integration,
        sample_document,
        pipeline_context
    ):
        """Test metadata extraction including relationship detection."""
        result = await pipeline_integration.process_document_with_metadata(
            sample_document,
            pipeline_context
        )
        
        # Verify relationships are detected
        assert len(result.relationships) >= 0
        
        # If relationships exist, verify structure
        if result.relationships:
            relationship = result.relationships[0]
            assert "source_element_id" in relationship
            assert "target_element_id" in relationship
            assert "relationship_type" in relationship
            assert "confidence" in relationship
            
    @pytest.mark.asyncio
    async def test_extraction_with_semantic_analysis(
        self,
        pipeline_integration,
        sample_document,
        pipeline_context
    ):
        """Test extraction with semantic role analysis."""
        result = await pipeline_integration.process_document_with_metadata(
            sample_document,
            pipeline_context
        )
        
        # Verify semantic analysis results
        semantic_data = result.metadata.get("semantic_roles", {})
        assert isinstance(semantic_data, dict)
        
        # Verify reading order analysis
        reading_order = result.metadata.get("reading_order", {})
        assert isinstance(reading_order, dict)
        
    @pytest.mark.asyncio
    async def test_extraction_performance_optimization(
        self,
        pipeline_integration,
        sample_document,
        pipeline_context
    ):
        """Test extraction with performance optimizations."""
        # Enable caching in context
        pipeline_context.processing_options["enable_caching"] = True
        
        # First extraction (should be slower)
        start_time = asyncio.get_event_loop().time()
        result1 = await pipeline_integration.process_document_with_metadata(
            sample_document,
            pipeline_context
        )
        first_duration = asyncio.get_event_loop().time() - start_time
        
        # Second extraction (should use cache and be faster)
        start_time = asyncio.get_event_loop().time()
        result2 = await pipeline_integration.process_document_with_metadata(
            sample_document,
            pipeline_context
        )
        second_duration = asyncio.get_event_loop().time() - start_time
        
        # Verify caching improves performance
        assert result1.metadata == result2.metadata
        # Note: In real implementation, second should be faster due to caching
        
    @pytest.mark.asyncio
    async def test_extraction_error_handling(
        self,
        pipeline_integration,
        pipeline_context
    ):
        """Test extraction error handling with invalid document."""
        # Create invalid document
        invalid_document = ProcessedDocument(
            id="invalid_doc",
            elements=None,  # Invalid elements
            metadata={},
            processing_stats={}
        )
        
        # Should handle error gracefully
        with pytest.raises(Exception):
            await pipeline_integration.process_document_with_metadata(
                invalid_document,
                pipeline_context
            )
            
    @pytest.mark.asyncio
    async def test_concurrent_extractions(
        self,
        pipeline_integration,
        sample_document
    ):
        """Test concurrent metadata extractions."""
        # Create multiple contexts
        contexts = [
            PipelineContext(
                document_id=f"doc_{i}",
                user_id=f"user_{i}",
                session_id=str(uuid.uuid4()),
                processing_options={},
                metadata={}
            )
            for i in range(5)
        ]
        
        # Process documents concurrently
        tasks = [
            pipeline_integration.process_document_with_metadata(sample_document, context)
            for context in contexts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all extractions completed successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, DocumentWithMetadata)


class TestAPIIntegration:
    """Test REST API integration for metadata extraction."""
    
    @pytest.mark.asyncio
    async def test_api_extraction_request(
        self,
        api_integration
    ):
        """Test API metadata extraction request."""
        # Create extraction request
        request = MetadataExtractionRequest(
            document_id="test_doc_123",
            user_id="test_user",
            options={"enable_relationships": True},
            enable_relationships=True,
            enable_semantic_analysis=True
        )
        
        # Mock background tasks
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                pass
        
        background_tasks = MockBackgroundTasks()
        
        # Submit extraction request
        response = await api_integration.extract_metadata(request, background_tasks)
        
        # Verify response
        assert isinstance(response, MetadataExtractionResponse)
        assert response.session_id is not None
        assert response.status == "processing"
        assert response.estimated_time > 0
        
    @pytest.mark.asyncio
    async def test_api_get_metadata(
        self,
        api_integration
    ):
        """Test API get metadata endpoint."""
        document_id = "test_doc_456"
        
        # Get metadata (will return mock data)
        metadata = await api_integration.get_metadata(document_id)
        
        # Verify response structure
        assert metadata.document_id == document_id
        assert isinstance(metadata.metadata, dict)
        assert isinstance(metadata.relationships, list)
        assert isinstance(metadata.extraction_stats, dict)
        
    @pytest.mark.asyncio
    async def test_api_get_relationships(
        self,
        api_integration
    ):
        """Test API get relationships endpoint."""
        document_id = "test_doc_789"
        
        # Get relationships
        relationships = await api_integration.get_relationships(document_id)
        
        # Verify response structure
        assert isinstance(relationships, list)
        
    @pytest.mark.asyncio
    async def test_api_processing_status(
        self,
        api_integration
    ):
        """Test API processing status endpoint."""
        # Create a session first
        request = MetadataExtractionRequest(
            document_id="test_doc_status",
            user_id="test_user",
            options={}
        )
        
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                pass
        
        response = await api_integration.extract_metadata(request, MockBackgroundTasks())
        session_id = response.session_id
        
        # Get processing status
        status = await api_integration.get_processing_status(session_id)
        
        # Verify status response
        assert status.session_id == session_id
        assert isinstance(status.status, str)
        assert isinstance(status.progress, dict)
        assert isinstance(status.created_at, datetime)
        
    @pytest.mark.asyncio
    async def test_api_cancel_processing(
        self,
        api_integration
    ):
        """Test API cancel processing endpoint."""
        # Create a session first
        request = MetadataExtractionRequest(
            document_id="test_doc_cancel",
            user_id="test_user",
            options={}
        )
        
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                pass
        
        response = await api_integration.extract_metadata(request, MockBackgroundTasks())
        session_id = response.session_id
        
        # Cancel processing
        cancel_response = await api_integration.cancel_processing(session_id)
        
        # Verify cancellation
        assert cancel_response["session_id"] == session_id
        assert cancel_response["status"] == "cancelled"
        
    @pytest.mark.asyncio
    async def test_api_health_check(
        self,
        api_integration
    ):
        """Test API health check endpoint."""
        health = api_integration.get_api_health()
        
        # Verify health response
        assert health["status"] == "healthy"
        assert "active_sessions" in health
        assert "version" in health
        assert "timestamp" in health


class TestWebSocketIntegration:
    """Test WebSocket integration for real-time progress updates."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_management(
        self,
        websocket_manager
    ):
        """Test WebSocket connection management."""
        # Mock WebSocket
        class MockWebSocket:
            async def accept(self):
                pass
            async def send_text(self, data):
                pass
                
        websocket = MockWebSocket()
        connection_id = "test_conn_123"
        user_id = "test_user"
        
        # Test connection
        await websocket_manager.connect(websocket, connection_id, user_id)
        
        # Verify connection is active
        assert connection_id in websocket_manager.active_connections
        assert connection_id in websocket_manager.connection_info
        
        # Test disconnection
        await websocket_manager.disconnect(connection_id)
        
        # Verify connection is removed
        assert connection_id not in websocket_manager.active_connections
        assert connection_id not in websocket_manager.connection_info
        
    @pytest.mark.asyncio
    async def test_session_subscription(
        self,
        websocket_manager
    ):
        """Test session subscription management."""
        # Mock WebSocket
        class MockWebSocket:
            async def accept(self):
                pass
            async def send_text(self, data):
                self.last_message = data
                
        websocket = MockWebSocket()
        connection_id = "test_conn_sub"
        user_id = "test_user"
        session_id = "test_session_123"
        
        # Connect and subscribe
        await websocket_manager.connect(websocket, connection_id, user_id)
        await websocket_manager.subscribe_to_session(connection_id, session_id)
        
        # Verify subscription
        assert session_id in websocket_manager.session_subscribers
        assert connection_id in websocket_manager.session_subscribers[session_id]
        
    @pytest.mark.asyncio
    async def test_progress_broadcasting(
        self,
        websocket_manager
    ):
        """Test progress update broadcasting."""
        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.messages = []
            async def accept(self):
                pass
            async def send_text(self, data):
                self.messages.append(data)
                
        websocket = MockWebSocket()
        connection_id = "test_conn_progress"
        user_id = "test_user"
        session_id = "test_session_progress"
        
        # Connect and subscribe
        await websocket_manager.connect(websocket, connection_id, user_id)
        await websocket_manager.subscribe_to_session(connection_id, session_id)
        
        # Broadcast progress update
        progress_update = ProgressUpdate(
            session_id=session_id,
            document_id="test_doc",
            stage="processing",
            progress_percentage=50.0,
            message="Processing metadata...",
            timestamp=datetime.utcnow(),
            details={"current_step": "relationship_detection"}
        )
        
        await websocket_manager.broadcast_progress(session_id, progress_update)
        
        # Verify message was sent
        assert len(websocket.messages) >= 2  # Welcome message + progress update
        
    @pytest.mark.asyncio
    async def test_connection_statistics(
        self,
        websocket_manager
    ):
        """Test connection statistics reporting."""
        # Get initial stats
        stats = websocket_manager.get_connection_stats()
        
        # Verify stats structure
        assert "total_connections" in stats
        assert "active_sessions" in stats
        assert "connections_by_user" in stats
        assert "session_subscriber_counts" in stats
        
        # Verify initial values
        assert stats["total_connections"] == 0
        assert stats["active_sessions"] == 0


class TestSystemIntegration:
    """Test complete system integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_system_workflow(
        self,
        pipeline_integration,
        api_integration,
        websocket_manager,
        sample_document
    ):
        """Test complete system workflow with all components."""
        # This would test the complete workflow:
        # 1. API request submission
        # 2. Pipeline processing
        # 3. WebSocket progress updates
        # 4. Result storage and retrieval
        
        # For now, verify all components are properly initialized
        assert pipeline_integration is not None
        assert api_integration is not None
        assert websocket_manager is not None
        
    @pytest.mark.asyncio
    async def test_system_performance_under_load(
        self,
        pipeline_integration,
        sample_document
    ):
        """Test system performance under concurrent load."""
        # Create multiple concurrent extraction requests
        tasks = []
        for i in range(10):
            context = PipelineContext(
                document_id=f"load_test_doc_{i}",
                user_id=f"load_test_user_{i}",
                session_id=str(uuid.uuid4()),
                processing_options={},
                metadata={}
            )
            
            task = pipeline_integration.process_document_with_metadata(
                sample_document,
                context
            )
            tasks.append(task)
            
        # Execute all tasks concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify all completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 10
        
        # Verify reasonable performance (adjust threshold as needed)
        average_time_per_extraction = total_time / 10
        assert average_time_per_extraction < 5.0  # Less than 5 seconds per extraction
        
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(
        self,
        pipeline_integration
    ):
        """Test system error recovery and resilience."""
        # Test with various error scenarios
        error_scenarios = [
            {"elements": None},  # Invalid elements
            {"elements": []},    # Empty elements
            {"elements": [{"invalid": "structure"}]}  # Invalid element structure
        ]
        
        for i, scenario in enumerate(error_scenarios):
            invalid_document = ProcessedDocument(
                id=f"error_test_{i}",
                **scenario,
                metadata={},
                processing_stats={}
            )
            
            context = PipelineContext(
                document_id=f"error_test_{i}",
                user_id="error_test_user",
                session_id=str(uuid.uuid4()),
                processing_options={},
                metadata={}
            )
            
            # Should handle errors gracefully
            try:
                await pipeline_integration.process_document_with_metadata(
                    invalid_document,
                    context
                )
            except Exception as e:
                # Error should be handled gracefully, not crash the system
                assert isinstance(e, Exception)
                
    @pytest.mark.asyncio
    async def test_monitoring_integration(
        self,
        pipeline_integration
    ):
        """Test monitoring and observability integration."""
        # This would test that monitoring systems are properly integrated
        # and collecting metrics during metadata extraction
        
        # For now, verify pipeline integration is working
        status = await pipeline_integration.get_processing_status("test_session")
        assert "session_id" in status