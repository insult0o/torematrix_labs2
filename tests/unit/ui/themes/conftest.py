"""Test fixtures for theme framework tests."""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from torematrix.core.config import ConfigManager
from torematrix.core.events import EventBus
from torematrix.ui.themes import ThemeEngine, Theme, ThemeMetadata
from torematrix.ui.themes.types import ThemeType, ThemeData


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    config = Mock(spec=ConfigManager)
    config.get.return_value = "test_themes"
    config.set.return_value = None
    return config


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    event_bus = Mock(spec=EventBus)
    event_bus.emit.return_value = None
    return event_bus


@pytest.fixture
def temp_themes_dir():
    """Temporary directory for theme files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_theme_data():
    """Sample theme data for testing."""
    return {
        'metadata': {
            'name': 'Test Theme',
            'version': '1.0.0',
            'description': 'A test theme',
            'author': 'Test Author',
            'category': 'light',
            'accessibility_compliant': True,
        },
        'colors': {
            'primary': '#2196F3',
            'background': '#FFFFFF',
            'text_primary': '#000000',
            'text_secondary': '#666666',
        },
        'typography': {
            'default': {
                'font_family': 'Arial',
                'font_size': 12,
                'font_weight': 400,
            }
        },
        'components': {
            'main_window': {
                'background': '${colors.background}',
            }
        }
    }


@pytest.fixture
def sample_theme_metadata():
    """Sample theme metadata."""
    return ThemeMetadata(
        name='Test Theme',
        version='1.0.0',
        description='A test theme',
        author='Test Author',
        category=ThemeType.LIGHT,
        accessibility_compliant=True,
    )


@pytest.fixture
def sample_theme(sample_theme_metadata, sample_theme_data):
    """Sample theme instance."""
    return Theme('test_theme', sample_theme_metadata, sample_theme_data)


@pytest.fixture
def theme_engine(mock_config_manager, mock_event_bus, temp_themes_dir, monkeypatch):
    """Theme engine instance for testing."""
    # Mock the themes directory path
    monkeypatch.setattr(Path, '__new__', lambda cls, path: temp_themes_dir if path == 'test_themes' else Path.__new__(cls, path))
    
    engine = ThemeEngine(mock_config_manager, mock_event_bus)
    yield engine
    engine.cleanup()


@pytest.fixture
def qapp():
    """QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app