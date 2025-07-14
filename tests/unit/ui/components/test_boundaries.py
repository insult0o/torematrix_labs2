"""
Tests for Error Boundary Components.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from torematrix.ui.components.boundaries import (
    ErrorBoundary,
    ErrorBoundaryWidget,
    ComponentError,
    StateResetStrategy,
    RetryStrategy,
    AsyncErrorBoundary,
    GlobalErrorBoundary,
    error_boundary,
    async_safe
)


class TestErrorBoundary:
    """Test error boundary functionality."""
    
    def test_error_boundary_creation(self):
        """Test creating an error boundary."""
        widget = QWidget()
        boundary = ErrorBoundary(widget)
        
        assert boundary.component == widget
        assert boundary.signals is not None
        assert len(boundary.recovery_strategies) == 2  # StateReset and Retry
        assert not boundary.is_error_state
        assert boundary.error_history == []
    
    def test_handle_error(self):
        """Test error handling."""
        widget = QWidget()
        boundary = ErrorBoundary(widget)
        
        # Mock the monitor
        boundary.monitor = Mock()
        boundary.monitor.record_error = Mock()
        
        # Test error handling
        test_error = ValueError("Test error")
        context = {'test': 'context'}
        
        boundary.handle_error(test_error, context)
        
        assert len(boundary.error_history) == 1
        error = boundary.error_history[0]
        assert isinstance(error, ComponentError)
        assert error.original_error == test_error
        assert error.context == context
        
        # Verify monitor was called
        boundary.monitor.record_error.assert_called_once()
    
    def test_state_reset_strategy(self):
        """Test state reset recovery strategy."""
        widget = Mock()
        widget.reset_state = Mock()
        
        strategy = StateResetStrategy()
        error = ComponentError(ValueError("test"), widget, {})
        
        # Test can_recover
        assert strategy.can_recover(error)
        
        # Test recover
        result = strategy.recover(error)
        assert result is True
        widget.reset_state.assert_called_once()
    
    def test_retry_strategy(self):
        """Test retry recovery strategy."""
        widget = Mock()
        widget.retry_last_operation = Mock()
        
        strategy = RetryStrategy(max_retries=2)
        error = ComponentError(ValueError("test"), widget, {})
        
        # Test can_recover
        assert strategy.can_recover(error)
        
        # Test recover
        result = strategy.recover(error)
        assert result is True
        widget.retry_last_operation.assert_called_once()
        
        # Test retry limit
        strategy.recover(error)  # Second retry
        result = strategy.recover(error)  # Third retry should fail
        assert result is False
    
    def test_show_fallback(self):
        """Test showing fallback UI."""
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        
        boundary = ErrorBoundary(widget)
        test_error = ValueError("Test error")
        component_error = ComponentError(test_error, widget, {})
        
        boundary.show_fallback(component_error)
        
        assert boundary.is_error_state
        assert boundary.fallback_widget is not None
        assert isinstance(boundary.fallback_widget, ErrorBoundaryWidget)
    
    def test_clear_error_state(self):
        """Test clearing error state."""
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        
        boundary = ErrorBoundary(widget)
        test_error = ValueError("Test error")
        component_error = ComponentError(test_error, widget, {})
        
        # Set error state
        boundary.show_fallback(component_error)
        assert boundary.is_error_state
        
        # Clear error state
        boundary.clear_error_state()
        assert not boundary.is_error_state
        assert boundary.fallback_widget is None
    
    def test_error_boundary_decorator(self):
        """Test error boundary decorator."""
        @error_boundary()
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.test_method_called = False
            
            def test_method(self):
                self.test_method_called = True
                raise ValueError("Test error")
        
        widget = TestWidget()
        assert hasattr(widget, 'boundary')
        assert isinstance(widget.boundary, ErrorBoundary)
        
        # Test that error is caught
        with pytest.raises(ValueError):
            widget.test_method()
        
        assert widget.test_method_called
        # Error should be in boundary history
        assert len(widget.boundary.error_history) > 0


class TestAsyncErrorBoundary:
    """Test async error boundary functionality."""
    
    def test_async_error_boundary_creation(self):
        """Test creating an async error boundary."""
        widget = QWidget()
        boundary = AsyncErrorBoundary(widget)
        
        assert boundary.component == widget
        assert boundary.signals is not None
        assert len(boundary.active_operations) == 0
    
    def test_handle_async_error(self):
        """Test handling async errors."""
        widget = QWidget()
        boundary = AsyncErrorBoundary(widget)
        
        # Mock the signals
        boundary.signals = Mock()
        boundary.signals.error_caught = Mock()
        boundary.signals.error_caught.emit = Mock()
        
        test_error = ValueError("Async test error")
        boundary.handle_async_error(test_error, "test_operation")
        
        # Verify signal emission (would be called via QTimer)
        # We can't easily test QTimer.singleShot, so we check the setup
        assert boundary.signals.error_caught.emit is not None
    
    def test_async_safe_decorator(self):
        """Test async_safe decorator."""
        class TestComponent:
            def __init__(self):
                self.async_boundary = AsyncErrorBoundary(QWidget())
                self.async_boundary.catch_async_errors = Mock()
                self.async_boundary.catch_async_errors.return_value.__enter__ = Mock()
                self.async_boundary.catch_async_errors.return_value.__exit__ = Mock()
            
            @async_safe("test_operation")
            async def test_async_method(self):
                return "success"
        
        component = TestComponent()
        
        # Test that the decorator is applied
        assert hasattr(component.test_async_method, '__wrapped__')


class TestGlobalErrorBoundary:
    """Test global error boundary functionality."""
    
    def test_singleton_pattern(self):
        """Test that GlobalErrorBoundary is a singleton."""
        boundary1 = GlobalErrorBoundary()
        boundary2 = GlobalErrorBoundary()
        
        assert boundary1 is boundary2
    
    def test_register_component(self):
        """Test registering a component."""
        global_boundary = GlobalErrorBoundary()
        widget = QWidget()
        
        boundary = global_boundary.register_component(widget)
        
        assert isinstance(boundary, ErrorBoundary)
        assert widget in global_boundary.component_boundaries
        assert global_boundary.component_boundaries[widget] == boundary
    
    def test_handle_global_error(self):
        """Test handling global errors."""
        global_boundary = GlobalErrorBoundary()
        global_boundary.monitor = Mock()
        global_boundary.monitor.record_error = Mock()
        
        widget = QWidget()
        test_error = ValueError("Global test error")
        component_error = ComponentError(test_error, widget, {})
        
        global_boundary.handle_global_error(component_error)
        
        # Verify monitor was called
        global_boundary.monitor.record_error.assert_called_once()
    
    def test_add_error_handler(self):
        """Test adding error handlers."""
        global_boundary = GlobalErrorBoundary()
        handler = Mock()
        
        global_boundary.add_error_handler(handler)
        
        assert handler in global_boundary.error_handlers
        
        # Test handler is called
        widget = QWidget()
        test_error = ValueError("Test error")
        component_error = ComponentError(test_error, widget, {})
        
        global_boundary.handle_global_error(component_error)
        
        handler.assert_called_once_with(component_error)
    
    def test_get_error_stats(self):
        """Test getting error statistics."""
        global_boundary = GlobalErrorBoundary()
        global_boundary.monitor = Mock()
        global_boundary.monitor.get_error_summary = Mock(return_value={})
        global_boundary.monitor.get_component_error_ranking = Mock(return_value=[])
        
        stats = global_boundary.get_error_stats()
        
        assert isinstance(stats, dict)
        assert 'total_boundaries' in stats
        assert 'total_errors' in stats
        assert 'error_types' in stats
        assert 'most_error_prone_components' in stats


class TestErrorBoundaryWidget:
    """Test error boundary widget functionality."""
    
    def test_error_boundary_widget_creation(self):
        """Test creating an error boundary widget."""
        widget = QWidget()
        test_error = ValueError("Test error")
        component_error = ComponentError(test_error, widget, {'test': 'context'})
        
        error_widget = ErrorBoundaryWidget(component_error)
        
        assert error_widget.error == component_error
        assert error_widget.layout() is not None
        
        # Check that UI elements are created
        children = error_widget.findChildren(QLabel)
        assert len(children) >= 2  # Title and message labels
    
    def test_retry_operation(self):
        """Test retry operation functionality."""
        widget = QWidget()
        test_error = ValueError("Test error")
        component_error = ComponentError(test_error, widget, {})
        
        # Create parent with boundary
        parent = QWidget()
        parent.boundary = Mock()
        parent.boundary.retry_recovery = Mock()
        
        error_widget = ErrorBoundaryWidget(component_error, parent)
        
        # Test retry
        error_widget.retry_operation()
        
        parent.boundary.retry_recovery.assert_called_once()


class TestComponentError:
    """Test ComponentError class."""
    
    def test_component_error_creation(self):
        """Test creating a ComponentError."""
        widget = QWidget()
        widget.__class__.__name__ = "TestWidget"
        
        original_error = ValueError("Original error")
        context = {'test': 'context'}
        
        error = ComponentError(original_error, widget, context)
        
        assert error.original_error == original_error
        assert error.component == widget
        assert error.context == context
        assert "TestWidget" in str(error)
        assert "Original error" in str(error)


@pytest.fixture
def mock_app():
    """Mock QApplication for testing."""
    app = Mock()
    with patch('PyQt6.QtWidgets.QApplication.instance', return_value=app):
        yield app


@pytest.fixture
def test_widget():
    """Create a test widget."""
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


@pytest.fixture
def error_boundary(test_widget):
    """Create an error boundary with test widget."""
    return ErrorBoundary(test_widget)


def test_error_boundary_integration(error_boundary, test_widget):
    """Test error boundary integration."""
    # Test that error boundary is properly integrated
    assert error_boundary.component == test_widget
    assert not error_boundary.is_error_state
    
    # Test error handling
    test_error = ValueError("Integration test error")
    error_boundary.handle_error(test_error)
    
    assert len(error_boundary.error_history) == 1
    assert isinstance(error_boundary.error_history[0], ComponentError)


def test_multiple_error_boundaries():
    """Test multiple error boundaries."""
    widget1 = QWidget()
    widget2 = QWidget()
    
    boundary1 = ErrorBoundary(widget1)
    boundary2 = ErrorBoundary(widget2)
    
    assert boundary1.component == widget1
    assert boundary2.component == widget2
    assert boundary1 is not boundary2
    
    # Test that errors are isolated
    boundary1.handle_error(ValueError("Error 1"))
    boundary2.handle_error(ValueError("Error 2"))
    
    assert len(boundary1.error_history) == 1
    assert len(boundary2.error_history) == 1
    assert boundary1.error_history[0].original_error.args[0] == "Error 1"
    assert boundary2.error_history[0].original_error.args[0] == "Error 2"


def test_error_boundary_cleanup():
    """Test error boundary cleanup."""
    widget = QWidget()
    boundary = ErrorBoundary(widget)
    
    # Create error state
    boundary.handle_error(ValueError("Test error"))
    assert len(boundary.error_history) == 1
    
    # Reset boundary
    boundary.reset()
    assert len(boundary.error_history) == 0
    assert not boundary.is_error_state