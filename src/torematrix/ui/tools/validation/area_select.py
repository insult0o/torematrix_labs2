"""
Area selection tool for manual validation workflow.

<<<<<<< HEAD
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
=======
Agent 2 implementation building on Agent 1's foundation.
This module provides the main area selection tool with advanced snapping algorithms
and magnetic edge detection for precise element boundary selection.
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
import math

from PyQt6.QtCore import (
    Qt, QObject, QPointF, QRectF, pyqtSignal, QEvent, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QKeyEvent, QMouseEvent, 
    QWheelEvent, QPainterPath, QTransform
>>>>>>> origin/main
)
from PyQt6.QtWidgets import QWidget

from torematrix.core.models import ElementType
from torematrix.utils.geometry import Point, Rect
from .shapes import (
    SelectionShape, RectangleShape, PolygonShape, FreehandShape,
    RectangleSelectionTool, PolygonSelectionTool, FreehandSelectionTool
)
<<<<<<< HEAD
=======
from .snapping import (
    SnapEngine, SnapTarget, SnapResult, SnapType,
    MagneticField, EdgeDetector, SnapConfiguration
)
>>>>>>> origin/main


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
<<<<<<< HEAD
=======
    MAGNETIC_EDGES = auto()      # Magnetic edge detection
>>>>>>> origin/main


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
<<<<<<< HEAD
=======
    
    # Agent 2: Snapping configuration
    snap_config: SnapConfiguration = field(default_factory=SnapConfiguration)
    magnetic_field_strength: float = 15.0  # Magnetic field radius
    edge_detection_sensitivity: float = 0.8  # Edge detection sensitivity
    show_snap_guides: bool = True
    snap_guide_color: QColor = field(default_factory=lambda: QColor(255, 0, 0, 128))
>>>>>>> origin/main


class ValidationAreaSelector(QObject):
    """
    Main area selection tool for manual validation workflow.
    
<<<<<<< HEAD
    This class manages the selection process, coordinates different shape tools,
    and emits signals when selections are completed or modified.
=======
    Agent 2 enhancement: Adds advanced snapping algorithms and magnetic edge detection
    for precise element boundary selection and improved user experience.
>>>>>>> origin/main
    """
    
    # Signals
    selection_started = pyqtSignal()
    selection_changed = pyqtSignal(object)  # SelectionShape
    selection_completed = pyqtSignal(object)  # SelectionShape
    selection_cancelled = pyqtSignal()
    mode_changed = pyqtSignal(AreaSelectionMode)
<<<<<<< HEAD
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the validation area selector."""
=======
    snap_target_found = pyqtSignal(object)  # SnapTarget
    snap_target_lost = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the validation area selector with snapping capabilities."""
>>>>>>> origin/main
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
<<<<<<< HEAD
        self.element_boundaries = []
=======
        self.element_boundaries: List[QRectF] = []
        
        # Agent 2: Snapping engine and magnetic field
        self.snap_engine = SnapEngine(self.config.snap_config)
        self.magnetic_field = MagneticField(self.config.magnetic_field_strength)
        self.edge_detector = EdgeDetector(self.config.edge_detection_sensitivity)
        
        # Current snap state
        self.current_snap_target: Optional[SnapTarget] = None
        self.snap_guides: List[QPointF] = []
        
        # Timer for delayed snapping calculations
        self.snap_timer = QTimer()
        self.snap_timer.setSingleShot(True)
        self.snap_timer.timeout.connect(self._calculate_snap_targets)
>>>>>>> origin/main
        
        # Install event filter if widget provided
        if self.widget:
            self.widget.installEventFilter(self)
    
<<<<<<< HEAD
=======
    def set_element_boundaries(self, boundaries: List[QRectF]):
        """Set element boundaries for snapping/alignment."""
        self.element_boundaries = boundaries
        
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
        self.magnetic_field.set_boundaries(boundaries)
    
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
        self.magnetic_field.start_interaction(snapped_point)
    
    def update_selection(self, point: QPointF):
        """Update the current selection with advanced snapping."""
        if not self.is_selecting or not self.current_tool:
            return
        
        # Apply smart snapping
        snapped_point = self._apply_smart_snapping(point)
        
        # Update magnetic field
        self.magnetic_field.update_interaction(snapped_point)
        
        # Update selection
        self.current_tool.update_selection(snapped_point)
        
        # Get current shape and apply constraints
        shape = self.current_tool.get_current_shape()
        if shape:
            self._apply_shape_constraints(shape)
            self.current_shape = shape
            self.selection_changed.emit(shape)
        
        # Update snap guides
        self._update_snap_guides(snapped_point)
    
    def complete_selection(self):
        """Complete the current selection."""
        if not self.is_selecting or not self.current_tool:
            return
        
        # Complete with tool
        shape = self.current_tool.complete_selection()
        
        if shape and self._is_valid_selection(shape):
            # Apply final constraints and snapping
            self._apply_shape_constraints(shape)
            self._apply_final_snapping(shape)
            
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
        self.magnetic_field.end_interaction()
    
    def _apply_smart_snapping(self, point: QPointF) -> QPointF:
        """Apply intelligent snapping based on current constraints and context."""
        # Start with original point
        result_point = point
        
        # Apply different snapping algorithms based on constraint
        if self.active_constraint == SelectionConstraint.ALIGN_TO_GRID:
            result_point = self._snap_to_grid(point)
        
        elif self.active_constraint == SelectionConstraint.ALIGN_TO_ELEMENTS:
            snap_result = self.snap_engine.find_snap_target(point)
            if snap_result.found:
                result_point = snap_result.snapped_point
                self.current_snap_target = snap_result.target
                self.snap_target_found.emit(snap_result.target)
            else:
                self.current_snap_target = None
                self.snap_target_lost.emit()
        
        elif self.active_constraint == SelectionConstraint.MAGNETIC_EDGES:
            # Apply magnetic edge detection
            magnetic_point = self.magnetic_field.apply_magnetic_force(point)
            edge_point = self.edge_detector.snap_to_edge(magnetic_point, self.element_boundaries)
            result_point = edge_point
        
        else:
            # Default: apply subtle magnetic assistance
            if self.config.snap_config.enable_magnetic_assistance:
                result_point = self.magnetic_field.apply_subtle_guidance(point)
        
        return result_point
    
    def _snap_to_grid(self, point: QPointF) -> QPointF:
        """Snap point to grid with sub-pixel precision."""
        grid_size = self.config.grid_size
        
        # Calculate grid position
        grid_x = round(point.x() / grid_size) * grid_size
        grid_y = round(point.y() / grid_size) * grid_size
        
        # Apply sub-pixel adjustment for smoother feel
        threshold = grid_size * 0.1
        if abs(point.x() - grid_x) < threshold:
            grid_x = point.x()
        if abs(point.y() - grid_y) < threshold:
            grid_y = point.y()
        
        return QPointF(grid_x, grid_y)
    
    def _apply_final_snapping(self, shape: SelectionShape):
        """Apply final snapping adjustments to completed shape."""
        if not self.config.snap_config.enable_final_adjustment:
            return
        
        # Get shape bounds
        bounds = shape.get_bounding_rect()
        
        # Find nearest element boundaries
        for element_rect in self.element_boundaries:
            # Check for alignment opportunities
            if self._should_align_to_element(bounds, element_rect):
                self._align_shape_to_element(shape, element_rect)
                break
    
    def _should_align_to_element(self, shape_bounds: QRectF, element_rect: QRectF) -> bool:
        """Check if shape should align to element boundary."""
        threshold = self.config.snap_threshold
        
        # Check for proximity to edges
        return (abs(shape_bounds.left() - element_rect.left()) < threshold or
                abs(shape_bounds.right() - element_rect.right()) < threshold or
                abs(shape_bounds.top() - element_rect.top()) < threshold or
                abs(shape_bounds.bottom() - element_rect.bottom()) < threshold)
    
    def _align_shape_to_element(self, shape: SelectionShape, element_rect: QRectF):
        """Align shape to element boundary."""
        if isinstance(shape, RectangleShape):
            bounds = shape.get_bounding_rect()
            threshold = self.config.snap_threshold
            
            # Align edges if close enough
            if abs(bounds.left() - element_rect.left()) < threshold:
                offset = element_rect.left() - bounds.left()
                shape.top_left.setX(shape.top_left.x() + offset)
            
            if abs(bounds.right() - element_rect.right()) < threshold:
                offset = element_rect.right() - bounds.right()
                shape.bottom_right.setX(shape.bottom_right.x() + offset)
            
            if abs(bounds.top() - element_rect.top()) < threshold:
                offset = element_rect.top() - bounds.top()
                shape.top_left.setY(shape.top_left.y() + offset)
            
            if abs(bounds.bottom() - element_rect.bottom()) < threshold:
                offset = element_rect.bottom() - bounds.bottom()
                shape.bottom_right.setY(shape.bottom_right.y() + offset)
    
    def _update_snap_guides(self, point: QPointF):
        """Update visual snap guides."""
        if not self.config.show_snap_guides:
            return
        
        self.snap_guides.clear()
        
        # Add grid guides
        if self.active_constraint == SelectionConstraint.ALIGN_TO_GRID:
            self._add_grid_guides(point)
        
        # Add element alignment guides
        if self.active_constraint == SelectionConstraint.ALIGN_TO_ELEMENTS:
            self._add_element_guides(point)
        
        # Add magnetic field visualization
        if self.active_constraint == SelectionConstraint.MAGNETIC_EDGES:
            self._add_magnetic_guides(point)
    
    def _add_grid_guides(self, point: QPointF):
        """Add grid alignment guides."""
        grid_size = self.config.grid_size
        
        # Calculate nearest grid lines
        grid_x = round(point.x() / grid_size) * grid_size
        grid_y = round(point.y() / grid_size) * grid_size
        
        # Add guide points
        self.snap_guides.extend([
            QPointF(grid_x, point.y()),
            QPointF(point.x(), grid_y),
            QPointF(grid_x, grid_y)
        ])
    
    def _add_element_guides(self, point: QPointF):
        """Add element alignment guides."""
        threshold = self.config.snap_threshold * 2
        
        for element_rect in self.element_boundaries:
            # Check for proximity to element
            if (abs(point.x() - element_rect.center().x()) < threshold or
                abs(point.y() - element_rect.center().y()) < threshold):
                
                # Add alignment guides
                self.snap_guides.extend([
                    QPointF(element_rect.center().x(), point.y()),
                    QPointF(point.x(), element_rect.center().y()),
                    element_rect.center()
                ])
    
    def _add_magnetic_guides(self, point: QPointF):
        """Add magnetic field visualization guides."""
        magnetic_influences = self.magnetic_field.get_field_influences(point)
        self.snap_guides.extend(magnetic_influences)
    
    def _calculate_snap_targets(self):
        """Calculate snap targets for current mouse position."""
        # This is called by timer to avoid expensive calculations on every mouse move
        if not self.is_selecting:
            return
        
        # Recalculate snap targets based on current selection
        # This allows for dynamic snapping as selection evolves
        pass
    
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
    
    def _draw_snap_target(self, painter: QPainter, target: SnapTarget):
        """Draw a snap target indicator."""
        painter.save()
        
        # Different colors for different snap types
        if target.snap_type == SnapType.CORNER:
            color = QColor(255, 0, 0, 180)  # Red for corners
        elif target.snap_type == SnapType.EDGE:
            color = QColor(0, 255, 0, 180)  # Green for edges
        elif target.snap_type == SnapType.CENTER:
            color = QColor(0, 0, 255, 180)  # Blue for centers
        else:
            color = QColor(255, 255, 0, 180)  # Yellow for other
        
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
    
    # Keep existing methods from Agent 1 with minimal changes
>>>>>>> origin/main
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
<<<<<<< HEAD
    
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
=======
        
        # Update snapping configuration based on constraint
        if constraint == SelectionConstraint.MAGNETIC_EDGES:
            self.config.snap_config.enable_magnetic_assistance = True
        elif constraint == SelectionConstraint.ALIGN_TO_ELEMENTS:
            self.config.snap_config.enable_element_snapping = True
        elif constraint == SelectionConstraint.ALIGN_TO_GRID:
            self.config.snap_config.enable_grid_snapping = True
>>>>>>> origin/main
    
    def cancel_selection(self):
        """Cancel the current selection."""
        if self.is_selecting and self.current_tool:
            self.current_tool.cancel_selection()
        
        self.is_selecting = False
        self.current_shape = None
<<<<<<< HEAD
=======
        self.current_snap_target = None
        self.snap_guides.clear()
        self.magnetic_field.end_interaction()
>>>>>>> origin/main
        self.selection_cancelled.emit()
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections.clear()
        self.selected_indices.clear()
        self.current_shape = None
<<<<<<< HEAD
=======
        self.current_snap_target = None
        self.snap_guides.clear()
>>>>>>> origin/main
    
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
    
<<<<<<< HEAD
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
    
=======
>>>>>>> origin/main
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
    
<<<<<<< HEAD
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
    
=======
>>>>>>> origin/main
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
        
<<<<<<< HEAD
        painter.restore()
=======
        painter.restore()
    
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
>>>>>>> origin/main
