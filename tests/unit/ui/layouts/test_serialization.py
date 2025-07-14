"""Tests for layout serialization system."""

import pytest
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QWidget, QSplitter, QTabWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QScreen

from src.torematrix.ui.layouts.serialization import (
    LayoutSerializer, LayoutDeserializer, SerializedLayout,
    LayoutMetadata, ComponentState, LayoutNode, DisplayGeometry,
    LayoutType, SerializationError, DeserializationError
)


class TestLayoutMetadata:
    """Test layout metadata functionality."""
    
    def test_metadata_creation(self):
        """Test creating layout metadata."""
        metadata = LayoutMetadata(
            name="Test Layout",
            description="Test description",
            author="Test Author"
        )
        
        assert metadata.name == "Test Layout"
        assert metadata.description == "Test description"
        assert metadata.author == "Test Author"
        assert metadata.version == "1.0.0"
        assert isinstance(metadata.created, datetime)
        assert isinstance(metadata.modified, datetime)
        assert metadata.tags == []
    
    def test_metadata_auto_timestamps(self):
        """Test automatic timestamp generation."""
        metadata = LayoutMetadata(name="Test")
        
        assert metadata.created is not None
        assert metadata.modified is not None
        assert metadata.created <= metadata.modified


class TestComponentState:
    """Test component state serialization."""
    
    def test_component_state_creation(self):
        """Test creating component state."""
        state = ComponentState(
            visible=True,
            enabled=False,
            geometry={"x": 10, "y": 20, "width": 100, "height": 200}
        )
        
        assert state.visible is True
        assert state.enabled is False
        assert state.geometry["x"] == 10
        assert state.properties == {}
    
    def test_component_state_defaults(self):
        """Test component state defaults."""
        state = ComponentState()
        
        assert state.visible is True
        assert state.enabled is True
        assert state.geometry is None
        assert state.size_policy is None
        assert state.properties == {}


class TestLayoutNode:
    """Test layout node structure."""
    
    def test_layout_node_creation(self):
        """Test creating layout node."""
        state = ComponentState()
        node = LayoutNode(
            type=LayoutType.SPLITTER,
            component_id="test_component",
            state=state
        )
        
        assert node.type == LayoutType.SPLITTER
        assert node.component_id == "test_component"
        assert node.state == state
        assert node.children == []
        assert node.properties == {}
    
    def test_layout_node_with_children(self):
        """Test layout node with children."""
        parent_state = ComponentState()
        child_state = ComponentState()
        
        child_node = LayoutNode(
            type=LayoutType.WIDGET,
            component_id="child",
            state=child_state
        )
        
        parent_node = LayoutNode(
            type=LayoutType.SPLITTER,
            component_id="parent",
            state=parent_state,
            children=[child_node]
        )
        
        assert len(parent_node.children) == 1
        assert parent_node.children[0] == child_node


@pytest.fixture
def qt_app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    return Mock()


@pytest.fixture
def mock_config_manager():
    """Create mock config manager."""
    return Mock()


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    return Mock()


@pytest.fixture
def layout_serializer(mock_event_bus, mock_config_manager, mock_state_manager):
    """Create layout serializer for testing."""
    return LayoutSerializer(mock_event_bus, mock_config_manager, mock_state_manager)


@pytest.fixture
def layout_deserializer(mock_event_bus, mock_config_manager, mock_state_manager):
    """Create layout deserializer for testing."""
    return LayoutDeserializer(mock_event_bus, mock_config_manager, mock_state_manager)


class TestLayoutSerializer:
    """Test layout serialization functionality."""
    
    def test_component_registration(self, layout_serializer, qt_app):
        """Test component registration."""
        widget = QWidget()
        component_id = "test_widget"
        
        layout_serializer.register_component(widget, component_id)
        
        assert widget in layout_serializer._component_registry
        assert layout_serializer._component_registry[widget] == component_id
    
    def test_serialization_handler_registration(self, layout_serializer):
        """Test custom serialization handler registration."""
        def custom_handler(widget):
            return {"custom": True}
        
        layout_serializer.register_serialization_handler(QWidget, custom_handler)
        
        assert QWidget in layout_serializer._serialization_handlers
        assert layout_serializer._serialization_handlers[QWidget] == custom_handler
    
    def test_serialize_simple_widget(self, layout_serializer, qt_app):
        """Test serializing a simple widget."""
        widget = QWidget()
        widget.setObjectName("test_widget")
        widget.resize(200, 150)
        
        metadata = LayoutMetadata(name="Test Layout")
        
        serialized = layout_serializer.serialize_layout(widget, metadata)
        
        assert isinstance(serialized, SerializedLayout)
        assert serialized.metadata.name == "Test Layout"
        assert serialized.layout.type == LayoutType.WIDGET
        assert serialized.layout.state.visible is True
        assert serialized.layout.state.enabled is True
    
    def test_serialize_splitter(self, layout_serializer, qt_app):
        """Test serializing a splitter widget."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Add child widgets
        child1 = QWidget()
        child2 = QWidget()
        splitter.addWidget(child1)
        splitter.addWidget(child2)
        splitter.setSizes([300, 200])
        
        metadata = LayoutMetadata(name="Splitter Layout")
        
        serialized = layout_serializer.serialize_layout(splitter, metadata)
        
        assert serialized.layout.type == LayoutType.SPLITTER
        assert len(serialized.layout.children) == 2
        assert "orientation" in serialized.layout.properties
        assert "sizes" in serialized.layout.properties
        assert serialized.layout.properties["sizes"] == [300, 200]
    
    def test_serialize_tab_widget(self, layout_serializer, qt_app):
        """Test serializing a tab widget."""
        tab_widget = QTabWidget()
        
        # Add tabs
        tab1 = QWidget()
        tab2 = QWidget()
        tab_widget.addTab(tab1, "Tab 1")
        tab_widget.addTab(tab2, "Tab 2")
        tab_widget.setCurrentIndex(1)
        
        metadata = LayoutMetadata(name="Tab Layout")
        
        serialized = layout_serializer.serialize_layout(tab_widget, metadata)
        
        assert serialized.layout.type == LayoutType.TAB_WIDGET
        assert len(serialized.layout.children) == 2
        assert "current_index" in serialized.layout.properties
        assert serialized.layout.properties["current_index"] == 1
        
        # Check tab properties
        assert "tab_text" in serialized.layout.children[0].properties
        assert serialized.layout.children[0].properties["tab_text"] == "Tab 1"
    
    def test_serialize_to_json(self, layout_serializer, qt_app):
        """Test serializing layout to JSON string."""
        widget = QWidget()
        metadata = LayoutMetadata(name="JSON Test")
        
        json_str = layout_serializer.serialize_to_json(widget, metadata)
        
        assert isinstance(json_str, str)
        
        # Parse back to verify valid JSON
        data = json.loads(json_str)
        assert "metadata" in data
        assert "layout" in data
        assert data["metadata"]["name"] == "JSON Test"
    
    def test_serialize_with_displays(self, layout_serializer, qt_app):
        """Test serializing with display information."""
        widget = QWidget()
        metadata = LayoutMetadata(name="Display Test")
        
        # Mock screen
        mock_screen = Mock(spec=QScreen)
        mock_screen.geometry.return_value = QRect(0, 0, 1920, 1080)
        mock_screen.logicalDotsPerInch.return_value = 96.0
        mock_screen.name.return_value = "Test Display"
        
        serialized = layout_serializer.serialize_layout(widget, metadata, [mock_screen])
        
        assert len(serialized.displays) == 1
        display = serialized.displays[0]
        assert display.width == 1920
        assert display.height == 1080
        assert display.dpi == 96.0
        assert display.name == "Test Display"
    
    def test_serialization_error_handling(self, layout_serializer, qt_app):
        """Test serialization error handling."""
        # Test with None widget
        metadata = LayoutMetadata(name="Error Test")
        
        with pytest.raises(SerializationError):
            layout_serializer.serialize_layout(None, metadata)


class TestLayoutDeserializer:
    """Test layout deserialization functionality."""
    
    def test_component_factory_registration(self, layout_deserializer):
        """Test component factory registration."""
        def factory():
            return QWidget()
        
        layout_deserializer.register_component_factory("test_component", factory)
        
        assert "test_component" in layout_deserializer._component_factory
        assert layout_deserializer._component_factory["test_component"] == factory
    
    def test_deserialization_handler_registration(self, layout_deserializer):
        """Test custom deserialization handler registration."""
        def custom_handler(node):
            return QWidget()
        
        layout_deserializer.register_deserialization_handler(LayoutType.CUSTOM, custom_handler)
        
        assert LayoutType.CUSTOM in layout_deserializer._deserialization_handlers
    
    def test_deserialize_simple_widget(self, layout_deserializer, qt_app):
        """Test deserializing a simple widget."""
        # Create serialized data
        metadata = LayoutMetadata(name="Test Widget")
        state = ComponentState(visible=True, enabled=False)
        node = LayoutNode(
            type=LayoutType.WIDGET,
            component_id="test_widget",
            state=state,
            properties={"object_name": "test_widget"}
        )
        
        serialized = SerializedLayout(
            metadata=metadata,
            displays=[],
            layout=node
        )
        
        widget = layout_deserializer.deserialize_layout(serialized)
        
        assert isinstance(widget, QWidget)
        assert widget.isVisible() is True
        assert widget.isEnabled() is False
        assert widget.objectName() == "test_widget"
    
    def test_deserialize_splitter(self, layout_deserializer, qt_app):
        """Test deserializing a splitter."""
        # Create splitter data
        metadata = LayoutMetadata(name="Splitter Test")
        
        child1_state = ComponentState()
        child1_node = LayoutNode(
            type=LayoutType.WIDGET,
            component_id="child1",
            state=child1_state
        )
        
        child2_state = ComponentState()
        child2_node = LayoutNode(
            type=LayoutType.WIDGET,
            component_id="child2",
            state=child2_state
        )
        
        splitter_state = ComponentState()
        splitter_node = LayoutNode(
            type=LayoutType.SPLITTER,
            component_id="splitter",
            state=splitter_state,
            children=[child1_node, child2_node],
            properties={
                "orientation": Qt.Orientation.Horizontal.value,
                "sizes": [300, 200]
            }
        )
        
        serialized = SerializedLayout(
            metadata=metadata,
            displays=[],
            layout=splitter_node
        )
        
        widget = layout_deserializer.deserialize_layout(serialized)
        
        assert isinstance(widget, QSplitter)
        assert widget.count() == 2
        assert widget.orientation() == Qt.Orientation.Horizontal
        assert widget.sizes() == [300, 200]
    
    def test_deserialize_from_json(self, layout_deserializer, qt_app):
        """Test deserializing from JSON string."""
        json_data = {
            "metadata": {
                "name": "JSON Test",
                "version": "1.0.0",
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "author": "Test",
                "description": "",
                "tags": []
            },
            "displays": [],
            "layout": {
                "type": "widget",
                "component_id": "test_widget",
                "state": {
                    "visible": True,
                    "enabled": True,
                    "geometry": None,
                    "size_policy": None,
                    "properties": {}
                },
                "children": [],
                "properties": {}
            },
            "global_properties": {}
        }
        
        json_str = json.dumps(json_data)
        widget = layout_deserializer.deserialize_from_json(json_str)
        
        assert isinstance(widget, QWidget)
        assert widget.isVisible() is True
        assert widget.isEnabled() is True
    
    def test_deserialization_error_handling(self, layout_deserializer):
        """Test deserialization error handling."""
        # Test with invalid JSON
        with pytest.raises(DeserializationError):
            layout_deserializer.deserialize_from_json("invalid json")
        
        # Test with invalid data structure
        invalid_data = {"invalid": "data"}
        with pytest.raises(DeserializationError):
            layout_deserializer.deserialize_from_json(json.dumps(invalid_data))
    
    def test_component_factory_usage(self, layout_deserializer, qt_app):
        """Test that component factories are used during deserialization."""
        # Register a custom factory
        custom_widget_created = False
        
        def custom_factory():
            nonlocal custom_widget_created
            custom_widget_created = True
            widget = QWidget()
            widget.setObjectName("custom_widget")
            return widget
        
        layout_deserializer.register_component_factory("custom_component", custom_factory)
        
        # Create data that should use the factory
        metadata = LayoutMetadata(name="Factory Test")
        state = ComponentState()
        node = LayoutNode(
            type=LayoutType.WIDGET,
            component_id="custom_component",
            state=state
        )
        
        serialized = SerializedLayout(
            metadata=metadata,
            displays=[],
            layout=node
        )
        
        widget = layout_deserializer.deserialize_layout(serialized)
        
        assert custom_widget_created
        assert widget.objectName() == "custom_widget"


class TestSerializationRoundTrip:
    """Test complete serialization/deserialization cycles."""
    
    def test_simple_roundtrip(self, layout_serializer, layout_deserializer, qt_app):
        """Test simple widget roundtrip."""
        # Create original widget
        original = QWidget()
        original.setObjectName("roundtrip_test")
        original.resize(300, 200)
        original.setVisible(True)
        original.setEnabled(False)
        
        # Serialize
        metadata = LayoutMetadata(name="Roundtrip Test")
        serialized = layout_serializer.serialize_layout(original, metadata)
        
        # Deserialize
        restored = layout_deserializer.deserialize_layout(serialized)
        
        # Verify restoration
        assert restored.objectName() == "roundtrip_test"
        assert restored.isVisible() is True
        assert restored.isEnabled() is False
    
    def test_splitter_roundtrip(self, layout_serializer, layout_deserializer, qt_app):
        """Test splitter roundtrip."""
        # Create original splitter
        original = QSplitter(Qt.Orientation.Vertical)
        
        child1 = QWidget()
        child1.setObjectName("child1")
        child2 = QWidget()
        child2.setObjectName("child2")
        
        original.addWidget(child1)
        original.addWidget(child2)
        original.setSizes([150, 250])
        
        # Serialize
        metadata = LayoutMetadata(name="Splitter Roundtrip")
        serialized = layout_serializer.serialize_layout(original, metadata)
        
        # Deserialize
        restored = layout_deserializer.deserialize_layout(serialized)
        
        # Verify restoration
        assert isinstance(restored, QSplitter)
        assert restored.orientation() == Qt.Orientation.Vertical
        assert restored.count() == 2
        assert restored.sizes() == [150, 250]
        
        # Check children
        assert restored.widget(0).objectName() == "child1"
        assert restored.widget(1).objectName() == "child2"
    
    def test_json_roundtrip(self, layout_serializer, layout_deserializer, qt_app):
        """Test complete JSON roundtrip."""
        # Create complex widget structure
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_widget.setObjectName("left_panel")
        
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setObjectName("right_splitter")
        
        top_widget = QWidget()
        top_widget.setObjectName("top_panel")
        bottom_widget = QWidget()
        bottom_widget.setObjectName("bottom_panel")
        
        right_splitter.addWidget(top_widget)
        right_splitter.addWidget(bottom_widget)
        right_splitter.setSizes([200, 100])
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([300, 300])
        
        # Serialize to JSON
        metadata = LayoutMetadata(
            name="Complex Layout",
            description="Complex layout for testing",
            author="Test Suite"
        )
        
        json_str = layout_serializer.serialize_to_json(main_splitter, metadata)
        
        # Deserialize from JSON
        restored = layout_deserializer.deserialize_from_json(json_str)
        
        # Verify structure
        assert isinstance(restored, QSplitter)
        assert restored.orientation() == Qt.Orientation.Horizontal
        assert restored.count() == 2
        
        # Check left panel
        left_restored = restored.widget(0)
        assert left_restored.objectName() == "left_panel"
        
        # Check right splitter
        right_restored = restored.widget(1)
        assert isinstance(right_restored, QSplitter)
        assert right_restored.orientation() == Qt.Orientation.Vertical
        assert right_restored.count() == 2
        
        # Check nested panels
        top_restored = right_restored.widget(0)
        bottom_restored = right_restored.widget(1)
        assert top_restored.objectName() == "top_panel"
        assert bottom_restored.objectName() == "bottom_panel"


class TestLayoutTypes:
    """Test different layout type handling."""
    
    def test_layout_type_detection(self, layout_serializer, qt_app):
        """Test layout type detection for different widgets."""
        # Test splitter
        splitter = QSplitter()
        assert layout_serializer._determine_layout_type(splitter) == LayoutType.SPLITTER
        
        # Test tab widget
        tab_widget = QTabWidget()
        assert layout_serializer._determine_layout_type(tab_widget) == LayoutType.TAB_WIDGET
        
        # Test widget with VBox layout
        widget_with_vbox = QWidget()
        vbox = QVBoxLayout(widget_with_vbox)
        assert layout_serializer._determine_layout_type(widget_with_vbox) == LayoutType.VBOX_LAYOUT
        
        # Test plain widget
        plain_widget = QWidget()
        assert layout_serializer._determine_layout_type(plain_widget) == LayoutType.WIDGET
    
    def test_property_serialization_by_type(self, layout_serializer, qt_app):
        """Test that different widget types serialize appropriate properties."""
        # Test splitter properties
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setChildrenCollapsible(False)
        
        properties = layout_serializer._serialize_splitter(splitter)
        
        assert "orientation" in properties
        assert "handle_width" in properties
        assert "children_collapsible" in properties
        assert properties["handle_width"] == 10
        assert properties["children_collapsible"] is False
        
        # Test tab widget properties
        tab_widget = QTabWidget()
        tab_widget.setTabsClosable(True)
        tab_widget.setTabsMovable(True)
        
        properties = layout_serializer._serialize_tab_widget(tab_widget)
        
        assert "current_index" in properties
        assert "tabs_closable" in properties
        assert "tabs_movable" in properties
        assert properties["tabs_closable"] is True
        assert properties["tabs_movable"] is True


if __name__ == "__main__":
    pytest.main([__file__])