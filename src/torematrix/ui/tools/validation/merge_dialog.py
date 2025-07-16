"""
Merge Dialog Component for Document Element Merging.

This module provides a comprehensive dialog interface for merging multiple
document elements, with support for element selection, preview, and metadata
conflict resolution.
"""

from typing import List, Optional, Dict, Any, Set
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QListWidget, QListWidgetItem, QTextEdit, QLabel, QPushButton,
    QSplitter, QWidget, QScrollArea, QFrame, QCheckBox, QComboBox,
    QProgressBar, QMessageBox, QToolButton, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QFont

from ....core.models import Element, ElementType
from .components.element_preview import ElementPreview
from .components.metadata_resolver import MetadataConflictResolver
from .components.operation_preview import OperationPreview
from .components.validation_ui import ValidationWarnings


class MergeDialog(QDialog):
    """
    Main dialog for merging multiple document elements.
    
    Provides an intuitive interface for selecting elements, configuring merge
    options, and previewing the merge result with metadata conflict resolution.
    """
    
    merge_requested = pyqtSignal(list, dict)  # elements, options
    
    def __init__(self, available_elements: List[Element], parent=None):
        super().__init__(parent)
        self.available_elements = available_elements
        self.selected_elements: List[Element] = []
        self.setup_ui()
        self.setup_connections()
        
        # Window configuration
        self.setWindowTitle("Merge Document Elements")
        self.setModal(True)
        self.resize(900, 700)
    
    def setup_ui(self):
        """Set up the main dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("Merge Document Elements")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        description_label = QLabel(
            "Select multiple elements to merge into a single element. "
            "You can drag elements from the available list or use the selection buttons."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(description_label)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(content_splitter)
        
        # Left panel - Element selection
        self.setup_selection_panel(content_splitter)
        
        # Right panel - Preview and options
        self.setup_preview_panel(content_splitter)
        
        # Bottom section - Validation and actions
        self.setup_bottom_section(layout)
    
    def setup_selection_panel(self, parent):
        """Set up the element selection panel."""
        selection_widget = QWidget()
        selection_layout = QVBoxLayout(selection_widget)
        
        # Available elements section
        available_group = QGroupBox("Available Elements")
        available_layout = QVBoxLayout(available_group)
        
        # Search and filter controls
        filter_layout = QHBoxLayout()
        self.element_type_filter = QComboBox()
        self.element_type_filter.addItem("All Types")
        for element_type in ElementType:
            self.element_type_filter.addItem(element_type.value)
        self.element_type_filter.currentTextChanged.connect(self.filter_available_elements)
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.element_type_filter)
        filter_layout.addStretch()
        available_layout.addLayout(filter_layout)
        
        # Available elements list
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.populate_available_elements()
        available_layout.addWidget(self.available_list)
        
        # Selection buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add →")
        self.add_all_button = QPushButton("Add All →")
        self.remove_button = QPushButton("← Remove")
        self.clear_button = QPushButton("← Clear All")
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.add_all_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.clear_button)
        available_layout.addLayout(button_layout)
        
        selection_layout.addWidget(available_group)
        
        # Selected elements section
        selected_group = QGroupBox("Selected for Merge")
        selected_layout = QVBoxLayout(selected_group)
        
        self.selected_list = QListWidget()
        selected_layout.addWidget(self.selected_list)
        
        # Order controls
        order_layout = QHBoxLayout()
        self.move_up_button = QToolButton()
        self.move_up_button.setText("↑")
        self.move_up_button.setToolTip("Move selected element up")
        self.move_down_button = QToolButton()
        self.move_down_button.setText("↓")
        self.move_down_button.setToolTip("Move selected element down")
        
        order_layout.addWidget(QLabel("Order:"))
        order_layout.addWidget(self.move_up_button)
        order_layout.addWidget(self.move_down_button)
        order_layout.addStretch()
        selected_layout.addLayout(order_layout)
        
        selection_layout.addWidget(selected_group)
        parent.addWidget(selection_widget)
    
    def setup_preview_panel(self, parent):
        """Set up the preview and options panel."""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # Merge preview
        preview_group = QGroupBox("Merge Preview")
        preview_group_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        preview_group_layout.addWidget(self.preview_text)
        
        # Merge options
        options_group = QGroupBox("Merge Options")
        options_layout = QGridLayout(options_group)
        
        # Separator selection
        options_layout.addWidget(QLabel("Text Separator:"), 0, 0)
        self.separator_combo = QComboBox()
        self.separator_combo.addItems([
            "Single Space", "Double Space", "Newline", 
            "Double Newline", "Custom..."
        ])
        self.separator_combo.currentTextChanged.connect(self.update_preview)
        options_layout.addWidget(self.separator_combo, 0, 1)
        
        # Preserve formatting
        self.preserve_formatting = QCheckBox("Preserve original formatting")
        self.preserve_formatting.setChecked(True)
        self.preserve_formatting.stateChanged.connect(self.update_preview)
        options_layout.addWidget(self.preserve_formatting, 1, 0, 1, 2)
        
        preview_group_layout.addWidget(options_group)
        preview_layout.addWidget(preview_group)
        
        # Metadata conflict resolution
        self.metadata_resolver = MetadataConflictResolver()
        preview_layout.addWidget(self.metadata_resolver)
        
        # Operation preview
        self.operation_preview = OperationPreview()
        preview_layout.addWidget(self.operation_preview)
        
        parent.addWidget(preview_widget)
    
    def setup_bottom_section(self, parent_layout):
        """Set up the bottom validation and action section."""
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Validation warnings
        self.validation_warnings = ValidationWarnings()
        bottom_layout.addWidget(self.validation_warnings)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_button = QPushButton("Preview Merge")
        self.preview_button.setEnabled(False)
        
        self.merge_button = QPushButton("Perform Merge")
        self.merge_button.setEnabled(False)
        self.merge_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.cancel_button)
        
        bottom_layout.addLayout(button_layout)
        parent_layout.addWidget(bottom_widget)
    
    def setup_connections(self):
        """Set up signal connections."""
        # Selection buttons
        self.add_button.clicked.connect(self.add_selected_elements)
        self.add_all_button.clicked.connect(self.add_all_elements)
        self.remove_button.clicked.connect(self.remove_selected_elements)
        self.clear_button.clicked.connect(self.clear_selected_elements)
        
        # Order buttons
        self.move_up_button.clicked.connect(self.move_element_up)
        self.move_down_button.clicked.connect(self.move_element_down)
        
        # List selections
        self.available_list.itemSelectionChanged.connect(self.update_button_states)
        self.selected_list.itemSelectionChanged.connect(self.update_button_states)
        self.selected_list.itemChanged.connect(self.update_merge_preview)
        
        # Action buttons
        self.preview_button.clicked.connect(self.preview_merge)
        self.merge_button.clicked.connect(self.perform_merge)
        self.cancel_button.clicked.connect(self.reject)
    
    def populate_available_elements(self):
        """Populate the available elements list."""
        self.available_list.clear()
        for element in self.available_elements:
            item = QListWidgetItem(f"{element.element_type.value}: {element.text[:50]}...")
            item.setData(Qt.ItemDataRole.UserRole, element)
            self.available_list.addItem(item)
    
    def filter_available_elements(self):
        """Filter available elements by type."""
        filter_type = self.element_type_filter.currentText()
        
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            element = item.data(Qt.ItemDataRole.UserRole)
            
            if filter_type == "All Types" or element.element_type.value == filter_type:
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def add_selected_elements(self):
        """Add selected elements to merge list."""
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            element = item.data(Qt.ItemDataRole.UserRole)
            if element not in self.selected_elements:
                self.selected_elements.append(element)
                
                merge_item = QListWidgetItem(f"{element.element_type.value}: {element.text[:50]}...")
                merge_item.setData(Qt.ItemDataRole.UserRole, element)
                self.selected_list.addItem(merge_item)
        
        self.update_merge_preview()
        self.update_button_states()
    
    def add_all_elements(self):
        """Add all visible elements to merge list."""
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            if not item.isHidden():
                element = item.data(Qt.ItemDataRole.UserRole)
                if element not in self.selected_elements:
                    self.selected_elements.append(element)
                    
                    merge_item = QListWidgetItem(f"{element.element_type.value}: {element.text[:50]}...")
                    merge_item.setData(Qt.ItemDataRole.UserRole, element)
                    self.selected_list.addItem(merge_item)
        
        self.update_merge_preview()
        self.update_button_states()
    
    def remove_selected_elements(self):
        """Remove selected elements from merge list."""
        selected_items = self.selected_list.selectedItems()
        for item in selected_items:
            element = item.data(Qt.ItemDataRole.UserRole)
            if element in self.selected_elements:
                self.selected_elements.remove(element)
            
            row = self.selected_list.row(item)
            self.selected_list.takeItem(row)
        
        self.update_merge_preview()
        self.update_button_states()
    
    def clear_selected_elements(self):
        """Clear all selected elements."""
        self.selected_elements.clear()
        self.selected_list.clear()
        self.update_merge_preview()
        self.update_button_states()
    
    def move_element_up(self):
        """Move selected element up in the merge order."""
        current_row = self.selected_list.currentRow()
        if current_row > 0:
            # Move in list widget
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row - 1, item)
            self.selected_list.setCurrentRow(current_row - 1)
            
            # Move in elements list
            self.selected_elements[current_row], self.selected_elements[current_row - 1] = \
                self.selected_elements[current_row - 1], self.selected_elements[current_row]
            
            self.update_merge_preview()
    
    def move_element_down(self):
        """Move selected element down in the merge order."""
        current_row = self.selected_list.currentRow()
        if current_row >= 0 and current_row < self.selected_list.count() - 1:
            # Move in list widget
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row + 1, item)
            self.selected_list.setCurrentRow(current_row + 1)
            
            # Move in elements list
            self.selected_elements[current_row], self.selected_elements[current_row + 1] = \
                self.selected_elements[current_row + 1], self.selected_elements[current_row]
            
            self.update_merge_preview()
    
    def update_merge_preview(self):
        """Update the merge preview with current selections."""
        if self.selected_elements:
            # Get separator
            separator_map = {
                "Single Space": " ",
                "Double Space": "  ",
                "Newline": "\n",
                "Double Newline": "\n\n"
            }
            separator = separator_map.get(self.separator_combo.currentText(), " ")
            
            # Merge text content
            merged_text = separator.join(element.text for element in self.selected_elements)
            self.preview_text.setPlainText(merged_text)
            
            # Check for metadata conflicts
            self.check_metadata_conflicts()
            
            # Update operation preview
            merge_options = self.get_merge_options()
            self.operation_preview.set_operation("merge", self.selected_elements, merge_options)
        else:
            self.preview_text.clear()
    
    def check_metadata_conflicts(self):
        """Check for metadata conflicts between selected elements."""
        if len(self.selected_elements) < 2:
            self.metadata_resolver.clear_conflicts()
            return
        
        # Simple conflict detection - check if elements have different types
        types = set(element.element_type for element in self.selected_elements)
        if len(types) > 1:
            conflicts = {
                "element_type": {
                    "values": list(types),
                    "resolution": "use_first"  # Default resolution
                }
            }
            self.metadata_resolver.set_conflicts(conflicts)
        else:
            self.metadata_resolver.clear_conflicts()
    
    def update_button_states(self):
        """Update button enabled states based on selections."""
        has_available_selection = bool(self.available_list.selectedItems())
        has_selected_elements = bool(self.selected_elements)
        has_selected_item = self.selected_list.currentItem() is not None
        
        self.add_button.setEnabled(has_available_selection)
        self.remove_button.setEnabled(has_selected_item)
        self.clear_button.setEnabled(has_selected_elements)
        
        current_row = self.selected_list.currentRow()
        self.move_up_button.setEnabled(current_row > 0)
        self.move_down_button.setEnabled(
            current_row >= 0 and current_row < self.selected_list.count() - 1
        )
        
        # Enable merge buttons only if we have 2+ elements
        can_merge = len(self.selected_elements) >= 2
        self.preview_button.setEnabled(can_merge)
        self.merge_button.setEnabled(can_merge)
    
    def preview_merge(self):
        """Preview the merge operation."""
        if len(self.selected_elements) < 2:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least 2 elements to merge.")
            return
        
        # Validate the merge operation
        warnings = self.validate_merge_operation()
        self.validation_warnings.set_warnings(warnings)
        
        # Update preview
        self.update_merge_preview()
    
    def validate_merge_operation(self) -> List[str]:
        """Validate the merge operation and return warnings."""
        warnings = []
        
        if len(self.selected_elements) < 2:
            warnings.append("At least 2 elements are required for merging.")
        
        if len(self.selected_elements) > 10:
            warnings.append("Merging many elements may result in very long text.")
        
        # Check for different element types
        types = set(element.element_type for element in self.selected_elements)
        if len(types) > 1:
            warnings.append(f"Merging different element types: {', '.join(t.value for t in types)}")
        
        return warnings
    
    def perform_merge(self):
        """Perform the actual merge operation."""
        if len(self.selected_elements) < 2:
            QMessageBox.warning(self, "Invalid Selection",
                              "Please select at least 2 elements to merge.")
            return
        
        # Get merge options
        merge_options = self.get_merge_options()
        
        # Get metadata conflict resolutions
        conflict_resolutions = self.metadata_resolver.get_resolutions()
        merge_options.update(conflict_resolutions)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        # Emit merge request
        self.merge_requested.emit(self.selected_elements, merge_options)
        
        # Close dialog
        QTimer.singleShot(500, self.accept)  # Small delay for visual feedback
    
    def get_selected_elements(self) -> List[Element]:
        """Get the currently selected elements for merging."""
        return self.selected_elements.copy()
    
    def get_merge_options(self) -> Dict[str, Any]:
        """Get the current merge configuration options."""
        separator_map = {
            "Single Space": " ",
            "Double Space": "  ", 
            "Newline": "\n",
            "Double Newline": "\n\n"
        }
        
        return {
            "separator": separator_map.get(self.separator_combo.currentText(), " "),
            "preserve_formatting": self.preserve_formatting.isChecked()
        }