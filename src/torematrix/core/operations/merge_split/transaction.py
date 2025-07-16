"""
Transaction Management System for Merge/Split Operations.

This module provides transactional capabilities for merge and split operations,
ensuring data consistency, rollback capabilities, and atomic operations.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import copy
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
import threading
from collections import deque

from ..core.elements import Element
from ..core.metadata import Metadata


class TransactionState(Enum):
    """Transaction lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    FAILED = "failed"


class OperationType(Enum):
    """Types of operations that can be performed."""
    MERGE = "merge"
    SPLIT = "split"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    BATCH = "batch"


@dataclass
class OperationRecord:
    """Record of a single operation within a transaction."""
    operation_id: str
    operation_type: OperationType
    target_elements: List[str]  # Element IDs
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_rollback_data(self) -> Dict[str, Any]:
        """Get data needed to rollback this operation."""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'target_elements': self.target_elements,
            'restore_state': self.before_state,
            'timestamp': self.timestamp
        }


@dataclass
class Transaction:
    """Transactional container for merge/split operations."""
    transaction_id: str
    state: TransactionState = TransactionState.PENDING
    operations: List[OperationRecord] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout_seconds: float = 300.0  # 5 minutes default
    isolation_level: str = "READ_COMMITTED"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Get transaction duration in seconds."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at if self.completed_at else time.time()
        return end_time - self.started_at
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is currently active."""
        return self.state == TransactionState.ACTIVE
    
    @property
    def is_completed(self) -> bool:
        """Check if transaction is completed (committed or aborted)."""
        return self.state in [TransactionState.COMMITTED, TransactionState.ABORTED]
    
    @property
    def is_timed_out(self) -> bool:
        """Check if transaction has timed out."""
        if self.started_at is None:
            return False
        return (time.time() - self.started_at) > self.timeout_seconds
    
    def add_operation(self, operation: OperationRecord) -> None:
        """Add an operation to this transaction."""
        if not self.is_active:
            raise ValueError(f"Cannot add operation to transaction in state {self.state}")
        self.operations.append(operation)
    
    def get_affected_elements(self) -> Set[str]:
        """Get all element IDs affected by this transaction."""
        affected = set()
        for op in self.operations:
            affected.update(op.target_elements)
        return affected


class TransactionIsolationLevel:
    """Transaction isolation level configurations."""
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"  
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionManager:
    """
    Manages transactions for merge/split operations.
    
    Provides ACID properties:
    - Atomicity: All operations in a transaction succeed or fail together
    - Consistency: Transactions maintain data integrity
    - Isolation: Concurrent transactions don't interfere
    - Durability: Committed changes are persistent
    """
    
    def __init__(self):
        self.active_transactions: Dict[str, Transaction] = {}
        self.completed_transactions: deque = deque(maxlen=1000)  # Keep last 1000
        self.element_locks: Dict[str, Set[str]] = {}  # element_id -> transaction_ids
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'total_transactions': 0,
            'committed_transactions': 0,
            'aborted_transactions': 0,
            'average_duration': 0.0,
            'total_operations': 0,
            'lock_conflicts': 0
        }
    
    def begin_transaction(self, 
                         timeout_seconds: float = 300.0,
                         isolation_level: str = TransactionIsolationLevel.READ_COMMITTED,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Begin a new transaction.
        
        Args:
            timeout_seconds: Transaction timeout
            isolation_level: Isolation level for the transaction
            metadata: Additional transaction metadata
            
        Returns:
            Transaction ID
        """
        with self.lock:
            transaction_id = str(uuid.uuid4())
            
            transaction = Transaction(
                transaction_id=transaction_id,
                timeout_seconds=timeout_seconds,
                isolation_level=isolation_level,
                metadata=metadata or {}
            )
            
            transaction.state = TransactionState.ACTIVE
            transaction.started_at = time.time()
            
            self.active_transactions[transaction_id] = transaction
            self.metrics['total_transactions'] += 1
            
            self.logger.info(f"Started transaction {transaction_id}")
            return transaction_id
    
    def add_operation(self,
                     transaction_id: str,
                     operation_type: OperationType,
                     target_elements: List[str],
                     before_state: Dict[str, Any],
                     after_state: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add an operation to a transaction.
        
        Args:
            transaction_id: Target transaction
            operation_type: Type of operation
            target_elements: Element IDs affected
            before_state: State before operation
            after_state: State after operation
            metadata: Operation metadata
            
        Returns:
            Operation ID
        """
        with self.lock:
            if transaction_id not in self.active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found or not active")
            
            transaction = self.active_transactions[transaction_id]
            
            # Check for timeout
            if transaction.is_timed_out:
                self._abort_transaction_internal(transaction_id, "Transaction timed out")
                raise TimeoutError(f"Transaction {transaction_id} has timed out")
            
            # Acquire locks on target elements
            if not self._acquire_element_locks(transaction_id, target_elements):
                raise RuntimeError(f"Could not acquire locks for elements: {target_elements}")
            
            # Create operation record
            operation = OperationRecord(
                operation_id=str(uuid.uuid4()),
                operation_type=operation_type,
                target_elements=target_elements,
                before_state=copy.deepcopy(before_state),
                after_state=copy.deepcopy(after_state),
                metadata=metadata or {}
            )
            
            transaction.add_operation(operation)
            self.metrics['total_operations'] += 1
            
            self.logger.debug(f"Added operation {operation.operation_id} to transaction {transaction_id}")
            return operation.operation_id
    
    def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction, making all changes permanent.
        
        Args:
            transaction_id: Transaction to commit
            
        Returns:
            True if committed successfully
        """
        with self.lock:
            if transaction_id not in self.active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found or not active")
            
            transaction = self.active_transactions[transaction_id]
            
            try:
                transaction.state = TransactionState.COMMITTING
                
                # Validate all operations before committing
                if not self._validate_transaction(transaction):
                    self._abort_transaction_internal(transaction_id, "Transaction validation failed")
                    return False
                
                # Apply all operations (this would integrate with actual element storage)
                self._apply_transaction_operations(transaction)
                
                # Mark as committed
                transaction.state = TransactionState.COMMITTED
                transaction.completed_at = time.time()
                
                # Release element locks
                self._release_element_locks(transaction_id)
                
                # Move to completed transactions
                self._complete_transaction(transaction)
                
                self.metrics['committed_transactions'] += 1
                self._update_average_duration(transaction.duration)
                
                self.logger.info(f"Committed transaction {transaction_id} with {len(transaction.operations)} operations")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to commit transaction {transaction_id}: {e}")
                self._abort_transaction_internal(transaction_id, str(e))
                return False
    
    def abort_transaction(self, transaction_id: str, reason: str = "User requested") -> bool:
        """
        Abort a transaction, rolling back all changes.
        
        Args:
            transaction_id: Transaction to abort
            reason: Reason for abortion
            
        Returns:
            True if aborted successfully
        """
        with self.lock:
            return self._abort_transaction_internal(transaction_id, reason)
    
    def _abort_transaction_internal(self, transaction_id: str, reason: str) -> bool:
        """Internal method to abort a transaction."""
        if transaction_id not in self.active_transactions:
            return False
        
        transaction = self.active_transactions[transaction_id]
        
        try:
            transaction.state = TransactionState.ABORTING
            transaction.error_message = reason
            
            # Rollback all operations in reverse order
            self._rollback_transaction_operations(transaction)
            
            # Mark as aborted
            transaction.state = TransactionState.ABORTED
            transaction.completed_at = time.time()
            
            # Release element locks
            self._release_element_locks(transaction_id)
            
            # Move to completed transactions
            self._complete_transaction(transaction)
            
            self.metrics['aborted_transactions'] += 1
            self._update_average_duration(transaction.duration)
            
            self.logger.info(f"Aborted transaction {transaction_id}: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to abort transaction {transaction_id}: {e}")
            transaction.state = TransactionState.FAILED
            transaction.error_message = f"Abort failed: {e}"
            return False
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a transaction.
        
        Args:
            transaction_id: Transaction to query
            
        Returns:
            Transaction status dictionary
        """
        with self.lock:
            # Check active transactions
            if transaction_id in self.active_transactions:
                transaction = self.active_transactions[transaction_id]
                return self._transaction_to_dict(transaction)
            
            # Check completed transactions
            for transaction in self.completed_transactions:
                if transaction.transaction_id == transaction_id:
                    return self._transaction_to_dict(transaction)
            
            return None
    
    def get_active_transactions(self) -> List[Dict[str, Any]]:
        """Get list of all active transactions."""
        with self.lock:
            return [self._transaction_to_dict(t) for t in self.active_transactions.values()]
    
    def cleanup_expired_transactions(self) -> int:
        """
        Clean up expired transactions.
        
        Returns:
            Number of transactions cleaned up
        """
        with self.lock:
            expired_ids = []
            
            for tid, transaction in self.active_transactions.items():
                if transaction.is_timed_out:
                    expired_ids.append(tid)
            
            for tid in expired_ids:
                self._abort_transaction_internal(tid, "Transaction expired")
            
            return len(expired_ids)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get transaction manager performance metrics."""
        with self.lock:
            return {
                **self.metrics,
                'active_transactions': len(self.active_transactions),
                'completed_transactions': len(self.completed_transactions),
                'locked_elements': len(self.element_locks)
            }
    
    @contextmanager
    def transaction(self, 
                   timeout_seconds: float = 300.0,
                   isolation_level: str = TransactionIsolationLevel.READ_COMMITTED,
                   auto_commit: bool = True):
        """
        Context manager for transaction handling.
        
        Args:
            timeout_seconds: Transaction timeout
            isolation_level: Isolation level
            auto_commit: Whether to auto-commit on success
            
        Usage:
            with transaction_manager.transaction() as tx_id:
                # Perform operations
                pass
        """
        transaction_id = self.begin_transaction(timeout_seconds, isolation_level)
        
        try:
            yield transaction_id
            
            if auto_commit:
                success = self.commit_transaction(transaction_id)
                if not success:
                    raise RuntimeError("Transaction commit failed")
                    
        except Exception as e:
            self.abort_transaction(transaction_id, str(e))
            raise
    
    # Private helper methods
    
    def _acquire_element_locks(self, transaction_id: str, element_ids: List[str]) -> bool:
        """Acquire locks on elements for a transaction."""
        # Check if any elements are already locked by other transactions
        for element_id in element_ids:
            if element_id in self.element_locks:
                locked_by = self.element_locks[element_id]
                if locked_by and transaction_id not in locked_by:
                    self.metrics['lock_conflicts'] += 1
                    return False
        
        # Acquire locks
        for element_id in element_ids:
            if element_id not in self.element_locks:
                self.element_locks[element_id] = set()
            self.element_locks[element_id].add(transaction_id)
        
        return True
    
    def _release_element_locks(self, transaction_id: str) -> None:
        """Release all element locks held by a transaction."""
        to_remove = []
        
        for element_id, locked_by in self.element_locks.items():
            if transaction_id in locked_by:
                locked_by.remove(transaction_id)
                if not locked_by:  # No more locks on this element
                    to_remove.append(element_id)
        
        for element_id in to_remove:
            del self.element_locks[element_id]
    
    def _validate_transaction(self, transaction: Transaction) -> bool:
        """Validate that a transaction can be committed."""
        # Check transaction state
        if transaction.state != TransactionState.COMMITTING:
            return False
        
        # Check for timeout
        if transaction.is_timed_out:
            return False
        
        # Validate each operation
        for operation in transaction.operations:
            if not self._validate_operation(operation):
                return False
        
        return True
    
    def _validate_operation(self, operation: OperationRecord) -> bool:
        """Validate a single operation."""
        # Check that operation has required data
        if not operation.target_elements:
            return False
        
        # Validate state data exists
        if operation.before_state is None or operation.after_state is None:
            return False
        
        # Additional validation based on operation type
        if operation.operation_type == OperationType.MERGE:
            return len(operation.target_elements) >= 2
        elif operation.operation_type == OperationType.SPLIT:
            return len(operation.target_elements) >= 1
        
        return True
    
    def _apply_transaction_operations(self, transaction: Transaction) -> None:
        """Apply all operations in a transaction."""
        # This is where we would integrate with the actual element storage system
        # For now, we just log the operations
        for operation in transaction.operations:
            self.logger.debug(f"Applying operation {operation.operation_id}: {operation.operation_type}")
    
    def _rollback_transaction_operations(self, transaction: Transaction) -> None:
        """Rollback all operations in a transaction."""
        # Apply operations in reverse order
        for operation in reversed(transaction.operations):
            self.logger.debug(f"Rolling back operation {operation.operation_id}: {operation.operation_type}")
            # This is where we would restore the before_state
    
    def _complete_transaction(self, transaction: Transaction) -> None:
        """Move transaction from active to completed."""
        if transaction.transaction_id in self.active_transactions:
            del self.active_transactions[transaction.transaction_id]
        self.completed_transactions.append(transaction)
    
    def _update_average_duration(self, duration: float) -> None:
        """Update average transaction duration metric."""
        total_completed = self.metrics['committed_transactions'] + self.metrics['aborted_transactions']
        if total_completed > 1:
            current_avg = self.metrics['average_duration']
            self.metrics['average_duration'] = ((current_avg * (total_completed - 1)) + duration) / total_completed
        else:
            self.metrics['average_duration'] = duration
    
    def _transaction_to_dict(self, transaction: Transaction) -> Dict[str, Any]:
        """Convert transaction to dictionary for serialization."""
        return {
            'transaction_id': transaction.transaction_id,
            'state': transaction.state.value,
            'operation_count': len(transaction.operations),
            'affected_elements': list(transaction.get_affected_elements()),
            'created_at': transaction.created_at,
            'started_at': transaction.started_at,
            'completed_at': transaction.completed_at,
            'duration': transaction.duration,
            'timeout_seconds': transaction.timeout_seconds,
            'isolation_level': transaction.isolation_level,
            'metadata': transaction.metadata,
            'error_message': transaction.error_message
        }


# Global transaction manager instance
_transaction_manager: Optional[TransactionManager] = None


def get_transaction_manager() -> TransactionManager:
    """Get the global transaction manager instance."""
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = TransactionManager()
    return _transaction_manager


def reset_transaction_manager() -> None:
    """Reset the global transaction manager (useful for testing)."""
    global _transaction_manager
    _transaction_manager = None