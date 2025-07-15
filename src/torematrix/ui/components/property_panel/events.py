"""Property event system for reactive updates"""

from typing import Dict, List, Callable, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass
from enum import Enum
from .models import PropertyChange

class PropertyEventType(Enum):
    VALUE_CHANGED = "value_changed"
    VALIDATION_FAILED = "validation_failed"
    PROPERTY_SELECTED = "property_selected"
    PROPERTY_FOCUSED = "property_focused"
    BATCH_UPDATE_START = "batch_update_start"
    BATCH_UPDATE_END = "batch_update_end"

@dataclass
class PropertyEvent:
    """Property event data"""
    event_type: PropertyEventType
    element_id: str
    property_name: str
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PropertyNotificationCenter(QObject):
    """Central hub for property change notifications"""
    
    # Core property signals
    property_changed = pyqtSignal(PropertyEvent)
    property_selected = pyqtSignal(str, str)  # element_id, property_name
    property_focused = pyqtSignal(str, str)   # element_id, property_name
    validation_failed = pyqtSignal(str, str, str)  # element_id, property_name, error
    
    # Batch operation signals
    batch_update_started = pyqtSignal(list)  # element_ids
    batch_update_completed = pyqtSignal(list, int)  # element_ids, count
    
    def __init__(self):
        super().__init__()
        self._listeners: Dict[PropertyEventType, List[Callable]] = {}
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._flush_batch)
        self._pending_events: List[PropertyEvent] = []
        self._batch_mode = False
    
    def register_listener(self, event_type: PropertyEventType, callback: Callable) -> None:
        """Register a listener for property events"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def unregister_listener(self, event_type: PropertyEventType, callback: Callable) -> None:
        """Unregister a property event listener"""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
            except ValueError:
                pass  # Callback not found, ignore
    
    def emit_property_event(self, event: PropertyEvent) -> None:
        """Emit a property event to all listeners"""
        if self._batch_mode:
            self._pending_events.append(event)
            self._batch_timer.start(50)  # 50ms batch delay
        else:
            self._dispatch_event(event)
    
    def emit_value_change(self, element_id: str, property_name: str, 
                         old_value: Any, new_value: Any, metadata: Dict[str, Any] = None) -> None:
        """Emit a property value change event"""
        event = PropertyEvent(
            event_type=PropertyEventType.VALUE_CHANGED,
            element_id=element_id,
            property_name=property_name,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {}
        )
        self.emit_property_event(event)
    
    def emit_validation_failed(self, element_id: str, property_name: str, 
                              error_message: str, metadata: Dict[str, Any] = None) -> None:
        """Emit a property validation failure event"""
        event = PropertyEvent(
            event_type=PropertyEventType.VALIDATION_FAILED,
            element_id=element_id,
            property_name=property_name,
            metadata={**(metadata or {}), 'error_message': error_message}
        )
        self.emit_property_event(event)
        self.validation_failed.emit(element_id, property_name, error_message)
    
    def emit_property_selected(self, element_id: str, property_name: str) -> None:
        """Emit a property selection event"""
        event = PropertyEvent(
            event_type=PropertyEventType.PROPERTY_SELECTED,
            element_id=element_id,
            property_name=property_name
        )
        self.emit_property_event(event)
        self.property_selected.emit(element_id, property_name)
    
    def start_batch_mode(self) -> None:
        """Start batch mode for efficient bulk updates"""
        self._batch_mode = True
        self._pending_events.clear()
        event = PropertyEvent(
            event_type=PropertyEventType.BATCH_UPDATE_START,
            element_id="",
            property_name=""
        )
        self._dispatch_event(event)
    
    def end_batch_mode(self) -> None:
        """End batch mode and flush pending events"""
        self._batch_mode = False
        self._flush_batch()
    
    def _dispatch_event(self, event: PropertyEvent) -> None:
        """Dispatch a single event to listeners"""
        # Emit Qt signal
        self.property_changed.emit(event)
        
        # Call registered listeners
        if event.event_type in self._listeners:
            for callback in self._listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in property event listener: {e}")
    
    def _flush_batch(self) -> None:
        """Flush all pending batch events"""
        if not self._pending_events:
            return
        
        # Group events by element for efficient processing
        events_by_element = {}
        for event in self._pending_events:
            element_id = event.element_id
            if element_id not in events_by_element:
                events_by_element[element_id] = []
            events_by_element[element_id].append(event)
        
        # Dispatch events
        for element_id, events in events_by_element.items():
            for event in events:
                self._dispatch_event(event)
        
        # Emit batch completion signal
        element_ids = list(events_by_element.keys())
        self.batch_update_completed.emit(element_ids, len(self._pending_events))
        
        # Emit batch end event
        event = PropertyEvent(
            event_type=PropertyEventType.BATCH_UPDATE_END,
            element_id="",
            property_name="",
            metadata={"event_count": len(self._pending_events)}
        )
        self._dispatch_event(event)
        
        self._pending_events.clear()
    
    def clear_listeners(self) -> None:
        """Clear all registered listeners"""
        self._listeners.clear()
    
    def get_listener_count(self, event_type: PropertyEventType) -> int:
        """Get number of listeners for an event type"""
        return len(self._listeners.get(event_type, []))

class PropertyEventManager:
    """High-level property event management"""
    
    def __init__(self, notification_center: PropertyNotificationCenter):
        self._notification_center = notification_center
        self._event_history: List[PropertyEvent] = []
        self._max_history = 1000
    
    def emit_value_change(self, element_id: str, property_name: str, 
                         old_value: Any, new_value: Any, metadata: Dict[str, Any] = None) -> None:
        """Emit a property value change event"""
        self._notification_center.emit_value_change(
            element_id, property_name, old_value, new_value, metadata
        )
    
    def emit_validation_failed(self, element_id: str, property_name: str, 
                              error_message: str, metadata: Dict[str, Any] = None) -> None:
        """Emit a property validation failure event"""
        self._notification_center.emit_validation_failed(
            element_id, property_name, error_message, metadata
        )
    
    def emit_property_selected(self, element_id: str, property_name: str) -> None:
        """Emit a property selection event"""
        self._notification_center.emit_property_selected(element_id, property_name)
    
    def get_event_history(self, element_id: Optional[str] = None, 
                         property_name: Optional[str] = None) -> List[PropertyEvent]:
        """Get filtered event history"""
        events = self._event_history
        if element_id:
            events = [e for e in events if e.element_id == element_id]
        if property_name:
            events = [e for e in events if e.property_name == property_name]
        return events
    
    def _add_to_history(self, event: PropertyEvent) -> None:
        """Add event to history with size limit"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
    
    def clear_event_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()