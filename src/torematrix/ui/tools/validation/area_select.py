"""
Area selection tool for manual validation workflow.

Agent 2 implementation building on Agent 1's foundation.
This module provides the main area selection tool with advanced snapping algorithms
and magnetic edge detection for precise element boundary selection.
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
import math
import logging

from PyQt6.QtCore import (
    Qt, QObject, QPointF, QRectF, pyqtSignal, QEvent, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QKeyEvent, QMouseEvent, 
    QWheelEvent, QPainterPath, QTransform
)
from PyQt6.QtWidgets import QWidget

from torematrix.core.models import ElementType
from torematrix.utils.geometry import Point, Rect
from .shapes import (
    SelectionShape, RectangleShape, PolygonShape, FreehandShape,
    RectangleSelectionTool, PolygonSelectionTool, FreehandSelectionTool
)

try:
    from .snapping import (
        SnapEngine, SnapTarget, SnapResult, SnapType,
        MagneticField, EdgeDetector, SnapConfiguration
    )
    _snapping_available = True
except ImportError:
    _snapping_available = False

logger = logging.getLogger(__name__)


class AreaSelectionMode(Enum):
    """Selection modes for validation areas."""
    CREATE_NEW = auto()          # Create new element from scratch
    ADJUST_BOUNDARY = auto()     # Adjust existing element boundary
    EXCLUDE_AREA = auto()        # Create exclusion zone in element
    MERGE_ELEMENTS = auto()      # Merge multiple elements
    SPLIT_ELEMENT = auto()       # Split element into multiple parts


class SelectionConstraint(Enum):
    """Constraints that can be applied to area selections."""
    NONE = auto()                # No constraints
    ASPECT_RATIO = auto()        # Maintain specific aspect ratio
    FIXED_SIZE = auto()          # Fixed width/height
    ALIGN_TO_GRID = auto()       # Snap to grid positions
    ALIGN_TO_ELEMENTS = auto()   # Snap to existing elements
    MAGNETIC_EDGES = auto()      # Magnetic edge detection


@dataclass
class ValidationSelectionConfig:
    """Configuration for validation area selection."""
    grid_size: int = 10
    snap_threshold: int = 15
    min_selection_size: int = 10
    
    # Visual styling
    selection_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 100))
    selection_border_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 255))
    selection_border_width: int = 2
    handle_color: QColor = field(default_factory=lambda: QColor(255, 255, 255, 255))
    handle_size: int = 8
    grid_color: QColor = field(default_factory=lambda: QColor(200, 200, 200, 100))
    
    # Grid and guides
    show_grid: bool = True
    show_snap_guides: bool = True
    snap_guide_color: QColor = field(default_factory=lambda: QColor(255, 0, 0, 128))
    
    # Constraints
    aspect_ratio: Optional[float] = None
    fixed_width: Optional[int] = None
    fixed_height: Optional[int] = None
    
    # Advanced snapping (Agent 2)
    magnetic_field_strength: float = 15.0
    edge_detection_sensitivity: float = 0.8


class ValidationAreaSelector(QObject):
    """
    Main area selection tool for manual validation workflow.
    
    Agent 2 enhancement: Adds advanced snapping algorithms and magnetic edge detection
    for precise element boundary selection and improved user experience.
    """
    
    # Signals
    selection_started = pyqtSignal()
    selection_changed = pyqtSignal(object)  # SelectionShape
    selection_completed = pyqtSignal(object)  # SelectionShape
    selection_cancelled = pyqtSignal()
    mode_changed = pyqtSignal(AreaSelectionMode)
    snap_target_found = pyqtSignal(object)  # SnapTarget
    snap_target_lost = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the validation area selector with snapping capabilities."""
        super().__init__(parent)
        
        self.widget = parent
        self.config = ValidationSelectionConfig()
        
        # Current state
        self.mode = AreaSelectionMode.CREATE_NEW
        self.active_constraint = SelectionConstraint.NONE
        self.is_selecting = False
        self.current_shape: Optional[SelectionShape] = None
        self.current_tool: Optional[object] = None
        
        # Shape tools
        self.shape_tools = {
            'rectangle': RectangleSelectionTool(),
            'polygon': PolygonSelectionTool(),
            'freehand': FreehandSelectionTool()
        }
        self.active_tool_name = 'rectangle'
        
        # Selection management
        self.selections: List[SelectionShape] = []
        self.selected_indices: Set[int] = set()
        
        # Element references (for snapping/alignment)
        self.element_boundaries: List[QRectF] = []
        
        # Advanced snapping (Agent 2)
        if _snapping_available:
            self.snap_engine = SnapEngine()
            self.magnetic_field = MagneticField(self.config.magnetic_field_strength)
            self.edge_detector = EdgeDetector(self.config.edge_detection_sensitivity)
        else:
            self.snap_engine = None
            self.magnetic_field = None
            self.edge_detector = None
        
        # Current snap state
        self.current_snap_target: Optional = None
        self.snap_guides: List[QPointF] = []
        
        # Timer for delayed snapping calculations
        self.snap_timer = QTimer()
        self.snap_timer.setSingleShot(True)
        self.snap_timer.timeout.connect(self._calculate_snap_targets)
        
        # Install event filter if widget provided
        if self.widget:
            self.widget.installEventFilter(self)
    
    def set_element_boundaries(self, boundaries: List[QRectF]):
        """Set element boundaries for snapping/alignment."""
        self.element_boundaries = boundaries
        
        if _snapping_available and self.snap_engine:
            # Update snap engine with new targets
            snap_targets = []
            for rect in boundaries:
                # Add corner targets
                snap_targets.extend([
                    SnapTarget(rect.topLeft(), SnapType.CORNER),
                    SnapTarget(rect.topRight(), SnapType.CORNER),
                    SnapTarget(rect.bottomLeft(), SnapType.CORNER),
                    SnapTarget(rect.bottomRight(), SnapType.CORNER)
                ])
                
                # Add edge targets
                snap_targets.extend([
                    SnapTarget(QPointF(rect.center().x(), rect.top()), SnapType.EDGE),
                    SnapTarget(QPointF(rect.right(), rect.center().y()), SnapType.EDGE),
                    SnapTarget(QPointF(rect.center().x(), rect.bottom()), SnapType.EDGE),
                    SnapTarget(QPointF(rect.left(), rect.center().y()), SnapType.EDGE)
                ])
                
                # Add midpoint targets
                snap_targets.append(SnapTarget(rect.center(), SnapType.CENTER))
            
            self.snap_engine.set_targets(snap_targets)
            if self.magnetic_field:
                self.magnetic_field.set_boundaries(boundaries)
    
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
    
    def start_selection(self, point: QPointF):
        """Start a new selection at the given point with snapping."""
        if not self.current_tool:
            self.current_tool = self.shape_tools[self.active_tool_name]
        
        # Apply snapping to starting point
        snapped_point = self._apply_smart_snapping(point)
        
        # Start selection with tool
        self.current_tool.start_selection(snapped_point)
        self.is_selecting = True
        self.selection_started.emit()
        
        # Start magnetic field interaction
        if self.magnetic_field:
            self.magnetic_field.start_interaction(snapped_point)
    
    def update_selection(self, point: QPointF):
        """Update the current selection with advanced snapping."""
        if not self.is_selecting or not self.current_tool:
            return
        
        # Apply smart snapping
        snapped_point = self._apply_smart_snapping(point)
        
        # Update magnetic field
        if self.magnetic_field:
            self.magnetic_field.update_interaction(snapped_point)
        
        # Update selection
        self.current_tool.update_selection(snapped_point)
        
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
        self.current_snap_target = None
        self.snap_guides.clear()
        if self.magnetic_field:
            self.magnetic_field.end_interaction()
    
    def cancel_selection(self):
        """Cancel the current selection."""
        if self.is_selecting and self.current_tool:
            self.current_tool.cancel_selection()
        
        self.is_selecting = False
        self.current_shape = None
        self.current_snap_target = None
        self.snap_guides.clear()
        if self.magnetic_field:
            self.magnetic_field.end_interaction()
        self.selection_cancelled.emit()
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections.clear()
        self.selected_indices.clear()
        self.current_shape = None
        self.current_snap_target = None
        self.snap_guides.clear()
    
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
    
    def _apply_smart_snapping(self, point: QPointF) -> QPointF:
        """Apply intelligent snapping based on current constraints and context."""
        # Start with original point
        result_point = point
        
        # Apply different snapping algorithms based on constraint
        if self.active_constraint == SelectionConstraint.ALIGN_TO_GRID:
            result_point = self._snap_to_grid(point)
        
        elif self.active_constraint == SelectionConstraint.ALIGN_TO_ELEMENTS:
            if _snapping_available and self.snap_engine:
                snap_result = self.snap_engine.find_snap_target(point)
                if snap_result and snap_result.found:
                    result_point = snap_result.snapped_point
                    self.current_snap_target = snap_result.target
                    self.snap_target_found.emit(snap_result.target)
                else:
                    self.current_snap_target = None
                    self.snap_target_lost.emit()
        
        elif self.active_constraint == SelectionConstraint.MAGNETIC_EDGES:
            if _snapping_available and self.magnetic_field and self.edge_detector:
                # Apply magnetic edge detection
                magnetic_point = self.magnetic_field.apply_magnetic_force(point)
                edge_point = self.edge_detector.snap_to_edge(magnetic_point, self.element_boundaries)
                result_point = edge_point
        
        return result_point
    
    def _snap_to_grid(self, point: QPointF) -> QPointF:
        """Snap point to grid with sub-pixel precision."""
        grid_size = self.config.grid_size
        
        # Calculate grid position
        grid_x = round(point.x() / grid_size) * grid_size
        grid_y = round(point.y() / grid_size) * grid_size
        
        # Apply soft snapping - only snap if close enough
        threshold = grid_size / 4
        if abs(point.x() - grid_x) < threshold:
            grid_x = point.x()
        if abs(point.y() - grid_y) < threshold:
            grid_y = point.y()
        
        return QPointF(grid_x, grid_y)
    
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
    
    def _calculate_snap_targets(self):
        """Calculate snap targets for current mouse position."""
        # This is called by timer to avoid expensive calculations on every mouse move
        if not self.is_selecting:
            return
        
        # Recalculate snap targets based on current selection
        # This allows for dynamic snapping as selection evolves
        pass
    
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
        """Paint all selections and snap guides."""
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
        
        # Draw snap guides
        if self.config.show_snap_guides:
            self._draw_snap_guides(painter)
        
        # Draw magnetic field visualization
        if self.active_constraint == SelectionConstraint.MAGNETIC_EDGES:
            self._draw_magnetic_field(painter)
    
    def _draw_grid(self, painter: QPainter):
        """Draw alignment grid."""
        painter.save()
        
        pen = QPen(self.config.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Get widget dimensions
        if self.widget:
            width = self.widget.width()
            height = self.widget.height()
            grid_size = self.config.grid_size
            
            # Draw vertical lines
            for x in range(0, width, grid_size):
                painter.drawLine(x, 0, x, height)
            
            # Draw horizontal lines
            for y in range(0, height, grid_size):
                painter.drawLine(0, y, width, y)
        
        painter.restore()
    
    def _draw_shape(self, painter: QPainter, shape: SelectionShape, is_selected: bool, is_current: bool = False):
        """Draw a selection shape."""
        painter.save()
        
        # Set colors based on state
        if is_current:
            fill_color = QColor(self.config.selection_color)
            fill_color.setAlpha(150)
            border_color = self.config.selection_border_color
        elif is_selected:
            fill_color = self.config.selection_color
            border_color = self.config.selection_border_color
        else:
            fill_color = QColor(self.config.selection_color)
            fill_color.setAlpha(50)
            border_color = QColor(self.config.selection_border_color)
            border_color.setAlpha(128)
        
        # Draw shape
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(border_color, self.config.selection_border_width))
        
        # Use shape's draw method
        shape.draw(painter)
        
        # Draw handles for selected shapes
        if is_selected or is_current:
            self._draw_selection_handles(painter, shape)
        
        painter.restore()
    
    def _draw_selection_handles(self, painter: QPainter, shape: SelectionShape):
        """Draw selection handles."""
        painter.save()
        
        handle_size = self.config.handle_size
        painter.setBrush(QBrush(self.config.handle_color))
        painter.setPen(QPen(self.config.selection_border_color, 1))
        
        # Get handle positions from shape
        handles = shape.get_handles()
        for handle in handles:
            rect = QRectF(
                handle.x() - handle_size/2,
                handle.y() - handle_size/2,
                handle_size,
                handle_size
            )
            painter.drawRect(rect)
        
        painter.restore()
    
    def _draw_snap_guides(self, painter: QPainter):
        """Draw snap guides and indicators."""
        painter.save()
        
        pen = QPen(self.config.snap_guide_color)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        # Draw guide lines
        for guide_point in self.snap_guides:
            # Draw crosshair at guide point
            size = 6
            painter.drawLine(
                guide_point.x() - size, guide_point.y(),
                guide_point.x() + size, guide_point.y()
            )
            painter.drawLine(
                guide_point.x(), guide_point.y() - size,
                guide_point.x(), guide_point.y() + size
            )
        
        # Draw current snap target
        if self.current_snap_target:
            self._draw_snap_target(painter, self.current_snap_target)
        
        painter.restore()
    
    def _draw_snap_target(self, painter: QPainter, target):
        """Draw a snap target indicator."""
        if not _snapping_available:
            return
            
        painter.save()
        
        # Different colors for different snap types
        color = QColor(255, 255, 0, 180)  # Default yellow
        
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw target indicator
        size = 8
        painter.drawEllipse(
            target.position.x() - size/2,
            target.position.y() - size/2,
            size, size
        )
        
        painter.restore()
    
    def _draw_magnetic_field(self, painter: QPainter):
        """Draw magnetic field visualization."""
        if not _snapping_available:
            return
            
        painter.save()
        
        # Draw magnetic field influences
        field_color = QColor(255, 0, 255, 60)  # Magenta for magnetic field
        brush = QBrush(field_color)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw field influence areas
        for rect in self.element_boundaries:
            expanded_rect = rect.adjusted(
                -self.config.magnetic_field_strength,
                -self.config.magnetic_field_strength,
                self.config.magnetic_field_strength,
                self.config.magnetic_field_strength
            )
            painter.drawRect(expanded_rect)
        
        painter.restore()