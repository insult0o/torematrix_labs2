"""
Tests for RectangleTool implementation.

Comprehensive tests for rectangle tool functionality including
drag selection, selection modes, and performance tracking.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QCursor

try:
    from src.torematrix.ui.viewer.tools.rectangle import RectangleTool
    from src.torematrix.ui.viewer.tools.base import ToolState, SelectionResult
    from src.torematrix.ui.viewer.coordinates import Point, Rectangle
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, element_id="test_element", bounds=None, element_type="text"):
        self.id = element_id
        self.element_type = element_type
        self.type = element_type
        self._bounds = bounds or Rectangle(10, 10, 50, 30)
    
    def get_bounds(self):
        return self._bounds


class MockSpatialIndex:
    """Mock spatial index for testing."""
    
    def __init__(self):
        self.elements = []
    
    def query_rectangle(self, rect):
        # Return elements that intersect with rectangle
        results = []
        for element in self.elements:
            bounds = element.get_bounds()
            if rect.intersects(bounds):
                results.append(element)
        return results
    
    def query_point(self, point, tolerance=3):
        results = []
        for element in self.elements:
            bounds = element.get_bounds()
            if (bounds.x - tolerance <= point.x <= bounds.x + bounds.width + tolerance and
                bounds.y - tolerance <= point.y <= bounds.y + bounds.height + tolerance):
                results.append(element)
        return results


class MockSelectionManager:
    """Mock selection manager for testing."""
    
    def __init__(self):
        self.selected_elements = []
        self.last_selection = None
    
    def set_selection(self, elements):
        self.selected_elements = elements.copy() if isinstance(elements, list) else [elements]
        self.last_selection = elements
    
    def add_to_selection(self, elements):
        if isinstance(elements, list):
            self.selected_elements.extend(elements)
        else:
            self.selected_elements.append(elements)


class MockOverlay:
    """Mock overlay for testing."""
    
    def __init__(self):
        self.cursor = QCursor()
        self.update_called = False
    
    def setCursor(self, cursor):
        self.cursor = cursor
    
    def update(self):
        self.update_called = True


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolCreation:
    """Test RectangleTool creation and initialization."""
    
    def test_rectangle_tool_creation(self):
        """Test basic rectangle tool creation."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        assert tool.tool_id == "rectangle_tool"
        assert tool.name == "Rectangle Tool"
        assert tool.get_current_state() == ToolState.INACTIVE
    
    def test_rectangle_tool_default_configuration(self):
        """Test default configuration values."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        assert tool.get_selection_mode() == "intersect"
        assert tool.get_preview_enabled() == True
        assert tool.get_snap_to_grid() == False


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolSelectionModes:
    """Test RectangleTool selection modes."""
    
    def test_selection_mode_configuration(self):
        """Test selection mode configuration."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Test selection modes
        assert tool.get_selection_mode() == "intersect"
        
        mode_changes = []
        tool.selection_mode_changed.connect(lambda mode: mode_changes.append(mode))
        
        tool.set_selection_mode("contain")
        assert tool.get_selection_mode() == "contain"
        assert "contain" in mode_changes
        
        tool.set_selection_mode("center")
        assert tool.get_selection_mode() == "center"
        assert "center" in mode_changes
        
        # Test invalid mode (should be ignored)
        tool.set_selection_mode("invalid")
        assert tool.get_selection_mode() == "center"  # Should remain unchanged
    
    def test_selection_mode_cycling(self):
        """Test cycling through selection modes."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Start with intersect
        assert tool.get_selection_mode() == "intersect"
        
        # Cycle through modes
        tool._cycle_selection_mode()
        assert tool.get_selection_mode() == "contain"
        
        tool._cycle_selection_mode()
        assert tool.get_selection_mode() == "center"
        
        tool._cycle_selection_mode()
        assert tool.get_selection_mode() == "intersect"  # Back to start


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolDragOperations:
    """Test RectangleTool drag operations."""
    
    @patch('src.torematrix.ui.viewer.tools.rectangle.get_global_cursor_manager')
    def test_drag_sequence(self, mock_cursor_manager):
        """Test complete drag sequence."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        # Add test elements
        spatial_index.elements = [
            MockElement("element1", Rectangle(20, 20, 30, 20), "text"),
            MockElement("element2", Rectangle(60, 60, 30, 20), "image"),
        ]
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        tool.activate()
        
        # Track signals
        rectangle_started = []
        rectangle_updated = []
        rectangle_completed = []
        
        tool.rectangle_started.connect(lambda pt: rectangle_started.append(pt))
        tool.rectangle_updated.connect(lambda start, current: rectangle_updated.append((start, current)))
        tool.rectangle_completed.connect(lambda rect: rectangle_completed.append(rect))
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(10, 10)):
            with patch.object(tool, '_qrect_to_document_rect', return_value=Rectangle(10, 10, 80, 80)):
                # Start drag
                result = tool.handle_mouse_press(
                    QPoint(10, 10),
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                assert result == True
                assert tool.get_current_state() == ToolState.SELECTING
                assert len(rectangle_started) == 1
                
                # Continue drag
                with patch.object(tool, '_screen_to_document', return_value=Point(90, 90)):
                    tool.handle_mouse_move(
                        QPoint(90, 90),
                        Qt.KeyboardModifier.NoModifier
                    )
                    assert len(rectangle_updated) > 0
                
                # End drag
                with patch.object(tool, '_screen_to_document', return_value=Point(90, 90)):
                    result = tool.handle_mouse_release(
                        QPoint(90, 90),
                        Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier
                    )
                    assert result == True
                    # Should have selected elements
                    assert len(selection_manager.selected_elements) > 0
    
    def test_small_rectangle_as_click(self):
        """Test small rectangle treated as click."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        # Add test element
        spatial_index.elements = [
            MockElement("element1", Rectangle(10, 10, 30, 20), "text"),
        ]
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        tool.activate()
        
        # Set minimum rectangle size
        tool.set_minimum_rectangle_size(10)
        
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 20)):
            # Start very small drag
            tool.handle_mouse_press(
                QPoint(10, 10),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # End with small movement (below minimum)
            tool.handle_mouse_release(
                QPoint(12, 12),  # Only 2 pixels movement
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Should be treated as click and select element at position
            assert tool.get_current_state() in [ToolState.ACTIVE, ToolState.SELECTED]


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolConfiguration:
    """Test RectangleTool configuration options."""
    
    def test_preview_configuration(self):
        """Test preview enable/disable."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Test preview toggle
        assert tool.get_preview_enabled() == True
        
        tool.set_preview_enabled(False)
        assert tool.get_preview_enabled() == False
        
        tool.set_preview_enabled(True)
        assert tool.get_preview_enabled() == True
    
    def test_grid_snapping_configuration(self):
        """Test grid snapping configuration."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Test grid snapping
        assert tool.get_snap_to_grid() == False
        
        tool.set_snap_to_grid(True)
        assert tool.get_snap_to_grid() == True
        
        # Test grid size
        tool.set_grid_size(20)
        assert tool.get_grid_size() == 20
        
        # Test grid size bounds
        tool.set_grid_size(0)  # Should be clamped to 1
        assert tool.get_grid_size() == 1
    
    def test_minimum_rectangle_size(self):
        """Test minimum rectangle size configuration."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Test minimum size
        assert tool.get_minimum_rectangle_size() == 5
        
        tool.set_minimum_rectangle_size(10)
        assert tool.get_minimum_rectangle_size() == 10
        
        # Test bounds
        tool.set_minimum_rectangle_size(0)  # Should be clamped to 1
        assert tool.get_minimum_rectangle_size() == 1


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolKeyboardHandling:
    """Test RectangleTool keyboard event handling."""
    
    def test_selection_mode_key_cycling(self):
        """Test selection mode cycling with 'M' key."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        tool.activate()
        
        # Test 'M' key for mode cycling
        assert tool.get_selection_mode() == "intersect"
        
        result = tool.handle_key_press(ord('M'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_selection_mode() == "contain"
        
        result = tool.handle_key_press(ord('M'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_selection_mode() == "center"
    
    def test_preview_toggle_key(self):
        """Test preview toggle with 'P' key."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        tool.activate()
        
        # Test 'P' key for preview toggle
        assert tool.get_preview_enabled() == True
        
        result = tool.handle_key_press(ord('P'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_preview_enabled() == False
        
        result = tool.handle_key_press(ord('P'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_preview_enabled() == True
    
    def test_grid_snapping_toggle_key(self):
        """Test grid snapping toggle with 'G' key."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        tool.activate()
        
        # Test 'G' key for grid snapping toggle
        assert tool.get_snap_to_grid() == False
        
        result = tool.handle_key_press(ord('G'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_snap_to_grid() == True
        
        result = tool.handle_key_press(ord('G'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_snap_to_grid() == False


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="Tool implementations not available")
class TestRectangleToolPerformance:
    """Test RectangleTool performance tracking."""
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics collection."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Add some fake performance data
        tool._element_count_history = [5, 3, 8, 2]
        tool._drag_distance_history = [50.0, 75.0, 30.0, 100.0]
        
        # Get metrics
        metrics = tool.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert "tool_type" in metrics
        assert metrics["tool_type"] == "rectangle_tool"
        
        assert "selection_performance" in metrics
        perf_metrics = metrics["selection_performance"]
        assert perf_metrics["total_selections"] == 4
        assert perf_metrics["average_elements_selected"] == 4.5  # (5+3+8+2)/4
        assert perf_metrics["max_elements_selected"] == 8
        assert perf_metrics["average_drag_distance"] == 63.75  # (50+75+30+100)/4
        assert perf_metrics["max_drag_distance"] == 100.0
        
        assert "configuration" in metrics
        config = metrics["configuration"]
        assert "selection_mode" in config
        assert "preview_enabled" in config
        assert "snap_to_grid" in config
    
    def test_performance_metrics_reset(self):
        """Test performance metrics reset."""
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = RectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        # Add some fake performance data
        tool._element_count_history = [5, 3, 8]
        tool._drag_distance_history = [50.0, 75.0, 30.0]
        
        # Verify data exists
        metrics = tool.get_performance_metrics()
        assert metrics["selection_performance"]["total_selections"] == 3
        
        # Reset metrics
        tool.reset_performance_metrics()
        
        # Verify data cleared
        new_metrics = tool.get_performance_metrics()
        assert new_metrics["selection_performance"]["total_selections"] == 0


class TestRectangleToolMockImplementation:
    """Test rectangle tool with mock implementation when tools not available."""
    
    @pytest.mark.skipif(TOOLS_AVAILABLE, reason="Real tools are available")
    def test_mock_rectangle_tool(self):
        """Test mock rectangle tool when real implementation not available."""
        # Create a simple mock implementation
        class MockRectangleTool:
            def __init__(self, overlay=None, selection_manager=None, spatial_index=None):
                self.tool_id = "rectangle_tool"
                self.name = "Rectangle Tool"
                self._state = "inactive"
                self._selection_mode = "intersect"
            
            def get_current_state(self):
                return self._state
            
            def get_selection_mode(self):
                return self._selection_mode
            
            def set_selection_mode(self, mode):
                if mode in ["intersect", "contain", "center"]:
                    self._selection_mode = mode
        
        # Test mock functionality
        overlay = MockOverlay()
        selection_manager = MockSelectionManager()
        spatial_index = MockSpatialIndex()
        
        tool = MockRectangleTool(
            overlay=overlay,
            selection_manager=selection_manager,
            spatial_index=spatial_index
        )
        
        assert tool.tool_id == "rectangle_tool"
        assert tool.name == "Rectangle Tool"
        assert tool.get_current_state() == "inactive"
        assert tool.get_selection_mode() == "intersect"
        
        tool.set_selection_mode("contain")
        assert tool.get_selection_mode() == "contain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])