"""PyQt test fixtures and utilities for UI testing."""

import pytest
import sys
from unittest.mock import Mock, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("ToreMatrix Test")
    yield app
    # Don't quit the app - let pytest handle cleanup


@pytest.fixture
def qapp_test(qapp):
    """Ensure clean QApplication state for each test."""
    # Process any pending events
    qapp.processEvents()
    yield qapp
    # Clean up after test
    qapp.processEvents()


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    event_bus = Mock()
    event_bus.publish = Mock()
    event_bus.subscribe = Mock()
    event_bus.unsubscribe = Mock()
    return event_bus


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager for testing."""
    config_manager = Mock()
    config_manager.get = Mock(return_value=None)
    config_manager.set = Mock()
    config_manager.save = Mock()
    config_manager.load = Mock()
    return config_manager


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager for testing."""
    state_manager = Mock()
    state_manager.get_state = Mock(return_value=None)
    state_manager.set_state = Mock()
    state_manager.save_state = Mock()
    state_manager.restore_state = Mock()
    return state_manager


@pytest.fixture
def main_window_dependencies(mock_event_bus, mock_config_manager, mock_state_manager):
    """Provide all dependencies needed for MainWindow."""
    return {
        'event_bus': mock_event_bus,
        'config_manager': mock_config_manager,
        'state_manager': mock_state_manager
    }


def process_events_until(condition_func, timeout_ms=1000):
    """Process Qt events until a condition is met or timeout."""
    import time
    start_time = time.time()
    timeout_s = timeout_ms / 1000.0
    
    while not condition_func() and (time.time() - start_time) < timeout_s:
        QApplication.processEvents()
        time.sleep(0.01)
    
    return condition_func()


def wait_for_signal(signal, timeout_ms=1000):
    """Wait for a Qt signal to be emitted."""
    result = {'emitted': False, 'args': None}
    
    def on_signal(*args):
        result['emitted'] = True
        result['args'] = args
    
    signal.connect(on_signal)
    
    process_events_until(lambda: result['emitted'], timeout_ms)
    
    try:
        signal.disconnect(on_signal)
    except:
        pass
    
    return result['emitted'], result['args']