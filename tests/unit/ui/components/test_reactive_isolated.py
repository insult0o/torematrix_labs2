"""
Isolated tests for ReactiveWidget that work without full dependencies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy

# Import only the reactive components
from torematrix.ui.components.reactive import (
    ReactiveWidget,
    ReactiveProperty,
    StateBinding,
    ReactiveMetaclass
)


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestReactiveWidgetCore:
    """Test core ReactiveWidget functionality."""
    
    def test_basic_initialization(self, qapp):
        """Test basic widget initialization."""
        widget = ReactiveWidget()
        
        assert widget.component_id
        assert widget._component_type == "ReactiveWidget"
        assert not widget.is_mounted
        assert len(widget._state_bindings) == 0
    
    def test_reactive_property_creation(self, qapp):
        """Test reactive property creation via metaclass."""
        class TestWidget(ReactiveWidget):
            title: str = "Default"
            count: int = 0
        
        widget = TestWidget()
        
        # Properties should be tracked
        assert "title" in widget._reactive_properties
        assert "count" in widget._reactive_properties
        
        # Can get/set values
        assert widget.title == "Default"
        widget.title = "New Title"
        assert widget.title == "New Title"
    
    def test_property_change_signals(self, qapp):
        """Test property change signals."""
        class TestWidget(ReactiveWidget):
            value: str = ""
        
        widget = TestWidget()
        spy = QSignalSpy(widget.property_changed)
        
        widget.value = "test"
        
        assert len(spy) == 1
        assert spy[0] == ["value", "", "test"]
    
    def test_lifecycle_methods(self, qapp):
        """Test lifecycle method detection."""
        class TestWidget(ReactiveWidget):
            mount_called = False
            
            def on_mount(self):
                self.mount_called = True
        
        widget = TestWidget()
        widget.mount()
        
        assert widget.mount_called
        assert widget.is_mounted
    
    def test_state_binding_creation(self, qapp):
        """Test state binding creation."""
        widget = ReactiveWidget()
        
        widget.bind_state(
            state_path="app.title",
            property_name="title",
            bidirectional=True
        )
        
        assert len(widget._state_bindings) == 1
        binding = list(widget._state_bindings)[0]
        assert binding.state_path == "app.title"
        assert binding.property_name == "title"
        assert binding.bidirectional
    
    def test_computed_property_setup(self, qapp):
        """Test computed property setup."""
        widget = ReactiveWidget()
        
        def compute_full(first, last):
            return f"{first} {last}"
        
        widget.computed_property(
            name="full_name",
            dependencies=["user.first", "user.last"],
            compute_func=compute_full
        )
        
        assert "full_name" in widget._reactive_properties
        prop = widget._reactive_properties["full_name"]
        assert prop.computed
        assert prop.dependencies == ["user.first", "user.last"]


class TestReactiveProperty:
    """Test ReactiveProperty dataclass."""
    
    def test_property_basic(self):
        """Test basic property creation."""
        prop = ReactiveProperty(
            name="test",
            value=42,
            type_hint=int
        )
        
        assert prop.name == "test"
        assert prop.value == 42
        assert prop.type_hint == int
    
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
        
        assert prop.validate(10)
        assert not prop.validate(-5)
    
    def test_property_transformation(self):
        """Test property transformation."""
        prop = ReactiveProperty(
            name="text",
            value="hello",
            type_hint=str,
            transformer=str.upper
        )
        
        assert prop.transform("hello") == "HELLO"


class TestStateBinding:
    """Test StateBinding dataclass."""
    
    def test_binding_creation(self):
        """Test binding creation."""
        binding = StateBinding(
            property_name="title",
            state_path="document.title"
        )
        
        assert binding.property_name == "title"
        assert binding.state_path == "document.title"
        assert not binding.bidirectional
        assert binding.debounce_ms == 0
    
    def test_binding_hashable(self):
        """Test binding is hashable for sets."""
        b1 = StateBinding("title", "doc.title")
        b2 = StateBinding("title", "doc.title")
        b3 = StateBinding("name", "doc.name")
        
        bindings = {b1, b2, b3}
        assert len(bindings) == 2  # b1 and b2 are same


if __name__ == "__main__":
    pytest.main([__file__, "-v"])