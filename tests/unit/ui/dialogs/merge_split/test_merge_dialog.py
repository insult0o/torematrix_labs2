"""
Tests for MergeDialog component

Agent 2 comprehensive test suite for merge dialog functionality
including drag-and-drop, preview, and metadata conflict resolution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from torematrix.core.models.element import Element, ElementType
from torematrix.core.models.coordinates import Coordinates
from torematrix.core.models.metadata import ElementMetadata
from torematrix.ui.dialogs.merge_split.merge_dialog import (
    MergeDialog, MergeDialogResult, MergeDialogMode
)
from torematrix.core.operations.merge_split.merge import MergeOperation, MergeResult
from torematrix.core.operations.merge_split.algorithms.text_merging import MergeStrategy

# Create QApplication instance if it doesn't exist
if not QApplication.instance():
    app = QApplication(sys.argv)


class TestMergeDialog:
    """Test cases for MergeDialog component."""
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        element1 = Element(
            element_id="elem1",
            element_type=ElementType.TEXT,
            text="First element text",
            metadata=ElementMetadata(
                coordinates=Coordinates(layout_bbox=(0, 0, 100, 20)),
                custom_fields={"source": "test1"}
            )
        )
        
        element2 = Element(
            element_id="elem2",
            element_type=ElementType.TEXT,
            text="Second element text",
            metadata=ElementMetadata(
                coordinates=Coordinates(layout_bbox=(0, 25, 100, 20)),
                custom_fields={"source": "test2"}
            )
        )
        
        element3 = Element(
            element_id="elem3",
            element_type=ElementType.HEADER,
            text="Third element heading",
            metadata=ElementMetadata(
                coordinates=Coordinates(layout_bbox=(0, 50, 100, 25)),
                custom_fields={"source": "test3", "level": 2}
            )
        )
        
        return [element1, element2, element3]
    
    @pytest.fixture
    def merge_dialog(self, sample_elements):
        """Create merge dialog instance."""
        dialog = MergeDialog(sample_elements)
        return dialog
    
    def test_merge_dialog_initialization(self, merge_dialog, sample_elements):
        """Test merge dialog initialization."""
        assert merge_dialog.elements == sample_elements
        assert merge_dialog.current_mode == MergeDialogMode.SELECTION
        assert merge_dialog.merge_result is None
        assert merge_dialog.dialog_result is not None
        assert merge_dialog.windowTitle() == "Merge Elements"
        assert merge_dialog.isModal() == True
    
    def test_merge_dialog_empty_initialization(self):
        """Test merge dialog with no initial elements."""
        dialog = MergeDialog()
        assert dialog.elements == []
        assert dialog.current_mode == MergeDialogMode.SELECTION
        assert dialog.merge_result is None
        assert not dialog.ok_button.isEnabled()
    
    def test_element_list_population(self, merge_dialog, sample_elements):
        """Test element list population."""
        # Check that elements are populated in the list
        assert merge_dialog.element_list.count() == len(sample_elements)
        
        # Check first item
        item = merge_dialog.element_list.item(0)
        assert "Element 1:" in item.text()
        assert "First element text" in item.text()
        
        # Check data storage
        stored_element = item.data(Qt.ItemDataRole.UserRole)
        assert stored_element == sample_elements[0]
    
    def test_add_element_functionality(self, merge_dialog):
        """Test adding individual elements."""
        new_element = Element(
            element_id="new_elem",
            element_type=ElementType.TEXT,
            text="New element",
            metadata=ElementMetadata(
                coordinates=Coordinates(layout_bbox=(0, 75, 100, 20))
            )
        )
        
        initial_count = len(merge_dialog.elements)
        merge_dialog.add_element(new_element)
        
        assert len(merge_dialog.elements) == initial_count + 1
        assert merge_dialog.elements[-1] == new_element
        assert merge_dialog.element_list.count() == initial_count + 1
    
    def test_remove_selected_elements(self, merge_dialog, sample_elements):
        """Test removing selected elements."""
        # Select first item
        merge_dialog.element_list.setCurrentRow(0)
        
        # Remove selected
        merge_dialog._remove_selected()
        
        assert len(merge_dialog.elements) == len(sample_elements) - 1
        assert merge_dialog.elements[0] == sample_elements[1]  # Second element becomes first
        assert merge_dialog.element_list.count() == len(sample_elements) - 1
    
    def test_merge_strategy_selection(self, merge_dialog):
        """Test merge strategy selection."""
        # Test different strategies
        merge_dialog.strategy_combo.setCurrentText("Smart (Recommended)")
        assert merge_dialog._get_merge_strategy() == MergeStrategy.SMART
        
        merge_dialog.strategy_combo.setCurrentText("Simple (Space-separated)")
        assert merge_dialog._get_merge_strategy() == MergeStrategy.SIMPLE
        
        merge_dialog.strategy_combo.setCurrentText("Paragraph (Line breaks)")
        assert merge_dialog._get_merge_strategy() == MergeStrategy.PARAGRAPH
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_merge_validation(self, mock_merge_op, merge_dialog):
        """Test merge validation."""
        # Mock successful validation
        mock_instance = Mock()
        mock_instance.validate.return_value = True
        mock_merge_op.return_value = mock_instance
        
        assert merge_dialog._is_valid_merge() == True
        mock_merge_op.assert_called_once_with(merge_dialog.elements)
        mock_instance.validate.assert_called_once()
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_merge_validation_failure(self, mock_merge_op, merge_dialog):
        """Test merge validation failure."""
        # Mock validation failure
        mock_instance = Mock()
        mock_instance.validate.return_value = False
        mock_merge_op.return_value = mock_instance
        
        assert merge_dialog._is_valid_merge() == False
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_preview_update(self, mock_merge_op, merge_dialog):
        """Test preview update functionality."""
        # Mock successful preview
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.merged_element = Mock()
        mock_instance.preview.return_value = mock_result
        mock_merge_op.return_value = mock_instance
        
        merge_dialog._update_preview()
        
        mock_merge_op.assert_called_once_with(merge_dialog.elements)
        mock_instance.preview.assert_called_once()
        assert merge_dialog.merge_result == mock_result
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_preview_update_failure(self, mock_merge_op, merge_dialog):
        """Test preview update failure."""
        # Mock preview failure
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Preview failed"
        mock_instance.preview.return_value = mock_result
        mock_merge_op.return_value = mock_instance
        
        merge_dialog._update_preview()
        
        assert merge_dialog.merge_result is None
        # Should add warning to validation widget
        assert merge_dialog.validation_widget.has_warnings()
    
    def test_preview_delayed_update(self, merge_dialog):
        """Test delayed preview update."""
        # Mock the timer
        with patch.object(merge_dialog.preview_timer, 'start') as mock_start:
            merge_dialog._update_preview_delayed()
            mock_start.assert_called_once_with(300)
    
    def test_ui_state_update(self, merge_dialog):
        """Test UI state updates."""
        # With valid elements
        merge_dialog._update_ui_state()
        
        # Should enable OK button if merge is valid
        with patch.object(merge_dialog, '_is_valid_merge', return_value=True):
            merge_dialog._update_ui_state()
            assert merge_dialog.ok_button.isEnabled()
        
        # Should disable OK button if merge is invalid
        with patch.object(merge_dialog, '_is_valid_merge', return_value=False):
            merge_dialog._update_ui_state()
            assert not merge_dialog.ok_button.isEnabled()
    
    def test_element_selection_change(self, merge_dialog):
        """Test element selection change handling."""
        # Select an item
        merge_dialog.element_list.setCurrentRow(0)
        merge_dialog._on_selection_changed()
        
        # Remove button should be enabled
        assert merge_dialog.remove_button.isEnabled()
        
        # Clear selection
        merge_dialog.element_list.clearSelection()
        merge_dialog._on_selection_changed()
        
        # Remove button should be disabled
        assert not merge_dialog.remove_button.isEnabled()
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_merge_execution_success(self, mock_merge_op, merge_dialog):
        """Test successful merge execution."""
        # Mock successful merge
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.merged_element = Mock()
        mock_instance.execute.return_value = mock_result
        mock_merge_op.return_value = mock_instance
        
        # Set up merge result
        merge_dialog.merge_result = mock_result
        
        # Mock dialog acceptance
        with patch.object(merge_dialog, 'accept') as mock_accept:
            merge_dialog._accept_merge()
            mock_accept.assert_called_once()
        
        # Check dialog result
        assert merge_dialog.dialog_result.accepted == True
        assert merge_dialog.dialog_result.merged_element == mock_result.merged_element
        assert merge_dialog.dialog_result.original_elements == merge_dialog.elements
    
    @patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeOperation')
    def test_merge_execution_failure(self, mock_merge_op, merge_dialog):
        """Test merge execution failure."""
        # Mock failed merge
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Merge failed"
        mock_instance.execute.return_value = mock_result
        mock_merge_op.return_value = mock_instance
        
        # Set up merge result
        merge_dialog.merge_result = Mock()
        
        merge_dialog._accept_merge()
        
        # Should not accept dialog
        assert merge_dialog.dialog_result.accepted == False
        # Should add error to validation widget
        assert merge_dialog.validation_widget.has_errors()
    
    def test_drag_drop_events(self, merge_dialog):
        """Test drag and drop event handling."""
        # Mock drag enter event
        mock_event = Mock()
        mock_event.mimeData.return_value.hasFormat.return_value = True
        
        merge_dialog.dragEnterEvent(mock_event)
        mock_event.acceptProposedAction.assert_called_once()
    
    def test_set_elements_method(self, merge_dialog, sample_elements):
        """Test set_elements method."""
        new_elements = sample_elements[:2]  # Only first two elements
        
        merge_dialog.set_elements(new_elements)
        
        assert merge_dialog.elements == new_elements
        assert merge_dialog.element_list.count() == len(new_elements)
    
    def test_signals_emission(self, merge_dialog):
        """Test signal emission."""
        # Test elements_changed signal
        with patch.object(merge_dialog.elements_changed, 'emit') as mock_emit:
            merge_dialog.set_elements([])
            mock_emit.assert_called_once()
        
        # Test preview_updated signal
        with patch.object(merge_dialog.preview_updated, 'emit') as mock_emit:
            mock_result = Mock()
            merge_dialog.merge_result = mock_result
            merge_dialog._on_preview_updated(mock_result)
            # Signal should be emitted when preview is updated
    
    def test_dialog_result_structure(self, merge_dialog):
        """Test dialog result structure."""
        result = merge_dialog.get_result()
        
        assert hasattr(result, 'accepted')
        assert hasattr(result, 'merged_element')
        assert hasattr(result, 'original_elements')
        assert hasattr(result, 'merge_strategy')
        assert hasattr(result, 'metadata_strategies')
        
        # Check default values
        assert result.accepted == False
        assert result.merged_element is None
        assert result.original_elements == []
        assert result.merge_strategy == MergeStrategy.SMART
        assert result.metadata_strategies == {}
    
    def test_empty_elements_handling(self, merge_dialog):
        """Test handling of empty elements list."""
        merge_dialog.set_elements([])
        
        assert merge_dialog.elements == []
        assert merge_dialog.element_list.count() == 0
        assert not merge_dialog.ok_button.isEnabled()
        assert not merge_dialog._is_valid_merge()
    
    def test_single_element_handling(self, merge_dialog, sample_elements):
        """Test handling of single element."""
        merge_dialog.set_elements([sample_elements[0]])
        
        assert len(merge_dialog.elements) == 1
        assert not merge_dialog.ok_button.isEnabled()
        assert not merge_dialog._is_valid_merge()
    
    def test_metadata_resolver_integration(self, merge_dialog):
        """Test metadata resolver integration."""
        # Should have metadata resolver
        assert merge_dialog.metadata_resolver is not None
        
        # Should call set_elements on preview update
        with patch.object(merge_dialog.metadata_resolver, 'set_elements') as mock_set:
            merge_dialog._update_preview()
            mock_set.assert_called_once_with(merge_dialog.elements)
    
    def test_validation_widget_integration(self, merge_dialog):
        """Test validation widget integration."""
        # Should have validation widget
        assert merge_dialog.validation_widget is not None
        
        # Should clear warnings on successful preview
        with patch.object(merge_dialog.validation_widget, 'clear_warnings') as mock_clear:
            with patch.object(merge_dialog, '_is_valid_merge', return_value=True):
                merge_dialog._update_preview()
                # Will be called if preview is successful
    
    def test_convenience_function(self, sample_elements):
        """Test convenience function for showing dialog."""
        from torematrix.ui.dialogs.merge_split.merge_dialog import show_merge_dialog
        
        # Mock the dialog execution
        with patch('torematrix.ui.dialogs.merge_split.merge_dialog.MergeDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_result = Mock()
            mock_dialog.get_result.return_value = mock_result
            mock_dialog_class.return_value = mock_dialog
            
            result = show_merge_dialog(sample_elements)
            
            mock_dialog_class.assert_called_once_with(sample_elements, None)
            mock_dialog.exec.assert_called_once()
            assert result == mock_result


class TestMergeDialogResult:
    """Test cases for MergeDialogResult."""
    
    def test_result_initialization(self):
        """Test result initialization."""
        result = MergeDialogResult()
        
        assert result.accepted == False
        assert result.merged_element is None
        assert result.original_elements == []
        assert result.merge_strategy == MergeStrategy.SMART
        assert result.metadata_strategies == {}
    
    def test_result_with_data(self):
        """Test result with actual data."""
        element = Mock()
        original = [Mock(), Mock()]
        strategies = {"key1": "value1"}
        
        result = MergeDialogResult(
            accepted=True,
            merged_element=element,
            original_elements=original,
            merge_strategy=MergeStrategy.PARAGRAPH,
            metadata_strategies=strategies
        )
        
        assert result.accepted == True
        assert result.merged_element == element
        assert result.original_elements == original
        assert result.merge_strategy == MergeStrategy.PARAGRAPH
        assert result.metadata_strategies == strategies