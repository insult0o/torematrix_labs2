"""Main Property Panel Widget

The central property panel widget that displays and allows editing of
document element properties. This serves as the main interface for
property management.
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QLineEdit, QComboBox, QPushButton, QGroupBox, QSplitter,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QTableWidget, QTableWidgetItem, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon


class PropertyPanel(QWidget):
    """Main property panel widget for element property management"""
    
    # Signals
    selection_changed = pyqtSignal(list)  # element_ids
    properties_modified = pyqtSignal(str, dict)  # element_id, properties
    property_value_changed = pyqtSignal(str, str, object)  # element_id, property_name, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_elements: List[str] = []
        self.property_data: Dict[str, Dict[str, Any]] = {}
        self.property_editors: Dict[str, QWidget] = {}
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        
        # Update timer for delayed updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._delayed_update)
        self.update_timer.setSingleShot(True)
    
    def _setup_ui(self) -> None:
        """Setup the property panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header section
        header_widget = self._create_header()
        layout.addWidget(header_widget)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # No selection view
        no_selection = QLabel("No elements selected")
        no_selection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_selection.setStyleSheet("color: gray; font-style: italic;")
        self.content_stack.addWidget(no_selection)
        
        # Single element view
        self.single_element_widget = self._create_single_element_view()
        self.content_stack.addWidget(self.single_element_widget)
        
        # Multiple element view
        self.multiple_element_widget = self._create_multiple_element_view()
        self.content_stack.addWidget(self.multiple_element_widget)
        
        layout.addWidget(self.content_stack)
        
        # Show no selection by default
        self.content_stack.setCurrentIndex(0)
    
    def _create_header(self) -> QWidget:
        """Create header section with selection info and controls"""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(header)
        
        # Selection info
        self.selection_label = QLabel("No selection")
        self.selection_label.setFont(QFont("", 9, QFont.Weight.Bold))
        layout.addWidget(self.selection_label)
        
        layout.addStretch()
        
        # Quick actions
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMaximumWidth(80)
        self.refresh_btn.clicked.connect(self.refresh_properties)
        layout.addWidget(self.refresh_btn)
        
        return header
    
    def _create_single_element_view(self) -> QWidget:
        """Create view for single element properties"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Element info
        self.element_info = QLabel()
        self.element_info.setFont(QFont("", 9, QFont.Weight.Bold))
        self.element_info.setStyleSheet("padding: 5px; background: #f0f0f0; border-radius: 3px;")
        layout.addWidget(self.element_info)
        
        # Properties scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Properties container
        self.properties_container = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_container)
        self.properties_layout.setContentsMargins(5, 5, 5, 5)
        self.properties_layout.addStretch()
        
        scroll.setWidget(self.properties_container)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_multiple_element_view(self) -> QWidget:
        """Create view for multiple element properties"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Multi-selection info
        self.multi_info = QLabel()
        self.multi_info.setFont(QFont("", 9, QFont.Weight.Bold))
        self.multi_info.setStyleSheet("padding: 5px; background: #e6f3ff; border-radius: 3px;")
        layout.addWidget(self.multi_info)
        
        # Tab widget for different views
        self.multi_tabs = QTabWidget()
        
        # Common properties tab
        self.common_props_widget = self._create_common_properties_view()
        self.multi_tabs.addTab(self.common_props_widget, "Common Properties")
        
        # Property comparison tab
        self.comparison_widget = self._create_property_comparison_view()
        self.multi_tabs.addTab(self.comparison_widget, "Compare Properties")
        
        # Batch editing tab
        self.batch_edit_widget = self._create_batch_editing_view()
        self.multi_tabs.addTab(self.batch_edit_widget, "Batch Edit")
        
        layout.addWidget(self.multi_tabs)
        
        return widget
    
    def _create_common_properties_view(self) -> QWidget:
        """Create view for common properties across selected elements"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.common_props_container = QWidget()
        self.common_props_layout = QVBoxLayout(self.common_props_container)
        self.common_props_layout.addStretch()
        
        scroll.setWidget(self.common_props_container)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_property_comparison_view(self) -> QWidget:
        """Create view for comparing properties across elements"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setAlternatingRowColors(True)
        self.comparison_table.setSortingEnabled(True)
        layout.addWidget(self.comparison_table)
        
        return widget
    
    def _create_batch_editing_view(self) -> QWidget:
        """Create view for batch editing operations"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Batch operations info
        info_label = QLabel("Select properties to modify across all selected elements:")
        info_label.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(info_label)
        
        # Batch editing controls
        self.batch_controls = QWidget()
        self.batch_layout = QVBoxLayout(self.batch_controls)
        self.batch_layout.addStretch()
        
        layout.addWidget(self.batch_controls)
        
        # Apply button
        apply_btn = QPushButton("Apply Changes to All Selected")
        apply_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        apply_btn.clicked.connect(self._apply_batch_changes)
        layout.addWidget(apply_btn)
        
        return widget
    
    def _setup_connections(self) -> None:
        """Setup signal connections"""
        pass
    
    def set_selected_elements(self, element_ids: List[str]) -> None:
        """Set the selected elements for property display"""
        self.selected_elements = element_ids
        self._update_selection_display()
        self._load_properties()
    
    def _update_selection_display(self) -> None:
        """Update the UI based on current selection"""
        count = len(self.selected_elements)
        
        if count == 0:
            self.selection_label.setText("No selection")
            self.content_stack.setCurrentIndex(0)
        elif count == 1:
            self.selection_label.setText(f"1 element selected")
            self.content_stack.setCurrentIndex(1)
            self._update_single_element_info()
        else:
            self.selection_label.setText(f"{count} elements selected")
            self.content_stack.setCurrentIndex(2)
            self._update_multiple_element_info()
    
    def _update_single_element_info(self) -> None:
        """Update info for single element selection"""
        if not self.selected_elements:
            return
        
        element_id = self.selected_elements[0]
        self.element_info.setText(f"Element: {element_id}")
    
    def _update_multiple_element_info(self) -> None:
        """Update info for multiple element selection"""
        count = len(self.selected_elements)
        self.multi_info.setText(f"{count} elements selected for batch operations")
    
    def _load_properties(self) -> None:
        """Load properties for selected elements"""
        # Clear existing property editors
        self._clear_property_editors()
        
        if not self.selected_elements:
            return
        
        # Load property data (would integrate with property manager)
        self._load_property_data()
        
        # Update property displays
        if len(self.selected_elements) == 1:
            self._display_single_element_properties()
        else:
            self._display_multiple_element_properties()
    
    def _load_property_data(self) -> None:
        """Load property data from property manager"""
        # This would integrate with the actual property manager
        # For now, create mock data
        self.property_data = {}
        
        for element_id in self.selected_elements:
            self.property_data[element_id] = {
                'type': f'Type_{element_id[-1]}',
                'content': f'Content for {element_id}',
                'x': 100 + hash(element_id) % 200,
                'y': 100 + hash(element_id) % 150,
                'width': 80 + hash(element_id) % 40,
                'height': 20 + hash(element_id) % 20,
                'confidence': 0.85 + (hash(element_id) % 15) / 100,
                'created': '2024-01-01',
                'modified': '2024-01-15'
            }
    
    def _display_single_element_properties(self) -> None:
        """Display properties for a single element"""
        if not self.selected_elements:
            return
        
        element_id = self.selected_elements[0]
        properties = self.property_data.get(element_id, {})
        
        # Create property groups
        self._create_property_group("Basic Properties", {
            'Type': properties.get('type', ''),
            'Content': properties.get('content', '')
        })
        
        self._create_property_group("Position & Size", {
            'X': properties.get('x', 0),
            'Y': properties.get('y', 0),
            'Width': properties.get('width', 0),
            'Height': properties.get('height', 0)
        })
        
        self._create_property_group("Metadata", {
            'Confidence': properties.get('confidence', 0.0),
            'Created': properties.get('created', ''),
            'Modified': properties.get('modified', '')
        })
    
    def _create_property_group(self, title: str, properties: Dict[str, Any]) -> None:
        """Create a group of property editors"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        for prop_name, prop_value in properties.items():
            editor_widget = self._create_property_editor(prop_name, prop_value)
            layout.addWidget(editor_widget)
        
        # Insert before stretch
        self.properties_layout.insertWidget(
            self.properties_layout.count() - 1, 
            group
        )
    
    def _create_property_editor(self, name: str, value: Any) -> QWidget:
        """Create an editor widget for a property"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        
        # Property label
        label = QLabel(f"{name}:")
        label.setMinimumWidth(80)
        layout.addWidget(label)
        
        # Property editor based on type
        if isinstance(value, bool):
            editor = QComboBox()
            editor.addItems(['False', 'True'])
            editor.setCurrentText(str(value))
        elif isinstance(value, (int, float)):
            editor = QLineEdit(str(value))
            editor.setMaximumWidth(100)
        elif isinstance(value, str):
            editor = QLineEdit(value)
        else:
            editor = QLineEdit(str(value))
        
        # Store editor reference
        self.property_editors[name] = editor
        
        # Connect change signal
        if hasattr(editor, 'textChanged'):
            editor.textChanged.connect(
                lambda text, prop=name: self._on_property_changed(prop, text)
            )
        elif hasattr(editor, 'currentTextChanged'):
            editor.currentTextChanged.connect(
                lambda text, prop=name: self._on_property_changed(prop, text)
            )
        
        layout.addWidget(editor)
        layout.addStretch()
        
        return container
    
    def _display_multiple_element_properties(self) -> None:
        """Display properties for multiple elements"""
        self._update_common_properties()
        self._update_property_comparison()
        self._update_batch_editing()
    
    def _update_common_properties(self) -> None:
        """Update common properties display"""
        # Clear existing
        self._clear_widget_layout(self.common_props_layout)
        
        # Find common properties
        common_props = self._find_common_properties()
        
        if not common_props:
            label = QLabel("No common properties found")
            label.setStyleSheet("color: gray; font-style: italic;")
            self.common_props_layout.addWidget(label)
        else:
            for prop_name, prop_value in common_props.items():
                editor = self._create_property_editor(prop_name, prop_value)
                self.common_props_layout.addWidget(editor)
        
        self.common_props_layout.addStretch()
    
    def _find_common_properties(self) -> Dict[str, Any]:
        """Find properties common to all selected elements"""
        if not self.selected_elements:
            return {}
        
        # Get properties from first element
        first_element = self.selected_elements[0]
        common_props = self.property_data.get(first_element, {}).copy()
        
        # Check against other elements
        for element_id in self.selected_elements[1:]:
            element_props = self.property_data.get(element_id, {})
            
            # Keep only properties that exist in this element with same value
            common_props = {
                key: value for key, value in common_props.items()
                if key in element_props and element_props[key] == value
            }
        
        return common_props
    
    def _update_property_comparison(self) -> None:
        """Update property comparison table"""
        if not self.selected_elements:
            return
        
        # Collect all unique property names
        all_props = set()
        for element_id in self.selected_elements:
            all_props.update(self.property_data.get(element_id, {}).keys())
        
        # Setup table
        self.comparison_table.setRowCount(len(all_props))
        self.comparison_table.setColumnCount(len(self.selected_elements) + 1)
        
        # Headers
        headers = ['Property'] + self.selected_elements
        self.comparison_table.setHorizontalHeaderLabels(headers)
        
        # Fill table
        for row, prop_name in enumerate(sorted(all_props)):
            # Property name column
            self.comparison_table.setItem(row, 0, QTableWidgetItem(prop_name))
            
            # Values for each element
            for col, element_id in enumerate(self.selected_elements, 1):
                properties = self.property_data.get(element_id, {})
                value = str(properties.get(prop_name, ''))
                item = QTableWidgetItem(value)
                
                # Highlight differences
                if col > 1:  # Compare with first element
                    first_value = str(self.property_data.get(
                        self.selected_elements[0], {}
                    ).get(prop_name, ''))
                    if value != first_value:
                        item.setBackground(Qt.GlobalColor.yellow)
                
                self.comparison_table.setItem(row, col, item)
        
        # Resize columns
        self.comparison_table.resizeColumnsToContents()
    
    def _update_batch_editing(self) -> None:
        """Update batch editing controls"""
        # Clear existing
        self._clear_widget_layout(self.batch_layout)
        
        # Get all unique properties
        all_props = set()
        for element_id in self.selected_elements:
            all_props.update(self.property_data.get(element_id, {}).keys())
        
        # Create batch edit controls for each property
        for prop_name in sorted(all_props):
            self._create_batch_property_editor(prop_name)
        
        self.batch_layout.addStretch()
    
    def _create_batch_property_editor(self, prop_name: str) -> None:
        """Create batch editing control for a property"""
        container = QWidget()
        layout = QHBoxLayout(container)
        
        # Enable checkbox
        enable_cb = QCheckBox(prop_name)
        enable_cb.setMinimumWidth(120)
        layout.addWidget(enable_cb)
        
        # Value editor
        editor = QLineEdit()
        editor.setEnabled(False)
        layout.addWidget(editor)
        
        # Connect checkbox to enable/disable editor
        enable_cb.toggled.connect(editor.setEnabled)
        
        # Store reference
        self.property_editors[f'batch_{prop_name}'] = {
            'enabled': enable_cb,
            'editor': editor
        }
        
        self.batch_layout.insertWidget(self.batch_layout.count() - 1, container)
    
    def _clear_property_editors(self) -> None:
        """Clear all property editors"""
        self.property_editors.clear()
        self._clear_widget_layout(self.properties_layout)
        self.properties_layout.addStretch()
    
    def _clear_widget_layout(self, layout: QVBoxLayout) -> None:
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _on_property_changed(self, property_name: str, value: str) -> None:
        """Handle property value change"""
        if self.selected_elements:
            element_id = self.selected_elements[0]
            
            # Convert value to appropriate type
            converted_value = self._convert_property_value(property_name, value)
            
            # Update property data
            if element_id in self.property_data:
                self.property_data[element_id][property_name] = converted_value
            
            # Emit signal
            self.property_value_changed.emit(element_id, property_name, converted_value)
            
            # Delayed update to avoid excessive updates
            self.update_timer.start(100)
    
    def _convert_property_value(self, property_name: str, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Try to convert to number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Check for boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Return as string
        return value
    
    def _apply_batch_changes(self) -> None:
        """Apply batch changes to all selected elements"""
        changes = {}
        
        # Collect enabled batch changes
        for key, editor_info in self.property_editors.items():
            if key.startswith('batch_') and isinstance(editor_info, dict):
                if editor_info['enabled'].isChecked():
                    prop_name = key[6:]  # Remove 'batch_' prefix
                    value = editor_info['editor'].text()
                    converted_value = self._convert_property_value(prop_name, value)
                    changes[prop_name] = converted_value
        
        if not changes:
            return
        
        # Apply to all selected elements
        for element_id in self.selected_elements:
            if element_id in self.property_data:
                self.property_data[element_id].update(changes)
                self.properties_modified.emit(element_id, changes)
        
        # Refresh display
        self.refresh_properties()
    
    def _delayed_update(self) -> None:
        """Handle delayed property updates"""
        # Emit properties modified signal
        if self.selected_elements:
            element_id = self.selected_elements[0]
            properties = self.property_data.get(element_id, {})
            self.properties_modified.emit(element_id, properties)
    
    def refresh_properties(self) -> None:
        """Refresh property display"""
        self._load_properties()
    
    def get_property_data(self) -> Dict[str, Dict[str, Any]]:
        """Get current property data"""
        return self.property_data.copy()
    
    def set_property_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Set property data"""
        self.property_data = data
        self._load_properties()