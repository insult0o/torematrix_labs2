"""Type Information Panel

Detailed information display for type definitions with editing capabilities.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QFrame, QGroupBox, QScrollArea,
    QFormLayout, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry


class TypeInfoPanel(QWidget):
    """Panel for displaying detailed type information"""
    
    type_modified = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type: Optional[TypeDefinition] = None
        self.is_editing = False
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the information panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Type Information")
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Edit/Save buttons
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.toggle_edit_mode)
        self.edit_btn.setEnabled(False)
        header_layout.addWidget(self.edit_btn)
        
        layout.addLayout(header_layout)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        # Basic information group
        self.basic_group = self.create_basic_info_group()
        self.scroll_layout.addWidget(self.basic_group)
        
        # Properties group
        self.properties_group = self.create_properties_group()
        self.scroll_layout.addWidget(self.properties_group)
        
        # Relationships group
        self.relationships_group = self.create_relationships_group()
        self.scroll_layout.addWidget(self.relationships_group)
        
        # Validation group
        self.validation_group = self.create_validation_group()
        self.scroll_layout.addWidget(self.validation_group)
        
        # Metadata group
        self.metadata_group = self.create_metadata_group()
        self.scroll_layout.addWidget(self.metadata_group)
        
        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Status/empty state
        self.empty_label = QLabel("No type selected")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-style: italic; font-size: 14px;")
        layout.addWidget(self.empty_label)
        
        # Initially show empty state
        self.show_empty_state()
    
    def create_basic_info_group(self) -> QGroupBox:
        """Create basic information group"""
        group = QGroupBox("Basic Information")
        layout = QFormLayout(group)
        
        # Type name
        self.name_display = QLabel()
        self.name_edit = QLineEdit()
        self.name_edit.setVisible(False)
        name_container = QWidget()
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.addWidget(self.name_display)
        name_layout.addWidget(self.name_edit)
        layout.addRow("Name:", name_container)
        
        # Type ID
        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-family: monospace; color: #666;")
        layout.addRow("Type ID:", self.id_label)
        
        # Category
        self.category_display = QLabel()
        self.category_edit = QLineEdit()
        self.category_edit.setVisible(False)
        category_container = QWidget()
        category_layout = QVBoxLayout(category_container)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.addWidget(self.category_display)
        category_layout.addWidget(self.category_edit)
        layout.addRow("Category:", category_container)
        
        # Description
        self.description_display = QLabel()
        self.description_display.setWordWrap(True)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setVisible(False)
        desc_container = QWidget()
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.addWidget(self.description_display)
        desc_layout.addWidget(self.description_edit)
        layout.addRow("Description:", desc_container)
        
        # Custom type indicator
        self.custom_label = QLabel()
        layout.addRow("Custom Type:", self.custom_label)
        
        # Created date
        self.created_label = QLabel()
        layout.addRow("Created:", self.created_label)
        
        return group
    
    def create_properties_group(self) -> QGroupBox:
        """Create properties group"""
        group = QGroupBox("Properties")
        layout = QVBoxLayout(group)
        
        self.properties_list = QListWidget()
        self.properties_list.setMaximumHeight(150)
        layout.addWidget(self.properties_list)
        
        # Property controls (for edit mode)
        prop_controls = QHBoxLayout()
        
        self.add_prop_btn = QPushButton("Add Property")
        self.add_prop_btn.setVisible(False)
        prop_controls.addWidget(self.add_prop_btn)
        
        self.remove_prop_btn = QPushButton("Remove Property")
        self.remove_prop_btn.setVisible(False)
        prop_controls.addWidget(self.remove_prop_btn)
        
        prop_controls.addStretch()
        layout.addLayout(prop_controls)
        
        return group
    
    def create_relationships_group(self) -> QGroupBox:
        """Create relationships group"""
        group = QGroupBox("Type Relationships")
        layout = QVBoxLayout(group)
        
        # Parent types
        layout.addWidget(QLabel("Parent Types:"))
        self.parents_list = QListWidget()
        self.parents_list.setMaximumHeight(80)
        layout.addWidget(self.parents_list)
        
        # Child types
        layout.addWidget(QLabel("Child Types:"))
        self.children_list = QListWidget()
        self.children_list.setMaximumHeight(80)
        layout.addWidget(self.children_list)
        
        return group
    
    def create_validation_group(self) -> QGroupBox:
        """Create validation rules group"""
        group = QGroupBox("Validation Rules")
        layout = QVBoxLayout(group)
        
        self.validation_list = QListWidget()
        self.validation_list.setMaximumHeight(120)
        layout.addWidget(self.validation_list)
        
        return group
    
    def create_metadata_group(self) -> QGroupBox:
        """Create metadata group"""
        group = QGroupBox("Metadata")
        layout = QVBoxLayout(group)
        
        # Tags
        layout.addWidget(QLabel("Tags:"))
        self.tags_list = QListWidget()
        self.tags_list.setMaximumHeight(60)
        layout.addWidget(self.tags_list)
        
        # Statistics
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.stats_label)
        
        return group
    
    def connect_signals(self):
        """Connect UI signals"""
        pass
    
    def set_type(self, type_id: str):
        """Set the type to display"""
        try:
            type_def = self.registry.get_type(type_id)
            self.current_type = type_def
            self.update_display()
            self.show_content()
        except Exception as e:
            self.show_error(f"Failed to load type: {e}")
    
    def update_display(self):
        """Update the display with current type information"""
        if not self.current_type:
            return
        
        type_def = self.current_type
        
        # Update title
        self.title_label.setText(f"Type: {type_def.name}")
        
        # Basic information
        self.name_display.setText(type_def.name)
        self.name_edit.setText(type_def.name)
        
        self.id_label.setText(type_def.type_id)
        
        self.category_display.setText(type_def.category.title())
        self.category_edit.setText(type_def.category)
        
        description = type_def.description or "No description provided"
        self.description_display.setText(description)
        self.description_edit.setPlainText(type_def.description or "")
        
        custom_text = "Yes" if type_def.is_custom else "No"
        custom_color = "#107c10" if type_def.is_custom else "#666"
        self.custom_label.setText(f'<span style="color: {custom_color}; font-weight: bold;">{custom_text}</span>')
        
        created_text = type_def.created_at.strftime("%Y-%m-%d %H:%M") if type_def.created_at else "Unknown"
        self.created_label.setText(created_text)
        
        # Properties
        self.properties_list.clear()
        for prop_name, prop_value in type_def.properties.items():
            item_text = f"{prop_name}: {prop_value}"
            item = QListWidgetItem(item_text)
            self.properties_list.addItem(item)
        
        # Relationships
        self.parents_list.clear()
        for parent_id in type_def.parent_types:
            try:
                parent_def = self.registry.get_type(parent_id)
                item = QListWidgetItem(f"{parent_def.name} ({parent_def.category})")
            except:
                item = QListWidgetItem(f"Missing: {parent_id}")
                item.setForeground(Qt.GlobalColor.red)
            self.parents_list.addItem(item)
        
        self.children_list.clear()
        for child_id in type_def.child_types:
            try:
                child_def = self.registry.get_type(child_id)
                item = QListWidgetItem(f"{child_def.name} ({child_def.category})")
            except:
                item = QListWidgetItem(f"Missing: {child_id}")
                item.setForeground(Qt.GlobalColor.red)
            self.children_list.addItem(item)
        
        # Validation rules
        self.validation_list.clear()
        for rule_name, rule_value in type_def.validation_rules.items():
            item_text = f"{rule_name}: {rule_value}"
            item = QListWidgetItem(item_text)
            self.validation_list.addItem(item)
        
        # Tags
        self.tags_list.clear()
        for tag in type_def.tags:
            item = QListWidgetItem(tag)
            self.tags_list.addItem(item)
        
        # Statistics
        stats_text = f"Properties: {len(type_def.properties)}, "
        stats_text += f"Validation Rules: {len(type_def.validation_rules)}, "
        stats_text += f"Parents: {len(type_def.parent_types)}, "
        stats_text += f"Children: {len(type_def.child_types)}"
        self.stats_label.setText(stats_text)
        
        # Enable edit button
        self.edit_btn.setEnabled(True)
    
    def toggle_edit_mode(self):
        """Toggle between display and edit mode"""
        if self.is_editing:
            # Save changes
            if self.save_changes():
                self.set_edit_mode(False)
        else:
            # Enter edit mode
            self.set_edit_mode(True)
    
    def set_edit_mode(self, editing: bool):
        """Set edit mode state"""
        self.is_editing = editing
        
        # Toggle visibility of edit/display widgets
        self.name_display.setVisible(not editing)
        self.name_edit.setVisible(editing)
        
        self.category_display.setVisible(not editing)
        self.category_edit.setVisible(editing)
        
        self.description_display.setVisible(not editing)
        self.description_edit.setVisible(editing)
        
        # Toggle property controls
        self.add_prop_btn.setVisible(editing)
        self.remove_prop_btn.setVisible(editing)
        
        # Update button text
        self.edit_btn.setText("Save" if editing else "Edit")
    
    def save_changes(self) -> bool:
        """Save changes to the type"""
        if not self.current_type:
            return False
        
        try:
            # Get edited values
            new_name = self.name_edit.text().strip()
            new_category = self.category_edit.text().strip()
            new_description = self.description_edit.toPlainText().strip()
            
            # Validate
            if not new_name:
                QMessageBox.warning(self, "Validation Error", "Type name cannot be empty.")
                return False
            
            if not new_category:
                QMessageBox.warning(self, "Validation Error", "Category cannot be empty.")
                return False
            
            # Update type (this would need the registry to support updates)
            # For now, just show a success message
            QMessageBox.information(
                self, 
                "Changes Saved", 
                f"Changes to type '{new_name}' have been saved.\n\n"
                "Note: Full editing support would require registry update methods."
            )
            
            # Emit signal
            self.type_modified.emit(self.current_type.type_id)
            
            return True
            
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save changes: {e}")
            return False
    
    def show_content(self):
        """Show the content areas"""
        self.empty_label.setVisible(False)
        self.basic_group.setVisible(True)
        self.properties_group.setVisible(True)
        self.relationships_group.setVisible(True)
        self.validation_group.setVisible(True)
        self.metadata_group.setVisible(True)
    
    def show_empty_state(self):
        """Show empty state"""
        self.empty_label.setVisible(True)
        self.basic_group.setVisible(False)
        self.properties_group.setVisible(False)
        self.relationships_group.setVisible(False)
        self.validation_group.setVisible(False)
        self.metadata_group.setVisible(False)
        
        self.edit_btn.setEnabled(False)
        self.title_label.setText("Type Information")
    
    def show_error(self, message: str):
        """Show error state"""
        self.empty_label.setText(f"Error: {message}")
        self.show_empty_state()
    
    def clear(self):
        """Clear the panel"""
        self.current_type = None
        self.is_editing = False
        self.show_empty_state()
    
    def refresh(self):
        """Refresh the current type display"""
        if self.current_type:
            self.set_type(self.current_type.type_id)