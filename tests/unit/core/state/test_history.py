"""
Tests for time-travel history system.

Comprehensive tests for history recording, navigation, and debugging features.
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock
import copy

from src.torematrix.core.state.history import (
    TimeTravel, HistoryEntry, HistoryBranch, TimeTravelMiddleware,
    HistoryDirection
)


class TestHistoryEntry:
    """Test HistoryEntry functionality."""
    
    def test_history_entry_creation(self):
        """Test creating a history entry."""
        action = {"type": "test_action", "payload": {"id": 1}}
        state_before = {"counter": 0}
        state_after = {"counter": 1}
        
        entry = HistoryEntry(
            id="test_entry",
            timestamp=time.time(),
            action=action,
            state_before=state_before,
            state_after=state_after,
            duration_ms=10.5
        )
        
        assert entry.id == "test_entry"
        assert entry.action == action
        assert entry.state_before == state_before
        assert entry.state_after == state_after
        assert entry.duration_ms == 10.5
        assert "action_type" in entry.metadata
    
    def test_history_entry_serialization(self):
        """Test history entry to/from dict conversion."""
        action = {"type": "test_action"}
        entry = HistoryEntry(
            id="serial_test",
            timestamp=time.time(),
            action=action,
            state_before={"a": 1},
            state_after={"a": 2}
        )
        
        # Convert to dict
        entry_dict = entry.to_dict()
        assert entry_dict["id"] == "serial_test"
        assert entry_dict["action"] == action
        
        # Convert back from dict
        restored_entry = HistoryEntry.from_dict(entry_dict)
        assert restored_entry.id == entry.id
        assert restored_entry.action == entry.action


class TestTimeTravel:
    """Test TimeTravel functionality."""
    
    @pytest.fixture
    def time_travel(self):
        """Create TimeTravel instance for testing."""
        return TimeTravel(max_history=100, enable_branching=True)
    
    def test_initialization(self, time_travel):
        """Test TimeTravel initialization."""
        assert time_travel.max_history == 100
        assert time_travel.enable_branching is True
        assert len(time_travel._history) == 0
        assert time_travel._current_index == -1
        assert "main" in time_travel._branches
    
    def test_record_action(self, time_travel):
        """Test recording actions in history."""
        action = {"type": "increment"}
        state_before = {"counter": 0}
        state_after = {"counter": 1}
        
        entry_id = time_travel.record_action(
            action=action,
            state_before=state_before,
            state_after=state_after,
            duration_ms=5.0
        )
        
        assert entry_id != ""
        assert len(time_travel._history) == 1
        assert time_travel._current_index == 0
        
        entry = time_travel._history[0]
        assert entry.action == action
        assert entry.state_before == state_before
        assert entry.state_after == state_after
        assert entry.duration_ms == 5.0
    
    def test_multiple_actions(self, time_travel):
        """Test recording multiple actions."""
        actions = [
            {"type": "increment"},
            {"type": "increment"},
            {"type": "decrement"}
        ]
        
        state = {"counter": 0}
        for action in actions:
            new_state = copy.deepcopy(state)
            if action["type"] == "increment":
                new_state["counter"] += 1
            else:
                new_state["counter"] -= 1
            
            time_travel.record_action(action, state, new_state)
            state = new_state
        
        assert len(time_travel._history) == 3
        assert time_travel._current_index == 2
        assert time_travel._history[-1].state_after["counter"] == 1
    
    def test_time_travel_to_index(self, time_travel):
        """Test traveling to specific history index."""
        # Record some history
        states = [{"counter": i} for i in range(5)]
        for i in range(1, len(states)):
            time_travel.record_action(
                {"type": "increment"},
                states[i-1],
                states[i]
            )
        
        # Travel to index 2
        state = time_travel.travel_to(2)
        assert state == {"counter": 2}
        assert time_travel._current_index == 2
        
        # Travel to index 0
        state = time_travel.travel_to(0)
        assert state == {"counter": 1}
        assert time_travel._current_index == 0
        
        # Invalid index
        state = time_travel.travel_to(10)
        assert state is None
        assert time_travel._current_index == 0  # Unchanged
    
    def test_travel_forward_backward(self, time_travel):
        """Test forward/backward navigation."""
        # Record history
        for i in range(5):
            time_travel.record_action(
                {"type": "action", "step": i},
                {"step": i},
                {"step": i + 1}
            )
        
        # Currently at index 4, travel backward
        state = time_travel.travel_backward(2)
        assert time_travel._current_index == 2
        assert state == {"step": 3}
        
        # Travel forward
        state = time_travel.travel_forward(1)
        assert time_travel._current_index == 3
        assert state == {"step": 4}
        
        # Try to travel beyond bounds
        state = time_travel.travel_forward(10)
        assert state is None
        assert time_travel._current_index == 3  # Unchanged
        
        # Travel to beginning and try to go back further
        time_travel.travel_to(0)
        state = time_travel.travel_backward(1)
        assert state is None
        assert time_travel._current_index == 0
    
    def test_travel_to_entry_id(self, time_travel):
        """Test traveling to entry by ID."""
        # Record actions and save entry IDs
        entry_ids = []
        for i in range(3):
            entry_id = time_travel.record_action(
                {"type": "action", "value": i},
                {"value": i},
                {"value": i + 1}
            )
            entry_ids.append(entry_id)
        
        # Travel to specific entry
        state = time_travel.travel_to_entry(entry_ids[1])
        assert state == {"value": 2}
        assert time_travel._current_index == 1
        
        # Try non-existent entry
        state = time_travel.travel_to_entry("non_existent")
        assert state is None
    
    def test_replay_from_index(self, time_travel):
        """Test replaying actions from specific index."""
        # Record actions
        actions = [
            {"type": "add", "value": 1},
            {"type": "add", "value": 2},
            {"type": "subtract", "value": 1}
        ]
        
        state = {"total": 0}
        for action in actions:
            new_state = copy.deepcopy(state)
            if action["type"] == "add":
                new_state["total"] += action["value"]
            else:
                new_state["total"] -= action["value"]
            
            time_travel.record_action(action, state, new_state)
            state = new_state
        
        # Replay from index 1
        replayed_actions = time_travel.replay_from(1)
        assert len(replayed_actions) == 2
        assert replayed_actions[0] == actions[1]
        assert replayed_actions[1] == actions[2]
    
    def test_branching(self, time_travel):
        """Test history branching functionality."""
        # Record some initial history
        time_travel.record_action(
            {"type": "init"},
            {},
            {"initialized": True}
        )
        
        # Create a branch
        branch_id = time_travel.create_branch("test_branch")
        assert branch_id in time_travel._branches
        
        branch = time_travel._branches[branch_id]
        assert branch.name == "test_branch"
        assert branch.parent_entry_id == time_travel._history[0].id
        
        # Switch to branch
        success = time_travel.switch_branch(branch_id)
        assert success is True
        assert time_travel._current_branch_id == branch_id
        
        # Switch to non-existent branch
        success = time_travel.switch_branch("non_existent")
        assert success is False
    
    def test_history_pruning(self):
        """Test automatic history pruning."""
        time_travel = TimeTravel(max_history=3, auto_prune=True)
        
        # Record more actions than max_history
        for i in range(5):
            time_travel.record_action(
                {"type": "action", "step": i},
                {"step": i},
                {"step": i + 1}
            )
        
        # Should have pruned to max_history
        assert len(time_travel._history) == 3
        
        # Should contain the most recent entries
        assert time_travel._history[0].action["step"] == 2
        assert time_travel._history[-1].action["step"] == 4
    
    def test_recording_enable_disable(self, time_travel):
        """Test enabling/disabling recording."""
        assert time_travel.is_recording() is True
        
        # Disable recording
        time_travel.disable_recording()
        assert time_travel.is_recording() is False
        
        # Record action - should be ignored
        time_travel.record_action(
            {"type": "ignored"},
            {},
            {"ignored": True}
        )
        assert len(time_travel._history) == 0
        
        # Re-enable recording
        time_travel.enable_recording()
        assert time_travel.is_recording() is True
        
        # Record action - should work
        time_travel.record_action(
            {"type": "recorded"},
            {},
            {"recorded": True}
        )
        assert len(time_travel._history) == 1
    
    def test_history_summary(self, time_travel):
        """Test getting history summary."""
        # Record some actions
        for i in range(3):
            time_travel.record_action(
                {"type": "action"},
                {"counter": i},
                {"counter": i + 1}
            )
        
        summary = time_travel.get_history_summary()
        
        assert summary["total_entries"] == 3
        assert summary["current_index"] == 2
        assert summary["current_branch"] == "main"
        assert summary["total_branches"] == 1
        assert summary["can_go_back"] is True
        assert summary["can_go_forward"] is False
        
        # Travel back and check again
        time_travel.travel_to(1)
        summary = time_travel.get_history_summary()
        assert summary["current_index"] == 1
        assert summary["can_go_back"] is True
        assert summary["can_go_forward"] is True
    
    def test_export_import_history(self, time_travel):
        """Test exporting and importing history."""
        # Record some history
        actions = [
            {"type": "add", "value": 1},
            {"type": "add", "value": 2}
        ]
        
        for action in actions:
            time_travel.record_action(action, {}, {})
        
        # Export history
        exported_data = time_travel.export_history(format="dict")
        
        assert "branches" in exported_data
        assert "main" in exported_data["branches"]
        assert len(exported_data["branches"]["main"]["entries"]) == 2
        
        # Create new TimeTravel and import
        new_time_travel = TimeTravel()
        success = new_time_travel.import_history(exported_data)
        
        assert success is True
        assert len(new_time_travel._history) == 2
        assert new_time_travel._history[0].action == actions[0]
        assert new_time_travel._history[1].action == actions[1]
    
    def test_clear_history(self, time_travel):
        """Test clearing history."""
        # Record some history
        time_travel.record_action({"type": "test"}, {}, {})
        assert len(time_travel._history) == 1
        
        # Clear history
        time_travel.clear_history()
        
        assert len(time_travel._history) == 0
        assert time_travel._current_index == -1
        assert len(time_travel._branches) == 1  # Only main branch
        assert "main" in time_travel._branches
    
    def test_event_listeners(self, time_travel):
        """Test history change and time travel listeners."""
        history_changes = []
        time_travels = []
        
        def on_history_change(tt):
            history_changes.append(len(tt._history))
        
        def on_time_travel(old_idx, new_idx, state):
            time_travels.append((old_idx, new_idx))
        
        # Add listeners
        time_travel.add_history_change_listener(on_history_change)
        time_travel.add_time_travel_listener(on_time_travel)
        
        # Record action - should trigger history change
        time_travel.record_action({"type": "test"}, {}, {"test": True})
        assert len(history_changes) == 1
        assert history_changes[0] == 1
        
        # Time travel - should trigger time travel event
        time_travel.travel_to(0)
        assert len(time_travels) == 1
        assert time_travels[0] == (0, 0)  # No actual movement since only one entry
        
        # Remove listeners
        time_travel.remove_history_change_listener(on_history_change)
        time_travel.remove_time_travel_listener(on_time_travel)
        
        # Record another action - should not trigger
        time_travel.record_action({"type": "test2"}, {}, {"test2": True})
        assert len(history_changes) == 1  # Unchanged


class TestTimeTravelMiddleware:
    """Test TimeTravelMiddleware integration."""
    
    @pytest.fixture
    def time_travel(self):
        """Create TimeTravel instance."""
        return TimeTravel(max_history=100)
    
    @pytest.fixture
    def middleware(self, time_travel):
        """Create TimeTravelMiddleware."""
        return TimeTravelMiddleware(time_travel)
    
    @pytest.mark.asyncio
    async def test_middleware_integration(self, middleware, time_travel):
        """Test middleware integration with store."""
        # Mock store
        mock_store = MagicMock()
        mock_store.get_state.side_effect = [
            {"counter": 0},  # Before action
            {"counter": 1}   # After action
        ]
        
        # Mock action
        mock_action = {"type": "increment"}
        
        # Mock next middleware
        async def next_middleware(action):
            return "success"
        
        # Execute middleware
        result = await middleware(mock_store, next_middleware, mock_action)
        
        assert result == "success"
        assert len(time_travel._history) == 1
        
        entry = time_travel._history[0]
        assert entry.action == mock_action
        assert entry.state_before == {"counter": 0}
        assert entry.state_after == {"counter": 1}
        assert entry.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_middleware_with_recording_disabled(self, middleware, time_travel):
        """Test middleware when recording is disabled."""
        # Disable recording
        time_travel.disable_recording()
        
        mock_store = MagicMock()
        mock_store.get_state.return_value = {"test": True}
        mock_action = {"type": "test"}
        
        async def next_middleware(action):
            return "success"
        
        # Execute middleware
        result = await middleware(mock_store, next_middleware, mock_action)
        
        assert result == "success"
        assert len(time_travel._history) == 0  # Not recorded
    
    @pytest.mark.asyncio
    async def test_middleware_with_action_failure(self, middleware, time_travel):
        """Test middleware when action fails."""
        mock_store = MagicMock()
        mock_store.get_state.return_value = {"counter": 0}
        mock_action = {"type": "failing_action"}
        
        async def failing_middleware(action):
            raise ValueError("Action failed")
        
        # Execute middleware - should raise exception
        with pytest.raises(ValueError, match="Action failed"):
            await middleware(mock_store, failing_middleware, mock_action)
        
        # Should still record the failed action
        assert len(time_travel._history) == 1
        entry = time_travel._history[0]
        assert entry.metadata["failed"] is True
        assert "error" in entry.metadata
        assert entry.state_before == entry.state_after  # State unchanged
    
    @pytest.mark.asyncio
    async def test_performance_with_large_states(self, middleware, time_travel):
        """Test middleware performance with large states."""
        # Create large state
        large_state = {
            "elements": [{"id": i, "data": f"element_{i}"} for i in range(1000)],
            "metadata": {"large": True}
        }
        
        mock_store = MagicMock()
        mock_store.get_state.return_value = large_state
        mock_action = {"type": "large_state_action"}
        
        async def next_middleware(action):
            return "success"
        
        # Measure execution time
        start_time = time.time()
        result = await middleware(mock_store, next_middleware, mock_action)
        execution_time = time.time() - start_time
        
        assert result == "success"
        assert len(time_travel._history) == 1
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert execution_time < 0.1, f"Middleware too slow: {execution_time}s"
        
        # Verify state was deep-copied correctly
        entry = time_travel._history[0]
        assert len(entry.state_before["elements"]) == 1000
        assert len(entry.state_after["elements"]) == 1000