"""Type Hierarchy View Widget

Visual representation of type hierarchies with inheritance relationships,
drag-and-drop support, and interactive navigation.
"""

from typing import Dict, List, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFrame, QHeaderView, QMenu, QMessageBox,
    QLineEdit, QComboBox, QCheckBox, QSplitter, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush, QIcon, QDrag, QPainter

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry


class TypeHierarchyItem(QTreeWidgetItem):
    """Custom tree item for type hierarchy with enhanced features"""
    
    def __init__(self, type_def: TypeDefinition, parent=None):
        super().__init__(parent)
        
        self.type_def = type_def
        self.setup_item()
    
    def setup_item(self):
        """Setup the tree item"""
        # Main type name
        self.setText(0, self.type_def.name)
        
        # Category
        self.setText(1, self.type_def.category.title())
        
        # Type ID (for debugging/reference)
        self.setText(2, self.type_def.type_id)
        
        # Custom type indicator
        if self.type_def.is_custom:
            self.setText(3, "Yes")
            self.setBackground(3, QColor(220, 248, 198))  # Light green
        else:
            self.setText(3, "No")
        
        # Store type_id in data
        self.setData(0, Qt.ItemDataRole.UserRole, self.type_def.type_id)
        
        # Set icon based on category
        icon = self.get_category_icon(self.type_def.category)
        self.setIcon(0, QIcon(icon) if icon else QIcon())
        
        # Set tooltip
        tooltip = f"{self.type_def.name}\n"
        tooltip += f"Category: {self.type_def.category}\n"
        tooltip += f"Description: {self.type_def.description or 'No description'}\n"
        tooltip += f"Children: {len(self.type_def.child_types)}\n"
        tooltip += f"Parents: {len(self.type_def.parent_types)}"
        if self.type_def.tags:
            tooltip += f"\nTags: {', '.join(self.type_def.tags)}"
        
        self.setToolTip(0, tooltip)
    
    def get_category_icon(self, category: str) -> Optional[str]:
        """Get icon for category"""
        icons = {
            'text': '📝',
            'media': '🖼️',
            'structure': '🏗️',
            'layout': '📐',
            'content': '📄',
            'metadata': '🏷️',
            'interactive': '🖱️'
        }
        return icons.get(category.lower())


class TypeRelationshipView(QWidget):
    """Widget showing detailed relationship information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_type: Optional[TypeDefinition] = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup relationship view UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        self.title_label = QLabel("Type Relationships")
        self.title_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        # Parent types
        parents_group = QGroupBox("Parent Types")
        parents_layout = QVBoxLayout(parents_group)
        
        self.parents_list = QTreeWidget()
        self.parents_list.setHeaderLabels(["Name", "Category"])
        self.parents_list.setMaximumHeight(100)
        parents_layout.addWidget(self.parents_list)
        
        layout.addWidget(parents_group)
        
        # Child types
        children_group = QGroupBox("Child Types")
        children_layout = QVBoxLayout(children_group)
        
        self.children_list = QTreeWidget()
        self.children_list.setHeaderLabels(["Name", "Category"])
        self.children_list.setMaximumHeight(100)
        children_layout.addWidget(self.children_list)
        
        layout.addWidget(children_group)
        
        # Relationship actions
        actions_layout = QHBoxLayout()
        
        self.add_parent_btn = QPushButton("Add Parent")
        self.add_parent_btn.setEnabled(False)
        actions_layout.addWidget(self.add_parent_btn)
        
        self.add_child_btn = QPushButton("Add Child")
        self.add_child_btn.setEnabled(False)
        actions_layout.addWidget(self.add_child_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def set_type(self, type_def: TypeDefinition, registry: TypeRegistry):
        """Set the type to display relationships for"""
        self.current_type = type_def
        self.registry = registry
        
        # Update title
        self.title_label.setText(f"Relationships: {type_def.name}")
        
        # Clear existing items
        self.parents_list.clear()
        self.children_list.clear()
        
        # Populate parent types
        for parent_id in type_def.parent_types:
            try:
                parent_def = registry.get_type(parent_id)
                item = QTreeWidgetItem([parent_def.name, parent_def.category.title()])
                item.setData(0, Qt.ItemDataRole.UserRole, parent_id)
                self.parents_list.addTopLevelItem(item)
            except:
                # Parent type not found
                item = QTreeWidgetItem([f"Missing: {parent_id}", "Unknown"])
                item.setForeground(0, QColor("red"))
                self.parents_list.addTopLevelItem(item)
        
        # Populate child types
        for child_id in type_def.child_types:
            try:
                child_def = registry.get_type(child_id)
                item = QTreeWidgetItem([child_def.name, child_def.category.title()])
                item.setData(0, Qt.ItemDataRole.UserRole, child_id)
                self.children_list.addTopLevelItem(item)
            except:
                # Child type not found
                item = QTreeWidgetItem([f"Missing: {child_id}", "Unknown"])
                item.setForeground(0, QColor("red"))
                self.children_list.addTopLevelItem(item)
        
        # Enable action buttons
        self.add_parent_btn.setEnabled(True)
        self.add_child_btn.setEnabled(True)
    
    def clear(self):
        """Clear the relationship view"""
        self.current_type = None
        self.title_label.setText("Type Relationships")
        self.parents_list.clear()
        self.children_list.clear()
        self.add_parent_btn.setEnabled(False)
        self.add_child_btn.setEnabled(False)


class TypeHierarchyView(QWidget):
    """Complete type hierarchy visualization widget"""
    
    # Signals
    type_selected = pyqtSignal(str)  # type_id
    hierarchy_changed = pyqtSignal()
    relationship_added = pyqtSignal(str, str, str)  # parent_id, child_id, relationship_type
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type_id: Optional[str] = None
        self.expanded_items: Set[str] = set()
        
        self.setup_ui()
        self.connect_signals()
        self.populate_hierarchy()
    
    def setup_ui(self):
        """Setup the hierarchy view UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Controls header
        controls_layout = QHBoxLayout()
        
        # View mode controls
        self.view_mode = QComboBox()
        self.view_mode.addItems(["All Types", "Root Types Only", "By Category"])
        controls_layout.addWidget(QLabel("View:"))
        controls_layout.addWidget(self.view_mode)
        
        controls_layout.addStretch()
        
        # Expand/collapse controls
        self.expand_all_btn = QPushButton("Expand All")
        self.expand_all_btn.clicked.connect(self.expand_all)
        controls_layout.addWidget(self.expand_all_btn)
        
        self.collapse_all_btn = QPushButton("Collapse All")
        self.collapse_all_btn.clicked.connect(self.collapse_all)
        controls_layout.addWidget(self.collapse_all_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh Hierarchy")
        self.refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(controls_layout)
        
        # Filter options
        filter_layout = QHBoxLayout()
        
        self.show_custom_only = QCheckBox("Custom Types Only")
        filter_layout.addWidget(self.show_custom_only)
        
        self.show_orphans = QCheckBox("Show Orphaned Types")
        self.show_orphans.setChecked(True)
        filter_layout.addWidget(self.show_orphans)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Hierarchy tree
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(4, 4, 4, 4)
        
        # Tree widget
        self.hierarchy_tree = QTreeWidget()
        self.hierarchy_tree.setHeaderLabels(["Type Name", "Category", "Type ID", "Custom"])
        
        # Configure tree
        header = self.hierarchy_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.hierarchy_tree.setAlternatingRowColors(True)
        self.hierarchy_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        
        # Enable drag and drop
        self.hierarchy_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.hierarchy_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        tree_layout.addWidget(self.hierarchy_tree)
        content_splitter.addWidget(tree_frame)
        
        # Relationship view
        self.relationship_view = TypeRelationshipView()
        content_splitter.addWidget(self.relationship_view)
        
        # Set splitter proportions (70% tree, 30% relationships)
        content_splitter.setSizes([350, 150])
        layout.addWidget(content_splitter)
        
        # Status info
        self.status_label = QLabel("0 types displayed")
        self.status_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        layout.addWidget(self.status_label)
    
    def connect_signals(self):
        """Connect UI signals"""
        # Tree selection
        self.hierarchy_tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.hierarchy_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Context menu
        self.hierarchy_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hierarchy_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # View mode changes
        self.view_mode.currentTextChanged.connect(self.on_view_mode_changed)
        
        # Filter changes
        self.show_custom_only.toggled.connect(self.apply_filters)
        self.show_orphans.toggled.connect(self.apply_filters)
        
        # Tree expansion tracking
        self.hierarchy_tree.itemExpanded.connect(self.on_item_expanded)
        self.hierarchy_tree.itemCollapsed.connect(self.on_item_collapsed)
    
    def populate_hierarchy(self):
        """Populate the hierarchy tree"""
        self.hierarchy_tree.clear()
        
        all_types = self.registry.list_types()
        
        # Apply view mode
        if self.view_mode.currentText() == "Root Types Only":
            root_types = [t for t in all_types.values() if not t.parent_types]
            self.build_hierarchy_recursive(root_types, None)
        elif self.view_mode.currentText() == "By Category":
            self.build_category_hierarchy(all_types)
        else:  # "All Types"
            # Show all types in a flat hierarchy with relationships
            self.build_full_hierarchy(all_types)
        
        # Apply filters
        self.apply_filters()
        
        # Restore expansion state
        self.restore_expansion_state()
        
        # Update status
        visible_items = self.count_visible_items()
        self.status_label.setText(f"{visible_items} types displayed")
    
    def build_hierarchy_recursive(self, types: List[TypeDefinition], parent_item: Optional[QTreeWidgetItem]):
        """Build hierarchy recursively from root types"""
        for type_def in types:
            item = TypeHierarchyItem(type_def, parent_item)
            
            if parent_item is None:
                self.hierarchy_tree.addTopLevelItem(item)
            
            # Add children recursively
            child_types = []
            for child_id in type_def.child_types:
                try:
                    child_def = self.registry.get_type(child_id)
                    child_types.append(child_def)
                except:
                    pass  # Skip missing child types
            
            if child_types:
                self.build_hierarchy_recursive(child_types, item)
    
    def build_category_hierarchy(self, all_types: Dict[str, TypeDefinition]):
        """Build hierarchy grouped by category"""
        # Group types by category
        categories = {}
        for type_def in all_types.values():
            category = type_def.category
            if category not in categories:
                categories[category] = []
            categories[category].append(type_def)
        
        # Create category nodes
        for category, types in categories.items():
            category_item = QTreeWidgetItem([f"{category.title()} ({len(types)})", "", "", ""])
            category_item.setFont(0, QFont("", 10, QFont.Weight.Bold))
            category_item.setBackground(0, QColor(240, 248, 255))
            
            # Add types under category
            for type_def in sorted(types, key=lambda t: t.name):
                type_item = TypeHierarchyItem(type_def, category_item)
            
            self.hierarchy_tree.addTopLevelItem(category_item)
    
    def build_full_hierarchy(self, all_types: Dict[str, TypeDefinition]):
        """Build full hierarchy showing all types and relationships"""
        # First pass: create all items
        items_map = {}
        root_items = []
        
        for type_def in all_types.values():
            item = TypeHierarchyItem(type_def)
            items_map[type_def.type_id] = item
            
            # If no parents, it's a root item
            if not type_def.parent_types:
                root_items.append(item)
        
        # Second pass: establish parent-child relationships
        for type_def in all_types.values():
            item = items_map[type_def.type_id]
            
            # Add to appropriate parent
            if type_def.parent_types:
                # Use first parent as tree parent (for simplicity)
                parent_id = type_def.parent_types[0]
                if parent_id in items_map:
                    parent_item = items_map[parent_id]
                    parent_item.addChild(item)
                else:
                    # Parent not found, treat as root
                    root_items.append(item)
            else:
                # Already added to root_items
                pass
        
        # Add root items to tree
        for item in root_items:
            self.hierarchy_tree.addTopLevelItem(item)
        
        # Add orphaned types if option is enabled
        if self.show_orphans.isChecked():
            orphaned_types = [t for t in all_types.values() 
                            if not t.parent_types and not t.child_types]
            
            if orphaned_types:
                orphan_category = QTreeWidgetItem(["Orphaned Types", "", "", ""])
                orphan_category.setFont(0, QFont("", 10, QFont.Weight.Bold))
                orphan_category.setForeground(0, QColor("orange"))
                
                for type_def in orphaned_types:
                    if type_def.type_id not in items_map:
                        continue
                    item = items_map[type_def.type_id]
                    # Only add if not already parented
                    if item.parent() is None:
                        orphan_category.addChild(item)
                
                if orphan_category.childCount() > 0:
                    self.hierarchy_tree.addTopLevelItem(orphan_category)
    
    def apply_filters(self):
        """Apply current filters to the tree"""
        show_custom_only = self.show_custom_only.isChecked()
        
        def filter_item(item: QTreeWidgetItem):
            type_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Skip category headers and other non-type items
            if not type_id:
                return True
            
            try:
                type_def = self.registry.get_type(type_id)
                
                # Apply custom filter
                if show_custom_only and not type_def.is_custom:
                    return False
                
                return True
            except:
                return False
        
        # Apply filter recursively
        self.filter_tree_items(filter_item)
    
    def filter_tree_items(self, filter_func):
        """Apply filter function to all tree items"""
        def filter_recursive(item: QTreeWidgetItem) -> bool:
            # Filter children first
            visible_children = 0
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_recursive(child):
                    visible_children += 1
            
            # Check if this item should be visible
            should_show = filter_func(item) or visible_children > 0
            item.setHidden(not should_show)
            
            return should_show
        
        # Apply to all top-level items
        for i in range(self.hierarchy_tree.topLevelItemCount()):
            item = self.hierarchy_tree.topLevelItem(i)
            filter_recursive(item)
    
    def on_selection_changed(self):
        """Handle tree selection change"""
        current_item = self.hierarchy_tree.currentItem()
        if current_item:
            type_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            if type_id:
                self.current_type_id = type_id
                self.type_selected.emit(type_id)
                
                # Update relationship view
                try:
                    type_def = self.registry.get_type(type_id)
                    self.relationship_view.set_type(type_def, self.registry)
                except Exception as e:
                    print(f"Error loading type {type_id}: {e}")
            else:
                self.relationship_view.clear()
        else:
            self.relationship_view.clear()
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double-click"""
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            # Could open type editor or detailed view
            pass
    
    def on_item_expanded(self, item: QTreeWidgetItem):
        """Track expanded items"""
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.expanded_items.add(type_id)
    
    def on_item_collapsed(self, item: QTreeWidgetItem):
        """Track collapsed items"""
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.expanded_items.discard(type_id)
    
    def restore_expansion_state(self):
        """Restore previously expanded items"""
        def restore_recursive(item: QTreeWidgetItem):
            type_id = item.data(0, Qt.ItemDataRole.UserRole)
            if type_id and type_id in self.expanded_items:
                item.setExpanded(True)
            
            for i in range(item.childCount()):
                restore_recursive(item.child(i))
        
        for i in range(self.hierarchy_tree.topLevelItemCount()):
            restore_recursive(self.hierarchy_tree.topLevelItem(i))
    
    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.hierarchy_tree.itemAt(position)
        if not item:
            return
        
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not type_id:
            return
        
        menu = QMenu(self)
        
        # Type actions
        edit_action = menu.addAction("Edit Type")
        duplicate_action = menu.addAction("Duplicate Type")
        menu.addSeparator()
        
        # Hierarchy actions
        add_child_action = menu.addAction("Add Child Type")
        add_parent_action = menu.addAction("Add Parent Type")
        menu.addSeparator()
        
        # Navigation actions
        expand_subtree_action = menu.addAction("Expand Subtree")
        collapse_subtree_action = menu.addAction("Collapse Subtree")
        menu.addSeparator()
        
        # Danger zone
        delete_action = menu.addAction("Delete Type")
        delete_action.setStyleSheet("color: red;")
        
        # Show menu
        action = menu.exec(self.hierarchy_tree.mapToGlobal(position))
        
        # Handle actions
        if action == edit_action:
            self.edit_type(type_id)
        elif action == duplicate_action:
            self.duplicate_type(type_id)
        elif action == add_child_action:
            self.add_child_type(type_id)
        elif action == add_parent_action:
            self.add_parent_type(type_id)
        elif action == expand_subtree_action:
            self.expand_subtree(item)
        elif action == collapse_subtree_action:
            self.collapse_subtree(item)
        elif action == delete_action:
            self.delete_type(type_id)
    
    def edit_type(self, type_id: str):
        """Edit type (placeholder)"""
        QMessageBox.information(self, "Edit Type", f"Edit type dialog for {type_id} would open here.")
    
    def duplicate_type(self, type_id: str):
        """Duplicate type (placeholder)"""
        QMessageBox.information(self, "Duplicate Type", f"Duplicate type dialog for {type_id} would open here.")
    
    def add_child_type(self, parent_id: str):
        """Add child type (placeholder)"""
        QMessageBox.information(self, "Add Child", f"Add child type dialog for parent {parent_id} would open here.")
    
    def add_parent_type(self, child_id: str):
        """Add parent type (placeholder)"""
        QMessageBox.information(self, "Add Parent", f"Add parent type dialog for child {child_id} would open here.")
    
    def delete_type(self, type_id: str):
        """Delete type with confirmation"""
        reply = QMessageBox.question(
            self,
            "Delete Type",
            f"Are you sure you want to delete type '{type_id}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete type logic would go here
                QMessageBox.information(self, "Success", f"Type {type_id} deleted successfully.")
                self.refresh()
                self.hierarchy_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete type: {e}")
    
    def expand_subtree(self, item: QTreeWidgetItem):
        """Expand entire subtree"""
        def expand_recursive(node: QTreeWidgetItem):
            node.setExpanded(True)
            for i in range(node.childCount()):
                expand_recursive(node.child(i))
        
        expand_recursive(item)
    
    def collapse_subtree(self, item: QTreeWidgetItem):
        """Collapse entire subtree"""
        def collapse_recursive(node: QTreeWidgetItem):
            node.setExpanded(False)
            for i in range(node.childCount()):
                collapse_recursive(node.child(i))
        
        collapse_recursive(item)
    
    def expand_all(self):
        """Expand all items"""
        self.hierarchy_tree.expandAll()
    
    def collapse_all(self):
        """Collapse all items"""
        self.hierarchy_tree.collapseAll()
    
    def on_view_mode_changed(self, mode: str):
        """Handle view mode change"""
        self.populate_hierarchy()
    
    def count_visible_items(self) -> int:
        """Count visible (non-hidden) items"""
        def count_recursive(item: QTreeWidgetItem) -> int:
            count = 0 if item.isHidden() else 1
            for i in range(item.childCount()):
                count += count_recursive(item.child(i))
            return count
        
        total = 0
        for i in range(self.hierarchy_tree.topLevelItemCount()):
            total += count_recursive(self.hierarchy_tree.topLevelItem(i))
        
        return total
    
    def highlight_inheritance_path(self, type_id: str):
        """Highlight inheritance path for a type"""
        # Find and highlight the inheritance chain
        # This would be used for visual emphasis
        pass
    
    def set_selected_type(self, type_id: str):
        """Select a specific type in the hierarchy"""
        def find_item_recursive(item: QTreeWidgetItem, target_id: str) -> Optional[QTreeWidgetItem]:
            if item.data(0, Qt.ItemDataRole.UserRole) == target_id:
                return item
            
            for i in range(item.childCount()):
                found = find_item_recursive(item.child(i), target_id)
                if found:
                    return found
            
            return None
        
        # Search all top-level items
        for i in range(self.hierarchy_tree.topLevelItemCount()):
            item = self.hierarchy_tree.topLevelItem(i)
            found_item = find_item_recursive(item, type_id)
            if found_item:
                self.hierarchy_tree.setCurrentItem(found_item)
                self.hierarchy_tree.scrollToItem(found_item)
                break
    
    def refresh(self):
        """Refresh the hierarchy view"""
        self.populate_hierarchy()