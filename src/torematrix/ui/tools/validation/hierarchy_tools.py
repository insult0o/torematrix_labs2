"""
Interactive hierarchy management tools for document validation.

This module provides UI components for managing document element hierarchies.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QToolButton, QCheckBox, QSplitter, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Rect


logger = logging.getLogger(__name__)


class HierarchyToolAction(Enum):
    """Actions available in hierarchy tools."""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    VALIDATE = "validate"


@dataclass
class HierarchyDisplayConfig:
    """Configuration for hierarchy display."""
    show_element_types: bool = True
    show_element_bounds: bool = False


class HierarchyTreeItem(QTreeWidgetItem):
    """Custom tree item for hierarchy display."""
    
    def __init__(self, element: Element, parent: Optional[QTreeWidgetItem] = None):
        super().__init__(parent)
        self.element = element
        self._setup_item()
    
    def _setup_item(self):
        """Set up the tree item display."""
        display_text = self.element.text
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."
        self.setText(0, display_text)
        self.setText(1, self.element.element_type.value)
        
        bounds = self.element.bounds
        self.setText(2, f"({bounds.x:.0f}, {bounds.y:.0f})")
        self.setText(3, f"{bounds.width:.0f}x{bounds.height:.0f}")
        self.setText(4, self.element.id)
    
    def get_element_id(self) -> str:
        """Get the element ID."""
        return self.element.id
    
    def get_element_type(self) -> ElementType:
        """Get the element type."""
        return self.element.element_type


class HierarchyTreeWidget(QTreeWidget):
    """Custom tree widget for hierarchy management."""
    
    element_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.element_items: Dict[str, HierarchyTreeItem] = {}
        self.config = HierarchyDisplayConfig()
        
        self._setup_tree()
    
    def _setup_tree(self):
        """Set up the tree widget."""
        self.setHeaderLabels(["Element", "Type", "Position", "Size", "ID"])
        self.setRootIsDecorated(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAnimated(True)
        
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
    
    def refresh_hierarchy(self):
        """Refresh the hierarchy display."""
        if not self.state_store:
            return
        
        self.clear()
        self.element_items.clear()
        
        elements = self.state_store.get_all_elements()
        if not elements:
            return
        
        self._build_tree(elements)
        self.expandAll()
    
    def _build_tree(self, elements: Dict[str, Element]):
        """Build the tree structure."""
        root_elements = [e for e in elements.values() if not e.parent_id]
        
        for element in root_elements:
            self._create_tree_item(element, elements, None)
    
    def _create_tree_item(self, element: Element, elements: Dict[str, Element], 
                         parent_item: Optional[HierarchyTreeItem] = None):
        """Create a tree item for an element."""
        if parent_item:
            item = HierarchyTreeItem(element, parent_item)
        else:
            item = HierarchyTreeItem(element)
            self.addTopLevelItem(item)
        
        self.element_items[element.id] = item
        
        if element.children:
            for child_id in element.children:
                if child_id in elements:
                    child_element = elements[child_id]
                    self._create_tree_item(child_element, elements, item)
    
    def get_selected_elements(self) -> List[str]:
        """Get selected element IDs."""
        selected_items = self.selectedItems()
        return [item.get_element_id() for item in selected_items 
                if isinstance(item, HierarchyTreeItem)]
    
    def select_element(self, element_id: str):
        """Select an element in the tree."""
        if element_id in self.element_items:
            item = self.element_items[element_id]
            self.setCurrentItem(item)
            self.scrollToItem(item)
    
    def _on_selection_changed(self):
        """Handle selection change."""
        selected_items = self.selectedItems()
        if selected_items:
            item = selected_items[0]
            if isinstance(item, HierarchyTreeItem):
                self.element_selected.emit(item.get_element_id())


class HierarchyControlPanel(QWidget):
    """Control panel for hierarchy management."""
    
    action_requested = pyqtSignal(HierarchyToolAction, list)
    config_changed = pyqtSignal(HierarchyDisplayConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = HierarchyDisplayConfig()
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        self.move_up_btn = QToolButton()
        self.move_up_btn.setText("Move Up")
        self.move_up_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.MOVE_UP))
        actions_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QToolButton()
        self.move_down_btn.setText("Move Down")
        self.move_down_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.MOVE_DOWN))
        actions_layout.addWidget(self.move_down_btn)
        
        self.validate_btn = QToolButton()
        self.validate_btn.setText("Validate")
        self.validate_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.VALIDATE))
        actions_layout.addWidget(self.validate_btn)
        
        layout.addWidget(actions_group)
        
        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.show_types_cb = QCheckBox("Show Element Types")
        self.show_types_cb.setChecked(self.config.show_element_types)
        self.show_types_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_types_cb)
        
        self.show_bounds_cb = QCheckBox("Show Element Bounds")
        self.show_bounds_cb.setChecked(self.config.show_element_bounds)
        self.show_bounds_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_bounds_cb)
        
        layout.addWidget(display_group)
        layout.addStretch()
    
    def set_selected_elements(self, element_ids: List[str]):
        """Update button states based on selected elements."""
        has_selection = len(element_ids) > 0
        
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)
        self.validate_btn.setEnabled(True)
    
    def _emit_action(self, action: HierarchyToolAction):
        """Emit action signal."""
        self.action_requested.emit(action, [])
    
    def _on_config_changed(self):
        """Handle configuration change."""
        self.config.show_element_types = self.show_types_cb.isChecked()
        self.config.show_element_bounds = self.show_bounds_cb.isChecked()
        self.config_changed.emit(self.config)


class HierarchyToolsWidget(QWidget):
    """Main widget for hierarchy management tools."""
    
    element_selected = pyqtSignal(str)
    element_changed = pyqtSignal(str)
    validation_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.event_bus = None
        self.selected_elements = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.tree_widget = HierarchyTreeWidget()
        splitter.addWidget(self.tree_widget)
        
        self.control_panel = HierarchyControlPanel()
        splitter.addWidget(self.control_panel)
        
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.tree_widget.element_selected.connect(self._on_element_selected)
        self.control_panel.action_requested.connect(self._on_action_requested)
        self.control_panel.config_changed.connect(self._on_config_changed)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
        self.tree_widget.set_hierarchy_manager(manager)
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
        self.tree_widget.set_state_store(store)
    
    def set_event_bus(self, bus: EventBus):
        """Set the event bus."""
        self.event_bus = bus
    
    def refresh(self):
        """Refresh the hierarchy display."""
        self.tree_widget.refresh_hierarchy()
    
    def select_element(self, element_id: str):
        """Select an element."""
        self.tree_widget.select_element(element_id)
    
    def _on_element_selected(self, element_id: str):
        """Handle element selection."""
        self.selected_elements = [element_id]
        self.control_panel.set_selected_elements(self.selected_elements)
        self.element_selected.emit(element_id)
    
    def _on_action_requested(self, action: HierarchyToolAction, element_ids: List[str]):
        """Handle action request."""
        if action == HierarchyToolAction.VALIDATE:
            self.validation_requested.emit()
    
    def _on_config_changed(self, config: HierarchyDisplayConfig):
        """Handle configuration change."""
        pass