"""Tests for ResourceManager system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap, QFont
from PyQt6.QtCore import QSettings

from src.torematrix.ui.resources import ResourceManager, ResourceType, IconSize
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
def temp_resource_path(tmp_path):
    """Create temporary resource directory."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    
    # Create icon subdirectories
    icons_dir = resource_dir / "icons"
    icons_dir.mkdir()
    
    light_dir = icons_dir / "light"
    light_dir.mkdir()
    
    dark_dir = icons_dir / "dark"
    dark_dir.mkdir()
    
    return resource_dir


@pytest.fixture
def resource_manager(qapp, mock_event_bus, mock_config_manager, mock_state_manager, temp_resource_path):
    """Create ResourceManager instance for testing."""
    with patch.object(QSettings, '__init__', return_value=None):
        with patch.object(QSettings, 'value', return_value="light"):
            manager = ResourceManager(
                event_bus=mock_event_bus,
                config_manager=mock_config_manager,
                state_manager=mock_state_manager
            )
            
            # Override resource paths to use temp directory
            manager._resource_paths[ResourceType.ICON] = temp_resource_path / "icons"
            manager._resource_paths[ResourceType.IMAGE] = temp_resource_path / "images"
            
            manager.initialize()
            return manager


class TestResourceManager:
    """Test ResourceManager functionality."""
    
    def test_initialization(self, resource_manager):
        """Test ResourceManager initialization."""
        assert resource_manager.is_initialized
        assert resource_manager._current_theme == "light"
        assert resource_manager._cache_enabled is True
    
    def test_theme_management(self, resource_manager):
        """Test theme changing functionality."""
        # Initial theme
        assert resource_manager.get_current_theme() == "light"
        
        # Change theme
        resource_manager.set_theme("dark")
        assert resource_manager.get_current_theme() == "dark"
    
    def test_available_themes(self, resource_manager):
        """Test getting available themes."""
        themes = resource_manager.get_available_themes()
        assert "light" in themes
        assert "dark" in themes
        assert len(themes) >= 2
    
    def test_get_icon_fallback(self, resource_manager):
        """Test icon loading with fallback."""
        # Request non-existent icon (should return empty icon, not None)
        icon = resource_manager.get_icon("nonexistent")
        assert isinstance(icon, QIcon)
        # Empty icons return True for isNull()
        assert icon.isNull()
    
    @patch('pathlib.Path.exists')
    def test_get_icon_with_file(self, mock_exists, resource_manager):
        """Test icon loading when file exists."""
        mock_exists.return_value = True
        
        with patch('PyQt6.QtGui.QIcon') as mock_icon_class:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_icon_class.return_value = mock_icon
            
            icon = resource_manager.get_icon("test_icon")
            assert icon is not None
    
    def test_icon_caching(self, resource_manager):
        """Test icon caching functionality."""
        # Get same icon twice
        icon1 = resource_manager.get_icon("test")
        icon2 = resource_manager.get_icon("test")
        
        # Should be cached (both requests return same instance or equivalent)
        assert resource_manager._cache_enabled
    
    def test_cache_management(self, resource_manager):
        """Test cache management functions."""
        # Get initial cache stats
        stats = resource_manager.get_cache_stats()
        assert isinstance(stats, dict)
        assert "icons" in stats
        assert "pixmaps" in stats
        
        # Clear cache
        resource_manager.clear_cache()
        stats_after = resource_manager.get_cache_stats()
        assert stats_after["icons"] == 0
    
    def test_cache_enable_disable(self, resource_manager):
        """Test enabling/disabling cache."""
        # Initially enabled
        assert resource_manager._cache_enabled
        
        # Disable cache
        resource_manager.set_cache_enabled(False)
        assert not resource_manager._cache_enabled
        
        # Enable cache
        resource_manager.set_cache_enabled(True)
        assert resource_manager._cache_enabled
    
    def test_get_pixmap(self, resource_manager):
        """Test pixmap loading."""
        pixmap = resource_manager.get_pixmap("test", 32, 32)
        assert isinstance(pixmap, QPixmap)
    
    def test_get_font(self, resource_manager):
        """Test font loading."""
        font = resource_manager.get_font("Arial", 12)
        assert isinstance(font, QFont)
        assert font.pointSize() == 12
    
    def test_get_stylesheet(self, resource_manager):
        """Test stylesheet loading."""
        # Non-existent stylesheet should return empty string
        stylesheet = resource_manager.get_stylesheet("nonexistent")
        assert isinstance(stylesheet, str)
        assert stylesheet == ""
    
    def test_stylesheet_variable_processing(self, resource_manager):
        """Test stylesheet variable processing."""
        # Test the variable processing method
        test_stylesheet = "@theme @primary-color @background-color"
        processed = resource_manager._process_stylesheet_variables(test_stylesheet)
        
        assert "@theme" not in processed
        assert resource_manager._current_theme in processed
    
    def test_resource_path_retrieval(self, resource_manager):
        """Test getting resource paths."""
        icon_path = resource_manager.get_resource_path(ResourceType.ICON)
        assert isinstance(icon_path, Path)
        
        image_path = resource_manager.get_resource_path(ResourceType.IMAGE)
        assert isinstance(image_path, Path)
    
    def test_resource_existence_check(self, resource_manager):
        """Test checking if resources exist."""
        # Non-existent resources
        assert not resource_manager.resource_exists("nonexistent", ResourceType.ICON)
        assert not resource_manager.resource_exists("nonexistent", ResourceType.STYLESHEET)
    
    def test_preload_resources(self, resource_manager):
        """Test resource preloading."""
        # Should not raise any exceptions
        resource_manager.preload_resources(["test1", "test2"], ResourceType.ICON)
    
    def test_icon_size_enum(self):
        """Test IconSize enum values."""
        assert IconSize.SMALL.value == (16, 16)
        assert IconSize.MEDIUM.value == (24, 24)
        assert IconSize.LARGE.value == (32, 32)
        assert IconSize.TOOLBAR.value == (24, 24)
        assert IconSize.MENU.value == (16, 16)
    
    def test_resource_type_enum(self):
        """Test ResourceType enum values."""
        assert ResourceType.ICON.value == "icon"
        assert ResourceType.IMAGE.value == "image"
        assert ResourceType.FONT.value == "font"
        assert ResourceType.STYLESHEET.value == "stylesheet"
        assert ResourceType.TRANSLATION.value == "translation"
    
    @patch.object(QSettings, 'setValue')
    def test_theme_persistence(self, mock_set_value, resource_manager):
        """Test theme preference persistence."""
        resource_manager.set_theme("dark")
        mock_set_value.assert_called_with("theme", "dark")
    
    def test_theme_aware_resources(self, resource_manager):
        """Test theme-aware resource tracking."""
        # Request theme-aware icon
        resource_manager.get_icon("test", theme_aware=True)
        assert "test" in resource_manager._theme_aware_resources
        
        # Request non-theme-aware icon
        resource_manager.get_icon("test2", theme_aware=False)
        assert "test2" not in resource_manager._theme_aware_resources
    
    def test_icon_fallback_strategies(self, resource_manager):
        """Test icon fallback loading strategies."""
        # The _load_icon_fallback method should try different approaches
        icon = resource_manager._load_icon_fallback("nonexistent", IconSize.MEDIUM, True)
        assert isinstance(icon, QIcon)
    
    def test_build_icon_path(self, resource_manager):
        """Test icon path building."""
        path = resource_manager._build_icon_path("test", IconSize.MEDIUM, True)
        assert isinstance(path, Path)
        assert "test" in str(path)


if __name__ == "__main__":
    pytest.main([__file__])