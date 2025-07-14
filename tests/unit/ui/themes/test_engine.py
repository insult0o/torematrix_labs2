"""Tests for the ThemeEngine class."""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import time

from PyQt6.QtWidgets import QWidget

from torematrix.ui.themes import ThemeEngine, Theme, ThemeProvider
from torematrix.ui.themes.engine import FileThemeProvider, BuiltinThemeProvider
from torematrix.ui.themes.exceptions import (
    ThemeNotFoundError, ThemeLoadError, ThemeValidationError
)


class TestThemeEngine:
    """Test cases for ThemeEngine."""
    
    def test_initialization(self, theme_engine):
        """Test theme engine initialization."""
        assert theme_engine is not None
        assert theme_engine.current_theme is None
        assert len(theme_engine.theme_providers) >= 2  # Built-in + file provider
        assert theme_engine.cache_enabled is True
        
    def test_builtin_themes_available(self, theme_engine):
        """Test that built-in themes are available."""
        available_themes = theme_engine.get_available_themes()
        assert 'light' in available_themes
        assert 'dark' in available_themes
        
    def test_load_builtin_theme(self, theme_engine):
        """Test loading built-in theme."""
        theme = theme_engine.load_theme('light')
        assert theme is not None
        assert theme.name == 'light'
        assert theme.metadata.category.value == 'light'
        
    def test_load_nonexistent_theme(self, theme_engine):
        """Test loading non-existent theme raises error."""
        with pytest.raises(ThemeNotFoundError):
            theme_engine.load_theme('nonexistent_theme')
            
    def test_theme_caching(self, theme_engine):
        """Test theme caching functionality."""
        # Load theme twice
        theme1 = theme_engine.load_theme('light')
        theme2 = theme_engine.load_theme('light')
        
        # Should be same instance from cache
        assert theme1 is theme2
        assert 'light' in theme_engine.theme_cache
        
    def test_switch_theme(self, theme_engine, qapp):
        """Test switching between themes."""
        # Switch to light theme
        success = theme_engine.switch_theme('light')
        assert success is True
        assert theme_engine.current_theme.name == 'light'
        
        # Switch to dark theme
        success = theme_engine.switch_theme('dark')
        assert success is True
        assert theme_engine.current_theme.name == 'dark'
        assert theme_engine.previous_theme_name == 'light'
        
    def test_switch_to_invalid_theme(self, theme_engine):
        """Test switching to invalid theme."""
        success = theme_engine.switch_theme('invalid_theme')
        assert success is False
        
    def test_apply_theme_to_widget(self, theme_engine, qapp):
        """Test applying theme to specific widget."""
        theme = theme_engine.load_theme('light')
        widget = QWidget()
        
        # Should not raise exception
        theme_engine.apply_theme(theme, widget)
        
        # Widget should have stylesheet applied
        assert widget.styleSheet() != ""
        
    def test_theme_change_callbacks(self, theme_engine):
        """Test theme change callback registration and execution."""
        callback_called = False
        received_theme = None
        
        def test_callback(theme):
            nonlocal callback_called, received_theme
            callback_called = True
            received_theme = theme
            
        # Register callback
        theme_engine.register_theme_change_callback(test_callback)
        
        # Switch theme
        theme_engine.switch_theme('light')
        
        # Callback should have been called
        assert callback_called is True
        assert received_theme is not None
        assert received_theme.name == 'light'
        
        # Unregister callback
        theme_engine.unregister_theme_change_callback(test_callback)
        
        # Reset
        callback_called = False
        theme_engine.switch_theme('dark')
        
        # Callback should not have been called
        assert callback_called is False
        
    def test_theme_validation(self, theme_engine):
        """Test theme validation functionality."""
        valid_theme_data = {
            'metadata': {
                'name': 'Test',
                'version': '1.0.0',
                'author': 'Tester',
            },
            'colors': {
                'background': '#FFFFFF',
                'text_primary': '#000000',
            }
        }
        
        # Should not raise exception
        assert theme_engine.validate_theme(valid_theme_data) is True
        
        # Test missing required section
        invalid_data = valid_theme_data.copy()
        del invalid_data['colors']
        
        with pytest.raises(ThemeValidationError):
            theme_engine.validate_theme(invalid_data)
            
    def test_clear_cache(self, theme_engine):
        """Test cache clearing."""
        # Load theme to populate cache
        theme_engine.load_theme('light')
        assert len(theme_engine.theme_cache) > 0
        
        # Clear cache
        theme_engine.clear_cache()
        assert len(theme_engine.theme_cache) == 0
        
    def test_performance_stats(self, theme_engine):
        """Test performance statistics."""
        # Load some themes
        theme_engine.load_theme('light')
        theme_engine.load_theme('dark')
        
        stats = theme_engine.get_performance_stats()
        assert 'themes_loaded' in stats
        assert 'avg_load_time' in stats
        assert stats['themes_loaded'] >= 2
        
    def test_theme_metadata_retrieval(self, theme_engine):
        """Test getting theme metadata without loading full theme."""
        metadata = theme_engine.get_theme_metadata('light')
        assert metadata is not None
        assert metadata.name == 'Light Professional'
        assert metadata.category.value == 'light'
        
    def test_register_custom_provider(self, theme_engine):
        """Test registering custom theme provider."""
        mock_provider = Mock(spec=ThemeProvider)
        mock_provider.get_available_themes.return_value = ['custom_theme']
        
        initial_count = len(theme_engine.theme_providers)
        theme_engine.register_theme_provider(mock_provider)
        
        assert len(theme_engine.theme_providers) == initial_count + 1
        assert mock_provider in theme_engine.theme_providers


class TestFileThemeProvider:
    """Test cases for FileThemeProvider."""
    
    def test_initialization(self, temp_themes_dir):
        """Test file provider initialization."""
        provider = FileThemeProvider(temp_themes_dir)
        assert provider.themes_directory == temp_themes_dir
        assert temp_themes_dir.exists()
        
    def test_load_yaml_theme(self, temp_themes_dir, sample_theme_data):
        """Test loading theme from YAML file."""
        provider = FileThemeProvider(temp_themes_dir)
        
        # Create theme file
        theme_file = temp_themes_dir / "test_theme.yaml"
        with open(theme_file, 'w') as f:
            yaml.dump(sample_theme_data, f)
            
        # Load theme
        theme = provider.load_theme('test_theme')
        assert theme.name == 'test_theme'
        assert theme.metadata.name == 'Test Theme'
        
    def test_load_json_theme(self, temp_themes_dir, sample_theme_data):
        """Test loading theme from JSON file."""
        provider = FileThemeProvider(temp_themes_dir)
        
        # Create theme file
        theme_file = temp_themes_dir / "test_theme.json"
        with open(theme_file, 'w') as f:
            json.dump(sample_theme_data, f)
            
        # Load theme
        theme = provider.load_theme('test_theme')
        assert theme.name == 'test_theme'
        
    def test_load_nonexistent_theme(self, temp_themes_dir):
        """Test loading non-existent theme."""
        provider = FileThemeProvider(temp_themes_dir)
        
        with pytest.raises(ThemeNotFoundError):
            provider.load_theme('nonexistent')
            
    def test_get_available_themes(self, temp_themes_dir, sample_theme_data):
        """Test getting available themes."""
        provider = FileThemeProvider(temp_themes_dir)
        
        # Create multiple theme files
        for name in ['theme1', 'theme2', 'theme3']:
            theme_file = temp_themes_dir / f"{name}.yaml"
            with open(theme_file, 'w') as f:
                yaml.dump(sample_theme_data, f)
                
        available = provider.get_available_themes()
        assert 'theme1' in available
        assert 'theme2' in available  
        assert 'theme3' in available
        
    def test_theme_exists(self, temp_themes_dir, sample_theme_data):
        """Test theme existence check."""
        provider = FileThemeProvider(temp_themes_dir)
        
        # Create theme file
        theme_file = temp_themes_dir / "exists.yaml"
        with open(theme_file, 'w') as f:
            yaml.dump(sample_theme_data, f)
            
        assert provider.theme_exists('exists') is True
        assert provider.theme_exists('does_not_exist') is False
        
    def test_cache_functionality(self, temp_themes_dir, sample_theme_data):
        """Test provider caching."""
        provider = FileThemeProvider(temp_themes_dir)
        
        # Create theme file
        theme_file = temp_themes_dir / "cached_theme.yaml"
        with open(theme_file, 'w') as f:
            yaml.dump(sample_theme_data, f)
            
        # Load theme twice
        theme1 = provider.load_theme('cached_theme')
        theme2 = provider.load_theme('cached_theme')
        
        # Should be same instance from cache
        assert theme1 is theme2
        
        # Clear cache
        provider.clear_cache()
        
        # Load again - should be different instance
        theme3 = provider.load_theme('cached_theme')
        assert theme3 is not theme1


class TestBuiltinThemeProvider:
    """Test cases for BuiltinThemeProvider."""
    
    def test_initialization(self):
        """Test built-in provider initialization."""
        provider = BuiltinThemeProvider()
        assert len(provider.get_available_themes()) >= 2
        
    def test_load_light_theme(self):
        """Test loading light theme."""
        provider = BuiltinThemeProvider()
        theme = provider.load_theme('light')
        
        assert theme.name == 'light'
        assert theme.metadata.category.value == 'light'
        assert theme.get_color_palette() is not None
        
    def test_load_dark_theme(self):
        """Test loading dark theme."""
        provider = BuiltinThemeProvider()
        theme = provider.load_theme('dark')
        
        assert theme.name == 'dark'
        assert theme.metadata.category.value == 'dark'
        assert theme.get_color_palette() is not None
        
    def test_theme_exists(self):
        """Test theme existence check."""
        provider = BuiltinThemeProvider()
        
        assert provider.theme_exists('light') is True
        assert provider.theme_exists('dark') is True
        assert provider.theme_exists('nonexistent') is False
        
    def test_load_invalid_theme(self):
        """Test loading invalid theme."""
        provider = BuiltinThemeProvider()
        
        with pytest.raises(ThemeNotFoundError):
            provider.load_theme('invalid_theme')


class TestThemeEngineSignals:
    """Test theme engine signal emissions."""
    
    def test_theme_loading_signal(self, theme_engine):
        """Test theme loading signal emission."""
        signal_received = False
        theme_name_received = None
        
        def on_theme_loading(theme_name):
            nonlocal signal_received, theme_name_received
            signal_received = True
            theme_name_received = theme_name
            
        theme_engine.theme_loading.connect(on_theme_loading)
        theme_engine.load_theme('light')
        
        assert signal_received is True
        assert theme_name_received == 'light'
        
    def test_theme_loaded_signal(self, theme_engine):
        """Test theme loaded signal emission."""
        signal_received = False
        
        def on_theme_loaded(theme_name):
            nonlocal signal_received
            signal_received = True
            
        theme_engine.theme_loaded.connect(on_theme_loaded)
        theme_engine.load_theme('light')
        
        assert signal_received is True
        
    def test_theme_changed_signal(self, theme_engine):
        """Test theme changed signal emission."""
        signal_received = False
        new_theme_received = None
        
        def on_theme_changed(new_theme, previous_theme):
            nonlocal signal_received, new_theme_received
            signal_received = True
            new_theme_received = new_theme
            
        theme_engine.theme_changed.connect(on_theme_changed)
        theme_engine.switch_theme('light')
        
        assert signal_received is True
        assert new_theme_received == 'light'
        
    def test_theme_error_signal(self, theme_engine):
        """Test theme error signal emission."""
        signal_received = False
        error_theme = None
        error_message = None
        
        def on_theme_error(theme_name, message):
            nonlocal signal_received, error_theme, error_message
            signal_received = True
            error_theme = theme_name
            error_message = message
            
        theme_engine.theme_error.connect(on_theme_error)
        
        # Try to load invalid theme
        try:
            theme_engine.load_theme('invalid_theme')
        except ThemeNotFoundError:
            pass
            
        assert signal_received is True
        assert error_theme == 'invalid_theme'
        assert error_message is not None