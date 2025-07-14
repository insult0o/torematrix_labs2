"""
Time-travel debugging system for state management.

This module provides comprehensive time-travel debugging capabilities,
allowing developers to record, replay, and navigate through state changes.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import logging
import copy
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class HistoryDirection(Enum):
    """Direction for history navigation."""
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class HistoryEntry:
    """
    A single entry in the history timeline.
    
    Records the state before and after an action, along with metadata
    for debugging and analysis.
    """
    id: str
    timestamp: float
    action: Any
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    
    def __post_init__(self):
        """Post-initialization to add derived fields."""
        if not self.metadata:
            self.metadata = {}
        
        # Add action metadata
        action_type = getattr(self.action, "__class__", {}).get("__name__", str(type(self.action)))
        self.metadata.update({
            "action_type": action_type,
            "action_id": getattr(self.action, "id", None),
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self._serialize_action(),
            "state_before": self.state_before,
            "state_after": self.state_after,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }
    
    def _serialize_action(self) -> Dict[str, Any]:
        """Serialize action for storage."""
        if hasattr(self.action, "to_dict"):
            return self.action.to_dict()
        elif hasattr(self.action, "__dict__"):
            return self.action.__dict__
        else:
            return {"action": str(self.action)}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        """Create from dictionary."""
        # For now, store action as dict - would need proper deserialization
        # in a real implementation based on action types
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            action=data["action"],
            state_before=data["state_before"],
            state_after=data["state_after"],
            metadata=data.get("metadata", {}),
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass
class HistoryBranch:
    """
    Represents a branch in the history timeline.
    
    Allows for non-linear history when time-traveling and making new changes.
    """
    id: str
    name: str
    parent_entry_id: Optional[str]
    created_at: float
    entries: List[HistoryEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimeTravel:
    """
    Time-travel debugging system.
    
    Provides comprehensive debugging capabilities including:
    - Action recording and replay
    - State navigation (forward/backward)
    - History branching
    - State comparison
    - Performance analysis
    """
    
    def __init__(
        self,
        max_history: int = 1000,
        enable_branching: bool = True,
        auto_prune: bool = True,
        compression_enabled: bool = False
    ):
        self.max_history = max_history
        self.enable_branching = enable_branching
        self.auto_prune = auto_prune
        self.compression_enabled = compression_enabled
        
        # History storage
        self._history: List[HistoryEntry] = []
        self._current_index: int = -1
        self._branches: Dict[str, HistoryBranch] = {}
        self._current_branch_id: str = "main"
        
        # State management
        self._replaying = False
        self._recording_enabled = True
        
        # Callbacks
        self._on_history_change: List[Callable] = []
        self._on_time_travel: List[Callable] = []
        
        # Performance tracking
        self._stats = {
            "total_actions": 0,
            "average_duration": 0.0,
            "memory_usage": 0,
        }
        
        # Create main branch
        self._branches["main"] = HistoryBranch(
            id="main",
            name="Main Timeline",
            parent_entry_id=None,
            created_at=time.time(),
            entries=self._history
        )
    
    def record_action(
        self,
        action: Any,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an action in the history.
        
        Args:
            action: The action that was executed
            state_before: State before the action
            state_after: State after the action
            duration_ms: How long the action took to execute
            metadata: Additional metadata about the action
            
        Returns:
            The ID of the created history entry
        """
        if not self._recording_enabled or self._replaying:
            return ""
        
        # Generate unique ID
        entry_id = f"entry_{int(time.time() * 1000000)}"
        
        # Create history entry
        entry = HistoryEntry(
            id=entry_id,
            timestamp=time.time(),
            action=self._deep_copy_if_needed(action),
            state_before=self._deep_copy_if_needed(state_before),
            state_after=self._deep_copy_if_needed(state_after),
            metadata=metadata or {},
            duration_ms=duration_ms
        )
        
        # If we're not at the end of history and branching is disabled,
        # truncate history from current position
        if not self.enable_branching and self._current_index < len(self._history) - 1:
            self._history = self._history[:self._current_index + 1]
        
        # Add to history
        self._history.append(entry)
        self._current_index = len(self._history) - 1
        
        # Update stats
        self._update_stats(entry)
        
        # Auto-prune if necessary
        if self.auto_prune and len(self._history) > self.max_history:
            self._prune_old_entries()
        
        # Notify listeners
        self._notify_history_change()
        
        logger.debug(f"Recorded action in history: {entry_id}")
        return entry_id
    
    def travel_to(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Travel to a specific point in history.
        
        Args:
            index: The history index to travel to
            
        Returns:
            The state at that point, or None if index is invalid
        """
        if not self._is_valid_index(index):
            logger.warning(f"Invalid history index: {index}")
            return None
        
        old_index = self._current_index
        self._current_index = index
        
        entry = self._history[index]
        state = copy.deepcopy(entry.state_after)
        
        # Notify listeners
        self._notify_time_travel(old_index, index, state)
        
        logger.debug(f"Time traveled from index {old_index} to {index}")
        return state
    
    def travel_to_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Travel to a specific history entry by ID.
        
        Args:
            entry_id: The ID of the history entry
            
        Returns:
            The state at that point, or None if entry not found
        """
        for i, entry in enumerate(self._history):
            if entry.id == entry_id:
                return self.travel_to(i)
        
        logger.warning(f"History entry not found: {entry_id}")
        return None
    
    def travel_forward(self, steps: int = 1) -> Optional[Dict[str, Any]]:
        """
        Travel forward in history.
        
        Args:
            steps: Number of steps to move forward
            
        Returns:
            The new current state, or None if can't move forward
        """
        new_index = self._current_index + steps
        if new_index >= len(self._history):
            logger.debug("Already at the end of history")
            return None
        
        return self.travel_to(new_index)
    
    def travel_backward(self, steps: int = 1) -> Optional[Dict[str, Any]]:
        """
        Travel backward in history.
        
        Args:
            steps: Number of steps to move backward
            
        Returns:
            The new current state, or None if can't move backward
        """
        new_index = self._current_index - steps
        if new_index < 0:
            logger.debug("Already at the beginning of history")
            return None
        
        return self.travel_to(new_index)
    
    def replay_from(self, start_index: int) -> List[Any]:
        """
        Replay actions from a specific point in history.
        
        Args:
            start_index: Index to start replaying from
            
        Returns:
            List of actions that were replayed
        """
        if not self._is_valid_index(start_index):
            return []
        
        actions = []
        for i in range(start_index, len(self._history)):
            entry = self._history[i]
            actions.append(entry.action)
        
        logger.debug(f"Replayed {len(actions)} actions from index {start_index}")
        return actions
    
    def create_branch(
        self,
        name: str,
        from_entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new history branch.
        
        Args:
            name: Name for the new branch
            from_entry_id: Entry ID to branch from, or None for current
            metadata: Additional metadata for the branch
            
        Returns:
            The ID of the created branch
        """
        if not self.enable_branching:
            raise ValueError("Branching is disabled")
        
        branch_id = f"branch_{int(time.time() * 1000000)}"
        
        # Find the entry to branch from
        parent_entry_id = from_entry_id
        if parent_entry_id is None and self._current_index >= 0:
            parent_entry_id = self._history[self._current_index].id
        
        # Create new branch
        branch = HistoryBranch(
            id=branch_id,
            name=name,
            parent_entry_id=parent_entry_id,
            created_at=time.time(),
            metadata=metadata or {}
        )
        
        self._branches[branch_id] = branch
        
        logger.debug(f"Created history branch: {branch_id} ({name})")
        return branch_id
    
    def switch_branch(self, branch_id: str) -> bool:
        """
        Switch to a different history branch.
        
        Args:
            branch_id: ID of the branch to switch to
            
        Returns:
            True if switch was successful
        """
        if branch_id not in self._branches:
            logger.warning(f"Branch not found: {branch_id}")
            return False
        
        self._current_branch_id = branch_id
        branch = self._branches[branch_id]
        self._history = branch.entries
        self._current_index = len(self._history) - 1
        
        logger.debug(f"Switched to branch: {branch_id}")
        return True
    
    def get_current_entry(self) -> Optional[HistoryEntry]:
        """Get the current history entry."""
        if self._current_index >= 0 and self._current_index < len(self._history):
            return self._history[self._current_index]
        return None
    
    def get_history_summary(self) -> Dict[str, Any]:
        """Get a summary of the history."""
        return {
            "total_entries": len(self._history),
            "current_index": self._current_index,
            "current_branch": self._current_branch_id,
            "total_branches": len(self._branches),
            "memory_usage": self._estimate_memory_usage(),
            "stats": self._stats.copy(),
            "can_go_back": self._current_index > 0,
            "can_go_forward": self._current_index < len(self._history) - 1,
        }
    
    def export_history(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """
        Export history in various formats.
        
        Args:
            format: Export format ("json", "dict")
            
        Returns:
            Exported history data
        """
        data = {
            "branches": {
                branch_id: {
                    "id": branch.id,
                    "name": branch.name,
                    "parent_entry_id": branch.parent_entry_id,
                    "created_at": branch.created_at,
                    "metadata": branch.metadata,
                    "entries": [entry.to_dict() for entry in branch.entries]
                }
                for branch_id, branch in self._branches.items()
            },
            "current_branch": self._current_branch_id,
            "current_index": self._current_index,
            "stats": self._stats,
            "exported_at": time.time()
        }
        
        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return data
    
    def import_history(self, data: Union[str, Dict[str, Any]]) -> bool:
        """
        Import history from exported data.
        
        Args:
            data: Exported history data
            
        Returns:
            True if import was successful
        """
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            # Clear current history
            self.clear_history()
            
            # Import branches
            for branch_id, branch_data in data.get("branches", {}).items():
                entries = [HistoryEntry.from_dict(entry_data) 
                          for entry_data in branch_data.get("entries", [])]
                
                branch = HistoryBranch(
                    id=branch_data["id"],
                    name=branch_data["name"],
                    parent_entry_id=branch_data.get("parent_entry_id"),
                    created_at=branch_data["created_at"],
                    entries=entries,
                    metadata=branch_data.get("metadata", {})
                )
                
                self._branches[branch_id] = branch
            
            # Set current branch and index
            self._current_branch_id = data.get("current_branch", "main")
            if self._current_branch_id in self._branches:
                self._history = self._branches[self._current_branch_id].entries
                self._current_index = data.get("current_index", -1)
            
            # Import stats
            self._stats.update(data.get("stats", {}))
            
            logger.info("History imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import history: {e}")
            return False
    
    def clear_history(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._current_index = -1
        self._branches.clear()
        self._current_branch_id = "main"
        
        # Recreate main branch
        self._branches["main"] = HistoryBranch(
            id="main",
            name="Main Timeline",
            parent_entry_id=None,
            created_at=time.time(),
            entries=self._history
        )
        
        self._stats = {
            "total_actions": 0,
            "average_duration": 0.0,
            "memory_usage": 0,
        }
        
        logger.debug("History cleared")
    
    def enable_recording(self) -> None:
        """Enable history recording."""
        self._recording_enabled = True
        logger.debug("History recording enabled")
    
    def disable_recording(self) -> None:
        """Disable history recording."""
        self._recording_enabled = False
        logger.debug("History recording disabled")
    
    def is_recording(self) -> bool:
        """Check if recording is enabled."""
        return self._recording_enabled and not self._replaying
    
    def add_history_change_listener(self, callback: Callable) -> None:
        """Add a listener for history changes."""
        self._on_history_change.append(callback)
    
    def add_time_travel_listener(self, callback: Callable) -> None:
        """Add a listener for time travel events."""
        self._on_time_travel.append(callback)
    
    def remove_history_change_listener(self, callback: Callable) -> None:
        """Remove a history change listener."""
        if callback in self._on_history_change:
            self._on_history_change.remove(callback)
    
    def remove_time_travel_listener(self, callback: Callable) -> None:
        """Remove a time travel listener."""
        if callback in self._on_time_travel:
            self._on_time_travel.remove(callback)
    
    # Private methods
    
    def _is_valid_index(self, index: int) -> bool:
        """Check if an index is valid."""
        return 0 <= index < len(self._history)
    
    def _deep_copy_if_needed(self, obj: Any) -> Any:
        """Deep copy object if needed for history storage."""
        try:
            return copy.deepcopy(obj)
        except Exception:
            # Fallback to shallow copy if deep copy fails
            logger.warning("Deep copy failed, using shallow copy")
            return copy.copy(obj)
    
    def _update_stats(self, entry: HistoryEntry) -> None:
        """Update performance statistics."""
        self._stats["total_actions"] += 1
        
        # Update average duration
        total_duration = (self._stats["average_duration"] * (self._stats["total_actions"] - 1) + 
                         entry.duration_ms)
        self._stats["average_duration"] = total_duration / self._stats["total_actions"]
        
        # Update memory usage estimate
        self._stats["memory_usage"] = self._estimate_memory_usage()
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of the history."""
        # Simple estimation based on JSON serialization
        try:
            sample_entries = self._history[:min(10, len(self._history))]
            if not sample_entries:
                return 0
            
            sample_size = sum(len(json.dumps(entry.to_dict()).encode('utf-8')) 
                            for entry in sample_entries)
            average_size = sample_size / len(sample_entries)
            return int(average_size * len(self._history))
        except Exception:
            return 0
    
    def _prune_old_entries(self) -> None:
        """Remove old entries to stay within memory limits."""
        if len(self._history) <= self.max_history:
            return
        
        # Keep the most recent entries
        entries_to_remove = len(self._history) - self.max_history
        self._history = self._history[entries_to_remove:]
        
        # Adjust current index
        self._current_index = max(0, self._current_index - entries_to_remove)
        
        logger.debug(f"Pruned {entries_to_remove} old history entries")
    
    def _notify_history_change(self) -> None:
        """Notify listeners of history changes."""
        for callback in self._on_history_change:
            try:
                callback(self)
            except Exception as e:
                logger.warning(f"History change listener failed: {e}")
    
    def _notify_time_travel(self, old_index: int, new_index: int, state: Dict[str, Any]) -> None:
        """Notify listeners of time travel events."""
        for callback in self._on_time_travel:
            try:
                callback(old_index, new_index, state)
            except Exception as e:
                logger.warning(f"Time travel listener failed: {e}")


class TimeTravelMiddleware:
    """Middleware for automatic time-travel integration with state stores."""
    
    def __init__(self, time_travel: TimeTravel):
        self.time_travel = time_travel
        
    async def __call__(self, store, next_middleware: Callable, action: Any) -> Any:
        """
        Middleware function that records actions in history.
        
        Args:
            store: The state store
            next_middleware: The next middleware in the chain
            action: The action being dispatched
            
        Returns:
            The result of the action
        """
        # Skip recording if we're replaying or recording is disabled
        if not self.time_travel.is_recording():
            return await next_middleware(action)
        
        # Get state before action
        state_before = store.get_state()
        start_time = time.time()
        
        try:
            # Execute the action
            result = await next_middleware(action)
            
            # Get state after action
            state_after = store.get_state()
            duration_ms = (time.time() - start_time) * 1000
            
            # Record in history
            self.time_travel.record_action(
                action=action,
                state_before=state_before,
                state_after=state_after,
                duration_ms=duration_ms
            )
            
            return result
            
        except Exception as e:
            # Record failed action
            duration_ms = (time.time() - start_time) * 1000
            self.time_travel.record_action(
                action=action,
                state_before=state_before,
                state_after=state_before,  # State unchanged on error
                duration_ms=duration_ms,
                metadata={"error": str(e), "failed": True}
            )
            raise