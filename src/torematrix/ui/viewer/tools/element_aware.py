"""
Element-Aware Tool for intelligent selection.

This tool provides smart selection that adapts to document element types,
with hierarchical selection and contextual expansion capabilities.
"""

import math
import time
from typing import List, Optional, Set, Dict, Any, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QPainter, QCursor, QPen, QColor, QBrush

from .base import SelectionTool, ToolState, SelectionResult
from ..coordinates import Point, Rectangle
from ..layers import LayerElement


class ElementAwareTool(SelectionTool):
    """
    Smart selection tool that adapts to document element types.
    
    Features:
    - Intelligent element prioritization
    - Contextual selection expansion
    - Hierarchical selection levels
    - Type-specific selection behaviors
    - Smart cursor changes based on element type
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Element type priority (higher priority = selected first)
        self._element_type_priority = {
            "text": 10,
            "formula": 9,
            "image": 8,
            "table": 7,
            "chart": 6,
            "shape": 5,
            "line": 4,
            "annotation": 3,
            "background": 2,
            "container": 1
        }
        
        # Selection configuration
        self._smart_selection_enabled = True
        self._context_radius = 20  # pixels
        self._hierarchy_levels = 3
        
        # Selection state
        self._current_element: Optional[LayerElement] = None
        self._hover_element: Optional[LayerElement] = None
        self._selection_hierarchy: List[Dict[str, Any]] = []
        self._current_hierarchy_level = 0
        
        # Context analysis
        self._context_elements: Set[LayerElement] = set()
        self._related_elements: Set[LayerElement] = set()
        
        # Visual styling
        self._selection_colors = {
            "text": QColor(138, 43, 226),      # Purple
            "image": QColor(255, 69, 0),      # Orange-red
            "table": QColor(0, 191, 255),     # Sky blue
            "formula": QColor(255, 215, 0),   # Gold
            "chart": QColor(50, 205, 50),     # Green
            "shape": QColor(255, 20, 147),    # Deep pink
            "default": QColor(138, 43, 226)   # Purple
        }
        
        # Performance tracking
        self._smart_selections = 0
        self._hierarchy_expansions = 0
        self._context_analyses = 0
    
    def activate(self) -> None:
        """Activate element-aware tool."""
        self._update_state(ToolState.ACTIVE)
        self.set_cursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def deactivate(self) -> None:
        """Deactivate element-aware tool."""
        self._update_state(ToolState.INACTIVE)
        self._reset_selection()
    
    def set_smart_selection_enabled(self, enabled: bool) -> None:
        """Enable or disable smart selection."""
        self._smart_selection_enabled = enabled
    
    def set_context_radius(self, radius: int) -> None:
        """Set context analysis radius."""
        self._context_radius = max(1, radius)
    
    def set_element_priority(self, element_type: str, priority: int) -> None:
        """Set priority for element type."""
        self._element_type_priority[element_type] = priority
    
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle smart element selection."""
        if self._state != ToolState.ACTIVE:
            return False
        
        start_time = time.time()
        
        # Find best element at point
        element = self._find_best_element(point)
        
        if element:
            self._current_element = element
            self._update_state(ToolState.SELECTING)
            
            # Build selection hierarchy
            self._selection_hierarchy = self._build_selection_hierarchy(element, point)
            self._current_hierarchy_level = 0
            
            # Analyze context
            if self._smart_selection_enabled:
                self._analyze_context(element, point)
                self._context_analyses += 1
            
            # Handle selection based on element type
            element_type = self._get_element_type(element)
            if element_type == "text":
                self._handle_text_selection(element, point, modifiers)
            elif element_type == "table":
                self._handle_table_selection(element, point, modifiers)
            elif element_type == "image":
                self._handle_image_selection(element, point, modifiers)
            elif element_type == "formula":
                self._handle_formula_selection(element, point, modifiers)
            else:
                self._handle_generic_selection(element, point, modifiers)
            
            self._smart_selections += 1
            
            operation_time = time.time() - start_time
            self._update_metrics(operation_time)
            
            return True
        else:
            # Clear selection if clicking empty space
            if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                self.clear_selection()
            return False
    
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle smart hover and preview."""
        if self._state == ToolState.ACTIVE:
            # Find best element at point
            element = self._find_best_element(point)
            
            if element != self._hover_element:
                self._hover_element = element
                
                if element:
                    # Update cursor for element type
                    self._update_cursor_for_element(element)
                    self._update_state(ToolState.HOVER)
                    
                    # Show preview of what would be selected
                    self._show_selection_preview(element, point)
                else:
                    self.set_cursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    self._update_state(ToolState.ACTIVE)
                    self._clear_preview()
            
            return True
        
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Complete smart selection."""
        if self._state == ToolState.SELECTING and self._selection_hierarchy:
            # Use current hierarchy level
            current_selection = self._selection_hierarchy[self._current_hierarchy_level]
            
            # Create selection result
            result = SelectionResult(
                elements=current_selection['elements'],
                geometry=current_selection['geometry'],
                tool_type="element_aware",
                timestamp=time.time(),
                metadata={
                    "element_type": current_selection['type'],
                    "smart_selection": True,
                    "hierarchy_level": self._current_hierarchy_level,
                    "hierarchy_levels": len(self._selection_hierarchy),
                    "context_elements": len(self._context_elements),
                    "related_elements": len(self._related_elements),
                    "selection_context": current_selection.get('context', {}),
                    "modifiers": int(modifiers)
                }
            )
            
            # Update selection
            self._current_selection = result
            self._update_state(ToolState.SELECTED)
            self.selection_changed.emit(result)
            
            return True
        
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle keyboard input for hierarchy navigation."""
        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            return True
        
        # Navigate hierarchy levels
        if self._selection_hierarchy:
            if key == Qt.Key.Key_Up or key == Qt.Key.Key_Plus:
                # Expand selection (go up hierarchy)
                if self._current_hierarchy_level < len(self._selection_hierarchy) - 1:
                    self._current_hierarchy_level += 1
                    self._update_hierarchy_selection()
                    self._hierarchy_expansions += 1
                return True
            
            elif key == Qt.Key.Key_Down or key == Qt.Key.Key_Minus:
                # Contract selection (go down hierarchy)
                if self._current_hierarchy_level > 0:
                    self._current_hierarchy_level -= 1
                    self._update_hierarchy_selection()
                return True
        
        # Toggle smart selection
        if key == Qt.Key.Key_S:
            self.set_smart_selection_enabled(not self._smart_selection_enabled)
            return True
        
        return False
    
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render smart selection with context."""
        if not self._visible:
            return
        
        # Draw selection hierarchy
        if self._selection_hierarchy:
            for level, selection in enumerate(self._selection_hierarchy):
                if level == self._current_hierarchy_level:
                    # Current level - solid highlight
                    color = self._get_color_for_type(selection['type'])
                    painter.setPen(QPen(color, 3))
                    painter.setBrush(QBrush())
                    painter.drawRect(self._rectangle_to_qrect(selection['geometry']))
                else:
                    # Other levels - faded highlight
                    color = self._get_color_for_type(selection['type'])
                    fade_color = QColor(color)
                    fade_color.setAlpha(100 - (abs(level - self._current_hierarchy_level) * 30))
                    painter.setPen(QPen(fade_color, 1))
                    painter.setBrush(QBrush())
                    painter.drawRect(self._rectangle_to_qrect(selection['geometry']))
        
        # Draw context elements
        if self._context_elements and self._smart_selection_enabled:
            painter.setPen(QPen(QColor(128, 128, 128, 100), 1))
            for element in self._context_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    painter.drawRect(self._rectangle_to_qrect(bounds))
        
        # Draw related elements
        if self._related_elements and self._smart_selection_enabled:
            painter.setPen(QPen(QColor(255, 255, 0, 150), 2))
            for element in self._related_elements:
                bounds = self._get_element_bounds(element)
                if bounds:
                    painter.drawRect(self._rectangle_to_qrect(bounds))
        
        # Draw selection info
        if self._selection_hierarchy:
            self._draw_selection_info(painter, viewport_rect)
    
    def _find_best_element(self, point: QPoint) -> Optional[LayerElement]:
        """Find the most appropriate element at point."""
        candidates = self._find_elements_at_point(point)
        
        if not candidates:
            return None
        
        # Sort by priority and proximity
        def element_score(element):
            element_type = self._get_element_type(element)
            type_priority = self._element_type_priority.get(element_type, 0)
            distance = self._distance_to_element(point, element)
            size_factor = self._get_element_size_factor(element)
            
            # Higher priority = better score (lower number)
            return (-type_priority, distance, size_factor)
        
        return min(candidates, key=element_score)
    
    def _build_selection_hierarchy(self, element: LayerElement, point: QPoint) -> List[Dict[str, Any]]:
        """Build hierarchy of possible selections."""
        hierarchy = []
        
        # Level 0: Exact element
        hierarchy.append({
            'type': self._get_element_type(element),
            'elements': [element],
            'geometry': self._get_element_bounds(element),
            'context': {'level': 'exact', 'click_point': self._qpoint_to_point(point)}
        })
        
        # Level 1: Contextual selection (word, cell, etc.)
        contextual_selection = self._get_contextual_selection(element, point)
        if contextual_selection:
            hierarchy.append(contextual_selection)
        
        # Level 2: Container selection (paragraph, row, etc.)
        container_selection = self._get_container_selection(element, point)
        if container_selection:
            hierarchy.append(container_selection)
        
        # Level 3: Group selection (entire table, figure, etc.)
        group_selection = self._get_group_selection(element, point)
        if group_selection:
            hierarchy.append(group_selection)
        
        return hierarchy
    
    def _analyze_context(self, element: LayerElement, point: QPoint) -> None:
        """Analyze context around the selected element."""
        element_bounds = self._get_element_bounds(element)
        if not element_bounds:
            return
        
        # Define context area
        context_area = Rectangle(
            element_bounds.x - self._context_radius,
            element_bounds.y - self._context_radius,
            element_bounds.width + 2 * self._context_radius,
            element_bounds.height + 2 * self._context_radius
        )
        
        # Find context elements
        self._context_elements = set(self._get_elements_in_area(context_area))
        self._context_elements.discard(element)  # Remove the selected element
        
        # Find related elements
        self._related_elements = self._find_related_elements(element)
    
    def _handle_text_selection(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle text-specific selection logic."""
        # Could expand to word, sentence, or paragraph based on context
        pass
    
    def _handle_table_selection(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle table-specific selection logic."""
        # Could select cell, row, column, or entire table
        pass
    
    def _handle_image_selection(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle image-specific selection logic."""
        # Could include caption or grouped elements
        pass
    
    def _handle_formula_selection(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle formula-specific selection logic."""
        # Could select sub-expressions or entire formula
        pass
    
    def _handle_generic_selection(self, element: LayerElement, point: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """Handle generic element selection."""
        # Default selection behavior
        pass
    
    def _get_contextual_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get contextual selection based on element type."""
        element_type = self._get_element_type(element)
        
        if element_type == "text":
            return self._get_word_selection(element, point)
        elif element_type == "table":
            return self._get_cell_selection(element, point)
        elif element_type == "image":
            return self._get_image_with_caption(element, point)
        
        return None
    
    def _get_container_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get container selection (paragraph, row, etc.)."""
        element_type = self._get_element_type(element)
        
        if element_type == "text":
            return self._get_paragraph_selection(element, point)
        elif element_type == "table":
            return self._get_row_selection(element, point)
        
        return None
    
    def _get_group_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get group selection (entire table, figure, etc.)."""
        element_type = self._get_element_type(element)
        
        if element_type == "table":
            return self._get_entire_table_selection(element, point)
        elif element_type in ["image", "chart"]:
            return self._get_figure_selection(element, point)
        
        return None
    
    def _get_word_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get word-level text selection."""
        # TODO: Implement word boundary detection
        return None
    
    def _get_cell_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get table cell selection."""
        # TODO: Implement cell boundary detection
        return None
    
    def _get_image_with_caption(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get image with caption selection."""
        # TODO: Implement caption detection
        return None
    
    def _get_paragraph_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get paragraph-level text selection."""
        # TODO: Implement paragraph boundary detection
        return None
    
    def _get_row_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get table row selection."""
        # TODO: Implement row boundary detection
        return None
    
    def _get_entire_table_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get entire table selection."""
        # TODO: Implement table boundary detection
        return None
    
    def _get_figure_selection(self, element: LayerElement, point: QPoint) -> Optional[Dict[str, Any]]:
        """Get figure with caption selection."""
        # TODO: Implement figure boundary detection
        return None
    
    def _find_related_elements(self, element: LayerElement) -> Set[LayerElement]:
        """Find elements related to the selected element."""
        # TODO: Implement relationship detection
        return set()
    
    def _update_cursor_for_element(self, element: LayerElement) -> None:
        """Update cursor based on element type."""
        element_type = self._get_element_type(element)
        
        cursor_map = {
            "text": Qt.CursorShape.IBeamCursor,
            "image": Qt.CursorShape.OpenHandCursor,
            "table": Qt.CursorShape.PointingHandCursor,
            "formula": Qt.CursorShape.CrossCursor,
            "chart": Qt.CursorShape.OpenHandCursor,
            "shape": Qt.CursorShape.SizeAllCursor,
            "link": Qt.CursorShape.PointingHandCursor,
            "button": Qt.CursorShape.PointingHandCursor
        }
        
        cursor_shape = cursor_map.get(element_type, Qt.CursorShape.PointingHandCursor)
        self.set_cursor(QCursor(cursor_shape))
    
    def _update_hierarchy_selection(self) -> None:
        """Update selection to current hierarchy level."""
        if not self._selection_hierarchy:
            return
        
        current_selection = self._selection_hierarchy[self._current_hierarchy_level]
        
        # Create updated selection result
        result = SelectionResult(
            elements=current_selection['elements'],
            geometry=current_selection['geometry'],
            tool_type="element_aware",
            timestamp=time.time(),
            metadata={
                "element_type": current_selection['type'],
                "smart_selection": True,
                "hierarchy_level": self._current_hierarchy_level,
                "hierarchy_levels": len(self._selection_hierarchy),
                "selection_context": current_selection.get('context', {})
            }
        )
        
        self._current_selection = result
        self.selection_changed.emit(result)
    
    def _show_selection_preview(self, element: LayerElement, point: QPoint) -> None:
        """Show preview of what would be selected."""
        # Build preview hierarchy
        preview_hierarchy = self._build_selection_hierarchy(element, point)
        
        if preview_hierarchy:
            preview_selection = preview_hierarchy[0]  # Show first level
            
            preview_result = SelectionResult(
                elements=preview_selection['elements'],
                geometry=preview_selection['geometry'],
                tool_type="element_aware",
                timestamp=time.time(),
                metadata={
                    "preview": True,
                    "element_type": preview_selection['type'],
                    "smart_selection": True
                }
            )
            
            self._preview_selection = preview_result
            self.preview_changed.emit(preview_result)
    
    def _clear_preview(self) -> None:
        """Clear selection preview."""
        self._preview_selection = SelectionResult()
        self.preview_changed.emit(self._preview_selection)
    
    def _get_color_for_type(self, element_type: str) -> QColor:
        """Get color for element type."""
        return self._selection_colors.get(element_type, self._selection_colors["default"])
    
    def _draw_selection_info(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Draw selection information."""
        if not self._selection_hierarchy:
            return
        
        current_selection = self._selection_hierarchy[self._current_hierarchy_level]
        
        # Format info text
        info_text = (
            f"Type: {current_selection['type']} | "
            f"Level: {self._current_hierarchy_level + 1}/{len(self._selection_hierarchy)} | "
            f"Elements: {len(current_selection['elements'])}"
        )
        
        # Draw info at top-left of viewport
        text_rect = painter.fontMetrics().boundingRect(info_text)
        bg_rect = QRect(10, 10, text_rect.width() + 10, text_rect.height() + 10)
        
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRect(bg_rect)
        
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(15, 25, info_text)
    
    def _find_elements_at_point(self, point: QPoint) -> List[LayerElement]:
        """Find all elements at given point."""
        # TODO: Implement actual element finding using overlay API
        return []
    
    def _get_elements_in_area(self, area: Rectangle) -> List[LayerElement]:
        """Get all elements in specified area."""
        # TODO: Implement actual element retrieval from overlay API
        return []
    
    def _distance_to_element(self, point: QPoint, element: LayerElement) -> float:
        """Calculate distance from point to element."""
        bounds = self._get_element_bounds(element)
        if not bounds:
            return float('inf')
        
        # Distance to center of element
        center = bounds.center
        return self._get_distance(point, self._point_to_qpoint(center))
    
    def _get_element_size_factor(self, element: LayerElement) -> float:
        """Get size factor for element (smaller elements have higher priority)."""
        bounds = self._get_element_bounds(element)
        if not bounds:
            return float('inf')
        
        area = bounds.width * bounds.height
        return math.sqrt(area)  # Prefer smaller elements
    
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
        self._current_element = None
        self._hover_element = None
        self._selection_hierarchy = []
        self._current_hierarchy_level = 0
        self._context_elements.clear()
        self._related_elements.clear()
        self._update_state(ToolState.ACTIVE)
        self.clear_selection()
        self._clear_preview()
    
    def get_intelligence_statistics(self) -> dict:
        """Get intelligence and context statistics."""
        return {
            "smart_selections": self._smart_selections,
            "hierarchy_expansions": self._hierarchy_expansions,
            "context_analyses": self._context_analyses,
            "current_hierarchy_level": self._current_hierarchy_level,
            "hierarchy_levels": len(self._selection_hierarchy),
            "context_elements": len(self._context_elements),
            "related_elements": len(self._related_elements),
            "smart_selection_enabled": self._smart_selection_enabled
        }
    
    def get_tool_info(self) -> dict:
        """Get tool information and statistics."""
        return {
            "name": "Element-Aware Tool",
            "type": "element_aware",
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "smart_selection_enabled": self._smart_selection_enabled,
            "context_radius": self._context_radius,
            "current_element": self._current_element is not None,
            "hover_element": self._hover_element is not None,
            "element_priorities": self._element_type_priority,
            "intelligence_statistics": self.get_intelligence_statistics(),
            "metrics": self.get_metrics()
        }