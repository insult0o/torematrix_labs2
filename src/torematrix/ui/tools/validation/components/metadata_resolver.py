"""
Metadata Conflict Resolver Component.

This module provides UI components for resolving metadata conflicts
during merge/split operations and managing inheritance settings.
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QPushButton, QScrollArea, QFrame,
    QCheckBox, QRadioButton, QButtonGroup, QListWidget,
    QListWidgetItem, QTextEdit, QSpinBox
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
        """Set up the conflict resolution widget UI."""
        layout = QVBoxLayout(self)
        
        # Property header
        header_layout = QHBoxLayout()
        
        property_label = QLabel(f"Property: {self.property_name}")
        property_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(property_label)
        
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
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.values_list.addItem(item)
        
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
        
        # Set default resolution
        default_resolution = self.conflict_data.get("resolution", "Use First Value")
        if default_resolution in [self.strategy_combo.itemText(i) for i in range(self.strategy_combo.count())]:
            self.strategy_combo.setCurrentText(default_resolution)
        
        strategy_layout.addWidget(self.strategy_combo)
        
        # Custom value input (initially hidden)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom value...")
        self.custom_input.setVisible(False)
        strategy_layout.addWidget(self.custom_input)
        
        layout.addWidget(strategy_group)
        
        # Connect signals
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        self.custom_input.textChanged.connect(self.on_custom_value_changed)
    
    def on_strategy_changed(self, strategy: str):
        """Handle strategy change."""
        # Show/hide custom input
        is_custom = strategy == "Custom Value"
        self.custom_input.setVisible(is_custom)
        
        # Emit resolution change
        resolution = self.get_resolution()
        self.resolution_changed.emit(self.property_name, resolution)
    
    def on_custom_value_changed(self, value: str):
        """Handle custom value change."""
        if self.strategy_combo.currentText() == "Custom Value":
            resolution = self.get_resolution()
            self.resolution_changed.emit(self.property_name, resolution)
    
    def get_resolution(self) -> Dict[str, Any]:
        """Get the current resolution configuration."""
        strategy = self.strategy_combo.currentText()
        
        resolution = {
            "property": self.property_name,
            "strategy": strategy,
            "values": self.conflict_data.get("values", [])
        }
        
        if strategy == "Custom Value":
            resolution["custom_value"] = self.custom_input.text()
        
        return resolution


class MetadataInheritanceWidget(QWidget):
    """Widget for configuring metadata inheritance settings."""
    
    inheritance_changed = pyqtSignal(dict)  # inheritance_config
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the inheritance widget UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Metadata Inheritance")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        # Copy options
        copy_group = QGroupBox("Copy Settings")
        copy_layout = QVBoxLayout(copy_group)
        
        self.copy_all_checkbox = QCheckBox("Copy all metadata from original element")
        self.copy_all_checkbox.setChecked(True)
        copy_layout.addWidget(self.copy_all_checkbox)
        
        self.preserve_parent_checkbox = QCheckBox("Preserve parent relationships")
        self.preserve_parent_checkbox.setChecked(True)
        copy_layout.addWidget(self.preserve_parent_checkbox)
        
        self.copy_position_checkbox = QCheckBox("Copy position information (bbox, page)")
        self.copy_position_checkbox.setChecked(False)
        copy_layout.addWidget(self.copy_position_checkbox)
        
        layout.addWidget(copy_group)
        
        # Hierarchy options
        hierarchy_group = QGroupBox("Hierarchy Settings")
        hierarchy_layout = QVBoxLayout(hierarchy_group)
        
        self.create_hierarchy_checkbox = QCheckBox("Create parent-child hierarchy for new elements")
        hierarchy_layout.addWidget(self.create_hierarchy_checkbox)
        
        self.maintain_order_checkbox = QCheckBox("Maintain original element order")
        self.maintain_order_checkbox.setChecked(True)
        hierarchy_layout.addWidget(self.maintain_order_checkbox)
        
        layout.addWidget(hierarchy_group)
        
        # Connect signals
        self.copy_all_checkbox.stateChanged.connect(self.on_inheritance_changed)
        self.preserve_parent_checkbox.stateChanged.connect(self.on_inheritance_changed)
        self.copy_position_checkbox.stateChanged.connect(self.on_inheritance_changed)
        self.create_hierarchy_checkbox.stateChanged.connect(self.on_inheritance_changed)
        self.maintain_order_checkbox.stateChanged.connect(self.on_inheritance_changed)
    
    def on_inheritance_changed(self):
        """Handle inheritance setting changes."""
        config = self.get_inheritance_config()
        self.inheritance_changed.emit(config)
    
    def get_inheritance_config(self) -> Dict[str, Any]:
        """Get the current inheritance configuration."""
        return {
            "copy_all_metadata": self.copy_all_checkbox.isChecked(),
            "preserve_parent": self.preserve_parent_checkbox.isChecked(),
            "copy_position": self.copy_position_checkbox.isChecked(),
            "create_hierarchy": self.create_hierarchy_checkbox.isChecked(),
            "maintain_order": self.maintain_order_checkbox.isChecked()
        }


class MetadataConflictResolver(QWidget):
    """
    Main metadata conflict resolver widget.
    
    Provides interface for resolving metadata conflicts during merge/split
    operations and configuring inheritance settings.
    """
    
    conflicts_resolved = pyqtSignal(dict)  # all_resolutions
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._conflicts: Dict[str, Dict[str, Any]] = {}
        self._resolutions: Dict[str, Dict[str, Any]] = {}
        self._operation_mode: str = "merge"
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main resolver widget UI."""
        layout = QVBoxLayout(self)
        
        # Header
        self.title_label = QLabel("Metadata Conflict Resolution")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        # Status
        self.status_label = QLabel("No conflicts detected")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Conflicts scroll area
        self.warnings_scroll = QScrollArea()
        self.warnings_scroll.setWidgetResizable(True)
        self.warnings_scroll.setMaximumHeight(200)
        self.warnings_scroll.setVisible(False)
        
        self.conflicts_widget = QWidget()
        self.conflicts_layout = QVBoxLayout(self.conflicts_widget)
        self.warnings_scroll.setWidget(self.conflicts_widget)
        
        layout.addWidget(self.warnings_scroll)
        
        # Inheritance settings (for split operations)
        self.inheritance_widget = MetadataInheritanceWidget()
        self.inheritance_widget.setVisible(False)
        layout.addWidget(self.inheritance_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.auto_resolve_button = QPushButton("Auto Resolve All")
        self.auto_resolve_button.clicked.connect(self.auto_resolve_conflicts)
        button_layout.addWidget(self.auto_resolve_button)
        
        self.clear_resolutions_button = QPushButton("Clear Resolutions")
        self.clear_resolutions_button.clicked.connect(self.clear_resolutions)
        button_layout.addWidget(self.clear_resolutions_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Connect inheritance signal
        self.inheritance_widget.inheritance_changed.connect(self.on_inheritance_changed)
    
    def set_conflicts(self, conflicts: Dict[str, Dict[str, Any]]):
        """Set the metadata conflicts to resolve."""
        self._conflicts = conflicts
        self._resolutions.clear()
        
        # Clear existing conflict widgets
        for i in reversed(range(self.conflicts_layout.count())):
            child = self.conflicts_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not conflicts:
            self.status_label.setText("No conflicts detected")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.warnings_scroll.setVisible(False)
            self.auto_resolve_button.setEnabled(False)
            self.clear_resolutions_button.setEnabled(False)
            return
        
        # Update status
        conflict_count = len(conflicts)
        self.status_label.setText(f"{conflict_count} conflict{'s' if conflict_count != 1 else ''} detected")
        self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.warnings_scroll.setVisible(True)
        self.auto_resolve_button.setEnabled(True)
        
        # Create conflict widgets
        for property_name, conflict_data in conflicts.items():
            conflict_widget = ConflictPropertyWidget(property_name, conflict_data)
            conflict_widget.resolution_changed.connect(self.on_resolution_changed)
            
            # Add separator
            if self.conflicts_layout.count() > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                self.conflicts_layout.addWidget(separator)
            
            self.conflicts_layout.addWidget(conflict_widget)
    
    def clear_conflicts(self):
        """Clear all conflicts."""
        self.set_conflicts({})
    
    def set_operation_mode(self, mode: str):
        """Set the operation mode (merge/split) to show appropriate options."""
        self._operation_mode = mode
        
        if mode == "split":
            self.title_label.setText("Metadata Inheritance & Conflicts")
            self.inheritance_widget.setVisible(True)
        else:
            self.title_label.setText("Metadata Conflict Resolution")
            self.inheritance_widget.setVisible(False)
    
    def auto_resolve_conflicts(self):
        """Automatically resolve all conflicts using default strategies."""
        for property_name, conflict_data in self._conflicts.items():
            resolution = {
                "property": property_name,
                "strategy": "Use First Value",
                "values": conflict_data.get("values", [])
            }
            self._resolutions[property_name] = resolution
        
        # Update status
        if self._conflicts:
            self.status_label.setText("All conflicts auto-resolved")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.clear_resolutions_button.setEnabled(True)
        
        # Emit signal
        self.conflicts_resolved.emit(self.get_resolutions())
    
    def clear_resolutions(self):
        """Clear all conflict resolutions."""
        self._resolutions.clear()
        
        if self._conflicts:
            conflict_count = len(self._conflicts)
            self.status_label.setText(f"{conflict_count} conflict{'s' if conflict_count != 1 else ''} detected")
            self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        
        self.clear_resolutions_button.setEnabled(False)
        self.conflicts_resolved.emit({})
    
    def on_resolution_changed(self, property_name: str, resolution: Dict[str, Any]):
        """Handle individual conflict resolution changes."""
        self._resolutions[property_name] = resolution
        
        # Update status if all conflicts are resolved
        if len(self._resolutions) == len(self._conflicts) and self._conflicts:
            self.status_label.setText("All conflicts resolved")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.clear_resolutions_button.setEnabled(True)
        
        # Emit signal
        self.conflicts_resolved.emit(self.get_resolutions())
    
    def on_inheritance_changed(self, config: Dict[str, Any]):
        """Handle inheritance configuration changes."""
        # Inheritance settings are included in the overall resolution
        pass
    
    def has_unresolved_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self._resolutions) < len(self._conflicts)
    
    def get_resolutions(self) -> Dict[str, Any]:
        """Get all conflict resolutions and inheritance settings."""
        resolutions = {
            "conflicts": self._resolutions.copy()
        }
        
        if self._operation_mode == "split":
            resolutions["inheritance"] = self.inheritance_widget.get_inheritance_config()
        
        return resolutions
    
    def get_conflict_count(self) -> int:
        """Get the number of conflicts."""
        return len(self._conflicts)
    
    def is_all_resolved(self) -> bool:
        """Check if all conflicts are resolved."""
        return not self.has_unresolved_conflicts()