"""
Tests for validation area selection tools.

This tests the core selection functionality without dependencies on 
Agent 2-4 features (snapping, optimization, integration).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt6.QtGui import QMouseEvent, QPainter, QColor
from PyQt6.QtWidgets import QWidget, QApplication

from torematrix.ui.tools.validation import (
    ValidationAreaSelector,
    AreaSelectionMode,
    SelectionConstraint,
    ValidationSelectionConfig,
    RectangleShape,
    PolygonShape,
    FreehandShape,
    RectangleSelectionTool,
    PolygonSelectionTool,
    FreehandSelectionTool
)


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def widget(app):
    """Create test widget."""
    widget = QWidget()
    widget.resize(800, 600)
    yield widget


class TestRectangleShape:
    """Test rectangle shape functionality."""
    
    def test_creation(self):
        """Test rectangle creation."""
        shape = RectangleShape(QPointF(10, 10), QPointF(50, 40))
        rect = shape.get_bounding_rect()
        
        assert rect.x() == 10
        assert rect.y() == 10
        assert rect.width() == 40
        assert rect.height() == 30
    
    def test_contains(self):
        """Test point containment."""
        shape = RectangleShape(QPointF(10, 10), QPointF(50, 40))
        
        assert shape.contains(QPointF(30, 25))  # Inside
        assert not shape.contains(QPointF(5, 5))  # Outside
        assert shape.contains(QPointF(10, 10))  # On boundary
    
    def test_handles(self):
        """Test handle positions."""
        shape = RectangleShape(QPointF(10, 10), QPointF(50, 40))
        handles = shape.get_handles()
        
        assert len(handles) == 8  # 4 corners + 4 edges
        assert handles[0] == QPointF(10, 10)  # Top-left
        assert handles[2] == QPointF(50, 40)  # Bottom-right
    
    def test_translate(self):
        """Test shape translation."""
        shape = RectangleShape(QPointF(10, 10), QPointF(50, 40))
        shape.translate(QPointF(20, 15))
        
        assert shape.top_left == QPointF(30, 25)
        assert shape.bottom_right == QPointF(70, 55)
    
    def test_aspect_ratio(self):
        """Test aspect ratio maintenance."""
        shape = RectangleShape(QPointF(10, 10), QPointF(50, 30))
        shape.maintain_aspect_ratio(2.0)  # Width should be 2x height
        
        rect = shape.get_bounding_rect()
        assert abs(rect.width() / rect.height() - 2.0) < 0.01


class TestPolygonShape:
    """Test polygon shape functionality."""
    
    def test_creation(self):
        """Test polygon creation."""
        points = [QPointF(10, 10), QPointF(50, 10), QPointF(30, 40)]
        shape = PolygonShape(points)
        
        assert len(shape.points) == 3
        assert shape.closed
    
    def test_bounding_rect(self):
        """Test bounding rectangle calculation."""
        points = [QPointF(10, 10), QPointF(50, 10), QPointF(30, 40)]
        shape = PolygonShape(points)
        rect = shape.get_bounding_rect()
        
        assert rect.x() == 10
        assert rect.y() == 10
        assert rect.width() == 40
        assert rect.height() == 30
    
    def test_add_remove_points(self):
        """Test adding and removing points."""
        shape = PolygonShape([QPointF(10, 10), QPointF(50, 10), QPointF(30, 40)])
        
        # Add point
        shape.add_point(QPointF(20, 30))
        assert len(shape.points) == 4
        
        # Remove point
        shape.remove_point(1)
        assert len(shape.points) == 3
    
    def test_simplify(self):
        """Test polygon simplification."""
        # Create polygon with many close points
        points = [
            QPointF(10, 10),
            QPointF(10.5, 10),  # Very close to previous
            QPointF(50, 10),
            QPointF(30, 40),
            QPointF(29.5, 40)  # Very close to previous
        ]
        shape = PolygonShape(points)
        shape.simplify(tolerance=2.0)
        
        # Should have fewer points after simplification
        assert len(shape.points) < 5


class TestFreehandShape:
    """Test freehand shape functionality."""
    
    def test_creation(self):
        """Test freehand creation."""
        shape = FreehandShape()
        shape.add_point(QPointF(10, 10))
        shape.add_point(QPointF(20, 20))
        shape.add_point(QPointF(30, 15))
        
        assert len(shape.points) == 3
    
    def test_smoothing_filter(self):
        """Test point filtering based on distance."""
        shape = FreehandShape(smoothing_factor=5.0)
        
        shape.add_point(QPointF(10, 10))
        shape.add_point(QPointF(11, 11))  # Too close, should be filtered
        shape.add_point(QPointF(20, 20))  # Far enough
        
        assert len(shape.points) == 2
    
    def test_smooth(self):
        """Test smoothing algorithm."""
        points = [QPointF(10, 10), QPointF(20, 30), QPointF(30, 15)]
        shape = FreehandShape(points)
        original_middle = shape.points[1]
        
        shape.smooth()
        
        # Middle point should be moved by smoothing
        assert shape.points[1] != original_middle
        assert len(shape.points) == 3


class TestSelectionTools:
    """Test selection tool implementations."""
    
    def test_rectangle_tool(self):
        """Test rectangle selection tool."""
        tool = RectangleSelectionTool()
        
        # Start selection
        tool.start_selection(QPointF(10, 10))
        assert tool.is_active
        assert tool.current_shape is not None
        
        # Update selection
        tool.update_selection(QPointF(50, 40))
        shape = tool.get_current_shape()
        assert shape.bottom_right == QPointF(50, 40)
        
        # Complete selection
        result = tool.complete_selection()
        assert result is not None
        assert not tool.is_active
        assert isinstance(result, RectangleShape)
    
    def test_polygon_tool(self):
        """Test polygon selection tool."""
        tool = PolygonSelectionTool()
        
        # Start selection
        tool.start_selection(QPointF(10, 10))
        assert tool.is_active
        
        # Add points
        tool.add_point(QPointF(50, 10))
        tool.add_point(QPointF(30, 40))
        
        # Complete selection
        result = tool.complete_selection()
        assert result is not None
        assert len(result.points) == 3
        assert result.closed
    
    def test_freehand_tool(self):
        """Test freehand selection tool."""
        tool = FreehandSelectionTool()
        
        # Start selection
        tool.start_selection(QPointF(10, 10))
        assert tool.is_active
        
        # Add points
        tool.update_selection(QPointF(20, 20))
        tool.update_selection(QPointF(30, 15))
        tool.update_selection(QPointF(40, 25))
        
        # Complete selection
        result = tool.complete_selection()
        assert result is not None
        assert isinstance(result, FreehandShape)
        assert len(result.points) >= 3


class TestValidationAreaSelector:
    """Test the main validation area selector."""
    
    def test_initialization(self, widget):
        """Test selector initialization."""
        selector = ValidationAreaSelector(widget)
        
        assert selector.widget == widget
        assert selector.mode == AreaSelectionMode.CREATE_NEW
        assert selector.active_constraint == SelectionConstraint.NONE
        assert not selector.is_selecting
    
    def test_mode_changes(self, widget):
        """Test selection mode changes."""
        selector = ValidationAreaSelector(widget)
        mode_changed = Mock()
        selector.mode_changed.connect(mode_changed)
        
        selector.set_mode(AreaSelectionMode.ADJUST_BOUNDARY)
        
        assert selector.mode == AreaSelectionMode.ADJUST_BOUNDARY
        mode_changed.assert_called_once_with(AreaSelectionMode.ADJUST_BOUNDARY)
    
    def test_tool_selection(self, widget):
        """Test tool selection."""
        selector = ValidationAreaSelector(widget)
        
        selector.set_tool('polygon')
        assert selector.active_tool_name == 'polygon'
        
        selector.set_tool('freehand')
        assert selector.active_tool_name == 'freehand'
    
    def test_constraint_setting(self, widget):
        """Test constraint settings."""
        selector = ValidationAreaSelector(widget)
        
        selector.set_constraint(SelectionConstraint.ALIGN_TO_GRID)
        assert selector.active_constraint == SelectionConstraint.ALIGN_TO_GRID
    
    def test_grid_alignment(self, widget):
        """Test grid alignment constraint."""
        selector = ValidationAreaSelector(widget)
        selector.config.grid_size = 20.0
        selector.set_constraint(SelectionConstraint.ALIGN_TO_GRID)
        
        # Test point snapping to grid
        point = QPointF(23, 17)
        aligned = selector._apply_point_constraints(point)
        
        assert aligned.x() == 20.0  # Snapped to nearest grid line
        assert aligned.y() == 20.0
    
    def test_selection_validation(self, widget):
        """Test selection validation."""
        selector = ValidationAreaSelector(widget)
        selector.config.min_selection_size = 10.0
        
        # Too small shape
        small_shape = RectangleShape(QPointF(0, 0), QPointF(5, 5))
        assert not selector._is_valid_selection(small_shape)
        
        # Valid shape
        valid_shape = RectangleShape(QPointF(0, 0), QPointF(20, 20))
        assert selector._is_valid_selection(valid_shape)
    
    def test_selection_workflow(self, widget):
        """Test complete selection workflow."""
        selector = ValidationAreaSelector(widget)
        
        # Connect signals
        started = Mock()
        changed = Mock()
        completed = Mock()
        
        selector.selection_started.connect(started)
        selector.selection_changed.connect(changed)
        selector.selection_completed.connect(completed)
        
        # Start selection
        selector.start_selection(QPointF(10, 10))
        assert selector.is_selecting
        started.assert_called_once()
        
        # Update selection
        selector.update_selection(QPointF(50, 50))
        changed.assert_called()
        
        # Complete selection
        selector.complete_selection()
        assert not selector.is_selecting
        completed.assert_called_once()
        
        # Check selection was stored
        assert len(selector.selections) == 1
        assert isinstance(selector.selections[0], RectangleShape)
    
    def test_multi_selection(self, widget):
        """Test multiple selections."""
        selector = ValidationAreaSelector(widget)
        selector.config.allow_multi_select = True
        
        # Create multiple selections
        for i in range(3):
            selector.start_selection(QPointF(i * 20, i * 20))
            selector.update_selection(QPointF(i * 20 + 40, i * 20 + 40))
            selector.complete_selection()
        
        assert len(selector.selections) == 3
        assert len(selector.selected_indices) == 3
    
    def test_selection_deletion(self, widget):
        """Test deleting selections."""
        selector = ValidationAreaSelector(widget)
        
        # Create selections
        for i in range(3):
            selector.start_selection(QPointF(i * 20, i * 20))
            selector.update_selection(QPointF(i * 20 + 40, i * 20 + 40))
            selector.complete_selection()
        
        # Delete middle selection
        selector.delete_selection(1)
        
        assert len(selector.selections) == 2
        # Check indices were adjusted
        assert 0 in selector.selected_indices
        assert 1 in selector.selected_indices
        assert 2 not in selector.selected_indices


class TestEventHandling:
    """Test event handling integration."""
    
    def test_mouse_events(self, widget):
        """Test mouse event handling."""
        selector = ValidationAreaSelector(widget)
        
        # Create mock mouse events
        press_event = MagicMock(spec=QMouseEvent)
        press_event.type.return_value = QEvent.Type.MouseButtonPress
        press_event.button.return_value = Qt.MouseButton.LeftButton
        press_event.position.return_value = QPointF(10, 10)
        
        move_event = MagicMock(spec=QMouseEvent)
        move_event.type.return_value = QEvent.Type.MouseMove
        move_event.position.return_value = QPointF(50, 50)
        
        release_event = MagicMock(spec=QMouseEvent)
        release_event.type.return_value = QEvent.Type.MouseButtonRelease
        release_event.button.return_value = Qt.MouseButton.LeftButton
        
        # Process events
        assert selector.eventFilter(widget, press_event)
        assert selector.is_selecting
        
        assert selector.eventFilter(widget, move_event)
        
        assert selector.eventFilter(widget, release_event)
        assert not selector.is_selecting
        assert len(selector.selections) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])