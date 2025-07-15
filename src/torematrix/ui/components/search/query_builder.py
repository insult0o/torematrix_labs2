"""
Visual Query Builder for Search and Filter System

Provides an intuitive drag-and-drop interface for building complex queries
with real-time preview and validation.
"""

import json
from typing import Dict, List, Set, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QFrame, QScrollArea,
    QGroupBox, QSplitter, QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QDialog, QDialogButtonBox, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QTimer
from PyQt6.QtGui import QDrag, QPainter, QPixmap, QFont, QPalette

from ....core.models.element import Element, ElementType
from .filters import (
    FilterManager, FilterSet, FilterGroup, FilterCondition,
    FilterType, FilterOperator, FilterLogic, FilterValue
)


class QueryBuilderMode(Enum):
    """Query builder interaction modes."""
    VISUAL = "visual"      # Drag-and-drop visual builder
    FORM = "form"         # Form-based builder
    TEXT = "text"         # Text-based DSL editor
    HYBRID = "hybrid"     # Combined visual and text


@dataclass
class QueryTemplate:
    """Predefined query template."""
    template_id: str
    name: str
    description: str
    filter_set: FilterSet
    category: str = "general"
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    tags: List[str] = field(default_factory=list)


class DraggableFilterWidget(QFrame):
    """Draggable widget representing a filter condition."""
    
    def __init__(self, filter_type: FilterType, parent=None):
        super().__init__(parent)
        self.filter_type = filter_type
        self.setup_ui()
        self.setFixedSize(120, 60)
        
    def setup_ui(self):
        """Setup the draggable filter UI."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
                border-radius: 8px;
                padding: 4px;
            }
            QFrame:hover {
                background-color: #bbdefb;
                border-color: #1976d2;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Filter type label
        type_label = QLabel(self.filter_type.value.replace("_", " ").title())
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        layout.addWidget(type_label)
        
        # Description
        desc_label = QLabel(self._get_filter_description())
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setFont(QFont("Arial", 7))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
    def _get_filter_description(self) -> str:
        """Get description for filter type."""
        descriptions = {
            FilterType.ELEMENT_TYPE: "Filter by element type",
            FilterType.TEXT_CONTENT: "Filter by text content",
            FilterType.CONFIDENCE: "Filter by confidence score",
            FilterType.PAGE_NUMBER: "Filter by page number",
            FilterType.DETECTION_METHOD: "Filter by detection method",
            FilterType.LANGUAGE: "Filter by language",
            FilterType.CUSTOM_FIELD: "Filter by custom field",
            FilterType.DATE_RANGE: "Filter by date range",
            FilterType.COORDINATE: "Filter by coordinates",
            FilterType.HIERARCHY: "Filter by hierarchy"
        }
        return descriptions.get(self.filter_type, "Custom filter")
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drag operation."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            self.parent().startDragDistance()):
            return
        
        # Create drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"filter_type:{self.filter_type.value}")
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        
        # Execute drag
        drag.exec(Qt.DropAction.CopyAction)


class FilterConditionWidget(QFrame):
    """Widget for editing a single filter condition."""
    
    condition_changed = pyqtSignal(FilterCondition)
    remove_requested = pyqtSignal(str)  # condition_id
    
    def __init__(self, condition: FilterCondition = None, parent=None):
        super().__init__(parent)
        self.condition = condition or FilterCondition()
        self.setup_ui()
        self.update_ui_from_condition()
        
    def setup_ui(self):
        """Setup the condition editing UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 2px;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Enable/disable checkbox
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setChecked(self.condition.enabled)
        self.enabled_checkbox.toggled.connect(self.on_condition_changed)
        layout.addWidget(self.enabled_checkbox)
        
        # Filter type combo
        self.type_combo = QComboBox()
        for filter_type in FilterType:
            self.type_combo.addItem(filter_type.value.replace("_", " ").title(), filter_type)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Field name (for custom fields)
        self.field_input = QLineEdit()
        self.field_input.setPlaceholderText("Field name...")
        self.field_input.textChanged.connect(self.on_condition_changed)
        layout.addWidget(self.field_input)
        
        # Operator combo
        self.operator_combo = QComboBox()
        self.populate_operators()
        self.operator_combo.currentIndexChanged.connect(self.on_condition_changed)
        layout.addWidget(self.operator_combo)
        
        # Value input (dynamic based on operator)
        self.value_widget = QWidget()
        self.value_layout = QHBoxLayout(self.value_widget)
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.value_widget)
        
        # Remove button
        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.condition.filter_id))
        layout.addWidget(self.remove_button)
        
        self.create_value_input()
    
    def populate_operators(self):
        """Populate operator combo based on filter type."""
        self.operator_combo.clear()
        
        filter_type = self.type_combo.currentData()
        if not filter_type:
            return
        
        # Get appropriate operators for filter type
        if filter_type in (FilterType.CONFIDENCE, FilterType.PAGE_NUMBER):
            operators = [
                FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                FilterOperator.GREATER_THAN, FilterOperator.LESS_THAN,
                FilterOperator.GREATER_EQUAL, FilterOperator.LESS_EQUAL,
                FilterOperator.BETWEEN
            ]
        elif filter_type == FilterType.ELEMENT_TYPE:
            operators = [
                FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                FilterOperator.IN, FilterOperator.NOT_IN
            ]
        elif filter_type in (FilterType.TEXT_CONTENT, FilterType.DETECTION_METHOD):
            operators = [
                FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS,
                FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH,
                FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                FilterOperator.REGEX, FilterOperator.FUZZY
            ]
        else:
            operators = [
                FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS,
                FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL
            ]
        
        for operator in operators:
            display_name = operator.value.replace("_", " ").title()
            self.operator_combo.addItem(display_name, operator)
    
    def create_value_input(self):
        """Create appropriate value input widget."""
        # Clear existing value widgets
        for i in reversed(range(self.value_layout.count())):
            child = self.value_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        operator = self.operator_combo.currentData()
        filter_type = self.type_combo.currentData()
        
        if operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
            # No value input needed
            label = QLabel("(no value)")
            label.setStyleSheet("color: #666; font-style: italic;")
            self.value_layout.addWidget(label)
            
        elif operator == FilterOperator.BETWEEN:
            # Two numeric inputs
            self.min_input = QDoubleSpinBox()
            self.min_input.setRange(-999999, 999999)
            self.min_input.valueChanged.connect(self.on_condition_changed)
            self.value_layout.addWidget(self.min_input)
            
            self.value_layout.addWidget(QLabel("to"))
            
            self.max_input = QDoubleSpinBox()
            self.max_input.setRange(-999999, 999999)
            self.max_input.valueChanged.connect(self.on_condition_changed)
            self.value_layout.addWidget(self.max_input)
            
        elif filter_type == FilterType.ELEMENT_TYPE and operator in (FilterOperator.IN, FilterOperator.NOT_IN):
            # Multiple element type selection
            self.type_list = QListWidget()
            self.type_list.setMaximumHeight(100)
            for element_type in ElementType:
                item = QListWidgetItem(element_type.value)
                item.setData(Qt.ItemDataRole.UserRole, element_type)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.type_list.addItem(item)
            self.type_list.itemChanged.connect(self.on_condition_changed)
            self.value_layout.addWidget(self.type_list)
            
        elif filter_type in (FilterType.CONFIDENCE, FilterType.PAGE_NUMBER):
            # Numeric input
            if filter_type == FilterType.CONFIDENCE:
                self.value_input = QDoubleSpinBox()
                self.value_input.setRange(0.0, 1.0)
                self.value_input.setSingleStep(0.1)
            else:
                self.value_input = QSpinBox()
                self.value_input.setRange(1, 9999)
            
            self.value_input.valueChanged.connect(self.on_condition_changed)
            self.value_layout.addWidget(self.value_input)
            
        else:
            # Text input
            self.value_input = QLineEdit()
            self.value_input.setPlaceholderText("Enter value...")
            self.value_input.textChanged.connect(self.on_condition_changed)
            self.value_layout.addWidget(self.value_input)
    
    def on_type_changed(self):
        """Handle filter type change."""
        self.populate_operators()
        self.create_value_input()
        self.on_condition_changed()
    
    def on_condition_changed(self):
        """Handle condition parameter changes."""
        # Update condition object
        self.condition.enabled = self.enabled_checkbox.isChecked()
        self.condition.filter_type = self.type_combo.currentData() or FilterType.TEXT_CONTENT
        self.condition.field_name = self.field_input.text()
        self.condition.operator = self.operator_combo.currentData() or FilterOperator.CONTAINS
        
        # Get value based on operator and type
        operator = self.condition.operator
        
        if operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
            self.condition.value = FilterValue(None)
            
        elif operator == FilterOperator.BETWEEN:
            if hasattr(self, 'min_input') and hasattr(self, 'max_input'):
                value = [self.min_input.value(), self.max_input.value()]
                self.condition.value = FilterValue(value, "list")
            
        elif hasattr(self, 'type_list'):
            # Multiple element types
            selected_types = []
            for i in range(self.type_list.count()):
                item = self.type_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    element_type = item.data(Qt.ItemDataRole.UserRole)
                    selected_types.append(element_type.value)
            self.condition.value = FilterValue(selected_types, "list")
            
        elif hasattr(self, 'value_input'):
            if isinstance(self.value_input, (QSpinBox, QDoubleSpinBox)):
                self.condition.value = FilterValue(self.value_input.value(), "number")
            else:
                self.condition.value = FilterValue(self.value_input.text(), "string")
        
        # Show/hide field name input
        self.field_input.setVisible(self.condition.filter_type == FilterType.CUSTOM_FIELD)
        
        self.condition_changed.emit(self.condition)
    
    def update_ui_from_condition(self):
        """Update UI elements from condition object."""
        self.enabled_checkbox.setChecked(self.condition.enabled)
        
        # Set filter type
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == self.condition.filter_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        self.field_input.setText(self.condition.field_name)
        
        # Set operator
        for i in range(self.operator_combo.count()):
            if self.operator_combo.itemData(i) == self.condition.operator:
                self.operator_combo.setCurrentIndex(i)
                break
        
        # Set value (this is complex and depends on the UI components created)
        # Implementation would be specific to each value input type
        
        self.field_input.setVisible(self.condition.filter_type == FilterType.CUSTOM_FIELD)


class FilterGroupWidget(QFrame):
    """Widget for editing a filter group."""
    
    group_changed = pyqtSignal(FilterGroup)
    remove_requested = pyqtSignal(str)  # group_id
    
    def __init__(self, group: FilterGroup = None, parent=None):
        super().__init__(parent)
        self.group = group or FilterGroup()
        self.condition_widgets: List[FilterConditionWidget] = []
        self.setup_ui()
        self.populate_conditions()
        
    def setup_ui(self):
        """Setup the group editing UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #2196f3;
                border-radius: 8px;
                margin: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with logic and controls
        header_layout = QHBoxLayout()
        
        # Enable checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(self.group.enabled)
        self.enabled_checkbox.toggled.connect(self.on_group_changed)
        header_layout.addWidget(self.enabled_checkbox)
        
        # Logic combo
        header_layout.addWidget(QLabel("Logic:"))
        self.logic_combo = QComboBox()
        for logic in FilterLogic:
            self.logic_combo.addItem(logic.value.upper(), logic)
        self.logic_combo.currentIndexChanged.connect(self.on_group_changed)
        header_layout.addWidget(self.logic_combo)
        
        header_layout.addStretch()
        
        # Add condition button
        self.add_button = QPushButton("+ Add Condition")
        self.add_button.clicked.connect(self.add_condition)
        header_layout.addWidget(self.add_button)
        
        # Remove group button
        self.remove_button = QPushButton("Remove Group")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.group.group_id))
        header_layout.addWidget(self.remove_button)
        
        layout.addLayout(header_layout)
        
        # Conditions container
        self.conditions_widget = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_widget)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.conditions_widget)
    
    def populate_conditions(self):
        """Populate condition widgets from group."""
        for condition in self.group.conditions:
            self.add_condition_widget(condition)
    
    def add_condition(self):
        """Add a new condition to the group."""
        condition = FilterCondition()
        self.group.add_condition(condition)
        self.add_condition_widget(condition)
        self.on_group_changed()
    
    def add_condition_widget(self, condition: FilterCondition):
        """Add a condition widget."""
        widget = FilterConditionWidget(condition, self)
        widget.condition_changed.connect(self.on_condition_changed)
        widget.remove_requested.connect(self.remove_condition)
        self.condition_widgets.append(widget)
        self.conditions_layout.addWidget(widget)
    
    def remove_condition(self, condition_id: str):
        """Remove a condition from the group."""
        # Remove from group
        self.group.remove_condition(condition_id)
        
        # Remove widget
        for i, widget in enumerate(self.condition_widgets):
            if widget.condition.filter_id == condition_id:
                widget.deleteLater()
                self.condition_widgets.pop(i)
                break
        
        self.on_group_changed()
    
    def on_condition_changed(self, condition: FilterCondition):
        """Handle condition changes."""
        self.on_group_changed()
    
    def on_group_changed(self):
        """Handle group changes."""
        self.group.enabled = self.enabled_checkbox.isChecked()
        self.group.logic = self.logic_combo.currentData() or FilterLogic.AND
        self.group_changed.emit(self.group)


class VisualQueryBuilder(QWidget):
    """Main visual query builder widget."""
    
    query_changed = pyqtSignal(FilterSet)
    
    def __init__(self, filter_manager: FilterManager, parent=None):
        super().__init__(parent)
        self.filter_manager = filter_manager
        self.current_filter_set: Optional[FilterSet] = None
        self.group_widgets: List[FilterGroupWidget] = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the visual query builder UI."""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        # Filter set name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Filter set name...")
        self.name_input.textChanged.connect(self.on_filter_set_changed)
        toolbar_layout.addWidget(QLabel("Name:"))
        toolbar_layout.addWidget(self.name_input)
        
        # Logic combo for combining groups
        toolbar_layout.addWidget(QLabel("Combine groups with:"))
        self.combination_logic_combo = QComboBox()
        for logic in FilterLogic:
            self.combination_logic_combo.addItem(logic.value.upper(), logic)
        self.combination_logic_combo.currentIndexChanged.connect(self.on_filter_set_changed)
        toolbar_layout.addWidget(self.combination_logic_combo)
        
        toolbar_layout.addStretch()
        
        # Actions
        self.add_group_button = QPushButton("+ Add Group")
        self.add_group_button.clicked.connect(self.add_group)
        toolbar_layout.addWidget(self.add_group_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(self.clear_button)
        
        layout.addLayout(toolbar_layout)
        
        # Groups scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAcceptDrops(True)
        
        self.groups_widget = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_widget)
        self.groups_layout.addStretch()
        
        self.scroll_area.setWidget(self.groups_widget)
        layout.addWidget(self.scroll_area)
        
        # Initialize with empty filter set
        self.set_filter_set(FilterSet(name="New Filter Set"))
    
    def set_filter_set(self, filter_set: FilterSet):
        """Set the current filter set being edited."""
        self.current_filter_set = filter_set
        
        # Update UI
        self.name_input.setText(filter_set.name)
        
        # Set combination logic
        for i in range(self.combination_logic_combo.count()):
            if self.combination_logic_combo.itemData(i) == filter_set.combination_logic:
                self.combination_logic_combo.setCurrentIndex(i)
                break
        
        # Clear existing group widgets
        for widget in self.group_widgets:
            widget.deleteLater()
        self.group_widgets.clear()
        
        # Add group widgets
        for group in filter_set.groups:
            self.add_group_widget(group)
        
        if not filter_set.groups:
            self.add_group()
    
    def add_group(self):
        """Add a new filter group."""
        group = FilterGroup()
        if self.current_filter_set:
            self.current_filter_set.add_group(group)
        self.add_group_widget(group)
        self.on_filter_set_changed()
    
    def add_group_widget(self, group: FilterGroup):
        """Add a group widget."""
        widget = FilterGroupWidget(group, self)
        widget.group_changed.connect(self.on_group_changed)
        widget.remove_requested.connect(self.remove_group)
        self.group_widgets.append(widget)
        
        # Insert before the stretch
        self.groups_layout.insertWidget(self.groups_layout.count() - 1, widget)
    
    def remove_group(self, group_id: str):
        """Remove a filter group."""
        if self.current_filter_set:
            self.current_filter_set.remove_group(group_id)
        
        # Remove widget
        for i, widget in enumerate(self.group_widgets):
            if widget.group.group_id == group_id:
                widget.deleteLater()
                self.group_widgets.pop(i)
                break
        
        self.on_filter_set_changed()
    
    def clear_all(self):
        """Clear all groups."""
        if self.current_filter_set:
            self.current_filter_set.groups.clear()
        
        for widget in self.group_widgets:
            widget.deleteLater()
        self.group_widgets.clear()
        
        self.add_group()  # Always have at least one group
        self.on_filter_set_changed()
    
    def on_group_changed(self, group: FilterGroup):
        """Handle group changes."""
        self.on_filter_set_changed()
    
    def on_filter_set_changed(self):
        """Handle filter set changes."""
        if not self.current_filter_set:
            return
        
        self.current_filter_set.name = self.name_input.text()
        self.current_filter_set.combination_logic = (
            self.combination_logic_combo.currentData() or FilterLogic.AND
        )
        
        self.query_changed.emit(self.current_filter_set)
    
    def get_filter_set(self) -> FilterSet:
        """Get the current filter set."""
        return self.current_filter_set


class QueryBuilderDialog(QDialog):
    """Dialog for building queries with multiple modes."""
    
    def __init__(self, filter_manager: FilterManager, initial_filter_set: FilterSet = None, parent=None):
        super().__init__(parent)
        self.filter_manager = filter_manager
        self.result_filter_set: Optional[FilterSet] = None
        self.setup_ui()
        
        if initial_filter_set:
            self.visual_builder.set_filter_set(initial_filter_set)
        
        self.setWindowTitle("Query Builder")
        self.resize(800, 600)
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Mode tabs
        self.tab_widget = QTabWidget()
        
        # Visual builder tab
        self.visual_builder = VisualQueryBuilder(self.filter_manager)
        self.visual_builder.query_changed.connect(self.on_query_changed)
        self.tab_widget.addTab(self.visual_builder, "Visual Builder")
        
        # TODO: Add other tabs (Form, Text, etc.)
        
        layout.addWidget(self.tab_widget)
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_query_changed(self, filter_set: FilterSet):
        """Handle query changes."""
        self.result_filter_set = filter_set
        
        # Update preview
        preview_text = f"Filter Set: {filter_set.name}\n"
        preview_text += f"Groups: {len(filter_set.groups)}\n"
        preview_text += f"Combination Logic: {filter_set.combination_logic.value.upper()}\n\n"
        
        for i, group in enumerate(filter_set.groups):
            preview_text += f"Group {i+1} ({group.logic.value.upper()}):\n"
            for j, condition in enumerate(group.conditions):
                if condition.enabled:
                    preview_text += f"  - {condition.filter_type.value} {condition.operator.value} {condition.value.value}\n"
            preview_text += "\n"
        
        self.preview_text.setPlainText(preview_text)
    
    def get_filter_set(self) -> Optional[FilterSet]:
        """Get the resulting filter set."""
        return self.result_filter_set