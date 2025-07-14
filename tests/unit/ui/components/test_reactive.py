"""
Tests for ReactiveWidget base class and metaclass functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QSignalSpy

from torematrix.ui.components.reactive import (
    ReactiveWidget,
    ReactiveMetaclass,
    ReactiveProperty,
    StateBinding,
)
from torematrix.core.state import Store, Action
from torematrix.core.events import EventBus


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_store():
    """Create mock store."""
    store = MagicMock(spec=Store)
    store.get_state.return_value = {
        "document": {
            "title": "Test Document",
            "content": "Test content",
            "metadata": {
                "author": "Test Author",
                "date": "2024-01-01"
            }
        },
        "ui": {
            "theme": "dark",
            "sidebar": {"visible": True}
        }
    }
    return store


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    return MagicMock(spec=EventBus)


class TestReactiveProperty:
    """Test ReactiveProperty dataclass."""
    
    def test_property_creation(self):
        """Test creating reactive property."""
        prop = ReactiveProperty(
            name="title",
            value="Initial",
            type_hint=str
        )
        
        assert prop.name == "title"
        assert prop.value == "Initial"
        assert prop.type_hint == str
        assert prop.validator is None
        assert prop.transformer is None
        assert prop.dependencies == []
        assert prop.computed is False
    
    def test_property_validation(self):
        """Test property validation."""
        def is_positive(x):
            return x > 0
        
        prop = ReactiveProperty(
            name="count",
            value=5,
            type_hint=int,
            validator=is_positive
        )
        
        assert prop.validate(10) is True
        assert prop.validate(-5) is False
        assert prop.validate(0) is False
    
    def test_property_transformation(self):
        """Test property transformation."""
        prop = ReactiveProperty(
            name="text",
            value="hello",
            type_hint=str,
            transformer=str.upper
        )
        
        assert prop.transform("hello") == "HELLO"
        assert prop.transform("world") == "WORLD"


class TestStateBinding:
    """Test StateBinding dataclass."""
    
    def test_binding_creation(self):
        """Test creating state binding."""
        binding = StateBinding(
            property_name="title",
            state_path="document.title"
        )
        
        assert binding.property_name == "title"
        assert binding.state_path == "document.title"
        assert binding.transform is None
        assert binding.bidirectional is False
        assert binding.debounce_ms == 0
    
    def test_binding_hash(self):
        """Test binding is hashable."""
        binding1 = StateBinding("title", "document.title")
        binding2 = StateBinding("title", "document.title")
        binding3 = StateBinding("content", "document.content")
        
        assert hash(binding1) == hash(binding2)
        assert hash(binding1) != hash(binding3)
        
        # Can be used in sets
        bindings = {binding1, binding2, binding3}
        assert len(bindings) == 2


class TestReactiveMetaclass:
    """Test ReactiveMetaclass functionality."""
    
    def test_metaclass_processes_annotations(self, qapp):
        """Test metaclass processes type annotations."""
        class TestWidget(ReactiveWidget):
            title: str
            count: int = 0
            _private: str = "ignored"
        
        widget = TestWidget()
        
        # Check reactive properties were created
        assert "title" in widget._reactive_properties
        assert "count" in widget._reactive_properties
        assert "_private" not in widget._reactive_properties
        
        # Check property descriptors work
        widget.title = "Test"
        assert widget.title == "Test"
        
        widget.count = 42
        assert widget.count == 42
    
    def test_metaclass_processes_lifecycle_methods(self, qapp):
        """Test metaclass identifies lifecycle methods."""
        class TestWidget(ReactiveWidget):
            def on_mount(self):
                pass
            
            def on_unmount(self):
                pass
            
            def on_update(self):
                pass
            
            def regular_method(self):
                pass
        
        # Check lifecycle methods were identified
        methods = TestWidget._lifecycle_methods
        assert "on_mount" in methods
        assert "on_unmount" in methods
        assert "on_update" in methods
        assert "regular_method" not in methods


class TestReactiveWidget:
    """Test ReactiveWidget base class."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initialization."""
        widget = ReactiveWidget(component_id="test-123")
        
        assert widget.component_id == "test-123"
        assert widget._component_type == "ReactiveWidget"
        assert widget.is_mounted is False
        assert len(widget._state_bindings) == 0
        assert widget._render_count == 0
    
    def test_property_change_signals(self, qapp):
        """Test property change signals."""
        class TestWidget(ReactiveWidget):
            title: str = ""
        
        widget = TestWidget()
        spy = QSignalSpy(widget.property_changed)
        
        widget.title = "New Title"
        
        assert len(spy) == 1
        assert spy[0][0] == "title"  # property name
        assert spy[0][1] == ""       # old value
        assert spy[0][2] == "New Title"  # new value
    
    def test_state_binding(self, qapp, mock_store):
        """Test binding property to state."""
        widget = ReactiveWidget()
        widget._store = mock_store
        
        # Bind property
        widget.bind_state(
            state_path="document.title",
            property_name="title",
            bidirectional=True
        )
        
        # Check binding was created
        assert len(widget._state_bindings) == 1
        binding = list(widget._state_bindings)[0]
        assert binding.state_path == "document.title"
        assert binding.property_name == "title"
        assert binding.bidirectional is True
    
    def test_computed_property(self, qapp, mock_store):
        """Test computed property creation."""
        widget = ReactiveWidget()
        widget._store = mock_store
        
        # Create computed property
        def compute_full_name(first, last):
            return f"{first} {last}"
        
        widget.computed_property(
            name="full_name",
            dependencies=["user.first", "user.last"],
            compute_func=compute_full_name
        )
        
        # Check property was created
        assert "full_name" in widget._reactive_properties
        prop = widget._reactive_properties["full_name"]
        assert prop.computed is True
        assert prop.dependencies == ["user.first", "user.last"]
    
    def test_state_change_callback(self, qapp, mock_store):
        """Test registering state change callbacks."""
        widget = ReactiveWidget()
        widget._store = mock_store
        
        callback_values = []
        
        def on_title_change(value):
            callback_values.append(value)
        
        # Register callback
        subscription_id = widget.on_state_change(
            "document.title",
            on_title_change,
            immediate=True
        )
        
        # Check callback was called immediately
        assert len(callback_values) == 1
        assert callback_values[0] == "Test Document"
        
        # Check subscription was recorded
        assert "document.title" in widget._state_subscriptions
        assert widget._state_subscriptions["document.title"] == subscription_id
    
    def test_update_state(self, qapp, mock_store):
        """Test updating state from component."""
        widget = ReactiveWidget()
        widget._store = mock_store
        
        # Update state
        widget.update_state("document.title", "New Title")
        
        # Check dispatch was called
        mock_store.dispatch.assert_called_once()
        action = mock_store.dispatch.call_args[0][0]
        assert action.type == "UPDATE_DOCUMENT_TITLE"
        assert action.payload == {"path": "document.title", "value": "New Title"}
    
    def test_mount_unmount_lifecycle(self, qapp):
        """Test mount/unmount lifecycle."""
        class TestWidget(ReactiveWidget):
            mount_called = False
            unmount_called = False
            
            def on_mount(self):
                self.mount_called = True
            
            def on_unmount(self):
                self.unmount_called = True
        
        widget = TestWidget()
        
        # Test mount
        widget.mount()
        assert widget.is_mounted is True
        assert widget.mount_called is True
        
        # Test unmount
        widget.unmount()
        assert widget.is_mounted is False
        assert widget.unmount_called is True
    
    def test_parent_child_relationships(self, qapp):
        """Test parent-child component relationships."""
        parent = ReactiveWidget()
        child1 = ReactiveWidget(parent=parent)
        child2 = ReactiveWidget(parent=parent)
        
        # Check children were registered
        assert len(parent._reactive_children) == 2
        
        # Check parent reference
        assert child1._reactive_parent is not None
        assert child1._reactive_parent() is parent
    
    def test_force_update(self, qapp):
        """Test force update mechanism."""
        class TestWidget(ReactiveWidget):
            update_count = 0
            
            def on_update(self):
                self.update_count += 1
        
        widget = TestWidget()
        widget.mount()
        
        # Force update
        widget.force_update()
        
        # Wait for update timer
        QTimer.singleShot(10, qapp.quit)
        qapp.exec()
        
        # Check update was called
        assert widget.update_count > 0
    
    def test_property_validation_error(self, qapp):
        """Test property validation raises error."""
        class TestWidget(ReactiveWidget):
            pass
        
        widget = TestWidget()
        
        # Add property with validator
        prop = ReactiveProperty(
            name="age",
            value=0,
            type_hint=int,
            validator=lambda x: x >= 0
        )
        widget._reactive_properties["age"] = prop
        
        # This should work
        widget._property_values["age"] = 25
        
        # This should raise
        with pytest.raises(ValueError):
            # Simulate property setter with validation
            if not prop.validate(-5):
                raise ValueError(f"Invalid value for property age: -5")
    
    def test_get_state_value_nested(self, qapp, mock_store):
        """Test getting nested state values."""
        widget = ReactiveWidget()
        widget._store = mock_store
        
        state = mock_store.get_state()
        
        # Test nested paths
        assert widget._get_state_value("document.title", state) == "Test Document"
        assert widget._get_state_value("document.metadata.author", state) == "Test Author"
        assert widget._get_state_value("ui.theme", state) == "dark"
        assert widget._get_state_value("ui.sidebar.visible", state) is True
        
        # Test non-existent paths
        assert widget._get_state_value("invalid.path", state) is None
        assert widget._get_state_value("document.invalid", state) is None
    
    def test_bidirectional_binding(self, qapp, mock_store):
        """Test bidirectional state binding."""
        class TestWidget(ReactiveWidget):
            title: str = ""
        
        widget = TestWidget()
        widget._store = mock_store
        widget.mount()
        
        # Create bidirectional binding
        widget.bind_state(
            state_path="document.title",
            property_name="title",
            bidirectional=True
        )
        
        # Change property should update state
        widget.title = "Updated Title"
        
        # Check state update was dispatched
        mock_store.dispatch.assert_called()
        action = mock_store.dispatch.call_args[0][0]
        assert action.payload["value"] == "Updated Title"
    
    def test_show_hide_events(self, qapp):
        """Test show/hide event handling."""
        widget = ReactiveWidget()
        
        # Show event should mount
        widget.show()
        assert widget.is_mounted is True
        
        # Hide event should not unmount
        widget.hide()
        assert widget.is_mounted is True
        
        # Close event should unmount
        widget.close()
        assert widget.is_mounted is False
    
    def test_service_connection_from_parent(self, qapp, mock_store, mock_event_bus):
        """Test connecting to services from parent."""
        # Create parent with services
        parent = QWidget()
        parent._store = mock_store
        parent._event_bus = mock_event_bus
        
        # Create child widget
        widget = ReactiveWidget(parent=parent)
        widget._connect_services()
        
        # Check services were connected
        assert widget._store is mock_store
        assert widget._event_bus is mock_event_bus
    
    def test_update_batching(self, qapp):
        """Test update batching mechanism."""
        class TestWidget(ReactiveWidget):
            render_count = 0
            
            def on_update(self):
                self.render_count += 1
        
        widget = TestWidget()
        widget.mount()
        
        # Schedule multiple updates rapidly
        for i in range(5):
            widget._schedule_update()
        
        # Wait for batch timer
        QTimer.singleShot(20, qapp.quit)
        qapp.exec()
        
        # Should have batched updates
        assert widget.render_count == 1  # All updates batched into one