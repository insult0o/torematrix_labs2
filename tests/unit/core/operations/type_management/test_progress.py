"""Tests for Progress Tracking System

Comprehensive test suite for progress tracking including:
- Real-time progress updates and callbacks
- Operation lifecycle management
- Progress phases and state transitions
- Thread-safe progress tracking
- Performance monitoring
"""

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from torematrix.core.operations.type_management.progress import (
    ProgressTracker, OperationProgress, ProgressPhase, ProgressCallback,
    start_operation_progress, update_operation_progress, complete_operation_progress,
    subscribe_to_operation_progress, get_progress_tracker
)


class TestProgressPhase:
    """Test ProgressPhase enum"""
    
    def test_progress_phases(self):
        """Test all progress phase values"""
        assert ProgressPhase.INITIALIZING.value == "initializing"
        assert ProgressPhase.ANALYZING.value == "analyzing"
        assert ProgressPhase.PROCESSING.value == "processing"
        assert ProgressPhase.VALIDATING.value == "validating"
        assert ProgressPhase.FINALIZING.value == "finalizing"
        assert ProgressPhase.COMPLETED.value == "completed"
        assert ProgressPhase.FAILED.value == "failed"
        assert ProgressPhase.CANCELLED.value == "cancelled"


class TestOperationProgress:
    """Test OperationProgress data class"""
    
    def test_progress_creation(self):
        """Test creating operation progress"""
        start_time = datetime.now()
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="bulk_change",
            phase=ProgressPhase.PROCESSING,
            current_item=50,
            total_items=100,
            start_time=start_time,
            message="Processing elements...",
            details={"batch": 2, "worker": 1}
        )
        
        assert progress.operation_id == "op_001"
        assert progress.operation_type == "bulk_change"
        assert progress.phase == ProgressPhase.PROCESSING
        assert progress.current_item == 50
        assert progress.total_items == 100
        assert progress.start_time == start_time
        assert progress.message == "Processing elements..."
        assert progress.details == {"batch": 2, "worker": 1}
    
    def test_progress_defaults(self):
        """Test default values for progress"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test"
        )
        
        assert progress.phase == ProgressPhase.INITIALIZING
        assert progress.current_item == 0
        assert progress.total_items == 0
        assert progress.message == ""
        assert progress.details == {}
        assert progress.start_time is not None
        assert progress.last_update is not None
        assert progress.end_time is None
    
    def test_percentage_calculation(self):
        """Test percentage calculation"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            current_item=25,
            total_items=100
        )
        
        assert progress.percentage == 25.0
    
    def test_percentage_zero_total(self):
        """Test percentage with zero total items"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            current_item=5,
            total_items=0
        )
        
        assert progress.percentage == 0.0
    
    def test_percentage_complete(self):
        """Test percentage when complete"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            current_item=100,
            total_items=100
        )
        
        assert progress.percentage == 100.0
    
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation"""
        start_time = datetime.now() - timedelta(seconds=10)
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            start_time=start_time
        )
        
        elapsed = progress.elapsed_time
        assert elapsed.total_seconds() >= 10
        assert elapsed.total_seconds() < 11  # Should be close to 10 seconds
    
    def test_estimated_total_time(self):
        """Test estimated total time calculation"""
        start_time = datetime.now() - timedelta(seconds=10)
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            current_item=25,
            total_items=100,
            start_time=start_time
        )
        
        estimated = progress.estimated_total_time
        # Should estimate around 40 seconds total (10 seconds for 25% = 40 seconds for 100%)
        assert estimated.total_seconds() >= 35
        assert estimated.total_seconds() <= 45
    
    def test_estimated_remaining_time(self):
        """Test estimated remaining time calculation"""
        start_time = datetime.now() - timedelta(seconds=10)
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            current_item=25,
            total_items=100,
            start_time=start_time
        )
        
        remaining = progress.estimated_remaining_time
        # Should estimate around 30 seconds remaining
        assert remaining.total_seconds() >= 25
        assert remaining.total_seconds() <= 35
    
    def test_is_complete_true(self):
        """Test is_complete when operation is done"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            phase=ProgressPhase.COMPLETED
        )
        
        assert progress.is_complete is True
    
    def test_is_complete_false(self):
        """Test is_complete when operation is running"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            phase=ProgressPhase.PROCESSING
        )
        
        assert progress.is_complete is False
    
    def test_is_complete_failed(self):
        """Test is_complete when operation failed"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            phase=ProgressPhase.FAILED
        )
        
        assert progress.is_complete is True
    
    def test_is_complete_cancelled(self):
        """Test is_complete when operation cancelled"""
        progress = OperationProgress(
            operation_id="op_001",
            operation_type="test",
            phase=ProgressPhase.CANCELLED
        )
        
        assert progress.is_complete is True


class TestProgressTracker:
    """Test ProgressTracker functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Create tracker instance for testing"""
        return ProgressTracker()
    
    def test_tracker_initialization(self):
        """Test tracker initialization"""
        tracker = ProgressTracker()
        
        assert tracker.operations == {}
        assert tracker.subscribers == {}
        assert tracker._lock is not None
        assert tracker._update_thread is None
        assert tracker._running is False
    
    def test_start_operation(self, tracker):
        """Test starting new operation"""
        progress = tracker.start_operation("op_001", "bulk_change", total_items=100)
        
        assert progress.operation_id == "op_001"
        assert progress.operation_type == "bulk_change"
        assert progress.total_items == 100
        assert progress.phase == ProgressPhase.INITIALIZING
        assert "op_001" in tracker.operations
    
    def test_start_operation_duplicate(self, tracker):
        """Test starting operation with duplicate ID"""
        tracker.start_operation("op_001", "bulk_change")
        
        with pytest.raises(ValueError, match="Operation with ID 'op_001' already exists"):
            tracker.start_operation("op_001", "another_type")
    
    def test_update_operation_progress_exists(self, tracker):
        """Test updating existing operation progress"""
        tracker.start_operation("op_001", "bulk_change", total_items=100)
        
        success = tracker.update_operation_progress(
            "op_001",
            current_item=50,
            phase=ProgressPhase.PROCESSING,
            message="Processing items..."
        )
        
        assert success is True
        progress = tracker.get_operation_progress("op_001")
        assert progress.current_item == 50
        assert progress.phase == ProgressPhase.PROCESSING
        assert progress.message == "Processing items..."
    
    def test_update_operation_progress_not_exists(self, tracker):
        """Test updating non-existent operation"""
        success = tracker.update_operation_progress("non_existent", current_item=50)
        assert success is False
    
    def test_complete_operation_success(self, tracker):
        """Test completing operation successfully"""
        tracker.start_operation("op_001", "bulk_change", total_items=100)
        
        success = tracker.complete_operation("op_001", ProgressPhase.COMPLETED, "All done!")
        
        assert success is True
        progress = tracker.get_operation_progress("op_001")
        assert progress.phase == ProgressPhase.COMPLETED
        assert progress.message == "All done!"
        assert progress.end_time is not None
        assert progress.is_complete is True
    
    def test_complete_operation_not_exists(self, tracker):
        """Test completing non-existent operation"""
        success = tracker.complete_operation("non_existent", ProgressPhase.COMPLETED)
        assert success is False
    
    def test_get_operation_progress_exists(self, tracker):
        """Test getting existing operation progress"""
        original = tracker.start_operation("op_001", "bulk_change")
        retrieved = tracker.get_operation_progress("op_001")
        
        assert retrieved.operation_id == original.operation_id
        assert retrieved.operation_type == original.operation_type
    
    def test_get_operation_progress_not_exists(self, tracker):
        """Test getting non-existent operation progress"""
        progress = tracker.get_operation_progress("non_existent")
        assert progress is None
    
    def test_list_active_operations(self, tracker):
        """Test listing active operations"""
        tracker.start_operation("op_001", "bulk_change")
        tracker.start_operation("op_002", "conversion")
        tracker.start_operation("op_003", "migration")
        
        # Complete one operation
        tracker.complete_operation("op_002", ProgressPhase.COMPLETED)
        
        active_ops = tracker.list_active_operations()
        
        assert "op_001" in active_ops
        assert "op_002" not in active_ops  # Completed
        assert "op_003" in active_ops
        assert len(active_ops) == 2
    
    def test_subscribe_to_operation(self, tracker):
        """Test subscribing to operation updates"""
        updates = []
        
        def callback(progress: OperationProgress):
            updates.append(progress)
        
        tracker.subscribe_to_operation("op_001", callback)
        
        assert "op_001" in tracker.subscribers
        assert callback in tracker.subscribers["op_001"]
    
    def test_unsubscribe_from_operation(self, tracker):
        """Test unsubscribing from operation updates"""
        def callback(progress: OperationProgress):
            pass
        
        tracker.subscribe_to_operation("op_001", callback)
        assert callback in tracker.subscribers["op_001"]
        
        tracker.unsubscribe_from_operation("op_001", callback)
        assert callback not in tracker.subscribers["op_001"]
    
    def test_callback_notification(self, tracker):
        """Test that callbacks are notified of updates"""
        updates = []
        
        def callback(progress: OperationProgress):
            updates.append(progress.current_item)
        
        tracker.subscribe_to_operation("op_001", callback)
        tracker.start_operation("op_001", "bulk_change", total_items=100)
        
        # Give background thread time to notify
        time.sleep(0.1)
        
        tracker.update_operation_progress("op_001", current_item=50)
        
        # Give background thread time to notify
        time.sleep(0.1)
        
        assert len(updates) >= 1  # Should have at least the start notification
    
    def test_start_background_updates(self, tracker):
        """Test starting background update thread"""
        tracker.start_background_updates()
        
        assert tracker._running is True
        assert tracker._update_thread is not None
        assert tracker._update_thread.is_alive()
        
        # Clean up
        tracker.stop_background_updates()
    
    def test_stop_background_updates(self, tracker):
        """Test stopping background update thread"""
        tracker.start_background_updates()
        time.sleep(0.1)  # Let thread start
        
        tracker.stop_background_updates()
        
        assert tracker._running is False
        # Thread should stop within reasonable time
        tracker._update_thread.join(timeout=1)
        assert not tracker._update_thread.is_alive()
    
    def test_cleanup_completed_operations(self, tracker):
        """Test cleanup of completed operations"""
        # Start multiple operations
        tracker.start_operation("op_001", "bulk_change")
        tracker.start_operation("op_002", "conversion")
        tracker.start_operation("op_003", "migration")
        
        # Complete some operations
        tracker.complete_operation("op_001", ProgressPhase.COMPLETED)
        tracker.complete_operation("op_002", ProgressPhase.FAILED)
        
        assert len(tracker.operations) == 3
        
        # Cleanup completed operations
        tracker.cleanup_completed_operations()
        
        # Should only have active operation left
        assert len(tracker.operations) == 1
        assert "op_003" in tracker.operations
    
    def test_get_operation_statistics(self, tracker):
        """Test getting operation statistics"""
        # Start various operations
        tracker.start_operation("op_001", "bulk_change")
        tracker.start_operation("op_002", "conversion")
        tracker.start_operation("op_003", "migration")
        
        # Complete some
        tracker.complete_operation("op_001", ProgressPhase.COMPLETED)
        tracker.complete_operation("op_002", ProgressPhase.FAILED)
        
        stats = tracker.get_operation_statistics()
        
        assert stats["total_operations"] == 3
        assert stats["active_operations"] == 1
        assert stats["completed_operations"] == 1
        assert stats["failed_operations"] == 1
        assert "operation_types" in stats
        assert stats["operation_types"]["bulk_change"] == 1
        assert stats["operation_types"]["conversion"] == 1
        assert stats["operation_types"]["migration"] == 1
    
    def test_thread_safety(self, tracker):
        """Test thread safety of progress tracking"""
        tracker.start_background_updates()
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Start operation
                tracker.start_operation(f"op_{worker_id}", "test_operation", total_items=100)
                
                # Update progress multiple times
                for i in range(0, 101, 10):
                    tracker.update_operation_progress(f"op_{worker_id}", current_item=i)
                    time.sleep(0.01)  # Small delay
                
                # Complete operation
                tracker.complete_operation(f"op_{worker_id}", ProgressPhase.COMPLETED)
                results.append(f"op_{worker_id}")
                
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Clean up
        tracker.stop_background_updates()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Check that all operations were tracked
        assert len(tracker.operations) == 5
        
        # All operations should be completed
        for op_id in [f"op_{i}" for i in range(5)]:
            progress = tracker.get_operation_progress(op_id)
            assert progress.phase == ProgressPhase.COMPLETED


class TestProgressModuleFunctions:
    """Test module-level progress functions"""
    
    def test_start_operation_progress(self):
        """Test start_operation_progress function"""
        progress = start_operation_progress("op_001", "test_operation", total_items=50)
        
        assert progress.operation_id == "op_001"
        assert progress.operation_type == "test_operation"
        assert progress.total_items == 50
    
    def test_update_operation_progress(self):
        """Test update_operation_progress function"""
        start_operation_progress("op_001", "test_operation", total_items=100)
        
        success = update_operation_progress("op_001", current_item=75, message="Almost done")
        
        assert success is True
        
        # Get progress to verify update
        tracker = get_progress_tracker()
        progress = tracker.get_operation_progress("op_001")
        assert progress.current_item == 75
        assert progress.message == "Almost done"
    
    def test_complete_operation_progress(self):
        """Test complete_operation_progress function"""
        start_operation_progress("op_001", "test_operation")
        
        success = complete_operation_progress("op_001", ProgressPhase.COMPLETED, "All done!")
        
        assert success is True
        
        # Verify completion
        tracker = get_progress_tracker()
        progress = tracker.get_operation_progress("op_001")
        assert progress.phase == ProgressPhase.COMPLETED
        assert progress.message == "All done!"
        assert progress.is_complete is True
    
    def test_subscribe_to_operation_progress(self):
        """Test subscribe_to_operation_progress function"""
        updates = []
        
        def callback(progress):
            updates.append(progress.current_item)
        
        subscribe_to_operation_progress("op_001", callback)
        
        # Verify subscription
        tracker = get_progress_tracker()
        assert "op_001" in tracker.subscribers
        assert callback in tracker.subscribers["op_001"]
    
    def test_get_progress_tracker_singleton(self):
        """Test that get_progress_tracker returns singleton"""
        tracker1 = get_progress_tracker()
        tracker2 = get_progress_tracker()
        
        assert tracker1 is tracker2


class TestProgressIntegration:
    """Integration tests for progress tracking system"""
    
    def test_end_to_end_progress_workflow(self):
        """Test complete progress tracking workflow"""
        tracker = ProgressTracker()
        tracker.start_background_updates()
        
        # Track callback updates
        updates = []
        
        def callback(progress):
            updates.append({
                'phase': progress.phase,
                'current': progress.current_item,
                'percentage': progress.percentage,
                'message': progress.message
            })
        
        try:
            # Subscribe to updates
            tracker.subscribe_to_operation("bulk_op", callback)
            
            # Start operation
            progress = tracker.start_operation("bulk_op", "bulk_change", total_items=1000)
            assert progress.phase == ProgressPhase.INITIALIZING
            
            # Simulate operation phases
            tracker.update_operation_progress(
                "bulk_op",
                phase=ProgressPhase.ANALYZING,
                message="Analyzing elements..."
            )
            
            tracker.update_operation_progress(
                "bulk_op",
                current_item=250,
                phase=ProgressPhase.PROCESSING,
                message="Processing batch 1..."
            )
            
            tracker.update_operation_progress(
                "bulk_op",
                current_item=500,
                message="Processing batch 2..."
            )
            
            tracker.update_operation_progress(
                "bulk_op",
                current_item=750,
                message="Processing batch 3..."
            )
            
            tracker.update_operation_progress(
                "bulk_op",
                current_item=1000,
                phase=ProgressPhase.VALIDATING,
                message="Validating results..."
            )
            
            # Complete operation
            tracker.complete_operation(
                "bulk_op",
                ProgressPhase.COMPLETED,
                "Operation completed successfully!"
            )
            
            # Give time for background updates
            time.sleep(0.2)
            
            # Verify final state
            final_progress = tracker.get_operation_progress("bulk_op")
            assert final_progress.phase == ProgressPhase.COMPLETED
            assert final_progress.current_item == 1000
            assert final_progress.percentage == 100.0
            assert final_progress.is_complete is True
            assert final_progress.end_time is not None
            
            # Verify we received updates
            assert len(updates) > 0
            
            # Check statistics
            stats = tracker.get_operation_statistics()
            assert stats["total_operations"] == 1
            assert stats["completed_operations"] == 1
            assert stats["operation_types"]["bulk_change"] == 1
            
        finally:
            tracker.stop_background_updates()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])