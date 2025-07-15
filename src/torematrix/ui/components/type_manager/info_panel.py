"""Type Information Panel

Detailed type information display with properties, validation rules, and metadata.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QScrollArea, QFrame, QGroupBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from torematrix.core.models.types import get_type_registry, TypeRegistry, TypeDefinition


class TypeInfoPanel(QWidget):
    """Type information display panel"""
    
    edit_requested = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type_id: Optional[str] = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.type_name_label = QLabel("No type selected")
        self.type_name_label.setFont(QFont("", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.type_name_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.content_layout = QVBoxLayout(scroll_widget)
        
        # Basic info group
        self.basic_info_group = QGroupBox("Basic Information")
        self.basic_info_layout = QVBoxLayout(self.basic_info_group)
        self.content_layout.addWidget(self.basic_info_group)
        
        # Properties group
        self.properties_group = QGroupBox("Properties")
        self.properties_layout = QVBoxLayout(self.properties_group)
        self.content_layout.addWidget(self.properties_group)
        
        # Validation group
        self.validation_group = QGroupBox("Validation Rules")
        self.validation_layout = QVBoxLayout(self.validation_group)
        self.content_layout.addWidget(self.validation_group)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
    
    def display_type(self, type_id: str):
        """Display information for specified type"""
        self.current_type_id = type_id
        
        try:
            type_def = self.registry.get_type(type_id)
            self._update_display(type_def)
        except Exception as e:
            self._show_error(f"Error loading type: {e}")
    
    def _update_display(self, type_def: TypeDefinition):
        """Update display with type definition"""
        # Update header
        self.type_name_label.setText(type_def.name)
        
        # Clear existing content
        self._clear_layout(self.basic_info_layout)
        self._clear_layout(self.properties_layout)
        self._clear_layout(self.validation_layout)
        
        # Basic info
        self._add_info_item(self.basic_info_layout, "ID", type_def.type_id)
        self._add_info_item(self.basic_info_layout, "Category", type_def.category)
        self._add_info_item(self.basic_info_layout, "Description", type_def.description)
        
        # Properties
        for prop_name, prop_config in type_def.properties.items():
            self._add_info_item(self.properties_layout, prop_name, str(prop_config))
        
        # Validation rules
        for rule_name, rule_config in type_def.validation_rules.items():
            self._add_info_item(self.validation_layout, rule_name, str(rule_config))
    
    def _add_info_item(self, layout, label: str, value: str):
        """Add info item to layout"""
        item_layout = QHBoxLayout()
        
        label_widget = QLabel(f"{label}:")
        label_widget.setFont(QFont("", 9, QFont.Weight.Bold))
        label_widget.setMinimumWidth(100)
        item_layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setWordWrap(True)
        item_layout.addWidget(value_widget, 1)
        
        layout.addLayout(item_layout)
    
    def _clear_layout(self, layout):
        """Clear all items from layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _show_error(self, message: str):
        """Show error message"""
        self.type_name_label.setText("Error")
        self._clear_layout(self.basic_info_layout)
        self._add_info_item(self.basic_info_layout, "Error", message)