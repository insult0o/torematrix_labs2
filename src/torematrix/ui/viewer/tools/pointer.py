"""
Pointer Tool for single-element selection.

This tool provides precise single-element selection with click-to-select behavior,
hover effects, and double-click expansion functionality.
"""

import time
from typing import Optional, List, Any

from PyQt6.QtCore import QPoint, QRect, QTimer, Qt
from PyQt6.QtGui import QPainter, QCursor, QPen, QColor, QBrush

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle
from ..layers import LayerElement


class PointerTool(SelectionTool):
    """
    Single-element selection tool with click-to-select behavior.
    
    Features:
    - Precise single-element selection
    - Hover effects with visual feedback
    - Double-click expansion for text and related elements
    - Modifier key support for multi-selection
    - Smart cursor changes based on element type
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Selection state
        self._current_element: Optional[LayerElement] = None
        self._hover_element: Optional[LayerElement] = None
        self._click_start_point: Optional[QPoint] = None
        
        # Double-click detection
        self._last_click_time = 0
        self._click_count = 0
        self._double_click_timeout = 300  # ms
        
        # Hover detection
        self._hover_timer = QTimer()
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._on_hover_timeout)
        self._hover_delay = 500  # ms
        
        # Visual feedback
        self._selection_color = QColor(0, 120, 215)  # Blue
        self._hover_color = QColor(0, 120, 215, 100)  # Semi-transparent blue
        self._selection_width = 2
        self._hover_width = 1
        
        # Performance tracking
        self._selection_hits = 0
        self._selection_misses = 0
    
    def activate(self) -> None:
        """Activate pointer tool with appropriate cursor."""
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def deactivate(self) -> None:
        """Deactivate pointer tool and clear state."""
        self._update_state(ToolState.INACTIVE)
        self._current_element = None
        self._hover_element = None
        self._click_start_point = None
        self._hover_timer.stop()
        self.clear_selection()
    
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse press for element selection."""
        if self._state != ToolState.ACTIVE:
            return False
        
        start_time = time.time()
        self._click_start_point = point
        
        # Handle double-click detection
        current_time = time.time() * 1000  # Convert to milliseconds
        if (current_time - self._last_click_time) < self._double_click_timeout:
            self._click_count += 1
        else:
            self._click_count = 1
        self._last_click_time = current_time
        
        # Find element at click position
        element = self._find_element_at_point(point)
        
        if element:
            self._current_element = element
            self._update_state(ToolState.SELECTING)
            self._selection_hits += 1
            
            # Handle double-click for expansion
            if self._click_count >= 2:
                self._handle_double_click(element, point, modifiers)
            
            operation_time = time.time() - start_time
            self._update_metrics(operation_time)
            return True
        else:
            # Clear selection if clicking empty space (unless adding to selection)
            if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                self.clear_selection()
            
            self._selection_misses += 1
            self._update_state(ToolState.ACTIVE)
            
            operation_time = time.time() - start_time
            self._update_metrics(operation_time)
            return False
    
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse movement for hover effects."""
        if self._state in [ToolState.ACTIVE, ToolState.SELECTED]:
            # Find element under cursor
            element = self._find_element_at_point(point)
            
            if element != self._hover_element:
                self._hover_element = element
                
                # Update cursor and state based on hover
                if element:
                    self._update_cursor_for_element(element)
                    self._update_state(ToolState.HOVER)
                    
                    # Start hover timer for delayed effects
                    self._hover_timer.start(self._hover_delay)
                else:
                    self.set_cursor(QCursor(Qt.CursorShape.ArrowCursor))
                    self._update_state(ToolState.ACTIVE)
                    self._hover_timer.stop()
            
            return True
        
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Complete selection on mouse release."""
        if self._state == ToolState.SELECTING:
            if self._current_element and self._click_start_point:
                # Check if release is within click tolerance
                if self._is_within_click_tolerance(point, self._click_start_point):
                    # Create selection result
                    result = SelectionResult(
                        elements=[self._current_element],
                        geometry=self._get_element_bounds(self._current_element),
                        tool_type="pointer",
                        timestamp=time.time(),
                        metadata={
                            "click_point": self._qpoint_to_point(point),
                            "click_count": self._click_count,
                            "element_type": self._get_element_type(self._current_element),
                            "modifiers": int(modifiers)
                        }
                    )
                    
                    # Update selection
                    self._current_selection = result
                    self._update_state(ToolState.SELECTED)
                    self.selection_changed.emit(result)
                    
                    return True
                else:
                    # Click was outside tolerance, cancel selection
                    self._current_element = None
                    self._update_state(ToolState.ACTIVE)
            
            return True
        
        return False
    
    def handle_mouse_double_click(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle double-click for element expansion."""
        element = self._find_element_at_point(point)
        if element:
            self._handle_double_click(element, point, modifiers)
            return True
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle keyboard input."""
        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            return True
        
        return False
    
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render selection highlight and hover effects."""
        if not self._visible:
            return
        
        # Draw selection highlight
        if self._current_element and self._state == ToolState.SELECTED:
            bounds = self._get_element_bounds(self._current_element)
            if bounds:
                qrect = self._rectangle_to_qrect(bounds)
                painter.setPen(QPen(self._selection_color, self._selection_width))
                painter.setBrush(QBrush())  # No fill
                painter.drawRect(qrect)
                
                # Draw corner handles for visual feedback
                self._draw_selection_handles(painter, qrect)
        
        # Draw hover highlight
        if self._hover_element and self._state == ToolState.HOVER:
            bounds = self._get_element_bounds(self._hover_element)
            if bounds:
                qrect = self._rectangle_to_qrect(bounds)
                painter.setPen(QPen(self._hover_color, self._hover_width))
                painter.setBrush(QBrush())  # No fill
                painter.drawRect(qrect)
    
    def _find_element_at_point(self, point: QPoint) -> Optional[LayerElement]:
        """Find element at given point using coordinate system."""
        # Convert to document coordinates
        doc_point = self._qpoint_to_point(point)
        
        # TODO: Implement actual element finding using overlay API
        # For now, return None as placeholder
        # This would typically query the overlay system for elements at the point
        return None
    
    def _handle_double_click(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle double-click for extended selection."""
        element_type = self._get_element_type(element)
        
        if element_type == "text":
            # For text elements, select whole word or paragraph
            self._expand_text_selection(element, point)
        elif element_type == "table":
            # For table elements, select row/column or whole table
            self._expand_table_selection(element, point)
        elif element_type == "group":
            # For grouped elements, select entire group
            self._expand_group_selection(element, point)
        else:
            # For other elements, select related elements
            self._expand_related_selection(element, point)
    
    def _expand_text_selection(self, element: LayerElement, point: QPoint) -> None:
        """Expand text selection to word or paragraph."""
        # TODO: Implement text expansion logic
        # This would analyze the text element and expand selection based on position
        pass
    
    def _expand_table_selection(self, element: LayerElement, point: QPoint) -> None:
        """Expand table selection to row, column, or entire table."""
        # TODO: Implement table expansion logic
        # This would analyze the table structure and expand selection
        pass
    
    def _expand_group_selection(self, element: LayerElement, point: QPoint) -> None:
        """Expand selection to entire group."""
        # TODO: Implement group expansion logic
        # This would find all elements in the same group
        pass
    
    def _expand_related_selection(self, element: LayerElement, point: QPoint) -> None:
        """Expand selection to related elements."""
        # TODO: Implement related element detection
        # This would find spatially or logically related elements
        pass
    
    def _is_within_click_tolerance(self, point1: QPoint, point2: QPoint) -> bool:
        """Check if points are within click tolerance."""
        tolerance = self.get_config('click_tolerance') or 3
        return self._get_distance(point1, point2) <= tolerance
    
    def _update_cursor_for_element(self, element: LayerElement) -> None:
        """Update cursor based on element type."""
        element_type = self._get_element_type(element)
        
        cursor_map = {
            "text": Qt.CursorShape.IBeamCursor,
            "image": Qt.CursorShape.OpenHandCursor,
            "table": Qt.CursorShape.PointingHandCursor,
            "formula": Qt.CursorShape.CrossCursor,
            "link": Qt.CursorShape.PointingHandCursor,
            "button": Qt.CursorShape.PointingHandCursor
        }
        
        cursor_shape = cursor_map.get(element_type, Qt.CursorShape.PointingHandCursor)
        self.set_cursor(QCursor(cursor_shape))
    
    def _get_element_type(self, element: LayerElement) -> str:
        """Get element type string."""
        if hasattr(element, 'element_type'):
            return element.element_type
        elif hasattr(element, 'type'):
            return element.type
        else:
            return "unknown"
    
    def _get_element_bounds(self, element: LayerElement) -> Optional[Rectangle]:
        """Get element bounding rectangle."""
        if hasattr(element, 'get_bounds'):
            return element.get_bounds()
        elif hasattr(element, 'bounds'):
            return element.bounds
        elif hasattr(element, 'bounding_rect'):
            return element.bounding_rect
        else:
            return None
    
    def _draw_selection_handles(self, painter: QPainter, rect: QRect) -> None:
        """Draw selection handles on corners."""
        handle_size = 6
        half_size = handle_size // 2
        
        # Define handle positions
        handles = [
            QPoint(rect.left(), rect.top()),          # Top-left
            QPoint(rect.right(), rect.top()),         # Top-right
            QPoint(rect.left(), rect.bottom()),       # Bottom-left
            QPoint(rect.right(), rect.bottom())       # Bottom-right
        ]
        
        # Draw handles
        painter.setPen(QPen(self._selection_color, 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))  # White fill
        
        for handle in handles:
            handle_rect = QRect(
                handle.x() - half_size,
                handle.y() - half_size,
                handle_size,
                handle_size
            )
            painter.drawRect(handle_rect)
    
    def _on_hover_timeout(self) -> None:
        """Handle hover timeout for delayed effects."""
        if self._hover_element:
            # Show tooltip or additional hover information
            # TODO: Implement tooltip system
            pass
    
    def get_selection_accuracy(self) -> float:
        """Get selection accuracy percentage."""
        total_attempts = self._selection_hits + self._selection_misses
        if total_attempts == 0:
            return 0.0
        return (self._selection_hits / total_attempts) * 100.0
    
    def get_tool_info(self) -> dict:
        """Get tool information and statistics."""
        return {
            "name": "Pointer Tool",
            "type": "pointer",
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "selection_hits": self._selection_hits,
            "selection_misses": self._selection_misses,
            "selection_accuracy": self.get_selection_accuracy(),
            "current_element": self._current_element is not None,
            "hover_element": self._hover_element is not None,
            "click_count": self._click_count,
            "metrics": self.get_metrics()
        }