"""Layout templates for ToreMatrix Layout Management System.

This module provides predefined layout templates including Document, Split,
Tabbed, and Multi-panel layouts with complete implementations and customization options.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from abc import abstractmethod

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QStackedWidget, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QResizeEvent

from .base import (
    BaseLayout, LayoutConfiguration, LayoutItem, LayoutType, LayoutState,
    LayoutGeometry
)

logger = logging.getLogger(__name__)


class DocumentLayout(BaseLayout):
    """Document-focused layout with properties and corrections panels.
    
    Layout Structure:
    ┌─────────────────────────────────┐
    │           Main Toolbar          │
    ├─────────────┬───────────────────┤
    │   Document  │     Properties    │
    │   Viewer    │     Panel         │
    │             │                   │
    │             ├───────────────────┤
    │             │   Corrections     │
    │             │   Panel           │
    └─────────────┴───────────────────┘
    """
    
    def __init__(self, config: LayoutConfiguration, parent: Optional[QWidget] = None):
        super().__init__(config, parent)
        self._main_splitter: Optional[QSplitter] = None
        self._right_splitter: Optional[QSplitter] = None
        self._document_area: Optional[QWidget] = None
        self._properties_area: Optional[QWidget] = None
        self._corrections_area: Optional[QWidget] = None
    
    def create_container(self) -> QWidget:
        """Create the document layout container."""
        container = QFrame()
        container.setObjectName("DocumentLayoutContainer")
        
        # Main layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main horizontal splitter
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setObjectName("DocumentMainSplitter")
        layout.addWidget(self._main_splitter)
        
        # Document viewer area (left side)
        self._document_area = QFrame()
        self._document_area.setObjectName("DocumentViewerArea")
        self._document_area.setMinimumWidth(400)
        self._document_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Right side vertical splitter
        self._right_splitter = QSplitter(Qt.Orientation.Vertical)
        self._right_splitter.setObjectName("DocumentRightSplitter")
        
        # Properties panel (top right)
        self._properties_area = QFrame()
        self._properties_area.setObjectName("PropertiesPanel")
        self._properties_area.setMinimumHeight(200)
        self._properties_area.setMaximumHeight(400)
        
        # Corrections panel (bottom right)
        self._corrections_area = QFrame()
        self._corrections_area.setObjectName("CorrectionsPanel")
        self._corrections_area.setMinimumHeight(200)
        
        # Add to splitters
        self._right_splitter.addWidget(self._properties_area)
        self._right_splitter.addWidget(self._corrections_area)
        
        self._main_splitter.addWidget(self._document_area)
        self._main_splitter.addWidget(self._right_splitter)
        
        # Set initial splitter sizes (2:1 ratio)
        self._main_splitter.setSizes([800, 400])
        self._right_splitter.setSizes([200, 200])
        
        return container
    
    def apply_layout(self) -> bool:
        """Apply the document layout configuration."""
        try:
            if not self._container:
                return False
            
            # Apply items to respective areas
            for item in self._config.items:
                area = self._get_area_for_item(item)
                if area and self._add_item_to_area(item, area):
                    self._items[item.id] = item
            
            # Restore splitter states if available
            if "main_splitter" in self._config.splitter_states:
                self._main_splitter.restoreState(self._config.splitter_states["main_splitter"])
            
            if "right_splitter" in self._config.splitter_states:
                self._right_splitter.restoreState(self._config.splitter_states["right_splitter"])
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply document layout: {e}")
            return False
    
    def _get_area_for_item(self, item: LayoutItem) -> Optional[QWidget]:
        """Get the appropriate area for a layout item."""
        item_type = item.properties.get("area_type", "document")
        
        if item_type == "document":
            return self._document_area
        elif item_type == "properties":
            return self._properties_area
        elif item_type == "corrections":
            return self._corrections_area
        else:
            # Default to document area
            return self._document_area
    
    def _add_item_to_area(self, item: LayoutItem, area: QWidget) -> bool:
        """Add an item to a specific area."""
        try:
            # Create layout if doesn't exist
            if not area.layout():
                layout = QVBoxLayout(area)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(2)
            
            # Add widget to area
            area.layout().addWidget(item.widget)
            
            # Apply item properties
            item.widget.setVisible(item.visible)
            
            if item.minimum_size:
                item.widget.setMinimumSize(item.minimum_size)
            
            if item.maximum_size:
                item.widget.setMaximumSize(item.maximum_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add item {item.id} to area: {e}")
            return False
    
    def add_item(self, item: LayoutItem) -> bool:
        """Add an item to the document layout."""
        area = self._get_area_for_item(item)
        if area and self._add_item_to_area(item, area):
            self._items[item.id] = item
            self.item_added.emit(item)
            return True
        return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the document layout."""
        if item_id not in self._items:
            return False
        
        try:
            item = self._items[item_id]
            item.widget.setParent(None)
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item {item_id}: {e}")
            return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Update an existing layout item."""
        if item_id not in self._items:
            return False
        
        # Remove old item
        if not self.remove_item(item_id):
            return False
        
        # Add updated item
        return self.add_item(item)
    
    def save_state(self) -> Dict[str, Any]:
        """Save document layout state."""
        state = super().save_state()
        
        # Save splitter states
        if self._main_splitter:
            state["splitter_states"]["main_splitter"] = self._main_splitter.saveState()
        
        if self._right_splitter:
            state["splitter_states"]["right_splitter"] = self._right_splitter.saveState()
        
        return state


class SplitLayout(BaseLayout):
    """Split layout with horizontal or vertical orientation.
    
    Layout Structure (Horizontal):
    ┌─────────────────────────────────┐
    │           Main Toolbar          │
    ├─────────────────┬───────────────┤
    │    Primary      │   Secondary   │
    │    Content      │   Content     │
    │                 │               │
    │                 │               │
    └─────────────────┴───────────────┘
    """
    
    def __init__(self, config: LayoutConfiguration, parent: Optional[QWidget] = None):
        super().__init__(config, parent)
        self._splitter: Optional[QSplitter] = None
        self._primary_area: Optional[QWidget] = None
        self._secondary_area: Optional[QWidget] = None
        self._orientation = self._get_orientation_from_config()
    
    def _get_orientation_from_config(self) -> Qt.Orientation:
        """Get splitter orientation from configuration."""
        if self._config.layout_type == LayoutType.SPLIT_VERTICAL:
            return Qt.Orientation.Vertical
        else:
            return Qt.Orientation.Horizontal
    
    def create_container(self) -> QWidget:
        """Create the split layout container."""
        container = QFrame()
        container.setObjectName("SplitLayoutContainer")
        
        # Main layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main splitter
        self._splitter = QSplitter(self._orientation)
        self._splitter.setObjectName("SplitLayoutSplitter")
        layout.addWidget(self._splitter)
        
        # Primary area
        self._primary_area = QFrame()
        self._primary_area.setObjectName("PrimaryArea")
        self._primary_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Secondary area
        self._secondary_area = QFrame()
        self._secondary_area.setObjectName("SecondaryArea")
        self._secondary_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Add to splitter
        self._splitter.addWidget(self._primary_area)
        self._splitter.addWidget(self._secondary_area)
        
        # Set equal sizes initially
        self._splitter.setSizes([500, 500])
        
        return container
    
    def apply_layout(self) -> bool:
        """Apply the split layout configuration."""
        try:
            if not self._container:
                return False
            
            # Apply items to respective areas
            for item in self._config.items:
                area = self._get_area_for_item(item)
                if area and self._add_item_to_area(item, area):
                    self._items[item.id] = item
            
            # Restore splitter state if available
            if "main_splitter" in self._config.splitter_states:
                self._splitter.restoreState(self._config.splitter_states["main_splitter"])
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply split layout: {e}")
            return False
    
    def _get_area_for_item(self, item: LayoutItem) -> Optional[QWidget]:
        """Get the appropriate area for a layout item."""
        area_type = item.properties.get("area_type", "primary")
        
        if area_type == "secondary":
            return self._secondary_area
        else:
            return self._primary_area
    
    def _add_item_to_area(self, item: LayoutItem, area: QWidget) -> bool:
        """Add an item to a specific area."""
        try:
            # Create layout if doesn't exist
            if not area.layout():
                layout = QVBoxLayout(area)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(2)
            
            # Add widget to area
            area.layout().addWidget(item.widget)
            
            # Apply item properties
            item.widget.setVisible(item.visible)
            
            if item.minimum_size:
                item.widget.setMinimumSize(item.minimum_size)
            
            if item.maximum_size:
                item.widget.setMaximumSize(item.maximum_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add item {item.id} to area: {e}")
            return False
    
    def add_item(self, item: LayoutItem) -> bool:
        """Add an item to the split layout."""
        area = self._get_area_for_item(item)
        if area and self._add_item_to_area(item, area):
            self._items[item.id] = item
            self.item_added.emit(item)
            return True
        return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the split layout."""
        if item_id not in self._items:
            return False
        
        try:
            item = self._items[item_id]
            item.widget.setParent(None)
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item {item_id}: {e}")
            return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Update an existing layout item."""
        if item_id not in self._items:
            return False
        
        # Remove old item
        if not self.remove_item(item_id):
            return False
        
        # Add updated item
        return self.add_item(item)
    
    def save_state(self) -> Dict[str, Any]:
        """Save split layout state."""
        state = super().save_state()
        
        # Save splitter state
        if self._splitter:
            state["splitter_states"]["main_splitter"] = self._splitter.saveState()
        
        return state


class TabbedLayout(BaseLayout):
    """Tabbed layout with multiple content areas.
    
    Layout Structure:
    ┌─────────────────────────────────┐
    │           Main Toolbar          │
    ├─────────────────────────────────┤
    │ Tab1 │ Tab2 │ Tab3 │            │
    ├─────────────────────────────────┤
    │                                 │
    │         Active Tab Content      │
    │                                 │
    │                                 │
    └─────────────────────────────────┘
    """
    
    def __init__(self, config: LayoutConfiguration, parent: Optional[QWidget] = None):
        super().__init__(config, parent)
        self._tab_widget: Optional[QTabWidget] = None
        self._tab_areas: Dict[str, QWidget] = {}
    
    def create_container(self) -> QWidget:
        """Create the tabbed layout container."""
        container = QFrame()
        container.setObjectName("TabbedLayoutContainer")
        
        # Main layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("TabbedLayoutTabWidget")
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        layout.addWidget(self._tab_widget)
        
        # Connect tab signals
        self._tab_widget.tabCloseRequested.connect(self._handle_tab_close_request)
        self._tab_widget.currentChanged.connect(self._handle_tab_changed)
        
        return container
    
    def apply_layout(self) -> bool:
        """Apply the tabbed layout configuration."""
        try:
            if not self._container:
                return False
            
            # Group items by tab
            tabs: Dict[str, List[LayoutItem]] = {}
            for item in self._config.items:
                tab_name = item.properties.get("tab_name", "Main")
                if tab_name not in tabs:
                    tabs[tab_name] = []
                tabs[tab_name].append(item)
            
            # Create tabs and add items
            for tab_name, items in tabs.items():
                tab_area = self._create_tab_area(tab_name)
                
                for item in items:
                    if self._add_item_to_tab(item, tab_area):
                        self._items[item.id] = item
            
            # Restore current tab if specified
            current_tab = self._config.properties.get("current_tab", 0)
            if isinstance(current_tab, int) and 0 <= current_tab < self._tab_widget.count():
                self._tab_widget.setCurrentIndex(current_tab)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply tabbed layout: {e}")
            return False
    
    def _create_tab_area(self, tab_name: str) -> QWidget:
        """Create a new tab area."""
        tab_area = QFrame()
        tab_area.setObjectName(f"TabArea_{tab_name}")
        
        # Create layout for tab content
        layout = QVBoxLayout(tab_area)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Add to tab widget
        self._tab_widget.addTab(tab_area, tab_name)
        self._tab_areas[tab_name] = tab_area
        
        return tab_area
    
    def _add_item_to_tab(self, item: LayoutItem, tab_area: QWidget) -> bool:
        """Add an item to a specific tab."""
        try:
            # Add widget to tab area
            tab_area.layout().addWidget(item.widget)
            
            # Apply item properties
            item.widget.setVisible(item.visible)
            
            if item.minimum_size:
                item.widget.setMinimumSize(item.minimum_size)
            
            if item.maximum_size:
                item.widget.setMaximumSize(item.maximum_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add item {item.id} to tab: {e}")
            return False
    
    def add_item(self, item: LayoutItem) -> bool:
        """Add an item to the tabbed layout."""
        tab_name = item.properties.get("tab_name", "Main")
        
        # Create tab if doesn't exist
        if tab_name not in self._tab_areas:
            tab_area = self._create_tab_area(tab_name)
        else:
            tab_area = self._tab_areas[tab_name]
        
        if self._add_item_to_tab(item, tab_area):
            self._items[item.id] = item
            self.item_added.emit(item)
            return True
        return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the tabbed layout."""
        if item_id not in self._items:
            return False
        
        try:
            item = self._items[item_id]
            item.widget.setParent(None)
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item {item_id}: {e}")
            return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Update an existing layout item."""
        if item_id not in self._items:
            return False
        
        # Remove old item
        if not self.remove_item(item_id):
            return False
        
        # Add updated item
        return self.add_item(item)
    
    def _handle_tab_close_request(self, index: int) -> None:
        """Handle tab close request."""
        if 0 <= index < self._tab_widget.count():
            tab_name = self._tab_widget.tabText(index)
            self._tab_widget.removeTab(index)
            
            # Remove from areas dict
            if tab_name in self._tab_areas:
                del self._tab_areas[tab_name]
    
    def _handle_tab_changed(self, index: int) -> None:
        """Handle tab changed."""
        # Update configuration
        self._config.properties["current_tab"] = index
    
    def save_state(self) -> Dict[str, Any]:
        """Save tabbed layout state."""
        state = super().save_state()
        
        # Save current tab
        if self._tab_widget:
            state["config"]["properties"]["current_tab"] = self._tab_widget.currentIndex()
        
        return state


class MultiPanelLayout(BaseLayout):
    """Multi-panel layout with flexible arrangement.
    
    Supports complex arrangements with multiple splitters and areas.
    """
    
    def __init__(self, config: LayoutConfiguration, parent: Optional[QWidget] = None):
        super().__init__(config, parent)
        self._panels: Dict[str, QWidget] = {}
        self._splitters: Dict[str, QSplitter] = {}
        self._main_container: Optional[QWidget] = None
    
    def create_container(self) -> QWidget:
        """Create the multi-panel layout container."""
        container = QFrame()
        container.setObjectName("MultiPanelLayoutContainer")
        
        # Main layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create panel structure from configuration
        panel_structure = self._config.properties.get("panel_structure", self._get_default_structure())
        self._main_container = self._create_panel_structure(panel_structure)
        
        if self._main_container:
            layout.addWidget(self._main_container)
        
        return container
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Get default panel structure."""
        return {
            "type": "horizontal_split",
            "panels": [
                {"type": "panel", "name": "left", "size": 300},
                {
                    "type": "vertical_split",
                    "panels": [
                        {"type": "panel", "name": "top_right", "size": 400},
                        {"type": "panel", "name": "bottom_right", "size": 200}
                    ]
                }
            ]
        }
    
    def _create_panel_structure(self, structure: Dict[str, Any]) -> QWidget:
        """Create panel structure from configuration."""
        structure_type = structure.get("type", "panel")
        
        if structure_type == "panel":
            return self._create_panel(structure)
        elif structure_type == "horizontal_split":
            return self._create_horizontal_split(structure)
        elif structure_type == "vertical_split":
            return self._create_vertical_split(structure)
        else:
            logger.warning(f"Unknown structure type: {structure_type}")
            return QFrame()
    
    def _create_panel(self, config: Dict[str, Any]) -> QWidget:
        """Create a single panel."""
        panel_name = config.get("name", f"panel_{len(self._panels)}")
        
        panel = QFrame()
        panel.setObjectName(f"Panel_{panel_name}")
        panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Create layout for panel content
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        self._panels[panel_name] = panel
        return panel
    
    def _create_horizontal_split(self, config: Dict[str, Any]) -> QSplitter:
        """Create horizontal splitter."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("HorizontalSplitter")
        
        panels = config.get("panels", [])
        for panel_config in panels:
            panel_widget = self._create_panel_structure(panel_config)
            splitter.addWidget(panel_widget)
        
        # Set sizes if specified
        sizes = [panel.get("size", 100) for panel in panels]
        if sizes:
            splitter.setSizes(sizes)
        
        splitter_name = config.get("name", f"hsplit_{len(self._splitters)}")
        self._splitters[splitter_name] = splitter
        
        return splitter
    
    def _create_vertical_split(self, config: Dict[str, Any]) -> QSplitter:
        """Create vertical splitter."""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("VerticalSplitter")
        
        panels = config.get("panels", [])
        for panel_config in panels:
            panel_widget = self._create_panel_structure(panel_config)
            splitter.addWidget(panel_widget)
        
        # Set sizes if specified
        sizes = [panel.get("size", 100) for panel in panels]
        if sizes:
            splitter.setSizes(sizes)
        
        splitter_name = config.get("name", f"vsplit_{len(self._splitters)}")
        self._splitters[splitter_name] = splitter
        
        return splitter
    
    def apply_layout(self) -> bool:
        """Apply the multi-panel layout configuration."""
        try:
            if not self._container:
                return False
            
            # Apply items to respective panels
            for item in self._config.items:
                panel = self._get_panel_for_item(item)
                if panel and self._add_item_to_panel(item, panel):
                    self._items[item.id] = item
            
            # Restore splitter states if available
            for splitter_name, splitter_state in self._config.splitter_states.items():
                if splitter_name in self._splitters:
                    self._splitters[splitter_name].restoreState(splitter_state)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply multi-panel layout: {e}")
            return False
    
    def _get_panel_for_item(self, item: LayoutItem) -> Optional[QWidget]:
        """Get the appropriate panel for a layout item."""
        panel_name = item.properties.get("panel_name", "left")
        return self._panels.get(panel_name)
    
    def _add_item_to_panel(self, item: LayoutItem, panel: QWidget) -> bool:
        """Add an item to a specific panel."""
        try:
            # Add widget to panel
            panel.layout().addWidget(item.widget)
            
            # Apply item properties
            item.widget.setVisible(item.visible)
            
            if item.minimum_size:
                item.widget.setMinimumSize(item.minimum_size)
            
            if item.maximum_size:
                item.widget.setMaximumSize(item.maximum_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add item {item.id} to panel: {e}")
            return False
    
    def add_item(self, item: LayoutItem) -> bool:
        """Add an item to the multi-panel layout."""
        panel = self._get_panel_for_item(item)
        if panel and self._add_item_to_panel(item, panel):
            self._items[item.id] = item
            self.item_added.emit(item)
            return True
        return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the multi-panel layout."""
        if item_id not in self._items:
            return False
        
        try:
            item = self._items[item_id]
            item.widget.setParent(None)
            del self._items[item_id]
            self.item_removed.emit(item_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item {item_id}: {e}")
            return False
    
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Update an existing layout item."""
        if item_id not in self._items:
            return False
        
        # Remove old item
        if not self.remove_item(item_id):
            return False
        
        # Add updated item
        return self.add_item(item)
    
    def save_state(self) -> Dict[str, Any]:
        """Save multi-panel layout state."""
        state = super().save_state()
        
        # Save splitter states
        for splitter_name, splitter in self._splitters.items():
            state["splitter_states"][splitter_name] = splitter.saveState()
        
        return state


# Template factory functions
def create_document_layout(config: LayoutConfiguration) -> DocumentLayout:
    """Create a document layout instance."""
    return DocumentLayout(config)


def create_split_horizontal_layout(config: LayoutConfiguration) -> SplitLayout:
    """Create a horizontal split layout instance."""
    config.layout_type = LayoutType.SPLIT_HORIZONTAL
    return SplitLayout(config)


def create_split_vertical_layout(config: LayoutConfiguration) -> SplitLayout:
    """Create a vertical split layout instance."""
    config.layout_type = LayoutType.SPLIT_VERTICAL
    return SplitLayout(config)


def create_tabbed_layout(config: LayoutConfiguration) -> TabbedLayout:
    """Create a tabbed layout instance."""
    return TabbedLayout(config)


def create_multi_panel_layout(config: LayoutConfiguration) -> MultiPanelLayout:
    """Create a multi-panel layout instance."""
    return MultiPanelLayout(config)


# Template registry for easy access
LAYOUT_TEMPLATES = {
    LayoutType.DOCUMENT: create_document_layout,
    LayoutType.SPLIT_HORIZONTAL: create_split_horizontal_layout,
    LayoutType.SPLIT_VERTICAL: create_split_vertical_layout,
    LayoutType.TABBED: create_tabbed_layout,
    LayoutType.MULTI_PANEL: create_multi_panel_layout,
}