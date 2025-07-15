"""
Selection history and undo/redo system.
Provides comprehensive undo/redo functionality for selection operations.
"""

import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal

from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from .base import SelectionResult


class HistoryActionType(Enum):
    """Types of history actions."""
    SELECT = "select"              # Selection made
    DESELECT = "deselect"         # Selection cleared
    ADD_TO_SELECTION = "add"      # Added to existing selection
    REMOVE_FROM_SELECTION = "remove"  # Removed from selection
    MODIFY_SELECTION = "modify"   # Modified existing selection
    TRANSFORM = "transform"       # Transformed selection (move, resize)
    TOOL_CHANGE = "tool_change"   # Changed selection tool
    BATCH = "batch"               # Batch of operations


@dataclass
class HistoryAction:
    """A single action in the history."""
    action_type: HistoryActionType
    timestamp: float
    description: str
    
    # State before action
    before_state: Optional[SelectionResult] = None
    
    # State after action
    after_state: Optional[SelectionResult] = None
    
    # Additional data for specific action types
    action_data: Dict[str, Any] = field(default_factory=dict)
    
    # Tool context
    tool_type: str = ""
    tool_config: Dict[str, Any] = field(default_factory=dict)
    
    # Performance tracking
    execution_time: float = 0.0
    
    def is_significant(self) -> bool:
        """Check if action is significant enough to save."""
        # Don't save actions with identical before/after states
        if self.before_state and self.after_state:
            if (self.before_state.elements == self.after_state.elements and
                self.before_state.geometry == self.after_state.geometry):
                return False
        
        return True
    
    def get_size_estimate(self) -> int:
        """Estimate memory size of this action in bytes."""
        size = 100  # Base size
        
        if self.before_state:
            size += len(self.before_state.elements) * 50
            if self.before_state.geometry:
                size += 32
        
        if self.after_state:
            size += len(self.after_state.elements) * 50
            if self.after_state.geometry:
                size += 32
        
        size += len(str(self.action_data)) * 2
        size += len(self.description) * 2
        
        return size


@dataclass
class HistoryBranch:
    """A branch in the history tree for advanced undo/redo."""
    branch_id: str
    parent_action_index: int
    actions: List[HistoryAction] = field(default_factory=list)
    description: str = ""
    created_timestamp: float = field(default_factory=time.time)
    
    def get_total_size(self) -> int:
        """Get total memory size of this branch."""
        return sum(action.get_size_estimate() for action in self.actions)


class SelectionHistory(QObject):
    """
    Advanced selection history system with undo/redo support.
    
    Features:
    - Linear and tree-based history modes
    - Configurable history limits and memory management
    - Action compression and optimization
    - Branch management for advanced workflows
    - Performance tracking and optimization
    - Export/import functionality
    - Automatic cleanup of insignificant actions
    """
    
    # Signals
    action_recorded = pyqtSignal(object)  # HistoryAction
    undo_performed = pyqtSignal(object)   # HistoryAction
    redo_performed = pyqtSignal(object)   # HistoryAction
    history_cleared = pyqtSignal()
    branch_created = pyqtSignal(str)      # branch_id
    branch_switched = pyqtSignal(str)     # branch_id
    limit_reached = pyqtSignal(int)       # current_size
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main history (linear mode)
        self._actions: deque = deque()
        self._current_index = -1
        
        # Tree mode support
        self._tree_mode = False
        self._branches: Dict[str, HistoryBranch] = {}
        self._current_branch = "main"
        self._branch_counter = 0
        
        # Configuration
        self._config = {
            'max_actions': 100,           # Maximum number of actions
            'max_memory_mb': 50,          # Maximum memory usage in MB
            'compress_actions': True,     # Compress similar actions
            'save_insignificant': False,  # Save insignificant actions
            'auto_cleanup': True,         # Automatic cleanup
            'cleanup_threshold': 0.8,     # Cleanup when 80% full
            'compression_window': 5,      # Actions to look back for compression
            'tree_mode': False,          # Enable tree-based history
            'action_timeout': 2.0        # Seconds to wait before finalizing action
        }
        
        # Current selection state
        self._current_selection: Optional[SelectionResult] = None
        
        # Performance tracking
        self._metrics = {
            'total_actions': 0,
            'undo_operations': 0,
            'redo_operations': 0,
            'compressed_actions': 0,
            'memory_cleanups': 0,
            'average_action_size': 0
        }
        
        # Pending action (for action compression)
        self._pending_action: Optional[HistoryAction] = None
        self._last_action_time = 0.0
    
    def record_action(self, action_type: HistoryActionType, 
                     description: str,
                     before_state: Optional[SelectionResult] = None,
                     after_state: Optional[SelectionResult] = None,
                     action_data: Optional[Dict[str, Any]] = None,
                     tool_type: str = "",
                     tool_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record a new action in the history.
        
        Args:
            action_type: Type of action
            description: Human-readable description
            before_state: State before action
            after_state: State after action
            action_data: Additional action data
            tool_type: Tool that performed the action
            tool_config: Tool configuration
            
        Returns:
            True if action was recorded
        """
        current_time = time.time()
        
        # Create action
        action = HistoryAction(
            action_type=action_type,
            timestamp=current_time,
            description=description,
            before_state=before_state,
            after_state=after_state,
            action_data=action_data or {},
            tool_type=tool_type,
            tool_config=tool_config or {}
        )
        
        # Check if action is significant
        if not self._config['save_insignificant'] and not action.is_significant():
            return False
        
        # Handle action compression
        if self._config['compress_actions']:
            if self._try_compress_action(action):
                return True
        
        # Finalize pending action if timeout reached
        if (self._pending_action and 
            current_time - self._last_action_time > self._config['action_timeout']):
            self._finalize_pending_action()
        
        # Store as pending for potential compression
        self._pending_action = action
        self._last_action_time = current_time
        
        return True
    
    def finalize_pending_action(self) -> None:
        """Finalize any pending action."""
        if self._pending_action:
            self._finalize_pending_action()
    
    def undo(self) -> Optional[SelectionResult]:
        """
        Perform undo operation.
        
        Returns:
            Previous selection state or None if no undo available
        """
        if not self.can_undo():
            return None
        
        # Finalize any pending action
        self.finalize_pending_action()
        
        if self._tree_mode:
            return self._undo_tree_mode()
        else:
            return self._undo_linear_mode()
    
    def redo(self) -> Optional[SelectionResult]:
        """
        Perform redo operation.
        
        Returns:
            Next selection state or None if no redo available
        """
        if not self.can_redo():
            return None
        
        if self._tree_mode:
            return self._redo_tree_mode()
        else:
            return self._redo_linear_mode()
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        if self._tree_mode:
            branch = self._branches.get(self._current_branch)
            return branch is not None and len(branch.actions) > 0
        else:
            return self._current_index >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        if self._tree_mode:
            # In tree mode, redo is more complex
            return False  # Simplified for now
        else:
            return self._current_index < len(self._actions) - 1
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of action that would be undone."""
        if not self.can_undo():
            return None
        
        if self._tree_mode:
            branch = self._branches.get(self._current_branch)
            if branch and branch.actions:
                return branch.actions[-1].description
        else:
            if self._current_index >= 0:
                return self._actions[self._current_index].description
        
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of action that would be redone."""
        if not self.can_redo():
            return None
        
        if not self._tree_mode and self._current_index < len(self._actions) - 1:
            return self._actions[self._current_index + 1].description
        
        return None
    
    def clear_history(self) -> None:
        """Clear all history."""
        self._actions.clear()
        self._current_index = -1
        self._branches.clear()
        self._current_branch = "main"
        self._pending_action = None
        
        self.history_cleared.emit()
    
    def get_history_list(self, max_items: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent actions for UI display."""
        actions = []
        
        if self._tree_mode:
            branch = self._branches.get(self._current_branch)
            if branch:
                recent_actions = list(branch.actions)[-max_items:]
            else:
                recent_actions = []
        else:
            recent_actions = list(self._actions)[-max_items:]
        
        for i, action in enumerate(recent_actions):
            actions.append({
                'index': i,
                'type': action.action_type.value,
                'description': action.description,
                'timestamp': action.timestamp,
                'tool_type': action.tool_type,
                'is_current': (not self._tree_mode and 
                              i == self._current_index)
            })
        
        return actions
    
    def create_branch(self, description: str = "") -> str:
        """Create a new history branch."""
        self._tree_mode = True
        self._branch_counter += 1
        branch_id = f"branch_{self._branch_counter}"
        
        # Create new branch from current state
        current_action_index = self._current_index if not self._tree_mode else -1
        
        branch = HistoryBranch(
            branch_id=branch_id,
            parent_action_index=current_action_index,
            description=description or f"Branch {self._branch_counter}"
        )
        
        self._branches[branch_id] = branch
        
        # Initialize main branch if not exists
        if "main" not in self._branches and not self._tree_mode:
            main_branch = HistoryBranch(
                branch_id="main",
                parent_action_index=-1,
                actions=list(self._actions),
                description="Main branch"
            )
            self._branches["main"] = main_branch
        
        self.branch_created.emit(branch_id)
        return branch_id
    
    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different history branch."""
        if branch_id not in self._branches:
            return False
        
        self._current_branch = branch_id
        self._tree_mode = True
        
        self.branch_switched.emit(branch_id)
        return True
    
    def get_branches(self) -> List[Dict[str, Any]]:
        """Get list of all branches."""
        return [
            {
                'id': branch_id,
                'description': branch.description,
                'actions_count': len(branch.actions),
                'created': branch.created_timestamp,
                'is_current': branch_id == self._current_branch
            }
            for branch_id, branch in self._branches.items()
        ]
    
    def optimize_memory(self) -> Dict[str, int]:
        """Optimize memory usage by cleaning up old actions."""
        initial_count = len(self._actions) if not self._tree_mode else sum(
            len(branch.actions) for branch in self._branches.values()
        )
        
        if self._tree_mode:
            self._optimize_branches()
        else:
            self._optimize_linear()
        
        final_count = len(self._actions) if not self._tree_mode else sum(
            len(branch.actions) for branch in self._branches.values()
        )
        
        removed = initial_count - final_count
        self._metrics['memory_cleanups'] += 1
        
        return {
            'actions_removed': removed,
            'memory_freed': removed * self._metrics.get('average_action_size', 1000)
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        if self._tree_mode:
            total_actions = sum(len(branch.actions) for branch in self._branches.values())
            total_size = sum(branch.get_total_size() for branch in self._branches.values())
        else:
            total_actions = len(self._actions)
            total_size = sum(action.get_size_estimate() for action in self._actions)
        
        return {
            'total_actions': total_actions,
            'estimated_size_bytes': total_size,
            'estimated_size_mb': total_size / (1024 * 1024),
            'max_actions': self._config['max_actions'],
            'max_memory_mb': self._config['max_memory_mb'],
            'usage_percent': min(100, (total_size / (1024 * 1024)) / self._config['max_memory_mb'] * 100)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics."""
        memory_info = self.get_memory_usage()
        
        return {
            'memory': memory_info,
            'metrics': self._metrics.copy(),
            'config': self._config.copy(),
            'tree_mode': self._tree_mode,
            'branches_count': len(self._branches),
            'current_branch': self._current_branch
        }
    
    def update_config(self, **kwargs) -> None:
        """Update configuration."""
        for key, value in kwargs.items():
            if key in self._config:
                self._config[key] = value
    
    # Private methods
    
    def _finalize_pending_action(self) -> None:
        """Finalize the pending action."""
        if not self._pending_action:
            return
        
        action = self._pending_action
        self._pending_action = None
        
        # Add to history
        if self._tree_mode:
            branch = self._branches.get(self._current_branch)
            if branch:
                branch.actions.append(action)
        else:
            # Remove actions after current index (for new branch)
            while len(self._actions) > self._current_index + 1:
                self._actions.pop()
            
            self._actions.append(action)
            self._current_index = len(self._actions) - 1
        
        # Update current selection
        if action.after_state:
            self._current_selection = action.after_state
        
        # Update metrics
        self._metrics['total_actions'] += 1
        self._update_average_action_size(action)
        
        # Check memory limits
        self._check_memory_limits()
        
        self.action_recorded.emit(action)
    
    def _try_compress_action(self, new_action: HistoryAction) -> bool:
        """Try to compress action with recent actions."""
        if not self._pending_action:
            return False
        
        pending = self._pending_action
        
        # Only compress actions of the same type from the same tool
        if (pending.action_type != new_action.action_type or
            pending.tool_type != new_action.tool_type):
            return False
        
        # Check if actions can be compressed
        if self._can_compress_actions(pending, new_action):
            # Merge the actions
            self._merge_actions(pending, new_action)
            self._metrics['compressed_actions'] += 1
            return True
        
        return False
    
    def _can_compress_actions(self, action1: HistoryAction, action2: HistoryAction) -> bool:
        """Check if two actions can be compressed."""
        # Time-based compression
        time_diff = action2.timestamp - action1.timestamp
        if time_diff > self._config['action_timeout']:
            return False
        
        # Type-specific compression rules
        if action1.action_type == HistoryActionType.MODIFY_SELECTION:
            return True  # Always compress modifications
        
        if action1.action_type == HistoryActionType.TRANSFORM:
            return True  # Always compress transformations
        
        return False
    
    def _merge_actions(self, action1: HistoryAction, action2: HistoryAction) -> None:
        """Merge two actions into the first one."""
        # Update timestamp to latest
        action1.timestamp = action2.timestamp
        
        # Update after state to final state
        action1.after_state = action2.after_state
        
        # Merge action data
        action1.action_data.update(action2.action_data)
        
        # Update description to indicate compression
        if "compressed" not in action1.description.lower():
            action1.description += " (compressed)"
    
    def _undo_linear_mode(self) -> Optional[SelectionResult]:
        """Undo in linear mode."""
        if self._current_index < 0:
            return None
        
        action = self._actions[self._current_index]
        self._current_index -= 1
        
        # Restore previous state
        result_state = action.before_state
        if result_state:
            self._current_selection = result_state
        
        self._metrics['undo_operations'] += 1
        self.undo_performed.emit(action)
        
        return result_state
    
    def _redo_linear_mode(self) -> Optional[SelectionResult]:
        """Redo in linear mode."""
        if self._current_index >= len(self._actions) - 1:
            return None
        
        self._current_index += 1
        action = self._actions[self._current_index]
        
        # Restore next state
        result_state = action.after_state
        if result_state:
            self._current_selection = result_state
        
        self._metrics['redo_operations'] += 1
        self.redo_performed.emit(action)
        
        return result_state
    
    def _undo_tree_mode(self) -> Optional[SelectionResult]:
        """Undo in tree mode."""
        branch = self._branches.get(self._current_branch)
        if not branch or not branch.actions:
            return None
        
        action = branch.actions.pop()
        
        # Restore previous state
        result_state = action.before_state
        if result_state:
            self._current_selection = result_state
        
        self._metrics['undo_operations'] += 1
        self.undo_performed.emit(action)
        
        return result_state
    
    def _redo_tree_mode(self) -> Optional[SelectionResult]:
        """Redo in tree mode (simplified)."""
        # Tree mode redo is complex - would need to track forward branches
        return None
    
    def _check_memory_limits(self) -> None:
        """Check and enforce memory limits."""
        usage = self.get_memory_usage()
        
        # Check action count limit
        if usage['total_actions'] > self._config['max_actions']:
            self.optimize_memory()
            return
        
        # Check memory size limit
        if usage['estimated_size_mb'] > self._config['max_memory_mb']:
            self.optimize_memory()
            self.limit_reached.emit(int(usage['estimated_size_mb']))
            return
        
        # Auto cleanup if threshold reached
        if (self._config['auto_cleanup'] and 
            usage['usage_percent'] > self._config['cleanup_threshold'] * 100):
            self.optimize_memory()
    
    def _optimize_linear(self) -> None:
        """Optimize linear history."""
        target_size = int(self._config['max_actions'] * 0.8)
        
        if len(self._actions) > target_size:
            # Remove oldest actions
            remove_count = len(self._actions) - target_size
            
            for _ in range(remove_count):
                self._actions.popleft()
                if self._current_index >= 0:
                    self._current_index -= 1
    
    def _optimize_branches(self) -> None:
        """Optimize tree history."""
        for branch in self._branches.values():
            target_size = int(self._config['max_actions'] * 0.8)
            
            if len(branch.actions) > target_size:
                # Remove oldest actions from branch
                remove_count = len(branch.actions) - target_size
                branch.actions = branch.actions[remove_count:]
    
    def _update_average_action_size(self, action: HistoryAction) -> None:
        """Update average action size metric."""
        size = action.get_size_estimate()
        count = self._metrics['total_actions']
        current_avg = self._metrics['average_action_size']
        
        self._metrics['average_action_size'] = (
            (current_avg * (count - 1) + size) / count
        )