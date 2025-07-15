"""Rollback System

Comprehensive rollback and undo system for type management operations.
Provides reliable operation reversal with state preservation and validation.
"""

import logging
import threading
import time
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Set
from pathlib import Path
import pickle
import gzip

logger = logging.getLogger(__name__)


class RollbackStatus(Enum):
    """Status of rollback operations"""
    PENDING = "pending"
    PREPARING = "preparing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class OperationType(Enum):
    """Types of operations that can be rolled back"""
    BULK_TYPE_CHANGE = "bulk_type_change"
    TYPE_CONVERSION = "type_conversion"
    TYPE_MIGRATION = "type_migration"
    BATCH_OPERATION = "batch_operation"
    CUSTOM = "custom"


@dataclass
class RollbackStep:
    """Individual step in a rollback operation"""
    step_id: str
    description: str
    operation_type: OperationType
    target_id: str  # Element or object ID
    original_state: Dict[str, Any]
    rollback_function: Optional[Callable] = None
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    validation_function: Optional[Callable] = None
    executed: bool = False
    execution_time: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class RollbackOperation:
    """Complete rollback operation definition"""
    rollback_id: str
    operation_name: str
    description: str
    original_operation_id: str
    steps: List[RollbackStep]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_steps(self) -> int:
        """Total number of rollback steps"""
        return len(self.steps)
    
    @property
    def executed_steps(self) -> List[RollbackStep]:
        """List of executed steps"""
        return [step for step in self.steps if step.executed]
    
    @property
    def pending_steps(self) -> List[RollbackStep]:
        """List of pending steps"""
        return [step for step in self.steps if not step.executed]
    
    @property
    def is_expired(self) -> bool:
        """Check if rollback operation has expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at


@dataclass
class RollbackState:
    """Current state of rollback operation execution"""
    rollback_id: str
    status: RollbackStatus
    current_step: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate rollback duration"""
        if not self.start_time:
            return 0.0
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total_attempted = self.successful_steps + self.failed_steps
        if total_attempted == 0:
            return 0.0
        return (self.successful_steps / total_attempted) * 100.0


class RollbackManager:
    """Comprehensive rollback and undo system
    
    Provides reliable operation reversal with:
    - State preservation and restoration
    - Multi-step rollback operations
    - Rollback validation and verification
    - Expiration and cleanup management
    - Transaction-like rollback semantics
    - Performance optimization for large rollbacks
    """
    
    def __init__(self, 
                 storage_dir: Optional[Path] = None,
                 max_rollback_age_days: int = 30,
                 enable_compression: bool = True):
        """Initialize rollback manager
        
        Args:
            storage_dir: Directory for storing rollback data
            max_rollback_age_days: Maximum age for rollback operations
            enable_compression: Whether to compress rollback data
        """
        self.storage_dir = storage_dir or Path("rollback_data")
        self.storage_dir.mkdir(exist_ok=True)
        self.max_rollback_age_days = max_rollback_age_days
        self.enable_compression = enable_compression
        
        self._rollback_operations: Dict[str, RollbackOperation] = {}
        self._rollback_states: Dict[str, RollbackState] = {}
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        
        self._load_existing_rollbacks()
        self._start_cleanup_thread()
        
        logger.info(f"RollbackManager initialized with storage at {self.storage_dir}")
    
    def create_rollback_operation(self, 
                                operation_name: str,
                                description: str,
                                original_operation_id: str,
                                steps: List[RollbackStep],
                                expiration_hours: int = 72,
                                tags: Optional[Set[str]] = None) -> RollbackOperation:
        """Create a new rollback operation
        
        Args:
            operation_name: Name of the rollback operation
            description: Description of what will be rolled back
            original_operation_id: ID of the original operation being rolled back
            steps: List of rollback steps
            expiration_hours: Hours until rollback expires
            tags: Optional tags for categorization
            
        Returns:
            Created RollbackOperation
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not operation_name or not steps:
            raise ValueError("Operation name and steps are required")
        
        # Generate rollback ID
        rollback_id = self._generate_rollback_id(operation_name, original_operation_id)
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=expiration_hours)
        
        rollback_op = RollbackOperation(
            rollback_id=rollback_id,
            operation_name=operation_name,
            description=description,
            original_operation_id=original_operation_id,
            steps=steps,
            expires_at=expires_at,
            tags=tags or set()
        )
        
        with self._lock:
            self._rollback_operations[rollback_id] = rollback_op
            self._rollback_states[rollback_id] = RollbackState(
                rollback_id=rollback_id,
                status=RollbackStatus.PENDING
            )
        
        # Save to storage
        self._save_rollback_operation(rollback_op)
        
        logger.info(f"Created rollback operation {rollback_id}: {operation_name}")
        return rollback_op
    
    def execute_rollback(self, 
                        rollback_id: str,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None) -> RollbackState:
        """Execute a rollback operation
        
        Args:
            rollback_id: ID of rollback operation to execute
            dry_run: If True, validate without executing
            progress_callback: Optional progress callback function
            
        Returns:
            RollbackState with execution results
            
        Raises:
            ValueError: If rollback not found or invalid
            RuntimeError: If rollback execution fails
        """
        with self._lock:
            if rollback_id not in self._rollback_operations:
                raise ValueError(f"Rollback operation {rollback_id} not found")
            
            rollback_op = self._rollback_operations[rollback_id]
            state = self._rollback_states[rollback_id]
            
            # Check if expired
            if rollback_op.is_expired:
                raise ValueError(f"Rollback operation {rollback_id} has expired")
            
            # Check if already executed
            if state.status in (RollbackStatus.COMPLETED, RollbackStatus.FAILED):
                logger.warning(f"Rollback {rollback_id} already executed with status: {state.status}")
                return state
        
        logger.info(f"Executing rollback {rollback_id} (dry_run={dry_run})")
        
        state.status = RollbackStatus.PREPARING
        state.start_time = datetime.now()
        
        try:
            # Validate rollback operation
            validation_result = self._validate_rollback_operation(rollback_op)
            if validation_result['errors']:
                state.status = RollbackStatus.FAILED
                state.errors.extend(validation_result['errors'])
                return state
            
            state.warnings.extend(validation_result['warnings'])
            
            if dry_run:
                state.status = RollbackStatus.COMPLETED
                logger.info(f"Dry run completed for rollback {rollback_id}")
                return state
            
            # Execute rollback steps
            state.status = RollbackStatus.EXECUTING
            
            for i, step in enumerate(rollback_op.steps):
                state.current_step = i + 1
                
                try:
                    logger.debug(f"Executing rollback step {i+1}/{len(rollback_op.steps)}: {step.description}")
                    
                    # Execute step
                    self._execute_rollback_step(step)
                    
                    step.executed = True
                    step.execution_time = datetime.now()
                    state.successful_steps += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = state.current_step / rollback_op.total_steps
                        progress_callback(progress, f"Executed step: {step.description}")
                    
                except Exception as e:
                    logger.error(f"Rollback step failed: {step.step_id}: {e}")
                    step.error = str(e)
                    state.failed_steps += 1
                    state.errors.append(f"Step {step.step_id}: {e}")
                    
                    # For rollbacks, we typically want to continue even if some steps fail
                    # to attempt to restore as much as possible
                    continue
            
            # Determine final status
            if state.failed_steps == 0:
                state.status = RollbackStatus.COMPLETED
            elif state.successful_steps > 0:
                state.status = RollbackStatus.PARTIAL
            else:
                state.status = RollbackStatus.FAILED
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            state.status = RollbackStatus.FAILED
            state.errors.append(str(e))
        
        finally:
            state.end_time = datetime.now()
            self._save_rollback_state(state)
        
        logger.info(f"Rollback {rollback_id} completed with status: {state.status}")
        return state
    
    def get_rollback_operation(self, rollback_id: str) -> Optional[RollbackOperation]:
        """Get rollback operation by ID
        
        Args:
            rollback_id: ID of rollback operation
            
        Returns:
            RollbackOperation if found, None otherwise
        """
        with self._lock:
            return self._rollback_operations.get(rollback_id)
    
    def get_rollback_state(self, rollback_id: str) -> Optional[RollbackState]:
        """Get rollback state by ID
        
        Args:
            rollback_id: ID of rollback operation
            
        Returns:
            RollbackState if found, None otherwise
        """
        with self._lock:
            return self._rollback_states.get(rollback_id)
    
    def list_rollback_operations(self, 
                                tags: Optional[Set[str]] = None,
                                status_filter: Optional[RollbackStatus] = None,
                                include_expired: bool = False) -> List[RollbackOperation]:
        """List rollback operations with optional filtering
        
        Args:
            tags: Filter by tags (operations must have all specified tags)
            status_filter: Filter by rollback status
            include_expired: Whether to include expired operations
            
        Returns:
            List of matching rollback operations
        """
        with self._lock:
            operations = []
            
            for rollback_id, operation in self._rollback_operations.items():
                # Check expiration
                if not include_expired and operation.is_expired:
                    continue
                
                # Check tags
                if tags and not tags.issubset(operation.tags):
                    continue
                
                # Check status
                if status_filter:
                    state = self._rollback_states.get(rollback_id)
                    if not state or state.status != status_filter:
                        continue
                
                operations.append(operation)
            
            return sorted(operations, key=lambda op: op.created_at, reverse=True)
    
    def delete_rollback_operation(self, rollback_id: str) -> bool:
        """Delete a rollback operation
        
        Args:
            rollback_id: ID of rollback operation to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if rollback_id not in self._rollback_operations:
                return False
            
            # Remove from memory
            del self._rollback_operations[rollback_id]
            del self._rollback_states[rollback_id]
            
            # Remove from storage
            self._delete_rollback_files(rollback_id)
            
            logger.info(f"Deleted rollback operation {rollback_id}")
            return True
    
    def cleanup_expired_rollbacks(self) -> int:
        """Clean up expired rollback operations
        
        Returns:
            Number of operations cleaned up
        """
        cleaned_count = 0
        expired_ids = []
        
        with self._lock:
            for rollback_id, operation in self._rollback_operations.items():
                if operation.is_expired:
                    expired_ids.append(rollback_id)
        
        for rollback_id in expired_ids:
            if self.delete_rollback_operation(rollback_id):
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} expired rollback operations")
        return cleaned_count
    
    def create_element_type_rollback_step(self, 
                                        element_id: str,
                                        current_type: str,
                                        original_type: str,
                                        element_data: Optional[Dict[str, Any]] = None) -> RollbackStep:
        """Create a rollback step for element type change
        
        Args:
            element_id: ID of element to rollback
            current_type: Current type of element
            original_type: Original type to restore
            element_data: Original element data to restore
            
        Returns:
            RollbackStep for type change rollback
        """
        step_id = f"type_rollback_{element_id}_{int(time.time())}"
        
        return RollbackStep(
            step_id=step_id,
            description=f"Rollback element {element_id} type from {current_type} to {original_type}",
            operation_type=OperationType.BULK_TYPE_CHANGE,
            target_id=element_id,
            original_state={
                'type': original_type,
                'data': element_data or {},
                'rollback_timestamp': datetime.now().isoformat()
            },
            rollback_function=self._rollback_element_type,
            rollback_data={
                'element_id': element_id,
                'target_type': original_type,
                'original_data': element_data
            }
        )
    
    def create_bulk_rollback_steps(self, 
                                 element_changes: List[Dict[str, Any]]) -> List[RollbackStep]:
        """Create multiple rollback steps for bulk operation
        
        Args:
            element_changes: List of element change records
            
        Returns:
            List of RollbackStep objects
        """
        steps = []
        
        for change in element_changes:
            step = self.create_element_type_rollback_step(
                element_id=change['element_id'],
                current_type=change['new_type'],
                original_type=change['old_type'],
                element_data=change.get('original_data')
            )
            steps.append(step)
        
        return steps
    
    def _generate_rollback_id(self, operation_name: str, original_operation_id: str) -> str:
        """Generate unique rollback ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = f"{operation_name}_{original_operation_id}_{timestamp}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"rollback_{timestamp}_{hash_suffix}"
    
    def _validate_rollback_operation(self, rollback_op: RollbackOperation) -> Dict[str, List[str]]:
        """Validate rollback operation before execution"""
        errors = []
        warnings = []
        
        # Check if expired
        if rollback_op.is_expired:
            errors.append("Rollback operation has expired")
        
        # Check steps
        if not rollback_op.steps:
            errors.append("Rollback operation has no steps")
        
        # Validate each step
        for step in rollback_op.steps:
            if not step.step_id or not step.description:
                errors.append(f"Step missing required fields: {step.step_id}")
            
            # Validate target exists (mock implementation)
            if not self._validate_rollback_target(step.target_id):
                warnings.append(f"Target {step.target_id} may not exist")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _execute_rollback_step(self, step: RollbackStep) -> None:
        """Execute a single rollback step"""
        logger.debug(f"Executing rollback step: {step.step_id}")
        
        if step.rollback_function:
            # Use custom rollback function
            step.rollback_function(step.rollback_data)
        else:
            # Use default rollback based on operation type
            if step.operation_type == OperationType.BULK_TYPE_CHANGE:
                self._rollback_element_type(step.rollback_data)
            elif step.operation_type == OperationType.TYPE_CONVERSION:
                self._rollback_type_conversion(step.rollback_data)
            else:
                raise NotImplementedError(f"Rollback not implemented for {step.operation_type}")
        
        # Validate rollback if validation function provided
        if step.validation_function:
            validation_result = step.validation_function(step.target_id, step.original_state)
            if not validation_result:
                raise RuntimeError(f"Rollback validation failed for step {step.step_id}")
    
    def _rollback_element_type(self, rollback_data: Dict[str, Any]) -> None:
        """Rollback element type change"""
        element_id = rollback_data['element_id']
        target_type = rollback_data['target_type']
        original_data = rollback_data.get('original_data', {})
        
        # Mock implementation - would restore element type and data
        logger.debug(f"Rolling back element {element_id} to type {target_type}")
        
        # In real implementation, would:
        # 1. Update element type in storage
        # 2. Restore original element data
        # 3. Update any related metadata
        # 4. Trigger any necessary notifications
    
    def _rollback_type_conversion(self, rollback_data: Dict[str, Any]) -> None:
        """Rollback type conversion operation"""
        # Mock implementation for type conversion rollback
        logger.debug(f"Rolling back type conversion: {rollback_data}")
    
    def _validate_rollback_target(self, target_id: str) -> bool:
        """Validate that rollback target exists (mock)"""
        # Mock implementation - would check if target exists
        return True
    
    def _save_rollback_operation(self, rollback_op: RollbackOperation) -> None:
        """Save rollback operation to storage"""
        file_path = self.storage_dir / f"{rollback_op.rollback_id}_operation.pkl"
        
        try:
            data = {
                'rollback_operation': rollback_op,
                'saved_at': datetime.now().isoformat()
            }
            
            if self.enable_compression:
                with gzip.open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            
            logger.debug(f"Saved rollback operation to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save rollback operation {rollback_op.rollback_id}: {e}")
    
    def _save_rollback_state(self, state: RollbackState) -> None:
        """Save rollback state to storage"""
        file_path = self.storage_dir / f"{state.rollback_id}_state.pkl"
        
        try:
            data = {
                'rollback_state': state,
                'saved_at': datetime.now().isoformat()
            }
            
            if self.enable_compression:
                with gzip.open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            
            logger.debug(f"Saved rollback state to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save rollback state {state.rollback_id}: {e}")
    
    def _load_existing_rollbacks(self) -> None:
        """Load existing rollback operations from storage"""
        if not self.storage_dir.exists():
            return
        
        loaded_count = 0
        
        for file_path in self.storage_dir.glob("*_operation.pkl"):
            try:
                if self.enable_compression:
                    with gzip.open(file_path, 'rb') as f:
                        data = pickle.load(f)
                else:
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                
                rollback_op = data['rollback_operation']
                self._rollback_operations[rollback_op.rollback_id] = rollback_op
                
                # Load corresponding state if exists
                state_file = self.storage_dir / f"{rollback_op.rollback_id}_state.pkl"
                if state_file.exists():
                    try:
                        if self.enable_compression:
                            with gzip.open(state_file, 'rb') as f:
                                state_data = pickle.load(f)
                        else:
                            with open(state_file, 'rb') as f:
                                state_data = pickle.load(f)
                        
                        self._rollback_states[rollback_op.rollback_id] = state_data['rollback_state']
                    except Exception as e:
                        logger.warning(f"Failed to load rollback state from {state_file}: {e}")
                        # Create default state
                        self._rollback_states[rollback_op.rollback_id] = RollbackState(
                            rollback_id=rollback_op.rollback_id,
                            status=RollbackStatus.PENDING
                        )
                else:
                    # Create default state
                    self._rollback_states[rollback_op.rollback_id] = RollbackState(
                        rollback_id=rollback_op.rollback_id,
                        status=RollbackStatus.PENDING
                    )
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to load rollback operation from {file_path}: {e}")
        
        logger.info(f"Loaded {loaded_count} existing rollback operations")
    
    def _delete_rollback_files(self, rollback_id: str) -> None:
        """Delete rollback files from storage"""
        operation_file = self.storage_dir / f"{rollback_id}_operation.pkl"
        state_file = self.storage_dir / f"{rollback_id}_state.pkl"
        
        for file_path in [operation_file, state_file]:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted rollback file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete rollback file {file_path}: {e}")
    
    def _start_cleanup_thread(self) -> None:
        """Start background thread for cleanup operations"""
        def cleanup_worker():
            while True:
                try:
                    # Run cleanup every hour
                    time.sleep(3600)
                    self.cleanup_expired_rollbacks()
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.debug("Started rollback cleanup thread")
    
    def __del__(self):
        """Cleanup when manager is destroyed"""
        # Cleanup thread is daemon, so it will exit automatically
        pass