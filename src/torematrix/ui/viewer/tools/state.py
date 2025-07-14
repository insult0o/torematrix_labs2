"""
Tool state management system.

This module provides state tracking, validation, and transition management
for selection tools including state machines and persistence.
"""

import time
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal

from .base import ToolState


@dataclass
class StateTransition:
    """Represents a state transition."""
    from_state: ToolState
    to_state: ToolState
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration_since(self) -> float:
        """Get duration since this transition occurred."""
        return time.time() - self.timestamp


@dataclass
class StateSnapshot:
    """Snapshot of tool state at a point in time."""
    state: ToolState
    timestamp: float = field(default_factory=time.time)
    tool_id: str = ""
    selection_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def age(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp


class StateValidationRule:
    """Rule for validating state transitions."""
    
    def __init__(self, name: str, condition: Callable[[ToolState, ToolState], bool], error_message: str = ""):
        self.name = name
        self.condition = condition
        self.error_message = error_message or f"Validation rule '{name}' failed"
    
    def validate(self, from_state: ToolState, to_state: ToolState) -> bool:
        """Validate transition."""
        return self.condition(from_state, to_state)


class ToolStateManager(QObject):
    """
    Advanced tool state management with validation, history, and persistence.
    
    Manages tool states, validates transitions, tracks history, and provides
    state persistence and recovery capabilities.
    """
    
    # Signals
    state_changed = pyqtSignal(object, object)  # (from_state, to_state)
    transition_failed = pyqtSignal(object, object, str)  # (from_state, to_state, reason)
    validation_failed = pyqtSignal(str, str)  # (rule_name, error_message)
    history_updated = pyqtSignal()  # History changed
    
    def __init__(self, tool_id: str = "", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.tool_id = tool_id
        
        # Current state
        self._current_state = ToolState.INACTIVE
        self._previous_state: Optional[ToolState] = None
        self._state_entry_time = time.time()
        
        # Transition rules
        self._valid_transitions: Dict[ToolState, Set[ToolState]] = {
            ToolState.INACTIVE: {ToolState.ACTIVE},
            ToolState.ACTIVE: {ToolState.INACTIVE, ToolState.SELECTING, ToolState.HOVER, ToolState.SELECTED},
            ToolState.HOVER: {ToolState.ACTIVE, ToolState.SELECTING, ToolState.SELECTED},
            ToolState.SELECTING: {ToolState.ACTIVE, ToolState.SELECTED, ToolState.HOVER},
            ToolState.SELECTED: {ToolState.ACTIVE, ToolState.SELECTING, ToolState.DRAG, ToolState.RESIZE, ToolState.MOVE},
            ToolState.DRAG: {ToolState.SELECTED, ToolState.ACTIVE},
            ToolState.RESIZE: {ToolState.SELECTED, ToolState.ACTIVE},
            ToolState.MOVE: {ToolState.SELECTED, ToolState.ACTIVE}
        }
        
        # State history
        self._history: List[StateTransition] = []
        self._max_history_size = 100
        
        # State snapshots for debugging/analysis
        self._snapshots: List[StateSnapshot] = []
        self._max_snapshots = 50
        
        # Validation rules
        self._validation_rules: List[StateValidationRule] = []
        self._setup_default_validation_rules()
        
        # State metadata
        self._state_metadata: Dict[ToolState, Dict[str, Any]] = {}
        
        # State timing
        self._state_durations: Dict[ToolState, List[float]] = {}
        
        # Persistence
        self._persist_state = False
        self._state_file_path = ""
    
    def _setup_default_validation_rules(self) -> None:
        """Setup default validation rules."""
        # Rule: Can't transition to same state
        self.add_validation_rule(
            "no_self_transition",
            lambda from_state, to_state: from_state != to_state,
            "Cannot transition to the same state"
        )
        
        # Rule: Must be valid transition
        self.add_validation_rule(
            "valid_transition",
            lambda from_state, to_state: to_state in self._valid_transitions.get(from_state, set()),
            "Invalid state transition"
        )
    
    def add_validation_rule(self, name: str, condition: Callable[[ToolState, ToolState], bool], error_message: str = "") -> None:
        """Add a custom validation rule."""
        rule = StateValidationRule(name, condition, error_message)
        self._validation_rules.append(rule)
    
    def remove_validation_rule(self, name: str) -> bool:
        """Remove a validation rule by name."""
        for i, rule in enumerate(self._validation_rules):
            if rule.name == name:
                del self._validation_rules[i]
                return True
        return False
    
    def add_valid_transition(self, from_state: ToolState, to_state: ToolState) -> None:
        """Add a valid transition."""
        if from_state not in self._valid_transitions:
            self._valid_transitions[from_state] = set()
        self._valid_transitions[from_state].add(to_state)
    
    def remove_valid_transition(self, from_state: ToolState, to_state: ToolState) -> bool:
        """Remove a valid transition."""
        if from_state in self._valid_transitions:
            if to_state in self._valid_transitions[from_state]:
                self._valid_transitions[from_state].remove(to_state)
                return True
        return False
    
    def can_transition(self, to_state: ToolState) -> bool:
        """Check if transition to new state is valid."""
        return self._validate_transition(self._current_state, to_state)
    
    def _validate_transition(self, from_state: ToolState, to_state: ToolState) -> bool:
        """Validate transition using all rules."""
        for rule in self._validation_rules:
            if not rule.validate(from_state, to_state):
                self.validation_failed.emit(rule.name, rule.error_message)
                return False
        return True
    
    def transition(self, to_state: ToolState, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transition to new state if valid.
        
        Args:
            to_state: Target state
            metadata: Optional metadata for transition
            
        Returns:
            True if transition successful
        """
        if not self._validate_transition(self._current_state, to_state):
            self.transition_failed.emit(self._current_state, to_state, "Validation failed")
            return False
        
        # Record state duration
        duration = time.time() - self._state_entry_time
        self._record_state_duration(self._current_state, duration)
        
        # Create transition record
        transition = StateTransition(
            from_state=self._current_state,
            to_state=to_state,
            metadata=metadata or {}
        )
        
        # Update state
        self._previous_state = self._current_state
        self._current_state = to_state
        self._state_entry_time = time.time()
        
        # Record transition
        self._add_to_history(transition)
        
        # Create snapshot
        self._create_snapshot()
        
        # Emit signals
        self.state_changed.emit(self._previous_state, self._current_state)
        self.history_updated.emit()
        
        # Persist if enabled
        if self._persist_state:
            self._save_state()
        
        return True
    
    def force_transition(self, to_state: ToolState, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Force transition without validation (use carefully)."""
        # Record state duration
        duration = time.time() - self._state_entry_time
        self._record_state_duration(self._current_state, duration)
        
        # Create transition record
        transition = StateTransition(
            from_state=self._current_state,
            to_state=to_state,
            metadata=(metadata or {}) | {"forced": True}
        )
        
        # Update state
        self._previous_state = self._current_state
        self._current_state = to_state
        self._state_entry_time = time.time()
        
        # Record transition
        self._add_to_history(transition)
        
        # Create snapshot
        self._create_snapshot()
        
        # Emit signals
        self.state_changed.emit(self._previous_state, self._current_state)
        self.history_updated.emit()
    
    def _record_state_duration(self, state: ToolState, duration: float) -> None:
        """Record how long was spent in a state."""
        if state not in self._state_durations:
            self._state_durations[state] = []
        self._state_durations[state].append(duration)
        
        # Keep only recent durations
        if len(self._state_durations[state]) > 100:
            self._state_durations[state] = self._state_durations[state][-100:]
    
    def get_current_state(self) -> ToolState:
        """Get current state."""
        return self._current_state
    
    def get_previous_state(self) -> Optional[ToolState]:
        """Get previous state."""
        return self._previous_state
    
    def get_time_in_current_state(self) -> float:
        """Get time spent in current state."""
        return time.time() - self._state_entry_time
    
    def get_state_metadata(self, state: ToolState) -> Dict[str, Any]:
        """Get metadata for a state."""
        return self._state_metadata.get(state, {}).copy()
    
    def set_state_metadata(self, state: ToolState, metadata: Dict[str, Any]) -> None:
        """Set metadata for a state."""
        self._state_metadata[state] = metadata.copy()
    
    def update_state_metadata(self, state: ToolState, key: str, value: Any) -> None:
        """Update specific metadata for a state."""
        if state not in self._state_metadata:
            self._state_metadata[state] = {}
        self._state_metadata[state][key] = value
    
    def reset(self) -> None:
        """Reset to inactive state."""
        if self._current_state != ToolState.INACTIVE:
            self.force_transition(ToolState.INACTIVE, {"reset": True})
    
    def _add_to_history(self, transition: StateTransition) -> None:
        """Add transition to history."""
        self._history.append(transition)
        
        # Trim history if too long
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]
    
    def _create_snapshot(self) -> None:
        """Create state snapshot."""
        snapshot = StateSnapshot(
            state=self._current_state,
            tool_id=self.tool_id,
            metadata=self.get_state_metadata(self._current_state)
        )
        
        self._snapshots.append(snapshot)
        
        # Trim snapshots if too many
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
    
    def get_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get state transition history."""
        if limit is None:
            return self._history.copy()
        return self._history[-limit:].copy()
    
    def get_recent_transitions(self, seconds: float) -> List[StateTransition]:
        """Get transitions within recent time period."""
        cutoff_time = time.time() - seconds
        return [t for t in self._history if t.timestamp >= cutoff_time]
    
    def get_snapshots(self, limit: Optional[int] = None) -> List[StateSnapshot]:
        """Get state snapshots."""
        if limit is None:
            return self._snapshots.copy()
        return self._snapshots[-limit:].copy()
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state usage statistics."""
        stats = {
            'current_state': self._current_state.value,
            'time_in_current_state': self.get_time_in_current_state(),
            'total_transitions': len(self._history),
            'states_visited': len(set(t.to_state for t in self._history)),
            'average_durations': {},
            'transition_counts': {},
            'most_common_state': None,
            'least_common_state': None
        }
        
        # Calculate average durations
        for state, durations in self._state_durations.items():
            if durations:
                stats['average_durations'][state.value] = sum(durations) / len(durations)
        
        # Count transitions
        transition_counts = {}
        for transition in self._history:
            key = f"{transition.from_state.value} -> {transition.to_state.value}"
            transition_counts[key] = transition_counts.get(key, 0) + 1
        
        stats['transition_counts'] = transition_counts
        
        # Find most/least common states
        state_counts = {}
        for transition in self._history:
            state_counts[transition.to_state] = state_counts.get(transition.to_state, 0) + 1
        
        if state_counts:
            most_common = max(state_counts.items(), key=lambda x: x[1])
            least_common = min(state_counts.items(), key=lambda x: x[1])
            stats['most_common_state'] = most_common[0].value
            stats['least_common_state'] = least_common[0].value
        
        return stats
    
    def clear_history(self) -> None:
        """Clear state history."""
        self._history.clear()
        self._snapshots.clear()
        self._state_durations.clear()
        self.history_updated.emit()
    
    def enable_persistence(self, file_path: str) -> None:
        """Enable state persistence to file."""
        self._persist_state = True
        self._state_file_path = file_path
    
    def disable_persistence(self) -> None:
        """Disable state persistence."""
        self._persist_state = False
        self._state_file_path = ""
    
    def _save_state(self) -> None:
        """Save current state to file."""
        if not self._state_file_path:
            return
        
        try:
            import json
            state_data = {
                'current_state': self._current_state.value,
                'previous_state': self._previous_state.value if self._previous_state else None,
                'state_entry_time': self._state_entry_time,
                'tool_id': self.tool_id,
                'metadata': {state.value: data for state, data in self._state_metadata.items()}
            }
            
            with open(self._state_file_path, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            # Don't fail if persistence fails
            pass
    
    def load_state(self, file_path: str) -> bool:
        """Load state from file."""
        try:
            import json
            with open(file_path, 'r') as f:
                state_data = json.load(f)
            
            # Restore state
            current_state = ToolState(state_data['current_state'])
            previous_state = ToolState(state_data['previous_state']) if state_data['previous_state'] else None
            
            self._current_state = current_state
            self._previous_state = previous_state
            self._state_entry_time = state_data.get('state_entry_time', time.time())
            
            # Restore metadata
            metadata = state_data.get('metadata', {})
            self._state_metadata = {ToolState(state): data for state, data in metadata.items()}
            
            return True
        except Exception as e:
            return False


class MultiToolStateManager(QObject):
    """Manager for multiple tool state managers."""
    
    # Signals
    tool_state_changed = pyqtSignal(str, object, object)  # (tool_id, from_state, to_state)
    active_tool_changed = pyqtSignal(str, str)  # (old_tool_id, new_tool_id)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tool_managers: Dict[str, ToolStateManager] = {}
        self._active_tool_id: Optional[str] = None
    
    def add_tool(self, tool_id: str) -> ToolStateManager:
        """Add a tool state manager."""
        if tool_id in self._tool_managers:
            return self._tool_managers[tool_id]
        
        manager = ToolStateManager(tool_id, self)
        manager.state_changed.connect(
            lambda from_state, to_state, tid=tool_id: self.tool_state_changed.emit(tid, from_state, to_state)
        )
        
        self._tool_managers[tool_id] = manager
        return manager
    
    def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool state manager."""
        if tool_id in self._tool_managers:
            if self._active_tool_id == tool_id:
                self._active_tool_id = None
            
            self._tool_managers[tool_id].deleteLater()
            del self._tool_managers[tool_id]
            return True
        return False
    
    def get_tool_manager(self, tool_id: str) -> Optional[ToolStateManager]:
        """Get tool state manager."""
        return self._tool_managers.get(tool_id)
    
    def set_active_tool(self, tool_id: str) -> bool:
        """Set active tool."""
        if tool_id not in self._tool_managers:
            return False
        
        old_tool_id = self._active_tool_id
        self._active_tool_id = tool_id
        
        if old_tool_id != tool_id:
            self.active_tool_changed.emit(old_tool_id or "", tool_id)
        
        return True
    
    def get_active_tool_manager(self) -> Optional[ToolStateManager]:
        """Get active tool state manager."""
        if self._active_tool_id:
            return self._tool_managers.get(self._active_tool_id)
        return None
    
    def get_active_tool_id(self) -> Optional[str]:
        """Get active tool ID."""
        return self._active_tool_id
    
    def get_all_tool_ids(self) -> List[str]:
        """Get all tool IDs."""
        return list(self._tool_managers.keys())
    
    def get_all_states(self) -> Dict[str, ToolState]:
        """Get current state of all tools."""
        return {tool_id: manager.get_current_state() 
                for tool_id, manager in self._tool_managers.items()}
    
    def deactivate_all_tools(self) -> None:
        """Deactivate all tools."""
        for manager in self._tool_managers.values():
            if manager.get_current_state() != ToolState.INACTIVE:
                manager.reset()
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get statistics for all tools."""
        stats = {
            'total_tools': len(self._tool_managers),
            'active_tool': self._active_tool_id,
            'tool_stats': {}
        }
        
        for tool_id, manager in self._tool_managers.items():
            stats['tool_stats'][tool_id] = manager.get_state_statistics()
        
        return stats