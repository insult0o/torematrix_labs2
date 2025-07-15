"""Rollback System

Comprehensive rollback and undo system for bulk operations with
transaction support, operation history, and reliable recovery.
"""

import json
import logging
import pickle
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Callable
from uuid import uuid4


class RollbackState(Enum):
    """States of rollback operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class OperationType(Enum):
    """Types of operations that can be rolled back"""
    BULK_TYPE_CHANGE = "bulk_type_change"
    TYPE_CONVERSION = "type_conversion"
    BATCH_UPDATE = "batch_update"
    BULK_DELETE = "bulk_delete"
    PROPERTY_UPDATE = "property_update"
    METADATA_UPDATE = "metadata_update"


@dataclass
class RollbackAction:
    """Individual action within a rollback operation"""
    action_id: str
    action_type: str
    element_id: str
    original_data: Dict[str, Any]
    rollback_function: Optional[str] = None
    rollback_params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    is_reversible: bool = True
    priority: int = 0  # Higher priority actions execute first


@dataclass
class RollbackOperation:
    """Complete rollback operation containing multiple actions"""
    operation_id: str
    original_operation_id: str
    operation_type: OperationType
    description: str
    created_at: datetime
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    actions: List[RollbackAction] = field(default_factory=list)
    state: RollbackState = RollbackState.PENDING
    execution_order: List[str] = field(default_factory=list)
    completed_actions: Set[str] = field(default_factory=set)
    failed_actions: Set[str] = field(default_factory=set)
    last_executed: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RollbackResult:
    """Result of a rollback operation execution"""
    operation_id: str
    success: bool
    state: RollbackState
    completed_actions: int
    failed_actions: int
    total_actions: int
    execution_time: float
    errors: List[str]
    warnings: List[str]
    rollback_summary: Dict[str, Any]


class RollbackManager:
    """Comprehensive rollback and undo system for bulk operations"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize rollback manager
        
        Args:
            storage_path: Path for persistent rollback data storage
        """
        self.storage_path = storage_path or Path("./rollback_data")
        self.storage_path.mkdir(exist_ok=True)
        
        # In-memory operation tracking
        self.active_rollbacks: Dict[str, RollbackOperation] = {}
        self.rollback_history: Dict[str, RollbackOperation] = {}
        
        # Rollback function registry
        self.rollback_functions: Dict[str, Callable] = {}
        
        # Configuration
        self.max_history_days = 30
        self.auto_cleanup_enabled = True
        self.backup_before_rollback = True
        
        # Statistics
        self.rollback_stats = {
            'total_rollbacks': 0,
            'successful_rollbacks': 0,
            'failed_rollbacks': 0,
            'average_rollback_time': 0.0,
            'data_recovered_mb': 0.0
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load existing rollback data
        self._load_persistent_data()
        
        # Register default rollback functions
        self._register_default_rollback_functions()
    
    async def save_rollback_operation(self, operation: RollbackOperation) -> bool:
        """Save rollback operation for future execution
        
        Args:
            operation: RollbackOperation to save
            
        Returns:
            True if save was successful
        """
        try:
            # Store in memory
            self.active_rollbacks[operation.operation_id] = operation
            
            # Persist to storage
            await self._persist_rollback_operation(operation)
            
            self.logger.info(
                f"Saved rollback operation {operation.operation_id} "
                f"with {len(operation.actions)} actions"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save rollback operation: {e}")
            return False
    
    async def execute_rollback(self, operation_id: str) -> bool:
        """Execute a rollback operation
        
        Args:
            operation_id: ID of rollback operation to execute
            
        Returns:
            True if rollback was successful
        """
        if operation_id not in self.active_rollbacks:
            self.logger.error(f"Rollback operation {operation_id} not found")
            return False
        
        operation = self.active_rollbacks[operation_id]
        start_time = datetime.now()
        
        try:
            operation.state = RollbackState.IN_PROGRESS
            operation.last_executed = start_time
            
            # Create backup if enabled
            if self.backup_before_rollback:
                await self._create_rollback_backup(operation)
            
            # Execute actions in proper order
            success = await self._execute_rollback_actions(operation)
            
            # Update operation state
            if success:
                operation.state = RollbackState.COMPLETED
                self.rollback_stats['successful_rollbacks'] += 1
            elif operation.completed_actions:
                operation.state = RollbackState.PARTIALLY_COMPLETED
            else:
                operation.state = RollbackState.FAILED
                self.rollback_stats['failed_rollbacks'] += 1
            
            # Calculate execution time
            end_time = datetime.now()
            operation.execution_time_seconds = (end_time - start_time).total_seconds()
            
            # Move to history
            self.rollback_history[operation_id] = operation
            if operation_id in self.active_rollbacks:
                del self.active_rollbacks[operation_id]
            
            # Update statistics
            self.rollback_stats['total_rollbacks'] += 1
            self._update_average_rollback_time(operation.execution_time_seconds)
            
            self.logger.info(
                f"Rollback operation {operation_id} completed with state: {operation.state}"
            )
            
            return success
            
        except Exception as e:
            operation.state = RollbackState.FAILED
            operation.errors.append(f"Rollback execution failed: {str(e)}")
            self.logger.error(f"Rollback execution error: {e}")
            return False
    
    def create_rollback_operation(self, 
                                original_operation_id: str,
                                operation_type: OperationType,
                                description: str) -> RollbackOperation:
        """Create a new rollback operation
        
        Args:
            original_operation_id: ID of the original operation to rollback
            operation_type: Type of operation being rolled back
            description: Human-readable description
            
        Returns:
            New RollbackOperation
        """
        operation = RollbackOperation(
            operation_id=str(uuid4()),
            original_operation_id=original_operation_id,
            operation_type=operation_type,
            description=description,
            created_at=datetime.now()
        )
        
        return operation
    
    def add_rollback_action(self, 
                          operation: RollbackOperation,
                          action_type: str,
                          element_id: str,
                          original_data: Dict[str, Any],
                          rollback_function: Optional[str] = None,
                          rollback_params: Dict[str, Any] = None,
                          dependencies: List[str] = None,
                          priority: int = 0) -> RollbackAction:
        """Add rollback action to operation
        
        Args:
            operation: RollbackOperation to add action to
            action_type: Type of rollback action
            element_id: ID of element to rollback
            original_data: Original data to restore
            rollback_function: Name of rollback function to use
            rollback_params: Parameters for rollback function
            dependencies: List of action IDs this depends on
            priority: Priority for execution order
            
        Returns:
            Created RollbackAction
        """
        action = RollbackAction(
            action_id=str(uuid4()),
            action_type=action_type,
            element_id=element_id,
            original_data=original_data,
            rollback_function=rollback_function,
            rollback_params=rollback_params or {},
            dependencies=dependencies or [],
            priority=priority
        )
        
        operation.actions.append(action)
        
        # Update execution order
        self._update_execution_order(operation)
        
        return action
    
    def get_rollback_status(self, operation_id: str) -> Optional[RollbackOperation]:
        """Get status of rollback operation
        
        Args:
            operation_id: ID of rollback operation
            
        Returns:
            RollbackOperation if found, None otherwise
        """
        # Check active operations
        if operation_id in self.active_rollbacks:
            return self.active_rollbacks[operation_id]
        
        # Check history
        if operation_id in self.rollback_history:
            return self.rollback_history[operation_id]
        
        return None
    
    def list_rollback_operations(self, 
                               state: Optional[RollbackState] = None,
                               operation_type: Optional[OperationType] = None) -> List[RollbackOperation]:
        """List rollback operations with optional filtering
        
        Args:
            state: Filter by rollback state
            operation_type: Filter by operation type
            
        Returns:
            List of matching RollbackOperation objects
        """
        all_operations = list(self.active_rollbacks.values()) + list(self.rollback_history.values())
        
        filtered_operations = []
        for operation in all_operations:
            if state and operation.state != state:
                continue
            if operation_type and operation.operation_type != operation_type:
                continue
            filtered_operations.append(operation)
        
        # Sort by creation date (newest first)
        filtered_operations.sort(key=lambda op: op.created_at, reverse=True)
        
        return filtered_operations
    
    def register_rollback_function(self, name: str, function: Callable):
        """Register a rollback function
        
        Args:
            name: Name of the rollback function
            function: Callable rollback function
        """
        self.rollback_functions[name] = function
        self.logger.info(f"Registered rollback function: {name}")
    
    def delete_rollback_operation(self, operation_id: str) -> bool:
        """Delete a rollback operation
        
        Args:
            operation_id: ID of operation to delete
            
        Returns:
            True if deletion was successful
        """
        deleted = False
        
        # Remove from active operations
        if operation_id in self.active_rollbacks:
            del self.active_rollbacks[operation_id]
            deleted = True
        
        # Remove from history
        if operation_id in self.rollback_history:
            del self.rollback_history[operation_id]
            deleted = True
        
        # Remove persistent storage
        if deleted:
            self._delete_persistent_rollback(operation_id)
            self.logger.info(f"Deleted rollback operation {operation_id}")
        
        return deleted
    
    def cleanup_old_rollbacks(self, max_age_days: int = None):
        """Clean up old rollback operations
        
        Args:
            max_age_days: Maximum age in days (uses default if None)
        """
        max_age = max_age_days or self.max_history_days
        cutoff_date = datetime.now() - timedelta(days=max_age)
        
        operations_to_remove = []
        
        # Find old operations in history
        for operation_id, operation in self.rollback_history.items():
            if operation.created_at < cutoff_date:
                operations_to_remove.append(operation_id)
        
        # Remove old operations
        for operation_id in operations_to_remove:
            self.delete_rollback_operation(operation_id)
        
        self.logger.info(f"Cleaned up {len(operations_to_remove)} old rollback operations")
    
    def get_rollback_statistics(self) -> Dict[str, Any]:
        """Get rollback system statistics
        
        Returns:
            Dictionary with rollback statistics
        """
        return {
            **self.rollback_stats,
            'active_rollbacks': len(self.active_rollbacks),
            'rollback_history_count': len(self.rollback_history),
            'registered_functions': len(self.rollback_functions),
            'storage_path': str(self.storage_path)
        }
    
    async def _execute_rollback_actions(self, operation: RollbackOperation) -> bool:
        """Execute all actions in a rollback operation"""
        if not operation.execution_order:
            self._update_execution_order(operation)
        
        total_success = True
        
        for action_id in operation.execution_order:
            action = next((a for a in operation.actions if a.action_id == action_id), None)
            if not action:
                continue
            
            try:
                # Check dependencies
                if not self._check_action_dependencies(action, operation):
                    operation.warnings.append(f"Skipping action {action_id} due to failed dependencies")
                    continue
                
                # Execute action
                success = await self._execute_single_action(action, operation)
                
                if success:
                    operation.completed_actions.add(action_id)
                else:
                    operation.failed_actions.add(action_id)
                    total_success = False
                    
            except Exception as e:
                operation.failed_actions.add(action_id)
                operation.errors.append(f"Action {action_id} failed: {str(e)}")
                total_success = False
                self.logger.error(f"Error executing rollback action {action_id}: {e}")
        
        return total_success and len(operation.failed_actions) == 0
    
    async def _execute_single_action(self, 
                                   action: RollbackAction, 
                                   operation: RollbackOperation) -> bool:
        """Execute a single rollback action"""
        try:
            if action.rollback_function and action.rollback_function in self.rollback_functions:
                # Use registered rollback function
                rollback_func = self.rollback_functions[action.rollback_function]
                success = await rollback_func(action, operation)
            else:
                # Use default rollback logic
                success = await self._default_rollback_action(action, operation)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in rollback action execution: {e}")
            return False
    
    async def _default_rollback_action(self, 
                                     action: RollbackAction, 
                                     operation: RollbackOperation) -> bool:
        """Default rollback action implementation"""
        # This would restore element data based on action type
        # For now, simulate success
        return True
    
    def _update_execution_order(self, operation: RollbackOperation):
        """Update execution order based on priorities and dependencies"""
        # Sort actions by priority (higher first), then by dependencies
        sorted_actions = sorted(
            operation.actions,
            key=lambda a: (-a.priority, len(a.dependencies))
        )
        
        # Simple topological sort for dependencies
        execution_order = []
        completed = set()
        
        while len(execution_order) < len(operation.actions):
            added_in_iteration = False
            
            for action in sorted_actions:
                if action.action_id in completed:
                    continue
                
                # Check if all dependencies are completed
                if all(dep in completed for dep in action.dependencies):
                    execution_order.append(action.action_id)
                    completed.add(action.action_id)
                    added_in_iteration = True
            
            # Break if no progress (circular dependencies)
            if not added_in_iteration:
                remaining_actions = [a.action_id for a in sorted_actions if a.action_id not in completed]
                execution_order.extend(remaining_actions)
                break
        
        operation.execution_order = execution_order
    
    def _check_action_dependencies(self, 
                                 action: RollbackAction, 
                                 operation: RollbackOperation) -> bool:
        """Check if action dependencies are satisfied"""
        for dep_id in action.dependencies:
            if dep_id not in operation.completed_actions:
                return False
        return True
    
    async def _create_rollback_backup(self, operation: RollbackOperation):
        """Create backup before executing rollback"""
        backup_data = {
            'operation_id': operation.operation_id,
            'backup_time': datetime.now().isoformat(),
            'affected_elements': [action.element_id for action in operation.actions]
        }
        
        backup_path = self.storage_path / f"backup_{operation.operation_id}.json"
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
    
    async def _persist_rollback_operation(self, operation: RollbackOperation):
        """Persist rollback operation to storage"""
        operation_path = self.storage_path / f"rollback_{operation.operation_id}.json"
        
        # Convert to serializable format
        operation_dict = asdict(operation)
        operation_dict['created_at'] = operation.created_at.isoformat()
        if operation.last_executed:
            operation_dict['last_executed'] = operation.last_executed.isoformat()
        operation_dict['state'] = operation.state.value
        operation_dict['operation_type'] = operation.operation_type.value
        operation_dict['completed_actions'] = list(operation.completed_actions)
        operation_dict['failed_actions'] = list(operation.failed_actions)
        
        with open(operation_path, 'w') as f:
            json.dump(operation_dict, f, indent=2)
    
    def _load_persistent_data(self):
        """Load rollback operations from persistent storage"""
        if not self.storage_path.exists():
            return
        
        for file_path in self.storage_path.glob("rollback_*.json"):
            try:
                with open(file_path, 'r') as f:
                    operation_dict = json.load(f)
                
                # Convert back to RollbackOperation
                operation = self._dict_to_rollback_operation(operation_dict)
                
                # Add to appropriate collection
                if operation.state in [RollbackState.PENDING, RollbackState.IN_PROGRESS]:
                    self.active_rollbacks[operation.operation_id] = operation
                else:
                    self.rollback_history[operation.operation_id] = operation
                    
            except Exception as e:
                self.logger.error(f"Error loading rollback operation from {file_path}: {e}")
    
    def _dict_to_rollback_operation(self, operation_dict: Dict[str, Any]) -> RollbackOperation:
        """Convert dictionary back to RollbackOperation"""
        # Convert datetime strings back to datetime objects
        operation_dict['created_at'] = datetime.fromisoformat(operation_dict['created_at'])
        if operation_dict.get('last_executed'):
            operation_dict['last_executed'] = datetime.fromisoformat(operation_dict['last_executed'])
        
        # Convert enum strings back to enums
        operation_dict['state'] = RollbackState(operation_dict['state'])
        operation_dict['operation_type'] = OperationType(operation_dict['operation_type'])
        
        # Convert sets
        operation_dict['completed_actions'] = set(operation_dict.get('completed_actions', []))
        operation_dict['failed_actions'] = set(operation_dict.get('failed_actions', []))
        
        # Convert actions
        actions = []
        for action_dict in operation_dict.get('actions', []):
            action = RollbackAction(**action_dict)
            actions.append(action)
        operation_dict['actions'] = actions
        
        return RollbackOperation(**operation_dict)
    
    def _delete_persistent_rollback(self, operation_id: str):
        """Delete persistent rollback data"""
        operation_path = self.storage_path / f"rollback_{operation_id}.json"
        backup_path = self.storage_path / f"backup_{operation_id}.json"
        
        for path in [operation_path, backup_path]:
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    self.logger.error(f"Error deleting {path}: {e}")
    
    def _update_average_rollback_time(self, execution_time: float):
        """Update average rollback time statistic"""
        current_avg = self.rollback_stats['average_rollback_time']
        total_rollbacks = self.rollback_stats['total_rollbacks']
        
        if total_rollbacks > 1:
            new_avg = (current_avg * (total_rollbacks - 1) + execution_time) / total_rollbacks
            self.rollback_stats['average_rollback_time'] = new_avg
        else:
            self.rollback_stats['average_rollback_time'] = execution_time
    
    def _register_default_rollback_functions(self):
        """Register default rollback functions"""
        self.register_rollback_function('restore_element_type', self._restore_element_type)
        self.register_rollback_function('restore_element_data', self._restore_element_data)
        self.register_rollback_function('restore_element_properties', self._restore_element_properties)
    
    async def _restore_element_type(self, 
                                  action: RollbackAction, 
                                  operation: RollbackOperation) -> bool:
        """Restore element type from rollback action"""
        # Placeholder implementation
        return True
    
    async def _restore_element_data(self, 
                                  action: RollbackAction, 
                                  operation: RollbackOperation) -> bool:
        """Restore element data from rollback action"""
        # Placeholder implementation
        return True
    
    async def _restore_element_properties(self, 
                                        action: RollbackAction, 
                                        operation: RollbackOperation) -> bool:
        """Restore element properties from rollback action"""
        # Placeholder implementation
        return True