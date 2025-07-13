"""
Rollback management for optimistic updates.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
import copy

logger = logging.getLogger(__name__)


class RollbackStrategy(Enum):
    """Strategies for handling rollbacks."""
    IMMEDIATE = "immediate"
    BATCH = "batch"
    SMART = "smart"
    MANUAL = "manual"


@dataclass
class RollbackPoint:
    """Represents a point in time for rollback."""
    id: str
    timestamp: float
    state: Dict[str, Any]
    action: Any
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of rollback point in seconds."""
        return time.time() - self.timestamp


class RollbackManager:
    """
    Manages rollback operations for optimistic updates.
    
    Features:
    - Multiple rollback strategies
    - State snapshots for recovery
    - Batch rollback operations
    - Smart conflict resolution
    """
    
    def __init__(self, 
                 strategy: RollbackStrategy = RollbackStrategy.IMMEDIATE,
                 max_rollback_points: int = 100,
                 auto_cleanup_age: float = 300.0):
        """
        Initialize rollback manager.
        
        Args:
            strategy: Default rollback strategy
            max_rollback_points: Maximum rollback points to keep
            auto_cleanup_age: Age after which to auto-cleanup rollback points
        """
        self.strategy = strategy
        self.max_rollback_points = max_rollback_points
        self.auto_cleanup_age = auto_cleanup_age
        
        self._rollback_points: Dict[str, RollbackPoint] = {}
        self._rollback_queue: List[str] = []
        self._conflict_resolvers: Dict[str, Callable] = {}
        
        self._stats = {
            'rollbacks_created': 0,
            'rollbacks_executed': 0,
            'rollbacks_failed': 0,
            'conflicts_resolved': 0,
            'batch_rollbacks': 0,
        }
    
    def create_rollback_point(self, 
                             rollback_id: str,
                             state: Dict[str, Any],
                             action: Any,
                             description: str = "",
                             metadata: Optional[Dict[str, Any]] = None) -> RollbackPoint:
        """
        Create a rollback point.
        
        Args:
            rollback_id: Unique identifier for the rollback point
            state: State snapshot
            action: Action that was applied
            description: Description of the rollback point
            metadata: Additional metadata
            
        Returns:
            Created rollback point
        """
        # Deep copy state to prevent mutations
        state_snapshot = copy.deepcopy(state)
        
        rollback_point = RollbackPoint(
            id=rollback_id,
            timestamp=time.time(),
            state=state_snapshot,
            action=action,
            description=description,
            metadata=metadata or {}
        )
        
        self._rollback_points[rollback_id] = rollback_point
        self._stats['rollbacks_created'] += 1
        
        # Cleanup old rollback points
        self._cleanup_old_rollback_points()
        
        logger.debug(f"Created rollback point: {rollback_id}")
        return rollback_point
    
    def execute_rollback(self, 
                        store: Any,
                        rollback_id: str,
                        force: bool = False) -> bool:
        """
        Execute a rollback to a specific point.
        
        Args:
            store: Store to rollback
            rollback_id: ID of rollback point
            force: Force rollback even with conflicts
            
        Returns:
            True if rollback was successful
        """
        if rollback_id not in self._rollback_points:
            logger.error(f"Rollback point {rollback_id} not found")
            return False
        
        rollback_point = self._rollback_points[rollback_id]
        
        try:
            if self.strategy == RollbackStrategy.IMMEDIATE:
                return self._execute_immediate_rollback(store, rollback_point, force)
            elif self.strategy == RollbackStrategy.BATCH:
                return self._queue_for_batch_rollback(rollback_id)
            elif self.strategy == RollbackStrategy.SMART:
                return self._execute_smart_rollback(store, rollback_point, force)
            elif self.strategy == RollbackStrategy.MANUAL:
                logger.info(f"Manual rollback queued: {rollback_id}")
                return True
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            self._stats['rollbacks_failed'] += 1
            return False
    
    def _execute_immediate_rollback(self, 
                                   store: Any,
                                   rollback_point: RollbackPoint,
                                   force: bool) -> bool:
        """Execute immediate rollback."""
        current_state = store.get_state()
        
        # Check for conflicts
        if not force and self._has_conflicts(current_state, rollback_point.state):
            logger.warning(f"Conflicts detected for rollback {rollback_point.id}")
            
            # Try to resolve conflicts
            if self._resolve_conflicts(current_state, rollback_point.state):
                logger.info(f"Conflicts resolved for rollback {rollback_point.id}")
            else:
                logger.error(f"Cannot resolve conflicts for rollback {rollback_point.id}")
                return False
        
        # Apply rollback state
        self._apply_rollback_state(store, rollback_point.state)
        
        # Cleanup rollback point
        del self._rollback_points[rollback_point.id]
        self._stats['rollbacks_executed'] += 1
        
        logger.info(f"Executed immediate rollback: {rollback_point.id}")
        return True
    
    def _queue_for_batch_rollback(self, rollback_id: str) -> bool:
        """Queue rollback for batch processing."""
        if rollback_id not in self._rollback_queue:
            self._rollback_queue.append(rollback_id)
            logger.debug(f"Queued rollback for batch processing: {rollback_id}")
        return True
    
    def _execute_smart_rollback(self, 
                               store: Any,
                               rollback_point: RollbackPoint,
                               force: bool) -> bool:
        """Execute smart rollback with automatic conflict resolution."""
        current_state = store.get_state()
        
        # Analyze rollback safety
        safety_score = self._calculate_rollback_safety(current_state, rollback_point.state)
        
        if safety_score < 0.5 and not force:
            logger.warning(f"Low safety score ({safety_score}) for rollback {rollback_point.id}")
            return False
        
        # Merge states intelligently
        merged_state = self._merge_states_intelligently(current_state, rollback_point.state)
        
        # Apply merged state
        self._apply_rollback_state(store, merged_state)
        
        # Cleanup
        del self._rollback_points[rollback_point.id]
        self._stats['rollbacks_executed'] += 1
        
        logger.info(f"Executed smart rollback: {rollback_point.id}")
        return True
    
    def execute_batch_rollbacks(self, store: Any) -> Dict[str, bool]:
        """Execute all queued batch rollbacks."""
        if not self._rollback_queue:
            return {}
        
        results = {}
        successful_rollbacks = []
        
        # Sort by timestamp (oldest first)
        sorted_queue = sorted(
            self._rollback_queue,
            key=lambda rid: self._rollback_points[rid].timestamp
        )
        
        for rollback_id in sorted_queue:
            if rollback_id in self._rollback_points:
                success = self._execute_immediate_rollback(
                    store, 
                    self._rollback_points[rollback_id], 
                    force=False
                )
                results[rollback_id] = success
                if success:
                    successful_rollbacks.append(rollback_id)
        
        # Clear queue
        self._rollback_queue.clear()
        self._stats['batch_rollbacks'] += 1
        
        logger.info(f"Executed batch rollbacks: {len(successful_rollbacks)}/{len(sorted_queue)} successful")
        return results
    
    def _has_conflicts(self, current_state: Dict[str, Any], rollback_state: Dict[str, Any]) -> bool:
        """Check if there are conflicts between current and rollback state."""
        # Simple conflict detection - compare modified values
        return self._deep_diff(current_state, rollback_state) != {}
    
    def _resolve_conflicts(self, current_state: Dict[str, Any], rollback_state: Dict[str, Any]) -> bool:
        """Attempt to resolve conflicts between states."""
        try:
            conflicts = self._deep_diff(current_state, rollback_state)
            
            for path, (current_val, rollback_val) in conflicts.items():
                # Try registered conflict resolvers
                for pattern, resolver in self._conflict_resolvers.items():
                    if pattern in path:
                        resolved_value = resolver(current_val, rollback_val, path)
                        self._set_nested_value(rollback_state, path, resolved_value)
                        self._stats['conflicts_resolved'] += 1
                        break
                else:
                    # No resolver found, use rollback value
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return False
    
    def _calculate_rollback_safety(self, current_state: Dict[str, Any], rollback_state: Dict[str, Any]) -> float:
        """Calculate safety score for rollback (0.0 to 1.0)."""
        try:
            # Simple heuristic based on data overlap
            current_keys = set(self._flatten_dict(current_state).keys())
            rollback_keys = set(self._flatten_dict(rollback_state).keys())
            
            if not current_keys:
                return 1.0
            
            overlap = len(current_keys.intersection(rollback_keys))
            return overlap / len(current_keys)
            
        except Exception as e:
            logger.error(f"Safety calculation failed: {e}")
            return 0.0
    
    def _merge_states_intelligently(self, current_state: Dict[str, Any], rollback_state: Dict[str, Any]) -> Dict[str, Any]:
        """Merge current and rollback states intelligently."""
        # Start with rollback state
        merged = copy.deepcopy(rollback_state)
        
        # Preserve critical current state data
        critical_paths = ['ui', 'user_preferences', 'session']
        
        for path in critical_paths:
            current_value = self._get_nested_value(current_state, path)
            if current_value is not None:
                self._set_nested_value(merged, path, current_value)
        
        return merged
    
    def _apply_rollback_state(self, store: Any, state: Dict[str, Any]):
        """Apply rollback state to store."""
        # Create rollback action
        class RollbackAction:
            def __init__(self, state: Dict[str, Any]):
                self.type = "__ROLLBACK__"
                self.payload = state
                self.internal = True
        
        action = RollbackAction(state)
        
        # Apply state
        if hasattr(store, '_set_state'):
            store._set_state(state)
        elif hasattr(store, 'dispatch'):
            store.dispatch(action)
        
        # Notify subscribers
        if hasattr(store, '_notify_subscribers'):
            store._notify_subscribers(state)
    
    def _cleanup_old_rollback_points(self):
        """Clean up old rollback points."""
        current_time = time.time()
        to_remove = []
        
        for rollback_id, point in self._rollback_points.items():
            if point.age > self.auto_cleanup_age:
                to_remove.append(rollback_id)
        
        for rollback_id in to_remove:
            del self._rollback_points[rollback_id]
            logger.debug(f"Cleaned up old rollback point: {rollback_id}")
        
        # Maintain max rollback points
        if len(self._rollback_points) > self.max_rollback_points:
            # Remove oldest points
            sorted_points = sorted(
                self._rollback_points.items(),
                key=lambda x: x[1].timestamp
            )
            
            excess_count = len(self._rollback_points) - self.max_rollback_points
            for rollback_id, _ in sorted_points[:excess_count]:
                del self._rollback_points[rollback_id]
    
    def register_conflict_resolver(self, path_pattern: str, resolver: Callable):
        """Register a conflict resolver for specific paths."""
        self._conflict_resolvers[path_pattern] = resolver
        logger.debug(f"Registered conflict resolver for pattern: {path_pattern}")
    
    def get_rollback_points(self) -> List[RollbackPoint]:
        """Get all rollback points."""
        return list(self._rollback_points.values())
    
    def get_rollback_point(self, rollback_id: str) -> Optional[RollbackPoint]:
        """Get specific rollback point."""
        return self._rollback_points.get(rollback_id)
    
    def remove_rollback_point(self, rollback_id: str) -> bool:
        """Remove a rollback point."""
        if rollback_id in self._rollback_points:
            del self._rollback_points[rollback_id]
            logger.debug(f"Removed rollback point: {rollback_id}")
            return True
        return False
    
    def clear_rollback_points(self):
        """Clear all rollback points."""
        self._rollback_points.clear()
        self._rollback_queue.clear()
        logger.info("Cleared all rollback points")
    
    def get_rollback_stats(self) -> Dict[str, Any]:
        """Get rollback statistics."""
        return {
            **self._stats,
            'active_rollback_points': len(self._rollback_points),
            'queued_rollbacks': len(self._rollback_queue),
        }
    
    # Utility methods
    def _deep_diff(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, tuple]:
        """Find differences between two dictionaries."""
        diff = {}
        
        flat1 = self._flatten_dict(dict1)
        flat2 = self._flatten_dict(dict2)
        
        all_keys = set(flat1.keys()) | set(flat2.keys())
        
        for key in all_keys:
            val1 = flat1.get(key)
            val2 = flat2.get(key)
            
            if val1 != val2:
                diff[key] = (val1, val2)
        
        return diff
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get value from nested object using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any):
        """Set value in nested object using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value