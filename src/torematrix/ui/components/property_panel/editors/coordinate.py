"""Coordinate and geometric property editors for spatial data"""

from typing import List, Tuple, Any, Optional, Dict
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QFrame, QSlider, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRect, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

from .base import BasePropertyEditor, EditorConfiguration, PropertyEditorState
from .validation import ValidationMixin


@dataclass
class Point2D:
    """2D point coordinate"""
    x: float
    y: float
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def to_qpoint(self) -> QPoint:
        return QPoint(int(self.x), int(self.y))
    
    def to_qpointf(self) -> QPointF:
        return QPointF(self.x, self.y)


@dataclass
class Rectangle2D:
    """2D rectangle coordinate"""
    x: float
    y: float
    width: float
    height: float
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)
    
    def to_qrect(self) -> QRect:
        return QRect(int(self.x), int(self.y), int(self.width), int(self.height))
    
    def to_qrectf(self) -> QRectF:
        return QRectF(self.x, self.y, self.width, self.height)


class Point2DEditor(BasePropertyEditor, ValidationMixin):
    """Editor for 2D point coordinates (x, y)"""
    
    point_changed = pyqtSignal(object)  # Point2D object
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._point = Point2D(0.0, 0.0)
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup point editor UI"""
        layout = QVBoxLayout(self)
        
        # Create group box
        group_box = QGroupBox("Point Coordinates")
        group_layout = QGridLayout(group_box)
        
        # X coordinate
        group_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spinbox = self._create_coordinate_spinbox()
        self.x_spinbox.valueChanged.connect(self._on_x_changed)
        group_layout.addWidget(self.x_spinbox, 0, 1)
        
        # Y coordinate
        group_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_spinbox = self._create_coordinate_spinbox()
        self.y_spinbox.valueChanged.connect(self._on_y_changed)
        group_layout.addWidget(self.y_spinbox, 1, 1)
        
        # Reset button
        reset_btn = QPushButton("Reset to (0, 0)")
        reset_btn.clicked.connect(self._reset_coordinates)
        group_layout.addWidget(reset_btn, 2, 0, 1, 2)
        
        layout.addWidget(group_box)
        
        # Add visual preview if enabled
        if self.config.custom_attributes.get('show_preview', False):
            self._add_visual_preview(layout)
    
    def _create_coordinate_spinbox(self) -> QDoubleSpinBox:
        """Create spinbox for coordinate input"""
        spinbox = QDoubleSpinBox()
        
        # Configure range from config
        min_val = self.config.custom_attributes.get('min_value', -10000.0)
        max_val = self.config.custom_attributes.get('max_value', 10000.0)
        decimals = self.config.custom_attributes.get('decimals', 2)
        step = self.config.custom_attributes.get('step', 1.0)
        
        spinbox.setRange(min_val, max_val)
        spinbox.setDecimals(decimals)
        spinbox.setSingleStep(step)
        
        return spinbox
    
    def _add_visual_preview(self, layout: QVBoxLayout) -> None:
        """Add visual coordinate preview"""
        self.preview_widget = CoordinatePreviewWidget()
        self.preview_widget.setFixedSize(200, 150)
        layout.addWidget(self.preview_widget)
    
    def get_value(self) -> Point2D:
        """Get current point value"""
        return self._point
    
    def set_value(self, value: Any) -> None:
        """Set point value"""
        if isinstance(value, Point2D):
            self._point = value
        elif isinstance(value, (tuple, list)) and len(value) >= 2:
            self._point = Point2D(float(value[0]), float(value[1]))
        elif isinstance(value, dict) and 'x' in value and 'y' in value:
            self._point = Point2D(float(value['x']), float(value['y']))
        else:
            self._point = Point2D(0.0, 0.0)
        
        # Update UI
        self.x_spinbox.setValue(self._point.x)
        self.y_spinbox.setValue(self._point.y)
        
        # Update preview
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_point(self._point)
    
    def _on_x_changed(self, value: float) -> None:
        """Handle X coordinate change"""
        old_point = self._point
        self._point = Point2D(value, self._point.y)
        
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_point(self._point)
        
        self.point_changed.emit(self._point)
        self.value_changed.emit(self._point)
    
    def _on_y_changed(self, value: float) -> None:
        """Handle Y coordinate change"""
        old_point = self._point
        self._point = Point2D(self._point.x, value)
        
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_point(self._point)
        
        self.point_changed.emit(self._point)
        self.value_changed.emit(self._point)
    
    def _reset_coordinates(self) -> None:
        """Reset coordinates to origin"""
        self.set_value(Point2D(0.0, 0.0))
        self.value_committed.emit(self._point)


class Rectangle2DEditor(BasePropertyEditor, ValidationMixin):
    """Editor for 2D rectangle coordinates (x, y, width, height)"""
    
    rectangle_changed = pyqtSignal(object)  # Rectangle2D object
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._rectangle = Rectangle2D(0.0, 0.0, 100.0, 100.0)
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup rectangle editor UI"""
        layout = QVBoxLayout(self)
        
        # Position group
        pos_group = QGroupBox("Position")
        pos_layout = QGridLayout(pos_group)
        
        pos_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spinbox = self._create_coordinate_spinbox()
        self.x_spinbox.valueChanged.connect(self._on_x_changed)
        pos_layout.addWidget(self.x_spinbox, 0, 1)
        
        pos_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_spinbox = self._create_coordinate_spinbox()
        self.y_spinbox.valueChanged.connect(self._on_y_changed)
        pos_layout.addWidget(self.y_spinbox, 1, 1)
        
        layout.addWidget(pos_group)
        
        # Size group
        size_group = QGroupBox("Size")
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_spinbox = self._create_size_spinbox()
        self.width_spinbox.valueChanged.connect(self._on_width_changed)
        size_layout.addWidget(self.width_spinbox, 0, 1)
        
        size_layout.addWidget(QLabel("Height:"), 1, 0)
        self.height_spinbox = self._create_size_spinbox()
        self.height_spinbox.valueChanged.connect(self._on_height_changed)
        size_layout.addWidget(self.height_spinbox, 1, 1)
        
        # Aspect ratio lock
        self.aspect_lock_cb = QCheckBox("Lock Aspect Ratio")
        self.aspect_lock_cb.toggled.connect(self._on_aspect_lock_toggled)
        size_layout.addWidget(self.aspect_lock_cb, 2, 0, 1, 2)
        
        layout.addWidget(size_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_rectangle)
        
        center_btn = QPushButton("Center at Origin")
        center_btn.clicked.connect(self._center_at_origin)
        
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(center_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Add visual preview if enabled
        if self.config.custom_attributes.get('show_preview', False):
            self._add_visual_preview(layout)
    
    def _create_coordinate_spinbox(self) -> QDoubleSpinBox:
        """Create spinbox for coordinate input"""
        spinbox = QDoubleSpinBox()
        min_val = self.config.custom_attributes.get('min_value', -10000.0)
        max_val = self.config.custom_attributes.get('max_value', 10000.0)
        spinbox.setRange(min_val, max_val)
        spinbox.setDecimals(2)
        spinbox.setSingleStep(1.0)
        return spinbox
    
    def _create_size_spinbox(self) -> QDoubleSpinBox:
        """Create spinbox for size input"""
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.1, 10000.0)
        spinbox.setDecimals(2)
        spinbox.setSingleStep(1.0)
        return spinbox
    
    def _add_visual_preview(self, layout: QVBoxLayout) -> None:
        """Add visual rectangle preview"""
        self.preview_widget = RectanglePreviewWidget()
        self.preview_widget.setFixedSize(200, 150)
        layout.addWidget(self.preview_widget)
    
    def get_value(self) -> Rectangle2D:
        """Get current rectangle value"""
        return self._rectangle
    
    def set_value(self, value: Any) -> None:
        """Set rectangle value"""
        if isinstance(value, Rectangle2D):
            self._rectangle = value
        elif isinstance(value, (tuple, list)) and len(value) >= 4:
            self._rectangle = Rectangle2D(
                float(value[0]), float(value[1]), 
                float(value[2]), float(value[3])
            )
        elif isinstance(value, dict):
            self._rectangle = Rectangle2D(
                float(value.get('x', 0)),
                float(value.get('y', 0)),
                float(value.get('width', 100)),
                float(value.get('height', 100))
            )
        else:
            self._rectangle = Rectangle2D(0.0, 0.0, 100.0, 100.0)
        
        # Update UI
        self.x_spinbox.setValue(self._rectangle.x)
        self.y_spinbox.setValue(self._rectangle.y)
        self.width_spinbox.setValue(self._rectangle.width)
        self.height_spinbox.setValue(self._rectangle.height)
        
        # Update preview
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_rectangle(self._rectangle)
    
    def _on_x_changed(self, value: float) -> None:
        """Handle X coordinate change"""
        self._rectangle = Rectangle2D(value, self._rectangle.y, 
                                    self._rectangle.width, self._rectangle.height)
        self._emit_change()
    
    def _on_y_changed(self, value: float) -> None:
        """Handle Y coordinate change"""
        self._rectangle = Rectangle2D(self._rectangle.x, value,
                                    self._rectangle.width, self._rectangle.height)
        self._emit_change()
    
    def _on_width_changed(self, value: float) -> None:
        """Handle width change"""
        if self.aspect_lock_cb.isChecked() and self._rectangle.width > 0:
            # Maintain aspect ratio
            aspect_ratio = self._rectangle.height / self._rectangle.width
            new_height = value * aspect_ratio
            self.height_spinbox.setValue(new_height)
            self._rectangle = Rectangle2D(self._rectangle.x, self._rectangle.y,
                                        value, new_height)
        else:
            self._rectangle = Rectangle2D(self._rectangle.x, self._rectangle.y,
                                        value, self._rectangle.height)
        self._emit_change()
    
    def _on_height_changed(self, value: float) -> None:
        """Handle height change"""
        if self.aspect_lock_cb.isChecked() and self._rectangle.height > 0:
            # Maintain aspect ratio
            aspect_ratio = self._rectangle.width / self._rectangle.height
            new_width = value * aspect_ratio
            self.width_spinbox.setValue(new_width)
            self._rectangle = Rectangle2D(self._rectangle.x, self._rectangle.y,
                                        new_width, value)
        else:
            self._rectangle = Rectangle2D(self._rectangle.x, self._rectangle.y,
                                        self._rectangle.width, value)
        self._emit_change()
    
    def _on_aspect_lock_toggled(self, checked: bool) -> None:
        """Handle aspect ratio lock toggle"""
        # Just visual feedback - actual constraint applied in size change handlers
        pass
    
    def _emit_change(self) -> None:
        """Emit rectangle change signals"""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_rectangle(self._rectangle)
        
        self.rectangle_changed.emit(self._rectangle)
        self.value_changed.emit(self._rectangle)
    
    def _reset_rectangle(self) -> None:
        """Reset rectangle to default values"""
        self.set_value(Rectangle2D(0.0, 0.0, 100.0, 100.0))
        self.value_committed.emit(self._rectangle)
    
    def _center_at_origin(self) -> None:
        """Center rectangle at origin"""
        centered = Rectangle2D(
            -self._rectangle.width / 2,
            -self._rectangle.height / 2,
            self._rectangle.width,
            self._rectangle.height
        )
        self.set_value(centered)
        self.value_committed.emit(self._rectangle)


class CoordinatePreviewWidget(QFrame):
    """Visual preview widget for coordinate display"""
    
    def __init__(self):
        super().__init__()
        self._point = Point2D(0.0, 0.0)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("background-color: white;")
    
    def set_point(self, point: Point2D) -> None:
        """Set point to display"""
        self._point = point
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the coordinate preview"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw coordinate system
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Draw axes
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawLine(0, center_y, self.width(), center_y)  # X axis
        painter.drawLine(center_x, 0, center_x, self.height())  # Y axis
        
        # Draw point
        scale = 0.1  # Scale factor for display
        point_x = center_x + int(self._point.x * scale)
        point_y = center_y - int(self._point.y * scale)  # Flip Y for screen coordinates
        
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        painter.drawEllipse(point_x - 3, point_y - 3, 6, 6)
        
        # Draw coordinates text
        painter.setPen(QPen(QColor(0, 0, 0)))
        coord_text = f"({self._point.x:.1f}, {self._point.y:.1f})"
        painter.drawText(5, 15, coord_text)


class RectanglePreviewWidget(QFrame):
    """Visual preview widget for rectangle display"""
    
    def __init__(self):
        super().__init__()
        self._rectangle = Rectangle2D(0.0, 0.0, 100.0, 100.0)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("background-color: white;")
    
    def set_rectangle(self, rectangle: Rectangle2D) -> None:
        """Set rectangle to display"""
        self._rectangle = rectangle
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the rectangle preview"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw coordinate system
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Draw axes
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawLine(0, center_y, self.width(), center_y)  # X axis
        painter.drawLine(center_x, 0, center_x, self.height())  # Y axis
        
        # Draw rectangle
        scale = 0.5  # Scale factor for display
        rect_x = center_x + int(self._rectangle.x * scale)
        rect_y = center_y - int(self._rectangle.y * scale)
        rect_w = int(self._rectangle.width * scale)
        rect_h = int(self._rectangle.height * scale)
        
        painter.setPen(QPen(QColor(0, 0, 255), 2))
        painter.setBrush(QBrush(QColor(0, 0, 255, 50)))
        painter.drawRect(rect_x, rect_y - rect_h, rect_w, rect_h)
        
        # Draw info text
        painter.setPen(QPen(QColor(0, 0, 0)))
        info_text = f"({self._rectangle.x:.0f}, {self._rectangle.y:.0f}) {self._rectangle.width:.0f}x{self._rectangle.height:.0f}"
        painter.drawText(5, 15, info_text)


# Export classes
__all__ = [
    'Point2D',
    'Rectangle2D',
    'Point2DEditor',
    'Rectangle2DEditor',
    'CoordinatePreviewWidget',
    'RectanglePreviewWidget'
]
