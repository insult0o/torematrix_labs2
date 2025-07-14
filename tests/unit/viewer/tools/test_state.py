"""
Tests for tool state management system.
"""

import pytest
import time
from unittest.mock import Mock, patch
from PyQt6.QtCore import QObject

from src.torematrix.ui.viewer.tools.base import ToolState
from src.torematrix.ui.viewer.tools.state import (
    StateTransition, StateSnapshot, StateValidationRule, ToolStateManager,
    MultiToolStateManager
)


class TestStateTransition:
    """Test StateTransition dataclass."""
    
    def test_state_transition_creation(self):
        """Test state transition creation."""
        transition = StateTransition(
            from_state=ToolState.INACTIVE,
            to_state=ToolState.ACTIVE
        )
        
        assert transition.from_state == ToolState.INACTIVE
        assert transition.to_state == ToolState.ACTIVE
        assert isinstance(transition.timestamp, float)
        assert transition.metadata == {}
    
    def test_state_transition_with_metadata(self):
        """Test state transition with metadata."""
        metadata = {"reason": "user_action", "button": "left"}
        transition = StateTransition(
            from_state=ToolState.ACTIVE,
            to_state=ToolState.SELECTING,
            metadata=metadata
        )
        
        assert transition.metadata == metadata
    
    def test_duration_since(self):
        """Test duration calculation."""
        transition = StateTransition(
            from_state=ToolState.INACTIVE,
            to_state=ToolState.ACTIVE
        )
        
        # Sleep briefly to ensure duration > 0
        time.sleep(0.001)
        duration = transition.duration_since()
        assert duration > 0


class TestStateSnapshot:
    """Test StateSnapshot dataclass."""
    
    def test_state_snapshot_creation(self):
        """Test state snapshot creation."""
        snapshot = StateSnapshot(
            state=ToolState.ACTIVE,
            tool_id="test_tool",
            selection_count=3
        )
        
        assert snapshot.state == ToolState.ACTIVE
        assert snapshot.tool_id == "test_tool"
        assert snapshot.selection_count == 3
        assert isinstance(snapshot.timestamp, float)
        assert snapshot.metadata == {}
    
    def test_snapshot_age(self):
        """Test snapshot age calculation."""
        snapshot = StateSnapshot(state=ToolState.ACTIVE)
        
        time.sleep(0.001)
        age = snapshot.age()
        assert age > 0


class TestStateValidationRule:
    """Test StateValidationRule class."""
    
    def test_validation_rule_creation(self):
        """Test validation rule creation."""
        rule = StateValidationRule(
            "test_rule",
            lambda from_state, to_state: from_state != to_state,
            "States must be different"
        )
        
        assert rule.name == "test_rule"
        assert rule.error_message == "States must be different"
    
    def test_validation_rule_validate(self):
        """Test validation rule validation."""
        rule = StateValidationRule(
            "no_self_transition",
            lambda from_state, to_state: from_state != to_state
        )
        
        # Valid transition
        assert rule.validate(ToolState.INACTIVE, ToolState.ACTIVE) == True
        
        # Invalid transition (self-transition)
        assert rule.validate(ToolState.ACTIVE, ToolState.ACTIVE) == False
    
    def test_validation_rule_default_error(self):
        """Test validation rule with default error message."""
        rule = StateValidationRule(
            "test_rule",
            lambda from_state, to_state: True
        )
        
        assert "test_rule" in rule.error_message


class TestToolStateManager:
    """Test ToolStateManager class."""
    
    def test_state_manager_creation(self):
        """Test state manager creation."""
        manager = ToolStateManager("test_tool")
        
        assert manager.tool_id == "test_tool"
        assert manager.get_current_state() == ToolState.INACTIVE
        assert manager.get_previous_state() is None
        assert manager.get_time_in_current_state() >= 0
    
    def test_basic_state_transition(self):
        """Test basic state transitions."""
        manager = ToolStateManager("test_tool")
        
        # Valid transition
        success = manager.transition(ToolState.ACTIVE)
        assert success == True
        assert manager.get_current_state() == ToolState.ACTIVE
        assert manager.get_previous_state() == ToolState.INACTIVE
        
        # Another valid transition
        success = manager.transition(ToolState.SELECTING)
        assert success == True
        assert manager.get_current_state() == ToolState.SELECTING
        assert manager.get_previous_state() == ToolState.ACTIVE
    
    def test_invalid_state_transition(self):
        """Test invalid state transitions."""
        manager = ToolStateManager("test_tool")
        
        # Try invalid transition (inactive -> selecting without going through active)
        success = manager.transition(ToolState.SELECTING)
        assert success == False
        assert manager.get_current_state() == ToolState.INACTIVE  # Should remain unchanged
    
    def test_self_transition_blocked(self):
        """Test that self-transitions are blocked."""
        manager = ToolStateManager("test_tool")
        manager.transition(ToolState.ACTIVE)
        
        # Try self-transition
        success = manager.transition(ToolState.ACTIVE)
        assert success == False
        assert manager.get_current_state() == ToolState.ACTIVE
    
    def test_transition_with_metadata(self):
        """Test transitions with metadata."""
        manager = ToolStateManager("test_tool")
        metadata = {"trigger": "mouse_click"}
        
        success = manager.transition(ToolState.ACTIVE, metadata)
        assert success == True
        
        # Check history contains metadata
        history = manager.get_history()
        assert len(history) == 1
        assert history[0].metadata == metadata
    
    def test_force_transition(self):
        """Test forced transitions."""
        manager = ToolStateManager("test_tool")
        
        # Force invalid transition
        manager.force_transition(ToolState.SELECTING)
        assert manager.get_current_state() == ToolState.SELECTING
        
        # Check that it was marked as forced
        history = manager.get_history()
        assert len(history) == 1
        assert history[0].metadata.get("forced") == True
    
    def test_can_transition(self):
        """Test transition validation checking."""
        manager = ToolStateManager("test_tool")
        
        # Valid transition
        assert manager.can_transition(ToolState.ACTIVE) == True
        
        # Invalid transition
        assert manager.can_transition(ToolState.SELECTING) == False
        
        # Self transition
        assert manager.can_transition(ToolState.INACTIVE) == False
    
    def test_custom_validation_rules(self):
        """Test custom validation rules."""
        manager = ToolStateManager("test_tool")
        
        # Add custom rule
        manager.add_validation_rule(
            "no_hover_from_inactive",
            lambda from_state, to_state: not (from_state == ToolState.INACTIVE and to_state == ToolState.HOVER),
            "Cannot hover from inactive state"
        )
        
        # This should now be blocked
        success = manager.transition(ToolState.HOVER)
        assert success == False
    
    def test_validation_rule_removal(self):
        """Test validation rule removal."""
        manager = ToolStateManager("test_tool")
        
        # Remove default rule
        success = manager.remove_validation_rule("no_self_transition")
        assert success == True
        
        # Now self-transitions should work
        manager.transition(ToolState.ACTIVE)
        success = manager.transition(ToolState.ACTIVE)
        assert success == True  # Should now be allowed
    
    def test_valid_transition_management(self):
        """Test adding/removing valid transitions."""
        manager = ToolStateManager("test_tool")
        
        # Add custom transition
        manager.add_valid_transition(ToolState.INACTIVE, ToolState.HOVER)
        
        # This should now work
        success = manager.transition(ToolState.HOVER)
        assert success == True
        
        # Remove the transition
        success = manager.remove_valid_transition(ToolState.INACTIVE, ToolState.HOVER)
        assert success == True
        
        # Reset and try again - should fail now
        manager.reset()
        success = manager.transition(ToolState.HOVER)
        assert success == False
    
    def test_state_history(self):
        """Test state history tracking."""
        manager = ToolStateManager("test_tool")
        
        # Make several transitions
        manager.transition(ToolState.ACTIVE)
        manager.transition(ToolState.SELECTING)
        manager.transition(ToolState.SELECTED)
        
        history = manager.get_history()
        assert len(history) == 3
        
        # Check order
        assert history[0].from_state == ToolState.INACTIVE
        assert history[0].to_state == ToolState.ACTIVE
        assert history[1].from_state == ToolState.ACTIVE
        assert history[1].to_state == ToolState.SELECTING
        assert history[2].from_state == ToolState.SELECTING
        assert history[2].to_state == ToolState.SELECTED
    
    def test_history_limit(self):
        """Test history size limiting."""
        manager = ToolStateManager("test_tool")
        manager._max_history_size = 3
        
        # Make more transitions than the limit
        for i in range(5):
            if i % 2 == 0:
                manager.force_transition(ToolState.ACTIVE)
            else:
                manager.force_transition(ToolState.INACTIVE)
        
        history = manager.get_history()
        assert len(history) <= 3
    
    def test_recent_transitions(self):
        """Test getting recent transitions."""
        manager = ToolStateManager("test_tool")
        
        manager.transition(ToolState.ACTIVE)
        time.sleep(0.001)
        manager.transition(ToolState.SELECTING)
        
        # Get recent transitions (within 1 second)
        recent = manager.get_recent_transitions(1.0)
        assert len(recent) == 2
        
        # Get very recent transitions (within 0.0001 seconds)
        very_recent = manager.get_recent_transitions(0.0001)
        assert len(very_recent) <= 2  # Might be 0, 1, or 2 depending on timing
    
    def test_state_metadata(self):
        """Test state metadata management."""
        manager = ToolStateManager("test_tool")
        
        # Set metadata for a state
        metadata = {"cursor": "crosshair", "tooltip": "Select area"}
        manager.set_state_metadata(ToolState.ACTIVE, metadata)
        
        retrieved = manager.get_state_metadata(ToolState.ACTIVE)
        assert retrieved == metadata
        
        # Update specific metadata
        manager.update_state_metadata(ToolState.ACTIVE, "cursor", "pointer")
        updated = manager.get_state_metadata(ToolState.ACTIVE)
        assert updated["cursor"] == "pointer"
        assert updated["tooltip"] == "Select area"
    
    def test_reset(self):
        """Test state manager reset."""
        manager = ToolStateManager("test_tool")
        
        # Make some transitions
        manager.transition(ToolState.ACTIVE)
        manager.transition(ToolState.SELECTING)
        
        assert manager.get_current_state() == ToolState.SELECTING
        
        # Reset
        manager.reset()
        
        assert manager.get_current_state() == ToolState.INACTIVE
    
    def test_statistics(self):
        """Test state statistics."""
        manager = ToolStateManager("test_tool")
        
        # Make some transitions
        manager.transition(ToolState.ACTIVE)
        manager.transition(ToolState.SELECTING)
        manager.transition(ToolState.ACTIVE)
        
        stats = manager.get_state_statistics()
        
        assert stats['current_state'] == ToolState.ACTIVE.value
        assert stats['total_transitions'] == 3
        assert 'average_durations' in stats
        assert 'transition_counts' in stats
    
    def test_clear_history(self):
        """Test clearing history."""
        manager = ToolStateManager("test_tool")
        
        manager.transition(ToolState.ACTIVE)
        manager.transition(ToolState.SELECTING)
        
        assert len(manager.get_history()) == 2
        
        manager.clear_history()
        
        assert len(manager.get_history()) == 0
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_persistence(self, mock_json_dump, mock_open):
        """Test state persistence."""
        manager = ToolStateManager("test_tool")
        manager.enable_persistence("/tmp/test_state.json")
        
        # Make a transition (should trigger save)
        manager.transition(ToolState.ACTIVE)
        
        # Check that file operations were called
        mock_open.assert_called_with("/tmp/test_state.json", 'w')
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', create=True)
    @patch('json.load')
    def test_load_state(self, mock_json_load, mock_open):
        """Test state loading."""
        mock_json_load.return_value = {
            'current_state': 'active',
            'previous_state': 'inactive',
            'state_entry_time': time.time(),
            'tool_id': 'test_tool',
            'metadata': {}
        }
        
        manager = ToolStateManager("test_tool")
        success = manager.load_state("/tmp/test_state.json")
        
        assert success == True
        assert manager.get_current_state() == ToolState.ACTIVE
        assert manager.get_previous_state() == ToolState.INACTIVE


class TestMultiToolStateManager:
    """Test MultiToolStateManager class."""
    
    def test_multi_manager_creation(self):
        """Test multi-tool state manager creation."""
        manager = MultiToolStateManager()
        
        assert len(manager.get_all_tool_ids()) == 0
        assert manager.get_active_tool_id() is None
        assert manager.get_active_tool_manager() is None
    
    def test_add_tool(self):
        """Test adding tools."""
        manager = MultiToolStateManager()
        
        tool_manager = manager.add_tool("tool1")
        assert isinstance(tool_manager, ToolStateManager)
        assert tool_manager.tool_id == "tool1"
        assert "tool1" in manager.get_all_tool_ids()
        
        # Adding same tool should return existing manager
        same_manager = manager.add_tool("tool1")
        assert same_manager is tool_manager
    
    def test_remove_tool(self):
        """Test removing tools."""
        manager = MultiToolStateManager()
        
        manager.add_tool("tool1")
        assert "tool1" in manager.get_all_tool_ids()
        
        success = manager.remove_tool("tool1")
        assert success == True
        assert "tool1" not in manager.get_all_tool_ids()
        
        # Removing non-existent tool
        success = manager.remove_tool("nonexistent")
        assert success == False
    
    def test_active_tool_management(self):
        """Test active tool management."""
        manager = MultiToolStateManager()
        
        manager.add_tool("tool1")
        manager.add_tool("tool2")
        
        # Set active tool
        success = manager.set_active_tool("tool1")
        assert success == True
        assert manager.get_active_tool_id() == "tool1"
        
        active_manager = manager.get_active_tool_manager()
        assert active_manager is not None
        assert active_manager.tool_id == "tool1"
        
        # Switch active tool
        success = manager.set_active_tool("tool2")
        assert success == True
        assert manager.get_active_tool_id() == "tool2"
        
        # Set invalid tool
        success = manager.set_active_tool("invalid")
        assert success == False
        assert manager.get_active_tool_id() == "tool2"  # Should remain unchanged
    
    def test_remove_active_tool(self):
        """Test removing active tool."""
        manager = MultiToolStateManager()
        
        manager.add_tool("tool1")
        manager.set_active_tool("tool1")
        
        assert manager.get_active_tool_id() == "tool1"
        
        manager.remove_tool("tool1")
        
        assert manager.get_active_tool_id() is None
        assert manager.get_active_tool_manager() is None
    
    def test_get_all_states(self):
        """Test getting all tool states."""
        manager = MultiToolStateManager()
        
        tool1_manager = manager.add_tool("tool1")
        tool2_manager = manager.add_tool("tool2")
        
        # Change states
        tool1_manager.transition(ToolState.ACTIVE)
        tool2_manager.transition(ToolState.ACTIVE)
        tool2_manager.transition(ToolState.SELECTING)
        
        all_states = manager.get_all_states()
        
        assert all_states["tool1"] == ToolState.ACTIVE
        assert all_states["tool2"] == ToolState.SELECTING
    
    def test_deactivate_all_tools(self):
        """Test deactivating all tools."""
        manager = MultiToolStateManager()
        
        tool1_manager = manager.add_tool("tool1")
        tool2_manager = manager.add_tool("tool2")
        
        # Activate tools
        tool1_manager.transition(ToolState.ACTIVE)
        tool2_manager.transition(ToolState.ACTIVE)
        tool2_manager.transition(ToolState.SELECTING)
        
        manager.deactivate_all_tools()
        
        all_states = manager.get_all_states()
        assert all_states["tool1"] == ToolState.INACTIVE
        assert all_states["tool2"] == ToolState.INACTIVE
    
    def test_global_statistics(self):
        """Test getting global statistics."""
        manager = MultiToolStateManager()
        
        manager.add_tool("tool1")
        manager.add_tool("tool2")
        manager.set_active_tool("tool1")
        
        stats = manager.get_global_statistics()
        
        assert stats['total_tools'] == 2
        assert stats['active_tool'] == "tool1"
        assert 'tool_stats' in stats
        assert 'tool1' in stats['tool_stats']
        assert 'tool2' in stats['tool_stats']


if __name__ == "__main__":
    pytest.main([__file__])