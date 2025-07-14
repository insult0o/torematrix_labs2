"""
Async Operation Mixins for Reactive Components.
This module provides async/await support and promise-like patterns for Qt components,
enabling smooth integration of async operations with reactive UI components.
"""
from __future__ import annotations

import asyncio
import weakref
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar, Union
from functools import wraps
from contextlib import asynccontextmanager

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QRunnable, QThreadPool
from PyQt6.QtWidgets import QWidget

from .reactive import ReactiveWidget
from .boundaries import AsyncErrorBoundary
from .monitoring import PerformanceMonitor


T = TypeVar('T')


class AsyncOperationSignals(QObject):
    """Signals for async operation events."""
    operation_started = pyqtSignal(str)  # operation_name
    operation_completed = pyqtSignal(str, object)  # operation_name, result
    operation_failed = pyqtSignal(str, object)  # operation_name, error
    operation_cancelled = pyqtSignal(str)  # operation_name
    progress_updated = pyqtSignal(str, int)  # operation_name, percentage


class AsyncOperationState:
    """State tracking for async operations."""
    
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self.is_cancelled = False
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None


class AsyncTask(QRunnable, Generic[T]):
    """Qt-compatible async task wrapper."""
    
    def __init__(self, coro: Awaitable[T], name: str = "async_task"):
        super().__init__()
        self.coro = coro
        self.name = name
        self.signals = AsyncOperationSignals()
        self.is_cancelled = False
        self.result = None
        self.error = None
    
    def run(self):
        """Run the async task in a thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the coroutine
            self.result = loop.run_until_complete(self.coro)
            
            # Signal completion
            self.signals.operation_completed.emit(self.name, self.result)
            
        except Exception as e:
            self.error = e
            self.signals.operation_failed.emit(self.name, e)
        finally:
            loop.close()
    
    def cancel(self):
        """Cancel the async task."""
        self.is_cancelled = True
        self.signals.operation_cancelled.emit(self.name)


class Promise(Generic[T]):
    """Promise-like pattern for Qt async operations."""
    
    def __init__(self, executor: Optional[Callable] = None):
        self.signals = AsyncOperationSignals()
        self.state = 'pending'  # pending, fulfilled, rejected
        self.result: Optional[T] = None
        self.error: Optional[Exception] = None
        self.then_callbacks = []
        self.catch_callbacks = []
        self.finally_callbacks = []
        
        if executor:
            try:
                executor(self.resolve, self.reject)
            except Exception as e:
                self.reject(e)
    
    def resolve(self, value: T):
        """Resolve the promise with a value."""
        if self.state != 'pending':
            return
        
        self.state = 'fulfilled'
        self.result = value
        
        # Execute then callbacks
        for callback in self.then_callbacks:
            try:
                callback(value)
            except Exception as e:
                self.reject(e)
                return
        
        # Execute finally callbacks
        self._execute_finally_callbacks()
    
    def reject(self, error: Exception):
        """Reject the promise with an error."""
        if self.state != 'pending':
            return
        
        self.state = 'rejected'
        self.error = error
        
        # Execute catch callbacks
        for callback in self.catch_callbacks:
            try:
                callback(error)
            except Exception as e:
                # If catch callback fails, log it
                import logging
                logging.error(f"Promise catch callback failed: {e}")
        
        # Execute finally callbacks
        self._execute_finally_callbacks()
    
    def then(self, callback: Callable[[T], Any]) -> Promise:
        """Add a then callback."""
        if self.state == 'fulfilled':
            # Execute immediately
            try:
                callback(self.result)
            except Exception as e:
                return Promise.reject_with(e)
        elif self.state == 'pending':
            self.then_callbacks.append(callback)
        
        return self
    
    def catch(self, callback: Callable[[Exception], Any]) -> Promise:
        """Add a catch callback."""
        if self.state == 'rejected':
            # Execute immediately
            try:
                callback(self.error)
            except Exception as e:
                import logging
                logging.error(f"Promise catch callback failed: {e}")
        elif self.state == 'pending':
            self.catch_callbacks.append(callback)
        
        return self
    
    def finally_callback(self, callback: Callable[[], Any]) -> Promise:
        """Add a finally callback."""
        if self.state != 'pending':
            # Execute immediately
            try:
                callback()
            except Exception as e:
                import logging
                logging.error(f"Promise finally callback failed: {e}")
        else:
            self.finally_callbacks.append(callback)
        
        return self
    
    def _execute_finally_callbacks(self):
        """Execute finally callbacks."""
        for callback in self.finally_callbacks:
            try:
                callback()
            except Exception as e:
                import logging
                logging.error(f"Promise finally callback failed: {e}")
    
    @classmethod
    def resolve_with(cls, value: T) -> Promise[T]:
        """Create a resolved promise."""
        promise = cls()
        promise.resolve(value)
        return promise
    
    @classmethod
    def reject_with(cls, error: Exception) -> Promise[T]:
        """Create a rejected promise."""
        promise = cls()
        promise.reject(error)
        return promise


class AsyncMixin:
    """Mixin to add async capabilities to Qt components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.async_signals = AsyncOperationSignals()
        self.async_operations: Dict[str, AsyncOperationState] = {}
        self.async_boundary = AsyncErrorBoundary(self)
        self.thread_pool = QThreadPool()
        self.monitor = PerformanceMonitor()
        
        # Connect signals
        self.async_signals.operation_started.connect(self._on_operation_started)
        self.async_signals.operation_completed.connect(self._on_operation_completed)
        self.async_signals.operation_failed.connect(self._on_operation_failed)
        self.async_signals.operation_cancelled.connect(self._on_operation_cancelled)
    
    def run_async(self, coro: Awaitable[T], name: str = None) -> Promise[T]:
        """Run an async operation and return a promise."""
        if name is None:
            name = f"async_op_{id(coro)}"
        
        # Create promise
        promise = Promise[T]()
        
        # Create async task
        task = AsyncTask(coro, name)
        
        # Connect task signals to promise
        task.signals.operation_completed.connect(
            lambda op_name, result: promise.resolve(result)
        )
        task.signals.operation_failed.connect(
            lambda op_name, error: promise.reject(error)
        )
        task.signals.operation_cancelled.connect(
            lambda op_name: promise.reject(asyncio.CancelledError())
        )
        
        # Connect to async signals
        task.signals.operation_started.connect(self.async_signals.operation_started)
        task.signals.operation_completed.connect(self.async_signals.operation_completed)
        task.signals.operation_failed.connect(self.async_signals.operation_failed)
        task.signals.operation_cancelled.connect(self.async_signals.operation_cancelled)
        
        # Start task
        self.thread_pool.start(task)
        
        return promise
    
    def cancel_operation(self, name: str):
        """Cancel an async operation."""
        if name in self.async_operations:
            operation = self.async_operations[name]
            if operation.is_running:
                operation.is_cancelled = True
                self.async_signals.operation_cancelled.emit(name)
    
    def cancel_all_operations(self):
        """Cancel all running async operations."""
        for name, operation in self.async_operations.items():
            if operation.is_running:
                self.cancel_operation(name)
    
    def is_operation_running(self, name: str) -> bool:
        """Check if an operation is running."""
        return name in self.async_operations and self.async_operations[name].is_running
    
    def get_operation_state(self, name: str) -> Optional[AsyncOperationState]:
        """Get the state of an async operation."""
        return self.async_operations.get(name)
    
    def _on_operation_started(self, name: str):
        """Handle operation start."""
        if name not in self.async_operations:
            self.async_operations[name] = AsyncOperationState(name)
        
        operation = self.async_operations[name]
        operation.is_running = True
        operation.start_time = self.monitor.current_time()
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_loading_state'):
            self.set_loading_state(name, True)
    
    def _on_operation_completed(self, name: str, result: Any):
        """Handle operation completion."""
        if name in self.async_operations:
            operation = self.async_operations[name]
            operation.is_running = False
            operation.result = result
            operation.end_time = self.monitor.current_time()
            
            # Record performance
            if operation.start_time:
                duration = operation.end_time - operation.start_time
                self.monitor.record_async_operation(name, duration, success=True)
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_loading_state'):
            self.set_loading_state(name, False)
    
    def _on_operation_failed(self, name: str, error: Exception):
        """Handle operation failure."""
        if name in self.async_operations:
            operation = self.async_operations[name]
            operation.is_running = False
            operation.error = error
            operation.end_time = self.monitor.current_time()
            
            # Record performance
            if operation.start_time:
                duration = operation.end_time - operation.start_time
                self.monitor.record_async_operation(name, duration, success=False)
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_loading_state'):
            self.set_loading_state(name, False)
        
        # Handle error through boundary
        self.async_boundary.handle_async_error(error, name)
    
    def _on_operation_cancelled(self, name: str):
        """Handle operation cancellation."""
        if name in self.async_operations:
            operation = self.async_operations[name]
            operation.is_running = False
            operation.is_cancelled = True
            operation.end_time = self.monitor.current_time()
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_loading_state'):
            self.set_loading_state(name, False)


class LoadingStateMixin:
    """Mixin to add loading state management to components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loading_states: Dict[str, bool] = {}
        self.loading_signals = AsyncOperationSignals()
    
    def set_loading_state(self, operation: str, loading: bool):
        """Set loading state for an operation."""
        self.loading_states[operation] = loading
        
        # Update overall loading state
        is_loading = any(self.loading_states.values())
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_state'):
            self.set_state({
                'loading': is_loading,
                'loading_operations': list(self.loading_states.keys())
            })
    
    def is_loading(self, operation: str = None) -> bool:
        """Check if loading (either specific operation or any operation)."""
        if operation:
            return self.loading_states.get(operation, False)
        return any(self.loading_states.values())
    
    def get_loading_operations(self) -> list[str]:
        """Get list of currently loading operations."""
        return [op for op, loading in self.loading_states.items() if loading]


class TimeoutMixin:
    """Mixin to add timeout support to async operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeouts: Dict[str, QTimer] = {}
        self.default_timeout = 30000  # 30 seconds
    
    def set_timeout(self, operation: str, timeout_ms: int = None):
        """Set timeout for an operation."""
        if timeout_ms is None:
            timeout_ms = self.default_timeout
        
        # Cancel existing timeout
        if operation in self.timeouts:
            self.timeouts[operation].stop()
        
        # Create new timeout
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._handle_timeout(operation))
        timer.start(timeout_ms)
        
        self.timeouts[operation] = timer
    
    def clear_timeout(self, operation: str):
        """Clear timeout for an operation."""
        if operation in self.timeouts:
            self.timeouts[operation].stop()
            del self.timeouts[operation]
    
    def _handle_timeout(self, operation: str):
        """Handle operation timeout."""
        if hasattr(self, 'cancel_operation'):
            self.cancel_operation(operation)
        
        # Emit timeout signal if available
        if hasattr(self, 'async_signals'):
            self.async_signals.operation_failed.emit(
                operation, 
                asyncio.TimeoutError(f"Operation {operation} timed out")
            )


class ProgressMixin:
    """Mixin to add progress tracking to async operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_states: Dict[str, int] = {}
        self.progress_signals = AsyncOperationSignals()
    
    def update_progress(self, operation: str, percentage: int):
        """Update progress for an operation."""
        self.progress_states[operation] = max(0, min(100, percentage))
        self.progress_signals.progress_updated.emit(operation, percentage)
        
        # Update UI if this is a reactive component
        if hasattr(self, 'set_state'):
            self.set_state({
                'progress': self.progress_states
            })
    
    def get_progress(self, operation: str) -> int:
        """Get progress for an operation."""
        return self.progress_states.get(operation, 0)
    
    def reset_progress(self, operation: str):
        """Reset progress for an operation."""
        self.progress_states[operation] = 0
        self.progress_signals.progress_updated.emit(operation, 0)


class AsyncReactiveWidget(ReactiveWidget, AsyncMixin, LoadingStateMixin, TimeoutMixin, ProgressMixin):
    """Reactive widget with full async capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Connect async signals to state updates
        self.async_signals.operation_started.connect(self._on_async_state_change)
        self.async_signals.operation_completed.connect(self._on_async_state_change)
        self.async_signals.operation_failed.connect(self._on_async_state_change)
        self.async_signals.operation_cancelled.connect(self._on_async_state_change)
    
    def _on_async_state_change(self, *args):
        """Handle async state changes."""
        # Update reactive state based on async operations
        self.set_state({
            'async_operations': {
                name: {
                    'running': op.is_running,
                    'cancelled': op.is_cancelled,
                    'progress': self.get_progress(name),
                    'error': str(op.error) if op.error else None
                }
                for name, op in self.async_operations.items()
            },
            'loading': self.is_loading(),
            'loading_operations': self.get_loading_operations()
        })


def async_method(timeout_ms: int = 30000, show_progress: bool = False):
    """Decorator to make a method async-safe with automatic timeout and progress."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            method_name = func.__name__
            
            # Set timeout if supported
            if hasattr(self, 'set_timeout'):
                self.set_timeout(method_name, timeout_ms)
            
            # Initialize progress if supported
            if show_progress and hasattr(self, 'reset_progress'):
                self.reset_progress(method_name)
            
            try:
                # Run the method
                result = await func(self, *args, **kwargs)
                
                # Complete progress if supported
                if show_progress and hasattr(self, 'update_progress'):
                    self.update_progress(method_name, 100)
                
                return result
                
            finally:
                # Clear timeout if supported
                if hasattr(self, 'clear_timeout'):
                    self.clear_timeout(method_name)
        
        return wrapper
    
    return decorator


@asynccontextmanager
async def async_operation_context(component: AsyncMixin, operation_name: str):
    """Context manager for async operations with automatic cleanup."""
    try:
        # Start operation
        component.async_signals.operation_started.emit(operation_name)
        
        yield
        
        # Complete operation
        component.async_signals.operation_completed.emit(operation_name, None)
        
    except Exception as e:
        # Fail operation
        component.async_signals.operation_failed.emit(operation_name, e)
        raise
    
    finally:
        # Cleanup
        if hasattr(component, 'clear_timeout'):
            component.clear_timeout(operation_name)