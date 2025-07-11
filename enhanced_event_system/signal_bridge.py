#!/usr/bin/env python3
"""
Signal Bridge for TORE Matrix Labs V1 Enhancement

This module provides a bridge between V1 PyQt signals and V2-style events,
enabling seamless integration of the new event system with existing V1 code
without breaking changes.
"""

import logging
import weakref
from typing import Dict, Any, Optional, Callable, List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from .event_types_v1 import EventTypeV1, V1EventData, EventPriority
from .unified_event_bus import UnifiedEventBus


class SignalEventAdapter(QObject):
    """
    Adapter that converts between PyQt signals and V2 events.
    
    This adapter allows V1 PyQt signals to be automatically converted
    to V2 events and vice versa, maintaining compatibility.
    """
    
    # Generic signals for different data types
    generic_signal = pyqtSignal(dict)
    string_signal = pyqtSignal(str)
    int_signal = pyqtSignal(int)
    bool_signal = pyqtSignal(bool)
    coordinate_signal = pyqtSignal(dict)
    document_signal = pyqtSignal(str, dict)
    validation_signal = pyqtSignal(str, bool, dict)
    
    def __init__(self, event_bus: UnifiedEventBus):
        super().__init__()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Connect generic signals to event publishing
        self.generic_signal.connect(self._handle_generic_signal)
        self.string_signal.connect(self._handle_string_signal)
        self.int_signal.connect(self._handle_int_signal)
        self.bool_signal.connect(self._handle_bool_signal)
        self.coordinate_signal.connect(self._handle_coordinate_signal)
        self.document_signal.connect(self._handle_document_signal)
        self.validation_signal.connect(self._handle_validation_signal)
    
    @pyqtSlot(dict)
    def _handle_generic_signal(self, data: dict):
        """Handle generic dictionary signal."""
        event_type = data.get('event_type', EventTypeV1.APPLICATION_STARTED)
        sender = data.get('sender', 'qt_signal')
        event_data = data.get('data', {})
        
        if isinstance(event_type, str):
            try:
                event_type = EventTypeV1(event_type)
            except ValueError:
                event_type = EventTypeV1.APPLICATION_STARTED
        
        self.event_bus.publish(event_type, sender, event_data)
    
    @pyqtSlot(str)
    def _handle_string_signal(self, value: str):
        """Handle string signal."""
        self.event_bus.publish(
            EventTypeV1.STATUS_MESSAGE_CHANGED,
            "qt_signal",
            {"message": value}
        )
    
    @pyqtSlot(int)
    def _handle_int_signal(self, value: int):
        """Handle integer signal."""
        self.event_bus.publish(
            EventTypeV1.PROGRESS_UPDATED,
            "qt_signal",
            {"progress": value}
        )
    
    @pyqtSlot(bool)
    def _handle_bool_signal(self, value: bool):
        """Handle boolean signal."""
        self.event_bus.publish(
            EventTypeV1.WIDGET_ACTIVATED if value else EventTypeV1.WIDGET_DEACTIVATED,
            "qt_signal",
            {"active": value}
        )
    
    @pyqtSlot(dict)
    def _handle_coordinate_signal(self, coords: dict):
        """Handle coordinate signal."""
        self.event_bus.publish(
            EventTypeV1.PDF_COORDINATE_MAPPED,
            "qt_signal",
            {"coordinates": coords}
        )
    
    @pyqtSlot(str, dict)
    def _handle_document_signal(self, doc_id: str, data: dict):
        """Handle document-related signal."""
        event_data = data.copy()
        event_data['document_id'] = doc_id
        
        self.event_bus.publish(
            EventTypeV1.DOCUMENT_STATE_CHANGED,
            "qt_signal",
            event_data
        )
    
    @pyqtSlot(str, bool, dict)
    def _handle_validation_signal(self, validation_type: str, success: bool, data: dict):
        """Handle validation signal."""
        event_type = EventTypeV1.MANUAL_VALIDATION_COMPLETED if success else EventTypeV1.VALIDATION_ISSUE_DETECTED
        
        event_data = data.copy()
        event_data.update({
            'validation_type': validation_type,
            'success': success
        })
        
        self.event_bus.publish(event_type, "qt_signal", event_data)


class SignalBridge:
    """
    Bridge between V1 PyQt signals and V2 event system.
    
    This bridge enables:
    1. V1 signals → V2 events conversion
    2. V2 events → V1 signals conversion  
    3. Automatic mapping of common signal patterns
    4. Custom signal mapping registration
    """
    
    def __init__(self, event_bus: UnifiedEventBus):
        self.event_bus = event_bus
        self.adapter = SignalEventAdapter(event_bus)
        self.logger = logging.getLogger(__name__)
        
        # Signal mappings: PyQt signal → Event type
        self.signal_mappings: Dict[str, EventTypeV1] = {
            # Document signals
            'document_loaded': EventTypeV1.DOCUMENT_LOADED,
            'document_saved': EventTypeV1.DOCUMENT_SAVED,
            'document_processing_started': EventTypeV1.DOCUMENT_PROCESSING_STARTED,
            'document_processing_completed': EventTypeV1.DOCUMENT_PROCESSING_COMPLETED,
            
            # PDF signals
            'page_changed': EventTypeV1.PDF_PAGE_CHANGED,
            'zoom_changed': EventTypeV1.PDF_ZOOM_CHANGED,
            'highlight_pdf_location': EventTypeV1.PDF_LOCATION_HIGHLIGHTED,
            'highlight_pdf_text_selection': EventTypeV1.PDF_TEXT_SELECTION_HIGHLIGHTED,
            'cursor_pdf_location': EventTypeV1.PDF_CURSOR_LOCATION_UPDATED,
            
            # Validation signals
            'validation_completed': EventTypeV1.MANUAL_VALIDATION_COMPLETED,
            'validation_started': EventTypeV1.MANUAL_VALIDATION_STARTED,
            'qa_validation_completed': EventTypeV1.QA_VALIDATION_COMPLETED,
            
            # Area signals
            'area_selected': EventTypeV1.AREA_SELECTED,
            'area_created': EventTypeV1.AREA_CREATED,
            'area_modified': EventTypeV1.AREA_MODIFIED,
            'area_deleted': EventTypeV1.AREA_DELETED,
            
            # Project signals
            'project_loaded': EventTypeV1.PROJECT_LOADED,
            'project_saved': EventTypeV1.PROJECT_SAVED,
            
            # UI signals
            'tab_changed': EventTypeV1.TAB_CHANGED,
            'status_changed': EventTypeV1.STATUS_MESSAGE_CHANGED,
            'progress_updated': EventTypeV1.PROGRESS_UPDATED
        }
        
        # Reverse mappings: Event type → Signal name
        self.event_to_signal: Dict[EventTypeV1, str] = {
            v: k for k, v in self.signal_mappings.items()
        }
        
        # Connected signals tracking
        self.connected_signals: Dict[str, List[Any]] = {}
        
        # V2 → V1 signal emitters (created on demand)
        self.signal_emitters: Dict[str, QObject] = {}
        
        self.logger.info("Signal bridge initialized")
    
    def connect_v1_signal_to_event(self, 
                                   qt_object: QObject,
                                   signal_name: str,
                                   event_type: Optional[EventTypeV1] = None,
                                   sender_id: Optional[str] = None) -> bool:
        """
        Connect a V1 PyQt signal to publish V2 events.
        
        Args:
            qt_object: QObject that owns the signal
            signal_name: Name of the signal
            event_type: Event type to publish (auto-mapped if None)
            sender_id: ID of sender (uses object name if None)
            
        Returns:
            True if connected successfully
        """
        try:
            # Get event type from mapping or parameter
            if event_type is None:
                event_type = self.signal_mappings.get(signal_name)
                if event_type is None:
                    self.logger.warning(f"No event mapping for signal {signal_name}")
                    return False
            
            # Get sender ID
            if sender_id is None:
                sender_id = qt_object.objectName() or qt_object.__class__.__name__
            
            # Get the signal object
            signal = getattr(qt_object, signal_name, None)
            if signal is None:
                self.logger.error(f"Signal {signal_name} not found on {qt_object}")
                return False
            
            # Create callback to publish event
            def signal_callback(*args, **kwargs):
                # Convert signal arguments to event data
                data = self._convert_signal_args_to_data(signal_name, args, kwargs)
                self.event_bus.publish(event_type, sender_id, data)
            
            # Connect signal to callback
            signal.connect(signal_callback)
            
            # Track connection
            connection_key = f"{id(qt_object)}_{signal_name}"
            if connection_key not in self.connected_signals:
                self.connected_signals[connection_key] = []
            self.connected_signals[connection_key].append({
                'object': weakref.ref(qt_object),
                'signal_name': signal_name,
                'event_type': event_type,
                'sender_id': sender_id,
                'callback': signal_callback
            })
            
            self.logger.debug(f"Connected signal {signal_name} → {event_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect signal {signal_name}: {e}")
            return False
    
    def connect_event_to_v1_signal(self,
                                   event_type: EventTypeV1,
                                   qt_object: QObject,
                                   signal_name: str) -> str:
        """
        Connect V2 events to emit V1 PyQt signals.
        
        Args:
            event_type: Event type to listen for
            qt_object: QObject that owns the signal to emit
            signal_name: Signal to emit when event occurs
            
        Returns:
            Subscription ID
        """
        def event_callback(event: V1EventData):
            try:
                # Get the signal
                signal = getattr(qt_object, signal_name, None)
                if signal is None:
                    self.logger.error(f"Signal {signal_name} not found on {qt_object}")
                    return
                
                # Convert event data to signal arguments
                args = self._convert_event_data_to_signal_args(signal_name, event.data)
                
                # Emit signal
                if args:
                    signal.emit(*args)
                else:
                    signal.emit()
                    
            except Exception as e:
                self.logger.error(f"Failed to emit signal {signal_name}: {e}")
        
        # Subscribe to event
        subscriber_id = self.event_bus.subscribe(event_type, event_callback)
        
        self.logger.debug(f"Connected event {event_type.value} → signal {signal_name}")
        return subscriber_id
    
    def auto_connect_widget(self, widget: QObject) -> int:
        """
        Automatically connect common widget signals to events.
        
        Args:
            widget: Widget to auto-connect
            
        Returns:
            Number of signals connected
        """
        connected_count = 0
        widget_name = widget.__class__.__name__
        
        # Common signal patterns to look for
        common_signals = [
            'document_loaded', 'document_saved', 'document_processing_started',
            'document_processing_completed', 'page_changed', 'zoom_changed',
            'highlight_pdf_location', 'highlight_pdf_text_selection',
            'cursor_pdf_location', 'validation_completed', 'validation_started',
            'area_selected', 'area_created', 'area_modified', 'area_deleted',
            'project_loaded', 'project_saved', 'tab_changed', 'status_changed'
        ]
        
        for signal_name in common_signals:
            if hasattr(widget, signal_name):
                if self.connect_v1_signal_to_event(widget, signal_name):
                    connected_count += 1
        
        self.logger.info(f"Auto-connected {connected_count} signals for {widget_name}")
        return connected_count
    
    def _convert_signal_args_to_data(self, signal_name: str, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Convert PyQt signal arguments to event data."""
        data = {}
        
        # Add all arguments as indexed data
        for i, arg in enumerate(args):
            data[f'arg_{i}'] = arg
        
        # Add keyword arguments
        data.update(kwargs)
        
        # Special handling for known signals
        if signal_name == 'highlight_pdf_location' and len(args) >= 1:
            data['coordinates'] = args[0] if isinstance(args[0], dict) else {}
        elif signal_name == 'highlight_pdf_text_selection' and len(args) >= 2:
            data['text_selection'] = args[0] if isinstance(args[0], str) else ""
            data['coordinates'] = args[1] if isinstance(args[1], dict) else {}
        elif signal_name == 'page_changed' and len(args) >= 1:
            data['page_number'] = args[0] if isinstance(args[0], int) else 1
        elif signal_name == 'document_loaded' and len(args) >= 1:
            data['document_id'] = args[0] if isinstance(args[0], str) else ""
        
        return data
    
    def _convert_event_data_to_signal_args(self, signal_name: str, event_data: Dict[str, Any]) -> List[Any]:
        """Convert event data to PyQt signal arguments."""
        # Extract arguments based on signal name patterns
        if signal_name == 'highlight_pdf_location':
            return [event_data.get('coordinates', {})]
        elif signal_name == 'highlight_pdf_text_selection':
            return [
                event_data.get('text_selection', ''),
                event_data.get('coordinates', {})
            ]
        elif signal_name == 'page_changed':
            return [event_data.get('page_number', 1)]
        elif signal_name == 'document_loaded':
            return [event_data.get('document_id', '')]
        elif signal_name == 'validation_completed':
            return [
                event_data.get('validation_type', ''),
                event_data.get('success', True),
                event_data
            ]
        else:
            # Generic conversion - extract indexed arguments
            args = []
            i = 0
            while f'arg_{i}' in event_data:
                args.append(event_data[f'arg_{i}'])
                i += 1
            return args
    
    def register_signal_mapping(self, signal_name: str, event_type: EventTypeV1):
        """Register a custom signal → event mapping."""
        self.signal_mappings[signal_name] = event_type
        self.event_to_signal[event_type] = signal_name
        self.logger.debug(f"Registered mapping: {signal_name} → {event_type.value}")
    
    def unregister_signal_mapping(self, signal_name: str):
        """Unregister a signal mapping."""
        if signal_name in self.signal_mappings:
            event_type = self.signal_mappings[signal_name]
            del self.signal_mappings[signal_name]
            if event_type in self.event_to_signal:
                del self.event_to_signal[event_type]
            self.logger.debug(f"Unregistered mapping: {signal_name}")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about current connections."""
        active_connections = {}
        
        for conn_key, connections in self.connected_signals.items():
            active_conns = []
            for conn in connections:
                obj_ref = conn['object']
                if obj_ref() is not None:  # Object still alive
                    active_conns.append({
                        'signal_name': conn['signal_name'],
                        'event_type': conn['event_type'].value,
                        'sender_id': conn['sender_id']
                    })
            
            if active_conns:
                active_connections[conn_key] = active_conns
        
        return {
            'total_mappings': len(self.signal_mappings),
            'active_connections': len(active_connections),
            'signal_mappings': {k: v.value for k, v in self.signal_mappings.items()},
            'connections': active_connections
        }
    
    def cleanup_dead_connections(self):
        """Clean up connections to deleted objects."""
        cleaned_count = 0
        
        for conn_key in list(self.connected_signals.keys()):
            connections = self.connected_signals[conn_key]
            active_connections = []
            
            for conn in connections:
                obj_ref = conn['object']
                if obj_ref() is not None:  # Object still alive
                    active_connections.append(conn)
                else:
                    cleaned_count += 1
            
            if active_connections:
                self.connected_signals[conn_key] = active_connections
            else:
                del self.connected_signals[conn_key]
        
        if cleaned_count > 0:
            self.logger.debug(f"Cleaned up {cleaned_count} dead signal connections")
        
        return cleaned_count