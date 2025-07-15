"""
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


@dataclass
class ValidationSelectionConfig:
    """Configuration for validation area selection."""
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
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections.clear()
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