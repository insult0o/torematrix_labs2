# Agent 2: PDF.js Qt-JavaScript Bridge
**Issue #16.2 | Sub-Issue #125 | Days 2-3 | Critical Bridge Communication**

## 🎯 Your Mission
You are **Agent 2**, responsible for implementing the bidirectional communication bridge between Qt and PDF.js using QWebChannel. Your work enables element highlighting, event forwarding to the Event Bus, and seamless data exchange between Python and JavaScript. This bridge is **essential** for Agent 3's performance monitoring and Agent 4's advanced features.

## 📋 Your Specific Tasks

### Phase 1: QWebChannel Setup & Configuration
#### 1.1 Bridge Architecture Setup
Create `src/torematrix/integrations/pdf/bridge.py`:

```python
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
```

#### 1.2 Communication Protocol Implementation
Create `src/torematrix/integrations/pdf/communication.py`:

```python
"""
Communication protocols and message handling for PDF.js bridge.

This module defines the message formats, protocols, and event handling
for reliable Qt-JavaScript communication.
"""

from __future__ import annotations

import json
import logging
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Union, Protocol
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of bridge messages."""
    HIGHLIGHT_ELEMENTS = "highlight_elements"
    CLEAR_HIGHLIGHTS = "clear_highlights"
    ELEMENT_SELECTED = "element_selected"
    FEATURE_COMMAND = "feature_command"
    PERFORMANCE_DATA = "performance_data"
    ERROR_REPORT = "error_report"
    BRIDGE_READY = "bridge_ready"


@dataclass
class BridgeMessage:
    """Base message structure for bridge communication."""
    type: str
    timestamp: float
    message_id: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BridgeMessage':
        """Deserialize message from JSON."""
        data = json.loads(json_str)
        return cls(**data)


class MessageValidator:
    """Validates bridge messages for security and correctness."""
    
    @staticmethod
    def validate_highlight_message(data: Dict[str, Any]) -> bool:
        """Validate highlight message format."""
        required_fields = ['elements', 'style']
        if not all(field in data for field in required_fields):
            return False
        
        # Validate elements structure
        if not isinstance(data['elements'], list):
            return False
        
        for element in data['elements']:
            if not isinstance(element, dict):
                return False
            
            required_element_fields = ['page', 'x', 'y', 'width', 'height', 'element_id']
            if not all(field in element for field in required_element_fields):
                return False
        
        return True
    
    @staticmethod
    def validate_selection_message(data: Dict[str, Any]) -> bool:
        """Validate selection message format."""
        required_fields = ['coordinates', 'timestamp', 'type']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def sanitize_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message data to prevent XSS and injection."""
        # Deep copy and sanitize
        import copy
        sanitized = copy.deepcopy(data)
        
        # Remove potentially dangerous keys
        dangerous_keys = ['__proto__', 'constructor', 'prototype']
        
        def clean_dict(d):
            if isinstance(d, dict):
                for key in dangerous_keys:
                    d.pop(key, None)
                for value in d.values():
                    clean_dict(value)
            elif isinstance(d, list):
                for item in d:
                    clean_dict(item)
        
        clean_dict(sanitized)
        return sanitized


class MessageQueue:
    """Manages message queuing and retry logic."""
    
    def __init__(self, max_retries: int = 3, max_queue_size: int = 1000):
        self.max_retries = max_retries
        self.max_queue_size = max_queue_size
        self.queue: List[BridgeMessage] = []
        self.retry_counts: Dict[str, int] = {}
    
    def enqueue(self, message: BridgeMessage) -> bool:
        """Add message to queue."""
        if len(self.queue) >= self.max_queue_size:
            logger.warning("Message queue full, dropping oldest message")
            self.queue.pop(0)
        
        self.queue.append(message)
        return True
    
    def dequeue(self) -> Optional[BridgeMessage]:
        """Get next message from queue."""
        return self.queue.pop(0) if self.queue else None
    
    def retry_message(self, message: BridgeMessage) -> bool:
        """Handle message retry logic."""
        retry_count = self.retry_counts.get(message.message_id, 0)
        
        if retry_count < self.max_retries:
            self.retry_counts[message.message_id] = retry_count + 1
            self.queue.insert(0, message)  # Prioritize retry
            return True
        else:
            # Max retries reached
            logger.error(f"Message {message.message_id} failed after {retry_count} retries")
            self.retry_counts.pop(message.message_id, None)
            return False
    
    def clear(self) -> None:
        """Clear all messages and retry counts."""
        self.queue.clear()
        self.retry_counts.clear()


class EventForwarder:
    """Forwards bridge events to the main Event Bus."""
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.event_filters: List[Callable] = []
    
    def add_filter(self, filter_func: Callable[[str, Dict[str, Any]], bool]) -> None:
        """Add event filter function."""
        self.event_filters.append(filter_func)
    
    def forward_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Forward event to Event Bus with filtering."""
        # Apply filters
        for filter_func in self.event_filters:
            if not filter_func(event_type, data):
                logger.debug(f"Event {event_type} filtered out")
                return False
        
        if self.event_bus:
            try:
                from torematrix.core.events import Event, EventPriority
                
                event = Event(
                    type=event_type,
                    source="pdf_bridge",
                    data=data,
                    priority=EventPriority.NORMAL
                )
                
                self.event_bus.emit(event)
                return True
                
            except Exception as e:
                logger.error(f"Failed to forward event: {e}")
                return False
        
        return False
```

### Phase 2: JavaScript Bridge Implementation
Create `resources/pdfjs/bridge.js`:

```javascript
/**
 * JavaScript bridge for Qt-PDF.js communication
 * Handles bidirectional communication with PyQt6
 */

class PDFJSBridge {
    constructor() {
        this.isConnected = false;
        this.messageQueue = [];
        this.highlightOverlays = [];
        this.eventListeners = new Map();
        
        // Initialize bridge
        this.init();
    }
    
    async init() {
        // Wait for Qt WebChannel to be available
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            await this.setupWebChannel();
        } else {
            // Retry after delay
            setTimeout(() => this.init(), 100);
        }
    }
    
    async setupWebChannel() {
        try {
            // Create QWebChannel connection
            this.channel = new QWebChannel(qt.webChannelTransport, (channel) => {
                this.bridge = channel.objects.pdfBridge;
                
                if (this.bridge) {
                    this.isConnected = true;
                    console.log('Bridge connected to Qt');
                    
                    // Notify Qt that bridge is ready
                    this.bridge.bridge_ready();
                    
                    // Process queued messages
                    this.processMessageQueue();
                    
                    // Setup PDF event listeners
                    this.setupPDFEventListeners();
                }
            });
            
        } catch (error) {
            console.error('Failed to setup web channel:', error);
        }
    }
    
    setupPDFEventListeners() {
        // Element selection events
        document.addEventListener('click', (event) => {
            this.handleElementClick(event);
        });
        
        document.addEventListener('mouseover', (event) => {
            this.handleElementHover(event);
        });
        
        // Text selection events
        document.addEventListener('selectionchange', () => {
            this.handleTextSelection();
        });
        
        // Performance monitoring
        this.setupPerformanceMonitoring();
    }
    
    handleElementClick(event) {
        const element = this.getElementFromEvent(event);
        if (element) {
            const selectionData = {
                coordinates: element,
                timestamp: Date.now(),
                type: 'click',
                text: this.getElementText(event.target)
            };
            
            this.sendToQt('element_selected', selectionData);
        }
    }
    
    handleElementHover(event) {
        const element = this.getElementFromEvent(event);
        if (element) {
            const selectionData = {
                coordinates: element,
                timestamp: Date.now(),
                type: 'hover'
            };
            
            this.sendToQt('element_selected', selectionData);
        }
    }
    
    handleTextSelection() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const element = this.getElementFromRange(range);
            
            if (element) {
                const selectionData = {
                    coordinates: element,
                    timestamp: Date.now(),
                    type: 'text_selection',
                    text: selection.toString()
                };
                
                this.sendToQt('element_selected', selectionData);
            }
        }
    }
    
    getElementFromEvent(event) {
        const target = event.target;
        const page = this.getPageFromElement(target);
        const rect = target.getBoundingClientRect();
        
        return {
            page: page,
            x: rect.left,
            y: rect.top,
            width: rect.width,
            height: rect.height,
            element_id: target.id || this.generateElementId(target),
            element_type: target.tagName.toLowerCase()
        };
    }
    
    getElementFromRange(range) {
        const rect = range.getBoundingClientRect();
        const element = range.commonAncestorContainer;
        const page = this.getPageFromElement(element);
        
        return {
            page: page,
            x: rect.left,
            y: rect.top,
            width: rect.width,
            height: rect.height,
            element_id: this.generateElementId(element),
            element_type: 'text_selection'
        };
    }
    
    getPageFromElement(element) {
        // Find the page container for this element
        let current = element;
        while (current && current.parentNode) {
            if (current.hasAttribute && current.hasAttribute('data-page')) {
                return parseInt(current.getAttribute('data-page'));
            }
            current = current.parentNode;
        }
        return currentPage || 1;
    }
    
    generateElementId(element) {
        if (element.id) return element.id;
        
        // Generate ID based on element position and content
        const rect = element.getBoundingClientRect();
        const content = element.textContent ? element.textContent.slice(0, 50) : '';
        return `elem_${rect.left}_${rect.top}_${content.replace(/\s+/g, '_')}`;
    }
    
    getElementText(element) {
        return element.textContent || element.innerText || '';
    }
    
    // Message handling from Qt
    handleBridgeMessage(message) {
        try {
            const data = typeof message === 'string' ? JSON.parse(message) : message;
            
            switch (data.type) {
                case 'highlight_elements':
                    this.highlightElements(data.elements, data.style);
                    break;
                
                case 'clear_highlights':
                    this.clearHighlights();
                    break;
                
                case 'feature_command':
                    this.handleFeatureCommand(data.feature, data.command, data.data);
                    break;
                
                default:
                    console.warn('Unknown message type:', data.type);
            }
            
        } catch (error) {
            console.error('Error handling bridge message:', error);
        }
    }
    
    highlightElements(elements, style) {
        elements.forEach(element => {
            this.highlightElement(element, style);
        });
    }
    
    highlightElement(element, style) {
        const overlay = document.createElement('div');
        overlay.className = 'pdf-highlight-overlay';
        overlay.style.cssText = `
            position: absolute;
            left: ${element.x}px;
            top: ${element.y}px;
            width: ${element.width}px;
            height: ${element.height}px;
            background-color: ${style.color};
            opacity: ${style.opacity};
            border: ${style.border_width}px solid ${style.border_color};
            pointer-events: none;
            z-index: 1000;
        `;
        
        // Add to appropriate page container
        const pageContainer = document.querySelector(`[data-page="${element.page}"]`);
        if (pageContainer) {
            pageContainer.appendChild(overlay);
            this.highlightOverlays.push(overlay);
        }
    }
    
    clearHighlights() {
        this.highlightOverlays.forEach(overlay => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        });
        this.highlightOverlays = [];
    }
    
    handleFeatureCommand(feature, command, data) {
        // Dispatch to feature handlers (Agent 4 will implement)
        const event = new CustomEvent('pdfFeatureCommand', {
            detail: { feature, command, data }
        });
        document.dispatchEvent(event);
    }
    
    setupPerformanceMonitoring() {
        // Monitor render performance
        let renderStartTime = null;
        
        // Hook into PDF.js render tasks
        const originalRender = renderPage;
        if (typeof originalRender === 'function') {
            window.renderPage = async function(pageNum) {
                renderStartTime = performance.now();
                
                try {
                    const result = await originalRender.call(this, pageNum);
                    
                    const renderTime = performance.now() - renderStartTime;
                    bridge.sendPerformanceData('page_render', {
                        page: pageNum,
                        render_time: renderTime,
                        timestamp: Date.now()
                    });
                    
                    return result;
                } catch (error) {
                    const renderTime = performance.now() - renderStartTime;
                    bridge.sendPerformanceData('page_render_error', {
                        page: pageNum,
                        render_time: renderTime,
                        error: error.message,
                        timestamp: Date.now()
                    });
                    throw error;
                }
            };
        }
        
        // Monitor memory usage
        if ('memory' in performance) {
            setInterval(() => {
                this.sendPerformanceData('memory_usage', {
                    used: performance.memory.usedJSHeapSize,
                    total: performance.memory.totalJSHeapSize,
                    limit: performance.memory.jsHeapSizeLimit,
                    timestamp: Date.now()
                });
            }, 5000); // Every 5 seconds
        }
    }
    
    sendToQt(method, data) {
        if (this.isConnected && this.bridge) {
            try {
                const jsonData = JSON.stringify(data);
                
                switch (method) {
                    case 'element_selected':
                        this.bridge.on_element_selected(jsonData);
                        break;
                    case 'performance_data':
                        this.bridge.on_performance_data(jsonData);
                        break;
                    case 'feature_event':
                        this.bridge.on_feature_event(jsonData);
                        break;
                    default:
                        console.warn('Unknown Qt method:', method);
                }
                
            } catch (error) {
                console.error('Error sending to Qt:', error);
            }
        } else {
            // Queue message for later
            this.messageQueue.push({ method, data });
        }
    }
    
    sendPerformanceData(type, metrics) {
        this.sendToQt('performance_data', { type, metrics });
    }
    
    sendFeatureEvent(feature, data) {
        this.sendToQt('feature_event', { feature, data });
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const { method, data } = this.messageQueue.shift();
            this.sendToQt(method, data);
        }
    }
}

// Initialize bridge when page loads
let bridge = null;

document.addEventListener('DOMContentLoaded', () => {
    bridge = new PDFJSBridge();
});

// Global message handler for Qt
window.handleBridgeMessage = function(message) {
    if (bridge) {
        bridge.handleBridgeMessage(message);
    }
};

console.log('PDF.js bridge script loaded');
```

### Phase 3: Agent 1 Integration
Update Agent 1's viewer to attach the bridge:

```python
# Add to PDFViewer class in viewer.py
def attach_bridge(self, bridge: PDFBridge) -> None:
    """Attach communication bridge for element highlighting and events."""
    self._bridge = bridge
    
    # Connect bridge to Event Bus if available
    if hasattr(self, '_event_bus') and self._event_bus:
        bridge.connect_to_event_bus(self._event_bus)
    
    # Connect bridge signals
    bridge.element_selected.connect(self._on_element_selected)
    bridge.performance_event.connect(self._on_performance_event)
    bridge.error_occurred.connect(self._on_bridge_error)
    
    logger.info("Bridge attached to PDFViewer")

def _on_element_selected(self, selection_event: SelectionEvent) -> None:
    """Handle element selection from bridge."""
    # Emit our own signal for UI components
    self.element_selected.emit(selection_event)

def _on_performance_event(self, event_type: str, data: dict) -> None:
    """Handle performance events from bridge."""
    # Forward to performance monitoring (Agent 3)
    if hasattr(self, '_performance_monitor'):
        self._performance_monitor.handle_bridge_event(event_type, data)

def _on_bridge_error(self, error_code: str, error_message: str) -> None:
    """Handle bridge errors."""
    logger.error(f"Bridge error {error_code}: {error_message}")
    self.load_error.emit(error_code, error_message)
```

### Phase 4: Testing & Integration
Create `tests/integration/pdf/test_bridge.py`:

```python
"""Integration tests for PDF.js bridge functionality."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebChannel import QWebChannel

from torematrix.integrations.pdf.viewer import PDFViewer
from torematrix.integrations.pdf.bridge import PDFBridge, ElementCoordinate, HighlightStyle


class TestPDFBridge:
    """Test PDF bridge functionality."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def mock_viewer(self, app):
        """Create mock PDF viewer."""
        viewer = Mock(spec=PDFViewer)
        viewer.page.return_value = Mock()
        viewer.page().setWebChannel = Mock()
        viewer.page().runJavaScript = Mock()
        return viewer
    
    @pytest.fixture
    def bridge(self, mock_viewer):
        """Create PDF bridge instance."""
        return PDFBridge(mock_viewer)
    
    def test_bridge_initialization(self, bridge, mock_viewer):
        """Test bridge initialization."""
        assert bridge.pdf_viewer == mock_viewer
        assert bridge.web_channel is not None
        assert not bridge.is_connected
        assert bridge.pending_highlights == []
        assert bridge.message_queue == []
    
    def test_web_channel_setup(self, bridge):
        """Test web channel setup."""
        assert bridge.web_channel is not None
        # Should have registered bridge object
        bridge.web_channel.registerObject.assert_called_with("pdfBridge", bridge)
    
    def test_bridge_ready_signal(self, bridge):
        """Test bridge ready signal handling."""
        # Add pending highlights
        element = ElementCoordinate(1, 10, 20, 100, 50, "test", "text")
        bridge.pending_highlights.append(element)
        
        # Add queued message
        message = {"type": "test", "data": {}}
        bridge.message_queue.append(message)
        
        # Call bridge_ready
        bridge.bridge_ready()
        
        assert bridge.is_connected
        assert bridge.pending_highlights == []
        assert bridge.message_queue == []
    
    def test_element_selection_handling(self, bridge):
        """Test element selection from JavaScript."""
        selection_data = {
            "coordinates": {
                "page": 1,
                "x": 10.0,
                "y": 20.0,
                "width": 100.0,
                "height": 50.0,
                "element_id": "test_element",
                "element_type": "text"
            },
            "timestamp": 1234567890,
            "type": "click",
            "text": "Sample text"
        }
        
        with patch.object(bridge, 'element_selected') as mock_signal:
            bridge.on_element_selected(json.dumps(selection_data))
            mock_signal.emit.assert_called_once()
    
    def test_highlight_elements(self, bridge):
        """Test element highlighting."""
        elements = [
            ElementCoordinate(1, 10, 20, 100, 50, "elem1", "text"),
            ElementCoordinate(1, 120, 70, 80, 30, "elem2", "image")
        ]
        style = HighlightStyle(color="#00ff00", opacity=0.5)
        
        # Mock connection
        bridge.is_connected = True
        
        with patch.object(bridge, '_send_message') as mock_send:
            bridge.highlight_elements(elements, style)
            mock_send.assert_called_once()
            
            # Check message structure
            call_args = mock_send.call_args[0][0]
            assert call_args['type'] == 'highlight_elements'
            assert len(call_args['elements']) == 2
            assert call_args['style']['color'] == "#00ff00"
    
    def test_performance_data_handling(self, bridge):
        """Test performance data from JavaScript."""
        perf_data = {
            "type": "page_render",
            "metrics": {
                "page": 1,
                "render_time": 150.5,
                "timestamp": 1234567890
            }
        }
        
        with patch.object(bridge, 'performance_event') as mock_signal:
            bridge.on_performance_data(json.dumps(perf_data))
            mock_signal.emit.assert_called_with("page_render", perf_data["metrics"])
    
    def test_event_bus_integration(self, bridge):
        """Test Event Bus integration."""
        mock_event_bus = Mock()
        bridge.connect_to_event_bus(mock_event_bus)
        
        assert bridge._event_bus == mock_event_bus
        
        # Test event forwarding
        with patch('torematrix.core.events.Event') as mock_event_class:
            bridge._forward_to_event_bus('test.event', {'data': 'test'})
            mock_event_bus.emit.assert_called_once()
    
    def test_bridge_disconnection(self, bridge):
        """Test bridge disconnection and cleanup."""
        bridge.is_connected = True
        bridge.pending_highlights.append(
            ElementCoordinate(1, 10, 20, 100, 50, "test", "text")
        )
        bridge.message_queue.append({"type": "test"})
        
        bridge.disconnect()
        
        assert not bridge.is_connected
        assert bridge.pending_highlights == []
        assert bridge.message_queue == []
    
    def test_error_handling(self, bridge):
        """Test error handling in bridge operations."""
        # Test invalid JSON in element selection
        with patch.object(bridge, 'error_occurred') as mock_error:
            bridge.on_element_selected("invalid json")
            mock_error.emit.assert_called()
    
    def test_message_queuing_when_disconnected(self, bridge):
        """Test message queuing when bridge is not connected."""
        assert not bridge.is_connected
        
        element = ElementCoordinate(1, 10, 20, 100, 50, "test", "text")
        bridge.highlight_element(element)
        
        # Message should be queued
        assert len(bridge.message_queue) == 1
        assert len(bridge.pending_highlights) == 1
```

## 🔗 Integration Points You Must Implement

### For Agent 1 (Viewer Integration)
```python
# Add this method to PDFViewer in viewer.py
def attach_bridge(self, bridge: PDFBridge) -> None:
    """Attach communication bridge."""
    self._bridge = bridge
    # Connect signals and setup integration
```

### For Agent 3 (Performance Integration)
```python
# Bridge provides performance monitoring interface
bridge.performance_event.connect(performance_monitor.handle_bridge_event)
```

### For Agent 4 (Features Integration)
```python
# Bridge provides feature communication interface
bridge.feature_event.connect(feature_manager.handle_feature_event)
bridge.send_feature_command(feature, command, data)
```

## 📁 Files You Must Create

```
src/torematrix/integrations/pdf/
├── bridge.py                      # Main PDFBridge class (YOUR FOCUS)
├── communication.py                # Message protocols and validation (YOUR FOCUS)
└── __init__.py                    # Updated with bridge exports

resources/pdfjs/
├── bridge.js                      # JavaScript bridge implementation (YOUR FOCUS)
└── viewer.js                      # Updated with bridge integration

tests/integration/pdf/
├── test_bridge.py                 # Bridge integration tests (YOUR FOCUS)
└── conftest.py                    # Test configuration
```

## 🎯 Success Criteria

### Functional Requirements ✅
- [ ] QWebChannel communication working bidirectionally
- [ ] Element highlighting functional and accurate
- [ ] Event forwarding to Event Bus operational
- [ ] Performance data collection working
- [ ] Error handling robust and comprehensive

### Performance Requirements ✅
- [ ] Message latency <10ms for standard operations
- [ ] Highlight response <50ms for element highlighting
- [ ] Event forwarding <5ms to Event Bus
- [ ] Memory overhead <10MB for bridge operations

### Integration Requirements ✅
- [ ] Agent 1 viewer integration complete
- [ ] Agent 3 performance monitoring interface ready
- [ ] Agent 4 feature communication interface ready
- [ ] Event Bus integration functional

## 🚀 Getting Started

```bash
# Create your branch
git checkout -b feature/pdfjs-bridge

# Wait for Agent 1 completion
# Check that PDFViewer foundation is ready

# Implement bridge classes
# Test Qt-JS communication
# Add JavaScript bridge
# Test with real PDFs
```

## 📊 Daily Progress Tracking

### Day 2 Goals
- [ ] PDFBridge class implemented
- [ ] QWebChannel setup functional  
- [ ] Basic Qt-JS communication working
- [ ] Element coordinate mapping functional

### Day 3 Goals
- [ ] JavaScript bridge complete
- [ ] Event Bus integration working
- [ ] Performance data collection active
- [ ] **Ready for Agent 3 & 4 parallel work**

---

**You are Agent 2. Your bridge enables all advanced functionality. Build reliable, performant communication that powers the entire PDF.js integration!**