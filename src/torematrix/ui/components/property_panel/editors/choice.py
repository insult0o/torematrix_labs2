"""Choice property editors for dropdown and selection inputs"""

from typing import Any, Optional, List, Union, Dict
from PyQt6.QtWidgets import (
    QComboBox, QListWidget, QListWidgetItem, QButtonGroup,
    QRadioButton, QCheckBox, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QValidator

from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)
from ..events import PropertyNotificationCenter


class ChoicePropertyEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Base class for choice-based property editors"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._choices: List[str] = []
        self._choice_values: Dict[str, Any] = {}
        self._allow_custom = False
        self._multiple_selection = False
        self._searchable = False
        
        # Parse configuration
        self._parse_choice_config()
    
    def _parse_choice_config(self) -> None:
        """Parse choice configuration from metadata"""
        if not self._config.metadata or not self._config.metadata.custom_attributes:
            return
        
        attrs = self._config.metadata.custom_attributes
        
        if 'choices' in attrs:
            choices = attrs['choices']
            if isinstance(choices, list):
                self._choices = [str(choice) for choice in choices]
            elif isinstance(choices, dict):
                self._choices = list(choices.keys())
                self._choice_values = choices
        
        if 'allow_custom' in attrs:
            self._allow_custom = bool(attrs['allow_custom'])
        
        if 'multiple' in attrs:
            self._multiple_selection = bool(attrs['multiple'])
        
        if 'searchable' in attrs:
            self._searchable = bool(attrs['searchable'])
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate choice value"""
        if self._multiple_selection:
            if not isinstance(value, (list, tuple)):
                return False, "Value must be a list for multiple selection"
            
            for item in value:
                if str(item) not in self._choices and not self._allow_custom:
                    return False, f"'{item}' is not a valid choice"
        else:
            if str(value) not in self._choices and not self._allow_custom:
                return False, f"'{value}' is not a valid choice"
        
        return True, None
    
    def get_choices(self) -> List[str]:
        """Get available choices"""
        return self._choices.copy()
    
    def set_choices(self, choices: Union[List[str], Dict[str, Any]]) -> None:
        """Set available choices"""
        if isinstance(choices, dict):
            self._choices = list(choices.keys())
            self._choice_values = choices
        else:
            self._choices = [str(choice) for choice in choices]
            self._choice_values = {}
        
        # Update UI if it exists
        if hasattr(self, '_update_choices'):
            self._update_choices()
    
    def add_choice(self, choice: str, value: Any = None) -> None:
        """Add a new choice"""
        if choice not in self._choices:
            self._choices.append(choice)
            if value is not None:
                self._choice_values[choice] = value
            
            if hasattr(self, '_update_choices'):
                self._update_choices()
    
    def remove_choice(self, choice: str) -> bool:
        """Remove a choice"""
        if choice in self._choices:
            self._choices.remove(choice)
            if choice in self._choice_values:
                del self._choice_values[choice]
            
            if hasattr(self, '_update_choices'):
                self._update_choices()
            return True
        return False
    
    def get_choice_value(self, choice: str) -> Any:
        """Get the value for a choice"""
        return self._choice_values.get(choice, choice)


class ComboBoxPropertyEditor(ChoicePropertyEditor):
    """Combo box-based choice editor"""
    
    def _setup_ui(self) -> None:
        """Setup combo box editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create combo box
        self._combo_box = QComboBox()
        self._combo_box.setEditable(self._allow_custom)
        
        # Configure based on metadata
        if self._config.metadata and self._config.metadata.description:
            self._combo_box.setToolTip(self._config.metadata.description)
        
        # Populate choices
        self._update_choices()
        
        # Apply styling
        self.setup_common_styling(self._combo_box)
        
        layout.addWidget(self._combo_box)
        
        # Add search functionality if enabled
        if self._searchable and not self._config.compact_mode:
            self._create_search_interface(layout)
        
        # Connect signals
        self._combo_box.currentTextChanged.connect(self._on_combo_changed)
        if self._allow_custom:
            self._combo_box.editTextChanged.connect(self._on_text_changed)
    
    def _create_search_interface(self, layout: QVBoxLayout) -> None:
        """Create search interface for combo box"""
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 2, 0, 0)
        search_layout.setSpacing(4)
        
        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search choices...")
        self._search_input.textChanged.connect(self._filter_choices)
        
        # Clear search button
        self._clear_search_button = QPushButton("×")
        self._clear_search_button.setMaximumSize(20, 20)
        self._clear_search_button.clicked.connect(self._clear_search)
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self._search_input)
        search_layout.addWidget(self._clear_search_button)
        
        layout.insertWidget(0, search_frame)
    
    def _update_choices(self) -> None:
        """Update combo box choices"""
        if not hasattr(self, '_combo_box'):
            return
        
        current_text = self._combo_box.currentText()
        self._combo_box.clear()
        
        for choice in self._choices:
            self._combo_box.addItem(choice)
        
        # Restore selection
        index = self._combo_box.findText(current_text)
        if index >= 0:
            self._combo_box.setCurrentIndex(index)
    
    def _filter_choices(self, search_text: str) -> None:
        """Filter choices based on search text"""
        if not hasattr(self, '_search_input'):
            return
        
        search_lower = search_text.lower()
        filtered_choices = [
            choice for choice in self._choices 
            if search_lower in choice.lower()
        ]
        
        current_text = self._combo_box.currentText()
        self._combo_box.clear()
        
        for choice in filtered_choices:
            self._combo_box.addItem(choice)
        
        # Try to restore selection
        index = self._combo_box.findText(current_text)
        if index >= 0:
            self._combo_box.setCurrentIndex(index)
    
    def _clear_search(self) -> None:
        """Clear search filter"""
        if hasattr(self, '_search_input'):
            self._search_input.clear()
    
    def _get_editor_value(self) -> Any:
        """Get current combo box value"""
        current_text = self._combo_box.currentText()
        return self.get_choice_value(current_text)
    
    def _set_editor_value(self, value: Any) -> None:
        """Set combo box value"""
        # Find matching choice
        for choice in self._choices:
            if self.get_choice_value(choice) == value or choice == str(value):
                index = self._combo_box.findText(choice)
                if index >= 0:
                    self._combo_box.setCurrentIndex(index)
                    return
        
        # If custom values allowed, set directly
        if self._allow_custom:
            self._combo_box.setEditText(str(value))
    
    def _on_combo_changed(self, text: str) -> None:
        """Handle combo box selection change"""
        self._on_value_changed()
        
        # Auto-commit for combo box selections
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _on_text_changed(self, text: str) -> None:
        """Handle text change in editable combo box"""
        self._on_value_changed()
        
        # Update validation styling
        is_valid, _ = self._validate_value(text)
        self.setup_validation_styling(self._combo_box, not is_valid)
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            self.setup_validation_styling(self._combo_box, True)
            if self._validation_error:
                self._combo_box.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self.setup_validation_styling(self._combo_box, False)
            self._combo_box.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_combo_box(self) -> QComboBox:
        """Get the underlying combo box widget"""
        return self._combo_box


class ListPropertyEditor(ChoicePropertyEditor):
    """List widget-based choice editor (supports multiple selection)"""
    
    def _setup_ui(self) -> None:
        """Setup list editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create list widget
        self._list_widget = QListWidget()
        self._list_widget.setMaximumHeight(150)  # Reasonable default height
        
        # Configure selection mode
        if self._multiple_selection:
            self._list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        else:
            self._list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Configure based on metadata
        if self._config.metadata and self._config.metadata.description:
            self._list_widget.setToolTip(self._config.metadata.description)
        
        # Populate choices
        self._update_choices()
        
        # Apply styling
        self.setup_common_styling(self._list_widget)
        
        layout.addWidget(self._list_widget)
        
        # Add control buttons if not in compact mode
        if not self._config.compact_mode:
            self._create_control_buttons(layout)
        
        # Connect signals
        self._list_widget.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _create_control_buttons(self, layout: QVBoxLayout) -> None:
        """Create control buttons for list editor"""
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 2, 0, 0)
        button_layout.setSpacing(4)
        
        if self._multiple_selection:
            # Select all button
            self._select_all_button = QPushButton("Select All")
            self._select_all_button.setMaximumWidth(80)
            self._select_all_button.clicked.connect(self._select_all)
            
            # Clear selection button
            self._clear_selection_button = QPushButton("Clear")
            self._clear_selection_button.setMaximumWidth(60)
            self._clear_selection_button.clicked.connect(self._clear_selection)
            
            button_layout.addWidget(self._select_all_button)
            button_layout.addWidget(self._clear_selection_button)
        
        button_layout.addStretch()
        
        # Selection count label
        self._selection_count_label = QLabel("0 selected")
        self._selection_count_label.setStyleSheet("color: #666; font-size: 9px;")
        button_layout.addWidget(self._selection_count_label)
        
        layout.addWidget(button_frame)
    
    def _update_choices(self) -> None:
        """Update list widget choices"""
        if not hasattr(self, '_list_widget'):
            return
        
        selected_items = []
        if self._list_widget.count() > 0:
            selected_items = [
                item.text() for item in self._list_widget.selectedItems()
            ]
        
        self._list_widget.clear()
        
        for choice in self._choices:
            item = QListWidgetItem(choice)
            self._list_widget.addItem(item)
            
            # Restore selection
            if choice in selected_items:
                item.setSelected(True)
    
    def _get_editor_value(self) -> Union[Any, List[Any]]:
        """Get current list selection value"""
        selected_items = self._list_widget.selectedItems()
        
        if self._multiple_selection:
            return [self.get_choice_value(item.text()) for item in selected_items]
        else:
            if selected_items:
                return self.get_choice_value(selected_items[0].text())
            return None
    
    def _set_editor_value(self, value: Any) -> None:
        """Set list selection value"""
        # Clear current selection
        self._list_widget.clearSelection()
        
        if self._multiple_selection and isinstance(value, (list, tuple)):
            # Multiple selection
            for v in value:
                for i in range(self._list_widget.count()):
                    item = self._list_widget.item(i)
                    if self.get_choice_value(item.text()) == v or item.text() == str(v):
                        item.setSelected(True)
        else:
            # Single selection
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if self.get_choice_value(item.text()) == value or item.text() == str(value):
                    item.setSelected(True)
                    break
        
        self._update_selection_count()
    
    def _on_selection_changed(self) -> None:
        """Handle selection change"""
        self._update_selection_count()
        self._on_value_changed()
        
        # Auto-commit for list selections
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _select_all(self) -> None:
        """Select all items"""
        if self._multiple_selection:
            for i in range(self._list_widget.count()):
                self._list_widget.item(i).setSelected(True)
    
    def _clear_selection(self) -> None:
        """Clear all selections"""
        self._list_widget.clearSelection()
    
    def _update_selection_count(self) -> None:
        """Update selection count display"""
        if hasattr(self, '_selection_count_label'):
            count = len(self._list_widget.selectedItems())
            if self._multiple_selection:
                self._selection_count_label.setText(f"{count} selected")
            else:
                self._selection_count_label.setText("1 selected" if count > 0 else "0 selected")
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            self.setup_validation_styling(self._list_widget, True)
            if self._validation_error:
                self._list_widget.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self.setup_validation_styling(self._list_widget, False)
            self._list_widget.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_list_widget(self) -> QListWidget:
        """Get the underlying list widget"""
        return self._list_widget


class RadioButtonChoiceEditor(ChoicePropertyEditor):
    """Radio button-based choice editor"""
    
    def _setup_ui(self) -> None:
        """Setup radio button choice editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create button group
        self._button_group = QButtonGroup()
        self._radio_buttons: Dict[str, QRadioButton] = {}
        
        # Create radio buttons for each choice
        for i, choice in enumerate(self._choices):
            radio = QRadioButton(choice)
            self._radio_buttons[choice] = radio
            self._button_group.addButton(radio, i)
            
            # Apply styling
            self.setup_common_styling(radio)
            
            # Configure based on metadata
            if self._config.metadata and self._config.metadata.description:
                radio.setToolTip(self._config.metadata.description)
            
            layout.addWidget(radio)
        
        # Connect signals
        self._button_group.buttonToggled.connect(self._on_radio_toggled)
    
    def _update_choices(self) -> None:
        """Update radio button choices"""
        # Clear existing buttons
        for button in self._radio_buttons.values():
            self._button_group.removeButton(button)
            button.deleteLater()
        self._radio_buttons.clear()
        
        # Recreate UI
        self._setup_ui()
    
    def _get_editor_value(self) -> Any:
        """Get current radio button value"""
        checked_button = self._button_group.checkedButton()
        if checked_button:
            button_text = checked_button.text()
            return self.get_choice_value(button_text)
        return None
    
    def _set_editor_value(self, value: Any) -> None:
        """Set radio button value"""
        for choice, button in self._radio_buttons.items():
            if self.get_choice_value(choice) == value or choice == str(value):
                button.setChecked(True)
                return
    
    def _on_radio_toggled(self, button, checked: bool) -> None:
        """Handle radio button toggle"""
        if checked:  # Only respond to the newly checked button
            self._on_value_changed()
            
            # Auto-commit for radio buttons
            if self.get_state() == PropertyEditorState.EDITING:
                self.commit_changes()
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        has_error = new_state == PropertyEditorState.ERROR
        
        for button in self._radio_buttons.values():
            self.setup_validation_styling(button, has_error)
            
            if has_error and self._validation_error:
                button.setToolTip(self.create_error_tooltip(self._validation_error))
            else:
                button.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def get_button_group(self) -> QButtonGroup:
        """Get the button group"""
        return self._button_group
    
    def get_radio_buttons(self) -> Dict[str, QRadioButton]:
        """Get the radio buttons dictionary"""
        return self._radio_buttons.copy()