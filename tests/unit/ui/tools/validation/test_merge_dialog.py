"""
Tests for MergeDialog component.

This module provides comprehensive tests for the merge dialog functionality
including element selection, preview, and merge operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QDropEvent, QDragEnterEvent

from src.torematrix.core.models import Element, ElementType
from src.torematrix.ui.tools.validation.merge_dialog import (
    MergeDialog, MergeElementListWidget, MergePreviewWidget
)


class TestMergeElementListWidget:
    """Tests for the merge element list widget with drag-and-drop."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def list_widget(self, app):
        """Create merge element list widget."""
        return MergeElementListWidget()
    
    def test_initialization(self, list_widget):
        """Test widget initialization."""
        assert list_widget.acceptDrops()
        assert list_widget.dragEnabled()
        assert list_widget.selectionMode() == list_widget.SelectionMode.ExtendedSelection
    
    def test_drag_enter_event_valid(self, list_widget):
        """Test drag enter with valid mime data."""
        # Mock drag enter event
        mime_data = Mock()
        mime_data.hasFormat.return_value = True
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        # Should accept valid mime data
        list_widget.dragEnterEvent(event)
        mime_data.hasFormat.assert_called_with("application/x-element-list")
        event.acceptProposedAction.assert_called_once()
    
    def test_drag_enter_event_invalid(self, list_widget):
        """Test drag enter with invalid mime data."""
        mime_data = Mock()
        mime_data.hasFormat.return_value = False
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        # Should ignore invalid mime data
        list_widget.dragEnterEvent(event)
        event.ignore.assert_called_once()
    
    def test_drop_event_valid(self, list_widget):
        """Test drop event with valid data."""
        # Connect signal to mock
        signal_mock = Mock()
        list_widget.elements_dropped.connect(signal_mock)
        
        # Mock drop event
        mime_data = Mock()
        mime_data.hasFormat.return_value = True
        mime_data.data.return_value = b"mock_data"
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        list_widget.dropEvent(event)
        
        # Should emit signal and accept event
        signal_mock.assert_called_once()
        event.acceptProposedAction.assert_called_once()


class TestMergePreviewWidget:
    """Tests for the merge preview widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create merge preview widget."""
        return MergePreviewWidget()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        return [
            Element(element_type=ElementType.TITLE, text="Title 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text content 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text content 2")
        ]
    
    def test_initialization(self, preview_widget):
        """Test widget initialization."""
        assert preview_widget.separator_combo.count() > 0
        assert preview_widget.preserve_formatting.isChecked()
    
    def test_set_elements(self, preview_widget, sample_elements):
        """Test setting elements for preview."""
        preview_widget.set_elements(sample_elements)
        
        # Should update before list
        assert preview_widget.before_list.count() == len(sample_elements)
        
        # Should generate merged result
        result = preview_widget.get_merged_result()
        assert result is not None
        assert result.element_type == sample_elements[0].element_type
    
    def test_update_preview_different_separators(self, preview_widget, sample_elements):
        """Test preview update with different separators."""
        preview_widget.set_elements(sample_elements)
        
        # Test single space separator
        preview_widget.separator_combo.setCurrentText("Single Space")
        preview_widget.update_preview()
        result = preview_widget.get_merged_result()
        expected_text = " ".join(e.text for e in sample_elements)
        assert result.text == expected_text
        
        # Test newline separator
        preview_widget.separator_combo.setCurrentText("Newline")
        preview_widget.update_preview()
        result = preview_widget.get_merged_result()
        expected_text = "\n".join(e.text for e in sample_elements)
        assert result.text == expected_text
    
    def test_get_merge_options(self, preview_widget):
        """Test getting merge options."""
        options = preview_widget.get_merge_options()
        
        assert "separator" in options
        assert "preserve_formatting" in options
        assert isinstance(options["preserve_formatting"], bool)


class TestMergeDialog:
    """Tests for the main merge dialog."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        return [
            Element(element_type=ElementType.TITLE, text="Title 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text content 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text content 2"),
            Element(element_type=ElementType.LIST_ITEM, text="List item 1"),
            Element(element_type=ElementType.LIST_ITEM, text="List item 2")
        ]
    
    @pytest.fixture
    def dialog(self, app, sample_elements):
        """Create merge dialog."""
        return MergeDialog(sample_elements)
    
    def test_initialization(self, dialog, sample_elements):
        """Test dialog initialization."""
        assert dialog.windowTitle() == "Merge Document Elements"
        assert dialog.isModal()
        assert len(dialog.available_elements) == len(sample_elements)
        assert dialog.available_list.count() == len(sample_elements)
    
    def test_populate_available_elements(self, dialog, sample_elements):
        """Test populating available elements list."""
        # Should populate all elements
        assert dialog.available_list.count() == len(sample_elements)
        
        # Each item should have element data
        for i in range(dialog.available_list.count()):
            item = dialog.available_list.item(i)
            element = item.data(Qt.ItemDataRole.UserRole)
            assert element in sample_elements
    
    def test_filter_available_elements(self, dialog):
        """Test filtering elements by type."""
        # Filter by TITLE type
        dialog.element_type_filter.setCurrentText("Title")
        dialog.filter_available_elements()
        
        # Should show only title elements
        visible_count = 0
        for i in range(dialog.available_list.count()):
            item = dialog.available_list.item(i)
            if not item.isHidden():
                visible_count += 1
                element = item.data(Qt.ItemDataRole.UserRole)
                assert element.element_type == ElementType.TITLE
        
        assert visible_count == 1  # Only one title element
    
    def test_add_selected_elements(self, dialog):
        """Test adding selected elements to merge list."""
        # Select first element
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        
        # Add to merge list
        dialog.add_selected_elements()
        
        # Should add element to selected list
        assert dialog.selected_list.count() == 1
        assert len(dialog.selected_elements) == 1
        
        # Element should be in both lists
        selected_element = dialog.selected_elements[0]
        available_element = dialog.available_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert selected_element == available_element
    
    def test_remove_selected_elements(self, dialog):
        """Test removing elements from merge list."""
        # First add an element
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        dialog.add_selected_elements()
        
        assert dialog.selected_list.count() == 1
        
        # Now remove it
        dialog.selected_list.setCurrentRow(0)
        dialog.selected_list.item(0).setSelected(True)
        dialog.remove_selected_elements()
        
        # Should be removed
        assert dialog.selected_list.count() == 0
        assert len(dialog.selected_elements) == 0
    
    def test_clear_selected_elements(self, dialog):
        """Test clearing all selected elements."""
        # Add multiple elements
        for i in range(3):
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        assert dialog.selected_list.count() == 3
        
        # Clear all
        dialog.clear_selected_elements()
        
        assert dialog.selected_list.count() == 0
        assert len(dialog.selected_elements) == 0
    
    def test_move_element_up(self, dialog):
        """Test moving element up in merge order."""
        # Add two elements
        for i in range(2):
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        # Select second element and move up
        dialog.selected_list.setCurrentRow(1)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_up()
        
        # Order should be reversed
        assert dialog.selected_elements[0] == original_order[1]
        assert dialog.selected_elements[1] == original_order[0]
        assert dialog.selected_list.currentRow() == 0
    
    def test_move_element_down(self, dialog):
        """Test moving element down in merge order."""
        # Add two elements
        for i in range(2):
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        # Select first element and move down
        dialog.selected_list.setCurrentRow(0)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_down()
        
        # Order should be reversed
        assert dialog.selected_elements[0] == original_order[1]
        assert dialog.selected_elements[1] == original_order[0]
        assert dialog.selected_list.currentRow() == 1
    
    def test_update_button_states(self, dialog):
        """Test button state updates based on selections."""
        # Initially no selections
        dialog.update_button_states()
        assert not dialog.add_button.isEnabled()
        assert not dialog.remove_button.isEnabled()
        assert not dialog.preview_button.isEnabled()
        assert not dialog.merge_button.isEnabled()
        
        # Select available element
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        dialog.update_button_states()
        assert dialog.add_button.isEnabled()
        
        # Add elements for merge
        dialog.add_selected_elements()
        dialog.available_list.clearSelection()
        dialog.available_list.setCurrentRow(1)
        dialog.available_list.item(1).setSelected(True)
        dialog.add_selected_elements()
        
        dialog.update_button_states()
        # Should enable merge buttons with 2+ elements
        assert dialog.preview_button.isEnabled()
        assert dialog.merge_button.isEnabled()
    
    def test_validate_merge_operation(self, dialog):
        """Test merge operation validation."""
        # No elements - should have warnings
        warnings = dialog.validate_merge_operation()
        assert len(warnings) > 0
        assert any("at least 2 elements" in w.lower() for w in warnings)
        
        # Add elements of different types
        elements_to_add = [0, 3]  # Title and List Item (different types)
        for i in elements_to_add:
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        warnings = dialog.validate_merge_operation()
        assert any("different element types" in w.lower() for w in warnings)
    
    def test_get_selected_elements(self, dialog):
        """Test getting selected elements."""
        # Add some elements
        for i in range(2):
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        selected = dialog.get_selected_elements()
        assert len(selected) == 2
        assert selected == dialog.selected_elements
        # Should be a copy, not the same object
        assert selected is not dialog.selected_elements
    
    def test_get_merge_options(self, dialog):
        """Test getting merge options."""
        options = dialog.get_merge_options()
        
        # Should include base options and conflict resolutions
        assert "separator" in options
        assert "preserve_formatting" in options
    
    @patch('src.torematrix.ui.tools.validation.merge_dialog.QMessageBox')
    def test_perform_merge_no_elements(self, mock_msgbox, dialog):
        """Test performing merge with no elements."""
        dialog.perform_merge()
        
        # Should show warning
        mock_msgbox.warning.assert_called_once()
    
    def test_perform_merge_signal_emission(self, dialog):
        """Test merge request signal emission."""
        # Add elements
        for i in range(2):
            dialog.available_list.setCurrentRow(i)
            dialog.available_list.item(i).setSelected(True)
            dialog.add_selected_elements()
            dialog.available_list.clearSelection()
        
        # Connect signal
        signal_mock = Mock()
        dialog.merge_requested.connect(signal_mock)
        
        # Perform merge
        dialog.perform_merge()
        
        # Should emit signal with elements and options
        signal_mock.assert_called_once()
        args = signal_mock.call_args[0]
        assert len(args) == 2  # elements, options
        assert len(args[0]) == 2  # Two elements
        assert isinstance(args[1], dict)  # Options dict