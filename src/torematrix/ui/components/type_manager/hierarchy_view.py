"""Type Hierarchy View

Visual hierarchy display showing type inheritance relationships
with drag-drop support, expansion controls, and relationship highlighting.
"""

from typing import Optional, List, Dict, Any, Set
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QHeaderView, QMenu,
    QMessageBox, QInputDialog, QToolTip, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor, QBrush, QPen, QAction

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.types.hierarchy import TypeHierarchy
from torematrix.core.models.types.metadata import MetadataManager, get_metadata_manager


class TypeHierarchyView(QTreeWidget):
    """Visual hierarchy display with drag-drop support"""
    
    # Signals
    type_selected = pyqtSignal(str)  # type_id
    hierarchy_changed = pyqtSignal()
    relationship_requested = pyqtSignal(str, str)  # parent_id, child_id
    type_details_requested = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent: QWidget = None):
        super().__init__(parent)
        
        # Core components
        self.registry = registry or get_type_registry()
        self.metadata_manager = get_metadata_manager()
        
        # State
        self.highlighted_types: Set[str] = set()
        self.expanded_types: Set[str] = set()
        self.filter_text: str = ""
        
        # Setup UI
        self.setup_ui()
        self.setup_drag_drop()
        self.load_hierarchy()
        self.connect_signals()
        
        # Load styles
        self.apply_styles()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Configure tree
        self.setHeaderLabels(["Type", "Category", "Elements", "Description"])
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setExpandsOnDoubleClick(True)
        self.setItemsExpandable(True)
        self.setAnimated(True)
        
        # Configure columns
        header = self.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable hover events
        self.setMouseTracking(True)
        
        # Set minimum size
        self.setMinimumSize(400, 300)
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
    
    def load_hierarchy(self):
        """Load type hierarchy into tree"""
        self.clear()
        
        # Get all types
        types = self.registry.list_types()
        
        # Build type map
        type_map = {t.type_id: t for t in types}
        
        # Find root types (no parents)
        root_types = [t for t in types if not t.parent_types]
        
        # Create tree items
        self.created_items: Dict[str, QTreeWidgetItem] = {}
        
        # Add root types
        for type_def in sorted(root_types, key=lambda t: (t.category, t.display_order, t.name)):
            if self.matches_filter(type_def):
                item = self.create_type_item(type_def)
                self.addTopLevelItem(item)
                self.created_items[type_def.type_id] = item
                self.add_children_recursive(type_def, item, type_map)
        
        # Restore expanded state
        self.restore_expanded_state()
        
        # Update statistics
        self.update_statistics()
    
    def create_type_item(self, type_def: TypeDefinition) -> QTreeWidgetItem:
        """Create tree item for type definition
        
        Args:
            type_def: Type definition
            
        Returns:
            QTreeWidgetItem for the type
        """
        # Create item
        item = QTreeWidgetItem()
        
        # Set data
        item.setData(0, Qt.ItemDataRole.UserRole, type_def.type_id)
        
        # Set text
        item.setText(0, type_def.name)
        item.setText(1, type_def.category.title())
        item.setText(2, "0")  # Element count placeholder
        item.setText(3, type_def.description)
        
        # Set icon
        icon = self.get_type_icon(type_def)
        item.setIcon(0, icon)
        
        # Set colors
        if type_def.color:
            color = QColor(type_def.color)
            item.setForeground(0, QBrush(color))
        
        # Set tooltip
        tooltip = self.create_tooltip(type_def)
        item.setToolTip(0, tooltip)
        
        # Store type definition
        item.setData(0, Qt.ItemDataRole.UserRole + 1, type_def)
        
        return item
    
    def add_children_recursive(self, parent_type: TypeDefinition, parent_item: QTreeWidgetItem,
                             type_map: Dict[str, TypeDefinition], visited: Set[str] = None):
        """Add children recursively to avoid circular dependencies
        
        Args:
            parent_type: Parent type definition
            parent_item: Parent tree item
            type_map: Map of type IDs to definitions
            visited: Set of visited type IDs to prevent cycles
        """
        if visited is None:
            visited = set()
        
        if parent_type.type_id in visited:
            return
        
        visited.add(parent_type.type_id)
        
        # Add direct children
        for child_id in sorted(parent_type.child_types):
            if child_id in type_map and child_id not in self.created_items:
                child_type = type_map[child_id]
                
                if self.matches_filter(child_type):
                    child_item = self.create_type_item(child_type)
                    parent_item.addChild(child_item)
                    self.created_items[child_id] = child_item
                    
                    # Recursively add grandchildren
                    self.add_children_recursive(child_type, child_item, type_map, visited.copy())
    
    def matches_filter(self, type_def: TypeDefinition) -> bool:
        """Check if type matches current filter
        
        Args:
            type_def: Type definition to check
            
        Returns:
            True if type matches filter
        """
        if not self.filter_text:
            return True
        
        query = self.filter_text.lower()
        return (
            query in type_def.name.lower() or
            query in type_def.description.lower() or
            query in type_def.category.lower() or
            any(query in tag.lower() for tag in type_def.tags)
        )
    
    def get_type_icon(self, type_def: TypeDefinition) -> QIcon:
        """Get icon for type definition
        
        Args:
            type_def: Type definition
            
        Returns:
            QIcon for the type
        """
        # Get metadata for icon
        metadata = self.metadata_manager.get_metadata(type_def.type_id)
        
        if metadata and metadata.icon:
            icon_url = metadata.icon.get_icon_url(size=16)
            
            # Handle different icon types
            if metadata.icon.icon_type.value == "font_awesome":
                return self.create_text_icon(f"fa-{icon_url}", type_def.color)
            elif metadata.icon.icon_type.value == "emoji":
                return self.create_text_icon(icon_url)
            else:
                # Try to load as image
                try:
                    pixmap = QPixmap(icon_url)
                    if not pixmap.isNull():
                        return QIcon(pixmap)
                except:
                    pass
        
        # Fallback based on category
        category_icons = {
            "text": "📝",
            "media": "🖼️",
            "structure": "🏗️",
            "layout": "📐",
            "data": "📊",
            "content": "📄"
        }
        
        icon_text = category_icons.get(type_def.category, "📄")
        return self.create_text_icon(icon_text, type_def.color)
    
    def create_text_icon(self, text: str, color: str = None) -> QIcon:
        """Create icon from text/emoji
        
        Args:
            text: Text or emoji to use
            color: Optional color for text
            
        Returns:
            QIcon created from text
        """
        # Create pixmap
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Draw text
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        
        # Set color
        if color:
            painter.setPen(QColor(color))
        
        # Draw text centered
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    def create_tooltip(self, type_def: TypeDefinition) -> str:
        """Create tooltip for type
        
        Args:
            type_def: Type definition
            
        Returns:
            HTML tooltip text
        """
        html = f"""
        <div style="max-width: 300px;">
            <h3 style="margin: 0; color: {type_def.color or '#333'};">{type_def.name}</h3>
            <p style="margin: 2px 0; color: #666; font-size: 11px;">
                <b>Category:</b> {type_def.category.title()}
            </p>
            <p style="margin: 2px 0; color: #666; font-size: 11px;">
                <b>ID:</b> {type_def.type_id}
            </p>
            <p style="margin: 4px 0;">{type_def.description}</p>
        """
        
        if type_def.parent_types:
            html += f"""
            <p style="margin: 2px 0; color: #666; font-size: 11px;">
                <b>Inherits from:</b> {', '.join(type_def.parent_types)}
            </p>
            """
        
        if type_def.child_types:
            html += f"""
            <p style="margin: 2px 0; color: #666; font-size: 11px;">
                <b>Has children:</b> {len(type_def.child_types)} types
            </p>
            """
        
        if type_def.tags:
            html += f"""
            <p style="margin: 2px 0; color: #666; font-size: 11px;">
                <b>Tags:</b> {', '.join(type_def.tags)}
            </p>
            """
        
        html += "</div>"
        return html
    
    def expand_type_branch(self, type_id: str) -> None:
        """Expand branch for specific type
        
        Args:
            type_id: Type ID to expand
        """
        if type_id in self.created_items:
            item = self.created_items[type_id]
            self.expandItem(item)
            
            # Scroll to item
            self.scrollToItem(item, QTreeWidget.ScrollHint.PositionAtCenter)
            
            # Select item
            self.setCurrentItem(item)
    
    def highlight_inheritance_path(self, type_id: str) -> None:
        """Highlight inheritance path for type
        
        Args:
            type_id: Type ID to highlight path for
        """
        self.clear_highlights()
        
        try:
            type_def = self.registry.get_type(type_id)
            
            # Highlight this type
            self.highlighted_types.add(type_id)
            
            # Highlight ancestors
            ancestors = type_def.get_all_parent_types(self.registry)
            self.highlighted_types.update(ancestors)
            
            # Highlight descendants
            descendants = self._get_all_descendants(type_id)
            self.highlighted_types.update(descendants)
            
            # Update visual highlighting
            self.update_highlighting()
            
        except Exception as e:
            print(f"Error highlighting inheritance path: {e}")
    
    def show_type_relationships(self, type_id: str) -> None:
        """Show type relationships in detail
        
        Args:
            type_id: Type ID to show relationships for
        """
        try:
            type_def = self.registry.get_type(type_id)
            
            # Create relationship info
            info = f"Relationships for: {type_def.name}\n\n"
            
            if type_def.parent_types:
                info += f"Parents: {', '.join(type_def.parent_types)}\n"
            
            if type_def.child_types:
                info += f"Children: {', '.join(type_def.child_types)}\n"
            
            # Get all ancestors
            ancestors = type_def.get_all_parent_types(self.registry)
            if ancestors:
                info += f"All Ancestors: {', '.join(ancestors)}\n"
            
            # Get all descendants
            descendants = self._get_all_descendants(type_id)
            if descendants:
                info += f"All Descendants: {', '.join(descendants)}\n"
            
            # Show in message box
            QMessageBox.information(self, "Type Relationships", info)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load relationships: {e}")
    
    def clear_highlights(self) -> None:
        """Clear all highlights"""
        self.highlighted_types.clear()
        self.update_highlighting()
    
    def update_highlighting(self) -> None:
        """Update visual highlighting"""
        # Reset all items
        for i in range(self.topLevelItemCount()):
            self.reset_item_highlighting_recursive(self.topLevelItem(i))
        
        # Apply highlighting
        for type_id in self.highlighted_types:
            if type_id in self.created_items:
                item = self.created_items[type_id]
                self.highlight_item(item)
    
    def reset_item_highlighting_recursive(self, item: QTreeWidgetItem) -> None:
        """Reset highlighting for item and children
        
        Args:
            item: Tree item to reset
        """
        # Reset background
        item.setBackground(0, QBrush())
        
        # Reset children
        for i in range(item.childCount()):
            self.reset_item_highlighting_recursive(item.child(i))
    
    def highlight_item(self, item: QTreeWidgetItem) -> None:
        """Highlight specific item
        
        Args:
            item: Item to highlight
        """
        # Set background color
        highlight_color = QColor(255, 255, 0, 80)  # Light yellow
        item.setBackground(0, QBrush(highlight_color))
    
    def filter_hierarchy(self, filter_text: str) -> None:
        """Filter hierarchy by text
        
        Args:
            filter_text: Filter text
        """
        self.filter_text = filter_text
        self.load_hierarchy()
    
    def save_expanded_state(self) -> None:
        """Save expanded state of items"""
        self.expanded_types.clear()
        
        for type_id, item in self.created_items.items():
            if item.isExpanded():
                self.expanded_types.add(type_id)
    
    def restore_expanded_state(self) -> None:
        """Restore expanded state of items"""
        for type_id in self.expanded_types:
            if type_id in self.created_items:
                item = self.created_items[type_id]
                item.setExpanded(True)
    
    def connect_signals(self) -> None:
        """Connect internal signals"""
        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemCollapsed.connect(self.on_item_collapsed)
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item click
        
        Args:
            item: Clicked item
            column: Clicked column
        """
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.type_selected.emit(type_id)
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double click
        
        Args:
            item: Double-clicked item
            column: Clicked column
        """
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.type_details_requested.emit(type_id)
    
    def on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Handle item expansion
        
        Args:
            item: Expanded item
        """
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.expanded_types.add(type_id)
    
    def on_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """Handle item collapse
        
        Args:
            item: Collapsed item
        """
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if type_id:
            self.expanded_types.discard(type_id)
    
    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu
        
        Args:
            position: Menu position
        """
        item = self.itemAt(position)
        if not item:
            return
        
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not type_id:
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Type actions
        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self.type_details_requested.emit(type_id))
        menu.addAction(view_action)
        
        highlight_action = QAction("Highlight Inheritance", self)
        highlight_action.triggered.connect(lambda: self.highlight_inheritance_path(type_id))
        menu.addAction(highlight_action)
        
        relationships_action = QAction("Show Relationships", self)
        relationships_action.triggered.connect(lambda: self.show_type_relationships(type_id))
        menu.addAction(relationships_action)
        
        menu.addSeparator()
        
        # Tree actions
        expand_all_action = QAction("Expand All", self)
        expand_all_action.triggered.connect(self.expandAll)
        menu.addAction(expand_all_action)
        
        collapse_all_action = QAction("Collapse All", self)
        collapse_all_action.triggered.connect(self.collapseAll)
        menu.addAction(collapse_all_action)
        
        clear_highlights_action = QAction("Clear Highlights", self)
        clear_highlights_action.triggered.connect(self.clear_highlights)
        menu.addAction(clear_highlights_action)
        
        # Show menu
        menu.exec(self.mapToGlobal(position))
    
    def update_statistics(self) -> None:
        """Update statistics for tree items"""
        # This would update element counts for each type
        # For now, just placeholder
        pass
    
    def refresh(self) -> None:
        """Refresh the hierarchy view"""
        # Save state
        self.save_expanded_state()
        selected_type = None
        
        current_item = self.currentItem()
        if current_item:
            selected_type = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Reload
        self.load_hierarchy()
        
        # Restore selection
        if selected_type and selected_type in self.created_items:
            item = self.created_items[selected_type]
            self.setCurrentItem(item)
    
    def apply_styles(self) -> None:
        """Apply custom styles"""
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ccc;
                background: white;
                selection-background-color: #e3f2fd;
                alternate-background-color: #f9f9f9;
            }
            
            QTreeWidget::item {
                padding: 2px;
                border: none;
            }
            
            QTreeWidget::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
            
            QTreeWidget::item:hover {
                background: #f0f0f0;
            }
            
            QTreeWidget::branch {
                background: white;
            }
            
            QTreeWidget::branch:closed:has-children {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNCAyTDggNkw0IDEwVjJaIiBmaWxsPSIjNjY2Ii8+PC9zdmc+);
            }
            
            QTreeWidget::branch:open:has-children {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMiA0TDYgOEwxMCA0SDJaIiBmaWxsPSIjNjY2Ii8+PC9zdmc+);
            }
            
            QHeaderView::section {
                background: #f5f5f5;
                border: 1px solid #ddd;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
    
    def _get_all_descendants(self, type_id: str) -> List[str]:
        """Get all descendant types recursively
        
        Args:
            type_id: Type ID to get descendants for
            
        Returns:
            List of descendant type IDs
        """
        descendants = []
        visited = set()
        
        def collect_descendants(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)
            
            try:
                type_def = self.registry.get_type(current_id)
                for child_id in type_def.child_types:
                    if child_id not in descendants:
                        descendants.append(child_id)
                        collect_descendants(child_id)
            except:
                pass
        
        collect_descendants(type_id)
        return descendants


class TypeHierarchyWidget(QWidget):
    """Complete type hierarchy widget with controls"""
    
    # Signals
    type_selected = pyqtSignal(str)
    hierarchy_changed = pyqtSignal()
    
    def __init__(self, registry: TypeRegistry = None, parent: QWidget = None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header with controls
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Type Hierarchy")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter types...")
        self.filter_input.setMaximumWidth(150)
        header_layout.addWidget(self.filter_input)
        
        # Buttons
        self.expand_btn = QPushButton("Expand All")
        self.expand_btn.setMaximumWidth(80)
        header_layout.addWidget(self.expand_btn)
        
        self.collapse_btn = QPushButton("Collapse All")
        self.collapse_btn.setMaximumWidth(80)
        header_layout.addWidget(self.collapse_btn)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setToolTip("Refresh hierarchy")
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Hierarchy view
        self.hierarchy_view = TypeHierarchyView(self.registry)
        layout.addWidget(self.hierarchy_view)
    
    def connect_signals(self):
        """Connect signals"""
        self.hierarchy_view.type_selected.connect(self.type_selected.emit)
        self.hierarchy_view.hierarchy_changed.connect(self.hierarchy_changed.emit)
        
        self.filter_input.textChanged.connect(self.hierarchy_view.filter_hierarchy)
        self.expand_btn.clicked.connect(self.hierarchy_view.expandAll)
        self.collapse_btn.clicked.connect(self.hierarchy_view.collapseAll)
        self.refresh_btn.clicked.connect(self.hierarchy_view.refresh)
    
    def expand_type_branch(self, type_id: str):
        """Expand branch for type"""
        self.hierarchy_view.expand_type_branch(type_id)
    
    def highlight_inheritance_path(self, type_id: str):
        """Highlight inheritance path"""
        self.hierarchy_view.highlight_inheritance_path(type_id)
    
    def refresh(self):
        """Refresh hierarchy"""
        self.hierarchy_view.refresh()