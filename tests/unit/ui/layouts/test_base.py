"""Unit tests for layout base classes and interfaces."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from PyQt6.QtWidgets import QWidget, QLabel, QMainWindow
from PyQt6.QtCore import QSize, QMargins
from PyQt6.QtGui import QResizeEvent

from torematrix.ui.layouts.base import (
    LayoutType, LayoutState, LayoutGeometry, LayoutItem, LayoutConfiguration,
    BaseLayout, LayoutItemRegistry
)


class TestLayoutGeometry:
    """Test LayoutGeometry data class."""
    
    def test_default_geometry(self):
        """Test default geometry values."""
        geometry = LayoutGeometry()
        
        assert geometry.x == 0
        assert geometry.y == 0
        assert geometry.width == 800
        assert geometry.height == 600
        assert geometry.margins == QMargins(0, 0, 0, 0)
    
    def test_custom_geometry(self):
        """Test custom geometry values."""
        margins = QMargins(10, 20, 30, 40)
        geometry = LayoutGeometry(
            x=100, y=200, width=1200, height=900, margins=margins
        )
        
        assert geometry.x == 100
        assert geometry.y == 200
        assert geometry.width == 1200
        assert geometry.height == 900
        assert geometry.margins == margins
    
    def test_to_rect(self):
        """Test conversion to QRect."""
        geometry = LayoutGeometry(x=100, y=200, width=800, height=600)
        rect = geometry.to_rect()
        
        assert rect.x() == 100
        assert rect.y() == 200
        assert rect.width() == 800
        assert rect.height() == 600
    
    def test_to_size(self):
        """Test conversion to QSize."""
        geometry = LayoutGeometry(width=1200, height=900)
        size = geometry.to_size()
        
        assert size.width() == 1200
        assert size.height() == 900


class TestLayoutItem:
    """Test LayoutItem data class."""
    
    def test_default_item(self):
        """Test default layout item values."""
        widget = QLabel("Test")
        item = LayoutItem(
            id="test-id",
            widget=widget,
            name="Test Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry()
        )
        
        assert item.id == "test-id"
        assert item.widget == widget
        assert item.name == "Test Item"
        assert item.layout_type == LayoutType.DOCUMENT
        assert item.visible is True
        assert item.stretch_factor == 1
        assert item.minimum_size is None
        assert item.maximum_size is None
        assert item.properties == {}
    
    def test_auto_id_generation(self):
        """Test automatic ID generation."""
        widget = QLabel("Test")
        item = LayoutItem(
            id="",  # Empty ID should trigger auto-generation
            widget=widget,
            name="Test Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry()
        )
        
        assert item.id != ""
        assert len(item.id) > 0
    
    def test_custom_properties(self):
        """Test custom item properties."""
        widget = QLabel("Test")
        properties = {"area_type": "properties", "custom_setting": True}
        
        item = LayoutItem(
            id="test-id",
            widget=widget,
            name="Test Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            visible=False,
            stretch_factor=3,
            minimum_size=QSize(100, 50),
            maximum_size=QSize(500, 300),
            properties=properties
        )
        
        assert item.visible is False
        assert item.stretch_factor == 3
        assert item.minimum_size == QSize(100, 50)
        assert item.maximum_size == QSize(500, 300)
        assert item.properties == properties


class TestLayoutConfiguration:
    """Test LayoutConfiguration data class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = LayoutConfiguration(
            id="test-config",
            name="Test Layout",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry()
        )
        
        assert config.id == "test-config"
        assert config.name == "Test Layout"
        assert config.layout_type == LayoutType.DOCUMENT
        assert len(config.items) == 0
        assert len(config.splitter_states) == 0
        assert config.properties == {}
        assert config.version == "1.0"
    
    def test_auto_id_generation(self):
        """Test automatic ID generation."""
        config = LayoutConfiguration(
            id="",  # Empty ID should trigger auto-generation
            name="Test Layout",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry()
        )
        
        assert config.id != ""
        assert len(config.id) > 0
    
    def test_with_items(self):
        """Test configuration with layout items."""
        widget1 = QLabel("Widget 1")
        widget2 = QLabel("Widget 2")
        
        item1 = LayoutItem("item1", widget1, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        item2 = LayoutItem("item2", widget2, "Item 2", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test-config",
            name="Test Layout",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            items=[item1, item2]
        )
        
        assert len(config.items) == 2
        assert config.items[0] == item1
        assert config.items[1] == item2


class MockLayout(BaseLayout):
    """Mock layout implementation for testing."""
    
    def __init__(self, config: LayoutConfiguration):
        super().__init__(config)
        self._create_container_called = False
        self._apply_layout_called = False
        self._mock_container = QWidget()
    
    def create_container(self) -> QWidget:
        """Mock container creation."""
        self._create_container_called = True
        return self._mock_container
    
    def apply_layout(self) -> bool:
        """Mock layout application."""
        self._apply_layout_called = True
        return True
    
    def add_item(self, item: LayoutItem) -> bool:
        """Mock add item."""
        self._items[item.id] = item
        self.item_added.emit(item)
        return True
    
    def remove_item(self, item_id: str) -> bool:
        """Mock remove item."""
        if item_id in self._items:
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
        return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Mock update item."""
        if item_id in self._items:
            self._items[item_id] = item
            return True
        return False


class TestBaseLayout:
    """Test BaseLayout abstract class functionality."""
    
    def test_initialization(self):
        """Test layout initialization."""
        widget1 = QLabel("Widget 1")
        item1 = LayoutItem("item1", widget1, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test-layout",
            name="Test Layout",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            items=[item1]
        )
        
        layout = MockLayout(config)
        
        assert layout.config == config
        assert layout.state == LayoutState.INACTIVE
        assert layout.container is None
        assert len(layout.items) == 1
        assert "item1" in layout.items
    
    def test_state_management(self):
        """Test layout state management."""
        config = LayoutConfiguration("test", "Test", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        # Track state changes
        state_changes = []
        layout.state_changed.connect(lambda state: state_changes.append(state))
        
        # Change state
        layout.set_state(LayoutState.ACTIVE)
        
        assert layout.state == LayoutState.ACTIVE
        assert len(state_changes) == 1
        assert state_changes[0] == LayoutState.ACTIVE
    
    def test_validation_success(self):
        """Test successful layout validation."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        assert layout.validate() is True
        assert layout.is_validated() is True
    
    def test_validation_failure_no_name(self):
        """Test validation failure for missing name."""
        config = LayoutConfiguration("test", "", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        assert layout.validate() is False
        assert layout.is_validated() is False
    
    def test_validation_failure_no_layout_type(self):
        """Test validation failure for missing layout type."""
        config = LayoutConfiguration("test", "Test", None, LayoutGeometry())
        layout = MockLayout(config)
        
        assert layout.validate() is False
        assert layout.is_validated() is False
    
    def test_activation_success(self):
        """Test successful layout activation."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        # Track state changes
        state_changes = []
        layout.state_changed.connect(lambda state: state_changes.append(state))
        
        result = layout.activate()
        
        assert result is True
        assert layout.state == LayoutState.ACTIVE
        assert layout._create_container_called is True
        assert layout._apply_layout_called is True
        assert layout.container is not None
        
        # Should have gone through transitioning state
        assert LayoutState.TRANSITIONING in state_changes
        assert LayoutState.ACTIVE in state_changes
    
    def test_activation_failure_invalid_config(self):
        """Test activation failure with invalid configuration."""
        config = LayoutConfiguration("test", "", LayoutType.DOCUMENT, LayoutGeometry())  # Invalid: no name
        layout = MockLayout(config)
        
        result = layout.activate()
        
        assert result is False
        assert layout.state == LayoutState.ERROR
    
    def test_deactivation(self):
        """Test layout deactivation."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        # First activate
        layout.activate()
        assert layout.state == LayoutState.ACTIVE
        
        # Then deactivate
        result = layout.deactivate()
        
        assert result is True
        assert layout.state == LayoutState.INACTIVE
        assert layout.container is None
    
    def test_item_management(self):
        """Test layout item management."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        # Track item events
        items_added = []
        items_removed = []
        layout.item_added.connect(lambda item: items_added.append(item))
        layout.item_removed.connect(lambda item_id: items_removed.append(item_id))
        
        # Add item
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Test Item", LayoutType.DOCUMENT, LayoutGeometry())
        
        result = layout.add_item(item)
        assert result is True
        assert "item1" in layout.items
        assert len(items_added) == 1
        assert items_added[0] == item
        
        # Get item
        retrieved_item = layout.get_item("item1")
        assert retrieved_item == item
        
        # Update item
        updated_item = LayoutItem("item1", widget, "Updated Item", LayoutType.DOCUMENT, LayoutGeometry())
        result = layout.update_item("item1", updated_item)
        assert result is True
        assert layout.get_item("item1").name == "Updated Item"
        
        # Remove item
        result = layout.remove_item("item1")
        assert result is True
        assert "item1" not in layout.items
        assert len(items_removed) == 1
        assert items_removed[0] == "item1"
    
    def test_geometry_update(self):
        """Test layout geometry update."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        layout.activate()  # Create container
        
        # Track geometry changes
        geometry_changes = []
        layout.geometry_changed.connect(lambda geom: geometry_changes.append(geom))
        
        # Update geometry
        new_geometry = LayoutGeometry(x=100, y=200, width=1200, height=900)
        layout.update_geometry(new_geometry)
        
        assert layout.config.geometry == new_geometry
        assert len(geometry_changes) == 1
        assert geometry_changes[0] == new_geometry
    
    def test_save_restore_state(self):
        """Test layout state save and restore."""
        config = LayoutConfiguration("test", "Test Layout", LayoutType.DOCUMENT, LayoutGeometry())
        layout = MockLayout(config)
        
        # Add an item
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Test Item", LayoutType.DOCUMENT, LayoutGeometry())
        layout.add_item(item)
        
        # Save state
        state = layout.save_state()
        
        assert state["config"]["id"] == "test"
        assert state["config"]["name"] == "Test Layout"
        assert state["config"]["layout_type"] == LayoutType.DOCUMENT.value
        assert len(state["items"]) == 1
        assert state["items"][0]["id"] == "item1"
        assert state["state"] == LayoutState.INACTIVE.value
        
        # Restore state
        result = layout.restore_state(state)
        assert result is True
        assert layout.config.id == "test"
        assert layout.config.name == "Test Layout"


class TestLayoutItemRegistry:
    """Test LayoutItemRegistry functionality."""
    
    def test_widget_registration(self):
        """Test widget registration and retrieval."""
        registry = LayoutItemRegistry()
        widget = QLabel("Test Widget")
        
        # Register widget
        registry.register_widget("widget1", widget)
        
        # Retrieve widget
        retrieved_widget = registry.get_widget("widget1")
        assert retrieved_widget == widget
        
        # Unregister widget
        registry.unregister_widget("widget1")
        retrieved_widget = registry.get_widget("widget1")
        assert retrieved_widget is None
    
    def test_item_registration(self):
        """Test layout item registration and retrieval."""
        registry = LayoutItemRegistry()
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Test Item", LayoutType.DOCUMENT, LayoutGeometry())
        
        # Register item
        registry.register_item(item)
        
        # Retrieve item
        retrieved_item = registry.get_item("item1")
        assert retrieved_item == item
        
        # Check widget was also registered
        retrieved_widget = registry.get_widget("item1")
        assert retrieved_widget == widget
        
        # Get all items
        all_items = registry.get_all_items()
        assert len(all_items) == 1
        assert all_items[0] == item
        
        # Unregister item
        registry.unregister_item("item1")
        retrieved_item = registry.get_item("item1")
        assert retrieved_item is None
        retrieved_widget = registry.get_widget("item1")
        assert retrieved_widget is None
    
    def test_clear_registry(self):
        """Test registry clearing."""
        registry = LayoutItemRegistry()
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Test Item", LayoutType.DOCUMENT, LayoutGeometry())
        
        # Register item and widget
        registry.register_item(item)
        registry.register_widget("widget2", QLabel("Another Widget"))
        
        # Verify items exist
        assert registry.get_item("item1") is not None
        assert registry.get_widget("widget2") is not None
        
        # Clear registry
        registry.clear()
        
        # Verify everything is cleared
        assert registry.get_item("item1") is None
        assert registry.get_widget("widget2") is None
        assert len(registry.get_all_items()) == 0


if __name__ == "__main__":
    pytest.main([__file__])