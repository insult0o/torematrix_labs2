"""
Tests for PDF.js Qt-JavaScript Bridge

This module tests the bidirectional communication bridge between Qt and PDF.js
including message validation, event handling, and integration with the viewer.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from src.torematrix.integrations.pdf.bridge import (
    PDFBridge, ElementCoordinate, HighlightStyle, SelectionEvent
)
from src.torematrix.integrations.pdf.communication import (
    MessageType, BridgeMessage, MessageValidator, MessageQueue,
    EventForwarder, CommunicationProtocol, SecurityManager
)


class TestElementCoordinate:
    """Test ElementCoordinate data class."""
    
    def test_element_coordinate_creation(self):
        """Test creating ElementCoordinate."""
        coord = ElementCoordinate(
            page=1,
            x=100.0,
            y=200.0,
            width=50.0,
            height=25.0,
            element_id="test_element",
            element_type="text"
        )
        
        assert coord.page == 1
        assert coord.x == 100.0
        assert coord.y == 200.0
        assert coord.width == 50.0
        assert coord.height == 25.0
        assert coord.element_id == "test_element"
        assert coord.element_type == "text"


class TestHighlightStyle:
    """Test HighlightStyle data class."""
    
    def test_highlight_style_defaults(self):
        """Test default highlight style."""
        style = HighlightStyle()
        
        assert style.color == "#ff0000"
        assert style.opacity == 0.3
        assert style.border_width == 2
        assert style.border_color == "#cc0000"
    
    def test_highlight_style_custom(self):
        """Test custom highlight style."""
        style = HighlightStyle(
            color="#0000ff",
            opacity=0.5,
            border_width=3,
            border_color="#0000cc"
        )
        
        assert style.color == "#0000ff"
        assert style.opacity == 0.5
        assert style.border_width == 3
        assert style.border_color == "#0000cc"


class TestSelectionEvent:
    """Test SelectionEvent data class."""
    
    def test_selection_event_creation(self):
        """Test creating SelectionEvent."""
        coord = ElementCoordinate(
            page=1, x=100.0, y=200.0, width=50.0, height=25.0,
            element_id="test", element_type="text"
        )
        
        event = SelectionEvent(
            coordinates=coord,
            timestamp=time.time(),
            selection_type="click",
            text_content="test text"
        )
        
        assert event.coordinates == coord
        assert event.selection_type == "click"
        assert event.text_content == "test text"
        assert event.timestamp > 0


class TestPDFBridge:
    """Test PDFBridge class."""
    
    @pytest.fixture
    def mock_web_view(self):
        """Create mock web view."""
        web_view = Mock(spec=QWebEngineView)
        web_view.page.return_value = Mock()
        web_view.page().setWebChannel = Mock()
        web_view.page().runJavaScript = Mock()
        return web_view
    
    @pytest.fixture
    def pdf_bridge(self, mock_web_view):
        """Create PDF bridge instance."""
        with patch('src.torematrix.integrations.pdf.bridge.QWebChannel'):
            bridge = PDFBridge(mock_web_view)
            bridge.web_channel = Mock(spec=QWebChannel)
            return bridge
    
    def test_bridge_initialization(self, pdf_bridge, mock_web_view):
        """Test bridge initialization."""
        assert pdf_bridge.pdf_viewer == mock_web_view
        assert pdf_bridge.is_connected is False
        assert pdf_bridge.pending_highlights == []
        assert pdf_bridge.message_queue == []
        assert pdf_bridge._event_bus is None
    
    def test_bridge_ready(self, pdf_bridge):
        """Test bridge ready callback."""
        # Add pending highlights
        coord = ElementCoordinate(
            page=1, x=100.0, y=200.0, width=50.0, height=25.0,
            element_id="test", element_type="text"
        )
        pdf_bridge.pending_highlights.append(coord)
        
        # Add pending messages
        message = {'type': 'test_message', 'data': 'test'}
        pdf_bridge.message_queue.append(message)
        
        # Mock highlight_element method
        pdf_bridge.highlight_element = Mock()
        pdf_bridge._send_message = Mock()
        
        # Call bridge_ready
        pdf_bridge.bridge_ready()
        
        assert pdf_bridge.is_connected is True
        assert len(pdf_bridge.pending_highlights) == 0
        assert len(pdf_bridge.message_queue) == 0
        pdf_bridge.highlight_element.assert_called_once_with(coord)
        pdf_bridge._send_message.assert_called_once_with(message)
    
    def test_element_selection_handling(self, pdf_bridge):
        """Test element selection handling."""
        # Mock signal emission
        pdf_bridge.element_selected = Mock()
        pdf_bridge.element_selected.emit = Mock()
        
        # Create test data
        event_data = {
            'coordinates': {
                'page': 1,
                'x': 100.0,
                'y': 200.0,
                'width': 50.0,
                'height': 25.0,
                'element_id': 'test_element',
                'element_type': 'text'
            },
            'timestamp': time.time(),
            'type': 'click',
            'text': 'test text'
        }
        
        # Test selection handling
        pdf_bridge.on_element_selected(json.dumps(event_data))
        
        # Verify signal was emitted
        pdf_bridge.element_selected.emit.assert_called_once()
        args = pdf_bridge.element_selected.emit.call_args[0]
        selection_event = args[0]
        
        assert isinstance(selection_event, SelectionEvent)
        assert selection_event.coordinates.element_id == 'test_element'
        assert selection_event.selection_type == 'click'
        assert selection_event.text_content == 'test text'
    
    def test_performance_data_handling(self, pdf_bridge):
        """Test performance data handling."""
        # Mock signal emission
        pdf_bridge.performance_event = Mock()
        pdf_bridge.performance_event.emit = Mock()
        
        # Create test data
        perf_data = {
            'type': 'render_time',
            'metrics': {
                'duration': 150.5,
                'page': 1,
                'elements': 25
            }
        }
        
        # Test performance data handling
        pdf_bridge.on_performance_data(json.dumps(perf_data))
        
        # Verify signal was emitted
        pdf_bridge.performance_event.emit.assert_called_once_with(
            'render_time', 
            perf_data['metrics']
        )
    
    def test_highlight_elements(self, pdf_bridge):
        """Test element highlighting."""
        # Mock _send_message
        pdf_bridge._send_message = Mock()
        pdf_bridge.element_highlighted = Mock()
        pdf_bridge.element_highlighted.emit = Mock()
        
        # Create test elements
        elements = [
            ElementCoordinate(
                page=1, x=100.0, y=200.0, width=50.0, height=25.0,
                element_id="test1", element_type="text"
            ),
            ElementCoordinate(
                page=1, x=200.0, y=300.0, width=75.0, height=30.0,
                element_id="test2", element_type="image"
            )
        ]
        
        style = HighlightStyle(color="#00ff00", opacity=0.4)
        
        # Set bridge as connected
        pdf_bridge.is_connected = True
        
        # Test highlighting
        pdf_bridge.highlight_elements(elements, style)
        
        # Verify message was sent
        pdf_bridge._send_message.assert_called_once()
        call_args = pdf_bridge._send_message.call_args[0][0]
        
        assert call_args['type'] == 'highlight_elements'
        assert len(call_args['elements']) == 2
        assert call_args['style']['color'] == "#00ff00"
        assert call_args['style']['opacity'] == 0.4
        
        # Verify signal was emitted
        pdf_bridge.element_highlighted.emit.assert_called_once_with(elements)
    
    def test_clear_highlights(self, pdf_bridge):
        """Test clearing highlights."""
        # Mock _send_message
        pdf_bridge._send_message = Mock()
        
        # Set bridge as connected
        pdf_bridge.is_connected = True
        
        # Test clearing highlights
        pdf_bridge.clear_highlights()
        
        # Verify message was sent
        pdf_bridge._send_message.assert_called_once()
        call_args = pdf_bridge._send_message.call_args[0][0]
        
        assert call_args['type'] == 'clear_highlights'
    
    def test_send_feature_command(self, pdf_bridge):
        """Test sending feature commands."""
        # Mock _send_message
        pdf_bridge._send_message = Mock()
        
        # Set bridge as connected
        pdf_bridge.is_connected = True
        
        # Test feature command
        pdf_bridge.send_feature_command(
            'zoom', 
            'set_zoom', 
            {'zoom': 1.5}
        )
        
        # Verify message was sent
        pdf_bridge._send_message.assert_called_once()
        call_args = pdf_bridge._send_message.call_args[0][0]
        
        assert call_args['type'] == 'feature_command'
        assert call_args['feature'] == 'zoom'
        assert call_args['command'] == 'set_zoom'
        assert call_args['data'] == {'zoom': 1.5}
    
    def test_event_bus_integration(self, pdf_bridge):
        """Test Event Bus integration."""
        # Mock Event Bus
        mock_event_bus = Mock()
        mock_event_bus.emit = Mock()
        
        # Connect bridge to Event Bus
        pdf_bridge.connect_to_event_bus(mock_event_bus)
        
        assert pdf_bridge._event_bus == mock_event_bus
        
        # Test event forwarding
        with patch('src.torematrix.integrations.pdf.bridge.Event') as mock_event:
            mock_event.return_value = Mock()
            
            # Call _forward_to_event_bus
            pdf_bridge._forward_to_event_bus('test.event', {'data': 'test'})
            
            # Verify event was created and emitted
            mock_event.assert_called_once()
            mock_event_bus.emit.assert_called_once()
    
    def test_connection_status(self, pdf_bridge):
        """Test connection status reporting."""
        # Test disconnected state
        status = pdf_bridge.get_connection_status()
        
        assert status['is_connected'] is False
        assert status['pending_highlights'] == 0
        assert status['queued_messages'] == 0
        assert status['event_bus_connected'] is False
        
        # Connect bridge and add some data
        pdf_bridge.is_connected = True
        pdf_bridge.pending_highlights.append(Mock())
        pdf_bridge.message_queue.append(Mock())
        pdf_bridge._event_bus = Mock()
        
        # Test connected state
        status = pdf_bridge.get_connection_status()
        
        assert status['is_connected'] is True
        assert status['pending_highlights'] == 1
        assert status['queued_messages'] == 1
        assert status['event_bus_connected'] is True
    
    def test_disconnect(self, pdf_bridge):
        """Test bridge disconnection."""
        # Set up bridge state
        pdf_bridge.is_connected = True
        pdf_bridge.pending_highlights.append(Mock())
        pdf_bridge.message_queue.append(Mock())
        pdf_bridge.web_channel = Mock()
        pdf_bridge.web_channel.deregisterObject = Mock()
        
        # Disconnect bridge
        pdf_bridge.disconnect()
        
        # Verify cleanup
        assert pdf_bridge.is_connected is False
        assert len(pdf_bridge.pending_highlights) == 0
        assert len(pdf_bridge.message_queue) == 0
        pdf_bridge.web_channel.deregisterObject.assert_called_once()


class TestMessageValidator:
    """Test MessageValidator class."""
    
    def test_validate_highlight_message(self):
        """Test highlight message validation."""
        # Valid message
        valid_data = {
            'elements': [
                {
                    'page': 1,
                    'x': 100.0,
                    'y': 200.0,
                    'width': 50.0,
                    'height': 25.0,
                    'element_id': 'test',
                    'element_type': 'text'
                }
            ],
            'style': {
                'color': '#ff0000',
                'opacity': 0.3
            }
        }
        
        assert MessageValidator.validate_highlight_message(valid_data) is True
        
        # Invalid message - missing elements
        invalid_data = {
            'style': {
                'color': '#ff0000',
                'opacity': 0.3
            }
        }
        
        assert MessageValidator.validate_highlight_message(invalid_data) is False
        
        # Invalid message - invalid element structure
        invalid_data = {
            'elements': [
                {
                    'page': 1,
                    'x': 100.0
                    # Missing required fields
                }
            ],
            'style': {
                'color': '#ff0000',
                'opacity': 0.3
            }
        }
        
        assert MessageValidator.validate_highlight_message(invalid_data) is False
    
    def test_validate_selection_message(self):
        """Test selection message validation."""
        # Valid message
        valid_data = {
            'coordinates': {
                'page': 1,
                'x': 100.0,
                'y': 200.0,
                'width': 50.0,
                'height': 25.0,
                'element_id': 'test',
                'element_type': 'text'
            },
            'timestamp': time.time(),
            'type': 'click'
        }
        
        assert MessageValidator.validate_selection_message(valid_data) is True
        
        # Invalid message - missing timestamp
        invalid_data = {
            'coordinates': {
                'page': 1,
                'x': 100.0,
                'y': 200.0,
                'width': 50.0,
                'height': 25.0,
                'element_id': 'test',
                'element_type': 'text'
            },
            'type': 'click'
        }
        
        assert MessageValidator.validate_selection_message(invalid_data) is False
    
    def test_sanitize_message(self):
        """Test message sanitization."""
        # Message with dangerous keys
        dangerous_data = {
            'normal_key': 'value',
            '__proto__': 'dangerous',
            'constructor': 'dangerous',
            'prototype': 'dangerous',
            'nested': {
                '__proto__': 'dangerous',
                'safe_key': 'safe_value'
            }
        }
        
        sanitized = MessageValidator.sanitize_message(dangerous_data)
        
        assert 'normal_key' in sanitized
        assert '__proto__' not in sanitized
        assert 'constructor' not in sanitized
        assert 'prototype' not in sanitized
        assert '__proto__' not in sanitized['nested']
        assert 'safe_key' in sanitized['nested']


class TestMessageQueue:
    """Test MessageQueue class."""
    
    def test_queue_operations(self):
        """Test basic queue operations."""
        queue = MessageQueue(max_retries=3, max_queue_size=5)
        
        # Test enqueue
        message = BridgeMessage(
            type='test',
            timestamp=time.time(),
            message_id='test_id',
            data={}
        )
        
        result = queue.enqueue(message)
        assert result is True
        
        # Test dequeue
        dequeued = queue.dequeue()
        assert dequeued == message
        
        # Test empty queue
        empty = queue.dequeue()
        assert empty is None
    
    def test_queue_size_limit(self):
        """Test queue size limiting."""
        queue = MessageQueue(max_retries=3, max_queue_size=2)
        
        # Add messages up to limit
        for i in range(3):
            message = BridgeMessage(
                type='test',
                timestamp=time.time(),
                message_id=f'test_{i}',
                data={}
            )
            queue.enqueue(message)
        
        # Should have only 2 messages (oldest dropped)
        assert len(queue.queue) == 2
        assert queue.queue[0].message_id == 'test_1'
        assert queue.queue[1].message_id == 'test_2'
    
    def test_retry_logic(self):
        """Test message retry logic."""
        queue = MessageQueue(max_retries=2, max_queue_size=10)
        
        message = BridgeMessage(
            type='test',
            timestamp=time.time(),
            message_id='test_id',
            data={}
        )
        
        # First retry
        result = queue.retry_message(message)
        assert result is True
        assert len(queue.queue) == 1
        assert queue.retry_counts['test_id'] == 1
        
        # Second retry
        result = queue.retry_message(message)
        assert result is True
        assert queue.retry_counts['test_id'] == 2
        
        # Third retry (should fail)
        result = queue.retry_message(message)
        assert result is False
        assert 'test_id' not in queue.retry_counts
    
    def test_queue_status(self):
        """Test queue status reporting."""
        queue = MessageQueue(max_retries=3, max_queue_size=10)
        
        status = queue.get_status()
        assert status['queue_size'] == 0
        assert status['active_retries'] == 0
        assert status['max_queue_size'] == 10
        assert status['max_retries'] == 3
        
        # Add message and retry
        message = BridgeMessage(
            type='test',
            timestamp=time.time(),
            message_id='test_id',
            data={}
        )
        
        queue.enqueue(message)
        queue.retry_message(message)
        
        status = queue.get_status()
        assert status['queue_size'] == 1
        assert status['active_retries'] == 1


class TestEventForwarder:
    """Test EventForwarder class."""
    
    def test_event_forwarding(self):
        """Test basic event forwarding."""
        mock_event_bus = Mock()
        mock_event_bus.emit = Mock()
        
        forwarder = EventForwarder(mock_event_bus)
        
        with patch('src.torematrix.integrations.pdf.communication.Event') as mock_event:
            mock_event.return_value = Mock()
            
            result = forwarder.forward_event('test.event', {'data': 'test'})
            
            assert result is True
            mock_event.assert_called_once()
            mock_event_bus.emit.assert_called_once()
    
    def test_event_filtering(self):
        """Test event filtering."""
        mock_event_bus = Mock()
        forwarder = EventForwarder(mock_event_bus)
        
        # Add filter that blocks certain events
        def filter_func(event_type, data):
            return event_type != 'blocked.event'
        
        forwarder.add_filter(filter_func)
        
        with patch('src.torematrix.integrations.pdf.communication.Event'):
            # This should be forwarded
            result = forwarder.forward_event('allowed.event', {})
            assert result is True
            
            # This should be blocked
            result = forwarder.forward_event('blocked.event', {})
            assert result is False
    
    def test_statistics_tracking(self):
        """Test event statistics tracking."""
        mock_event_bus = Mock()
        forwarder = EventForwarder(mock_event_bus)
        
        with patch('src.torematrix.integrations.pdf.communication.Event'):
            # Forward some events
            forwarder.forward_event('event.type1', {})
            forwarder.forward_event('event.type1', {})
            forwarder.forward_event('event.type2', {})
            
            stats = forwarder.get_statistics()
            assert stats['event.type1'] == 2
            assert stats['event.type2'] == 1
            
            # Clear statistics
            forwarder.clear_statistics()
            stats = forwarder.get_statistics()
            assert len(stats) == 0


class TestIntegrationTests:
    """Integration tests for the complete bridge system."""
    
    @pytest.fixture
    def mock_viewer(self):
        """Create mock PDF viewer."""
        viewer = Mock()
        viewer.web_view = Mock(spec=QWebEngineView)
        viewer.web_view.page.return_value = Mock()
        viewer.web_view.page().setWebChannel = Mock()
        viewer.web_view.page().runJavaScript = Mock()
        return viewer
    
    @pytest.fixture
    def integrated_bridge(self, mock_viewer):
        """Create integrated bridge with viewer."""
        with patch('src.torematrix.integrations.pdf.bridge.QWebChannel'):
            bridge = PDFBridge(mock_viewer.web_view)
            bridge.web_channel = Mock()
            return bridge
    
    def test_complete_highlight_workflow(self, integrated_bridge):
        """Test complete highlighting workflow."""
        # Create test elements
        elements = [
            ElementCoordinate(
                page=1, x=100.0, y=200.0, width=50.0, height=25.0,
                element_id="test1", element_type="text"
            )
        ]
        
        style = HighlightStyle(color="#00ff00")
        
        # Mock signal connections
        integrated_bridge.element_highlighted = Mock()
        integrated_bridge.element_highlighted.emit = Mock()
        integrated_bridge._send_message = Mock()
        
        # Set as connected
        integrated_bridge.is_connected = True
        
        # Test highlighting
        integrated_bridge.highlight_elements(elements, style)
        
        # Verify all parts of the workflow
        integrated_bridge._send_message.assert_called_once()
        integrated_bridge.element_highlighted.emit.assert_called_once()
        
        # Verify message content
        call_args = integrated_bridge._send_message.call_args[0][0]
        assert call_args['type'] == 'highlight_elements'
        assert len(call_args['elements']) == 1
        assert call_args['style']['color'] == "#00ff00"
    
    def test_complete_selection_workflow(self, integrated_bridge):
        """Test complete selection workflow."""
        # Mock signal connections
        integrated_bridge.element_selected = Mock()
        integrated_bridge.element_selected.emit = Mock()
        
        # Mock Event Bus
        mock_event_bus = Mock()
        integrated_bridge._event_bus = mock_event_bus
        
        # Create test selection data
        selection_data = {
            'coordinates': {
                'page': 1,
                'x': 100.0,
                'y': 200.0,
                'width': 50.0,
                'height': 25.0,
                'element_id': 'test_element',
                'element_type': 'text'
            },
            'timestamp': time.time(),
            'type': 'click',
            'text': 'selected text'
        }
        
        with patch('src.torematrix.integrations.pdf.bridge.Event') as mock_event:
            mock_event.return_value = Mock()
            
            # Process selection
            integrated_bridge.on_element_selected(json.dumps(selection_data))
            
            # Verify signal emission
            integrated_bridge.element_selected.emit.assert_called_once()
            
            # Verify Event Bus forwarding
            mock_event.assert_called_once()
            mock_event_bus.emit.assert_called_once()
    
    def test_error_handling(self, integrated_bridge):
        """Test error handling throughout the system."""
        # Mock error signal
        integrated_bridge.error_occurred = Mock()
        integrated_bridge.error_occurred.emit = Mock()
        
        # Test invalid JSON handling
        integrated_bridge.on_element_selected("invalid json")
        
        # Should emit error signal
        integrated_bridge.error_occurred.emit.assert_called_once()
        args = integrated_bridge.error_occurred.emit.call_args[0]
        assert args[0] == "SELECTION_PROCESSING_FAILED"
        assert "Failed to process element selection" in args[1]