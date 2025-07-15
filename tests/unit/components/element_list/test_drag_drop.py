"""
Tests for Drag and Drop System

Comprehensive test suite for drag-and-drop functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, QMimeData, Qt, QModelIndex
from PyQt6.QtWidgets import QTreeView, QApplication
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

from src.torematrix.ui.components.element_list.interactions.drag_drop import (
    DragDropHandler, DragDropValidator, DropIndicator, DragDropMimeData
)
from src.torematrix.ui.components.element_list.models.tree_node import TreeNode


@pytest.fixture
def mock_tree_view():
    """Create mock tree view."""
    tree_view = Mock(spec=QTreeView)
    tree_view.model.return_value = Mock()
    tree_view.mapToGlobal.return_value = QPoint(100, 100)
    tree_view.viewport.return_value = Mock()
    tree_view.indexAt.return_value = QModelIndex()
    tree_view.visualRect.return_value = Mock()
    return tree_view


@pytest.fixture
def mock_element():
    """Create mock element."""
    element = Mock()
    element.id = "test_element_1"
    element.type = "text"
    element.text = "Test content"
    element.confidence = 0.95
    return element


@pytest.fixture
def sample_nodes(mock_element):
    """Create sample tree nodes."""
    parent = TreeNode()
    child1 = TreeNode(mock_element, parent)
    child2 = TreeNode(mock_element, parent)
    parent.add_child(child1)
    parent.add_child(child2)
    return parent, child1, child2


class TestDragDropValidator:
    """Test drag-drop validation logic."""
    
    def test_can_drop_on_target_valid(self, sample_nodes):
        """Test valid drop operation."""
        parent, child1, child2 = sample_nodes
        
        can_drop, reason = DragDropValidator.can_drop_on_target(child1, parent)
        assert can_drop
        assert reason == "Valid drop"
    
    def test_can_drop_on_target_self(self, sample_nodes):
        """Test dropping on self is invalid."""
        parent, child1, child2 = sample_nodes
        
        can_drop, reason = DragDropValidator.can_drop_on_target(child1, child1)
        assert not can_drop
        assert "Cannot drop on self" in reason
    
    def test_can_drop_on_target_ancestor(self, sample_nodes):
        """Test dropping on ancestor is invalid."""
        parent, child1, child2 = sample_nodes
        
        # Add grandchild
        grandchild = TreeNode(Mock(), child1)
        child1.add_child(grandchild)
        
        can_drop, reason = DragDropValidator.can_drop_on_target(child1, grandchild)
        assert not can_drop
        assert "Cannot drop on descendant" in reason
    
    def test_can_drop_invalid_nodes(self):
        """Test with invalid nodes."""
        can_drop, reason = DragDropValidator.can_drop_on_target(None, None)
        assert not can_drop
        assert "Invalid nodes" in reason
    
    def test_get_insert_position_on(self, sample_nodes):
        """Test insert position 'on'."""
        parent, child1, child2 = sample_nodes
        
        result_parent, insert_index = DragDropValidator.get_insert_position(parent, 'on')
        assert result_parent == parent
        assert insert_index == parent.child_count()
    
    def test_get_insert_position_above(self, sample_nodes):
        """Test insert position 'above'."""
        parent, child1, child2 = sample_nodes
        
        result_parent, insert_index = DragDropValidator.get_insert_position(child1, 'above')
        assert result_parent == parent
        assert insert_index == 0  # child1 is at index 0
    
    def test_get_insert_position_below(self, sample_nodes):
        """Test insert position 'below'."""
        parent, child1, child2 = sample_nodes
        
        result_parent, insert_index = DragDropValidator.get_insert_position(child1, 'below')
        assert result_parent == parent
        assert insert_index == 1  # Insert after child1


class TestDropIndicator:
    """Test drop indicator visual feedback."""
    
    def test_show_indicator_above(self, mock_tree_view):
        """Test showing indicator above item."""
        indicator = DropIndicator(mock_tree_view)
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.left.return_value = 10
        mock_rect.top.return_value = 20
        mock_rect.width.return_value = 100
        mock_rect.height.return_value = 25
        
        mock_tree_view.visualRect.return_value = mock_rect
        
        indicator.show_indicator(mock_index, 'above')
        
        assert indicator.visible
        assert indicator.drop_position == 'above'
        assert indicator.indicator_rect.top() == 19  # rect.top() - 1
    
    def test_show_indicator_below(self, mock_tree_view):
        """Test showing indicator below item."""
        indicator = DropIndicator(mock_tree_view)
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.left.return_value = 10
        mock_rect.bottom.return_value = 45
        mock_rect.width.return_value = 100
        mock_rect.height.return_value = 25
        
        mock_tree_view.visualRect.return_value = mock_rect
        
        indicator.show_indicator(mock_index, 'below')
        
        assert indicator.visible
        assert indicator.drop_position == 'below'
        assert indicator.indicator_rect.top() == 44  # rect.bottom() - 1
    
    def test_show_indicator_on(self, mock_tree_view):
        """Test showing indicator on item."""
        indicator = DropIndicator(mock_tree_view)
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.left.return_value = 10
        mock_rect.top.return_value = 20
        mock_rect.width.return_value = 100
        mock_rect.height.return_value = 25
        
        mock_tree_view.visualRect.return_value = mock_rect
        
        indicator.show_indicator(mock_index, 'on')
        
        assert indicator.visible
        assert indicator.drop_position == 'on'
        assert indicator.indicator_rect == mock_rect
    
    def test_hide_indicator(self, mock_tree_view):
        """Test hiding indicator."""
        indicator = DropIndicator(mock_tree_view)
        indicator.visible = True
        
        indicator.hide_indicator()
        
        assert not indicator.visible
        assert indicator.indicator_rect.isEmpty()


class TestDragDropMimeData:
    """Test MIME data handling."""
    
    def test_create_element_mime_data_single(self):
        """Test creating MIME data for single element."""
        element_ids = ["element_1"]
        mime_data = DragDropMimeData.create_element_mime_data(element_ids)
        
        assert mime_data.text() == "element_1"
        assert mime_data.hasFormat(DragDropMimeData.ELEMENT_ID_FORMAT)
    
    def test_create_element_mime_data_multiple(self):
        """Test creating MIME data for multiple elements."""
        element_ids = ["element_1", "element_2", "element_3"]
        mime_data = DragDropMimeData.create_element_mime_data(element_ids)
        
        assert mime_data.hasFormat(DragDropMimeData.ELEMENT_LIST_FORMAT)
        list_data = mime_data.data(DragDropMimeData.ELEMENT_LIST_FORMAT).data().decode()
        assert list_data == "element_1\nelement_2\nelement_3"
    
    def test_extract_element_ids_single(self):
        """Test extracting single element ID."""
        mime_data = QMimeData()
        mime_data.setText("element_1")
        
        element_ids = DragDropMimeData.extract_element_ids(mime_data)
        assert element_ids == ["element_1"]
    
    def test_extract_element_ids_multiple(self):
        """Test extracting multiple element IDs."""
        mime_data = QMimeData()
        mime_data.setData(DragDropMimeData.ELEMENT_LIST_FORMAT, 
                         "element_1\nelement_2\nelement_3".encode())
        
        element_ids = DragDropMimeData.extract_element_ids(mime_data)
        assert element_ids == ["element_1", "element_2", "element_3"]
    
    def test_extract_element_ids_empty(self):
        """Test extracting from empty MIME data."""
        mime_data = QMimeData()
        
        element_ids = DragDropMimeData.extract_element_ids(mime_data)
        assert element_ids == []


class TestDragDropHandler:
    """Test drag-drop handler functionality."""
    
    def setup_method(self):
        """Setup test method."""
        # Ensure QApplication exists
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_handler_initialization(self, mock_tree_view):
        """Test handler initialization."""
        handler = DragDropHandler(mock_tree_view)
        
        assert handler.tree_view == mock_tree_view
        assert isinstance(handler.validator, DragDropValidator)
        assert isinstance(handler.drop_indicator, DropIndicator)
        assert not handler.dragging
    
    def test_setup_drag_drop_configuration(self, mock_tree_view):
        """Test drag-drop configuration setup."""
        handler = DragDropHandler(mock_tree_view)
        
        # Verify configuration methods were called
        mock_tree_view.setDragEnabled.assert_called_with(True)
        mock_tree_view.setAcceptDrops.assert_called_with(True)
        mock_tree_view.setDropIndicatorShown.assert_called_with(False)
    
    @patch('src.torematrix.ui.components.element_list.interactions.drag_drop.QDrag')
    def test_start_drag(self, mock_qdrag_class, mock_tree_view):
        """Test starting drag operation."""
        handler = DragDropHandler(mock_tree_view)
        
        # Setup mock index and model
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_model = Mock()
        mock_model.data.return_value = "element_1"
        mock_tree_view.model.return_value = mock_model
        
        # Setup mock drag
        mock_drag = Mock()
        mock_qdrag_class.return_value = mock_drag
        mock_drag.exec.return_value = Qt.DropAction.MoveAction
        
        # Test start drag
        handler.start_drag(mock_index)
        
        assert handler.dragging
        assert handler.drag_source_index == mock_index
        mock_qdrag_class.assert_called_once()
    
    def test_get_drop_position_above(self, mock_tree_view):
        """Test determining drop position - above."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.top.return_value = 100
        mock_rect.height.return_value = 30
        mock_tree_view.visualRect.return_value = mock_rect
        
        # Position in top third
        position = QPoint(50, 105)
        drop_pos = handler._get_drop_position(mock_index, position)
        
        assert drop_pos == 'above'
    
    def test_get_drop_position_below(self, mock_tree_view):
        """Test determining drop position - below."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.top.return_value = 100
        mock_rect.height.return_value = 30
        mock_tree_view.visualRect.return_value = mock_rect
        
        # Position in bottom third
        position = QPoint(50, 125)
        drop_pos = handler._get_drop_position(mock_index, position)
        
        assert drop_pos == 'below'
    
    def test_get_drop_position_on(self, mock_tree_view):
        """Test determining drop position - on."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_index = Mock()
        mock_rect = Mock()
        mock_rect.top.return_value = 100
        mock_rect.height.return_value = 30
        mock_tree_view.visualRect.return_value = mock_rect
        
        # Position in middle third
        position = QPoint(50, 115)
        drop_pos = handler._get_drop_position(mock_index, position)
        
        assert drop_pos == 'on'
    
    def test_is_valid_drag_with_text(self, mock_tree_view):
        """Test drag validation with text data."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_event = Mock()
        mock_mime_data = Mock()
        mock_mime_data.hasText.return_value = True
        mock_mime_data.hasFormat.return_value = False
        mock_event.mimeData.return_value = mock_mime_data
        
        assert handler._is_valid_drag(mock_event)
    
    def test_is_valid_drag_with_element_format(self, mock_tree_view):
        """Test drag validation with element format."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_event = Mock()
        mock_mime_data = Mock()
        mock_mime_data.hasText.return_value = False
        mock_mime_data.hasFormat.return_value = True
        mock_event.mimeData.return_value = mock_mime_data
        
        assert handler._is_valid_drag(mock_event)
    
    def test_is_valid_drag_invalid(self, mock_tree_view):
        """Test drag validation with invalid data."""
        handler = DragDropHandler(mock_tree_view)
        
        mock_event = Mock()
        mock_mime_data = Mock()
        mock_mime_data.hasText.return_value = False
        mock_mime_data.hasFormat.return_value = False
        mock_event.mimeData.return_value = mock_mime_data
        
        assert not handler._is_valid_drag(mock_event)
    
    def test_signal_emission(self, mock_tree_view):
        """Test signal emission."""
        handler = DragDropHandler(mock_tree_view)
        
        # Test signal connections exist
        assert hasattr(handler, 'elementMoved')
        assert hasattr(handler, 'elementCopied')
        assert hasattr(handler, 'dragStarted')
        assert hasattr(handler, 'dragEnded')


@pytest.mark.integration
class TestDragDropIntegration:
    """Integration tests for drag-drop system."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_full_drag_drop_workflow(self, mock_tree_view, sample_nodes):
        """Test complete drag-drop workflow."""
        handler = DragDropHandler(mock_tree_view)
        parent, child1, child2 = sample_nodes
        
        # Setup model mock to return nodes
        mock_model = Mock()
        mock_model.get_node_by_element_id.side_effect = lambda id: child1 if id == "element_1" else child2
        mock_tree_view.model.return_value = mock_model
        
        # Test validation
        can_drop, reason = handler.validator.can_drop_on_target(child1, parent)
        assert can_drop
        
        # Test drop position calculation
        parent_node, insert_index = handler.validator.get_insert_position(child1, 'on')
        assert parent_node == child1
        assert insert_index == 0  # child1 has no children
    
    def test_drag_drop_signal_workflow(self, mock_tree_view):
        """Test signal emission workflow."""
        handler = DragDropHandler(mock_tree_view)
        
        # Mock signal connections
        element_moved_spy = Mock()
        element_copied_spy = Mock()
        drag_started_spy = Mock()
        drag_ended_spy = Mock()
        
        handler.elementMoved.connect(element_moved_spy)
        handler.elementCopied.connect(element_copied_spy)
        handler.dragStarted.connect(drag_started_spy)
        handler.dragEnded.connect(drag_ended_spy)
        
        # Test that signals can be connected (basic functionality test)
        assert handler.elementMoved is not None
        assert handler.elementCopied is not None
        assert handler.dragStarted is not None
        assert handler.dragEnded is not None


class TestDragDropEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_drag_drop_with_none_values(self, mock_tree_view):
        """Test handling of None values."""
        handler = DragDropHandler(mock_tree_view)
        
        # Test with None index
        handler.start_drag(None)
        assert not handler.dragging
        
        # Test with invalid model
        mock_tree_view.model.return_value = None
        mock_index = Mock()
        mock_index.isValid.return_value = True
        handler.start_drag(mock_index)
        assert not handler.dragging
    
    def test_validator_with_none_elements(self):
        """Test validator with None elements."""
        node1 = TreeNode(None)
        node2 = TreeNode(None)
        
        can_drop, reason = DragDropValidator.can_drop_on_target(node1, node2)
        assert can_drop  # Should still be valid even with None elements
    
    def test_mime_data_with_empty_list(self):
        """Test MIME data creation with empty list."""
        mime_data = DragDropMimeData.create_element_mime_data([])
        
        # Should handle empty list gracefully
        assert mime_data is not None
        element_ids = DragDropMimeData.extract_element_ids(mime_data)
        assert element_ids == []
    
    def test_drop_indicator_with_invalid_index(self, mock_tree_view):
        """Test drop indicator with invalid index."""
        indicator = DropIndicator(mock_tree_view)
        
        mock_index = Mock()
        mock_index.isValid.return_value = False
        
        indicator.show_indicator(mock_index, 'above')
        
        assert not indicator.visible
    
    def test_handler_performance_with_large_selection(self, mock_tree_view):
        """Test handler performance with large number of elements."""
        handler = DragDropHandler(mock_tree_view)
        
        # Create large list of element IDs
        large_element_list = [f"element_{i}" for i in range(1000)]
        mime_data = DragDropMimeData.create_element_mime_data(large_element_list)
        
        # Test extraction performance
        extracted_ids = DragDropMimeData.extract_element_ids(mime_data)
        assert len(extracted_ids) == 1000
        assert extracted_ids[0] == "element_0"
        assert extracted_ids[-1] == "element_999"


if __name__ == "__main__":
    pytest.main([__file__])