"""
Multi-Selection Handler for Element Tree View

Provides advanced selection capabilities with keyboard modifiers and range selection.
"""

from typing import List, Set, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QModelIndex, Qt, QItemSelection
from PyQt6.QtWidgets import QTreeView
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from ..models.tree_node import TreeNode


class SelectionRange:
    """Represents a selection range in the tree."""
    
    def __init__(self, start_index: QModelIndex, end_index: QModelIndex):
        self.start_index = start_index
        self.end_index = end_index
    
    def contains(self, index: QModelIndex) -> bool:
        """Check if index is within this range."""
        # This is a simplified implementation
        # In a real tree, range selection is more complex
        return index == self.start_index or index == self.end_index
    
    def to_index_list(self, model) -> List[QModelIndex]:
        """Convert range to list of indices."""
        indices = []
        # For tree views, range selection typically includes all visible items
        # between start and end in the current display order
        # This is a simplified implementation
        if self.start_index.isValid():
            indices.append(self.start_index)
        if self.end_index.isValid() and self.end_index != self.start_index:
            indices.append(self.end_index)
        return indices


class SelectionTracker:
    """Tracks selection state and history."""
    
    def __init__(self):
        self.selected_elements: Set[str] = set()
        self.selection_order: List[str] = []
        self.last_selected: Optional[str] = None
        self.anchor_element: Optional[str] = None
    
    def add_element(self, element_id: str) -> None:
        """Add element to selection."""
        if element_id not in self.selected_elements:
            self.selected_elements.add(element_id)
            self.selection_order.append(element_id)
        self.last_selected = element_id
    
    def remove_element(self, element_id: str) -> None:
        """Remove element from selection."""
        if element_id in self.selected_elements:
            self.selected_elements.remove(element_id)
            if element_id in self.selection_order:
                self.selection_order.remove(element_id)
        
        if self.last_selected == element_id:
            self.last_selected = self.selection_order[-1] if self.selection_order else None
    
    def toggle_element(self, element_id: str) -> bool:
        """Toggle element selection state."""
        if element_id in self.selected_elements:
            self.remove_element(element_id)
            return False
        else:
            self.add_element(element_id)
            return True
    
    def clear(self) -> None:
        """Clear all selection."""
        self.selected_elements.clear()
        self.selection_order.clear()
        self.last_selected = None
        self.anchor_element = None
    
    def set_anchor(self, element_id: str) -> None:
        """Set anchor for range selection."""
        self.anchor_element = element_id
    
    def get_selection_list(self) -> List[str]:
        """Get selection as ordered list."""
        return self.selection_order.copy()
    
    def is_selected(self, element_id: str) -> bool:
        """Check if element is selected."""
        return element_id in self.selected_elements
    
    def count(self) -> int:
        """Get selection count."""
        return len(self.selected_elements)


class MultiSelectionHandler(QObject):
    """Handles multi-selection operations for the tree view."""
    
    # Signals
    selectionChanged = pyqtSignal(list)  # List of selected element IDs
    elementSelected = pyqtSignal(str, bool)  # element_id, is_multi_select
    elementDeselected = pyqtSignal(str)
    selectionCleared = pyqtSignal()
    rangeSelected = pyqtSignal(list)  # List of element IDs in range
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.tracker = SelectionTracker()
        
        # Selection state
        self.multi_select_mode = False
        self.range_select_mode = False
        self.selection_locked = False
        
        # Connect to tree view selection model
        self._connect_selection_model()
    
    def _connect_selection_model(self) -> None:
        """Connect to tree view's selection model."""
        selection_model = self.tree_view.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_qt_selection_changed)
    
    def _on_qt_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        """Handle Qt selection model changes."""
        if self.selection_locked:
            return
        
        # Update tracker based on Qt selection changes
        model = self.tree_view.model()
        if not model:
            return
        
        # Process deselected items
        for index in deselected.indexes():
            if index.column() == 0:  # Only process first column
                element_id = model.data(index, Qt.ItemDataRole.UserRole)
                if element_id:
                    self.tracker.remove_element(element_id)
                    self.elementDeselected.emit(element_id)
        
        # Process selected items
        for index in selected.indexes():
            if index.column() == 0:  # Only process first column
                element_id = model.data(index, Qt.ItemDataRole.UserRole)
                if element_id:
                    self.tracker.add_element(element_id)
                    self.elementSelected.emit(element_id, self.multi_select_mode)
        
        # Emit selection changed
        self.selectionChanged.emit(self.tracker.get_selection_list())
    
    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """
        Handle mouse press for selection.
        
        Returns:
            True if event was handled, False to pass to default handler
        """
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        index = self.tree_view.indexAt(event.pos())
        if not index.isValid():
            # Click on empty area - clear selection unless Ctrl is held
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.clear_selection()
            return True
        
        # Check modifiers
        ctrl_held = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        
        model = self.tree_view.model()
        element_id = model.data(index, Qt.ItemDataRole.UserRole) if model else None
        
        if not element_id:
            return False
        
        if shift_held and self.tracker.last_selected:
            # Range selection
            self._handle_range_selection(element_id, index)
        elif ctrl_held:
            # Toggle selection
            self._handle_toggle_selection(element_id, index)
        else:
            # Single selection
            self._handle_single_selection(element_id, index)
        
        return True
    
    def _handle_single_selection(self, element_id: str, index: QModelIndex) -> None:
        """Handle single selection (clear others and select this one)."""
        self.multi_select_mode = False
        
        if not self.tracker.is_selected(element_id) or self.tracker.count() > 1:
            self.clear_selection()
            self.select_element(element_id)
            self.tracker.set_anchor(element_id)
    
    def _handle_toggle_selection(self, element_id: str, index: QModelIndex) -> None:
        """Handle toggle selection (Ctrl+click)."""
        self.multi_select_mode = True
        
        if self.tracker.is_selected(element_id):
            self.deselect_element(element_id)
        else:
            self.select_element(element_id)
            self.tracker.set_anchor(element_id)
    
    def _handle_range_selection(self, element_id: str, index: QModelIndex) -> None:
        """Handle range selection (Shift+click)."""
        if not self.tracker.anchor_element:
            self.tracker.set_anchor(element_id)
            self.select_element(element_id)
            return
        
        self.range_select_mode = True
        self.multi_select_mode = True
        
        # Get range of elements to select
        range_elements = self._get_range_elements(self.tracker.anchor_element, element_id)
        
        # Clear current selection and select range
        self.clear_selection()
        for elem_id in range_elements:
            self.select_element(elem_id, emit_signal=False)
        
        # Emit range selection signal
        self.rangeSelected.emit(range_elements)
        self.selectionChanged.emit(self.tracker.get_selection_list())
    
    def _get_range_elements(self, start_element_id: str, end_element_id: str) -> List[str]:
        """Get all elements between start and end in display order."""
        model = self.tree_view.model()
        if not model:
            return [start_element_id, end_element_id]
        
        # Get indices
        start_index = model.get_index_by_element_id(start_element_id)
        end_index = model.get_index_by_element_id(end_element_id)
        
        if not start_index.isValid() or not end_index.isValid():
            return [start_element_id, end_element_id]
        
        # For simplicity, we'll return just the start and end elements
        # A full implementation would traverse the visible tree structure
        # between these two points
        elements = [start_element_id]
        if end_element_id != start_element_id:
            elements.append(end_element_id)
        
        return elements
    
    def select_element(self, element_id: str, emit_signal: bool = True) -> bool:
        """
        Select a single element.
        
        Args:
            element_id: Element ID to select
            emit_signal: Whether to emit selection signal
            
        Returns:
            True if selection was successful
        """
        model = self.tree_view.model()
        if not model:
            return False
        
        # Get index
        index = model.get_index_by_element_id(element_id)
        if not index.isValid():
            return False
        
        # Update Qt selection
        self.selection_locked = True
        selection_model = self.tree_view.selectionModel()
        if selection_model:
            selection_model.select(index, selection_model.SelectionFlag.Select)
        self.selection_locked = False
        
        # Update tracker
        self.tracker.add_element(element_id)
        
        if emit_signal:
            self.elementSelected.emit(element_id, self.multi_select_mode)
            self.selectionChanged.emit(self.tracker.get_selection_list())
        
        return True
    
    def deselect_element(self, element_id: str) -> bool:
        """
        Deselect a single element.
        
        Args:
            element_id: Element ID to deselect
            
        Returns:
            True if deselection was successful
        """
        model = self.tree_view.model()
        if not model:
            return False
        
        # Get index
        index = model.get_index_by_element_id(element_id)
        if not index.isValid():
            return False
        
        # Update Qt selection
        self.selection_locked = True
        selection_model = self.tree_view.selectionModel()
        if selection_model:
            selection_model.select(index, selection_model.SelectionFlag.Deselect)
        self.selection_locked = False
        
        # Update tracker
        self.tracker.remove_element(element_id)
        
        self.elementDeselected.emit(element_id)
        self.selectionChanged.emit(self.tracker.get_selection_list())
        
        return True
    
    def select_elements(self, element_ids: List[str]) -> int:
        """
        Select multiple elements.
        
        Args:
            element_ids: List of element IDs to select
            
        Returns:
            Number of elements successfully selected
        """
        self.multi_select_mode = True
        selected_count = 0
        
        for element_id in element_ids:
            if self.select_element(element_id, emit_signal=False):
                selected_count += 1
        
        if selected_count > 0:
            self.selectionChanged.emit(self.tracker.get_selection_list())
        
        return selected_count
    
    def clear_selection(self) -> None:
        """Clear all selection."""
        if self.tracker.count() == 0:
            return
        
        # Clear Qt selection
        self.selection_locked = True
        selection_model = self.tree_view.selectionModel()
        if selection_model:
            selection_model.clear()
        self.selection_locked = False
        
        # Clear tracker
        self.tracker.clear()
        
        # Reset modes
        self.multi_select_mode = False
        self.range_select_mode = False
        
        self.selectionCleared.emit()
        self.selectionChanged.emit([])
    
    def select_all(self) -> None:
        """Select all visible elements."""
        model = self.tree_view.model()
        if not model:
            return
        
        # Get all element IDs from the model
        all_elements = []
        for element_id in model._element_map.keys():
            all_elements.append(element_id)
        
        if all_elements:
            self.clear_selection()
            self.select_elements(all_elements)
    
    def invert_selection(self) -> None:
        """Invert current selection."""
        model = self.tree_view.model()
        if not model:
            return
        
        # Get currently selected and all elements
        currently_selected = set(self.tracker.get_selection_list())
        all_elements = set(model._element_map.keys())
        
        # Calculate inverted selection
        to_select = all_elements - currently_selected
        
        if to_select:
            self.clear_selection()
            self.select_elements(list(to_select))
    
    def get_selected_elements(self) -> List[str]:
        """Get list of selected element IDs."""
        return self.tracker.get_selection_list()
    
    def get_selected_count(self) -> int:
        """Get number of selected elements."""
        return self.tracker.count()
    
    def is_element_selected(self, element_id: str) -> bool:
        """Check if element is selected."""
        return self.tracker.is_selected(element_id)
    
    def get_last_selected(self) -> Optional[str]:
        """Get the last selected element ID."""
        return self.tracker.last_selected
    
    def handle_key_event(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard events for selection.
        
        Returns:
            True if event was handled, False to pass to default handler
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Ctrl+A - Select all
        if (key == Qt.Key.Key_A and 
            modifiers & Qt.KeyboardModifier.ControlModifier):
            self.select_all()
            return True
        
        # Escape - Clear selection
        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            return True
        
        # Space - Toggle selection of current item
        if key == Qt.Key.Key_Space:
            current_index = self.tree_view.currentIndex()
            if current_index.isValid():
                model = self.tree_view.model()
                element_id = model.data(current_index, Qt.ItemDataRole.UserRole) if model else None
                if element_id:
                    if modifiers & Qt.KeyboardModifier.ControlModifier:
                        # Ctrl+Space - Toggle without affecting others
                        self.multi_select_mode = True
                        if self.tracker.is_selected(element_id):
                            self.deselect_element(element_id)
                        else:
                            self.select_element(element_id)
                    else:
                        # Space - Single select
                        self.clear_selection()
                        self.select_element(element_id)
                    return True
        
        return False
    
    def save_selection_state(self) -> Dict[str, Any]:
        """Save current selection state."""
        return {
            'selected_elements': list(self.tracker.selected_elements),
            'selection_order': self.tracker.selection_order.copy(),
            'last_selected': self.tracker.last_selected,
            'anchor_element': self.tracker.anchor_element,
            'multi_select_mode': self.multi_select_mode
        }
    
    def restore_selection_state(self, state: Dict[str, Any]) -> None:
        """Restore selection state."""
        self.clear_selection()
        
        # Restore tracker state
        self.tracker.selected_elements = set(state.get('selected_elements', []))
        self.tracker.selection_order = state.get('selection_order', [])
        self.tracker.last_selected = state.get('last_selected')
        self.tracker.anchor_element = state.get('anchor_element')
        self.multi_select_mode = state.get('multi_select_mode', False)
        
        # Update Qt selection model
        if self.tracker.selected_elements:
            self.select_elements(list(self.tracker.selected_elements))