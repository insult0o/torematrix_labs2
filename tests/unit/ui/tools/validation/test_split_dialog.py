"""
Tests for SplitDialog component.

This module provides comprehensive tests for the split dialog functionality
including text editing, split point selection, and split operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QMouseEvent, QTextCursor

from src.torematrix.core.models import Element, ElementType
from src.torematrix.ui.tools.validation.split_dialog import (
    SplitDialog, InteractiveSplitTextEdit, SplitPreviewWidget, SplitPointHighlighter
)


class TestSplitPointHighlighter:
    """Tests for the split point highlighter."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def highlighter(self, app):
        """Create split point highlighter."""
        from PyQt6.QtGui import QTextDocument
        document = QTextDocument()
        return SplitPointHighlighter(document)
    
    def test_initialization(self, highlighter):
        """Test highlighter initialization."""
        assert highlighter.split_positions == []
        assert highlighter.split_format is not None
    
    def test_set_split_positions(self, highlighter):
        """Test setting split positions."""
        positions = [10, 20, 30]
        highlighter.set_split_positions(positions)
        
        assert highlighter.split_positions == positions


class TestInteractiveSplitTextEdit:
    """Tests for the interactive split text editor."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def text_edit(self, app):
        """Create interactive split text editor."""
        editor = InteractiveSplitTextEdit()
        editor.setPlainText("This is a sample text for testing split functionality.")
        return editor
    
    def test_initialization(self, text_edit):
        """Test text editor initialization."""
        assert text_edit.split_positions == []
        assert text_edit.highlighter is not None
        assert text_edit.toPlainText() != ""
    
    def test_add_split_point(self, text_edit):
        """Test adding split points."""
        # Connect signal to mock
        signal_mock = Mock()
        text_edit.split_point_added.connect(signal_mock)
        
        # Add split point
        position = 10
        text_edit.add_split_point(position)
        
        assert position in text_edit.split_positions
        signal_mock.assert_called_once_with(position)
    
    def test_add_split_point_duplicate(self, text_edit):
        """Test adding duplicate split points."""
        position = 10
        text_edit.add_split_point(position)
        text_edit.add_split_point(position)  # Duplicate
        
        # Should only appear once
        assert text_edit.split_positions.count(position) == 1
    
    def test_add_split_point_zero_position(self, text_edit):
        """Test adding split point at position 0."""
        text_edit.add_split_point(0)
        
        # Position 0 should not be added
        assert 0 not in text_edit.split_positions
    
    def test_remove_split_point(self, text_edit):
        """Test removing split points."""
        # Connect signal to mock
        signal_mock = Mock()
        text_edit.split_point_removed.connect(signal_mock)
        
        # Add and then remove split point
        position = 10
        text_edit.add_split_point(position)
        text_edit.remove_split_point(position)
        
        assert position not in text_edit.split_positions
        signal_mock.assert_called_once_with(position)
    
    def test_clear_split_points(self, text_edit):
        """Test clearing all split points."""
        # Add multiple split points
        positions = [10, 20, 30]
        for pos in positions:
            text_edit.add_split_point(pos)
        
        text_edit.clear_split_points()
        assert text_edit.split_positions == []
    
    def test_get_split_positions(self, text_edit):
        """Test getting split positions."""
        positions = [30, 10, 20]  # Unsorted
        for pos in positions:
            text_edit.add_split_point(pos)
        
        result = text_edit.get_split_positions()
        expected = sorted(positions)
        assert result == expected
    
    def test_set_split_positions(self, text_edit):
        """Test setting split positions programmatically."""
        positions = [30, 10, 20]  # Unsorted
        text_edit.set_split_positions(positions)
        
        assert text_edit.split_positions == sorted(positions)
    
    def test_get_split_segments_no_splits(self, text_edit):
        """Test getting segments with no split points."""
        segments = text_edit.get_split_segments()
        assert len(segments) == 1
        assert segments[0] == text_edit.toPlainText()
    
    def test_get_split_segments_with_splits(self, text_edit):
        """Test getting segments with split points."""
        text = "Hello world! This is a test."
        text_edit.setPlainText(text)
        
        # Add split points at spaces
        positions = [6, 13]  # After "Hello " and "world! "
        text_edit.set_split_positions(positions)
        
        segments = text_edit.get_split_segments()
        assert len(segments) == 3
        assert segments[0].strip() == "Hello"
        assert segments[1].strip() == "world!"
        assert segments[2].strip() == "This is a test."
    
    def test_mouse_press_event_normal_click(self, text_edit):
        """Test normal mouse click without Ctrl."""
        # Mock cursor position
        with patch.object(text_edit, 'cursorForPosition') as mock_cursor_for_pos:
            mock_cursor = Mock()
            mock_cursor.position.return_value = 10
            mock_cursor_for_pos.return_value = mock_cursor
            
            # Create mock mouse event
            event = Mock()
            event.button.return_value = Qt.MouseButton.LeftButton
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
            event.pos.return_value = Mock()
            
            # Call mousePressEvent
            with patch('PyQt6.QtWidgets.QTextEdit.mousePressEvent') as mock_super:
                text_edit.mousePressEvent(event)
                mock_super.assert_called_once_with(event)
    
    def test_mouse_press_event_ctrl_click(self, text_edit):
        """Test Ctrl+click to add split point."""
        # Mock cursor position
        with patch.object(text_edit, 'cursorForPosition') as mock_cursor_for_pos:
            mock_cursor = Mock()
            mock_cursor.position.return_value = 10
            mock_cursor_for_pos.return_value = mock_cursor
            
            # Create mock mouse event with Ctrl
            event = Mock()
            event.button.return_value = Qt.MouseButton.LeftButton
            event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
            event.pos.return_value = Mock()
            
            # Call mousePressEvent
            text_edit.mousePressEvent(event)
            
            assert 10 in text_edit.split_positions


class TestSplitPreviewWidget:
    """Tests for the split preview widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create split preview widget."""
        return SplitPreviewWidget()
    
    @pytest.fixture
    def sample_element(self):
        """Create sample element for testing."""
        return Element(
            element_type=ElementType.NARRATIVE_TEXT,
            text="This is a sample text that will be split into multiple segments."
        )
    
    def test_initialization(self, preview_widget):
        """Test widget initialization."""
        assert preview_widget.element_type_combo.count() > 0
        assert preview_widget.preserve_metadata.isChecked()
        assert preview_widget.auto_trim.isChecked()
    
    def test_set_original_element(self, preview_widget, sample_element):
        """Test setting original element."""
        preview_widget.set_original_element(sample_element)
        
        # Should update info display
        info_text = preview_widget.original_info.text()
        assert sample_element.element_type.value in info_text
        assert str(len(sample_element.text)) in info_text
        
        # Should set element type combo
        combo_text = preview_widget.element_type_combo.currentText()
        assert combo_text == sample_element.element_type.value
    
    def test_set_split_segments(self, preview_widget, sample_element):
        """Test setting split segments."""
        preview_widget.set_original_element(sample_element)
        
        segments = ["This is a sample text", "that will be split", "into multiple segments."]
        preview_widget.set_split_segments(segments)
        
        # Should update result list
        assert preview_widget.result_list.count() == len(segments)
        
        for i in range(len(segments)):
            item = preview_widget.result_list.item(i)
            assert segments[i][:20] in item.text()  # Check partial text match
    
    def test_get_resulting_elements(self, preview_widget, sample_element):
        """Test getting resulting elements."""
        preview_widget.set_original_element(sample_element)
        segments = ["Segment 1", "Segment 2", "Segment 3"]
        preview_widget.set_split_segments(segments)
        
        elements = preview_widget.get_resulting_elements()
        
        assert len(elements) == len(segments)
        for i, element in enumerate(elements):
            assert element.text == segments[i]
            assert element.element_type == ElementType.NARRATIVE_TEXT
    
    def test_get_resulting_elements_empty_segments(self, preview_widget, sample_element):
        """Test getting elements with empty segments."""
        preview_widget.set_original_element(sample_element)
        segments = ["Segment 1", "", "Segment 3", "   "]  # Include empty and whitespace
        preview_widget.set_split_segments(segments)
        
        elements = preview_widget.get_resulting_elements()
        
        # Should only create elements for non-empty segments
        assert len(elements) == 2  # Only "Segment 1" and "Segment 3"
        assert elements[0].text == "Segment 1"
        assert elements[1].text == "Segment 3"
    
    def test_get_split_options(self, preview_widget):
        """Test getting split options."""
        # Set custom options
        preview_widget.element_type_combo.setCurrentText("Title")
        preview_widget.preserve_metadata.setChecked(False)
        preview_widget.auto_trim.setChecked(False)
        
        options = preview_widget.get_split_options()
        
        assert options["element_type"] == "Title"
        assert options["preserve_metadata"] == False
        assert options["auto_trim"] == False


class TestSplitDialog:
    """Tests for the main split dialog."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def sample_element(self):
        """Create sample element for testing."""
        return Element(
            element_type=ElementType.NARRATIVE_TEXT,
            text="This is a sample text that will be split into multiple segments for testing purposes."
        )
    
    @pytest.fixture
    def dialog(self, app, sample_element):
        """Create split dialog."""
        return SplitDialog(sample_element)
    
    def test_initialization(self, dialog, sample_element):
        """Test dialog initialization."""
        assert sample_element.element_type.value in dialog.windowTitle()
        assert dialog.isModal()
        assert dialog.original_element == sample_element
        assert dialog.text_editor.toPlainText() == sample_element.text
    
    def test_load_element(self, dialog, sample_element):
        """Test loading element content."""
        # Element should be loaded automatically in __init__
        info_text = dialog.element_info.text()
        assert sample_element.element_type.value in info_text
        assert sample_element.element_id in info_text
        
        assert dialog.text_editor.toPlainText() == sample_element.text
    
    def test_add_split_at_cursor(self, dialog):
        """Test adding split point at cursor position."""
        # Set cursor position
        cursor = dialog.text_editor.textCursor()
        cursor.setPosition(10)
        dialog.text_editor.setTextCursor(cursor)
        
        dialog.add_split_at_cursor()
        
        assert 10 in dialog.text_editor.get_split_positions()
    
    def test_remove_split_at_cursor(self, dialog):
        """Test removing split point at cursor position."""
        # Add split point first
        dialog.text_editor.add_split_point(10)
        
        # Set cursor to same position
        cursor = dialog.text_editor.textCursor()
        cursor.setPosition(10)
        dialog.text_editor.setTextCursor(cursor)
        
        dialog.remove_split_at_cursor()
        
        assert 10 not in dialog.text_editor.get_split_positions()
    
    def test_clear_all_splits(self, dialog):
        """Test clearing all split points."""
        # Add multiple split points
        positions = [10, 20, 30]
        for pos in positions:
            dialog.text_editor.add_split_point(pos)
        
        dialog.clear_all_splits()
        
        assert dialog.text_editor.get_split_positions() == []
        assert dialog.split_positions == []
    
    def test_on_split_point_added(self, dialog):
        """Test handling split point addition."""
        initial_count = dialog.positions_list.count()
        
        # Simulate split point addition
        dialog.text_editor.add_split_point(10)
        dialog.on_split_point_added(10)
        
        assert dialog.positions_list.count() == initial_count + 1
        assert 10 in dialog.split_positions
    
    def test_on_split_point_removed(self, dialog):
        """Test handling split point removal."""
        # Add split point first
        dialog.text_editor.add_split_point(10)
        dialog.on_split_point_added(10)
        initial_count = dialog.positions_list.count()
        
        # Remove split point
        dialog.text_editor.remove_split_point(10)
        dialog.on_split_point_removed(10)
        
        assert dialog.positions_list.count() == initial_count - 1
        assert 10 not in dialog.split_positions
    
    def test_update_split_preview(self, dialog):
        """Test updating split preview."""
        # Add split points
        positions = [20, 40]
        for pos in positions:
            dialog.text_editor.add_split_point(pos)
        
        dialog.update_split_preview()
        
        # Should update preview with segments
        segments = dialog.text_editor.get_split_segments()
        assert len(segments) == 3  # Text split at 2 points = 3 segments
    
    def test_update_button_states(self, dialog):
        """Test button state updates."""
        # Initially no splits
        dialog.update_button_states()
        assert not dialog.preview_button.isEnabled()
        assert not dialog.split_button.isEnabled()
        
        # Add split points
        dialog.text_editor.add_split_point(10)
        dialog.split_positions = [10]
        dialog.update_button_states()
        
        assert dialog.preview_button.isEnabled()
        assert dialog.split_button.isEnabled()
    
    def test_validate_split_operation_no_splits(self, dialog):
        """Test validation with no split points."""
        warnings = dialog.validate_split_operation()
        assert len(warnings) > 0
        assert any("no split points" in w.lower() for w in warnings)
    
    def test_validate_split_operation_many_segments(self, dialog):
        """Test validation with too many segments."""
        # Add many split points
        positions = list(range(5, 100, 5))  # Create many segments
        for pos in positions:
            dialog.text_editor.add_split_point(pos)
        
        warnings = dialog.validate_split_operation()
        assert any("too many" in w.lower() for w in warnings)
    
    def test_perform_auto_split_sentences(self, dialog):
        """Test automatic split by sentences."""
        # Set text with sentences
        text_with_sentences = "First sentence. Second sentence! Third sentence?"
        dialog.text_editor.setPlainText(text_with_sentences)
        
        dialog.perform_auto_split("Split by sentences")
        
        # Should add split points after sentence endings
        positions = dialog.text_editor.get_split_positions()
        assert len(positions) > 0
    
    def test_perform_auto_split_character_count(self, dialog):
        """Test automatic split by character count."""
        with patch('PyQt6.QtWidgets.QInputDialog.getInt') as mock_input:
            mock_input.return_value = (20, True)  # 20 characters per segment
            
            dialog.perform_auto_split("Split by character count")
            
            positions = dialog.text_editor.get_split_positions()
            # Should have splits approximately every 20 characters
            if positions:
                assert positions[0] == 20
    
    def test_get_split_positions(self, dialog):
        """Test getting split positions."""
        positions = [10, 20, 30]
        for pos in positions:
            dialog.text_editor.add_split_point(pos)
        dialog.split_positions = positions
        
        result = dialog.get_split_positions()
        assert result == positions
        # Should be a copy
        assert result is not dialog.split_positions
    
    def test_get_resulting_elements(self, dialog):
        """Test getting resulting elements."""
        # Add split points
        positions = [20, 40]
        for pos in positions:
            dialog.text_editor.add_split_point(pos)
        
        dialog.update_split_preview()
        elements = dialog.get_resulting_elements()
        
        assert len(elements) >= 2  # Should have multiple segments
        for element in elements:
            assert isinstance(element, Element)
            assert element.text.strip()  # Should have non-empty text
    
    def test_get_split_options(self, dialog):
        """Test getting split options."""
        options = dialog.get_split_options()
        
        assert "element_type" in options
        assert "preserve_metadata" in options
        assert "auto_trim" in options
    
    @patch('src.torematrix.ui.tools.validation.split_dialog.QMessageBox')
    def test_perform_split_no_splits(self, mock_msgbox, dialog):
        """Test performing split with no split points."""
        dialog.perform_split()
        
        # Should show warning
        mock_msgbox.warning.assert_called_once()
    
    def test_perform_split_signal_emission(self, dialog):
        """Test split request signal emission."""
        # Add split points
        dialog.text_editor.add_split_point(20)
        dialog.split_positions = [20]
        
        # Connect signal
        signal_mock = Mock()
        dialog.split_requested.connect(signal_mock)
        
        # Perform split
        dialog.perform_split()
        
        # Should emit signal with element, positions, and options
        signal_mock.assert_called_once()
        args = signal_mock.call_args[0]
        assert len(args) == 3  # element, positions, options
        assert args[0] == dialog.original_element
        assert args[1] == [20]
        assert isinstance(args[2], dict)