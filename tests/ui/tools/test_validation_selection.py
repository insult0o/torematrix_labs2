"""
Tests for validation area selection tools.
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