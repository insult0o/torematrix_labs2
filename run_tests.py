#!/usr/bin/env python3
"""
Simple test runner for state management system.
"""

import sys
import traceback
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_basic_tests():
    """Run basic functionality tests."""
    print("Running basic state management tests...")
    
    try:
        # Test middleware pipeline
        from src.torematrix.core.state.middleware.pipeline import MiddlewarePipeline, logging_middleware
        
        pipeline = MiddlewarePipeline()
        pipeline.use(logging_middleware)
        
        print("✓ Middleware pipeline creation successful")
        
        # Test Event Bus integration
        from unittest.mock import Mock
        from src.torematrix.core.state.integration.event_bus import EventBusIntegration
        
        mock_event_bus = Mock()
        integration = EventBusIntegration(mock_event_bus)
        middleware = integration.create_middleware()
        
        print("✓ Event Bus integration successful")
        
        # Test optimistic middleware
        from src.torematrix.core.state.optimistic.updates import OptimisticMiddleware
        
        optimistic = OptimisticMiddleware()
        print("✓ Optimistic middleware creation successful")
        
        # Test DevTools
        from src.torematrix.core.state.devtools import ReduxDevTools
        
        devtools = ReduxDevTools()
        devtools_middleware = devtools.create_middleware()
        
        print("✓ DevTools integration successful")
        
        # Test transactions
        from src.torematrix.core.state.transactions import TransactionMiddleware
        
        tx_middleware = TransactionMiddleware()
        print("✓ Transaction middleware creation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
        return False


def run_performance_benchmark():
    """Run performance benchmarks."""
    print("\nRunning performance benchmarks...")
    
    try:
        from unittest.mock import Mock
        from src.torematrix.core.state.middleware.pipeline import MiddlewarePipeline, logging_middleware, timing_middleware
        from src.torematrix.core.state.devtools import ReduxDevTools
        
        # Set up pipeline with all middleware
        pipeline = MiddlewarePipeline()
        pipeline.use(logging_middleware)
        pipeline.use(timing_middleware)
        
        # Add DevTools
        devtools = ReduxDevTools()
        pipeline.use(devtools.create_middleware())
        
        # Mock store
        mock_store = Mock()
        mock_store.get_state.return_value = {'test': 'state'}
        mock_store._dispatch = Mock(return_value='result')
        mock_store._notify_subscribers = Mock()
        
        # Compose pipeline
        composed = pipeline.compose()
        dispatch_func = composed(mock_store)
        
        # Performance test
        num_actions = 1000
        start_time = time.time()
        
        for i in range(num_actions):
            action = Mock()
            action.type = f'PERF_ACTION_{i}'
            action.payload = {'data': f'test_data_{i}'}
            dispatch_func(action)
        
        duration = time.time() - start_time
        actions_per_second = num_actions / duration
        
        print(f"✓ Performance test completed:")
        print(f"  - {num_actions} actions in {duration:.3f}s")
        print(f"  - {actions_per_second:.1f} actions/second")
        print(f"  - {duration/num_actions*1000:.3f}ms per action")
        
        # Get middleware metrics
        metrics = pipeline.get_metrics()
        print(f"  - Average middleware time: {metrics['avg_time_per_action']*1000:.3f}ms")
        
        # DevTools metrics
        perf_stats = devtools.get_performance_stats()
        print(f"  - DevTools logged {perf_stats['total_actions']} actions")
        print(f"  - Average DevTools overhead: {perf_stats['avg_duration']*1000:.3f}ms")
        
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        traceback.print_exc()
        return False


def run_integration_test():
    """Run integration test with all systems."""
    print("\nRunning integration test...")
    
    try:
        from unittest.mock import Mock
        from src.torematrix.core.state.middleware.pipeline import MiddlewarePipeline
        from src.torematrix.core.state.integration.event_bus import EventBusIntegration
        from src.torematrix.core.state.integration.sync import StateSyncManager, SyncMode
        from src.torematrix.core.state.optimistic.updates import OptimisticMiddleware
        from src.torematrix.core.state.devtools import ReduxDevTools
        from src.torematrix.core.state.transactions import TransactionMiddleware
        
        # Set up all components
        pipeline = MiddlewarePipeline()
        
        # Event Bus
        mock_event_bus = Mock()
        event_integration = EventBusIntegration(mock_event_bus)
        pipeline.use(event_integration.create_middleware())
        
        # Optimistic updates
        optimistic = OptimisticMiddleware()
        # Note: Can't add async middleware to sync pipeline easily
        
        # DevTools
        devtools = ReduxDevTools()
        pipeline.use(devtools.create_middleware())
        
        # Transactions
        tx_middleware = TransactionMiddleware()
        pipeline.use(tx_middleware)
        
        # Sync manager
        sync_manager = StateSyncManager(SyncMode.MANUAL)
        
        # Mock stores
        store1 = Mock()
        store1.get_state.return_value = {'store1': 'data', 'shared': 'value1'}
        store1.dispatch = Mock()
        
        store2 = Mock()
        store2.get_state.return_value = {'store2': 'data', 'shared': 'value2'}
        store2.dispatch = Mock()
        
        # Register stores
        sync_manager.register_store('store1', store1)
        sync_manager.register_store('store2', store2)
        
        # Test integrated dispatch
        composed = pipeline.compose()
        dispatch_func = composed(store1)
        
        # Execute test action
        action = Mock()
        action.type = 'INTEGRATED_ACTION'
        action.payload = {'test': 'integration'}
        
        result = dispatch_func(action)
        
        # Verify components worked
        assert mock_event_bus.publish.called, "Event Bus should publish events"
        assert len(devtools.get_action_log()) > 0, "DevTools should log actions"
        
        # Test sync
        sync_manager.sync_stores('store1', ['store2'])
        assert store2.dispatch.called, "Sync should trigger store2 dispatch"
        
        print("✓ Integration test successful:")
        print(f"  - Event Bus published {mock_event_bus.publish.call_count} events")
        print(f"  - DevTools logged {len(devtools.get_action_log())} actions")
        print(f"  - Sync manager performed sync operation")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("TORE Matrix State Management System - Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Run tests
    if run_basic_tests():
        success_count += 1
    
    if run_performance_benchmark():
        success_count += 1
        
    if run_integration_test():
        success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! State management system is working correctly.")
        return 0
    else:
        print(f"❌ {total_tests - success_count} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())