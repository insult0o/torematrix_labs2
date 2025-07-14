"""
Tests for Cleanup Strategies.
"""

import pytest
import gc
import time
import threading
import asyncio
from unittest.mock import Mock, patch, MagicMock, call
from contextlib import contextmanager

from src.torematrix.ui.components.cleanup import (
    CleanupPhase,
    CleanupTask,
    CleanupRegistry,
    get_cleanup_registry,
    CleanupManager,
    with_cleanup,
    CleanupMixin,
    ResourceGuard,
    cleanup_on_error
)


class TestCleanupPhase:
    """Test the CleanupPhase enum."""
    
    def test_cleanup_phase_order(self):
        """Test that cleanup phases have correct order."""
        phases = list(CleanupPhase)
        
        # Verify order
        assert phases[0] == CleanupPhase.SUBSCRIPTIONS
        assert phases[1] == CleanupPhase.EVENTS
        assert phases[2] == CleanupPhase.TIMERS
        assert phases[3] == CleanupPhase.ASYNC_TASKS
        assert phases[4] == CleanupPhase.RESOURCES
        assert phases[5] == CleanupPhase.MEMORY
        
        # Verify values increase
        for i in range(1, len(phases)):
            assert phases[i].value > phases[i-1].value


class TestCleanupTask:
    """Test the CleanupTask dataclass."""
    
    def test_cleanup_task_creation(self):
        """Test creating a cleanup task."""
        callback = Mock()
        
        task = CleanupTask(
            phase=CleanupPhase.RESOURCES,
            callback=callback,
            name="test_cleanup",
            priority=10
        )
        
        assert task.phase == CleanupPhase.RESOURCES
        assert task.callback == callback
        assert task.name == "test_cleanup"
        assert task.priority == 10
    
    def test_cleanup_task_comparison(self):
        """Test cleanup task sorting."""
        task1 = CleanupTask(
            phase=CleanupPhase.SUBSCRIPTIONS,
            callback=Mock(),
            name="task1",
            priority=5
        )
        
        task2 = CleanupTask(
            phase=CleanupPhase.SUBSCRIPTIONS,
            callback=Mock(),
            name="task2",
            priority=10
        )
        
        task3 = CleanupTask(
            phase=CleanupPhase.EVENTS,
            callback=Mock(),
            name="task3",
            priority=20
        )
        
        # Same phase: higher priority comes first
        assert task2 < task1
        
        # Different phase: earlier phase comes first
        assert task1 < task3
        assert task2 < task3


class TestCleanupRegistry:
    """Test the CleanupRegistry class."""
    
    def test_register_cleanup(self):
        """Test registering a cleanup task."""
        registry = CleanupRegistry()
        obj = Mock()
        callback = Mock()
        callback.__name__ = 'test_callback'
        
        registry.register(
            obj=obj,
            callback=callback,
            phase=CleanupPhase.RESOURCES,
            name="test_cleanup"
        )
        
        assert id(obj) in registry._tasks
        assert len(registry._tasks[id(obj)]) == 1
    
    def test_cleanup_object(self):
        """Test cleaning up an object."""
        registry = CleanupRegistry()
        obj = Mock()
        callback1 = Mock()
        callback1.__name__ = 'callback1'
        callback2 = Mock()
        callback2.__name__ = 'callback2'
        
        # Register multiple cleanups
        registry.register(obj, callback1, CleanupPhase.SUBSCRIPTIONS, "cleanup1")
        registry.register(obj, callback2, CleanupPhase.RESOURCES, "cleanup2")
        
        # Cleanup object
        registry.cleanup_object(obj)
        
        # Verify callbacks called in correct order
        callback1.assert_called_once()
        callback2.assert_called_once()
        
        # Verify object marked as cleaned up
        assert id(obj) in registry._cleaned_up
        assert id(obj) not in registry._tasks
    
    def test_cleanup_object_idempotent(self):
        """Test that cleanup is idempotent."""
        registry = CleanupRegistry()
        obj = Mock()
        callback = Mock()
        callback.__name__ = 'callback'
        
        registry.register(obj, callback, CleanupPhase.RESOURCES)
        
        # Cleanup multiple times
        registry.cleanup_object(obj)
        registry.cleanup_object(obj)
        
        # Callback should only be called once
        callback.assert_called_once()
    
    def test_cleanup_with_error_handler(self):
        """Test cleanup with error handler."""
        registry = CleanupRegistry()
        obj = Mock()
        
        # Callback that raises error
        def failing_callback():
            raise RuntimeError("Cleanup failed")
        
        error_handler = Mock()
        
        registry.register(
            obj=obj,
            callback=failing_callback,
            phase=CleanupPhase.RESOURCES,
            error_handler=error_handler
        )
        
        # Cleanup should not raise
        registry.cleanup_object(obj)
        
        # Error handler should be called
        error_handler.assert_called_once()
        assert isinstance(error_handler.call_args[0][0], RuntimeError)
    
    def test_cleanup_all(self):
        """Test cleaning up all objects."""
        registry = CleanupRegistry()
        
        obj1 = Mock()
        obj2 = Mock()
        callback1 = Mock()
        callback1.__name__ = 'callback1'
        callback2 = Mock()
        callback2.__name__ = 'callback2'
        
        registry.register(obj1, callback1, CleanupPhase.RESOURCES)
        registry.register(obj2, callback2, CleanupPhase.RESOURCES)
        
        registry.cleanup_all()
        
        # Both callbacks should be called
        callback1.assert_called_once()
        callback2.assert_called_once()
        
        # Registry should be empty
        assert len(registry._tasks) == 0
    
    def test_automatic_cleanup_on_gc(self):
        """Test automatic cleanup when object is garbage collected."""
        registry = CleanupRegistry()
        callback = Mock()
        callback.__name__ = 'callback'
        
        # Create object in scope
        def create_and_register():
            obj = Mock()
            registry.register(obj, callback, CleanupPhase.RESOURCES)
            return weakref.ref(obj)
        
        import weakref
        obj_ref = create_and_register()
        
        # Force garbage collection
        gc.collect()
        time.sleep(0.1)
        
        # Verify cleanup was called
        callback.assert_called_once()


class TestCleanupManager:
    """Test the CleanupManager class."""
    
    def test_cleanup_manager_initialization(self):
        """Test initializing cleanup manager."""
        component = Mock()
        manager = CleanupManager(component)
        
        assert manager.component == component
        assert manager.component_id == id(component)
        assert not manager._is_cleaned_up
    
    def test_register_cleanup(self):
        """Test registering cleanup through manager."""
        component = Mock()
        manager = CleanupManager(component)
        callback = Mock()
        callback.__name__ = 'callback'
        
        manager.register_cleanup(
            callback=callback,
            phase=CleanupPhase.RESOURCES,
            name="test_cleanup"
        )
        
        # Verify registered with global registry
        registry = get_cleanup_registry()
        assert id(component) in registry._tasks
    
    def test_add_subscription_cleanup(self):
        """Test adding subscription cleanup."""
        manager = CleanupManager(Mock())
        callback = Mock()
        
        manager.add_subscription_cleanup(callback)
        
        # Should be registered with SUBSCRIPTIONS phase
        registry = get_cleanup_registry()
        tasks = registry._tasks[manager.component_id]
        assert any(
            task.phase == CleanupPhase.SUBSCRIPTIONS
            for task in tasks
        )
    
    def test_add_timer(self):
        """Test adding a timer."""
        manager = CleanupManager(Mock())
        
        timer = threading.Timer(10.0, lambda: None)
        result = manager.add_timer(timer)
        
        assert result is timer
        assert timer in manager._timers
    
    def test_add_async_task(self):
        """Test adding an async task."""
        async def async_function():
            await asyncio.sleep(1)
        
        manager = CleanupManager(Mock())
        
        # Create event loop for testing
        loop = asyncio.new_event_loop()
        task = loop.create_task(async_function())
        
        result = manager.add_async_task(task)
        
        assert result is task
        assert task in manager._async_tasks
        
        # Clean up
        task.cancel()
        loop.close()
    
    def test_add_resource(self):
        """Test adding a resource."""
        manager = CleanupManager(Mock())
        resource = Mock()
        
        result = manager.add_resource(resource)
        
        assert result is resource
        assert resource in manager._resources
    
    def test_cleanup_cancels_timers(self):
        """Test that cleanup cancels timers."""
        manager = CleanupManager(Mock())
        
        timer1 = Mock(spec=threading.Timer)
        timer2 = Mock(spec=threading.Timer)
        
        manager.add_timer(timer1)
        manager.add_timer(timer2)
        
        manager.cleanup()
        
        timer1.cancel.assert_called_once()
        timer2.cancel.assert_called_once()
        assert len(manager._timers) == 0
    
    def test_cleanup_cancels_async_tasks(self):
        """Test that cleanup cancels async tasks."""
        manager = CleanupManager(Mock())
        
        task1 = Mock()
        task1.done.return_value = False
        task2 = Mock()
        task2.done.return_value = True  # Already done
        
        manager._async_tasks.add(task1)
        manager._async_tasks.add(task2)
        
        manager.cleanup()
        
        task1.cancel.assert_called_once()
        task2.cancel.assert_not_called()
        assert len(manager._async_tasks) == 0
    
    def test_cleanup_closes_resources(self):
        """Test that cleanup closes resources."""
        manager = CleanupManager(Mock())
        
        # Resource with close method
        resource1 = Mock()
        resource1.close = Mock()
        
        # Resource with cleanup method
        resource2 = Mock()
        resource2.cleanup = Mock()
        del resource2.close  # Ensure no close method
        
        manager.add_resource(resource1)
        manager.add_resource(resource2)
        
        manager.cleanup()
        
        resource1.close.assert_called_once()
        resource2.cleanup.assert_called_once()
        assert len(manager._resources) == 0
    
    def test_cleanup_idempotent(self):
        """Test that cleanup is idempotent."""
        manager = CleanupManager(Mock())
        timer = Mock(spec=threading.Timer)
        
        manager.add_timer(timer)
        
        # Cleanup multiple times
        manager.cleanup()
        manager.cleanup()
        
        # Timer should only be cancelled once
        timer.cancel.assert_called_once()
    
    def test_context_manager(self):
        """Test using cleanup manager as context manager."""
        component = Mock()
        timer = Mock(spec=threading.Timer)
        
        with CleanupManager(component) as manager:
            manager.add_timer(timer)
        
        # Timer should be cancelled on exit
        timer.cancel.assert_called_once()


class TestWithCleanupDecorator:
    """Test the with_cleanup decorator."""
    
    def test_with_cleanup_function(self):
        """Test with_cleanup on a function."""
        @with_cleanup
        def test_function(cleanup_manager, value):
            assert isinstance(cleanup_manager, CleanupManager)
            return value * 2
        
        result = test_function(5)
        assert result == 10
    
    def test_with_cleanup_method(self):
        """Test with_cleanup on a method."""
        class TestClass:
            @with_cleanup
            def test_method(self, cleanup_manager, value):
                assert isinstance(cleanup_manager, CleanupManager)
                assert cleanup_manager.component is self
                return value * 3
        
        obj = TestClass()
        result = obj.test_method(4)
        assert result == 12
    
    def test_with_cleanup_ensures_cleanup(self):
        """Test that with_cleanup ensures cleanup on exception."""
        timer = Mock(spec=threading.Timer)
        
        @with_cleanup
        def failing_function(cleanup_manager):
            cleanup_manager.add_timer(timer)
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            failing_function()
        
        # Timer should still be cancelled
        timer.cancel.assert_called_once()


class TestCleanupMixin:
    """Test the CleanupMixin class."""
    
    def test_mixin_initialization(self):
        """Test that mixin initializes properly."""
        class TestComponent(CleanupMixin):
            pass
        
        component = TestComponent()
        
        assert hasattr(component, '_cleanup_manager')
        assert isinstance(component.cleanup_manager, CleanupManager)
    
    def test_register_cleanup(self):
        """Test registering cleanup through mixin."""
        class TestComponent(CleanupMixin):
            pass
        
        component = TestComponent()
        callback = Mock()
        callback.__name__ = 'callback'
        
        component.register_cleanup(
            callback=callback,
            phase=CleanupPhase.RESOURCES
        )
        
        component.cleanup()
        callback.assert_called_once()
    
    def test_cleanup_in_del(self):
        """Test that cleanup is called in __del__."""
        cleanup_called = []
        
        class TestComponent(CleanupMixin):
            def cleanup(self):
                cleanup_called.append(True)
                super().cleanup()
        
        # Create and delete component
        component = TestComponent()
        del component
        gc.collect()
        
        # Verify cleanup was called
        assert len(cleanup_called) > 0


class TestResourceGuard:
    """Test the ResourceGuard class."""
    
    def test_add_resource_with_close(self):
        """Test adding a resource with close method."""
        guard = ResourceGuard()
        
        resource = Mock()
        resource.close = Mock()
        
        result = guard.add(resource)
        
        assert result is resource
        guard.cleanup()
        resource.close.assert_called_once()
    
    def test_add_resource_with_custom_cleanup(self):
        """Test adding a resource with custom cleanup."""
        guard = ResourceGuard()
        
        resource = Mock()
        cleanup = Mock()
        
        guard.add(resource, cleanup)
        guard.cleanup()
        
        cleanup.assert_called_once()
    
    def test_cleanup_order(self):
        """Test that resources are cleaned up in reverse order."""
        guard = ResourceGuard()
        
        cleanups = []
        
        def make_cleanup(n):
            def cleanup():
                cleanups.append(n)
            return cleanup
        
        # Add resources
        for i in range(3):
            guard.add(Mock(), make_cleanup(i))
        
        guard.cleanup()
        
        # Should be cleaned up in reverse order
        assert cleanups == [2, 1, 0]
    
    def test_context_manager(self):
        """Test using ResourceGuard as context manager."""
        resource = Mock()
        resource.close = Mock()
        
        with ResourceGuard() as guard:
            guard.add(resource)
        
        resource.close.assert_called_once()
    
    def test_cleanup_errors_handled(self):
        """Test that cleanup errors are handled."""
        guard = ResourceGuard()
        
        # Resource that fails to close
        bad_resource = Mock()
        bad_resource.close = Mock(side_effect=RuntimeError("Close failed"))
        
        # Good resource
        good_resource = Mock()
        good_resource.close = Mock()
        
        guard.add(bad_resource)
        guard.add(good_resource)
        
        # Should not raise
        guard.cleanup()
        
        # Both should be attempted
        bad_resource.close.assert_called_once()
        good_resource.close.assert_called_once()


class TestCleanupOnError:
    """Test the cleanup_on_error context manager."""
    
    def test_no_cleanup_on_success(self):
        """Test that cleanup is not called on success."""
        cleanup = Mock()
        
        with cleanup_on_error(cleanup):
            pass  # Success
        
        cleanup.assert_not_called()
    
    def test_cleanup_on_error(self):
        """Test that cleanup is called on error."""
        cleanup = Mock()
        
        with pytest.raises(RuntimeError):
            with cleanup_on_error(cleanup):
                raise RuntimeError("Test error")
        
        cleanup.assert_called_once()
    
    def test_cleanup_error_suppressed(self):
        """Test that cleanup errors don't mask original error."""
        def failing_cleanup():
            raise ValueError("Cleanup error")
        
        with pytest.raises(RuntimeError) as exc_info:
            with cleanup_on_error(failing_cleanup):
                raise RuntimeError("Original error")
        
        # Original error should be raised
        assert str(exc_info.value) == "Original error"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])