"""Tests for MenuBuilder system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMenuBar, QMenu
from PyQt6.QtGui import QAction

from src.torematrix.ui.menus import MenuBuilder, MenuDefinition
from src.torematrix.ui.actions import ActionManager
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


@pytest.fixture
def mock_action_manager():
    """Mock action manager."""
    manager = Mock(spec=ActionManager)
    # Create mock actions
    test_action = Mock(spec=QAction)
    test_action.text.return_value = "Test Action"
    manager.get_action.return_value = test_action
    manager.create_all_standard_actions.return_value = {}
    return manager


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
def menu_builder(qapp, mock_action_manager, mock_event_bus, mock_config_manager, mock_state_manager):
    """Create MenuBuilder instance for testing."""
    builder = MenuBuilder(
        action_manager=mock_action_manager,
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        state_manager=mock_state_manager
    )
    builder.initialize()
    return builder


class TestMenuBuilder:
    """Test MenuBuilder functionality."""
    
    def test_initialization(self, menu_builder):
        """Test MenuBuilder initialization."""
        assert menu_builder.is_initialized
        assert len(menu_builder._menu_definitions) > 0
        assert "file" in menu_builder._menu_definitions
        assert "edit" in menu_builder._menu_definitions
        assert "view" in menu_builder._menu_definitions
    
    def test_standard_menu_definitions(self, menu_builder):
        """Test standard menu definitions are properly set up."""
        file_menu = menu_builder._menu_definitions["file"]
        assert file_menu.name == "file"
        assert file_menu.title == "&File"
        assert "file_new" in file_menu.actions
        assert "file_open" in file_menu.actions
        assert None in file_menu.actions  # Has separators
        
        edit_menu = menu_builder._menu_definitions["edit"]
        assert edit_menu.name == "edit"
        assert edit_menu.title == "&Edit"
        assert "edit_undo" in edit_menu.actions
    
    def test_build_menu(self, menu_builder, qapp):
        """Test building a single menu."""
        menu = menu_builder.build_menu("file")
        
        assert isinstance(menu, QMenu)
        assert menu.title() == "&File"
        assert "file" in menu_builder._menus
    
    def test_build_menubar(self, menu_builder, qapp):
        """Test building complete menubar."""
        menubar = QMenuBar()
        menu_builder.build_menubar(menubar)
        
        # Check that menus were added
        assert len(menubar.actions()) > 0
        
        # Check that standard menus exist
        menu_titles = [action.text() for action in menubar.actions()]
        assert "&File" in menu_titles
        assert "&Edit" in menu_titles
    
    def test_create_custom_menu(self, menu_builder, qapp):
        """Test creating custom menu."""
        custom_actions = ["file_new", "file_open", None, "file_save"]
        
        menu = menu_builder.create_custom_menu(
            menu_name="custom",
            title="Custom Menu",
            actions=custom_actions
        )
        
        assert isinstance(menu, QMenu)
        assert menu.title() == "Custom Menu"
        assert "custom" in menu_builder._menu_definitions
        assert "custom" in menu_builder._menus
    
    def test_add_menu_action(self, menu_builder, mock_action_manager, qapp):
        """Test adding action to existing menu."""
        # Build a menu first
        menu = menu_builder.build_menu("file")
        
        # Add action
        success = menu_builder.add_menu_action("file", "test_action")
        assert success
        
        # Verify action was requested from action manager
        mock_action_manager.get_action.assert_called_with("test_action")
    
    def test_add_menu_action_with_position(self, menu_builder, mock_action_manager, qapp):
        """Test adding action at specific position."""
        menu = menu_builder.build_menu("file")
        
        success = menu_builder.add_menu_action("file", "test_action", position=0)
        assert success
    
    def test_remove_menu_action(self, menu_builder, mock_action_manager, qapp):
        """Test removing action from menu."""
        menu = menu_builder.build_menu("file")
        
        success = menu_builder.remove_menu_action("file", "file_new")
        assert success
    
    def test_add_menu_separator(self, menu_builder, qapp):
        """Test adding separator to menu."""
        menu = menu_builder.build_menu("file")
        
        success = menu_builder.add_menu_separator("file")
        assert success
        
        # Check definition was updated
        definition = menu_builder._menu_definitions["file"]
        assert None in definition.actions
    
    def test_menu_visibility(self, menu_builder, qapp):
        """Test menu visibility control."""
        menu = menu_builder.build_menu("file")
        
        # Initially visible
        assert menu.isVisible()
        
        # Hide menu
        menu_builder.update_menu_visibility("file", False)
        assert not menu.isVisible()
        
        # Show menu
        menu_builder.update_menu_visibility("file", True)
        assert menu.isVisible()
    
    def test_enable_disable_menu(self, menu_builder, qapp):
        """Test enabling/disabling menus."""
        menu = menu_builder.build_menu("file")
        
        # Initially enabled
        assert menu.isEnabled()
        
        # Disable
        menu_builder.enable_menu("file", False)
        assert not menu.isEnabled()
        
        # Enable
        menu_builder.enable_menu("file", True)
        assert menu.isEnabled()
    
    def test_rebuild_menu(self, menu_builder, qapp):
        """Test rebuilding menu from definition."""
        menu = menu_builder.build_menu("file")
        original_action_count = len(menu.actions())
        
        # Modify definition
        definition = menu_builder._menu_definitions["file"]
        definition.actions.append("new_action")
        
        # Rebuild
        success = menu_builder.rebuild_menu("file")
        assert success
    
    def test_get_menu(self, menu_builder, qapp):
        """Test getting menu by name."""
        menu_builder.build_menu("file")
        
        retrieved = menu_builder.get_menu("file")
        assert retrieved is not None
        assert isinstance(retrieved, QMenu)
        
        missing = menu_builder.get_menu("nonexistent")
        assert missing is None
    
    def test_get_all_menus(self, menu_builder, qapp):
        """Test getting all menus."""
        menu_builder.build_menu("file")
        menu_builder.build_menu("edit")
        
        all_menus = menu_builder.get_all_menus()
        assert len(all_menus) >= 2
        assert "file" in all_menus
        assert "edit" in all_menus
    
    def test_context_menu_creation(self, menu_builder, mock_action_manager, qapp):
        """Test creating context menu."""
        actions = ["file_new", "file_open", None, "file_save"]
        
        context_menu = menu_builder.create_context_menu(actions)
        
        assert isinstance(context_menu, QMenu)
        # Verify actions were requested
        expected_calls = ["file_new", "file_open", "file_save"]
        for action_name in expected_calls:
            mock_action_manager.get_action.assert_any_call(action_name)
    
    def test_menu_definition_management(self, menu_builder):
        """Test menu definition getter/setter."""
        # Get existing definition
        file_def = menu_builder.get_menu_definition("file")
        assert file_def is not None
        assert file_def.name == "file"
        
        # Create new definition
        new_def = MenuDefinition(
            name="test",
            title="Test Menu",
            actions=["test_action"]
        )
        
        menu_builder.set_menu_definition("test", new_def)
        
        retrieved = menu_builder.get_menu_definition("test")
        assert retrieved is not None
        assert retrieved.name == "test"


class TestMenuDefinition:
    """Test MenuDefinition dataclass."""
    
    def test_menu_definition_creation(self):
        """Test creating MenuDefinition."""
        definition = MenuDefinition(
            name="test",
            title="Test Menu",
            actions=["action1", None, "action2"]
        )
        
        assert definition.name == "test"
        assert definition.title == "Test Menu"
        assert definition.actions == ["action1", None, "action2"]
        assert definition.submenu_definitions is None
    
    def test_menu_definition_with_submenus(self):
        """Test MenuDefinition with submenus."""
        submenu = MenuDefinition(
            name="submenu",
            title="Sub Menu",
            actions=["sub_action"]
        )
        
        definition = MenuDefinition(
            name="main",
            title="Main Menu",
            actions=["main_action"],
            submenu_definitions={"submenu": submenu}
        )
        
        assert definition.submenu_definitions is not None
        assert "submenu" in definition.submenu_definitions
        assert definition.submenu_definitions["submenu"].name == "submenu"


if __name__ == "__main__":
    pytest.main([__file__])