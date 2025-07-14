"""
Element Tree Model Implementation

Qt model implementation for hierarchical element representation.
"""

from typing import Any, List, Optional, Dict, Union
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon

from .tree_node import TreeNode
from ..interfaces.tree_interfaces import ElementProtocol, ElementProvider, TreeModelInterface


class ElementTreeModel(QAbstractItemModel):
    """Tree model for hierarchical element representation."""
    
    # Custom signals
    elementAdded = pyqtSignal(str)  # element_id
    elementRemoved = pyqtSignal(str)  # element_id
    elementUpdated = pyqtSignal(str)  # element_id
    modelRefreshed = pyqtSignal()
    
    def __init__(self, element_provider: Optional[ElementProvider] = None, parent=None):
        """
        Initialize tree model.
        
        Args:
            element_provider: Provider for element data
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self._element_provider = element_provider
        self._root_node = TreeNode()  # Virtual root node
        self._element_map: Dict[str, TreeNode] = {}  # element_id -> TreeNode
        self._headers = ["Content", "Type", "Confidence"]
        
        if element_provider:
            self._build_tree()
    
    def set_element_provider(self, provider: ElementProvider) -> None:
        """Set element provider and rebuild tree."""
        self.beginResetModel()
        self._element_provider = provider
        self._build_tree()
        self.endResetModel()
        self.modelRefreshed.emit()
    
    def _build_tree(self) -> None:
        """Build tree structure from element provider."""
        if not self._element_provider:
            return
        
        # Clear existing tree
        self._root_node.clear_children()
        self._element_map.clear()
        
        try:
            # Get root elements and build tree
            root_elements = self._element_provider.get_root_elements()
            for element in root_elements:
                self._add_element_recursive(element, self._root_node)
        except Exception as e:
            print(f"Error building tree: {e}")
    
    def _add_element_recursive(self, element: ElementProtocol, parent_node: TreeNode) -> TreeNode:
        """
        Recursively add element and its children to tree.
        
        Args:
            element: Element to add
            parent_node: Parent tree node
            
        Returns:
            Created tree node
        """
        # Create node for element
        node = TreeNode(element, parent_node)
        parent_node.add_child(node)
        self._element_map[element.id] = node
        
        # Add children if provider supports it
        if hasattr(self._element_provider, 'get_child_elements'):
            try:
                child_elements = self._element_provider.get_child_elements(element.id)
                for child_element in child_elements:
                    self._add_element_recursive(child_element, node)
            except Exception as e:
                print(f"Error adding child elements for {element.id}: {e}")
        
        return node
    
    # QAbstractItemModel implementation
    
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Create model index for given position."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        
        parent_node = self._node_from_index(parent) if parent.isValid() else self._root_node
        child_node = parent_node.child(row)
        
        if child_node:
            return self.createIndex(row, column, child_node)
        return QModelIndex()
    
    def parent(self, index: QModelIndex) -> QModelIndex:
        """Get parent index for given child index."""
        if not index.isValid():
            return QModelIndex()
        
        child_node = self._node_from_index(index)
        parent_node = child_node.parent()
        
        if parent_node == self._root_node or parent_node is None:
            return QModelIndex()
        
        grandparent_node = parent_node.parent()
        if grandparent_node is None:
            return QModelIndex()
        
        row = grandparent_node.index_of_child(parent_node)
        return self.createIndex(row, 0, parent_node)
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Get number of children for parent index."""
        parent_node = self._node_from_index(parent) if parent.isValid() else self._root_node
        return parent_node.child_count()
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Get number of columns."""
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get data for display in tree view."""
        if not index.isValid():
            return QVariant()
        
        node = self._node_from_index(index)
        element = node.element()
        
        if not element:
            return QVariant()
        
        column = index.column()
        
        # Display role - main content
        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:  # Content
                return element.text[:100] if element.text else "No content"
            elif column == 1:  # Type
                return element.type.title() if element.type else "Unknown"
            elif column == 2:  # Confidence
                return f"{element.confidence:.1%}" if element.confidence is not None else "N/A"
        
        # Tooltip role - detailed information
        elif role == Qt.ItemDataRole.ToolTipRole:
            tooltip_parts = [
                f"Type: {element.type}",
                f"ID: {element.id}",
                f"Confidence: {element.confidence:.1%}" if element.confidence is not None else "Confidence: N/A"
            ]
            if element.text:
                tooltip_parts.append(f"Content: {element.text[:200]}...")
            return "\n".join(tooltip_parts)
        
        # User role - element ID for internal use
        elif role == Qt.ItemDataRole.UserRole:
            return element.id
        
        # Font role - styling based on confidence or type
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if element.type in ['title', 'header']:
                font.setBold(True)
            return font
        
        # Text color role - based on confidence
        elif role == Qt.ItemDataRole.ForegroundRole:
            if element.confidence is not None:
                if element.confidence >= 0.8:
                    return QColor(0, 100, 0)  # Dark green for high confidence
                elif element.confidence >= 0.6:
                    return QColor(200, 100, 0)  # Orange for medium confidence
                elif element.confidence < 0.5:
                    return QColor(150, 150, 150)  # Gray for low confidence
        
        # Background color role - subtle highlighting
        elif role == Qt.ItemDataRole.BackgroundRole:
            if element.type == 'title':
                return QColor(240, 248, 255)  # Light blue for titles
            elif element.type == 'header':
                return QColor(248, 248, 255)  # Very light blue for headers
        
        # Text alignment
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 2:  # Confidence column
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get header data for tree view."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        elif orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.ToolTipRole:
            tooltips = [
                "Element content text",
                "Element type (text, title, list, etc.)",
                "Confidence score from extraction"
            ]
            if 0 <= section < len(tooltips):
                return tooltips[section]
        return QVariant()
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Get item flags."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEnabled | 
                Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsDragEnabled)
    
    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Check if item has children."""
        parent_node = self._node_from_index(parent) if parent.isValid() else self._root_node
        return parent_node.child_count() > 0
    
    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Check if more data can be fetched (for lazy loading)."""
        # This can be extended later for lazy loading support
        return False
    
    def fetchMore(self, parent: QModelIndex) -> None:
        """Fetch more data (for lazy loading)."""
        # Implementation for lazy loading will be added by Agent 3
        pass
    
    # Custom methods for tree operations
    
    def _node_from_index(self, index: QModelIndex) -> TreeNode:
        """Get tree node from model index."""
        if index.isValid():
            return index.internalPointer()
        return self._root_node
    
    def get_node_by_element_id(self, element_id: str) -> Optional[TreeNode]:
        """Get tree node by element ID."""
        return self._element_map.get(element_id)
    
    def get_element_by_id(self, element_id: str) -> Optional[ElementProtocol]:
        """Get element by ID."""
        node = self._element_map.get(element_id)
        return node.element() if node else None
    
    def get_index_by_element_id(self, element_id: str) -> QModelIndex:
        """Get model index by element ID."""
        node = self._element_map.get(element_id)
        if not node:
            return QModelIndex()
        
        # Build path to root
        path = node.path_to_root()[1:]  # Exclude virtual root
        if not path:
            return QModelIndex()
        
        # Navigate down the path to create index
        current_index = QModelIndex()
        for node_in_path in path:
            parent_node = node_in_path.parent()
            if parent_node:
                row = parent_node.index_of_child(node_in_path)
                current_index = self.index(row, 0, current_index)
        
        return current_index
    
    def add_element(self, element: ElementProtocol, parent_id: Optional[str] = None) -> bool:
        """
        Add new element to tree.
        
        Args:
            element: Element to add
            parent_id: Parent element ID (None for root level)
            
        Returns:
            True if added successfully
        """
        # Find parent node
        if parent_id:
            parent_node = self._element_map.get(parent_id)
            if not parent_node:
                return False
        else:
            parent_node = self._root_node
        
        # Get parent index for model signals
        parent_index = self.get_index_by_element_id(parent_id) if parent_id else QModelIndex()
        
        # Add element
        row = parent_node.child_count()
        self.beginInsertRows(parent_index, row, row)
        
        new_node = TreeNode(element, parent_node)
        parent_node.add_child(new_node)
        self._element_map[element.id] = new_node
        
        self.endInsertRows()
        self.elementAdded.emit(element.id)
        return True
    
    def remove_element(self, element_id: str) -> bool:
        """
        Remove element from tree.
        
        Args:
            element_id: Element ID to remove
            
        Returns:
            True if removed successfully
        """
        node = self._element_map.get(element_id)
        if not node:
            return False
        
        parent_node = node.parent()
        if not parent_node:
            return False
        
        # Get indices for model signals
        parent_index = QModelIndex()
        if parent_node != self._root_node:
            parent_element = parent_node.element()
            if parent_element:
                parent_index = self.get_index_by_element_id(parent_element.id)
        
        row = parent_node.index_of_child(node)
        if row < 0:
            return False
        
        # Remove element and all descendants
        self.beginRemoveRows(parent_index, row, row)
        
        # Remove from element map (including descendants)
        descendants = node.get_all_descendants()
        for desc_node in descendants:
            if desc_node.element():
                self._element_map.pop(desc_node.element().id, None)
        
        self._element_map.pop(element_id, None)
        parent_node.remove_child(node)
        
        self.endRemoveRows()
        self.elementRemoved.emit(element_id)
        return True
    
    def update_element(self, element: ElementProtocol) -> bool:
        """
        Update existing element in tree.
        
        Args:
            element: Updated element
            
        Returns:
            True if updated successfully
        """
        node = self._element_map.get(element.id)
        if not node:
            return False
        
        # Update element
        node.set_element(element)
        
        # Emit data changed signal
        index = self.get_index_by_element_id(element.id)
        if index.isValid():
            bottom_right = self.index(index.row(), self.columnCount() - 1, index.parent())
            self.dataChanged.emit(index, bottom_right)
            self.elementUpdated.emit(element.id)
            return True
        
        return False
    
    def refresh_element(self, element_id: str) -> bool:
        """
        Refresh specific element from provider.
        
        Args:
            element_id: Element ID to refresh
            
        Returns:
            True if refreshed successfully
        """
        if not self._element_provider:
            return False
        
        try:
            element = self._element_provider.get_element_by_id(element_id)
            if element:
                return self.update_element(element)
        except Exception as e:
            print(f"Error refreshing element {element_id}: {e}")
        
        return False
    
    def refresh_all(self) -> None:
        """Refresh entire tree from provider."""
        if self._element_provider:
            self.beginResetModel()
            self._build_tree()
            self.endResetModel()
            self.modelRefreshed.emit()
    
    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get statistics about the tree."""
        total_elements = len(self._element_map)
        total_nodes = self._root_node.size() - 1  # Exclude virtual root
        
        # Count by type
        type_counts = {}
        for node in self._element_map.values():
            element = node.element()
            if element:
                element_type = element.type
                type_counts[element_type] = type_counts.get(element_type, 0) + 1
        
        # Calculate depth statistics
        depths = []
        for node in self._element_map.values():
            depths.append(node.depth() - 1)  # Adjust for virtual root
        
        max_depth = max(depths) if depths else 0
        avg_depth = sum(depths) / len(depths) if depths else 0
        
        return {
            'total_elements': total_elements,
            'total_nodes': total_nodes,
            'max_depth': max_depth,
            'average_depth': avg_depth,
            'type_counts': type_counts,
            'root_children': self._root_node.child_count()
        }
    
    def validate_tree_integrity(self) -> List[str]:
        """Validate tree integrity and return any issues found."""
        errors = []
        
        # Check element map consistency
        for element_id, node in self._element_map.items():
            element = node.element()
            if not element or element.id != element_id:
                errors.append(f"Element map inconsistency for {element_id}")
        
        # Validate tree structure
        errors.extend(self._root_node.validate_tree_integrity())
        
        return errors