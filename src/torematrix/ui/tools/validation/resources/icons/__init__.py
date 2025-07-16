"""
Icons for merge/split UI components.
"""

from enum import Enum
from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QSize


class IconType(Enum):
    """Types of icons available."""
    MERGE = "merge"
    SPLIT = "split"
    ADD = "add"
    REMOVE = "remove"
    UP_ARROW = "up_arrow"
    DOWN_ARROW = "down_arrow"
    PREVIEW = "preview"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    SUCCESS = "success"
    SETTINGS = "settings"
    FILTER = "filter"
    CLEAR = "clear"
    SAVE = "save"
    CANCEL = "cancel"


class IconRenderer:
    """Renders vector-based icons for UI components."""
    
    @staticmethod
    def create_icon(icon_type: IconType, size: QSize = QSize(16, 16), color: QColor = QColor(0, 0, 0)) -> QIcon:
        """Create a vector icon of the specified type and size."""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        brush = QBrush(color)
        painter.setBrush(brush)
        
        width = size.width()
        height = size.height()
        
        if icon_type == IconType.MERGE:
            IconRenderer._draw_merge_icon(painter, width, height)
        elif icon_type == IconType.SPLIT:
            IconRenderer._draw_split_icon(painter, width, height)
        elif icon_type == IconType.ADD:
            IconRenderer._draw_add_icon(painter, width, height)
        elif icon_type == IconType.REMOVE:
            IconRenderer._draw_remove_icon(painter, width, height)
        elif icon_type == IconType.UP_ARROW:
            IconRenderer._draw_up_arrow_icon(painter, width, height)
        elif icon_type == IconType.DOWN_ARROW:
            IconRenderer._draw_down_arrow_icon(painter, width, height)
        elif icon_type == IconType.PREVIEW:
            IconRenderer._draw_preview_icon(painter, width, height)
        elif icon_type == IconType.WARNING:
            IconRenderer._draw_warning_icon(painter, width, height)
        elif icon_type == IconType.ERROR:
            IconRenderer._draw_error_icon(painter, width, height)
        elif icon_type == IconType.INFO:
            IconRenderer._draw_info_icon(painter, width, height)
        elif icon_type == IconType.SUCCESS:
            IconRenderer._draw_success_icon(painter, width, height)
        elif icon_type == IconType.SETTINGS:
            IconRenderer._draw_settings_icon(painter, width, height)
        elif icon_type == IconType.FILTER:
            IconRenderer._draw_filter_icon(painter, width, height)
        elif icon_type == IconType.CLEAR:
            IconRenderer._draw_clear_icon(painter, width, height)
        elif icon_type == IconType.SAVE:
            IconRenderer._draw_save_icon(painter, width, height)
        elif icon_type == IconType.CANCEL:
            IconRenderer._draw_cancel_icon(painter, width, height)
        
        painter.end()
        
        icon = QIcon(pixmap)
        return icon
    
    @staticmethod
    def _draw_merge_icon(painter: QPainter, width: int, height: int):
        """Draw merge icon (multiple lines converging to one)."""
        # Draw three lines converging
        center_x = width // 2
        center_y = height // 2
        
        # Left line
        painter.drawLine(2, center_y - 4, center_x - 2, center_y)
        # Right line  
        painter.drawLine(width - 2, center_y - 4, center_x + 2, center_y)
        # Bottom line
        painter.drawLine(2, center_y + 4, center_x - 2, center_y)
        # Output line
        painter.drawLine(center_x, center_y, width - 2, center_y)
    
    @staticmethod
    def _draw_split_icon(painter: QPainter, width: int, height: int):
        """Draw split icon (one line diverging to multiple)."""
        # Draw one line splitting into three
        center_x = width // 2
        center_y = height // 2
        
        # Input line
        painter.drawLine(2, center_y, center_x, center_y)
        # Top line
        painter.drawLine(center_x, center_y, width - 2, center_y - 4)
        # Middle line
        painter.drawLine(center_x, center_y, width - 2, center_y)
        # Bottom line
        painter.drawLine(center_x, center_y, width - 2, center_y + 4)
    
    @staticmethod
    def _draw_add_icon(painter: QPainter, width: int, height: int):
        """Draw add icon (plus sign)."""
        center_x = width // 2
        center_y = height // 2
        size = min(width, height) // 3
        
        # Horizontal line
        painter.drawLine(center_x - size, center_y, center_x + size, center_y)
        # Vertical line
        painter.drawLine(center_x, center_y - size, center_x, center_y + size)
    
    @staticmethod
    def _draw_remove_icon(painter: QPainter, width: int, height: int):
        """Draw remove icon (minus sign)."""
        center_x = width // 2
        center_y = height // 2
        size = min(width, height) // 3
        
        # Horizontal line
        painter.drawLine(center_x - size, center_y, center_x + size, center_y)
    
    @staticmethod
    def _draw_up_arrow_icon(painter: QPainter, width: int, height: int):
        """Draw up arrow icon."""
        center_x = width // 2
        top = height // 4
        bottom = 3 * height // 4
        size = width // 4
        
        # Arrow body
        painter.drawLine(center_x, top, center_x, bottom)
        # Arrow head
        painter.drawLine(center_x - size, top + size, center_x, top)
        painter.drawLine(center_x + size, top + size, center_x, top)
    
    @staticmethod
    def _draw_down_arrow_icon(painter: QPainter, width: int, height: int):
        """Draw down arrow icon."""
        center_x = width // 2
        top = height // 4
        bottom = 3 * height // 4
        size = width // 4
        
        # Arrow body
        painter.drawLine(center_x, top, center_x, bottom)
        # Arrow head
        painter.drawLine(center_x - size, bottom - size, center_x, bottom)
        painter.drawLine(center_x + size, bottom - size, center_x, bottom)
    
    @staticmethod
    def _draw_preview_icon(painter: QPainter, width: int, height: int):
        """Draw preview icon (eye)."""
        center_x = width // 2
        center_y = height // 2
        
        # Eye outline (ellipse)
        painter.drawEllipse(width // 4, height // 3, width // 2, height // 3)
        # Pupil
        painter.setBrush(QBrush(painter.pen().color()))
        painter.drawEllipse(center_x - 2, center_y - 2, 4, 4)
    
    @staticmethod
    def _draw_warning_icon(painter: QPainter, width: int, height: int):
        """Draw warning icon (triangle with exclamation)."""
        # Triangle
        points = [
            (width // 2, height // 8),
            (width // 8, 7 * height // 8),
            (7 * width // 8, 7 * height // 8)
        ]
        for i in range(len(points)):
            start = points[i]
            end = points[(i + 1) % len(points)]
            painter.drawLine(start[0], start[1], end[0], end[1])
        
        # Exclamation mark
        center_x = width // 2
        painter.drawLine(center_x, height // 3, center_x, 2 * height // 3)
        painter.drawPoint(center_x, 3 * height // 4)
    
    @staticmethod
    def _draw_error_icon(painter: QPainter, width: int, height: int):
        """Draw error icon (X in circle)."""
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 2
        
        # Circle
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        # X
        offset = radius // 2
        painter.drawLine(center_x - offset, center_y - offset, center_x + offset, center_y + offset)
        painter.drawLine(center_x - offset, center_y + offset, center_x + offset, center_y - offset)
    
    @staticmethod
    def _draw_info_icon(painter: QPainter, width: int, height: int):
        """Draw info icon (i in circle)."""
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 2
        
        # Circle
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        # i
        painter.drawPoint(center_x, center_y - radius // 2)
        painter.drawLine(center_x, center_y - radius // 4, center_x, center_y + radius // 2)
    
    @staticmethod
    def _draw_success_icon(painter: QPainter, width: int, height: int):
        """Draw success icon (checkmark in circle)."""
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 2
        
        # Circle
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        # Checkmark
        painter.drawLine(center_x - radius // 2, center_y, center_x - radius // 4, center_y + radius // 3)
        painter.drawLine(center_x - radius // 4, center_y + radius // 3, center_x + radius // 2, center_y - radius // 3)
    
    @staticmethod
    def _draw_settings_icon(painter: QPainter, width: int, height: int):
        """Draw settings icon (gear)."""
        center_x = width // 2
        center_y = height // 2
        
        # Simple gear representation
        painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)
        # Teeth
        for angle in range(0, 360, 45):
            import math
            x = center_x + 6 * math.cos(math.radians(angle))
            y = center_y + 6 * math.sin(math.radians(angle))
            painter.drawLine(center_x, center_y, int(x), int(y))
    
    @staticmethod
    def _draw_filter_icon(painter: QPainter, width: int, height: int):
        """Draw filter icon (funnel)."""
        # Funnel shape
        top_width = 3 * width // 4
        bottom_width = width // 4
        
        # Top line
        painter.drawLine(width // 8, height // 4, 7 * width // 8, height // 4)
        # Left side
        painter.drawLine(width // 8, height // 4, 3 * width // 8, 3 * height // 4)
        # Right side
        painter.drawLine(7 * width // 8, height // 4, 5 * width // 8, 3 * height // 4)
        # Bottom
        painter.drawLine(3 * width // 8, 3 * height // 4, 5 * width // 8, 3 * height // 4)
    
    @staticmethod
    def _draw_clear_icon(painter: QPainter, width: int, height: int):
        """Draw clear icon (X)."""
        margin = width // 4
        painter.drawLine(margin, margin, width - margin, height - margin)
        painter.drawLine(margin, height - margin, width - margin, margin)
    
    @staticmethod
    def _draw_save_icon(painter: QPainter, width: int, height: int):
        """Draw save icon (floppy disk)."""
        # Disk outline
        painter.drawRect(width // 8, height // 8, 3 * width // 4, 3 * height // 4)
        # Label area
        painter.drawRect(width // 4, height // 8, width // 2, height // 4)
        # Notch
        painter.drawRect(5 * width // 8, height // 8, width // 8, height // 8)
    
    @staticmethod
    def _draw_cancel_icon(painter: QPainter, width: int, height: int):
        """Draw cancel icon (circle with X)."""
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 1
        
        # Circle
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        # X
        offset = radius // 2
        painter.drawLine(center_x - offset, center_y - offset, center_x + offset, center_y + offset)
        painter.drawLine(center_x - offset, center_y + offset, center_x + offset, center_y - offset)


def get_icon(icon_type: IconType, size: QSize = QSize(16, 16), color: Optional[QColor] = None) -> QIcon:
    """Get an icon of the specified type, size, and color."""
    if color is None:
        color = QColor(0, 0, 0)  # Default black
    
    return IconRenderer.create_icon(icon_type, size, color)


__all__ = ["IconType", "IconRenderer", "get_icon"]