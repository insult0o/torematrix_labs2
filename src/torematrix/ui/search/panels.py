"""Filter Panel and Visual Controls

Advanced filter interface with drag-and-drop support, visual controls,
and intuitive filter management for complex search operations.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QCheckBox, QSlider,
    QGroupBox, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QToolButton, QMenu, QAction, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QRect, QSize
from PyQt6.QtGui import QIcon, QFont, QPainter, QColor, QDragEnterEvent, QDropEvent

logger = logging.getLogger(__name__)


class FilterType(Enum):
    """Types of filters available"""
    TEXT = "text"
    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"
    LIST = "list"
    RANGE = "range"
    CUSTOM = "custom"


class FilterOperator(Enum):
    """Filter comparison operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"


@dataclass
class FilterDefinition:
    """Definition of an available filter"""
    field: str
    label: str
    filter_type: FilterType
    description: str = ""
    options: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_operator: FilterOperator = FilterOperator.EQUALS
    supported_operators: List[FilterOperator] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.supported_operators:
            # Set default operators based on type
            if self.filter_type == FilterType.TEXT:
                self.supported_operators = [
                    FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS,
                    FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                    FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH
                ]
            elif self.filter_type == FilterType.NUMERIC:
                self.supported_operators = [
                    FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                    FilterOperator.GREATER_THAN, FilterOperator.LESS_THAN,
                    FilterOperator.GREATER_EQUAL, FilterOperator.LESS_EQUAL,
                    FilterOperator.BETWEEN
                ]
            elif self.filter_type == FilterType.DATE:
                self.supported_operators = [
                    FilterOperator.EQUALS, FilterOperator.NOT_EQUALS,
                    FilterOperator.GREATER_THAN, FilterOperator.LESS_THAN,
                    FilterOperator.BETWEEN
                ]
            elif self.filter_type == FilterType.BOOLEAN:
                self.supported_operators = [FilterOperator.EQUALS]
            elif self.filter_type == FilterType.LIST:
                self.supported_operators = [
                    FilterOperator.IN, FilterOperator.NOT_IN,
                    FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS
                ]


@dataclass
class FilterInstance:
    """An active filter instance"""
    id: str
    definition: FilterDefinition
    operator: FilterOperator
    value: Any
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary representation"""
        return {
            'id': self.id,
            'field': self.definition.field,
            'operator': self.operator.value,
            'value': self.value,
            'enabled': self.enabled
        }
    
    def matches(self, element_data: Dict[str, Any]) -> bool:
        """Check if element data matches this filter"""
        if not self.enabled:
            return True
        
        field_value = element_data.get(self.definition.field)
        
        try:
            if self.operator == FilterOperator.EQUALS:
                return field_value == self.value
            elif self.operator == FilterOperator.NOT_EQUALS:
                return field_value != self.value
            elif self.operator == FilterOperator.CONTAINS:
                return str(self.value).lower() in str(field_value).lower()
            elif self.operator == FilterOperator.NOT_CONTAINS:
                return str(self.value).lower() not in str(field_value).lower()
            elif self.operator == FilterOperator.STARTS_WITH:
                return str(field_value).lower().startswith(str(self.value).lower())
            elif self.operator == FilterOperator.ENDS_WITH:
                return str(field_value).lower().endswith(str(self.value).lower())
            elif self.operator == FilterOperator.GREATER_THAN:
                return float(field_value) > float(self.value)
            elif self.operator == FilterOperator.LESS_THAN:
                return float(field_value) < float(self.value)
            elif self.operator == FilterOperator.GREATER_EQUAL:
                return float(field_value) >= float(self.value)
            elif self.operator == FilterOperator.LESS_EQUAL:
                return float(field_value) <= float(self.value)
            elif self.operator == FilterOperator.BETWEEN:
                if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                    return float(self.value[0]) <= float(field_value) <= float(self.value[1])
            elif self.operator == FilterOperator.IN:
                return field_value in self.value if isinstance(self.value, (list, set)) else False
            elif self.operator == FilterOperator.NOT_IN:
                return field_value not in self.value if isinstance(self.value, (list, set)) else True
            elif self.operator == FilterOperator.IS_NULL:
                return field_value is None
            elif self.operator == FilterOperator.IS_NOT_NULL:
                return field_value is not None
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Filter evaluation error: {e}")
            return True


class FilterWidget(QFrame):
    """Widget for a single filter instance"""
    
    # Signals
    filter_changed = pyqtSignal(object)  # FilterInstance
    remove_requested = pyqtSignal(object)  # self
    
    def __init__(self, filter_instance: FilterInstance, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.filter_instance = filter_instance
        self._setup_ui()
        self._setup_connections()
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMaximumHeight(80)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Header with field name and remove button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Enable checkbox
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setChecked(self.filter_instance.enabled)
        header_layout.addWidget(self.enabled_checkbox)
        
        # Field label
        field_label = QLabel(self.filter_instance.definition.label)
        field_label.setStyleSheet("font-weight: bold; color: #333;")
        header_layout.addWidget(field_label)
        
        header_layout.addStretch()
        
        # Remove button
        self.remove_button = QToolButton()
        self.remove_button.setText("×")
        self.remove_button.setStyleSheet("QToolButton { color: #dc3545; font-weight: bold; }")
        self.remove_button.setMaximumSize(20, 20)
        self.remove_button.setToolTip("Remove filter")
        header_layout.addWidget(self.remove_button)
        
        layout.addLayout(header_layout)
        
        # Filter controls
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(20, 0, 0, 0)  # Indent under checkbox
        
        # Operator selector
        self.operator_combo = QComboBox()
        self.operator_combo.setMinimumWidth(100)
        for op in self.filter_instance.definition.supported_operators:
            self.operator_combo.addItem(op.value.replace('_', ' ').title(), op)
        
        # Set current operator
        for i in range(self.operator_combo.count()):
            if self.operator_combo.itemData(i) == self.filter_instance.operator:
                self.operator_combo.setCurrentIndex(i)
                break
        
        controls_layout.addWidget(self.operator_combo)
        
        # Value widget (depends on filter type)
        self.value_widget = self._create_value_widget()
        controls_layout.addWidget(self.value_widget)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
    
    def _create_value_widget(self) -> QWidget:
        """Create appropriate value input widget based on filter type"""
        filter_type = self.filter_instance.definition.filter_type
        
        if filter_type == FilterType.TEXT:
            widget = QLineEdit()
            widget.setText(str(self.filter_instance.value) if self.filter_instance.value else "")
            widget.setPlaceholderText("Enter text...")
            return widget
            
        elif filter_type == FilterType.NUMERIC:
            if self.filter_instance.operator == FilterOperator.BETWEEN:
                # Range widget
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(0, 0, 0, 0)
                
                min_spin = QDoubleSpinBox()
                min_spin.setMinimum(self.filter_instance.definition.min_value or -999999)
                min_spin.setMaximum(self.filter_instance.definition.max_value or 999999)
                
                max_spin = QDoubleSpinBox()
                max_spin.setMinimum(self.filter_instance.definition.min_value or -999999)
                max_spin.setMaximum(self.filter_instance.definition.max_value or 999999)
                
                # Set current values
                if isinstance(self.filter_instance.value, (list, tuple)) and len(self.filter_instance.value) == 2:
                    min_spin.setValue(float(self.filter_instance.value[0]))
                    max_spin.setValue(float(self.filter_instance.value[1]))
                
                layout.addWidget(min_spin)
                layout.addWidget(QLabel("to"))
                layout.addWidget(max_spin)
                
                return widget
            else:
                # Single value
                widget = QDoubleSpinBox()
                widget.setMinimum(self.filter_instance.definition.min_value or -999999)
                widget.setMaximum(self.filter_instance.definition.max_value or 999999)
                if self.filter_instance.value is not None:
                    widget.setValue(float(self.filter_instance.value))
                return widget
                
        elif filter_type == FilterType.DATE:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            if self.filter_instance.value:
                if isinstance(self.filter_instance.value, str):
                    # Parse date string
                    try:
                        date_obj = datetime.fromisoformat(self.filter_instance.value).date()
                        widget.setDate(date_obj)
                    except:
                        pass
                elif isinstance(self.filter_instance.value, (date, datetime)):
                    widget.setDate(self.filter_instance.value)
            return widget
            
        elif filter_type == FilterType.BOOLEAN:
            widget = QComboBox()
            widget.addItem("True", True)
            widget.addItem("False", False)
            if self.filter_instance.value is not None:
                widget.setCurrentIndex(0 if self.filter_instance.value else 1)
            return widget
            
        elif filter_type == FilterType.LIST:
            if self.filter_instance.definition.options:
                widget = QComboBox()
                widget.setEditable(True)
                for option in self.filter_instance.definition.options:
                    widget.addItem(option)
                if self.filter_instance.value:
                    widget.setCurrentText(str(self.filter_instance.value))
                return widget
            else:
                widget = QLineEdit()
                widget.setText(str(self.filter_instance.value) if self.filter_instance.value else "")
                widget.setPlaceholderText("Enter value...")
                return widget
        
        # Default to text input
        widget = QLineEdit()
        widget.setText(str(self.filter_instance.value) if self.filter_instance.value else "")
        return widget
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.enabled_checkbox.toggled.connect(self._on_enabled_changed)
        self.operator_combo.currentIndexChanged.connect(self._on_operator_changed)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        
        # Value widget connections (depends on type)
        if isinstance(self.value_widget, QLineEdit):
            self.value_widget.textChanged.connect(self._on_value_changed)
        elif isinstance(self.value_widget, (QSpinBox, QDoubleSpinBox)):
            self.value_widget.valueChanged.connect(self._on_value_changed)
        elif isinstance(self.value_widget, QDateEdit):
            self.value_widget.dateChanged.connect(self._on_value_changed)
        elif isinstance(self.value_widget, QComboBox):
            self.value_widget.currentTextChanged.connect(self._on_value_changed)
    
    def _on_enabled_changed(self, enabled: bool):
        """Handle enable/disable change"""
        self.filter_instance.enabled = enabled
        self.value_widget.setEnabled(enabled)
        self.operator_combo.setEnabled(enabled)
        self.filter_changed.emit(self.filter_instance)
    
    def _on_operator_changed(self):
        """Handle operator change"""
        operator = self.operator_combo.currentData()
        if operator != self.filter_instance.operator:
            self.filter_instance.operator = operator
            
            # Recreate value widget if needed (e.g., for BETWEEN operator)
            if (operator == FilterOperator.BETWEEN and 
                self.filter_instance.definition.filter_type == FilterType.NUMERIC):
                
                # Replace value widget
                old_widget = self.value_widget
                self.value_widget = self._create_value_widget()
                
                layout = old_widget.parent().layout()
                layout.replaceWidget(old_widget, self.value_widget)
                old_widget.deleteLater()
                
                # Reconnect signals
                if isinstance(self.value_widget, QWidget):
                    # Handle range widget connections
                    pass
            
            self.filter_changed.emit(self.filter_instance)
    
    def _on_value_changed(self):
        """Handle value change"""
        try:
            if isinstance(self.value_widget, QLineEdit):
                self.filter_instance.value = self.value_widget.text()
            elif isinstance(self.value_widget, (QSpinBox, QDoubleSpinBox)):
                self.filter_instance.value = self.value_widget.value()
            elif isinstance(self.value_widget, QDateEdit):
                self.filter_instance.value = self.value_widget.date().toPython()
            elif isinstance(self.value_widget, QComboBox):
                if self.filter_instance.definition.filter_type == FilterType.BOOLEAN:
                    self.filter_instance.value = self.value_widget.currentData()
                else:
                    self.filter_instance.value = self.value_widget.currentText()
            
            self.filter_changed.emit(self.filter_instance)
            
        except Exception as e:
            logger.warning(f"Error updating filter value: {e}")
    
    def get_filter_instance(self) -> FilterInstance:
        """Get the current filter instance"""
        return self.filter_instance


class FilterPanel(QWidget):
    """Main filter panel with drag-and-drop and visual controls"""
    
    # Signals
    filters_changed = pyqtSignal(list)  # List[FilterInstance]
    filter_applied = pyqtSignal()
    filter_cleared = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        
        # State
        self._available_filters: Dict[str, FilterDefinition] = {}
        self._active_filters: List[FilterInstance] = []
        self._filter_widgets: List[FilterWidget] = []
        
        # Setup default filters
        self._setup_default_filters()
        
        logger.info("FilterPanel initialized")
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Filters")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Add filter button
        self.add_filter_button = QToolButton()
        self.add_filter_button.setText("+ Add Filter")
        self.add_filter_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_filter_button.setStyleSheet("QToolButton { padding: 4px 8px; }")
        header_layout.addWidget(self.add_filter_button)
        
        # Clear all button
        self.clear_button = QPushButton("Clear All")
        self.clear_button.setMaximumWidth(80)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        
        # Filter list area
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self.filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.filter_container = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_container)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(4)
        self.filter_layout.addStretch()  # Push filters to top
        
        self.filter_scroll.setWidget(self.filter_container)
        layout.addWidget(self.filter_scroll)
        
        # Filter summary
        self.summary_label = QLabel("No active filters")
        self.summary_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Filters")
        self.apply_button.setEnabled(False)
        self.apply_button.setStyleSheet("QPushButton { font-weight: bold; }")
        button_layout.addWidget(self.apply_button)
        
        self.reset_button = QPushButton("Reset")
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.clear_button.clicked.connect(self.clear_all_filters)
        self.apply_button.clicked.connect(self._apply_filters)
        self.reset_button.clicked.connect(self._reset_filters)
    
    def _setup_default_filters(self):
        """Setup default available filters"""
        default_filters = [
            FilterDefinition(
                field="name",
                label="Name",
                filter_type=FilterType.TEXT,
                description="Element name or title"
            ),
            FilterDefinition(
                field="type",
                label="Type", 
                filter_type=FilterType.LIST,
                description="Element type",
                options=["text", "title", "paragraph", "list", "table", "image", "figure"]
            ),
            FilterDefinition(
                field="size",
                label="Size",
                filter_type=FilterType.NUMERIC,
                description="Element size in bytes",
                min_value=0,
                max_value=1000000
            ),
            FilterDefinition(
                field="created_at",
                label="Created",
                filter_type=FilterType.DATE,
                description="Creation date"
            ),
            FilterDefinition(
                field="modified_at",
                label="Modified",
                filter_type=FilterType.DATE,
                description="Last modification date"
            ),
            FilterDefinition(
                field="level",
                label="Level",
                filter_type=FilterType.NUMERIC,
                description="Hierarchy level",
                min_value=0,
                max_value=10
            ),
            FilterDefinition(
                field="has_children",
                label="Has Children",
                filter_type=FilterType.BOOLEAN,
                description="Whether element has child elements"
            )
        ]
        
        for filter_def in default_filters:
            self._available_filters[filter_def.field] = filter_def
        
        # Setup add filter menu
        self._setup_add_filter_menu()
    
    def _setup_add_filter_menu(self):
        """Setup the add filter dropdown menu"""
        menu = QMenu(self.add_filter_button)
        
        for field, filter_def in self._available_filters.items():
            action = QAction(filter_def.label, menu)
            action.setToolTip(filter_def.description)
            action.setData(field)
            action.triggered.connect(lambda checked, f=field: self._add_filter(f))
            menu.addAction(action)
        
        self.add_filter_button.setMenu(menu)
    
    def _add_filter(self, field: str):
        """Add a new filter instance"""
        if field not in self._available_filters:
            logger.warning(f"Unknown filter field: {field}")
            return
        
        filter_def = self._available_filters[field]
        
        # Create filter instance
        filter_id = f"{field}_{len(self._active_filters)}"
        filter_instance = FilterInstance(
            id=filter_id,
            definition=filter_def,
            operator=filter_def.default_operator,
            value="",
            enabled=True
        )
        
        # Create filter widget
        filter_widget = FilterWidget(filter_instance)
        filter_widget.filter_changed.connect(self._on_filter_changed)
        filter_widget.remove_requested.connect(self._remove_filter_widget)
        
        # Add to layout (before stretch)
        self.filter_layout.insertWidget(self.filter_layout.count() - 1, filter_widget)
        
        # Store references
        self._active_filters.append(filter_instance)
        self._filter_widgets.append(filter_widget)
        
        # Update UI
        self._update_ui_state()
        
        logger.debug(f"Added filter: {filter_def.label}")
    
    def _remove_filter_widget(self, widget: FilterWidget):
        """Remove a filter widget"""
        try:
            # Find and remove filter instance
            filter_instance = widget.get_filter_instance()
            if filter_instance in self._active_filters:
                self._active_filters.remove(filter_instance)
            
            # Remove widget
            if widget in self._filter_widgets:
                self._filter_widgets.remove(widget)
            
            # Remove from layout
            self.filter_layout.removeWidget(widget)
            widget.deleteLater()
            
            # Update UI
            self._update_ui_state()
            
            logger.debug(f"Removed filter: {filter_instance.definition.label}")
            
        except Exception as e:
            logger.error(f"Error removing filter widget: {e}")
    
    def _on_filter_changed(self, filter_instance: FilterInstance):
        """Handle filter change"""
        self._update_ui_state()
        logger.debug(f"Filter changed: {filter_instance.definition.label}")
    
    def _update_ui_state(self):
        """Update UI state based on current filters"""
        active_count = len([f for f in self._active_filters if f.enabled])
        total_count = len(self._active_filters)
        
        # Update summary
        if total_count == 0:
            self.summary_label.setText("No active filters")
        elif active_count == 0:
            self.summary_label.setText(f"{total_count} filter{'s' if total_count != 1 else ''} (all disabled)")
        else:
            self.summary_label.setText(f"{active_count} of {total_count} filter{'s' if total_count != 1 else ''} active")
        
        # Update button states
        self.apply_button.setEnabled(active_count > 0)
        self.clear_button.setEnabled(total_count > 0)
        self.reset_button.setEnabled(total_count > 0)
        
        # Emit filters changed signal
        self.filters_changed.emit(self._active_filters)
    
    def _apply_filters(self):
        """Apply current filters"""
        active_filters = [f for f in self._active_filters if f.enabled]
        logger.info(f"Applying {len(active_filters)} filters")
        self.filter_applied.emit()
    
    def _reset_filters(self):
        """Reset all filter values to defaults"""
        for filter_widget in self._filter_widgets:
            filter_instance = filter_widget.get_filter_instance()
            filter_instance.value = ""
            filter_instance.enabled = True
            # TODO: Reset widget values
        
        self._update_ui_state()
        logger.debug("Filters reset")
    
    def clear_all_filters(self):
        """Clear all filters"""
        # Remove all filter widgets
        for widget in self._filter_widgets.copy():
            self._remove_filter_widget(widget)
        
        self._active_filters.clear()
        self._filter_widgets.clear()
        self._update_ui_state()
        
        self.filter_cleared.emit()
        logger.debug("All filters cleared")
    
    def get_active_filters(self) -> List[FilterInstance]:
        """Get list of active (enabled) filters"""
        return [f for f in self._active_filters if f.enabled]
    
    def get_all_filters(self) -> List[FilterInstance]:
        """Get list of all filters (enabled and disabled)"""
        return self._active_filters.copy()
    
    def apply_filters_to_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply active filters to a list of elements"""
        active_filters = self.get_active_filters()
        if not active_filters:
            return elements
        
        filtered_elements = []
        for element in elements:
            # Element must pass all active filters
            if all(filter_inst.matches(element) for filter_inst in active_filters):
                filtered_elements.append(element)
        
        logger.debug(f"Filtered {len(elements)} elements to {len(filtered_elements)} results")
        return filtered_elements
    
    def add_filter_definition(self, filter_def: FilterDefinition):
        """Add a new filter definition"""
        self._available_filters[filter_def.field] = filter_def
        self._setup_add_filter_menu()  # Recreate menu
        logger.debug(f"Added filter definition: {filter_def.label}")
    
    def set_filter_values(self, filter_values: Dict[str, Any]):
        """Set filter values programmatically"""
        for field, value in filter_values.items():
            # Find existing filter or create new one
            existing_filter = None
            for f in self._active_filters:
                if f.definition.field == field:
                    existing_filter = f
                    break
            
            if existing_filter:
                existing_filter.value = value
            else:
                # Create new filter
                self._add_filter(field)
                if self._active_filters:
                    self._active_filters[-1].value = value
        
        self._update_ui_state()


# Factory function for easy instantiation  
def create_filter_panel(parent: Optional[QWidget] = None) -> FilterPanel:
    """Create and configure a FilterPanel instance"""
    panel = FilterPanel(parent)
    return panel