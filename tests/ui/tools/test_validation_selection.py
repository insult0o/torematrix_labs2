"""
Tests for validation area selection tools.
<<<<<<< HEAD

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
=======
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import UUID

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QPolygonF
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene

from torematrix.ui.tools.validation.area_select import (
    ValidationAreaSelector,
    ValidationSelection,
    SelectionMode,
    SelectionState,
)
from torematrix.ui.tools.validation.shapes import (
    SelectionRectangle,
    SelectionPolygon,
    SelectionFreehand,
)
from torematrix.core.base import ToolMode
from torematrix.models.element import ElementType


@pytest.fixture
def app(qapp):
    """Get Qt application."""
    return qapp


@pytest.fixture
def graphics_view():
    """Create a graphics view for testing."""
    view = QGraphicsView()
    scene = QGraphicsScene()
    view.setScene(scene)
    return view


@pytest.fixture
def selector():
    """Create a validation area selector."""
    return ValidationAreaSelector()


class TestValidationSelection:
    """Test ValidationSelection class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        selection = ValidationSelection()
        
        assert isinstance(selection.id, UUID)
        assert selection.page_number == 0
        assert selection.shape_type == SelectionMode.RECTANGLE
        assert selection.points == []
        assert selection.element_type is None
        assert selection.confidence == 0.0
        assert selection.notes == ""
        assert not selection.is_complete
        
    def test_bounding_rect_empty(self):
        """Test bounding rect with no points."""
        selection = ValidationSelection()
        rect = selection.bounding_rect
        
        assert rect.isEmpty()
        
    def test_bounding_rect_with_points(self):
        """Test bounding rect calculation."""
        selection = ValidationSelection()
        selection.points = [
            QPointF(10, 20),
            QPointF(50, 40),
            QPointF(30, 60),
            QPointF(20, 10)
        ]
        
        rect = selection.bounding_rect
        assert rect.x() == 10
        assert rect.y() == 10
        assert rect.width() == 40
        assert rect.height() == 50
        
    def test_to_dict(self):
        """Test conversion to dictionary."""
        selection = ValidationSelection(
            page_number=5,
            shape_type=SelectionMode.POLYGON,
            element_type=ElementType.TABLE,
            confidence=0.95,
            notes="Test selection"
        )
        selection.points = [QPointF(10, 20), QPointF(30, 40)]
        
        data = selection.to_dict()
        
        assert data['id'] == str(selection.id)
        assert data['page_number'] == 5
        assert data['shape_type'] == 'polygon'
        assert data['points'] == [(10.0, 20.0), (30.0, 40.0)]
        assert data['element_type'] == 'table'
        assert data['confidence'] == 0.95
        assert data['notes'] == "Test selection"
        assert not data['is_complete']
        
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'id': '12345678-1234-5678-1234-567812345678',
            'page_number': 3,
            'shape_type': 'freehand',
            'points': [(10, 20), (30, 40), (50, 60)],
            'element_type': 'figure',
            'confidence': 0.85,
            'notes': 'Imported selection',
            'created_at': '2024-01-01T10:00:00',
            'modified_at': '2024-01-01T11:00:00',
            'is_complete': True
        }
        
        selection = ValidationSelection.from_dict(data)
        
        assert str(selection.id) == data['id']
        assert selection.page_number == 3
        assert selection.shape_type == SelectionMode.FREEHAND
        assert len(selection.points) == 3
        assert selection.element_type == ElementType.FIGURE
        assert selection.confidence == 0.85
        assert selection.notes == 'Imported selection'
        assert selection.is_complete


class TestValidationAreaSelector:
    """Test ValidationAreaSelector class."""
    
    def test_init(self):
        """Test initialization."""
        selector = ValidationAreaSelector()
        
        assert selector.name == "Validation Area Selector"
        assert selector.mode == ToolMode.INACTIVE
        assert selector.selection_mode == SelectionMode.RECTANGLE
        assert selector._state == SelectionState.IDLE
        assert len(selector._active_selections) == 0
        
    def test_selection_mode_change(self, selector):
        """Test changing selection mode."""
        # Mock signal
        selector.mode_changed = Mock()
        
        # Change mode
        selector.selection_mode = SelectionMode.POLYGON
        
        assert selector.selection_mode == SelectionMode.POLYGON
        selector.mode_changed.emit.assert_called_once_with(SelectionMode.POLYGON)
        
        # Same mode shouldn't emit signal
        selector.mode_changed.reset_mock()
        selector.selection_mode = SelectionMode.POLYGON
        selector.mode_changed.emit.assert_not_called()
        
    def test_activate(self, selector, graphics_view):
        """Test tool activation."""
        selector.activate(graphics_view)
        
        assert selector.mode == ToolMode.ACTIVE
        assert selector._view == graphics_view
        assert selector._scene == graphics_view.scene()
        
    def test_deactivate(self, selector, graphics_view):
        """Test tool deactivation."""
        selector.activate(graphics_view)
        selector.deactivate()
        
        assert selector.mode == ToolMode.INACTIVE
        assert selector._view is None
        assert selector._scene is None
        
    def test_mouse_press_starts_selection(self, selector, graphics_view):
        """Test mouse press starts new selection."""
        selector.activate(graphics_view)
        
        # Create mouse event
        pos = QPointF(100, 200)
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value.toPoint.return_value = pos.toPoint()
        
        # Mock view mapping
        graphics_view.mapToScene = Mock(return_value=pos)
        
        # Process event
        result = selector.mouse_press_event(event)
        
        assert result is True
        assert selector._state == SelectionState.DRAWING
        assert selector._start_point == pos
        assert selector._current_selection is not None
        
    def test_mouse_move_updates_rectangle(self, selector, graphics_view):
        """Test mouse move updates rectangle preview."""
        selector.activate(graphics_view)
        selector.selection_mode = SelectionMode.RECTANGLE
        
        # Start selection
        start_pos = QPointF(100, 100)
        selector._start_new_selection(start_pos)
        
        # Create preview item
        selector._preview_item = Mock(spec=SelectionRectangle)
        
        # Move mouse
        move_pos = QPointF(200, 200)
        event = Mock()
        event.position.return_value.toPoint.return_value = move_pos.toPoint()
        graphics_view.mapToScene = Mock(return_value=move_pos)
        
        result = selector.mouse_move_event(event)
        
        assert result is True
        # Check that preview was updated
        selector._preview_item.setRect.assert_called()
        
    def test_mouse_release_completes_rectangle(self, selector, graphics_view):
        """Test mouse release completes rectangle selection."""
        selector.activate(graphics_view)
        selector.selection_mode = SelectionMode.RECTANGLE
        
        # Mock signal
        selector.selection_created = Mock()
        
        # Start selection
        start_pos = QPointF(100, 100)
        selector._start_new_selection(start_pos)
        
        # Create preview rectangle
        rect = QRectF(100, 100, 100, 100)
        selector._preview_item = Mock()
        selector._preview_item.rect.return_value = rect
        
        # Release mouse
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        
        result = selector.mouse_release_event(event)
        
        assert result is True
        assert selector._state == SelectionState.IDLE
        assert len(selector._active_selections) == 1
        selector.selection_created.emit.assert_called_once()
        
    def test_polygon_mode_point_addition(self, selector, graphics_view):
        """Test adding points in polygon mode."""
        selector.activate(graphics_view)
        selector.selection_mode = SelectionMode.POLYGON
        
        # Start selection
        p1 = QPointF(100, 100)
        selector._start_new_selection(p1)
        
        # Add second point
        p2 = QPointF(200, 100)
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.position.return_value.toPoint.return_value = p2.toPoint()
        graphics_view.mapToScene = Mock(return_value=p2)
        
        result = selector.mouse_press_event(event)
        
        assert result is True
        assert len(selector._current_points) == 2
        assert selector._current_points[1] == p2
        
    def test_polygon_double_click_completion(self, selector, graphics_view):
        """Test double-click completes polygon."""
        selector.activate(graphics_view)
        selector.selection_mode = SelectionMode.POLYGON
        
        # Mock signal
        selector.selection_created = Mock()
        
        # Create polygon with 3 points
        selector._start_new_selection(QPointF(100, 100))
        selector._current_points = [
            QPointF(100, 100),
            QPointF(200, 100),
            QPointF(150, 200)
        ]
        selector._current_selection = ValidationSelection(
            shape_type=SelectionMode.POLYGON
        )
        
        # Double-click event
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        
        result = selector.mouse_double_click_event(event)
        
        assert result is True
        assert selector._state == SelectionState.IDLE
        assert len(selector._active_selections) == 1
        selector.selection_created.emit.assert_called_once()
        
    def test_escape_key_cancels_selection(self, selector, graphics_view):
        """Test escape key cancels current selection."""
        selector.activate(graphics_view)
        
        # Start selection
        selector._start_new_selection(QPointF(100, 100))
        assert selector._state == SelectionState.DRAWING
        
        # Press escape
        event = Mock()
        event.key.return_value = Qt.Key.Key_Escape
        
        result = selector.key_press_event(event)
        
        assert result is True
        assert selector._state == SelectionState.IDLE
        assert selector._current_selection is None
        
    def test_minimum_selection_size(self, selector, graphics_view):
        """Test minimum selection size requirement."""
        selector.activate(graphics_view)
        
        # Start selection
        selector._start_new_selection(QPointF(100, 100))
        
        # Create tiny preview rectangle
        rect = QRectF(100, 100, 5, 5)  # Below minimum size
        selector._preview_item = Mock()
        selector._preview_item.rect.return_value = rect
        
        # Try to complete
        selector._complete_rectangle()
        
        # Should be cancelled
        assert selector._state == SelectionState.IDLE
        assert len(selector._active_selections) == 0
        
    def test_get_selections_all(self, selector):
        """Test getting all selections."""
        # Create test selections
        sel1 = ValidationSelection(page_number=1)
        sel2 = ValidationSelection(page_number=2)
        sel3 = ValidationSelection(page_number=1)
        
        selector._active_selections = {
            sel1.id: sel1,
            sel2.id: sel2,
            sel3.id: sel3
        }
        
        # Get all
        all_selections = selector.get_selections()
        assert len(all_selections) == 3
        
    def test_get_selections_by_page(self, selector):
        """Test getting selections by page."""
        # Create test selections
        sel1 = ValidationSelection(page_number=1)
        sel2 = ValidationSelection(page_number=2)
        sel3 = ValidationSelection(page_number=1)
        
        selector._active_selections = {
            sel1.id: sel1,
            sel2.id: sel2,
            sel3.id: sel3
        }
        
        # Get page 1 selections
        page1_selections = selector.get_selections(page_number=1)
        assert len(page1_selections) == 2
        assert all(s.page_number == 1 for s in page1_selections)
        
    def test_clear_selections_all(self, selector):
        """Test clearing all selections."""
        # Mock signal
        selector.selection_deleted = Mock()
        
        # Create test selections
        sel1 = ValidationSelection()
        sel2 = ValidationSelection()
        
        selector._active_selections = {
            sel1.id: sel1,
            sel2.id: sel2
        }
        
        # Clear all
        selector.clear_selections()
        
        assert len(selector._active_selections) == 0
        assert selector.selection_deleted.emit.call_count == 2
        
    def test_clear_selections_by_page(self, selector):
        """Test clearing selections by page."""
        # Mock signal
        selector.selection_deleted = Mock()
        
        # Create test selections
        sel1 = ValidationSelection(page_number=1)
        sel2 = ValidationSelection(page_number=2)
        sel3 = ValidationSelection(page_number=1)
        
        selector._active_selections = {
            sel1.id: sel1,
            sel2.id: sel2,
            sel3.id: sel3
        }
        
        # Clear page 1
        selector.clear_selections(page_number=1)
        
        assert len(selector._active_selections) == 1
        assert sel2.id in selector._active_selections
        assert selector.selection_deleted.emit.call_count == 2


class TestSelectionShapes:
    """Test selection shape classes."""
    
    def test_rectangle_shape_creation(self):
        """Test creating rectangle shape."""
        rect = QRectF(10, 20, 100, 50)
        shape = SelectionRectangle(rect)
        
        assert shape.rect() == rect
        assert shape.isSelectable()
        
    def test_polygon_shape_creation(self):
        """Test creating polygon shape."""
        points = [QPointF(0, 0), QPointF(100, 0), QPointF(50, 100)]
        polygon = QPolygonF(points)
        shape = SelectionPolygon(polygon)
        
        assert shape.polygon() == polygon
        assert shape.isSelectable()
        
    def test_freehand_shape_creation(self):
        """Test creating freehand shape."""
        from PyQt6.QtGui import QPainterPath
        
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 50)
        path.lineTo(50, 100)
        path.closeSubpath()
        
        shape = SelectionFreehand(path)
        
        assert shape.path() == path
        assert shape.isSelectable()
        
    def test_shape_editing_mode(self):
        """Test shape editing mode."""
        rect = QRectF(10, 20, 100, 50)
        shape = SelectionRectangle(rect)
        
        # Initially not editing
        assert not shape._editing
        assert len(shape._handles) == 0
        
        # Enable editing
        shape.set_editing(True)
        assert shape._editing
        assert len(shape._handles) > 0
        
        # Disable editing
        shape.set_editing(False)
        assert not shape._editing
        assert len(shape._handles) == 0
>>>>>>> origin/main
