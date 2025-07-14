"""Unit tests for layout templates."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtWidgets import QWidget, QLabel, QSplitter, QTabWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtTest import QSignalSpy

from torematrix.ui.layouts.templates import (
    DocumentLayout, SplitLayout, TabbedLayout, MultiPanelLayout,
    create_document_layout, create_split_horizontal_layout, 
    create_split_vertical_layout, create_tabbed_layout,
    create_multi_panel_layout, LAYOUT_TEMPLATES
)
from torematrix.ui.layouts.base import (
    LayoutType, LayoutGeometry, LayoutItem, LayoutConfiguration
)


class TestDocumentLayout:
    """Test DocumentLayout implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = LayoutConfiguration(
            id="doc-layout",
            name="Document Layout",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(width=1200, height=800)
        )
        self.layout = DocumentLayout(self.config)
    
    def test_initialization(self):
        """Test document layout initialization."""
        assert self.layout.config == self.config
        assert self.layout._main_splitter is None
        assert self.layout._right_splitter is None
        assert self.layout._document_area is None
        assert self.layout._properties_area is None
        assert self.layout._corrections_area is None
    
    def test_create_container(self):
        """Test container creation."""
        container = self.layout.create_container()
        
        assert container is not None
        assert container.objectName() == "DocumentLayoutContainer"
        assert self.layout._main_splitter is not None
        assert self.layout._right_splitter is not None
        assert self.layout._document_area is not None
        assert self.layout._properties_area is not None
        assert self.layout._corrections_area is not None
        
        # Check splitter orientations
        assert self.layout._main_splitter.orientation() == Qt.Orientation.Horizontal
        assert self.layout._right_splitter.orientation() == Qt.Orientation.Vertical
    
    def test_apply_layout(self):
        """Test layout application."""
        # Create container first
        container = self.layout.create_container()
        self.layout._container = container
        
        result = self.layout.apply_layout()
        assert result is True
    
    def test_add_item_to_document_area(self):
        """Test adding item to document area."""
        # Create container
        container = self.layout.create_container()
        self.layout._container = container
        
        # Create item for document area
        widget = QLabel("Document Widget")
        item = LayoutItem(
            id="doc-item",
            widget=widget,
            name="Document Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            properties={"area_type": "document"}
        )
        
        # Track signals
        spy = QSignalSpy(self.layout.item_added)
        
        result = self.layout.add_item(item)
        
        assert result is True
        assert "doc-item" in self.layout.items
        assert len(spy) == 1
    
    def test_add_item_to_properties_area(self):
        """Test adding item to properties area."""
        # Create container
        container = self.layout.create_container()
        self.layout._container = container
        
        # Create item for properties area
        widget = QLabel("Properties Widget")
        item = LayoutItem(
            id="props-item",
            widget=widget,
            name="Properties Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            properties={"area_type": "properties"}
        )
        
        result = self.layout.add_item(item)
        
        assert result is True
        assert "props-item" in self.layout.items
    
    def test_add_item_to_corrections_area(self):
        """Test adding item to corrections area."""
        # Create container
        container = self.layout.create_container()
        self.layout._container = container
        
        # Create item for corrections area
        widget = QLabel("Corrections Widget")
        item = LayoutItem(
            id="corr-item",
            widget=widget,
            name="Corrections Item",
            layout_type=LayoutType.DOCUMENT,
            geometry=LayoutGeometry(),
            properties={"area_type": "corrections"}
        )
        
        result = self.layout.add_item(item)
        
        assert result is True
        assert "corr-item" in self.layout.items
    
    def test_remove_item(self):
        """Test item removal."""
        # Setup
        container = self.layout.create_container()
        self.layout._container = container
        
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        self.layout.add_item(item)
        
        # Track signals
        spy = QSignalSpy(self.layout.item_removed)
        
        # Remove item
        result = self.layout.remove_item("item1")
        
        assert result is True
        assert "item1" not in self.layout.items
        assert len(spy) == 1
        assert spy[0][0] == "item1"
    
    def test_update_item(self):
        """Test item update."""
        # Setup
        container = self.layout.create_container()
        self.layout._container = container
        
        widget = QLabel("Test Widget")
        item = LayoutItem("item1", widget, "Original Name", LayoutType.DOCUMENT, LayoutGeometry())
        self.layout.add_item(item)
        
        # Update item
        updated_item = LayoutItem("item1", widget, "Updated Name", LayoutType.DOCUMENT, LayoutGeometry())
        result = self.layout.update_item("item1", updated_item)
        
        assert result is True
        assert self.layout.get_item("item1").name == "Updated Name"
    
    def test_save_state(self):
        """Test state saving."""
        # Create container to have splitters
        container = self.layout.create_container()
        self.layout._container = container
        
        state = self.layout.save_state()
        
        assert "config" in state
        assert "items" in state
        assert "splitter_states" in state
        assert state["config"]["layout_type"] == LayoutType.DOCUMENT.value


class TestSplitLayout:
    """Test SplitLayout implementation."""
    
    def test_horizontal_split_initialization(self):
        """Test horizontal split layout initialization."""
        config = LayoutConfiguration(
            id="split-h", name="Horizontal Split", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry()
        )
        layout = SplitLayout(config)
        
        assert layout.config == config
        assert layout._orientation == Qt.Orientation.Horizontal
    
    def test_vertical_split_initialization(self):
        """Test vertical split layout initialization."""
        config = LayoutConfiguration(
            id="split-v", name="Vertical Split", 
            layout_type=LayoutType.SPLIT_VERTICAL, geometry=LayoutGeometry()
        )
        layout = SplitLayout(config)
        
        assert layout.config == config
        assert layout._orientation == Qt.Orientation.Vertical
    
    def test_create_container(self):
        """Test split container creation."""
        config = LayoutConfiguration(
            id="split-h", name="Horizontal Split", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry()
        )
        layout = SplitLayout(config)
        
        container = layout.create_container()
        
        assert container is not None
        assert layout._splitter is not None
        assert layout._primary_area is not None
        assert layout._secondary_area is not None
        assert layout._splitter.orientation() == Qt.Orientation.Horizontal
    
    def test_add_item_to_primary_area(self):
        """Test adding item to primary area."""
        config = LayoutConfiguration(
            id="split-h", name="Horizontal Split", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry()
        )
        layout = SplitLayout(config)
        
        # Create container
        container = layout.create_container()
        layout._container = container
        
        # Create item for primary area
        widget = QLabel("Primary Widget")
        item = LayoutItem(
            id="primary-item",
            widget=widget,
            name="Primary Item",
            layout_type=LayoutType.SPLIT_HORIZONTAL,
            geometry=LayoutGeometry(),
            properties={"area_type": "primary"}
        )
        
        result = layout.add_item(item)
        assert result is True
        assert "primary-item" in layout.items
    
    def test_add_item_to_secondary_area(self):
        """Test adding item to secondary area."""
        config = LayoutConfiguration(
            id="split-h", name="Horizontal Split", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry()
        )
        layout = SplitLayout(config)
        
        # Create container
        container = layout.create_container()
        layout._container = container
        
        # Create item for secondary area
        widget = QLabel("Secondary Widget")
        item = LayoutItem(
            id="secondary-item",
            widget=widget,
            name="Secondary Item",
            layout_type=LayoutType.SPLIT_HORIZONTAL,
            geometry=LayoutGeometry(),
            properties={"area_type": "secondary"}
        )
        
        result = layout.add_item(item)
        assert result is True
        assert "secondary-item" in layout.items


class TestTabbedLayout:
    """Test TabbedLayout implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = LayoutConfiguration(
            id="tabbed", name="Tabbed Layout", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry()
        )
        self.layout = TabbedLayout(self.config)
    
    def test_initialization(self):
        """Test tabbed layout initialization."""
        assert self.layout.config == self.config
        assert self.layout._tab_widget is None
        assert len(self.layout._tab_areas) == 0
    
    def test_create_container(self):
        """Test tabbed container creation."""
        container = self.layout.create_container()
        
        assert container is not None
        assert self.layout._tab_widget is not None
        assert isinstance(self.layout._tab_widget, QTabWidget)
        assert self.layout._tab_widget.isTabsClosable() is True
        assert self.layout._tab_widget.isMovable() is True
    
    def test_add_item_to_new_tab(self):
        """Test adding item to new tab."""
        # Create container
        container = self.layout.create_container()
        self.layout._container = container
        
        # Create item for new tab
        widget = QLabel("Tab Widget")
        item = LayoutItem(
            id="tab-item",
            widget=widget,
            name="Tab Item",
            layout_type=LayoutType.TABBED,
            geometry=LayoutGeometry(),
            properties={"tab_name": "Test Tab"}
        )
        
        result = self.layout.add_item(item)
        
        assert result is True
        assert "tab-item" in self.layout.items
        assert "Test Tab" in self.layout._tab_areas
        assert self.layout._tab_widget.count() == 1
        assert self.layout._tab_widget.tabText(0) == "Test Tab"
    
    def test_add_item_to_existing_tab(self):
        """Test adding item to existing tab."""
        # Create container
        container = self.layout.create_container()
        self.layout._container = container
        
        # Add first item to create tab
        widget1 = QLabel("Widget 1")
        item1 = LayoutItem(
            id="item1", widget=widget1, name="Item 1", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry(),
            properties={"tab_name": "Shared Tab"}
        )
        self.layout.add_item(item1)
        
        # Add second item to same tab
        widget2 = QLabel("Widget 2")
        item2 = LayoutItem(
            id="item2", widget=widget2, name="Item 2", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry(),
            properties={"tab_name": "Shared Tab"}
        )
        result = self.layout.add_item(item2)
        
        assert result is True
        assert "item2" in self.layout.items
        assert self.layout._tab_widget.count() == 1  # Still only one tab
    
    def test_apply_layout_with_current_tab(self):
        """Test layout application with current tab setting."""
        # Add items first
        widget1 = QLabel("Widget 1")
        item1 = LayoutItem(
            id="item1", widget=widget1, name="Item 1", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry(),
            properties={"tab_name": "Tab 1"}
        )
        
        widget2 = QLabel("Widget 2")
        item2 = LayoutItem(
            id="item2", widget=widget2, name="Item 2", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry(),
            properties={"tab_name": "Tab 2"}
        )
        
        self.config.items = [item1, item2]
        self.config.properties["current_tab"] = 1
        
        # Create container and apply layout
        container = self.layout.create_container()
        self.layout._container = container
        
        result = self.layout.apply_layout()
        
        assert result is True
        assert self.layout._tab_widget.count() == 2
        assert self.layout._tab_widget.currentIndex() == 1


class TestMultiPanelLayout:
    """Test MultiPanelLayout implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = LayoutConfiguration(
            id="multi", name="Multi Panel Layout", 
            layout_type=LayoutType.MULTI_PANEL, geometry=LayoutGeometry()
        )
        self.layout = MultiPanelLayout(self.config)
    
    def test_initialization(self):
        """Test multi-panel layout initialization."""
        assert self.layout.config == self.config
        assert len(self.layout._panels) == 0
        assert len(self.layout._splitters) == 0
        assert self.layout._main_container is None
    
    def test_create_container_with_default_structure(self):
        """Test container creation with default structure."""
        container = self.layout.create_container()
        
        assert container is not None
        assert self.layout._main_container is not None
        assert len(self.layout._panels) > 0
        assert len(self.layout._splitters) > 0
    
    def test_create_container_with_custom_structure(self):
        """Test container creation with custom structure."""
        # Define custom panel structure
        panel_structure = {
            "type": "vertical_split",
            "panels": [
                {"type": "panel", "name": "top", "size": 300},
                {"type": "panel", "name": "bottom", "size": 500}
            ]
        }
        self.config.properties["panel_structure"] = panel_structure
        
        container = self.layout.create_container()
        
        assert container is not None
        assert "top" in self.layout._panels
        assert "bottom" in self.layout._panels
    
    def test_add_item_to_specific_panel(self):
        """Test adding item to specific panel."""
        # Create container with default structure
        container = self.layout.create_container()
        self.layout._container = container
        
        # Create item for specific panel
        widget = QLabel("Panel Widget")
        item = LayoutItem(
            id="panel-item",
            widget=widget,
            name="Panel Item",
            layout_type=LayoutType.MULTI_PANEL,
            geometry=LayoutGeometry(),
            properties={"panel_name": "left"}
        )
        
        result = self.layout.add_item(item)
        
        assert result is True
        assert "panel-item" in self.layout.items


class TestTemplateFactories:
    """Test template factory functions."""
    
    def test_create_document_layout(self):
        """Test document layout factory."""
        config = LayoutConfiguration(
            id="doc", name="Document", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        layout = create_document_layout(config)
        
        assert isinstance(layout, DocumentLayout)
        assert layout.config == config
    
    def test_create_split_horizontal_layout(self):
        """Test horizontal split layout factory."""
        config = LayoutConfiguration(
            id="split-h", name="Horizontal Split", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry()
        )
        
        layout = create_split_horizontal_layout(config)
        
        assert isinstance(layout, SplitLayout)
        assert layout.config.layout_type == LayoutType.SPLIT_HORIZONTAL
    
    def test_create_split_vertical_layout(self):
        """Test vertical split layout factory."""
        config = LayoutConfiguration(
            id="split-v", name="Vertical Split", 
            layout_type=LayoutType.SPLIT_VERTICAL, geometry=LayoutGeometry()
        )
        
        layout = create_split_vertical_layout(config)
        
        assert isinstance(layout, SplitLayout)
        assert layout.config.layout_type == LayoutType.SPLIT_VERTICAL
    
    def test_create_tabbed_layout(self):
        """Test tabbed layout factory."""
        config = LayoutConfiguration(
            id="tabbed", name="Tabbed", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry()
        )
        
        layout = create_tabbed_layout(config)
        
        assert isinstance(layout, TabbedLayout)
        assert layout.config == config
    
    def test_create_multi_panel_layout(self):
        """Test multi-panel layout factory."""
        config = LayoutConfiguration(
            id="multi", name="Multi Panel", 
            layout_type=LayoutType.MULTI_PANEL, geometry=LayoutGeometry()
        )
        
        layout = create_multi_panel_layout(config)
        
        assert isinstance(layout, MultiPanelLayout)
        assert layout.config == config
    
    def test_layout_templates_registry(self):
        """Test LAYOUT_TEMPLATES registry."""
        assert LayoutType.DOCUMENT in LAYOUT_TEMPLATES
        assert LayoutType.SPLIT_HORIZONTAL in LAYOUT_TEMPLATES
        assert LayoutType.SPLIT_VERTICAL in LAYOUT_TEMPLATES
        assert LayoutType.TABBED in LAYOUT_TEMPLATES
        assert LayoutType.MULTI_PANEL in LAYOUT_TEMPLATES
        
        # Test that factories work
        config = LayoutConfiguration(
            id="test", name="Test", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        factory = LAYOUT_TEMPLATES[LayoutType.DOCUMENT]
        layout = factory(config)
        
        assert isinstance(layout, DocumentLayout)


if __name__ == "__main__":
    pytest.main([__file__])