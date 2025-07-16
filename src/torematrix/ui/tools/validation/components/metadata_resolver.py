"""
Metadata Conflict Resolver for Merge/Split Operations.

This module provides a sophisticated UI for resolving metadata conflicts
that arise during element merging and splitting operations.
"""

from typing import Dict, Any, List, Optional, Union
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QScrollArea, QFrame,
    QButtonGroup, QRadioButton, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from .....core.models import Element, ElementType


class ConflictPropertyWidget(QWidget):
    """Widget for resolving a single metadata property conflict."""
    
    resolution_changed = pyqtSignal(str, dict)  # property_name, resolution
    
    def __init__(self, property_name: str, conflict_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.property_name = property_name
        self.conflict_data = conflict_data
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the conflict resolution UI."""
        layout = QVBoxLayout(self)
        
        # Property header
        header_layout = QHBoxLayout()
        property_label = QLabel(f"Property: {self.property_name}")
        property_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(property_label)
        header_layout.addStretch()
        
        # Conflict indicator
        conflict_indicator = QLabel("⚠️ Conflict")
        conflict_indicator.setStyleSheet("color: #ff9800; font-weight: bold;")
        header_layout.addWidget(conflict_indicator)
        
        layout.addLayout(header_layout)
        
        # Values display
        values_group = QGroupBox("Conflicting Values")
        values_layout = QVBoxLayout(values_group)
        
        self.values_list = QTableWidget()
        self.values_list.setColumnCount(3)
        self.values_list.setHorizontalHeaderLabels(["Source", "Value", "Select"])
        self.values_list.horizontalHeader().setStretchLastSection(True)
        
        # Populate values
        values = self.conflict_data.get("values", [])
        self.values_list.setRowCount(len(values))
        
        self.value_buttons = QButtonGroup()
        for i, value in enumerate(values):
            # Source (element index or description)
            source_item = QTableWidgetItem(f"Element {i+1}")
            self.values_list.setItem(i, 0, source_item)
            
            # Value
            value_item = QTableWidgetItem(str(value))
            self.values_list.setItem(i, 1, value_item)
            
            # Selection radio button
            radio_button = QRadioButton()
            radio_button.setProperty("row", i)
            radio_button.setProperty("value", value)
            radio_button.toggled.connect(self.on_value_selected)
            self.value_buttons.addButton(radio_button)
            self.values_list.setCellWidget(i, 2, radio_button)
        
        values_layout.addWidget(self.values_list)
        layout.addWidget(values_group)
        
        # Resolution strategy
        strategy_group = QGroupBox("Resolution Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Use First Value",
            "Use Last Value", 
            "Use Most Common Value",
            "Concatenate Values",
            "Custom Value"
        ])
        
        # Set default strategy
        default_strategy = self.conflict_data.get("resolution", "Use First Value")
        index = self.strategy_combo.findText(default_strategy)
        if index >= 0:
            self.strategy_combo.setCurrentIndex(index)
        
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        
        # Custom value input (initially hidden)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom value...")
        self.custom_input.setVisible(False)
        self.custom_input.textChanged.connect(self.on_custom_value_changed)
        strategy_layout.addWidget(self.custom_input)
        
        layout.addWidget(strategy_group)
        
        # Initialize with default strategy
        self.on_strategy_changed(self.strategy_combo.currentText())
    
    def on_value_selected(self):
        """Handle value selection from radio buttons."""
        sender = self.sender()
        if sender.isChecked():
            value = sender.property("value")
            self.emit_resolution_change("selected_value", value)
    
    def on_strategy_changed(self, strategy: str):
        """Handle strategy change."""
        # Show/hide custom input
        self.custom_input.setVisible(strategy == "Custom Value")
        
        # Auto-select based on strategy
        if strategy == "Use First Value" and self.values_list.rowCount() > 0:
            self.value_buttons.button(0).setChecked(True)
        elif strategy == "Use Last Value" and self.values_list.rowCount() > 0:
            self.value_buttons.button(self.values_list.rowCount() - 1).setChecked(True)
        
        self.emit_resolution_change("strategy", strategy)
    
    def on_custom_value_changed(self, text: str):
        """Handle custom value change."""
        if self.strategy_combo.currentText() == "Custom Value":
            self.emit_resolution_change("custom_value", text)
    
    def emit_resolution_change(self, resolution_type: str, value: Any):
        """Emit resolution change signal."""
        resolution = {
            "strategy": self.strategy_combo.currentText(),
            "type": resolution_type,
            "value": value
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
            resolution["value"] = self.custom_input.text()
        else:
            # Get selected value from radio buttons
            for button in self.value_buttons.buttons():
                if button.isChecked():
                    resolution["value"] = button.property("value")
                    break
        
        return resolution


class MetadataInheritanceWidget(QWidget):
    """Widget for configuring metadata inheritance in split operations."""
    
    inheritance_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the inheritance configuration UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Metadata Inheritance")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        # Inheritance options
        options_group = QGroupBox("Inheritance Options")
        options_layout = QVBoxLayout(options_group)
        
        # Copy all metadata
        self.copy_all_checkbox = QCheckBox("Copy all metadata to new elements")
        self.copy_all_checkbox.setChecked(True)
        self.copy_all_checkbox.stateChanged.connect(self.on_inheritance_changed)
        options_layout.addWidget(self.copy_all_checkbox)
        
        # Preserve parent relationships
        self.preserve_parent_checkbox = QCheckBox("Preserve parent relationships")
        self.preserve_parent_checkbox.setChecked(True)
        self.preserve_parent_checkbox.stateChanged.connect(self.on_inheritance_changed)
        options_layout.addWidget(self.preserve_parent_checkbox)
        
        # Create element hierarchy
        self.create_hierarchy_checkbox = QCheckBox("Create parent-child hierarchy for split elements")
        self.create_hierarchy_checkbox.stateChanged.connect(self.on_inheritance_changed)
        options_layout.addWidget(self.create_hierarchy_checkbox)
        
        layout.addWidget(options_group)
        
        # Custom metadata rules
        rules_group = QGroupBox("Custom Rules")
        rules_layout = QVBoxLayout(rules_group)
        
        rules_help = QLabel(
            "Define custom rules for metadata inheritance. "
            "For example, you might want to update position coordinates for each split element."
        )
        rules_help.setWordWrap(True)
        rules_help.setStyleSheet("color: #666666; font-style: italic;")
        rules_layout.addWidget(rules_help)
        
        # Rules table (simplified)
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(2)
        self.rules_table.setHorizontalHeaderLabels(["Property", "Rule"])
        self.rules_table.setMaximumHeight(100)
        rules_layout.addWidget(self.rules_table)
        
        layout.addWidget(rules_group)
    
    def on_inheritance_changed(self):
        """Handle inheritance option changes."""
        config = self.get_inheritance_config()
        self.inheritance_changed.emit(config)
    
    def get_inheritance_config(self) -> Dict[str, Any]:
        """Get the current inheritance configuration."""
        return {
            "copy_all_metadata": self.copy_all_checkbox.isChecked(),
            "preserve_parent": self.preserve_parent_checkbox.isChecked(),
            "create_hierarchy": self.create_hierarchy_checkbox.isChecked(),
            "custom_rules": []  # Could be extended for custom rules
        }


class MetadataConflictResolver(QWidget):
    """
    Comprehensive metadata conflict resolver for merge/split operations.
    
    Provides sophisticated UI for resolving conflicts and configuring
    metadata inheritance policies.
    """
    
    resolutions_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._conflicts: Dict[str, Dict[str, Any]] = {}
        self._resolutions: Dict[str, Dict[str, Any]] = {}
        self._inheritance_config: Dict[str, Any] = {}
    
    def setup_ui(self):
        """Set up the main resolver UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Metadata Conflict Resolution")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.conflict_count_label = QLabel("No conflicts")
        self.conflict_count_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        header_layout.addWidget(self.conflict_count_label)
        
        layout.addLayout(header_layout)
        
        # Scroll area for conflicts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.conflicts_container = QWidget()
        self.conflicts_layout = QVBoxLayout(self.conflicts_container)
        self.conflicts_layout.addStretch()  # Add stretch at the end
        
        scroll_area.setWidget(self.conflicts_container)
        layout.addWidget(scroll_area)
        
        # Inheritance configuration (for split operations)
        self.inheritance_widget = MetadataInheritanceWidget()
        self.inheritance_widget.inheritance_changed.connect(self.on_inheritance_changed)
        self.inheritance_widget.setVisible(False)  # Initially hidden
        layout.addWidget(self.inheritance_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.auto_resolve_button = QPushButton("Auto-Resolve All")
        self.auto_resolve_button.clicked.connect(self.auto_resolve_conflicts)
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_resolutions)
        
        button_layout.addWidget(self.auto_resolve_button)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
    
    def set_conflicts(self, conflicts: Dict[str, Dict[str, Any]]):
        """Set metadata conflicts to resolve."""
        self._conflicts = conflicts
        self.update_conflicts_display()
    
    def clear_conflicts(self):
        """Clear all conflicts."""
        self._conflicts = {}
        self._resolutions = {}
        self.update_conflicts_display()
    
    def update_conflicts_display(self):
        """Update the conflicts display."""
        # Clear existing widgets
        for i in reversed(range(self.conflicts_layout.count() - 1)):  # -1 to keep stretch
            child = self.conflicts_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Update header
        conflict_count = len(self._conflicts)
        if conflict_count == 0:
            self.conflict_count_label.setText("No conflicts")
            self.conflict_count_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.auto_resolve_button.setEnabled(False)
            self.reset_button.setEnabled(False)
        else:
            self.conflict_count_label.setText(f"{conflict_count} conflict{'s' if conflict_count != 1 else ''}")
            self.conflict_count_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            self.auto_resolve_button.setEnabled(True)
            self.reset_button.setEnabled(True)
        
        # Add conflict widgets
        for property_name, conflict_data in self._conflicts.items():
            conflict_widget = ConflictPropertyWidget(property_name, conflict_data)
            conflict_widget.resolution_changed.connect(self.on_resolution_changed)
            
            # Add separator frame
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("color: #e0e0e0;")
            
            self.conflicts_layout.insertWidget(self.conflicts_layout.count() - 1, conflict_widget)
            self.conflicts_layout.insertWidget(self.conflicts_layout.count() - 1, separator)
    
    def on_resolution_changed(self, property_name: str, resolution: Dict[str, Any]):
        """Handle resolution change for a property."""
        self._resolutions[property_name] = resolution
        self.resolutions_changed.emit(self._resolutions)
    
    def on_inheritance_changed(self, config: Dict[str, Any]):
        """Handle inheritance configuration change."""
        self._inheritance_config = config
        self.resolutions_changed.emit(self.get_all_resolutions())
    
    def auto_resolve_conflicts(self):
        """Auto-resolve all conflicts using default strategies."""
        for property_name, conflict_data in self._conflicts.items():
            # Use "Use First Value" as default strategy
            if "values" in conflict_data and conflict_data["values"]:
                resolution = {
                    "strategy": "Use First Value",
                    "type": "auto_resolved",
                    "value": conflict_data["values"][0],
                    "property": property_name
                }
                self._resolutions[property_name] = resolution
        
        # Update display and emit changes
        self.update_conflicts_display()
        self.resolutions_changed.emit(self._resolutions)
    
    def reset_resolutions(self):
        """Reset all resolutions to defaults."""
        self._resolutions = {}
        self._inheritance_config = {}
        self.inheritance_widget.copy_all_checkbox.setChecked(True)
        self.inheritance_widget.preserve_parent_checkbox.setChecked(True)
        self.inheritance_widget.create_hierarchy_checkbox.setChecked(False)
        
        self.update_conflicts_display()
        self.resolutions_changed.emit(self._resolutions)
    
    def get_resolutions(self) -> Dict[str, Any]:
        """Get current conflict resolutions."""
        return self._resolutions.copy()
    
    def get_inheritance_config(self) -> Dict[str, Any]:
        """Get current inheritance configuration."""
        return self._inheritance_config.copy()
    
    def get_all_resolutions(self) -> Dict[str, Any]:
        """Get all resolutions including inheritance config."""
        all_resolutions = self._resolutions.copy()
        all_resolutions["inheritance"] = self._inheritance_config
        return all_resolutions
    
    def set_operation_mode(self, mode: str):
        """Set the operation mode (merge or split) to show relevant options."""
        if mode == "split":
            self.inheritance_widget.setVisible(True)
            self.title_label.setText("Metadata Conflict Resolution & Inheritance")
        else:
            self.inheritance_widget.setVisible(False)
            self.title_label.setText("Metadata Conflict Resolution")
    
    def has_unresolved_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self._conflicts) > len(self._resolutions)
    
    def validate_resolutions(self) -> List[str]:
        """Validate current resolutions and return warnings."""
        warnings = []
        
        for property_name, conflict_data in self._conflicts.items():
            if property_name not in self._resolutions:
                warnings.append(f"Unresolved conflict for property: {property_name}")
            else:
                resolution = self._resolutions[property_name]
                if resolution.get("strategy") == "Custom Value" and not resolution.get("value"):
                    warnings.append(f"Custom value not specified for property: {property_name}")
        
        return warnings