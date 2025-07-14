"""
Rectangle Tool for area-based selection.

This tool provides rectangular selection with drag-to-select behavior,
real-time preview, and modifier key support for selection operations.
"""

import time
from typing import Optional, List, Set

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QPainter, QCursor, QPen, QColor, QBrush

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from ..multi_select import SelectionStrategy


class RectangleTool(SelectionTool):
    """
    Area-based selection tool with drag-to-select rectangle.
    
    Features:
    - Drag-to-select rectangular areas
    - Real-time preview of elements within selection
    - Multiple selection strategies (contains, intersects, etc.)
    - Modifier key support for selection operations
    - Visual feedback with dashed selection rectangle
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Selection state
        self._start_point: Optional[QPoint] = None
        self._current_point: Optional[QPoint] = None
        self._current_rect: Optional[QRect] = None
        self._is_dragging = False
        
        # Preview elements
        self._preview_elements: Set[LayerElement] = set()
        self._final_elements: Set[LayerElement] = set()
        
        # Configuration
        self._drag_threshold = 3  # pixels
        self._selection_strategy = SelectionStrategy.INTERSECTS
        self._min_selection_size = 5  # minimum width/height
        
        # Visual styling
        self._selection_color = QColor(255, 140, 0)  # Orange
        self._preview_color = QColor(255, 140, 0, 100)  # Semi-transparent orange
        self._selection_width = 1
        self._preview_width = 1
        
        # Performance tracking
        self._drag_operations = 0
        self._elements_processed = 0
        self._last_preview_time = 0
    
    def activate(self) -> None:
        """Activate rectangle tool with crosshair cursor."""
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.CrossCursor))
    
    def deactivate(self) -> None:
        """Deactivate rectangle tool and reset state."""
        self._update_state(ToolState.INACTIVE)
        self._reset_selection()
    
    def set_selection_strategy(self, strategy: SelectionStrategy) -> None:
        """Set the selection strategy for element inclusion."""
        self._selection_strategy = strategy
    
    def get_selection_strategy(self) -> SelectionStrategy:
        """Get the current selection strategy."""
        return self._selection_strategy
    
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Start rectangle selection."""
        if self._state != ToolState.ACTIVE:
            return False
        
        start_time = time.time()
        
        # Initialize selection
        self._start_point = point
        self._current_point = point
        self._current_rect = QRect(point, point)
        self._is_dragging = False
        self._preview_elements.clear()
        self._final_elements.clear()
        
        self._update_state(ToolState.SELECTING)
        
        operation_time = time.time() - start_time
        self._update_metrics(operation_time)
        
        return True
    
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Update rectangle during drag."""
        if self._state == ToolState.SELECTING and self._start_point:
            self._current_point = point
            self._current_rect = QRect(self._start_point, point).normalized()
            
            # Check if we've moved beyond drag threshold
            if not self._is_dragging:
                distance = self._get_distance(self._start_point, point)
                if distance > self._drag_threshold:
                    self._is_dragging = True
                    self._drag_operations += 1
                    self.set_cursor(QCursor(Qt.CursorShape.SizeAllCursor))
            
            # Update preview if dragging
            if self._is_dragging:
                self._update_preview_selection()
            
            return True
        
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Complete rectangle selection."""
        if self._state == ToolState.SELECTING and self._start_point:
            start_time = time.time()
            
            # Check if we actually dragged or just clicked
            if not self._is_dragging:
                distance = self._get_distance(self._start_point, point)
                if distance <= self._drag_threshold:
                    # Single click - clear selection unless adding
                    if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                        self.clear_selection()
                    self._reset_selection()
                    return True
            
            # Ensure minimum selection size
            if (self._current_rect.width() < self._min_selection_size and 
                self._current_rect.height() < self._min_selection_size):
                self._reset_selection()
                return True
            
            # Find final elements in selection
            self._final_elements = self._find_elements_in_rect(self._current_rect)
            
            if self._final_elements:
                # Calculate selection bounds
                selection_bounds = self._calculate_selection_bounds(self._final_elements)
                
                # Create selection result
                result = SelectionResult(
                    elements=list(self._final_elements),
                    geometry=selection_bounds,
                    tool_type="rectangle",
                    timestamp=time.time(),
                    metadata={
                        "start_point": self._qpoint_to_point(self._start_point),
                        "end_point": self._qpoint_to_point(point),
                        "selection_rect": self._qrect_to_rectangle(self._current_rect),
                        "area": self._current_rect.width() * self._current_rect.height(),
                        "element_count": len(self._final_elements),
                        "selection_strategy": self._selection_strategy.value,
                        "modifiers": int(modifiers)
                    }
                )
                
                # Update selection
                self._current_selection = result
                self._update_state(ToolState.SELECTED)
                self.selection_changed.emit(result)
                
                operation_time = time.time() - start_time
                self._update_metrics(operation_time)
                
                return True
            else:
                # No elements selected
                self._reset_selection()
                return True
        
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle keyboard input."""
        if key == Qt.Key.Key_Escape:
            if self._state == ToolState.SELECTING:
                self._reset_selection()
            else:
                self.clear_selection()
            return True
        
        # Strategy switching shortcuts
        if key == Qt.Key.Key_1:
            self.set_selection_strategy(SelectionStrategy.CONTAINS)
            return True
        elif key == Qt.Key.Key_2:
            self.set_selection_strategy(SelectionStrategy.INTERSECTS)
            return True
        elif key == Qt.Key.Key_3:
            self.set_selection_strategy(SelectionStrategy.CENTER_POINT)
            return True
        elif key == Qt.Key.Key_4:
            self.set_selection_strategy(SelectionStrategy.MAJORITY)
            return True
        
        return False
    
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render selection rectangle and preview."""
        if not self._visible:
            return
        
        # Draw selection rectangle during drag
        if self._current_rect and self._state == ToolState.SELECTING:
            painter.setPen(QPen(self._selection_color, self._selection_width, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(self._selection_color.red(), 
                                         self._selection_color.green(), 
                                         self._selection_color.blue(), 30)))
            painter.drawRect(self._current_rect)
            
            # Draw selection info
            self._draw_selection_info(painter, self._current_rect)
        
        # Highlight preview elements during drag
        if self._preview_elements and self._state == ToolState.SELECTING:
            painter.setPen(QPen(self._preview_color, self._preview_width))
            painter.setBrush(QBrush())  # No fill
            
            for element in self._preview_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    qrect = self._rectangle_to_qrect(bounds)
                    painter.drawRect(qrect)
        
        # Draw final selection
        if self._final_elements and self._state == ToolState.SELECTED:
            painter.setPen(QPen(self._selection_color, self._selection_width + 1))
            painter.setBrush(QBrush())  # No fill
            
            for element in self._final_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    qrect = self._rectangle_to_qrect(bounds)
                    painter.drawRect(qrect)
            
            # Draw final selection rectangle
            if self._current_rect:
                painter.setPen(QPen(self._selection_color, self._selection_width))
                painter.setBrush(QBrush())  # No fill
                painter.drawRect(self._current_rect)
    
    def _update_preview_selection(self) -> None:
        """Update preview elements during drag."""
        if not self._current_rect:
            return
        
        start_time = time.time()
        
        # Find elements in current rectangle
        new_preview = self._find_elements_in_rect(self._current_rect)
        
        # Update preview if changed
        if new_preview != self._preview_elements:
            self._preview_elements = new_preview
            
            # Create preview result
            if self._preview_elements:
                preview_bounds = self._calculate_selection_bounds(self._preview_elements)
                preview_result = SelectionResult(
                    elements=list(self._preview_elements),
                    geometry=preview_bounds,
                    tool_type="rectangle",
                    timestamp=time.time(),
                    metadata={
                        "preview": True,
                        "element_count": len(self._preview_elements),
                        "selection_strategy": self._selection_strategy.value
                    }
                )
                
                self._preview_selection = preview_result
                self.preview_changed.emit(preview_result)
        
        self._last_preview_time = time.time() - start_time
    
    def _find_elements_in_rect(self, rect: QRect) -> Set[LayerElement]:
        """Find all elements that match the selection criteria within rectangle."""
        if not rect:
            return set()
        
        # Convert QRect to Rectangle
        selection_rect = self._qrect_to_rectangle(rect)
        
        # TODO: Get elements from overlay API
        # For now, return empty set as placeholder
        elements = self._get_elements_in_area(selection_rect)
        
        # Filter elements based on selection strategy
        selected_elements = set()
        for element in elements:
            if self._element_matches_strategy(element, selection_rect):
                selected_elements.add(element)
        
        self._elements_processed += len(elements)
        return selected_elements
    
    def _get_elements_in_area(self, area: Rectangle) -> List[LayerElement]:
        """Get all elements in the specified area."""
        # TODO: Implement actual element retrieval from overlay API
        # This would typically query the spatial index or layer system
        return []
    
    def _element_matches_strategy(self, element: LayerElement, selection_rect: Rectangle) -> bool:
        """Check if element matches the current selection strategy."""
        element_bounds = self._get_element_bounds(element)
        if not element_bounds:
            return False
        
        if self._selection_strategy == SelectionStrategy.CONTAINS:
            # Element must be fully contained in selection
            return self._rectangle_contains(selection_rect, element_bounds)
        
        elif self._selection_strategy == SelectionStrategy.INTERSECTS:
            # Element must intersect with selection
            return selection_rect.intersects(element_bounds)
        
        elif self._selection_strategy == SelectionStrategy.CENTER_POINT:
            # Element's center must be in selection
            center = element_bounds.center
            return selection_rect.contains(center)
        
        elif self._selection_strategy == SelectionStrategy.MAJORITY:
            # Majority of element must be in selection
            intersection = selection_rect.intersection(element_bounds)
            if intersection.width <= 0 or intersection.height <= 0:
                return False
            
            intersection_area = intersection.width * intersection.height
            element_area = element_bounds.width * element_bounds.height
            
            return intersection_area >= (element_area * 0.5)
        
        return False
    
    def _rectangle_contains(self, outer: Rectangle, inner: Rectangle) -> bool:
        """Check if outer rectangle fully contains inner rectangle."""
        return (inner.x >= outer.x and 
                inner.y >= outer.y and 
                inner.x + inner.width <= outer.x + outer.width and 
                inner.y + inner.height <= outer.y + outer.height)
    
    def _calculate_selection_bounds(self, elements: Set[LayerElement]) -> Rectangle:
        """Calculate bounding rectangle for a set of elements."""
        if not elements:
            return Rectangle(0, 0, 0, 0)
        
        bounds_list = []
        for element in elements:
            bounds = self._get_element_bounds(element)
            if bounds:
                bounds_list.append(bounds)
        
        if not bounds_list:
            return Rectangle(0, 0, 0, 0)
        
        # Calculate union of all bounds
        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
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
    
    def _draw_selection_info(self, painter: QPainter, rect: QRect) -> None:
        """Draw selection information text."""
        if not self._preview_elements:
            return
        
        # Format info text
        info_text = f"Elements: {len(self._preview_elements)} | Strategy: {self._selection_strategy.value}"
        
        # Calculate text position
        text_rect = painter.fontMetrics().boundingRect(info_text)
        text_pos = QPoint(rect.x(), rect.y() - 5)
        
        # Ensure text is visible within viewport
        if text_pos.y() < text_rect.height():
            text_pos.setY(rect.bottom() + text_rect.height() + 5)
        
        # Draw background
        bg_rect = QRect(text_pos.x() - 2, text_pos.y() - text_rect.height() - 2,
                       text_rect.width() + 4, text_rect.height() + 4)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRect(bg_rect)
        
        # Draw text
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(text_pos, info_text)
    
    def _reset_selection(self) -> None:
        """Reset selection state."""
        self._start_point = None
        self._current_point = None
        self._current_rect = None
        self._is_dragging = False
        self._preview_elements.clear()
        self._final_elements.clear()
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.CrossCursor))
        
        # Clear preview
        self._preview_selection = SelectionResult()
        self.preview_changed.emit(self._preview_selection)
    
    def get_drag_statistics(self) -> dict:
        """Get drag operation statistics."""
        return {
            "drag_operations": self._drag_operations,
            "elements_processed": self._elements_processed,
            "last_preview_time": self._last_preview_time,
            "average_elements_per_drag": (
                self._elements_processed / max(1, self._drag_operations)
            )
        }
    
    def get_tool_info(self) -> dict:
        """Get tool information and statistics."""
        return {
            "name": "Rectangle Tool",
            "type": "rectangle",
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "selection_strategy": self._selection_strategy.value,
            "is_dragging": self._is_dragging,
            "preview_elements": len(self._preview_elements),
            "final_elements": len(self._final_elements),
            "drag_statistics": self.get_drag_statistics(),
            "metrics": self.get_metrics()
        }