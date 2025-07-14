"""
Multi-Select Tool for advanced selection operations.

This tool provides multi-element selection capabilities with modifier key support,
selection combination operations, and batch selection management.
"""

import time
from typing import List, Set, Optional, Dict, Any
from enum import Enum

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QCursor, QPen, QColor, QBrush

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from ..selection import SelectionOperation


class MultiSelectMode(Enum):
    """Multi-selection modes."""
    ADDITIVE = "additive"           # Add to current selection
    SUBTRACTIVE = "subtractive"     # Remove from current selection
    TOGGLE = "toggle"               # Toggle selection state
    INTERSECT = "intersect"         # Intersect with current selection
    REPLACE = "replace"             # Replace current selection


class MultiSelectTool(SelectionTool):
    """
    Multi-element selection tool with modifier key support.
    
    Features:
    - Additive selection (Ctrl+Click)
    - Subtractive selection (Shift+Click)
    - Toggle selection (Alt+Click)
    - Batch selection operations
    - Selection combination modes
    - Visual feedback for multi-selection
    """
    
    # Additional signals for multi-selection
    selection_added = pyqtSignal(object)    # SelectionResult
    selection_removed = pyqtSignal(object)  # SelectionResult
    selection_toggled = pyqtSignal(object)  # SelectionResult
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Multi-selection state
        self._selected_elements: Set[LayerElement] = set()
        self._selection_history: List[SelectionResult] = []
        self._max_history_size = 50
        
        # Selection modes
        self._current_mode = MultiSelectMode.REPLACE
        self._sticky_mode = False  # Keep mode active between selections
        
        # Modifier key configuration
        self._modifier_modes = {
            Qt.KeyboardModifier.ControlModifier: MultiSelectMode.ADDITIVE,
            Qt.KeyboardModifier.ShiftModifier: MultiSelectMode.SUBTRACTIVE,
            Qt.KeyboardModifier.AltModifier: MultiSelectMode.TOGGLE
        }
        
        # Visual styling
        self._selection_colors = {
            MultiSelectMode.ADDITIVE: QColor(0, 255, 0, 100),     # Green
            MultiSelectMode.SUBTRACTIVE: QColor(255, 0, 0, 100),  # Red
            MultiSelectMode.TOGGLE: QColor(255, 255, 0, 100),     # Yellow
            MultiSelectMode.INTERSECT: QColor(0, 255, 255, 100),  # Cyan
            MultiSelectMode.REPLACE: QColor(0, 120, 215, 100)     # Blue
        }
        
        # Performance tracking
        self._multi_operations = 0
        self._elements_selected = 0
        self._elements_deselected = 0
        self._batch_operations = 0
    
    def activate(self) -> None:
        """Activate multi-select tool."""
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def deactivate(self) -> None:
        """Deactivate multi-select tool."""
        self._update_state(ToolState.INACTIVE)
        self._reset_selection()
    
    def set_selection_mode(self, mode: MultiSelectMode) -> None:
        """Set the current selection mode."""
        self._current_mode = mode
        self._update_cursor_for_mode()
    
    def get_selection_mode(self) -> MultiSelectMode:
        """Get the current selection mode."""
        return self._current_mode
    
    def set_sticky_mode(self, sticky: bool) -> None:
        """Set sticky mode (keep mode active between selections)."""
        self._sticky_mode = sticky
    
    def set_modifier_mode(self, modifier: Qt.KeyboardModifier, mode: MultiSelectMode) -> None:
        """Set mode for specific modifier key."""
        self._modifier_modes[modifier] = mode
    
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse press with multi-selection logic."""
        if self._state != ToolState.ACTIVE:
            return False
        
        start_time = time.time()
        
        # Determine selection mode from modifiers
        selection_mode = self._get_mode_from_modifiers(modifiers)
        
        # Find element at point
        element = self._find_element_at_point(point)
        
        if element:
            self._update_state(ToolState.SELECTING)
            
            # Apply selection operation
            result = self._apply_selection_operation(element, selection_mode, point)
            
            if result:
                # Update selection history
                self._add_to_history(result)
                
                # Emit appropriate signals
                if selection_mode == MultiSelectMode.ADDITIVE:
                    self.selection_added.emit(result)
                elif selection_mode == MultiSelectMode.SUBTRACTIVE:
                    self.selection_removed.emit(result)
                elif selection_mode == MultiSelectMode.TOGGLE:
                    self.selection_toggled.emit(result)
                
                # Always emit main selection signal
                self.selection_changed.emit(result)
                
                self._multi_operations += 1
                
                operation_time = time.time() - start_time
                self._update_metrics(operation_time)
                
                return True
        else:
            # Clicked empty space
            if selection_mode == MultiSelectMode.REPLACE:
                self.clear_selection()
            return False
        
        return False
    
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse movement for hover effects."""
        if self._state == ToolState.ACTIVE:
            # Update cursor based on modifiers
            mode = self._get_mode_from_modifiers(modifiers)
            if mode != self._current_mode:
                self._current_mode = mode
                self._update_cursor_for_mode()
            
            # Find element for hover effects
            element = self._find_element_at_point(point)
            self._show_hover_preview(element, mode)
            
            return True
        
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Complete multi-selection operation."""
        if self._state == ToolState.SELECTING:
            self._update_state(ToolState.SELECTED)
            return True
        
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle keyboard shortcuts for multi-selection."""
        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            return True
        
        # Select all
        if key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.select_all()
            return True
        
        # Invert selection
        if key == Qt.Key.Key_I and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.invert_selection()
            return True
        
        # Undo last selection
        if key == Qt.Key.Key_Z and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.undo_selection()
            return True
        
        # Mode switching shortcuts
        if key == Qt.Key.Key_1:
            self.set_selection_mode(MultiSelectMode.REPLACE)
            return True
        elif key == Qt.Key.Key_2:
            self.set_selection_mode(MultiSelectMode.ADDITIVE)
            return True
        elif key == Qt.Key.Key_3:
            self.set_selection_mode(MultiSelectMode.SUBTRACTIVE)
            return True
        elif key == Qt.Key.Key_4:
            self.set_selection_mode(MultiSelectMode.TOGGLE)
            return True
        
        return False
    
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render multi-selection with visual feedback."""
        if not self._visible:
            return
        
        # Draw selected elements
        if self._selected_elements:
            selection_color = self._selection_colors.get(
                MultiSelectMode.REPLACE, 
                QColor(0, 120, 215, 100)
            )
            
            painter.setPen(QPen(selection_color, 2))
            painter.setBrush(QBrush())
            
            for element in self._selected_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    qrect = self._rectangle_to_qrect(bounds)
                    painter.drawRect(qrect)
            
            # Draw selection count
            self._draw_selection_count(painter, viewport_rect)
        
        # Draw mode indicator
        self._draw_mode_indicator(painter, viewport_rect)
    
    def select_all(self) -> bool:
        """Select all available elements."""
        all_elements = self._get_all_elements()
        
        if all_elements:
            self._selected_elements = set(all_elements)
            
            # Calculate selection bounds
            selection_bounds = self._calculate_selection_bounds(self._selected_elements)
            
            # Create selection result
            result = SelectionResult(
                elements=list(self._selected_elements),
                geometry=selection_bounds,
                tool_type="multi_select",
                timestamp=time.time(),
                metadata={
                    "operation": "select_all",
                    "element_count": len(self._selected_elements),
                    "mode": self._current_mode.value
                }
            )
            
            self._current_selection = result
            self._add_to_history(result)
            self.selection_changed.emit(result)
            
            self._batch_operations += 1
            self._elements_selected += len(self._selected_elements)
            
            return True
        
        return False
    
    def invert_selection(self) -> bool:
        """Invert current selection."""
        all_elements = set(self._get_all_elements())
        
        if all_elements:
            # Calculate new selection (all elements minus current selection)
            new_selection = all_elements - self._selected_elements
            old_count = len(self._selected_elements)
            
            self._selected_elements = new_selection
            
            # Calculate selection bounds
            selection_bounds = self._calculate_selection_bounds(self._selected_elements)
            
            # Create selection result
            result = SelectionResult(
                elements=list(self._selected_elements),
                geometry=selection_bounds,
                tool_type="multi_select",
                timestamp=time.time(),
                metadata={
                    "operation": "invert_selection",
                    "element_count": len(self._selected_elements),
                    "previous_count": old_count,
                    "mode": self._current_mode.value
                }
            )
            
            self._current_selection = result
            self._add_to_history(result)
            self.selection_changed.emit(result)
            
            self._batch_operations += 1
            
            return True
        
        return False
    
    def undo_selection(self) -> bool:
        """Undo last selection operation."""
        if len(self._selection_history) > 1:
            # Remove current selection
            self._selection_history.pop()
            
            # Restore previous selection
            if self._selection_history:
                previous_result = self._selection_history[-1]
                self._selected_elements = set(previous_result.elements)
                self._current_selection = previous_result
                self.selection_changed.emit(previous_result)
                return True
        
        return False
    
    def clear_selection(self) -> None:
        """Clear all selected elements."""
        if self._selected_elements:
            self._selected_elements.clear()
            self._current_selection = SelectionResult()
            self.selection_changed.emit(self._current_selection)
    
    def get_selected_elements(self) -> Set[LayerElement]:
        """Get currently selected elements."""
        return self._selected_elements.copy()
    
    def get_selection_count(self) -> int:
        """Get number of selected elements."""
        return len(self._selected_elements)
    
    def is_element_selected(self, element: LayerElement) -> bool:
        """Check if element is selected."""
        return element in self._selected_elements
    
    def _get_mode_from_modifiers(self, modifiers: Qt.KeyboardModifier) -> MultiSelectMode:
        """Get selection mode from modifier keys."""
        if not self._sticky_mode:
            # Check modifier keys
            for modifier, mode in self._modifier_modes.items():
                if modifiers & modifier:
                    return mode
        
        # Return current mode if no modifiers or sticky mode
        return self._current_mode
    
    def _apply_selection_operation(self, element: LayerElement, mode: MultiSelectMode, point: QPoint) -> Optional[SelectionResult]:
        """Apply selection operation based on mode."""
        old_count = len(self._selected_elements)
        
        if mode == MultiSelectMode.REPLACE:
            self._selected_elements = {element}
            self._elements_selected += 1
            
        elif mode == MultiSelectMode.ADDITIVE:
            if element not in self._selected_elements:
                self._selected_elements.add(element)
                self._elements_selected += 1
            
        elif mode == MultiSelectMode.SUBTRACTIVE:
            if element in self._selected_elements:
                self._selected_elements.remove(element)
                self._elements_deselected += 1
            
        elif mode == MultiSelectMode.TOGGLE:
            if element in self._selected_elements:
                self._selected_elements.remove(element)
                self._elements_deselected += 1
            else:
                self._selected_elements.add(element)
                self._elements_selected += 1
        
        elif mode == MultiSelectMode.INTERSECT:
            if element in self._selected_elements:
                self._selected_elements = {element}
            else:
                self._selected_elements.clear()
        
        # Create selection result if selection changed
        if len(self._selected_elements) != old_count or mode == MultiSelectMode.REPLACE:
            # Calculate selection bounds
            selection_bounds = self._calculate_selection_bounds(self._selected_elements)
            
            result = SelectionResult(
                elements=list(self._selected_elements),
                geometry=selection_bounds,
                tool_type="multi_select",
                timestamp=time.time(),
                metadata={
                    "operation": mode.value,
                    "element_count": len(self._selected_elements),
                    "click_point": self._qpoint_to_point(point),
                    "previous_count": old_count,
                    "element_type": self._get_element_type(element)
                }
            )
            
            self._current_selection = result
            return result
        
        return None
    
    def _show_hover_preview(self, element: Optional[LayerElement], mode: MultiSelectMode) -> None:
        """Show hover preview for multi-selection."""
        if element:
            # Create preview result
            preview_result = SelectionResult(
                elements=[element],
                geometry=self._get_element_bounds(element),
                tool_type="multi_select",
                timestamp=time.time(),
                metadata={
                    "preview": True,
                    "mode": mode.value,
                    "would_select": element not in self._selected_elements,
                    "element_type": self._get_element_type(element)
                }
            )
            
            self._preview_selection = preview_result
            self.preview_changed.emit(preview_result)
    
    def _update_cursor_for_mode(self) -> None:
        """Update cursor based on selection mode."""
        cursor_map = {
            MultiSelectMode.REPLACE: Qt.CursorShape.ArrowCursor,
            MultiSelectMode.ADDITIVE: Qt.CursorShape.CrossCursor,
            MultiSelectMode.SUBTRACTIVE: Qt.CursorShape.ForbiddenCursor,
            MultiSelectMode.TOGGLE: Qt.CursorShape.PointingHandCursor,
            MultiSelectMode.INTERSECT: Qt.CursorShape.WhatsThisCursor
        }
        
        cursor_shape = cursor_map.get(self._current_mode, Qt.CursorShape.ArrowCursor)
        self.set_cursor(QCursor(cursor_shape))
    
    def _draw_selection_count(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Draw selection count information."""
        if not self._selected_elements:
            return
        
        count_text = f"Selected: {len(self._selected_elements)}"
        
        # Position at bottom-right
        text_rect = painter.fontMetrics().boundingRect(count_text)
        pos = QPoint(
            viewport_rect.right() - text_rect.width() - 10,
            viewport_rect.bottom() - text_rect.height() - 10
        )
        
        # Draw background
        bg_rect = QRect(pos.x() - 5, pos.y() - 5, 
                       text_rect.width() + 10, text_rect.height() + 10)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRect(bg_rect)
        
        # Draw text
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(pos, count_text)
    
    def _draw_mode_indicator(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Draw current mode indicator."""
        mode_text = f"Mode: {self._current_mode.value.title()}"
        
        # Position at top-right
        text_rect = painter.fontMetrics().boundingRect(mode_text)
        pos = QPoint(
            viewport_rect.right() - text_rect.width() - 10,
            20
        )
        
        # Draw background with mode color
        mode_color = self._selection_colors.get(self._current_mode, QColor(128, 128, 128))
        bg_rect = QRect(pos.x() - 5, pos.y() - 15, 
                       text_rect.width() + 10, text_rect.height() + 10)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(mode_color))
        painter.drawRect(bg_rect)
        
        # Draw text
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(pos, mode_text)
    
    def _add_to_history(self, result: SelectionResult) -> None:
        """Add selection result to history."""
        self._selection_history.append(result)
        
        # Limit history size
        if len(self._selection_history) > self._max_history_size:
            self._selection_history.pop(0)
    
    def _calculate_selection_bounds(self, elements: Set[LayerElement]) -> Optional[Rectangle]:
        """Calculate bounding rectangle for selected elements."""
        if not elements:
            return None
        
        bounds_list = []
        for element in elements:
            bounds = self._get_element_bounds(element)
            if bounds:
                bounds_list.append(bounds)
        
        if not bounds_list:
            return None
        
        # Calculate union of all bounds
        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _find_element_at_point(self, point: QPoint) -> Optional[LayerElement]:
        """Find element at given point."""
        # TODO: Implement actual element finding using overlay API
        return None
    
    def _get_all_elements(self) -> List[LayerElement]:
        """Get all available elements."""
        # TODO: Implement actual element retrieval from overlay API
        return []
    
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
    
    def _reset_selection(self) -> None:
        """Reset selection state."""
        self._selected_elements.clear()
        self._selection_history.clear()
        self._current_mode = MultiSelectMode.REPLACE
        self.clear_selection()
    
    def get_multi_select_statistics(self) -> dict:
        """Get multi-selection statistics."""
        return {
            "multi_operations": self._multi_operations,
            "elements_selected": self._elements_selected,
            "elements_deselected": self._elements_deselected,
            "batch_operations": self._batch_operations,
            "current_selection_count": len(self._selected_elements),
            "history_length": len(self._selection_history),
            "selection_efficiency": (
                self._elements_selected / max(1, self._multi_operations)
            )
        }
    
    def get_tool_info(self) -> dict:
        """Get tool information and statistics."""
        return {
            "name": "Multi-Select Tool",
            "type": "multi_select",
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "selection_mode": self._current_mode.value,
            "sticky_mode": self._sticky_mode,
            "selected_elements": len(self._selected_elements),
            "history_size": len(self._selection_history),
            "modifier_modes": {
                str(mod): mode.value for mod, mode in self._modifier_modes.items()
            },
            "multi_select_statistics": self.get_multi_select_statistics(),
            "metrics": self.get_metrics()
        }