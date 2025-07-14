"""
Tests for UI Integration Utilities.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import QEvent

from torematrix.ui.components.integration import (
    ReactiveContainer,
    ReactiveWrapper,
    MainWindowIntegration,
    LayoutIntegration,
    MigrationHelper,
    AsyncIntegration,
    reactive_integration,
    get_global_integration,
    set_global_integration
)
from torematrix.ui.components.reactive import ReactiveWidget
from torematrix.ui.components.boundaries import ErrorBoundary


class TestReactiveContainer:
    """Test ReactiveContainer functionality."""
    
    def test_reactive_container_creation(self):
        """Test creating a ReactiveContainer."""
        container = ReactiveContainer()
        
        assert container.signals is not None
        assert container.child_components == {}
        assert container.reactive_wrappers == {}
        assert container.state_bindings == {}
        assert container.monitor is not None
        assert container.state_manager is not None
        assert isinstance(container.error_boundary, ErrorBoundary)
        assert container.main_layout is not None
    
    def test_add_component(self):
        """Test adding components to container."""
        container = ReactiveContainer()
        widget = QWidget()
        
        name = container.add_component(widget, "test_widget")
        
        assert name == "test_widget"
        assert container.child_components["test_widget"] == widget
        assert container.main_layout.count() == 1
        assert container.main_layout.itemAt(0).widget() == widget
    
    def test_add_component_auto_name(self):
        """Test adding component with auto-generated name."""
        container = ReactiveContainer()
        widget = QWidget()
        
        name = container.add_component(widget)
        
        assert name == "component_0"
        assert container.child_components["component_0"] == widget
    
    def test_add_component_reactive_wrapper(self):
        """Test adding component with reactive wrapper."""
        container = ReactiveContainer()
        widget = QWidget()
        
        container.add_component(widget, "test_widget", reactive=True)
        
        assert widget in container.reactive_wrappers
        assert isinstance(container.reactive_wrappers[widget], ReactiveWrapper)
    
    def test_add_component_no_reactive_wrapper(self):
        """Test adding component without reactive wrapper."""
        container = ReactiveContainer()
        widget = QWidget()
        
        container.add_component(widget, "test_widget", reactive=False)
        
        assert widget not in container.reactive_wrappers
    
    def test_remove_component(self):
        """Test removing components from container."""
        container = ReactiveContainer()
        widget = QWidget()
        
        container.add_component(widget, "test_widget")
        assert "test_widget" in container.child_components
        
        container.remove_component("test_widget")
        assert "test_widget" not in container.child_components
        assert container.main_layout.count() == 0
    
    def test_get_component(self):
        """Test getting components from container."""
        container = ReactiveContainer()
        widget = QWidget()
        
        container.add_component(widget, "test_widget")
        
        retrieved = container.get_component("test_widget")
        assert retrieved == widget
        
        not_found = container.get_component("nonexistent")
        assert not_found is None
    
    def test_bind_state(self):
        """Test binding state to components."""
        container = ReactiveContainer()
        callback = Mock()
        
        container.bind_state("test_component", "test_state", callback)
        
        assert "test_state" in container.state_bindings
        assert callback in container.state_bindings["test_state"]
    
    def test_update_state(self):
        """Test updating state."""
        container = ReactiveContainer()
        
        # Mock the state manager
        container.state_manager = Mock()
        container.state_manager.set_state = Mock()
        
        container.update_state("test_key", "test_value")
        
        container.state_manager.set_state.assert_called_once_with("test_key", "test_value")


class TestReactiveWrapper:
    """Test ReactiveWrapper functionality."""
    
    def test_reactive_wrapper_creation(self):
        """Test creating a ReactiveWrapper."""
        widget = QWidget()
        wrapper = ReactiveWrapper(widget)
        
        assert wrapper.widget == widget
        assert wrapper.signals is not None
        assert wrapper.state_subscriptions == {}
        assert wrapper.property_bindings == {}
        assert wrapper.event_handlers == {}
        assert wrapper.monitor is not None
        assert isinstance(wrapper.error_boundary, ErrorBoundary)
        assert wrapper.state_manager is not None
    
    def test_bind_property(self):
        """Test binding properties to state."""
        widget = QLabel()
        wrapper = ReactiveWrapper(widget)
        
        # Mock the state manager
        wrapper.state_manager = Mock()
        wrapper.state_manager.subscribe = Mock()
        
        wrapper.bind_property("text", "text_state")
        
        assert wrapper.property_bindings["text"] == "text_state"
        wrapper.state_manager.subscribe.assert_called_once()
    
    def test_update_property_text(self):
        """Test updating text property."""
        widget = QLabel()
        wrapper = ReactiveWrapper(widget)
        
        wrapper._update_property("text", "new_text")
        
        assert widget.text() == "new_text"
    
    def test_update_property_visible(self):
        """Test updating visible property."""
        widget = QWidget()
        wrapper = ReactiveWrapper(widget)
        
        wrapper._update_property("visible", False)
        
        assert not widget.isVisible()
    
    def test_update_property_enabled(self):
        """Test updating enabled property."""
        widget = QWidget()
        wrapper = ReactiveWrapper(widget)
        
        wrapper._update_property("enabled", False)
        
        assert not widget.isEnabled()
    
    def test_add_event_handler(self):
        """Test adding event handlers."""
        widget = QWidget()
        wrapper = ReactiveWrapper(widget)
        handler = Mock()
        
        wrapper.add_event_handler(QEvent.Type.MouseButtonPress, handler)
        
        assert QEvent.Type.MouseButtonPress in wrapper.event_handlers
        assert wrapper.event_handlers[QEvent.Type.MouseButtonPress] == handler
    
    def test_cleanup(self):
        """Test wrapper cleanup."""
        widget = QWidget()
        wrapper = ReactiveWrapper(widget)
        
        # Add some test data
        wrapper.state_subscriptions["test"] = [Mock()]
        wrapper.property_bindings["test"] = "test_state"
        wrapper.event_handlers[QEvent.Type.MouseButtonPress] = Mock()
        
        # Mock the state manager
        wrapper.state_manager = Mock()
        wrapper.state_manager.unsubscribe = Mock()
        
        wrapper.cleanup()
        
        assert wrapper.state_subscriptions == {}
        assert wrapper.property_bindings == {}
        assert wrapper.event_handlers == {}
        wrapper.state_manager.unsubscribe.assert_called_once()


class TestMainWindowIntegration:
    """Test MainWindowIntegration functionality."""
    
    def test_main_window_integration_creation(self):
        """Test creating MainWindowIntegration."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        
        assert integration.main_window == main_window
        assert integration.signals is not None
        assert integration.reactive_areas == {}
        assert integration.menu_integrations == {}
        assert integration.toolbar_integrations == {}
        assert integration.status_bar_integrations == {}
        assert integration.monitor is not None
        assert integration.state_manager is not None
    
    def test_create_reactive_area(self):
        """Test creating reactive areas."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        
        container = integration.create_reactive_area("test_area")
        
        assert isinstance(container, ReactiveContainer)
        assert integration.reactive_areas["test_area"] == container
    
    def test_get_reactive_area(self):
        """Test getting reactive areas."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        
        container = integration.create_reactive_area("test_area")
        retrieved = integration.get_reactive_area("test_area")
        
        assert retrieved == container
        
        not_found = integration.get_reactive_area("nonexistent")
        assert not_found is None
    
    def test_integrate_menu_action(self):
        """Test integrating menu actions."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        callback = Mock()
        
        integration.integrate_menu_action("Test Action", callback)
        
        assert integration.menu_integrations["Test Action"] == callback
    
    def test_integrate_toolbar_action(self):
        """Test integrating toolbar actions."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        callback = Mock()
        
        integration.integrate_toolbar_action("Test Action", callback)
        
        assert integration.toolbar_integrations["Test Action"] == callback
    
    def test_integrate_status_bar(self):
        """Test integrating status bar."""
        main_window = QMainWindow()
        main_window.statusBar()  # Create status bar
        integration = MainWindowIntegration(main_window)
        callback = Mock()
        
        integration.integrate_status_bar(callback)
        
        assert integration.status_bar_integrations["default"] == callback
    
    def test_broadcast_state_change(self):
        """Test broadcasting state changes."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        
        # Mock the state manager
        integration.state_manager = Mock()
        integration.state_manager.set_state = Mock()
        
        # Create a reactive area
        container = integration.create_reactive_area("test_area")
        container.update_state = Mock()
        
        integration.broadcast_state_change("test_key", "test_value")
        
        integration.state_manager.set_state.assert_called_once_with("test_key", "test_value")
        container.update_state.assert_called_once_with("test_key", "test_value")


class TestLayoutIntegration:
    """Test LayoutIntegration functionality."""
    
    def test_convert_layout_to_reactive(self):
        """Test converting layout to reactive."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        child1 = QLabel("Child 1")
        child2 = QLabel("Child 2")
        layout.addWidget(child1)
        layout.addWidget(child2)
        
        container = LayoutIntegration.convert_layout_to_reactive(widget)
        
        assert isinstance(container, ReactiveContainer)
        assert len(container.child_components) == 2
    
    def test_create_responsive_layout(self):
        """Test creating responsive layout."""
        components = [QLabel("Label 1"), QLabel("Label 2"), QLabel("Label 3")]
        
        layout_widget = LayoutIntegration.create_responsive_layout(components)
        
        assert isinstance(layout_widget, QWidget)
        assert layout_widget.layout() is not None
        assert layout_widget.layout().count() == 3


class TestMigrationHelper:
    """Test MigrationHelper functionality."""
    
    def test_migrate_widget_to_reactive(self):
        """Test migrating widget to reactive."""
        widget = QWidget()
        widget.setObjectName("test_widget")
        widget.setVisible(True)
        widget.setEnabled(True)
        
        with patch('torematrix.ui.components.integration.ReactiveWidget') as mock_reactive:
            mock_reactive.return_value = Mock()
            
            reactive_widget = MigrationHelper.migrate_widget_to_reactive(widget)
            
            assert reactive_widget is not None
            mock_reactive.assert_called_once_with(widget.parent())
    
    def test_is_reactive_candidate(self):
        """Test checking if widget is reactive candidate."""
        # Widget with state
        widget_with_state = QWidget()
        widget_with_state.state = {}
        assert MigrationHelper._is_reactive_candidate(widget_with_state)
        
        # Widget with data
        widget_with_data = QWidget()
        widget_with_data.data = {}
        assert MigrationHelper._is_reactive_candidate(widget_with_data)
        
        # Widget with many children
        widget_with_children = QWidget()
        for i in range(6):
            child = QWidget(widget_with_children)
        assert MigrationHelper._is_reactive_candidate(widget_with_children)
        
        # Custom widget
        class CustomWidget(QWidget):
            pass
        custom_widget = CustomWidget()
        assert MigrationHelper._is_reactive_candidate(custom_widget)
        
        # Simple widget
        simple_widget = QWidget()
        assert not MigrationHelper._is_reactive_candidate(simple_widget)
    
    def test_create_migration_plan(self):
        """Test creating migration plan."""
        root_widget = QWidget()
        child1 = QWidget(root_widget)
        child1.state = {}  # Make it a reactive candidate
        child2 = QWidget(root_widget)
        
        plan = MigrationHelper.create_migration_plan(root_widget)
        
        assert isinstance(plan, dict)
        assert 'widgets_to_migrate' in plan
        assert 'reactive_candidates' in plan
        assert 'integration_points' in plan
        assert 'estimated_effort' in plan
        assert plan['estimated_effort'] > 0


class TestAsyncIntegration:
    """Test AsyncIntegration functionality."""
    
    def test_async_integration_creation(self):
        """Test creating AsyncIntegration."""
        main_window = QMainWindow()
        integration = AsyncIntegration(main_window)
        
        assert integration.main_window == main_window
        assert integration.async_components == {}
        assert not integration.global_loading_state
        assert integration.monitor is not None
    
    def test_register_async_component(self):
        """Test registering async component."""
        main_window = QMainWindow()
        integration = AsyncIntegration(main_window)
        
        component = Mock()
        component.async_signals = Mock()
        component.async_signals.operation_started = Mock()
        component.async_signals.operation_started.connect = Mock()
        component.async_signals.operation_completed = Mock()
        component.async_signals.operation_completed.connect = Mock()
        component.async_signals.operation_failed = Mock()
        component.async_signals.operation_failed.connect = Mock()
        
        integration.register_async_component("test_component", component)
        
        assert integration.async_components["test_component"] == component
        # Verify signal connections
        component.async_signals.operation_started.connect.assert_called_once()
        component.async_signals.operation_completed.connect.assert_called_once()
        component.async_signals.operation_failed.connect.assert_called_once()
    
    def test_update_global_loading_state(self):
        """Test updating global loading state."""
        main_window = QMainWindow()
        integration = AsyncIntegration(main_window)
        
        # Mock the main window update method
        integration._update_main_window_loading_state = Mock()
        
        # Add mock component
        component = Mock()
        component.is_loading = Mock(return_value=True)
        integration.async_components["test_component"] = component
        
        integration._update_global_loading_state()
        
        assert integration.global_loading_state is True
        integration._update_main_window_loading_state.assert_called_once_with(True)
    
    def test_cancel_all_operations(self):
        """Test canceling all operations."""
        main_window = QMainWindow()
        integration = AsyncIntegration(main_window)
        
        # Add mock components
        component1 = Mock()
        component1.cancel_all_operations = Mock()
        component2 = Mock()
        component2.cancel_all_operations = Mock()
        
        integration.async_components["comp1"] = component1
        integration.async_components["comp2"] = component2
        
        integration.cancel_all_operations()
        
        component1.cancel_all_operations.assert_called_once()
        component2.cancel_all_operations.assert_called_once()


class TestReactiveIntegrationDecorator:
    """Test reactive_integration decorator."""
    
    def test_reactive_integration_decorator(self):
        """Test applying reactive_integration decorator."""
        @reactive_integration(auto_migrate=True)
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        
        assert hasattr(widget, 'reactive_wrapper')
        assert hasattr(widget, 'integration_signals')
        assert isinstance(widget.reactive_wrapper, ReactiveWrapper)
    
    def test_reactive_integration_no_auto_migrate(self):
        """Test reactive_integration decorator without auto-migration."""
        @reactive_integration(auto_migrate=False)
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        
        assert hasattr(widget, 'reactive_wrapper')
        assert hasattr(widget, 'integration_signals')
        # Should not have auto-migration features
        assert not hasattr(widget, 'error_boundary')


class TestGlobalIntegration:
    """Test global integration functionality."""
    
    def test_set_get_global_integration(self):
        """Test setting and getting global integration."""
        main_window = QMainWindow()
        integration = MainWindowIntegration(main_window)
        
        set_global_integration(integration)
        retrieved = get_global_integration()
        
        assert retrieved == integration
    
    def test_get_global_integration_none(self):
        """Test getting global integration when none is set."""
        # Reset global integration
        set_global_integration(None)
        
        retrieved = get_global_integration()
        assert retrieved is None


@pytest.fixture
def mock_qt_app():
    """Mock Qt application for testing."""
    with patch('PyQt6.QtWidgets.QApplication.instance'):
        yield


@pytest.fixture
def test_container(mock_qt_app):
    """Create test reactive container."""
    return ReactiveContainer()


@pytest.fixture
def test_main_window(mock_qt_app):
    """Create test main window."""
    return QMainWindow()


def test_reactive_container_integration(test_container):
    """Test reactive container integration."""
    container = test_container
    
    # Test adding multiple components
    widget1 = QWidget()
    widget2 = QWidget()
    
    name1 = container.add_component(widget1, "widget1")
    name2 = container.add_component(widget2, "widget2")
    
    assert name1 == "widget1"
    assert name2 == "widget2"
    assert len(container.child_components) == 2
    assert container.main_layout.count() == 2
    
    # Test component retrieval
    assert container.get_component("widget1") == widget1
    assert container.get_component("widget2") == widget2
    
    # Test component removal
    container.remove_component("widget1")
    assert len(container.child_components) == 1
    assert container.main_layout.count() == 1
    assert container.get_component("widget1") is None


def test_main_window_integration(test_main_window):
    """Test main window integration."""
    main_window = test_main_window
    integration = MainWindowIntegration(main_window)
    
    # Test creating reactive areas
    area1 = integration.create_reactive_area("area1")
    area2 = integration.create_reactive_area("area2")
    
    assert isinstance(area1, ReactiveContainer)
    assert isinstance(area2, ReactiveContainer)
    assert area1 is not area2
    
    # Test area retrieval
    assert integration.get_reactive_area("area1") == area1
    assert integration.get_reactive_area("area2") == area2
    assert integration.get_reactive_area("nonexistent") is None


def test_wrapper_integration():
    """Test reactive wrapper integration."""
    widget = QLabel("Test Label")
    wrapper = ReactiveWrapper(widget)
    
    # Test property binding
    wrapper.bind_property("text", "text_state")
    assert "text" in wrapper.property_bindings
    assert wrapper.property_bindings["text"] == "text_state"
    
    # Test property update
    wrapper._update_property("text", "New Text")
    assert widget.text() == "New Text"
    
    # Test event handling
    handler = Mock()
    wrapper.add_event_handler(QEvent.Type.MouseButtonPress, handler)
    assert QEvent.Type.MouseButtonPress in wrapper.event_handlers
    
    # Test cleanup
    wrapper.cleanup()
    assert wrapper.property_bindings == {}
    assert wrapper.event_handlers == {}


def test_migration_helper_integration():
    """Test migration helper integration."""
    # Create a widget with some properties
    widget = QWidget()
    widget.setObjectName("test_widget")
    widget.setVisible(True)
    widget.setEnabled(True)
    widget.setStyleSheet("background-color: red;")
    
    # Test migration plan
    plan = MigrationHelper.create_migration_plan(widget)
    
    assert isinstance(plan, dict)
    assert 'widgets_to_migrate' in plan
    assert 'reactive_candidates' in plan
    assert 'integration_points' in plan
    assert 'estimated_effort' in plan
    
    # Test reactive candidate detection
    simple_widget = QWidget()
    assert not MigrationHelper._is_reactive_candidate(simple_widget)
    
    complex_widget = QWidget()
    complex_widget.state = {}
    assert MigrationHelper._is_reactive_candidate(complex_widget)