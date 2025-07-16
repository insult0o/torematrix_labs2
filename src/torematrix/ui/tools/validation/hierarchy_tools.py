"""
Interactive hierarchy management UI tools for manual validation.

Agent 2 implementation for Issue #241 - Interactive Hierarchy UI Tools.
Provides drag-drop tree widgets, control panels, and visual feedback
for hierarchy manipulation and validation in manual validation workflows.
"""

from typing import Dict, List, Optional, Set, Union, Any, Callable
from dataclasses import dataclass
from enum import Enum, auto
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QFrame, QSplitter, QGroupBox,
    QScrollArea, QTabWidget, QProgressBar, QMessageBox, QMenu,
    QHeaderView, QAbstractItemView, QStyleOptionViewItem,
    QStyledItemDelegate, QApplication, QStyle, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QTextEdit, QDialog
)
from PyQt6.QtCore import (
    Qt, QMimeData, QByteArray, pyqtSignal, QTimer, QRect,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QModelIndex, QPoint, QSize, QObject, QThread
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap, QIcon,
    QDrag, QPalette, QFontMetrics, QLinearGradient, QAction
)

# Import hierarchy models
from ....core.models.element import Element, ElementType
from ....core.models.hierarchy import ElementHierarchy, ElementRelationship, RelationshipType
from ....core.state import Store  
from ....core.events import EventBus

logger = logging.getLogger(__name__)


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
    VALIDATE = auto()       # Validate hierarchy
    REFRESH = auto()        # Refresh display


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
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
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
        return QSize(size.width() + 25, max(size.height(), 24))


class HierarchyTreeWidget(QTreeWidget):
    """Drag-drop enabled tree widget for hierarchy manipulation"""
    
    # Signals
    hierarchy_changed = pyqtSignal(str, str)  # element_id, operation
    validation_changed = pyqtSignal(str, ValidationLevel)  # element_id, level
    selection_changed = pyqtSignal(list)  # selected_element_ids
    element_double_clicked = pyqtSignal(str)  # element_id
    
    def __init__(self, state_manager: Store, event_bus: EventBus, parent=None):
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
        self.setHeaderLabels(["Element", "Type", "Status", "Depth"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAnimated(True)
        self.setIndentation(20)
        
        # Set custom delegate
        self.setItemDelegate(HierarchyTreeDelegate(self))
        
        # Configure columns
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Style the widget
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e3f2fd;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border-bottom: 1px solid #f5f5f5;
                min-height: 24px;
            }
            QTreeWidget::item:selected {
                background-color: #2196f3;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
            QTreeWidget::branch {
                background-color: white;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(:/icons/branch-closed.png);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(:/icons/branch-open.png);
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
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
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
    
    def _build_tree_structure(self):
        """Build the tree structure from hierarchy"""
        if not self.hierarchy:
            return
        
        # Create items for root elements first
        root_elements = self.hierarchy.get_root_elements()
        
        for element in root_elements:
            item = self._create_tree_item(element)
            self.addTopLevelItem(item)
            self._add_children_recursive(element, item)
    
    def _create_tree_item(self, element: Element) -> QTreeWidgetItem:
        """Create tree widget item for element"""
        item = QTreeWidgetItem()
        
        # Set display data
        text = element.text if hasattr(element, 'text') else str(element)
        if len(text) > 50:
            text = text[:47] + "..."
        item.setText(0, text)
        
        # Element type
        element_type = element.element_type if hasattr(element, 'element_type') else ElementType.TEXT
        item.setText(1, element_type.value if element_type else "Unknown")
        
        # Status
        item.setText(2, "Valid")  # Default status
        
        # Depth
        depth = self.hierarchy.get_depth(element.element_id) if self.hierarchy else 0
        item.setText(3, str(depth))
        
        # Store element reference
        element_id = element.element_id if hasattr(element, 'element_id') else str(id(element))
        item.setData(0, Qt.ItemDataRole.UserRole, element_id)
        
        # Set validation level
        validation_level = self.validation_cache.get(element_id, ValidationLevel.VALID)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, validation_level)
        
        # Set icon based on element type
        if element_type:
            item.setIcon(0, self._get_element_icon(element_type))
        
        # Store in lookup
        self.element_items[element_id] = item
        
        return item
    
    def _add_children_recursive(self, parent_element: Element, parent_item: QTreeWidgetItem):
        """Recursively add children to tree item"""
        if not self.hierarchy:
            return
        
        element_id = parent_element.element_id if hasattr(parent_element, 'element_id') else str(id(parent_element))
        children = self.hierarchy.get_children(element_id)
        
        for child_element in children:
            child_item = self._create_tree_item(child_element)
            parent_item.addChild(child_item)
            self._add_children_recursive(child_element, child_item)
    
    def _get_element_icon(self, element_type: ElementType) -> QIcon:
        """Get icon for element type"""
        # Create simple colored icons for different types
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color mapping for element types
        type_colors = {
            ElementType.TITLE: QColor(63, 81, 181),      # Indigo
            ElementType.TEXT: QColor(76, 175, 80),       # Green
            ElementType.LIST: QColor(255, 152, 0),       # Orange
            ElementType.TABLE: QColor(156, 39, 176),     # Purple
            ElementType.IMAGE: QColor(244, 67, 54),      # Red
            ElementType.FIGURE: QColor(3, 169, 244),     # Light Blue
        }
        
        color = type_colors.get(element_type, QColor(158, 158, 158))  # Default gray
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        
        painter.end()
        return QIcon(pixmap)
    
    def _validate_hierarchy(self):
        """Validate current hierarchy and update status"""
        if not self.hierarchy:
            return
        
        # Clear validation cache
        self.validation_cache.clear()
        
        # Run hierarchy validation
        errors = self.hierarchy.validate_hierarchy()
        
        # Process validation results
        for error in errors:
            # Extract element ID from error message (simplified)
            if "Element" in error:
                parts = error.split()
                if len(parts) > 1:
                    element_id = parts[1]
                    self.validation_cache[element_id] = ValidationLevel.ERROR
        
        # Check for other validation issues
        for element in self.hierarchy.elements.values():
            element_id = element.element_id if hasattr(element, 'element_id') else str(id(element))
            
            if element_id not in self.validation_cache:
                # Check for potential issues
                depth = self.hierarchy.get_depth(element_id)
                children_count = len(self.hierarchy.get_children(element_id))
                
                if depth > 5:  # Very deep nesting
                    self.validation_cache[element_id] = ValidationLevel.WARNING
                elif children_count > 10:  # Too many children
                    self.validation_cache[element_id] = ValidationLevel.WARNING
                else:
                    self.validation_cache[element_id] = ValidationLevel.VALID
        
        # Update tree items
        for element_id, level in self.validation_cache.items():
            if element_id in self.element_items:
                item = self.element_items[element_id]
                item.setData(0, Qt.ItemDataRole.UserRole + 1, level)
                
                # Update status text
                status_text = {
                    ValidationLevel.VALID: "Valid",
                    ValidationLevel.WARNING: "Warning", 
                    ValidationLevel.ERROR: "Error",
                    ValidationLevel.CRITICAL: "Critical"
                }
                item.setText(2, status_text[level])
        
        # Update display
        self.update()
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.selectedItems()
        selected_ids = []
        
        for item in selected_items:
            element_id = item.data(0, Qt.ItemDataRole.UserRole)
            if element_id:
                selected_ids.append(element_id)
        
        self.selection_changed.emit(selected_ids)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item changes"""
        if column == 0:  # Text column
            element_id = item.data(0, Qt.ItemDataRole.UserRole)
            if element_id:
                self.hierarchy_changed.emit(element_id, "text_changed")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double-click"""
        element_id = item.data(0, Qt.ItemDataRole.UserRole)
        if element_id:
            self.element_double_clicked.emit(element_id)
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu at position"""
        item = self.itemAt(position)
        if not item:
            return
        
        selected_items = self.selectedItems()
        selected_count = len(selected_items)
        
        menu = QMenu(self)
        
        # Single item operations
        if selected_count == 1:
            element_id = item.data(0, Qt.ItemDataRole.UserRole)
            element = self.hierarchy.elements.get(element_id) if self.hierarchy else None
            
            if element:
                # Basic operations
                indent_action = menu.addAction("Indent →")
                indent_action.setIcon(self._create_action_icon("#2196f3"))
                indent_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.INDENT))
                
                outdent_action = menu.addAction("← Outdent")
                outdent_action.setIcon(self._create_action_icon("#2196f3"))
                outdent_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.OUTDENT))
                
                menu.addSeparator()
                
                # Move operations
                move_up_action = menu.addAction("Move Up ↑")
                move_up_action.setIcon(self._create_action_icon("#4caf50"))
                move_up_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.MOVE_UP))
                
                move_down_action = menu.addAction("Move Down ↓")
                move_down_action.setIcon(self._create_action_icon("#4caf50"))
                move_down_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.MOVE_DOWN))
                
                menu.addSeparator()
                
                # Edit operations
                duplicate_action = menu.addAction("Duplicate")
                duplicate_action.setIcon(self._create_action_icon("#ff9800"))
                duplicate_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.DUPLICATE))
                
                # Check if element can be ungrouped (has children)
                children = self.hierarchy.get_children(element_id)
                if children:
                    ungroup_action = menu.addAction("Ungroup")
                    ungroup_action.setIcon(self._create_action_icon("#9c27b0"))
                    ungroup_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.UNGROUP))
                
                menu.addSeparator()
                
                # Validation operations
                validate_action = menu.addAction("Validate Element")
                validate_action.setIcon(self._create_action_icon("#607d8b"))
                validate_action.triggered.connect(lambda: self._validate_element(element_id))
                
                # Element details
                details_action = menu.addAction("Show Details...")
                details_action.setIcon(self._create_action_icon("#795548"))
                details_action.triggered.connect(lambda: self._show_element_details(element))
                
                menu.addSeparator()
                
                # Danger zone
                delete_action = menu.addAction("Delete")
                delete_action.setIcon(self._create_action_icon("#f44336"))
                delete_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.DELETE))
        
        # Multiple item operations
        elif selected_count > 1:
            # Group operation
            group_action = menu.addAction(f"Group {selected_count} Elements")
            group_action.setIcon(self._create_action_icon("#9c27b0"))
            group_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.GROUP))
            
            menu.addSeparator()
            
            # Batch operations
            batch_indent_action = menu.addAction("Indent All →")
            batch_indent_action.setIcon(self._create_action_icon("#2196f3"))
            batch_indent_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.INDENT))
            
            batch_outdent_action = menu.addAction("← Outdent All")
            batch_outdent_action.setIcon(self._create_action_icon("#2196f3"))
            batch_outdent_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.OUTDENT))
            
            menu.addSeparator()
            
            # Danger operations
            delete_all_action = menu.addAction(f"Delete {selected_count} Elements")
            delete_all_action.setIcon(self._create_action_icon("#f44336"))
            delete_all_action.triggered.connect(lambda: self._context_operation(HierarchyOperation.DELETE))
        
        # Show menu
        global_pos = self.mapToGlobal(position)
        menu.exec(global_pos)
    
    def _create_action_icon(self, color: str) -> QIcon:
        """Create a simple colored icon for menu actions"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        return QIcon(pixmap)
    
    def _context_operation(self, operation: HierarchyOperation):
        """Perform operation from context menu"""
        selected_ids = self.get_selected_elements()
        if selected_ids:
            self.perform_operation(operation, selected_ids)
    
    def _validate_element(self, element_id: str):
        """Validate specific element"""
        if not self.hierarchy or element_id not in self.hierarchy.elements:
            return
        
        # Run validation on this element
        element = self.hierarchy.elements[element_id]
        validation_level = ValidationLevel.VALID
        validation_messages = []
        
        # Check depth
        depth = self.hierarchy.get_depth(element_id)
        if depth > 5:
            validation_level = ValidationLevel.WARNING
            validation_messages.append(f"Deep nesting (level {depth})")
        
        # Check children count
        children = self.hierarchy.get_children(element_id)
        if len(children) > 10:
            validation_level = ValidationLevel.WARNING
            validation_messages.append(f"Many children ({len(children)})")
        
        # Check for orphaned references
        parent_id = getattr(element, 'parent_id', None)
        if parent_id and parent_id not in self.hierarchy.elements:
            validation_level = ValidationLevel.ERROR
            validation_messages.append("References non-existent parent")
        
        # Update validation cache and display
        self.validation_cache[element_id] = validation_level
        if element_id in self.element_items:
            item = self.element_items[element_id]
            item.setData(0, Qt.ItemDataRole.UserRole + 1, validation_level)
            
            status_text = {
                ValidationLevel.VALID: "Valid",
                ValidationLevel.WARNING: "Warning",
                ValidationLevel.ERROR: "Error",
                ValidationLevel.CRITICAL: "Critical"
            }
            item.setText(2, status_text[validation_level])
        
        # Show validation results
        element_text = getattr(element, 'text', str(element))
        if validation_messages:
            message_text = "\n".join(validation_messages)
            QMessageBox.information(self, "Element Validation", 
                                  f"Element: {element_text[:30]}...\n\n{message_text}")
        else:
            QMessageBox.information(self, "Element Validation", 
                                  f"Element: {element_text[:30]}...\n\nNo validation issues found.")
        
        self.update()
        self.validation_changed.emit(element_id, validation_level)
    
    def _show_element_details(self, element: Element):
        """Show detailed element information"""
        if not self.hierarchy:
            return
        
        element_id = getattr(element, 'element_id', str(id(element)))
        element_text = getattr(element, 'text', str(element))
        element_type = getattr(element, 'element_type', ElementType.TEXT)
        
        # Gather element details
        depth = self.hierarchy.get_depth(element_id)
        children = self.hierarchy.get_children(element_id)
        parent = self.hierarchy.get_parent(element_id)
        siblings = self.hierarchy.get_siblings(element_id)
        
        parent_text = getattr(parent, 'text', 'None (Root element)') if parent else 'None (Root element)'
        
        details = f"""Element Details:
        
ID: {element_id}
Type: {element_type.value if element_type else 'Unknown'}
Text: {element_text[:100]}{'...' if len(element_text) > 100 else ''}

Hierarchy Information:
• Depth: {depth}
• Children: {len(children)}
• Siblings: {len(siblings)}
• Parent: {parent_text[:30] + '...' if parent and len(parent_text) > 30 else parent_text}

Validation: {self.validation_cache.get(element_id, ValidationLevel.VALID).name}
"""
        
        QMessageBox.information(self, "Element Details", details)
    
    def perform_operation(self, operation: HierarchyOperation, element_ids: List[str]):
        """Perform hierarchy operation on selected elements"""
        if not self.hierarchy or not element_ids:
            return
        
        try:
            if operation == HierarchyOperation.INDENT:
                self._indent_elements(element_ids)
            elif operation == HierarchyOperation.OUTDENT:
                self._outdent_elements(element_ids)
            elif operation == HierarchyOperation.MOVE_UP:
                self._move_elements_up(element_ids)
            elif operation == HierarchyOperation.MOVE_DOWN:
                self._move_elements_down(element_ids)
            elif operation == HierarchyOperation.GROUP:
                self._group_elements(element_ids)
            elif operation == HierarchyOperation.DELETE:
                self._delete_elements(element_ids)
            elif operation == HierarchyOperation.VALIDATE:
                self._validate_hierarchy()
            elif operation == HierarchyOperation.REFRESH:
                self.load_hierarchy(self.hierarchy)
            
            # Reload hierarchy display
            self.load_hierarchy(self.hierarchy)
            
            # Emit change signal
            for element_id in element_ids:
                self.hierarchy_changed.emit(element_id, operation.name.lower())
            
        except Exception as e:
            logger.error(f"Error performing hierarchy operation {operation}: {e}")
            QMessageBox.warning(self, "Operation Failed", f"Failed to perform operation: {str(e)}")
    
    def _indent_elements(self, element_ids: List[str]):
        """Indent elements (make them children of previous sibling)"""
        for element_id in element_ids:
            element = self.hierarchy.elements.get(element_id)
            if not element:
                continue
            
            # Find previous sibling
            siblings = self.hierarchy.get_siblings(element_id)
            current_index = next((i for i, sib in enumerate(siblings) 
                                if getattr(sib, 'element_id', str(id(sib))) == element_id), -1)
            
            if current_index > 0:
                new_parent = siblings[current_index - 1]
                new_parent_id = getattr(new_parent, 'element_id', str(id(new_parent)))
                # Update element parent
                if hasattr(element, 'parent_id'):
                    element.parent_id = new_parent_id
    
    def _outdent_elements(self, element_ids: List[str]):
        """Outdent elements (move them up one level)"""
        for element_id in element_ids:
            element = self.hierarchy.elements.get(element_id)
            if not element or not getattr(element, 'parent_id', None):
                continue
            
            # Get grandparent
            parent_id = getattr(element, 'parent_id', None)
            parent = self.hierarchy.elements.get(parent_id) if parent_id else None
            if parent:
                grandparent_id = getattr(parent, 'parent_id', None)
                if hasattr(element, 'parent_id'):
                    element.parent_id = grandparent_id  # Could be None for root level
    
    def _move_elements_up(self, element_ids: List[str]):
        """Move elements up in sibling order"""
        # This would require more complex reordering logic
        # For now, just emit the change signal
        pass
    
    def _move_elements_down(self, element_ids: List[str]):
        """Move elements down in sibling order"""
        # This would require more complex reordering logic
        # For now, just emit the change signal
        pass
    
    def _group_elements(self, element_ids: List[str]):
        """Group elements under a new parent"""
        if len(element_ids) < 2:
            return
        
        # Create new group element (simplified)
        import uuid
        group_id = str(uuid.uuid4())
        
        # This would need integration with element creation system
        # For now, just emit the change signal
        pass
    
    def _delete_elements(self, element_ids: List[str]):
        """Delete elements from hierarchy"""
        for element_id in element_ids:
            if element_id in self.hierarchy.elements:
                # Move children to parent level
                children = self.hierarchy.get_children(element_id)
                element = self.hierarchy.elements[element_id]
                
                parent_id = getattr(element, 'parent_id', None)
                for child in children:
                    if hasattr(child, 'parent_id'):
                        child.parent_id = parent_id
                
                # Remove element
                del self.hierarchy.elements[element_id]
    
    def get_selected_elements(self) -> List[str]:
        """Get currently selected element IDs"""
        selected_items = self.selectedItems()
        return [item.data(0, Qt.ItemDataRole.UserRole) for item in selected_items 
                if item.data(0, Qt.ItemDataRole.UserRole)]
    
    def select_elements(self, element_ids: List[str]):
        """Select specific elements in tree"""
        self.clearSelection()
        
        for element_id in element_ids:
            if element_id in self.element_items:
                item = self.element_items[element_id]
                item.setSelected(True)


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
        
        # Validation and utility buttons
        util_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setToolTip("Validate hierarchy")
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh hierarchy display")
        
        util_layout.addWidget(self.validate_btn)
        util_layout.addWidget(self.refresh_btn)
        operations_layout.addLayout(util_layout)
        
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
        self.validate_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.VALIDATE))
        self.refresh_btn.clicked.connect(lambda: self._request_operation(HierarchyOperation.REFRESH))
        
        # Connect to tree selection changes
        self.tree_widget.selection_changed.connect(self._on_selection_changed)
    
    def _request_operation(self, operation: HierarchyOperation):
        """Request hierarchy operation"""
        if operation in [HierarchyOperation.VALIDATE, HierarchyOperation.REFRESH]:
            # These operations don't require selection
            self.operation_requested.emit(operation, [])
        elif self.selected_elements:
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
        
        # Utility operations always enabled
        self.validate_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
    
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
        self.updated_label = QLabel("Last Updated: Never")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.depth_label)
        stats_layout.addWidget(self.orphans_label)
        stats_layout.addWidget(self.errors_label)
        stats_layout.addWidget(self.updated_label)
        
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
        
        # Format timestamp
        if metrics.last_updated:
            time_str = metrics.last_updated.strftime("%H:%M:%S")
            self.updated_label.setText(f"Last Updated: {time_str}")
        
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
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class HierarchyToolsWidget(QWidget):
    """Main container widget for hierarchy tools"""
    
    # Signals
    element_selected = pyqtSignal(str)
    hierarchy_modified = pyqtSignal(dict)
    
    def __init__(self, state_manager: Store, event_bus: EventBus, parent=None):
        super().__init__(parent)
        
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.hierarchy: Optional[ElementHierarchy] = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
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
        
        # Validation feedback
        validation_group = QGroupBox("Validation Feedback")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validation_text = QTextEdit()
        self.validation_text.setMaximumHeight(150)
        self.validation_text.setReadOnly(True)
        self.validation_text.setPlainText("Hierarchy validation will appear here...")
        validation_layout.addWidget(self.validation_text)
        
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
        self.tree_widget.selection_changed.connect(self._on_selection_changed)
        self.tree_widget.element_double_clicked.connect(self.element_selected.emit)
        
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
        
        # Update validation feedback
        self._update_validation_feedback(hierarchy)
    
    def _calculate_metrics(self, hierarchy: ElementHierarchy) -> HierarchyMetrics:
        """Calculate hierarchy metrics"""
        if not hierarchy:
            return HierarchyMetrics()
        
        metrics = HierarchyMetrics()
        metrics.total_elements = len(hierarchy.elements)
        metrics.last_updated = datetime.now()
        
        # Calculate max depth
        max_depth = 0
        for element_id in hierarchy.elements:
            depth = hierarchy.get_depth(element_id)
            max_depth = max(max_depth, depth)
        metrics.depth_levels = max_depth
        
        # Count orphaned elements
        orphaned = 0
        for element in hierarchy.elements.values():
            parent_id = getattr(element, 'parent_id', None)
            if parent_id and parent_id not in hierarchy.elements:
                orphaned += 1
        metrics.orphaned_elements = orphaned
        
        # Validation errors
        errors = hierarchy.validate_hierarchy()
        metrics.validation_errors = len(errors)
        
        # Circular references (count from errors)
        circular = sum(1 for error in errors if "circular" in error.lower())
        metrics.circular_references = circular
        
        return metrics
    
    def _update_validation_feedback(self, hierarchy: ElementHierarchy):
        """Update validation feedback display"""
        if not hierarchy:
            self.validation_text.setPlainText("No hierarchy loaded.")
            return
        
        errors = hierarchy.validate_hierarchy()
        
        if not errors:
            self.validation_text.setPlainText("✅ Hierarchy validation passed!\nNo issues found.")
        else:
            feedback_lines = ["⚠️ Hierarchy validation issues found:\n"]
            for i, error in enumerate(errors, 1):
                feedback_lines.append(f"{i}. {error}")
            
            self.validation_text.setPlainText("\n".join(feedback_lines))
    
    def _on_hierarchy_changed(self, element_id: str, operation: str):
        """Handle hierarchy change events"""
        logger.info(f"Hierarchy changed: {element_id} - {operation}")
        
        # Recalculate metrics
        if self.hierarchy:
            metrics = self._calculate_metrics(self.hierarchy)
            self.metrics_widget.update_metrics(metrics)
            
            # Update validation feedback
            self._update_validation_feedback(self.hierarchy)
        
        # Emit state change
        self.hierarchy_modified.emit({
            "element_id": element_id,
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        })
        
        # Notify event bus
        self.event_bus.emit("hierarchy_modified", {
            "element_id": element_id,
            "operation": operation
        })
    
    def _on_validation_changed(self, element_id: str, level: ValidationLevel):
        """Handle validation level changes"""
        logger.info(f"Validation changed: {element_id} - {level}")
    
    def _on_selection_changed(self, element_ids: List[str]):
        """Handle selection changes"""
        if element_ids:
            # Emit first selected element
            self.element_selected.emit(element_ids[0])
    
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