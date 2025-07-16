"""Coordinate property editors for the property panel

Specialized editors for coordinate-based properties including positions,
dimensions, transforms, and geometric properties.
"""

from typing import Any, Optional, List, Dict, Callable
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QSpinBox, QDoubleSpinBox, QHBoxLayout, QVBoxLayout,
    QLabel, QGroupBox, QGridLayout
)
from PyQt6.QtCore import pyqtSignal

from ..base import BasePropertyEditor
from ....core.models import Point, Rectangle, Transform


@dataclass
class CoordinateConfig:
    """Configuration for coordinate editors."""
    min_value: float = -999999.0
    max_value: float = 999999.0
    precision: int = 2
    step: float = 1.0
    suffix: str = ""
    read_only: bool = False


class PointEditor(BasePropertyEditor):
    """Editor for Point coordinates (x, y)."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, config: CoordinateConfig = None, parent=None):
        super().__init__(parent)
        self.config = config or CoordinateConfig()
        self._current_point = Point(0, 0)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the point editor UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # X coordinate
        layout.addWidget(QLabel("X:"))
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(self.config.min_value, self.config.max_value)
        self.x_spinbox.setDecimals(self.config.precision)
        self.x_spinbox.setSingleStep(self.config.step)
        if self.config.suffix:
            self.x_spinbox.setSuffix(self.config.suffix)
        self.x_spinbox.setReadOnly(self.config.read_only)
        self.x_spinbox.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.x_spinbox)
        
        # Y coordinate
        layout.addWidget(QLabel("Y:"))
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(self.config.min_value, self.config.max_value)
        self.y_spinbox.setDecimals(self.config.precision)
        self.y_spinbox.setSingleStep(self.config.step)
        if self.config.suffix:
            self.y_spinbox.setSuffix(self.config.suffix)
        self.y_spinbox.setReadOnly(self.config.read_only)
        self.y_spinbox.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.y_spinbox)
        
    def get_value(self) -> Point:
        """Get the current point value."""
        return Point(self.x_spinbox.value(), self.y_spinbox.value())
        
    def set_value(self, value: Point):
        """Set the point value."""
        if value and isinstance(value, Point):
            self._current_point = value
            self.x_spinbox.setValue(value.x)
            self.y_spinbox.setValue(value.y)
            
    def _on_value_changed(self):
        """Handle value changes."""
        new_point = self.get_value()
        if new_point != self._current_point:
            self._current_point = new_point
            self.value_changed.emit(new_point)


class RectangleEditor(BasePropertyEditor):
    """Editor for Rectangle coordinates (x, y, width, height)."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, config: CoordinateConfig = None, parent=None):
        super().__init__(parent)
        self.config = config or CoordinateConfig()
        self._current_rect = Rectangle(0, 0, 0, 0)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the rectangle editor UI."""
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Position
        position_group = QGroupBox("Position")
        pos_layout = QHBoxLayout(position_group)
        
        pos_layout.addWidget(QLabel("X:"))
        self.x_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.x_spinbox)
        pos_layout.addWidget(self.x_spinbox)
        
        pos_layout.addWidget(QLabel("Y:"))
        self.y_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.y_spinbox)
        pos_layout.addWidget(self.y_spinbox)
        
        layout.addWidget(position_group, 0, 0)
        
        # Size
        size_group = QGroupBox("Size")
        size_layout = QHBoxLayout(size_group)
        
        size_layout.addWidget(QLabel("W:"))
        self.width_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.width_spinbox)
        size_layout.addWidget(self.width_spinbox)
        
        size_layout.addWidget(QLabel("H:"))
        self.height_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.height_spinbox)
        size_layout.addWidget(self.height_spinbox)
        
        layout.addWidget(size_group, 0, 1)
        
    def _configure_spinbox(self, spinbox: QDoubleSpinBox):
        """Configure a spinbox with common settings."""
        spinbox.setRange(self.config.min_value, self.config.max_value)
        spinbox.setDecimals(self.config.precision)
        spinbox.setSingleStep(self.config.step)
        if self.config.suffix:
            spinbox.setSuffix(self.config.suffix)
        spinbox.setReadOnly(self.config.read_only)
        spinbox.valueChanged.connect(self._on_value_changed)
        
    def get_value(self) -> Rectangle:
        """Get the current rectangle value."""
        return Rectangle(
            self.x_spinbox.value(),
            self.y_spinbox.value(),
            self.width_spinbox.value(),
            self.height_spinbox.value()
        )
        
    def set_value(self, value: Rectangle):
        """Set the rectangle value."""
        if value and isinstance(value, Rectangle):
            self._current_rect = value
            self.x_spinbox.setValue(value.x)
            self.y_spinbox.setValue(value.y)
            self.width_spinbox.setValue(value.width)
            self.height_spinbox.setValue(value.height)
            
    def _on_value_changed(self):
        """Handle value changes."""
        new_rect = self.get_value()
        if new_rect != self._current_rect:
            self._current_rect = new_rect
            self.value_changed.emit(new_rect)


class TransformEditor(BasePropertyEditor):
    """Editor for Transform properties (translation, rotation, scale)."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, config: CoordinateConfig = None, parent=None):
        super().__init__(parent)
        self.config = config or CoordinateConfig()
        self._current_transform = Transform()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the transform editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Translation
        trans_group = QGroupBox("Translation")
        trans_layout = QHBoxLayout(trans_group)
        
        trans_layout.addWidget(QLabel("X:"))
        self.trans_x_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.trans_x_spinbox)
        trans_layout.addWidget(self.trans_x_spinbox)
        
        trans_layout.addWidget(QLabel("Y:"))
        self.trans_y_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.trans_y_spinbox)
        trans_layout.addWidget(self.trans_y_spinbox)
        
        layout.addWidget(trans_group)
        
        # Rotation
        rot_group = QGroupBox("Rotation")
        rot_layout = QHBoxLayout(rot_group)
        
        rot_layout.addWidget(QLabel("Angle:"))
        self.rotation_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.rotation_spinbox)
        self.rotation_spinbox.setSuffix("°")
        rot_layout.addWidget(self.rotation_spinbox)
        
        layout.addWidget(rot_group)
        
        # Scale
        scale_group = QGroupBox("Scale")
        scale_layout = QHBoxLayout(scale_group)
        
        scale_layout.addWidget(QLabel("X:"))
        self.scale_x_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.scale_x_spinbox)
        self.scale_x_spinbox.setValue(1.0)
        scale_layout.addWidget(self.scale_x_spinbox)
        
        scale_layout.addWidget(QLabel("Y:"))
        self.scale_y_spinbox = QDoubleSpinBox()
        self._configure_spinbox(self.scale_y_spinbox)
        self.scale_y_spinbox.setValue(1.0)
        scale_layout.addWidget(self.scale_y_spinbox)
        
        layout.addWidget(scale_group)
        
    def _configure_spinbox(self, spinbox: QDoubleSpinBox):
        """Configure a spinbox with common settings."""
        spinbox.setRange(self.config.min_value, self.config.max_value)
        spinbox.setDecimals(self.config.precision)
        spinbox.setSingleStep(self.config.step)
        spinbox.setReadOnly(self.config.read_only)
        spinbox.valueChanged.connect(self._on_value_changed)
        
    def get_value(self) -> Transform:
        """Get the current transform value."""
        return Transform(
            translation=Point(self.trans_x_spinbox.value(), self.trans_y_spinbox.value()),
            rotation=self.rotation_spinbox.value(),
            scale=Point(self.scale_x_spinbox.value(), self.scale_y_spinbox.value())
        )
        
    def set_value(self, value: Transform):
        """Set the transform value."""
        if value and isinstance(value, Transform):
            self._current_transform = value
            if value.translation:
                self.trans_x_spinbox.setValue(value.translation.x)
                self.trans_y_spinbox.setValue(value.translation.y)
            self.rotation_spinbox.setValue(value.rotation or 0.0)
            if value.scale:
                self.scale_x_spinbox.setValue(value.scale.x)
                self.scale_y_spinbox.setValue(value.scale.y)
            
    def _on_value_changed(self):
        """Handle value changes."""
        new_transform = self.get_value()
        if new_transform != self._current_transform:
            self._current_transform = new_transform
            self.value_changed.emit(new_transform)


# Export coordinate editors
__all__ = [
    'CoordinateConfig',
    'PointEditor',
    'RectangleEditor', 
    'TransformEditor'
]