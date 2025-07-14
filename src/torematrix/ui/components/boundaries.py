"""
Error Boundary Components for Reactive Components.
This module provides robust error handling and isolation for reactive components,
preventing errors from propagating throughout the application.
"""
from __future__ import annotations

import logging
import traceback
import weakref
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
from contextlib import contextmanager

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit

from .reactive import ReactiveWidget
from .lifecycle import LifecycleManager
from .monitoring import PerformanceMonitor


logger = logging.getLogger(__name__)


class ErrorBoundaryException(Exception):
    """Base exception for error boundary operations."""
    pass


class ComponentError(ErrorBoundaryException):
    """Represents an error that occurred within a component."""
    
    def __init__(self, original_error: Exception, component: QWidget, context: Dict[str, Any]):
        self.original_error = original_error
        self.component = component
        self.context = context
        super().__init__(f"Component error in {component.__class__.__name__}: {original_error}")


class ErrorBoundarySignals(QObject):
    """Signals for error boundary events."""
    error_caught = pyqtSignal(object)  # ComponentError
    error_recovered = pyqtSignal(object)  # Component
    fallback_rendered = pyqtSignal(object)  # Component
    boundary_reset = pyqtSignal(object)  # Component


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def can_recover(self, error: ComponentError) -> bool:
        """Check if this strategy can recover from the error."""
        return False
    
    def recover(self, error: ComponentError) -> bool:
        """Attempt to recover from the error. Returns True if successful."""
        return False


class StateResetStrategy(ErrorRecoveryStrategy):
    """Recovery strategy that resets component state."""
    
    def can_recover(self, error: ComponentError) -> bool:
        """Check if component has state that can be reset."""
        return hasattr(error.component, 'reset_state')
    
    def recover(self, error: ComponentError) -> bool:
        """Reset component state."""
        try:
            if hasattr(error.component, 'reset_state'):
                error.component.reset_state()
                return True
        except Exception as e:
            logger.error(f"Failed to reset state: {e}")
        return False


class RetryStrategy(ErrorRecoveryStrategy):
    """Recovery strategy that retries the failed operation."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_counts = weakref.WeakKeyDictionary()
    
    def can_recover(self, error: ComponentError) -> bool:
        """Check if we haven't exceeded retry limit."""
        component = error.component
        return self.retry_counts.get(component, 0) < self.max_retries
    
    def recover(self, error: ComponentError) -> bool:
        """Retry the failed operation."""
        component = error.component
        retry_count = self.retry_counts.get(component, 0)
        
        if retry_count >= self.max_retries:
            return False
        
        try:
            # Increment retry count
            self.retry_counts[component] = retry_count + 1
            
            # Attempt to retry last operation
            if hasattr(component, 'retry_last_operation'):
                component.retry_last_operation()
                return True
                
        except Exception as e:
            logger.error(f"Retry failed: {e}")
        
        return False


class ErrorBoundaryWidget(QWidget):
    """Widget that displays error information and recovery options."""
    
    def __init__(self, error: ComponentError, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.error = error
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the error display UI."""
        layout = QVBoxLayout(self)
        
        # Error title
        title = QLabel(f"Error in {self.error.component.__class__.__name__}")
        title.setStyleSheet("font-weight: bold; color: red; font-size: 14px;")
        layout.addWidget(title)
        
        # Error message
        message = QLabel(str(self.error.original_error))
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Error details (expandable)
        details = QTextEdit()
        details.setPlainText(traceback.format_exception(
            type(self.error.original_error),
            self.error.original_error,
            self.error.original_error.__traceback__
        ))
        details.setMaximumHeight(200)
        layout.addWidget(details)
        
        # Recovery button
        retry_btn = QPushButton("Retry")
        retry_btn.clicked.connect(self.retry_operation)
        layout.addWidget(retry_btn)
        
        # Context information
        if self.error.context:
            context_text = QTextEdit()
            context_text.setPlainText(f"Context: {self.error.context}")
            context_text.setMaximumHeight(100)
            layout.addWidget(context_text)
    
    def retry_operation(self):
        """Emit signal to retry the failed operation."""
        self.parent().boundary.retry_recovery()


class ErrorBoundary:
    """Error boundary implementation for reactive components."""
    
    def __init__(self, component: QWidget):
        self.component = component
        self.signals = ErrorBoundarySignals()
        self.recovery_strategies = [
            StateResetStrategy(),
            RetryStrategy(max_retries=3)
        ]
        self.fallback_widget = None
        self.is_error_state = False
        self.error_history = []
        self.monitor = PerformanceMonitor()
        
        # Connect to component lifecycle if available
        if hasattr(component, 'lifecycle'):
            component.lifecycle.error_occurred.connect(self.handle_error)
    
    def add_recovery_strategy(self, strategy: ErrorRecoveryStrategy):
        """Add a custom recovery strategy."""
        self.recovery_strategies.append(strategy)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None):
        """Handle an error that occurred in the component."""
        if context is None:
            context = {}
        
        component_error = ComponentError(error, self.component, context)
        self.error_history.append(component_error)
        
        logger.error(f"Error boundary caught error: {component_error}")
        
        # Record error in performance monitor
        self.monitor.record_error(
            component_type=self.component.__class__.__name__,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )
        
        # Try recovery strategies
        recovered = self.attempt_recovery(component_error)
        
        if not recovered:
            # Show fallback UI
            self.show_fallback(component_error)
        
        # Emit signal
        self.signals.error_caught.emit(component_error)
    
    def attempt_recovery(self, error: ComponentError) -> bool:
        """Attempt to recover from the error using available strategies."""
        for strategy in self.recovery_strategies:
            if strategy.can_recover(error):
                try:
                    if strategy.recover(error):
                        logger.info(f"Recovered from error using {strategy.__class__.__name__}")
                        self.signals.error_recovered.emit(self.component)
                        return True
                except Exception as e:
                    logger.error(f"Recovery strategy failed: {e}")
        
        return False
    
    def show_fallback(self, error: ComponentError):
        """Show fallback UI when recovery fails."""
        self.is_error_state = True
        
        # Create fallback widget
        self.fallback_widget = ErrorBoundaryWidget(error, self.component)
        
        # Replace component content with fallback
        if hasattr(self.component, 'layout') and self.component.layout():
            # Clear existing layout
            layout = self.component.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
            
            # Add fallback widget
            layout.addWidget(self.fallback_widget)
        
        self.signals.fallback_rendered.emit(self.component)
    
    def retry_recovery(self):
        """Retry recovery from the current error state."""
        if not self.is_error_state or not self.error_history:
            return
        
        last_error = self.error_history[-1]
        
        # Try recovery again
        if self.attempt_recovery(last_error):
            self.clear_error_state()
    
    def clear_error_state(self):
        """Clear the error state and restore normal component."""
        if not self.is_error_state:
            return
        
        self.is_error_state = False
        
        # Remove fallback widget
        if self.fallback_widget and hasattr(self.component, 'layout'):
            layout = self.component.layout()
            if layout:
                layout.removeWidget(self.fallback_widget)
                self.fallback_widget.deleteLater()
                self.fallback_widget = None
        
        # Restore component functionality
        if hasattr(self.component, 'restore_from_error'):
            self.component.restore_from_error()
        
        self.signals.boundary_reset.emit(self.component)
    
    def reset(self):
        """Reset the error boundary state."""
        self.error_history.clear()
        self.clear_error_state()
        
        # Reset retry counts in strategies
        for strategy in self.recovery_strategies:
            if isinstance(strategy, RetryStrategy):
                strategy.retry_counts.clear()


def error_boundary(fallback_component: Optional[Type[QWidget]] = None):
    """Decorator to add error boundary to a component."""
    def decorator(component_class: Type[QWidget]):
        
        class ErrorBoundaryComponent(component_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.boundary = ErrorBoundary(self)
                self.boundary.fallback_component = fallback_component
                
                # Override methods to catch errors
                self._wrap_methods()
            
            def _wrap_methods(self):
                """Wrap component methods to catch errors."""
                methods_to_wrap = [
                    'paintEvent', 'resizeEvent', 'mousePressEvent',
                    'mouseReleaseEvent', 'keyPressEvent', 'keyReleaseEvent'
                ]
                
                for method_name in methods_to_wrap:
                    if hasattr(self, method_name):
                        original_method = getattr(self, method_name)
                        wrapped_method = self._wrap_method(original_method)
                        setattr(self, method_name, wrapped_method)
            
            def _wrap_method(self, method: Callable):
                """Wrap a method to catch and handle errors."""
                @wraps(method)
                def wrapper(*args, **kwargs):
                    try:
                        return method(*args, **kwargs)
                    except Exception as e:
                        self.boundary.handle_error(e, {
                            'method': method.__name__,
                            'args': args,
                            'kwargs': kwargs
                        })
                
                return wrapper
        
        return ErrorBoundaryComponent
    
    return decorator


class AsyncErrorBoundary:
    """Error boundary for async operations."""
    
    def __init__(self, component: QWidget):
        self.component = component
        self.signals = ErrorBoundarySignals()
        self.active_operations = weakref.WeakSet()
        
    @contextmanager
    def catch_async_errors(self, operation_name: str = "async_operation"):
        """Context manager for catching async errors."""
        try:
            yield
        except Exception as e:
            self.handle_async_error(e, operation_name)
    
    def handle_async_error(self, error: Exception, operation_name: str):
        """Handle an error from an async operation."""
        context = {
            'operation': operation_name,
            'async': True,
            'component': self.component.__class__.__name__
        }
        
        component_error = ComponentError(error, self.component, context)
        
        logger.error(f"Async error boundary caught error: {component_error}")
        
        # Show error in UI thread
        QTimer.singleShot(0, lambda: self.signals.error_caught.emit(component_error))


def async_safe(operation_name: str = None):
    """Decorator to make async operations safe with error boundaries."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if hasattr(self, 'async_boundary'):
                op_name = operation_name or func.__name__
                with self.async_boundary.catch_async_errors(op_name):
                    return await func(self, *args, **kwargs)
            else:
                return await func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


class GlobalErrorBoundary:
    """Global error boundary for application-wide error handling."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.signals = ErrorBoundarySignals()
        self.component_boundaries = weakref.WeakKeyDictionary()
        self.error_handlers = []
        self.monitor = PerformanceMonitor()
    
    def register_component(self, component: QWidget) -> ErrorBoundary:
        """Register a component with the global error boundary."""
        boundary = ErrorBoundary(component)
        self.component_boundaries[component] = boundary
        
        # Connect to global signals
        boundary.signals.error_caught.connect(self.handle_global_error)
        
        return boundary
    
    def handle_global_error(self, error: ComponentError):
        """Handle a global error from any component."""
        logger.error(f"Global error handler: {error}")
        
        # Record in global performance monitor
        self.monitor.record_error(
            component_type=error.component.__class__.__name__,
            error_type=type(error.original_error).__name__,
            error_message=str(error.original_error),
            context=error.context
        )
        
        # Notify global error handlers
        for handler in self.error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")
    
    def add_error_handler(self, handler: Callable[[ComponentError], None]):
        """Add a global error handler."""
        self.error_handlers.append(handler)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get global error statistics."""
        return {
            'total_boundaries': len(self.component_boundaries),
            'total_errors': sum(len(b.error_history) for b in self.component_boundaries.values()),
            'error_types': self.monitor.get_error_summary(),
            'most_error_prone_components': self.monitor.get_component_error_ranking()
        }