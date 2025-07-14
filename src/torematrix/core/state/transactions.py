"""
Transaction support for atomic state operations.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import copy

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Status of a transaction."""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Transaction:
    """Represents a state transaction."""
    id: str
    actions: List[Any] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    committed_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    initial_state: Optional[Dict[str, Any]] = None
    final_state: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get transaction duration."""
        end_time = self.committed_at or self.rolled_back_at or time.time()
        return end_time - self.created_at
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self.status == TransactionStatus.PENDING
    
    @property
    def is_completed(self) -> bool:
        """Check if transaction is completed."""
        return self.status in [TransactionStatus.COMMITTED, TransactionStatus.ROLLED_BACK]


class TransactionMiddleware:
    """
    Middleware for handling transactional state operations.
    
    Features:
    - Atomic action groups
    - Automatic rollback on failure
    - Nested transaction support
    - Transaction isolation levels
    """
    
    def __init__(self, 
                 auto_commit: bool = True,
                 max_transaction_size: int = 100,
                 transaction_timeout: float = 30.0):
        """
        Initialize transaction middleware.
        
        Args:
            auto_commit: Whether to auto-commit single actions
            max_transaction_size: Maximum actions per transaction
            transaction_timeout: Transaction timeout in seconds
        """
        self.auto_commit = auto_commit
        self.max_transaction_size = max_transaction_size
        self.transaction_timeout = transaction_timeout
        
        self._active_transactions: Dict[str, Transaction] = {}
        self._transaction_stack: List[str] = []  # For nested transactions
        self._transaction_states: Dict[str, Dict[str, Any]] = {}
        
        self._stats = {
            'transactions_created': 0,
            'transactions_committed': 0,
            'transactions_rolled_back': 0,
            'nested_transactions': 0,
            'avg_transaction_time': 0,
        }
    
    def __call__(self, store):
        """Create transaction middleware function."""
        def middleware(next_dispatch):
            def dispatch(action):
                # Check if action is transactional
                if self._is_transactional_action(action):
                    return self._handle_transactional_action(store, action, next_dispatch)
                else:
                    return next_dispatch(action)
            
            return dispatch
        return middleware
    
    def _is_transactional_action(self, action) -> bool:
        """Check if action should be handled transactionally."""
        # Check for transaction markers
        if hasattr(action, 'transactional') and action.transactional:
            return True
        
        if hasattr(action, 'type'):
            # Transaction control actions
            if action.type in ['BEGIN_TRANSACTION', 'COMMIT_TRANSACTION', 'ROLLBACK_TRANSACTION']:
                return True
            
            # Actions that should be transactional by default
            transactional_patterns = ['BATCH_', 'MULTI_', 'ATOMIC_']
            return any(action.type.startswith(pattern) for pattern in transactional_patterns)
        
        return False
    
    def _handle_transactional_action(self, store, action, next_dispatch):
        """Handle a transactional action."""
        action_type = getattr(action, 'type', '')
        
        if action_type == 'BEGIN_TRANSACTION':
            return self._begin_transaction(store, action)
        elif action_type == 'COMMIT_TRANSACTION':
            return self._commit_transaction(store, action)
        elif action_type == 'ROLLBACK_TRANSACTION':
            return self._rollback_transaction(store, action)
        else:
            return self._execute_in_transaction(store, action, next_dispatch)
    
    def _begin_transaction(self, store, action) -> str:
        """Begin a new transaction."""
        transaction_id = getattr(action, 'transaction_id', None) or str(uuid.uuid4())
        
        # Check if transaction already exists
        if transaction_id in self._active_transactions:
            logger.warning(f"Transaction {transaction_id} already exists")
            return transaction_id
        
        # Create new transaction
        transaction = Transaction(
            id=transaction_id,
            initial_state=copy.deepcopy(store.get_state()),
            metadata=getattr(action, 'metadata', {})
        )
        
        self._active_transactions[transaction_id] = transaction
        self._transaction_stack.append(transaction_id)
        
        # Store initial state
        self._transaction_states[transaction_id] = transaction.initial_state
        
        self._stats['transactions_created'] += 1
        if len(self._transaction_stack) > 1:
            self._stats['nested_transactions'] += 1
        
        logger.info(f"Started transaction: {transaction_id}")
        return transaction_id
    
    def _commit_transaction(self, store, action) -> bool:
        """Commit a transaction."""
        transaction_id = getattr(action, 'transaction_id', None)
        
        if transaction_id is None:
            # Commit latest transaction
            if not self._transaction_stack:
                logger.warning("No active transaction to commit")
                return False
            transaction_id = self._transaction_stack[-1]
        
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self._active_transactions[transaction_id]
        
        try:
            # Mark as committed
            transaction.status = TransactionStatus.COMMITTED
            transaction.committed_at = time.time()
            transaction.final_state = copy.deepcopy(store.get_state())
            
            # Clean up
            self._cleanup_transaction(transaction_id)
            
            # Update stats
            self._stats['transactions_committed'] += 1
            self._update_avg_transaction_time(transaction.duration)
            
            logger.info(f"Committed transaction: {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit transaction {transaction_id}: {e}")
            transaction.error = e
            transaction.status = TransactionStatus.FAILED
            return False
    
    def _rollback_transaction(self, store, action) -> bool:
        """Rollback a transaction."""
        transaction_id = getattr(action, 'transaction_id', None)
        
        if transaction_id is None:
            # Rollback latest transaction
            if not self._transaction_stack:
                logger.warning("No active transaction to rollback")
                return False
            transaction_id = self._transaction_stack[-1]
        
        if transaction_id not in self._active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self._active_transactions[transaction_id]
        
        try:
            # Restore initial state
            if transaction.initial_state:
                self._restore_state(store, transaction.initial_state)
            
            # Mark as rolled back
            transaction.status = TransactionStatus.ROLLED_BACK
            transaction.rolled_back_at = time.time()
            
            # Clean up
            self._cleanup_transaction(transaction_id)
            
            # Update stats
            self._stats['transactions_rolled_back'] += 1
            self._update_avg_transaction_time(transaction.duration)
            
            logger.info(f"Rolled back transaction: {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback transaction {transaction_id}: {e}")
            transaction.error = e
            transaction.status = TransactionStatus.FAILED
            return False
    
    def _execute_in_transaction(self, store, action, next_dispatch):
        """Execute action within a transaction context."""
        # If no active transaction and auto_commit is enabled, create one
        if not self._transaction_stack and self.auto_commit:
            transaction_id = self._begin_transaction(store, type('BeginAction', (), {
                'type': 'BEGIN_TRANSACTION',
                'transaction_id': str(uuid.uuid4()),
                'metadata': {'auto_created': True}
            })())
        
        # Get current transaction
        if self._transaction_stack:
            transaction_id = self._transaction_stack[-1]
            transaction = self._active_transactions[transaction_id]
            
            # Check transaction limits
            if len(transaction.actions) >= self.max_transaction_size:
                logger.error(f"Transaction {transaction_id} exceeded max size")
                self._rollback_transaction(store, type('RollbackAction', (), {
                    'type': 'ROLLBACK_TRANSACTION',
                    'transaction_id': transaction_id
                })())
                raise RuntimeError(f"Transaction {transaction_id} exceeded maximum size")
            
            # Check timeout
            if transaction.duration > self.transaction_timeout:
                logger.error(f"Transaction {transaction_id} timed out")
                self._rollback_transaction(store, type('RollbackAction', (), {
                    'type': 'ROLLBACK_TRANSACTION',
                    'transaction_id': transaction_id
                })())
                raise RuntimeError(f"Transaction {transaction_id} timed out")
            
            # Add action to transaction
            transaction.actions.append(action)
        
        try:
            # Execute action
            result = next_dispatch(action)
            
            # Auto-commit if enabled and this was an auto-created transaction
            if (self.auto_commit and 
                self._transaction_stack and 
                self._active_transactions[self._transaction_stack[-1]].metadata.get('auto_created')):
                self._commit_transaction(store, type('CommitAction', (), {
                    'type': 'COMMIT_TRANSACTION',
                    'transaction_id': self._transaction_stack[-1]
                })())
            
            return result
            
        except Exception as e:
            # Rollback on error
            if self._transaction_stack:
                transaction_id = self._transaction_stack[-1]
                logger.error(f"Action failed in transaction {transaction_id}: {e}")
                self._rollback_transaction(store, type('RollbackAction', (), {
                    'type': 'ROLLBACK_TRANSACTION',
                    'transaction_id': transaction_id
                })())
            raise e
    
    def _restore_state(self, store, state: Dict[str, Any]):
        """Restore store to a specific state."""
        if hasattr(store, '_set_state'):
            store._set_state(state)
        else:
            # Create restore action
            class RestoreStateAction:
                def __init__(self, state: Dict[str, Any]):
                    self.type = "__RESTORE_STATE__"
                    self.payload = state
                    self.internal = True
            
            action = RestoreStateAction(state)
            store.dispatch(action)
        
        # Notify subscribers
        if hasattr(store, '_notify_subscribers'):
            store._notify_subscribers(state)
    
    def _cleanup_transaction(self, transaction_id: str):
        """Clean up transaction resources."""
        # Remove from active transactions
        if transaction_id in self._active_transactions:
            del self._active_transactions[transaction_id]
        
        # Remove from stack
        if transaction_id in self._transaction_stack:
            self._transaction_stack.remove(transaction_id)
        
        # Remove stored state
        if transaction_id in self._transaction_states:
            del self._transaction_states[transaction_id]
    
    def _update_avg_transaction_time(self, duration: float):
        """Update average transaction time statistic."""
        current_avg = self._stats['avg_transaction_time']
        total_transactions = self._stats['transactions_committed'] + self._stats['transactions_rolled_back']
        
        if total_transactions == 1:
            self._stats['avg_transaction_time'] = duration
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats['avg_transaction_time'] = alpha * duration + (1 - alpha) * current_avg
    
    @contextmanager
    def transaction(self, store, transaction_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for transactions.
        
        Args:
            store: Store instance
            transaction_id: Optional transaction ID
            metadata: Optional metadata
            
        Yields:
            Transaction ID
        """
        transaction_id = transaction_id or str(uuid.uuid4())
        
        # Begin transaction
        begin_action = type('BeginAction', (), {
            'type': 'BEGIN_TRANSACTION',
            'transaction_id': transaction_id,
            'metadata': metadata or {}
        })()
        
        self._begin_transaction(store, begin_action)
        
        try:
            yield transaction_id
            
            # Commit on successful completion
            commit_action = type('CommitAction', (), {
                'type': 'COMMIT_TRANSACTION',
                'transaction_id': transaction_id
            })()
            
            self._commit_transaction(store, commit_action)
            
        except Exception as e:
            # Rollback on error
            rollback_action = type('RollbackAction', (), {
                'type': 'ROLLBACK_TRANSACTION',
                'transaction_id': transaction_id
            })()
            
            self._rollback_transaction(store, rollback_action)
            raise e
    
    def get_active_transactions(self) -> List[Transaction]:
        """Get list of active transactions."""
        return list(self._active_transactions.values())
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get specific transaction."""
        return self._active_transactions.get(transaction_id)
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        return {
            **self._stats,
            'active_transactions': len(self._active_transactions),
            'nested_level': len(self._transaction_stack),
        }
    
    def force_rollback_all(self, store) -> int:
        """Force rollback all active transactions."""
        count = 0
        
        # Rollback in reverse order (nested first)
        for transaction_id in reversed(self._transaction_stack):
            if transaction_id in self._active_transactions:
                rollback_action = type('RollbackAction', (), {
                    'type': 'ROLLBACK_TRANSACTION',
                    'transaction_id': transaction_id
                })()
                
                if self._rollback_transaction(store, rollback_action):
                    count += 1
        
        logger.info(f"Force rolled back {count} transactions")
        return count
    
    def clear_stats(self):
        """Clear transaction statistics."""
        self._stats = {
            'transactions_created': 0,
            'transactions_committed': 0,
            'transactions_rolled_back': 0,
            'nested_transactions': 0,
            'avg_transaction_time': 0,
        }