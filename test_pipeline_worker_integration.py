#!/usr/bin/env python3
"""
Integration test for Pipeline Manager and Worker Pool.

Tests the integration between Agent 1's Pipeline Manager and Agent 3's Worker Pool
to ensure proper task submission and execution.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from torematrix.processing.integration import ProcessingSystem, create_default_config
from torematrix.processing.pipeline.config import PipelineConfig, StageConfig, StageType
from torematrix.processing.workers.config import WorkerConfig
from torematrix.processing.workers.resources import ResourceLimits
from torematrix.processing.processors.base import (
    BaseProcessor, ProcessorContext, ProcessorResult, ProcessorMetadata, 
    StageStatus, ProcessorCapability
)
from torematrix.processing.processors.registry import ProcessorRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockProcessor(BaseProcessor):
    """Mock processor for testing pipeline integration."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="mock_processor",
            version="1.0.0",
            description="Mock processor for testing",
            author="Test",
            capabilities=[ProcessorCapability.TEXT_EXTRACTION],
            supported_formats=["txt", "pdf"],
            timeout_seconds=10
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Mock processing that simulates work."""
        logger.info(f"MockProcessor processing document: {context.document_id}")
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        return ProcessorResult(
            processor_name="mock_processor",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={
                "text": f"Processed content for {context.document_id}",
                "pages": 1,
                "words": 100
            },
            metadata={
                "file_size": 1024,
                "processing_time": 0.1
            }
        )


class SlowProcessor(BaseProcessor):
    """Slow processor for testing worker pool concurrency."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="slow_processor",
            version="1.0.0",
            description="Slow processor for testing concurrency",
            author="Test",
            capabilities=[ProcessorCapability.METADATA_EXTRACTION],
            supported_formats=["txt", "pdf"],
            timeout_seconds=30
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Slow processing to test concurrency."""
        logger.info(f"SlowProcessor processing document: {context.document_id}")
        
        # Simulate longer work
        await asyncio.sleep(2.0)
        
        return ProcessorResult(
            processor_name="slow_processor",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={
                "metadata": f"Metadata for {context.document_id}",
                "author": "Test Author",
                "created_date": "2024-01-01"
            }
        )


async def test_basic_integration():
    """Test basic pipeline and worker pool integration."""
    logger.info("=== Testing Basic Pipeline-Worker Integration ===")
    
    # Create custom configuration
    pipeline_config = PipelineConfig(
        name="test_pipeline",
        stages=[
            StageConfig(
                name="mock_stage",
                type=StageType.PROCESSOR,
                processor="mock_processor",
                dependencies=[]
            )
        ]
    )
    
    worker_config = WorkerConfig(
        async_workers=2,
        thread_workers=1,
        max_queue_size=100,
        default_timeout=30.0
    )
    
    resource_limits = ResourceLimits(
        max_cpu_percent=80.0,
        max_memory_percent=75.0
    )
    
    # Create processing system configuration
    from torematrix.processing.integration import ProcessingSystemConfig
    config = ProcessingSystemConfig(
        pipeline_config=pipeline_config,
        worker_config=worker_config,
        resource_limits=resource_limits,
        monitoring_enabled=False  # Disable for testing
    )
    
    # Create and start processing system
    system = ProcessingSystem(config)
    
    try:
        await system.initialize()
        
        # Register mock processor
        system.processor_registry.register(MockProcessor)
        
        # Verify worker pool is running
        assert system.worker_pool._running, "Worker pool should be running"
        logger.info("✓ Worker pool started successfully")
        
        # Test get_stats method
        stats = system.worker_pool.get_stats()
        assert "total_workers" in stats, "get_stats should return statistics"
        logger.info(f"✓ Worker pool stats: {stats}")
        
        # Test get_pool_stats method (Agent 3 method)
        pool_stats = system.worker_pool.get_pool_stats()
        assert pool_stats.total_workers > 0, "Should have workers"
        logger.info(f"✓ Pool stats: total_workers={pool_stats.total_workers}")
        
        # Test wait_for_completion method
        completion_result = await system.worker_pool.wait_for_completion(timeout=1.0)
        assert completion_result is True, "Should complete immediately with no tasks"
        logger.info("✓ wait_for_completion works correctly")
        
        # Create test document
        test_doc = Path(__file__).parent / "test_document.txt"
        test_doc.write_text("This is a test document for processing.")
        
        try:
            # Process document through pipeline
            pipeline_id = await system.process_document(
                document_path=test_doc,
                pipeline_name="test_pipeline",
                metadata={"test": True}
            )
            
            logger.info(f"✓ Document processed with pipeline ID: {pipeline_id}")
            
            # Wait for completion
            await asyncio.sleep(1.0)  # Give time for processing
            
            # Check pipeline status
            status = system.get_pipeline_status(pipeline_id)
            logger.info(f"✓ Pipeline status: {status}")
            
            # Check system metrics
            metrics = system.get_system_metrics()
            logger.info(f"✓ System metrics: workers={metrics['workers']['total_workers']}")
            
        finally:
            # Clean up test file
            if test_doc.exists():
                test_doc.unlink()
        
        logger.info("✓ Basic integration test passed!")
        
    except Exception as e:
        logger.error(f"✗ Basic integration test failed: {e}")
        raise
    finally:
        await system.shutdown()


async def test_concurrent_processing():
    """Test concurrent processing with multiple documents."""
    logger.info("=== Testing Concurrent Processing ===")
    
    # Create configuration with concurrent stages
    pipeline_config = PipelineConfig(
        name="concurrent_pipeline",
        stages=[
            StageConfig(
                name="mock_stage",
                type=StageType.PROCESSOR,
                processor="mock_processor",
                dependencies=[]
            ),
            StageConfig(
                name="slow_stage",
                type=StageType.PROCESSOR,
                processor="slow_processor",
                dependencies=["mock_stage"]
            )
        ]
    )
    
    worker_config = WorkerConfig(
        async_workers=4,
        thread_workers=2,
        max_queue_size=100,
        default_timeout=60.0
    )
    
    resource_limits = ResourceLimits(
        max_cpu_percent=90.0,
        max_memory_percent=80.0
    )
    
    from torematrix.processing.integration import ProcessingSystemConfig
    config = ProcessingSystemConfig(
        pipeline_config=pipeline_config,
        worker_config=worker_config,
        resource_limits=resource_limits,
        monitoring_enabled=False
    )
    
    system = ProcessingSystem(config)
    
    try:
        await system.initialize()
        
        # Register processors
        system.processor_registry.register(MockProcessor)
        system.processor_registry.register(SlowProcessor)
        
        # Create multiple test documents
        test_docs = []
        for i in range(3):
            doc = Path(__file__).parent / f"test_document_{i}.txt"
            doc.write_text(f"This is test document {i} for concurrent processing.")
            test_docs.append(doc)
        
        try:
            # Process documents concurrently
            start_time = time.time()
            
            tasks = []
            for i, doc in enumerate(test_docs):
                task = system.process_document(
                    document_path=doc,
                    pipeline_name="concurrent_pipeline",
                    metadata={"document_index": i}
                )
                tasks.append(task)
            
            # Wait for all pipeline IDs
            pipeline_ids = await asyncio.gather(*tasks)
            logger.info(f"✓ Started {len(pipeline_ids)} concurrent pipelines")
            
            # Wait for processing to complete
            await asyncio.sleep(8.0)  # Should be enough for slow processors
            
            # Wait for worker pool to complete all tasks
            completion_result = await system.worker_pool.wait_for_completion(timeout=10.0)
            logger.info(f"✓ All tasks completed: {completion_result}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Check final statistics
            final_stats = system.worker_pool.get_stats()
            logger.info(f"✓ Final stats: completed={final_stats['completed_tasks']}, "
                       f"failed={final_stats['failed_tasks']}")
            
            logger.info(f"✓ Concurrent processing completed in {total_time:.2f}s")
            
            # Verify we processed tasks concurrently (should be faster than sequential)
            expected_sequential_time = 3 * 2.1  # 3 docs * 2.1s each
            assert total_time < expected_sequential_time * 0.8, \
                f"Should be faster than sequential: {total_time}s vs {expected_sequential_time}s"
            
        finally:
            # Clean up test files
            for doc in test_docs:
                if doc.exists():
                    doc.unlink()
        
        logger.info("✓ Concurrent processing test passed!")
        
    except Exception as e:
        logger.error(f"✗ Concurrent processing test failed: {e}")
        raise
    finally:
        await system.shutdown()


async def test_processor_context_compatibility():
    """Test that ProcessorContext from Agent 2 is compatible with Worker Pool."""
    logger.info("=== Testing ProcessorContext Compatibility ===")
    
    from torematrix.processing.processors.base import ProcessorContext
    
    # Create a processor context as Agent 2 would
    context = ProcessorContext(
        document_id="test_doc_123",
        file_path="/path/to/test.pdf",
        mime_type="application/pdf",
        metadata={"author": "Test", "pages": 5},
        previous_results={"validation": {"valid": True}}
    )
    
    # Test that it has expected attributes
    assert hasattr(context, 'document_id'), "Context should have document_id"
    assert hasattr(context, 'file_path'), "Context should have file_path"
    assert hasattr(context, 'mime_type'), "Context should have mime_type"
    assert hasattr(context, 'metadata'), "Context should have metadata"
    assert hasattr(context, 'previous_results'), "Context should have previous_results"
    
    # Test get_previous_result method
    validation_result = context.get_previous_result("validation")
    assert validation_result == {"valid": True}, "Should retrieve previous results correctly"
    
    logger.info("✓ ProcessorContext compatibility verified")


async def test_worker_pool_methods():
    """Test that all required WorkerPool methods exist and work."""
    logger.info("=== Testing Worker Pool Method Compatibility ===")
    
    config = create_default_config()
    system = ProcessingSystem(config)
    
    try:
        await system.initialize()
        
        # Test required methods exist
        assert hasattr(system.worker_pool, 'wait_for_completion'), "Should have wait_for_completion method"
        assert hasattr(system.worker_pool, 'get_stats'), "Should have get_stats method"
        assert hasattr(system.worker_pool, 'get_pool_stats'), "Should have get_pool_stats method"
        
        # Test method signatures and return types
        stats = system.worker_pool.get_stats()
        assert isinstance(stats, dict), "get_stats should return dict"
        assert 'total_workers' in stats, "get_stats should include total_workers"
        
        pool_stats = system.worker_pool.get_pool_stats()
        assert hasattr(pool_stats, 'total_workers'), "get_pool_stats should return PoolStats object"
        
        # Test wait_for_completion
        result = await system.worker_pool.wait_for_completion(timeout=1.0)
        assert isinstance(result, bool), "wait_for_completion should return bool"
        
        logger.info("✓ All required methods are present and functional")
        
    finally:
        await system.shutdown()


async def run_all_tests():
    """Run all integration tests."""
    logger.info("Starting Pipeline-Worker Integration Tests")
    
    tests = [
        test_processor_context_compatibility,
        test_worker_pool_methods,
        test_basic_integration,
        test_concurrent_processing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            failed += 1
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed > 0:
        logger.error("Some tests failed!")
        return False
    else:
        logger.info("All tests passed!")
        return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)