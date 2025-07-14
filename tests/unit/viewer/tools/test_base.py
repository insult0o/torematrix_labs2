"""
Tests for base selection tool classes and interfaces.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QObject, QPoint, QRect, Qt
from PyQt6.QtGui import QPainter, QCursor

from src.torematrix.ui.viewer.tools.base import (
    ToolState, SelectionResult, SelectionTool, ToolRegistry
)
from src.torematrix.ui.viewer.coordinates import Rectangle, Point
from src.torematrix.ui.viewer.layers import LayerElement


class MockTool(SelectionTool):
    """Mock tool for testing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.activated = False
        self.deactivated = False
        self.mouse_press_calls = []
        self.mouse_move_calls = []
        self.mouse_release_calls = []
        self.render_calls = []
    
    def activate(self):
        self.activated = True
        self._update_state(ToolState.ACTIVE)
    
    def deactivate(self):
        self.deactivated = True
        self._update_state(ToolState.INACTIVE)
    
    def handle_mouse_press(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        self.mouse_press_calls.append((point, modifiers))
        return True
    
    def handle_mouse_move(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        self.mouse_move_calls.append((point, modifiers))
        return True
    
    def handle_mouse_release(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        self.mouse_release_calls.append((point, modifiers))
        return True
    
    def render_overlay(self, painter, viewport_rect):
        self.render_calls.append((painter, viewport_rect))


class MockLayerElement:
    """Mock layer element for testing."""
    
    def __init__(self, x, y, width, height, element_id="test"):
        self._bounds = Rectangle(x, y, width, height)
        self._id = element_id
    
    def get_bounds(self):
        return self._bounds
    
    def get_id(self):
        return self._id


class TestToolState:
    """Test ToolState enum."""
    
    def test_tool_states_exist(self):
        """Test that all required tool states exist."""
        assert ToolState.INACTIVE == ToolState.INACTIVE
        assert ToolState.ACTIVE == ToolState.ACTIVE
        assert ToolState.HOVER == ToolState.HOVER
        assert ToolState.SELECTING == ToolState.SELECTING
        assert ToolState.SELECTED == ToolState.SELECTED
        assert ToolState.DRAG == ToolState.DRAG
        assert ToolState.RESIZE == ToolState.RESIZE
        assert ToolState.MOVE == ToolState.MOVE
    
    def test_tool_state_values(self):
        """Test tool state string values."""
        assert ToolState.INACTIVE.value == "inactive"
        assert ToolState.ACTIVE.value == "active"
        assert ToolState.HOVER.value == "hover"
        assert ToolState.SELECTING.value == "selecting"
        assert ToolState.SELECTED.value == "selected"
        assert ToolState.DRAG.value == "drag"
        assert ToolState.RESIZE.value == "resize"
        assert ToolState.MOVE.value == "move"


class TestSelectionResult:
    """Test SelectionResult dataclass."""
    
    def test_default_construction(self):
        """Test default SelectionResult construction."""
        result = SelectionResult()
        
        assert result.elements == []
        assert result.geometry is None
        assert result.tool_type == "unknown"
        assert isinstance(result.timestamp, float)
        assert result.metadata == {}
    
    def test_custom_construction(self):
        """Test custom SelectionResult construction."""
        elements = [MockLayerElement(0, 0, 10, 10)]
        geometry = Rectangle(0, 0, 10, 10)
        metadata = {"test": "value"}
        
        result = SelectionResult(
            elements=elements,
            geometry=geometry,
            tool_type="test_tool",
            metadata=metadata
        )
        
        assert result.elements == elements
        assert result.geometry == geometry
        assert result.tool_type == "test_tool"
        assert result.metadata == metadata
    
    def test_is_valid(self):
        """Test is_valid method."""
        # Empty result
        result = SelectionResult()
        assert not result.is_valid()
        
        # Result with elements
        result.elements = [MockLayerElement(0, 0, 10, 10)]
        assert result.is_valid()
        
        # Result with geometry only
        result = SelectionResult(geometry=Rectangle(0, 0, 10, 10))
        assert result.is_valid()
    
    def test_get_element_count(self):
        """Test get_element_count method."""
        result = SelectionResult()
        assert result.get_element_count() == 0
        
        result.elements = [MockLayerElement(0, 0, 10, 10), MockLayerElement(10, 10, 10, 10)]
        assert result.get_element_count() == 2
    
    def test_get_element_ids(self):
        """Test get_element_ids method."""
        result = SelectionResult()
        assert result.get_element_ids() == []
        
        elem1 = MockLayerElement(0, 0, 10, 10, "elem1")
        elem2 = MockLayerElement(10, 10, 10, 10, "elem2")
        result.elements = [elem1, elem2]
        
        ids = result.get_element_ids()
        assert "elem1" in ids
        assert "elem2" in ids
        assert len(ids) == 2
    
    def test_get_bounds_with_geometry(self):
        """Test get_bounds with explicit geometry."""
        geometry = Rectangle(5, 5, 20, 20)
        result = SelectionResult(geometry=geometry)
        
        bounds = result.get_bounds()
        assert bounds == geometry
    
    def test_get_bounds_with_elements(self):
        """Test get_bounds calculated from elements."""
        elem1 = MockLayerElement(0, 0, 10, 10)
        elem2 = MockLayerElement(15, 5, 10, 10)
        result = SelectionResult(elements=[elem1, elem2])
        
        bounds = result.get_bounds()
        assert bounds is not None
        assert bounds.x == 0
        assert bounds.y == 0
        assert bounds.width == 25  # 0 to 25
        assert bounds.height == 15  # 0 to 15
    
    def test_get_bounds_empty(self):
        """Test get_bounds with no elements or geometry."""
        result = SelectionResult()
        assert result.get_bounds() is None


class TestSelectionTool:
    """Test SelectionTool abstract base class."""
    
    def test_tool_creation(self):
        """Test tool creation and initialization."""
        tool = MockTool()
        
        assert tool.state == ToolState.INACTIVE
        assert tool.enabled == True
        assert tool.visible == True
        assert isinstance(tool.cursor, QCursor)
        assert isinstance(tool.current_selection, SelectionResult)
        assert isinstance(tool.preview_selection, SelectionResult)
    
    def test_tool_properties(self):
        """Test tool properties."""
        tool = MockTool()
        
        # Test enabled property
        assert tool.enabled == True
        tool.set_enabled(False)
        assert tool.enabled == False
        
        # Test visible property
        assert tool.visible == True
        tool.set_visible(False)
        assert tool.visible == False
    
    def test_configuration(self):
        """Test tool configuration."""
        tool = MockTool()
        
        # Test default config
        assert tool.get_config('double_click_threshold') == 300
        assert tool.get_config('drag_threshold') == 5
        
        # Test setting config
        tool.set_config('double_click_threshold', 500)
        assert tool.get_config('double_click_threshold') == 500
        
        # Test invalid config key
        tool.set_config('invalid_key', 'value')
        assert tool.get_config('invalid_key') is None
    
    def test_activation_deactivation(self):
        """Test tool activation and deactivation."""
        tool = MockTool()
        
        assert not tool.activated
        assert not tool.deactivated
        assert tool.state == ToolState.INACTIVE
        
        # Test activation
        tool.activate()
        assert tool.activated
        assert tool.state == ToolState.ACTIVE
        
        # Test deactivation
        tool.deactivate()
        assert tool.deactivated
        assert tool.state == ToolState.INACTIVE
    
    def test_mouse_events(self):
        """Test mouse event handling."""
        tool = MockTool()
        point = QPoint(10, 20)
        modifiers = Qt.KeyboardModifier.ControlModifier
        
        # Test mouse press
        result = tool.handle_mouse_press(point, modifiers)
        assert result == True
        assert len(tool.mouse_press_calls) == 1
        assert tool.mouse_press_calls[0] == (point, modifiers)
        
        # Test mouse move
        result = tool.handle_mouse_move(point, modifiers)
        assert result == True
        assert len(tool.mouse_move_calls) == 1
        assert tool.mouse_move_calls[0] == (point, modifiers)
        
        # Test mouse release
        result = tool.handle_mouse_release(point, modifiers)
        assert result == True
        assert len(tool.mouse_release_calls) == 1
        assert tool.mouse_release_calls[0] == (point, modifiers)
    
    def test_keyboard_events(self):
        """Test keyboard event handling."""
        tool = MockTool()
        
        # Test default implementations
        result = tool.handle_key_press(Qt.Key.Key_A)
        assert result == False
        
        result = tool.handle_key_release(Qt.Key.Key_A)
        assert result == False
    
    def test_wheel_events(self):
        """Test wheel event handling."""
        tool = MockTool()
        
        # Test default implementation
        result = tool.handle_wheel(120, QPoint(10, 10))
        assert result == False
    
    def test_double_click_events(self):
        """Test double click event handling."""
        tool = MockTool()
        
        # Test default implementation
        result = tool.handle_mouse_double_click(QPoint(10, 10))
        assert result == False
    
    def test_render_overlay(self):
        """Test overlay rendering."""
        tool = MockTool()
        painter = Mock(spec=QPainter)
        viewport_rect = QRect(0, 0, 100, 100)
        
        tool.render_overlay(painter, viewport_rect)
        assert len(tool.render_calls) == 1
        assert tool.render_calls[0] == (painter, viewport_rect)
    
    def test_reset(self):
        """Test tool reset."""
        tool = MockTool()
        
        # Set up some state
        tool.activate()
        tool._current_selection = SelectionResult(tool_type="test")
        tool._preview_selection = SelectionResult(tool_type="preview")
        
        # Reset
        tool.reset()
        
        assert tool.state == ToolState.INACTIVE
        assert tool.current_selection.tool_type == "unknown"
        assert tool.preview_selection.tool_type == "unknown"
    
    def test_clear_selection(self):
        """Test selection clearing."""
        tool = MockTool()
        
        # Set up selections
        tool._current_selection = SelectionResult(tool_type="test")
        tool._preview_selection = SelectionResult(tool_type="preview")
        
        # Clear selections
        tool.clear_selection()
        
        assert tool.current_selection.tool_type == "unknown"
        assert tool.preview_selection.tool_type == "unknown"
    
    def test_cursor_management(self):
        """Test cursor management."""
        tool = MockTool()
        
        original_cursor = tool.cursor
        new_cursor = QCursor(Qt.CursorShape.CrossCursor)
        
        tool.set_cursor(new_cursor)
        assert tool.cursor == new_cursor
        assert tool.cursor != original_cursor
    
    def test_metrics(self):
        """Test performance metrics."""
        tool = MockTool()
        
        metrics = tool.get_metrics()
        assert isinstance(metrics, dict)
        assert 'operations_count' in metrics
        assert 'average_operation_time' in metrics
        assert 'last_operation_time' in metrics
        assert 'selection_accuracy' in metrics
        
        # Test metrics update
        tool._update_metrics(0.1)
        updated_metrics = tool.get_metrics()
        assert updated_metrics['operations_count'] == 1
        assert updated_metrics['last_operation_time'] == 0.1
        assert updated_metrics['average_operation_time'] == 0.1
    
    def test_utility_methods(self):
        """Test utility conversion methods."""
        tool = MockTool()
        
        # Test distance calculation
        p1 = QPoint(0, 0)
        p2 = QPoint(3, 4)
        distance = tool._get_distance(p1, p2)
        assert distance == 5.0
        
        # Test point conversions
        qpoint = QPoint(10, 20)
        point = tool._qpoint_to_point(qpoint)
        assert point.x == 10
        assert point.y == 20
        
        converted_back = tool._point_to_qpoint(point)
        assert converted_back.x() == 10
        assert converted_back.y() == 20
        
        # Test rectangle conversions
        qrect = QRect(5, 10, 15, 20)
        rect = tool._qrect_to_rectangle(qrect)
        assert rect.x == 5
        assert rect.y == 10
        assert rect.width == 15
        assert rect.height == 20
        
        converted_back = tool._rectangle_to_qrect(rect)
        assert converted_back.x() == 5
        assert converted_back.y() == 10
        assert converted_back.width() == 15
        assert converted_back.height() == 20
    
    def test_disabled_tool_deactivation(self):
        """Test that disabling tool deactivates it."""
        tool = MockTool()
        tool.activate()
        assert tool.state == ToolState.ACTIVE
        
        tool.set_enabled(False)
        assert tool.state == ToolState.INACTIVE
        assert tool.deactivated == True
    
    def test_invisible_tool_deactivation(self):
        """Test that making tool invisible deactivates it."""
        tool = MockTool()
        tool.activate()
        assert tool.state == ToolState.ACTIVE
        
        tool.set_visible(False)
        assert tool.state == ToolState.INACTIVE
        assert tool.deactivated == True


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_registry_creation(self):
        """Test registry creation."""
        registry = ToolRegistry()
        
        assert len(registry.get_all_tools()) == 0
        assert registry.get_active_tool() is None
        assert registry.get_active_tool_name() is None
    
    def test_tool_registration(self):
        """Test tool registration."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register_tool("test_tool", tool)
        
        assert "test_tool" in registry.get_all_tools()
        assert registry.get_tool("test_tool") == tool
        assert len(registry.get_all_tools()) == 1
    
    def test_tool_unregistration(self):
        """Test tool unregistration."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register_tool("test_tool", tool)
        assert registry.get_tool("test_tool") == tool
        
        registry.unregister_tool("test_tool")
        assert registry.get_tool("test_tool") is None
        assert len(registry.get_all_tools()) == 0
    
    def test_active_tool_management(self):
        """Test active tool management."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()
        
        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)
        
        # Test setting active tool
        success = registry.set_active_tool("tool1")
        assert success == True
        assert registry.get_active_tool() == tool1
        assert registry.get_active_tool_name() == "tool1"
        assert tool1.activated == True
        
        # Test switching active tool
        success = registry.set_active_tool("tool2")
        assert success == True
        assert registry.get_active_tool() == tool2
        assert registry.get_active_tool_name() == "tool2"
        assert tool1.deactivated == True
        assert tool2.activated == True
        
        # Test setting invalid tool
        success = registry.set_active_tool("invalid_tool")
        assert success == False
        assert registry.get_active_tool() == tool2  # Should remain unchanged
    
    def test_unregister_active_tool(self):
        """Test unregistering active tool."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register_tool("test_tool", tool)
        registry.set_active_tool("test_tool")
        
        assert registry.get_active_tool() == tool
        assert tool.activated == True
        
        registry.unregister_tool("test_tool")
        
        assert registry.get_active_tool() is None
        assert registry.get_active_tool_name() is None
        assert tool.deactivated == True
    
    def test_deactivate_all(self):
        """Test deactivating all tools."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()
        
        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)
        
        # Activate tools
        tool1.activate()
        tool2.activate()
        
        registry.deactivate_all()
        
        assert tool1.deactivated == True
        assert tool2.deactivated == True
        assert registry.get_active_tool() is None
    
    def test_get_all_tools(self):
        """Test getting all tools."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()
        
        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)
        
        all_tools = registry.get_all_tools()
        assert isinstance(all_tools, dict)
        assert len(all_tools) == 2
        assert all_tools["tool1"] == tool1
        assert all_tools["tool2"] == tool2
        
        # Ensure it's a copy (modifications don't affect registry)
        all_tools["tool3"] = MockTool()
        assert len(registry.get_all_tools()) == 2


if __name__ == "__main__":
    pytest.main([__file__])