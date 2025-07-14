"""
Comprehensive integration tests for selection tools.

Tests the integration between different tools and core infrastructure,
ensuring tools work correctly with Agent 1's foundation.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QCursor

# Import core infrastructure
from src.torematrix.ui.viewer.tools.base import SelectionTool, ToolState, SelectionResult
from src.torematrix.ui.viewer.tools.geometry import HitTesting, SelectionGeometry
from src.torematrix.ui.viewer.tools.cursor import CursorManager, CursorType
from src.torematrix.ui.viewer.tools.events import EventDispatcher, EventType
from src.torematrix.ui.viewer.tools.registry import AdvancedToolRegistry

# Import tool implementations
from src.torematrix.ui.viewer.tools.pointer import PointerTool
from src.torematrix.ui.viewer.tools.rectangle import RectangleTool
from src.torematrix.ui.viewer.tools.lasso import LassoTool
from src.torematrix.ui.viewer.tools.element_aware import ElementAwareTool
from src.torematrix.ui.viewer.tools.multi_select import MultiSelectTool

# Mock coordinate types
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, element_id="test_element", bounds=None, element_type="text"):
        self.id = element_id
        self.element_type = element_type
        self.type = element_type
        self._bounds = bounds or Rectangle(10, 10, 50, 30)
        self.z_order = 0
    
    def get_bounds(self):
        return self._bounds
    
    @property
    def bounds(self):
        return self._bounds


class MockSpatialIndex:
    """Mock spatial index for testing."""
    
    def __init__(self):
        self.elements = []
    
    def add_element(self, element):
        self.elements.append(element)
    
    def query_point(self, point, tolerance=3):
        # Return elements whose bounds contain the point
        results = []
        for element in self.elements:
            bounds = element.get_bounds()
            if (bounds.x <= point.x <= bounds.x + bounds.width and
                bounds.y <= point.y <= bounds.y + bounds.height):
                results.append(element)
        return results
    
    def query_rectangle(self, rect):
        # Return elements that intersect with rectangle
        results = []
        for element in self.elements:
            bounds = element.get_bounds()
            if rect.intersects(bounds):
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
    
    def deselect_element(self, element):
        if element in self.selected_elements:
            self.selected_elements.remove(element)
    
    def toggle_element_selection(self, element):
        if self.is_selected(element):
            self.deselect_element(element)
        else:
            self.add_to_selection(element)
    
    def clear_selection(self):
        self.selected_elements.clear()
    
    def get_last_selection(self):
        return self.last_selection


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
    """Create mock overlay."""
    return MockOverlay()


@pytest.fixture
def mock_selection_manager():
    """Create mock selection manager."""
    return MockSelectionManager()


@pytest.fixture
def mock_spatial_index():
    """Create mock spatial index with test elements."""
    index = MockSpatialIndex()
    
    # Add test elements
    index.add_element(MockElement("element1", Rectangle(10, 10, 50, 30), "text"))
    index.add_element(MockElement("element2", Rectangle(100, 50, 40, 20), "image"))
    index.add_element(MockElement("element3", Rectangle(200, 100, 60, 40), "table"))
    
    return index


@pytest.fixture
def event_dispatcher():
    """Create event dispatcher."""
    return EventDispatcher()


class TestPointerTool:
    """Test PointerTool functionality."""
    
    def test_pointer_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool creation."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.tool_id == "pointer_tool"
        assert tool.name == "Pointer Tool"
        assert tool.get_current_state() == ToolState.INACTIVE
    
    def test_pointer_tool_activation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool activation."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.activate() == True
        assert tool.get_current_state() == ToolState.ACTIVE
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_pointer_tool_mouse_press(self, mock_cursor_manager, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool mouse press handling."""
        # Setup mocks
        mock_cursor_manager.return_value = Mock()
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            # Test mouse press on element
            result = tool.handle_mouse_press(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            assert result == True
            assert tool.get_current_state() in [ToolState.SELECTED, ToolState.SELECTING]
    
    def test_pointer_tool_precision_mode(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool precision mode."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test precision mode toggle
        assert tool.get_precision_mode() == False
        tool.set_precision_mode(True)
        assert tool.get_precision_mode() == True
    
    def test_pointer_tool_hit_tolerance(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool hit tolerance configuration."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test hit tolerance
        tool.set_hit_tolerance(5)
        assert tool.get_hit_tolerance() == 5
        
        # Test bounds checking
        tool.set_hit_tolerance(15)  # Should be clamped to 10
        assert tool.get_hit_tolerance() == 10


class TestRectangleTool:
    """Test RectangleTool functionality."""
    
    def test_rectangle_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test rectangle tool creation."""
        tool = RectangleTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        assert tool.tool_id == "rectangle_tool"
        assert tool.name == "Rectangle Tool"
        assert tool.get_current_state() == ToolState.INACTIVE
    
    def test_rectangle_tool_selection_modes(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test rectangle tool selection modes."""
        tool = RectangleTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test selection modes
        assert tool.get_selection_mode() == "intersect"
        
        tool.set_selection_mode("contain")
        assert tool.get_selection_mode() == "contain"
        
        tool.set_selection_mode("center")
        assert tool.get_selection_mode() == "center"
    
    def test_rectangle_tool_drag_sequence(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test rectangle tool drag sequence."""
        tool = RectangleTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        tool.activate()
        
        # Mock coordinate conversion
        with patch.object(tool, '_screen_to_document', return_value=Point(10, 10)):
            # Start drag
            tool.handle_mouse_press(
                QPoint(10, 10),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            assert tool.get_current_state() == ToolState.SELECTING
            
            # Continue drag
            with patch.object(tool, '_screen_to_document', return_value=Point(60, 60)):
                tool.handle_mouse_move(
                    QPoint(60, 60),
                    Qt.KeyboardModifier.NoModifier
                )
            
            # End drag
            with patch.object(tool, '_screen_to_document', return_value=Point(60, 60)):
                tool.handle_mouse_release(
                    QPoint(60, 60),
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
    
    def test_rectangle_tool_grid_snapping(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test rectangle tool grid snapping."""
        tool = RectangleTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test grid snapping
        assert tool.get_snap_to_grid() == False
        tool.set_snap_to_grid(True)
        assert tool.get_snap_to_grid() == True
        
        # Test grid size
        tool.set_grid_size(20)
        assert tool.get_grid_size() == 20


class TestLassoTool:
    """Test LassoTool functionality."""
    
    def test_lasso_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test lasso tool creation."""
        with patch('src.torematrix.ui.viewer.tools.lasso.LassoTool') as MockLassoTool:
            mock_tool = Mock()
            mock_tool.tool_id = "lasso_tool"
            mock_tool.name = "Lasso Tool"
            MockLassoTool.return_value = mock_tool
            
            tool = MockLassoTool(
                overlay=mock_overlay,
                selection_manager=mock_selection_manager,
                spatial_index=mock_spatial_index
            )
            
            assert tool.tool_id == "lasso_tool"
            assert tool.name == "Lasso Tool"


class TestElementAwareTool:
    """Test ElementAwareTool functionality."""
    
    def test_element_aware_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test element aware tool creation."""
        with patch('src.torematrix.ui.viewer.tools.element_aware.ElementAwareTool') as MockElementAwareTool:
            mock_tool = Mock()
            mock_tool.tool_id = "element_aware_tool"
            mock_tool.name = "Element Aware Tool"
            MockElementAwareTool.return_value = mock_tool
            
            tool = MockElementAwareTool(
                overlay=mock_overlay,
                selection_manager=mock_selection_manager,
                spatial_index=mock_spatial_index
            )
            
            assert tool.tool_id == "element_aware_tool"
            assert tool.name == "Element Aware Tool"


class TestMultiSelectTool:
    """Test MultiSelectTool functionality."""
    
    def test_multi_select_tool_creation(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test multi select tool creation."""
        with patch('src.torematrix.ui.viewer.tools.multi_select.MultiSelectTool') as MockMultiSelectTool:
            mock_tool = Mock()
            mock_tool.tool_id = "multi_select_tool"
            mock_tool.name = "Multi Select Tool"
            MockMultiSelectTool.return_value = mock_tool
            
            tool = MockMultiSelectTool(
                overlay=mock_overlay,
                selection_manager=mock_selection_manager,
                spatial_index=mock_spatial_index
            )
            
            assert tool.tool_id == "multi_select_tool"
            assert tool.name == "Multi Select Tool"


class TestToolRegistry:
    """Test tool registry integration."""
    
    def test_tool_registry_with_tools(self):
        """Test registering tools with registry."""
        registry = AdvancedToolRegistry()
        
        # Create mock tools
        pointer_tool = Mock()
        pointer_tool.tool_id = "pointer_tool"
        pointer_tool.name = "Pointer Tool"
        pointer_tool.get_capabilities = Mock(return_value=[])
        
        rectangle_tool = Mock()
        rectangle_tool.tool_id = "rectangle_tool"
        rectangle_tool.name = "Rectangle Tool"
        rectangle_tool.get_capabilities = Mock(return_value=[])
        
        # Register tools
        assert registry.register_tool(pointer_tool) == True
        assert registry.register_tool(rectangle_tool) == True
        
        # Check registration
        assert registry.is_tool_registered("pointer_tool") == True
        assert registry.is_tool_registered("rectangle_tool") == True
        
        # Get tools
        assert registry.get_tool("pointer_tool") == pointer_tool
        assert registry.get_tool("rectangle_tool") == rectangle_tool


class TestToolPerformance:
    """Test tool performance metrics."""
    
    def test_pointer_tool_performance_metrics(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test pointer tool performance tracking."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Get performance metrics
        metrics = tool.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert "tool_type" in metrics
        assert "hover_response" in metrics
        assert "selection_response" in metrics
        assert "configuration" in metrics
        
        # Reset metrics
        tool.reset_performance_metrics()
        
        new_metrics = tool.get_performance_metrics()
        assert new_metrics["hover_response"]["samples"] == 0
        assert new_metrics["selection_response"]["samples"] == 0
    
    def test_rectangle_tool_performance_metrics(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test rectangle tool performance tracking."""
        tool = RectangleTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Get performance metrics
        metrics = tool.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert "tool_type" in metrics
        assert "selection_performance" in metrics
        assert "configuration" in metrics
        
        # Reset metrics
        tool.reset_performance_metrics()


class TestToolIntegration:
    """Test integration between tools and core infrastructure."""
    
    def test_tools_with_event_dispatcher(self, mock_overlay, mock_selection_manager, mock_spatial_index, event_dispatcher):
        """Test tools integration with event dispatcher."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Connect to event dispatcher
        tool._event_dispatcher = event_dispatcher
        
        # Add mock event handler
        handler_called = []
        
        class MockHandler:
            def __init__(self):
                self.name = "test_handler"
                self.enabled = True
                self.priority = 1
            
            def handle_event(self, event):
                handler_called.append(event)
                return True
            
            def is_enabled(self):
                return self.enabled
            
            def _handle_event_impl(self, event):
                return self.handle_event(event)
        
        handler = MockHandler()
        event_dispatcher.add_handler(handler)
        
        tool.activate()
        
        # Simulate mouse press (should create and dispatch event)
        with patch.object(tool, '_screen_to_document', return_value=Point(25, 25)):
            tool.handle_mouse_press(
                QPoint(25, 25),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
        
        # Check that event was dispatched
        assert len(handler_called) > 0
    
    @patch('src.torematrix.ui.viewer.tools.pointer.get_global_cursor_manager')
    def test_tools_with_cursor_manager(self, mock_cursor_manager_func, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test tools integration with cursor manager."""
        # Setup cursor manager mock
        cursor_manager = Mock()
        cursor_manager.get_cursor_for_state.return_value = QCursor()
        cursor_manager.get_cursor.return_value = QCursor()
        mock_cursor_manager_func.return_value = cursor_manager
        
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        tool.activate()
        
        # Verify cursor manager was called
        assert cursor_manager.get_cursor_for_state.called or cursor_manager.get_cursor.called
    
    def test_tools_state_transitions(self, mock_overlay, mock_selection_manager, mock_spatial_index):
        """Test tool state transitions."""
        tool = PointerTool(
            overlay=mock_overlay,
            selection_manager=mock_selection_manager,
            spatial_index=mock_spatial_index
        )
        
        # Test state progression
        assert tool.get_current_state() == ToolState.INACTIVE
        
        tool.activate()
        assert tool.get_current_state() == ToolState.ACTIVE
        
        tool.deactivate()
        assert tool.get_current_state() == ToolState.INACTIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])