"""
Area selection tool for manual validation workflow.

This module provides the main area selection tool that manages different selection
modes and coordinates the various shape tools for creating validation areas.
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field

from PyQt6.QtCore import (
    Qt, QObject, QPointF, QRectF, pyqtSignal, QEvent
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QKeyEvent, QMouseEvent, 
    QWheelEvent, QPainterPath
)
from PyQt6.QtWidgets import QWidget

from torematrix.core.models import ElementType
from torematrix.utils.geometry import Point, Rect
from .shapes import (
    SelectionShape, RectangleShape, PolygonShape, FreehandShape,
    RectangleSelectionTool, PolygonSelectionTool, FreehandSelectionTool
)


class AreaSelectionMode(Enum):
    """Selection modes for validation areas."""
    CREATE_NEW = auto()          # Create new element from scratch
    ADJUST_BOUNDARY = auto()     # Adjust existing element boundary
    EXCLUDE_AREA = auto()        # Create exclusion zone in element
    MERGE_ELEMENTS = auto()      # Merge multiple elements
    SPLIT_ELEMENT = auto()       # Split element into multiple parts


class SelectionConstraint(Enum):
    """Constraints that can be applied during selection."""
    NONE = auto()                # No constraints
    ASPECT_RATIO = auto()        # Maintain aspect ratio
    FIXED_SIZE = auto()          # Fixed size selection
    ALIGN_TO_GRID = auto()       # Snap to grid
    ALIGN_TO_ELEMENTS = auto()   # Snap to existing elements


@dataclass
class ValidationSelectionConfig:
    """Configuration for validation area selection."""
    # Visual settings
    selection_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 100))
    selection_border_color: QColor = field(default_factory=lambda: QColor(0, 120, 215))
    selection_border_width: float = 2.0
    handle_size: float = 8.0
    handle_color: QColor = field(default_factory=lambda: QColor(0, 120, 215))
    
    # Behavior settings
    min_selection_size: float = 10.0  # Minimum size in pixels
    snap_threshold: float = 10.0      # Snap distance in pixels
    smoothing_factor: float = 2.0     # For freehand smoothing
    
    # Grid settings
    grid_size: float = 20.0
    show_grid: bool = False
    grid_color: QColor = field(default_factory=lambda: QColor(200, 200, 200, 50))
    
    # Constraints
    aspect_ratio: Optional[float] = None  # Width/height ratio
    fixed_width: Optional[float] = None
    fixed_height: Optional[float] = None
    
    # Multi-selection
    allow_multi_select: bool = True
    multi_select_mode: str = "additive"  # "additive" or "subtractive"


class ValidationAreaSelector(QObject):
    """
    Main area selection tool for manual validation workflow.
    
    This class manages the selection process, coordinates different shape tools,
    and emits signals when selections are completed or modified.
    """
    
    # Signals
    selection_started = pyqtSignal()
    selection_changed = pyqtSignal(object)  # SelectionShape
    selection_completed = pyqtSignal(object)  # SelectionShape
    selection_cancelled = pyqtSignal()
    mode_changed = pyqtSignal(AreaSelectionMode)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the validation area selector."""
        super().__init__(parent)
        
        self.widget = parent
        self.config = ValidationSelectionConfig()
        
        # Current state
        self.mode = AreaSelectionMode.CREATE_NEW
        self.active_constraint = SelectionConstraint.NONE
        self.is_selecting = False
        self.current_tool = None
        self.current_shape = None
        
        # Shape tools
        self.shape_tools = {
            'rectangle': RectangleSelectionTool(),
            'polygon': PolygonSelectionTool(),
            'freehand': FreehandSelectionTool()
        }
        self.active_tool_name = 'rectangle'
        
        # Selection history
        self.selections: List[SelectionShape] = []
        self.selected_indices: Set[int] = set()
        
        # Element references (for snapping/alignment)
        self.element_boundaries = []
        
        # Install event filter if widget provided
        if self.widget:
            self.widget.installEventFilter(self)
    
    def set_mode(self, mode: AreaSelectionMode):
        """Set the current selection mode."""
        self.mode = mode
        self.mode_changed.emit(mode)
    
    def set_tool(self, tool_name: str):
        """Set the active shape tool."""
        if tool_name in self.shape_tools:
            self.active_tool_name = tool_name
            self.current_tool = self.shape_tools[tool_name]
    
    def set_constraint(self, constraint: SelectionConstraint):
        """Set the active selection constraint."""
        self.active_constraint = constraint
    
    def set_element_boundaries(self, boundaries: List[QRectF]):
        """Set element boundaries for snapping/alignment."""
        self.element_boundaries = boundaries
    
    def start_selection(self, point: QPointF):
        """Start a new selection at the given point."""
        if not self.current_tool:
            self.current_tool = self.shape_tools[self.active_tool_name]
        
        # Apply constraints to starting point
        constrained_point = self._apply_point_constraints(point)
        
        # Start selection with tool
        self.current_tool.start_selection(constrained_point)
        self.is_selecting = True
        self.selection_started.emit()
    
    def update_selection(self, point: QPointF):
        """Update the current selection with a new point."""
        if not self.is_selecting or not self.current_tool:
            return
        
        # Apply constraints to point
        constrained_point = self._apply_point_constraints(point)
        
        # Update selection
        self.current_tool.update_selection(constrained_point)
        
        # Get current shape and apply constraints
        shape = self.current_tool.get_current_shape()
        if shape:
            self._apply_shape_constraints(shape)
            self.current_shape = shape
            self.selection_changed.emit(shape)
    
    def complete_selection(self):
        """Complete the current selection."""
        if not self.is_selecting or not self.current_tool:
            return
        
        # Complete with tool
        shape = self.current_tool.complete_selection()
        
        if shape and self._is_valid_selection(shape):
            # Apply final constraints
            self._apply_shape_constraints(shape)
            
            # Add to selections
            self.selections.append(shape)
            self.selected_indices.add(len(self.selections) - 1)
            
            # Emit completion
            self.selection_completed.emit(shape)
        
        # Reset state
        self.is_selecting = False
        self.current_shape = None
    
    def cancel_selection(self):
        """Cancel the current selection."""
        if self.is_selecting and self.current_tool:
            self.current_tool.cancel_selection()
        
        self.is_selecting = False
        self.current_shape = None
        self.selection_cancelled.emit()
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections.clear()
        self.selected_indices.clear()
        self.current_shape = None
    
    def delete_selection(self, index: int):
        """Delete a specific selection."""
        if 0 <= index < len(self.selections):
            self.selections.pop(index)
            self.selected_indices.discard(index)
            # Adjust indices
            self.selected_indices = {
                i if i < index else i - 1 
                for i in self.selected_indices
            }
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events for the widget."""
        if obj != self.widget:
            return False
        
        if event.type() == QEvent.Type.MouseButtonPress:
            mouse_event = event
            if mouse_event.button() == Qt.MouseButton.LeftButton:
                self.start_selection(mouse_event.position())
                return True
        
        elif event.type() == QEvent.Type.MouseMove:
            mouse_event = event
            if self.is_selecting:
                self.update_selection(mouse_event.position())
                return True
        
        elif event.type() == QEvent.Type.MouseButtonRelease:
            mouse_event = event
            if mouse_event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
                self.complete_selection()
                return True
        
        elif event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Escape and self.is_selecting:
                self.cancel_selection()
                return True
        
        return False
    
    def paint(self, painter: QPainter):
        """Paint all selections and current selection."""
        # Draw grid if enabled
        if self.config.show_grid:
            self._draw_grid(painter)
        
        # Draw completed selections
        for i, shape in enumerate(self.selections):
            is_selected = i in self.selected_indices
            self._draw_shape(painter, shape, is_selected)
        
        # Draw current selection
        if self.current_shape:
            self._draw_shape(painter, self.current_shape, True, is_current=True)
    
    def _apply_point_constraints(self, point: QPointF) -> QPointF:
        """Apply constraints to a point."""
        x, y = point.x(), point.y()
        
        # Grid alignment
        if self.active_constraint == SelectionConstraint.ALIGN_TO_GRID:
            grid_size = self.config.grid_size
            x = round(x / grid_size) * grid_size
            y = round(y / grid_size) * grid_size
        
        # Element alignment
        elif self.active_constraint == SelectionConstraint.ALIGN_TO_ELEMENTS:
            snap_point = self._find_snap_point(point)
            if snap_point:
                return snap_point
        
        return QPointF(x, y)
    
    def _apply_shape_constraints(self, shape: SelectionShape):
        """Apply constraints to a shape."""
        if self.active_constraint == SelectionConstraint.ASPECT_RATIO:
            if self.config.aspect_ratio and hasattr(shape, 'maintain_aspect_ratio'):
                shape.maintain_aspect_ratio(self.config.aspect_ratio)
        
        elif self.active_constraint == SelectionConstraint.FIXED_SIZE:
            if self.config.fixed_width and self.config.fixed_height:
                if hasattr(shape, 'set_fixed_size'):
                    shape.set_fixed_size(self.config.fixed_width, self.config.fixed_height)
    
    def _is_valid_selection(self, shape: SelectionShape) -> bool:
        """Check if a selection is valid."""
        bounds = shape.get_bounding_rect()
        min_size = self.config.min_selection_size
        return bounds.width() >= min_size and bounds.height() >= min_size
    
    def _find_snap_point(self, point: QPointF) -> Optional[QPointF]:
        """Find snap point near element boundaries."""
        threshold = self.config.snap_threshold
        
        for rect in self.element_boundaries:
            # Check corners
            corners = [
                rect.topLeft(), rect.topRight(),
                rect.bottomLeft(), rect.bottomRight()
            ]
            
            for corner in corners:
                if (point - corner).manhattanLength() < threshold:
                    return corner
            
            # Check edges
            edges = [
                (rect.topLeft(), rect.topRight()),
                (rect.topRight(), rect.bottomRight()),
                (rect.bottomRight(), rect.bottomLeft()),
                (rect.bottomLeft(), rect.topLeft())
            ]
            
            for start, end in edges:
                # Project point onto edge
                edge_vec = end - start
                edge_len = (edge_vec.x()**2 + edge_vec.y()**2)**0.5
                if edge_len > 0:
                    t = max(0, min(1, QPointF.dotProduct(point - start, edge_vec) / (edge_len**2)))
                    projected = start + t * edge_vec
                    if (point - projected).manhattanLength() < threshold:
                        return projected
        
        return None
    
    def _draw_grid(self, painter: QPainter):
        """Draw alignment grid."""
        painter.save()
        
        pen = QPen(self.config.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Get widget bounds
        if self.widget:
            rect = self.widget.rect()
            grid_size = self.config.grid_size
            
            # Draw vertical lines
            x = 0
            while x <= rect.width():
                painter.drawLine(int(x), 0, int(x), rect.height())
                x += grid_size
            
            # Draw horizontal lines
            y = 0
            while y <= rect.height():
                painter.drawLine(0, int(y), rect.width(), int(y))
                y += grid_size
        
        painter.restore()
    
    def _draw_shape(self, painter: QPainter, shape: SelectionShape, 
                    is_selected: bool, is_current: bool = False):
        """Draw a selection shape."""
        painter.save()
        
        # Set colors based on state
        if is_current:
            fill_color = QColor(self.config.selection_color)
            fill_color.setAlpha(150)
            border_color = self.config.selection_border_color
        else:
            fill_color = QColor(self.config.selection_color)
            fill_color.setAlpha(100 if is_selected else 50)
            border_color = QColor(self.config.selection_border_color)
            border_color.setAlpha(255 if is_selected else 128)
        
        # Draw shape
        pen = QPen(border_color)
        pen.setWidth(self.config.selection_border_width)
        pen.setStyle(Qt.PenStyle.SolidLine if not is_current else Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill_color))
        
        shape.draw(painter)
        
        # Draw handles if selected
        if is_selected and not is_current:
            self._draw_handles(painter, shape)
        
        painter.restore()
    
    def _draw_handles(self, painter: QPainter, shape: SelectionShape):
        """Draw selection handles."""
        handles = shape.get_handles()
        
        painter.save()
        painter.setPen(QPen(self.config.handle_color, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        
        handle_size = self.config.handle_size
        for handle in handles:
            rect = QRectF(
                handle.x() - handle_size/2,
                handle.y() - handle_size/2,
                handle_size,
                handle_size
            )
            painter.drawRect(rect)
        
        painter.restore()
    
    # Integration hooks for Agent 2, 3, and 4
    def get_snapping_hooks(self):
        """Get hooks for advanced snapping (Agent 2)."""
        return {
            'apply_point_constraints': self._apply_point_constraints,
            'element_boundaries': self.element_boundaries
        }
    
    def get_shape_manipulation_hooks(self):
        """Get hooks for advanced shape manipulation (Agent 3)."""
        return {
            'current_selections': self.selections,
            'selected_indices': self.selected_indices,
            'delete_selection': self.delete_selection
        }
    
    def get_integration_hooks(self):
        """Get hooks for UI integration (Agent 4)."""
        return {
            'selector': self,
            'config': self.config,
            'signals': {
                'selection_started': self.selection_started,
                'selection_changed': self.selection_changed,
                'selection_completed': self.selection_completed,
                'selection_cancelled': self.selection_cancelled,
                'mode_changed': self.mode_changed
            }
        }