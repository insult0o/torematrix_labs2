"""Tests for ActionManager system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSettings

from src.torematrix.ui.actions import ActionManager, ActionCategory, ActionDefinition
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigManager
from src.torematrix.core.state import StateManager


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it may be needed by other tests


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    return Mock(spec=EventBus)


@pytest.fixture
def mock_config_manager():
    """Mock config manager."""
    return Mock(spec=ConfigManager)


@pytest.fixture
def mock_state_manager():
    """Mock state manager."""
    return Mock(spec=StateManager)


@pytest.fixture
def action_manager(qapp, mock_event_bus, mock_config_manager, mock_state_manager):
    """Create ActionManager instance for testing."""
    with patch.object(QSettings, '__init__', return_value=None):
        with patch.object(QSettings, 'beginGroup'):
            with patch.object(QSettings, 'endGroup'):
                with patch.object(QSettings, 'childGroups', return_value=[]):
                    manager = ActionManager(
                        event_bus=mock_event_bus,
                        config_manager=mock_config_manager,
                        state_manager=mock_state_manager
                    )
                    manager.initialize()
                    return manager


class TestActionManager:
    """Test ActionManager functionality."""
    
    def test_initialization(self, action_manager):
        """Test ActionManager initialization."""
        assert action_manager.is_initialized
        assert len(action_manager._action_definitions) > 0
        assert "file_new" in action_manager._action_definitions
        assert "edit_undo" in action_manager._action_definitions
    
    def test_create_action(self, action_manager):
        """Test creating a new action."""
        action = action_manager.create_action(
            name="test_action",
            text="Test Action",
            shortcut="Ctrl+T",
            tooltip="Test tooltip",
            category=ActionCategory.CUSTOM
        )
        
        assert isinstance(action, QAction)
        assert action.text() == "Test Action"
        assert action.toolTip() == "Test tooltip"
        assert action.shortcut().toString() == "Ctrl+T"
        assert "test_action" in action_manager._actions
    
    def test_create_duplicate_action(self, action_manager):
        """Test creating duplicate action returns existing."""
        action1 = action_manager.create_action("duplicate", "First")
        action2 = action_manager.create_action("duplicate", "Second")
        
        assert action1 is action2
        assert action1.text() == "First"  # Original is kept
    
    def test_get_action(self, action_manager):
        """Test getting action by name."""
        action_manager.create_action("get_test", "Get Test")
        
        retrieved = action_manager.get_action("get_test")
        assert retrieved is not None
        assert retrieved.text() == "Get Test"
        
        missing = action_manager.get_action("missing")
        assert missing is None
    
    def test_get_actions_by_category(self, action_manager):
        """Test getting actions by category."""
        # Create all standard actions first
        action_manager.create_all_standard_actions()
        
        file_actions = action_manager.get_actions_by_category(ActionCategory.FILE)
        assert len(file_actions) > 0
        
        # Check that all returned actions are actually file category
        for action in file_actions:
            action_name = None
            for name, act in action_manager._actions.items():
                if act is action:
                    action_name = name
                    break
            
            if action_name:
                definition = action_manager._action_definitions[action_name]
                assert definition.category == ActionCategory.FILE
    
    def test_action_group_creation(self, action_manager):
        """Test creating action groups."""
        action_manager.create_action("group1", "Group 1", checkable=True)
        action_manager.create_action("group2", "Group 2", checkable=True)
        
        group = action_manager.create_action_group(
            "test_group", 
            ["group1", "group2"], 
            exclusive=True
        )
        
        assert group is not None
        assert group.isExclusive()
        assert len(group.actions()) == 2
    
    def test_enable_disable_action(self, action_manager):
        """Test enabling/disabling actions."""
        action_manager.create_action("enable_test", "Enable Test")
        
        # Initially enabled
        action = action_manager.get_action("enable_test")
        assert action.isEnabled()
        
        # Disable
        action_manager.set_action_enabled("enable_test", False)
        assert not action.isEnabled()
        
        # Enable
        action_manager.set_action_enabled("enable_test", True)
        assert action.isEnabled()
    
    def test_checkable_action(self, action_manager):
        """Test checkable action functionality."""
        action_manager.create_action("check_test", "Check Test", checkable=True)
        
        # Initially unchecked
        action = action_manager.get_action("check_test")
        assert not action.isChecked()
        
        # Check
        action_manager.set_action_checked("check_test", True)
        assert action.isChecked()
        
        # Uncheck
        action_manager.set_action_checked("check_test", False)
        assert not action.isChecked()
    
    def test_shortcut_conflict_detection(self, action_manager):
        """Test shortcut conflict detection."""
        # Create two actions with same shortcut
        action_manager.create_action("conflict1", "Conflict 1", shortcut="Ctrl+K")
        action_manager.create_action("conflict2", "Conflict 2", shortcut="Ctrl+K")
        
        # Should have conflicts
        conflicts = action_manager.get_shortcut_conflicts()
        assert "Ctrl+K" in conflicts
    
    def test_customize_shortcut(self, action_manager):
        """Test customizing shortcuts."""
        action_manager.create_action("shortcut_test", "Shortcut Test", shortcut="Ctrl+1")
        
        # Change shortcut
        success = action_manager.customize_shortcut("shortcut_test", "Ctrl+2")
        assert success
        
        action = action_manager.get_action("shortcut_test")
        assert action.shortcut().toString() == "Ctrl+2"
    
    def test_shortcut_conflict_resolution(self, action_manager):
        """Test resolving shortcut conflicts."""
        action_manager.create_action("resolve1", "Resolve 1", shortcut="Ctrl+R")
        action_manager.create_action("resolve2", "Resolve 2", shortcut="Ctrl+R")
        
        # Resolve conflict in favor of resolve1
        action_manager.resolve_shortcut_conflict("Ctrl+R", "resolve1")
        
        conflicts = action_manager.get_shortcut_conflicts()
        assert "Ctrl+R" not in conflicts
    
    def test_action_definition_retrieval(self, action_manager):
        """Test getting action definitions."""
        action_manager.create_action("def_test", "Definition Test", tooltip="Test def")
        
        definition = action_manager.get_action_definition("def_test")
        assert definition is not None
        assert definition.name == "def_test"
        assert definition.text == "Definition Test"
        assert definition.tooltip == "Test def"
    
    def test_standard_actions_creation(self, action_manager):
        """Test creating all standard actions."""
        actions = action_manager.create_all_standard_actions()
        
        assert len(actions) > 0
        assert "file_new" in actions
        assert "edit_undo" in actions
        assert "view_zoom_in" in actions
        assert "help_about" in actions
        
        # Verify actions are properly created
        for name, action in actions.items():
            assert isinstance(action, QAction)
            assert action.text() != ""
    
    @patch.object(QSettings, 'setValue')
    @patch.object(QSettings, 'beginGroup')
    @patch.object(QSettings, 'endGroup')
    def test_save_action_states(self, mock_end_group, mock_begin_group, mock_set_value, action_manager):
        """Test saving action states."""
        action_manager.create_action("save_test", "Save Test", checkable=True)
        action_manager.set_action_checked("save_test", True)
        action_manager.set_action_enabled("save_test", False)
        
        action_manager.save_states()
        
        # Verify settings were saved
        mock_begin_group.assert_called()
        mock_set_value.assert_called()
        mock_end_group.assert_called()


class TestActionDefinition:
    """Test ActionDefinition dataclass."""
    
    def test_action_definition_creation(self):
        """Test creating ActionDefinition."""
        definition = ActionDefinition(
            name="test",
            text="Test Action",
            tooltip="Test tooltip",
            shortcut="Ctrl+T",
            category=ActionCategory.EDIT,
            checkable=True,
            enabled=False
        )
        
        assert definition.name == "test"
        assert definition.text == "Test Action"
        assert definition.tooltip == "Test tooltip"
        assert definition.shortcut == "Ctrl+T"
        assert definition.category == ActionCategory.EDIT
        assert definition.checkable is True
        assert definition.enabled is False
    
    def test_action_definition_defaults(self):
        """Test ActionDefinition default values."""
        definition = ActionDefinition(name="test", text="Test")
        
        assert definition.tooltip == ""
        assert definition.shortcut == ""
        assert definition.icon == ""
        assert definition.category == ActionCategory.CUSTOM
        assert definition.checkable is False
        assert definition.enabled is True
        assert definition.separator_after is False
        assert definition.handler is None


if __name__ == "__main__":
    pytest.main([__file__])