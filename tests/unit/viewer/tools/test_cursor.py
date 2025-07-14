"""
Tests for cursor management system.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QCursor, QPixmap, QColor

from src.torematrix.ui.viewer.tools.base import ToolState
from src.torematrix.ui.viewer.tools.cursor import (
    CursorType, CursorTheme, CursorManager, CursorStack,
    get_global_cursor_manager, set_global_cursor_theme
)


class TestCursorType:
    """Test CursorType enum."""
    
    def test_cursor_types_exist(self):
        """Test that all cursor types exist."""
        assert CursorType.ARROW.value == "arrow"
        assert CursorType.CROSS.value == "cross"
        assert CursorType.HAND.value == "hand"
        assert CursorType.CLOSED_HAND.value == "closed_hand"
        assert CursorType.POINTER.value == "pointer"
        assert CursorType.CROSSHAIR.value == "crosshair"
        assert CursorType.RESIZE_HORIZONTAL.value == "resize_horizontal"
        assert CursorType.RESIZE_VERTICAL.value == "resize_vertical"
        assert CursorType.RESIZE_DIAGONAL_1.value == "resize_diagonal_1"
        assert CursorType.RESIZE_DIAGONAL_2.value == "resize_diagonal_2"
        assert CursorType.MOVE.value == "move"
        assert CursorType.CUSTOM.value == "custom"


class TestCursorTheme:
    """Test CursorTheme enum."""
    
    def test_cursor_themes_exist(self):
        """Test that all cursor themes exist."""
        assert CursorTheme.SYSTEM.value == "system"
        assert CursorTheme.DARK.value == "dark"
        assert CursorTheme.LIGHT.value == "light"
        assert CursorTheme.HIGH_CONTRAST.value == "high_contrast"
        assert CursorTheme.COLORFUL.value == "colorful"


class TestCursorManager:
    """Test CursorManager class."""
    
    def test_cursor_manager_creation(self):
        """Test cursor manager creation."""
        manager = CursorManager()
        
        assert manager.get_theme() == CursorTheme.SYSTEM
        assert manager.get_cursor_size() == 16
        assert len(manager.get_available_cursors()) > 0
    
    def test_cursor_manager_with_theme(self):
        """Test cursor manager creation with specific theme."""
        manager = CursorManager(CursorTheme.DARK)
        
        assert manager.get_theme() == CursorTheme.DARK
    
    def test_system_cursors(self):
        """Test system cursor creation."""
        manager = CursorManager()
        
        # Test basic cursor types
        arrow_cursor = manager.get_cursor(CursorType.ARROW.value)
        assert isinstance(arrow_cursor, QCursor)
        
        cross_cursor = manager.get_cursor(CursorType.CROSS.value)
        assert isinstance(cross_cursor, QCursor)
        
        hand_cursor = manager.get_cursor(CursorType.HAND.value)
        assert isinstance(hand_cursor, QCursor)
    
    def test_custom_cursors(self):
        """Test custom cursor creation."""
        manager = CursorManager(CursorTheme.DARK)
        
        # These should exist for non-system themes
        selection_cursor = manager.get_cursor("selection")
        assert isinstance(selection_cursor, QCursor)
        
        precision_cursor = manager.get_cursor("precision")
        assert isinstance(precision_cursor, QCursor)
    
    def test_cursor_for_state(self):
        """Test getting cursor for tool state."""
        manager = CursorManager()
        
        # Test different states
        inactive_cursor = manager.get_cursor_for_state(ToolState.INACTIVE)
        assert isinstance(inactive_cursor, QCursor)
        
        active_cursor = manager.get_cursor_for_state(ToolState.ACTIVE)
        assert isinstance(active_cursor, QCursor)
        
        selecting_cursor = manager.get_cursor_for_state(ToolState.SELECTING)
        assert isinstance(selecting_cursor, QCursor)
        
        # Cursors should be different for different states
        assert inactive_cursor != active_cursor
    
    def test_custom_cursor_creation(self):
        """Test creating custom cursors."""
        manager = CursorManager()
        
        # Test text cursor
        text_cursor = manager.create_text_cursor("Test")
        assert isinstance(text_cursor, QCursor)
        
        # Test progress cursor
        progress_cursor = manager.create_progress_cursor(0.5)
        assert isinstance(progress_cursor, QCursor)
        
        # Test tool cursor
        tool_cursor = manager.create_tool_cursor("test_tool")
        assert isinstance(tool_cursor, QCursor)
    
    def test_cursor_caching(self):
        """Test cursor caching."""
        manager = CursorManager()
        
        # Get cursor twice
        cursor1 = manager.get_cursor(CursorType.ARROW.value)
        cursor2 = manager.get_cursor(CursorType.ARROW.value)
        
        # Should be the same object (cached)
        assert cursor1 is cursor2
    
    def test_set_custom_cursor(self):
        """Test setting custom cursor."""
        manager = CursorManager()
        
        custom_cursor = QCursor(Qt.CursorShape.WaitCursor)
        manager.set_cursor("custom_wait", custom_cursor)
        
        retrieved_cursor = manager.get_cursor("custom_wait")
        assert retrieved_cursor is custom_cursor
    
    def test_theme_change(self):
        """Test changing cursor theme."""
        manager = CursorManager(CursorTheme.SYSTEM)
        
        original_cursors = manager.get_available_cursors().copy()
        
        manager.set_theme(CursorTheme.DARK)
        
        assert manager.get_theme() == CursorTheme.DARK
        
        # Should have potentially different cursors
        new_cursors = manager.get_available_cursors()
        assert len(new_cursors) >= len(original_cursors)
    
    def test_cursor_size_change(self):
        """Test changing cursor size."""
        manager = CursorManager()
        
        original_size = manager.get_cursor_size()
        manager.set_cursor_size(24)
        
        assert manager.get_cursor_size() == 24
        assert manager.get_cursor_size() != original_size
    
    def test_cursor_size_limits(self):
        """Test cursor size limits."""
        manager = CursorManager()
        
        original_size = manager.get_cursor_size()
        
        # Too small
        manager.set_cursor_size(4)
        assert manager.get_cursor_size() == original_size  # Should not change
        
        # Too large
        manager.set_cursor_size(128)
        assert manager.get_cursor_size() == original_size  # Should not change
        
        # Valid size
        manager.set_cursor_size(32)
        assert manager.get_cursor_size() == 32
    
    def test_clear_cache(self):
        """Test clearing cursor cache."""
        manager = CursorManager()
        
        # Get some cursors to populate cache
        manager.get_cursor(CursorType.ARROW.value)
        manager.get_cursor(CursorType.CROSS.value)
        
        original_count = len(manager.get_available_cursors())
        
        manager.clear_cache()
        
        # Should still have cursors (recreated)
        new_count = len(manager.get_available_cursors())
        assert new_count >= len([t.value for t in CursorType if t != CursorType.CUSTOM])
    
    def test_nonexistent_cursor(self):
        """Test getting non-existent cursor."""
        manager = CursorManager()
        
        # Should return default arrow cursor
        cursor = manager.get_cursor("nonexistent_cursor")
        arrow_cursor = manager.get_cursor(CursorType.ARROW.value)
        
        assert cursor == arrow_cursor
    
    def test_tool_cursor_creation(self):
        """Test creating tool-specific cursors."""
        manager = CursorManager()
        
        # Test different tool types
        pointer_cursor = manager.create_tool_cursor("pointer_tool")
        assert isinstance(pointer_cursor, QCursor)
        
        rectangle_cursor = manager.create_tool_cursor("rectangle_tool")
        assert isinstance(rectangle_cursor, QCursor)
        
        lasso_cursor = manager.create_tool_cursor("lasso_tool")
        assert isinstance(lasso_cursor, QCursor)
        
        # Should be cached
        pointer_cursor2 = manager.create_tool_cursor("pointer_tool")
        assert pointer_cursor is pointer_cursor2
    
    @patch('os.path.exists')
    @patch('PyQt6.QtGui.QPixmap')
    def test_export_cursor(self, mock_pixmap_class, mock_exists):
        """Test exporting cursor to file."""
        manager = CursorManager()
        
        # Mock pixmap save
        mock_pixmap = Mock()
        mock_pixmap.save.return_value = True
        mock_pixmap.isNull.return_value = False
        
        with patch.object(manager._cursors[CursorType.ARROW.value], 'pixmap', return_value=mock_pixmap):
            success = manager.export_cursor(CursorType.ARROW.value, "/tmp/test_cursor.png")
            assert success == True
            mock_pixmap.save.assert_called_once_with("/tmp/test_cursor.png")
    
    @patch('os.path.exists')
    @patch('PyQt6.QtGui.QPixmap')
    def test_import_cursor(self, mock_pixmap_class, mock_exists):
        """Test importing cursor from file."""
        manager = CursorManager()
        
        mock_exists.return_value = True
        
        # Mock pixmap load
        mock_pixmap = Mock()
        mock_pixmap.isNull.return_value = False
        mock_pixmap_class.return_value = mock_pixmap
        
        success = manager.import_cursor("imported_cursor", "/tmp/test_cursor.png")
        assert success == True
        
        # Check cursor was added
        cursor = manager.get_cursor("imported_cursor")
        assert isinstance(cursor, QCursor)


class TestCursorStack:
    """Test CursorStack class."""
    
    def test_cursor_stack_creation(self):
        """Test cursor stack creation."""
        manager = CursorManager()
        stack = CursorStack(manager)
        
        assert stack.get_stack_depth() == 0
        assert stack.peek_cursor() is None
    
    def test_push_pop_cursor(self):
        """Test pushing and popping cursors."""
        manager = CursorManager()
        stack = CursorStack(manager)
        
        # Push cursor
        stack.push_cursor(CursorType.ARROW.value)
        assert stack.get_stack_depth() == 0  # First cursor doesn't increase depth
        assert stack.peek_cursor() == CursorType.ARROW.value
        
        # Push another cursor
        stack.push_cursor(CursorType.CROSS.value)
        assert stack.get_stack_depth() == 1
        assert stack.peek_cursor() == CursorType.CROSS.value
        
        # Pop cursor
        popped = stack.pop_cursor()
        assert popped == CursorType.ARROW.value
        assert stack.get_stack_depth() == 0
        assert stack.peek_cursor() == CursorType.ARROW.value
    
    def test_pop_empty_stack(self):
        """Test popping from empty stack."""
        manager = CursorManager()
        stack = CursorStack(manager)
        
        popped = stack.pop_cursor()
        assert popped is None
    
    def test_clear_stack(self):
        """Test clearing cursor stack."""
        manager = CursorManager()
        stack = CursorStack(manager)
        
        stack.push_cursor(CursorType.ARROW.value)
        stack.push_cursor(CursorType.CROSS.value)
        stack.push_cursor(CursorType.HAND.value)
        
        assert stack.get_stack_depth() == 2
        
        stack.clear_stack()
        
        assert stack.get_stack_depth() == 0
        assert stack.peek_cursor() is None
    
    def test_get_current_qcursor(self):
        """Test getting current QCursor."""
        manager = CursorManager()
        stack = CursorStack(manager)
        
        # Empty stack should return arrow cursor
        cursor = stack.get_current_qcursor()
        assert isinstance(cursor, QCursor)
        
        # With cursor on stack
        stack.push_cursor(CursorType.CROSS.value)
        cursor = stack.get_current_qcursor()
        assert isinstance(cursor, QCursor)


class TestGlobalCursorManager:
    """Test global cursor manager functions."""
    
    def test_get_global_cursor_manager(self):
        """Test getting global cursor manager."""
        manager1 = get_global_cursor_manager()
        manager2 = get_global_cursor_manager()
        
        # Should be same instance
        assert manager1 is manager2
        assert isinstance(manager1, CursorManager)
    
    def test_set_global_cursor_theme(self):
        """Test setting global cursor theme."""
        manager = get_global_cursor_manager()
        original_theme = manager.get_theme()
        
        new_theme = CursorTheme.DARK if original_theme != CursorTheme.DARK else CursorTheme.LIGHT
        set_global_cursor_theme(new_theme)
        
        assert manager.get_theme() == new_theme
    
    def test_global_manager_persistence(self):
        """Test that global manager persists across calls."""
        manager = get_global_cursor_manager()
        manager.set_cursor("test_cursor", QCursor(Qt.CursorShape.WaitCursor))
        
        # Get manager again
        manager2 = get_global_cursor_manager()
        
        # Should have the custom cursor
        cursor = manager2.get_cursor("test_cursor")
        assert isinstance(cursor, QCursor)


if __name__ == "__main__":
    pytest.main([__file__])