"""Boolean property editors for true/false values"""

from typing import Any, Optional
from PyQt6.QtWidgets import (
    QCheckBox, QRadioButton, QButtonGroup, QVBoxLayout, 
    QHBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)
from ..events import PropertyNotificationCenter


class BooleanPropertyEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Base class for boolean property editors"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._true_text = "True"
        self._false_text = "False"
        self._use_custom_labels = False
        
        # Parse configuration
        self._parse_boolean_config()
    
    def _parse_boolean_config(self) -> None:
        """Parse boolean configuration from metadata"""
        if not self._config.metadata or not self._config.metadata.custom_attributes:
            return
        
        attrs = self._config.metadata.custom_attributes
        
        if 'true_text' in attrs:
            self._true_text = str(attrs['true_text'])
            self._use_custom_labels = True
        
        if 'false_text' in attrs:
            self._false_text = str(attrs['false_text'])
            self._use_custom_labels = True
        
        # Common alternative labels
        if 'labels' in attrs and isinstance(attrs['labels'], dict):
            labels = attrs['labels']
            if 'true' in labels:
                self._true_text = str(labels['true'])
                self._use_custom_labels = True
            if 'false' in labels:
                self._false_text = str(labels['false'])
                self._use_custom_labels = True
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate boolean value"""
        if not isinstance(value, bool):
            # Try to convert to boolean
            if isinstance(value, str):
                if value.lower() in ['true', '1', 'yes', 'on', 'enabled']:
                    return True, None
                elif value.lower() in ['false', '0', 'no', 'off', 'disabled']:
                    return True, None
                else:
                    return False, "Value must be true or false"
            elif isinstance(value, (int, float)):
                return True, None  # 0 = False, anything else = True
            else:
                return False, "Value must be a boolean"
        
        return True, None


class CheckboxPropertyEditor(BooleanPropertyEditor):
    """Checkbox-based boolean property editor"""
    
    def _setup_ui(self) -> None:
        """Setup checkbox editor UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Create checkbox
        self._checkbox = QCheckBox()
        
        # Set checkbox text
        if self._use_custom_labels:
            # For custom labels, we'll show both options
            checkbox_text = f"{self._false_text} / {self._true_text}"
        else:
            checkbox_text = self._config.property_name.replace('_', ' ').title()
        
        self._checkbox.setText(checkbox_text)
        
        # Apply styling
        self.setup_common_styling(self._checkbox)
        
        # Configure based on metadata
        if self._config.metadata:
            if self._config.metadata.description:
                self._checkbox.setToolTip(self._config.metadata.description)
        
        layout.addWidget(self._checkbox)
        layout.addStretch()
        
        # Connect signals
        self._checkbox.toggled.connect(self._on_checkbox_toggled)
    
    def _get_editor_value(self) -> bool:
        """Get current checkbox value"""
        return self._checkbox.isChecked()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set checkbox value"""
        if isinstance(value, bool):
            bool_value = value
        elif isinstance(value, str):
            bool_value = value.lower() in ['true', '1', 'yes', 'on', 'enabled']
        elif isinstance(value, (int, float)):
            bool_value = bool(value)
        else:
            bool_value = False
        
        self._checkbox.setChecked(bool_value)
    
    def _on_checkbox_toggled(self, checked: bool) -> None:
        """Handle checkbox toggle"""
        self._on_value_changed()
        
        # Auto-commit for boolean values (they're usually immediate)
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            self.setup_validation_styling(self._checkbox, True)
            if self._validation_error:
                self._checkbox.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self.setup_validation_styling(self._checkbox, False)
            self._checkbox.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_checkbox(self) -> QCheckBox:
        """Get the underlying checkbox widget"""
        return self._checkbox
    
    def set_text(self, text: str) -> None:
        """Set checkbox text"""
        self._checkbox.setText(text)


class RadioButtonPropertyEditor(BooleanPropertyEditor):
    """Radio button-based boolean property editor"""
    
    def _setup_ui(self) -> None:
        """Setup radio button editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create button group
        self._button_group = QButtonGroup()
        
        # Create radio buttons
        self._true_radio = QRadioButton(self._true_text)
        self._false_radio = QRadioButton(self._false_text)
        
        # Add to button group
        self._button_group.addButton(self._true_radio, 1)  # True = 1
        self._button_group.addButton(self._false_radio, 0)  # False = 0
        
        # Apply styling
        self.setup_common_styling(self._true_radio)
        self.setup_common_styling(self._false_radio)
        
        # Configure based on metadata
        if self._config.metadata and self._config.metadata.description:
            self._true_radio.setToolTip(self._config.metadata.description)
            self._false_radio.setToolTip(self._config.metadata.description)
        
        # Layout radio buttons
        if self._config.compact_mode:
            # Horizontal layout for compact mode
            radio_layout = QHBoxLayout()
            radio_layout.addWidget(self._true_radio)
            radio_layout.addWidget(self._false_radio)
            radio_layout.addStretch()
            layout.addLayout(radio_layout)
        else:
            # Vertical layout for normal mode
            layout.addWidget(self._true_radio)
            layout.addWidget(self._false_radio)
        
        # Connect signals
        self._button_group.buttonToggled.connect(self._on_radio_toggled)
    
    def _get_editor_value(self) -> bool:
        """Get current radio button value"""
        return self._true_radio.isChecked()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set radio button value"""
        if isinstance(value, bool):
            bool_value = value
        elif isinstance(value, str):
            bool_value = value.lower() in ['true', '1', 'yes', 'on', 'enabled']
        elif isinstance(value, (int, float)):
            bool_value = bool(value)
        else:
            bool_value = False
        
        if bool_value:
            self._true_radio.setChecked(True)
        else:
            self._false_radio.setChecked(True)
    
    def _on_radio_toggled(self, button, checked: bool) -> None:
        """Handle radio button toggle"""
        if checked:  # Only respond to the newly checked button
            self._on_value_changed()
            
            # Auto-commit for boolean values
            if self.get_state() == PropertyEditorState.EDITING:
                self.commit_changes()
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        has_error = new_state == PropertyEditorState.ERROR
        
        self.setup_validation_styling(self._true_radio, has_error)
        self.setup_validation_styling(self._false_radio, has_error)
        
        if has_error and self._validation_error:
            tooltip = self.create_error_tooltip(self._validation_error)
            self._true_radio.setToolTip(tooltip)
            self._false_radio.setToolTip(tooltip)
        else:
            tooltip = self._config.metadata.description if self._config.metadata else ""
            self._true_radio.setToolTip(tooltip)
            self._false_radio.setToolTip(tooltip)
    
    def get_true_radio(self) -> QRadioButton:
        """Get the true radio button"""
        return self._true_radio
    
    def get_false_radio(self) -> QRadioButton:
        """Get the false radio button"""
        return self._false_radio
    
    def get_button_group(self) -> QButtonGroup:
        """Get the button group"""
        return self._button_group
    
    def set_labels(self, true_text: str, false_text: str) -> None:
        """Set radio button labels"""
        self._true_text = true_text
        self._false_text = false_text
        self._true_radio.setText(true_text)
        self._false_radio.setText(false_text)


class ToggleSwitchEditor(BooleanPropertyEditor):
    """Toggle switch-style boolean property editor"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._switch_width = 50
        self._switch_height = 25
    
    def _setup_ui(self) -> None:
        """Setup toggle switch UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Create toggle switch (using styled checkbox)
        self._toggle = QCheckBox()
        self._toggle.setFixedSize(self._switch_width, self._switch_height)
        
        # Apply toggle switch styling
        self._apply_toggle_styling()
        
        # Create labels
        if self._use_custom_labels:
            self._false_label = QLabel(self._false_text)
            self._true_label = QLabel(self._true_text)
            
            # Style labels
            self._false_label.setStyleSheet("color: #666; font-size: 9px;")
            self._true_label.setStyleSheet("color: #666; font-size: 9px;")
            
            layout.addWidget(self._false_label)
        
        layout.addWidget(self._toggle)
        
        if self._use_custom_labels:
            layout.addWidget(self._true_label)
        
        layout.addStretch()
        
        # Configure based on metadata
        if self._config.metadata and self._config.metadata.description:
            self._toggle.setToolTip(self._config.metadata.description)
        
        # Connect signals
        self._toggle.toggled.connect(self._on_toggle_switched)
    
    def _apply_toggle_styling(self) -> None:
        """Apply toggle switch styling"""
        self._toggle.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                outline: none;
            }
            
            QCheckBox::indicator {
                width: 46px;
                height: 21px;
                border-radius: 10px;
                background-color: #ccc;
                border: 2px solid #999;
            }
            
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }
            
            QCheckBox::indicator:unchecked {
                background-color: #f0f0f0;
                border: 2px solid #ccc;
            }
            
            QCheckBox::indicator:hover {
                border: 2px solid #007acc;
            }
            
            QCheckBox::indicator:checked:hover {
                background-color: #45a049;
                border: 2px solid #45a049;
            }
        """)
    
    def _get_editor_value(self) -> bool:
        """Get current toggle value"""
        return self._toggle.isChecked()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set toggle value"""
        if isinstance(value, bool):
            bool_value = value
        elif isinstance(value, str):
            bool_value = value.lower() in ['true', '1', 'yes', 'on', 'enabled']
        elif isinstance(value, (int, float)):
            bool_value = bool(value)
        else:
            bool_value = False
        
        self._toggle.setChecked(bool_value)
        self._update_label_styling(bool_value)
    
    def _on_toggle_switched(self, checked: bool) -> None:
        """Handle toggle switch"""
        self._update_label_styling(checked)
        self._on_value_changed()
        
        # Auto-commit for boolean values
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _update_label_styling(self, checked: bool) -> None:
        """Update label styling based on state"""
        if not self._use_custom_labels:
            return
        
        if checked:
            self._false_label.setStyleSheet("color: #999; font-size: 9px;")
            self._true_label.setStyleSheet("color: #4CAF50; font-size: 9px; font-weight: bold;")
        else:
            self._false_label.setStyleSheet("color: #f44336; font-size: 9px; font-weight: bold;")
            self._true_label.setStyleSheet("color: #999; font-size: 9px;")
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            if self._validation_error:
                self._toggle.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self._toggle.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_toggle(self) -> QCheckBox:
        """Get the underlying toggle widget"""
        return self._toggle
    
    def set_switch_size(self, width: int, height: int) -> None:
        """Set toggle switch size"""
        self._switch_width = width
        self._switch_height = height
        self._toggle.setFixedSize(width, height)