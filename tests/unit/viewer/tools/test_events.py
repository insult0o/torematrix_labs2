"""
Tests for tool event system.
"""

import pytest
import time
import tempfile
from unittest.mock import Mock, patch
from PyQt6.QtCore import QPoint, QRect, Qt

from src.torematrix.ui.viewer.tools.base import ToolState, SelectionResult
from src.torematrix.ui.viewer.tools.events import (
    EventType, EventPriority, ToolEvent, MouseEvent, KeyEvent, WheelEvent,
    StateEvent, SelectionEvent, OperationEvent, CustomEvent, EventFilter,
    EventHandler, EventDispatcher, EventRecorder, get_global_event_dispatcher,
    create_mouse_event, create_key_event, create_state_event, create_selection_event
)


class TestEventType:
    """Test EventType enum."""
    
    def test_event_types_exist(self):
        """Test that all event types exist."""
        assert EventType.MOUSE_PRESS
        assert EventType.MOUSE_MOVE
        assert EventType.MOUSE_RELEASE
        assert EventType.MOUSE_DOUBLE_CLICK
        assert EventType.KEY_PRESS
        assert EventType.KEY_RELEASE
        assert EventType.WHEEL
        assert EventType.TOOL_ACTIVATED
        assert EventType.TOOL_DEACTIVATED
        assert EventType.STATE_CHANGED
        assert EventType.SELECTION_CHANGED
        assert EventType.CURSOR_CHANGED
        assert EventType.PREVIEW_CHANGED
        assert EventType.ERROR_OCCURRED
        assert EventType.OPERATION_STARTED
        assert EventType.OPERATION_COMPLETED
        assert EventType.OPERATION_CANCELLED
        assert EventType.CUSTOM


class TestEventPriority:
    """Test EventPriority enum."""
    
    def test_event_priorities_exist(self):
        """Test that all event priorities exist."""
        assert EventPriority.LOW.value == 1
        assert EventPriority.NORMAL.value == 2
        assert EventPriority.HIGH.value == 3
        assert EventPriority.CRITICAL.value == 4


class TestToolEvent:
    """Test ToolEvent base class."""
    
    def test_tool_event_creation(self):
        """Test tool event creation."""
        event = ToolEvent(
            event_type=EventType.CUSTOM,
            tool_id="test_tool",
            priority=EventPriority.HIGH
        )
        
        assert event.event_type == EventType.CUSTOM
        assert event.tool_id == "test_tool"
        assert event.priority == EventPriority.HIGH
        assert isinstance(event.timestamp, float)
        assert event.metadata == {}
        assert event.handled == False
        assert event.cancelled == False
    
    def test_tool_event_with_metadata(self):
        """Test tool event with metadata."""
        metadata = {"key": "value", "number": 42}
        event = ToolEvent(
            event_type=EventType.CUSTOM,
            metadata=metadata
        )
        
        assert event.metadata == metadata
    
    def test_event_age(self):
        """Test event age calculation."""
        event = ToolEvent(event_type=EventType.CUSTOM)
        
        time.sleep(0.001)
        age = event.age()
        assert age > 0
    
    def test_mark_handled(self):
        """Test marking event as handled."""
        event = ToolEvent(event_type=EventType.CUSTOM)
        
        assert event.handled == False
        event.mark_handled()
        assert event.handled == True
    
    def test_cancel_event(self):
        """Test canceling event."""
        event = ToolEvent(event_type=EventType.CUSTOM)
        
        assert event.cancelled == False
        event.cancel()
        assert event.cancelled == True
    
    def test_event_type_checks(self):
        """Test event type checking methods."""
        mouse_event = ToolEvent(event_type=EventType.MOUSE_PRESS)
        key_event = ToolEvent(event_type=EventType.KEY_PRESS)
        tool_event = ToolEvent(event_type=EventType.STATE_CHANGED)
        operation_event = ToolEvent(event_type=EventType.OPERATION_STARTED)
        
        assert mouse_event.is_mouse_event() == True
        assert mouse_event.is_keyboard_event() == False
        assert mouse_event.is_tool_event() == False
        assert mouse_event.is_operation_event() == False
        
        assert key_event.is_keyboard_event() == True
        assert key_event.is_mouse_event() == False
        
        assert tool_event.is_tool_event() == True
        assert tool_event.is_mouse_event() == False
        
        assert operation_event.is_operation_event() == True
        assert operation_event.is_mouse_event() == False


class TestMouseEvent:
    """Test MouseEvent class."""
    
    def test_mouse_event_creation(self):
        """Test mouse event creation."""
        position = QPoint(10, 20)
        event = MouseEvent(
            event_type=EventType.MOUSE_PRESS,
            position=position,
            button=Qt.MouseButton.LeftButton,
            modifiers=Qt.KeyboardModifier.ControlModifier
        )
        
        assert event.event_type == EventType.MOUSE_PRESS
        assert event.position == position
        assert event.button == Qt.MouseButton.LeftButton
        assert event.modifiers == Qt.KeyboardModifier.ControlModifier
    
    def test_mouse_event_invalid_type(self):
        """Test mouse event with invalid type."""
        with pytest.raises(ValueError):
            MouseEvent(
                event_type=EventType.KEY_PRESS,  # Invalid for MouseEvent
                position=QPoint(0, 0)
            )
    
    def test_mouse_event_defaults(self):
        """Test mouse event with default values."""
        event = MouseEvent(event_type=EventType.MOUSE_MOVE)
        
        assert event.position == QPoint()
        assert event.button == Qt.MouseButton.NoButton
        assert event.buttons == Qt.MouseButton.NoButton
        assert event.modifiers == Qt.KeyboardModifier.NoModifier


class TestKeyEvent:
    """Test KeyEvent class."""
    
    def test_key_event_creation(self):
        """Test key event creation."""
        event = KeyEvent(
            event_type=EventType.KEY_PRESS,
            key=Qt.Key.Key_A,
            modifiers=Qt.KeyboardModifier.ShiftModifier,
            text="A"
        )
        
        assert event.event_type == EventType.KEY_PRESS
        assert event.key == Qt.Key.Key_A
        assert event.modifiers == Qt.KeyboardModifier.ShiftModifier
        assert event.text == "A"
        assert event.auto_repeat == False
    
    def test_key_event_invalid_type(self):
        """Test key event with invalid type."""
        with pytest.raises(ValueError):
            KeyEvent(
                event_type=EventType.MOUSE_PRESS,  # Invalid for KeyEvent
                key=Qt.Key.Key_A
            )


class TestWheelEvent:
    """Test WheelEvent class."""
    
    def test_wheel_event_creation(self):
        """Test wheel event creation."""
        position = QPoint(50, 60)
        angle_delta = QPoint(0, 120)
        
        event = WheelEvent(
            event_type=EventType.WHEEL,
            position=position,
            angle_delta=angle_delta,
            modifiers=Qt.KeyboardModifier.AltModifier
        )
        
        assert event.event_type == EventType.WHEEL
        assert event.position == position
        assert event.angle_delta == angle_delta
        assert event.modifiers == Qt.KeyboardModifier.AltModifier
    
    def test_wheel_event_invalid_type(self):
        """Test wheel event with invalid type."""
        with pytest.raises(ValueError):
            WheelEvent(
                event_type=EventType.KEY_PRESS  # Invalid for WheelEvent
            )


class TestStateEvent:
    """Test StateEvent class."""
    
    def test_state_event_creation(self):
        """Test state event creation."""
        event = StateEvent(
            event_type=EventType.STATE_CHANGED,
            old_state=ToolState.INACTIVE,
            new_state=ToolState.ACTIVE
        )
        
        assert event.event_type == EventType.STATE_CHANGED
        assert event.old_state == ToolState.INACTIVE
        assert event.new_state == ToolState.ACTIVE
    
    def test_state_event_invalid_type(self):
        """Test state event with invalid type."""
        with pytest.raises(ValueError):
            StateEvent(
                event_type=EventType.MOUSE_PRESS,  # Invalid for StateEvent
                old_state=ToolState.INACTIVE,
                new_state=ToolState.ACTIVE
            )


class TestSelectionEvent:
    """Test SelectionEvent class."""
    
    def test_selection_event_creation(self):
        """Test selection event creation."""
        selection = SelectionResult(tool_type="test_tool")
        previous_selection = SelectionResult(tool_type="previous_tool")
        
        event = SelectionEvent(
            event_type=EventType.SELECTION_CHANGED,
            selection=selection,
            previous_selection=previous_selection
        )
        
        assert event.event_type == EventType.SELECTION_CHANGED
        assert event.selection == selection
        assert event.previous_selection == previous_selection
    
    def test_selection_event_invalid_type(self):
        """Test selection event with invalid type."""
        with pytest.raises(ValueError):
            SelectionEvent(
                event_type=EventType.MOUSE_PRESS  # Invalid for SelectionEvent
            )


class TestOperationEvent:
    """Test OperationEvent class."""
    
    def test_operation_event_creation(self):
        """Test operation event creation."""
        event = OperationEvent(
            event_type=EventType.OPERATION_STARTED,
            operation_id="op123",
            operation_type="selection",
            progress=0.5
        )
        
        assert event.event_type == EventType.OPERATION_STARTED
        assert event.operation_id == "op123"
        assert event.operation_type == "selection"
        assert event.progress == 0.5
    
    def test_operation_event_invalid_type(self):
        """Test operation event with invalid type."""
        with pytest.raises(ValueError):
            OperationEvent(
                event_type=EventType.MOUSE_PRESS  # Invalid for OperationEvent
            )


class TestCustomEvent:
    """Test CustomEvent class."""
    
    def test_custom_event_creation(self):
        """Test custom event creation."""
        data = {"custom": "data"}
        event = CustomEvent(
            event_type=EventType.CUSTOM,
            name="custom_action",
            data=data
        )
        
        assert event.event_type == EventType.CUSTOM
        assert event.name == "custom_action"
        assert event.data == data
    
    def test_custom_event_invalid_type(self):
        """Test custom event with invalid type."""
        with pytest.raises(ValueError):
            CustomEvent(
                event_type=EventType.MOUSE_PRESS  # Invalid for CustomEvent
            )


class TestEventFilter:
    """Test EventFilter class."""
    
    def test_event_filter_creation(self):
        """Test event filter creation."""
        filter_obj = EventFilter("test_filter")
        
        assert filter_obj.name == "test_filter"
        assert len(filter_obj.event_types) == 0
        assert len(filter_obj.tool_ids) == 0
        assert len(filter_obj.priorities) == 0
    
    def test_event_filter_configuration(self):
        """Test event filter configuration."""
        filter_obj = EventFilter("test_filter")
        
        filter_obj.add_event_type(EventType.MOUSE_PRESS)
        filter_obj.add_tool_id("tool1")
        filter_obj.add_priority(EventPriority.HIGH)
        filter_obj.set_age_range(0.0, 10.0)
        
        assert EventType.MOUSE_PRESS in filter_obj.event_types
        assert "tool1" in filter_obj.tool_ids
        assert EventPriority.HIGH in filter_obj.priorities
        assert filter_obj.min_age == 0.0
        assert filter_obj.max_age == 10.0
    
    def test_event_filter_matching(self):
        """Test event filter matching."""
        filter_obj = EventFilter("test_filter")
        filter_obj.add_event_type(EventType.MOUSE_PRESS)
        filter_obj.add_tool_id("tool1")
        filter_obj.add_priority(EventPriority.HIGH)
        
        # Matching event
        matching_event = MouseEvent(
            event_type=EventType.MOUSE_PRESS,
            tool_id="tool1",
            priority=EventPriority.HIGH
        )
        assert filter_obj.matches(matching_event) == True
        
        # Non-matching event (wrong type)
        non_matching_event = MouseEvent(
            event_type=EventType.MOUSE_MOVE,
            tool_id="tool1",
            priority=EventPriority.HIGH
        )
        assert filter_obj.matches(non_matching_event) == False
        
        # Non-matching event (wrong tool)
        non_matching_event2 = MouseEvent(
            event_type=EventType.MOUSE_PRESS,
            tool_id="tool2",
            priority=EventPriority.HIGH
        )
        assert filter_obj.matches(non_matching_event2) == False
    
    def test_event_filter_custom_filter(self):
        """Test event filter with custom filter function."""
        filter_obj = EventFilter("test_filter")
        filter_obj.set_custom_filter(lambda event: event.tool_id.startswith("test_"))
        
        # Matching event
        matching_event = ToolEvent(
            event_type=EventType.CUSTOM,
            tool_id="test_tool"
        )
        assert filter_obj.matches(matching_event) == True
        
        # Non-matching event
        non_matching_event = ToolEvent(
            event_type=EventType.CUSTOM,
            tool_id="other_tool"
        )
        assert filter_obj.matches(non_matching_event) == False


class TestEventHandler:
    """Test EventHandler class."""
    
    def test_event_handler_creation(self):
        """Test event handler creation."""
        handler = EventHandler("test_handler")
        
        assert handler.name == "test_handler"
        assert handler.enabled == True
        assert handler.priority == EventPriority.NORMAL
    
    def test_event_handler_enable_disable(self):
        """Test event handler enable/disable."""
        handler = EventHandler("test_handler")
        
        assert handler.is_enabled() == True
        
        handler.set_enabled(False)
        assert handler.is_enabled() == False
        
        handler.set_enabled(True)
        assert handler.is_enabled() == True
    
    def test_event_handler_handle_event(self):
        """Test event handler event handling."""
        handler = EventHandler("test_handler")
        event = ToolEvent(event_type=EventType.CUSTOM)
        
        # Default implementation returns False
        result = handler.handle_event(event)
        assert result == False
        
        # Disabled handler should not handle
        handler.set_enabled(False)
        result = handler.handle_event(event)
        assert result == False


class MockEventHandler(EventHandler):
    """Mock event handler for testing."""
    
    def __init__(self, name="mock_handler", should_handle=True):
        super().__init__(name)
        self.should_handle = should_handle
        self.events_handled = []
    
    def _handle_event_impl(self, event):
        self.events_handled.append(event)
        return self.should_handle


class TestEventDispatcher:
    """Test EventDispatcher class."""
    
    def test_event_dispatcher_creation(self):
        """Test event dispatcher creation."""
        dispatcher = EventDispatcher()
        
        assert len(dispatcher.get_handlers()) == 0
        assert len(dispatcher.get_filters()) == 0
        assert dispatcher.get_queue_size() == 0
    
    def test_add_remove_handler(self):
        """Test adding and removing handlers."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("test_handler")
        
        dispatcher.add_handler(handler)
        assert len(dispatcher.get_handlers()) == 1
        assert handler in dispatcher.get_handlers()
        
        success = dispatcher.remove_handler(handler)
        assert success == True
        assert len(dispatcher.get_handlers()) == 0
        
        # Remove non-existent handler
        success = dispatcher.remove_handler(handler)
        assert success == False
    
    def test_remove_handler_by_name(self):
        """Test removing handler by name."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("test_handler")
        
        dispatcher.add_handler(handler)
        
        success = dispatcher.remove_handler_by_name("test_handler")
        assert success == True
        assert len(dispatcher.get_handlers()) == 0
        
        # Remove non-existent handler
        success = dispatcher.remove_handler_by_name("nonexistent")
        assert success == False
    
    def test_handler_priority_sorting(self):
        """Test handler priority sorting."""
        dispatcher = EventDispatcher()
        
        low_handler = MockEventHandler("low")
        low_handler.priority = EventPriority.LOW
        
        high_handler = MockEventHandler("high")
        high_handler.priority = EventPriority.HIGH
        
        normal_handler = MockEventHandler("normal")
        normal_handler.priority = EventPriority.NORMAL
        
        # Add in random order
        dispatcher.add_handler(normal_handler)
        dispatcher.add_handler(low_handler)
        dispatcher.add_handler(high_handler)
        
        handlers = dispatcher.get_handlers()
        
        # Should be sorted by priority (highest first)
        assert handlers[0] == high_handler
        assert handlers[1] == normal_handler
        assert handlers[2] == low_handler
    
    def test_dispatch_event(self):
        """Test event dispatching."""
        dispatcher = EventDispatcher()
        handler1 = MockEventHandler("handler1", should_handle=False)
        handler2 = MockEventHandler("handler2", should_handle=True)
        handler3 = MockEventHandler("handler3", should_handle=False)
        
        dispatcher.add_handler(handler1)
        dispatcher.add_handler(handler2)
        dispatcher.add_handler(handler3)
        
        event = ToolEvent(event_type=EventType.CUSTOM)
        result = dispatcher.dispatch_event(event)
        
        assert result == True  # handler2 handled it
        assert event.handled == True
        
        # All handlers should have received the event
        assert len(handler1.events_handled) == 1
        assert len(handler2.events_handled) == 1
        assert len(handler3.events_handled) == 1
    
    def test_dispatch_cancelled_event(self):
        """Test dispatching cancelled event."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("handler")
        
        dispatcher.add_handler(handler)
        
        event = ToolEvent(event_type=EventType.CUSTOM)
        event.cancel()
        
        result = dispatcher.dispatch_event(event)
        assert result == False
        assert len(handler.events_handled) == 0
    
    def test_event_filtering(self):
        """Test event filtering."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("handler")
        
        # Add filter that only allows mouse events
        filter_obj = EventFilter("mouse_only")
        filter_obj.add_event_type(EventType.MOUSE_PRESS)
        
        dispatcher.add_handler(handler)
        dispatcher.add_filter(filter_obj)
        
        # Mouse event should pass
        mouse_event = MouseEvent(event_type=EventType.MOUSE_PRESS)
        result = dispatcher.dispatch_event(mouse_event)
        assert result == True
        assert len(handler.events_handled) == 1
        
        # Key event should be filtered
        key_event = KeyEvent(event_type=EventType.KEY_PRESS, key=Qt.Key.Key_A)
        result = dispatcher.dispatch_event(key_event)
        assert result == False
        assert len(handler.events_handled) == 1  # No new events
    
    def test_event_queue(self):
        """Test event queueing."""
        dispatcher = EventDispatcher()
        
        event1 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool1")
        event2 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool2")
        
        success1 = dispatcher.queue_event(event1)
        success2 = dispatcher.queue_event(event2)
        
        assert success1 == True
        assert success2 == True
        assert dispatcher.get_queue_size() == 2
    
    def test_process_queued_events(self):
        """Test processing queued events."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("handler")
        dispatcher.add_handler(handler)
        
        # Queue some events
        event1 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool1")
        event2 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool2")
        
        dispatcher.queue_event(event1)
        dispatcher.queue_event(event2)
        
        processed = dispatcher.process_queued_events()
        
        assert processed == 2
        assert dispatcher.get_queue_size() == 0
        assert len(handler.events_handled) == 2
    
    def test_queue_size_limit(self):
        """Test queue size limiting."""
        dispatcher = EventDispatcher()
        dispatcher.set_max_queue_size(2)
        
        # Add events up to limit
        event1 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool1")
        event2 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool2")
        event3 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool3")
        
        dispatcher.queue_event(event1)
        dispatcher.queue_event(event2)
        dispatcher.queue_event(event3)  # Should remove event1
        
        assert dispatcher.get_queue_size() == 2
    
    def test_clear_queue(self):
        """Test clearing event queue."""
        dispatcher = EventDispatcher()
        
        event = ToolEvent(event_type=EventType.CUSTOM)
        dispatcher.queue_event(event)
        
        assert dispatcher.get_queue_size() == 1
        
        dispatcher.clear_queue()
        
        assert dispatcher.get_queue_size() == 0
    
    def test_statistics(self):
        """Test event statistics."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler("handler")
        dispatcher.add_handler(handler)
        
        stats = dispatcher.get_statistics()
        assert stats['events_dispatched'] == 0
        assert stats['events_handled'] == 0
        assert stats['handlers_count'] == 1
        
        # Dispatch some events
        event1 = ToolEvent(event_type=EventType.CUSTOM)
        event2 = ToolEvent(event_type=EventType.CUSTOM)
        
        dispatcher.dispatch_event(event1)
        dispatcher.dispatch_event(event2)
        
        stats = dispatcher.get_statistics()
        assert stats['events_dispatched'] == 2
        assert stats['events_handled'] == 2
        
        # Reset statistics
        dispatcher.reset_statistics()
        stats = dispatcher.get_statistics()
        assert stats['events_dispatched'] == 0
        assert stats['events_handled'] == 0


class TestEventRecorder:
    """Test EventRecorder class."""
    
    def test_event_recorder_creation(self):
        """Test event recorder creation."""
        recorder = EventRecorder()
        
        assert recorder.is_recording() == False
        assert len(recorder.get_recorded_events()) == 0
    
    def test_recording_lifecycle(self):
        """Test recording start/stop."""
        recorder = EventRecorder()
        
        recorder.start_recording()
        assert recorder.is_recording() == True
        
        recorder.stop_recording()
        assert recorder.is_recording() == False
    
    def test_record_events(self):
        """Test recording events."""
        recorder = EventRecorder()
        
        # Events while not recording should be ignored
        event1 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool1")
        recorder.record_event(event1)
        assert len(recorder.get_recorded_events()) == 0
        
        # Start recording
        recorder.start_recording()
        
        event2 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool2")
        event3 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool3")
        
        recorder.record_event(event2)
        recorder.record_event(event3)
        
        recorded = recorder.get_recorded_events()
        assert len(recorded) == 2
        assert recorded[0].tool_id == "tool2"
        assert recorded[1].tool_id == "tool3"
    
    def test_clear_recording(self):
        """Test clearing recorded events."""
        recorder = EventRecorder()
        recorder.start_recording()
        
        event = ToolEvent(event_type=EventType.CUSTOM)
        recorder.record_event(event)
        
        assert len(recorder.get_recorded_events()) == 1
        
        recorder.clear_recording()
        
        assert len(recorder.get_recorded_events()) == 0
    
    def test_recording_limit(self):
        """Test recording size limit."""
        recorder = EventRecorder(max_events=2)
        recorder.start_recording()
        
        # Record more events than limit
        event1 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool1")
        event2 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool2")
        event3 = ToolEvent(event_type=EventType.CUSTOM, tool_id="tool3")
        
        recorder.record_event(event1)
        recorder.record_event(event2)
        recorder.record_event(event3)  # Should remove event1
        
        recorded = recorder.get_recorded_events()
        assert len(recorded) == 2
        assert recorded[0].tool_id == "tool2"
        assert recorded[1].tool_id == "tool3"


class TestEventCreationFunctions:
    """Test event creation helper functions."""
    
    def test_create_mouse_event(self):
        """Test creating mouse event."""
        position = QPoint(10, 20)
        event = create_mouse_event(
            EventType.MOUSE_PRESS,
            position,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            "test_tool"
        )
        
        assert isinstance(event, MouseEvent)
        assert event.event_type == EventType.MOUSE_PRESS
        assert event.position == position
        assert event.button == Qt.MouseButton.LeftButton
        assert event.modifiers == Qt.KeyboardModifier.ControlModifier
        assert event.tool_id == "test_tool"
    
    def test_create_key_event(self):
        """Test creating key event."""
        event = create_key_event(
            EventType.KEY_PRESS,
            Qt.Key.Key_A,
            Qt.KeyboardModifier.ShiftModifier,
            "A",
            "test_tool"
        )
        
        assert isinstance(event, KeyEvent)
        assert event.event_type == EventType.KEY_PRESS
        assert event.key == Qt.Key.Key_A
        assert event.modifiers == Qt.KeyboardModifier.ShiftModifier
        assert event.text == "A"
        assert event.tool_id == "test_tool"
    
    def test_create_state_event(self):
        """Test creating state event."""
        event = create_state_event(
            ToolState.INACTIVE,
            ToolState.ACTIVE,
            "test_tool"
        )
        
        assert isinstance(event, StateEvent)
        assert event.event_type == EventType.STATE_CHANGED
        assert event.old_state == ToolState.INACTIVE
        assert event.new_state == ToolState.ACTIVE
        assert event.tool_id == "test_tool"
    
    def test_create_selection_event(self):
        """Test creating selection event."""
        selection = SelectionResult(tool_type="test_tool")
        previous_selection = SelectionResult(tool_type="previous_tool")
        
        event = create_selection_event(
            selection,
            "test_tool",
            previous_selection
        )
        
        assert isinstance(event, SelectionEvent)
        assert event.event_type == EventType.SELECTION_CHANGED
        assert event.selection == selection
        assert event.previous_selection == previous_selection
        assert event.tool_id == "test_tool"


class TestGlobalEventDispatcher:
    """Test global event dispatcher functions."""
    
    def test_get_global_event_dispatcher(self):
        """Test getting global event dispatcher."""
        dispatcher1 = get_global_event_dispatcher()
        dispatcher2 = get_global_event_dispatcher()
        
        # Should be same instance
        assert dispatcher1 is dispatcher2
        assert isinstance(dispatcher1, EventDispatcher)
    
    def test_global_dispatcher_persistence(self):
        """Test that global dispatcher persists across calls."""
        dispatcher = get_global_event_dispatcher()
        handler = MockEventHandler("test_handler")
        dispatcher.add_handler(handler)
        
        # Get dispatcher again
        dispatcher2 = get_global_event_dispatcher()
        
        # Should have the handler
        handlers = dispatcher2.get_handlers()
        assert len(handlers) == 1
        assert handlers[0].name == "test_handler"


if __name__ == "__main__":
    pytest.main([__file__])