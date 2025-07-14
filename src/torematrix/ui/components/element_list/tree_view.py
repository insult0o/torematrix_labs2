"""
Hierarchical Tree View Implementation

Main tree view component for hierarchical element display.
"""

from typing import Optional, List, Dict, Any, Union
from PyQt6.QtWidgets import QTreeView, QWidget, QHeaderView, QAbstractItemView
from PyQt6.QtCore import QModelIndex, pyqtSignal, Qt, QTimer, QItemSelectionModel
from PyQt6.QtGui import QKeySequence, QShortcut

from .models.tree_model import ElementTreeModel
from .models.tree_node import TreeNode
from .interfaces.tree_interfaces import ElementProtocol, ElementProvider


class HierarchicalTreeView(QTreeView):
    """Main tree view component for hierarchical element display."""
    
    # Signals
    elementSelected = pyqtSignal(str)  # element_id
    elementDoubleClicked = pyqtSignal(str)  # element_id
    elementExpanded = pyqtSignal(str)  # element_id
    elementCollapsed = pyqtSignal(str)  # element_id
    selectionChanged = pyqtSignal(list)  # List[element_id]
    contextMenuRequested = pyqtSignal(str, object)  # element_id, QPoint
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize hierarchical tree view.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Internal state
        self._element_model: Optional[ElementTreeModel] = None
        self._last_selected_elements: List[str] = []
        self._expansion_state: Dict[str, bool] = {}
        
        # Setup view
        self._setup_view()
        self._setup_signals()
        self._setup_keyboard_shortcuts()
        
        # Update timer for batching selection changes
        self._selection_timer = QTimer()
        self._selection_timer.setSingleShot(True)
        self._selection_timer.timeout.connect(self._emit_selection_changed)
    
    def _setup_view(self) -> None:
        """Configure tree view appearance and behavior."""
        # Header configuration
        self.setHeaderHidden(False)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Interaction settings
        self.setExpandsOnDoubleClick(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(False)  # Allow variable heights
        self.setAnimated(True)  # Enable expand/collapse animations
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Sorting
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # Configure header
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    
    def _setup_signals(self) -> None:
        """Setup signal connections."""
        # Tree view signals
        self.expanded.connect(self._on_item_expanded)
        self.collapsed.connect(self._on_item_collapsed)
        self.doubleClicked.connect(self._on_item_double_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu_requested)
        
        # Selection model signals (will be connected when model is set)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Expand all
        expand_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Plus"), self)
        expand_all_shortcut.activated.connect(self.expandAll)
        
        # Collapse all
        collapse_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Minus"), self)
        collapse_all_shortcut.activated.connect(self.collapseAll)
        
        # Select all
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self.selectAll)
    
    def set_model(self, model: ElementTreeModel) -> None:
        """
        Set the tree model with proper signal connections.
        
        Args:
            model: Element tree model
        """
        # Disconnect old model signals
        if self._element_model:
            self._disconnect_model_signals()
        
        # Set model
        self.setModel(model)
        self._element_model = model
        
        # Connect new model signals
        if model:
            self._connect_model_signals()
            
            # Restore expansion state if available
            self._restore_expansion_state()
    
    def _connect_model_signals(self) -> None:
        """Connect model signals."""
        if not self._element_model:
            return
        
        # Model change signals
        self._element_model.modelRefreshed.connect(self._on_model_refreshed)
        self._element_model.elementAdded.connect(self._on_element_added)
        self._element_model.elementRemoved.connect(self._on_element_removed)
        self._element_model.elementUpdated.connect(self._on_element_updated)
        
        # Selection model signals
        selection_model = self.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)
    
    def _disconnect_model_signals(self) -> None:
        """Disconnect model signals."""
        if not self._element_model:
            return
        
        # Disconnect all signals
        self._element_model.modelRefreshed.disconnect()
        self._element_model.elementAdded.disconnect()
        self._element_model.elementRemoved.disconnect()
        self._element_model.elementUpdated.disconnect()
        
        # Disconnect selection model
        selection_model = self.selectionModel()
        if selection_model:
            selection_model.selectionChanged.disconnect()
    
    # Event handlers
    
    def _on_item_expanded(self, index: QModelIndex) -> None:
        """Handle item expansion."""
        if not index.isValid() or not self._element_model:
            return
        
        element_id = index.data(Qt.ItemDataRole.UserRole)
        if element_id:
            self._expansion_state[element_id] = True
            self.elementExpanded.emit(element_id)
    
    def _on_item_collapsed(self, index: QModelIndex) -> None:
        """Handle item collapse."""
        if not index.isValid() or not self._element_model:
            return
        
        element_id = index.data(Qt.ItemDataRole.UserRole)
        if element_id:
            self._expansion_state[element_id] = False
            self.elementCollapsed.emit(element_id)
    
    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """Handle item double click."""
        if not index.isValid() or not self._element_model:
            return
        
        element_id = index.data(Qt.ItemDataRole.UserRole)
        if element_id:
            self.elementDoubleClicked.emit(element_id)
    
    def _on_context_menu_requested(self, position) -> None:
        """Handle context menu request."""
        index = self.indexAt(position)
        if index.isValid() and self._element_model:
            element_id = index.data(Qt.ItemDataRole.UserRole)
            if element_id:
                global_pos = self.mapToGlobal(position)
                self.contextMenuRequested.emit(element_id, global_pos)
    
    def _on_selection_changed(self, selected, deselected) -> None:
        """Handle selection change with debouncing."""
        # Use timer to batch rapid selection changes
        self._selection_timer.stop()
        self._selection_timer.start(50)  # 50ms debounce
    
    def _emit_selection_changed(self) -> None:
        """Emit selection changed signal."""
        current_selected = self.get_selected_elements()
        if current_selected != self._last_selected_elements:
            self._last_selected_elements = current_selected.copy()
            self.selectionChanged.emit(current_selected)
            
            # Emit single selection signal if exactly one item selected
            if len(current_selected) == 1:
                self.elementSelected.emit(current_selected[0])
    
    def _on_model_refreshed(self) -> None:
        """Handle model refresh."""
        self._restore_expansion_state()
    
    def _on_element_added(self, element_id: str) -> None:
        """Handle element addition."""
        # Could expand parent to show new element
        pass
    
    def _on_element_removed(self, element_id: str) -> None:
        """Handle element removal."""
        # Clean up expansion state
        self._expansion_state.pop(element_id, None)
    
    def _on_element_updated(self, element_id: str) -> None:
        """Handle element update."""
        # Update could trigger visual refresh
        pass
    
    # Public methods for tree operations
    
    def get_selected_elements(self) -> List[str]:
        """Get list of currently selected element IDs."""
        if not self._element_model:
            return []
        
        selected_indexes = self.selectionModel().selectedIndexes()
        element_ids = []
        
        for index in selected_indexes:
            if index.column() == 0:  # Only consider first column to avoid duplicates
                element_id = index.data(Qt.ItemDataRole.UserRole)
                if element_id:
                    element_ids.append(element_id)
        
        return element_ids
    
    def select_elements(self, element_ids: List[str]) -> None:
        """
        Select multiple elements in tree.
        
        Args:
            element_ids: List of element IDs to select
        """
        if not self._element_model or not element_ids:
            return
        
        selection_model = self.selectionModel()
        if not selection_model:
            return
        
        # Clear current selection
        selection_model.clearSelection()
        
        # Select each element
        for element_id in element_ids:
            index = self._element_model.get_index_by_element_id(element_id)
            if index.isValid():
                selection_model.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    
    def select_element(self, element_id: str) -> None:
        """
        Select single element in tree.
        
        Args:
            element_id: Element ID to select
        """
        self.select_elements([element_id])
    
    def expand_element(self, element_id: str) -> bool:
        """
        Expand tree node for specific element.
        
        Args:
            element_id: Element ID to expand
            
        Returns:
            True if expanded successfully
        """
        if not self._element_model:
            return False
        
        index = self._element_model.get_index_by_element_id(element_id)
        if index.isValid():
            self.expand(index)
            return True
        return False
    
    def collapse_element(self, element_id: str) -> bool:
        """
        Collapse tree node for specific element.
        
        Args:
            element_id: Element ID to collapse
            
        Returns:
            True if collapsed successfully
        """
        if not self._element_model:
            return False
        
        index = self._element_model.get_index_by_element_id(element_id)
        if index.isValid():
            self.collapse(index)
            return True
        return False
    
    def scroll_to_element(self, element_id: str) -> bool:
        """
        Scroll to and ensure element is visible.
        
        Args:
            element_id: Element ID to scroll to
            
        Returns:
            True if scrolled successfully
        """
        if not self._element_model:
            return False
        
        index = self._element_model.get_index_by_element_id(element_id)
        if index.isValid():
            self.scrollTo(index, QAbstractItemView.ScrollHint.EnsureVisible)
            return True
        return False
    
    def expand_to_element(self, element_id: str) -> bool:
        """
        Expand all parents to make element visible.
        
        Args:
            element_id: Element ID to expand to
            
        Returns:
            True if expanded successfully
        """
        if not self._element_model:
            return False
        
        node = self._element_model.get_node_by_element_id(element_id)
        if not node:
            return False
        
        # Get path to root and expand all parents
        path = node.path_to_root()[1:]  # Exclude virtual root
        for path_node in path[:-1]:  # Exclude target node itself
            element = path_node.element()
            if element:
                self.expand_element(element.id)
        
        return True
    
    def get_expanded_elements(self) -> List[str]:
        """Get list of expanded element IDs."""
        return [element_id for element_id, expanded in self._expansion_state.items() if expanded]
    
    def set_expanded_elements(self, element_ids: List[str]) -> None:
        """
        Set which elements should be expanded.
        
        Args:
            element_ids: List of element IDs to expand
        """
        # First collapse all
        self.collapseAll()
        self._expansion_state.clear()
        
        # Then expand specified elements
        for element_id in element_ids:
            if self.expand_element(element_id):
                self._expansion_state[element_id] = True
    
    def _save_expansion_state(self) -> None:
        """Save current expansion state."""
        if not self._element_model:
            return
        
        # Walk through all items and record expansion state
        def save_recursive(parent_index: QModelIndex = QModelIndex()):
            row_count = self._element_model.rowCount(parent_index)
            for row in range(row_count):
                index = self._element_model.index(row, 0, parent_index)
                if index.isValid():
                    element_id = index.data(Qt.ItemDataRole.UserRole)
                    if element_id:
                        self._expansion_state[element_id] = self.isExpanded(index)
                    
                    # Recurse into children
                    save_recursive(index)
        
        save_recursive()
    
    def _restore_expansion_state(self) -> None:
        """Restore expansion state from saved state."""
        if not self._element_model or not self._expansion_state:
            return
        
        for element_id, expanded in self._expansion_state.items():
            if expanded:
                self.expand_element(element_id)
    
    def get_scroll_position(self) -> Dict[str, int]:
        """Get current scroll position."""
        return {
            'horizontal': self.horizontalScrollBar().value(),
            'vertical': self.verticalScrollBar().value()
        }
    
    def set_scroll_position(self, position: Dict[str, int]) -> None:
        """
        Set scroll position.
        
        Args:
            position: Dictionary with 'horizontal' and 'vertical' keys
        """
        if 'horizontal' in position:
            self.horizontalScrollBar().setValue(position['horizontal'])
        if 'vertical' in position:
            self.verticalScrollBar().setValue(position['vertical'])
    
    def get_column_widths(self) -> List[int]:
        """Get current column widths."""
        header = self.header()
        return [header.sectionSize(i) for i in range(header.count())]
    
    def set_column_widths(self, widths: List[int]) -> None:
        """
        Set column widths.
        
        Args:
            widths: List of column widths
        """
        header = self.header()
        for i, width in enumerate(widths):
            if i < header.count():
                header.resizeSection(i, width)
    
    def get_sort_order(self) -> Dict[str, Any]:
        """Get current sort order."""
        header = self.header()
        return {
            'column': header.sortIndicatorSection(),
            'order': header.sortIndicatorOrder()
        }
    
    def apply_sort_order(self, sort_order: Dict[str, Any]) -> None:
        """
        Apply sort order.
        
        Args:
            sort_order: Dictionary with 'column' and 'order' keys
        """
        if 'column' in sort_order and 'order' in sort_order:
            self.sortByColumn(sort_order['column'], sort_order['order'])
    
    def refresh_view(self) -> None:
        """Refresh the view."""
        if self._element_model:
            self._save_expansion_state()
            self._element_model.refresh_all()
    
    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get tree statistics."""
        if self._element_model:
            return self._element_model.get_tree_statistics()
        return {}
    
    # Keyboard event handling
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Enter/Return - emit double click signal
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected = self.get_selected_elements()
            if len(selected) == 1:
                self.elementDoubleClicked.emit(selected[0])
            event.accept()
            return
        
        # Space - toggle expansion
        if key == Qt.Key.Key_Space:
            current_index = self.currentIndex()
            if current_index.isValid():
                if self.isExpanded(current_index):
                    self.collapse(current_index)
                else:
                    self.expand(current_index)
            event.accept()
            return
        
        # Pass other events to parent
        super().keyPressEvent(event)