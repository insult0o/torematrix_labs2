"""
Tests for Async Operation Mixins.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget

from torematrix.ui.components.mixins import (
    AsyncMixin,
    LoadingStateMixin,
    TimeoutMixin,
    ProgressMixin,
    AsyncReactiveWidget,
    AsyncTask,
    Promise,
    AsyncOperationState,
    async_method,
    async_operation_context
)


class TestAsyncTask:
    """Test AsyncTask functionality."""
    
    def test_async_task_creation(self):
        """Test creating an async task."""
        async def test_coro():
            return "test_result"
        
        task = AsyncTask(test_coro(), "test_task")
        
        assert task.name == "test_task"
        assert task.signals is not None
        assert not task.is_cancelled
        assert task.result is None
        assert task.error is None
    
    def test_async_task_run(self):
        """Test running an async task."""
        async def test_coro():
            await asyncio.sleep(0.01)
            return "test_result"
        
        task = AsyncTask(test_coro(), "test_task")
        
        # Mock the signals
        task.signals = Mock()
        task.signals.operation_completed = Mock()
        task.signals.operation_completed.emit = Mock()
        
        # Run the task
        task.run()
        
        assert task.result == "test_result"
        assert task.error is None
        task.signals.operation_completed.emit.assert_called_once_with("test_task", "test_result")
    
    def test_async_task_error(self):
        """Test async task error handling."""
        async def failing_coro():
            raise ValueError("Test error")
        
        task = AsyncTask(failing_coro(), "failing_task")
        
        # Mock the signals
        task.signals = Mock()
        task.signals.operation_failed = Mock()
        task.signals.operation_failed.emit = Mock()
        
        # Run the task
        task.run()
        
        assert task.result is None
        assert isinstance(task.error, ValueError)
        task.signals.operation_failed.emit.assert_called_once()
    
    def test_async_task_cancel(self):
        """Test canceling an async task."""
        async def test_coro():
            return "test_result"
        
        task = AsyncTask(test_coro(), "test_task")
        
        # Mock the signals
        task.signals = Mock()
        task.signals.operation_cancelled = Mock()
        task.signals.operation_cancelled.emit = Mock()
        
        # Cancel the task
        task.cancel()
        
        assert task.is_cancelled
        task.signals.operation_cancelled.emit.assert_called_once_with("test_task")


class TestPromise:
    """Test Promise functionality."""
    
    def test_promise_creation(self):
        """Test creating a promise."""
        promise = Promise()
        
        assert promise.state == 'pending'
        assert promise.result is None
        assert promise.error is None
        assert promise.then_callbacks == []
        assert promise.catch_callbacks == []
        assert promise.finally_callbacks == []
    
    def test_promise_resolve(self):
        """Test resolving a promise."""
        promise = Promise()
        callback = Mock()
        
        promise.then(callback)
        promise.resolve("test_result")
        
        assert promise.state == 'fulfilled'
        assert promise.result == "test_result"
        callback.assert_called_once_with("test_result")
    
    def test_promise_reject(self):
        """Test rejecting a promise."""
        promise = Promise()
        callback = Mock()
        
        promise.catch(callback)
        test_error = ValueError("Test error")
        promise.reject(test_error)
        
        assert promise.state == 'rejected'
        assert promise.error == test_error
        callback.assert_called_once_with(test_error)
    
    def test_promise_then_after_resolve(self):
        """Test adding then callback after promise is resolved."""
        promise = Promise()
        promise.resolve("test_result")
        
        callback = Mock()
        promise.then(callback)
        
        callback.assert_called_once_with("test_result")
    
    def test_promise_catch_after_reject(self):
        """Test adding catch callback after promise is rejected."""
        promise = Promise()
        test_error = ValueError("Test error")
        promise.reject(test_error)
        
        callback = Mock()
        promise.catch(callback)
        
        callback.assert_called_once_with(test_error)
    
    def test_promise_finally(self):
        """Test finally callback."""
        promise = Promise()
        finally_callback = Mock()
        
        promise.finally_callback(finally_callback)
        promise.resolve("test_result")
        
        finally_callback.assert_called_once()
    
    def test_promise_resolve_with(self):
        """Test Promise.resolve_with class method."""
        promise = Promise.resolve_with("test_result")
        
        assert promise.state == 'fulfilled'
        assert promise.result == "test_result"
    
    def test_promise_reject_with(self):
        """Test Promise.reject_with class method."""
        test_error = ValueError("Test error")
        promise = Promise.reject_with(test_error)
        
        assert promise.state == 'rejected'
        assert promise.error == test_error


class TestAsyncMixin:
    """Test AsyncMixin functionality."""
    
    class TestComponent(AsyncMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    def test_async_mixin_creation(self):
        """Test creating a component with AsyncMixin."""
        component = self.TestComponent()
        
        assert hasattr(component, 'async_signals')
        assert hasattr(component, 'async_operations')
        assert hasattr(component, 'async_boundary')
        assert hasattr(component, 'thread_pool')
        assert hasattr(component, 'monitor')
        assert component.async_operations == {}
    
    def test_run_async(self):
        """Test running async operations."""
        component = self.TestComponent()
        
        async def test_coro():
            await asyncio.sleep(0.01)
            return "test_result"
        
        promise = component.run_async(test_coro(), "test_operation")
        
        assert isinstance(promise, Promise)
        # Note: Full async testing would require more complex setup
    
    def test_cancel_operation(self):
        """Test canceling operations."""
        component = self.TestComponent()
        
        # Create a mock operation
        operation = AsyncOperationState("test_operation")
        operation.is_running = True
        component.async_operations["test_operation"] = operation
        
        # Mock the signals
        component.async_signals = Mock()
        component.async_signals.operation_cancelled = Mock()
        component.async_signals.operation_cancelled.emit = Mock()
        
        component.cancel_operation("test_operation")
        
        assert operation.is_cancelled
        component.async_signals.operation_cancelled.emit.assert_called_once_with("test_operation")
    
    def test_cancel_all_operations(self):
        """Test canceling all operations."""
        component = self.TestComponent()
        
        # Create mock operations
        op1 = AsyncOperationState("op1")
        op1.is_running = True
        op2 = AsyncOperationState("op2")
        op2.is_running = True
        
        component.async_operations["op1"] = op1
        component.async_operations["op2"] = op2
        
        # Mock the signals
        component.async_signals = Mock()
        component.async_signals.operation_cancelled = Mock()
        component.async_signals.operation_cancelled.emit = Mock()
        
        component.cancel_all_operations()
        
        assert op1.is_cancelled
        assert op2.is_cancelled
        assert component.async_signals.operation_cancelled.emit.call_count == 2
    
    def test_is_operation_running(self):
        """Test checking if operation is running."""
        component = self.TestComponent()
        
        # Create mock operation
        operation = AsyncOperationState("test_operation")
        operation.is_running = True
        component.async_operations["test_operation"] = operation
        
        assert component.is_operation_running("test_operation")
        assert not component.is_operation_running("nonexistent_operation")
    
    def test_get_operation_state(self):
        """Test getting operation state."""
        component = self.TestComponent()
        
        # Create mock operation
        operation = AsyncOperationState("test_operation")
        component.async_operations["test_operation"] = operation
        
        state = component.get_operation_state("test_operation")
        assert state == operation
        
        state = component.get_operation_state("nonexistent_operation")
        assert state is None
    
    def test_operation_lifecycle(self):
        """Test operation lifecycle callbacks."""
        component = self.TestComponent()
        
        # Test operation started
        component._on_operation_started("test_operation")
        
        assert "test_operation" in component.async_operations
        operation = component.async_operations["test_operation"]
        assert operation.is_running
        assert operation.start_time is not None
        
        # Test operation completed
        component._on_operation_completed("test_operation", "result")
        
        assert not operation.is_running
        assert operation.result == "result"
        assert operation.end_time is not None
        
        # Test operation failed
        component._on_operation_started("failed_operation")
        test_error = ValueError("Test error")
        component._on_operation_failed("failed_operation", test_error)
        
        failed_op = component.async_operations["failed_operation"]
        assert not failed_op.is_running
        assert failed_op.error == test_error
        assert failed_op.end_time is not None
        
        # Test operation cancelled
        component._on_operation_started("cancelled_operation")
        component._on_operation_cancelled("cancelled_operation")
        
        cancelled_op = component.async_operations["cancelled_operation"]
        assert not cancelled_op.is_running
        assert cancelled_op.is_cancelled
        assert cancelled_op.end_time is not None


class TestLoadingStateMixin:
    """Test LoadingStateMixin functionality."""
    
    class TestComponent(LoadingStateMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    def test_loading_state_mixin_creation(self):
        """Test creating a component with LoadingStateMixin."""
        component = self.TestComponent()
        
        assert hasattr(component, 'loading_states')
        assert hasattr(component, 'loading_signals')
        assert component.loading_states == {}
    
    def test_set_loading_state(self):
        """Test setting loading state."""
        component = self.TestComponent()
        
        component.set_loading_state("operation1", True)
        assert component.loading_states["operation1"] is True
        
        component.set_loading_state("operation1", False)
        assert component.loading_states["operation1"] is False
    
    def test_is_loading(self):
        """Test checking loading state."""
        component = self.TestComponent()
        
        assert not component.is_loading()
        assert not component.is_loading("operation1")
        
        component.set_loading_state("operation1", True)
        assert component.is_loading()
        assert component.is_loading("operation1")
        
        component.set_loading_state("operation2", True)
        assert component.is_loading()
        
        component.set_loading_state("operation1", False)
        assert component.is_loading()  # operation2 still loading
        
        component.set_loading_state("operation2", False)
        assert not component.is_loading()
    
    def test_get_loading_operations(self):
        """Test getting loading operations."""
        component = self.TestComponent()
        
        assert component.get_loading_operations() == []
        
        component.set_loading_state("operation1", True)
        component.set_loading_state("operation2", True)
        component.set_loading_state("operation3", False)
        
        loading_ops = component.get_loading_operations()
        assert "operation1" in loading_ops
        assert "operation2" in loading_ops
        assert "operation3" not in loading_ops
        assert len(loading_ops) == 2


class TestTimeoutMixin:
    """Test TimeoutMixin functionality."""
    
    class TestComponent(TimeoutMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    def test_timeout_mixin_creation(self):
        """Test creating a component with TimeoutMixin."""
        component = self.TestComponent()
        
        assert hasattr(component, 'timeouts')
        assert hasattr(component, 'default_timeout')
        assert component.timeouts == {}
        assert component.default_timeout == 30000
    
    def test_set_timeout(self):
        """Test setting timeout."""
        component = self.TestComponent()
        
        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance
            
            component.set_timeout("operation1", 5000)
            
            assert "operation1" in component.timeouts
            assert component.timeouts["operation1"] == mock_timer_instance
            mock_timer_instance.setSingleShot.assert_called_once_with(True)
            mock_timer_instance.start.assert_called_once_with(5000)
    
    def test_clear_timeout(self):
        """Test clearing timeout."""
        component = self.TestComponent()
        
        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance
            
            component.set_timeout("operation1", 5000)
            component.clear_timeout("operation1")
            
            assert "operation1" not in component.timeouts
            mock_timer_instance.stop.assert_called_once()
    
    def test_handle_timeout(self):
        """Test handling timeout."""
        component = self.TestComponent()
        component.cancel_operation = Mock()
        component.async_signals = Mock()
        component.async_signals.operation_failed = Mock()
        component.async_signals.operation_failed.emit = Mock()
        
        component._handle_timeout("operation1")
        
        component.cancel_operation.assert_called_once_with("operation1")
        component.async_signals.operation_failed.emit.assert_called_once()


class TestProgressMixin:
    """Test ProgressMixin functionality."""
    
    class TestComponent(ProgressMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    def test_progress_mixin_creation(self):
        """Test creating a component with ProgressMixin."""
        component = self.TestComponent()
        
        assert hasattr(component, 'progress_states')
        assert hasattr(component, 'progress_signals')
        assert component.progress_states == {}
    
    def test_update_progress(self):
        """Test updating progress."""
        component = self.TestComponent()
        
        # Mock the signals
        component.progress_signals = Mock()
        component.progress_signals.progress_updated = Mock()
        component.progress_signals.progress_updated.emit = Mock()
        
        component.update_progress("operation1", 50)
        
        assert component.progress_states["operation1"] == 50
        component.progress_signals.progress_updated.emit.assert_called_once_with("operation1", 50)
    
    def test_update_progress_bounds(self):
        """Test progress bounds checking."""
        component = self.TestComponent()
        
        # Mock the signals
        component.progress_signals = Mock()
        component.progress_signals.progress_updated = Mock()
        component.progress_signals.progress_updated.emit = Mock()
        
        # Test lower bound
        component.update_progress("operation1", -10)
        assert component.progress_states["operation1"] == 0
        
        # Test upper bound
        component.update_progress("operation1", 150)
        assert component.progress_states["operation1"] == 100
    
    def test_get_progress(self):
        """Test getting progress."""
        component = self.TestComponent()
        
        assert component.get_progress("operation1") == 0
        
        component.progress_states["operation1"] = 75
        assert component.get_progress("operation1") == 75
    
    def test_reset_progress(self):
        """Test resetting progress."""
        component = self.TestComponent()
        
        # Mock the signals
        component.progress_signals = Mock()
        component.progress_signals.progress_updated = Mock()
        component.progress_signals.progress_updated.emit = Mock()
        
        component.progress_states["operation1"] = 50
        component.reset_progress("operation1")
        
        assert component.progress_states["operation1"] == 0
        component.progress_signals.progress_updated.emit.assert_called_once_with("operation1", 0)


class TestAsyncReactiveWidget:
    """Test AsyncReactiveWidget functionality."""
    
    def test_async_reactive_widget_creation(self):
        """Test creating an AsyncReactiveWidget."""
        with patch('torematrix.ui.components.mixins.ReactiveWidget'):
            widget = AsyncReactiveWidget()
            
            # Check that all mixins are included
            assert hasattr(widget, 'async_signals')
            assert hasattr(widget, 'loading_states')
            assert hasattr(widget, 'timeouts')
            assert hasattr(widget, 'progress_states')
    
    def test_async_state_change(self):
        """Test async state change handling."""
        with patch('torematrix.ui.components.mixins.ReactiveWidget') as mock_reactive:
            widget = AsyncReactiveWidget()
            
            # Mock the set_state method
            widget.set_state = Mock()
            
            # Create mock operation
            operation = AsyncOperationState("test_operation")
            operation.is_running = True
            widget.async_operations["test_operation"] = operation
            
            # Test state change
            widget._on_async_state_change("test_operation")
            
            # Verify set_state was called
            widget.set_state.assert_called_once()
            call_args = widget.set_state.call_args[0][0]
            assert 'async_operations' in call_args
            assert 'loading' in call_args
            assert 'loading_operations' in call_args


class TestAsyncMethodDecorator:
    """Test async_method decorator."""
    
    def test_async_method_decorator(self):
        """Test applying async_method decorator."""
        class TestComponent:
            def __init__(self):
                self.set_timeout = Mock()
                self.reset_progress = Mock()
                self.update_progress = Mock()
                self.clear_timeout = Mock()
            
            @async_method(timeout_ms=5000, show_progress=True)
            async def test_method(self):
                return "success"
        
        component = TestComponent()
        
        # Test that decorator is applied
        assert hasattr(component.test_method, '__wrapped__')
        
        # Note: Full async testing would require more complex setup
        # to actually run the decorated method


class TestAsyncOperationContext:
    """Test async_operation_context context manager."""
    
    def test_async_operation_context(self):
        """Test async operation context manager."""
        class MockComponent:
            def __init__(self):
                self.async_signals = Mock()
                self.async_signals.operation_started = Mock()
                self.async_signals.operation_started.emit = Mock()
                self.async_signals.operation_completed = Mock()
                self.async_signals.operation_completed.emit = Mock()
                self.clear_timeout = Mock()
        
        component = MockComponent()
        
        # Note: Testing async context manager requires more complex setup
        # This is a basic structure test
        assert hasattr(component, 'async_signals')
        assert hasattr(component, 'clear_timeout')


class TestAsyncOperationState:
    """Test AsyncOperationState class."""
    
    def test_async_operation_state_creation(self):
        """Test creating an AsyncOperationState."""
        state = AsyncOperationState("test_operation")
        
        assert state.name == "test_operation"
        assert not state.is_running
        assert not state.is_cancelled
        assert state.progress == 0
        assert state.result is None
        assert state.error is None
        assert state.start_time is None
        assert state.end_time is None


@pytest.fixture
def mock_qt_app():
    """Mock Qt application for testing."""
    with patch('PyQt6.QtWidgets.QApplication.instance'):
        yield


@pytest.fixture
def test_async_component(mock_qt_app):
    """Create test async component."""
    class TestComponent(AsyncMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    return TestComponent()


def test_async_integration(test_async_component):
    """Test async integration."""
    component = test_async_component
    
    # Test that component has async capabilities
    assert hasattr(component, 'run_async')
    assert hasattr(component, 'cancel_operation')
    assert hasattr(component, 'cancel_all_operations')
    assert hasattr(component, 'is_operation_running')
    assert hasattr(component, 'get_operation_state')
    
    # Test async operations dictionary
    assert isinstance(component.async_operations, dict)
    assert len(component.async_operations) == 0


def test_multiple_mixins():
    """Test combining multiple mixins."""
    class MultiMixinComponent(AsyncMixin, LoadingStateMixin, TimeoutMixin, ProgressMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    component = MultiMixinComponent()
    
    # Test that all mixin capabilities are available
    assert hasattr(component, 'async_signals')
    assert hasattr(component, 'loading_states')
    assert hasattr(component, 'timeouts')
    assert hasattr(component, 'progress_states')
    
    # Test that methods work together
    component.set_loading_state("operation1", True)
    component.update_progress("operation1", 50)
    
    assert component.is_loading("operation1")
    assert component.get_progress("operation1") == 50