"""Unit tests for LayoutManager core functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from PyQt6.QtWidgets import QWidget, QLabel, QMainWindow, QStackedWidget
from PyQt6.QtCore import QObject, QTimer, QSize
from PyQt6.QtTest import QSignalSpy

from torematrix.ui.layouts.manager import LayoutManager, LayoutTransitionError, LayoutValidationError
from torematrix.ui.layouts.base import (
    LayoutType, LayoutState, LayoutGeometry, LayoutItem, LayoutConfiguration,
    BaseLayout, LayoutProvider
)


class MockEventBus(QObject):
    """Mock event bus for testing."""
    
    def __init__(self):
        super().__init__()
        self.events = []
        self.subscriptions = {}
    
    def publish_event(self, event_type, data):
        self.events.append((event_type, data))
    
    def subscribe_to_event(self, event_type, handler):
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        self.subscriptions[event_type].append(handler)


class MockConfigManager:
    """Mock configuration manager for testing."""
    
    def __init__(self):
        self.config = {}
    
    def get_config(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set_config(self, key, value):
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value


class MockStateManager:
    """Mock state manager for testing."""
    
    def __init__(self):
        self.state = {}
    
    def get_state(self, key, default=None):
        return self.state.get(key, default)
    
    def set_state(self, key, value):
        self.state[key] = value


class MockLayout(BaseLayout):
    """Mock layout implementation for testing."""
    
    def __init__(self, config: LayoutConfiguration):
        super().__init__(config)
        self._mock_container = QWidget()
        self._create_called = False
        self._apply_called = False
    
    def create_container(self) -> QWidget:
        self._create_called = True
        return self._mock_container
    
    def apply_layout(self) -> bool:
        self._apply_called = True
        return True
    
    def add_item(self, item: LayoutItem) -> bool:
        self._items[item.id] = item
        self.item_added.emit(item)
        return True
    
    def remove_item(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
        return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        if item_id in self._items:
            self._items[item_id] = item
            return True
        return False


class MockLayoutProvider:
    """Mock layout provider for testing."""
    
    def get_supported_layouts(self):
        return [LayoutType.CUSTOM]
    
    def create_layout(self, layout_type, config):
        if layout_type == LayoutType.CUSTOM:
            return QWidget()
        return None
    
    def validate_configuration(self, config):
        return True


class TestLayoutManager:
    """Test LayoutManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.main_window = QMainWindow()
        self.event_bus = MockEventBus()
        self.config_manager = MockConfigManager()
        self.state_manager = MockStateManager()
        
        self.manager = LayoutManager(
            self.main_window,
            self.event_bus,
            self.config_manager,
            self.state_manager
        )
    
    def test_initialization(self):
        """Test layout manager initialization."""
        assert self.manager._main_window == self.main_window
        assert self.manager._current_layout is None
        assert len(self.manager._layouts) == 0
        assert len(self.manager._templates) == 0
        assert len(self.manager._providers) == 0
        assert self.manager._switching_enabled is True
        assert isinstance(self.manager._layout_stack, QStackedWidget)
    
    def test_template_registration(self):
        """Test layout template registration."""
        # Track signal
        spy = QSignalSpy(self.manager.template_registered)
        
        # Register template
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        
        assert LayoutType.DOCUMENT in self.manager._templates
        assert self.manager._templates[LayoutType.DOCUMENT] == mock_factory
        assert len(spy) == 1
        assert spy[0][0] == LayoutType.DOCUMENT
    
    def test_provider_registration(self):
        """Test layout provider registration."""
        provider = MockLayoutProvider()
        
        self.manager.register_provider(provider)
        
        assert provider in self.manager._providers
    
    def test_component_registration(self):
        """Test UI component registration."""
        widget = QLabel("Test Component")
        
        # Track signal
        spy = QSignalSpy(self.manager.component_registered)
        
        self.manager.register_component("comp1", widget)
        
        assert "comp1" in self.manager._registered_components
        assert self.manager._registered_components["comp1"] == widget
        assert len(spy) == 1
        assert spy[0][0] == "comp1"
        assert spy[0][1] == widget
    
    def test_component_unregistration(self):
        """Test UI component unregistration."""
        widget = QLabel("Test Component")
        
        # Register first
        self.manager.register_component("comp1", widget)
        assert "comp1" in self.manager._registered_components
        
        # Unregister
        self.manager.unregister_component("comp1")
        assert "comp1" not in self.manager._registered_components
    
    def test_create_layout_success(self):
        """Test successful layout creation."""
        # Register template
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        
        # Create layout
        layout_id = self.manager.create_layout(
            LayoutType.DOCUMENT,
            "Test Layout",
            LayoutGeometry(width=1200, height=800)
        )
        
        assert layout_id in self.manager._layouts
        layout = self.manager._layouts[layout_id]
        assert layout.config.name == "Test Layout"
        assert layout.config.layout_type == LayoutType.DOCUMENT
        assert layout.config.geometry.width == 1200
        assert layout.config.geometry.height == 800
    
    def test_create_layout_no_template(self):
        """Test layout creation with no registered template."""
        with pytest.raises(LayoutValidationError):
            self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
    
    def test_activate_layout_success(self):
        """Test successful layout activation."""
        # Setup
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        # Track signals
        spy_activated = QSignalSpy(self.manager.layout_activated)
        
        # Activate layout
        result = self.manager.activate_layout(layout_id)
        
        assert result is True
        assert self.manager._current_layout is not None
        assert self.manager._current_layout.config.id == layout_id
        assert self.manager._current_layout.state == LayoutState.ACTIVE
        assert len(spy_activated) == 1
        
        # Check events published
        events = [event for event in self.event_bus.events if event[0] == "layout.activated"]
        assert len(events) == 1
        assert events[0][1]["layout_id"] == layout_id
    
    def test_activate_layout_not_found(self):
        """Test activation of non-existent layout."""
        result = self.manager.activate_layout("non-existent")
        
        assert result is False
        assert self.manager._current_layout is None
    
    def test_deactivate_current_layout(self):
        """Test deactivation of current layout."""
        # Setup and activate
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        self.manager.activate_layout(layout_id)
        
        # Track signals
        spy_deactivated = QSignalSpy(self.manager.layout_deactivated)
        
        # Deactivate
        result = self.manager.deactivate_current_layout()
        
        assert result is True
        assert self.manager._current_layout is None
        assert len(spy_deactivated) == 1
        assert spy_deactivated[0][0] == layout_id
        
        # Check events published
        events = [event for event in self.event_bus.events if event[0] == "layout.deactivated"]
        assert len(events) == 1
        assert events[0][1]["layout_id"] == layout_id
    
    def test_switch_layout_immediate(self):
        """Test immediate layout switching."""
        # Setup layouts
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout1_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 1")
        layout2_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 2")
        
        # Activate first layout
        self.manager.activate_layout(layout1_id)
        
        # Track signals
        spy_switched = QSignalSpy(self.manager.layout_switched)
        
        # Switch to second layout
        result = self.manager.switch_layout(layout2_id, transition=False)
        
        assert result is True
        assert self.manager._current_layout.config.id == layout2_id
        assert len(spy_switched) == 1
        assert spy_switched[0][0] == layout1_id
        assert spy_switched[0][1] == layout2_id
    
    def test_switch_layout_with_transition(self):
        """Test layout switching with transition."""
        # Setup layouts
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout1_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 1")
        layout2_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 2")
        
        # Set short transition time for testing
        self.manager.set_transition_duration(10)
        
        # Activate first layout
        self.manager.activate_layout(layout1_id)
        
        # Switch with transition
        result = self.manager.switch_layout(layout2_id, transition=True)
        
        assert result is True
        assert self.manager._pending_layout == layout2_id
        
        # Simulate transition completion
        self.manager._complete_layout_transition()
        
        assert self.manager._current_layout.config.id == layout2_id
        assert self.manager._pending_layout is None
    
    def test_switch_layout_disabled(self):
        """Test layout switching when disabled."""
        self.manager.set_switching_enabled(False)
        
        result = self.manager.switch_layout("any-layout")
        
        assert result is False
        assert not self.manager.is_switching_enabled()
    
    def test_add_component_to_layout(self):
        """Test adding component to layout."""
        # Setup
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        widget = QLabel("Test Component")
        self.manager.register_component("comp1", widget)
        
        # Add component to layout
        result = self.manager.add_component_to_layout(
            layout_id,
            "comp1",
            name="Test Component",
            visible=True
        )
        
        assert result is True
        assert "comp1" in self.manager._component_layouts
        assert self.manager._component_layouts["comp1"] == layout_id
        
        layout = self.manager._layouts[layout_id]
        assert "comp1" in layout.items
    
    def test_remove_component_from_layout(self):
        """Test removing component from layout."""
        # Setup
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        widget = QLabel("Test Component")
        self.manager.register_component("comp1", widget)
        self.manager.add_component_to_layout(layout_id, "comp1")
        
        # Remove component from layout
        result = self.manager.remove_component_from_layout(layout_id, "comp1")
        
        assert result is True
        assert "comp1" not in self.manager._component_layouts
        
        layout = self.manager._layouts[layout_id]
        assert "comp1" not in layout.items
    
    def test_delete_layout(self):
        """Test layout deletion."""
        # Setup
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        # Activate layout
        self.manager.activate_layout(layout_id)
        assert self.manager._current_layout is not None
        
        # Delete layout
        result = self.manager.delete_layout(layout_id)
        
        assert result is True
        assert layout_id not in self.manager._layouts
        assert self.manager._current_layout is None
    
    def test_layout_history(self):
        """Test layout history navigation."""
        # Setup multiple layouts
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout1_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 1")
        layout2_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 2")
        layout3_id = self.manager.create_layout(LayoutType.DOCUMENT, "Layout 3")
        
        # Activate layouts in sequence
        self.manager.activate_layout(layout1_id)
        self.manager.activate_layout(layout2_id)
        self.manager.activate_layout(layout3_id)
        
        # Current should be layout 3
        assert self.manager._current_layout.config.id == layout3_id
        
        # Go back to layout 2
        result = self.manager.go_back()
        assert result is True
        assert self.manager._current_layout.config.id == layout2_id
        
        # Go back to layout 1
        result = self.manager.go_back()
        assert result is True
        assert self.manager._current_layout.config.id == layout1_id
        
        # Can't go back further
        result = self.manager.go_back()
        assert result is False
        
        # Go forward to layout 2
        result = self.manager.go_forward()
        assert result is True
        assert self.manager._current_layout.config.id == layout2_id
    
    def test_get_layout_types(self):
        """Test getting available layout types."""
        # Register template and provider
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        
        provider = MockLayoutProvider()
        self.manager.register_provider(provider)
        
        layout_types = self.manager.get_layout_types()
        
        assert LayoutType.DOCUMENT in layout_types
        assert LayoutType.CUSTOM in layout_types
    
    def test_switching_context_manager(self):
        """Test switching disabled context manager."""
        assert self.manager.is_switching_enabled() is True
        
        with self.manager.switching_disabled():
            assert self.manager.is_switching_enabled() is False
        
        assert self.manager.is_switching_enabled() is True
    
    def test_transition_duration_setting(self):
        """Test transition duration setting."""
        self.manager.set_transition_duration(500)
        assert self.manager.get_transition_duration() == 500
        
        # Negative values should be clamped to 0
        self.manager.set_transition_duration(-100)
        assert self.manager.get_transition_duration() == 0
    
    def test_auto_save_configuration(self):
        """Test auto-save configuration."""
        # Create and activate layout
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        self.manager.activate_layout(layout_id)
        
        # Trigger auto-save
        self.manager._auto_save_current_layout()
        
        # Check config was saved
        saved_config = self.config_manager.get_config(f"layouts.saved.{layout_id}")
        assert saved_config is not None
    
    def test_event_handling(self):
        """Test event handling."""
        # Setup layout
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        # Test layout switch request event
        if "layout.request_switch" in self.event_bus.subscriptions:
            handler = self.event_bus.subscriptions["layout.request_switch"][0]
            handler({"layout_id": layout_id})
            
            # Should attempt to switch (will fail since layout not activated first)
            # But the handler should have been called
    
    def test_error_handling_invalid_layout_creation(self):
        """Test error handling for invalid layout creation."""
        # Try to create layout without registered template
        with pytest.raises(LayoutValidationError):
            self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
    
    def test_layout_signals_connected(self):
        """Test that layout signals are properly connected."""
        # Setup
        def mock_factory(config):
            return MockLayout(config)
        
        self.manager.register_template(LayoutType.DOCUMENT, mock_factory)
        layout_id = self.manager.create_layout(LayoutType.DOCUMENT, "Test Layout")
        
        layout = self.manager._layouts[layout_id]
        
        # Test state change signal
        layout.set_state(LayoutState.ACTIVE)
        
        # Check event was published
        events = [event for event in self.event_bus.events if event[0] == "layout.state_changed"]
        assert len(events) == 1
        assert events[0][1]["layout_id"] == layout_id
        assert events[0][1]["state"] == LayoutState.ACTIVE.value


if __name__ == "__main__":
    pytest.main([__file__])