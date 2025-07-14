"""
Tests for reactive component decorators.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QSignalSpy

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
from torematrix.core.state import Store


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_store():
    """Create mock store with test state."""
    store = MagicMock(spec=Store)
    store.get_state.return_value = {
        "user": {
            "firstName": "John",
            "lastName": "Doe",
            "role": "admin"
        },
        "app": {
            "theme": "dark",
            "language": "en"
        },
        "document": {
            "title": "Test Doc",
            "content": "Test content"
        }
    }
    return store


class TestPropertyDescriptor:
    """Test PropertyDescriptor class."""
    
    def test_descriptor_basic(self, qapp):
        """Test basic descriptor functionality."""
        class TestWidget(ReactiveWidget):
            prop = PropertyDescriptor("prop", default="default")
        
        widget = TestWidget()
        
        # Test default value
        assert widget.prop == "default"
        
        # Test setting value
        widget.prop = "new value"
        assert widget.prop == "new value"
    
    def test_descriptor_validation(self, qapp):
        """Test descriptor validation."""
        def is_positive(x):
            return x > 0
        
        class TestWidget(ReactiveWidget):
            count = PropertyDescriptor("count", default=1, validator=is_positive)
        
        widget = TestWidget()
        
        # Valid value
        widget.count = 10
        assert widget.count == 10
        
        # Invalid value
        with pytest.raises(ValueError):
            widget.count = -5
    
    def test_descriptor_transformation(self, qapp):
        """Test descriptor transformation."""
        class TestWidget(ReactiveWidget):
            text = PropertyDescriptor("text", transformer=str.upper)
        
        widget = TestWidget()
        
        widget.text = "hello"
        assert widget.text == "HELLO"
        
        widget.text = "world"
        assert widget.text == "WORLD"
    
    def test_descriptor_change_notification(self, qapp):
        """Test descriptor triggers property change."""
        class TestWidget(ReactiveWidget):
            value = PropertyDescriptor("value", default=0)
        
        widget = TestWidget()
        spy = QSignalSpy(widget.property_changed)
        
        widget.value = 42
        
        # Check signal was emitted
        assert len(spy) == 1
        assert spy[0][0] == "value"  # property name
        assert spy[0][1] == 0        # old value
        assert spy[0][2] == 42       # new value


class TestReactivePropertyDecorator:
    """Test @reactive_property decorator."""
    
    def test_reactive_property_decorator(self, qapp):
        """Test reactive property decorator."""
        class TestWidget(ReactiveWidget):
            @reactive_property(default="", validator=lambda x: isinstance(x, str))
            def title(self):
                pass
        
        widget = TestWidget()
        
        # Check property works
        assert isinstance(widget.title, PropertyDescriptor)


class TestComputedDecorator:
    """Test @computed decorator."""
    
    def test_computed_basic(self, qapp, mock_store):
        """Test basic computed property."""
        class TestWidget(ReactiveWidget):
            @computed("user.firstName", "user.lastName")
            def full_name(self, first: str, last: str) -> str:
                return f"{first} {last}"
        
        widget = TestWidget()
        widget._store = mock_store
        
        # Access computed property
        assert widget.full_name() == "John Doe"
    
    def test_computed_dependencies(self, qapp):
        """Test computed property dependencies are stored."""
        class TestWidget(ReactiveWidget):
            @computed("app.theme", "app.language")
            def app_info(self, theme: str, lang: str) -> str:
                return f"{theme}-{lang}"
        
        # Check dependencies stored on function
        assert hasattr(TestWidget.app_info, "_computed_dependencies")
        assert TestWidget.app_info._computed_dependencies == ["app.theme", "app.language"]
        assert TestWidget.app_info._is_computed is True


class TestBindStateDecorator:
    """Test @bind_state decorator."""
    
    def test_bind_state_basic(self, qapp, mock_store):
        """Test basic state binding."""
        class TestWidget(ReactiveWidget):
            @bind_state("document.title")
            def title(self) -> str:
                return self._property_values.get("title", "")
        
        widget = TestWidget()
        widget._store = mock_store
        widget.mount()
        
        # Access property to trigger binding
        _ = widget.title()
        
        # Check binding was created
        assert hasattr(widget, "_bound_title")
    
    def test_bind_state_with_options(self, qapp):
        """Test state binding with options."""
        class TestWidget(ReactiveWidget):
            @bind_state(
                "user.role",
                transform=str.upper,
                bidirectional=True,
                debounce=100
            )
            def role(self) -> str:
                return ""
        
        # Check binding info stored on function
        assert hasattr(TestWidget.role, "_state_binding")
        binding = TestWidget.role._state_binding
        assert binding["path"] == "user.role"
        assert binding["transform"] is str.upper
        assert binding["bidirectional"] is True
        assert binding["debounce"] == 100


class TestWatchDecorator:
    """Test @watch decorator."""
    
    def test_watch_single_path(self, qapp, mock_store):
        """Test watching single state path."""
        class TestWidget(ReactiveWidget):
            theme_changes = []
            
            @watch("app.theme")
            def on_theme_change(self, theme: str) -> None:
                self.theme_changes.append(theme)
        
        widget = TestWidget()
        widget._store = mock_store
        widget._is_mounted = True
        
        # Trigger watch registration
        widget.on_theme_change()
        
        # Check watcher was registered
        assert hasattr(widget, "_watching_on_theme_change")
    
    def test_watch_multiple_paths(self, qapp):
        """Test watching multiple state paths."""
        class TestWidget(ReactiveWidget):
            @watch("user.role", "app.theme", immediate=False)
            def on_user_or_theme_change(self, role: str, theme: str) -> None:
                pass
        
        # Check watch info stored on function
        assert hasattr(TestWidget.on_user_or_theme_change, "_watch_paths")
        assert TestWidget.on_user_or_theme_change._watch_paths == ["user.role", "app.theme"]
        assert TestWidget.on_user_or_theme_change._watch_immediate is False


class TestLifecycleDecorator:
    """Test @lifecycle decorator."""
    
    def test_lifecycle_valid_hooks(self, qapp):
        """Test lifecycle decorator with valid hooks."""
        class TestWidget(ReactiveWidget):
            @lifecycle("mount")
            def setup(self) -> None:
                pass
            
            @lifecycle("unmount")
            def cleanup(self) -> None:
                pass
            
            @lifecycle("update")
            def refresh(self) -> None:
                pass
        
        # Check lifecycle info stored
        assert TestWidget.setup._lifecycle_hook == "on_mount"
        assert TestWidget.cleanup._lifecycle_hook == "on_unmount"
        assert TestWidget.refresh._lifecycle_hook == "on_update"
    
    def test_lifecycle_invalid_hook(self):
        """Test lifecycle decorator with invalid hook."""
        with pytest.raises(ValueError, match="Invalid lifecycle hook"):
            @lifecycle("invalid")
            def bad_hook(self):
                pass


class TestThrottleDecorator:
    """Test @throttle decorator."""
    
    def test_throttle_basic(self, qapp):
        """Test basic throttling."""
        class TestWidget(ReactiveWidget):
            call_count = 0
            
            @throttle(delay_ms=50)
            def throttled_method(self):
                self.call_count += 1
                return self.call_count
        
        widget = TestWidget()
        
        # First call should work
        assert widget.throttled_method() == 1
        
        # Immediate second call should be throttled
        assert widget.throttled_method() is None
        
        # Wait for throttle period
        time.sleep(0.06)  # 60ms > 50ms
        
        # Should work again
        assert widget.throttled_method() == 2


class TestDebounceDecorator:
    """Test @debounce decorator."""
    
    def test_debounce_basic(self, qapp):
        """Test basic debouncing."""
        class TestWidget(ReactiveWidget):
            call_count = 0
            
            @debounce(delay_ms=50)
            def debounced_method(self):
                self.call_count += 1
        
        widget = TestWidget()
        
        # Multiple rapid calls
        for _ in range(5):
            widget.debounced_method()
        
        # Should not have been called yet
        assert widget.call_count == 0
        
        # Wait for debounce period
        QTimer.singleShot(60, qapp.quit)
        qapp.exec()
        
        # Should have been called once
        assert widget.call_count == 1


class TestMemoizeDecorator:
    """Test @memoize decorator."""
    
    def test_memoize_basic(self, qapp):
        """Test basic memoization."""
        class TestWidget(ReactiveWidget):
            compute_count = 0
            
            @memoize()
            def expensive_compute(self, x: int, y: int) -> int:
                self.compute_count += 1
                return x + y
        
        widget = TestWidget()
        
        # First call
        result1 = widget.expensive_compute(2, 3)
        assert result1 == 5
        assert widget.compute_count == 1
        
        # Same args - should use cache
        result2 = widget.expensive_compute(2, 3)
        assert result2 == 5
        assert widget.compute_count == 1  # Not incremented
        
        # Different args - should compute
        result3 = widget.expensive_compute(4, 5)
        assert result3 == 9
        assert widget.compute_count == 2
    
    def test_memoize_with_max_size(self, qapp):
        """Test memoization with max cache size."""
        class TestWidget(ReactiveWidget):
            @memoize(max_size=2)
            def compute(self, x: int) -> int:
                return x * 2
        
        widget = TestWidget()
        
        # Fill cache
        assert widget.compute(1) == 2
        assert widget.compute(2) == 4
        
        # This should evict oldest (x=1)
        assert widget.compute(3) == 6
        
        # x=1 should be recomputed (not cached)
        # This is hard to test without tracking calls
        assert widget.compute(1) == 2
    
    def test_memoize_per_instance(self, qapp):
        """Test memoization is per-instance."""
        class TestWidget(ReactiveWidget):
            @memoize()
            def compute(self, x: int) -> int:
                return x * 2
        
        widget1 = TestWidget()
        widget2 = TestWidget()
        
        # Cache in widget1
        assert widget1.compute(5) == 10
        
        # widget2 should have its own cache
        # (Can't directly test this without call tracking)
        assert widget2.compute(5) == 10