"""
Icon management for merge/split operation dialogs.

This module provides icon generation and management for UI components,
including vector-based icons that scale properly for high-DPI displays.
"""

from enum import Enum
from typing import Optional, Tuple
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize


class IconType(Enum):
    """Available icon types for merge/split operations."""
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


def create_merge_icon(size: int = 24, color: QColor = QColor("#2196f3")) -> QPixmap:
    """Create a merge operation icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw two separate elements merging into one
    pen = QPen(color, 2)
    painter.setPen(pen)
    
    # Left element
    rect1 = QRectF(2, 4, size * 0.25, size * 0.3)
    painter.drawRect(rect1)
    
    # Right element  
    rect2 = QRectF(size * 0.4, 4, size * 0.25, size * 0.3)
    painter.drawRect(rect2)
    
    # Arrow pointing down and converging
    arrow_start_y = size * 0.4
    arrow_mid_y = size * 0.6
    arrow_end_y = size * 0.8
    
    # Left arrow
    painter.drawLine(int(rect1.center().x()), int(arrow_start_y), 
                    int(size * 0.5), int(arrow_mid_y))
    
    # Right arrow
    painter.drawLine(int(rect2.center().x()), int(arrow_start_y),
                    int(size * 0.5), int(arrow_mid_y))
    
    # Merged result
    result_rect = QRectF(size * 0.25, arrow_end_y, size * 0.5, size * 0.15)
    painter.drawRect(result_rect)
    
    # Connecting line
    painter.drawLine(int(size * 0.5), int(arrow_mid_y),
                    int(size * 0.5), int(arrow_end_y))
    
    painter.end()
    return pixmap


def create_split_icon(size: int = 24, color: QColor = QColor("#ff9800")) -> QPixmap:
    """Create a split operation icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, 2)
    painter.setPen(pen)
    
    # Original element at top
    orig_rect = QRectF(size * 0.25, 2, size * 0.5, size * 0.2)
    painter.drawRect(orig_rect)
    
    # Split line from center
    center_x = size * 0.5
    split_start_y = size * 0.3
    split_mid_y = size * 0.5
    
    painter.drawLine(int(center_x), int(split_start_y), 
                    int(center_x), int(split_mid_y))
    
    # Diverging arrows
    left_end_x = size * 0.2
    right_end_x = size * 0.8
    split_end_y = size * 0.7
    
    painter.drawLine(int(center_x), int(split_mid_y),
                    int(left_end_x), int(split_end_y))
    painter.drawLine(int(center_x), int(split_mid_y),
                    int(right_end_x), int(split_end_y))
    
    # Result elements
    left_rect = QRectF(left_end_x - size * 0.1, split_end_y + 4, 
                      size * 0.2, size * 0.15)
    right_rect = QRectF(right_end_x - size * 0.1, split_end_y + 4,
                       size * 0.2, size * 0.15)
    
    painter.drawRect(left_rect)
    painter.drawRect(right_rect)
    
    painter.end()
    return pixmap


def create_add_icon(size: int = 24, color: QColor = QColor("#4caf50")) -> QPixmap:
    """Create an add/plus icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, 3)
    painter.setPen(pen)
    
    center = size // 2
    line_length = size * 0.6
    
    # Horizontal line
    painter.drawLine(int(center - line_length/2), center,
                    int(center + line_length/2), center)
    
    # Vertical line
    painter.drawLine(center, int(center - line_length/2),
                    center, int(center + line_length/2))
    
    painter.end()
    return pixmap


def create_remove_icon(size: int = 24, color: QColor = QColor("#f44336")) -> QPixmap:
    """Create a remove/minus icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, 3)
    painter.setPen(pen)
    
    center = size // 2
    line_length = size * 0.6
    
    # Horizontal line
    painter.drawLine(int(center - line_length/2), center,
                    int(center + line_length/2), center)
    
    painter.end()
    return pixmap


def create_arrow_icon(size: int = 24, direction: str = "up", 
                     color: QColor = QColor("#666666")) -> QPixmap:
    """Create an arrow icon in the specified direction."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    brush = QBrush(color)
    painter.setBrush(brush)
    painter.setPen(Qt.PenStyle.NoPen)
    
    center = size // 2
    arrow_size = size * 0.4
    
    if direction == "up":
        points = [
            QPointF(center, center - arrow_size/2),
            QPointF(center - arrow_size/2, center + arrow_size/2),
            QPointF(center + arrow_size/2, center + arrow_size/2)
        ]
    elif direction == "down":
        points = [
            QPointF(center, center + arrow_size/2),
            QPointF(center - arrow_size/2, center - arrow_size/2),
            QPointF(center + arrow_size/2, center - arrow_size/2)
        ]
    elif direction == "left":
        points = [
            QPointF(center - arrow_size/2, center),
            QPointF(center + arrow_size/2, center - arrow_size/2),
            QPointF(center + arrow_size/2, center + arrow_size/2)
        ]
    elif direction == "right":
        points = [
            QPointF(center + arrow_size/2, center),
            QPointF(center - arrow_size/2, center - arrow_size/2),
            QPointF(center - arrow_size/2, center + arrow_size/2)
        ]
    else:
        points = []  # Invalid direction
    
    if points:
        polygon = QPolygonF(points)
        painter.drawPolygon(polygon)
    
    painter.end()
    return pixmap


def create_warning_icon(size: int = 24, color: QColor = QColor("#ff9800")) -> QPixmap:
    """Create a warning icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Triangle background
    brush = QBrush(color)
    painter.setBrush(brush)
    painter.setPen(Qt.PenStyle.NoPen)
    
    center = size // 2
    triangle_size = size * 0.8
    
    points = [
        QPointF(center, size * 0.1),
        QPointF(size * 0.1, size * 0.9),
        QPointF(size * 0.9, size * 0.9)
    ]
    
    triangle = QPolygonF(points)
    painter.drawPolygon(triangle)
    
    # Exclamation mark
    painter.setBrush(QBrush(QColor("white")))
    
    # Line
    line_rect = QRectF(center - 1.5, size * 0.3, 3, size * 0.35)
    painter.drawRect(line_rect)
    
    # Dot
    dot_rect = QRectF(center - 2, size * 0.75, 4, 4)
    painter.drawEllipse(dot_rect)
    
    painter.end()
    return pixmap


def create_success_icon(size: int = 24, color: QColor = QColor("#4caf50")) -> QPixmap:
    """Create a success/checkmark icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, 3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    # Checkmark
    check_size = size * 0.6
    start_x = size * 0.2
    start_y = size * 0.5
    mid_x = size * 0.4
    mid_y = size * 0.7
    end_x = size * 0.8
    end_y = size * 0.3
    
    painter.drawLine(int(start_x), int(start_y), int(mid_x), int(mid_y))
    painter.drawLine(int(mid_x), int(mid_y), int(end_x), int(end_y))
    
    painter.end()
    return pixmap


def create_error_icon(size: int = 24, color: QColor = QColor("#f44336")) -> QPixmap:
    """Create an error/X icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(color, 3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    
    # X mark
    margin = size * 0.2
    painter.drawLine(int(margin), int(margin), 
                    int(size - margin), int(size - margin))
    painter.drawLine(int(size - margin), int(margin),
                    int(margin), int(size - margin))
    
    painter.end()
    return pixmap


def create_info_icon(size: int = 24, color: QColor = QColor("#2196f3")) -> QPixmap:
    """Create an info icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Circle background
    brush = QBrush(color)
    painter.setBrush(brush)
    painter.setPen(Qt.PenStyle.NoPen)
    
    margin = size * 0.1
    circle_rect = QRectF(margin, margin, size - 2*margin, size - 2*margin)
    painter.drawEllipse(circle_rect)
    
    # "i" letter
    painter.setBrush(QBrush(QColor("white")))
    
    center = size // 2
    
    # Dot
    dot_rect = QRectF(center - 2, size * 0.25, 4, 4)
    painter.drawEllipse(dot_rect)
    
    # Line
    line_rect = QRectF(center - 1.5, size * 0.4, 3, size * 0.35)
    painter.drawRect(line_rect)
    
    painter.end()
    return pixmap


def get_icon(icon_type: IconType, size: int = 24, color: Optional[QColor] = None) -> QIcon:
    """Get an icon of the specified type and size."""
    if color is None:
        # Default colors for different icon types
        color_map = {
            IconType.MERGE: QColor("#2196f3"),
            IconType.SPLIT: QColor("#ff9800"),
            IconType.ADD: QColor("#4caf50"),
            IconType.REMOVE: QColor("#f44336"),
            IconType.MOVE_UP: QColor("#666666"),
            IconType.MOVE_DOWN: QColor("#666666"),
            IconType.PREVIEW: QColor("#9c27b0"),
            IconType.WARNING: QColor("#ff9800"),
            IconType.ERROR: QColor("#f44336"),
            IconType.SUCCESS: QColor("#4caf50"),
            IconType.INFO: QColor("#2196f3"),
            IconType.SETTINGS: QColor("#666666"),
            IconType.HELP: QColor("#2196f3"),
            IconType.CLEAR: QColor("#f44336"),
            IconType.SEARCH: QColor("#666666"),
            IconType.FILTER: QColor("#666666")
        }
        color = color_map.get(icon_type, QColor("#666666"))
    
    # Create pixmap based on icon type
    if icon_type == IconType.MERGE:
        pixmap = create_merge_icon(size, color)
    elif icon_type == IconType.SPLIT:
        pixmap = create_split_icon(size, color)
    elif icon_type == IconType.ADD:
        pixmap = create_add_icon(size, color)
    elif icon_type == IconType.REMOVE:
        pixmap = create_remove_icon(size, color)
    elif icon_type == IconType.MOVE_UP:
        pixmap = create_arrow_icon(size, "up", color)
    elif icon_type == IconType.MOVE_DOWN:
        pixmap = create_arrow_icon(size, "down", color)
    elif icon_type == IconType.WARNING:
        pixmap = create_warning_icon(size, color)
    elif icon_type == IconType.ERROR:
        pixmap = create_error_icon(size, color)
    elif icon_type == IconType.SUCCESS:
        pixmap = create_success_icon(size, color)
    elif icon_type == IconType.INFO:
        pixmap = create_info_icon(size, color)
    else:
        # Default icon for unimplemented types
        pixmap = QPixmap(size, size)
        pixmap.fill(color)
    
    return QIcon(pixmap)


def get_icon_sizes() -> list:
    """Get available icon sizes."""
    return [16, 20, 24, 32, 48, 64]


def create_icon_set(icon_type: IconType, color: Optional[QColor] = None) -> QIcon:
    """Create an icon with multiple sizes for better scaling."""
    icon = QIcon()
    
    for size in get_icon_sizes():
        pixmap = get_icon(icon_type, size, color).pixmap(QSize(size, size))
        icon.addPixmap(pixmap)
    
    return icon