"""Tests for Rollback Management System

Test suite for rollback functionality including:
- Operation recording and history management
- Rollback execution and validation
- Transaction support and consistency
- Thread safety and concurrent operations
"""

import pytest
import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from torematrix.core.operations.type_management.rollback import (
    RollbackManager, RollbackOperation, RollbackState, TransactionState
)


class TestRollbackOperation:
    """Test suite for RollbackOperation data class"""
    
    def test_rollback_operation_creation(self):
        """Test creating rollback operation"""
        element_changes = [
            {
                'element_id': 'elem1',
                'old_type': 'text',
                'new_type': 'title',
                'old_data': {'content': 'Original'},
                'new_data': {'content': 'Modified'}
            }
        ]
        
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=element_changes
        )
        
        assert operation.operation_id == 'test_op'
        assert operation.operation_type == 'bulk_change'
        assert len(operation.element_changes) == 1
        assert operation.element_changes[0]['element_id'] == 'elem1'
    
    def test_rollback_operation_with_metadata(self):
        """Test rollback operation with metadata"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='conversion',
            timestamp=datetime.now(),
            element_changes=[],
            metadata={'user': 'test_user', 'reason': 'test_conversion'}
        )
        
        assert operation.metadata['user'] == 'test_user'
        assert operation.metadata['reason'] == 'test_conversion'


class TestRollbackManager:
    """Test suite for RollbackManager"""
    
    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager instance"""
        return RollbackManager()
    
    def test_manager_initialization(self, rollback_manager):
        """Test rollback manager initialization"""
        assert len(rollback_manager.operation_history) == 0
        assert len(rollback_manager.rollback_states) == 0
        assert len(rollback_manager.transactions) == 0
    
    def test_record_operation(self, rollback_manager):
        """Test recording rollback operation"""
        element_changes = [
            {
                'element_id': 'elem1',
                'old_type': 'text',
                'new_type': 'title',
                'old_data': {'content': 'Original'},
                'new_data': {'content': 'Modified'}
            }
        ]
        
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=element_changes
        )
        
        rollback_manager.record_operation(operation)
        
        # Check operation is recorded
        assert 'test_op' in rollback_manager.operation_history
        recorded = rollback_manager.operation_history['test_op']
        assert recorded.operation_id == 'test_op'
        assert len(recorded.element_changes) == 1
        
        # Check rollback state is initialized
        assert 'test_op' in rollback_manager.rollback_states
        assert rollback_manager.rollback_states['test_op'] == RollbackState.RECORDED
    
    def test_get_operation_history(self, rollback_manager):
        """Test getting operation history"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.record_operation(operation)
        
        retrieved = rollback_manager.get_operation_history('test_op')
        assert retrieved is not None
        assert retrieved.operation_id == 'test_op'
        
        # Test non-existent operation
        retrieved = rollback_manager.get_operation_history('nonexistent')
        assert retrieved is None
    
    def test_get_rollback_state(self, rollback_manager):
        """Test getting rollback state"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.record_operation(operation)
        
        state = rollback_manager.get_rollback_state('test_op')
        assert state == RollbackState.RECORDED
        
        # Test non-existent operation
        state = rollback_manager.get_rollback_state('nonexistent')
        assert state == RollbackState.NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_execute_rollback(self, rollback_manager):
        """Test executing rollback operation"""
        element_changes = [
            {
                'element_id': 'elem1',
                'old_type': 'text',
                'new_type': 'title',
                'old_data': {'content': 'Original'},
                'new_data': {'content': 'Modified'}
            },
            {
                'element_id': 'elem2',
                'old_type': 'paragraph',
                'new_type': 'text',
                'old_data': {'content': 'Another original'},
                'new_data': {'content': 'Another modified'}
            }
        ]
        
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=element_changes
        )
        
        rollback_manager.record_operation(operation)
        
        # Execute rollback
        success = await rollback_manager.execute_rollback('test_op')
        assert success
        
        # Check state is updated
        state = rollback_manager.get_rollback_state('test_op')
        assert state == RollbackState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_rollback_nonexistent(self, rollback_manager):
        """Test executing rollback for non-existent operation"""
        success = await rollback_manager.execute_rollback('nonexistent')
        assert not success
    
    @pytest.mark.asyncio
    async def test_execute_rollback_already_executed(self, rollback_manager):
        """Test executing rollback that was already executed"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.record_operation(operation)
        
        # Execute first time
        success1 = await rollback_manager.execute_rollback('test_op')
        assert success1
        
        # Execute second time - should fail
        success2 = await rollback_manager.execute_rollback('test_op')
        assert not success2
    
    def test_can_rollback(self, rollback_manager):
        """Test checking if operation can be rolled back"""
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.record_operation(operation)
        
        # Should be able to rollback initially
        assert rollback_manager.can_rollback('test_op')
        
        # Manually set state to completed
        rollback_manager.rollback_states['test_op'] = RollbackState.COMPLETED
        
        # Should not be able to rollback again
        assert not rollback_manager.can_rollback('test_op')
        
        # Test non-existent operation
        assert not rollback_manager.can_rollback('nonexistent')
    
    def test_list_rollbackable_operations(self, rollback_manager):
        """Test listing rollbackable operations"""
        # Create multiple operations
        operations = []
        for i in range(3):
            operation = RollbackOperation(
                operation_id=f'op_{i}',
                operation_type='bulk_change',
                timestamp=datetime.now(),
                element_changes=[]
            )
            operations.append(operation)
            rollback_manager.record_operation(operation)
        
        # All should be rollbackable initially
        rollbackable = rollback_manager.list_rollbackable_operations()
        assert len(rollbackable) == 3
        assert 'op_0' in rollbackable
        assert 'op_1' in rollbackable
        assert 'op_2' in rollbackable
        
        # Mark one as completed
        rollback_manager.rollback_states['op_1'] = RollbackState.COMPLETED
        
        rollbackable = rollback_manager.list_rollbackable_operations()
        assert len(rollbackable) == 2
        assert 'op_0' in rollbackable
        assert 'op_2' in rollbackable
        assert 'op_1' not in rollbackable
    
    def test_get_operation_statistics(self, rollback_manager):
        """Test getting rollback statistics"""
        # Create operations with different states
        for i in range(5):
            operation = RollbackOperation(
                operation_id=f'op_{i}',
                operation_type='bulk_change',
                timestamp=datetime.now(),
                element_changes=[]
            )
            rollback_manager.record_operation(operation)
        
        # Set different states
        rollback_manager.rollback_states['op_1'] = RollbackState.COMPLETED
        rollback_manager.rollback_states['op_2'] = RollbackState.FAILED
        rollback_manager.rollback_states['op_3'] = RollbackState.IN_PROGRESS
        
        stats = rollback_manager.get_operation_statistics()
        
        assert stats['total_operations'] == 5
        assert stats['recorded_operations'] == 2  # op_0, op_4
        assert stats['completed_rollbacks'] == 1  # op_1
        assert stats['failed_rollbacks'] == 1    # op_2
        assert stats['in_progress_rollbacks'] == 1  # op_3
    
    def test_cleanup_old_operations(self, rollback_manager):
        """Test cleaning up old operations"""
        # Create operations with different timestamps
        old_operation = RollbackOperation(
            operation_id='old_op',
            operation_type='bulk_change',
            timestamp=datetime.now() - timedelta(days=8),  # 8 days old
            element_changes=[]
        )
        
        recent_operation = RollbackOperation(
            operation_id='recent_op',
            operation_type='bulk_change',
            timestamp=datetime.now() - timedelta(days=3),  # 3 days old
            element_changes=[]
        )
        
        rollback_manager.record_operation(old_operation)
        rollback_manager.record_operation(recent_operation)
        
        # Cleanup operations older than 7 days
        cleaned_count = rollback_manager.cleanup_old_operations(max_age_days=7)
        
        assert cleaned_count == 1
        assert 'old_op' not in rollback_manager.operation_history
        assert 'recent_op' in rollback_manager.operation_history
    
    def test_get_operations_by_type(self, rollback_manager):
        """Test getting operations by type"""
        # Create operations of different types
        bulk_op = RollbackOperation(
            operation_id='bulk_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        conversion_op = RollbackOperation(
            operation_id='conversion_op',
            operation_type='conversion',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.record_operation(bulk_op)
        rollback_manager.record_operation(conversion_op)
        
        bulk_ops = rollback_manager.get_operations_by_type('bulk_change')
        assert len(bulk_ops) == 1
        assert bulk_ops[0].operation_id == 'bulk_op'
        
        conversion_ops = rollback_manager.get_operations_by_type('conversion')
        assert len(conversion_ops) == 1
        assert conversion_ops[0].operation_id == 'conversion_op'
        
        # Test non-existent type
        empty_ops = rollback_manager.get_operations_by_type('nonexistent')
        assert len(empty_ops) == 0
    
    def test_get_operations_by_date_range(self, rollback_manager):
        """Test getting operations by date range"""
        now = datetime.now()
        
        # Create operations with different timestamps
        old_op = RollbackOperation(
            operation_id='old_op',
            operation_type='bulk_change',
            timestamp=now - timedelta(days=5),
            element_changes=[]
        )
        
        recent_op = RollbackOperation(
            operation_id='recent_op',
            operation_type='conversion',
            timestamp=now - timedelta(days=1),
            element_changes=[]
        )
        
        rollback_manager.record_operation(old_op)
        rollback_manager.record_operation(recent_op)
        
        # Get operations from last 3 days
        start_date = now - timedelta(days=3)
        operations = rollback_manager.get_operations_by_date_range(start_date, now)
        
        assert len(operations) == 1
        assert operations[0].operation_id == 'recent_op'


class TestTransactionSupport:
    """Test transaction support in rollback manager"""
    
    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager for transaction testing"""
        return RollbackManager()
    
    def test_start_transaction(self, rollback_manager):
        """Test starting transaction"""
        transaction_id = rollback_manager.start_transaction('test_transaction')
        
        assert transaction_id is not None
        assert transaction_id in rollback_manager.transactions
        assert rollback_manager.transactions[transaction_id]['state'] == TransactionState.ACTIVE
        assert len(rollback_manager.transactions[transaction_id]['operations']) == 0
    
    def test_add_operation_to_transaction(self, rollback_manager):
        """Test adding operation to transaction"""
        transaction_id = rollback_manager.start_transaction('test_transaction')
        
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.add_operation_to_transaction(transaction_id, operation)
        
        transaction = rollback_manager.transactions[transaction_id]
        assert len(transaction['operations']) == 1
        assert transaction['operations'][0] == operation
    
    @pytest.mark.asyncio
    async def test_commit_transaction(self, rollback_manager):
        """Test committing transaction"""
        transaction_id = rollback_manager.start_transaction('test_transaction')
        
        operations = []
        for i in range(3):
            operation = RollbackOperation(
                operation_id=f'op_{i}',
                operation_type='bulk_change',
                timestamp=datetime.now(),
                element_changes=[]
            )
            operations.append(operation)
            rollback_manager.add_operation_to_transaction(transaction_id, operation)
        
        success = await rollback_manager.commit_transaction(transaction_id)
        assert success
        
        # Check transaction state
        transaction = rollback_manager.transactions[transaction_id]
        assert transaction['state'] == TransactionState.COMMITTED
        
        # Check operations are recorded
        for operation in operations:
            assert operation.operation_id in rollback_manager.operation_history
    
    @pytest.mark.asyncio
    async def test_rollback_transaction(self, rollback_manager):
        """Test rolling back transaction"""
        transaction_id = rollback_manager.start_transaction('test_transaction')
        
        operation = RollbackOperation(
            operation_id='test_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[]
        )
        
        rollback_manager.add_operation_to_transaction(transaction_id, operation)
        
        success = await rollback_manager.rollback_transaction(transaction_id)
        assert success
        
        # Check transaction state
        transaction = rollback_manager.transactions[transaction_id]
        assert transaction['state'] == TransactionState.ROLLED_BACK
        
        # Check operation is not recorded
        assert 'test_op' not in rollback_manager.operation_history


class TestThreadSafety:
    """Test thread safety of rollback manager"""
    
    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager for thread safety testing"""
        return RollbackManager()
    
    def test_concurrent_operation_recording(self, rollback_manager):
        """Test concurrent operation recording"""
        def record_operation(op_id):
            operation = RollbackOperation(
                operation_id=f'op_{op_id}',
                operation_type='bulk_change',
                timestamp=datetime.now(),
                element_changes=[]
            )
            rollback_manager.record_operation(operation)
        
        threads = []
        
        # Start multiple threads recording operations
        for i in range(10):
            thread = threading.Thread(target=record_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all operations were recorded
        assert len(rollback_manager.operation_history) == 10
        for i in range(10):
            assert f'op_{i}' in rollback_manager.operation_history
    
    @pytest.mark.asyncio
    async def test_concurrent_rollback_execution(self, rollback_manager):
        """Test concurrent rollback execution"""
        # Record multiple operations
        for i in range(5):
            operation = RollbackOperation(
                operation_id=f'op_{i}',
                operation_type='bulk_change',
                timestamp=datetime.now(),
                element_changes=[]
            )
            rollback_manager.record_operation(operation)
        
        async def execute_rollback(op_id):
            return await rollback_manager.execute_rollback(f'op_{op_id}')
        
        # Execute rollbacks concurrently
        tasks = [execute_rollback(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All rollbacks should succeed
        assert all(results)
        
        # Check all states are updated
        for i in range(5):
            state = rollback_manager.get_rollback_state(f'op_{i}')
            assert state == RollbackState.COMPLETED


class TestRollbackValidation:
    """Test rollback validation and error handling"""
    
    @pytest.fixture
    def rollback_manager(self):
        """Create rollback manager for validation testing"""
        return RollbackManager()
    
    def test_validate_rollback_operation(self, rollback_manager):
        """Test rollback operation validation"""
        # Valid operation
        valid_operation = RollbackOperation(
            operation_id='valid_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[
                {
                    'element_id': 'elem1',
                    'old_type': 'text',
                    'new_type': 'title',
                    'old_data': {'content': 'Original'},
                    'new_data': {'content': 'Modified'}
                }
            ]
        )
        
        is_valid, errors = rollback_manager.validate_rollback_operation(valid_operation)
        assert is_valid
        assert len(errors) == 0
        
        # Invalid operation - missing required fields
        invalid_operation = RollbackOperation(
            operation_id='invalid_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[
                {
                    'element_id': 'elem1',
                    # Missing old_type, new_type, etc.
                }
            ]
        )
        
        is_valid, errors = rollback_manager.validate_rollback_operation(invalid_operation)
        assert not is_valid
        assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_rollback_with_validation_failure(self, rollback_manager):
        """Test rollback execution with validation failure"""
        # Mock validation to fail
        def mock_validate_element_rollback(element_id, old_type, new_type, old_data):
            return False, ['Validation failed']
        
        rollback_manager.validate_element_rollback = mock_validate_element_rollback
        
        operation = RollbackOperation(
            operation_id='failing_op',
            operation_type='bulk_change',
            timestamp=datetime.now(),
            element_changes=[
                {
                    'element_id': 'elem1',
                    'old_type': 'text',
                    'new_type': 'title',
                    'old_data': {'content': 'Original'},
                    'new_data': {'content': 'Modified'}
                }
            ]
        )
        
        rollback_manager.record_operation(operation)
        
        success = await rollback_manager.execute_rollback('failing_op')
        assert not success
        
        # State should be FAILED
        state = rollback_manager.get_rollback_state('failing_op')
        assert state == RollbackState.FAILED


if __name__ == '__main__':
    pytest.main([__file__, '-v'])