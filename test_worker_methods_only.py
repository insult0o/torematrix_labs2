#!/usr/bin/env python3
"""
Direct test of Worker Pool methods required by integration.py.

Tests only the specific methods without dependencies.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_method_signatures():
    """Test that WorkerPool has the required methods with correct signatures."""
    logger.info("=== Testing Method Signatures ===")
    
    try:
        from torematrix.processing.workers.pool import WorkerPool
        import inspect
        
        # Test wait_for_completion method
        assert hasattr(WorkerPool, 'wait_for_completion'), "Missing wait_for_completion method"
        wait_sig = inspect.signature(WorkerPool.wait_for_completion)
        assert 'timeout' in wait_sig.parameters, "wait_for_completion should accept timeout parameter"
        logger.info("✓ wait_for_completion method signature correct")
        
        # Test get_stats method
        assert hasattr(WorkerPool, 'get_stats'), "Missing get_stats method"
        stats_sig = inspect.signature(WorkerPool.get_stats)
        required_params = [p for p in stats_sig.parameters.values() 
                          if p.default == inspect.Parameter.empty and p.name != 'self']
        assert len(required_params) == 0, "get_stats should not require parameters"
        logger.info("✓ get_stats method signature correct")
        
        # Test get_pool_stats method
        assert hasattr(WorkerPool, 'get_pool_stats'), "Missing get_pool_stats method"
        pool_sig = inspect.signature(WorkerPool.get_pool_stats)
        required_params = [p for p in pool_sig.parameters.values() 
                          if p.default == inspect.Parameter.empty and p.name != 'self']
        assert len(required_params) == 0, "get_pool_stats should not require parameters"
        logger.info("✓ get_pool_stats method signature correct")
        
        # Test start and stop methods
        assert hasattr(WorkerPool, 'start'), "Missing start method"
        assert hasattr(WorkerPool, 'stop'), "Missing stop method"
        
        stop_sig = inspect.signature(WorkerPool.stop)
        assert 'timeout' in stop_sig.parameters, "stop should accept timeout parameter"
        logger.info("✓ start and stop method signatures correct")
        
        logger.info("✓ All method signatures are correct!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Method signature test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_processor_context_standalone():
    """Test ProcessorContext without importing dependencies."""
    logger.info("=== Testing ProcessorContext Standalone ===")
    
    try:
        # Import just the base module
        sys.path.insert(0, str(Path(__file__).parent / "src" / "torematrix" / "processing" / "processors"))
        from base import ProcessorContext
        
        # Test context creation
        context = ProcessorContext(
            document_id="test_doc_123",
            file_path="/path/to/test.pdf",
            mime_type="application/pdf",
            metadata={"author": "Test", "pages": 5},
            previous_results={"validation": {"valid": True}}
        )
        
        # Test attributes
        assert context.document_id == "test_doc_123"
        assert context.file_path == "/path/to/test.pdf"
        assert context.mime_type == "application/pdf"
        assert isinstance(context.metadata, dict)
        assert isinstance(context.previous_results, dict)
        
        # Test get_previous_result method
        validation_result = context.get_previous_result("validation")
        assert validation_result == {"valid": True}
        
        missing_result = context.get_previous_result("nonexistent")
        assert missing_result is None
        
        logger.info("✓ ProcessorContext works correctly!")
        return True
        
    except Exception as e:
        logger.error(f"✗ ProcessorContext test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_expectations():
    """Test what integration.py expects from WorkerPool."""
    logger.info("=== Testing Integration Expectations ===")
    
    try:
        from torematrix.processing.workers.pool import WorkerPool, WorkerConfig
        from torematrix.processing.workers.resources import ResourceLimits
        
        # Create a minimal config
        config = WorkerConfig(
            async_workers=1,
            thread_workers=0,
            max_queue_size=10
        )
        
        # Create pool without event bus to avoid dependency issues
        pool = WorkerPool(config=config, event_bus=None, resource_monitor=None)
        
        # Test that methods exist and return expected types
        
        # Test get_stats (used in integration.py line 251 and 276)
        stats = pool.get_stats()
        assert isinstance(stats, dict), "get_stats should return dict"
        expected_keys = ['total_workers', 'active_workers', 'idle_workers', 'queued_tasks', 
                        'completed_tasks', 'failed_tasks', 'average_wait_time', 
                        'average_processing_time', 'resource_utilization']
        for key in expected_keys:
            assert key in stats, f"get_stats should include {key}"
        logger.info(f"✓ get_stats returns correct format: {list(stats.keys())}")
        
        # Test get_pool_stats (Agent 3's preferred method)
        pool_stats = pool.get_pool_stats()
        assert hasattr(pool_stats, 'total_workers'), "get_pool_stats should return object with total_workers"
        assert hasattr(pool_stats, 'active_workers'), "get_pool_stats should return object with active_workers"
        logger.info("✓ get_pool_stats returns correct format")
        
        # Test that pool has the _running attribute (used in integration.py)
        assert hasattr(pool, '_running'), "Worker pool should have _running attribute"
        assert pool._running is False, "Pool should start with _running=False"
        logger.info("✓ _running attribute exists and is correct")
        
        logger.info("✓ All integration expectations met!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration expectations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_wait_for_completion_method():
    """Test wait_for_completion method specifically."""
    logger.info("=== Testing wait_for_completion Method ===")
    
    try:
        from torematrix.processing.workers.pool import WorkerPool, WorkerConfig
        
        config = WorkerConfig(async_workers=1, thread_workers=0, max_queue_size=10)
        pool = WorkerPool(config=config, event_bus=None, resource_monitor=None)
        
        # Test wait_for_completion without starting pool (should complete immediately)
        result = await pool.wait_for_completion(timeout=0.1)
        assert isinstance(result, bool), "wait_for_completion should return bool"
        assert result is True, "Should return True when no active tasks"
        logger.info("✓ wait_for_completion works correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ wait_for_completion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_method_tests():
    """Run all method-focused tests."""
    logger.info("Starting Worker Pool Method Tests")
    
    tests = [
        test_method_signatures,
        test_processor_context_standalone,
        test_integration_expectations,
        test_wait_for_completion_method,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                success = await test()
            else:
                success = test()
            
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
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_method_tests())
    if success:
        logger.info("🎉 All Worker Pool methods are compatible with Pipeline Manager!")
    else:
        logger.error("❌ Some compatibility issues found.")
    sys.exit(0 if success else 1)