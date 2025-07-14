"""Tests for theme management system."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import json

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

from torematrix.ui.themes import (
    ThemeManager, ThemeType, ThemeColors, 
    LIGHT_THEME, DARK_THEME
)
from torematrix.core.events import EventBus
from torematrix.core.config import ConfigManager
from torematrix.core.state import StateManager


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for ThemeManager."""
    event_bus = Mock(spec=EventBus)
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)
    
    return event_bus, config_manager, state_manager


@pytest.fixture
def theme_manager(app, mock_dependencies):
    """Create ThemeManager instance for testing."""
    event_bus, config_manager, state_manager = mock_dependencies
    
    with patch('torematrix.ui.themes.QSettings'):
        manager = ThemeManager(event_bus, config_manager, state_manager)
    
    return manager


class TestThemeColors:
    """Test ThemeColors data class."""
    
    def test_theme_colors_creation(self):
        """Test creating ThemeColors instance."""
        colors = ThemeColors(
            background="#ffffff",
            primary_background="#f8f9fa",
            text="#212529",
            text_disabled="#6c757d",
            accent="#007bff",
            accent_dark="#0056b3",
            accent_light="#66b3ff",
            border="#dee2e6",
            button_background="#ffffff",
            button_border="#ced4da",
            button_hover="#e9ecef",
            button_pressed="#dee2e6",
            button_disabled="#f8f9fa",
            menu_background="#ffffff",
            menu_hover="#007bff",
            menu_separator="#dee2e6",
            success="#28a745",
            warning="#ffc107",
            error="#dc3545",
            info="#17a2b8"
        )
        
        assert colors.background == "#ffffff"
        assert colors.accent == "#007bff"
        assert colors.success == "#28a745"


class TestThemeManager:
    """Test ThemeManager functionality."""
    
    def test_initialization(self, theme_manager):
        """Test ThemeManager initialization."""
        assert theme_manager._current_theme == ThemeManager.LIGHT_THEME
        assert ThemeManager.LIGHT_THEME in theme_manager._themes
        assert ThemeManager.DARK_THEME in theme_manager._themes
        assert len(theme_manager._stylesheets) >= 0  # May be empty if files not found
    
    def test_builtin_themes_setup(self, theme_manager):
        """Test that built-in themes are set up correctly."""
        light_colors = theme_manager._themes[ThemeManager.LIGHT_THEME]
        dark_colors = theme_manager._themes[ThemeManager.DARK_THEME]
        
        assert light_colors.background == "#ffffff"
        assert dark_colors.background == "#2b2b2b"
        assert light_colors.accent == "#007bff"
        assert dark_colors.accent == "#0e639c"
    
    def test_get_current_theme(self, theme_manager):
        """Test getting current theme."""
        assert theme_manager.get_current_theme() == ThemeManager.LIGHT_THEME
    
    def test_get_available_themes(self, theme_manager):
        """Test getting available themes."""
        themes = theme_manager.get_available_themes()
        assert ThemeManager.LIGHT_THEME in themes
        assert ThemeManager.DARK_THEME in themes
        assert len(themes) >= 2
    
    def test_toggle_theme(self, theme_manager):
        """Test theme toggling."""
        # Start with light theme
        assert theme_manager.get_current_theme() == ThemeManager.LIGHT_THEME
        
        # Toggle to dark
        with patch.object(theme_manager, 'load_theme') as mock_load:
            new_theme = theme_manager.toggle_theme()
            assert new_theme == ThemeManager.DARK_THEME
            mock_load.assert_called_once_with(ThemeManager.DARK_THEME)
    
    def test_get_theme_color(self, theme_manager):
        """Test getting theme colors."""
        color = theme_manager.get_theme_color("background")
        assert isinstance(color, QColor)
        assert color.name() == "#ffffff"  # Light theme background
        
        # Test invalid color role
        invalid_color = theme_manager.get_theme_color("invalid_role")
        assert invalid_color == QColor()
    
    def test_get_theme_colors(self, theme_manager):
        """Test getting theme colors object."""
        colors = theme_manager.get_theme_colors()
        assert isinstance(colors, ThemeColors)
        assert colors.background == "#ffffff"
        
        # Test specific theme
        dark_colors = theme_manager.get_theme_colors(ThemeManager.DARK_THEME)
        assert dark_colors.background == "#2b2b2b"
    
    def test_register_custom_theme(self, theme_manager):
        """Test registering custom theme."""
        custom_colors = ThemeColors(
            background="#ff0000",
            primary_background="#ff1111",
            text="#ffffff",
            text_disabled="#cccccc",
            accent="#0000ff",
            accent_dark="#000099",
            accent_light="#3333ff",
            border="#888888",
            button_background="#ff0000",
            button_border="#888888",
            button_hover="#ff3333",
            button_pressed="#cc0000",
            button_disabled="#ff6666",
            menu_background="#ff0000",
            menu_hover="#0000ff",
            menu_separator="#888888",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            info="#00ffff"
        )
        
        result = theme_manager.register_custom_theme("custom", custom_colors)
        assert result is True
        assert "custom" in theme_manager._themes
        assert theme_manager._themes["custom"] == custom_colors
    
    def test_theme_change_callbacks(self, theme_manager):
        """Test theme change callback registration and execution."""
        callback_mock = Mock()
        
        # Register callback
        theme_manager.register_theme_change_callback(callback_mock)
        assert callback_mock in theme_manager._theme_callbacks
        
        # Load theme should trigger callback
        with patch.object(theme_manager, '_apply_theme'):
            with patch.object(theme_manager, '_save_theme_preference'):
                theme_manager.load_theme(ThemeManager.DARK_THEME)
                callback_mock.assert_called_once_with(ThemeManager.DARK_THEME)
        
        # Unregister callback
        theme_manager.unregister_theme_change_callback(callback_mock)
        assert callback_mock not in theme_manager._theme_callbacks
    
    def test_apply_theme_to_widget(self, theme_manager, app):
        """Test applying theme to specific widget."""
        widget = QWidget()
        
        # Mock stylesheet loading
        theme_manager._stylesheets[ThemeManager.DARK_THEME] = "QWidget { background: black; }"
        
        result = theme_manager.apply_theme(widget, ThemeManager.DARK_THEME)
        assert result is True
        assert widget.styleSheet() == "QWidget { background: black; }"
        
        # Test with non-existent theme
        result = theme_manager.apply_theme(widget, "non_existent")
        assert result is False
    
    def test_export_theme(self, theme_manager):
        """Test theme export functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = Path(f.name)
        
        try:
            # Export light theme
            result = theme_manager.export_theme(ThemeManager.LIGHT_THEME, export_path)
            assert result is True
            assert export_path.exists()
            
            # Verify exported content
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            assert data["name"] == ThemeManager.LIGHT_THEME
            assert "colors" in data
            assert data["colors"]["background"] == "#ffffff"
            
        finally:
            if export_path.exists():
                export_path.unlink()
    
    def test_import_theme(self, theme_manager):
        """Test theme import functionality."""
        # Create test theme file
        theme_data = {
            "name": "imported_theme",
            "colors": {
                "background": "#123456",
                "primary_background": "#234567",
                "text": "#ffffff",
                "text_disabled": "#cccccc",
                "accent": "#ff0000",
                "accent_dark": "#cc0000",
                "accent_light": "#ff3333",
                "border": "#888888",
                "button_background": "#123456",
                "button_border": "#888888",
                "button_hover": "#345678",
                "button_pressed": "#012345",
                "button_disabled": "#456789",
                "menu_background": "#123456",
                "menu_hover": "#ff0000",
                "menu_separator": "#888888",
                "success": "#00ff00",
                "warning": "#ffff00",
                "error": "#ff0000",
                "info": "#00ffff"
            },
            "stylesheet": "QWidget { background: #123456; }"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(theme_data, f)
            import_path = Path(f.name)
        
        try:
            # Import theme
            result = theme_manager.import_theme(import_path)
            assert result == "imported_theme"
            assert "imported_theme" in theme_manager._themes
            assert theme_manager._themes["imported_theme"].background == "#123456"
            
        finally:
            if import_path.exists():
                import_path.unlink()
    
    def test_auto_theme_switching(self, theme_manager):
        """Test automatic theme switching functionality."""
        # Test enabling auto switching
        with patch.object(theme_manager._settings, 'setValue') as mock_set:
            theme_manager.set_auto_theme_switching(True)
            mock_set.assert_called_with("theme/auto_switch", True)
        
        # Test checking auto switching status
        with patch.object(theme_manager._settings, 'value', return_value=True):
            assert theme_manager.is_auto_theme_switching() is True
    
    def test_system_theme_change_handler(self, theme_manager):
        """Test system theme change event handling."""
        # Mock auto switching enabled
        with patch.object(theme_manager._settings, 'value', return_value=True):
            with patch.object(theme_manager, 'load_theme') as mock_load:
                # Test dark system theme
                theme_manager._handle_system_theme_change({"theme": "dark"})
                mock_load.assert_called_with(ThemeManager.DARK_THEME)
                
                # Test light system theme
                theme_manager._handle_system_theme_change({"theme": "light"})
                mock_load.assert_called_with(ThemeManager.LIGHT_THEME)
    
    def test_palette_creation(self, theme_manager):
        """Test QPalette creation from theme."""
        palette = theme_manager._create_palette_from_theme(ThemeManager.LIGHT_THEME)
        assert palette is not None
        
        # Test with invalid theme
        palette = theme_manager._create_palette_from_theme("invalid")
        assert palette is None
    
    def test_icon_caching(self, theme_manager):
        """Test themed icon caching."""
        # Mock icon file exists
        with patch('pathlib.Path.exists', return_value=True):
            with patch('torematrix.ui.themes.QIcon') as mock_icon:
                mock_icon_instance = Mock()
                mock_icon.return_value = mock_icon_instance
                
                # Get icon (should cache it)
                icon1 = theme_manager.get_theme_icon("test_icon")
                assert icon1 == mock_icon_instance
                
                # Get same icon again (should use cache)
                icon2 = theme_manager.get_theme_icon("test_icon")
                assert icon2 == mock_icon_instance
                
                # Verify caching
                assert "test_icon" in theme_manager._themed_icons
                assert theme_manager._current_theme in theme_manager._themed_icons["test_icon"]
    
    @patch('torematrix.ui.themes.QApplication.instance')
    def test_load_theme_success(self, mock_app_instance, theme_manager):
        """Test successful theme loading."""
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        
        with patch.object(theme_manager, '_save_theme_preference') as mock_save:
            result = theme_manager.load_theme(ThemeManager.DARK_THEME)
            
            assert result is True
            assert theme_manager._current_theme == ThemeManager.DARK_THEME
            mock_save.assert_called_once_with(ThemeManager.DARK_THEME)
    
    def test_load_theme_failure(self, theme_manager):
        """Test theme loading failure."""
        result = theme_manager.load_theme("non_existent_theme")
        assert result is False
    
    def test_signal_emissions(self, theme_manager):
        """Test that appropriate signals are emitted."""
        with patch.object(theme_manager, '_apply_theme'):
            with patch.object(theme_manager, '_save_theme_preference'):
                # Connect signal spy
                signal_spy = Mock()
                theme_manager.theme_changed.connect(signal_spy)
                
                # Load theme
                theme_manager.load_theme(ThemeManager.DARK_THEME)
                
                # Verify signal was emitted
                signal_spy.assert_called_once_with(ThemeManager.DARK_THEME)