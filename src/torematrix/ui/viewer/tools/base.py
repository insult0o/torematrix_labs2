"""
Base classes for selection tools.

This module provides the foundation for all selection tools including
common interfaces, state management, and result structures.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect, Qt
from PyQt6.QtGui import QPainter, QCursor

from ..coordinates import Rectangle, Point
from ..layers import LayerElement


class ToolState(Enum):
    """States for selection tools."""
    INACTIVE = "inactive"       # Tool is not active
    ACTIVE = "active"          # Tool is active but not selecting
    HOVER = "hover"            # Tool is hovering over selectable element
    SELECTING = "selecting"     # Tool is actively selecting
    SELECTED = "selected"      # Tool has completed selection
    DRAG = "drag"              # Tool is dragging selection
    RESIZE = "resize"          # Tool is resizing selection
    MOVE = "move"              # Tool is moving selection


@dataclass
class SelectionResult:
    """Result of a selection operation."""
    elements: List[LayerElement] = field(default_factory=list)
    geometry: Optional[Rectangle] = None
    tool_type: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if selection result is valid."""
        return len(self.elements) > 0 or self.geometry is not None
    
    def get_element_count(self) -> int:
        """Get number of selected elements."""
        return len(self.elements)
    
    def get_element_ids(self) -> List[str]:
        """Get IDs of selected elements."""
        return [elem.get_id() for elem in self.elements if hasattr(elem, 'get_id')]
    
    def get_bounds(self) -> Optional[Rectangle]:
        """Get bounding rectangle of selection."""
        if self.geometry:
            return self.geometry
        
        if not self.elements:
            return None
        
        bounds_list = []
        for element in self.elements:
            if hasattr(element, 'get_bounds'):
                bounds_list.append(element.get_bounds())
        
        if not bounds_list:
            return None
        
        # Calculate union of all bounds
        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)


class QObjectMeta(type(QObject), type(ABC)):
    """Metaclass to resolve conflicts between QObject and ABC."""
    pass


class SelectionTool(QObject, ABC, metaclass=QObjectMeta):
    """
    Abstract base class for all selection tools.
    
    Provides common interface and functionality for pointer, rectangle,
    lasso, and element-aware selection tools.
    """
    
    # Signals
    state_changed = pyqtSignal(object)  # ToolState
    selection_changed = pyqtSignal(object)  # SelectionResult
    cursor_changed = pyqtSignal(object)  # QCursor
    preview_changed = pyqtSignal(object)  # SelectionResult
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = ToolState.INACTIVE
        self._cursor = QCursor(Qt.CursorShape.ArrowCursor)
        self._enabled = True
        self._visible = True
        
        # Selection state
        self._current_selection = SelectionResult()
        self._preview_selection = SelectionResult()
        
        # Performance tracking
        self._metrics = {
            'operations_count': 0,
            'average_operation_time': 0.0,
            'last_operation_time': 0.0,
            'selection_accuracy': 0.0
        }
        
        # Tool configuration
        self._config = {
            'double_click_threshold': 300,  # ms
            'drag_threshold': 5,  # pixels
            'click_tolerance': 3,  # pixels
            'animation_duration': 200  # ms
        }
    
    @property
    def state(self) -> ToolState:
        """Get current tool state."""
        return self._state
    
    @property
    def enabled(self) -> bool:
        """Check if tool is enabled."""
        return self._enabled
    
    @property
    def visible(self) -> bool:
        """Check if tool is visible."""
        return self._visible
    
    @property
    def cursor(self) -> QCursor:
        """Get current cursor."""
        return self._cursor
    
    @property
    def current_selection(self) -> SelectionResult:
        """Get current selection result."""
        return self._current_selection
    
    @property
    def preview_selection(self) -> SelectionResult:
        """Get preview selection result."""
        return self._preview_selection
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the tool."""
        if self._enabled != enabled:
            self._enabled = enabled
            if not enabled and self._state != ToolState.INACTIVE:
                self.deactivate()
    
    def set_visible(self, visible: bool) -> None:
        """Set tool visibility."""
        if self._visible != visible:
            self._visible = visible
            if not visible and self._state != ToolState.INACTIVE:
                self.deactivate()
    
    def set_config(self, key: str, value: Any) -> None:
        """Set tool configuration value."""
        if key in self._config:
            self._config[key] = value
    
    def get_config(self, key: str) -> Any:
        """Get tool configuration value."""
        return self._config.get(key)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tool performance metrics."""
        return self._metrics.copy()
    
    @abstractmethod
    def activate(self) -> None:
        """Activate the tool."""
        pass
    
    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the tool."""
        pass
    
    @abstractmethod
    def handle_mouse_press(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse press event."""
        pass
    
    @abstractmethod
    def handle_mouse_move(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse move event."""
        pass
    
    @abstractmethod
    def handle_mouse_release(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse release event."""
        pass
    
    def handle_mouse_double_click(self, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse double click event."""
        # Default implementation - can be overridden
        return False
    
    def handle_key_press(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle key press event."""
        # Default implementation - can be overridden
        return False
    
    def handle_key_release(self, key: int, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle key release event."""
        # Default implementation - can be overridden
        return False
    
    def handle_wheel(self, delta: int, point: QPoint, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Handle mouse wheel event."""
        # Default implementation - can be overridden
        return False
    
    @abstractmethod
    def render_overlay(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render tool overlay graphics."""
        pass
    
    def reset(self) -> None:
        """Reset tool to initial state."""
        self._current_selection = SelectionResult()
        self._preview_selection = SelectionResult()
        if self._state != ToolState.INACTIVE:
            self.deactivate()
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_selection = SelectionResult()
        self._preview_selection = SelectionResult()
        self.selection_changed.emit(self._current_selection)
        self.preview_changed.emit(self._preview_selection)
    
    def set_cursor(self, cursor: QCursor) -> None:
        """Set tool cursor."""
        if self._cursor != cursor:
            self._cursor = cursor
            self.cursor_changed.emit(self._cursor)
    
    def _update_state(self, new_state: ToolState) -> None:
        """Update tool state and emit signal."""
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(self._state)
    
    def _update_metrics(self, operation_time: float) -> None:
        """Update performance metrics."""
        self._metrics['operations_count'] += 1
        self._metrics['last_operation_time'] = operation_time
        
        # Update average operation time
        count = self._metrics['operations_count']
        current_avg = self._metrics['average_operation_time']
        self._metrics['average_operation_time'] = (
            (current_avg * (count - 1) + operation_time) / count
        )
    
    def _emit_error(self, message: str) -> None:
        """Emit error signal."""
        self.error_occurred.emit(message)
    
    def _get_distance(self, point1: QPoint, point2: QPoint) -> float:
        """Calculate distance between two points."""
        dx = point2.x() - point1.x()
        dy = point2.y() - point1.y()
        return (dx * dx + dy * dy) ** 0.5
    
    def _qpoint_to_point(self, qpoint: QPoint) -> Point:
        """Convert QPoint to Point."""
        return Point(qpoint.x(), qpoint.y())
    
    def _point_to_qpoint(self, point: Point) -> QPoint:
        """Convert Point to QPoint."""
        return QPoint(int(point.x), int(point.y))
    
    def _qrect_to_rectangle(self, qrect: QRect) -> Rectangle:
        """Convert QRect to Rectangle."""
        return Rectangle(qrect.x(), qrect.y(), qrect.width(), qrect.height())
    
    def _rectangle_to_qrect(self, rect: Rectangle) -> QRect:
        """Convert Rectangle to QRect."""
        return QRect(int(rect.x), int(rect.y), int(rect.width), int(rect.height))


class ToolRegistry:
    """Registry for managing selection tools."""
    
    def __init__(self):
        self._tools: Dict[str, SelectionTool] = {}
        self._active_tool: Optional[str] = None
    
    def register_tool(self, name: str, tool: SelectionTool) -> None:
        """Register a tool."""
        self._tools[name] = tool
    
    def unregister_tool(self, name: str) -> None:
        """Unregister a tool."""
        if name in self._tools:
            if self._active_tool == name:
                self._tools[name].deactivate()
                self._active_tool = None
            del self._tools[name]
    
    def get_tool(self, name: str) -> Optional[SelectionTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, SelectionTool]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def set_active_tool(self, name: str) -> bool:
        """Set the active tool."""
        if name not in self._tools:
            return False
        
        # Deactivate current tool
        if self._active_tool and self._active_tool in self._tools:
            self._tools[self._active_tool].deactivate()
        
        # Activate new tool
        self._active_tool = name
        self._tools[name].activate()
        return True
    
    def get_active_tool(self) -> Optional[SelectionTool]:
        """Get the currently active tool."""
        if self._active_tool:
            return self._tools.get(self._active_tool)
        return None
    
    def get_active_tool_name(self) -> Optional[str]:
        """Get the name of the currently active tool."""
        return self._active_tool
    
    def deactivate_all(self) -> None:
        """Deactivate all tools."""
        for tool in self._tools.values():
            tool.deactivate()
        self._active_tool = None