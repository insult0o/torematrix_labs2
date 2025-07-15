"""Coordinate property editors for point and position values"""

from typing import Any, Optional, Dict, Union, Tuple
from PyQt6.QtWidgets import (
    QSpinBox, QDoubleSpinBox, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QSlider, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)
from ..events import PropertyNotificationCenter


class CoordinatePropertyEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Base class for coordinate property editors"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._dimensions = 2  # Default to 2D (x, y)
        self._min_values: Dict[str, float] = {}
        self._max_values: Dict[str, float] = {}
        self._step_size = 1.0
        self._decimal_places = 2
        self._show_labels = True
        self._show_visual = False
        self._linked_values = False
        
        # Parse configuration
        self._parse_coordinate_config()
    
    def _parse_coordinate_config(self) -> None:
        """Parse coordinate configuration from metadata"""
        if not self._config.metadata or not self._config.metadata.custom_attributes:
            return
        
        attrs = self._config.metadata.custom_attributes
        
        if 'dimensions' in attrs:
            self._dimensions = int(attrs['dimensions'])
        
        if 'decimal_places' in attrs:
            self._decimal_places = int(attrs['decimal_places'])
        
        if 'step_size' in attrs:
            self._step_size = float(attrs['step_size'])
        
        if 'show_labels' in attrs:
            self._show_labels = bool(attrs['show_labels'])
        
        if 'show_visual' in attrs:
            self._show_visual = bool(attrs['show_visual'])
        
        if 'linked' in attrs:
            self._linked_values = bool(attrs['linked'])
        
        # Parse range constraints
        for dim in ['x', 'y', 'z', 'w']:
            if f'{dim}_min' in attrs:
                self._min_values[dim] = float(attrs[f'{dim}_min'])
            if f'{dim}_max' in attrs:
                self._max_values[dim] = float(attrs[f'{dim}_max'])
        
        # Parse general range
        if 'min_value' in attrs:
            min_val = float(attrs['min_value'])
            for dim in ['x', 'y', 'z', 'w'][:self._dimensions]:
                if dim not in self._min_values:
                    self._min_values[dim] = min_val
        
        if 'max_value' in attrs:
            max_val = float(attrs['max_value'])
            for dim in ['x', 'y', 'z', 'w'][:self._dimensions]:
                if dim not in self._max_values:
                    self._max_values[dim] = max_val
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate coordinate value"""
        if isinstance(value, dict):
            # Validate dict format
            expected_keys = ['x', 'y', 'z', 'w'][:self._dimensions]
            
            for key in expected_keys:
                if key not in value:
                    return False, f"Missing required coordinate '{key}'"
                
                coord_value = value[key]
                if not isinstance(coord_value, (int, float)):
                    return False, f"Coordinate '{key}' must be a number"
                
                # Check range constraints
                if key in self._min_values and coord_value < self._min_values[key]:
                    return False, f"Coordinate '{key}' below minimum ({self._min_values[key]})"
                
                if key in self._max_values and coord_value > self._max_values[key]:
                    return False, f"Coordinate '{key}' above maximum ({self._max_values[key]})"
        
        elif isinstance(value, (list, tuple)):
            # Validate list/tuple format
            if len(value) != self._dimensions:
                return False, f"Expected {self._dimensions} coordinates, got {len(value)}"
            
            for i, coord_value in enumerate(value):
                if not isinstance(coord_value, (int, float)):
                    return False, f"Coordinate {i} must be a number"
        
        else:
            return False, "Value must be a coordinate dict, list, or tuple"
        
        return True, None
    
    def get_dimensions(self) -> int:
        """Get number of dimensions"""
        return self._dimensions
    
    def set_dimensions(self, dimensions: int) -> None:
        """Set number of dimensions"""
        if dimensions != self._dimensions:
            self._dimensions = max(2, min(4, dimensions))  # Clamp to 2-4
            # Recreate UI if it exists
            if hasattr(self, '_coordinate_inputs'):
                self._setup_ui()
    
    def get_range(self, dimension: str) -> Tuple[Optional[float], Optional[float]]:
        """Get min/max range for a dimension"""
        return (self._min_values.get(dimension), self._max_values.get(dimension))
    
    def set_range(self, dimension: str, min_value: Optional[float], max_value: Optional[float]) -> None:
        """Set range for a dimension"""
        if min_value is not None:
            self._min_values[dimension] = min_value
        elif dimension in self._min_values:
            del self._min_values[dimension]
        
        if max_value is not None:
            self._max_values[dimension] = max_value
        elif dimension in self._max_values:
            del self._max_values[dimension]
        
        # Update input ranges if they exist
        if hasattr(self, '_coordinate_inputs'):
            self._update_input_ranges()


class Point2DEditor(CoordinatePropertyEditor):
    """2D point coordinate editor"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._dimensions = 2
    
    def _setup_ui(self) -> None:
        """Setup 2D point editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create coordinate inputs frame
        coord_frame = QFrame()
        coord_layout = QHBoxLayout(coord_frame)
        coord_layout.setContentsMargins(0, 0, 0, 0)
        coord_layout.setSpacing(4)
        
        # Create coordinate inputs
        self._coordinate_inputs: Dict[str, QDoubleSpinBox] = {}
        self._coordinate_labels: Dict[str, QLabel] = {}
        
        dimensions = ['X', 'Y']
        dim_keys = ['x', 'y']
        
        for i, (dim_name, dim_key) in enumerate(zip(dimensions, dim_keys)):
            # Create label if enabled
            if self._show_labels:
                label = QLabel(f"{dim_name}:")
                label.setMinimumWidth(15)
                self._coordinate_labels[dim_key] = label
                coord_layout.addWidget(label)
            
            # Create spin box
            spin_box = QDoubleSpinBox()
            spin_box.setDecimals(self._decimal_places)
            spin_box.setSingleStep(self._step_size)
            
            # Set range if configured
            if dim_key in self._min_values:
                spin_box.setMinimum(self._min_values[dim_key])
            else:
                spin_box.setMinimum(-999999.99)
            
            if dim_key in self._max_values:
                spin_box.setMaximum(self._max_values[dim_key])
            else:
                spin_box.setMaximum(999999.99)
            
            # Apply styling
            self.setup_common_styling(spin_box)
            
            # Configure based on metadata
            if self._config.metadata and self._config.metadata.description:
                spin_box.setToolTip(self._config.metadata.description)
            
            self._coordinate_inputs[dim_key] = spin_box
            coord_layout.addWidget(spin_box)
            
            # Connect signals
            spin_box.valueChanged.connect(self._on_coordinate_changed)
        
        # Add link button if linked values enabled
        if self._linked_values:
            self._link_button = QPushButton("🔗")
            self._link_button.setCheckable(True)
            self._link_button.setMaximumSize(25, 25)
            self._link_button.setToolTip("Link X and Y values")
            self._link_button.clicked.connect(self._on_link_toggled)
            coord_layout.addWidget(self._link_button)
        
        layout.addWidget(coord_frame)
        
        # Add visual representation if enabled
        if self._show_visual and not self._config.compact_mode:
            self._create_visual_display(layout)
    
    def _create_visual_display(self, layout: QVBoxLayout) -> None:
        """Create visual coordinate display"""
        visual_frame = QFrame()
        visual_frame.setMinimumHeight(100)
        visual_frame.setMaximumHeight(100)
        visual_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #ccc;
                background-color: #f9f9f9;
            }
        """)
        
        self._visual_widget = CoordinateVisualWidget(self)
        visual_layout = QVBoxLayout(visual_frame)
        visual_layout.setContentsMargins(2, 2, 2, 2)
        visual_layout.addWidget(self._visual_widget)
        
        layout.addWidget(visual_frame)
    
    def _get_editor_value(self) -> Dict[str, float]:
        """Get current coordinate values"""
        return {
            'x': self._coordinate_inputs['x'].value(),
            'y': self._coordinate_inputs['y'].value()
        }
    
    def _set_editor_value(self, value: Any) -> None:
        """Set coordinate values"""
        if isinstance(value, dict):
            if 'x' in value:
                self._coordinate_inputs['x'].setValue(float(value['x']))
            if 'y' in value:
                self._coordinate_inputs['y'].setValue(float(value['y']))
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            self._coordinate_inputs['x'].setValue(float(value[0]))
            self._coordinate_inputs['y'].setValue(float(value[1]))
        
        # Update visual display
        if hasattr(self, '_visual_widget'):
            self._visual_widget.update()
    
    def _on_coordinate_changed(self, value: float) -> None:
        """Handle coordinate value change"""
        sender = self.sender()
        
        # Handle linked values
        if (self._linked_values and hasattr(self, '_link_button') and 
            self._link_button.isChecked()):
            # Find which coordinate changed and sync the other
            for dim_key, spin_box in self._coordinate_inputs.items():
                if spin_box == sender:
                    # Update other coordinates to match
                    for other_key, other_spin_box in self._coordinate_inputs.items():
                        if other_key != dim_key:
                            other_spin_box.blockSignals(True)
                            other_spin_box.setValue(value)
                            other_spin_box.blockSignals(False)
                    break
        
        # Update visual display
        if hasattr(self, '_visual_widget'):
            self._visual_widget.update()
        
        self._on_value_changed()
    
    def _on_link_toggled(self, checked: bool) -> None:
        """Handle link button toggle"""
        if checked:
            # Sync all values to the first coordinate
            first_value = self._coordinate_inputs['x'].value()
            for dim_key, spin_box in self._coordinate_inputs.items():
                if dim_key != 'x':
                    spin_box.setValue(first_value)
    
    def _update_input_ranges(self) -> None:
        """Update input ranges based on current configuration"""
        for dim_key, spin_box in self._coordinate_inputs.items():
            if dim_key in self._min_values:
                spin_box.setMinimum(self._min_values[dim_key])
            if dim_key in self._max_values:
                spin_box.setMaximum(self._max_values[dim_key])
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        has_error = new_state == PropertyEditorState.ERROR
        
        for spin_box in self._coordinate_inputs.values():
            self.setup_validation_styling(spin_box, has_error)
            
            if has_error and self._validation_error:
                spin_box.setToolTip(self.create_error_tooltip(self._validation_error))
            else:
                spin_box.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_coordinate_inputs(self) -> Dict[str, QDoubleSpinBox]:
        """Get coordinate input widgets"""
        return self._coordinate_inputs.copy()


class Point3DEditor(Point2DEditor):
    """3D point coordinate editor"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._dimensions = 3
    
    def _setup_ui(self) -> None:
        """Setup 3D point editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create coordinate inputs frame
        coord_frame = QFrame()
        
        # Use vertical layout for 3D to save space if in compact mode
        if self._config.compact_mode:
            coord_layout = QVBoxLayout(coord_frame)
        else:
            coord_layout = QHBoxLayout(coord_frame)
        
        coord_layout.setContentsMargins(0, 0, 0, 0)
        coord_layout.setSpacing(4)
        
        # Create coordinate inputs
        self._coordinate_inputs: Dict[str, QDoubleSpinBox] = {}
        self._coordinate_labels: Dict[str, QLabel] = {}
        
        dimensions = ['X', 'Y', 'Z']
        dim_keys = ['x', 'y', 'z']
        
        for i, (dim_name, dim_key) in enumerate(zip(dimensions, dim_keys)):
            if self._config.compact_mode:
                # Create horizontal sub-layout for each coordinate
                coord_sub_frame = QFrame()
                coord_sub_layout = QHBoxLayout(coord_sub_frame)
                coord_sub_layout.setContentsMargins(0, 0, 0, 0)
                coord_sub_layout.setSpacing(4)
                
                # Create label
                if self._show_labels:
                    label = QLabel(f"{dim_name}:")
                    label.setMinimumWidth(15)
                    self._coordinate_labels[dim_key] = label
                    coord_sub_layout.addWidget(label)
                
                # Create spin box
                spin_box = self._create_coordinate_spinbox(dim_key)
                coord_sub_layout.addWidget(spin_box)
                
                coord_layout.addWidget(coord_sub_frame)
            else:
                # Create label if enabled
                if self._show_labels:
                    label = QLabel(f"{dim_name}:")
                    label.setMinimumWidth(15)
                    self._coordinate_labels[dim_key] = label
                    coord_layout.addWidget(label)
                
                # Create spin box
                spin_box = self._create_coordinate_spinbox(dim_key)
                coord_layout.addWidget(spin_box)
        
        # Add link button if linked values enabled
        if self._linked_values:
            self._link_button = QPushButton("🔗")
            self._link_button.setCheckable(True)
            self._link_button.setMaximumSize(25, 25)
            self._link_button.setToolTip("Link X, Y, and Z values")
            self._link_button.clicked.connect(self._on_link_toggled)
            coord_layout.addWidget(self._link_button)
        
        layout.addWidget(coord_frame)
    
    def _create_coordinate_spinbox(self, dim_key: str) -> QDoubleSpinBox:
        """Create a coordinate spin box"""
        spin_box = QDoubleSpinBox()
        spin_box.setDecimals(self._decimal_places)
        spin_box.setSingleStep(self._step_size)
        
        # Set range if configured
        if dim_key in self._min_values:
            spin_box.setMinimum(self._min_values[dim_key])
        else:
            spin_box.setMinimum(-999999.99)
        
        if dim_key in self._max_values:
            spin_box.setMaximum(self._max_values[dim_key])
        else:
            spin_box.setMaximum(999999.99)
        
        # Apply styling
        self.setup_common_styling(spin_box)
        
        # Configure based on metadata
        if self._config.metadata and self._config.metadata.description:
            spin_box.setToolTip(self._config.metadata.description)
        
        self._coordinate_inputs[dim_key] = spin_box
        
        # Connect signals
        spin_box.valueChanged.connect(self._on_coordinate_changed)
        
        return spin_box
    
    def _get_editor_value(self) -> Dict[str, float]:
        """Get current coordinate values"""
        return {
            'x': self._coordinate_inputs['x'].value(),
            'y': self._coordinate_inputs['y'].value(),
            'z': self._coordinate_inputs['z'].value()
        }
    
    def _set_editor_value(self, value: Any) -> None:
        """Set coordinate values"""
        if isinstance(value, dict):
            for dim_key in ['x', 'y', 'z']:
                if dim_key in value:
                    self._coordinate_inputs[dim_key].setValue(float(value[dim_key]))
        elif isinstance(value, (list, tuple)) and len(value) >= 3:
            self._coordinate_inputs['x'].setValue(float(value[0]))
            self._coordinate_inputs['y'].setValue(float(value[1]))
            self._coordinate_inputs['z'].setValue(float(value[2]))
    
    def _on_link_toggled(self, checked: bool) -> None:
        """Handle link button toggle"""
        if checked:
            # Sync all values to the first coordinate
            first_value = self._coordinate_inputs['x'].value()
            for dim_key in ['y', 'z']:
                self._coordinate_inputs[dim_key].setValue(first_value)


class CoordinateVisualWidget(QFrame):
    """Visual representation widget for 2D coordinates"""
    
    def __init__(self, editor: Point2DEditor):
        super().__init__()
        self._editor = editor
        self.setMinimumSize(96, 96)
    
    def paintEvent(self, event):
        """Paint the coordinate visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(249, 249, 249))
        
        # Draw border
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # Get coordinate values
        coords = self._editor._get_editor_value()
        x_val = coords.get('x', 0)
        y_val = coords.get('y', 0)
        
        # Calculate drawing area
        margin = 10
        draw_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        # Draw center cross
        center_x = draw_rect.center().x()
        center_y = draw_rect.center().y()
        
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawLine(draw_rect.left(), center_y, draw_rect.right(), center_y)
        painter.drawLine(center_x, draw_rect.top(), center_x, draw_rect.bottom())
        
        # Draw coordinate point
        # Scale coordinates to fit in the drawing area
        max_coord = max(abs(x_val), abs(y_val), 1)  # Avoid division by zero
        scale = min(draw_rect.width(), draw_rect.height()) / 2 / max_coord
        
        point_x = center_x + x_val * scale
        point_y = center_y - y_val * scale  # Invert Y for screen coordinates
        
        # Draw point
        painter.setBrush(QBrush(QColor(0, 122, 204)))
        painter.setPen(QPen(QColor(0, 100, 180), 2))
        painter.drawEllipse(int(point_x - 4), int(point_y - 4), 8, 8)
        
        # Draw coordinate lines
        painter.setPen(QPen(QColor(0, 122, 204, 128), 1))
        painter.drawLine(center_x, center_y, int(point_x), int(point_y))