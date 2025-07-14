"""
Test the integrated TORE Matrix V3 system.

This test verifies that all components work together properly
after the integration fixes.
"""

import asyncio
import pytest
from pathlib import Path
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_system_initialization():
    """Test that the system can be initialized."""
    from torematrix.integration import ToreMatrixSystem, SystemConfig
    
    config = SystemConfig(
        name="Test System",
        storage_backend="sqlite",
        storage_path=":memory:",
        enable_monitoring=False
    )
    
    system = ToreMatrixSystem(config)
    
    assert system.status.value == "initializing"
    assert system.config.name == "Test System"
    
    # Initialize the system
    await system.initialize()
    
    assert system.status.value == "running"
    assert system.event_bus is not None
    assert system.storage is not None
    assert system.state is not None
    
    # Shutdown
    await system.shutdown()
    assert system.status.value == "stopped"


@pytest.mark.asyncio
async def test_event_flow():
    """Test event flow through the system."""
    from torematrix.integration import create_system, SystemConfig
    
    config = SystemConfig(
        storage_path=":memory:",
        enable_monitoring=False
    )
    
    system = await create_system(config)
    
    # Track events
    events_received = []
    
    async def event_tracker(event):
        events_received.append(event)
        logger.info(f"Event received: {getattr(event, 'event_type', 'unknown')}")
    
    # Subscribe to all events
    system.event_bus.subscribe("*", event_tracker)
    
    # Emit a test event
    await system.event_bus.emit("test.event", {"data": "test"})
    
    # Allow event processing
    await asyncio.sleep(0.1)
    
    # Check event was received
    assert len(events_received) > 0
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_document_processing_flow():
    """Test document processing flow (mocked)."""
    from torematrix.integration import create_system, SystemConfig
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Test document content")
        
        config = SystemConfig(
            storage_path=f"{tmpdir}/test.db",
            enable_monitoring=False,
            max_concurrent_documents=10
        )
        
        system = await create_system(config)
        
        # Track document states
        doc_states = []
        
        async def state_tracker(event):
            data = system.event_coordinator._extract_event_data(event)
            if "id" in data:
                state = system.event_coordinator.get_document_state(data["id"])
                if state:
                    doc_states.append(state.value)
        
        system.event_bus.subscribe("document.*", state_tracker)
        
        # Submit document for processing
        doc_id = await system.process_document(test_file)
        
        assert doc_id is not None
        assert doc_id.startswith("doc_")
        
        # Check document is tracked
        status = system.get_document_status(doc_id)
        assert status is not None
        assert status["id"] == doc_id
        
        # Allow some processing
        await asyncio.sleep(0.2)
        
        # Check events were fired
        assert len(doc_states) > 0
        
        await system.shutdown()


@pytest.mark.asyncio
async def test_adapter_functionality():
    """Test that adapters work correctly."""
    from torematrix.integration.adapters import (
        EventBusAdapter,
        StorageAdapter,
        StateAdapter,
        ConfigAdapter
    )
    
    # Test EventBusAdapter
    class MockEventBus:
        def __init__(self):
            self.events = []
            
        async def publish(self, event):
            self.events.append(event)
            
        def subscribe(self, pattern, handler):
            pass
    
    mock_bus = MockEventBus()
    adapter = EventBusAdapter(mock_bus)
    
    await adapter.emit("test.event", {"data": "test"})
    assert len(mock_bus.events) == 1
    
    # Test StorageAdapter
    class MockStorage:
        def __init__(self):
            self.data = {}
            
        async def create(self, element):
            self.data["test"] = element
            return "test"
            
        async def get(self, id):
            return self.data.get(id)
    
    mock_storage = MockStorage()
    storage_adapter = StorageAdapter(mock_storage)
    
    element_id = await storage_adapter.save_element({"type": "test"})
    assert element_id == "test"
    
    retrieved = await storage_adapter.get_element("test")
    assert retrieved is not None


@pytest.mark.asyncio
async def test_data_transformation():
    """Test data transformation between formats."""
    from torematrix.integration.transformer import DataTransformer
    
    transformer = DataTransformer()
    
    # Test unstructured to core transformation
    unstructured_elements = [
        {
            "type": "Title",
            "text": "Test Title",
            "metadata": {"page_number": 1}
        },
        {
            "type": "NarrativeText",
            "text": "Test content",
            "metadata": {"page_number": 1}
        }
    ]
    
    # Transform to core format
    core_elements = transformer.transform_document_batch(
        unstructured_elements,
        from_format="unstructured",
        to_format="core"
    )
    
    assert len(core_elements) == 2
    assert core_elements[0]["element_type"] == "TitleElement"
    assert core_elements[0]["text"] == "Test Title"
    
    # Transform to pipeline format
    pipeline_elements = transformer.transform_document_batch(
        core_elements,
        from_format="core",
        to_format="pipeline"
    )
    
    assert len(pipeline_elements) == 2
    assert pipeline_elements[0]["type"] == "title"
    assert pipeline_elements[0]["content"] == "Test Title"
    
    # Transform to storage format
    storage_elements = transformer.transform_document_batch(
        pipeline_elements,
        from_format="pipeline", 
        to_format="storage"
    )
    
    assert len(storage_elements) == 2
    assert storage_elements[0]["kind"] == "TITLE"
    assert storage_elements[0]["value"] == "Test Title"


@pytest.mark.asyncio
async def test_system_status():
    """Test system status and statistics."""
    from torematrix.integration import create_system, SystemConfig
    
    config = SystemConfig(
        storage_path=":memory:",
        enable_monitoring=False
    )
    
    system = await create_system(config)
    
    # Get system status
    status = system.get_system_status()
    
    assert status["status"] == "running"
    assert status["version"] == "3.0.0"
    assert status["active_documents"] == 0
    assert status["total_processed"] == 0
    assert "configuration" in status
    
    # Test pause/resume
    await system.pause()
    assert system.status.value == "paused"
    
    await system.resume()
    assert system.status.value == "running"
    
    await system.shutdown()


def test_imports():
    """Test that main imports work correctly."""
    try:
        from torematrix import (
            ToreMatrixSystem,
            SystemConfig,
            create_system,
            get_version,
            get_system_info
        )
        
        # Check version
        assert get_version() == "3.0.0"
        
        # Check system info
        info = get_system_info()
        assert info["name"] == "TORE Matrix V3"
        assert len(info["features"]) > 0
        
        # Check classes are importable
        assert ToreMatrixSystem is not None
        assert SystemConfig is not None
        
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_system_initialization())
    asyncio.run(test_event_flow())
    asyncio.run(test_document_processing_flow())
    asyncio.run(test_adapter_functionality())
    asyncio.run(test_data_transformation())
    asyncio.run(test_system_status())
    test_imports()
    
    print("\n✅ All integration tests passed!")