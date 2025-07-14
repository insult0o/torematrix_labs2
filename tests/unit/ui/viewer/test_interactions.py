"""
Unit tests for the interaction management system.
Tests mouse, keyboard, and general interaction handling functionality.
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent

from src.torematrix.ui.viewer.interactions import (
    InteractionManager, InteractionMode, MouseButton, InteractionEvent,
    MouseInteractionEvent, KeyboardInteractionEvent, SelectionModeHandler,
    PanModeHandler, ZoomModeHandler
)
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class TestInteractionEvent:
    """Test interaction event classes."""
    
    def test_interaction_event_creation(self):
        """Test basic interaction event creation."""
        event = InteractionEvent(position=Point(10, 20), modifiers=["ctrl"])
        
        assert event.position.x == 10
        assert event.position.y == 20
        assert "ctrl" in event.modifiers
        assert isinstance(event.timestamp, float)
    
    def test_mouse_interaction_event(self):
        """Test mouse interaction event creation."""
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousedown",
            position=Point(15, 25),
            delta=Point(1, 2)
        )
        
        assert event.button == MouseButton.LEFT
        assert event.event_type == "mousedown"
        assert event.delta.x == 1
        assert event.delta.y == 2
    
    def test_keyboard_interaction_event(self):
        """Test keyboard interaction event creation."""
        event = KeyboardInteractionEvent(
            key="Enter",
            event_type="keydown",
            text="\\n"
        )
        
        assert event.key == "Enter"
        assert event.event_type == "keydown"
        assert event.text == "\\n"


class TestSelectionModeHandler:
    """Test selection mode handler."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_interaction_manager = Mock()
        self.mock_interaction_manager.get_elements_at_point.return_value = []
        self.mock_interaction_manager.clear_selection = Mock()
        self.mock_interaction_manager.select_element = Mock()
        self.mock_interaction_manager.select_elements_in_rectangle = Mock()
        self.mock_interaction_manager.start_rectangular_selection = Mock()
        self.mock_interaction_manager.update_rectangular_selection = Mock()
        self.mock_interaction_manager.end_rectangular_selection = Mock()
        
        self.handler = SelectionModeHandler(self.mock_interaction_manager)
    
    def test_mouse_down_no_element(self):
        """Test mouse down when no element is under cursor."""
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousedown",
            position=Point(10, 10)
        )
        
        handled = self.handler.handle_mouse_down(event)
        
        assert handled
        assert self.handler.drag_start == Point(10, 10)
        self.mock_interaction_manager.clear_selection.assert_called_once()
    
    def test_mouse_down_with_element(self):
        """Test mouse down when element is under cursor."""
        mock_element = Mock()
        self.mock_interaction_manager.get_elements_at_point.return_value = [mock_element]
        
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousedown",
            position=Point(10, 10),
            modifiers=["ctrl"]
        )
        
        handled = self.handler.handle_mouse_down(event)
        
        assert handled
        self.mock_interaction_manager.select_element.assert_called_once_with(
            mock_element, ["ctrl"]
        )
    
    def test_mouse_move_starts_drag(self):
        """Test mouse move that starts drag selection."""
        # Setup drag start
        self.handler.drag_start = Point(0, 0)
        
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousemove",
            position=Point(10, 0)  # Move more than 5px threshold
        )
        
        handled = self.handler.handle_mouse_move(event)
        
        assert handled
        assert self.handler.is_dragging
        self.mock_interaction_manager.start_rectangular_selection.assert_called_once()
        self.mock_interaction_manager.update_rectangular_selection.assert_called_once()
    
    def test_mouse_up_completes_selection(self):
        """Test mouse up that completes rectangular selection."""
        self.handler.drag_start = Point(0, 0)
        self.handler.is_dragging = True
        
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mouseup",
            position=Point(10, 10),
            modifiers=["shift"]
        )
        
        handled = self.handler.handle_mouse_up(event)
        
        assert handled
        assert not self.handler.is_dragging
        assert self.handler.drag_start is None
        
        # Check that rectangular selection was called with correct bounds
        expected_rect = Rectangle(0, 0, 10, 10)
        self.mock_interaction_manager.select_elements_in_rectangle.assert_called_once()
        
        # Get the actual call arguments
        call_args = self.mock_interaction_manager.select_elements_in_rectangle.call_args
        actual_rect = call_args[0][0]
        actual_modifiers = call_args[0][1]
        
        assert actual_rect.x == expected_rect.x
        assert actual_rect.y == expected_rect.y
        assert actual_rect.width == expected_rect.width
        assert actual_rect.height == expected_rect.height
        assert actual_modifiers == ["shift"]
    
    def test_key_down_escape(self):
        """Test escape key clears selection."""
        event = KeyboardInteractionEvent(
            key="Escape",
            event_type="keydown"
        )
        
        handled = self.handler.handle_key_down(event)
        
        assert handled
        self.mock_interaction_manager.clear_selection.assert_called_once()
    
    def test_key_down_select_all(self):
        """Test Ctrl+A selects all."""
        event = KeyboardInteractionEvent(
            key="Ctrl+A",
            event_type="keydown"
        )
        
        self.mock_interaction_manager.select_all = Mock()
        handled = self.handler.handle_key_down(event)
        
        assert handled
        self.mock_interaction_manager.select_all.assert_called_once()


class TestPanModeHandler:
    """Test pan mode handler."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_interaction_manager = Mock()
        self.mock_interaction_manager.pan_viewport = Mock()
        self.handler = PanModeHandler(self.mock_interaction_manager)
    
    def test_pan_sequence(self):
        """Test complete pan sequence."""
        # Mouse down
        down_event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousedown",
            position=Point(10, 10)
        )
        
        handled = self.handler.handle_mouse_down(down_event)
        assert handled
        assert self.handler.is_panning
        assert self.handler.pan_start == Point(10, 10)
        
        # Mouse move
        move_event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousemove",
            position=Point(15, 12)
        )
        
        handled = self.handler.handle_mouse_move(move_event)
        assert handled
        
        # Check pan delta
        expected_delta = Point(5, 2)
        self.mock_interaction_manager.pan_viewport.assert_called_once_with(expected_delta)
        
        # Mouse up
        up_event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mouseup",
            position=Point(15, 12)
        )
        
        handled = self.handler.handle_mouse_up(up_event)
        assert handled
        assert not self.handler.is_panning
        assert self.handler.pan_start is None


class TestZoomModeHandler:
    """Test zoom mode handler."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_interaction_manager = Mock()
        self.mock_interaction_manager.zoom_at_point = Mock()
        self.mock_interaction_manager.zoom_viewport = Mock()
        self.handler = ZoomModeHandler(self.mock_interaction_manager)
    
    def test_left_click_zoom_in(self):
        """Test left click zooms in."""
        event = MouseInteractionEvent(
            button=MouseButton.LEFT,
            event_type="mousedown",
            position=Point(100, 100)
        )
        
        handled = self.handler.handle_mouse_down(event)
        
        assert handled
        self.mock_interaction_manager.zoom_at_point.assert_called_once_with(
            Point(100, 100), 1.2
        )
    
    def test_right_click_zoom_out(self):
        """Test right click zooms out."""
        event = MouseInteractionEvent(
            button=MouseButton.RIGHT,
            event_type="mousedown",
            position=Point(100, 100)
        )
        
        handled = self.handler.handle_mouse_down(event)
        
        assert handled
        self.mock_interaction_manager.zoom_at_point.assert_called_once_with(
            Point(100, 100), 0.8
        )
    
    def test_plus_key_zoom_in(self):
        """Test plus key zooms in."""
        event = KeyboardInteractionEvent(
            key="Plus",
            event_type="keydown"
        )
        
        handled = self.handler.handle_key_down(event)
        
        assert handled
        self.mock_interaction_manager.zoom_viewport.assert_called_once_with(1.2)
    
    def test_minus_key_zoom_out(self):
        """Test minus key zooms out."""
        event = KeyboardInteractionEvent(
            key="Minus",
            event_type="keydown"
        )
        
        handled = self.handler.handle_key_down(event)
        
        assert handled
        self.mock_interaction_manager.zoom_viewport.assert_called_once_with(0.8)


class TestInteractionManager:
    """Test main interaction manager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_overlay_engine = Mock()
        self.mock_overlay_engine.screen_to_document.return_value = Point(10, 10)
        self.mock_overlay_engine.get_viewport_info.return_value = Mock()
        
        self.mock_selection_manager = Mock()
        self.mock_selection_manager.get_selected_elements.return_value = []
        
        self.mock_spatial_index = Mock()
        self.mock_spatial_index.query_point.return_value = []
        
        self.manager = InteractionManager(
            self.mock_overlay_engine,
            self.mock_selection_manager,
            self.mock_spatial_index
        )
    
    def test_initialization(self):
        """Test manager initialization."""
        assert self.manager.current_mode == InteractionMode.SELECT
        assert self.manager.hover_element is None
        assert len(self.manager.mode_handlers) >= 3
        assert InteractionMode.SELECT in self.manager.mode_handlers
        assert InteractionMode.PAN in self.manager.mode_handlers
        assert InteractionMode.ZOOM in self.manager.mode_handlers
    
    def test_mode_change(self):
        """Test interaction mode change."""
        with patch.object(self.manager.signals, 'mode_changed') as mock_signal:
            self.manager.set_mode(InteractionMode.PAN)
            
            assert self.manager.current_mode == InteractionMode.PAN
            mock_signal.emit.assert_called_once_with(InteractionMode.PAN.value)
    
    def test_get_elements_at_point(self):
        """Test getting elements at point."""
        mock_elements = [Mock(), Mock()]
        self.mock_spatial_index.query_point.return_value = mock_elements
        
        elements = self.manager.get_elements_at_point(Point(50, 50))
        
        assert elements == mock_elements
        self.mock_overlay_engine.screen_to_document.assert_called_once_with(Point(50, 50))
    
    def test_hover_handling(self):
        """Test hover element handling."""
        mock_element = Mock()
        self.mock_spatial_index.query_point.return_value = [mock_element]
        
        with patch.object(self.manager, '_on_hover_enter') as mock_enter:
            self.manager.handle_hover(Point(25, 25))
            
            assert self.manager.hover_element == mock_element
            mock_enter.assert_called_once_with(mock_element, Point(25, 25))
    
    def test_hover_exit(self):
        """Test hover element exit."""
        mock_element = Mock()
        self.manager.hover_element = mock_element
        self.mock_spatial_index.query_point.return_value = []
        
        with patch.object(self.manager, '_on_hover_exit') as mock_exit:
            self.manager.handle_hover(Point(25, 25))
            
            assert self.manager.hover_element is None
            mock_exit.assert_called_once_with(mock_element)
    
    def test_select_element_single(self):
        """Test single element selection."""
        mock_element = Mock()
        
        self.manager.select_element(mock_element, [])
        
        self.mock_selection_manager.select_single.assert_called_once_with(mock_element)
    
    def test_select_element_ctrl_toggle(self):
        """Test Ctrl+click element toggle."""
        mock_element = Mock()
        
        self.manager.select_element(mock_element, ["ctrl"])
        
        self.mock_selection_manager.toggle_element.assert_called_once_with(mock_element)
    
    def test_select_element_shift_extend(self):
        """Test Shift+click element extend selection."""
        mock_element = Mock()
        
        self.manager.select_element(mock_element, ["shift"])
        
        self.mock_selection_manager.extend_selection.assert_called_once_with(mock_element)
    
    def test_rectangular_selection_workflow(self):
        """Test rectangular selection workflow."""
        # Start selection
        start_point = Point(10, 10)
        self.manager.start_rectangular_selection(start_point)
        
        assert self.manager.is_rectangular_selection
        assert self.manager.selection_rectangle is not None
        assert self.manager.selection_rectangle.x == 10
        assert self.manager.selection_rectangle.y == 10
        
        # Update selection
        current_point = Point(30, 40)
        self.manager.update_rectangular_selection(current_point)
        
        expected_rect = Rectangle(10, 10, 20, 30)
        assert self.manager.selection_rectangle.x == expected_rect.x
        assert self.manager.selection_rectangle.y == expected_rect.y
        assert self.manager.selection_rectangle.width == expected_rect.width
        assert self.manager.selection_rectangle.height == expected_rect.height
        
        # End selection
        self.manager.end_rectangular_selection()
        
        assert not self.manager.is_rectangular_selection
        assert self.manager.selection_rectangle is None
    
    def test_qt_to_mouse_button_conversion(self):
        """Test Qt mouse button conversion."""
        from PyQt6.QtCore import Qt
        
        assert self.manager._qt_to_mouse_button(Qt.MouseButton.LeftButton) == MouseButton.LEFT
        assert self.manager._qt_to_mouse_button(Qt.MouseButton.RightButton) == MouseButton.RIGHT
        assert self.manager._qt_to_mouse_button(Qt.MouseButton.MiddleButton) == MouseButton.MIDDLE
    
    def test_qt_to_modifiers_conversion(self):
        """Test Qt modifiers conversion."""
        from PyQt6.QtCore import Qt
        
        modifiers = (Qt.KeyboardModifier.ControlModifier | 
                    Qt.KeyboardModifier.ShiftModifier)
        
        result = self.manager._qt_to_modifiers(modifiers)
        
        assert "ctrl" in result
        assert "shift" in result
        assert len(result) == 2
    
    def test_interaction_metrics_tracking(self):
        """Test interaction metrics tracking."""
        self.manager._track_interaction_metric("test_interaction", 15.5)
        self.manager._track_interaction_metric("test_interaction", 20.0)
        
        metrics = self.manager.get_interaction_metrics()
        
        assert "test_interaction" in metrics
        assert metrics["test_interaction"]["count"] == 2
        assert metrics["test_interaction"]["average"] == 17.75
        assert metrics["test_interaction"]["min"] == 15.5
        assert metrics["test_interaction"]["max"] == 20.0
    
    def test_register_custom_mode_handler(self):
        """Test registering custom mode handler."""
        custom_mode = InteractionMode.DRAW
        mock_handler = Mock()
        
        self.manager.register_mode_handler(custom_mode, mock_handler)
        
        assert custom_mode in self.manager.mode_handlers
        assert self.manager.mode_handlers[custom_mode] == mock_handler
    
    @patch('src.torematrix.ui.viewer.interactions.time.time')
    def test_performance_tracking(self, mock_time):
        """Test performance tracking for interactions."""
        mock_time.return_value = 100.0
        
        # Simulate interaction timing
        start_time = time.time()
        self.manager._track_interaction_metric("mouse_click", 5.0)
        
        metrics = self.manager.get_interaction_metrics()
        assert "mouse_click" in metrics
        assert metrics["mouse_click"]["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__])