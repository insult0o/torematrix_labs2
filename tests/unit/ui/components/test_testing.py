"""
Tests for Testing Framework for Reactive Components.
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QEvent

from torematrix.ui.components.testing import (
    ComponentTester,
    AsyncComponentTester,
    ErrorBoundaryTester,
    PerformanceTester,
    IntegrationTester,
    MockStateManager,
    test_component_context,
    test_async_component_context,
    mock_state_provider,
    simulate_user_interaction,
    create_test_suite,
    test_component_creation,
    test_state_updates,
    test_error_handling,
    test_performance,
    test_integration
)
from torematrix.ui.components.reactive import ReactiveWidget
from torematrix.ui.components.mixins import AsyncMixin
from torematrix.ui.components.boundaries import ErrorBoundary
from torematrix.ui.components.integration import ReactiveContainer


class TestMockStateManager:
    """Test MockStateManager functionality."""
    
    def test_mock_state_manager_creation(self):
        """Test creating a MockStateManager."""
        manager = MockStateManager()
        
        assert manager.state == {}
        assert manager.subscriptions == {}
        assert manager.state_history == []
    
    def test_get_state(self):
        """Test getting state values."""
        manager = MockStateManager()
        
        # Test default value
        assert manager.get_state("nonexistent") is None
        assert manager.get_state("nonexistent", "default") == "default"
        
        # Test existing value
        manager.state["test_key"] = "test_value"
        assert manager.get_state("test_key") == "test_value"
    
    def test_set_state(self):
        """Test setting state values."""
        manager = MockStateManager()
        
        manager.set_state("test_key", "test_value")
        
        assert manager.state["test_key"] == "test_value"
        assert len(manager.state_history) == 1
        
        history_entry = manager.state_history[0]
        assert history_entry["key"] == "test_key"
        assert history_entry["old_value"] is None
        assert history_entry["new_value"] == "test_value"
        assert "timestamp" in history_entry
    
    def test_state_history(self):
        """Test state history tracking."""
        manager = MockStateManager()
        
        manager.set_state("key1", "value1")
        manager.set_state("key2", "value2")
        manager.set_state("key1", "updated_value1")
        
        history = manager.get_state_history()
        assert len(history) == 3
        
        # Check first entry
        assert history[0]["key"] == "key1"
        assert history[0]["old_value"] is None
        assert history[0]["new_value"] == "value1"
        
        # Check last entry
        assert history[2]["key"] == "key1"
        assert history[2]["old_value"] == "value1"
        assert history[2]["new_value"] == "updated_value1"
    
    def test_subscribe_unsubscribe(self):
        """Test subscription functionality."""
        manager = MockStateManager()
        callback = Mock()
        
        # Test subscribe
        manager.subscribe("test_key", callback)
        assert "test_key" in manager.subscriptions
        assert callback in manager.subscriptions["test_key"]
        
        # Test callback is called on state change
        manager.set_state("test_key", "test_value")
        callback.assert_called_once_with("test_value")
        
        # Test unsubscribe
        manager.unsubscribe("test_key", callback)
        assert callback not in manager.subscriptions["test_key"]
    
    def test_clear_state(self):
        """Test clearing state."""
        manager = MockStateManager()
        
        manager.set_state("key1", "value1")
        manager.set_state("key2", "value2")
        
        assert len(manager.state) == 2
        assert len(manager.state_history) == 2
        
        manager.clear_state()
        
        assert len(manager.state) == 0
        assert len(manager.state_history) == 0


class TestComponentTester:
    """Test ComponentTester functionality."""
    
    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.render_called = False
        
        def render(self):
            self.render_called = True
            return "rendered"
    
    def test_component_tester_creation(self):
        """Test creating a ComponentTester."""
        tester = ComponentTester(self.TestWidget)
        
        assert tester.component_class == self.TestWidget
        assert tester.signals is not None
        assert isinstance(tester.mock_state_manager, MockStateManager)
        assert tester.test_instances == []
        assert tester.render_count == 0
        assert tester.last_render_time == 0
    
    def test_create_test_component(self):
        """Test creating a test component."""
        tester = ComponentTester(self.TestWidget)
        
        with patch.object(self.TestWidget, 'state_manager', tester.mock_state_manager):
            component = tester.create_test_component()
        
        assert isinstance(component, self.TestWidget)
        assert component in tester.test_instances
        assert hasattr(component, 'state_manager')
    
    def test_render_tracking(self):
        """Test render tracking."""
        tester = ComponentTester(self.TestWidget)
        
        component = tester.create_test_component()
        
        # Test render tracking
        assert tester.render_count == 0
        component.render()
        assert tester.render_count == 1
        assert tester.last_render_time > 0
    
    def test_trigger_state_change(self):
        """Test triggering state changes."""
        tester = ComponentTester(self.TestWidget)
        
        tester.trigger_state_change("test_key", "test_value")
        
        assert tester.mock_state_manager.get_state("test_key") == "test_value"
    
    def test_assert_state_value(self):
        """Test asserting state values."""
        tester = ComponentTester(self.TestWidget)
        
        tester.mock_state_manager.set_state("test_key", "test_value")
        
        # Should not raise
        tester.assert_state_value("test_key", "test_value")
        
        # Should raise
        with pytest.raises(AssertionError):
            tester.assert_state_value("test_key", "wrong_value")
    
    def test_assert_render_count(self):
        """Test asserting render count."""
        tester = ComponentTester(self.TestWidget)
        component = tester.create_test_component()
        
        # Should not raise
        tester.assert_render_count(0)
        
        component.render()
        tester.assert_render_count(1)
        
        # Should raise
        with pytest.raises(AssertionError):
            tester.assert_render_count(2)
    
    def test_assert_render_within_time(self):
        """Test asserting render time."""
        tester = ComponentTester(self.TestWidget)
        component = tester.create_test_component()
        
        # Should raise - no renders
        with pytest.raises(AssertionError):
            tester.assert_render_within_time(100)
        
        # Render and test
        component.render()
        tester.assert_render_within_time(1000)  # 1 second should be enough
    
    def test_reset_render_tracking(self):
        """Test resetting render tracking."""
        tester = ComponentTester(self.TestWidget)
        component = tester.create_test_component()
        
        component.render()
        assert tester.render_count == 1
        assert tester.last_render_time > 0
        
        tester.reset_render_tracking()
        assert tester.render_count == 0
        assert tester.last_render_time == 0
    
    def test_cleanup(self):
        """Test cleanup."""
        tester = ComponentTester(self.TestWidget)
        
        # Create mock component with deleteLater
        component = Mock()
        component.deleteLater = Mock()
        tester.test_instances.append(component)
        
        tester.cleanup()
        
        component.deleteLater.assert_called_once()
        assert tester.test_instances == []


class TestAsyncComponentTester:
    """Test AsyncComponentTester functionality."""
    
    class TestAsyncComponent(AsyncMixin, QWidget):
        def __init__(self):
            super().__init__()
    
    def test_async_component_tester_creation(self):
        """Test creating an AsyncComponentTester."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        assert tester.component_class == self.TestAsyncComponent
        assert tester.signals is not None
        assert isinstance(tester.mock_state_manager, MockStateManager)
        assert tester.async_operations == {}
        assert tester.completed_operations == []
        assert tester.failed_operations == []
    
    def test_create_test_component(self):
        """Test creating a test async component."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        component = tester.create_test_component()
        
        assert isinstance(component, self.TestAsyncComponent)
        assert hasattr(component, 'state_manager')
        assert component.state_manager == tester.mock_state_manager
    
    def test_operation_tracking(self):
        """Test operation tracking."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        # Test operation started
        tester._on_operation_started("test_operation")
        
        assert "test_operation" in tester.async_operations
        operation = tester.async_operations["test_operation"]
        assert operation["started"] > 0
        assert not operation["completed"]
        assert not operation["failed"]
        
        # Test operation completed
        tester._on_operation_completed("test_operation", "result")
        
        assert operation["completed"]
        assert operation["result"] == "result"
        assert "end_time" in operation
        assert "test_operation" in tester.completed_operations
        
        # Test operation failed
        tester._on_operation_started("failed_operation")
        test_error = ValueError("Test error")
        tester._on_operation_failed("failed_operation", test_error)
        
        failed_op = tester.async_operations["failed_operation"]
        assert failed_op["failed"]
        assert failed_op["error"] == test_error
        assert "failed_operation" in tester.failed_operations
    
    def test_assert_operation_completed(self):
        """Test asserting operation completion."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        tester.completed_operations.append("test_operation")
        
        # Should not raise
        tester.assert_operation_completed("test_operation")
        
        # Should raise
        with pytest.raises(AssertionError):
            tester.assert_operation_completed("nonexistent_operation")
    
    def test_assert_operation_failed(self):
        """Test asserting operation failure."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        tester.failed_operations.append("test_operation")
        
        # Should not raise
        tester.assert_operation_failed("test_operation")
        
        # Should raise
        with pytest.raises(AssertionError):
            tester.assert_operation_failed("nonexistent_operation")
    
    def test_get_operation_duration(self):
        """Test getting operation duration."""
        tester = AsyncComponentTester(self.TestAsyncComponent)
        
        # Test nonexistent operation
        with pytest.raises(ValueError):
            tester.get_operation_duration("nonexistent")
        
        # Test incomplete operation
        tester.async_operations["incomplete"] = {"started": time.time()}
        with pytest.raises(ValueError):
            tester.get_operation_duration("incomplete")
        
        # Test completed operation
        start_time = time.time()
        end_time = start_time + 1.0
        tester.async_operations["completed"] = {
            "started": start_time,
            "end_time": end_time
        }
        
        duration = tester.get_operation_duration("completed")
        assert duration == 1.0


class TestErrorBoundaryTester:
    """Test ErrorBoundaryTester functionality."""
    
    def test_error_boundary_tester_creation(self):
        """Test creating an ErrorBoundaryTester."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        assert tester.component == component
        assert tester.signals is not None
        assert tester.caught_errors == []
        assert tester.recovery_attempts == []
        assert tester.fallback_renders == []
        assert hasattr(component, 'error_boundary')
        assert isinstance(component.error_boundary, ErrorBoundary)
    
    def test_error_tracking(self):
        """Test error tracking."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Create mock error
        error = Mock()
        error.original_error = ValueError("Test error")
        
        # Test error caught
        tester._on_error_caught(error)
        
        assert len(tester.caught_errors) == 1
        assert tester.caught_errors[0]["error"] == error
        assert "timestamp" in tester.caught_errors[0]
        
        # Test error recovered
        tester._on_error_recovered(component)
        
        assert len(tester.recovery_attempts) == 1
        assert tester.recovery_attempts[0]["component"] == component
        assert tester.recovery_attempts[0]["success"] is True
        
        # Test fallback rendered
        tester._on_fallback_rendered(component)
        
        assert len(tester.fallback_renders) == 1
        assert tester.fallback_renders[0]["component"] == component
    
    def test_trigger_error(self):
        """Test triggering errors."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Mock the error boundary
        component.error_boundary = Mock()
        component.error_boundary.handle_error = Mock()
        
        test_error = ValueError("Test error")
        tester.trigger_error(test_error)
        
        component.error_boundary.handle_error.assert_called_once_with(test_error)
    
    def test_assert_error_caught(self):
        """Test asserting error caught."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Should raise - no errors
        with pytest.raises(AssertionError):
            tester.assert_error_caught()
        
        # Add error
        error = Mock()
        error.original_error = ValueError("Test error")
        tester.caught_errors.append({"error": error})
        
        # Should not raise
        tester.assert_error_caught()
        
        # Test specific error type
        tester.assert_error_caught(ValueError)
        
        # Should raise - wrong error type
        with pytest.raises(AssertionError):
            tester.assert_error_caught(TypeError)
    
    def test_assert_recovery_attempted(self):
        """Test asserting recovery attempted."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Should raise - no recovery attempts
        with pytest.raises(AssertionError):
            tester.assert_recovery_attempted()
        
        # Add recovery attempt
        tester.recovery_attempts.append({"component": component})
        
        # Should not raise
        tester.assert_recovery_attempted()
    
    def test_assert_fallback_rendered(self):
        """Test asserting fallback rendered."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Should raise - no fallback renders
        with pytest.raises(AssertionError):
            tester.assert_fallback_rendered()
        
        # Add fallback render
        tester.fallback_renders.append({"component": component})
        
        # Should not raise
        tester.assert_fallback_rendered()
    
    def test_reset_error_tracking(self):
        """Test resetting error tracking."""
        component = QWidget()
        tester = ErrorBoundaryTester(component)
        
        # Add some data
        tester.caught_errors.append({"error": Mock()})
        tester.recovery_attempts.append({"component": component})
        tester.fallback_renders.append({"component": component})
        
        tester.reset_error_tracking()
        
        assert tester.caught_errors == []
        assert tester.recovery_attempts == []
        assert tester.fallback_renders == []


class TestPerformanceTester:
    """Test PerformanceTester functionality."""
    
    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
        
        def render(self):
            time.sleep(0.001)  # Simulate some work
            return "rendered"
    
    def test_performance_tester_creation(self):
        """Test creating a PerformanceTester."""
        component = self.TestWidget()
        tester = PerformanceTester(component)
        
        assert tester.component == component
        assert tester.signals is not None
        assert tester.render_times == []
        assert tester.memory_usage == []
        assert tester.start_time is None
    
    def test_performance_monitoring(self):
        """Test performance monitoring."""
        component = self.TestWidget()
        tester = PerformanceTester(component)
        
        # Start monitoring
        tester.start_performance_monitoring()
        
        assert tester.start_time is not None
        assert tester.render_times == []
        
        # Call render multiple times
        component.render()
        component.render()
        component.render()
        
        assert len(tester.render_times) == 3
        assert all(t > 0 for t in tester.render_times)
        
        # Stop monitoring
        tester.stop_performance_monitoring()
        assert tester.start_time is None
    
    def test_assert_average_render_time(self):
        """Test asserting average render time."""
        component = self.TestWidget()
        tester = PerformanceTester(component)
        
        # Should raise - no render times
        with pytest.raises(AssertionError):
            tester.assert_average_render_time(10.0)
        
        # Add render times
        tester.render_times = [5.0, 10.0, 15.0]  # Average: 10.0
        
        # Should not raise
        tester.assert_average_render_time(10.0)
        
        # Should raise - exceeds limit
        with pytest.raises(AssertionError):
            tester.assert_average_render_time(5.0)
    
    def test_assert_max_render_time(self):
        """Test asserting maximum render time."""
        component = self.TestWidget()
        tester = PerformanceTester(component)
        
        # Should raise - no render times
        with pytest.raises(AssertionError):
            tester.assert_max_render_time(10.0)
        
        # Add render times
        tester.render_times = [5.0, 15.0, 10.0]  # Max: 15.0
        
        # Should not raise
        tester.assert_max_render_time(15.0)
        
        # Should raise - exceeds limit
        with pytest.raises(AssertionError):
            tester.assert_max_render_time(10.0)
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        component = self.TestWidget()
        tester = PerformanceTester(component)
        
        # Test empty summary
        summary = tester.get_performance_summary()
        assert summary["render_times"] == []
        assert summary["summary"] == "No data"
        
        # Add render times
        tester.render_times = [5.0, 10.0, 15.0]
        summary = tester.get_performance_summary()
        
        assert summary["render_times"] == [5.0, 10.0, 15.0]
        assert summary["average_render_time"] == 10.0
        assert summary["max_render_time"] == 15.0
        assert summary["min_render_time"] == 5.0
        assert summary["total_renders"] == 3


class TestIntegrationTester:
    """Test IntegrationTester functionality."""
    
    def test_integration_tester_creation(self):
        """Test creating an IntegrationTester."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        assert tester.container == container
        assert tester.signals is not None
        assert tester.component_interactions == []
        assert tester.state_propagations == []
    
    def test_add_test_component(self):
        """Test adding test components."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        widget = QWidget()
        name = tester.add_test_component(widget, "test_widget")
        
        assert name == "test_widget"
        assert container.get_component("test_widget") == widget
    
    def test_trigger_state_propagation(self):
        """Test triggering state propagation."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        # Mock container update_state
        container.update_state = Mock()
        
        tester.trigger_state_propagation("test_key", "test_value")
        
        container.update_state.assert_called_once_with("test_key", "test_value")
        assert len(tester.state_propagations) == 1
        
        propagation = tester.state_propagations[0]
        assert propagation["state_key"] == "test_key"
        assert propagation["value"] == "test_value"
        assert "timestamp" in propagation
    
    def test_assert_state_propagated(self):
        """Test asserting state propagation."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        # Add component with state manager
        widget = QWidget()
        widget.state_manager = Mock()
        widget.state_manager.get_state = Mock(return_value="test_value")
        
        tester.add_test_component(widget, "test_widget")
        
        # Should not raise
        tester.assert_state_propagated("test_key", "test_value")
        
        # Should raise - wrong value
        with pytest.raises(AssertionError):
            tester.assert_state_propagated("test_key", "wrong_value")
    
    def test_assert_component_interaction(self):
        """Test asserting component interaction."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        # Should raise - no interactions
        with pytest.raises(AssertionError):
            tester.assert_component_interaction("test_widget")
        
        # Add interaction
        tester.component_interactions.append({"component": "test_widget"})
        
        # Should not raise
        tester.assert_component_interaction("test_widget")
    
    def test_get_interaction_summary(self):
        """Test getting interaction summary."""
        container = ReactiveContainer()
        tester = IntegrationTester(container)
        
        # Add some test data
        tester.component_interactions = [
            {"component": "widget1"},
            {"component": "widget2"},
            {"component": "widget1"}
        ]
        tester.state_propagations = [
            {"state_key": "key1", "value": "value1"},
            {"state_key": "key2", "value": "value2"}
        ]
        
        # Add components to container
        container.child_components = {"widget1": QWidget(), "widget2": QWidget()}
        
        summary = tester.get_interaction_summary()
        
        assert summary["total_interactions"] == 3
        assert summary["components_with_interactions"] == 2
        assert summary["state_propagations"] == 2
        assert summary["interactions_by_component"]["widget1"] == 2
        assert summary["interactions_by_component"]["widget2"] == 1


class TestContextManagers:
    """Test context managers."""
    
    def test_test_component_context(self):
        """Test test_component_context."""
        class TestWidget(QWidget):
            pass
        
        with test_component_context(TestWidget) as (component, tester):
            assert isinstance(component, TestWidget)
            assert isinstance(tester, ComponentTester)
            assert component in tester.test_instances
    
    def test_test_async_component_context(self):
        """Test test_async_component_context."""
        class TestAsyncWidget(AsyncMixin, QWidget):
            pass
        
        with test_async_component_context(TestAsyncWidget) as (component, tester):
            assert isinstance(component, TestAsyncWidget)
            assert isinstance(tester, AsyncComponentTester)


class TestMockStateProvider:
    """Test mock_state_provider function."""
    
    def test_mock_state_provider_empty(self):
        """Test creating empty mock state provider."""
        provider = mock_state_provider()
        
        assert isinstance(provider, MockStateManager)
        assert provider.state == {}
    
    def test_mock_state_provider_with_initial_state(self):
        """Test creating mock state provider with initial state."""
        initial_state = {"key1": "value1", "key2": "value2"}
        provider = mock_state_provider(initial_state)
        
        assert isinstance(provider, MockStateManager)
        assert provider.get_state("key1") == "value1"
        assert provider.get_state("key2") == "value2"


class TestSimulateUserInteraction:
    """Test simulate_user_interaction function."""
    
    def test_simulate_click(self):
        """Test simulating click interaction."""
        widget = Mock()
        widget.click = Mock()
        
        simulate_user_interaction(widget, "click")
        
        widget.click.assert_called_once()
    
    def test_simulate_unknown_interaction(self):
        """Test simulating unknown interaction."""
        widget = QWidget()
        
        with pytest.raises(ValueError):
            simulate_user_interaction(widget, "unknown_interaction")


class TestCreateTestSuite:
    """Test create_test_suite function."""
    
    def test_create_test_suite(self):
        """Test creating test suite."""
        class TestWidget(QWidget):
            pass
        
        suite = create_test_suite(TestWidget)
        
        assert isinstance(suite, dict)
        assert "test_component_creation" in suite
        assert "test_state_updates" in suite
        assert "test_error_handling" in suite
        assert "test_performance" in suite
        assert "test_integration" in suite
        
        # Test that all values are callable
        for test_name, test_func in suite.items():
            assert callable(test_func)


class TestTestFunctions:
    """Test individual test functions."""
    
    def test_test_component_creation(self):
        """Test test_component_creation function."""
        class TestWidget(QWidget):
            pass
        
        # Should not raise
        test_component_creation(TestWidget)
    
    def test_test_state_updates(self):
        """Test test_state_updates function."""
        class TestWidget(QWidget):
            pass
        
        # Should not raise
        test_state_updates(TestWidget)
    
    def test_test_error_handling(self):
        """Test test_error_handling function."""
        class TestWidget(QWidget):
            pass
        
        # Should not raise
        test_error_handling(TestWidget)
    
    def test_test_performance(self):
        """Test test_performance function."""
        class TestWidget(QWidget):
            def render(self):
                return "rendered"
        
        # Should not raise
        test_performance(TestWidget)
    
    def test_test_integration(self):
        """Test test_integration function."""
        class TestWidget(QWidget):
            pass
        
        # Should not raise
        test_integration(TestWidget)


@pytest.fixture
def mock_qt_app():
    """Mock Qt application for testing."""
    with patch('PyQt6.QtWidgets.QApplication.instance'):
        yield


@pytest.fixture
def test_widget():
    """Create test widget."""
    return QWidget()


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    return MockStateManager()


def test_testing_framework_integration(mock_qt_app, test_widget, mock_state_manager):
    """Test testing framework integration."""
    # Test component tester
    tester = ComponentTester(QWidget)
    component = tester.create_test_component()
    
    assert isinstance(component, QWidget)
    assert component.state_manager == tester.mock_state_manager
    
    # Test state changes
    tester.trigger_state_change("test_key", "test_value")
    tester.assert_state_value("test_key", "test_value")
    
    # Test error boundary tester
    error_tester = ErrorBoundaryTester(component)
    assert hasattr(component, 'error_boundary')
    
    # Test performance tester
    perf_tester = PerformanceTester(component)
    assert perf_tester.component == component
    
    # Cleanup
    tester.cleanup()


def test_full_testing_workflow(mock_qt_app):
    """Test full testing workflow."""
    class TestReactiveWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.render_count = 0
        
        def render(self):
            self.render_count += 1
            return f"rendered_{self.render_count}"
    
    # Use context manager
    with test_component_context(TestReactiveWidget) as (component, tester):
        # Test component creation
        assert isinstance(component, TestReactiveWidget)
        assert component.render_count == 0
        
        # Test state updates
        tester.trigger_state_change("test_state", "test_value")
        tester.assert_state_value("test_state", "test_value")
        
        # Test rendering
        component.render()
        tester.assert_render_count(1)
        
        # Test error handling
        error_tester = ErrorBoundaryTester(component)
        test_error = ValueError("Test error")
        error_tester.trigger_error(test_error)
        
        # Test performance
        perf_tester = PerformanceTester(component)
        perf_tester.start_performance_monitoring()
        
        # Render multiple times
        for i in range(5):
            component.render()
        
        # Check performance
        assert len(perf_tester.render_times) == 5
        summary = perf_tester.get_performance_summary()
        assert summary["total_renders"] == 5
        assert summary["average_render_time"] > 0