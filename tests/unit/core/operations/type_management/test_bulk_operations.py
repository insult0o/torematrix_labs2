"""Tests for Bulk Operations System

Comprehensive test suite for bulk type operations including:
- Bulk operation engine functionality
- Type conversion testing
- Progress tracking validation
- Rollback system verification
- Performance and thread safety testing
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

from torematrix.core.operations.type_management.bulk_operations import (
    BulkTypeOperationEngine, BulkOperationOptions, BulkOperationResult,
    BulkChangePreview, ElementChange, OperationStatus, ConflictResolution
)
from torematrix.core.operations.type_management.conversions import (
    TypeConversionEngine, ConversionResult, ConversionAnalysis
)
from torematrix.core.operations.type_management.progress import (
    ProgressTracker, OperationProgress, ProgressPhase, ProgressCallback,
    start_operation_progress, update_operation_progress, complete_operation_progress
)
from torematrix.core.operations.type_management.rollback import (
    RollbackManager, RollbackOperation, RollbackState
)
from torematrix.core.type_system.registry import TypeRegistry
from torematrix.core.type_system.validation import TypeValidationEngine, ValidationResult
from torematrix.core.validation.system import ValidationMessage, ValidationSeverity


class TestBulkTypeOperationEngine:
    """Test suite for BulkTypeOperationEngine"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock type registry"""
        registry = Mock(spec=TypeRegistry)
        registry.get_type_definition.return_value = {
            'name': 'test_type',
            'fields': {}
        }
        registry.validate_type.return_value = True
        return registry
    
    @pytest.fixture
    def mock_validator(self):
        """Mock validation engine"""
        validator = Mock(spec=TypeValidationEngine)
        validator.validate_bulk_change.return_value = ValidationResult(
            is_valid=True,
            messages=[
                ValidationMessage(
                    message="Validation passed",
                    severity=ValidationSeverity.INFO
                )
            ]
        )
        return validator
    
    @pytest.fixture
    def bulk_engine(self, mock_registry, mock_validator):
        """Create bulk operation engine instance"""
        return BulkTypeOperationEngine(
            registry=mock_registry,
            validator=mock_validator,
            max_workers=2
        )
    
    def test_engine_initialization(self, bulk_engine):
        """Test proper engine initialization"""
        assert bulk_engine.max_workers == 2
        assert len(bulk_engine._operations) == 0
        assert len(bulk_engine._cancel_events) == 0
    
    def test_preview_bulk_changes(self, bulk_engine):
        """Test bulk change preview generation"""
        element_ids = ['elem1', 'elem2', 'elem3']
        from_type = 'old_type'
        to_type = 'new_type'
        
        preview = bulk_engine.preview_bulk_changes(
            element_ids=element_ids,
            from_type=from_type,
            to_type=to_type
        )
        
        assert isinstance(preview, BulkChangePreview)
        assert preview.from_type == from_type
        assert preview.to_type == to_type
        assert len(preview.element_changes) == 3
        assert preview.total_elements == 3
        
        # Check element changes
        for i, change in enumerate(preview.element_changes):
            assert change.element_id == f'elem{i+1}'
            assert change.from_type == from_type
            assert change.to_type == to_type
    
    def test_execute_bulk_change_sync(self, bulk_engine):
        """Test synchronous bulk change execution"""
        element_ids = ['elem1', 'elem2']
        from_type = 'old_type'
        to_type = 'new_type'
        
        options = BulkOperationOptions(
            preserve_data=True,
            validate_before_change=True
        )
        
        result = bulk_engine.execute_bulk_change(
            element_ids=element_ids,
            from_type=from_type,
            to_type=to_type,
            options=options
        )
        
        assert isinstance(result, BulkOperationResult)
        assert result.operation_id
        assert result.status == OperationStatus.COMPLETED
        assert result.total_elements == 2
        assert result.processed_elements == 2
        assert result.success_count == 2
        assert result.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_execute_bulk_change_async(self, bulk_engine):
        """Test asynchronous bulk change execution"""
        element_ids = ['elem1', 'elem2', 'elem3']
        from_type = 'old_type'
        to_type = 'new_type'
        
        options = BulkOperationOptions(
            preserve_data=True,
            batch_size=2
        )
        
        result = await bulk_engine.execute_bulk_change_async(
            element_ids=element_ids,
            from_type=from_type,
            to_type=to_type,
            options=options
        )
        
        assert isinstance(result, BulkOperationResult)
        assert result.status == OperationStatus.COMPLETED
        assert result.total_elements == 3
        assert result.success_count == 3
    
    def test_cancel_operation(self, bulk_engine):
        """Test operation cancellation"""
        element_ids = ['elem1', 'elem2', 'elem3']
        
        # Start operation in background
        def run_operation():
            options = BulkOperationOptions(batch_size=1)
            bulk_engine.execute_bulk_change(
                element_ids=element_ids,
                from_type='old_type',
                to_type='new_type',
                options=options
            )
        
        thread = threading.Thread(target=run_operation)
        thread.start()
        
        # Give operation time to start
        time.sleep(0.1)
        
        # Cancel the operation
        operations = list(bulk_engine._operations.keys())
        if operations:
            success = bulk_engine.cancel_operation(operations[0])
            assert success
        
        thread.join(timeout=2)
    
    def test_get_operation_status(self, bulk_engine):
        """Test getting operation status"""
        element_ids = ['elem1']
        
        result = bulk_engine.execute_bulk_change(
            element_ids=element_ids,
            from_type='old_type',
            to_type='new_type'
        )
        
        status = bulk_engine.get_operation_status(result.operation_id)
        assert status is not None
        assert status.status == OperationStatus.COMPLETED
    
    def test_conflict_resolution(self, bulk_engine):
        """Test conflict resolution during bulk operations"""
        element_ids = ['elem1', 'elem2']
        
        options = BulkOperationOptions(
            conflict_resolution=ConflictResolution.MERGE_PRESERVE_EXISTING
        )
        
        result = bulk_engine.execute_bulk_change(
            element_ids=element_ids,
            from_type='old_type',
            to_type='new_type',
            options=options
        )
        
        assert result.status == OperationStatus.COMPLETED


class TestTypeConversionEngine:
    """Test suite for TypeConversionEngine"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock type registry"""
        registry = Mock(spec=TypeRegistry)
        registry.get_type_definition.return_value = {
            'name': 'test_type',
            'fields': {'text': {'type': 'string'}}
        }
        return registry
    
    @pytest.fixture
    def conversion_engine(self, mock_registry):
        """Create conversion engine instance"""
        return TypeConversionEngine(registry=mock_registry)
    
    def test_convert_element_type(self, conversion_engine):
        """Test basic element type conversion"""
        element_data = {'text': 'test content', 'metadata': {'source': 'test'}}
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='title',
            element_data=element_data,
            preserve_data=True
        )
        
        assert isinstance(result, ConversionResult)
        assert result.success
        assert result.element_id == 'elem1'
        assert result.from_type == 'text'
        assert result.to_type == 'title'
    
    def test_analyze_conversion_compatibility(self, conversion_engine):
        """Test conversion compatibility analysis"""
        analysis = conversion_engine.analyze_conversion_compatibility(
            from_type='text',
            to_type='title'
        )
        
        assert isinstance(analysis, ConversionAnalysis)
        assert analysis.from_type == 'text'
        assert analysis.to_type == 'title'
        assert isinstance(analysis.compatibility_score, float)
        assert 0 <= analysis.compatibility_score <= 1
    
    def test_batch_convert_elements(self, conversion_engine):
        """Test batch element conversion"""
        conversions = [
            ('elem1', 'text', 'title'),
            ('elem2', 'text', 'paragraph')
        ]
        
        results = conversion_engine.batch_convert_elements(conversions)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ConversionResult)
            assert result.success


class TestProgressTracker:
    """Test suite for ProgressTracker"""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker instance"""
        return ProgressTracker()
    
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
        assert progress.phase == ProgressPhase.INITIALIZING
    
    def test_update_operation_progress(self, progress_tracker):
        """Test updating operation progress"""
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        
        success = progress_tracker.update_operation_progress(
            operation_id='test_op',
            current_item=50,
            phase=ProgressPhase.PROCESSING,
            message='Processing items'
        )
        
        assert success
        
        progress = progress_tracker.get_operation_progress('test_op')
        assert progress.current_item == 50
        assert progress.phase == ProgressPhase.PROCESSING
        assert progress.message == 'Processing items'
        assert progress.percentage == 50.0
    
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
        assert progress.is_complete
        assert progress.end_time is not None
    
    def test_progress_callbacks(self, progress_tracker):
        """Test progress callback notifications"""
        callback_calls = []
        
        def test_callback(progress: OperationProgress):
            callback_calls.append(progress.current_item)
        
        progress_tracker.start_operation('test_op', 'bulk_change', 100)
        progress_tracker.subscribe_to_operation('test_op', test_callback)
        
        progress_tracker.update_operation_progress('test_op', current_item=25)
        progress_tracker.update_operation_progress('test_op', current_item=50)
        
        assert len(callback_calls) >= 2
        assert 25 in callback_calls
        assert 50 in callback_calls
    
    def test_list_active_operations(self, progress_tracker):
        """Test listing active operations"""
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.start_operation('op2', 'conversion', 50)
        
        active_ops = progress_tracker.list_active_operations()
        assert len(active_ops) == 2
        assert 'op1' in active_ops
        assert 'op2' in active_ops
        
        # Complete one operation
        progress_tracker.complete_operation('op1', ProgressPhase.COMPLETED)
        
        active_ops = progress_tracker.list_active_operations()
        assert len(active_ops) == 1
        assert 'op2' in active_ops
    
    def test_operation_statistics(self, progress_tracker):
        """Test operation statistics"""
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.start_operation('op2', 'conversion', 50)
        progress_tracker.complete_operation('op1', ProgressPhase.COMPLETED)
        progress_tracker.complete_operation('op2', ProgressPhase.FAILED)
        
        stats = progress_tracker.get_operation_statistics()
        
        assert stats['total_operations'] == 2
        assert stats['active_operations'] == 0
        assert stats['completed_operations'] == 1
        assert stats['failed_operations'] == 1
        assert 'bulk_change' in stats['operation_types']
        assert 'conversion' in stats['operation_types']
    
    def test_cleanup_completed_operations(self, progress_tracker):
        """Test cleanup of old completed operations"""
        progress_tracker.start_operation('op1', 'bulk_change', 100)
        progress_tracker.complete_operation('op1', ProgressPhase.COMPLETED)
        
        # Manually set end time to past
        progress = progress_tracker.get_operation_progress('op1')
        progress.end_time = datetime.now() - timedelta(hours=2)
        
        # Cleanup operations older than 1 hour
        progress_tracker.cleanup_completed_operations(keep_hours=1)
        
        # Operation should be cleaned up
        assert progress_tracker.get_operation_progress('op1') is None


class TestRollbackManager:
    """Test suite for RollbackManager"""
    
    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager instance"""
        return RollbackManager()
    
    def test_record_operation(self, rollback_manager):
        """Test recording rollback operation"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[
                {'element_id': 'elem1', 'old_type': 'text', 'new_type': 'title'}
            ]
        )
        
        rollback_manager.record_operation(operation)
        
        recorded = rollback_manager.get_operation_history('test_op')
        assert recorded is not None
        assert recorded.operation_id == 'test_op'
    
    @pytest.mark.asyncio
    async def test_execute_rollback(self, rollback_manager):
        """Test rollback execution"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[
                {'element_id': 'elem1', 'old_type': 'text', 'new_type': 'title'}
            ]
        )
        
        rollback_manager.record_operation(operation)
        
        success = await rollback_manager.execute_rollback('test_op')
        assert success
        
        state = rollback_manager.get_rollback_state('test_op')
        assert state == RollbackState.COMPLETED


class TestModuleLevelFunctions:
    """Test module-level convenience functions"""
    
    def test_start_operation_progress(self):
        """Test module-level start operation function"""
        progress = start_operation_progress(
            operation_id='module_test',
            operation_type='test_operation',
            total_items=50
        )
        
        assert isinstance(progress, OperationProgress)
        assert progress.operation_id == 'module_test'
        assert progress.total_items == 50
    
    def test_update_operation_progress(self):
        """Test module-level update progress function"""
        start_operation_progress('module_test2', 'test_operation', 50)
        
        success = update_operation_progress(
            operation_id='module_test2',
            current_item=25,
            message='Half complete'
        )
        
        assert success
    
    def test_complete_operation_progress(self):
        """Test module-level complete operation function"""
        start_operation_progress('module_test3', 'test_operation', 50)
        
        success = complete_operation_progress(
            operation_id='module_test3',
            final_phase=ProgressPhase.COMPLETED,
            message='Test completed'
        )
        
        assert success


class TestThreadSafety:
    """Test thread safety of bulk operations"""
    
    @pytest.fixture
    def bulk_engine(self):
        """Create bulk engine for thread safety testing"""
        registry = Mock(spec=TypeRegistry)
        validator = Mock(spec=TypeValidationEngine)
        validator.validate_bulk_change.return_value = ValidationResult(
            is_valid=True,
            messages=[
                ValidationMessage(
                    message="Validation passed",
                    severity=ValidationSeverity.INFO
                )
            ]
        )
        
        return BulkTypeOperationEngine(
            registry=registry,
            validator=validator,
            max_workers=4
        )
    
    def test_concurrent_operations(self, bulk_engine):
        """Test concurrent bulk operations"""
        def run_bulk_operation(operation_id):
            element_ids = [f'elem_{operation_id}_{i}' for i in range(10)]
            
            result = bulk_engine.execute_bulk_change(
                element_ids=element_ids,
                from_type='text',
                to_type='title'
            )
            
            return result.success_count == 10
        
        threads = []
        results = {}
        
        # Start multiple concurrent operations
        for i in range(3):
            thread = threading.Thread(
                target=lambda op_id=i: results.update({op_id: run_bulk_operation(op_id)})
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert len(results) == 3
        assert all(results.values())


class TestPerformance:
    """Performance tests for bulk operations"""
    
    @pytest.fixture
    def large_bulk_engine(self):
        """Create bulk engine for performance testing"""
        registry = Mock(spec=TypeRegistry)
        validator = Mock(spec=TypeValidationEngine)
        validator.validate_bulk_change.return_value = ValidationResult(
            is_valid=True,
            messages=[
                ValidationMessage(
                    message="Validation passed",
                    severity=ValidationSeverity.INFO
                )
            ]
        )
        
        return BulkTypeOperationEngine(
            registry=registry,
            validator=validator,
            max_workers=8
        )
    
    def test_large_batch_performance(self, large_bulk_engine):
        """Test performance with large batch sizes"""
        # Create large number of elements
        element_ids = [f'elem_{i}' for i in range(1000)]
        
        start_time = time.time()
        
        result = large_bulk_engine.execute_bulk_change(
            element_ids=element_ids,
            from_type='text',
            to_type='title',
            options=BulkOperationOptions(batch_size=100)
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert result.status == OperationStatus.COMPLETED
        assert result.success_count == 1000
        # Performance should be reasonable (less than 5 seconds for 1000 items)
        assert execution_time < 5.0
    
    def test_memory_usage_large_operations(self, large_bulk_engine):
        """Test memory usage with large operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process large batch
        element_ids = [f'elem_{i}' for i in range(5000)]
        
        result = large_bulk_engine.execute_bulk_change(
            element_ids=element_ids,
            from_type='text',
            to_type='title',
            options=BulkOperationOptions(batch_size=500)
        )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        assert result.status == OperationStatus.COMPLETED
        # Memory increase should be reasonable (less than 100MB for 5000 items)
        assert memory_increase < 100 * 1024 * 1024


if __name__ == '__main__':
    pytest.main([__file__, '-v'])