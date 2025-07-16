"""
Icon resources for merge/split UI components.

This module provides vector-based icon generation with support for
multiple sizes, colors, and high-DPI displays.
"""

from enum import Enum
from typing import List, Optional
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon
from PyQt6.QtCore import Qt, QSize, QPoint


class IconType(Enum):
    """Enumeration of available icon types."""
    MERGE = "merge"
    SPLIT = "split"
    ADD = "add"
    REMOVE = "remove"
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    PREVIEW = "preview"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    SETTINGS = "settings"
    HELP = "help"
    CLEAR = "clear"
    SEARCH = "search"
    FILTER = "filter"


def create_merge_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create a merge operation icon."""
    if color is None:
        color = QColor("#2196f3")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Set up pen and brush
    pen = QPen(color, max(1, size // 12))
    painter.setPen(pen)
    painter.setBrush(QBrush(color))
    
    # Draw two separate elements coming together
    margin = size // 6
    width = size - 2 * margin
    height = size // 4
    
    # Top element
    painter.drawRect(margin, margin, width, height)
    
    # Bottom element
    painter.drawRect(margin, size - margin - height, width, height)
    
    # Arrow pointing to merged result
    arrow_start_y = margin + height + size // 8
    arrow_end_y = size - margin - height - size // 8
    center_x = size // 2
    
    painter.drawLine(center_x, arrow_start_y, center_x, arrow_end_y)
    
    # Arrow head
    arrow_size = size // 8
    painter.drawLine(center_x, arrow_end_y, center_x - arrow_size, arrow_end_y - arrow_size)
    painter.drawLine(center_x, arrow_end_y, center_x + arrow_size, arrow_end_y - arrow_size)
    
    painter.end()
    return pixmap


def create_split_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create a split operation icon."""
    if color is None:
        color = QColor("#ff9800")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Set up pen and brush
    pen = QPen(color, max(1, size // 12))
    painter.setPen(pen)
    painter.setBrush(QBrush(color))
    
    # Draw single element at top
    margin = size // 6
    width = size - 2 * margin
    height = size // 4
    
    painter.drawRect(margin, margin, width, height)
    
    # Draw split arrow pointing down and splitting
    center_x = size // 2
    arrow_start_y = margin + height + size // 8
    arrow_mid_y = size // 2
    
    # Main arrow shaft
    painter.drawLine(center_x, arrow_start_y, center_x, arrow_mid_y)
    
    # Split into two arrows
    left_end_x = margin + width // 4
    right_end_x = size - margin - width // 4
    arrow_end_y = size - margin - height - size // 8
    
    painter.drawLine(center_x, arrow_mid_y, left_end_x, arrow_end_y)
    painter.drawLine(center_x, arrow_mid_y, right_end_x, arrow_end_y)
    
    # Arrow heads
    arrow_size = size // 8
    painter.drawLine(left_end_x, arrow_end_y, left_end_x - arrow_size, arrow_end_y - arrow_size)
    painter.drawLine(left_end_x, arrow_end_y, left_end_x + arrow_size, arrow_end_y - arrow_size)
    
    painter.drawLine(right_end_x, arrow_end_y, right_end_x - arrow_size, arrow_end_y - arrow_size)
    painter.drawLine(right_end_x, arrow_end_y, right_end_x + arrow_size, arrow_end_y - arrow_size)
    
    # Two result elements
    result_width = width // 3
    painter.drawRect(margin, size - margin - height, result_width, height)
    painter.drawRect(size - margin - result_width, size - margin - height, result_width, height)
    
    painter.end()
    return pixmap


def create_add_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create an add/plus icon."""
    if color is None:
        color = QColor("#4caf50")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, max(2, size // 8))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    # Draw plus sign
    margin = size // 4
    center = size // 2
    
    # Horizontal line
    painter.drawLine(margin, center, size - margin, center)
    # Vertical line
    painter.drawLine(center, margin, center, size - margin)
    
    painter.end()
    return pixmap


def create_remove_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create a remove/minus icon."""
    if color is None:
        color = QColor("#f44336")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, max(2, size // 8))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    # Draw minus sign
    margin = size // 4
    center = size // 2
    
    painter.drawLine(margin, center, size - margin, center)
    
    painter.end()
    return pixmap


def create_arrow_icon(size: int = 24, direction: str = "up", color: QColor = None) -> QPixmap:
    """Create an arrow icon pointing in the specified direction."""
    if color is None:
        color = QColor("#666666")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    painter.setPen(QPen(color, max(1, size // 12)))
    painter.setBrush(QBrush(color))
    
    # Create arrow polygon
    center = size // 2
    arrow_size = size // 3
    
    if direction == "up":
        points = [
            QPoint(center, center - arrow_size),
            QPoint(center - arrow_size, center + arrow_size),
            QPoint(center + arrow_size, center + arrow_size)
        ]
    elif direction == "down":
        points = [
            QPoint(center, center + arrow_size),
            QPoint(center - arrow_size, center - arrow_size),
            QPoint(center + arrow_size, center - arrow_size)
        ]
    elif direction == "left":
        points = [
            QPoint(center - arrow_size, center),
            QPoint(center + arrow_size, center - arrow_size),
            QPoint(center + arrow_size, center + arrow_size)
        ]
    elif direction == "right":
        points = [
            QPoint(center + arrow_size, center),
            QPoint(center - arrow_size, center - arrow_size),
            QPoint(center - arrow_size, center + arrow_size)
        ]
    else:
        points = []  # Invalid direction
    
    if points:
        polygon = QPolygon(points)
        painter.drawPolygon(polygon)
    
    painter.end()
    return pixmap


def create_warning_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create a warning icon (triangle with exclamation)."""
    if color is None:
        color = QColor("#ff9800")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    painter.setPen(QPen(color, max(1, size // 16)))
    painter.setBrush(QBrush(color))
    
    # Draw triangle
    margin = size // 8
    top = QPoint(size // 2, margin)
    bottom_left = QPoint(margin, size - margin)
    bottom_right = QPoint(size - margin, size - margin)
    
    triangle = QPolygon([top, bottom_left, bottom_right])
    painter.drawPolygon(triangle)
    
    # Draw exclamation mark
    painter.setPen(QPen(QColor("white"), max(2, size // 8)))
    center_x = size // 2
    
    # Exclamation line
    line_start_y = size // 3
    line_end_y = size * 2 // 3
    painter.drawLine(center_x, line_start_y, center_x, line_end_y)
    
    # Exclamation dot
    dot_y = size * 3 // 4
    dot_size = max(2, size // 12)
    painter.drawEllipse(center_x - dot_size//2, dot_y - dot_size//2, dot_size, dot_size)
    
    painter.end()
    return pixmap


def create_success_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create a success icon (check mark)."""
    if color is None:
        color = QColor("#4caf50")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, max(2, size // 6))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    
    # Draw check mark
    margin = size // 4
    check_start_x = margin
    check_middle_x = size * 2 // 5
    check_end_x = size - margin
    
    check_start_y = size // 2
    check_middle_y = size * 3 // 4
    check_end_y = margin
    
    # First line of check
    painter.drawLine(check_start_x, check_start_y, check_middle_x, check_middle_y)
    # Second line of check
    painter.drawLine(check_middle_x, check_middle_y, check_end_x, check_end_y)
    
    painter.end()
    return pixmap


def create_error_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create an error icon (X mark)."""
    if color is None:
        color = QColor("#f44336")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, max(2, size // 6))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    # Draw X mark
    margin = size // 4
    
    # Diagonal line from top-left to bottom-right
    painter.drawLine(margin, margin, size - margin, size - margin)
    # Diagonal line from top-right to bottom-left
    painter.drawLine(size - margin, margin, margin, size - margin)
    
    painter.end()
    return pixmap


def create_info_icon(size: int = 24, color: QColor = None) -> QPixmap:
    """Create an info icon (i in circle)."""
    if color is None:
        color = QColor("#2196f3")
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    painter.setPen(QPen(color, max(1, size // 16)))
    painter.setBrush(QBrush(color))
    
    # Draw circle
    margin = size // 8
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    
    # Draw "i"
    painter.setPen(QPen(QColor("white"), max(2, size // 8)))
    center_x = size // 2
    
    # Dot of "i"
    dot_y = size // 3
    dot_size = max(2, size // 12)
    painter.drawEllipse(center_x - dot_size//2, dot_y - dot_size//2, dot_size, dot_size)
    
    # Line of "i"
    line_start_y = size // 2
    line_end_y = size * 3 // 4
    painter.drawLine(center_x, line_start_y, center_x, line_end_y)
    
    painter.end()
    return pixmap


def get_icon_sizes() -> List[int]:
    """Get list of standard icon sizes."""
    return [16, 20, 24, 32, 48, 64]


def create_icon_set(icon_type: IconType, color: QColor = None) -> QIcon:
    """Create an icon set with multiple sizes for the given type."""
    icon = QIcon()
    
    for size in get_icon_sizes():
        pixmap = get_icon_pixmap(icon_type, size, color)
        if not pixmap.isNull():
            icon.addPixmap(pixmap)
    
    return icon


def get_icon_pixmap(icon_type: IconType, size: int = 24, color: QColor = None) -> QPixmap:
    """Get a pixmap for the specified icon type and size."""
    icon_functions = {
        IconType.MERGE: create_merge_icon,
        IconType.SPLIT: create_split_icon,
        IconType.ADD: create_add_icon,
        IconType.REMOVE: create_remove_icon,
        IconType.MOVE_UP: lambda s, c: create_arrow_icon(s, "up", c),
        IconType.MOVE_DOWN: lambda s, c: create_arrow_icon(s, "down", c),
        IconType.WARNING: create_warning_icon,
        IconType.ERROR: create_error_icon,
        IconType.SUCCESS: create_success_icon,
        IconType.INFO: create_info_icon,
    }
    
    if icon_type in icon_functions:
        return icon_functions[icon_type](size, color)
    
    # Default icon for unsupported types
    return create_info_icon(size, color or QColor("#666666"))


def get_icon(icon_type: IconType, size: int = 24, color: QColor = None) -> QIcon:
    """Get an icon for the specified type, size, and color."""
    pixmap = get_icon_pixmap(icon_type, size, color)
    return QIcon(pixmap)