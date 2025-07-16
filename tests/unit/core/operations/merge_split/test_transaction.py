"""
Comprehensive tests for transaction management system.

Tests transaction lifecycle, ACID properties, performance,
and error handling scenarios.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.torematrix.core.operations.merge_split.transaction import (
    TransactionManager,
    Transaction,
    TransactionState,
    OperationType,
    OperationRecord,
    TransactionIsolationLevel,
    get_transaction_manager,
    reset_transaction_manager
)


@pytest.fixture
def transaction_manager():
    """Create a fresh transaction manager for each test."""
    reset_transaction_manager()
    return TransactionManager()


@pytest.fixture
def sample_operation_data():
    """Sample operation data for testing."""
    return {
        'before_state': {'element_1': {'content': 'Original text', 'bounds': [0, 0, 100, 50]}},
        'after_state': {'element_merged': {'content': 'Merged text', 'bounds': [0, 0, 200, 50]}}
    }


class TestTransaction:
    """Test Transaction dataclass and methods."""
    
    def test_transaction_creation(self):
        """Test transaction creation with default values."""
        tx = Transaction(transaction_id="test-123")
        
        assert tx.transaction_id == "test-123"
        assert tx.state == TransactionState.PENDING
        assert len(tx.operations) == 0
        assert tx.created_at > 0
        assert tx.started_at is None
        assert tx.completed_at is None
        assert tx.timeout_seconds == 300.0
        assert tx.isolation_level == "READ_COMMITTED"
        assert len(tx.metadata) == 0
        assert tx.error_message is None
    
    def test_transaction_duration_calculation(self):
        """Test transaction duration calculations."""
        tx = Transaction(transaction_id="test-123")
        
        # No start time
        assert tx.duration == 0.0
        
        # With start time, no end time
        tx.started_at = time.time()
        time.sleep(0.1)
        duration1 = tx.duration
        assert duration1 > 0.05  # Should be around 0.1 seconds
        
        # With both start and end time
        tx.completed_at = tx.started_at + 5.0
        assert tx.duration == 5.0
    
    def test_transaction_state_properties(self):
        """Test transaction state property methods."""
        tx = Transaction(transaction_id="test-123")
        
        # Pending state
        assert not tx.is_active
        assert not tx.is_completed
        
        # Active state
        tx.state = TransactionState.ACTIVE
        assert tx.is_active
        assert not tx.is_completed
        
        # Committed state
        tx.state = TransactionState.COMMITTED
        assert not tx.is_active
        assert tx.is_completed
        
        # Aborted state
        tx.state = TransactionState.ABORTED
        assert not tx.is_active
        assert tx.is_completed
    
    def test_transaction_timeout_check(self):
        """Test transaction timeout detection."""
        tx = Transaction(transaction_id="test-123", timeout_seconds=0.1)
        
        # No start time
        assert not tx.is_timed_out
        
        # Recent start time
        tx.started_at = time.time()
        assert not tx.is_timed_out
        
        # Old start time
        tx.started_at = time.time() - 1.0  # 1 second ago
        assert tx.is_timed_out
    
    def test_add_operation_to_active_transaction(self):
        """Test adding operations to active transaction."""
        tx = Transaction(transaction_id="test-123")
        tx.state = TransactionState.ACTIVE
        
        operation = OperationRecord(
            operation_id="op-1",
            operation_type=OperationType.MERGE,
            target_elements=["elem1", "elem2"],
            before_state={},
            after_state={}
        )
        
        tx.add_operation(operation)
        assert len(tx.operations) == 1
        assert tx.operations[0] == operation
    
    def test_add_operation_to_inactive_transaction(self):
        """Test that adding operations to inactive transaction fails."""
        tx = Transaction(transaction_id="test-123")
        # Default state is PENDING
        
        operation = OperationRecord(
            operation_id="op-1",
            operation_type=OperationType.MERGE,
            target_elements=["elem1"],
            before_state={},
            after_state={}
        )
        
        with pytest.raises(ValueError, match="Cannot add operation to transaction"):
            tx.add_operation(operation)
    
    def test_get_affected_elements(self):
        """Test getting all affected elements from transaction."""
        tx = Transaction(transaction_id="test-123")
        tx.state = TransactionState.ACTIVE
        
        # Add multiple operations
        for i in range(3):
            operation = OperationRecord(
                operation_id=f"op-{i}",
                operation_type=OperationType.UPDATE,
                target_elements=[f"elem{i}", f"elem{i+1}"],
                before_state={},
                after_state={}
            )
            tx.add_operation(operation)
        
        affected = tx.get_affected_elements()
        expected = {"elem0", "elem1", "elem2", "elem3"}
        assert affected == expected


class TestOperationRecord:
    """Test OperationRecord dataclass and methods."""
    
    def test_operation_record_creation(self):
        """Test operation record creation."""
        before_state = {"element_1": {"content": "Original"}}
        after_state = {"element_1": {"content": "Modified"}}
        
        op = OperationRecord(
            operation_id="op-123",
            operation_type=OperationType.SPLIT,
            target_elements=["element_1"],
            before_state=before_state,
            after_state=after_state
        )
        
        assert op.operation_id == "op-123"
        assert op.operation_type == OperationType.SPLIT
        assert op.target_elements == ["element_1"]
        assert op.before_state == before_state
        assert op.after_state == after_state
        assert op.timestamp > 0
        assert len(op.metadata) == 0
    
    def test_get_rollback_data(self):
        """Test getting rollback data from operation."""
        before_state = {"element_1": {"content": "Original"}}
        after_state = {"element_1": {"content": "Modified"}}
        
        op = OperationRecord(
            operation_id="op-123",
            operation_type=OperationType.UPDATE,
            target_elements=["element_1"],
            before_state=before_state,
            after_state=after_state
        )
        
        rollback_data = op.get_rollback_data()
        
        assert rollback_data["operation_id"] == "op-123"
        assert rollback_data["operation_type"] == OperationType.UPDATE
        assert rollback_data["target_elements"] == ["element_1"]
        assert rollback_data["restore_state"] == before_state
        assert "timestamp" in rollback_data


class TestTransactionManager:
    """Test TransactionManager functionality."""
    
    def test_transaction_manager_initialization(self, transaction_manager):
        """Test transaction manager initialization."""
        assert len(transaction_manager.active_transactions) == 0
        assert len(transaction_manager.completed_transactions) == 0
        assert len(transaction_manager.element_locks) == 0
        assert transaction_manager.metrics["total_transactions"] == 0
    
    def test_begin_transaction(self, transaction_manager):
        """Test beginning a new transaction."""
        tx_id = transaction_manager.begin_transaction()
        
        assert isinstance(tx_id, str)
        assert len(tx_id) > 0
        assert tx_id in transaction_manager.active_transactions
        
        tx = transaction_manager.active_transactions[tx_id]
        assert tx.state == TransactionState.ACTIVE
        assert tx.started_at is not None
        assert transaction_manager.metrics["total_transactions"] == 1
    
    def test_begin_transaction_with_options(self, transaction_manager):
        """Test beginning transaction with custom options."""
        metadata = {"user": "test_user", "session": "session_123"}
        
        tx_id = transaction_manager.begin_transaction(
            timeout_seconds=600.0,
            isolation_level=TransactionIsolationLevel.SERIALIZABLE,
            metadata=metadata
        )
        
        tx = transaction_manager.active_transactions[tx_id]
        assert tx.timeout_seconds == 600.0
        assert tx.isolation_level == TransactionIsolationLevel.SERIALIZABLE
        assert tx.metadata == metadata
    
    def test_add_operation_success(self, transaction_manager, sample_operation_data):
        """Test successfully adding operation to transaction."""
        tx_id = transaction_manager.begin_transaction()
        
        op_id = transaction_manager.add_operation(
            transaction_id=tx_id,
            operation_type=OperationType.MERGE,
            target_elements=["elem1", "elem2"],
            before_state=sample_operation_data["before_state"],
            after_state=sample_operation_data["after_state"]
        )
        
        assert isinstance(op_id, str)
        assert len(op_id) > 0
        
        tx = transaction_manager.active_transactions[tx_id]
        assert len(tx.operations) == 1
        assert tx.operations[0].operation_id == op_id
        assert transaction_manager.metrics["total_operations"] == 1
    
    def test_add_operation_invalid_transaction(self, transaction_manager):
        """Test adding operation to invalid transaction."""
        with pytest.raises(ValueError, match="Transaction .* not found"):
            transaction_manager.add_operation(
                transaction_id="invalid-id",
                operation_type=OperationType.UPDATE,
                target_elements=["elem1"],
                before_state={},
                after_state={}
            )
    
    def test_add_operation_timeout(self, transaction_manager):
        """Test adding operation to timed out transaction."""
        tx_id = transaction_manager.begin_transaction(timeout_seconds=0.1)
        
        # Wait for timeout
        time.sleep(0.2)
        
        with pytest.raises(TimeoutError, match="Transaction .* has timed out"):
            transaction_manager.add_operation(
                transaction_id=tx_id,
                operation_type=OperationType.UPDATE,
                target_elements=["elem1"],
                before_state={},
                after_state={}
            )
    
    def test_commit_transaction_success(self, transaction_manager, sample_operation_data):
        """Test successful transaction commit."""
        tx_id = transaction_manager.begin_transaction()
        
        # Add operation
        transaction_manager.add_operation(
            transaction_id=tx_id,
            operation_type=OperationType.MERGE,
            target_elements=["elem1", "elem2"],
            before_state=sample_operation_data["before_state"],
            after_state=sample_operation_data["after_state"]
        )
        
        # Commit transaction
        success = transaction_manager.commit_transaction(tx_id)
        
        assert success is True
        assert tx_id not in transaction_manager.active_transactions
        assert len(transaction_manager.completed_transactions) == 1
        assert transaction_manager.metrics["committed_transactions"] == 1
        
        # Check completed transaction
        completed_tx = transaction_manager.completed_transactions[0]
        assert completed_tx.state == TransactionState.COMMITTED
        assert completed_tx.completed_at is not None
    
    def test_commit_invalid_transaction(self, transaction_manager):
        """Test committing invalid transaction."""
        with pytest.raises(ValueError, match="Transaction .* not found"):
            transaction_manager.commit_transaction("invalid-id")
    
    def test_abort_transaction_success(self, transaction_manager, sample_operation_data):
        """Test successful transaction abort."""
        tx_id = transaction_manager.begin_transaction()
        
        # Add operation
        transaction_manager.add_operation(
            transaction_id=tx_id,
            operation_type=OperationType.MERGE,
            target_elements=["elem1", "elem2"],
            before_state=sample_operation_data["before_state"],
            after_state=sample_operation_data["after_state"]
        )
        
        # Abort transaction
        success = transaction_manager.abort_transaction(tx_id, "Test abort")
        
        assert success is True
        assert tx_id not in transaction_manager.active_transactions
        assert len(transaction_manager.completed_transactions) == 1
        assert transaction_manager.metrics["aborted_transactions"] == 1
        
        # Check aborted transaction
        aborted_tx = transaction_manager.completed_transactions[0]
        assert aborted_tx.state == TransactionState.ABORTED
        assert aborted_tx.error_message == "Test abort"
        assert aborted_tx.completed_at is not None
    
    def test_element_locking(self, transaction_manager):
        """Test element locking mechanism."""
        tx_id1 = transaction_manager.begin_transaction()
        tx_id2 = transaction_manager.begin_transaction()
        
        # First transaction locks elements
        transaction_manager.add_operation(
            transaction_id=tx_id1,
            operation_type=OperationType.UPDATE,
            target_elements=["elem1", "elem2"],
            before_state={},
            after_state={}
        )
        
        # Second transaction tries to lock same elements - should fail
        with pytest.raises(RuntimeError, match="Could not acquire locks"):
            transaction_manager.add_operation(
                transaction_id=tx_id2,
                operation_type=OperationType.UPDATE,
                target_elements=["elem2", "elem3"],  # elem2 is already locked
                before_state={},
                after_state={}
            )
        
        # After committing first transaction, locks should be released
        transaction_manager.commit_transaction(tx_id1)
        
        # Now second transaction should succeed
        op_id = transaction_manager.add_operation(
            transaction_id=tx_id2,
            operation_type=OperationType.UPDATE,
            target_elements=["elem2", "elem3"],
            before_state={},
            after_state={}
        )
        
        assert isinstance(op_id, str)
    
    def test_get_transaction_status(self, transaction_manager, sample_operation_data):
        """Test getting transaction status."""
        # Active transaction
        tx_id = transaction_manager.begin_transaction()
        transaction_manager.add_operation(
            transaction_id=tx_id,
            operation_type=OperationType.MERGE,
            target_elements=["elem1", "elem2"],
            before_state=sample_operation_data["before_state"],
            after_state=sample_operation_data["after_state"]
        )
        
        status = transaction_manager.get_transaction_status(tx_id)
        assert status is not None
        assert status["transaction_id"] == tx_id
        assert status["state"] == TransactionState.ACTIVE.value
        assert status["operation_count"] == 1
        assert "elem1" in status["affected_elements"]
        assert "elem2" in status["affected_elements"]
        
        # Commit and check completed status
        transaction_manager.commit_transaction(tx_id)
        
        status = transaction_manager.get_transaction_status(tx_id)
        assert status["state"] == TransactionState.COMMITTED.value
        assert status["completed_at"] is not None
        
        # Non-existent transaction
        status = transaction_manager.get_transaction_status("invalid-id")
        assert status is None
    
    def test_get_active_transactions(self, transaction_manager):
        """Test getting list of active transactions."""
        # No active transactions
        active = transaction_manager.get_active_transactions()
        assert len(active) == 0
        
        # Create multiple active transactions
        tx_ids = []
        for i in range(3):
            tx_id = transaction_manager.begin_transaction()
            tx_ids.append(tx_id)
        
        active = transaction_manager.get_active_transactions()
        assert len(active) == 3
        
        active_ids = [tx["transaction_id"] for tx in active]
        assert set(active_ids) == set(tx_ids)
        
        # Commit one transaction
        transaction_manager.commit_transaction(tx_ids[0])
        
        active = transaction_manager.get_active_transactions()
        assert len(active) == 2
    
    def test_cleanup_expired_transactions(self, transaction_manager):
        """Test cleanup of expired transactions."""
        # Create transactions with very short timeout
        tx_ids = []
        for i in range(3):
            tx_id = transaction_manager.begin_transaction(timeout_seconds=0.1)
            tx_ids.append(tx_id)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Cleanup expired transactions
        cleaned_count = transaction_manager.cleanup_expired_transactions()
        
        assert cleaned_count == 3
        assert len(transaction_manager.active_transactions) == 0
        assert len(transaction_manager.completed_transactions) == 3
        
        # All should be aborted with timeout reason
        for completed_tx in transaction_manager.completed_transactions:
            assert completed_tx.state == TransactionState.ABORTED
            assert "expired" in completed_tx.error_message.lower()
    
    def test_performance_metrics(self, transaction_manager, sample_operation_data):
        """Test performance metrics tracking."""
        initial_metrics = transaction_manager.get_performance_metrics()
        
        # Perform several operations
        for i in range(3):
            tx_id = transaction_manager.begin_transaction()
            transaction_manager.add_operation(
                transaction_id=tx_id,
                operation_type=OperationType.UPDATE,
                target_elements=[f"elem{i}"],
                before_state=sample_operation_data["before_state"],
                after_state=sample_operation_data["after_state"]
            )
            transaction_manager.commit_transaction(tx_id)
        
        final_metrics = transaction_manager.get_performance_metrics()
        
        assert final_metrics["total_transactions"] == initial_metrics["total_transactions"] + 3
        assert final_metrics["committed_transactions"] == initial_metrics["committed_transactions"] + 3
        assert final_metrics["total_operations"] == initial_metrics["total_operations"] + 3
        assert final_metrics["average_duration"] > 0
        assert final_metrics["active_transactions"] == 0
        assert final_metrics["completed_transactions"] == 3
    
    def test_context_manager(self, transaction_manager, sample_operation_data):
        """Test transaction context manager."""
        # Successful transaction
        with transaction_manager.transaction() as tx_id:
            transaction_manager.add_operation(
                transaction_id=tx_id,
                operation_type=OperationType.UPDATE,
                target_elements=["elem1"],
                before_state=sample_operation_data["before_state"],
                after_state=sample_operation_data["after_state"]
            )
        
        # Transaction should be committed
        status = transaction_manager.get_transaction_status(tx_id)
        assert status["state"] == TransactionState.COMMITTED.value
        
        # Failed transaction
        with pytest.raises(RuntimeError):
            with transaction_manager.transaction() as tx_id:
                transaction_manager.add_operation(
                    transaction_id=tx_id,
                    operation_type=OperationType.UPDATE,
                    target_elements=["elem2"],
                    before_state=sample_operation_data["before_state"],
                    after_state=sample_operation_data["after_state"]
                )
                raise RuntimeError("Test error")
        
        # Transaction should be aborted
        status = transaction_manager.get_transaction_status(tx_id)
        assert status["state"] == TransactionState.ABORTED.value
        assert "Test error" in status["error_message"]


class TestConcurrency:
    """Test transaction manager thread safety."""
    
    def test_concurrent_transactions(self, transaction_manager):
        """Test concurrent transaction execution."""
        results = []
        errors = []
        
        def create_transaction(thread_id):
            try:
                tx_id = transaction_manager.begin_transaction()
                transaction_manager.add_operation(
                    transaction_id=tx_id,
                    operation_type=OperationType.UPDATE,
                    target_elements=[f"elem{thread_id}"],
                    before_state={},
                    after_state={}
                )
                success = transaction_manager.commit_transaction(tx_id)
                results.append((thread_id, success))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_transaction, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 10
        assert len(errors) == 0
        assert all(success for _, success in results)
        assert transaction_manager.metrics["total_transactions"] == 10
        assert transaction_manager.metrics["committed_transactions"] == 10
    
    def test_concurrent_element_locking(self, transaction_manager):
        """Test concurrent access to same elements."""
        results = []
        errors = []
        
        def try_lock_element(thread_id):
            try:
                tx_id = transaction_manager.begin_transaction()
                transaction_manager.add_operation(
                    transaction_id=tx_id,
                    operation_type=OperationType.UPDATE,
                    target_elements=["shared_element"],  # Same element for all
                    before_state={},
                    after_state={}
                )
                success = transaction_manager.commit_transaction(tx_id)
                results.append((thread_id, success))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads trying to access same element
        threads = []
        for i in range(5):
            thread = threading.Thread(target=try_lock_element, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Only one should succeed due to locking
        successful_results = [r for r in results if r[1]]
        lock_errors = [e for e in errors if "Could not acquire locks" in e[1]]
        
        assert len(successful_results) == 1
        assert len(lock_errors) == 4
        assert transaction_manager.metrics["lock_conflicts"] == 4


class TestGlobalManager:
    """Test global transaction manager functions."""
    
    def test_get_transaction_manager_singleton(self):
        """Test that get_transaction_manager returns singleton."""
        manager1 = get_transaction_manager()
        manager2 = get_transaction_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, TransactionManager)
    
    def test_reset_transaction_manager(self):
        """Test resetting global transaction manager."""
        manager1 = get_transaction_manager()
        manager1.begin_transaction()
        
        reset_transaction_manager()
        
        manager2 = get_transaction_manager()
        assert manager1 is not manager2
        assert len(manager2.active_transactions) == 0


if __name__ == '__main__':
    pytest.main([__file__])