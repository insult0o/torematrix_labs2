"""Tests for UI Framework Integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication

from src.torematrix.ui.integration import UIFrameworkIntegrator, create_ui_framework
from src.torematrix.ui.main_window import MainWindow
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
def mock_main_window():
    """Mock main window."""
    window = Mock(spec=MainWindow)
    window.get_menubar_container.return_value = Mock()
    window.get_toolbar_container.return_value = Mock()
    return window


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


class TestUIFrameworkIntegrator:
    """Test UIFrameworkIntegrator functionality."""
    
    @patch('src.torematrix.ui.integration.ResourceManager')
    @patch('src.torematrix.ui.integration.ActionManager')
    @patch('src.torematrix.ui.integration.MenuBuilder')
    @patch('src.torematrix.ui.integration.ToolbarManager')
    @patch('src.torematrix.ui.integration.ShortcutManager')
    @patch('src.torematrix.ui.integration.QSettings')
    def test_initialization(
        self, 
        mock_settings,
        mock_shortcut_manager,
        mock_toolbar_manager,
        mock_menu_builder,
        mock_action_manager,
        mock_resource_manager,
        qapp,
        mock_main_window,
        mock_event_bus,
        mock_config_manager,
        mock_state_manager
    ):
        """Test integrator initialization."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource_instance.initialize.return_value = None
        mock_resource_manager.return_value = mock_resource_instance
        
        mock_action_instance = Mock()
        mock_action_instance.initialize.return_value = None
        mock_action_manager.return_value = mock_action_instance
        
        mock_menu_instance = Mock()
        mock_menu_instance.initialize.return_value = None
        mock_menu_instance.build_menubar.return_value = None
        mock_menu_builder.return_value = mock_menu_instance
        
        mock_toolbar_instance = Mock()
        mock_toolbar_instance.initialize.return_value = None
        mock_toolbar_instance.create_all_standard_toolbars.return_value = {}
        mock_toolbar_manager.return_value = mock_toolbar_instance
        
        mock_shortcut_instance = Mock()
        mock_shortcut_instance.initialize.return_value = None
        mock_shortcut_instance.create_all_shortcuts.return_value = None
        mock_shortcut_manager.return_value = mock_shortcut_instance
        
        # Create integrator
        integrator = UIFrameworkIntegrator(
            main_window=mock_main_window,
            event_bus=mock_event_bus,
            config_manager=mock_config_manager,
            state_manager=mock_state_manager
        )
        
        integrator.initialize()
        
        # Verify components were created
        assert integrator._components_initialized
        assert mock_resource_manager.called
        assert mock_action_manager.called
        assert mock_menu_builder.called
        assert mock_toolbar_manager.called
        assert mock_shortcut_manager.called
    
    def test_component_getters(
        self,
        qapp,
        mock_main_window,
        mock_event_bus,
        mock_config_manager,
        mock_state_manager
    ):
        """Test component getter methods."""
        with patch('src.torematrix.ui.integration.ResourceManager') as mock_rm:
            with patch('src.torematrix.ui.integration.ActionManager') as mock_am:
                with patch('src.torematrix.ui.integration.MenuBuilder') as mock_mb:
                    with patch('src.torematrix.ui.integration.ToolbarManager') as mock_tm:
                        with patch('src.torematrix.ui.integration.ShortcutManager') as mock_sm:
                            with patch('src.torematrix.ui.integration.QSettings'):
                                # Setup mock instances
                                for mock_class in [mock_rm, mock_am, mock_mb, mock_tm, mock_sm]:
                                    instance = Mock()
                                    instance.initialize.return_value = None
                                    mock_class.return_value = instance
                                
                                # Additional setup for specific mocks
                                mock_mb.return_value.build_menubar.return_value = None
                                mock_tm.return_value.create_all_standard_toolbars.return_value = {}
                                mock_sm.return_value.create_all_shortcuts.return_value = None
                                
                                integrator = UIFrameworkIntegrator(
                                    main_window=mock_main_window,
                                    event_bus=mock_event_bus,
                                    config_manager=mock_config_manager,
                                    state_manager=mock_state_manager
                                )
                                
                                integrator.initialize()
                                
                                # Test getters
                                assert integrator.get_action_manager() is not None
                                assert integrator.get_menu_builder() is not None
                                assert integrator.get_resource_manager() is not None
                                assert integrator.get_toolbar_manager() is not None
                                assert integrator.get_shortcut_manager() is not None
    
    def test_theme_management(
        self,
        qapp,
        mock_main_window,
        mock_event_bus,
        mock_config_manager,
        mock_state_manager
    ):
        """Test theme management functionality."""
        with patch('src.torematrix.ui.integration.ResourceManager') as mock_rm:
            with patch('src.torematrix.ui.integration.ActionManager'):
                with patch('src.torematrix.ui.integration.MenuBuilder'):
                    with patch('src.torematrix.ui.integration.ToolbarManager'):
                        with patch('src.torematrix.ui.integration.ShortcutManager'):
                            with patch('src.torematrix.ui.integration.QSettings'):
                                # Setup mock
                                mock_resource_instance = Mock()
                                mock_resource_instance.initialize.return_value = None
                                mock_resource_instance.get_current_theme.return_value = "light"
                                mock_resource_instance.set_theme.return_value = None
                                mock_rm.return_value = mock_resource_instance
                                
                                integrator = UIFrameworkIntegrator(
                                    main_window=mock_main_window,
                                    event_bus=mock_event_bus,
                                    config_manager=mock_config_manager,
                                    state_manager=mock_state_manager
                                )
                                
                                # Test theme operations
                                current_theme = integrator.get_current_theme()
                                assert current_theme == "light"
                                
                                success = integrator.set_theme("dark")
                                assert success
                                mock_resource_instance.set_theme.assert_called_with("dark")
    
    def test_framework_status(
        self,
        qapp,
        mock_main_window,
        mock_event_bus,
        mock_config_manager,
        mock_state_manager
    ):
        """Test framework status reporting."""
        with patch('src.torematrix.ui.integration.ResourceManager') as mock_rm:
            with patch('src.torematrix.ui.integration.ActionManager') as mock_am:
                with patch('src.torematrix.ui.integration.MenuBuilder') as mock_mb:
                    with patch('src.torematrix.ui.integration.ToolbarManager') as mock_tm:
                        with patch('src.torematrix.ui.integration.ShortcutManager') as mock_sm:
                            with patch('src.torematrix.ui.integration.QSettings'):
                                # Setup mocks
                                mock_instances = {}
                                for name, mock_class in [
                                    ('resource', mock_rm), ('action', mock_am), 
                                    ('menu', mock_mb), ('toolbar', mock_tm), ('shortcut', mock_sm)
                                ]:
                                    instance = Mock()
                                    instance.initialize.return_value = None
                                    instance.is_initialized = True
                                    mock_class.return_value = instance
                                    mock_instances[name] = instance
                                
                                # Additional setup
                                mock_instances['resource'].get_current_theme.return_value = "light"
                                mock_instances['action'].get_all_actions.return_value = {"action1": Mock()}
                                mock_instances['menu'].get_all_menus.return_value = {"menu1": Mock()}
                                mock_instances['menu'].build_menubar.return_value = None
                                mock_instances['toolbar'].get_all_toolbars.return_value = {"toolbar1": Mock()}
                                mock_instances['toolbar'].create_all_standard_toolbars.return_value = {}
                                mock_instances['shortcut'].get_all_shortcuts.return_value = {"shortcut1": Mock()}
                                mock_instances['shortcut'].create_all_shortcuts.return_value = None
                                
                                integrator = UIFrameworkIntegrator(
                                    main_window=mock_main_window,
                                    event_bus=mock_event_bus,
                                    config_manager=mock_config_manager,
                                    state_manager=mock_state_manager
                                )
                                
                                integrator.initialize()
                                
                                status = integrator.get_framework_status()
                                
                                assert status["initialized"] is True
                                assert status["action_manager"] is True
                                assert status["menu_builder"] is True
                                assert status["resource_manager"] is True
                                assert status["toolbar_manager"] is True
                                assert status["shortcut_manager"] is True
                                assert status["theme"] == "light"
                                assert status["action_count"] == 1
                                assert status["menu_count"] == 1
                                assert status["toolbar_count"] == 1
                                assert status["shortcut_count"] == 1


class TestCreateUIFramework:
    """Test create_ui_framework factory function."""
    
    @patch('src.torematrix.ui.integration.UIFrameworkIntegrator')
    def test_create_ui_framework(
        self, 
        mock_integrator_class,
        mock_main_window,
        mock_event_bus,
        mock_config_manager,
        mock_state_manager
    ):
        """Test framework creation factory function."""
        mock_integrator = Mock()
        mock_integrator.initialize.return_value = None
        mock_integrator_class.return_value = mock_integrator
        
        result = create_ui_framework(
            main_window=mock_main_window,
            event_bus=mock_event_bus,
            config_manager=mock_config_manager,
            state_manager=mock_state_manager
        )
        
        assert result is mock_integrator
        mock_integrator_class.assert_called_once_with(
            main_window=mock_main_window,
            event_bus=mock_event_bus,
            config_manager=mock_config_manager,
            state_manager=mock_state_manager
        )
        mock_integrator.initialize.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])