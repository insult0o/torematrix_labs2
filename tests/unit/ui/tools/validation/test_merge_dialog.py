"""
Tests for MergeDialog component.

This module provides comprehensive tests for the merge dialog functionality
including element selection, merge operations, and metadata conflict resolution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.torematrix.core.models import Element, ElementType
from src.torematrix.ui.tools.validation.merge_dialog import MergeDialog


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
            Element(
                element_type=ElementType.TITLE,
                text="First Title Element"
            ),
            Element(
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is the first narrative text element with some content."
            ),
            Element(
                element_type=ElementType.TITLE,
                text="Second Title Element"
            ),
            Element(
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is the second narrative text element with different content."
            ),
            Element(
                element_type=ElementType.LIST_ITEM,
                text="A list item element"
            )
        ]
    
    @pytest.fixture
    def dialog(self, app, sample_elements):
        """Create merge dialog with sample elements."""
        return MergeDialog(sample_elements)
    
    def test_initialization(self, dialog, sample_elements):
        """Test dialog initialization."""
        assert dialog.windowTitle() == "Merge Document Elements"
        assert dialog.isModal()
        assert len(dialog.available_elements) == len(sample_elements)
        assert dialog.selected_elements == []
        
        # Check that available list is populated
        assert dialog.available_list.count() == len(sample_elements)
        
        # Check that selected list is empty
        assert dialog.selected_list.count() == 0
    
    def test_populate_available_elements(self, dialog, sample_elements):
        """Test populating the available elements list."""
        dialog.populate_available_elements()
        
        assert dialog.available_list.count() == len(sample_elements)
        
        # Check that each element is properly displayed
        for i in range(dialog.available_list.count()):
            item = dialog.available_list.item(i)
            element = item.data(Qt.ItemDataRole.UserRole)
            assert element in sample_elements
            assert element.element_type.value in item.text()
    
    def test_filter_available_elements(self, dialog):
        """Test filtering available elements by type."""
        # Test filtering by Title
        dialog.element_type_filter.setCurrentText("Title")
        dialog.filter_available_elements()
        
        visible_count = 0
        for i in range(dialog.available_list.count()):
            item = dialog.available_list.item(i)
            if not item.isHidden():
                visible_count += 1
                element = item.data(Qt.ItemDataRole.UserRole)
                assert element.element_type == ElementType.TITLE
        
        assert visible_count == 2  # Two title elements in sample data
        
        # Test showing all types
        dialog.element_type_filter.setCurrentText("All Types")
        dialog.filter_available_elements()
        
        visible_count = 0
        for i in range(dialog.available_list.count()):
            item = dialog.available_list.item(i)
            if not item.isHidden():
                visible_count += 1
        
        assert visible_count == dialog.available_list.count()
    
    def test_add_selected_elements(self, dialog, sample_elements):
        """Test adding elements to the merge selection."""
        # Select first element
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        
        initial_selected_count = len(dialog.selected_elements)
        dialog.add_selected_elements()
        
        assert len(dialog.selected_elements) == initial_selected_count + 1
        assert sample_elements[0] in dialog.selected_elements
        assert dialog.selected_list.count() == initial_selected_count + 1
    
    def test_add_selected_elements_no_duplicates(self, dialog, sample_elements):
        """Test that adding the same element twice doesn't create duplicates."""
        # Add first element
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        dialog.add_selected_elements()
        
        initial_count = len(dialog.selected_elements)
        
        # Try to add the same element again
        dialog.available_list.setCurrentRow(0)
        dialog.available_list.item(0).setSelected(True)
        dialog.add_selected_elements()
        
        # Count should not increase
        assert len(dialog.selected_elements) == initial_count
    
    def test_add_all_elements(self, dialog, sample_elements):
        """Test adding all visible elements to merge selection."""
        dialog.add_all_elements()
        
        assert len(dialog.selected_elements) == len(sample_elements)
        assert dialog.selected_list.count() == len(sample_elements)
        
        # Check that all elements were added
        for element in sample_elements:
            assert element in dialog.selected_elements
    
    def test_remove_selected_elements(self, dialog, sample_elements):
        """Test removing elements from merge selection."""
        # First add some elements
        dialog.add_all_elements()
        initial_count = len(dialog.selected_elements)
        
        # Select first item in selected list
        dialog.selected_list.setCurrentRow(0)
        dialog.selected_list.item(0).setSelected(True)
        
        dialog.remove_selected_elements()
        
        assert len(dialog.selected_elements) == initial_count - 1
        assert dialog.selected_list.count() == initial_count - 1
    
    def test_clear_selected_elements(self, dialog, sample_elements):
        """Test clearing all selected elements."""
        # First add all elements
        dialog.add_all_elements()
        assert len(dialog.selected_elements) > 0
        
        dialog.clear_selected_elements()
        
        assert len(dialog.selected_elements) == 0
        assert dialog.selected_list.count() == 0
    
    def test_move_element_up(self, dialog, sample_elements):
        """Test moving element up in merge order."""
        # Add multiple elements
        dialog.add_all_elements()
        
        # Select second element (index 1)
        dialog.selected_list.setCurrentRow(1)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_up()
        
        # Element should have moved up
        assert dialog.selected_elements[0] == original_order[1]
        assert dialog.selected_elements[1] == original_order[0]
        assert dialog.selected_list.currentRow() == 0
    
    def test_move_element_down(self, dialog, sample_elements):
        """Test moving element down in merge order."""
        # Add multiple elements
        dialog.add_all_elements()
        
        # Select first element (index 0)
        dialog.selected_list.setCurrentRow(0)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_down()
        
        # Element should have moved down
        assert dialog.selected_elements[0] == original_order[1]
        assert dialog.selected_elements[1] == original_order[0]
        assert dialog.selected_list.currentRow() == 1
    
    def test_move_element_up_boundary(self, dialog, sample_elements):
        """Test moving element up when already at top."""
        # Add multiple elements
        dialog.add_all_elements()
        
        # Select first element (already at top)
        dialog.selected_list.setCurrentRow(0)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_up()
        
        # Order should not change
        assert dialog.selected_elements == original_order
    
    def test_move_element_down_boundary(self, dialog, sample_elements):
        """Test moving element down when already at bottom."""
        # Add multiple elements
        dialog.add_all_elements()
        
        # Select last element (already at bottom)
        last_index = len(dialog.selected_elements) - 1
        dialog.selected_list.setCurrentRow(last_index)
        original_order = dialog.selected_elements.copy()
        
        dialog.move_element_down()
        
        # Order should not change
        assert dialog.selected_elements == original_order
    
    def test_update_merge_preview(self, dialog, sample_elements):
        """Test updating merge preview."""
        # Add some elements
        dialog.selected_elements = sample_elements[:2]
        
        # Update preview
        dialog.update_merge_preview()
        
        # Check that preview text contains merged content
        preview_text = dialog.preview_text.toPlainText()
        assert sample_elements[0].text in preview_text
        assert sample_elements[1].text in preview_text
    
    def test_update_merge_preview_empty(self, dialog):
        """Test updating merge preview with no elements."""
        dialog.selected_elements = []
        dialog.update_merge_preview()
        
        # Preview should be empty
        assert dialog.preview_text.toPlainText() == ""
    
    def test_check_metadata_conflicts_no_conflicts(self, dialog, sample_elements):
        """Test metadata conflict detection with no conflicts."""
        # Use elements of the same type
        same_type_elements = [
            Element(element_type=ElementType.TITLE, text="Title 1"),
            Element(element_type=ElementType.TITLE, text="Title 2")
        ]
        dialog.selected_elements = same_type_elements
        
        dialog.check_metadata_conflicts()
        
        # Should not detect conflicts
        # This would need to be verified by checking the metadata resolver state
    
    def test_check_metadata_conflicts_with_conflicts(self, dialog, sample_elements):
        """Test metadata conflict detection with conflicts."""
        # Use elements of different types
        dialog.selected_elements = [sample_elements[0], sample_elements[1]]  # Title and Text
        
        dialog.check_metadata_conflicts()
        
        # Should detect type conflicts
        # This would need to be verified by checking the metadata resolver state
    
    def test_update_button_states_no_selection(self, dialog):
        """Test button states with no elements selected."""
        dialog.selected_elements = []
        dialog.update_button_states()
        
        assert not dialog.preview_button.isEnabled()
        assert not dialog.merge_button.isEnabled()
        assert not dialog.clear_button.isEnabled()
    
    def test_update_button_states_with_selection(self, dialog, sample_elements):
        """Test button states with elements selected."""
        dialog.selected_elements = sample_elements[:2]
        dialog.update_button_states()
        
        assert dialog.preview_button.isEnabled()
        assert dialog.merge_button.isEnabled()
        assert dialog.clear_button.isEnabled()
    
    def test_update_button_states_single_element(self, dialog, sample_elements):
        """Test button states with only one element selected."""
        dialog.selected_elements = [sample_elements[0]]
        dialog.update_button_states()
        
        # Need at least 2 elements to merge
        assert not dialog.preview_button.isEnabled()
        assert not dialog.merge_button.isEnabled()
    
    def test_validate_merge_operation_insufficient_elements(self, dialog):
        """Test validation with insufficient elements."""
        dialog.selected_elements = []
        warnings = dialog.validate_merge_operation()
        
        assert len(warnings) > 0
        assert any("at least 2 elements" in w.lower() for w in warnings)
    
    def test_validate_merge_operation_too_many_elements(self, dialog, sample_elements):
        """Test validation with too many elements."""
        # Create many elements
        many_elements = [
            Element(element_type=ElementType.TITLE, text=f"Element {i}")
            for i in range(15)
        ]
        dialog.selected_elements = many_elements
        
        warnings = dialog.validate_merge_operation()
        assert any("many elements" in w.lower() for w in warnings)
    
    def test_validate_merge_operation_different_types(self, dialog, sample_elements):
        """Test validation with different element types."""
        dialog.selected_elements = [sample_elements[0], sample_elements[1]]  # Title and Text
        
        warnings = dialog.validate_merge_operation()
        assert any("different element types" in w.lower() for w in warnings)
    
    def test_get_merge_options(self, dialog):
        """Test getting merge options."""
        # Set specific options
        dialog.separator_combo.setCurrentText("Newline")
        dialog.preserve_formatting.setChecked(False)
        
        options = dialog.get_merge_options()
        
        assert options["separator"] == "\n"
        assert options["preserve_formatting"] == False
    
    def test_get_merge_options_default(self, dialog):
        """Test getting default merge options."""
        options = dialog.get_merge_options()
        
        assert "separator" in options
        assert "preserve_formatting" in options
        assert isinstance(options["preserve_formatting"], bool)
    
    def test_get_selected_elements(self, dialog, sample_elements):
        """Test getting selected elements."""
        dialog.selected_elements = sample_elements[:2]
        
        result = dialog.get_selected_elements()
        
        assert len(result) == 2
        assert result == sample_elements[:2]
        # Should return a copy
        assert result is not dialog.selected_elements
    
    @patch('src.torematrix.ui.tools.validation.merge_dialog.QMessageBox')
    def test_preview_merge_insufficient_elements(self, mock_msgbox, dialog):
        """Test preview merge with insufficient elements."""
        dialog.selected_elements = [Element(element_type=ElementType.TITLE, text="Single")]
        
        dialog.preview_merge()
        
        # Should show warning
        mock_msgbox.warning.assert_called_once()
    
    def test_preview_merge_valid_selection(self, dialog, sample_elements):
        """Test preview merge with valid selection."""
        dialog.selected_elements = sample_elements[:2]
        
        # Should not raise exception
        dialog.preview_merge()
        
        # Preview should be updated
        preview_text = dialog.preview_text.toPlainText()
        assert len(preview_text) > 0
    
    @patch('src.torematrix.ui.tools.validation.merge_dialog.QMessageBox')
    def test_perform_merge_insufficient_elements(self, mock_msgbox, dialog):
        """Test perform merge with insufficient elements."""
        dialog.selected_elements = []
        
        dialog.perform_merge()
        
        # Should show warning
        mock_msgbox.warning.assert_called_once()
    
    def test_perform_merge_signal_emission(self, dialog, sample_elements):
        """Test merge request signal emission."""
        dialog.selected_elements = sample_elements[:2]
        
        # Connect signal to mock
        signal_mock = Mock()
        dialog.merge_requested.connect(signal_mock)
        
        # Perform merge
        dialog.perform_merge()
        
        # Should emit signal with elements and options
        signal_mock.assert_called_once()
        args = signal_mock.call_args[0]
        assert len(args) == 2  # elements, options
        assert args[0] == sample_elements[:2]
        assert isinstance(args[1], dict)
    
    def test_separator_options(self, dialog):
        """Test different separator options."""
        separators = {
            "Single Space": " ",
            "Double Space": "  ",
            "Newline": "\n",
            "Double Newline": "\n\n"
        }
        
        for separator_name, expected_value in separators.items():
            dialog.separator_combo.setCurrentText(separator_name)
            options = dialog.get_merge_options()
            assert options["separator"] == expected_value
    
    def test_accessibility_features(self, dialog):
        """Test accessibility features."""
        # Check that buttons have accessible names/tooltips
        assert dialog.add_button.text()
        assert dialog.remove_button.text()
        assert dialog.merge_button.text()
        
        # Check that lists have proper selection modes
        assert dialog.available_list.selectionMode() == dialog.available_list.SelectionMode.ExtendedSelection
    
    def test_keyboard_navigation(self, dialog, app):
        """Test keyboard navigation support."""
        # Focus should be able to move between controls
        dialog.available_list.setFocus()
        assert dialog.available_list.hasFocus()
        
        # Tab should move focus
        QTest.keyPress(dialog.available_list, Qt.Key.Key_Tab)
        # Note: Exact focus behavior depends on tab order setup
    
    def test_dialog_rejection(self, dialog):
        """Test dialog rejection (cancel)."""
        # Connect signal to track rejection
        rejected = Mock()
        dialog.rejected.connect(rejected)
        
        # Simulate cancel button click
        dialog.cancel_button.click()
        
        # Dialog should be rejected
        rejected.assert_called_once()
    
    def test_progress_indication(self, dialog, sample_elements):
        """Test progress indication during merge."""
        dialog.selected_elements = sample_elements[:2]
        
        # Progress bar should be hidden initially
        assert not dialog.progress_bar.isVisible()
        
        # Mock the merge request to avoid actually closing dialog
        with patch.object(dialog, 'merge_requested'):
            dialog.perform_merge()
            
            # Progress bar should become visible
            assert dialog.progress_bar.isVisible()
    
    def test_element_order_preservation(self, dialog, sample_elements):
        """Test that element order is preserved during operations."""
        # Add elements in specific order
        for element in sample_elements[:3]:
            if element not in dialog.selected_elements:
                dialog.selected_elements.append(element)
        
        # Update UI to reflect changes
        dialog.update_merge_preview()
        
        # Order should be maintained
        assert dialog.selected_elements == sample_elements[:3]
    
    def test_large_text_handling(self, dialog):
        """Test handling of elements with large text content."""
        large_text = "A" * 10000  # 10KB of text
        large_element = Element(
            element_type=ElementType.NARRATIVE_TEXT,
            text=large_text
        )
        
        dialog.selected_elements = [large_element]
        dialog.update_merge_preview()
        
        # Should handle large text without errors
        preview_text = dialog.preview_text.toPlainText()
        assert len(preview_text) > 0
    
    def test_unicode_text_handling(self, dialog):
        """Test handling of Unicode text content."""
        unicode_elements = [
            Element(element_type=ElementType.TITLE, text="Tëst Ünîcödë 测试"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Émojis: 🚀🎉💻")
        ]
        
        dialog.selected_elements = unicode_elements
        dialog.update_merge_preview()
        
        # Should handle Unicode text correctly
        preview_text = dialog.preview_text.toPlainText()
        assert "Tëst Ünîcödë" in preview_text
        assert "🚀🎉💻" in preview_text