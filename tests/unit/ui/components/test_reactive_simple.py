"""
Simple tests for reactive components that avoid import conflicts.
"""

import pytest
from PyQt6.QtWidgets import QApplication

# Direct imports from our modules
from torematrix.ui.components.reactive import (
    ReactiveWidget,
    ReactiveProperty,
    StateBinding,
    ReactiveMetaclass
)
from torematrix.ui.components.decorators import (
    reactive_property,
    computed,
    bind_state,
    lifecycle,
    throttle,
    memoize
)
from torematrix.ui.components.lifecycle import (
    LifecycleManager,
    LifecyclePhase,
    RenderMetrics,
    get_lifecycle_manager
)


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestReactiveProperty:
    """Test ReactiveProperty dataclass."""
    
    def test_property_creation(self):
        """Test creating reactive property."""
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
        
        assert prop.validate(10) is True
        assert prop.validate(-5) is False


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
        assert binding.bidirectional is False
    
    def test_binding_hashable(self):
        """Test binding is hashable."""
        b1 = StateBinding("title", "doc.title")
        b2 = StateBinding("title", "doc.title")
        b3 = StateBinding("name", "doc.name")
        
        bindings = {b1, b2, b3}
        assert len(bindings) == 2


class TestReactiveWidget:
    """Test ReactiveWidget base class."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initialization."""
        widget = ReactiveWidget(component_id="test-123")
        
        assert widget.component_id == "test-123"
        assert widget.is_mounted is False
        assert len(widget._state_bindings) == 0
    
    def test_reactive_properties(self, qapp):
        """Test reactive property creation."""
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
    
    def test_lifecycle_methods(self, qapp):
        """Test lifecycle methods."""
        class TestWidget(ReactiveWidget):
            mount_called = False
            unmount_called = False
            
            def on_mount(self):
                self.mount_called = True
            
            def on_unmount(self):
                self.unmount_called = True
        
        widget = TestWidget()
        
        # Mount
        widget.mount()
        assert widget.is_mounted is True
        assert widget.mount_called is True
        
        # Unmount
        widget.unmount()
        assert widget.is_mounted is False
        assert widget.unmount_called is True


class TestLifecyclePhase:
    """Test LifecyclePhase enum."""
    
    def test_phases_exist(self):
        """Test all phases are defined."""
        assert LifecyclePhase.UNMOUNTED
        assert LifecyclePhase.MOUNTING
        assert LifecyclePhase.MOUNTED
        assert LifecyclePhase.UPDATING
        assert LifecyclePhase.UNMOUNTING
        assert LifecyclePhase.ERROR


class TestLifecycleManager:
    """Test LifecycleManager functionality."""
    
    def test_manager_creation(self):
        """Test creating lifecycle manager."""
        manager = LifecycleManager()
        
        assert manager._update_batch_size == 10
        assert manager._update_delay_ms == 16
        assert manager._performance_enabled is True
    
    def test_component_registration(self, qapp):
        """Test registering component."""
        manager = LifecycleManager()
        widget = ReactiveWidget(component_id="test-123")
        
        manager.register_component(widget)
        
        assert "test-123" in manager._components
        assert manager._component_phases["test-123"] == LifecyclePhase.UNMOUNTED
    
    def test_singleton_manager(self):
        """Test singleton pattern."""
        m1 = get_lifecycle_manager()
        m2 = get_lifecycle_manager()
        assert m1 is m2


class TestDecorators:
    """Test decorator functionality."""
    
    def test_lifecycle_decorator(self):
        """Test lifecycle decorator."""
        @lifecycle("mount")
        def on_mount(self):
            pass
        
        assert on_mount._lifecycle_hook == "on_mount"
    
    def test_computed_decorator(self):
        """Test computed decorator."""
        class Widget(ReactiveWidget):
            @computed("user.first", "user.last")
            def full_name(self, first: str, last: str) -> str:
                return f"{first} {last}"
        
        assert hasattr(Widget.full_name, "_computed_dependencies")
        assert Widget.full_name._computed_dependencies == ["user.first", "user.last"]
    
    def test_memoize_decorator(self):
        """Test memoize decorator."""
        class Widget:
            call_count = 0
            
            @memoize()
            def compute(self, x: int) -> int:
                self.call_count += 1
                return x * 2
        
        w = Widget()
        
        # First call
        assert w.compute(5) == 10
        assert w.call_count == 1
        
        # Cached call
        assert w.compute(5) == 10
        assert w.call_count == 1  # Not incremented


if __name__ == "__main__":
    pytest.main([__file__, "-v"])