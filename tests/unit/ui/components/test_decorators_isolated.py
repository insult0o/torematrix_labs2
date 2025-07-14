"""
Isolated tests for reactive component decorators.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
import time
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import only the components we need
from torematrix.ui.components.reactive import ReactiveWidget
from torematrix.ui.components.decorators import (
    PropertyDescriptor,
    reactive_property,
    computed,
    bind_state,
    watch,
    lifecycle,
    throttle,
    debounce,
    memoize,
)


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestPropertyDescriptor:
    """Test PropertyDescriptor functionality."""
    
    def test_descriptor_usage(self, qapp):
        """Test descriptor get/set."""
        class Widget(ReactiveWidget):
            value = PropertyDescriptor("value", default=10)
        
        w = Widget()
        assert w.value == 10
        
        w.value = 20
        assert w.value == 20
    
    def test_descriptor_validation(self, qapp):
        """Test descriptor with validator."""
        class Widget(ReactiveWidget):
            age = PropertyDescriptor(
                "age", 
                default=0,
                validator=lambda x: x >= 0
            )
        
        w = Widget()
        w.age = 25
        assert w.age == 25
        
        with pytest.raises(ValueError):
            w.age = -5
    
    def test_descriptor_transform(self, qapp):
        """Test descriptor with transformer."""
        class Widget(ReactiveWidget):
            name = PropertyDescriptor(
                "name",
                transformer=str.upper
            )
        
        w = Widget()
        w.name = "john"
        assert w.name == "JOHN"


class TestComputedDecorator:
    """Test @computed decorator."""
    
    def test_computed_decorator(self, qapp):
        """Test computed property decorator."""
        class Widget(ReactiveWidget):
            @computed("user.first", "user.last")
            def full_name(self, first: str, last: str) -> str:
                return f"{first} {last}"
        
        # Check metadata
        assert hasattr(Widget.full_name, "_computed_dependencies")
        assert Widget.full_name._computed_dependencies == ["user.first", "user.last"]
        assert Widget.full_name._is_computed


class TestBindStateDecorator:
    """Test @bind_state decorator."""
    
    def test_bind_state_decorator(self, qapp):
        """Test state binding decorator."""
        class Widget(ReactiveWidget):
            @bind_state("app.theme", bidirectional=True)
            def theme(self) -> str:
                return ""
        
        # Check metadata
        assert hasattr(Widget.theme, "_state_binding")
        binding = Widget.theme._state_binding
        assert binding["path"] == "app.theme"
        assert binding["bidirectional"]


class TestWatchDecorator:
    """Test @watch decorator."""
    
    def test_watch_decorator(self, qapp):
        """Test watch decorator."""
        class Widget(ReactiveWidget):
            @watch("user.role", "app.theme")
            def on_change(self, role: str, theme: str) -> None:
                pass
        
        # Check metadata
        assert hasattr(Widget.on_change, "_watch_paths")
        assert Widget.on_change._watch_paths == ["user.role", "app.theme"]
        assert Widget.on_change._watch_immediate


class TestLifecycleDecorator:
    """Test @lifecycle decorator."""
    
    def test_lifecycle_valid(self):
        """Test valid lifecycle hooks."""
        @lifecycle("mount")
        def on_mount(self):
            pass
        
        @lifecycle("unmount")
        def on_unmount(self):
            pass
        
        assert on_mount._lifecycle_hook == "on_mount"
        assert on_unmount._lifecycle_hook == "on_unmount"
    
    def test_lifecycle_invalid(self):
        """Test invalid lifecycle hook."""
        with pytest.raises(ValueError):
            @lifecycle("invalid")
            def bad_hook(self):
                pass


class TestThrottleDecorator:
    """Test @throttle decorator."""
    
    def test_throttle_timing(self, qapp):
        """Test throttle prevents rapid calls."""
        class Widget(ReactiveWidget):
            call_count = 0
            
            @throttle(50)  # 50ms
            def method(self):
                self.call_count += 1
                return self.call_count
        
        w = Widget()
        
        # First call works
        assert w.method() == 1
        
        # Immediate second call is blocked
        assert w.method() is None
        
        # Wait and try again
        time.sleep(0.06)
        assert w.method() == 2


class TestDebounceDecorator:
    """Test @debounce decorator."""
    
    def test_debounce_delays_execution(self, qapp):
        """Test debounce delays execution."""
        class Widget(ReactiveWidget):
            call_count = 0
            
            @debounce(50)  # 50ms
            def method(self):
                self.call_count += 1
        
        w = Widget()
        
        # Multiple rapid calls
        w.method()
        w.method()
        w.method()
        
        # Should not have executed yet
        assert w.call_count == 0
        
        # Wait for debounce
        QTimer.singleShot(60, qapp.quit)
        qapp.exec()
        
        # Should have executed once
        assert w.call_count == 1


class TestMemoizeDecorator:
    """Test @memoize decorator."""
    
    def test_memoize_caches_results(self, qapp):
        """Test memoize caches results."""
        class Widget(ReactiveWidget):
            compute_count = 0
            
            @memoize()
            def compute(self, x: int, y: int) -> int:
                self.compute_count += 1
                return x + y
        
        w = Widget()
        
        # First call
        assert w.compute(2, 3) == 5
        assert w.compute_count == 1
        
        # Same args - cached
        assert w.compute(2, 3) == 5
        assert w.compute_count == 1
        
        # Different args
        assert w.compute(4, 5) == 9
        assert w.compute_count == 2
    
    def test_memoize_with_limit(self, qapp):
        """Test memoize with cache limit."""
        class Widget(ReactiveWidget):
            @memoize(max_size=2)
            def compute(self, x: int) -> int:
                return x * 2
        
        w = Widget()
        
        # Fill cache
        assert w.compute(1) == 2
        assert w.compute(2) == 4
        assert w.compute(3) == 6  # This evicts oldest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])