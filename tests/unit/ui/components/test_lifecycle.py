"""
Tests for lifecycle management functionality.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QSignalSpy

from torematrix.ui.components.reactive import ReactiveWidget
from torematrix.ui.components.lifecycle import (
    LifecycleManager,
    LifecycleMixin,
    LifecyclePhase,
    LifecycleEvent,
    RenderMetrics,
    get_lifecycle_manager,
    with_lifecycle,
)


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def lifecycle_manager():
    """Create fresh lifecycle manager."""
    return LifecycleManager()


@pytest.fixture
def test_widget(qapp):
    """Create test reactive widget."""
    class TestWidget(ReactiveWidget):
        mount_count = 0
        unmount_count = 0
        update_count = 0
        
        def on_mount(self):
            self.mount_count += 1
        
        def on_unmount(self):
            self.unmount_count += 1
        
        def on_update(self):
            self.update_count += 1
    
    return TestWidget()


class TestLifecyclePhase:
    """Test LifecyclePhase enum."""
    
    def test_phase_values(self):
        """Test lifecycle phase values exist."""
        assert LifecyclePhase.UNMOUNTED
        assert LifecyclePhase.MOUNTING
        assert LifecyclePhase.MOUNTED
        assert LifecyclePhase.UPDATING
        assert LifecyclePhase.UNMOUNTING
        assert LifecyclePhase.ERROR


class TestLifecycleEvent:
    """Test LifecycleEvent dataclass."""
    
    def test_event_creation(self):
        """Test creating lifecycle event."""
        event = LifecycleEvent(
            phase=LifecyclePhase.MOUNTED,
            component_id="test-123",
            component_type="TestWidget"
        )
        
        assert event.phase == LifecyclePhase.MOUNTED
        assert event.component_id == "test-123"
        assert event.component_type == "TestWidget"
        assert isinstance(event.timestamp, float)
        assert event.metadata == {}
    
    def test_event_with_metadata(self):
        """Test event with metadata."""
        event = LifecycleEvent(
            phase=LifecyclePhase.ERROR,
            component_id="test-123",
            component_type="TestWidget",
            metadata={"error": "Test error"}
        )
        
        assert event.metadata == {"error": "Test error"}


class TestRenderMetrics:
    """Test RenderMetrics dataclass."""
    
    def test_metrics_defaults(self):
        """Test metrics default values."""
        metrics = RenderMetrics()
        
        assert metrics.render_count == 0
        assert metrics.total_render_time == 0.0
        assert metrics.last_render_time == 0.0
        assert metrics.average_render_time == 0.0
        assert metrics.slowest_render_time == 0.0
        assert metrics.fastest_render_time == float("inf")


class TestLifecycleManager:
    """Test LifecycleManager class."""
    
    def test_register_component(self, lifecycle_manager, test_widget):
        """Test registering component."""
        lifecycle_manager.register_component(test_widget)
        
        component_id = test_widget.component_id
        assert component_id in lifecycle_manager._components
        assert lifecycle_manager._component_phases[component_id] == LifecyclePhase.UNMOUNTED
        assert component_id in lifecycle_manager._component_metrics
    
    def test_unregister_component(self, lifecycle_manager, test_widget):
        """Test unregistering component."""
        lifecycle_manager.register_component(test_widget)
        component_id = test_widget.component_id
        
        lifecycle_manager.unregister_component(component_id)
        
        assert component_id not in lifecycle_manager._components
        assert component_id not in lifecycle_manager._component_phases
        assert component_id not in lifecycle_manager._component_metrics
    
    def test_mount_component(self, lifecycle_manager, test_widget):
        """Test mounting component."""
        spy = QSignalSpy(lifecycle_manager.lifecycle_event)
        
        lifecycle_manager.mount_component(test_widget)
        
        # Check phase transitions
        assert len(spy) >= 2  # MOUNTING and MOUNTED events
        
        # Check component state
        component_id = test_widget.component_id
        assert lifecycle_manager._component_phases[component_id] == LifecyclePhase.MOUNTED
        assert test_widget.mount_count == 1
    
    def test_mount_already_mounted(self, lifecycle_manager, test_widget):
        """Test mounting already mounted component."""
        lifecycle_manager.mount_component(test_widget)
        initial_mount_count = test_widget.mount_count
        
        # Try to mount again
        lifecycle_manager.mount_component(test_widget)
        
        # Should not mount again
        assert test_widget.mount_count == initial_mount_count
    
    def test_unmount_component(self, lifecycle_manager, test_widget):
        """Test unmounting component."""
        lifecycle_manager.mount_component(test_widget)
        
        spy = QSignalSpy(lifecycle_manager.lifecycle_event)
        lifecycle_manager.unmount_component(test_widget)
        
        # Check phase transitions
        assert len(spy) >= 2  # UNMOUNTING and UNMOUNTED events
        
        # Check component was unregistered
        assert test_widget.component_id not in lifecycle_manager._components
        assert test_widget.unmount_count == 1
    
    def test_unmount_not_mounted(self, lifecycle_manager, test_widget):
        """Test unmounting component that's not mounted."""
        lifecycle_manager.register_component(test_widget)
        
        # Should handle gracefully
        lifecycle_manager.unmount_component(test_widget)
        assert test_widget.unmount_count == 0
    
    def test_schedule_update(self, lifecycle_manager, test_widget, qapp):
        """Test scheduling component update."""
        lifecycle_manager.mount_component(test_widget)
        
        # Schedule update
        lifecycle_manager.schedule_update(test_widget.component_id)
        
        # Wait for update timer
        QTimer.singleShot(30, qapp.quit)
        qapp.exec()
        
        # Check update was processed
        assert test_widget.update_count > 0
    
    def test_schedule_update_not_mounted(self, lifecycle_manager, test_widget):
        """Test scheduling update for unmounted component."""
        lifecycle_manager.register_component(test_widget)
        
        # Should not update
        lifecycle_manager.schedule_update(test_widget.component_id)
        assert test_widget.component_id not in lifecycle_manager._update_queue
    
    def test_force_update(self, lifecycle_manager, test_widget):
        """Test forcing immediate update."""
        lifecycle_manager.mount_component(test_widget)
        
        lifecycle_manager.force_update(test_widget.component_id)
        
        # Should update immediately
        assert test_widget.update_count == 1
    
    def test_global_hooks(self, lifecycle_manager, test_widget):
        """Test global lifecycle hooks."""
        mount_hook_called = []
        unmount_hook_called = []
        
        def on_mount_hook(component):
            mount_hook_called.append(component.component_id)
        
        def on_unmount_hook(component):
            unmount_hook_called.append(component.component_id)
        
        # Add hooks
        lifecycle_manager.add_global_hook(LifecyclePhase.MOUNTED, on_mount_hook)
        lifecycle_manager.add_global_hook(LifecyclePhase.UNMOUNTED, on_unmount_hook)
        
        # Mount and unmount
        lifecycle_manager.mount_component(test_widget)
        lifecycle_manager.unmount_component(test_widget)
        
        # Check hooks were called
        assert test_widget.component_id in mount_hook_called
        assert test_widget.component_id in unmount_hook_called
        
        # Remove hook and verify
        lifecycle_manager.remove_global_hook(LifecyclePhase.MOUNTED, on_mount_hook)
        assert on_mount_hook not in lifecycle_manager._global_hooks[LifecyclePhase.MOUNTED]
    
    def test_error_handling(self, lifecycle_manager):
        """Test error handling during lifecycle."""
        class ErrorWidget(ReactiveWidget):
            def on_mount(self):
                raise ValueError("Mount error")
        
        widget = ErrorWidget()
        spy = QSignalSpy(lifecycle_manager.error_occurred)
        
        # Mount should raise and emit error
        with pytest.raises(ValueError):
            lifecycle_manager.mount_component(widget)
        
        # Check error was emitted
        assert len(spy) == 1
        assert spy[0][0] == widget.component_id
        assert isinstance(spy[0][1], ValueError)
        
        # Check phase is ERROR
        assert lifecycle_manager._component_phases[widget.component_id] == LifecyclePhase.ERROR
    
    def test_error_handler(self, lifecycle_manager):
        """Test custom error handlers."""
        errors_handled = []
        
        def error_handler(component_id, error):
            errors_handled.append((component_id, error))
        
        lifecycle_manager.add_error_handler(error_handler)
        
        class ErrorWidget(ReactiveWidget):
            def on_mount(self):
                raise RuntimeError("Test error")
        
        widget = ErrorWidget()
        
        with pytest.raises(RuntimeError):
            lifecycle_manager.mount_component(widget)
        
        # Check handler was called
        assert len(errors_handled) == 1
        assert errors_handled[0][0] == widget.component_id
        assert isinstance(errors_handled[0][1], RuntimeError)
    
    def test_get_component_phase(self, lifecycle_manager, test_widget):
        """Test getting component phase."""
        lifecycle_manager.register_component(test_widget)
        
        # Initial phase
        phase = lifecycle_manager.get_component_phase(test_widget.component_id)
        assert phase == LifecyclePhase.UNMOUNTED
        
        # After mount
        lifecycle_manager.mount_component(test_widget)
        phase = lifecycle_manager.get_component_phase(test_widget.component_id)
        assert phase == LifecyclePhase.MOUNTED
        
        # Unknown component
        assert lifecycle_manager.get_component_phase("unknown") is None
    
    def test_get_component_metrics(self, lifecycle_manager, test_widget):
        """Test getting component metrics."""
        lifecycle_manager.register_component(test_widget)
        
        metrics = lifecycle_manager.get_component_metrics(test_widget.component_id)
        assert isinstance(metrics, RenderMetrics)
        assert metrics.render_count == 0
        
        # Unknown component
        assert lifecycle_manager.get_component_metrics("unknown") is None
    
    def test_performance_monitoring(self, lifecycle_manager, test_widget):
        """Test performance monitoring."""
        lifecycle_manager.enable_performance_monitoring(True)
        lifecycle_manager.set_slow_render_threshold(10.0)  # 10ms
        
        lifecycle_manager.mount_component(test_widget)
        
        # Force a slow update
        class SlowWidget(ReactiveWidget):
            def on_update(self):
                time.sleep(0.02)  # 20ms
        
        slow_widget = SlowWidget()
        lifecycle_manager.mount_component(slow_widget)
        
        # This should trigger slow render warning
        with patch("torematrix.ui.components.lifecycle.logger") as mock_logger:
            lifecycle_manager.force_update(slow_widget.component_id)
            mock_logger.warning.assert_called()
    
    def test_update_batching(self, lifecycle_manager, qapp):
        """Test update batching."""
        widgets = []
        for i in range(5):
            widget = ReactiveWidget(component_id=f"widget-{i}")
            lifecycle_manager.mount_component(widget)
            widgets.append(widget)
        
        # Schedule multiple updates
        for widget in widgets:
            lifecycle_manager.schedule_update(widget.component_id)
        
        # Check all are queued
        assert len(lifecycle_manager._update_queue) == 5
        
        # Wait for batch processing
        QTimer.singleShot(30, qapp.quit)
        qapp.exec()
        
        # Queue should be processed
        assert len(lifecycle_manager._update_queue) == 0


class TestGlobalLifecycleManager:
    """Test global lifecycle manager singleton."""
    
    def test_get_lifecycle_manager(self):
        """Test getting global lifecycle manager."""
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()
        
        # Should be same instance
        assert manager1 is manager2
        assert isinstance(manager1, LifecycleManager)


class TestWithLifecycleDecorator:
    """Test @with_lifecycle decorator."""
    
    def test_with_lifecycle_decorator(self, qapp):
        """Test class decorator for lifecycle."""
        @with_lifecycle
        class TestWidget(ReactiveWidget):
            pass
        
        widget = TestWidget()
        
        # Should be auto-registered
        manager = get_lifecycle_manager()
        assert widget.component_id in manager._components


class TestLifecycleMixin:
    """Test LifecycleMixin class."""
    
    def test_mixin_with_qwidget(self, qapp):
        """Test mixin with regular QWidget."""
        class MyWidget(LifecycleMixin, QWidget):
            pass
        
        widget = MyWidget()
        
        # Should have component_id
        assert hasattr(widget, "component_id")
        assert widget.component_id
        
        # Should be registered
        manager = get_lifecycle_manager()
        assert widget.component_id in manager._components
    
    def test_mixin_lifecycle_methods(self, qapp):
        """Test mixin lifecycle methods."""
        class MyWidget(LifecycleMixin, QWidget):
            mounted = False
            unmounted = False
            
            def on_mount(self):
                self.mounted = True
            
            def on_unmount(self):
                self.unmounted = True
        
        widget = MyWidget()
        
        # Test mount
        widget.mount()
        assert widget.mounted is True
        
        # Test unmount
        widget.unmount()
        assert widget.unmounted is True
    
    def test_mixin_update_methods(self, qapp):
        """Test mixin update methods."""
        class MyWidget(LifecycleMixin, QWidget):
            update_count = 0
            
            def update(self):
                self.update_count += 1
                super().update()
        
        widget = MyWidget()
        widget.mount()
        
        # Schedule update
        widget.schedule_update()
        
        # Force update
        widget.force_update()
        assert widget.update_count > 0