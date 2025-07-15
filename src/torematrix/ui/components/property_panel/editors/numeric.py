"""Numeric property editors for integer and float values"""

from typing import Any, Optional, Union
from PyQt6.QtWidgets import (
    QSpinBox, QDoubleSpinBox, QSlider, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QValidator

from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)
from ..events import PropertyNotificationCenter


class NumericPropertyEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Base class for numeric property editors"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._min_value: Optional[Union[int, float]] = None
        self._max_value: Optional[Union[int, float]] = None
        self._step_size: Union[int, float] = 1
        self._show_slider = False
        self._show_buttons = True
        self._prefix = ""
        self._suffix = ""
        
        # Parse configuration
        self._parse_numeric_config()
    
    def _parse_numeric_config(self) -> None:
        """Parse numeric configuration from metadata"""
        if not self._config.metadata or not self._config.metadata.validation_rules:
            return
        
        for rule in self._config.metadata.validation_rules:
            if rule.startswith('range:'):
                try:
                    range_spec = rule[6:]  # Remove 'range:' prefix
                    if '-' in range_spec:
                        min_val, max_val = range_spec.split('-')
                        self._min_value = self._parse_numeric_value(min_val)
                        self._max_value = self._parse_numeric_value(max_val)
                    elif range_spec.startswith('>='):
                        self._min_value = self._parse_numeric_value(range_spec[2:])
                    elif range_spec.startswith('<='):
                        self._max_value = self._parse_numeric_value(range_spec[2:])
                except (ValueError, IndexError):
                    pass
            
            elif rule.startswith('step:'):
                try:
                    step_spec = rule[5:]  # Remove 'step:' prefix
                    self._step_size = self._parse_numeric_value(step_spec)
                except ValueError:
                    pass
        
        # Check custom attributes
        if self._config.metadata and self._config.metadata.custom_attributes:
            attrs = self._config.metadata.custom_attributes
            
            if 'show_slider' in attrs:
                self._show_slider = bool(attrs['show_slider'])
            
            if 'show_buttons' in attrs:
                self._show_buttons = bool(attrs['show_buttons'])
            
            if 'prefix' in attrs:
                self._prefix = str(attrs['prefix'])
            
            if 'suffix' in attrs:
                self._suffix = str(attrs['suffix'])
    
    def _parse_numeric_value(self, value_str: str) -> Union[int, float]:
        """Parse numeric value from string"""
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    
    def _create_spin_box(self) -> Union[QSpinBox, QDoubleSpinBox]:
        """Create appropriate spin box (override in subclasses)"""
        raise NotImplementedError
    
    def _setup_ui(self) -> None:
        """Setup numeric editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create main input row
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        
        # Create spin box
        self._spin_box = self._create_spin_box()
        
        # Configure spin box
        self._configure_spin_box()
        
        # Apply styling
        self.setup_common_styling(self._spin_box)
        
        input_layout.addWidget(self._spin_box)
        
        # Add buttons if enabled
        if self._show_buttons and not self._config.compact_mode:
            self._create_value_buttons(input_layout)
        
        layout.addWidget(input_frame)
        
        # Add slider if enabled
        if self._show_slider and not self._config.compact_mode:
            self._create_slider(layout)
        
        # Connect signals
        self._connect_spin_box_signals()
    
    def _configure_spin_box(self) -> None:
        """Configure spin box properties"""
        # Set range
        if self._min_value is not None and self._max_value is not None:
            self._spin_box.setRange(self._min_value, self._max_value)
        elif self._min_value is not None:
            self._spin_box.setMinimum(self._min_value)
        elif self._max_value is not None:
            self._spin_box.setMaximum(self._max_value)
        
        # Set step size
        if hasattr(self._spin_box, 'setSingleStep'):
            self._spin_box.setSingleStep(self._step_size)
        
        # Set prefix and suffix
        if self._prefix:
            self._spin_box.setPrefix(self._prefix)
        if self._suffix:
            self._spin_box.setSuffix(self._suffix)
        
        # Configure based on metadata
        if self._config.metadata:
            if self._config.metadata.description:
                self._spin_box.setToolTip(self._config.metadata.description)
    
    def _create_value_buttons(self, layout: QHBoxLayout) -> None:
        """Create increment/decrement buttons"""
        # Decrement button
        self._dec_button = QPushButton("-")
        self._dec_button.setMaximumSize(25, 25)
        self._dec_button.clicked.connect(self._decrement_value)
        
        # Increment button
        self._inc_button = QPushButton("+")
        self._inc_button.setMaximumSize(25, 25)
        self._inc_button.clicked.connect(self._increment_value)
        
        layout.addWidget(self._dec_button)
        layout.addWidget(self._inc_button)
    
    def _create_slider(self, layout: QVBoxLayout) -> None:
        """Create value slider"""
        slider_frame = QFrame()
        slider_layout = QHBoxLayout(slider_frame)
        slider_layout.setContentsMargins(0, 2, 0, 0)
        
        # Create slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        
        # Configure slider range
        if self._min_value is not None and self._max_value is not None:
            # Scale values for slider (sliders work with integers)
            if isinstance(self._step_size, float):
                scale_factor = int(1 / self._step_size)
                self._slider_scale = scale_factor
                self._slider.setRange(
                    int(self._min_value * scale_factor),
                    int(self._max_value * scale_factor)
                )
                self._slider.setSingleStep(1)
            else:
                self._slider_scale = 1
                self._slider.setRange(self._min_value, self._max_value)
                self._slider.setSingleStep(self._step_size)
        else:
            self._slider_scale = 1
            self._slider.setRange(0, 100)
        
        # Min/max labels
        if self._min_value is not None:
            min_label = QLabel(str(self._min_value))
            min_label.setStyleSheet("font-size: 9px; color: #666;")
            slider_layout.addWidget(min_label)
        
        slider_layout.addWidget(self._slider)
        
        if self._max_value is not None:
            max_label = QLabel(str(self._max_value))
            max_label.setStyleSheet("font-size: 9px; color: #666;")
            slider_layout.addWidget(max_label)
        
        layout.addWidget(slider_frame)
        
        # Connect slider signals
        self._slider.valueChanged.connect(self._on_slider_changed)
    
    def _connect_spin_box_signals(self) -> None:
        """Connect spin box signals (override in subclasses)"""
        raise NotImplementedError
    
    def _increment_value(self) -> None:
        """Increment value by step size"""
        self._spin_box.stepUp()
    
    def _decrement_value(self) -> None:
        """Decrement value by step size"""
        self._spin_box.stepDown()
    
    def _on_slider_changed(self, value: int) -> None:
        """Handle slider value change"""
        if hasattr(self, '_slider_scale'):
            actual_value = value / self._slider_scale
        else:
            actual_value = value
        
        # Update spin box without triggering signals
        self._spin_box.blockSignals(True)
        self._spin_box.setValue(actual_value)
        self._spin_box.blockSignals(False)
        
        # Trigger value change
        self._on_value_changed()
    
    def _update_slider_from_spinbox(self) -> None:
        """Update slider position from spin box value"""
        if hasattr(self, '_slider'):
            value = self._spin_box.value()
            if hasattr(self, '_slider_scale'):
                slider_value = int(value * self._slider_scale)
            else:
                slider_value = value
            
            self._slider.blockSignals(True)
            self._slider.setValue(slider_value)
            self._slider.blockSignals(False)
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            self.setup_validation_styling(self._spin_box, True)
            if self._validation_error:
                self._spin_box.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self.setup_validation_styling(self._spin_box, False)
            self._spin_box.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_spin_box(self) -> Union[QSpinBox, QDoubleSpinBox]:
        """Get the underlying spin box widget"""
        return self._spin_box
    
    def get_slider(self) -> Optional[QSlider]:
        """Get the slider widget if it exists"""
        return getattr(self, '_slider', None)
    
    def set_range(self, min_value: Union[int, float], max_value: Union[int, float]) -> None:
        """Set value range"""
        self._min_value = min_value
        self._max_value = max_value
        self._spin_box.setRange(min_value, max_value)
        
        if hasattr(self, '_slider'):
            if isinstance(self._step_size, float):
                scale_factor = int(1 / self._step_size)
                self._slider.setRange(
                    int(min_value * scale_factor),
                    int(max_value * scale_factor)
                )
            else:
                self._slider.setRange(min_value, max_value)
    
    def set_step_size(self, step: Union[int, float]) -> None:
        """Set step size"""
        self._step_size = step
        if hasattr(self._spin_box, 'setSingleStep'):
            self._spin_box.setSingleStep(step)


class IntegerPropertyEditor(NumericPropertyEditor):
    """Integer property editor"""
    
    def _create_spin_box(self) -> QSpinBox:
        """Create integer spin box"""
        return QSpinBox()
    
    def _configure_spin_box(self) -> None:
        """Configure integer spin box"""
        super()._configure_spin_box()
        
        # Set default range for integers
        if self._min_value is None and self._max_value is None:
            self._spin_box.setRange(-2147483648, 2147483647)  # 32-bit int range
    
    def _get_editor_value(self) -> int:
        """Get current integer value"""
        return self._spin_box.value()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set integer value"""
        if isinstance(value, (int, float)):
            int_value = int(value)
        else:
            try:
                int_value = int(value) if value is not None else 0
            except (ValueError, TypeError):
                int_value = 0
        
        self._spin_box.setValue(int_value)
        self._update_slider_from_spinbox()
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate integer value"""
        # Check type
        if not isinstance(value, int):
            try:
                int(value)
            except (ValueError, TypeError):
                return False, "Value must be an integer"
        
        # Check range
        if self._min_value is not None or self._max_value is not None:
            is_valid, error = self.validate_range(value, self._min_value, self._max_value)
            if not is_valid:
                return is_valid, error
        
        return True, None
    
    def _connect_spin_box_signals(self) -> None:
        """Connect integer spin box signals"""
        self._spin_box.valueChanged.connect(self._on_spin_box_changed)
        self._spin_box.editingFinished.connect(self._on_editing_finished)
    
    def _on_spin_box_changed(self, value: int) -> None:
        """Handle spin box value change"""
        self._update_slider_from_spinbox()
        self._on_value_changed()
    
    def _on_editing_finished(self) -> None:
        """Handle editing finished"""
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()


class FloatPropertyEditor(NumericPropertyEditor):
    """Float property editor"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._decimal_places = 3
        
        # Parse decimal places from metadata
        if config.metadata and config.metadata.custom_attributes:
            if 'decimal_places' in config.metadata.custom_attributes:
                self._decimal_places = int(config.metadata.custom_attributes['decimal_places'])
    
    def _create_spin_box(self) -> QDoubleSpinBox:
        """Create double spin box"""
        return QDoubleSpinBox()
    
    def _configure_spin_box(self) -> None:
        """Configure double spin box"""
        super()._configure_spin_box()
        
        # Set decimal places
        self._spin_box.setDecimals(self._decimal_places)
        
        # Set default range for floats
        if self._min_value is None and self._max_value is None:
            self._spin_box.setRange(-999999.999, 999999.999)
        
        # Set default step for floats
        if self._step_size == 1:  # Default integer step
            self._step_size = 0.1
            self._spin_box.setSingleStep(self._step_size)
    
    def _get_editor_value(self) -> float:
        """Get current float value"""
        return self._spin_box.value()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set float value"""
        if isinstance(value, (int, float)):
            float_value = float(value)
        else:
            try:
                float_value = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                float_value = 0.0
        
        self._spin_box.setValue(float_value)
        self._update_slider_from_spinbox()
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate float value"""
        # Check type
        if not isinstance(value, (int, float)):
            try:
                float(value)
            except (ValueError, TypeError):
                return False, "Value must be a number"
        
        # Check range
        if self._min_value is not None or self._max_value is not None:
            is_valid, error = self.validate_range(value, self._min_value, self._max_value)
            if not is_valid:
                return is_valid, error
        
        return True, None
    
    def _connect_spin_box_signals(self) -> None:
        """Connect double spin box signals"""
        self._spin_box.valueChanged.connect(self._on_spin_box_changed)
        self._spin_box.editingFinished.connect(self._on_editing_finished)
    
    def _on_spin_box_changed(self, value: float) -> None:
        """Handle spin box value change"""
        self._update_slider_from_spinbox()
        self._on_value_changed()
    
    def _on_editing_finished(self) -> None:
        """Handle editing finished"""
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def set_decimal_places(self, places: int) -> None:
        """Set number of decimal places"""
        self._decimal_places = places
        self._spin_box.setDecimals(places)