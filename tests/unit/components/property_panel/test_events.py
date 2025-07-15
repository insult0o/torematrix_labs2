"""Tests for property event system"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtCore import QObject, QTimer
from src.torematrix.ui.components.property_panel.events import (
    PropertyNotificationCenter, PropertyEvent, PropertyEventType, PropertyEventManager
)

class TestPropertyEvent:
    def test_creation(self):
        """Test PropertyEvent creation"""
        event = PropertyEvent(
            event_type=PropertyEventType.VALUE_CHANGED,
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value="new"
        )
        assert event.event_type == PropertyEventType.VALUE_CHANGED
        assert event.element_id == "elem1"
        assert event.property_name == "text"
        assert event.old_value == "old"
        assert event.new_value == "new"
        assert event.metadata == {}
    
    def test_creation_with_metadata(self):
        """Test PropertyEvent creation with metadata"""
        metadata = {"user_id": "user123", "source": "ui"}
        event = PropertyEvent(
            event_type=PropertyEventType.VALIDATION_FAILED,
            element_id="elem1",
            property_name="x",
            metadata=metadata
        )
        assert event.metadata == metadata

class TestPropertyNotificationCenter:
    @pytest.fixture
    def notification_center(self):
        """Create PropertyNotificationCenter for testing"""
        return PropertyNotificationCenter()
    
    def test_initialization(self, notification_center):
        """Test PropertyNotificationCenter initialization"""
        assert notification_center._listeners == {}
        assert notification_center._pending_events == []
        assert notification_center._batch_mode is False
    
    def test_listener_registration(self, notification_center):
        """Test listener registration and unregistration"""
        callback = Mock()
        
        # Register listener
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, callback)
        assert PropertyEventType.VALUE_CHANGED in notification_center._listeners
        assert callback in notification_center._listeners[PropertyEventType.VALUE_CHANGED]
        assert notification_center.get_listener_count(PropertyEventType.VALUE_CHANGED) == 1
        
        # Unregister listener
        notification_center.unregister_listener(PropertyEventType.VALUE_CHANGED, callback)
        assert callback not in notification_center._listeners[PropertyEventType.VALUE_CHANGED]
        assert notification_center.get_listener_count(PropertyEventType.VALUE_CHANGED) == 0
    
    def test_event_dispatch(self, notification_center):
        """Test event dispatching to listeners"""
        callback1 = Mock()
        callback2 = Mock()
        
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, callback1)
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, callback2)
        
        event = PropertyEvent(
            event_type=PropertyEventType.VALUE_CHANGED,
            element_id="elem1",
            property_name="text",
            new_value="test"
        )
        
        notification_center.emit_property_event(event)
        
        # Both callbacks should be called
        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)
    
    def test_emit_value_change(self, notification_center):
        """Test emit_value_change convenience method"""
        # Mock signal emission
        notification_center.property_changed = Mock()
        
        notification_center.emit_value_change(
            "elem1", "text", "old", "new", {"user": "test"}
        )
        
        # Should emit property_changed signal
        notification_center.property_changed.emit.assert_called_once()
        emitted_event = notification_center.property_changed.emit.call_args[0][0]
        assert emitted_event.event_type == PropertyEventType.VALUE_CHANGED
        assert emitted_event.element_id == "elem1"
        assert emitted_event.property_name == "text"
        assert emitted_event.old_value == "old"
        assert emitted_event.new_value == "new"
        assert emitted_event.metadata["user"] == "test"
    
    def test_emit_validation_failed(self, notification_center):
        """Test emit_validation_failed convenience method"""
        # Mock signal emission
        notification_center.validation_failed = Mock()
        
        notification_center.emit_validation_failed(
            "elem1", "x", "Invalid coordinate"
        )
        
        # Should emit validation_failed signal
        notification_center.validation_failed.emit.assert_called_once_with(
            "elem1", "x", "Invalid coordinate"
        )
    
    def test_emit_property_selected(self, notification_center):
        """Test emit_property_selected convenience method"""
        # Mock signal emission
        notification_center.property_selected = Mock()
        
        notification_center.emit_property_selected("elem1", "text")
        
        # Should emit property_selected signal
        notification_center.property_selected.emit.assert_called_once_with("elem1", "text")
    
    def test_batch_mode(self, notification_center):
        """Test batch mode operation"""
        callback = Mock()
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, callback)
        
        # Start batch mode
        notification_center.start_batch_mode()
        assert notification_center._batch_mode is True
        
        # Emit events in batch mode
        event1 = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "text", "old1", "new1")
        event2 = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "x", 10, 20)
        
        notification_center.emit_property_event(event1)
        notification_center.emit_property_event(event2)
        
        # Events should be pending, not dispatched yet
        assert len(notification_center._pending_events) == 2
        callback.assert_not_called()
        
        # End batch mode
        notification_center.end_batch_mode()
        assert notification_center._batch_mode is False
        
        # Events should now be dispatched
        assert len(notification_center._pending_events) == 0
        assert callback.call_count == 2
    
    def test_listener_exception_handling(self, notification_center):
        """Test exception handling in listeners"""
        # Create a callback that raises an exception
        failing_callback = Mock(side_effect=Exception("Test exception"))
        working_callback = Mock()
        
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, failing_callback)
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, working_callback)
        
        event = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "text", "old", "new")
        
        # Should not raise exception, should call both callbacks
        notification_center.emit_property_event(event)
        
        failing_callback.assert_called_once_with(event)
        working_callback.assert_called_once_with(event)
    
    def test_clear_listeners(self, notification_center):
        """Test clearing all listeners"""
        callback1 = Mock()
        callback2 = Mock()
        
        notification_center.register_listener(PropertyEventType.VALUE_CHANGED, callback1)
        notification_center.register_listener(PropertyEventType.VALIDATION_FAILED, callback2)
        
        assert len(notification_center._listeners) == 2
        
        notification_center.clear_listeners()
        assert len(notification_center._listeners) == 0

class TestPropertyEventManager:
    @pytest.fixture
    def event_manager(self):
        """Create PropertyEventManager for testing"""
        notification_center = PropertyNotificationCenter()
        return PropertyEventManager(notification_center)
    
    def test_initialization(self, event_manager):
        """Test PropertyEventManager initialization"""
        assert event_manager._event_history == []
        assert event_manager._max_history == 1000
        assert isinstance(event_manager._notification_center, PropertyNotificationCenter)
    
    def test_emit_value_change(self, event_manager):
        """Test emit_value_change method"""
        # Mock notification center
        event_manager._notification_center.emit_value_change = Mock()
        
        event_manager.emit_value_change("elem1", "text", "old", "new", {"user": "test"})
        
        event_manager._notification_center.emit_value_change.assert_called_once_with(
            "elem1", "text", "old", "new", {"user": "test"}
        )
    
    def test_emit_validation_failed(self, event_manager):
        """Test emit_validation_failed method"""
        # Mock notification center
        event_manager._notification_center.emit_validation_failed = Mock()
        
        event_manager.emit_validation_failed("elem1", "x", "Invalid value")
        
        event_manager._notification_center.emit_validation_failed.assert_called_once_with(
            "elem1", "x", "Invalid value", None
        )
    
    def test_emit_property_selected(self, event_manager):
        """Test emit_property_selected method"""
        # Mock notification center
        event_manager._notification_center.emit_property_selected = Mock()
        
        event_manager.emit_property_selected("elem1", "text")
        
        event_manager._notification_center.emit_property_selected.assert_called_once_with(
            "elem1", "text"
        )
    
    def test_event_history(self, event_manager):
        """Test event history management"""
        # Add events to history
        event1 = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "text", "old1", "new1")
        event2 = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "x", 10, 20)
        event3 = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem2", "text", "old2", "new2")
        
        event_manager._add_to_history(event1)
        event_manager._add_to_history(event2)
        event_manager._add_to_history(event3)
        
        # Get all history
        all_events = event_manager.get_event_history()
        assert len(all_events) == 3
        
        # Filter by element
        elem1_events = event_manager.get_event_history(element_id="elem1")
        assert len(elem1_events) == 2
        assert event1 in elem1_events
        assert event2 in elem1_events
        
        # Filter by property
        text_events = event_manager.get_event_history(property_name="text")
        assert len(text_events) == 2
        assert event1 in text_events
        assert event3 in text_events
        
        # Filter by both
        elem1_text_events = event_manager.get_event_history(element_id="elem1", property_name="text")
        assert len(elem1_text_events) == 1
        assert elem1_text_events[0] == event1
    
    def test_clear_event_history(self, event_manager):
        """Test clearing event history"""
        event = PropertyEvent(PropertyEventType.VALUE_CHANGED, "elem1", "text", "old", "new")
        event_manager._add_to_history(event)
        
        assert len(event_manager._event_history) == 1
        
        event_manager.clear_event_history()
        assert len(event_manager._event_history) == 0
    
    def test_history_size_limit(self, event_manager):
        """Test event history size limit"""
        # Set smaller limit for testing
        event_manager._max_history = 3
        
        # Add more events than limit
        for i in range(5):
            event = PropertyEvent(PropertyEventType.VALUE_CHANGED, f"elem{i}", "text", f"old{i}", f"new{i}")
            event_manager._add_to_history(event)
        
        # Should only keep last 3
        assert len(event_manager._event_history) == 3
        
        # Should have events 2, 3, 4 (newest 3)
        events = event_manager.get_event_history()
        assert events[0].element_id == "elem2"
        assert events[1].element_id == "elem3"
        assert events[2].element_id == "elem4"