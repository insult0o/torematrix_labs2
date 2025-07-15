"""
Tests for Multi-Selection System

Comprehensive test suite for multi-selection functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import Qt, QModelIndex, QItemSelection
from PyQt6.QtWidgets import QTreeView, QApplication
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from src.torematrix.ui.components.element_list.interactions.selection import (
    MultiSelectionHandler, SelectionTracker, SelectionRange
)


@pytest.fixture
def mock_tree_view():
    """Create mock tree view."""
    tree_view = Mock(spec=QTreeView)
    mock_selection_model = Mock()
    tree_view.selectionModel.return_value = mock_selection_model
    tree_view.currentIndex.return_value = QModelIndex()
    tree_view.setCurrentIndex = Mock()
    tree_view.model.return_value = Mock()
    return tree_view


@pytest.fixture
def selection_tracker():
    """Create selection tracker."""
    return SelectionTracker()


class TestSelectionTracker:
    """Test selection tracking functionality."""
    
    def test_add_element(self, selection_tracker):
        """Test adding element to selection."""
        selection_tracker.add_element("element_1")
        
        assert "element_1" in selection_tracker.selected_elements
        assert selection_tracker.selection_order == ["element_1"]
        assert selection_tracker.last_selected == "element_1"
    
    def test_add_duplicate_element(self, selection_tracker):
        """Test adding duplicate element."""
        selection_tracker.add_element("element_1")
        selection_tracker.add_element("element_1")
        
        assert selection_tracker.count() == 1
        assert selection_tracker.selection_order == ["element_1"]
        assert selection_tracker.last_selected == "element_1"
    
    def test_remove_element(self, selection_tracker):
        """Test removing element from selection."""
        selection_tracker.add_element("element_1")
        selection_tracker.add_element("element_2")
        
        selection_tracker.remove_element("element_1")
        
        assert "element_1" not in selection_tracker.selected_elements
        assert selection_tracker.selection_order == ["element_2"]
        assert selection_tracker.last_selected == "element_2"
    
    def test_remove_nonexistent_element(self, selection_tracker):
        """Test removing element that doesn't exist."""
        selection_tracker.add_element("element_1")
        
        selection_tracker.remove_element("element_2")
        
        assert selection_tracker.count() == 1
        assert "element_1" in selection_tracker.selected_elements
    
    def test_toggle_element_add(self, selection_tracker):
        """Test toggling element (adding)."""
        result = selection_tracker.toggle_element("element_1")
        
        assert result is True
        assert "element_1" in selection_tracker.selected_elements
    
    def test_toggle_element_remove(self, selection_tracker):
        """Test toggling element (removing)."""
        selection_tracker.add_element("element_1")
        
        result = selection_tracker.toggle_element("element_1")
        
        assert result is False
        assert "element_1" not in selection_tracker.selected_elements
    
    def test_clear_selection(self, selection_tracker):
        """Test clearing all selection."""
        selection_tracker.add_element("element_1")
        selection_tracker.add_element("element_2")
        selection_tracker.set_anchor("element_1")
        
        selection_tracker.clear()
        
        assert selection_tracker.count() == 0
        assert len(selection_tracker.selection_order) == 0
        assert selection_tracker.last_selected is None
        assert selection_tracker.anchor_element is None
    
    def test_set_anchor(self, selection_tracker):
        """Test setting anchor element."""
        selection_tracker.set_anchor("element_1")
        
        assert selection_tracker.anchor_element == "element_1"
    
    def test_is_selected(self, selection_tracker):
        """Test checking if element is selected."""
        selection_tracker.add_element("element_1")
        
        assert selection_tracker.is_selected("element_1")
        assert not selection_tracker.is_selected("element_2")
    
    def test_get_selection_list(self, selection_tracker):
        """Test getting selection as ordered list."""
        selection_tracker.add_element("element_1")
        selection_tracker.add_element("element_2")
        selection_tracker.add_element("element_3")
        
        selection_list = selection_tracker.get_selection_list()
        
        assert selection_list == ["element_1", "element_2", "element_3"]
        # Ensure it's a copy
        selection_list.append("element_4")
        assert selection_tracker.count() == 3


class TestSelectionRange:
    """Test selection range functionality."""
    
    def test_range_creation(self):
        """Test creating selection range."""
        start_index = QModelIndex()
        end_index = QModelIndex()
        
        range_obj = SelectionRange(start_index, end_index)
        
        assert range_obj.start_index == start_index
        assert range_obj.end_index == end_index
    
    def test_range_contains(self):
        """Test range contains check."""
        start_index = Mock()
        end_index = Mock()
        test_index = Mock()
        
        range_obj = SelectionRange(start_index, end_index)
        
        # Test contains start
        assert range_obj.contains(start_index)
        # Test contains end
        assert range_obj.contains(end_index)
        # Test doesn't contain other
        assert not range_obj.contains(test_index)
    
    def test_range_to_index_list(self):
        """Test converting range to index list."""
        start_index = Mock()
        start_index.isValid.return_value = True
        end_index = Mock()
        end_index.isValid.return_value = True
        
        range_obj = SelectionRange(start_index, end_index)
        mock_model = Mock()
        
        index_list = range_obj.to_index_list(mock_model)
        
        assert len(index_list) >= 1  # At least start index
        assert start_index in index_list


class TestMultiSelectionHandler:
    """Test multi-selection handler functionality."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_handler_initialization(self, mock_tree_view):
        """Test handler initialization."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        assert handler.tree_view == mock_tree_view
        assert isinstance(handler.tracker, SelectionTracker)
        assert not handler.multi_select_mode
        assert not handler.range_select_mode
        assert not handler.selection_locked
    
    def test_select_element_success(self, mock_tree_view):
        """Test successful element selection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model
        mock_model = Mock()
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_model.get_index_by_element_id.return_value = mock_index
        mock_tree_view.model.return_value = mock_model
        
        # Setup mock selection model
        mock_selection_model = Mock()
        mock_tree_view.selectionModel.return_value = mock_selection_model
        
        result = handler.select_element("element_1")
        
        assert result is True
        assert handler.tracker.is_selected("element_1")
    
    def test_select_element_invalid_model(self, mock_tree_view):
        """Test element selection with invalid model."""
        handler = MultiSelectionHandler(mock_tree_view)
        mock_tree_view.model.return_value = None
        
        result = handler.select_element("element_1")
        
        assert result is False
        assert not handler.tracker.is_selected("element_1")
    
    def test_select_element_invalid_index(self, mock_tree_view):
        """Test element selection with invalid index."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model with invalid index
        mock_model = Mock()
        mock_index = Mock()
        mock_index.isValid.return_value = False
        mock_model.get_index_by_element_id.return_value = mock_index
        mock_tree_view.model.return_value = mock_model
        
        result = handler.select_element("element_1")
        
        assert result is False
        assert not handler.tracker.is_selected("element_1")
    
    def test_deselect_element(self, mock_tree_view):
        """Test element deselection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model
        mock_model = Mock()
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_model.get_index_by_element_id.return_value = mock_index
        mock_tree_view.model.return_value = mock_model
        
        # Setup mock selection model
        mock_selection_model = Mock()
        mock_tree_view.selectionModel.return_value = mock_selection_model
        
        # First select, then deselect
        handler.select_element("element_1", emit_signal=False)
        result = handler.deselect_element("element_1")
        
        assert result is True
        assert not handler.tracker.is_selected("element_1")
    
    def test_select_multiple_elements(self, mock_tree_view):
        """Test selecting multiple elements."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model
        mock_model = Mock()
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_model.get_index_by_element_id.return_value = mock_index
        mock_tree_view.model.return_value = mock_model
        
        # Setup mock selection model
        mock_selection_model = Mock()
        mock_tree_view.selectionModel.return_value = mock_selection_model
        
        element_ids = ["element_1", "element_2", "element_3"]
        result = handler.select_elements(element_ids)
        
        assert result == 3
        assert handler.multi_select_mode
        for element_id in element_ids:
            assert handler.tracker.is_selected(element_id)
    
    def test_clear_selection(self, mock_tree_view):
        """Test clearing selection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock selection model
        mock_selection_model = Mock()
        mock_tree_view.selectionModel.return_value = mock_selection_model
        
        # Add some selections
        handler.tracker.add_element("element_1")
        handler.tracker.add_element("element_2")
        handler.multi_select_mode = True
        
        handler.clear_selection()
        
        assert handler.tracker.count() == 0
        assert not handler.multi_select_mode
        assert not handler.range_select_mode
    
    def test_select_all(self, mock_tree_view):
        """Test select all functionality."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model with element map
        mock_model = Mock()
        mock_model._element_map = {
            "element_1": Mock(),
            "element_2": Mock(),
            "element_3": Mock()
        }
        mock_tree_view.model.return_value = mock_model
        
        # Mock the select_elements method
        handler.select_elements = Mock(return_value=3)
        
        handler.select_all()
        
        handler.select_elements.assert_called_once()
        call_args = handler.select_elements.call_args[0][0]
        assert set(call_args) == {"element_1", "element_2", "element_3"}
    
    def test_invert_selection(self, mock_tree_view):
        """Test invert selection functionality."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model
        mock_model = Mock()
        mock_model._element_map = {
            "element_1": Mock(),
            "element_2": Mock(),
            "element_3": Mock()
        }
        mock_tree_view.model.return_value = mock_model
        
        # Select some elements
        handler.tracker.add_element("element_1")
        
        # Mock methods
        handler.clear_selection = Mock()
        handler.select_elements = Mock()
        
        handler.invert_selection()
        
        handler.clear_selection.assert_called_once()
        handler.select_elements.assert_called_once()
        # Should select elements 2 and 3 (not 1)
        call_args = handler.select_elements.call_args[0][0]
        assert set(call_args) == {"element_2", "element_3"}
    
    def test_handle_mouse_press_single_selection(self, mock_tree_view):
        """Test mouse press for single selection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock mouse event
        mock_event = Mock()
        mock_event.button.return_value = Qt.MouseButton.LeftButton
        mock_event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        mock_event.pos.return_value = Mock()
        
        # Setup mock index and model
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_tree_view.indexAt.return_value = mock_index
        
        mock_model = Mock()
        mock_model.data.return_value = "element_1"
        mock_tree_view.model.return_value = mock_model
        
        # Mock handler methods
        handler._handle_single_selection = Mock()
        
        result = handler.handle_mouse_press(mock_event)
        
        assert result is True
        handler._handle_single_selection.assert_called_once_with("element_1", mock_index)
    
    def test_handle_mouse_press_toggle_selection(self, mock_tree_view):
        """Test mouse press for toggle selection (Ctrl+click)."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock mouse event with Ctrl
        mock_event = Mock()
        mock_event.button.return_value = Qt.MouseButton.LeftButton
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        mock_event.pos.return_value = Mock()
        
        # Setup mock index and model
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_tree_view.indexAt.return_value = mock_index
        
        mock_model = Mock()
        mock_model.data.return_value = "element_1"
        mock_tree_view.model.return_value = mock_model
        
        # Mock handler methods
        handler._handle_toggle_selection = Mock()
        
        result = handler.handle_mouse_press(mock_event)
        
        assert result is True
        handler._handle_toggle_selection.assert_called_once_with("element_1", mock_index)
    
    def test_handle_mouse_press_range_selection(self, mock_tree_view):
        """Test mouse press for range selection (Shift+click)."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock mouse event with Shift
        mock_event = Mock()
        mock_event.button.return_value = Qt.MouseButton.LeftButton
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ShiftModifier
        mock_event.pos.return_value = Mock()
        
        # Setup mock index and model
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_tree_view.indexAt.return_value = mock_index
        
        mock_model = Mock()
        mock_model.data.return_value = "element_1"
        mock_tree_view.model.return_value = mock_model
        
        # Set last selected
        handler.tracker.last_selected = "element_0"
        
        # Mock handler methods
        handler._handle_range_selection = Mock()
        
        result = handler.handle_mouse_press(mock_event)
        
        assert result is True
        handler._handle_range_selection.assert_called_once_with("element_1", mock_index)
    
    def test_handle_mouse_press_empty_area(self, mock_tree_view):
        """Test mouse press on empty area."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock mouse event
        mock_event = Mock()
        mock_event.button.return_value = Qt.MouseButton.LeftButton
        mock_event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        mock_event.pos.return_value = Mock()
        
        # Setup invalid index (empty area)
        mock_index = Mock()
        mock_index.isValid.return_value = False
        mock_tree_view.indexAt.return_value = mock_index
        
        # Mock clear_selection
        handler.clear_selection = Mock()
        
        result = handler.handle_mouse_press(mock_event)
        
        assert result is True
        handler.clear_selection.assert_called_once()
    
    def test_handle_key_event_select_all(self, mock_tree_view):
        """Test Ctrl+A key event for select all."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock key event for Ctrl+A
        mock_event = Mock()
        mock_event.key.return_value = Qt.Key.Key_A
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        
        # Mock select_all
        handler.select_all = Mock()
        
        result = handler.handle_key_event(mock_event)
        
        assert result is True
        handler.select_all.assert_called_once()
    
    def test_handle_key_event_escape(self, mock_tree_view):
        """Test Escape key event for clear selection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock key event for Escape
        mock_event = Mock()
        mock_event.key.return_value = Qt.Key.Key_Escape
        mock_event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        
        # Mock clear_selection
        handler.clear_selection = Mock()
        
        result = handler.handle_key_event(mock_event)
        
        assert result is True
        handler.clear_selection.assert_called_once()
    
    def test_handle_key_event_space_toggle(self, mock_tree_view):
        """Test Space key event for toggle selection."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock key event for Ctrl+Space
        mock_event = Mock()
        mock_event.key.return_value = Qt.Key.Key_Space
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        
        # Setup current index
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_tree_view.currentIndex.return_value = mock_index
        
        # Setup mock model
        mock_model = Mock()
        mock_model.data.return_value = "element_1"
        mock_tree_view.model.return_value = mock_model
        
        # Mock methods
        handler.deselect_element = Mock()
        handler.select_element = Mock()
        handler.tracker.is_selected = Mock(return_value=True)
        
        result = handler.handle_key_event(mock_event)
        
        assert result is True
        handler.deselect_element.assert_called_once_with("element_1")
    
    def test_save_and_restore_selection_state(self, mock_tree_view):
        """Test saving and restoring selection state."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup some selection state
        handler.tracker.add_element("element_1")
        handler.tracker.add_element("element_2")
        handler.tracker.set_anchor("element_1")
        handler.multi_select_mode = True
        
        # Save state
        state = handler.save_selection_state()
        
        # Verify saved state
        assert "element_1" in state['selected_elements']
        assert "element_2" in state['selected_elements']
        assert state['anchor_element'] == "element_1"
        assert state['multi_select_mode'] is True
        
        # Clear and restore
        handler.clear_selection()
        handler.multi_select_mode = False
        
        # Mock select_elements for restore
        handler.select_elements = Mock()
        
        handler.restore_selection_state(state)
        
        # Verify restored state
        assert handler.tracker.anchor_element == "element_1"
        assert handler.multi_select_mode is True
        handler.select_elements.assert_called_once()


class TestSelectionSignals:
    """Test selection signal emission."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_signal_emission_on_selection_change(self, mock_tree_view):
        """Test signals are emitted on selection changes."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Mock signal connections
        selection_changed_spy = Mock()
        element_selected_spy = Mock()
        element_deselected_spy = Mock()
        
        handler.selectionChanged.connect(selection_changed_spy)
        handler.elementSelected.connect(element_selected_spy)
        handler.elementDeselected.connect(element_deselected_spy)
        
        # Verify signals exist and can be connected
        assert handler.selectionChanged is not None
        assert handler.elementSelected is not None
        assert handler.elementDeselected is not None


@pytest.mark.integration
class TestSelectionIntegration:
    """Integration tests for selection system."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_qt_selection_model_integration(self, mock_tree_view):
        """Test integration with Qt selection model."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Create mock Qt selection change
        mock_selected = Mock()
        mock_deselected = Mock()
        
        # Mock indexes
        mock_index1 = Mock()
        mock_index1.column.return_value = 0
        mock_selected.indexes.return_value = [mock_index1]
        
        mock_index2 = Mock()
        mock_index2.column.return_value = 0
        mock_deselected.indexes.return_value = [mock_index2]
        
        # Setup model
        mock_model = Mock()
        mock_model.data.side_effect = lambda idx, role: "element_1" if idx == mock_index1 else "element_2"
        mock_tree_view.model.return_value = mock_model
        
        # Test Qt selection change handling
        handler._on_qt_selection_changed(mock_selected, mock_deselected)
        
        # Verify tracker was updated
        assert handler.tracker.is_selected("element_1")
        assert not handler.tracker.is_selected("element_2")
    
    def test_selection_workflow_with_model(self, mock_tree_view):
        """Test complete selection workflow with model."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup mock model with multiple elements
        mock_model = Mock()
        mock_model._element_map = {
            "element_1": Mock(),
            "element_2": Mock(),
            "element_3": Mock()
        }
        
        # Setup index mapping
        def get_index_side_effect(element_id):
            mock_index = Mock()
            mock_index.isValid.return_value = True
            return mock_index
        
        mock_model.get_index_by_element_id.side_effect = get_index_side_effect
        mock_tree_view.model.return_value = mock_model
        
        # Setup mock selection model
        mock_selection_model = Mock()
        mock_tree_view.selectionModel.return_value = mock_selection_model
        
        # Test workflow: select -> add to multi-select -> clear
        assert handler.select_element("element_1")
        assert handler.select_element("element_2", emit_signal=False)
        assert handler.tracker.count() == 2
        
        handler.clear_selection()
        assert handler.tracker.count() == 0


class TestSelectionEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_selection_with_none_values(self, mock_tree_view):
        """Test selection handling with None values."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Test with None element ID
        result = handler.select_element(None)
        assert result is False
        
        # Test with empty string
        result = handler.select_element("")
        assert result is False
    
    def test_tracker_with_large_selection(self):
        """Test tracker performance with large selection."""
        tracker = SelectionTracker()
        
        # Add large number of elements
        large_selection = [f"element_{i}" for i in range(10000)]
        for element_id in large_selection:
            tracker.add_element(element_id)
        
        assert tracker.count() == 10000
        assert tracker.is_selected("element_5000")
        assert not tracker.is_selected("element_10000")
        
        # Test removal performance
        for i in range(0, 10000, 2):  # Remove every other element
            tracker.remove_element(f"element_{i}")
        
        assert tracker.count() == 5000
    
    def test_selection_state_serialization(self, mock_tree_view):
        """Test selection state can be serialized/deserialized."""
        handler = MultiSelectionHandler(mock_tree_view)
        
        # Setup complex selection state
        handler.tracker.add_element("element_1")
        handler.tracker.add_element("element_2")
        handler.tracker.set_anchor("element_1")
        handler.multi_select_mode = True
        
        # Save and verify state can be serialized
        state = handler.save_selection_state()
        
        # Basic check that state is serializable (contains basic types)
        assert isinstance(state['selected_elements'], list)
        assert isinstance(state['selection_order'], list)
        assert isinstance(state['multi_select_mode'], bool)
        
        # Test that all values are JSON-serializable
        import json
        json_str = json.dumps(state)
        restored_state = json.loads(json_str)
        
        assert restored_state['selected_elements'] == state['selected_elements']


if __name__ == "__main__":
    pytest.main([__file__])