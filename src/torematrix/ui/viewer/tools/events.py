"""
Tool event definitions and event handling system.

This module provides event classes, event handling infrastructure, and
event dispatching for selection tools with comprehensive event management.
"""

import time
from typing import Any, Dict, List, Optional, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from .base import ToolState, SelectionResult


class EventType(Enum):
    """Event types for tool events."""
    MOUSE_PRESS = auto()
    MOUSE_MOVE = auto()
    MOUSE_RELEASE = auto()
    MOUSE_DOUBLE_CLICK = auto()
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    WHEEL = auto()
    TOOL_ACTIVATED = auto()
    TOOL_DEACTIVATED = auto()
    STATE_CHANGED = auto()
    SELECTION_CHANGED = auto()
    CURSOR_CHANGED = auto()
    PREVIEW_CHANGED = auto()
    ERROR_OCCURRED = auto()
    OPERATION_STARTED = auto()
    OPERATION_COMPLETED = auto()
    OPERATION_CANCELLED = auto()
    CUSTOM = auto()


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ToolEvent:
    """Base class for tool events."""
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    tool_id: str = ""
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False
    cancelled: bool = False
    
    def age(self) -> float:
        """Get age of event in seconds."""
        return time.time() - self.timestamp
    
    def mark_handled(self) -> None:
        """Mark event as handled."""
        self.handled = True
    
    def cancel(self) -> None:
        """Cancel event."""
        self.cancelled = True
    
    def is_mouse_event(self) -> bool:
        """Check if this is a mouse event."""
        return self.event_type in {
            EventType.MOUSE_PRESS,
            EventType.MOUSE_MOVE,
            EventType.MOUSE_RELEASE,
            EventType.MOUSE_DOUBLE_CLICK
        }
    
    def is_keyboard_event(self) -> bool:
        """Check if this is a keyboard event."""
        return self.event_type in {EventType.KEY_PRESS, EventType.KEY_RELEASE}
    
    def is_tool_event(self) -> bool:
        """Check if this is a tool-specific event."""
        return self.event_type in {
            EventType.TOOL_ACTIVATED,
            EventType.TOOL_DEACTIVATED,
            EventType.STATE_CHANGED,
            EventType.SELECTION_CHANGED,
            EventType.CURSOR_CHANGED,
            EventType.PREVIEW_CHANGED
        }
    
    def is_operation_event(self) -> bool:
        """Check if this is an operation event."""
        return self.event_type in {
            EventType.OPERATION_STARTED,
            EventType.OPERATION_COMPLETED,
            EventType.OPERATION_CANCELLED
        }


@dataclass
class MouseEvent(ToolEvent):
    """Mouse event for tools."""
    position: QPoint = field(default_factory=QPoint)
    button: Qt.MouseButton = Qt.MouseButton.NoButton
    buttons: Qt.MouseButton = Qt.MouseButton.NoButton
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    global_position: QPoint = field(default_factory=QPoint)
    
    def __post_init__(self):
        if self.event_type not in {
            EventType.MOUSE_PRESS,
            EventType.MOUSE_MOVE,
            EventType.MOUSE_RELEASE,
            EventType.MOUSE_DOUBLE_CLICK
        }:
            raise ValueError(f"Invalid event type for MouseEvent: {self.event_type}")


@dataclass
class KeyEvent(ToolEvent):
    """Keyboard event for tools."""
    key: int = 0
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    text: str = ""
    auto_repeat: bool = False
    
    def __post_init__(self):
        if self.event_type not in {EventType.KEY_PRESS, EventType.KEY_RELEASE}:
            raise ValueError(f"Invalid event type for KeyEvent: {self.event_type}")


@dataclass
class WheelEvent(ToolEvent):
    """Wheel event for tools."""
    position: QPoint = field(default_factory=QPoint)
    global_position: QPoint = field(default_factory=QPoint)
    pixel_delta: QPoint = field(default_factory=QPoint)
    angle_delta: QPoint = field(default_factory=QPoint)
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    
    def __post_init__(self):
        if self.event_type != EventType.WHEEL:
            raise ValueError(f"Invalid event type for WheelEvent: {self.event_type}")


@dataclass
class StateEvent(ToolEvent):
    """Tool state change event."""
    old_state: ToolState = ToolState.INACTIVE
    new_state: ToolState = ToolState.INACTIVE
    
    def __post_init__(self):
        if self.event_type != EventType.STATE_CHANGED:
            raise ValueError(f"Invalid event type for StateEvent: {self.event_type}")


@dataclass
class SelectionEvent(ToolEvent):
    """Selection change event."""
    selection: SelectionResult = field(default_factory=SelectionResult)
    previous_selection: Optional[SelectionResult] = None
    
    def __post_init__(self):
        if self.event_type not in {EventType.SELECTION_CHANGED, EventType.PREVIEW_CHANGED}:
            raise ValueError(f"Invalid event type for SelectionEvent: {self.event_type}")


@dataclass
class OperationEvent(ToolEvent):
    """Operation lifecycle event."""
    operation_id: str = ""
    operation_type: str = ""
    progress: float = 0.0
    error_message: str = ""
    result: Any = None
    
    def __post_init__(self):
        if self.event_type not in {
            EventType.OPERATION_STARTED,
            EventType.OPERATION_COMPLETED,
            EventType.OPERATION_CANCELLED,
            EventType.ERROR_OCCURRED
        }:
            raise ValueError(f"Invalid event type for OperationEvent: {self.event_type}")


@dataclass
class CustomEvent(ToolEvent):
    """Custom event for tool-specific needs."""
    name: str = ""
    data: Any = None
    
    def __post_init__(self):
        if self.event_type != EventType.CUSTOM:
            raise ValueError(f"Invalid event type for CustomEvent: {self.event_type}")


# Type alias for all event types
AnyToolEvent = Union[ToolEvent, MouseEvent, KeyEvent, WheelEvent, StateEvent, SelectionEvent, OperationEvent, CustomEvent]


class EventFilter:
    """Filter for tool events."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.event_types: Set[EventType] = set()
        self.tool_ids: Set[str] = set()
        self.priorities: Set[EventPriority] = set()
        self.min_age: float = 0.0
        self.max_age: float = float('inf')
        self.custom_filter: Optional[Callable[[AnyToolEvent], bool]] = None
    
    def add_event_type(self, event_type: EventType) -> None:
        """Add event type to filter."""
        self.event_types.add(event_type)
    
    def add_tool_id(self, tool_id: str) -> None:
        """Add tool ID to filter."""
        self.tool_ids.add(tool_id)
    
    def add_priority(self, priority: EventPriority) -> None:
        """Add priority to filter."""
        self.priorities.add(priority)
    
    def set_age_range(self, min_age: float, max_age: float) -> None:
        """Set age range for events."""
        self.min_age = min_age
        self.max_age = max_age
    
    def set_custom_filter(self, filter_func: Callable[[AnyToolEvent], bool]) -> None:
        """Set custom filter function."""
        self.custom_filter = filter_func
    
    def matches(self, event: AnyToolEvent) -> bool:
        """Check if event matches filter."""
        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check tool IDs
        if self.tool_ids and event.tool_id not in self.tool_ids:
            return False
        
        # Check priorities
        if self.priorities and event.priority not in self.priorities:
            return False
        
        # Check age range
        age = event.age()
        if age < self.min_age or age > self.max_age:
            return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True


class EventHandler:
    """Base class for event handlers."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.enabled = True
        self.priority = EventPriority.NORMAL
    
    def handle_event(self, event: AnyToolEvent) -> bool:
        """
        Handle event.
        
        Returns:
            True if event was handled and should not be passed to other handlers
        """
        if not self.enabled:
            return False
        
        return self._handle_event_impl(event)
    
    def _handle_event_impl(self, event: AnyToolEvent) -> bool:
        """Override this method to implement event handling."""
        return False
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable handler."""
        self.enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if handler is enabled."""
        return self.enabled


class EventDispatcher(QObject):
    """
    Event dispatcher for tool events.
    
    Manages event handlers, filters events, and dispatches events
    to registered handlers with priority support.
    """
    
    # Signals
    event_dispatched = pyqtSignal(object)  # AnyToolEvent
    handler_added = pyqtSignal(str)  # handler name
    handler_removed = pyqtSignal(str)  # handler name
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._handlers: List[EventHandler] = []
        self._filters: List[EventFilter] = []
        self._event_queue: List[AnyToolEvent] = []
        self._max_queue_size = 1000
        self._processing_events = False
        
        # Event statistics
        self._stats = {
            'events_dispatched': 0,
            'events_handled': 0,
            'events_dropped': 0,
            'handlers_count': 0
        }
    
    def add_handler(self, handler: EventHandler) -> None:
        """Add event handler."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            # Sort by priority (highest first)
            self._handlers.sort(key=lambda h: h.priority.value, reverse=True)
            self._stats['handlers_count'] = len(self._handlers)
            self.handler_added.emit(handler.name)
    
    def remove_handler(self, handler: EventHandler) -> bool:
        """Remove event handler."""
        try:
            self._handlers.remove(handler)
            self._stats['handlers_count'] = len(self._handlers)
            self.handler_removed.emit(handler.name)
            return True
        except ValueError:
            return False
    
    def remove_handler_by_name(self, name: str) -> bool:
        """Remove event handler by name."""
        for handler in self._handlers[:]:
            if handler.name == name:
                return self.remove_handler(handler)
        return False
    
    def add_filter(self, event_filter: EventFilter) -> None:
        """Add event filter."""
        if event_filter not in self._filters:
            self._filters.append(event_filter)
    
    def remove_filter(self, event_filter: EventFilter) -> bool:
        """Remove event filter."""
        try:
            self._filters.remove(event_filter)
            return True
        except ValueError:
            return False
    
    def dispatch_event(self, event: AnyToolEvent) -> bool:
        """
        Dispatch event to handlers.
        
        Returns:
            True if event was handled
        """
        if event.cancelled:
            return False
        
        # Apply filters
        for event_filter in self._filters:
            if not event_filter.matches(event):
                return False
        
        self._stats['events_dispatched'] += 1
        handled = False
        
        # Dispatch to handlers in priority order
        for handler in self._handlers:
            if handler.handle_event(event):
                handled = True
                event.mark_handled()
                if event.cancelled:
                    break
        
        if handled:
            self._stats['events_handled'] += 1
        
        self.event_dispatched.emit(event)
        return handled
    
    def queue_event(self, event: AnyToolEvent) -> bool:
        """Queue event for later processing."""
        if len(self._event_queue) >= self._max_queue_size:
            # Remove oldest event
            self._event_queue.pop(0)
            self._stats['events_dropped'] += 1
        
        self._event_queue.append(event)
        return True
    
    def process_queued_events(self) -> int:
        """Process all queued events."""
        if self._processing_events:
            return 0
        
        self._processing_events = True
        processed = 0
        
        try:
            while self._event_queue:
                event = self._event_queue.pop(0)
                self.dispatch_event(event)
                processed += 1
        finally:
            self._processing_events = False
        
        return processed
    
    def clear_queue(self) -> None:
        """Clear event queue."""
        self._event_queue.clear()
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._event_queue)
    
    def get_handlers(self) -> List[EventHandler]:
        """Get list of handlers."""
        return self._handlers.copy()
    
    def get_filters(self) -> List[EventFilter]:
        """Get list of filters."""
        return self._filters.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics."""
        return self._stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset event statistics."""
        self._stats = {
            'events_dispatched': 0,
            'events_handled': 0,
            'events_dropped': 0,
            'handlers_count': len(self._handlers)
        }
    
    def set_max_queue_size(self, size: int) -> None:
        """Set maximum queue size."""
        if size > 0:
            self._max_queue_size = size


class EventRecorder:
    """Records tool events for analysis and replay."""
    
    def __init__(self, max_events: int = 1000):
        self._recorded_events: List[AnyToolEvent] = []
        self._max_events = max_events
        self._recording = False
        self._start_time: Optional[float] = None
    
    def start_recording(self) -> None:
        """Start recording events."""
        self._recording = True
        self._start_time = time.time()
        self._recorded_events.clear()
    
    def stop_recording(self) -> None:
        """Stop recording events."""
        self._recording = False
    
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._recording
    
    def record_event(self, event: AnyToolEvent) -> None:
        """Record an event."""
        if not self._recording:
            return
        
        # Add relative timestamp
        if self._start_time:
            event.metadata['relative_time'] = event.timestamp - self._start_time
        
        self._recorded_events.append(event)
        
        # Trim if too many events
        if len(self._recorded_events) > self._max_events:
            self._recorded_events.pop(0)
    
    def get_recorded_events(self) -> List[AnyToolEvent]:
        """Get recorded events."""
        return self._recorded_events.copy()
    
    def clear_recording(self) -> None:
        """Clear recorded events."""
        self._recorded_events.clear()
    
    def save_recording(self, file_path: str) -> bool:
        """Save recording to file."""
        try:
            import json
            
            # Convert events to serializable format
            events_data = []
            for event in self._recorded_events:
                event_data = {
                    'type': event.event_type.name,
                    'timestamp': event.timestamp,
                    'tool_id': event.tool_id,
                    'priority': event.priority.name,
                    'metadata': event.metadata,
                    'handled': event.handled,
                    'cancelled': event.cancelled
                }
                
                # Add event-specific data
                if isinstance(event, MouseEvent):
                    event_data.update({
                        'position': [event.position.x(), event.position.y()],
                        'button': int(event.button),
                        'buttons': int(event.buttons),
                        'modifiers': int(event.modifiers)
                    })
                elif isinstance(event, KeyEvent):
                    event_data.update({
                        'key': event.key,
                        'modifiers': int(event.modifiers),
                        'text': event.text,
                        'auto_repeat': event.auto_repeat
                    })
                elif isinstance(event, StateEvent):
                    event_data.update({
                        'old_state': event.old_state.value,
                        'new_state': event.new_state.value
                    })
                
                events_data.append(event_data)
            
            with open(file_path, 'w') as f:
                json.dump({
                    'start_time': self._start_time,
                    'events': events_data
                }, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def load_recording(self, file_path: str) -> bool:
        """Load recording from file."""
        try:
            import json
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self._start_time = data.get('start_time')
            self._recorded_events.clear()
            
            # Convert back to event objects
            for event_data in data.get('events', []):
                # Create appropriate event type
                event_type = EventType[event_data['type']]
                
                if event_type in {EventType.MOUSE_PRESS, EventType.MOUSE_MOVE, 
                                  EventType.MOUSE_RELEASE, EventType.MOUSE_DOUBLE_CLICK}:
                    event = MouseEvent(
                        event_type=event_type,
                        timestamp=event_data['timestamp'],
                        tool_id=event_data['tool_id'],
                        priority=EventPriority[event_data['priority']],
                        metadata=event_data['metadata'],
                        position=QPoint(*event_data['position']),
                        button=Qt.MouseButton(event_data['button']),
                        buttons=Qt.MouseButton(event_data['buttons']),
                        modifiers=Qt.KeyboardModifier(event_data['modifiers'])
                    )
                elif event_type in {EventType.KEY_PRESS, EventType.KEY_RELEASE}:
                    event = KeyEvent(
                        event_type=event_type,
                        timestamp=event_data['timestamp'],
                        tool_id=event_data['tool_id'],
                        priority=EventPriority[event_data['priority']],
                        metadata=event_data['metadata'],
                        key=event_data['key'],
                        modifiers=Qt.KeyboardModifier(event_data['modifiers']),
                        text=event_data['text'],
                        auto_repeat=event_data['auto_repeat']
                    )
                elif event_type == EventType.STATE_CHANGED:
                    event = StateEvent(
                        event_type=event_type,
                        timestamp=event_data['timestamp'],
                        tool_id=event_data['tool_id'],
                        priority=EventPriority[event_data['priority']],
                        metadata=event_data['metadata'],
                        old_state=ToolState(event_data['old_state']),
                        new_state=ToolState(event_data['new_state'])
                    )
                else:
                    # Generic event
                    event = ToolEvent(
                        event_type=event_type,
                        timestamp=event_data['timestamp'],
                        tool_id=event_data['tool_id'],
                        priority=EventPriority[event_data['priority']],
                        metadata=event_data['metadata']
                    )
                
                event.handled = event_data['handled']
                event.cancelled = event_data['cancelled']
                self._recorded_events.append(event)
            
            return True
        except Exception:
            return False


# Global event dispatcher instance
_global_event_dispatcher: Optional[EventDispatcher] = None


def get_global_event_dispatcher() -> EventDispatcher:
    """Get global event dispatcher instance."""
    global _global_event_dispatcher
    if _global_event_dispatcher is None:
        _global_event_dispatcher = EventDispatcher()
    return _global_event_dispatcher


def create_mouse_event(event_type: EventType, position: QPoint, button: Qt.MouseButton = Qt.MouseButton.NoButton,
                      modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier, tool_id: str = "") -> MouseEvent:
    """Create mouse event."""
    return MouseEvent(
        event_type=event_type,
        position=position,
        button=button,
        modifiers=modifiers,
        tool_id=tool_id
    )


def create_key_event(event_type: EventType, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
                    text: str = "", tool_id: str = "") -> KeyEvent:
    """Create key event."""
    return KeyEvent(
        event_type=event_type,
        key=key,
        modifiers=modifiers,
        text=text,
        tool_id=tool_id
    )


def create_state_event(old_state: ToolState, new_state: ToolState, tool_id: str = "") -> StateEvent:
    """Create state change event."""
    return StateEvent(
        event_type=EventType.STATE_CHANGED,
        old_state=old_state,
        new_state=new_state,
        tool_id=tool_id
    )


def create_selection_event(selection: SelectionResult, tool_id: str = "", 
                          previous_selection: Optional[SelectionResult] = None) -> SelectionEvent:
    """Create selection change event."""
    return SelectionEvent(
        event_type=EventType.SELECTION_CHANGED,
        selection=selection,
        previous_selection=previous_selection,
        tool_id=tool_id
    )