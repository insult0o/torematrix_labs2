"""
Optimistic updates implementation for immediate UI feedback.
"""

from typing import Dict, Any, Optional, Callable, List
import asyncio
import uuid
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from .rollback import RollbackManager

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """Status of an optimistic update."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class OptimisticUpdate:
    """Represents an optimistic update operation."""
    id: str
    action: Any
    optimistic_state: Dict[str, Any]
    original_state: Dict[str, Any]
    status: UpdateStatus = UpdateStatus.PENDING
    created_at: float = field(default_factory=time.time)
    confirmed_at: Optional[float] = None
    failed_at: Optional[float] = None
    error: Optional[Exception] = None
    
    @property
    def duration(self) -> float:
        """Get duration of the update."""
        end_time = self.confirmed_at or self.failed_at or time.time()
        return end_time - self.created_at
    
    @property
    def is_pending(self) -> bool:
        """Check if update is still pending."""
        return self.status == UpdateStatus.PENDING
    
    @property
    def is_completed(self) -> bool:
        """Check if update is completed (confirmed or failed)."""
        return self.status in [UpdateStatus.CONFIRMED, UpdateStatus.FAILED, UpdateStatus.ROLLED_BACK]


class OptimisticMiddleware:
    """
    Middleware for handling optimistic updates with automatic rollback.
    
    Features:
    - Immediate UI updates for async operations
    - Automatic rollback on failure
    - Conflict resolution for concurrent updates
    - Comprehensive tracking and metrics
    """
    
    def __init__(self, 
                 timeout: float = 30.0,
                 max_pending: int = 100,
                 auto_rollback: bool = True):
        """
        Initialize optimistic updates middleware.
        
        Args:
            timeout: Timeout for pending updates in seconds
            max_pending: Maximum number of pending updates
            auto_rollback: Whether to auto-rollback failed updates
        """
        self.timeout = timeout
        self.max_pending = max_pending
        self.auto_rollback = auto_rollback
        
        self._pending_updates: Dict[str, OptimisticUpdate] = {}
        self._rollback_manager = RollbackManager()
        self._predictor = OptimisticPredictor()
        
        self._stats = {
            'total_updates': 0,
            'confirmed_updates': 0,
            'failed_updates': 0,
            'rollbacks': 0,
            'timeouts': 0,
            'avg_confirmation_time': 0,
        }
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_pending_updates())
    
    def __call__(self, store):
        """Create optimistic middleware function."""
        def middleware(next_dispatch):
            async def dispatch(action):
                # Check if action should be optimistic
                if self._should_apply_optimistic(action):
                    return await self._handle_optimistic_action(store, action, next_dispatch)
                else:
                    return next_dispatch(action)
            
            return dispatch
        return middleware
    
    def _should_apply_optimistic(self, action) -> bool:
        """Determine if action should be handled optimistically."""
        # Check for optimistic flag
        if hasattr(action, 'optimistic') and action.optimistic:
            return True
        
        # Check for async operations
        if hasattr(action, 'async_operation') and action.async_operation:
            return True
        
        # Check action type patterns
        optimistic_patterns = ['UPDATE_', 'CREATE_', 'DELETE_', 'SAVE_']
        if hasattr(action, 'type'):
            return any(action.type.startswith(pattern) for pattern in optimistic_patterns)
        
        return False
    
    async def _handle_optimistic_action(self, store, action, next_dispatch):
        """Handle an action optimistically."""
        # Check pending updates limit
        if len(self._pending_updates) >= self.max_pending:
            logger.warning(f"Max pending updates reached ({self.max_pending})")
            # Process normally without optimism
            return next_dispatch(action)
        
        # Generate update ID
        update_id = str(uuid.uuid4())
        
        # Get current state
        current_state = store.get_state()
        
        # Predict optimistic state
        optimistic_state = self._predictor.predict_state(current_state, action)
        
        # Create optimistic update
        update = OptimisticUpdate(
            id=update_id,
            action=action,
            optimistic_state=optimistic_state,
            original_state=current_state
        )
        
        # Track update
        self._pending_updates[update_id] = update
        self._stats['total_updates'] += 1
        
        # Apply optimistic state immediately
        self._apply_optimistic_state(store, optimistic_state)
        
        try:
            # Perform actual async operation
            result = await self._perform_async_operation(action, next_dispatch)
            
            # Confirm update
            await self._confirm_update(store, update_id, result)
            
            return result
            
        except Exception as e:
            # Handle failure
            await self._handle_update_failure(store, update_id, e)
            raise e
    
    def _apply_optimistic_state(self, store, optimistic_state: Dict[str, Any]):
        """Apply optimistic state to store."""
        # Create internal action to update state
        class OptimisticStateAction:
            def __init__(self, state: Dict[str, Any]):
                self.type = "__OPTIMISTIC_UPDATE__"
                self.payload = state
                self.internal = True
        
        action = OptimisticStateAction(optimistic_state)
        
        # Notify subscribers with optimistic state
        if hasattr(store, '_notify_subscribers'):
            store._notify_subscribers(optimistic_state)
        
        logger.debug("Applied optimistic state")
    
    async def _perform_async_operation(self, action, next_dispatch):
        """Perform the actual async operation."""
        # If action has async_operation method, call it
        if hasattr(action, 'async_operation'):
            return await action.async_operation()
        
        # If action has async handler, use it
        if hasattr(action, 'async_handler'):
            return await action.async_handler()
        
        # Otherwise, dispatch normally (might be sync)
        return next_dispatch(action)
    
    async def _confirm_update(self, store, update_id: str, result: Any):
        """Confirm an optimistic update."""
        if update_id not in self._pending_updates:
            logger.warning(f"Update {update_id} not found for confirmation")
            return
        
        update = self._pending_updates[update_id]
        update.status = UpdateStatus.CONFIRMED
        update.confirmed_at = time.time()
        
        # Update stats
        self._stats['confirmed_updates'] += 1
        self._update_avg_confirmation_time(update.duration)
        
        # Clean up
        del self._pending_updates[update_id]
        
        logger.debug(f"Confirmed optimistic update {update_id}")
    
    async def _handle_update_failure(self, store, update_id: str, error: Exception):
        """Handle failure of an optimistic update."""
        if update_id not in self._pending_updates:
            logger.warning(f"Update {update_id} not found for failure handling")
            return
        
        update = self._pending_updates[update_id]
        update.status = UpdateStatus.FAILED
        update.failed_at = time.time()
        update.error = error
        
        # Update stats
        self._stats['failed_updates'] += 1
        
        if self.auto_rollback:
            await self._rollback_update(store, update_id)
        
        logger.error(f"Optimistic update {update_id} failed: {error}")
    
    async def _rollback_update(self, store, update_id: str):
        """Rollback a failed optimistic update."""
        if update_id not in self._pending_updates:
            return
        
        update = self._pending_updates[update_id]
        
        try:
            # Restore original state
            self._apply_optimistic_state(store, update.original_state)
            
            update.status = UpdateStatus.ROLLED_BACK
            self._stats['rollbacks'] += 1
            
            logger.info(f"Rolled back optimistic update {update_id}")
            
        except Exception as e:
            logger.error(f"Rollback failed for update {update_id}: {e}")
        finally:
            # Clean up
            if update_id in self._pending_updates:
                del self._pending_updates[update_id]
    
    async def _cleanup_pending_updates(self):
        """Background task to clean up timed-out updates."""
        while True:
            try:
                current_time = time.time()
                timed_out_updates = []
                
                for update_id, update in self._pending_updates.items():
                    if current_time - update.created_at > self.timeout:
                        timed_out_updates.append(update_id)
                
                for update_id in timed_out_updates:
                    logger.warning(f"Optimistic update {update_id} timed out")
                    await self._handle_update_failure(
                        None,  # Store not available in cleanup
                        update_id,
                        TimeoutError(f"Update timed out after {self.timeout}s")
                    )
                    self._stats['timeouts'] += 1
                
                # Sleep before next cleanup
                await asyncio.sleep(min(self.timeout / 4, 5.0))
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(5.0)
    
    def _update_avg_confirmation_time(self, duration: float):
        """Update average confirmation time statistic."""
        current_avg = self._stats['avg_confirmation_time']
        confirmed_count = self._stats['confirmed_updates']
        
        if confirmed_count == 1:
            self._stats['avg_confirmation_time'] = duration
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats['avg_confirmation_time'] = alpha * duration + (1 - alpha) * current_avg
    
    def get_pending_updates(self) -> List[OptimisticUpdate]:
        """Get list of pending updates."""
        return list(self._pending_updates.values())
    
    def get_update_status(self, update_id: str) -> Optional[UpdateStatus]:
        """Get status of a specific update."""
        update = self._pending_updates.get(update_id)
        return update.status if update else None
    
    def force_confirm_update(self, update_id: str):
        """Force confirm a pending update."""
        if update_id in self._pending_updates:
            update = self._pending_updates[update_id]
            update.status = UpdateStatus.CONFIRMED
            update.confirmed_at = time.time()
            del self._pending_updates[update_id]
            self._stats['confirmed_updates'] += 1
            logger.info(f"Force confirmed update {update_id}")
    
    def force_rollback_update(self, store, update_id: str):
        """Force rollback a pending update."""
        if update_id in self._pending_updates:
            asyncio.create_task(self._rollback_update(store, update_id))
    
    def get_optimistic_stats(self) -> Dict[str, Any]:
        """Get optimistic updates statistics."""
        return {
            **self._stats,
            'pending_count': len(self._pending_updates),
            'success_rate': (
                self._stats['confirmed_updates'] / max(self._stats['total_updates'], 1)
            ),
            'failure_rate': (
                self._stats['failed_updates'] / max(self._stats['total_updates'], 1)
            ),
        }
    
    def clear_stats(self):
        """Clear statistics."""
        self._stats = {
            'total_updates': 0,
            'confirmed_updates': 0,
            'failed_updates': 0,
            'rollbacks': 0,
            'timeouts': 0,
            'avg_confirmation_time': 0,
        }
    
    def shutdown(self):
        """Shutdown the middleware and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


class OptimisticPredictor:
    """Predicts optimistic state changes based on actions."""
    
    def predict_state(self, current_state: Dict[str, Any], action: Any) -> Dict[str, Any]:
        """
        Predict the state after applying an action.
        
        Args:
            current_state: Current state
            action: Action to apply
            
        Returns:
            Predicted state
        """
        # Start with current state
        predicted_state = dict(current_state)
        
        # Apply prediction based on action type
        if hasattr(action, 'type'):
            action_type = action.type
            
            if action_type.startswith('UPDATE_'):
                predicted_state = self._predict_update(predicted_state, action)
            elif action_type.startswith('CREATE_'):
                predicted_state = self._predict_create(predicted_state, action)
            elif action_type.startswith('DELETE_'):
                predicted_state = self._predict_delete(predicted_state, action)
            elif hasattr(action, 'optimistic_state'):
                # Action provides its own optimistic state
                predicted_state.update(action.optimistic_state)
        
        return predicted_state
    
    def _predict_update(self, state: Dict[str, Any], action: Any) -> Dict[str, Any]:
        """Predict state for update actions."""
        if hasattr(action, 'payload'):
            if 'path' in action.payload and 'value' in action.payload:
                # Path-based update
                path = action.payload['path']
                value = action.payload['value']
                return self._set_nested_value(state, path, value)
            else:
                # Direct state update
                state.update(action.payload)
        return state
    
    def _predict_create(self, state: Dict[str, Any], action: Any) -> Dict[str, Any]:
        """Predict state for create actions."""
        if hasattr(action, 'payload'):
            # Add new item to appropriate collection
            if 'collection' in action.payload and 'item' in action.payload:
                collection = action.payload['collection']
                item = action.payload['item']
                
                if collection not in state:
                    state[collection] = []
                
                if isinstance(state[collection], list):
                    state[collection].append(item)
                elif isinstance(state[collection], dict):
                    item_id = item.get('id', str(uuid.uuid4()))
                    state[collection][item_id] = item
        return state
    
    def _predict_delete(self, state: Dict[str, Any], action: Any) -> Dict[str, Any]:
        """Predict state for delete actions."""
        if hasattr(action, 'payload'):
            if 'collection' in action.payload and 'id' in action.payload:
                collection = action.payload['collection']
                item_id = action.payload['id']
                
                if collection in state:
                    if isinstance(state[collection], list):
                        state[collection] = [
                            item for item in state[collection]
                            if item.get('id') != item_id
                        ]
                    elif isinstance(state[collection], dict):
                        state[collection].pop(item_id, None)
        return state
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
        """Set value in nested object using dot notation."""
        keys = path.split('.')
        current = obj
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set final value
        current[keys[-1]] = value
        return obj