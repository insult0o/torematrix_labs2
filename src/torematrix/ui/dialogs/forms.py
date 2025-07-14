"""Form dialog builder implementation.

Provides a flexible form builder for creating custom dialogs
with validation, dynamic fields, and data binding.
"""

from typing import Optional, List, Dict, Any, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum, auto
import re
import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QSlider, QDateEdit, QTimeEdit,
    QDateTimeEdit, QPushButton, QWidget, QGroupBox,
    QRadioButton, QButtonGroup, QListWidget, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal, QDate, QTime, QDateTime
from PyQt6.QtGui import QPalette

from .base import BaseDialog, DialogResult, DialogButton

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Types of form fields."""
    TEXT = auto()
    MULTILINE_TEXT = auto()
    NUMBER = auto()
    DECIMAL = auto()
    CHECKBOX = auto()
    RADIO = auto()
    DROPDOWN = auto()
    SLIDER = auto()
    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    FILE = auto()
    COLOR = auto()
    LIST = auto()
    CUSTOM = auto()


@dataclass
class ValidationRule:
    """Validation rule for a field."""
    validator: Callable[[Any], bool]
    message: str
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Run validation.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if self.validator(value):
                return True, None
            return False, self.message
        except Exception as e:
            return False, f"Validation error: {str(e)}"


@dataclass
class FormField:
    """Configuration for a form field."""
    name: str
    label: str
    field_type: FieldType
    default_value: Any = None
    required: bool = False
    enabled: bool = True
    visible: bool = True
    tooltip: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    
    # Type-specific options
    options: Optional[List[Union[str, tuple[str, Any]]]] = None  # For dropdown/radio
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    decimals: Optional[int] = None
    file_filter: Optional[str] = None
    
    # Validation
    validators: List[ValidationRule] = field(default_factory=list)
    
    # Dynamic behavior
    depends_on: Optional[str] = None
    dependency_value: Any = None
    update_callback: Optional[Callable[[Any], None]] = None


class FormWidget:
    """Wrapper for form field widgets."""
    
    def __init__(self, field: FormField, widget: QWidget):
        self.field = field
        self.widget = widget
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        self.error_label.hide()
    
    def get_value(self) -> Any:
        """Get the current field value."""
        if isinstance(self.widget, QLineEdit):
            return self.widget.text()
        elif isinstance(self.widget, QTextEdit):
            return self.widget.toPlainText()
        elif isinstance(self.widget, (QSpinBox, QDoubleSpinBox, QSlider)):
            return self.widget.value()
        elif isinstance(self.widget, QCheckBox):
            return self.widget.isChecked()
        elif isinstance(self.widget, QComboBox):
            return self.widget.currentData() or self.widget.currentText()
        elif isinstance(self.widget, QDateEdit):
            return self.widget.date().toPython()
        elif isinstance(self.widget, QTimeEdit):
            return self.widget.time().toPython()
        elif isinstance(self.widget, QDateTimeEdit):
            return self.widget.dateTime().toPython()
        elif isinstance(self.widget, QButtonGroup):
            checked = self.widget.checkedButton()
            return checked.property("value") if checked else None
        elif isinstance(self.widget, QListWidget):
            return [item.text() for item in self.widget.selectedItems()]
        return None
    
    def set_value(self, value: Any) -> None:
        """Set the field value."""
        if isinstance(self.widget, QLineEdit):
            self.widget.setText(str(value or ""))
        elif isinstance(self.widget, QTextEdit):
            self.widget.setPlainText(str(value or ""))
        elif isinstance(self.widget, (QSpinBox, QDoubleSpinBox, QSlider)):
            self.widget.setValue(value or 0)
        elif isinstance(self.widget, QCheckBox):
            self.widget.setChecked(bool(value))
        elif isinstance(self.widget, QComboBox):
            index = self.widget.findData(value)
            if index >= 0:
                self.widget.setCurrentIndex(index)
            else:
                self.widget.setCurrentText(str(value or ""))
        elif isinstance(self.widget, QDateEdit):
            if value:
                self.widget.setDate(QDate(value))
        elif isinstance(self.widget, QTimeEdit):
            if value:
                self.widget.setTime(QTime(value))
        elif isinstance(self.widget, QDateTimeEdit):
            if value:
                self.widget.setDateTime(QDateTime(value))
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate the field value.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        value = self.get_value()
        
        # Check required
        if self.field.required and not value:
            return False, f"{self.field.label} is required"
        
        # Run validators
        for rule in self.field.validators:
            is_valid, error = rule.validate(value)
            if not is_valid:
                return False, error
        
        return True, None
    
    def show_error(self, message: str) -> None:
        """Show validation error."""
        self.error_label.setText(message)
        self.error_label.show()
    
    def clear_error(self) -> None:
        """Clear validation error."""
        self.error_label.hide()
        self.error_label.clear()


class FormDialog(BaseDialog):
    """Dialog with dynamic form builder.
    
    Features:
    - Multiple field types
    - Validation support
    - Dynamic field dependencies
    - Custom layouts
    - Data binding
    """
    
    # Signals
    field_changed = Signal(str, object)  # field_name, value
    form_submitted = Signal(dict)  # form_data
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Form",
        fields: Optional[List[FormField]] = None,
        layout_type: str = "form",  # form, vertical, grid
        groups: Optional[Dict[str, List[str]]] = None,
        submit_text: str = "Submit",
        show_reset: bool = True,
        validation_on_change: bool = True,
        **kwargs
    ):
        """Initialize form dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            fields: List of form fields
            layout_type: Layout type for fields
            groups: Field grouping (group_name -> field_names)
            submit_text: Submit button text
            show_reset: Show reset button
            validation_on_change: Validate on field change
            **kwargs: Additional BaseDialog arguments
        """
        super().__init__(parent, title, **kwargs)
        
        self.fields = fields or []
        self.layout_type = layout_type
        self.groups = groups or {}
        self.submit_text = submit_text
        self.show_reset = show_reset
        self.validation_on_change = validation_on_change
        
        self._field_widgets: Dict[str, FormWidget] = {}
        self._form_data: Dict[str, Any] = {}
        
        self._setup_form_ui()
        self._setup_field_dependencies()
        self._load_default_values()
    
    def _setup_form_ui(self) -> None:
        """Setup the form UI."""
        # Create form layout based on type
        if self.groups:
            # Grouped layout
            for group_name, field_names in self.groups.items():
                group_box = QGroupBox(group_name)
                group_layout = self._create_layout()
                
                # Add fields to group
                group_fields = [f for f in self.fields if f.name in field_names]
                for field in group_fields:
                    self._add_field_to_layout(field, group_layout)
                
                group_box.setLayout(group_layout)
                self.content_layout.addWidget(group_box)
        else:
            # Single layout
            form_layout = self._create_layout()
            for field in self.fields:
                self._add_field_to_layout(field, form_layout)
            
            if isinstance(form_layout, QFormLayout):
                self.content_layout.addLayout(form_layout)
            else:
                # Wrap in widget for other layouts
                form_widget = QWidget()
                form_widget.setLayout(form_layout)
                self.content_layout.addWidget(form_widget)
        
        # Add spacing
        self.content_layout.addStretch()
        
        # Add buttons
        self._add_form_buttons()
    
    def _create_layout(self) -> Union[QFormLayout, QVBoxLayout]:
        """Create appropriate layout based on type.
        
        Returns:
            Layout instance
        """
        if self.layout_type == "form":
            layout = QFormLayout()
            layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            return layout
        else:
            return QVBoxLayout()
    
    def _add_field_to_layout(self, field: FormField, layout: Union[QFormLayout, QVBoxLayout]) -> None:
        """Add field to layout.
        
        Args:
            field: Field configuration
            layout: Target layout
        """
        # Create widget
        widget = self._create_field_widget(field)
        form_widget = FormWidget(field, widget)
        self._field_widgets[field.name] = form_widget
        
        # Setup visibility
        if not field.visible:
            widget.hide()
        
        # Add to layout
        if isinstance(layout, QFormLayout):
            # Help text
            if field.help_text:
                help_label = QLabel(field.help_text)
                help_label.setWordWrap(True)
                help_label.setStyleSheet("color: gray; font-size: 12px;")
                layout.addRow(help_label)
            
            # Field
            layout.addRow(field.label + ":", widget)
            
            # Error label
            layout.addRow("", form_widget.error_label)
        else:
            # Vertical layout
            field_layout = QVBoxLayout()
            
            # Label
            label = QLabel(field.label + ":")
            field_layout.addWidget(label)
            
            # Help text
            if field.help_text:
                help_label = QLabel(field.help_text)
                help_label.setWordWrap(True)
                help_label.setStyleSheet("color: gray; font-size: 12px;")
                field_layout.addWidget(help_label)
            
            # Widget
            field_layout.addWidget(widget)
            
            # Error label
            field_layout.addWidget(form_widget.error_label)
            
            layout.addLayout(field_layout)
        
        # Connect change signal
        self._connect_field_signals(field, widget)
    
    def _create_field_widget(self, field: FormField) -> QWidget:
        """Create widget for field type.
        
        Args:
            field: Field configuration
            
        Returns:
            Created widget
        """
        widget = None
        
        if field.field_type == FieldType.TEXT:
            widget = QLineEdit()
            if field.placeholder:
                widget.setPlaceholderText(field.placeholder)
            
        elif field.field_type == FieldType.MULTILINE_TEXT:
            widget = QTextEdit()
            widget.setMaximumHeight(100)
            
        elif field.field_type == FieldType.NUMBER:
            widget = QSpinBox()
            if field.min_value is not None:
                widget.setMinimum(int(field.min_value))
            if field.max_value is not None:
                widget.setMaximum(int(field.max_value))
            if field.step:
                widget.setSingleStep(int(field.step))
                
        elif field.field_type == FieldType.DECIMAL:
            widget = QDoubleSpinBox()
            if field.min_value is not None:
                widget.setMinimum(float(field.min_value))
            if field.max_value is not None:
                widget.setMaximum(float(field.max_value))
            if field.step:
                widget.setSingleStep(float(field.step))
            if field.decimals:
                widget.setDecimals(field.decimals)
                
        elif field.field_type == FieldType.CHECKBOX:
            widget = QCheckBox(field.label)
            
        elif field.field_type == FieldType.DROPDOWN:
            widget = QComboBox()
            if field.options:
                for option in field.options:
                    if isinstance(option, tuple):
                        widget.addItem(option[0], option[1])
                    else:
                        widget.addItem(str(option))
                        
        elif field.field_type == FieldType.RADIO:
            widget = QButtonGroup()
            radio_layout = QHBoxLayout()
            
            if field.options:
                for i, option in enumerate(field.options):
                    if isinstance(option, tuple):
                        text, value = option
                    else:
                        text = value = option
                    
                    radio = QRadioButton(str(text))
                    radio.setProperty("value", value)
                    widget.addButton(radio, i)
                    radio_layout.addWidget(radio)
            
            # Return container widget
            container = QWidget()
            container.setLayout(radio_layout)
            return container
            
        elif field.field_type == FieldType.SLIDER:
            widget = QSlider(Qt.Orientation.Horizontal)
            if field.min_value is not None:
                widget.setMinimum(int(field.min_value))
            if field.max_value is not None:
                widget.setMaximum(int(field.max_value))
            if field.step:
                widget.setTickInterval(int(field.step))
                widget.setTickPosition(QSlider.TickPosition.TicksBelow)
                
        elif field.field_type == FieldType.DATE:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            
        elif field.field_type == FieldType.TIME:
            widget = QTimeEdit()
            widget.setTime(QTime.currentTime())
            
        elif field.field_type == FieldType.DATETIME:
            widget = QDateTimeEdit()
            widget.setCalendarPopup(True)
            widget.setDateTime(QDateTime.currentDateTime())
            
        elif field.field_type == FieldType.FILE:
            # File selector with button
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            
            line_edit = QLineEdit()
            line_edit.setReadOnly(True)
            button = QPushButton("Browse...")
            
            def browse():
                file_path, _ = QFileDialog.getOpenFileName(
                    self, f"Select {field.label}", 
                    "", field.file_filter or "All Files (*)"
                )
                if file_path:
                    line_edit.setText(file_path)
                    self._on_field_changed(field.name, file_path)
            
            button.clicked.connect(browse)
            
            layout.addWidget(line_edit, 1)
            layout.addWidget(button)
            
            return container
            
        elif field.field_type == FieldType.LIST:
            widget = QListWidget()
            widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            if field.options:
                for option in field.options:
                    widget.addItem(str(option))
            widget.setMaximumHeight(100)
        
        elif field.field_type == FieldType.CUSTOM and field.update_callback:
            # Custom widget creation via callback
            widget = field.update_callback(field)
        
        # Common setup
        if widget:
            widget.setEnabled(field.enabled)
            if field.tooltip:
                widget.setToolTip(field.tooltip)
        
        return widget or QLabel("Unsupported field type")
    
    def _connect_field_signals(self, field: FormField, widget: QWidget) -> None:
        """Connect field change signals.
        
        Args:
            field: Field configuration
            widget: Field widget
        """
        def on_change(*args):
            self._on_field_changed(field.name, *args)
        
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(on_change)
        elif isinstance(widget, QTextEdit):
            widget.textChanged.connect(on_change)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.valueChanged.connect(on_change)
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(on_change)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(on_change)
        elif isinstance(widget, QSlider):
            widget.valueChanged.connect(on_change)
        elif isinstance(widget, (QDateEdit, QTimeEdit, QDateTimeEdit)):
            widget.dateTimeChanged.connect(on_change)
    
    def _setup_field_dependencies(self) -> None:
        """Setup field dependency relationships."""
        for field in self.fields:
            if field.depends_on:
                # Find dependency field
                if field.depends_on in self._field_widgets:
                    self._update_field_visibility(field)
    
    def _update_field_visibility(self, field: FormField) -> None:
        """Update field visibility based on dependencies.
        
        Args:
            field: Field to update
        """
        if not field.depends_on:
            return
        
        dep_widget = self._field_widgets.get(field.depends_on)
        if dep_widget:
            dep_value = dep_widget.get_value()
            should_show = dep_value == field.dependency_value
            
            widget = self._field_widgets.get(field.name)
            if widget:
                widget.widget.setVisible(should_show)
    
    def _load_default_values(self) -> None:
        """Load default values into fields."""
        for field in self.fields:
            if field.default_value is not None:
                widget = self._field_widgets.get(field.name)
                if widget:
                    widget.set_value(field.default_value)
    
    def _add_form_buttons(self) -> None:
        """Add form buttons."""
        # Submit button
        self.add_button(DialogButton(
            self.submit_text,
            DialogResult.OK,
            is_default=True,
            callback=self._on_submit
        ))
        
        # Reset button
        if self.show_reset:
            self.add_button(DialogButton(
                "Reset",
                DialogResult.CUSTOM,
                callback=self._on_reset
            ))
        
        # Cancel button
        self.add_button(DialogButton("Cancel", DialogResult.CANCEL))
    
    def _on_field_changed(self, field_name: str, *args) -> None:
        """Handle field value change.
        
        Args:
            field_name: Name of changed field
            *args: Change arguments
        """
        widget = self._field_widgets.get(field_name)
        if not widget:
            return
        
        value = widget.get_value()
        self.field_changed.emit(field_name, value)
        
        # Update dependent fields
        for field in self.fields:
            if field.depends_on == field_name:
                self._update_field_visibility(field)
        
        # Validate if enabled
        if self.validation_on_change:
            self._validate_field(field_name)
    
    def _validate_field(self, field_name: str) -> bool:
        """Validate a single field.
        
        Args:
            field_name: Field to validate
            
        Returns:
            True if valid
        """
        widget = self._field_widgets.get(field_name)
        if not widget:
            return True
        
        is_valid, error = widget.validate()
        
        if is_valid:
            widget.clear_error()
        else:
            widget.show_error(error or "Invalid value")
        
        return is_valid
    
    def _validate_all(self) -> bool:
        """Validate all fields.
        
        Returns:
            True if all valid
        """
        all_valid = True
        
        for field_name, widget in self._field_widgets.items():
            if not self._validate_field(field_name):
                all_valid = False
        
        return all_valid
    
    def _on_submit(self) -> None:
        """Handle form submission."""
        if not self._validate_all():
            return
        
        # Collect form data
        self._form_data = self.get_form_data()
        self.form_submitted.emit(self._form_data)
        
        # Dialog will be accepted by button handler
    
    def _on_reset(self) -> None:
        """Reset form to defaults."""
        self._load_default_values()
        
        # Clear errors
        for widget in self._field_widgets.values():
            widget.clear_error()
    
    def get_form_data(self) -> Dict[str, Any]:
        """Get all form field values.
        
        Returns:
            Dictionary of field values
        """
        data = {}
        
        for field_name, widget in self._field_widgets.items():
            data[field_name] = widget.get_value()
        
        return data
    
    def set_form_data(self, data: Dict[str, Any]) -> None:
        """Set form field values.
        
        Args:
            data: Dictionary of field values
        """
        for field_name, value in data.items():
            widget = self._field_widgets.get(field_name)
            if widget:
                widget.set_value(value)
    
    def add_field(self, field: FormField) -> None:
        """Add a field dynamically.
        
        Args:
            field: Field to add
        """
        self.fields.append(field)
        # TODO: Add to layout
    
    def remove_field(self, field_name: str) -> None:
        """Remove a field dynamically.
        
        Args:
            field_name: Name of field to remove
        """
        # TODO: Remove from layout and fields list
        pass


# Convenience functions for common field types

def create_text_field(
    name: str,
    label: str,
    required: bool = False,
    **kwargs
) -> FormField:
    """Create a text input field."""
    return FormField(name, label, FieldType.TEXT, required=required, **kwargs)


def create_number_field(
    name: str,
    label: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    **kwargs
) -> FormField:
    """Create a number input field."""
    return FormField(
        name, label, FieldType.NUMBER,
        min_value=min_value, max_value=max_value,
        **kwargs
    )


def create_choice_field(
    name: str,
    label: str,
    options: List[Union[str, tuple[str, Any]]],
    **kwargs
) -> FormField:
    """Create a dropdown choice field."""
    return FormField(name, label, FieldType.DROPDOWN, options=options, **kwargs)


def create_checkbox_field(
    name: str,
    label: str,
    default: bool = False,
    **kwargs
) -> FormField:
    """Create a checkbox field."""
    return FormField(name, label, FieldType.CHECKBOX, default_value=default, **kwargs)