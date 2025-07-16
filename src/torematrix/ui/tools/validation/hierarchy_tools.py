"""
<<<<<<< HEAD
Interactive hierarchy management UI tools for manual validation.

Agent 2 implementation for Issue #29.2 - Interactive Hierarchy UI Tools.
Provides drag-drop tree widgets, control panels, and visual feedback
for hierarchy manipulation and validation.
"""

from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass
from enum import Enum, auto
import json
import logging

from PyQt6.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QFrame, QSplitter, QGroupBox,
    QScrollArea, QTabWidget, QProgressBar, QMessageBox, QMenu,
    QHeaderView, QAbstractItemView, QStyleOptionViewItem,
    QStyledItemDelegate, QApplication, QStyle
)
from PyQt6.QtCore import (
    Qt, QMimeData, QByteArray, pyqtSignal, QTimer, QRect,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QModelIndex, QPoint, QSize
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap, QIcon,
    QDrag, QPalette, QFontMetrics, QLinearGradient
)

from ....core.models.element import Element, ElementType
from ....core.models.hierarchy import ElementHierarchy, HierarchyOperations
from ....core.state import StateManager
from ....core.events import EventBus
from ....ui.components.base import BaseWidget
=======
Interactive hierarchy management tools for document validation.

This module provides UI components for managing document element hierarchies.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QToolButton, QCheckBox, QSplitter, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Rect

>>>>>>> origin/main

logger = logging.getLogger(__name__)


<<<<<<< HEAD
class HierarchyOperation(Enum):
    """Types of hierarchy operations"""
    INDENT = auto()         # Move element deeper in hierarchy
    OUTDENT = auto()        # Move element up in hierarchy
    MOVE_UP = auto()        # Move element up in sibling order
    MOVE_DOWN = auto()      # Move element down in sibling order
    GROUP = auto()          # Group multiple elements
    UNGROUP = auto()        # Ungroup elements
    DELETE = auto()         # Delete elements
    DUPLICATE = auto()      # Duplicate elements


class ValidationLevel(Enum):
    """Hierarchy validation levels"""
    VALID = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class HierarchyMetrics:
    """Metrics for hierarchy analysis"""
    total_elements: int = 0
    depth_levels: int = 0
    orphaned_elements: int = 0
    circular_references: int = 0
    validation_errors: int = 0
    reading_order_issues: int = 0
    
    @property
    def health_score(self) -> float:
        """Calculate overall hierarchy health score (0-1)"""
        if self.total_elements == 0:
            return 1.0
        
        # Penalty factors
        orphan_penalty = (self.orphaned_elements / self.total_elements) * 0.3
        circular_penalty = (self.circular_references / self.total_elements) * 0.5
        error_penalty = (self.validation_errors / self.total_elements) * 0.4
        order_penalty = (self.reading_order_issues / self.total_elements) * 0.2
        
        return max(0.0, 1.0 - (orphan_penalty + circular_penalty + error_penalty + order_penalty))


class HierarchyTreeDelegate(QStyledItemDelegate):
    """Custom delegate for hierarchy tree styling and rendering"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.validation_colors = {
            ValidationLevel.VALID: QColor(46, 125, 50),      # Green
            ValidationLevel.WARNING: QColor(255, 152, 0),    # Orange  
            ValidationLevel.ERROR: QColor(211, 47, 47),      # Red
            ValidationLevel.CRITICAL: QColor(136, 14, 79)    # Purple
        }
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Custom paint method for tree items"""
        super().paint(painter, option, index)
        
        # Get validation level from item data
        validation_level = index.data(Qt.ItemDataRole.UserRole + 1)
        if validation_level and isinstance(validation_level, ValidationLevel):
            # Draw validation indicator
            rect = option.rect
            indicator_rect = QRect(rect.right() - 20, rect.top() + 2, 16, rect.height() - 4)
            
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(self.validation_colors[validation_level]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(indicator_rect)
            painter.restore()
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Provide size hint for items"""
        size = super().sizeHint(option, index)
        return QSize(size.width() + 25, max(size.height(), 24))  # Extra space for indicator


class HierarchyTreeWidget(QTreeWidget):
    """Drag-drop enabled tree widget for hierarchy manipulation"""
    
    # Signals
    hierarchy_changed = pyqtSignal(str, str)  # element_id, operation
    validation_changed = pyqtSignal(str, ValidationLevel)  # element_id, level
    selection_changed = pyqtSignal(list)  # selected_element_ids
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(parent)
        
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.hierarchy: Optional[ElementHierarchy] = None
        self.element_items: Dict[str, QTreeWidgetItem] = {}
        self.validation_cache: Dict[str, ValidationLevel] = {}
        
        self._setup_ui()
        self._setup_drag_drop()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components"""
        # Configure tree widget
        self.setHeaderLabels(["Element", "Type", "Status"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Set custom delegate
        self.setItemDelegate(HierarchyTreeDelegate(self))
        
        # Configure columns
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Style the widget
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e3f2fd;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #2196f3;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
    
    def _setup_drag_drop(self):
        """Configure drag and drop functionality"""
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
    
    def _connect_signals(self):
        """Connect internal signals"""
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemChanged.connect(self._on_item_changed)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def load_hierarchy(self, hierarchy: ElementHierarchy):
        """Load and display hierarchy"""
        self.hierarchy = hierarchy
        self.clear()
        self.element_items.clear()
        
        if not hierarchy:
            return
        
        # Build tree structure
        self._build_tree_structure()
        
        # Validate hierarchy
        self._validate_hierarchy()
        
        # Expand all items initially
        self.expandAll()


class HierarchyControlPanel(QWidget):
    """Control panel for hierarchy operations"""
    
    # Signals
    operation_requested = pyqtSignal(HierarchyOperation, list)  # operation, element_ids
    
    def __init__(self, tree_widget: HierarchyTreeWidget, parent=None):
        super().__init__(parent)
        
        self.tree_widget = tree_widget
        self.selected_elements: List[str] = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        
        # Operations group
        operations_group = QGroupBox("Hierarchy Operations")
        operations_layout = QVBoxLayout(operations_group)
        
        # Button layouts
        indent_layout = QHBoxLayout()
        move_layout = QHBoxLayout()
        group_layout = QHBoxLayout()
        
        # Indent/Outdent buttons
        self.indent_btn = QPushButton("Indent →")
        self.indent_btn.setToolTip("Move elements deeper in hierarchy")
        self.outdent_btn = QPushButton("← Outdent")
        self.outdent_btn.setToolTip("Move elements up in hierarchy")
        
        indent_layout.addWidget(self.outdent_btn)
        indent_layout.addWidget(self.indent_btn)
        
        # Move up/down buttons
        self.move_up_btn = QPushButton("Move Up ↑")
        self.move_up_btn.setToolTip("Move elements up in order")
        self.move_down_btn = QPushButton("Move Down ↓")
        self.move_down_btn.setToolTip("Move elements down in order")
        
        move_layout.addWidget(self.move_up_btn)
        move_layout.addWidget(self.move_down_btn)
        
        # Group/Ungroup buttons
        self.group_btn = QPushButton("Group")
        self.group_btn.setToolTip("Group selected elements")
        self.ungroup_btn = QPushButton("Ungroup")
        self.ungroup_btn.setToolTip("Ungroup selected elements")
        
        group_layout.addWidget(self.group_btn)
        group_layout.addWidget(self.ungroup_btn)
        
        # Add to operations layout
        operations_layout.addLayout(indent_layout)
        operations_layout.addLayout(move_layout)
        operations_layout.addLayout(group_layout)
        
        # Delete/Duplicate buttons
        danger_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip("Delete selected elements")
        self.delete_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setToolTip("Duplicate selected elements")
        
        danger_layout.addWidget(self.duplicate_btn)
        danger_layout.addWidget(self.delete_btn)
        operations_layout.addLayout(danger_layout)
        
        # Add operations group to main layout
        layout.addWidget(operations_group)
        
        # Selection info
        info_group = QGroupBox("Selection Info")
        info_layout = QVBoxLayout(info_group)
        
        self.selection_label = QLabel("No elements selected")
        self.selection_label.setStyleSheet("color: #666666; font-style: italic;")
        info_layout.addWidget(self.selection_label)
        
        layout.addWidget(info_group)
        
        # Initially disable all buttons
        self._update_button_states()
    
    def _connect_signals(self):
        """Connect button signals"""
        self.indent_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.INDENT))
        self.outdent_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.OUTDENT))
        self.move_up_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.MOVE_UP))
        self.move_down_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.MOVE_DOWN))
        self.group_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.GROUP))
        self.ungroup_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.UNGROUP))
        self.delete_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.DELETE))
        self.duplicate_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.DUPLICATE))
        
        # Connect to tree selection changes
        self.tree_widget.selection_changed.connect(self._on_selection_changed)
    
    def _request_operation(self, operation: HierarchyOperation):
        """Request hierarchy operation"""
        if self.selected_elements:
            # Confirm dangerous operations
            if operation == HierarchyOperation.DELETE:
                reply = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Delete {len(self.selected_elements)} selected element(s)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            self.operation_requested.emit(operation, self.selected_elements.copy())
    
    def _on_selection_changed(self, element_ids: List[str]):
        """Handle selection changes from tree"""
        self.selected_elements = element_ids
        self._update_button_states()
        self._update_selection_info()
    
    def _update_button_states(self):
        """Update button enabled states based on selection"""
        has_selection = len(self.selected_elements) > 0
        has_multiple = len(self.selected_elements) > 1
        
        # Basic operations require selection
        self.indent_btn.setEnabled(has_selection)
        self.outdent_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.duplicate_btn.setEnabled(has_selection)
        
        # Group requires multiple selection
        self.group_btn.setEnabled(has_multiple)
        
        # Ungroup requires single selection (group element)
        self.ungroup_btn.setEnabled(has_selection and len(self.selected_elements) == 1)
    
    def _update_selection_info(self):
        """Update selection information display"""
        count = len(self.selected_elements)
        
        if count == 0:
            self.selection_label.setText("No elements selected")
        elif count == 1:
            self.selection_label.setText("1 element selected")
        else:
            self.selection_label.setText(f"{count} elements selected")


class HierarchyMetricsWidget(QWidget):
    """Widget displaying hierarchy metrics and health"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.metrics = HierarchyMetrics()
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        
        # Metrics group
        metrics_group = QGroupBox("Hierarchy Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Health score
        health_layout = QHBoxLayout()
        health_layout.addWidget(QLabel("Health Score:"))
        
        self.health_bar = QProgressBar()
        self.health_bar.setRange(0, 100)
        self.health_bar.setTextVisible(True)
        health_layout.addWidget(self.health_bar)
        
        metrics_layout.addLayout(health_layout)
        
        # Stats grid
        stats_frame = QFrame()
        stats_layout = QVBoxLayout(stats_frame)
        
        self.total_label = QLabel("Total Elements: 0")
        self.depth_label = QLabel("Max Depth: 0")
        self.orphans_label = QLabel("Orphaned: 0")
        self.errors_label = QLabel("Errors: 0")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.depth_label)
        stats_layout.addWidget(self.orphans_label)
        stats_layout.addWidget(self.errors_label)
        
        metrics_layout.addWidget(stats_frame)
        layout.addWidget(metrics_group)
        
        # Style health bar
        self._update_health_bar_style()
    
    def update_metrics(self, metrics: HierarchyMetrics):
        """Update displayed metrics"""
        self.metrics = metrics
        
        # Update labels
        self.total_label.setText(f"Total Elements: {metrics.total_elements}")
        self.depth_label.setText(f"Max Depth: {metrics.depth_levels}")
        self.orphans_label.setText(f"Orphaned: {metrics.orphaned_elements}")
        self.errors_label.setText(f"Errors: {metrics.validation_errors}")
        
        # Update health score
        health_score = int(metrics.health_score * 100)
        self.health_bar.setValue(health_score)
        self.health_bar.setFormat(f"{health_score}%")
        
        self._update_health_bar_style()
    
    def _update_health_bar_style(self):
        """Update health bar color based on score"""
        score = self.metrics.health_score
        
        if score >= 0.8:
            color = "#4caf50"  # Green
        elif score >= 0.6:
            color = "#ff9800"  # Orange
        elif score >= 0.4:
            color = "#f44336"  # Red
        else:
            color = "#9c27b0"  # Purple
        
        self.health_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class HierarchyToolsWidget(QWidget):
    """Main container widget for hierarchy tools"""
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(parent)
        
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.hierarchy: Optional[ElementHierarchy] = None
=======
class HierarchyToolAction(Enum):
    """Actions available in hierarchy tools."""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    VALIDATE = "validate"


@dataclass
class HierarchyDisplayConfig:
    """Configuration for hierarchy display."""
    show_element_types: bool = True
    show_element_bounds: bool = False


class HierarchyTreeItem(QTreeWidgetItem):
    """Custom tree item for hierarchy display."""
    
    def __init__(self, element: Element, parent: Optional[QTreeWidgetItem] = None):
        super().__init__(parent)
        self.element = element
        self._setup_item()
    
    def _setup_item(self):
        """Set up the tree item display."""
        display_text = self.element.text
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."
        self.setText(0, display_text)
        self.setText(1, self.element.element_type.value)
        
        bounds = self.element.bounds
        self.setText(2, f"({bounds.x:.0f}, {bounds.y:.0f})")
        self.setText(3, f"{bounds.width:.0f}x{bounds.height:.0f}")
        self.setText(4, self.element.id)
    
    def get_element_id(self) -> str:
        """Get the element ID."""
        return self.element.id
    
    def get_element_type(self) -> ElementType:
        """Get the element type."""
        return self.element.element_type


class HierarchyTreeWidget(QTreeWidget):
    """Custom tree widget for hierarchy management."""
    
    element_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.element_items: Dict[str, HierarchyTreeItem] = {}
        self.config = HierarchyDisplayConfig()
        
        self._setup_tree()
    
    def _setup_tree(self):
        """Set up the tree widget."""
        self.setHeaderLabels(["Element", "Type", "Position", "Size", "ID"])
        self.setRootIsDecorated(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAnimated(True)
        
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
    
    def refresh_hierarchy(self):
        """Refresh the hierarchy display."""
        if not self.state_store:
            return
        
        self.clear()
        self.element_items.clear()
        
        elements = self.state_store.get_all_elements()
        if not elements:
            return
        
        self._build_tree(elements)
        self.expandAll()
    
    def _build_tree(self, elements: Dict[str, Element]):
        """Build the tree structure."""
        root_elements = [e for e in elements.values() if not e.parent_id]
        
        for element in root_elements:
            self._create_tree_item(element, elements, None)
    
    def _create_tree_item(self, element: Element, elements: Dict[str, Element], 
                         parent_item: Optional[HierarchyTreeItem] = None):
        """Create a tree item for an element."""
        if parent_item:
            item = HierarchyTreeItem(element, parent_item)
        else:
            item = HierarchyTreeItem(element)
            self.addTopLevelItem(item)
        
        self.element_items[element.id] = item
        
        if element.children:
            for child_id in element.children:
                if child_id in elements:
                    child_element = elements[child_id]
                    self._create_tree_item(child_element, elements, item)
    
    def get_selected_elements(self) -> List[str]:
        """Get selected element IDs."""
        selected_items = self.selectedItems()
        return [item.get_element_id() for item in selected_items 
                if isinstance(item, HierarchyTreeItem)]
    
    def select_element(self, element_id: str):
        """Select an element in the tree."""
        if element_id in self.element_items:
            item = self.element_items[element_id]
            self.setCurrentItem(item)
            self.scrollToItem(item)
    
    def _on_selection_changed(self):
        """Handle selection change."""
        selected_items = self.selectedItems()
        if selected_items:
            item = selected_items[0]
            if isinstance(item, HierarchyTreeItem):
                self.element_selected.emit(item.get_element_id())


class HierarchyControlPanel(QWidget):
    """Control panel for hierarchy management."""
    
    action_requested = pyqtSignal(HierarchyToolAction, list)
    config_changed = pyqtSignal(HierarchyDisplayConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = HierarchyDisplayConfig()
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        self.move_up_btn = QToolButton()
        self.move_up_btn.setText("Move Up")
        self.move_up_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.MOVE_UP))
        actions_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QToolButton()
        self.move_down_btn.setText("Move Down")
        self.move_down_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.MOVE_DOWN))
        actions_layout.addWidget(self.move_down_btn)
        
        self.validate_btn = QToolButton()
        self.validate_btn.setText("Validate")
        self.validate_btn.clicked.connect(lambda: self._emit_action(HierarchyToolAction.VALIDATE))
        actions_layout.addWidget(self.validate_btn)
        
        layout.addWidget(actions_group)
        
        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.show_types_cb = QCheckBox("Show Element Types")
        self.show_types_cb.setChecked(self.config.show_element_types)
        self.show_types_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_types_cb)
        
        self.show_bounds_cb = QCheckBox("Show Element Bounds")
        self.show_bounds_cb.setChecked(self.config.show_element_bounds)
        self.show_bounds_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_bounds_cb)
        
        layout.addWidget(display_group)
        layout.addStretch()
    
    def set_selected_elements(self, element_ids: List[str]):
        """Update button states based on selected elements."""
        has_selection = len(element_ids) > 0
        
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)
        self.validate_btn.setEnabled(True)
    
    def _emit_action(self, action: HierarchyToolAction):
        """Emit action signal."""
        self.action_requested.emit(action, [])
    
    def _on_config_changed(self):
        """Handle configuration change."""
        self.config.show_element_types = self.show_types_cb.isChecked()
        self.config.show_element_bounds = self.show_bounds_cb.isChecked()
        self.config_changed.emit(self.config)


class HierarchyToolsWidget(QWidget):
    """Main widget for hierarchy management tools."""
    
    element_selected = pyqtSignal(str)
    element_changed = pyqtSignal(str)
    validation_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.event_bus = None
        self.selected_elements = []
        
>>>>>>> origin/main
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
<<<<<<< HEAD
        """Initialize UI components"""
        layout = QHBoxLayout(self)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Tree and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Tree widget
        self.tree_widget = HierarchyTreeWidget(self.state_manager, self.event_bus)
        left_layout.addWidget(self.tree_widget, 1)  # Give it more space
        
        # Control panel
        self.control_panel = HierarchyControlPanel(self.tree_widget)
        left_layout.addWidget(self.control_panel)
        
        splitter.addWidget(left_widget)
        
        # Right side - Metrics and validation
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Metrics widget
        self.metrics_widget = HierarchyMetricsWidget()
        right_layout.addWidget(self.metrics_widget)
        
        # Validation feedback (placeholder for future expansion)
        validation_group = QGroupBox("Validation Feedback")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validation_label = QLabel("Hierarchy validation will appear here")
        self.validation_label.setStyleSheet("color: #666666; font-style: italic; padding: 10px;")
        validation_layout.addWidget(self.validation_label)
        
        right_layout.addWidget(validation_group)
        right_layout.addStretch()  # Push everything to top
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions (70% tree, 30% metrics)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect component signals"""
        # Tree signals
        self.tree_widget.hierarchy_changed.connect(self._on_hierarchy_changed)
        self.tree_widget.validation_changed.connect(self._on_validation_changed)
        
        # Control panel signals
        self.control_panel.operation_requested.connect(self._on_operation_requested)
        
        # State manager events
        self.event_bus.subscribe("hierarchy_updated", self._on_hierarchy_updated)
        self.event_bus.subscribe("elements_changed", self._on_elements_changed)
    
    def load_hierarchy(self, hierarchy: ElementHierarchy):
        """Load hierarchy into tools"""
        self.hierarchy = hierarchy
        self.tree_widget.load_hierarchy(hierarchy)
        
        # Calculate and update metrics
        metrics = self._calculate_metrics(hierarchy)
        self.metrics_widget.update_metrics(metrics)
    
    def _calculate_metrics(self, hierarchy: ElementHierarchy) -> HierarchyMetrics:
        """Calculate hierarchy metrics"""
        if not hierarchy:
            return HierarchyMetrics()
        
        metrics = HierarchyMetrics()
        metrics.total_elements = len(hierarchy.elements)
        
        # Calculate max depth
        max_depth = 0
        for element_id in hierarchy.elements:
            depth = hierarchy.get_depth(element_id)
            max_depth = max(max_depth, depth)
        metrics.depth_levels = max_depth
        
        # Count orphaned elements
        orphaned = 0
        for element in hierarchy.elements.values():
            if element.parent_id and element.parent_id not in hierarchy.elements:
                orphaned += 1
        metrics.orphaned_elements = orphaned
        
        # Validation errors
        errors = hierarchy.validate_hierarchy()
        metrics.validation_errors = len(errors)
        
        # Circular references (count from errors)
        circular = sum(1 for error in errors if "circular" in error.lower())
        metrics.circular_references = circular
        
        return metrics
    
    def _on_hierarchy_changed(self, element_id: str, operation: str):
        """Handle hierarchy change events"""
        logger.info(f"Hierarchy changed: {element_id} - {operation}")
        
        # Recalculate metrics
        if self.hierarchy:
            metrics = self._calculate_metrics(self.hierarchy)
            self.metrics_widget.update_metrics(metrics)
        
        # Emit state change
        self.event_bus.emit("hierarchy_modified", {
            "element_id": element_id,
            "operation": operation
        })
    
    def _on_validation_changed(self, element_id: str, level: ValidationLevel):
        """Handle validation level changes"""
        logger.info(f"Validation changed: {element_id} - {level}")
    
    def _on_operation_requested(self, operation: HierarchyOperation, element_ids: List[str]):
        """Handle operation requests from control panel"""
        logger.info(f"Operation requested: {operation} on {element_ids}")
        
        # Perform operation on tree widget
        self.tree_widget.perform_operation(operation, element_ids)
    
    def _on_hierarchy_updated(self, event_data: Dict[str, Any]):
        """Handle hierarchy update events from state"""
        if "hierarchy" in event_data:
            self.load_hierarchy(event_data["hierarchy"])
    
    def _on_elements_changed(self, event_data: Dict[str, Any]):
        """Handle element change events"""
        # Reload current hierarchy to reflect changes
        if self.hierarchy:
            self.tree_widget.load_hierarchy(self.hierarchy)
    
    def get_selected_elements(self) -> List[str]:
        """Get currently selected element IDs"""
        return self.tree_widget.get_selected_elements()
    
    def select_elements(self, element_ids: List[str]):
        """Select specific elements"""
        self.tree_widget.select_elements(element_ids)
=======
        """Set up the UI."""
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.tree_widget = HierarchyTreeWidget()
        splitter.addWidget(self.tree_widget)
        
        self.control_panel = HierarchyControlPanel()
        splitter.addWidget(self.control_panel)
        
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.tree_widget.element_selected.connect(self._on_element_selected)
        self.control_panel.action_requested.connect(self._on_action_requested)
        self.control_panel.config_changed.connect(self._on_config_changed)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
        self.tree_widget.set_hierarchy_manager(manager)
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
        self.tree_widget.set_state_store(store)
    
    def set_event_bus(self, bus: EventBus):
        """Set the event bus."""
        self.event_bus = bus
    
    def refresh(self):
        """Refresh the hierarchy display."""
        self.tree_widget.refresh_hierarchy()
    
    def select_element(self, element_id: str):
        """Select an element."""
        self.tree_widget.select_element(element_id)
    
    def _on_element_selected(self, element_id: str):
        """Handle element selection."""
        self.selected_elements = [element_id]
        self.control_panel.set_selected_elements(self.selected_elements)
        self.element_selected.emit(element_id)
    
    def _on_action_requested(self, action: HierarchyToolAction, element_ids: List[str]):
        """Handle action request."""
        if action == HierarchyToolAction.VALIDATE:
            self.validation_requested.emit()
    
    def _on_config_changed(self, config: HierarchyDisplayConfig):
        """Handle configuration change."""
        pass
>>>>>>> origin/main
