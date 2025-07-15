"""Tests for Progress Tracking System

Test suite for progress tracking functionality including:
- Operation lifecycle management
- Real-time progress updates
- Progress callbacks and notifications
- Thread-safe operations
- Background update threads
"""

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from torematrix.core.operations.type_management.progress import (
    ProgressTracker, OperationProgress, ProgressPhase, ProgressCallback,
    start_operation_progress, update_operation_progress, complete_operation_progress,
    get_progress_tracker
)


class TestOperationProgress:
    """Test suite for OperationProgress class"""
    
    def test_progress_initialization(self):
        """Test progress initialization"""
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=100
        )
        
        assert progress.operation_id == 'test_op'
        assert progress.operation_type == 'bulk_change'
        assert progress.total_items == 100
        assert progress.current_item == 0
        assert progress.phase == ProgressPhase.INITIALIZING
        assert not progress.is_complete
    
    def test_percentage_calculation(self):
        """Test percentage calculation"""
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=100
        )
        
        # Test 0%
        assert progress.percentage == 0.0
        
        # Test 50%
        progress.current_item = 50
        assert progress.percentage == 50.0
        
        # Test 100%
        progress.current_item = 100
        assert progress.percentage == 100.0
        
        # Test overflow protection
        progress.current_item = 150
        assert progress.percentage == 100.0
    
    def test_percentage_with_zero_total(self):
        """Test percentage when total items is 0"""
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=0
        )
        
        assert progress.percentage == 0.0
    
    def test_elapsed_time(self):
        """Test elapsed time calculation"""
        start_time = datetime.now()
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=100
        )
        progress.start_time = start_time
        
        # Sleep briefly to ensure elapsed time
        time.sleep(0.01)
        
        elapsed = progress.elapsed_time
        assert isinstance(elapsed, timedelta)
        assert elapsed.total_seconds() > 0
    
    def test_estimated_time_calculations(self):
        """Test time estimation calculations"""
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=100
        )
        
        # Set start time to 1 second ago
        progress.start_time = datetime.now() - timedelta(seconds=1)
        progress.current_item = 25  # 25% complete
        
        estimated_total = progress.estimated_total_time
        assert isinstance(estimated_total, timedelta)
        assert estimated_total.total_seconds() > 0
        
        estimated_remaining = progress.estimated_remaining_time
        assert isinstance(estimated_remaining, timedelta)
    
    def test_is_complete_property(self):
        """Test is_complete property"""
        progress = OperationProgress(
            operation_id='test_op',
            operation_type='bulk_change'
        )
        
        # Test initial state
        assert not progress.is_complete
        
        # Test completed state
        progress.phase = ProgressPhase.COMPLETED
        assert progress.is_complete
        
        # Test failed state
        progress.phase = ProgressPhase.FAILED
        assert progress.is_complete
        
        # Test cancelled state
        progress.phase = ProgressPhase.CANCELLED
        assert progress.is_complete
        
        # Test processing state
        progress.phase = ProgressPhase.PROCESSING
        assert not progress.is_complete


class TestProgressTracker:
    """Test suite for ProgressTracker class"""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create fresh progress tracker for each test"""
        return ProgressTracker()
    
    def test_tracker_initialization(self, progress_tracker):
        """Test tracker initialization"""
        assert len(progress_tracker.operations) == 0
        assert len(progress_tracker.subscribers) == 0
        assert not progress_tracker._running
    
    def test_start_operation(self, progress_tracker):
        """Test starting operation tracking"""
        progress = progress_tracker.start_operation(
            operation_id='test_op',
            operation_type='bulk_change',
            total_items=100
        )
        
        assert isinstance(progress, OperationProgress)
        assert progress.operation_id == 'test_op'
        assert progress.operation_type == 'bulk_change'
        assert progress.total_items == 100
        
        # Check it's stored in tracker
        assert 'test_op' in progress_tracker.operations
        assert 'test_op' in progress_tracker.subscribers
    
    def test_start_duplicate_operation(self, progress_tracker):
        """Test starting operation with duplicate ID"""
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        with pytest.raises(ValueError, match="Operation with ID 'test_op' already exists"):
            progress_tracker.start_operation('test_op', 'another_type', 50)
    
    def test_update_operation_progress(self, progress_tracker):
        """Test updating operation progress"""
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        success = progress_tracker.update_operation_progress(
            operation_id='test_op',
            current_item=50,
            phase=ProgressPhase.PROCESSING,
            message='Half complete',
            details={'batch': 1}
        )
        
        assert success
        
        progress = progress_tracker.get_operation_progress('test_op')
        assert progress.current_item == 50
        assert progress.phase == ProgressPhase.PROCESSING
        assert progress.message == 'Half complete'
        assert progress.details['batch'] == 1
    
    def test_update_nonexistent_operation(self, progress_tracker):
        """Test updating non-existent operation"""
        success = progress_tracker.update_operation_progress(
            operation_id='nonexistent',
            current_item=50
        )
        
        assert not success
    
    def test_complete_operation(self, progress_tracker):
        """Test completing operation"""
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        success = progress_tracker.complete_operation(
            operation_id='test_op',
            final_phase=ProgressPhase.COMPLETED,
            message='Operation completed successfully'
        )
        
        assert success
        
        progress = progress_tracker.get_operation_progress('test_op')
        assert progress.phase == ProgressPhase.COMPLETED
        assert progress.message == 'Operation completed successfully'
        assert progress.end_time is not None
        assert progress.is_complete
    
    def test_complete_nonexistent_operation(self, progress_tracker):
        """Test completing non-existent operation"""
        success = progress_tracker.complete_operation(
            operation_id='nonexistent',
            final_phase=ProgressPhase.COMPLETED
        )
        
        assert not success
    
    def test_get_operation_progress(self, progress_tracker):
        """Test getting operation progress"""
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        progress = progress_tracker.get_operation_progress('test_op')
        assert progress is not None
        assert progress.operation_id == 'test_op'
        
        # Test non-existent operation
        progress = progress_tracker.get_operation_progress('nonexistent')
        assert progress is None
    
    def test_list_active_operations(self, progress_tracker):
        """Test listing active operations"""
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.start_operation('op2', 'conversion', 50)
        progress_tracker.start_operation('op3', 'validation', 25)
        
        active_ops = progress_tracker.list_active_operations()
        assert len(active_ops) == 3
        assert 'op1' in active_ops
        assert 'op2' in active_ops
        assert 'op3' in active_ops
        
        # Complete one operation
        progress_tracker.complete_operation('op2', ProgressPhase.COMPLETED)
        
        active_ops = progress_tracker.list_active_operations()
        assert len(active_ops) == 2
        assert 'op1' in active_ops
        assert 'op3' in active_ops
        assert 'op2' not in active_ops
    
    def test_subscribe_to_operation(self, progress_tracker):
        """Test subscribing to operation updates"""
        callback_calls = []
        
        def test_callback(progress: OperationProgress):
            callback_calls.append(progress.current_item)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', test_callback)
        
        # Update progress
        progress_tracker.update_operation_progress('test_op', current_item=25)
        progress_tracker.update_operation_progress('test_op', current_item=50)
        
        assert len(callback_calls) >= 2
        assert 25 in callback_calls
        assert 50 in callback_calls
    
    def test_unsubscribe_from_operation(self, progress_tracker):
        """Test unsubscribing from operation updates"""
        callback_calls = []
        
        def test_callback(progress: OperationProgress):
            callback_calls.append(progress.current_item)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', test_callback)
        
        # Update progress
        progress_tracker.update_operation_progress('test_op', current_item=25)
        
        # Unsubscribe
        progress_tracker.unsubscribe_from_operation('test_op', test_callback)
        
        # Update again
        progress_tracker.update_operation_progress('test_op', current_item=50)
        
        # Should only have one callback call
        assert len(callback_calls) == 1
        assert callback_calls[0] == 25
    
    def test_background_updates(self, progress_tracker):
        """Test background update thread"""
        callback_calls = []
        
        def test_callback(progress: OperationProgress):
            callback_calls.append(progress.current_item)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', test_callback)
        
        # Start background updates
        progress_tracker.start_background_updates(update_interval=0.05)
        
        # Update progress
        progress_tracker.update_operation_progress('test_op', current_item=25)
        
        # Wait for background updates
        time.sleep(0.2)
        
        # Stop background updates
        progress_tracker.stop_background_updates()
        
        # Should have received multiple callback calls due to background updates
        assert len(callback_calls) > 1
    
    def test_cleanup_completed_operations(self, progress_tracker):
        """Test cleanup of old completed operations"""
        # Start and complete operations
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.start_operation('op2', 'conversion', 50)
        
        progress_tracker.complete_operation('op1', ProgressPhase.COMPLETED)
        progress_tracker.complete_operation('op2', ProgressPhase.FAILED)
        
        # Manually set end times to simulate old operations
        progress1 = progress_tracker.get_operation_progress('op1')
        progress2 = progress_tracker.get_operation_progress('op2')
        progress1.end_time = datetime.now() - timedelta(hours=2)
        progress2.end_time = datetime.now() - timedelta(minutes=30)
        
        # Cleanup operations older than 1 hour
        progress_tracker.cleanup_completed_operations(keep_hours=1)
        
        # op1 should be cleaned up, op2 should remain
        assert progress_tracker.get_operation_progress('op1') is None
        assert progress_tracker.get_operation_progress('op2') is not None
    
    def test_get_operation_statistics(self, progress_tracker):
        """Test getting operation statistics"""
        # Start various operations
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.start_operation('op2', 'conversion', 50)
        progress_tracker.start_operation('op3', 'bulk_change', 75)
        
        # Complete some operations
        progress_tracker.complete_operation('op1', ProgressPhase.COMPLETED)
        progress_tracker.complete_operation('op2', ProgressPhase.FAILED)
        
        stats = progress_tracker.get_operation_statistics()
        
        assert stats['total_operations'] == 3
        assert stats['active_operations'] == 1
        assert stats['completed_operations'] == 1
        assert stats['failed_operations'] == 1
        assert stats['operation_types']['bulk_change'] == 2
        assert stats['operation_types']['conversion'] == 1


class TestThreadSafety:
    """Test thread safety of progress tracker"""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker for thread safety testing"""
        return ProgressTracker()
    
    def test_concurrent_operations(self, progress_tracker):
        """Test concurrent operation management"""
        def create_and_update_operation(op_id):
            progress_tracker.start_operation(f'op_{op_id}', 'bulk_change', 100)
            
            for i in range(10):
                progress_tracker.update_operation_progress(
                    f'op_{op_id}',
                    current_item=i * 10
                )
                time.sleep(0.01)
            
            progress_tracker.complete_operation(
                f'op_{op_id}',
                ProgressPhase.COMPLETED
            )
        
        threads = []
        
        # Start multiple concurrent operations
        for i in range(5):
            thread = threading.Thread(target=create_and_update_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations completed
        stats = progress_tracker.get_operation_statistics()
        assert stats['total_operations'] == 5
        assert stats['completed_operations'] == 5
    
    def test_concurrent_subscribers(self, progress_tracker):
        """Test concurrent subscriber management"""
        callback_counts = {}
        
        def create_callback(callback_id):
            def callback(progress):
                if callback_id not in callback_counts:
                    callback_counts[callback_id] = 0
                callback_counts[callback_id] += 1
            return callback
        
        def subscribe_and_unsubscribe(callback_id):
            callback = create_callback(callback_id)
            progress_tracker.subscribe_to_operation('test_op', callback)
            time.sleep(0.05)
            progress_tracker.unsubscribe_from_operation('test_op', callback)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        threads = []
        
        # Start multiple subscriber threads
        for i in range(5):
            thread = threading.Thread(target=subscribe_and_unsubscribe, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Update progress while subscribers are being managed
        for i in range(10):
            progress_tracker.update_operation_progress('test_op', current_item=i * 10)
            time.sleep(0.01)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should complete without errors
        assert len(callback_counts) <= 5


class TestModuleLevelFunctions:
    """Test module-level convenience functions"""
    
    def test_start_operation_progress(self):
        """Test module-level start operation function"""
        progress = start_operation_progress(
            operation_id='module_test_1',
            operation_type='test_operation',
            total_items=50
        )
        
        assert isinstance(progress, OperationProgress)
        assert progress.operation_id == 'module_test_1'
        assert progress.total_items == 50
    
    def test_update_operation_progress_function(self):
        """Test module-level update progress function"""
        start_operation_progress('module_test_2', 'test_operation', 50)
        
        success = update_operation_progress(
            operation_id='module_test_2',
            current_item=25,
            message='Half complete'
        )
        
        assert success
    
    def test_complete_operation_progress_function(self):
        """Test module-level complete operation function"""
        start_operation_progress('module_test_3', 'test_operation', 50)
        
        success = complete_operation_progress(
            operation_id='module_test_3',
            final_phase=ProgressPhase.COMPLETED,
            message='Test completed'
        )
        
        assert success
    
    def test_get_progress_tracker_singleton(self):
        """Test global progress tracker singleton"""
        tracker1 = get_progress_tracker()
        tracker2 = get_progress_tracker()
        
        # Should be the same instance
        assert tracker1 is tracker2


class TestProgressCallbacks:
    """Test progress callback functionality"""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker for callback testing"""
        return ProgressTracker()
    
    def test_callback_error_handling(self, progress_tracker):
        """Test callback error handling"""
        def failing_callback(progress):
            raise Exception("Callback error")
        
        def working_callback(progress):
            working_callback.called = True
        working_callback.called = False
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', failing_callback)
        progress_tracker.subscribe_to_operation('test_op', working_callback)
        
        # Update progress - should not fail despite callback error
        progress_tracker.update_operation_progress('test_op', current_item=50)
        
        # Working callback should still be called
        assert working_callback.called
    
    def test_multiple_callbacks(self, progress_tracker):
        """Test multiple callbacks for single operation"""
        callback1_calls = []
        callback2_calls = []
        
        def callback1(progress):
            callback1_calls.append(progress.current_item)
        
        def callback2(progress):
            callback2_calls.append(progress.current_item)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', callback1)
        progress_tracker.subscribe_to_operation('test_op', callback2)
        
        progress_tracker.update_operation_progress('test_op', current_item=50)
        
        # Both callbacks should be called
        assert len(callback1_calls) > 0
        assert len(callback2_calls) > 0
        assert callback1_calls[-1] == 50
        assert callback2_calls[-1] == 50


if __name__ == '__main__':
    pytest.main([__file__, '-v'])