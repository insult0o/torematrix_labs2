"""
Undo/Redo System for Merge/Split Operations.

This module provides comprehensive undo/redo functionality with state persistence,
allowing users to revert and replay operations with full state restoration.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import copy
import pickle
import gzip
import threading
from collections import deque
from pathlib import Path
import logging

from .transaction import TransactionManager, Transaction, OperationRecord, OperationType


class CommandType(Enum):
    """Types of commands that can be undone/redone."""
    MERGE_OPERATION = "merge_operation"
    SPLIT_OPERATION = "split_operation"
    BATCH_OPERATION = "batch_operation"
    TRANSACTION = "transaction"
    ELEMENT_UPDATE = "element_update"
    METADATA_CHANGE = "metadata_change"


class CommandState(Enum):
    """States of a command in the undo/redo system."""
    PENDING = "pending"
    EXECUTED = "executed"
    UNDONE = "undone"
    REDONE = "redone"
    FAILED = "failed"


@dataclass
class Command:
    """Represents a single undoable/redoable command."""
    command_id: str
    command_type: CommandType
    description: str
    execute_data: Dict[str, Any]
    undo_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    state: CommandState = CommandState.PENDING
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution callbacks
    execute_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
    undo_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    def can_execute(self) -> bool:
        """Check if command can be executed."""
        return self.state == CommandState.PENDING and self.execute_callback is not None
    
    def can_undo(self) -> bool:
        """Check if command can be undone."""
        return self.state == CommandState.EXECUTED and self.undo_callback is not None
    
    def can_redo(self) -> bool:
        """Check if command can be redone."""
        return self.state == CommandState.UNDONE and self.execute_callback is not None
    
    def execute(self) -> bool:
        """Execute the command."""
        if not self.can_execute():
            return False
        
        try:
            if self.execute_callback(self.execute_data):
                self.state = CommandState.EXECUTED
                return True
            else:
                self.state = CommandState.FAILED
                return False
        except Exception:
            self.state = CommandState.FAILED
            return False
    
    def undo(self) -> bool:
        """Undo the command."""
        if not self.can_undo():
            return False
        
        try:
            if self.undo_callback(self.undo_data):
                self.state = CommandState.UNDONE
                return True
            else:
                self.state = CommandState.FAILED
                return False
        except Exception:
            self.state = CommandState.FAILED
            return False
    
    def redo(self) -> bool:
        """Redo the command."""
        if not self.can_redo():
            return False
        
        try:
            if self.execute_callback(self.execute_data):
                self.state = CommandState.EXECUTED
                return True
            else:
                self.state = CommandState.FAILED
                return False
        except Exception:
            self.state = CommandState.FAILED
            return False


@dataclass
class CommandGroup:
    """Groups related commands for batch undo/redo operations."""
    group_id: str
    description: str
    commands: List[Command] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_command(self, command: Command) -> None:
        """Add a command to this group."""
        self.commands.append(command)
    
    def can_execute_all(self) -> bool:
        """Check if all commands in group can be executed."""
        return all(cmd.can_execute() for cmd in self.commands)
    
    def can_undo_all(self) -> bool:
        """Check if all commands in group can be undone."""
        return all(cmd.can_undo() for cmd in self.commands)
    
    def can_redo_all(self) -> bool:
        """Check if all commands in group can be redone."""
        return all(cmd.can_redo() for cmd in self.commands)
    
    def execute_all(self) -> bool:
        """Execute all commands in group."""
        if not self.can_execute_all():
            return False
        
        executed_commands = []
        try:
            for command in self.commands:
                if command.execute():
                    executed_commands.append(command)
                else:
                    # Rollback executed commands
                    for executed_cmd in reversed(executed_commands):
                        executed_cmd.undo()
                    return False
            return True
        except Exception:
            # Rollback executed commands
            for executed_cmd in reversed(executed_commands):
                executed_cmd.undo()
            return False
    
    def undo_all(self) -> bool:
        """Undo all commands in group (in reverse order)."""
        if not self.can_undo_all():
            return False
        
        undone_commands = []
        try:
            for command in reversed(self.commands):
                if command.undo():
                    undone_commands.append(command)
                else:
                    # Re-execute undone commands
                    for undone_cmd in reversed(undone_commands):
                        undone_cmd.execute()
                    return False
            return True
        except Exception:
            # Re-execute undone commands
            for undone_cmd in reversed(undone_commands):
                undone_cmd.execute()
            return False
    
    def redo_all(self) -> bool:
        """Redo all commands in group."""
        if not self.can_redo_all():
            return False
        
        return self.execute_all()


class StateSnapshot:
    """Captures a snapshot of system state for restoration."""
    
    def __init__(self, snapshot_id: str, description: str, data: Dict[str, Any]):
        self.snapshot_id = snapshot_id
        self.description = description
        self.timestamp = time.time()
        self.data = copy.deepcopy(data)
        self.compressed_data: Optional[bytes] = None
        self._compress_data()
    
    def _compress_data(self) -> None:
        """Compress snapshot data to save memory."""
        try:
            serialized = pickle.dumps(self.data)
            self.compressed_data = gzip.compress(serialized)
            # Clear uncompressed data to save memory
            self.data = {}
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to compress snapshot {self.snapshot_id}: {e}")
    
    def get_data(self) -> Dict[str, Any]:
        """Get uncompressed snapshot data."""
        if self.data:
            return copy.deepcopy(self.data)
        
        if self.compressed_data:
            try:
                serialized = gzip.decompress(self.compressed_data)
                return pickle.loads(serialized)
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to decompress snapshot {self.snapshot_id}: {e}")
                return {}
        
        return {}
    
    def get_size_bytes(self) -> int:
        """Get approximate size of snapshot in bytes."""
        if self.compressed_data:
            return len(self.compressed_data)
        return len(pickle.dumps(self.data))


class UndoRedoManager:
    """
    Manages undo/redo operations with state persistence and performance optimization.
    
    Features:
    - Command pattern implementation
    - Grouped operations (batch undo/redo)
    - State snapshots for fast restoration
    - Memory-efficient storage with compression
    - Transaction integration
    - Performance monitoring
    """
    
    def __init__(self, 
                 max_history_size: int = 100,
                 max_memory_mb: int = 100,
                 snapshot_interval: int = 10,
                 auto_cleanup: bool = True):
        self.max_history_size = max_history_size
        self.max_memory_mb = max_memory_mb
        self.snapshot_interval = snapshot_interval
        self.auto_cleanup = auto_cleanup
        
        # Command history
        self.undo_stack: deque = deque(maxlen=max_history_size)
        self.redo_stack: deque = deque(maxlen=max_history_size)
        
        # State snapshots
        self.snapshots: Dict[str, StateSnapshot] = {}
        self.snapshot_counter = 0
        
        # Command groups for batch operations
        self.command_groups: Dict[str, CommandGroup] = {}
        
        # Current state
        self.current_position = 0
        self.last_snapshot_position = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Integration with transaction manager
        self.transaction_manager: Optional[TransactionManager] = None
        
        # Performance metrics
        self.metrics = {
            'commands_executed': 0,
            'commands_undone': 0,
            'commands_redone': 0,
            'snapshots_created': 0,
            'memory_usage_mb': 0.0,
            'average_undo_time_ms': 0.0,
            'average_redo_time_ms': 0.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def set_transaction_manager(self, transaction_manager: TransactionManager) -> None:
        """Set the transaction manager for integration."""
        self.transaction_manager = transaction_manager
    
    def execute_command(self, command: Command, group_id: Optional[str] = None) -> bool:
        """
        Execute a command and add it to undo history.
        
        Args:
            command: Command to execute
            group_id: Optional group ID for batch operations
            
        Returns:
            True if command executed successfully
        """
        with self.lock:
            # Execute the command
            start_time = time.time()
            success = command.execute()
            execution_time = (time.time() - start_time) * 1000  # ms
            
            if success:
                # Add to undo stack
                self.undo_stack.append(command)
                
                # Clear redo stack when new command is executed
                self.redo_stack.clear()
                
                # Add to group if specified
                if group_id:
                    self._add_command_to_group(command, group_id)
                
                # Update position and check for snapshot
                self.current_position += 1
                self._check_create_snapshot()
                
                # Update metrics
                self.metrics['commands_executed'] += 1
                self._update_memory_usage()
                
                # Auto cleanup if enabled
                if self.auto_cleanup:
                    self._cleanup_if_needed()
                
                self.logger.debug(f"Executed command {command.command_id} in {execution_time:.2f}ms")
                return True
            else:
                self.logger.warning(f"Failed to execute command {command.command_id}")
                return False
    
    def undo(self, count: int = 1) -> Tuple[bool, List[str]]:
        """
        Undo the last command(s).
        
        Args:
            count: Number of commands to undo
            
        Returns:
            (success, list of undone command IDs)
        """
        with self.lock:
            if not self.can_undo():
                return False, []
            
            undone_commands = []
            start_time = time.time()
            
            try:
                for _ in range(min(count, len(self.undo_stack))):
                    command = self.undo_stack.pop()
                    
                    if command.undo():
                        self.redo_stack.append(command)
                        undone_commands.append(command.command_id)
                        self.current_position -= 1
                    else:
                        # Restore command to undo stack if undo failed
                        self.undo_stack.append(command)
                        break
                
                # Update metrics
                undo_time = (time.time() - start_time) * 1000
                self.metrics['commands_undone'] += len(undone_commands)
                self._update_average_time('undo', undo_time)
                
                self.logger.debug(f"Undone {len(undone_commands)} commands in {undo_time:.2f}ms")
                return len(undone_commands) > 0, undone_commands
                
            except Exception as e:
                self.logger.error(f"Error during undo operation: {e}")
                return False, undone_commands
    
    def redo(self, count: int = 1) -> Tuple[bool, List[str]]:
        """
        Redo the last undone command(s).
        
        Args:
            count: Number of commands to redo
            
        Returns:
            (success, list of redone command IDs)
        """
        with self.lock:
            if not self.can_redo():
                return False, []
            
            redone_commands = []
            start_time = time.time()
            
            try:
                for _ in range(min(count, len(self.redo_stack))):
                    command = self.redo_stack.pop()
                    
                    if command.redo():
                        self.undo_stack.append(command)
                        redone_commands.append(command.command_id)
                        self.current_position += 1
                    else:
                        # Restore command to redo stack if redo failed
                        self.redo_stack.append(command)
                        break
                
                # Update metrics
                redo_time = (time.time() - start_time) * 1000
                self.metrics['commands_redone'] += len(redone_commands)
                self._update_average_time('redo', redo_time)
                
                self.logger.debug(f"Redone {len(redone_commands)} commands in {redo_time:.2f}ms")
                return len(redone_commands) > 0, redone_commands
                
            except Exception as e:
                self.logger.error(f"Error during redo operation: {e}")
                return False, redone_commands
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        with self.lock:
            return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        with self.lock:
            return len(self.redo_stack) > 0
    
    def create_snapshot(self, description: str, data: Dict[str, Any]) -> str:
        """
        Create a state snapshot for fast restoration.
        
        Args:
            description: Description of the snapshot
            data: State data to capture
            
        Returns:
            Snapshot ID
        """
        with self.lock:
            snapshot_id = f"snapshot_{int(time.time())}_{self.snapshot_counter}"
            self.snapshot_counter += 1
            
            snapshot = StateSnapshot(snapshot_id, description, data)
            self.snapshots[snapshot_id] = snapshot
            self.last_snapshot_position = self.current_position
            
            self.metrics['snapshots_created'] += 1
            self._update_memory_usage()
            
            self.logger.debug(f"Created snapshot {snapshot_id}: {description}")
            return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore state from a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            
        Returns:
            Restored state data or None if not found
        """
        with self.lock:
            if snapshot_id not in self.snapshots:
                return None
            
            snapshot = self.snapshots[snapshot_id]
            data = snapshot.get_data()
            
            self.logger.debug(f"Restored snapshot {snapshot_id}")
            return data
    
    def create_command_group(self, group_id: str, description: str) -> CommandGroup:
        """
        Create a new command group for batch operations.
        
        Args:
            group_id: Unique group identifier
            description: Group description
            
        Returns:
            Created command group
        """
        with self.lock:
            group = CommandGroup(group_id, description)
            self.command_groups[group_id] = group
            return group
    
    def execute_command_group(self, group_id: str) -> bool:
        """
        Execute all commands in a group.
        
        Args:
            group_id: ID of group to execute
            
        Returns:
            True if all commands executed successfully
        """
        with self.lock:
            if group_id not in self.command_groups:
                return False
            
            group = self.command_groups[group_id]
            success = group.execute_all()
            
            if success:
                # Add all commands to undo stack
                for command in group.commands:
                    self.undo_stack.append(command)
                
                self.current_position += len(group.commands)
                self._check_create_snapshot()
                
                self.metrics['commands_executed'] += len(group.commands)
                self._update_memory_usage()
            
            return success
    
    def undo_command_group(self, group_id: str) -> bool:
        """
        Undo all commands in a group.
        
        Args:
            group_id: ID of group to undo
            
        Returns:
            True if all commands undone successfully
        """
        with self.lock:
            if group_id not in self.command_groups:
                return False
            
            group = self.command_groups[group_id]
            success = group.undo_all()
            
            if success:
                # Move commands from undo to redo stack
                for command in reversed(group.commands):
                    if command in self.undo_stack:
                        self.undo_stack.remove(command)
                        self.redo_stack.append(command)
                
                self.current_position -= len(group.commands)
                self.metrics['commands_undone'] += len(group.commands)
            
            return success
    
    def get_undo_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get undo history for display.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of command information
        """
        with self.lock:
            history = []
            
            for command in list(self.undo_stack)[-limit:]:
                history.append({
                    'command_id': command.command_id,
                    'type': command.command_type.value,
                    'description': command.description,
                    'timestamp': command.timestamp,
                    'state': command.state.value
                })
            
            return list(reversed(history))
    
    def get_redo_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get redo history for display.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of command information
        """
        with self.lock:
            history = []
            
            for command in list(self.redo_stack)[-limit:]:
                history.append({
                    'command_id': command.command_id,
                    'type': command.command_type.value,
                    'description': command.description,
                    'timestamp': command.timestamp,
                    'state': command.state.value
                })
            
            return list(reversed(history))
    
    def clear_history(self) -> None:
        """Clear all undo/redo history and snapshots."""
        with self.lock:
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.snapshots.clear()
            self.command_groups.clear()
            self.current_position = 0
            self.last_snapshot_position = 0
            self.snapshot_counter = 0
            
            self._update_memory_usage()
            self.logger.info("Cleared all undo/redo history")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        with self.lock:
            return {
                **self.metrics,
                'undo_stack_size': len(self.undo_stack),
                'redo_stack_size': len(self.redo_stack),
                'snapshot_count': len(self.snapshots),
                'command_group_count': len(self.command_groups),
                'current_position': self.current_position
            }
    
    # Private helper methods
    
    def _add_command_to_group(self, command: Command, group_id: str) -> None:
        """Add command to a group."""
        if group_id not in self.command_groups:
            self.command_groups[group_id] = CommandGroup(group_id, f"Auto-created group {group_id}")
        
        self.command_groups[group_id].add_command(command)
    
    def _check_create_snapshot(self) -> None:
        """Check if a new snapshot should be created."""
        if (self.current_position - self.last_snapshot_position) >= self.snapshot_interval:
            # This would integrate with actual state capture
            snapshot_data = {'position': self.current_position, 'timestamp': time.time()}
            self.create_snapshot(f"Auto snapshot at position {self.current_position}", snapshot_data)
    
    def _update_memory_usage(self) -> None:
        """Update memory usage metrics."""
        total_size = 0
        
        # Calculate size of undo/redo stacks
        for command in self.undo_stack:
            total_size += len(pickle.dumps(command))
        
        for command in self.redo_stack:
            total_size += len(pickle.dumps(command))
        
        # Calculate size of snapshots
        for snapshot in self.snapshots.values():
            total_size += snapshot.get_size_bytes()
        
        self.metrics['memory_usage_mb'] = total_size / (1024 * 1024)
    
    def _update_average_time(self, operation: str, time_ms: float) -> None:
        """Update average operation time."""
        metric_key = f'average_{operation}_time_ms'
        current_avg = self.metrics[metric_key]
        count_key = f'commands_{operation}ne' if operation == 'undo' else f'commands_{operation}ne'
        count = self.metrics[count_key]
        
        if count > 1:
            self.metrics[metric_key] = ((current_avg * (count - 1)) + time_ms) / count
        else:
            self.metrics[metric_key] = time_ms
    
    def _cleanup_if_needed(self) -> None:
        """Cleanup old data if memory usage is too high."""
        if self.metrics['memory_usage_mb'] > self.max_memory_mb:
            # Remove oldest snapshots first
            if self.snapshots:
                oldest_snapshot = min(self.snapshots.values(), key=lambda s: s.timestamp)
                del self.snapshots[oldest_snapshot.snapshot_id]
                self.logger.debug(f"Removed old snapshot {oldest_snapshot.snapshot_id}")
            
            # Remove old command groups
            if self.command_groups:
                oldest_group = min(self.command_groups.values(), key=lambda g: g.timestamp)
                del self.command_groups[oldest_group.group_id]
                self.logger.debug(f"Removed old command group {oldest_group.group_id}")
            
            self._update_memory_usage()


# Convenience functions for creating common commands

def create_merge_command(element_ids: List[str], 
                        before_state: Dict[str, Any],
                        after_state: Dict[str, Any],
                        execute_callback: Callable,
                        undo_callback: Callable) -> Command:
    """Create a merge operation command."""
    return Command(
        command_id=str(uuid.uuid4()),
        command_type=CommandType.MERGE_OPERATION,
        description=f"Merge {len(element_ids)} elements",
        execute_data={'element_ids': element_ids, 'after_state': after_state},
        undo_data={'element_ids': element_ids, 'before_state': before_state},
        execute_callback=execute_callback,
        undo_callback=undo_callback
    )


def create_split_command(element_id: str,
                        before_state: Dict[str, Any],
                        after_state: Dict[str, Any],
                        execute_callback: Callable,
                        undo_callback: Callable) -> Command:
    """Create a split operation command."""
    return Command(
        command_id=str(uuid.uuid4()),
        command_type=CommandType.SPLIT_OPERATION,
        description=f"Split element {element_id}",
        execute_data={'element_id': element_id, 'after_state': after_state},
        undo_data={'element_id': element_id, 'before_state': before_state},
        execute_callback=execute_callback,
        undo_callback=undo_callback
    )