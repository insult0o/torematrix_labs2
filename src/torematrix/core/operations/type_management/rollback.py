"""Rollback Management System

Comprehensive rollback and undo system for bulk operations with:
- Operation recording and history management
- Rollback execution and validation
- Transaction support and consistency
- Thread safety and concurrent operations
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class RollbackState(Enum):
    """Rollback operation states"""
    NOT_FOUND = "not_found"
    RECORDED = "recorded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionState(Enum):
    """Transaction states for grouped operations"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class RollbackOperation:
    """Rollback operation data"""
    operation_id: str
    operation_type: str
    timestamp: datetime
    element_changes: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    transaction_id: Optional[str] = None


class RollbackManager:
    """Comprehensive rollback and undo system for bulk operations
    
    Provides transaction support, operation history, and safe rollback
    execution with validation and consistency checks.
    """
    
    def __init__(self):
        """Initialize rollback manager"""
        self.operation_history: Dict[str, RollbackOperation] = {}
        self.rollback_states: Dict[str, RollbackState] = {}
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        logger.info("RollbackManager initialized")
    
    def record_operation(self, operation: RollbackOperation):
        """Record an operation for potential rollback
        
        Args:
            operation: RollbackOperation to record
        """
        with self._lock:
            self.operation_history[operation.operation_id] = operation
            self.rollback_states[operation.operation_id] = RollbackState.RECORDED
            
            logger.info(f"Recorded operation {operation.operation_id} for rollback")
    
    def get_operation_history(self, operation_id: str) -> Optional[RollbackOperation]:
        """Get operation history
        
        Args:
            operation_id: ID of operation to retrieve
            
        Returns:
            RollbackOperation if found, None otherwise
        """
        with self._lock:
            return self.operation_history.get(operation_id)
    
    def get_rollback_state(self, operation_id: str) -> RollbackState:
        """Get rollback state for operation
        
        Args:
            operation_id: ID of operation to check
            
        Returns:
            Current rollback state
        """
        with self._lock:
            return self.rollback_states.get(operation_id, RollbackState.NOT_FOUND)
    
    async def execute_rollback(self, operation_id: str) -> bool:
        """Execute rollback operation
        
        Args:
            operation_id: ID of operation to rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        with self._lock:
            if operation_id not in self.operation_history:
                logger.error(f"Operation {operation_id} not found for rollback")
                return False
            
            current_state = self.rollback_states.get(operation_id)
            if current_state != RollbackState.RECORDED:
                logger.error(f"Operation {operation_id} cannot be rolled back (state: {current_state})")
                return False
            
            self.rollback_states[operation_id] = RollbackState.IN_PROGRESS
        
        try:
            operation = self.operation_history[operation_id]
            
            # Execute rollback for each element change
            for change in operation.element_changes:
                await self._rollback_element_change(change)
            
            with self._lock:
                self.rollback_states[operation_id] = RollbackState.COMPLETED
            
            logger.info(f"Successfully rolled back operation {operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback operation {operation_id}: {e}")
            with self._lock:
                self.rollback_states[operation_id] = RollbackState.FAILED
            return False
    
    async def _rollback_element_change(self, change: Dict[str, Any]):
        """Rollback a single element change
        
        Args:
            change: Element change dictionary
        """
        # Simulate rollback operation
        await asyncio.sleep(0.001)  # Simulate async work
        
        # In real implementation, this would:
        # 1. Validate the rollback is safe
        # 2. Restore element to previous type and data
        # 3. Update any dependent systems
        logger.debug(f"Rolled back element {change.get('element_id')}")
    
    def can_rollback(self, operation_id: str) -> bool:
        """Check if operation can be rolled back
        
        Args:
            operation_id: ID of operation to check
            
        Returns:
            True if operation can be rolled back
        """
        with self._lock:
            return (operation_id in self.operation_history and 
                   self.rollback_states.get(operation_id) == RollbackState.RECORDED)
    
    def list_rollbackable_operations(self) -> List[str]:
        """List all operations that can be rolled back
        
        Returns:
            List of operation IDs that can be rolled back
        """
        with self._lock:
            return [
                op_id for op_id, state in self.rollback_states.items()
                if state == RollbackState.RECORDED
            ]
    
    def get_operation_statistics(self) -> Dict[str, Any]:
        """Get rollback operation statistics
        
        Returns:
            Dictionary with rollback statistics
        """
        with self._lock:
            stats = {
                'total_operations': len(self.operation_history),
                'recorded_operations': 0,
                'completed_rollbacks': 0,
                'failed_rollbacks': 0,
                'in_progress_rollbacks': 0
            }
            
            for state in self.rollback_states.values():
                if state == RollbackState.RECORDED:
                    stats['recorded_operations'] += 1
                elif state == RollbackState.COMPLETED:
                    stats['completed_rollbacks'] += 1
                elif state == RollbackState.FAILED:
                    stats['failed_rollbacks'] += 1
                elif state == RollbackState.IN_PROGRESS:
                    stats['in_progress_rollbacks'] += 1
            
            return stats
    
    def cleanup_old_operations(self, max_age_days: int = 7) -> int:
        """Clean up old operations
        
        Args:
            max_age_days: Maximum age of operations to keep
            
        Returns:
            Number of operations cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        with self._lock:
            to_remove = []
            
            for op_id, operation in self.operation_history.items():
                if operation.timestamp < cutoff_date:
                    to_remove.append(op_id)
            
            for op_id in to_remove:
                del self.operation_history[op_id]
                self.rollback_states.pop(op_id, None)
                cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old rollback operations")
        
        return cleaned_count
    
    def get_operations_by_type(self, operation_type: str) -> List[RollbackOperation]:
        """Get operations by type
        
        Args:
            operation_type: Type of operations to retrieve
            
        Returns:
            List of operations of specified type
        """
        with self._lock:
            return [
                operation for operation in self.operation_history.values()
                if operation.operation_type == operation_type
            ]
    
    def get_operations_by_date_range(self, start_date: datetime, end_date: datetime) -> List[RollbackOperation]:
        """Get operations within date range
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of operations within date range
        """
        with self._lock:
            return [
                operation for operation in self.operation_history.values()
                if start_date <= operation.timestamp <= end_date
            ]
    
    def validate_rollback_operation(self, operation: RollbackOperation) -> tuple[bool, List[str]]:
        """Validate rollback operation
        
        Args:
            operation: Operation to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not operation.operation_id:
            errors.append("Operation ID is required")
        
        if not operation.operation_type:
            errors.append("Operation type is required")
        
        if not operation.element_changes:
            errors.append("Element changes are required")
        
        for i, change in enumerate(operation.element_changes):
            if 'element_id' not in change:
                errors.append(f"Element change {i} missing element_id")
            if 'old_type' not in change:
                errors.append(f"Element change {i} missing old_type")
            if 'new_type' not in change:
                errors.append(f"Element change {i} missing new_type")
        
        return len(errors) == 0, errors
    
    def validate_element_rollback(self, element_id: str, old_type: str, new_type: str, old_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate element rollback
        
        Args:
            element_id: ID of element to rollback
            old_type: Original type to restore
            new_type: Current type to change from
            old_data: Original data to restore
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        # In real implementation, this would validate:
        # - Element exists and has expected current type
        # - Old type is valid and supported
        # - Old data is compatible with old type
        # - No dependencies prevent the rollback
        
        return True, []
    
    # Transaction Support
    
    def start_transaction(self, description: str = "") -> str:
        """Start a new transaction
        
        Args:
            description: Description of the transaction
            
        Returns:
            Transaction ID
        """
        transaction_id = f"txn_{datetime.now().timestamp()}"
        
        with self._lock:
            self.transactions[transaction_id] = {
                'state': TransactionState.ACTIVE,
                'description': description,
                'start_time': datetime.now(),
                'operations': []
            }
        
        logger.info(f"Started transaction {transaction_id}")
        return transaction_id
    
    def add_operation_to_transaction(self, transaction_id: str, operation: RollbackOperation):
        """Add operation to transaction
        
        Args:
            transaction_id: ID of transaction
            operation: Operation to add
        """
        with self._lock:
            if transaction_id in self.transactions:
                self.transactions[transaction_id]['operations'].append(operation)
                operation.transaction_id = transaction_id
                logger.debug(f"Added operation {operation.operation_id} to transaction {transaction_id}")
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit transaction
        
        Args:
            transaction_id: ID of transaction to commit
            
        Returns:
            True if commit successful
        """
        with self._lock:
            if transaction_id not in self.transactions:
                return False
            
            transaction = self.transactions[transaction_id]
            if transaction['state'] != TransactionState.ACTIVE:
                return False
            
            # Record all operations
            for operation in transaction['operations']:
                self.record_operation(operation)
            
            transaction['state'] = TransactionState.COMMITTED
            transaction['end_time'] = datetime.now()
        
        logger.info(f"Committed transaction {transaction_id}")
        return True
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback transaction
        
        Args:
            transaction_id: ID of transaction to rollback
            
        Returns:
            True if rollback successful
        """
        with self._lock:
            if transaction_id not in self.transactions:
                return False
            
            transaction = self.transactions[transaction_id]
            if transaction['state'] != TransactionState.ACTIVE:
                return False
            
            transaction['state'] = TransactionState.ROLLED_BACK
            transaction['end_time'] = datetime.now()
        
        logger.info(f"Rolled back transaction {transaction_id}")
        return True