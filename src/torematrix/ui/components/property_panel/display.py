"""Property display widgets for value rendering and visualization"""

from typing import Any, Optional, Dict, Union
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
    QProgressBar, QPushButton, QTextEdit, QLineEdit,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QBrush

from .models import PropertyValue, PropertyMetadata


class PropertyDisplayWidget(QWidget):
    """Widget for displaying and editing individual property values"""
    
    # Signals
    value_changed = pyqtSignal(str, object)  # property_name, new_value
    selected = pyqtSignal(str)  # property_name
    
    def __init__(self, property_name: str, property_value: Any, 
                 metadata: Optional[PropertyMetadata] = None, parent=None):
        super().__init__(parent)
        self._property_name = property_name
        self._property_value = property_value
        self._metadata = metadata
        self._compact_mode = False
        self._show_metadata = True
        self._is_selected = False
        self._validation_error: Optional[str] = None
        
        self._setup_ui()
        self._update_display()
        self._apply_styles()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(2)
        
        # Property header
        self._create_property_header()
        
        # Property value display/editor
        self._create_value_display()
        
        # Metadata section (if enabled)
        self._create_metadata_section()
        
        # Validation error section
        self._create_validation_section()
    
    def _create_property_header(self) -> None:
        """Create property name header"""
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)
        
        # Property name label
        self._name_label = QLabel(self._get_display_name())
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self._name_label.setFont(font)
        
        # Property type indicator
        self._type_label = QLabel(self._get_property_type_display())
        self._type_label.setStyleSheet("color: #666; font-size: 8px;")
        
        header_layout.addWidget(self._name_label)
        header_layout.addStretch()
        header_layout.addWidget(self._type_label)
        
        self._main_layout.addWidget(header_frame)
    
    def _create_value_display(self) -> None:
        """Create value display/editor widget"""
        self._value_frame = QFrame()
        self._value_layout = QVBoxLayout(self._value_frame)
        self._value_layout.setContentsMargins(4, 4, 4, 4)
        
        # Create appropriate editor based on property type
        self._value_widget = self._create_value_editor()
        self._value_layout.addWidget(self._value_widget)
        
        self._main_layout.addWidget(self._value_frame)
    
    def _create_value_editor(self) -> QWidget:
        """Create appropriate editor widget for the property type"""
        property_type = self._get_property_type()
        
        if property_type == "string":
            return self._create_string_editor()
        elif property_type == "integer":
            return self._create_integer_editor()
        elif property_type == "float":
            return self._create_float_editor()
        elif property_type == "boolean":
            return self._create_boolean_editor()
        elif property_type == "choice":
            return self._create_choice_editor()
        elif property_type == "confidence":
            return self._create_confidence_editor()
        elif property_type == "coordinate":
            return self._create_coordinate_editor()
        else:
            return self._create_generic_editor()
    
    def _create_string_editor(self) -> QWidget:
        """Create string property editor"""
        if self._is_multiline_string():
            editor = QTextEdit()
            editor.setMaximumHeight(60)
            editor.setPlainText(str(self._property_value))
            editor.textChanged.connect(
                lambda: self._emit_value_changed(editor.toPlainText())
            )
        else:
            editor = QLineEdit()
            editor.setText(str(self._property_value))
            editor.textChanged.connect(
                lambda text: self._emit_value_changed(text)
            )
        
        return editor
    
    def _create_integer_editor(self) -> QWidget:
        """Create integer property editor"""
        editor = QSpinBox()
        editor.setRange(-999999, 999999)
        editor.setValue(int(self._property_value) if self._property_value is not None else 0)
        editor.valueChanged.connect(
            lambda value: self._emit_value_changed(value)
        )
        return editor
    
    def _create_float_editor(self) -> QWidget:
        """Create float property editor"""
        editor = QDoubleSpinBox()
        editor.setRange(-999999.0, 999999.0)
        editor.setDecimals(3)
        editor.setValue(float(self._property_value) if self._property_value is not None else 0.0)
        editor.valueChanged.connect(
            lambda value: self._emit_value_changed(value)
        )
        return editor
    
    def _create_boolean_editor(self) -> QWidget:
        """Create boolean property editor"""
        editor = QCheckBox("Enabled")
        editor.setChecked(bool(self._property_value))
        editor.toggled.connect(
            lambda checked: self._emit_value_changed(checked)
        )
        return editor
    
    def _create_choice_editor(self) -> QWidget:
        """Create choice property editor"""
        editor = QComboBox()
        choices = self._get_property_choices()
        editor.addItems(choices)
        
        current_value = str(self._property_value)
        if current_value in choices:
            editor.setCurrentText(current_value)
        
        editor.currentTextChanged.connect(
            lambda text: self._emit_value_changed(text)
        )
        return editor
    
    def _create_confidence_editor(self) -> QWidget:
        """Create confidence score display (read-only)"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar for confidence visualization
        progress = QProgressBar()
        progress.setRange(0, 100)
        confidence_value = float(self._property_value) if self._property_value is not None else 0.0
        progress.setValue(int(confidence_value * 100))
        progress.setFormat(f"{confidence_value:.3f}")
        
        # Color coding based on confidence level
        if confidence_value >= 0.8:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        elif confidence_value >= 0.6:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
        else:
            progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        
        layout.addWidget(progress)
        return container
    
    def _create_coordinate_editor(self) -> QWidget:
        """Create coordinate property editor"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if isinstance(self._property_value, dict):
            x_value = self._property_value.get("x", 0.0)
            y_value = self._property_value.get("y", 0.0)
        else:
            x_value = y_value = 0.0
        
        # X coordinate
        x_label = QLabel("X:")
        x_editor = QDoubleSpinBox()
        x_editor.setRange(-99999.0, 99999.0)
        x_editor.setDecimals(2)
        x_editor.setValue(x_value)
        
        # Y coordinate  
        y_label = QLabel("Y:")
        y_editor = QDoubleSpinBox()
        y_editor.setRange(-99999.0, 99999.0)
        y_editor.setDecimals(2)
        y_editor.setValue(y_value)
        
        def emit_coordinate_change():
            coord_value = {"x": x_editor.value(), "y": y_editor.value()}
            self._emit_value_changed(coord_value)
        
        x_editor.valueChanged.connect(emit_coordinate_change)
        y_editor.valueChanged.connect(emit_coordinate_change)
        
        layout.addWidget(x_label)
        layout.addWidget(x_editor)
        layout.addWidget(y_label)
        layout.addWidget(y_editor)
        
        return container
    
    def _create_generic_editor(self) -> QWidget:
        """Create generic property editor for unknown types"""
        editor = QLineEdit()
        editor.setText(str(self._property_value) if self._property_value is not None else "")
        editor.textChanged.connect(
            lambda text: self._emit_value_changed(text)
        )
        return editor
    
    def _create_metadata_section(self) -> None:
        """Create metadata display section"""
        if not self._show_metadata or not self._metadata:
            self._metadata_frame = None
            return
        
        self._metadata_frame = QFrame()
        self._metadata_frame.setFrameStyle(QFrame.Shape.Box)
        self._metadata_frame.setStyleSheet("QFrame { background-color: #f0f0f0; border: 1px solid #ddd; }")
        
        metadata_layout = QVBoxLayout(self._metadata_frame)
        metadata_layout.setContentsMargins(4, 2, 4, 2)
        metadata_layout.setSpacing(1)
        
        # Description
        if self._metadata.description:
            desc_label = QLabel(self._metadata.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 8px; font-style: italic;")
            metadata_layout.addWidget(desc_label)
        
        # Validation rules
        if self._metadata.validation_rules:
            rules_text = ", ".join(self._metadata.validation_rules)
            rules_label = QLabel(f"Rules: {rules_text}")
            rules_label.setStyleSheet("color: #666; font-size: 8px;")
            metadata_layout.addWidget(rules_label)
        
        self._main_layout.addWidget(self._metadata_frame)
    
    def _create_validation_section(self) -> None:
        """Create validation error display section"""
        self._validation_frame = QFrame()
        self._validation_frame.setVisible(False)
        self._validation_frame.setStyleSheet("""
            QFrame {
                background-color: #ffebee;
                border: 1px solid #f44336;
                border-radius: 3px;
            }
        """)
        
        validation_layout = QHBoxLayout(self._validation_frame)
        validation_layout.setContentsMargins(4, 2, 4, 2)
        
        self._validation_label = QLabel()
        self._validation_label.setStyleSheet("color: #d32f2f; font-size: 8px;")
        self._validation_label.setWordWrap(True)
        
        validation_layout.addWidget(self._validation_label)
        
        self._main_layout.addWidget(self._validation_frame)
    
    def _update_display(self) -> None:
        """Update the display with current property value"""
        if hasattr(self, '_value_widget'):
            # Update the value widget based on type
            property_type = self._get_property_type()
            
            if property_type == "string":
                if isinstance(self._value_widget, QTextEdit):
                    self._value_widget.setPlainText(str(self._property_value))
                elif isinstance(self._value_widget, QLineEdit):
                    self._value_widget.setText(str(self._property_value))
            elif property_type in ["integer", "float"]:
                if hasattr(self._value_widget, 'setValue'):
                    self._value_widget.setValue(self._property_value)
            elif property_type == "boolean":
                if isinstance(self._value_widget, QCheckBox):
                    self._value_widget.setChecked(bool(self._property_value))
    
    def _apply_styles(self) -> None:
        """Apply custom styling to the widget"""
        base_style = """
            PropertyDisplayWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                margin: 1px;
            }
            PropertyDisplayWidget:hover {
                border-color: #007acc;
            }
        """
        
        if self._is_selected:
            base_style += """
                PropertyDisplayWidget {
                    border-color: #007acc;
                    background-color: #e6f3ff;
                }
            """
        
        self.setStyleSheet(base_style)
    
    # Helper methods
    def _get_display_name(self) -> str:
        """Get display name for the property"""
        if self._metadata and self._metadata.display_name:
            return self._metadata.display_name
        return self._property_name.replace("_", " ").title()
    
    def _get_property_type(self) -> str:
        """Get property type"""
        if self._metadata:
            return getattr(self._metadata, 'property_type', 'string')
        
        # Infer type from property name
        type_mapping = {
            "text": "string",
            "content": "string", 
            "x": "float",
            "y": "float",
            "width": "float",
            "height": "float",
            "confidence": "confidence",
            "type": "choice",
            "page": "integer"
        }
        return type_mapping.get(self._property_name, "string")
    
    def _get_property_type_display(self) -> str:
        """Get display text for property type"""
        property_type = self._get_property_type()
        return property_type.upper()
    
    def _is_multiline_string(self) -> bool:
        """Check if string property should use multiline editor"""
        if self._property_name in ["text", "content"] and isinstance(self._property_value, str):
            return len(self._property_value) > 50 or '\n' in self._property_value
        return False
    
    def _get_property_choices(self) -> list:
        """Get choices for choice property"""
        # Default choices - will be enhanced by other agents
        choice_mapping = {
            "type": ["Text", "Title", "Header", "List", "Table", "Image", "Formula"]
        }
        return choice_mapping.get(self._property_name, ["Option 1", "Option 2", "Option 3"])
    
    def _emit_value_changed(self, new_value: Any) -> None:
        """Emit value changed signal"""
        if new_value != self._property_value:
            self._property_value = new_value
            self.value_changed.emit(self._property_name, new_value)
    
    # Public interface
    def update_value(self, new_value: Any) -> None:
        """Update the property value and refresh display"""
        self._property_value = new_value
        self._update_display()
    
    def set_selected(self, selected: bool) -> None:
        """Set selection state"""
        self._is_selected = selected
        self._apply_styles()
        if selected:
            self.selected.emit(self._property_name)
    
    def set_compact_mode(self, compact: bool) -> None:
        """Set compact display mode"""
        self._compact_mode = compact
        if compact:
            self._main_layout.setSpacing(1)
            self._main_layout.setContentsMargins(2, 2, 2, 2)
        else:
            self._main_layout.setSpacing(2)
            self._main_layout.setContentsMargins(4, 4, 4, 4)
    
    def set_show_metadata(self, show: bool) -> None:
        """Set metadata visibility"""
        self._show_metadata = show
        if hasattr(self, '_metadata_frame') and self._metadata_frame:
            self._metadata_frame.setVisible(show)
    
    def show_validation_error(self, error_message: str) -> None:
        """Show validation error"""
        self._validation_error = error_message
        self._validation_label.setText(error_message)
        self._validation_frame.setVisible(True)
        
        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, self._hide_validation_error)
    
    def _hide_validation_error(self) -> None:
        """Hide validation error"""
        self._validation_error = None
        self._validation_frame.setVisible(False)
    
    def get_property_name(self) -> str:
        """Get property name"""
        return self._property_name
    
    def get_property_value(self) -> Any:
        """Get current property value"""
        return self._property_value
    
    def get_validation_error(self) -> Optional[str]:
        """Get current validation error"""
        return self._validation_error
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press for selection"""
        super().mousePressEvent(event)
        self.set_selected(True)
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget"""
        if self._compact_mode:
            return QSize(200, 30)
        else:
            return QSize(250, 60)


class ConfidenceScoreWidget(QWidget):
    """Widget for displaying confidence scores with color coding"""
    
    def __init__(self, confidence_score: float, parent=None):
        super().__init__(parent)
        self._confidence_score = max(0.0, min(1.0, confidence_score))  # Clamp to [0,1]
        self._show_text = True
        self._compact_mode = False
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(1)
        
        # Confidence score label
        self._score_label = QLabel(f"{self._confidence_score:.3f}")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self._score_label.setFont(font)
        
        # Progress bar for visual representation
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(int(self._confidence_score * 100))
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMaximumHeight(8)
        
        self._layout.addWidget(self._score_label)
        self._layout.addWidget(self._progress_bar)
    
    def _apply_styles(self) -> None:
        """Apply color coding based on confidence level"""
        # Determine color based on confidence score
        if self._confidence_score >= 0.8:
            color = "#4CAF50"  # Green for high confidence
            text_color = "#2E7D32"
        elif self._confidence_score >= 0.6:
            color = "#FF9800"  # Orange for medium confidence  
            text_color = "#E65100"
        elif self._confidence_score >= 0.4:
            color = "#FFC107"  # Amber for low-medium confidence
            text_color = "#FF8F00"
        else:
            color = "#F44336"  # Red for low confidence
            text_color = "#C62828"
        
        self.setStyleSheet(f"""
            ConfidenceScoreWidget {{
                background-color: {color}20;
                border: 1px solid {color};
                border-radius: 3px;
            }}
            QLabel {{
                color: {text_color};
                background-color: transparent;
                border: none;
            }}
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 2px;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 1px;
            }}
        """)
    
    def update_confidence_score(self, new_score: float) -> None:
        """Update the confidence score and refresh display"""
        self._confidence_score = max(0.0, min(1.0, new_score))
        self._score_label.setText(f"{self._confidence_score:.3f}")
        self._progress_bar.setValue(int(self._confidence_score * 100))
        self._apply_styles()
    
    def set_compact_mode(self, compact: bool) -> None:
        """Set compact display mode"""
        self._compact_mode = compact
        if compact:
            self._score_label.setVisible(False)
            self._progress_bar.setMaximumHeight(6)
        else:
            self._score_label.setVisible(True)
            self._progress_bar.setMaximumHeight(8)
    
    def set_show_text(self, show: bool) -> None:
        """Set text visibility"""
        self._show_text = show
        self._score_label.setVisible(show and not self._compact_mode)
    
    def get_confidence_score(self) -> float:
        """Get current confidence score"""
        return self._confidence_score
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget"""
        if self._compact_mode:
            return QSize(40, 20)
        else:
            return QSize(60, 35)
    
    def paintEvent(self, event) -> None:
        """Custom paint event for additional visual effects"""
        super().paintEvent(event)
        
        # Could add custom drawing here for more sophisticated visuals
        # For now, relying on stylesheet styling