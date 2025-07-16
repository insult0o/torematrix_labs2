"""
<<<<<<< HEAD
Area selection component for manual validation workflows.

This module provides the ValidationAreaSelector class and related functionality
for selecting areas in documents during manual validation.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from PyQt6.QtCore import QObject, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class AreaSelectionMode(Enum):
    """Modes for area selection during validation."""
    CREATE_NEW = auto()      # Create new element from selection
    ADJUST_BOUNDARY = auto() # Adjust existing element boundary
    EXCLUDE_AREA = auto()    # Mark area to exclude from processing
    MERGE_ELEMENTS = auto()  # Merge multiple elements
    SPLIT_ELEMENT = auto()   # Split element into multiple


class SelectionConstraint(Enum):
    """Constraints that can be applied to selections."""
    NONE = auto()
    ASPECT_RATIO = auto()
    FIXED_SIZE = auto()
    ALIGN_TO_GRID = auto()
    ALIGN_TO_ELEMENTS = auto()
=======
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
<<<<<<< HEAD
    grid_size: int = 10
    snap_distance: int = 5
    min_selection_size: int = 10
    selection_color: QColor = QColor(0, 120, 215, 100)
    border_color: QColor = QColor(0, 120, 215, 255)
    handle_color: QColor = QColor(255, 255, 255, 255)
    handle_size: int = 8
    show_grid: bool = True
    show_rulers: bool = True
    enable_snapping: bool = True


class ValidationAreaSelector(QObject):
    """Main coordinator for area selection during manual validation."""
    
    # Signals
    selection_started = pyqtSignal(QPoint)
    selection_changed = pyqtSignal(QRect)
    selection_finished = pyqtSignal(QRect)
    mode_changed = pyqtSignal(AreaSelectionMode)
    constraint_changed = pyqtSignal(SelectionConstraint)
    
    def __init__(self, viewer, selection_manager=None, snapping_manager=None):
        """Initialize area selector."""
        super().__init__()
        self.viewer = viewer
        self.selection_manager = selection_manager
        self.snapping_manager = snapping_manager
        self.config = ValidationSelectionConfig()
        
        # State
        self.mode = AreaSelectionMode.CREATE_NEW
        self.constraint = SelectionConstraint.NONE
        self.is_selecting = False
        self.selection_start = QPoint()
        self.current_selection = QRect()
        self.selections = []
        
        # Grid and snapping
        self.grid_enabled = True
        self.snap_enabled = True
        
        logger.info("ValidationAreaSelector initialized")
    
    def set_mode(self, mode: AreaSelectionMode):
        """Set the current selection mode."""
        if self.mode != mode:
            self.mode = mode
            self.mode_changed.emit(mode)
            logger.debug(f"Selection mode changed to {mode.name}")
    
    def set_constraint(self, constraint: SelectionConstraint):
        """Set the current selection constraint."""
        if self.constraint != constraint:
            self.constraint = constraint
            self.constraint_changed.emit(constraint)
            logger.debug(f"Selection constraint changed to {constraint.name}")
    
    def set_config(self, config: ValidationSelectionConfig):
        """Update configuration."""
        self.config = config
        logger.debug("Configuration updated")
    
    def start_selection(self, start_point: QPoint):
        """Start area selection."""
        self.is_selecting = True
        self.selection_start = start_point
        self.current_selection = QRect(start_point, start_point)
        self.selection_started.emit(start_point)
        logger.debug(f"Selection started at {start_point}")
    
    def update_selection(self, current_point: QPoint):
        """Update current selection area."""
        if not self.is_selecting:
            return
        
        # Apply snapping if enabled
        if self.snap_enabled:
            current_point = self._apply_snapping(current_point)
        
        # Apply constraints
        current_point = self._apply_constraints(current_point)
        
        # Update selection rectangle
        self.current_selection = QRect(self.selection_start, current_point).normalized()
        self.selection_changed.emit(self.current_selection)
        logger.debug(f"Selection updated to {self.current_selection}")
    
    def finish_selection(self):
        """Finish area selection."""
        if not self.is_selecting:
            return
        
        self.is_selecting = False
        
        # Validate minimum size
        if (self.current_selection.width() < self.config.min_selection_size or
            self.current_selection.height() < self.config.min_selection_size):
            logger.warning("Selection too small, ignoring")
            return
        
        # Add to selections
        self.selections.append(self.current_selection)
        self.selection_finished.emit(self.current_selection)
        logger.info(f"Selection finished: {self.current_selection}")
    
    def cancel_selection(self):
        """Cancel current selection."""
        if self.is_selecting:
            self.is_selecting = False
            self.current_selection = QRect()
            logger.debug("Selection cancelled")
=======
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
>>>>>>> origin/main
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections.clear()
<<<<<<< HEAD
        self.current_selection = QRect()
        logger.debug("All selections cleared")
    
    def get_selections(self) -> List[QRect]:
        """Get all current selections."""
        return self.selections.copy()
    
    def remove_selection(self, index: int):
        """Remove selection at index."""
        if 0 <= index < len(self.selections):
            removed = self.selections.pop(index)
            logger.debug(f"Removed selection at index {index}: {removed}")
    
    def _apply_snapping(self, point: QPoint) -> QPoint:
        """Apply snapping to point."""
        if not self.snap_enabled:
            return point
        
        # Grid snapping
        if self.grid_enabled:
            grid_size = self.config.grid_size
            snapped_x = round(point.x() / grid_size) * grid_size
            snapped_y = round(point.y() / grid_size) * grid_size
            return QPoint(snapped_x, snapped_y)
        
        # Element snapping (basic implementation)
        if self.snapping_manager:
            return self.snapping_manager.snap_point(point)
        
        return point
    
    def _apply_constraints(self, point: QPoint) -> QPoint:
        """Apply constraints to point."""
        if self.constraint == SelectionConstraint.NONE:
            return point
        
        if self.constraint == SelectionConstraint.ASPECT_RATIO:
            # Maintain square aspect ratio
            start = self.selection_start
            width = abs(point.x() - start.x())
            height = abs(point.y() - start.y())
            size = max(width, height)
            
            if point.x() >= start.x():
                new_x = start.x() + size
            else:
                new_x = start.x() - size
            
            if point.y() >= start.y():
                new_y = start.y() + size
            else:
                new_y = start.y() - size
            
            return QPoint(new_x, new_y)
        
        if self.constraint == SelectionConstraint.ALIGN_TO_GRID:
            return self._apply_snapping(point)
        
        return point
    
    def render_selection(self, painter: QPainter, widget: QWidget):
        """Render selection overlay."""
        if not painter:
            return
        
        # Draw grid if enabled
        if self.config.show_grid and self.grid_enabled:
            self._draw_grid(painter, widget)
        
        # Draw existing selections
        for selection in self.selections:
            self._draw_selection_rect(painter, selection, finished=True)
        
        # Draw current selection
        if self.is_selecting and not self.current_selection.isEmpty():
            self._draw_selection_rect(painter, self.current_selection, finished=False)
    
    def _draw_grid(self, painter: QPainter, widget: QWidget):
        """Draw grid overlay."""
        grid_size = self.config.grid_size
        width = widget.width()
        height = widget.height()
        
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1))
        
        # Vertical lines
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        
        # Horizontal lines
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)
    
    def _draw_selection_rect(self, painter: QPainter, rect: QRect, finished: bool):
        """Draw selection rectangle."""
        # Fill
        painter.setBrush(QBrush(self.config.selection_color))
        painter.setPen(QPen(self.config.border_color, 2))
        painter.drawRect(rect)
        
        # Draw handles for finished selections
        if finished:
            self._draw_selection_handles(painter, rect)
    
    def _draw_selection_handles(self, painter: QPainter, rect: QRect):
        """Draw selection handles."""
        handle_size = self.config.handle_size
        half_size = handle_size // 2
        
        painter.setBrush(QBrush(self.config.handle_color))
        painter.setPen(QPen(self.config.border_color, 1))
        
        # Corner handles
        handles = [
            QPoint(rect.left() - half_size, rect.top() - half_size),
            QPoint(rect.right() - half_size, rect.top() - half_size),
            QPoint(rect.right() - half_size, rect.bottom() - half_size),
            QPoint(rect.left() - half_size, rect.bottom() - half_size),
            # Edge handles
            QPoint(rect.center().x() - half_size, rect.top() - half_size),
            QPoint(rect.center().x() - half_size, rect.bottom() - half_size),
            QPoint(rect.left() - half_size, rect.center().y() - half_size),
            QPoint(rect.right() - half_size, rect.center().y() - half_size),
        ]
        
        for handle in handles:
            painter.drawRect(handle.x(), handle.y(), handle_size, handle_size)
    
    def hit_test_handle(self, point: QPoint, selection_index: int) -> Optional[str]:
        """Test if point hits a selection handle."""
        if selection_index < 0 or selection_index >= len(self.selections):
            return None
        
        rect = self.selections[selection_index]
        handle_size = self.config.handle_size
        half_size = handle_size // 2
        
        # Define handle positions
        handles = {
            'top_left': QRect(rect.left() - half_size, rect.top() - half_size, handle_size, handle_size),
            'top_right': QRect(rect.right() - half_size, rect.top() - half_size, handle_size, handle_size),
            'bottom_right': QRect(rect.right() - half_size, rect.bottom() - half_size, handle_size, handle_size),
            'bottom_left': QRect(rect.left() - half_size, rect.bottom() - half_size, handle_size, handle_size),
            'top_center': QRect(rect.center().x() - half_size, rect.top() - half_size, handle_size, handle_size),
            'bottom_center': QRect(rect.center().x() - half_size, rect.bottom() - half_size, handle_size, handle_size),
            'left_center': QRect(rect.left() - half_size, rect.center().y() - half_size, handle_size, handle_size),
            'right_center': QRect(rect.right() - half_size, rect.center().y() - half_size, handle_size, handle_size),
        }
        
        for handle_name, handle_rect in handles.items():
            if handle_rect.contains(point):
                return handle_name
        
        return None
    
    def resize_selection(self, index: int, handle: str, new_point: QPoint):
        """Resize selection by dragging handle."""
        if index < 0 or index >= len(self.selections):
            return
        
        rect = self.selections[index]
        
        # Apply snapping
        if self.snap_enabled:
            new_point = self._apply_snapping(new_point)
        
        # Calculate new rectangle based on handle
        if handle == 'top_left':
            new_rect = QRect(new_point, rect.bottomRight())
        elif handle == 'top_right':
            new_rect = QRect(QPoint(rect.left(), new_point.y()), 
                           QPoint(new_point.x(), rect.bottom()))
        elif handle == 'bottom_right':
            new_rect = QRect(rect.topLeft(), new_point)
        elif handle == 'bottom_left':
            new_rect = QRect(QPoint(new_point.x(), rect.top()), 
                           QPoint(rect.right(), new_point.y()))
        elif handle == 'top_center':
            new_rect = QRect(QPoint(rect.left(), new_point.y()), rect.bottomRight())
        elif handle == 'bottom_center':
            new_rect = QRect(rect.topLeft(), QPoint(rect.right(), new_point.y()))
        elif handle == 'left_center':
            new_rect = QRect(QPoint(new_point.x(), rect.top()), rect.bottomRight())
        elif handle == 'right_center':
            new_rect = QRect(rect.topLeft(), QPoint(new_point.x(), rect.bottom()))
        else:
            return
        
        # Validate minimum size
        new_rect = new_rect.normalized()
        if (new_rect.width() >= self.config.min_selection_size and
            new_rect.height() >= self.config.min_selection_size):
            self.selections[index] = new_rect
            logger.debug(f"Selection {index} resized to {new_rect}")
    
    def move_selection(self, index: int, offset: QPoint):
        """Move selection by offset."""
        if index < 0 or index >= len(self.selections):
            return
        
        rect = self.selections[index]
        new_rect = rect.translated(offset)
        
        # Apply snapping to new position
        if self.snap_enabled:
            top_left = self._apply_snapping(new_rect.topLeft())
            new_rect = QRect(top_left, new_rect.size())
        
        self.selections[index] = new_rect
        logger.debug(f"Selection {index} moved by {offset}")
    
    def get_selection_at_point(self, point: QPoint) -> int:
        """Get selection index at point, or -1 if none."""
        for i, rect in enumerate(self.selections):
            if rect.contains(point):
                return i
        return -1
    
    def set_grid_enabled(self, enabled: bool):
        """Enable or disable grid."""
        self.grid_enabled = enabled
        logger.debug(f"Grid enabled: {enabled}")
    
    def set_snap_enabled(self, enabled: bool):
        """Enable or disable snapping."""
        self.snap_enabled = enabled
        logger.debug(f"Snapping enabled: {enabled}")
    
    def get_selection_info(self, index: int) -> Dict[str, Any]:
        """Get information about selection."""
        if index < 0 or index >= len(self.selections):
            return {}
        
        rect = self.selections[index]
        return {
            'index': index,
            'rect': rect,
            'x': rect.x(),
            'y': rect.y(),
            'width': rect.width(),
            'height': rect.height(),
            'area': rect.width() * rect.height(),
            'center': rect.center(),
            'mode': self.mode.name,
            'constraint': self.constraint.name
        }
    
    def export_selections(self) -> List[Dict[str, Any]]:
        """Export all selections as data."""
        return [self.get_selection_info(i) for i in range(len(self.selections))]
    
    def import_selections(self, data: List[Dict[str, Any]]):
        """Import selections from data."""
        self.selections.clear()
        
        for item in data:
            if 'rect' in item:
                self.selections.append(item['rect'])
            elif all(key in item for key in ['x', 'y', 'width', 'height']):
                rect = QRect(item['x'], item['y'], item['width'], item['height'])
                self.selections.append(rect)
        
        logger.info(f"Imported {len(self.selections)} selections")
=======
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
