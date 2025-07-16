"""
Merge Dialog Component for Agent 2 - Issue #235.

This module provides the MergeDialog component for merging multiple document elements
with drag-and-drop support, metadata conflict resolution, and merge preview.
"""

from typing import List, Dict, Optional, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QComboBox,
    QLineEdit, QCheckBox, QTextEdit, QGroupBox, QProgressBar,
    QFrame, QSpacerItem, QSizePolicy, QTabWidget, QWidget,
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QDrag, QFont, QColor, QPalette

from src.torematrix.core.models import Element, ElementType
from .components import ElementPreview, MetadataConflictResolver, OperationPreview, ValidationWarnings
from .resources import get_icon, IconType, merge_split_styles


class MergeDialog(QDialog):
    """Dialog for merging multiple document elements."""
    
    # Signals
    merge_requested = pyqtSignal(list, dict)  # elements, options
    preview_requested = pyqtSignal(list, dict)  # elements, options
    
    def __init__(self, available_elements: List[Element], parent=None):
        super().__init__(parent)
        self.available_elements = available_elements
        self.selected_elements = []
        self.metadata_conflicts = {}
        
        self.setup_ui()
        self.setup_connections()
        self.populate_available_elements()
        self.update_button_states()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Merge Document Elements")
        self.setModal(True)
        self.resize(1000, 700)
        
        # Apply styles
        self.setStyleSheet(merge_split_styles)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title and info
        title_layout = QHBoxLayout()
        title_label = QLabel("Merge Document Elements")
        title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        self.element_count_label = QLabel("0 elements selected")
        title_layout.addWidget(self.element_count_label)
        layout.addLayout(title_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Element selection
        left_panel = self.create_selection_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and options
        right_panel = self.create_preview_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.preview_button = QPushButton("Preview Merge")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_merge)
        
        self.merge_button = QPushButton("Merge Elements")
        self.merge_button.setEnabled(False)
        self.merge_button.setDefault(True)
        self.merge_button.clicked.connect(self.perform_merge)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.merge_button)
        
        layout.addLayout(button_layout)
        
    def create_selection_panel(self) -> QWidget:
        """Create the element selection panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Available elements section
        available_group = QGroupBox("Available Elements")
        available_layout = QVBoxLayout(available_group)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search elements...")
        self.filter_input.textChanged.connect(self.filter_available_elements)
        filter_layout.addWidget(self.filter_input)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        for element_type in ElementType:
            self.type_filter.addItem(element_type.value)
        self.type_filter.currentTextChanged.connect(self.filter_available_elements)
        filter_layout.addWidget(self.type_filter)
        
        available_layout.addLayout(filter_layout)
        
        # Available elements list
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.available_list.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        available_layout.addWidget(self.available_list)
        
        # Add buttons
        add_button_layout = QHBoxLayout()
        self.add_selected_button = QPushButton("Add Selected")
        self.add_selected_button.clicked.connect(self.add_selected_elements)
        self.add_all_button = QPushButton("Add All")
        self.add_all_button.clicked.connect(self.add_all_elements)
        
        add_button_layout.addWidget(self.add_selected_button)
        add_button_layout.addWidget(self.add_all_button)
        available_layout.addLayout(add_button_layout)
        
        layout.addWidget(available_group)
        
        # Selected elements section
        selected_group = QGroupBox("Selected Elements for Merge")
        selected_layout = QVBoxLayout(selected_group)
        
        self.selected_list = QListWidget()
        self.selected_list.setAcceptDrops(True)
        self.selected_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        selected_layout.addWidget(self.selected_list)
        
        # Remove and reorder buttons
        selected_button_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected_elements)
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_selected_elements)
        
        selected_button_layout.addWidget(self.remove_button)
        selected_button_layout.addWidget(self.clear_button)
        selected_layout.addLayout(selected_button_layout)
        
        # Order controls
        order_layout = QHBoxLayout()
        self.move_up_button = QPushButton("↑ Move Up")
        self.move_up_button.clicked.connect(self.move_element_up)
        self.move_down_button = QPushButton("↓ Move Down")
        self.move_down_button.clicked.connect(self.move_element_down)
        
        order_layout.addWidget(self.move_up_button)
        order_layout.addWidget(self.move_down_button)
        selected_layout.addLayout(order_layout)
        
        layout.addWidget(selected_group)
        
        return panel
        
    def create_preview_panel(self) -> QWidget:
        """Create the preview and options panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Options tab
        options_tab = self.create_options_tab()
        self.tab_widget.addTab(options_tab, "Merge Options")
        
        # Preview tab
        self.preview_widget = ElementPreview()
        self.tab_widget.addTab(self.preview_widget, "Element Preview")
        
        # Conflicts tab
        self.conflict_resolver = MetadataConflictResolver()
        self.tab_widget.addTab(self.conflict_resolver, "Metadata Conflicts")
        
        # Operation preview tab
        self.operation_preview = OperationPreview()
        self.tab_widget.addTab(self.operation_preview, "Operation Preview")
        
        # Validation tab
        self.validation_warnings = ValidationWarnings()
        self.tab_widget.addTab(self.validation_warnings, "Validation")
        
        layout.addWidget(self.tab_widget)
        
        return panel
        
    def create_options_tab(self) -> QWidget:
        """Create the merge options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Merge configuration
        config_group = QGroupBox("Merge Configuration")
        config_layout = QGridLayout(config_group)
        
        # Separator options
        config_layout.addWidget(QLabel("Text Separator:"), 0, 0)
        self.separator_combo = QComboBox()
        self.separator_combo.setEditable(True)
        self.separator_combo.addItems([" ", "\n", "\n\n", " | ", " - ", ""])
        config_layout.addWidget(self.separator_combo, 0, 1)
        
        # Element type for result
        config_layout.addWidget(QLabel("Result Element Type:"), 1, 0)
        self.result_type_combo = QComboBox()
        for element_type in ElementType:
            self.result_type_combo.addItem(element_type.value)
        config_layout.addWidget(self.result_type_combo, 1, 1)
        
        # Merge options checkboxes
        self.preserve_formatting = QCheckBox("Preserve text formatting")
        self.preserve_formatting.setChecked(True)
        config_layout.addWidget(self.preserve_formatting, 2, 0, 1, 2)
        
        self.merge_metadata = QCheckBox("Merge metadata from all elements")
        self.merge_metadata.setChecked(True)
        config_layout.addWidget(self.merge_metadata, 3, 0, 1, 2)
        
        self.create_hierarchy = QCheckBox("Create hierarchical relationship")
        config_layout.addWidget(self.create_hierarchy, 4, 0, 1, 2)
        
        layout.addWidget(config_group)
        
        # Preview section
        preview_group = QGroupBox("Merge Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setPlaceholderText("Select elements to see merge preview...")
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
        return tab
        
    def setup_connections(self):
        """Setup signal connections."""
        self.selected_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.separator_combo.currentTextChanged.connect(self.update_merge_preview)
        self.result_type_combo.currentTextChanged.connect(self.update_merge_preview)
        self.preserve_formatting.toggled.connect(self.update_merge_preview)
        
    def populate_available_elements(self):
        """Populate the available elements list."""
        self.available_list.clear()
        for element in self.available_elements:
            item = QListWidgetItem()
            item.setText(f"{element.element_type.value}: {element.text[:50]}...")
            item.setData(Qt.ItemDataRole.UserRole, element)
            self.available_list.addItem(item)
            
    def filter_available_elements(self):
        """Filter available elements based on search and type."""
        search_text = self.filter_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            element = item.data(Qt.ItemDataRole.UserRole)
            
            # Check text filter
            text_match = search_text in element.text.lower() if search_text else True
            
            # Check type filter
            type_match = (type_filter == "All Types" or 
                         element.element_type.value == type_filter)
            
            item.setHidden(not (text_match and type_match))
            
    def add_selected_elements(self):
        """Add selected elements to merge list."""
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            element = item.data(Qt.ItemDataRole.UserRole)
            if element not in self.selected_elements:
                self.selected_elements.append(element)
                
                merge_item = QListWidgetItem()
                merge_item.setText(f"{element.element_type.value}: {element.text[:50]}...")
                merge_item.setData(Qt.ItemDataRole.UserRole, element)
                self.selected_list.addItem(merge_item)
                
        self.update_element_count()
        self.update_button_states()
        self.update_merge_preview()
        self.check_metadata_conflicts()
        
    def add_all_elements(self):
        """Add all visible elements to merge list."""
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            if not item.isHidden():
                element = item.data(Qt.ItemDataRole.UserRole)
                if element not in self.selected_elements:
                    self.selected_elements.append(element)
                    
                    merge_item = QListWidgetItem()
                    merge_item.setText(f"{element.element_type.value}: {element.text[:50]}...")
                    merge_item.setData(Qt.ItemDataRole.UserRole, element)
                    self.selected_list.addItem(merge_item)
                    
        self.update_element_count()
        self.update_button_states()
        self.update_merge_preview()
        self.check_metadata_conflicts()
        
    def remove_selected_elements(self):
        """Remove selected elements from merge list."""
        selected_items = self.selected_list.selectedItems()
        for item in selected_items:
            element = item.data(Qt.ItemDataRole.UserRole)
            if element in self.selected_elements:
                self.selected_elements.remove(element)
            self.selected_list.takeItem(self.selected_list.row(item))
            
        self.update_element_count()
        self.update_button_states()
        self.update_merge_preview()
        self.check_metadata_conflicts()
        
    def clear_selected_elements(self):
        """Clear all selected elements."""
        self.selected_elements.clear()
        self.selected_list.clear()
        self.update_element_count()
        self.update_button_states()
        self.update_merge_preview()
        self.metadata_conflicts.clear()
        self.conflict_resolver.clear_conflicts()
        
    def move_element_up(self):
        """Move selected element up in the list."""
        current_row = self.selected_list.currentRow()
        if current_row > 0:
            # Move in list widget
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row - 1, item)
            self.selected_list.setCurrentRow(current_row - 1)
            
            # Move in elements list
            element = self.selected_elements.pop(current_row)
            self.selected_elements.insert(current_row - 1, element)
            
            self.update_merge_preview()
            
    def move_element_down(self):
        """Move selected element down in the list."""
        current_row = self.selected_list.currentRow()
        if current_row < self.selected_list.count() - 1:
            # Move in list widget
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row + 1, item)
            self.selected_list.setCurrentRow(current_row + 1)
            
            # Move in elements list
            element = self.selected_elements.pop(current_row)
            self.selected_elements.insert(current_row + 1, element)
            
            self.update_merge_preview()
            
    def update_element_count(self):
        """Update the element count label."""
        count = len(self.selected_elements)
        self.element_count_label.setText(f"{count} element{'s' if count != 1 else ''} selected")
        
    def update_button_states(self):
        """Update button enabled states."""
        has_selection = len(self.selected_elements) > 0
        has_multiple = len(self.selected_elements) > 1
        
        self.preview_button.setEnabled(has_multiple)
        self.merge_button.setEnabled(has_multiple)
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(has_selection)
        
        current_row = self.selected_list.currentRow()
        self.move_up_button.setEnabled(current_row > 0)
        self.move_down_button.setEnabled(
            current_row >= 0 and current_row < self.selected_list.count() - 1
        )
        
    def update_merge_preview(self):
        """Update the merge preview text."""
        if len(self.selected_elements) < 2:
            self.preview_text.setPlainText("Select at least 2 elements to preview merge...")
            return
            
        separator = self.separator_combo.currentText()
        if separator == "\\n":
            separator = "\n"
        elif separator == "\\n\\n":
            separator = "\n\n"
            
        texts = [element.text for element in self.selected_elements]
        merged_text = separator.join(texts)
        
        self.preview_text.setPlainText(merged_text)
        
        # Update preview widget if elements are selected
        if self.selected_elements:
            self.preview_widget.set_elements(self.selected_elements)
            
    def check_metadata_conflicts(self):
        """Check for metadata conflicts between selected elements."""
        if len(self.selected_elements) < 2:
            self.metadata_conflicts.clear()
            self.conflict_resolver.clear_conflicts()
            return
            
        # Simulate metadata conflict detection
        conflicts = {}
        
        # Check element types
        types = [element.element_type for element in self.selected_elements]
        if len(set(types)) > 1:
            conflicts["element_type"] = {
                "values": [t.value for t in types],
                "resolution": "Use Most Common Type"
            }
            
        # Check other potential conflicts
        if conflicts:
            self.metadata_conflicts = conflicts
            self.conflict_resolver.set_conflicts(conflicts)
            
    def on_selection_changed(self):
        """Handle selection changes in the selected elements list."""
        self.update_button_states()
        
        # Update preview widget with current selection
        selected_items = self.selected_list.selectedItems()
        if selected_items:
            elements = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
            self.preview_widget.set_elements(elements)
            
    def validate_merge_operation(self) -> List[str]:
        """Validate the merge operation and return warnings."""
        warnings = []
        
        if len(self.selected_elements) < 2:
            warnings.append("At least 2 elements are required for merging.")
            
        if len(self.selected_elements) > 10:
            warnings.append("Merging more than 10 elements may be slow.")
            
        # Check for different element types
        types = set(element.element_type for element in self.selected_elements)
        if len(types) > 1:
            warnings.append("Merging elements of different types may cause issues.")
            
        return warnings
        
    def get_merge_options(self) -> Dict[str, Any]:
        """Get current merge options."""
        separator = self.separator_combo.currentText()
        if separator == "\\n":
            separator = "\n"
        elif separator == "\\n\\n":
            separator = "\n\n"
            
        return {
            "separator": separator,
            "result_type": self.result_type_combo.currentText(),
            "preserve_formatting": self.preserve_formatting.isChecked(),
            "merge_metadata": self.merge_metadata.isChecked(),
            "create_hierarchy": self.create_hierarchy.isChecked(),
            "conflict_resolutions": self.conflict_resolver.get_resolutions()
        }
        
    def get_selected_elements(self) -> List[Element]:
        """Get the list of selected elements in order."""
        return self.selected_elements.copy()
        
    def preview_merge(self):
        """Preview the merge operation."""
        if len(self.selected_elements) < 2:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least 2 elements to preview merge.")
            return
            
        warnings = self.validate_merge_operation()
        if warnings:
            self.validation_warnings.set_warnings(warnings)
            
        # Update operation preview
        options = self.get_merge_options()
        self.operation_preview.set_operation("merge", self.selected_elements, options)
        
        # Switch to preview tab
        self.tab_widget.setCurrentWidget(self.operation_preview)
        
        # Emit preview signal
        self.preview_requested.emit(self.selected_elements, options)
        
    def perform_merge(self):
        """Perform the merge operation."""
        if len(self.selected_elements) < 2:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least 2 elements to merge.")
            return
            
        warnings = self.validate_merge_operation()
        if warnings and any("error" in w.lower() for w in warnings):
            QMessageBox.critical(self, "Merge Error", 
                               "Cannot proceed with merge due to errors:\n" + "\n".join(warnings))
            return
            
        # Check for unresolved conflicts
        if self.conflict_resolver.has_unresolved_conflicts():
            QMessageBox.warning(self, "Unresolved Conflicts",
                              "Please resolve all metadata conflicts before merging.")
            return
            
        options = self.get_merge_options()
        
        # Emit merge signal
        self.merge_requested.emit(self.selected_elements, options)
        
        # Close dialog
        self.accept()