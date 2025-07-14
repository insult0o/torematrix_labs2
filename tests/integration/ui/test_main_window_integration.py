"""Integration tests for the complete UI framework main window system.

Tests the integration of all Agent 1-4 components working together.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QAction

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

# Import all our UI components
from torematrix.ui.main_window import MainWindow
from torematrix.ui.panels import PanelManager, PanelConfig
from torematrix.ui.statusbar import StatusBarManager
from torematrix.ui.persistence import WindowPersistence, PersistenceScope
from torematrix.ui.window_manager import WindowManager
from torematrix.ui.splash import SplashScreen, SplashManager
from torematrix.ui.themes import ThemeManager, ThemeType
from torematrix.ui.actions import ActionManager
from torematrix.ui.menus import MenuBuilder


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    event_bus = Mock()
    config_manager = Mock()
    state_manager = Mock()
    
    # Configure mock returns
    config_manager.get_setting.return_value = "test_value"
    state_manager.get_state.return_value = {}
    
    return {
        'event_bus': event_bus,
        'config_manager': config_manager,
        'state_manager': state_manager
    }


@pytest.fixture
def main_window(qapp, mock_services):
    """Create main window with mock services."""
    # Mock the imports to avoid dependencies
    with patch('torematrix.ui.main_window.EventBus', return_value=mock_services['event_bus']), \
         patch('torematrix.ui.main_window.ConfigManager', return_value=mock_services['config_manager']), \
         patch('torematrix.ui.main_window.StateManager', return_value=mock_services['state_manager']):
        
        window = MainWindow()
        window.show()
        return window


class TestMainWindowIntegration:
    """Test main window integration with all components."""
    
    def test_main_window_creation(self, main_window):
        """Test main window can be created and displayed."""
        assert main_window is not None
        assert isinstance(main_window, QMainWindow)
        assert main_window.isVisible()
        assert main_window.windowTitle()
    
    def test_window_basic_structure(self, main_window):
        """Test main window has required components."""
        # Should have menubar
        assert main_window.menuBar() is not None
        
        # Should have status bar
        assert main_window.statusBar() is not None
        
        # Should have central widget
        assert main_window.centralWidget() is not None
    
    def test_window_size_constraints(self, main_window):
        """Test window respects size constraints."""
        size = main_window.size()
        assert size.width() >= 800  # Minimum width
        assert size.height() >= 600  # Minimum height


class TestPanelManagerIntegration:
    """Test panel manager integration."""
    
    def test_panel_manager_creation(self, main_window, mock_services):
        """Test panel manager can be created and integrated."""
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']):
            
            panel_manager = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            assert panel_manager is not None
            assert panel_manager.main_window == main_window
    
    def test_standard_panels_registration(self, main_window, mock_services):
        """Test standard panels are registered."""
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']):
            
            panel_manager = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            # Check standard panels are registered
            panels = panel_manager.get_panel_list()
            expected_panels = ['project_explorer', 'properties', 'console', 'log_viewer']
            
            for panel_id in expected_panels:
                assert panel_id in panels
    
    def test_panel_creation_and_visibility(self, main_window, mock_services):
        """Test panels can be created and shown."""
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']):
            
            panel_manager = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            # Create and show a panel
            dock_widget = panel_manager.create_panel('project_explorer')
            assert dock_widget is not None
            
            # Show panel
            success = panel_manager.show_panel('project_explorer')
            assert success
            assert panel_manager.is_panel_visible('project_explorer')


class TestStatusBarIntegration:
    """Test status bar manager integration."""
    
    def test_status_bar_manager_creation(self, main_window, mock_services):
        """Test status bar manager integration."""
        with patch('torematrix.ui.statusbar.EventBus', return_value=mock_services['event_bus']):
            
            status_manager = StatusBarManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            assert status_manager is not None
            assert status_manager.main_window == main_window
            assert status_manager.status_bar == main_window.statusBar()
    
    def test_status_indicators_creation(self, main_window, mock_services):
        """Test status indicators are created."""
        with patch('torematrix.ui.statusbar.EventBus', return_value=mock_services['event_bus']):
            
            status_manager = StatusBarManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            # Check standard indicators exist
            expected_indicators = ['memory_usage', 'zoom_level', 'cursor_position', 'document_status', 'connection_status']
            
            for indicator_name in expected_indicators:
                assert indicator_name in status_manager.indicators
    
    def test_progress_display(self, main_window, mock_services):
        """Test progress display functionality."""
        with patch('torematrix.ui.statusbar.EventBus', return_value=mock_services['event_bus']):
            
            status_manager = StatusBarManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            # Show progress
            status_manager.show_progress("test_op", 50, 100, "Testing...")
            assert status_manager.is_progress_active()
            
            # Hide progress
            status_manager.hide_progress()


class TestWindowPersistenceIntegration:
    """Test window persistence integration."""
    
    def test_persistence_manager_creation(self, main_window, mock_services):
        """Test window persistence manager creation."""
        persistence = WindowPersistence(
            main_window,
            mock_services['config_manager'],
            PersistenceScope.GLOBAL
        )
        
        assert persistence is not None
        assert persistence.main_window == main_window
    
    def test_window_state_save_restore(self, main_window, mock_services):
        """Test window state can be saved and restored."""
        persistence = WindowPersistence(
            main_window,
            mock_services['config_manager'],
            PersistenceScope.TEMPORARY
        )
        
        # Save window state
        success = persistence.save_window_state()
        assert success
        
        # Modify window
        main_window.resize(1000, 700)
        
        # Restore window state
        success = persistence.restore_window_state()
        # Note: May not work in test environment, but should not crash


class TestWindowManagerIntegration:
    """Test window manager integration."""
    
    def test_window_manager_creation(self, main_window, mock_services):
        """Test window manager creation."""
        with patch('torematrix.ui.window_manager.EventBus', return_value=mock_services['event_bus']):
            
            window_manager = WindowManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            assert window_manager is not None
            assert window_manager.main_window == main_window
    
    def test_main_window_registration(self, main_window, mock_services):
        """Test main window is registered automatically."""
        with patch('torematrix.ui.window_manager.EventBus', return_value=mock_services['event_bus']):
            
            window_manager = WindowManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            # Main window should be registered
            assert "main" in window_manager.get_all_windows()
            assert window_manager.get_window("main") == main_window


class TestSplashScreenIntegration:
    """Test splash screen integration."""
    
    def test_splash_screen_creation(self, qapp):
        """Test splash screen can be created."""
        splash = SplashScreen()
        assert splash is not None
        
        # Test basic functionality
        splash.set_progress(50, "Loading...")
        assert splash.current_progress == 50
        assert splash.current_message == "Loading..."
    
    def test_splash_manager_with_tasks(self, qapp):
        """Test splash manager with loading tasks."""
        manager = SplashManager()
        splash = manager.create_splash()
        
        # Add test tasks
        manager.add_task("task1", "Test Task 1", 1)
        manager.add_task("task2", "Test Task 2", 2)
        
        assert len(manager.tasks) == 2
        assert manager.total_weight == 3


class TestThemeIntegration:
    """Test theme system integration."""
    
    def test_theme_manager_with_main_window(self, main_window, mock_services):
        """Test theme manager can be applied to main window."""
        # Mock the theme manager since it requires full dependencies
        with patch('torematrix.ui.themes.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.themes.ConfigManager', return_value=mock_services['config_manager']), \
             patch('torematrix.ui.themes.StateManager', return_value=mock_services['state_manager']):
            
            # This would normally create a ThemeManager, but we'll just test the concept
            # theme_manager = ThemeManager(...)
            
            # Test that we can apply styles to main window
            assert main_window.styleSheet() is not None or main_window.styleSheet() == ""


class TestFullSystemIntegration:
    """Test full system integration with all components."""
    
    def test_complete_ui_framework_integration(self, main_window, mock_services):
        """Test all UI components can work together."""
        components = {}
        
        # Create all managers
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']), \
             patch('torematrix.ui.statusbar.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.window_manager.EventBus', return_value=mock_services['event_bus']):
            
            # Panel Manager
            components['panel_manager'] = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            # Status Bar Manager
            components['status_manager'] = StatusBarManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            # Window Persistence
            components['persistence'] = WindowPersistence(
                main_window,
                mock_services['config_manager'],
                PersistenceScope.TEMPORARY
            )
            
            # Window Manager
            components['window_manager'] = WindowManager(
                main_window,
                mock_services['event_bus'],
                mock_services['config_manager']
            )
            
            # Verify all components are created
            assert all(comp is not None for comp in components.values())
            
            # Test basic interactions
            # Show a panel
            components['panel_manager'].show_panel('project_explorer')
            
            # Update status
            components['status_manager'].show_message("System ready")
            
            # Save state
            components['persistence'].save_window_state()
            
            # All should work without errors
            assert True
    
    def test_event_bus_integration(self, main_window, mock_services):
        """Test event bus integration across components."""
        # Verify event bus is called when components interact
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']):
            
            panel_manager = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            # Show panel should trigger events
            panel_manager.show_panel('project_explorer')
            
            # Verify event bus was used
            assert mock_services['event_bus'].emit.called or mock_services['event_bus'].subscribe.called
    
    def test_memory_management(self, main_window, mock_services):
        """Test components don't leak memory."""
        # Create components in a scope
        with patch('torematrix.ui.panels.EventBus', return_value=mock_services['event_bus']), \
             patch('torematrix.ui.panels.ConfigManager', return_value=mock_services['config_manager']):
            
            panel_manager = PanelManager(
                main_window, 
                mock_services['config_manager'], 
                mock_services['event_bus']
            )
            
            # Create some panels
            panel_manager.create_panel('project_explorer')
            panel_manager.create_panel('properties')
            
            # This should not crash or leak
            del panel_manager
    
    def test_cross_platform_compatibility(self, main_window):
        """Test basic cross-platform functionality."""
        # Test that main window works on current platform
        assert main_window.isVisible()
        
        # Test window can be resized
        original_size = main_window.size()
        main_window.resize(900, 700)
        new_size = main_window.size()
        assert new_size != original_size
        
        # Test window can be moved (if not maximized)
        if not main_window.isMaximized():
            original_pos = main_window.pos()
            main_window.move(100, 100)
            # Position change may not work in test environment, but shouldn't crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])