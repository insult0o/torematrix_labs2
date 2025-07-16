"""
Metadata Conflict Resolver Component for Agent 2 - Issue #235.

This module provides UI components for resolving metadata conflicts
during merge/split operations with inheritance options.
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QLineEdit, QCheckBox, QGroupBox, QPushButton,
    QScrollArea, QFrame, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette


class ConflictPropertyWidget(QWidget):
    """Widget for resolving a single metadata property conflict."""
    
    resolution_changed = pyqtSignal(str, dict)  # property_name, resolution
    
    def __init__(self, property_name: str, conflict_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.property_name = property_name
        self.conflict_data = conflict_data
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the conflict resolution UI."""
        layout = QVBoxLayout(self)
        
        # Property header
        header_layout = QHBoxLayout()
        
        title_label = QLabel(f"Property: {self.property_name}")
        title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Conflicting values
        values_group = QGroupBox("Conflicting Values")
        values_layout = QVBoxLayout(values_group)
        
        self.values_list = QListWidget()
        self.values_list.setMaximumHeight(80)
        
        values = self.conflict_data.get("values", [])
        for i, value in enumerate(values):
            item = QListWidgetItem(f"{i+1}. {str(value)}")
            self.values_list.addItem(item)
            
        values_layout.addWidget(self.values_list)
        layout.addWidget(values_group)
        
        # Resolution strategy
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("Resolution:"))
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Use First Value",
            "Use Last Value", 
            "Use Most Common Value",
            "Concatenate All Values",
            "Custom Value"
        ])
        
        # Set current resolution if available
        current_resolution = self.conflict_data.get("resolution", "Use First Value")
        self.strategy_combo.setCurrentText(current_resolution)
        
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        
        layout.addLayout(strategy_layout)
        
        # Custom value input (initially hidden)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom value...")
        self.custom_input.setVisible(False)
        self.custom_input.textChanged.connect(self.on_custom_value_changed)
        layout.addWidget(self.custom_input)
        
    def on_strategy_changed(self, strategy: str):
        """Handle strategy change."""
        self.custom_input.setVisible(strategy == "Custom Value")
        
        resolution = {
            "strategy": strategy,
            "property": self.property_name
        }
        
        if strategy == "Custom Value":
            resolution["custom_value"] = self.custom_input.text()
            
        self.resolution_changed.emit(self.property_name, resolution)
        
    def on_custom_value_changed(self, value: str):
        """Handle custom value change."""
        if self.strategy_combo.currentText() == "Custom Value":
            resolution = {
                "strategy": "Custom Value",
                "property": self.property_name,
                "custom_value": value
            }
            self.resolution_changed.emit(self.property_name, resolution)
            
    def get_resolution(self) -> Dict[str, Any]:
        """Get the current resolution configuration."""
        strategy = self.strategy_combo.currentText()
        resolution = {
            "strategy": strategy,
            "property": self.property_name
        }
        
        if strategy == "Custom Value":
            resolution["custom_value"] = self.custom_input.text()
            
        return resolution


class MetadataInheritanceWidget(QWidget):
    """Widget for configuring metadata inheritance in split operations."""
    
    inheritance_changed = pyqtSignal(dict)  # inheritance config
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the inheritance configuration UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Metadata Inheritance Configuration")
        title_label.setFont(QFont("", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Inheritance options
        self.copy_all_checkbox = QCheckBox("Copy all metadata to new elements")
        self.copy_all_checkbox.setChecked(True)
        self.copy_all_checkbox.toggled.connect(self.on_inheritance_changed)
        layout.addWidget(self.copy_all_checkbox)
        
        self.preserve_parent_checkbox = QCheckBox("Preserve parent relationships")
        self.preserve_parent_checkbox.setChecked(True)
        self.preserve_parent_checkbox.toggled.connect(self.on_inheritance_changed)
        layout.addWidget(self.preserve_parent_checkbox)
        
        self.create_hierarchy_checkbox = QCheckBox("Create hierarchical relationship with original")
        self.create_hierarchy_checkbox.toggled.connect(self.on_inheritance_changed)
        layout.addWidget(self.create_hierarchy_checkbox)
        
        # Description
        desc_text = QTextEdit()
        desc_text.setMaximumHeight(60)
        desc_text.setReadOnly(True)
        desc_text.setPlainText(
            "Configure how metadata is inherited by new elements created during split operations."
        )
        layout.addWidget(desc_text)
        
    def on_inheritance_changed(self):
        """Handle inheritance configuration change."""
        config = self.get_inheritance_config()
        self.inheritance_changed.emit(config)
        
    def get_inheritance_config(self) -> Dict[str, Any]:
        """Get the current inheritance configuration."""
        return {
            "copy_all_metadata": self.copy_all_checkbox.isChecked(),
            "preserve_parent": self.preserve_parent_checkbox.isChecked(),
            "create_hierarchy": self.create_hierarchy_checkbox.isChecked()
        }


class MetadataConflictResolver(QWidget):
    """Main metadata conflict resolver widget."""
    
    conflicts_resolved = pyqtSignal(dict)  # all resolutions
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._conflicts = {}
        self._resolutions = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the conflict resolver UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Metadata Conflicts")
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("No conflicts")
        self.status_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Conflicts scroll area
        self.conflicts_scroll = QScrollArea()
        self.conflicts_scroll.setWidgetResizable(True)
        self.conflicts_scroll.setVisible(False)
        
        self.conflicts_widget = QWidget()
        self.conflicts_layout = QVBoxLayout(self.conflicts_widget)
        self.conflicts_scroll.setWidget(self.conflicts_widget)
        
        layout.addWidget(self.conflicts_scroll)
        
        # Auto-resolve button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.auto_resolve_button = QPushButton("Auto-Resolve All")
        self.auto_resolve_button.clicked.connect(self.auto_resolve_conflicts)
        self.auto_resolve_button.setVisible(False)
        button_layout.addWidget(self.auto_resolve_button)
        
        layout.addLayout(button_layout)
        
        # Inheritance widget (for split operations)
        self.inheritance_widget = MetadataInheritanceWidget()
        self.inheritance_widget.setVisible(False)
        self.inheritance_widget.inheritance_changed.connect(self.on_inheritance_changed)
        layout.addWidget(self.inheritance_widget)
        
        layout.addStretch()
        
    def set_conflicts(self, conflicts: Dict[str, Dict[str, Any]]):
        """Set metadata conflicts to resolve."""
        self._conflicts = conflicts
        self._resolutions.clear()
        
        # Clear existing conflict widgets
        for i in reversed(range(self.conflicts_layout.count())):
            child = self.conflicts_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                
        # Create widgets for each conflict
        if conflicts:
            for property_name, conflict_data in conflicts.items():
                conflict_widget = ConflictPropertyWidget(property_name, conflict_data)
                conflict_widget.resolution_changed.connect(self.on_resolution_changed)
                self.conflicts_layout.addWidget(conflict_widget)
                
                # Add separator
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                self.conflicts_layout.addWidget(separator)
                
        # Update UI state
        self.update_status()
        
    def clear_conflicts(self):
        """Clear all conflicts."""
        self.set_conflicts({})
        
    def update_status(self):
        """Update the status display."""
        conflict_count = len(self._conflicts)
        
        if conflict_count == 0:
            self.status_label.setText("No conflicts")
            self.conflicts_scroll.setVisible(False)
            self.auto_resolve_button.setVisible(False)
        else:
            self.status_label.setText(f"{conflict_count} conflict{'s' if conflict_count != 1 else ''}")
            self.conflicts_scroll.setVisible(True)
            self.auto_resolve_button.setVisible(True)
            
    def on_resolution_changed(self, property_name: str, resolution: Dict[str, Any]):
        """Handle resolution change for a property."""
        self._resolutions[property_name] = resolution
        self.conflicts_resolved.emit(self._resolutions)
        
    def on_inheritance_changed(self, config: Dict[str, Any]):
        """Handle inheritance configuration change."""
        # Include inheritance config in resolutions
        self._resolutions["_inheritance"] = config
        self.conflicts_resolved.emit(self._resolutions)
        
    def auto_resolve_conflicts(self):
        """Auto-resolve all conflicts using default strategies."""
        for property_name, conflict_data in self._conflicts.items():
            # Use "Use First Value" as default strategy
            resolution = {
                "strategy": "Use First Value",
                "property": property_name
            }
            self._resolutions[property_name] = resolution
            
        # Update UI to reflect auto-resolutions
        self.conflicts_resolved.emit(self._resolutions)
        
        # Update widgets to show selected strategies
        for i in range(self.conflicts_layout.count()):
            widget = self.conflicts_layout.itemAt(i).widget()
            if isinstance(widget, ConflictPropertyWidget):
                widget.strategy_combo.setCurrentText("Use First Value")
                
    def has_unresolved_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self._conflicts) > len(self._resolutions)
        
    def get_resolutions(self) -> Dict[str, Any]:
        """Get all current resolutions."""
        return self._resolutions.copy()
        
    def set_operation_mode(self, mode: str):
        """Set the operation mode (merge/split) to show appropriate options."""
        if mode == "split":
            self.inheritance_widget.setVisible(True)
            self.title_label.setText("Metadata Conflicts & Inheritance")
        else:
            self.inheritance_widget.setVisible(False)
            self.title_label.setText("Metadata Conflicts")