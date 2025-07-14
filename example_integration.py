"""
Example of using the integrated TORE Matrix V3 system.

This demonstrates how all components work together after integration.
"""

import asyncio
import logging
from pathlib import Path
import tempfile

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate the integrated system."""
    
    # Import the integrated system
    from torematrix import ToreMatrixSystem, SystemConfig, create_system
    
    logger.info("=== TORE Matrix V3 Integration Demo ===")
    
    # 1. Create system with configuration
    config = SystemConfig(
        name="Demo System",
        storage_backend="sqlite",
        storage_path=":memory:",  # In-memory for demo
        max_concurrent_documents=10,
        enable_monitoring=False,  # Disable for demo
        enable_ocr=True,
        default_pipeline="standard"
    )
    
    logger.info("Creating TORE Matrix system...")
    system = await create_system(config)
    
    # 2. Show system status
    status = system.get_system_status()
    logger.info(f"System Status: {status['status']}")
    logger.info(f"Version: {status['version']}")
    logger.info(f"Configuration: {status['configuration']}")
    
    # 3. Demonstrate event flow
    logger.info("\n--- Testing Event Flow ---")
    
    # Track events
    events_captured = []
    
    async def event_monitor(event):
        event_type = getattr(event, 'event_type', 'unknown')
        logger.info(f"Event captured: {event_type}")
        events_captured.append(event_type)
    
    # Subscribe to all events
    system.event_bus.subscribe("*", event_monitor)
    
    # Emit some test events
    await system.event_bus.emit("test.event1", {"message": "Hello"})
    await system.event_bus.emit("test.event2", {"message": "World"})
    
    # Allow events to process
    await asyncio.sleep(0.5)
    
    logger.info(f"Total events captured: {len(events_captured)}")
    
    # 4. Demonstrate document processing (simulated)
    logger.info("\n--- Testing Document Processing ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test document
        test_file = Path(tmpdir) / "test_document.txt"
        test_file.write_text("""
        TORE Matrix V3 Integration Test Document
        
        This document demonstrates the integrated processing pipeline.
        It will be processed through the following stages:
        1. Upload and validation
        2. Content extraction
        3. Element transformation
        4. Storage
        
        The system handles events, state management, and coordination
        between all components automatically.
        """)
        
        # Submit document for processing
        try:
            doc_id = await system.process_document(
                file_path=test_file,
                metadata={
                    "source": "demo",
                    "type": "test"
                },
                priority="high"
            )
            
            logger.info(f"Document submitted: {doc_id}")
            
            # Check document status
            status = system.get_document_status(doc_id)
            if status:
                logger.info(f"Document status: {status}")
            
            # Monitor document progress
            await asyncio.sleep(1.0)
            
            # Check active documents
            active_docs = system.event_coordinator.get_active_documents()
            logger.info(f"Active documents: {len(active_docs)}")
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
    
    # 5. Demonstrate data transformation
    logger.info("\n--- Testing Data Transformation ---")
    
    # Example element transformation
    test_elements = [
        {
            "type": "Title",
            "text": "Integration Test",
            "metadata": {"page_number": 1}
        }
    ]
    
    # Transform through the pipeline
    transformed = system.data_transformer.transform_document_batch(
        test_elements,
        from_format="unstructured",
        to_format="storage"
    )
    
    logger.info(f"Original: {test_elements[0]}")
    logger.info(f"Transformed: {transformed[0]}")
    
    # 6. Test storage adapter
    logger.info("\n--- Testing Storage Adapter ---")
    
    # Save an element
    element_id = await system.storage.save_element({
        "type": "test",
        "content": "Integration test element",
        "timestamp": "2024-01-01"
    })
    
    logger.info(f"Saved element: {element_id}")
    
    # Retrieve element
    retrieved = await system.storage.get_element(element_id)
    logger.info(f"Retrieved: {retrieved}")
    
    # 7. Show final system statistics
    logger.info("\n--- Final System Statistics ---")
    
    final_status = system.get_system_status()
    logger.info(f"Total processed: {final_status['total_processed']}")
    logger.info(f"Active documents: {final_status['active_documents']}")
    
    if final_status['uptime_seconds']:
        logger.info(f"Uptime: {final_status['uptime_seconds']:.2f} seconds")
    
    # 8. Shutdown
    logger.info("\n--- Shutting Down ---")
    await system.shutdown()
    
    logger.info("✅ Integration demo complete!")


if __name__ == "__main__":
    asyncio.run(main())