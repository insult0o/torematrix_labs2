"""
Qt-JavaScript communication bridge for PDF.js integration.

This module provides bidirectional communication between Qt and PDF.js
using QWebChannel for element highlighting, events, and data exchange.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QVariant
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


@dataclass
class ElementCoordinate:
    """Represents an element's coordinate in PDF space."""
    page: int
    x: float
    y: float
    width: float
    height: float
    element_id: str
    element_type: str


@dataclass
class HighlightStyle:
    """Styling for element highlighting."""
    color: str = "#ff0000"
    opacity: float = 0.3
    border_width: int = 2
    border_color: str = "#cc0000"


@dataclass
class SelectionEvent:
    """Represents a selection event from PDF.js."""
    coordinates: ElementCoordinate
    timestamp: float
    selection_type: str  # 'click', 'hover', 'text_selection'
    text_content: Optional[str] = None


class PDFBridge(QObject):
    """
    Bidirectional communication bridge between Qt and PDF.js.
    
    This bridge handles:
    - Element highlighting and selection
    - Event forwarding to the main Event Bus
    - Performance monitoring data collection
    - Feature enablement communication
    
    Signals:
        element_selected: Emitted when user selects an element
        element_highlighted: Emitted when element is highlighted
        performance_event: Emitted for performance monitoring
        feature_event: Emitted for feature interactions
        error_occurred: Emitted when bridge errors occur
    """
    
    # Signals for event forwarding
    element_selected = pyqtSignal(SelectionEvent)
    element_highlighted = pyqtSignal(list)  # List[ElementCoordinate]
    performance_event = pyqtSignal(str, dict)  # event_type, data
    feature_event = pyqtSignal(str, dict)  # feature_name, data
    error_occurred = pyqtSignal(str, str)  # error_code, error_message
    
    def __init__(self, pdf_viewer: QWebEngineView):
        """Initialize PDF bridge."""
        super().__init__()
        
        self.pdf_viewer = pdf_viewer
        self.web_channel: Optional[QWebChannel] = None
        
        # State management
        self.is_connected = False
        self.pending_highlights: List[ElementCoordinate] = []
        self.message_queue: List[Dict[str, Any]] = []
        
        # Event Bus integration
        self._event_bus = None
        
        # Initialize bridge
        self._setup_web_channel()
        
        logger.info("PDFBridge initialized")
    
    def _setup_web_channel(self) -> None:
        """Setup QWebChannel for Qt-JS communication."""
        try:
            # Create web channel
            self.web_channel = QWebChannel()
            
            # Register this object as bridge
            self.web_channel.registerObject("pdfBridge", self)
            
            # Set channel on web page
            self.pdf_viewer.page().setWebChannel(self.web_channel)
            
            logger.info("QWebChannel setup complete")
            
        except Exception as e:
            error_msg = f"Failed to setup web channel: {e}"
            logger.error(error_msg)
            self.error_occurred.emit("CHANNEL_SETUP_FAILED", error_msg)
    
    @pyqtSlot()
    def bridge_ready(self) -> None:
        """Called from JavaScript when bridge is ready."""
        self.is_connected = True
        logger.info("Bridge connection established")
        
        # Process pending highlights
        for highlight in self.pending_highlights:
            self.highlight_element(highlight)
        self.pending_highlights.clear()
        
        # Process message queue
        for message in self.message_queue:
            self._send_message(message)
        self.message_queue.clear()
    
    @pyqtSlot(str)
    def on_element_selected(self, event_data: str) -> None:
        """Handle element selection from JavaScript."""
        try:
            data = json.loads(event_data)
            
            # Create selection event
            coordinates = ElementCoordinate(**data['coordinates'])
            selection_event = SelectionEvent(
                coordinates=coordinates,
                timestamp=data.get('timestamp', 0),
                selection_type=data.get('type', 'click'),
                text_content=data.get('text')
            )
            
            # Emit signal
            self.element_selected.emit(selection_event)
            
            # Forward to Event Bus
            if self._event_bus:
                self._forward_to_event_bus('pdf.element_selected', {
                    'coordinates': asdict(coordinates),
                    'selection_type': selection_event.selection_type,
                    'text_content': selection_event.text_content
                })
            
            logger.debug(f"Element selected: {coordinates.element_id}")
            
        except Exception as e:
            error_msg = f"Failed to process element selection: {e}"
            logger.error(error_msg)
            self.error_occurred.emit("SELECTION_PROCESSING_FAILED", error_msg)
    
    @pyqtSlot(str)
    def on_performance_data(self, perf_data: str) -> None:
        """Handle performance data from JavaScript."""
        try:
            data = json.loads(perf_data)
            
            # Emit performance signal
            self.performance_event.emit(data['type'], data['metrics'])
            
            # Forward to Event Bus
            if self._event_bus:
                self._forward_to_event_bus('pdf.performance', data)
            
            logger.debug(f"Performance data received: {data['type']}")
            
        except Exception as e:
            error_msg = f"Failed to process performance data: {e}"
            logger.error(error_msg)
    
    @pyqtSlot(str)
    def on_feature_event(self, feature_data: str) -> None:
        """Handle feature events from JavaScript."""
        try:
            data = json.loads(feature_data)
            
            # Emit feature signal
            self.feature_event.emit(data['feature'], data['data'])
            
            # Forward to Event Bus
            if self._event_bus:
                self._forward_to_event_bus('pdf.feature', data)
            
            logger.debug(f"Feature event received: {data['feature']}")
            
        except Exception as e:
            error_msg = f"Failed to process feature event: {e}"
            logger.error(error_msg)
    
    def highlight_elements(self, elements: List[ElementCoordinate], style: Optional[HighlightStyle] = None) -> None:
        """Highlight elements in the PDF viewer."""
        if not elements:
            return
        
        if style is None:
            style = HighlightStyle()
        
        message = {
            'type': 'highlight_elements',
            'elements': [asdict(elem) for elem in elements],
            'style': asdict(style)
        }
        
        if self.is_connected:
            self._send_message(message)
        else:
            # Queue for later
            self.pending_highlights.extend(elements)
            self.message_queue.append(message)
        
        # Emit signal
        self.element_highlighted.emit(elements)
        
        logger.debug(f"Highlighting {len(elements)} elements")
    
    def highlight_element(self, element: ElementCoordinate, style: Optional[HighlightStyle] = None) -> None:
        """Highlight a single element."""
        self.highlight_elements([element], style)
    
    def clear_highlights(self) -> None:
        """Clear all highlights in the PDF viewer."""
        message = {'type': 'clear_highlights'}
        
        if self.is_connected:
            self._send_message(message)
        else:
            self.message_queue.append(message)
        
        logger.debug("Clearing all highlights")
    
    def send_feature_command(self, feature: str, command: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Send feature command to JavaScript."""
        message = {
            'type': 'feature_command',
            'feature': feature,
            'command': command,
            'data': data or {}
        }
        
        if self.is_connected:
            self._send_message(message)
        else:
            self.message_queue.append(message)
        
        logger.debug(f"Feature command sent: {feature}.{command}")
    
    def _send_message(self, message: Dict[str, Any]) -> None:
        """Send message to JavaScript."""
        try:
            js_code = f"""
                if (typeof window.handleBridgeMessage === 'function') {{
                    window.handleBridgeMessage({json.dumps(message)});
                }} else {{
                    console.error('Bridge message handler not ready');
                }}
            """
            
            self.pdf_viewer.page().runJavaScript(js_code)
            
        except Exception as e:
            error_msg = f"Failed to send message to JavaScript: {e}"
            logger.error(error_msg)
            self.error_occurred.emit("MESSAGE_SEND_FAILED", error_msg)
    
    def connect_to_event_bus(self, event_bus) -> None:
        """Connect bridge to the main Event Bus."""
        self._event_bus = event_bus
        logger.info("Bridge connected to Event Bus")
    
    def _forward_to_event_bus(self, event_type: str, data: Dict[str, Any]) -> None:
        """Forward event to Event Bus."""
        if self._event_bus:
            try:
                # Create event for Event Bus
                from torematrix.core.events import Event, EventPriority
                
                event = Event(
                    type=event_type,
                    source="pdf_bridge",
                    data=data,
                    priority=EventPriority.NORMAL
                )
                
                self._event_bus.emit(event)
                
            except Exception as e:
                logger.error(f"Failed to forward event to Event Bus: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get bridge connection status."""
        return {
            'is_connected': self.is_connected,
            'pending_highlights': len(self.pending_highlights),
            'queued_messages': len(self.message_queue),
            'event_bus_connected': self._event_bus is not None
        }
    
    def disconnect(self) -> None:
        """Disconnect bridge and cleanup."""
        self.is_connected = False
        self.pending_highlights.clear()
        self.message_queue.clear()
        
        if self.web_channel:
            self.web_channel.deregisterObject(self)
        
        logger.info("Bridge disconnected")
    
    # Agent 3 Performance Integration
    def send_performance_command(self, command: str, parameters: Dict[str, Any]) -> None:
        """Send performance command to JavaScript (Agent 3 integration).
        
        Args:
            command: Performance command to execute
            parameters: Command parameters
        """
        if not self.channel:
            return
            
        message = {
            'type': 'performance_command',
            'command': command,
            'parameters': parameters,
            'timestamp': time.time()
        }
        
        self.channel.send_message(json.dumps(message))
        logger.debug(f"Performance command sent: {command}")
    
    def handle_performance_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle performance event from JavaScript (Agent 3 integration).
        
        Args:
            event_type: Type of performance event
            data: Event data
        """
        # Emit performance signal for Agent 3 monitoring
        self.performance_event.emit(event_type, data)
        
        # Log performance events
        if event_type in ['page_load', 'page_render', 'memory_pressure']:
            logger.info(f"Performance event: {event_type} - {data}")
        else:
            logger.debug(f"Performance event: {event_type} - {data}")
    
    def get_performance_status(self) -> Dict[str, Any]:
        """Get current performance status (Agent 3 integration).
        
        Returns:
            Dictionary containing performance status
        """
        return {
            'bridge_connected': self.channel is not None,
            'message_queue_size': len(self.message_queue),
            'last_message_time': self.last_message_time,
            'performance_monitoring': True
        }