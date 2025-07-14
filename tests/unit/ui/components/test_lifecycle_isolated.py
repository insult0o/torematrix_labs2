"""
Isolated tests for lifecycle management.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
import time
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QSignalSpy

# Import only what we need
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
def manager():
    """Create fresh lifecycle manager."""
    return LifecycleManager()


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


class TestRenderMetrics:
    """Test RenderMetrics dataclass."""
    
    def test_metrics_defaults(self):
        """Test default metric values."""
        metrics = RenderMetrics()
        
        assert metrics.render_count == 0
        assert metrics.total_render_time == 0.0
        assert metrics.average_render_time == 0.0
        assert metrics.fastest_render_time == float("inf")


class TestLifecycleManager:
    """Test LifecycleManager functionality."""
    
    def test_register_component(self, manager, qapp):
        """Test registering a component."""
        widget = ReactiveWidget(component_id="test-123")
        manager.register_component(widget)
        
        assert "test-123" in manager._components
        assert manager._component_phases["test-123"] == LifecyclePhase.UNMOUNTED
    
    def test_unregister_component(self, manager, qapp):
        """Test unregistering a component."""
        widget = ReactiveWidget(component_id="test-123")
        manager.register_component(widget)
        manager.unregister_component("test-123")
        
        assert "test-123" not in manager._components
        assert "test-123" not in manager._component_phases
    
    def test_mount_unmount_cycle(self, manager, qapp):
        """Test mount/unmount cycle."""
        class TestWidget(ReactiveWidget):
            mount_called = False
            unmount_called = False
            
            def on_mount(self):
                self.mount_called = True
            
            def on_unmount(self):
                self.unmount_called = True
        
        widget = TestWidget()
        
        # Mount
        manager.mount_component(widget)
        assert widget.mount_called
        assert manager._component_phases[widget.component_id] == LifecyclePhase.MOUNTED
        
        # Unmount
        manager.unmount_component(widget)
        assert widget.unmount_called
        assert widget.component_id not in manager._components
    
    def test_schedule_update(self, manager, qapp):
        """Test scheduling updates."""
        widget = ReactiveWidget()
        manager.mount_component(widget)
        
        # Schedule update
        manager.schedule_update(widget.component_id)
        assert widget.component_id in manager._update_queue
        
        # Wait for processing
        QTimer.singleShot(30, qapp.quit)
        qapp.exec()
        
        # Queue should be processed
        assert widget.component_id not in manager._update_queue
    
    def test_force_update(self, manager, qapp):
        """Test forcing immediate update."""
        class TestWidget(ReactiveWidget):
            update_count = 0
            
            def force_update(self):
                self.update_count += 1
                super().force_update()
        
        widget = TestWidget()
        manager.mount_component(widget)
        
        manager.force_update(widget.component_id)
        assert widget.update_count == 1
    
    def test_global_hooks(self, manager, qapp):
        """Test global lifecycle hooks."""
        hook_calls = []
        
        def mount_hook(component):
            hook_calls.append(("mount", component.component_id))
        
        manager.add_global_hook(LifecyclePhase.MOUNTED, mount_hook)
        
        widget = ReactiveWidget()
        manager.mount_component(widget)
        
        assert ("mount", widget.component_id) in hook_calls
        
        # Remove hook
        manager.remove_global_hook(LifecyclePhase.MOUNTED, mount_hook)
        assert mount_hook not in manager._global_hooks[LifecyclePhase.MOUNTED]
    
    def test_error_handling(self, manager, qapp):
        """Test error handling during lifecycle."""
        class ErrorWidget(ReactiveWidget):
            def on_mount(self):
                raise ValueError("Test error")
        
        widget = ErrorWidget()
        spy = QSignalSpy(manager.error_occurred)
        
        with pytest.raises(ValueError):
            manager.mount_component(widget)
        
        assert len(spy) == 1
        assert spy[0][0] == widget.component_id
        assert isinstance(spy[0][1], ValueError)
        assert manager._component_phases[widget.component_id] == LifecyclePhase.ERROR
    
    def test_get_component_info(self, manager, qapp):
        """Test getting component information."""
        widget = ReactiveWidget(component_id="test-123")
        manager.register_component(widget)
        
        # Get phase
        phase = manager.get_component_phase("test-123")
        assert phase == LifecyclePhase.UNMOUNTED
        
        # Get metrics
        metrics = manager.get_component_metrics("test-123")
        assert isinstance(metrics, RenderMetrics)
        
        # Unknown component
        assert manager.get_component_phase("unknown") is None
        assert manager.get_component_metrics("unknown") is None


class TestGlobalManager:
    """Test global lifecycle manager."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        m1 = get_lifecycle_manager()
        m2 = get_lifecycle_manager()
        assert m1 is m2


class TestWithLifecycleDecorator:
    """Test @with_lifecycle decorator."""
    
    def test_auto_registration(self, qapp):
        """Test automatic registration."""
        @with_lifecycle
        class TestWidget(ReactiveWidget):
            pass
        
        widget = TestWidget()
        
        # Should be registered
        manager = get_lifecycle_manager()
        assert widget.component_id in manager._components


class TestLifecycleMixin:
    """Test LifecycleMixin functionality."""
    
    def test_mixin_basic(self, qapp):
        """Test basic mixin usage."""
        class MyWidget(LifecycleMixin, QWidget):
            pass
        
        widget = MyWidget()
        
        # Should have component_id
        assert hasattr(widget, "component_id")
        assert widget.component_id
        
        # Should be registered
        manager = get_lifecycle_manager()
        assert widget.component_id in manager._components
    
    def test_mixin_lifecycle(self, qapp):
        """Test mixin lifecycle methods."""
        class MyWidget(LifecycleMixin, QWidget):
            mounted = False
            
            def on_mount(self):
                self.mounted = True
        
        widget = MyWidget()
        widget.mount()
        
        # Mount should work
        assert widget.mounted
        
        # Can schedule updates
        widget.schedule_update()
        widget.force_update()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])