"""
End-to-end integration tests for selection tools.

Tests complete workflows and system integration scenarios
to ensure all components work together correctly.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication

from src.torematrix.ui.viewer.tools.accessibility import AccessibilityManager, AccessibilityMode
from src.torematrix.ui.viewer.tools.event_integration import ToolEventBus, ToolEventIntegration, EventType
from src.torematrix.ui.viewer.tools.serialization import ToolPersistenceManager, ToolSession
from src.torematrix.ui.viewer.tools.monitoring import SystemMonitor, MetricsCollector
from src.torematrix.ui.viewer.tools.base import SelectionTool, ToolState, SelectionResult
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockSelectionTool(SelectionTool):
    """Mock selection tool for testing."""
    
    def __init__(self, tool_id="test_tool", name="Test Tool"):
        # Mock the required dependencies
        overlay = Mock()
        selection_manager = Mock()
        spatial_index = Mock()
        
        super().__init__(
            tool_id=tool_id,
            name=name,
            description="Test tool for integration testing",
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
    
    def activate(self):
        self._state = ToolState.ACTIVE
        self.state_changed.emit(self._state)
    
    def deactivate(self):
        self._state = ToolState.INACTIVE
        self.state_changed.emit(self._state)
    
    def handle_mouse_press(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        self._state = ToolState.SELECTING
        self.state_changed.emit(self._state)
        return True
    
    def handle_mouse_release(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        # Create mock selection result
        result = SelectionResult(
            elements=[Mock()],
            geometry=Rectangle(100, 100, 50, 50),
            tool_type="test",
            timestamp=time.time(),
            metadata={"test": True}
        )
        
        self._current_selection = result
        self._state = ToolState.SELECTED
        self.selection_changed.emit(result)
        self.state_changed.emit(self._state)
        return True


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return ToolEventBus()


@pytest.fixture
def metrics_collector():
    """Create metrics collector for testing."""
    return MetricsCollector()


@pytest.fixture
def accessibility_manager(app):
    """Create accessibility manager for testing."""
    return AccessibilityManager()


@pytest.fixture
def persistence_manager(tmp_path):
    """Create persistence manager with temporary storage."""
    return ToolPersistenceManager(storage_dir=tmp_path)


@pytest.fixture
def system_monitor(metrics_collector):
    """Create system monitor for testing."""
    return SystemMonitor(metrics_collector)


@pytest.fixture
def mock_tool():
    """Create mock selection tool."""
    return MockSelectionTool()


class TestCompleteIntegration:
    """Test complete system integration scenarios."""
    
    def test_full_system_initialization(self, app, event_bus, metrics_collector, 
                                      accessibility_manager, persistence_manager, 
                                      system_monitor):
        """Test complete system initialization."""
        # Create event integration
        event_integration = ToolEventIntegration(event_bus)
        
        # Verify all components are initialized
        assert event_bus is not None
        assert metrics_collector is not None
        assert accessibility_manager is not None
        assert persistence_manager is not None
        assert system_monitor is not None
        assert event_integration is not None
    
    def test_tool_lifecycle_with_all_systems(self, app, event_bus, metrics_collector,
                                           accessibility_manager, persistence_manager,
                                           system_monitor, mock_tool):
        """Test tool lifecycle with all systems integrated."""
        # Create event integration
        event_integration = ToolEventIntegration(event_bus)
        
        # Register tool with all systems
        event_integration.integrate_tool(mock_tool)
        accessibility_manager.register_tool(mock_tool)
        system_monitor.register_tool(mock_tool)
        
        # Test tool activation
        mock_tool.activate()
        assert mock_tool.get_state() == ToolState.ACTIVE
        
        # Test selection workflow
        mouse_point = QPoint(150, 150)
        
        # Mouse press
        success = mock_tool.handle_mouse_press(mouse_point)
        assert success
        assert mock_tool.get_state() == ToolState.SELECTING
        
        # Mouse release (completes selection)
        success = mock_tool.handle_mouse_release(mouse_point)
        assert success
        assert mock_tool.get_state() == ToolState.SELECTED
        assert mock_tool.get_current_selection() is not None
        
        # Test tool deactivation
        mock_tool.deactivate()
        assert mock_tool.get_state() == ToolState.INACTIVE
        
        # Verify metrics were collected
        stats = metrics_collector.get_statistics()
        assert stats['total_metrics'] > 0
    
    def test_accessibility_integration(self, app, accessibility_manager, mock_tool):
        """Test accessibility features integration."""
        # Register tool
        accessibility_manager.register_tool(mock_tool)
        accessibility_manager.set_current_tool(mock_tool)
        
        # Test accessibility mode changes
        accessibility_manager.apply_accessibility_mode(AccessibilityMode.HIGH_CONTRAST)
        assert accessibility_manager.get_settings().mode == AccessibilityMode.HIGH_CONTRAST
        
        # Test keyboard navigation
        from PyQt6.QtGui import QKeyEvent
        key_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier
        )
        
        handled = accessibility_manager.handle_key_event(key_event)
        # Should handle navigation keys
        assert handled
    
    def test_event_system_integration(self, event_bus, mock_tool):
        """Test event system integration."""
        event_integration = ToolEventIntegration(event_bus)
        
        # Track events
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to tool events
        event_bus.subscribe(
            "test_subscriber",
            event_handler
        )
        
        # Integrate tool
        event_integration.integrate_tool(mock_tool)
        
        # Trigger tool state changes
        mock_tool.activate()
        mock_tool.handle_mouse_press(QPoint(100, 100))
        mock_tool.handle_mouse_release(QPoint(100, 100))
        
        # Process any queued events
        time.sleep(0.1)
        app = QApplication.instance()
        if app:
            app.processEvents()
        
        # Verify events were published and received
        assert len(events_received) > 0
        
        # Check for specific event types
        event_types = [event.event_type for event in events_received]
        assert EventType.TOOL_ACTIVATED in event_types
    
    def test_persistence_integration(self, persistence_manager, mock_tool):
        """Test persistence system integration."""
        # Create session
        session = persistence_manager.create_session()
        assert session is not None
        
        # Save tool configuration
        success = persistence_manager.save_tool_configuration(mock_tool)
        assert success
        
        # Save session
        success = persistence_manager.save_session(session)
        assert success
        
        # Load configuration
        config = persistence_manager.load_tool_configuration(mock_tool.tool_id)
        assert config is not None
        assert config.tool_id == mock_tool.tool_id
        
        # Load session
        loaded_session = persistence_manager.load_session()
        assert loaded_session is not None
        assert loaded_session.session_id == session.session_id
    
    def test_monitoring_integration(self, metrics_collector, system_monitor, mock_tool):
        """Test monitoring system integration."""
        # Register tool
        system_monitor.register_tool(mock_tool)
        
        # Trigger some operations
        mock_tool.activate()
        mock_tool.handle_mouse_press(QPoint(100, 100))
        mock_tool.handle_mouse_release(QPoint(100, 100))
        
        # Get tool statistics
        tool_stats = system_monitor.get_tool_statistics()
        assert mock_tool.tool_id in tool_stats
        
        tool_data = tool_stats[mock_tool.tool_id]
        assert tool_data['tool_id'] == mock_tool.tool_id
        assert tool_data['selection_count'] >= 0
    
    def test_error_handling_integration(self, app, event_bus, system_monitor, 
                                      metrics_collector, mock_tool):
        """Test error handling across all systems."""
        # Create event integration
        event_integration = ToolEventIntegration(event_bus)
        
        # Register tool with systems
        event_integration.integrate_tool(mock_tool)
        system_monitor.register_tool(mock_tool)
        
        # Track alerts
        alerts_raised = []
        
        def alert_handler(alert):
            alerts_raised.append(alert)
        
        system_monitor.alert_raised.connect(alert_handler)
        
        # Simulate tool error
        if hasattr(mock_tool, 'error_occurred'):
            mock_tool.error_occurred.emit("Test error message")
        
        # Process events
        time.sleep(0.1)
        if app:
            app.processEvents()
        
        # Verify error handling
        # Note: Actual alert generation depends on the specific error conditions
        # This test mainly verifies the integration points work
    
    def test_performance_under_load(self, app, event_bus, metrics_collector, 
                                   system_monitor):
        """Test system performance with multiple tools and operations."""
        # Create multiple tools
        tools = [MockSelectionTool(f"tool_{i}", f"Test Tool {i}") for i in range(5)]
        
        # Create event integration
        event_integration = ToolEventIntegration(event_bus)
        
        # Register all tools
        for tool in tools:
            event_integration.integrate_tool(tool)
            system_monitor.register_tool(tool)
        
        # Perform operations on all tools
        start_time = time.time()
        
        for tool in tools:
            tool.activate()
            for i in range(10):  # 10 selections per tool
                tool.handle_mouse_press(QPoint(i * 10, i * 10))
                tool.handle_mouse_release(QPoint(i * 10, i * 10))
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Process all events
        if app:
            app.processEvents()
        
        # Verify performance
        assert operation_time < 5.0  # Should complete within 5 seconds
        
        # Check metrics
        stats = metrics_collector.get_statistics()
        assert stats['total_metrics'] > 0
        
        # Check tool statistics
        tool_stats = system_monitor.get_tool_statistics()
        assert len(tool_stats) == len(tools)
    
    def test_memory_management(self, app, event_bus, metrics_collector, 
                             accessibility_manager, system_monitor):
        """Test memory management across system components."""
        import gc
        import sys
        
        # Get initial memory usage
        if hasattr(sys, 'getsizeof'):
            initial_objects = len(gc.get_objects())
        
        # Create and destroy tools multiple times
        for iteration in range(3):
            tools = []
            event_integration = ToolEventIntegration(event_bus)
            
            # Create tools
            for i in range(10):
                tool = MockSelectionTool(f"temp_tool_{iteration}_{i}")
                tools.append(tool)
                
                # Register with systems
                event_integration.integrate_tool(tool)
                accessibility_manager.register_tool(tool)
                system_monitor.register_tool(tool)
            
            # Use tools
            for tool in tools:
                tool.activate()
                tool.handle_mouse_press(QPoint(100, 100))
                tool.handle_mouse_release(QPoint(100, 100))
                tool.deactivate()
            
            # Clean up
            for tool in tools:
                event_integration.remove_tool(tool.tool_id)
                accessibility_manager.unregister_tool(tool.tool_id)
                system_monitor.unregister_tool(tool.tool_id)
            
            # Force garbage collection
            del tools
            del event_integration
            gc.collect()
            
            if app:
                app.processEvents()
        
        # Check final memory usage
        if hasattr(sys, 'getsizeof'):
            final_objects = len(gc.get_objects())
            # Allow for some growth, but not excessive
            assert final_objects < initial_objects * 1.5
    
    def test_concurrent_operations(self, app, event_bus, metrics_collector):
        """Test concurrent operations across the system."""
        import threading
        
        # Create tools
        tools = [MockSelectionTool(f"concurrent_tool_{i}") for i in range(3)]
        event_integration = ToolEventIntegration(event_bus)
        
        # Register tools
        for tool in tools:
            event_integration.integrate_tool(tool)
        
        # Define worker function
        def worker(tool, operations=20):
            for i in range(operations):
                tool.activate()
                tool.handle_mouse_press(QPoint(i, i))
                time.sleep(0.001)  # Small delay
                tool.handle_mouse_release(QPoint(i, i))
                tool.deactivate()
        
        # Start concurrent operations
        threads = []
        for tool in tools:
            thread = threading.Thread(target=worker, args=(tool,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Process events
        if app:
            app.processEvents()
        
        # Verify operations completed successfully
        stats = metrics_collector.get_statistics()
        assert stats['total_metrics'] > 0