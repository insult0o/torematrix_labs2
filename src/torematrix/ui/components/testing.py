"""
Testing Framework for Reactive Components.
This module provides comprehensive testing utilities for reactive components,
including mock providers, render testing, and integration test patterns.
"""
from __future__ import annotations

import asyncio
import time
import weakref
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtTest import QTest

from .reactive import ReactiveWidget
from .mixins import AsyncMixin, LoadingStateMixin
from .boundaries import ErrorBoundary
from .integration import ReactiveContainer
from ..state.manager import StateManager


T = TypeVar('T', bound=QWidget)


class TestSignals(QObject):
    """Signals for testing events."""
    test_started = pyqtSignal(str)  # test_name
    test_completed = pyqtSignal(str, bool)  # test_name, success
    assertion_failed = pyqtSignal(str, str)  # test_name, message
    render_completed = pyqtSignal(object)  # component


class MockStateManager:
    """Mock state manager for testing."""
    
    def __init__(self):
        self.state = {}
        self.subscriptions = {}
        self.state_history = []
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self.state.get(key, default)
    
    def set_state(self, key: str, value: Any):
        """Set state value."""
        old_value = self.state.get(key)
        self.state[key] = value
        
        # Record in history
        self.state_history.append({
            'key': key,
            'old_value': old_value,
            'new_value': value,
            'timestamp': time.time()
        })
        
        # Notify subscribers
        if key in self.subscriptions:
            for callback in self.subscriptions[key]:
                callback(value)
    
    def subscribe(self, key: str, callback: Callable[[Any], None]):
        """Subscribe to state changes."""
        if key not in self.subscriptions:
            self.subscriptions[key] = []
        self.subscriptions[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable[[Any], None]):
        """Unsubscribe from state changes."""
        if key in self.subscriptions:
            self.subscriptions[key].remove(callback)
    
    def clear_state(self):
        """Clear all state."""
        self.state.clear()
        self.state_history.clear()
    
    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get state change history."""
        return self.state_history.copy()


class ComponentTester:
    """Testing utilities for reactive components."""
    
    def __init__(self, component_class: Type[QWidget]):
        self.component_class = component_class
        self.signals = TestSignals()
        self.mock_state_manager = MockStateManager()
        self.test_instances = []
        self.render_count = 0
        self.last_render_time = 0
    
    def create_test_component(self, *args, **kwargs) -> QWidget:
        """Create a test instance of the component."""
        # Patch state manager
        with patch.object(self.component_class, 'state_manager', self.mock_state_manager):
            component = self.component_class(*args, **kwargs)
        
        # Override state manager
        if hasattr(component, 'state_manager'):
            component.state_manager = self.mock_state_manager
        
        # Track render calls
        if hasattr(component, 'render'):
            original_render = component.render
            
            def tracked_render(*args, **kwargs):
                self.render_count += 1
                self.last_render_time = time.time()
                result = original_render(*args, **kwargs)
                self.signals.render_completed.emit(component)
                return result
            
            component.render = tracked_render
        
        # Add to test instances
        self.test_instances.append(component)
        
        return component
    
    def trigger_state_change(self, key: str, value: Any):
        """Trigger a state change for testing."""
        self.mock_state_manager.set_state(key, value)
    
    def assert_state_value(self, key: str, expected_value: Any):
        """Assert that state has expected value."""
        actual_value = self.mock_state_manager.get_state(key)
        if actual_value != expected_value:
            message = f"Expected state[{key}] to be {expected_value}, got {actual_value}"
            self.signals.assertion_failed.emit("assert_state_value", message)
            raise AssertionError(message)
    
    def assert_render_count(self, expected_count: int):
        """Assert that component has rendered expected number of times."""
        if self.render_count != expected_count:
            message = f"Expected {expected_count} renders, got {self.render_count}"
            self.signals.assertion_failed.emit("assert_render_count", message)
            raise AssertionError(message)
    
    def assert_render_within_time(self, max_time_ms: int):
        """Assert that last render completed within time limit."""
        if self.last_render_time == 0:
            message = "No renders have occurred"
            self.signals.assertion_failed.emit("assert_render_within_time", message)
            raise AssertionError(message)
        
        elapsed_ms = (time.time() - self.last_render_time) * 1000
        if elapsed_ms > max_time_ms:
            message = f"Render took {elapsed_ms}ms, expected under {max_time_ms}ms"
            self.signals.assertion_failed.emit("assert_render_within_time", message)
            raise AssertionError(message)
    
    def reset_render_tracking(self):
        """Reset render tracking counters."""
        self.render_count = 0
        self.last_render_time = 0
    
    def cleanup(self):
        """Cleanup test instances."""
        for component in self.test_instances:
            if hasattr(component, 'deleteLater'):
                component.deleteLater()
        self.test_instances.clear()


class AsyncComponentTester:
    """Testing utilities for async reactive components."""
    
    def __init__(self, component_class: Type[AsyncMixin]):
        self.component_class = component_class
        self.signals = TestSignals()
        self.mock_state_manager = MockStateManager()
        self.async_operations = {}
        self.completed_operations = []
        self.failed_operations = []
    
    def create_test_component(self, *args, **kwargs) -> AsyncMixin:
        """Create a test instance of the async component."""
        component = self.component_class(*args, **kwargs)
        
        # Override state manager
        if hasattr(component, 'state_manager'):
            component.state_manager = self.mock_state_manager
        
        # Track async operations
        if hasattr(component, 'async_signals'):
            component.async_signals.operation_started.connect(self._on_operation_started)
            component.async_signals.operation_completed.connect(self._on_operation_completed)
            component.async_signals.operation_failed.connect(self._on_operation_failed)
        
        return component
    
    def _on_operation_started(self, operation_name: str):
        """Track operation start."""
        self.async_operations[operation_name] = {
            'started': time.time(),
            'completed': False,
            'failed': False
        }
    
    def _on_operation_completed(self, operation_name: str, result: Any):
        """Track operation completion."""
        if operation_name in self.async_operations:
            self.async_operations[operation_name]['completed'] = True
            self.async_operations[operation_name]['result'] = result
            self.async_operations[operation_name]['end_time'] = time.time()
            self.completed_operations.append(operation_name)
    
    def _on_operation_failed(self, operation_name: str, error: Exception):
        """Track operation failure."""
        if operation_name in self.async_operations:
            self.async_operations[operation_name]['failed'] = True
            self.async_operations[operation_name]['error'] = error
            self.async_operations[operation_name]['end_time'] = time.time()
            self.failed_operations.append(operation_name)
    
    async def wait_for_operation(self, operation_name: str, timeout_ms: int = 5000):
        """Wait for an async operation to complete."""
        start_time = time.time()
        
        while operation_name not in self.completed_operations and operation_name not in self.failed_operations:
            await asyncio.sleep(0.01)  # 10ms polling
            
            if (time.time() - start_time) * 1000 > timeout_ms:
                raise asyncio.TimeoutError(f"Operation {operation_name} timed out")
    
    def assert_operation_completed(self, operation_name: str):
        """Assert that an operation completed successfully."""
        if operation_name not in self.completed_operations:
            message = f"Operation {operation_name} did not complete"
            self.signals.assertion_failed.emit("assert_operation_completed", message)
            raise AssertionError(message)
    
    def assert_operation_failed(self, operation_name: str):
        """Assert that an operation failed."""
        if operation_name not in self.failed_operations:
            message = f"Operation {operation_name} did not fail"
            self.signals.assertion_failed.emit("assert_operation_failed", message)
            raise AssertionError(message)
    
    def get_operation_duration(self, operation_name: str) -> float:
        """Get the duration of an operation in seconds."""
        if operation_name not in self.async_operations:
            raise ValueError(f"Operation {operation_name} not found")
        
        op = self.async_operations[operation_name]
        if 'end_time' not in op:
            raise ValueError(f"Operation {operation_name} has not completed")
        
        return op['end_time'] - op['started']


class ErrorBoundaryTester:
    """Testing utilities for error boundaries."""
    
    def __init__(self, component: QWidget):
        self.component = component
        self.signals = TestSignals()
        self.caught_errors = []
        self.recovery_attempts = []
        self.fallback_renders = []
        
        # Setup error boundary if not exists
        if not hasattr(component, 'error_boundary'):
            component.error_boundary = ErrorBoundary(component)
        
        # Connect to error boundary signals
        component.error_boundary.signals.error_caught.connect(self._on_error_caught)
        component.error_boundary.signals.error_recovered.connect(self._on_error_recovered)
        component.error_boundary.signals.fallback_rendered.connect(self._on_fallback_rendered)
    
    def _on_error_caught(self, error):
        """Track caught errors."""
        self.caught_errors.append({
            'error': error,
            'timestamp': time.time()
        })
    
    def _on_error_recovered(self, component):
        """Track recovery attempts."""
        self.recovery_attempts.append({
            'component': component,
            'timestamp': time.time(),
            'success': True
        })
    
    def _on_fallback_rendered(self, component):
        """Track fallback renders."""
        self.fallback_renders.append({
            'component': component,
            'timestamp': time.time()
        })
    
    def trigger_error(self, error: Exception):
        """Trigger an error for testing."""
        self.component.error_boundary.handle_error(error)
    
    def assert_error_caught(self, error_type: Type[Exception] = None):
        """Assert that an error was caught."""
        if not self.caught_errors:
            message = "No errors were caught"
            self.signals.assertion_failed.emit("assert_error_caught", message)
            raise AssertionError(message)
        
        if error_type:
            found = any(isinstance(err['error'].original_error, error_type) for err in self.caught_errors)
            if not found:
                message = f"No error of type {error_type.__name__} was caught"
                self.signals.assertion_failed.emit("assert_error_caught", message)
                raise AssertionError(message)
    
    def assert_recovery_attempted(self):
        """Assert that recovery was attempted."""
        if not self.recovery_attempts:
            message = "No recovery attempts were made"
            self.signals.assertion_failed.emit("assert_recovery_attempted", message)
            raise AssertionError(message)
    
    def assert_fallback_rendered(self):
        """Assert that fallback UI was rendered."""
        if not self.fallback_renders:
            message = "No fallback UI was rendered"
            self.signals.assertion_failed.emit("assert_fallback_rendered", message)
            raise AssertionError(message)
    
    def reset_error_tracking(self):
        """Reset error tracking."""
        self.caught_errors.clear()
        self.recovery_attempts.clear()
        self.fallback_renders.clear()


class PerformanceTester:
    """Testing utilities for performance validation."""
    
    def __init__(self, component: QWidget):
        self.component = component
        self.signals = TestSignals()
        self.render_times = []
        self.memory_usage = []
        self.start_time = None
    
    def start_performance_monitoring(self):
        """Start monitoring performance."""
        self.start_time = time.time()
        self.render_times.clear()
        self.memory_usage.clear()
        
        # Track render times
        if hasattr(self.component, 'render'):
            original_render = self.component.render
            
            def timed_render(*args, **kwargs):
                start = time.time()
                result = original_render(*args, **kwargs)
                end = time.time()
                self.render_times.append((end - start) * 1000)  # Convert to ms
                return result
            
            self.component.render = timed_render
    
    def stop_performance_monitoring(self):
        """Stop monitoring performance."""
        self.start_time = None
    
    def assert_average_render_time(self, max_ms: float):
        """Assert that average render time is within limit."""
        if not self.render_times:
            message = "No render times recorded"
            self.signals.assertion_failed.emit("assert_average_render_time", message)
            raise AssertionError(message)
        
        avg_time = sum(self.render_times) / len(self.render_times)
        if avg_time > max_ms:
            message = f"Average render time {avg_time:.2f}ms exceeds limit {max_ms}ms"
            self.signals.assertion_failed.emit("assert_average_render_time", message)
            raise AssertionError(message)
    
    def assert_max_render_time(self, max_ms: float):
        """Assert that maximum render time is within limit."""
        if not self.render_times:
            message = "No render times recorded"
            self.signals.assertion_failed.emit("assert_max_render_time", message)
            raise AssertionError(message)
        
        max_time = max(self.render_times)
        if max_time > max_ms:
            message = f"Maximum render time {max_time:.2f}ms exceeds limit {max_ms}ms"
            self.signals.assertion_failed.emit("assert_max_render_time", message)
            raise AssertionError(message)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.render_times:
            return {'render_times': [], 'summary': 'No data'}
        
        return {
            'render_times': self.render_times,
            'average_render_time': sum(self.render_times) / len(self.render_times),
            'max_render_time': max(self.render_times),
            'min_render_time': min(self.render_times),
            'total_renders': len(self.render_times),
            'memory_usage': self.memory_usage
        }


class IntegrationTester:
    """Testing utilities for integration scenarios."""
    
    def __init__(self, container: ReactiveContainer):
        self.container = container
        self.signals = TestSignals()
        self.component_interactions = []
        self.state_propagations = []
    
    def add_test_component(self, component: QWidget, name: str = None) -> str:
        """Add a test component to the container."""
        component_name = self.container.add_component(component, name)
        
        # Track interactions
        if hasattr(component, 'signals'):
            component.signals.connect(lambda: self._track_interaction(component_name))
        
        return component_name
    
    def _track_interaction(self, component_name: str):
        """Track component interactions."""
        self.component_interactions.append({
            'component': component_name,
            'timestamp': time.time()
        })
    
    def trigger_state_propagation(self, state_key: str, value: Any):
        """Trigger state propagation for testing."""
        self.container.update_state(state_key, value)
        
        # Track propagation
        self.state_propagations.append({
            'state_key': state_key,
            'value': value,
            'timestamp': time.time()
        })
    
    def assert_state_propagated(self, state_key: str, expected_value: Any):
        """Assert that state was propagated correctly."""
        # Check if any component received the state
        found = False
        for component_name, component in self.container.child_components.items():
            if hasattr(component, 'state_manager'):
                actual_value = component.state_manager.get_state(state_key)
                if actual_value == expected_value:
                    found = True
                    break
        
        if not found:
            message = f"State {state_key} was not propagated with value {expected_value}"
            self.signals.assertion_failed.emit("assert_state_propagated", message)
            raise AssertionError(message)
    
    def assert_component_interaction(self, component_name: str):
        """Assert that a component had an interaction."""
        interactions = [i for i in self.component_interactions if i['component'] == component_name]
        if not interactions:
            message = f"Component {component_name} had no interactions"
            self.signals.assertion_failed.emit("assert_component_interaction", message)
            raise AssertionError(message)
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """Get interaction summary."""
        return {
            'total_interactions': len(self.component_interactions),
            'components_with_interactions': len(set(i['component'] for i in self.component_interactions)),
            'state_propagations': len(self.state_propagations),
            'interactions_by_component': {
                name: len([i for i in self.component_interactions if i['component'] == name])
                for name in self.container.child_components.keys()
            }
        }


@contextmanager
def test_component_context(component_class: Type[QWidget], *args, **kwargs):
    """Context manager for testing components."""
    tester = ComponentTester(component_class)
    component = tester.create_test_component(*args, **kwargs)
    
    try:
        yield component, tester
    finally:
        tester.cleanup()


@contextmanager
def test_async_component_context(component_class: Type[AsyncMixin], *args, **kwargs):
    """Context manager for testing async components."""
    tester = AsyncComponentTester(component_class)
    component = tester.create_test_component(*args, **kwargs)
    
    try:
        yield component, tester
    finally:
        if hasattr(component, 'cancel_all_operations'):
            component.cancel_all_operations()
        if hasattr(component, 'deleteLater'):
            component.deleteLater()


def mock_state_provider(initial_state: Dict[str, Any] = None) -> MockStateManager:
    """Create a mock state provider for testing."""
    mock_manager = MockStateManager()
    
    if initial_state:
        for key, value in initial_state.items():
            mock_manager.set_state(key, value)
    
    return mock_manager


def simulate_user_interaction(component: QWidget, interaction_type: str, *args, **kwargs):
    """Simulate user interactions for testing."""
    if interaction_type == 'click' and hasattr(component, 'click'):
        component.click()
    elif interaction_type == 'key_press':
        if args:
            QTest.keyClick(component, args[0])
    elif interaction_type == 'mouse_press':
        pos = kwargs.get('pos', component.rect().center())
        QTest.mouseClick(component, Qt.LeftButton, pos=pos)
    elif interaction_type == 'text_input':
        if args:
            QTest.keyClicks(component, args[0])
    else:
        raise ValueError(f"Unknown interaction type: {interaction_type}")


def create_test_suite(component_class: Type[QWidget]) -> Dict[str, Callable]:
    """Create a comprehensive test suite for a component."""
    return {
        'test_component_creation': lambda: test_component_creation(component_class),
        'test_state_updates': lambda: test_state_updates(component_class),
        'test_error_handling': lambda: test_error_handling(component_class),
        'test_performance': lambda: test_performance(component_class),
        'test_integration': lambda: test_integration(component_class)
    }


def test_component_creation(component_class: Type[QWidget]):
    """Test component creation."""
    with test_component_context(component_class) as (component, tester):
        assert component is not None
        assert isinstance(component, component_class)


def test_state_updates(component_class: Type[QWidget]):
    """Test state updates."""
    with test_component_context(component_class) as (component, tester):
        # Test state change
        tester.trigger_state_change('test_key', 'test_value')
        tester.assert_state_value('test_key', 'test_value')


def test_error_handling(component_class: Type[QWidget]):
    """Test error handling."""
    with test_component_context(component_class) as (component, tester):
        error_tester = ErrorBoundaryTester(component)
        
        # Trigger error
        test_error = ValueError("Test error")
        error_tester.trigger_error(test_error)
        
        # Assert error was caught
        error_tester.assert_error_caught(ValueError)


def test_performance(component_class: Type[QWidget]):
    """Test performance."""
    with test_component_context(component_class) as (component, tester):
        perf_tester = PerformanceTester(component)
        
        # Monitor performance
        perf_tester.start_performance_monitoring()
        
        # Simulate renders
        for i in range(10):
            tester.trigger_state_change(f'key_{i}', f'value_{i}')
        
        # Check performance
        perf_tester.assert_average_render_time(10.0)  # 10ms limit


def test_integration(component_class: Type[QWidget]):
    """Test integration scenarios."""
    container = ReactiveContainer()
    integration_tester = IntegrationTester(container)
    
    # Add test components
    component1 = component_class()
    component2 = component_class()
    
    name1 = integration_tester.add_test_component(component1, 'comp1')
    name2 = integration_tester.add_test_component(component2, 'comp2')
    
    # Test state propagation
    integration_tester.trigger_state_propagation('shared_state', 'shared_value')
    integration_tester.assert_state_propagated('shared_state', 'shared_value')