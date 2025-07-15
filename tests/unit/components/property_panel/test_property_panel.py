"""Tests for PropertyPanel main widget"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.torematrix.ui.components.property_panel.property_panel import PropertyPanel
from src.torematrix.ui.components.property_panel.models import PropertyValue, PropertyMetadata
from src.torematrix.ui.components.property_panel.events import PropertyEvent, PropertyEventType
from src.torematrix.core.property.manager import PropertyManager


class TestPropertyPanel:
    @pytest.fixture
    def mock_property_manager(self):
        """Create mock property manager"""
        manager = Mock(spec=PropertyManager)
        manager.get_notification_center.return_value = Mock()
        manager.get_element_properties = AsyncMock(return_value={})
        manager.get_property_metadata = AsyncMock(return_value=None)
        return manager
    
    @pytest.fixture
    def property_panel(self, qtbot, mock_property_manager):
        """Create PropertyPanel for testing"""
        panel = PropertyPanel(mock_property_manager)
        qtbot.addWidget(panel)
        return panel
    
    def test_initialization(self, property_panel, mock_property_manager):
        """Test PropertyPanel initialization"""
        assert property_panel._property_manager == mock_property_manager
        assert property_panel._current_element_id is None
        assert property_panel._layout_mode == "vertical"
        assert property_panel._compact_mode is False
        assert property_panel._show_metadata is True
        assert property_panel._group_by_category is True
    
    def test_ui_components_created(self, property_panel):
        """Test that UI components are properly created"""
        # Check header components
        assert hasattr(property_panel, '_title_label')
        assert hasattr(property_panel, '_element_info_label')
        assert property_panel._title_label.text() == "Properties"
        
        # Check scroll area
        assert hasattr(property_panel, '_scroll_area')
        assert hasattr(property_panel, '_content_widget')
        assert hasattr(property_panel, '_content_layout')
        
        # Check status bar
        assert hasattr(property_panel, '_status_label')
        assert hasattr(property_panel, '_property_count_label')
        assert property_panel._status_label.text() == "Ready"
    
    @pytest.mark.asyncio
    async def test_set_element_with_properties(self, property_panel, mock_property_manager):
        """Test setting element with properties"""
        # Setup mock data
        element_id = "test_element"
        properties = {
            "text": "Sample text",
            "x": 10.5,
            "confidence": 0.85
        }
        mock_property_manager.get_element_properties.return_value = properties
        
        # Set element
        await property_panel.set_element(element_id)
        
        # Verify element is set
        assert property_panel._current_element_id == element_id
        assert "Element: test_element" in property_panel._element_info_label.text()
        assert "3 properties" in property_panel._property_count_label.text()
        
        # Verify properties are displayed
        assert len(property_panel._property_widgets) == 3
        assert "text" in property_panel._property_widgets
        assert "x" in property_panel._property_widgets
        assert "confidence" in property_panel._property_widgets
    
    @pytest.mark.asyncio
    async def test_set_element_no_properties(self, property_panel, mock_property_manager):
        """Test setting element with no properties"""
        element_id = "empty_element"
        mock_property_manager.get_element_properties.return_value = {}
        
        await property_panel.set_element(element_id)
        
        assert property_panel._current_element_id == element_id
        assert len(property_panel._property_widgets) == 0
        assert "0 properties" in property_panel._property_count_label.text()
    
    @pytest.mark.asyncio
    async def test_set_element_none(self, property_panel):
        """Test setting element to None"""
        await property_panel.set_element(None)
        
        assert property_panel._current_element_id is None
        assert "No element selected" in property_panel._element_info_label.text()
        assert "No element selected" in property_panel._status_label.text()
    
    def test_categorize_properties(self, property_panel):
        """Test property categorization"""
        properties = {
            "text": "Sample text",
            "content": "Sample content", 
            "x": 10.5,
            "y": 20.3,
            "width": 100,
            "confidence": 0.85,
            "type": "Text",
            "page": 1
        }
        
        categorized = property_panel._categorize_properties(properties)
        
        # Check categories
        assert "Content" in categorized
        assert "Position" in categorized
        assert "Dimensions" in categorized
        assert "Analysis" in categorized
        assert "Classification" in categorized
        assert "Document" in categorized
        
        # Check content of categories
        assert "text" in categorized["Content"]
        assert "content" in categorized["Content"]
        assert "x" in categorized["Position"]
        assert "y" in categorized["Position"]
        assert "width" in categorized["Dimensions"]
        assert "confidence" in categorized["Analysis"]
        assert "type" in categorized["Classification"]
        assert "page" in categorized["Document"]
    
    def test_get_property_category(self, property_panel):
        """Test property category mapping"""
        assert property_panel._get_property_category("text") == "Content"
        assert property_panel._get_property_category("x") == "Position"
        assert property_panel._get_property_category("width") == "Dimensions"
        assert property_panel._get_property_category("confidence") == "Analysis"
        assert property_panel._get_property_category("type") == "Classification"
        assert property_panel._get_property_category("page") == "Document"
        assert property_panel._get_property_category("unknown") == "General"
    
    def test_has_confidence_score(self, property_panel):
        """Test confidence score detection"""
        # Dict with confidence
        assert property_panel._has_confidence_score({"value": "test", "confidence": 0.8})
        
        # Dict without confidence
        assert not property_panel._has_confidence_score({"value": "test"})
        
        # Non-dict value
        assert not property_panel._has_confidence_score("simple_value")
        assert not property_panel._has_confidence_score(42)
    
    def test_get_confidence_score(self, property_panel):
        """Test confidence score extraction"""
        # Dict with confidence
        assert property_panel._get_confidence_score({"value": "test", "confidence": 0.8}) == 0.8
        
        # Dict without confidence
        assert property_panel._get_confidence_score({"value": "test"}) == 0.0
        
        # Non-dict value
        assert property_panel._get_confidence_score("simple_value") == 0.0
    
    def test_layout_configuration(self, property_panel):
        """Test layout configuration methods"""
        # Test layout mode
        property_panel.set_layout_mode("horizontal")
        assert property_panel._layout_mode == "horizontal"
        
        property_panel.set_layout_mode("grid")
        assert property_panel._layout_mode == "grid"
        
        # Test compact mode
        property_panel.set_compact_mode(True)
        assert property_panel._compact_mode is True
        
        # Test metadata visibility
        property_panel.set_show_metadata(False)
        assert property_panel._show_metadata is False
        
        # Test category grouping
        property_panel.set_group_by_category(False)
        assert property_panel._group_by_category is False
    
    def test_property_changed_signal_handling(self, property_panel):
        """Test property changed signal handling"""
        # Setup element and widget
        property_panel._current_element_id = "test_element"
        mock_widget = Mock()
        property_panel._property_widgets["text"] = mock_widget
        
        # Create and emit event
        event = PropertyEvent(
            event_type=PropertyEventType.VALUE_CHANGED,
            element_id="test_element",
            property_name="text",
            old_value="old",
            new_value="new"
        )
        
        property_panel._on_property_changed(event)
        
        # Verify widget was updated
        mock_widget.update_value.assert_called_once_with("new")
    
    def test_validation_failed_signal_handling(self, property_panel):
        """Test validation failed signal handling"""
        # Setup element and widget
        property_panel._current_element_id = "test_element"
        mock_widget = Mock()
        property_panel._property_widgets["text"] = mock_widget
        
        property_panel._on_validation_failed("test_element", "text", "Invalid value")
        
        # Verify widget shows error
        mock_widget.show_validation_error.assert_called_once_with("Invalid value")
        assert "Validation error: Invalid value" in property_panel._status_label.text()
    
    def test_batch_update_signals(self, property_panel):
        """Test batch update signal handling"""
        property_panel._current_element_id = "test_element"
        
        # Test batch start
        property_panel._on_batch_update_started(["test_element", "other_element"])
        assert "Updating properties..." in property_panel._status_label.text()
        
        # Test batch completion
        property_panel._on_batch_update_completed(["test_element"], 5)
        assert "Updated 5 properties" in property_panel._status_label.text()
    
    def test_property_value_changed_handler(self, property_panel):
        """Test property value change from widget"""
        property_panel._current_element_id = "test_element"
        
        # Connect signal handler
        signal_emitted = []
        property_panel.property_changed.connect(
            lambda eid, pname, value: signal_emitted.append((eid, pname, value))
        )
        
        property_panel._on_property_value_changed("text", "new_value")
        
        # Verify signal was emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("test_element", "text", "new_value")
    
    def test_property_widget_selected_handler(self, property_panel):
        """Test property widget selection"""
        property_panel._current_element_id = "test_element"
        
        # Connect signal handler
        signal_emitted = []
        property_panel.property_selected.connect(
            lambda eid, pname: signal_emitted.append((eid, pname))
        )
        
        property_panel._on_property_widget_selected("text")
        
        # Verify signal was emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("test_element", "text")
    
    def test_clear_property_widgets(self, property_panel):
        """Test clearing property widgets"""
        # Add some mock widgets
        mock_widget1 = Mock()
        mock_widget2 = Mock()
        property_panel._property_widgets["text"] = mock_widget1
        property_panel._property_widgets["x"] = mock_widget2
        property_panel._confidence_widgets["confidence"] = Mock()
        
        property_panel._clear_property_widgets()
        
        # Verify widgets are cleared
        assert len(property_panel._property_widgets) == 0
        assert len(property_panel._confidence_widgets) == 0
    
    def test_public_interface(self, property_panel):
        """Test public interface methods"""
        # Test get_current_element_id
        property_panel._current_element_id = "test_element"
        assert property_panel.get_current_element_id() == "test_element"
        
        # Test get_property_widget
        mock_widget = Mock()
        property_panel._property_widgets["text"] = mock_widget
        assert property_panel.get_property_widget("text") == mock_widget
        assert property_panel.get_property_widget("nonexistent") is None
        
        # Test get_confidence_widget
        mock_conf_widget = Mock()
        property_panel._confidence_widgets["confidence"] = mock_conf_widget
        assert property_panel.get_confidence_widget("confidence") == mock_conf_widget
        assert property_panel.get_confidence_widget("nonexistent") is None
    
    def test_size_hint(self, property_panel):
        """Test size hint"""
        size_hint = property_panel.sizeHint()
        assert size_hint.width() == 300
        assert size_hint.height() == 400