"""
Tests for PointerTool implementation.

Comprehensive tests for pointer tool functionality including
precision mode, hit tolerance, and performance tracking.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QCursor

from src.torematrix.ui.viewer.tools.pointer import PointerTool
from src.torematrix.ui.viewer.tools.base import ToolState, SelectionResult
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, element_id="test_element", bounds=None, element_type="text", z_order=0):
        self.id = element_id
        self.element_type = element_type
        self.type = element_type
        self._bounds = bounds or Rectangle(10, 10, 50, 30)
        self.z_order = z_order
    
    def get_bounds(self):
        return self._bounds


class MockSpatialIndex:
    """Mock spatial index for testing."""
    
    def __init__(self):
        self.elements = []
    
    def query_point(self, point, tolerance=3):
        results = []
        for element in self.elements:
            bounds = element.get_bounds()
            # Expand bounds by tolerance
            if (bounds.x - tolerance <= point.x <= bounds.x + bounds.width + tolerance and
                bounds.y - tolerance <= point.y <= bounds.y + bounds.height + tolerance):
                results.append(element)
        return results
    
    def get_all_elements(self):
        return self.elements.copy()


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
    
    def is_selected(self, element):
        return element in self.selected_elements
    
    def toggle_element_selection(self, element):
        if self.is_selected(element):
            self.selected_elements.remove(element)
        else:
            self.selected_elements.append(element)


class MockOverlay:
    """Mock overlay for testing."""
    
    def __init__(self):
        self.cursor = QCursor()
        self.update_called = False
    
    def setCursor(self, cursor):
        self.cursor = cursor
    
    def update(self):
        self.update_called = True


@pytest.fixture
def mock_overlay():
    return MockOverlay()


@pytest.fixture
def mock_selection_manager():
    return MockSelectionManager()


@pytest.fixture
def mock_spatial_index():
    index = MockSpatialIndex()
    # Add test elements with different z-orders
    index.elements = [
        MockElement("element1", Rectangle(10, 10, 50, 30), "text", z_order=1),
        MockElement("element2", Rectangle(15, 15, 40, 20), "image", z_order=2),  # Overlapping, higher z-order
        MockElement("element3", Rectangle(100, 50, 40, 20), "table", z_order=0),
    ]
    return index


class TestPointerToolCreation:
    """Test PointerTool creation and initialization."""
    
    def test_pointer_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test basic pointer tool creation."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.tool_id == "pointer_tool"
        assert tool.name == "Pointer Tool"
        assert tool.description == "Precise point-based element selection"
        assert tool.get_current_state() == ToolState.INACTIVE
    
    def test_pointer_tool_default_configuration(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test default configuration values."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.get_hit_tolerance() == 3
        assert tool.get_precision_mode() == False
        assert tool.get_hover_delay() == 0.5


class TestPointerToolActivation:
    """Test PointerTool activation and deactivation."""
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_pointer_tool_activation(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool activation."""
        # Setup cursor manager mock
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.activate() == True
        assert tool.get_current_state() == ToolState.ACTIVE
    
    def test_pointer_tool_deactivation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool deactivation."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        tool.activate()
        tool.deactivate()
        
        assert tool.get_current_state() == ToolState.INACTIVE


class TestPointerToolMouseHandling:
    """Test PointerTool mouse event handling."""
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_mouse_press_on_element(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test mouse press on an element."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            # Press on element
            result = tool.handle_mouse_press(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            assert result == True
            # Should select the element with higher z-order (element2)
            assert len(mock_selection_manager.selected_elements) > 0
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_mouse_press_on_empty_area(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test mouse press on empty area."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(500, 500)):
            # Press on empty area
            result = tool.handle_mouse_press(
                QPoint(500, 500),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            assert result == True
            # Should clear selection
            assert len(mock_selection_manager.selected_elements) == 0
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_mouse_move_hover_detection(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test mouse move for hover detection."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Track signals
        highlighted_elements = []
        unhighlighted_elements = []
        
        tool.element_highlighted.connect(lambda el: highlighted_elements.append(el))
        tool.element_unhighlighted.connect(lambda el: unhighlighted_elements.append(el))
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            # Move over element
            tool.handle_mouse_move(
                QPoint(25, 25),
                Qt.KeyboardModifier.NoModifier
            )
            
            assert tool.get_current_state() == ToolState.HOVER
            assert len(highlighted_elements) > 0
        
        # Move away from element
        with patch.object(tool, '_screen_to_document', return_value=Point(500, 500)):
            tool.handle_mouse_move(
                QPoint(500, 500),
                Qt.KeyboardModifier.NoModifier
            )
            
            assert tool.get_current_state() == ToolState.ACTIVE
            assert len(unhighlighted_elements) > 0


class TestPointerToolDoubleClick:
    """Test PointerTool double-click functionality."""
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_double_click_selection(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test double-click selection of similar elements."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        # Add more text elements for double-click testing
        mock_spatial_index.elements.extend([
            MockElement("text1", Rectangle(200, 200, 50, 20), "text"),
            MockElement("text2", Rectangle(300, 300, 50, 20), "text"),
        ])
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            # First click
            tool.handle_mouse_press(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            tool.handle_mouse_release(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Quick second click (double-click)
            tool._last_click_time = time.time()
            tool.handle_mouse_press(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Should select similar elements (all text elements)
            text_elements = [el for el in mock_selection_manager.selected_elements 
                           if getattr(el, 'type', None) == 'text']
            assert len(text_elements) > 1


class TestPointerToolConfiguration:
    """Test PointerTool configuration options."""
    
    def test_precision_mode_configuration(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test precision mode configuration."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test precision mode toggle
        assert tool.get_precision_mode() == False
        
        precision_changed = []
        tool.precision_mode_changed.connect(lambda enabled: precision_changed.append(enabled))
        
        tool.set_precision_mode(True)
        assert tool.get_precision_mode() == True
        assert precision_changed == [True]
        
        tool.set_precision_mode(False)
        assert tool.get_precision_mode() == False
        assert precision_changed == [True, False]
    
    def test_hit_tolerance_configuration(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test hit tolerance configuration."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test hit tolerance
        assert tool.get_hit_tolerance() == 3
        
        tool.set_hit_tolerance(5)
        assert tool.get_hit_tolerance() == 5
        
        # Test bounds
        tool.set_hit_tolerance(15)  # Should be clamped to 10
        assert tool.get_hit_tolerance() == 10
        
        tool.set_hit_tolerance(0)   # Should be clamped to 1
        assert tool.get_hit_tolerance() == 1
    
    def test_hover_delay_configuration(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test hover delay configuration."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test hover delay
        assert tool.get_hover_delay() == 0.5
        
        tool.set_hover_delay(1.0)
        assert tool.get_hover_delay() == 1.0
        
        tool.set_hover_delay(-1.0)  # Should be clamped to 0
        assert tool.get_hover_delay() == 0.0


class TestPointerToolKeyboardHandling:
    """Test PointerTool keyboard event handling."""
    
    def test_precision_mode_key_toggle(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test precision mode toggle with 'P' key."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Test 'P' key for precision mode
        assert tool.get_precision_mode() == False
        
        result = tool.handle_key_press(ord('P'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_precision_mode() == True
        
        result = tool.handle_key_press(ord('P'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_precision_mode() == False
    
    def test_hit_tolerance_keys(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test hit tolerance adjustment with +/- keys."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        initial_tolerance = tool.get_hit_tolerance()
        
        # Test '+' key
        result = tool.handle_key_press(ord('+'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_hit_tolerance() == initial_tolerance + 1
        
        # Test '-' key
        result = tool.handle_key_press(ord('-'), Qt.KeyboardModifier.NoModifier)
        assert result == True
        assert tool.get_hit_tolerance() == initial_tolerance
    
    def test_escape_key_clear_selection(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test Escape key to clear selection."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Add some selection
        mock_selection_manager.set_selection([MockElement("test")])
        assert len(mock_selection_manager.selected_elements) > 0
        
        # Press Escape
        result = tool.handle_key_press(0x1000000, Qt.KeyboardModifier.NoModifier)  # Qt::Key_Escape
        assert result == True
        assert len(mock_selection_manager.selected_elements) == 0


class TestPointerToolPerformance:
    """Test PointerTool performance tracking."""
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_performance_metrics_tracking(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test performance metrics collection."""
        # Setup mocks
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Perform some operations to generate metrics
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            # Hover operations
            for i in range(5):
                tool.handle_mouse_move(
                    QPoint(25 + i, 25 + i),
                    Qt.KeyboardModifier.NoModifier
                )
            
            # Selection operations
            for i in range(3):
                tool.handle_mouse_press(
                    QPoint(25 + i, 25 + i),
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
        
        # Get metrics
        metrics = tool.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert "tool_type" in metrics
        assert metrics["tool_type"] == "pointer_tool"
        
        assert "hover_response" in metrics
        hover_metrics = metrics["hover_response"]
        assert hover_metrics["samples"] >= 5
        assert "average_ms" in hover_metrics
        assert "max_ms" in hover_metrics
        
        assert "selection_response" in metrics
        selection_metrics = metrics["selection_response"]
        assert selection_metrics["samples"] >= 3
        
        assert "configuration" in metrics
        config = metrics["configuration"]
        assert "hit_tolerance" in config
        assert "precision_mode" in config
    
    def test_performance_metrics_reset(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test performance metrics reset."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Add some fake performance data
        tool._hover_response_times = [1.0, 2.0, 3.0]
        tool._selection_response_times = [5.0, 6.0]
        
        # Verify data exists
        metrics = tool.get_performance_metrics()
        assert metrics["hover_response"]["samples"] == 3
        assert metrics["selection_response"]["samples"] == 2
        
        # Reset metrics
        tool.reset_performance_metrics()
        
        # Verify data cleared
        new_metrics = tool.get_performance_metrics()
        assert new_metrics["hover_response"]["samples"] == 0
        assert new_metrics["selection_response"]["samples"] == 0


class TestPointerToolSelectionHistory:
    """Test PointerTool selection history functionality."""
    
    def test_selection_history_tracking(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test selection history tracking."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Create test elements
        element1 = MockElement("el1")
        element2 = MockElement("el2")
        element3 = MockElement("el3")
        
        # Add to history
        tool._add_to_selection_history(element1)
        tool._add_to_selection_history(element2)
        tool._add_to_selection_history(element3)
        
        history = tool.get_selection_history()
        assert len(history) == 3
        assert history[0] == element3  # Most recent first
        assert history[1] == element2
        assert history[2] == element1
    
    def test_selection_history_deduplication(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test selection history deduplication."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        element1 = MockElement("el1")
        element2 = MockElement("el2")
        
        # Add same element multiple times
        tool._add_to_selection_history(element1)
        tool._add_to_selection_history(element2)
        tool._add_to_selection_history(element1)  # Should move to front
        
        history = tool.get_selection_history()
        assert len(history) == 2
        assert history[0] == element1  # Most recent
        assert history[1] == element2
    
    def test_selection_history_limit(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test selection history size limit."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Add more than limit (20)
        for i in range(25):
            element = MockElement(f"el{i}")
            tool._add_to_selection_history(element)
        
        history = tool.get_selection_history()
        assert len(history) == 20  # Should be limited to 20
    
    def test_clear_selection_history(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test clearing selection history."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Add some history
        tool._add_to_selection_history(MockElement("el1"))
        tool._add_to_selection_history(MockElement("el2"))
        
        assert len(tool.get_selection_history()) == 2
        
        # Clear history
        tool.clear_selection_history()
        
        assert len(tool.get_selection_history()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])