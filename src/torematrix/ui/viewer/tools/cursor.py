"""
Cursor management system for selection tools.

This module provides cursor creation, caching, and management for different
tool states and operations with custom cursor support.
"""

import os
from typing import Dict, Optional, Tuple, Union
from enum import Enum
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QPen, QBrush, QColor, QFont

from .base import ToolState


class CursorType(Enum):
    """Predefined cursor types."""
    ARROW = "arrow"
    CROSS = "cross"
    HAND = "hand"
    CLOSED_HAND = "closed_hand"
    POINTER = "pointer"
    CROSSHAIR = "crosshair"
    RESIZE_HORIZONTAL = "resize_horizontal"
    RESIZE_VERTICAL = "resize_vertical"
    RESIZE_DIAGONAL_1 = "resize_diagonal_1"
    RESIZE_DIAGONAL_2 = "resize_diagonal_2"
    MOVE = "move"
    CUSTOM = "custom"


class CursorTheme(Enum):
    """Cursor visual themes."""
    SYSTEM = "system"
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"
    COLORFUL = "colorful"


class CursorManager:
    """
    Advanced cursor management for selection tools.
    
    Provides cursor creation, caching, theming, and dynamic cursor updates
    for different tool states and visual feedback.
    """
    
    def __init__(self, theme: CursorTheme = CursorTheme.SYSTEM):
        self._cursors: Dict[str, QCursor] = {}
        self._theme = theme
        self._cursor_size = 16
        self._current_cursor: Optional[QCursor] = None
        
        # Create default cursors
        self._create_system_cursors()
        self._create_custom_cursors()
    
    def _create_system_cursors(self) -> None:
        """Create system default cursors."""
        system_cursors = {
            CursorType.ARROW: Qt.CursorShape.ArrowCursor,
            CursorType.CROSS: Qt.CursorShape.CrossCursor,
            CursorType.HAND: Qt.CursorShape.OpenHandCursor,
            CursorType.CLOSED_HAND: Qt.CursorShape.ClosedHandCursor,
            CursorType.POINTER: Qt.CursorShape.PointingHandCursor,
            CursorType.CROSSHAIR: Qt.CursorShape.CrossCursor,
            CursorType.RESIZE_HORIZONTAL: Qt.CursorShape.SizeHorCursor,
            CursorType.RESIZE_VERTICAL: Qt.CursorShape.SizeVerCursor,
            CursorType.RESIZE_DIAGONAL_1: Qt.CursorShape.SizeFDiagCursor,
            CursorType.RESIZE_DIAGONAL_2: Qt.CursorShape.SizeBDiagCursor,
            CursorType.MOVE: Qt.CursorShape.SizeAllCursor
        }
        
        for cursor_type, qt_cursor in system_cursors.items():
            self._cursors[cursor_type.value] = QCursor(qt_cursor)
    
    def _create_custom_cursors(self) -> None:
        """Create custom themed cursors."""
        if self._theme == CursorTheme.SYSTEM:
            return
        
        # Create custom cursors based on theme
        self._create_selection_cursor()
        self._create_precision_cursor()
        self._create_lasso_cursor()
        self._create_rectangle_cursor()
        self._create_element_aware_cursor()
        self._create_multi_select_cursor()
    
    def _create_selection_cursor(self) -> None:
        """Create selection tool cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("primary")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw crosshair
        center = self._cursor_size // 2
        painter.drawLine(center, 0, center, self._cursor_size)
        painter.drawLine(0, center, self._cursor_size, center)
        
        # Draw center dot
        painter.setBrush(QBrush(color))
        painter.drawEllipse(center - 2, center - 2, 4, 4)
        
        painter.end()
        
        self._cursors["selection"] = QCursor(pixmap, center, center)
    
    def _create_precision_cursor(self) -> None:
        """Create precision selection cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("accent")
        pen = QPen(color, 1)
        painter.setPen(pen)
        
        center = self._cursor_size // 2
        
        # Draw fine crosshair
        painter.drawLine(center - 6, center, center - 2, center)
        painter.drawLine(center + 2, center, center + 6, center)
        painter.drawLine(center, center - 6, center, center - 2)
        painter.drawLine(center, center + 2, center, center + 6)
        
        # Draw circle indicator
        painter.drawEllipse(center - 3, center - 3, 6, 6)
        
        painter.end()
        
        self._cursors["precision"] = QCursor(pixmap, center, center)
    
    def _create_lasso_cursor(self) -> None:
        """Create lasso tool cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("lasso")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw lasso loop
        center = self._cursor_size // 2
        painter.drawEllipse(center - 4, center - 4, 8, 8)
        
        # Draw line to cursor point
        painter.drawLine(center, center + 4, center + 2, self._cursor_size - 2)
        
        painter.end()
        
        self._cursors["lasso"] = QCursor(pixmap, center, center)
    
    def _create_rectangle_cursor(self) -> None:
        """Create rectangle selection cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("rectangle")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw rectangle outline
        margin = 3
        painter.drawRect(margin, margin, self._cursor_size - 2 * margin, self._cursor_size - 2 * margin)
        
        # Draw corner indicator
        painter.setBrush(QBrush(color))
        painter.drawEllipse(margin - 1, margin - 1, 3, 3)
        
        painter.end()
        
        self._cursors["rectangle"] = QCursor(pixmap, margin, margin)
    
    def _create_element_aware_cursor(self) -> None:
        """Create element-aware selection cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("element")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        center = self._cursor_size // 2
        
        # Draw target reticle
        painter.drawEllipse(center - 5, center - 5, 10, 10)
        painter.drawLine(center - 8, center, center - 6, center)
        painter.drawLine(center + 6, center, center + 8, center)
        painter.drawLine(center, center - 8, center, center - 6)
        painter.drawLine(center, center + 6, center, center + 8)
        
        # Draw center dot
        painter.setBrush(QBrush(color))
        painter.drawEllipse(center - 1, center - 1, 2, 2)
        
        painter.end()
        
        self._cursors["element_aware"] = QCursor(pixmap, center, center)
    
    def _create_multi_select_cursor(self) -> None:
        """Create multi-select cursor."""
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("multi")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw arrow
        center = self._cursor_size // 2
        painter.drawLine(2, 2, center, center - 2)
        painter.drawLine(2, 2, center - 2, center)
        
        # Draw plus sign
        plus_center = self._cursor_size - 4
        painter.drawLine(plus_center - 2, plus_center, plus_center + 2, plus_center)
        painter.drawLine(plus_center, plus_center - 2, plus_center, plus_center + 2)
        
        painter.end()
        
        self._cursors["multi_select"] = QCursor(pixmap, 2, 2)
    
    def _get_theme_color(self, role: str) -> QColor:
        """Get color for theme and role."""
        color_schemes = {
            CursorTheme.DARK: {
                "primary": QColor(255, 255, 255),
                "accent": QColor(0, 170, 255),
                "lasso": QColor(255, 170, 0),
                "rectangle": QColor(0, 255, 0),
                "element": QColor(255, 0, 170),
                "multi": QColor(170, 255, 0)
            },
            CursorTheme.LIGHT: {
                "primary": QColor(0, 0, 0),
                "accent": QColor(0, 100, 200),
                "lasso": QColor(200, 100, 0),
                "rectangle": QColor(0, 150, 0),
                "element": QColor(200, 0, 100),
                "multi": QColor(100, 150, 0)
            },
            CursorTheme.HIGH_CONTRAST: {
                "primary": QColor(255, 255, 0),
                "accent": QColor(255, 0, 255),
                "lasso": QColor(0, 255, 255),
                "rectangle": QColor(255, 255, 255),
                "element": QColor(255, 128, 0),
                "multi": QColor(128, 255, 128)
            },
            CursorTheme.COLORFUL: {
                "primary": QColor(50, 150, 250),
                "accent": QColor(250, 50, 150),
                "lasso": QColor(250, 150, 50),
                "rectangle": QColor(50, 250, 150),
                "element": QColor(150, 50, 250),
                "multi": QColor(150, 250, 50)
            }
        }
        
        return color_schemes.get(self._theme, color_schemes[CursorTheme.DARK]).get(role, QColor(255, 255, 255))
    
    def get_cursor_for_state(self, state: ToolState) -> QCursor:
        """Get appropriate cursor for tool state."""
        cursor_mapping = {
            ToolState.INACTIVE: CursorType.ARROW,
            ToolState.ACTIVE: CursorType.CROSS,
            ToolState.HOVER: CursorType.POINTER,
            ToolState.SELECTING: CursorType.CLOSED_HAND,
            ToolState.SELECTED: CursorType.HAND,
            ToolState.DRAG: CursorType.CLOSED_HAND,
            ToolState.RESIZE: CursorType.RESIZE_DIAGONAL_1,
            ToolState.MOVE: CursorType.MOVE
        }
        
        cursor_type = cursor_mapping.get(state, CursorType.ARROW)
        return self.get_cursor(cursor_type.value)
    
    def get_cursor(self, cursor_name: str) -> QCursor:
        """Get cursor by name."""
        return self._cursors.get(cursor_name, self._cursors[CursorType.ARROW.value])
    
    def set_cursor(self, cursor_name: str, cursor: QCursor) -> None:
        """Set custom cursor."""
        self._cursors[cursor_name] = cursor
    
    def create_text_cursor(self, text: str, color: QColor = QColor(255, 255, 255)) -> QCursor:
        """Create cursor with text label."""
        font = QFont("Arial", 8)
        
        # Calculate text size
        pixmap = QPixmap(100, 30)  # Temporary pixmap for measurement
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect(text)
        painter.end()
        
        # Create actual cursor pixmap
        cursor_pixmap = QPixmap(text_rect.width() + 4, text_rect.height() + 4)
        cursor_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(font)
        
        # Draw text background
        painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, cursor_pixmap.width(), cursor_pixmap.height(), 2, 2)
        
        # Draw text
        painter.setPen(QPen(color))
        painter.drawText(2, text_rect.height(), text)
        
        painter.end()
        
        return QCursor(cursor_pixmap)
    
    def create_progress_cursor(self, progress: float, size: int = 16) -> QCursor:
        """Create cursor showing progress (0.0 to 1.0)."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = size // 2
        radius = center - 2
        
        # Draw background circle
        painter.setPen(QPen(QColor(128, 128, 128), 2))
        painter.drawEllipse(center - radius, center - radius, 2 * radius, 2 * radius)
        
        # Draw progress arc
        if progress > 0:
            painter.setPen(QPen(self._get_theme_color("accent"), 2))
            start_angle = -90 * 16  # Start at top (in sixteenths of a degree)
            span_angle = int(progress * 360 * 16)  # Progress arc
            painter.drawArc(center - radius, center - radius, 2 * radius, 2 * radius, start_angle, span_angle)
        
        painter.end()
        
        return QCursor(pixmap, center, center)
    
    def create_tool_cursor(self, tool_name: str, hotspot: Tuple[int, int] = (8, 8)) -> QCursor:
        """Create cursor for specific tool."""
        if tool_name in self._cursors:
            return self._cursors[tool_name]
        
        # Create default tool cursor
        pixmap = QPixmap(self._cursor_size, self._cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self._get_theme_color("primary")
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw tool-specific icon
        if "pointer" in tool_name.lower():
            # Arrow cursor
            painter.drawLine(2, 2, 10, 10)
            painter.drawLine(2, 2, 6, 10)
            painter.drawLine(2, 2, 10, 6)
        elif "rectangle" in tool_name.lower():
            # Rectangle cursor
            painter.drawRect(3, 3, 10, 10)
        elif "lasso" in tool_name.lower():
            # Lasso cursor
            painter.drawEllipse(4, 4, 8, 8)
            painter.drawLine(8, 12, 10, 14)
        else:
            # Default crosshair
            painter.drawLine(8, 0, 8, 16)
            painter.drawLine(0, 8, 16, 8)
        
        painter.end()
        
        cursor = QCursor(pixmap, hotspot[0], hotspot[1])
        self._cursors[tool_name] = cursor
        return cursor
    
    def set_theme(self, theme: CursorTheme) -> None:
        """Change cursor theme."""
        if self._theme != theme:
            self._theme = theme
            # Recreate custom cursors with new theme
            self._create_custom_cursors()
    
    def get_theme(self) -> CursorTheme:
        """Get current theme."""
        return self._theme
    
    def set_cursor_size(self, size: int) -> None:
        """Set cursor size and recreate cursors."""
        if size != self._cursor_size and 8 <= size <= 64:
            self._cursor_size = size
            self._create_custom_cursors()
    
    def get_cursor_size(self) -> int:
        """Get current cursor size."""
        return self._cursor_size
    
    def get_available_cursors(self) -> list[str]:
        """Get list of available cursor names."""
        return list(self._cursors.keys())
    
    def clear_cache(self) -> None:
        """Clear cursor cache."""
        self._cursors.clear()
        self._create_system_cursors()
        self._create_custom_cursors()
    
    def export_cursor(self, cursor_name: str, file_path: str) -> bool:
        """Export cursor to image file."""
        if cursor_name not in self._cursors:
            return False
        
        try:
            cursor = self._cursors[cursor_name]
            pixmap = cursor.pixmap()
            if not pixmap.isNull():
                return pixmap.save(file_path)
        except Exception:
            pass
        
        return False
    
    def import_cursor(self, cursor_name: str, file_path: str, hotspot: Tuple[int, int] = (8, 8)) -> bool:
        """Import cursor from image file."""
        try:
            if os.path.exists(file_path):
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self._cursors[cursor_name] = QCursor(pixmap, hotspot[0], hotspot[1])
                    return True
        except Exception:
            pass
        
        return False


class CursorStack:
    """Stack-based cursor management for temporary cursor changes."""
    
    def __init__(self, manager: CursorManager):
        self._manager = manager
        self._stack: list[str] = []
        self._current_cursor: Optional[str] = None
    
    def push_cursor(self, cursor_name: str) -> None:
        """Push cursor onto stack."""
        if self._current_cursor:
            self._stack.append(self._current_cursor)
        self._current_cursor = cursor_name
    
    def pop_cursor(self) -> Optional[str]:
        """Pop cursor from stack."""
        if self._stack:
            self._current_cursor = self._stack.pop()
            return self._current_cursor
        else:
            self._current_cursor = None
            return None
    
    def peek_cursor(self) -> Optional[str]:
        """Peek at current cursor without popping."""
        return self._current_cursor
    
    def clear_stack(self) -> None:
        """Clear cursor stack."""
        self._stack.clear()
        self._current_cursor = None
    
    def get_current_qcursor(self) -> QCursor:
        """Get current QCursor object."""
        if self._current_cursor:
            return self._manager.get_cursor(self._current_cursor)
        return self._manager.get_cursor(CursorType.ARROW.value)
    
    def get_stack_depth(self) -> int:
        """Get stack depth."""
        return len(self._stack)


# Global cursor manager instance
_global_cursor_manager: Optional[CursorManager] = None


def get_global_cursor_manager() -> CursorManager:
    """Get global cursor manager instance."""
    global _global_cursor_manager
    if _global_cursor_manager is None:
        _global_cursor_manager = CursorManager()
    return _global_cursor_manager


def set_global_cursor_theme(theme: CursorTheme) -> None:
    """Set global cursor theme."""
    manager = get_global_cursor_manager()
    manager.set_theme(theme)