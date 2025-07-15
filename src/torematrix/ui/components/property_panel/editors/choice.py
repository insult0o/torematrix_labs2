"""Choice and dropdown property editors with flexible selection options"""

from typing import List, Any, Optional, Dict, Callable
from PyQt6.QtWidgets import (
    QComboBox, QListWidget, QListWidgetItem, QButtonGroup, QRadioButton,
    QCheckBox, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QGroupBox,
    QCompleter, QLineEdit, QPushButton, QMenu, QAction
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QSortFilterProxyModel
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon

from .base import BasePropertyEditor, EditorConfiguration, PropertyEditorState
from .validation import ValidationMixin


class DropdownPropertyEditor(BasePropertyEditor, ValidationMixin):
    """Dropdown/combobox editor for single selection from predefined choices"""
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup dropdown UI components"""
        layout = QVBoxLayout(self)
        
        # Main combobox
        self.combo_box = QComboBox()
        self.combo_box.setEditable(self.config.allow_custom_values)
        self.combo_box.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
        
        # Configure appearance
        if self.config.placeholder_text:
            self.combo_box.setPlaceholderText(self.config.placeholder_text)
        
        # Setup choices
        self._update_choices()
        
        # Connect signals
        self.combo_box.currentTextChanged.connect(self._on_text_changed)
        self.combo_box.editTextChanged.connect(self._on_edit_text_changed)
        self.combo_box.activated.connect(self._on_selection_activated)
        
        layout.addWidget(self.combo_box)
        
        # Add search/filter if enabled
        if self.config.searchable:
            self._setup_search_filter()
    
    def _setup_search_filter(self) -> None:
        """Setup search/filter functionality"""
        # Make combobox searchable with completer
        completer = QCompleter()
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Create model for completer
        model = QStringListModel()
        choices = self.config.custom_attributes.get('choices', [])
        if isinstance(choices, dict):
            model.setStringList(list(choices.keys()))
        else:
            model.setStringList([str(choice) for choice in choices])
        
        completer.setModel(model)
        self.combo_box.setCompleter(completer)
    
    def _update_choices(self) -> None:
        """Update available choices"""
        self.combo_box.clear()
        
        choices = self.config.custom_attributes.get('choices', [])
        
        if isinstance(choices, dict):
            # Dict format: {display_text: value}
            for display_text, value in choices.items():
                self.combo_box.addItem(display_text, value)
        elif isinstance(choices, list):
            # List format: [value1, value2, ...]
            for choice in choices:
                if isinstance(choice, tuple) and len(choice) == 2:
                    # Tuple format: (display_text, value)
                    self.combo_box.addItem(choice[0], choice[1])
                else:
                    # Simple value
                    self.combo_box.addItem(str(choice), choice)
    
    def get_value(self) -> Any:
        """Get current selected value"""
        current_data = self.combo_box.currentData()
        if current_data is not None:
            return current_data
        return self.combo_box.currentText()
    
    def set_value(self, value: Any) -> None:
        """Set current selection by value"""
        # Try to find by data first
        for i in range(self.combo_box.count()):
            if self.combo_box.itemData(i) == value:
                self.combo_box.setCurrentIndex(i)
                return
        
        # Try to find by text
        index = self.combo_box.findText(str(value))
        if index >= 0:
            self.combo_box.setCurrentIndex(index)
        elif self.config.allow_custom_values:
            # Add and select custom value
            self.combo_box.addItem(str(value), value)
            self.combo_box.setCurrentIndex(self.combo_box.count() - 1)
    
    def _on_text_changed(self, text: str) -> None:
        """Handle combo box text change"""
        if self._validate_input(text):
            self.value_changed.emit(self.get_value())
    
    def _on_edit_text_changed(self, text: str) -> None:
        """Handle editable text change"""
        if self.combo_box.isEditable():
            self._validate_input(text)
    
    def _on_selection_activated(self, index: int) -> None:
        """Handle selection activation"""
        self.value_committed.emit(self.get_value())


class MultiSelectListEditor(BasePropertyEditor, ValidationMixin):
    """Multi-selection list editor with checkable items"""
    
    selection_changed = pyqtSignal(list)  # List of selected values
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup multi-select list UI"""
        layout = QVBoxLayout(self)
        
        # Create list widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Setup choices
        self._update_choices()
        
        # Connect signals
        self.list_widget.itemChanged.connect(self._on_item_changed)
        
        # Add to scroll area if many items
        if len(self.config.custom_attributes.get('choices', [])) > 10:
            scroll_area = QScrollArea()
            scroll_area.setWidget(self.list_widget)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(200)
            layout.addWidget(scroll_area)
        else:
            layout.addWidget(self.list_widget)
        
        # Add select all/none buttons
        if self.config.custom_attributes.get('show_select_buttons', True):
            self._add_selection_buttons(layout)
    
    def _add_selection_buttons(self, layout: QVBoxLayout) -> None:
        """Add select all/none buttons"""
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(select_none_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def _update_choices(self) -> None:
        """Update available choices"""
        self.list_widget.clear()
        
        choices = self.config.custom_attributes.get('choices', [])
        
        for choice in choices:
            if isinstance(choice, tuple) and len(choice) == 2:
                display_text, value = choice
            else:
                display_text = value = str(choice)
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            
            self.list_widget.addItem(item)
    
    def get_value(self) -> List[Any]:
        """Get list of selected values"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected
    
    def set_value(self, values: List[Any]) -> None:
        """Set selected values"""
        if not isinstance(values, list):
            values = [values] if values is not None else []
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_value = item.data(Qt.ItemDataRole.UserRole)
            
            if item_value in values:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Handle item check state change"""
        selected_values = self.get_value()
        self.selection_changed.emit(selected_values)
        self.value_changed.emit(selected_values)
    
    def _select_all(self) -> None:
        """Select all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
    
    def _select_none(self) -> None:
        """Deselect all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)


class RadioButtonGroupEditor(BasePropertyEditor, ValidationMixin):
    """Radio button group for exclusive selection"""
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup radio button group UI"""
        layout = QVBoxLayout(self)
        
        # Create button group for exclusive selection
        self.button_group = QButtonGroup()
        
        # Create group box if label provided
        group_label = self.config.custom_attributes.get('group_label')
        if group_label:
            group_box = QGroupBox(group_label)
            group_layout = QVBoxLayout(group_box)
            layout.addWidget(group_box)
            container = group_layout
        else:
            container = layout
        
        # Create radio buttons
        self._create_radio_buttons(container)
        
        # Connect signals
        self.button_group.buttonToggled.connect(self._on_button_toggled)
    
    def _create_radio_buttons(self, container) -> None:
        """Create radio buttons for choices"""
        choices = self.config.custom_attributes.get('choices', [])
        
        for i, choice in enumerate(choices):
            if isinstance(choice, tuple) and len(choice) == 2:
                display_text, value = choice
            else:
                display_text = value = str(choice)
            
            radio_btn = QRadioButton(display_text)
            radio_btn.setProperty('value', value)
            
            self.button_group.addButton(radio_btn, i)
            container.addWidget(radio_btn)
    
    def get_value(self) -> Any:
        """Get selected radio button value"""
        checked_button = self.button_group.checkedButton()
        if checked_button:
            return checked_button.property('value')
        return None
    
    def set_value(self, value: Any) -> None:
        """Set selected radio button by value"""
        for button in self.button_group.buttons():
            if button.property('value') == value:
                button.setChecked(True)
                return
    
    def _on_button_toggled(self, button, checked: bool) -> None:
        """Handle radio button toggle"""
        if checked:
            value = button.property('value')
            self.value_changed.emit(value)


class TagsEditor(BasePropertyEditor, ValidationMixin):
    """Tags editor with add/remove functionality"""
    
    tags_changed = pyqtSignal(list)  # List of tag strings
    
    def __init__(self, config: EditorConfiguration):
        super().__init__(config)
        self._tags: List[str] = []
        self._setup_ui()
        self._setup_validation()
        
    def _setup_ui(self) -> None:
        """Setup tags editor UI"""
        layout = QVBoxLayout(self)
        
        # Input area for new tags
        input_layout = QHBoxLayout()
        
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tag and press Enter")
        self.tag_input.returnPressed.connect(self._add_current_tag)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_current_tag)
        
        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)
        
        # Tags display area
        self.tags_widget = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for tags
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.tags_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(100)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(scroll_area)
        
        # Setup autocomplete if suggestions provided
        suggestions = self.config.custom_attributes.get('suggestions', [])
        if suggestions:
            completer = QCompleter(suggestions)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.tag_input.setCompleter(completer)
    
    def get_value(self) -> List[str]:
        """Get current tags list"""
        return self._tags.copy()
    
    def set_value(self, tags: List[str]) -> None:
        """Set tags list"""
        if not isinstance(tags, list):
            tags = [str(tags)] if tags is not None else []
        
        self._tags = tags.copy()
        self._update_tags_display()
    
    def _add_current_tag(self) -> None:
        """Add tag from input field"""
        tag_text = self.tag_input.text().strip()
        if tag_text and tag_text not in self._tags:
            self._tags.append(tag_text)
            self.tag_input.clear()
            self._update_tags_display()
            self.tags_changed.emit(self._tags)
            self.value_changed.emit(self._tags)
    
    def _remove_tag(self, tag: str) -> None:
        """Remove specific tag"""
        if tag in self._tags:
            self._tags.remove(tag)
            self._update_tags_display()
            self.tags_changed.emit(self._tags)
            self.value_changed.emit(self._tags)
    
    def _update_tags_display(self) -> None:
        """Update visual display of tags"""
        # Clear existing tag widgets
        while self.tags_layout.count():
            child = self.tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add tag widgets
        for tag in self._tags:
            tag_widget = self._create_tag_widget(tag)
            self.tags_layout.addWidget(tag_widget)
        
        # Add stretch to push tags to left
        self.tags_layout.addStretch()
    
    def _create_tag_widget(self, tag: str) -> QWidget:
        """Create widget for individual tag"""
        tag_widget = QWidget()
        tag_widget.setStyleSheet("""
            QWidget {
                background-color: #e1f5fe;
                border: 1px solid #0277bd;
                border-radius: 12px;
                padding: 2px 8px;
                margin: 2px;
            }
        """)
        
        layout = QHBoxLayout(tag_widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Tag text
        from PyQt6.QtWidgets import QLabel
        tag_label = QLabel(tag)
        tag_label.setStyleSheet("border: none; background: transparent;")
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #666;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5252;
                color: white;
                border-radius: 8px;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_tag(tag))
        
        layout.addWidget(tag_label)
        layout.addWidget(remove_btn)
        
        return tag_widget


# Export classes
__all__ = [
    'DropdownPropertyEditor',
    'MultiSelectListEditor', 
    'RadioButtonGroupEditor',
    'TagsEditor'
]
