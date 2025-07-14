"""
Interactive Features System for Document Viewer Overlay.
This module provides comprehensive user interaction handling including
mouse, keyboard, and touch events with mode-specific behavior.
"""
from __future__ import annotations

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Tuple, Union

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent, QCursor
from PyQt6.QtWidgets import QWidget

from .coordinates import Rectangle, Point
from .overlay import OverlayEngine, ViewportInfo
from .selection import SelectionManager, SelectionMode
from .spatial import SpatialIndex


class InteractionMode(Enum):
    """Available interaction modes for the overlay system."""
    SELECT = "select"           # Element selection mode
    PAN = "pan"                # Pan/scroll mode
    ZOOM = "zoom"              # Zoom mode
    DRAW = "draw"              # Drawing mode
    MEASURE = "measure"        # Measurement mode
    ANNOTATE = "annotate"      # Annotation mode


class MouseButton(Enum):
    """Mouse button identifiers."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass
class InteractionEvent:
    """Base class for interaction events."""
    timestamp: float = field(default_factory=time.time)
    position: Point = field(default_factory=lambda: Point(0, 0))
    modifiers: List[str] = field(default_factory=list)


@dataclass
class MouseInteractionEvent(InteractionEvent):
    """Mouse interaction event."""
    button: MouseButton
    event_type: str  # mousedown, mouseup, mousemove, wheel
    delta: Optional[Point] = None  # For wheel events


@dataclass
class KeyboardInteractionEvent(InteractionEvent):
    """Keyboard interaction event."""
    key: str
    event_type: str  # keydown, keyup
    text: str = ""


class InteractionHandler(ABC):
    """Abstract base class for interaction mode handlers."""
    
    @abstractmethod
    def handle_mouse_down(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse button press. Return True if handled."""
        pass
    
    @abstractmethod
    def handle_mouse_up(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse button release. Return True if handled."""
        pass
    
    @abstractmethod
    def handle_mouse_move(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse movement. Return True if handled."""
        pass
    
    @abstractmethod
    def handle_key_down(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key press. Return True if handled."""
        pass
    
    @abstractmethod
    def handle_key_up(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key release. Return True if handled."""
        pass


class SelectionModeHandler(InteractionHandler):
    """Handler for element selection interactions."""
    
    def __init__(self, interaction_manager: 'InteractionManager'):
        self.interaction_manager = interaction_manager
        self.drag_start: Optional[Point] = None
        self.is_dragging: bool = False
        
    def handle_mouse_down(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse down for selection."""
        if event.button == MouseButton.LEFT:
            self.drag_start = event.position
            self.is_dragging = False
            
            # Find element under cursor
            elements = self.interaction_manager.get_elements_at_point(event.position)
            
            if elements:
                element = elements[0]  # Top-most element
                self.interaction_manager.select_element(element, event.modifiers)
            else:
                # Start rectangular selection if no element found
                if not ("ctrl" in event.modifiers or "shift" in event.modifiers):
                    self.interaction_manager.clear_selection()
                    
            return True
        return False
    
    def handle_mouse_up(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse up for selection."""
        if event.button == MouseButton.LEFT and self.drag_start:
            if self.is_dragging:
                # Complete rectangular selection
                rect = Rectangle(
                    min(self.drag_start.x, event.position.x),
                    min(self.drag_start.y, event.position.y),
                    abs(event.position.x - self.drag_start.x),
                    abs(event.position.y - self.drag_start.y)
                )
                self.interaction_manager.select_elements_in_rectangle(rect, event.modifiers)
                self.interaction_manager.end_rectangular_selection()
            
            self.drag_start = None
            self.is_dragging = False
            return True
        return False
    
    def handle_mouse_move(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse move for selection."""
        if self.drag_start:
            # Check if we should start dragging
            distance = ((event.position.x - self.drag_start.x) ** 2 + 
                       (event.position.y - self.drag_start.y) ** 2) ** 0.5
            
            if distance > 5:  # 5px threshold for drag start
                if not self.is_dragging:
                    self.is_dragging = True
                    self.interaction_manager.start_rectangular_selection(self.drag_start)
                
                # Update selection rectangle
                self.interaction_manager.update_rectangular_selection(event.position)
                return True
        else:
            # Handle hover
            self.interaction_manager.handle_hover(event.position)
        
        return False
    
    def handle_key_down(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key down for selection."""
        if event.key == "Escape":
            self.interaction_manager.clear_selection()
            return True
        elif event.key == "Ctrl+A":
            self.interaction_manager.select_all()
            return True
        elif event.key == "Delete":
            self.interaction_manager.delete_selected()
            return True
        return False
    
    def handle_key_up(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key up for selection."""
        return False


class PanModeHandler(InteractionHandler):
    """Handler for pan/scroll interactions."""
    
    def __init__(self, interaction_manager: 'InteractionManager'):
        self.interaction_manager = interaction_manager
        self.pan_start: Optional[Point] = None
        self.is_panning: bool = False
        
    def handle_mouse_down(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse down for pan."""
        if event.button == MouseButton.LEFT:
            self.pan_start = event.position
            self.is_panning = True
            return True
        return False
    
    def handle_mouse_up(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse up for pan."""
        if event.button == MouseButton.LEFT:
            self.pan_start = None
            self.is_panning = False
            return True
        return False
    
    def handle_mouse_move(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse move for pan."""
        if self.is_panning and self.pan_start:
            delta = Point(
                event.position.x - self.pan_start.x,
                event.position.y - self.pan_start.y
            )
            self.interaction_manager.pan_viewport(delta)
            self.pan_start = event.position
            return True
        return False
    
    def handle_key_down(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key down for pan."""
        return False
    
    def handle_key_up(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key up for pan."""
        return False


class ZoomModeHandler(InteractionHandler):
    """Handler for zoom interactions."""
    
    def __init__(self, interaction_manager: 'InteractionManager'):
        self.interaction_manager = interaction_manager
        
    def handle_mouse_down(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse down for zoom."""
        if event.button == MouseButton.LEFT:
            # Zoom in at cursor position
            self.interaction_manager.zoom_at_point(event.position, 1.2)
            return True
        elif event.button == MouseButton.RIGHT:
            # Zoom out at cursor position
            self.interaction_manager.zoom_at_point(event.position, 0.8)
            return True
        return False
    
    def handle_mouse_up(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse up for zoom."""
        return False
    
    def handle_mouse_move(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse move for zoom."""
        return False
    
    def handle_key_down(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key down for zoom."""
        if event.key == "Plus" or event.key == "Equal":
            self.interaction_manager.zoom_viewport(1.2)
            return True
        elif event.key == "Minus":
            self.interaction_manager.zoom_viewport(0.8)
            return True
        return False
    
    def handle_key_up(self, event: KeyboardInteractionEvent) -> bool:
        """Handle key up for zoom."""
        return False


class InteractionSignals(QObject):
    """Signals for interaction events."""
    mode_changed = pyqtSignal(str)  # mode_name
    element_hovered = pyqtSignal(object)  # element
    element_clicked = pyqtSignal(object, list)  # element, modifiers
    selection_changed = pyqtSignal(list)  # selected_elements
    viewport_changed = pyqtSignal(object)  # viewport_info
    interaction_started = pyqtSignal(str)  # interaction_type
    interaction_completed = pyqtSignal(str, float)  # interaction_type, duration


class InteractionManager(QObject):
    """
    Main interaction manager for the overlay system.
    Handles all user interactions and coordinates with other systems.
    """
    
    def __init__(self, overlay_engine: OverlayEngine, 
                 selection_manager: SelectionManager,
                 spatial_index: SpatialIndex):
        super().__init__()
        
        # Core dependencies
        self.overlay_engine = overlay_engine
        self.selection_manager = selection_manager
        self.spatial_index = spatial_index
        
        # Interaction state
        self.current_mode = InteractionMode.SELECT
        self.hover_element = None
        self.last_interaction_time = 0.0
        
        # Mode handlers
        self.mode_handlers: Dict[InteractionMode, InteractionHandler] = {
            InteractionMode.SELECT: SelectionModeHandler(self),
            InteractionMode.PAN: PanModeHandler(self),
            InteractionMode.ZOOM: ZoomModeHandler(self),
        }
        
        # Signals
        self.signals = InteractionSignals()
        
        # Performance tracking
        self.interaction_metrics: Dict[str, List[float]] = {}
        
        # Hover timer for tooltip delay
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._on_hover_timeout)
        
        # Rectangle selection state
        self.selection_rectangle: Optional[Rectangle] = None
        self.is_rectangular_selection = False
        
    def set_mode(self, mode: InteractionMode) -> None:
        """Set the current interaction mode."""
        if mode != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = mode
            self.signals.mode_changed.emit(mode.value)
            
    def handle_mouse_event(self, event: QMouseEvent) -> bool:
        """Handle Qt mouse events."""
        start_time = time.time()
        
        # Convert Qt event to our event format
        button = self._qt_to_mouse_button(event.button())
        position = Point(event.position().x(), event.position().y())
        modifiers = self._qt_to_modifiers(event.modifiers())
        
        interaction_event = MouseInteractionEvent(
            button=button,
            event_type=self._qt_mouse_event_type(event.type()),
            position=position,
            modifiers=modifiers,
            timestamp=start_time
        )
        
        # Handle special cases
        if interaction_event.event_type == "mousemove":
            handled = self._handle_mouse_move(interaction_event)
        elif interaction_event.event_type == "mousedown":
            handled = self._handle_mouse_down(interaction_event)
        elif interaction_event.event_type == "mouseup":
            handled = self._handle_mouse_up(interaction_event)
        else:
            handled = False
        
        # Track performance
        duration = (time.time() - start_time) * 1000
        self._track_interaction_metric("mouse_" + interaction_event.event_type, duration)
        
        self.last_interaction_time = start_time
        return handled
    
    def handle_wheel_event(self, event: QWheelEvent) -> bool:
        """Handle Qt wheel events."""
        start_time = time.time()
        
        position = Point(event.position().x(), event.position().y())
        delta = Point(event.angleDelta().x(), event.angleDelta().y())
        modifiers = self._qt_to_modifiers(event.modifiers())
        
        # Handle zoom with wheel
        zoom_factor = 1.0 + (delta.y / 1200.0)  # Smooth zoom
        self.zoom_at_point(position, zoom_factor)
        
        # Track performance
        duration = (time.time() - start_time) * 1000
        self._track_interaction_metric("wheel", duration)
        
        return True
    
    def handle_key_event(self, event: QKeyEvent) -> bool:
        """Handle Qt keyboard events."""
        start_time = time.time()
        
        key_event = KeyboardInteractionEvent(
            key=event.key(),
            event_type="keydown" if event.type() == event.Type.KeyPress else "keyup",
            text=event.text(),
            timestamp=start_time
        )
        
        # Get current mode handler
        handler = self.mode_handlers.get(self.current_mode)
        if handler:
            if key_event.event_type == "keydown":
                handled = handler.handle_key_down(key_event)
            else:
                handled = handler.handle_key_up(key_event)
        else:
            handled = False
        
        # Track performance
        duration = (time.time() - start_time) * 1000
        self._track_interaction_metric("key_" + key_event.event_type, duration)
        
        return handled
    
    def _handle_mouse_down(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse down events."""
        self.signals.interaction_started.emit("mouse_down")
        
        handler = self.mode_handlers.get(self.current_mode)
        if handler:
            return handler.handle_mouse_down(event)
        return False
    
    def _handle_mouse_up(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse up events."""
        handler = self.mode_handlers.get(self.current_mode)
        if handler:
            handled = handler.handle_mouse_up(event)
            if handled:
                self.signals.interaction_completed.emit(
                    "mouse_up", 
                    (time.time() - self.last_interaction_time) * 1000
                )
            return handled
        return False
    
    def _handle_mouse_move(self, event: MouseInteractionEvent) -> bool:
        """Handle mouse move events."""
        handler = self.mode_handlers.get(self.current_mode)
        if handler:
            return handler.handle_mouse_move(event)
        return False
    
    def handle_hover(self, position: Point) -> None:
        """Handle hover interactions."""
        # Find elements under cursor
        elements = self.get_elements_at_point(position)
        
        if elements:
            element = elements[0]  # Top-most element
            if element != self.hover_element:
                self._on_hover_enter(element, position)
                self.hover_element = element
        else:
            if self.hover_element:
                self._on_hover_exit(self.hover_element)
                self.hover_element = None
    
    def _on_hover_enter(self, element, position: Point) -> None:
        """Handle hover enter."""
        self.signals.element_hovered.emit(element)
        
        # Start hover timer for tooltip
        self.hover_timer.stop()
        self.hover_timer.start(500)  # 500ms delay
        
        # Update visual style
        if hasattr(self.overlay_engine, 'set_element_style'):
            self.overlay_engine.set_element_style(element, 'hover')
    
    def _on_hover_exit(self, element) -> None:
        """Handle hover exit."""
        # Stop hover timer
        self.hover_timer.stop()
        
        # Reset visual style
        if hasattr(self.overlay_engine, 'reset_element_style'):
            self.overlay_engine.reset_element_style(element)
    
    def _on_hover_timeout(self) -> None:
        """Handle hover timeout for tooltip display."""
        if self.hover_element:
            # Import here to avoid circular imports
            from .tooltips import TooltipManager
            tooltip_manager = TooltipManager.get_instance()
            if tooltip_manager:
                tooltip_manager.show_tooltip(self.hover_element, self._get_cursor_position())
    
    def get_elements_at_point(self, position: Point) -> List[Any]:
        """Get elements at the specified position."""
        # Convert screen position to document coordinates
        doc_position = self.overlay_engine.screen_to_document(position)
        
        # Query spatial index
        return self.spatial_index.query_point(doc_position)
    
    def select_element(self, element: Any, modifiers: List[str]) -> None:
        """Select an element with modifier support."""
        if "ctrl" in modifiers:
            self.selection_manager.toggle_element(element)
        elif "shift" in modifiers:
            self.selection_manager.extend_selection(element)
        else:
            self.selection_manager.select_single(element)
        
        self.signals.element_clicked.emit(element, modifiers)
        self.signals.selection_changed.emit(self.selection_manager.get_selected_elements())
    
    def select_elements_in_rectangle(self, rect: Rectangle, modifiers: List[str]) -> None:
        """Select elements within a rectangle."""
        # Convert screen rectangle to document coordinates
        doc_rect = self.overlay_engine.screen_to_document_rect(rect)
        
        # Query spatial index for elements in rectangle
        elements = self.spatial_index.query_rectangle(doc_rect)
        
        if "ctrl" in modifiers:
            for element in elements:
                self.selection_manager.toggle_element(element)
        elif "shift" in modifiers:
            for element in elements:
                self.selection_manager.add_to_selection(element)
        else:
            self.selection_manager.select_multiple(elements)
        
        self.signals.selection_changed.emit(self.selection_manager.get_selected_elements())
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self.selection_manager.clear_selection()
        self.signals.selection_changed.emit([])
    
    def select_all(self) -> None:
        """Select all visible elements."""
        viewport = self.overlay_engine.get_viewport_info()
        elements = self.spatial_index.query_rectangle(viewport.bounds)
        self.selection_manager.select_multiple(elements)
        self.signals.selection_changed.emit(self.selection_manager.get_selected_elements())
    
    def delete_selected(self) -> None:
        """Delete selected elements."""
        selected = self.selection_manager.get_selected_elements()
        for element in selected:
            # Remove from spatial index and overlay
            self.spatial_index.remove_element(element)
            self.overlay_engine.remove_element(element)
        
        self.clear_selection()
    
    def start_rectangular_selection(self, start_point: Point) -> None:
        """Start rectangular selection."""
        self.selection_rectangle = Rectangle(start_point.x, start_point.y, 0, 0)
        self.is_rectangular_selection = True
        
        # Show selection rectangle on overlay
        if hasattr(self.overlay_engine, 'show_selection_rectangle'):
            self.overlay_engine.show_selection_rectangle(self.selection_rectangle)
    
    def update_rectangular_selection(self, current_point: Point) -> None:
        """Update rectangular selection."""
        if self.selection_rectangle and self.is_rectangular_selection:
            # Update rectangle dimensions
            start_x = self.selection_rectangle.x
            start_y = self.selection_rectangle.y
            
            self.selection_rectangle = Rectangle(
                min(start_x, current_point.x),
                min(start_y, current_point.y),
                abs(current_point.x - start_x),
                abs(current_point.y - start_y)
            )
            
            # Update visualization
            if hasattr(self.overlay_engine, 'update_selection_rectangle'):
                self.overlay_engine.update_selection_rectangle(self.selection_rectangle)
    
    def end_rectangular_selection(self) -> None:
        """End rectangular selection."""
        self.selection_rectangle = None
        self.is_rectangular_selection = False
        
        # Hide selection rectangle
        if hasattr(self.overlay_engine, 'hide_selection_rectangle'):
            self.overlay_engine.hide_selection_rectangle()
    
    def pan_viewport(self, delta: Point) -> None:
        """Pan the viewport by the specified delta."""
        if hasattr(self.overlay_engine, 'pan_viewport'):
            self.overlay_engine.pan_viewport(delta)
            self.signals.viewport_changed.emit(self.overlay_engine.get_viewport_info())
    
    def zoom_viewport(self, factor: float) -> None:
        """Zoom the viewport by the specified factor."""
        if hasattr(self.overlay_engine, 'zoom_viewport'):
            self.overlay_engine.zoom_viewport(factor)
            self.signals.viewport_changed.emit(self.overlay_engine.get_viewport_info())
    
    def zoom_at_point(self, point: Point, factor: float) -> None:
        """Zoom at a specific point."""
        if hasattr(self.overlay_engine, 'zoom_at_point'):
            self.overlay_engine.zoom_at_point(point, factor)
            self.signals.viewport_changed.emit(self.overlay_engine.get_viewport_info())
    
    def _get_cursor_position(self) -> Point:
        """Get current cursor position."""
        cursor_pos = QCursor.pos()
        return Point(cursor_pos.x(), cursor_pos.y())
    
    def _qt_to_mouse_button(self, qt_button) -> MouseButton:
        """Convert Qt mouse button to our enum."""
        from PyQt6.QtCore import Qt
        
        if qt_button == Qt.MouseButton.LeftButton:
            return MouseButton.LEFT
        elif qt_button == Qt.MouseButton.RightButton:
            return MouseButton.RIGHT
        elif qt_button == Qt.MouseButton.MiddleButton:
            return MouseButton.MIDDLE
        else:
            return MouseButton.LEFT  # Default
    
    def _qt_to_modifiers(self, qt_modifiers) -> List[str]:
        """Convert Qt modifiers to our format."""
        from PyQt6.QtCore import Qt
        
        modifiers = []
        if qt_modifiers & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if qt_modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if qt_modifiers & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if qt_modifiers & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("meta")
        
        return modifiers
    
    def _qt_mouse_event_type(self, qt_type) -> str:
        """Convert Qt mouse event type to our format."""
        from PyQt6.QtCore import QEvent
        
        if qt_type == QEvent.Type.MouseButtonPress:
            return "mousedown"
        elif qt_type == QEvent.Type.MouseButtonRelease:
            return "mouseup"
        elif qt_type == QEvent.Type.MouseMove:
            return "mousemove"
        else:
            return "unknown"
    
    def _track_interaction_metric(self, interaction_type: str, duration: float) -> None:
        """Track interaction performance metrics."""
        if interaction_type not in self.interaction_metrics:
            self.interaction_metrics[interaction_type] = []
        
        self.interaction_metrics[interaction_type].append(duration)
        
        # Keep only last 100 measurements
        if len(self.interaction_metrics[interaction_type]) > 100:
            self.interaction_metrics[interaction_type] = (
                self.interaction_metrics[interaction_type][-100:]
            )
    
    def get_interaction_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get interaction performance metrics."""
        metrics = {}
        
        for interaction_type, durations in self.interaction_metrics.items():
            if durations:
                metrics[interaction_type] = {
                    "average": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "count": len(durations)
                }
        
        return metrics
    
    def register_mode_handler(self, mode: InteractionMode, handler: InteractionHandler) -> None:
        """Register a custom interaction mode handler."""
        self.mode_handlers[mode] = handler
    
    def get_current_mode(self) -> InteractionMode:
        """Get the current interaction mode."""
        return self.current_mode