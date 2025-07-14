#!/usr/bin/env python3
"""
Focused integration test for Worker Pool methods.

Tests just the Worker Pool methods that are called by the integration.py module.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_worker_pool_basic():
    """Test basic WorkerPool functionality without full pipeline integration."""
    logger.info("=== Testing Worker Pool Basic Functionality ===")
    
    try:
        from torematrix.processing.workers.pool import WorkerPool, WorkerConfig
        from torematrix.processing.workers.resources import ResourceLimits, ResourceMonitor
        from torematrix.core.events import EventBus
        
        # Create configuration
        config = WorkerConfig(
            async_workers=2,
            thread_workers=1,
            max_queue_size=100,
            default_timeout=30.0
        )
        
        # Create dependencies
        event_bus = EventBus()
        resource_monitor = ResourceMonitor(
            limits=ResourceLimits(max_cpu_percent=80.0, max_memory_percent=75.0)
        )
        
        # Create worker pool
        pool = WorkerPool(
            config=config,
            event_bus=event_bus,
            resource_monitor=resource_monitor
        )
        
        # Start the pool
        await pool.start()
        assert pool._running, "Pool should be running"
        logger.info("✓ Worker pool started successfully")
        
        # Test get_stats method (required by integration.py)
        stats = pool.get_stats()
        assert isinstance(stats, dict), "get_stats should return dict"
        assert 'total_workers' in stats, "Should have total_workers"
        assert 'active_workers' in stats, "Should have active_workers"
        assert 'queued_tasks' in stats, "Should have queued_tasks"
        logger.info(f"✓ get_stats() works: {stats}")
        
        # Test get_pool_stats method (Agent 3's preferred method)
        pool_stats = pool.get_pool_stats()
        assert hasattr(pool_stats, 'total_workers'), "Should have total_workers attribute"
        assert pool_stats.total_workers == 2, "Should have 2 async workers"
        logger.info(f"✓ get_pool_stats() works: total_workers={pool_stats.total_workers}")
        
        # Test wait_for_completion method (required by integration.py shutdown)
        result = await pool.wait_for_completion(timeout=1.0)
        assert result is True, "Should complete immediately with no tasks"
        logger.info("✓ wait_for_completion() works correctly")
        
        # Test that pool can be stopped
        await pool.stop(timeout=5.0)
        assert not pool._running, "Pool should be stopped"
        logger.info("✓ Worker pool stopped successfully")
        
        logger.info("✓ All Worker Pool basic tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Worker Pool basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_processor_context():
    """Test ProcessorContext compatibility."""
    logger.info("=== Testing ProcessorContext Compatibility ===")
    
    try:
        from torematrix.processing.processors.base import ProcessorContext
        
        # Create context as Agent 2 would
        context = ProcessorContext(
            document_id="test_doc_123",
            file_path="/path/to/test.pdf",
            mime_type="application/pdf",
            metadata={"author": "Test", "pages": 5},
            previous_results={"validation": {"valid": True}}
        )
        
        # Test required attributes
        assert context.document_id == "test_doc_123"
        assert context.file_path == "/path/to/test.pdf"
        assert context.mime_type == "application/pdf"
        assert isinstance(context.metadata, dict)
        assert isinstance(context.previous_results, dict)
        
        # Test get_previous_result method
        validation_result = context.get_previous_result("validation")
        assert validation_result == {"valid": True}
        
        # Test non-existent result
        missing_result = context.get_previous_result("nonexistent")
        assert missing_result is None
        
        logger.info("✓ ProcessorContext compatibility verified")
        return True
        
    except Exception as e:
        logger.error(f"✗ ProcessorContext test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_compatibility():
    """Test compatibility with integration.py expectations."""
    logger.info("=== Testing Integration.py Compatibility ===")
    
    try:
        # Test that WorkerPool has the methods that integration.py calls
        from torematrix.processing.workers.pool import WorkerPool
        
        # Check method existence
        assert hasattr(WorkerPool, 'wait_for_completion'), "Missing wait_for_completion method"
        assert hasattr(WorkerPool, 'get_stats'), "Missing get_stats method"
        assert hasattr(WorkerPool, 'get_pool_stats'), "Missing get_pool_stats method"
        assert hasattr(WorkerPool, 'start'), "Missing start method"
        assert hasattr(WorkerPool, 'stop'), "Missing stop method"
        
        # Check method signatures
        import inspect
        
        # wait_for_completion should accept timeout parameter
        wait_sig = inspect.signature(WorkerPool.wait_for_completion)
        assert 'timeout' in wait_sig.parameters, "wait_for_completion should accept timeout"
        
        # get_stats should not require parameters
        stats_sig = inspect.signature(WorkerPool.get_stats)
        required_params = [p for p in stats_sig.parameters.values() 
                          if p.default == inspect.Parameter.empty and p.name != 'self']
        assert len(required_params) == 0, "get_stats should not require parameters"
        
        logger.info("✓ Integration compatibility verified")
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_focused_tests():
    """Run focused integration tests."""
    logger.info("Starting Focused Pipeline-Worker Integration Tests")
    
    tests = [
        test_processor_context,
        test_integration_compatibility,
        test_worker_pool_basic,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            success = await test()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed > 0:
        logger.error("Some tests failed!")
        return False
    else:
        logger.info("All focused tests passed!")
        return True


if __name__ == "__main__":
    success = asyncio.run(run_focused_tests())
    sys.exit(0 if success else 1)