"""Tests for property panel integration and main UI components"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt

from torematrix.ui.components.property_panel.events import PropertyNotificationCenter
from torematrix.ui.components.property_panel.models import PropertyMetadata
from torematrix.ui.components.property_panel.display import PropertyDisplayWidget


@pytest.fixture
def qt_app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def main_window(qt_app):
    """Create main window for testing"""
    window = QMainWindow()
    window.show()
    return window


@pytest.fixture
def notification_center():
    """Create notification center"""
    return PropertyNotificationCenter()


class TestPropertyDisplayWidget:
    """Test property display widget integration"""
    
    def test_initialization(self, notification_center):
        """Test display widget initialization"""
        widget = PropertyDisplayWidget(notification_center)
        assert widget.notification_center == notification_center
        assert widget.isVisible()
    
    def test_set_selected_elements(self, notification_center):
        """Test setting selected elements"""
        widget = PropertyDisplayWidget(notification_center)
        
        element_ids = ["elem1", "elem2", "elem3"]
        widget.set_selected_elements(element_ids)
        
        # Should store the selected elements
        assert hasattr(widget, '_selected_elements')


class TestPropertyNotificationCenter:
    """Test property notification center"""
    
    def test_initialization(self, notification_center):
        """Test notification center initialization"""
        assert notification_center._listeners == {}
        assert notification_center._pending_events == []
        assert not notification_center._batch_mode
    
    def test_register_unregister_listener(self, notification_center):
        """Test listener registration"""
        from torematrix.ui.components.property_panel.events import PropertyEventType
        
        mock_listener = Mock()
        
        # Register listener
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, mock_listener)
        assert PropertyEventType.VALUE_CHANGED in notification_center._listeners
        assert mock_listener in notification_center._listeners[PropertyEventType.VALUE_CHANGED]
        
        # Unregister listener
        notification_center.unregister_listener(PropertyEventType.VALUE_CHANGED, mock_listener)
        assert mock_listener not in notification_center._listeners.get(PropertyEventType.VALUE_CHANGED, [])
    
    def test_emit_value_change(self, notification_center):
        """Test value change emission"""
        from torematrix.ui.components.property_panel.events import PropertyEventType
        
        mock_listener = Mock()
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, mock_listener)
        
        # Emit value change
        notification_center.emit_value_change("elem1", "prop1", "old_value", "new_value")
        
        # Should have called listener
        assert mock_listener.call_count == 1
    
    def test_batch_mode(self, notification_center):
        """Test batch mode operation"""
        assert not notification_center._batch_mode
        
        # Start batch mode
        notification_center.start_batch_mode()
        assert notification_center._batch_mode
        
        # End batch mode
        notification_center.end_batch_mode()
        assert not notification_center._batch_mode


class TestPropertyMetadata:
    """Test property metadata"""
    
    def test_initialization(self):
        """Test metadata initialization"""
        metadata = PropertyMetadata(
            name="test_prop",
            display_name="Test Property",
            description="A test property",
            category="Test Category"
        )
        
        assert metadata.name == "test_prop"
        assert metadata.display_name == "Test Property"
        assert metadata.description == "A test property"
        assert metadata.category == "Test Category"
        assert metadata.editable is True
        assert metadata.visible is True
    
    def test_to_dict(self):
        """Test metadata serialization"""
        metadata = PropertyMetadata(
            name="test_prop",
            display_name="Test Property",
            description="A test property",
            category="Test Category",
            editable=False,
            visible=True
        )
        
        data = metadata.to_dict()
        
        assert data["name"] == "test_prop"
        assert data["display_name"] == "Test Property"
        assert data["description"] == "A test property"
        assert data["category"] == "Test Category"
        assert data["editable"] is False
        assert data["visible"] is True


@pytest.mark.integration
class TestPropertyPanelIntegrationFlow:
    """Integration tests for complete property panel workflow"""
    
    def test_complete_notification_workflow(self, notification_center):
        """Test complete notification workflow"""
        from torematrix.ui.components.property_panel.events import PropertyEventType
        
        # Setup listeners
        value_listener = Mock()
        validation_listener = Mock()
        
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, value_listener)
        notification_center.register_listener(PropertyEventType.VALIDATION_FAILED, validation_listener)
        
        # Test value change notification
        notification_center.emit_value_change("elem1", "prop1", "old", "new")
        assert value_listener.call_count == 1
        
        # Test validation notification
        notification_center.emit_validation_failed("elem1", "prop1", "Validation error")
        assert validation_listener.call_count == 1
        
        # Test batch mode
        notification_center.start_batch_mode()
        
        # Emit events in batch mode
        notification_center.emit_value_change("elem2", "prop2", "old2", "new2")
        notification_center.emit_value_change("elem3", "prop3", "old3", "new3")
        
        # Events should be queued
        assert len(notification_center._pending_events) == 2
        
        # End batch mode
        notification_center.end_batch_mode()
        
        # Events should be processed
        assert len(notification_center._pending_events) == 0
    
    def test_property_panel_components_integration(self, qt_app, notification_center):
        """Test property panel components integration"""
        # Create display widget
        display_widget = PropertyDisplayWidget(notification_center)
        
        # Create metadata
        metadata = PropertyMetadata(
            name="integration_test",
            display_name="Integration Test Property",
            description="Test property for integration testing",
            category="Integration"
        )
        
        # Test metadata serialization
        metadata_dict = metadata.to_dict()
        assert metadata_dict["name"] == "integration_test"
        
        # Test notification system
        from torematrix.ui.components.property_panel.events import PropertyEventType
        
        listener_called = False
        def test_listener(event):
            nonlocal listener_called
            listener_called = True
        
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, test_listener)
        notification_center.emit_value_change("elem1", "test_prop", "old", "new")
        
        assert listener_called