"""
Tree Node Implementation

Hierarchical node representation with parent-child relationships.
"""

from typing import Optional, List, Dict, Any, Union
import weakref
from ..interfaces.tree_interfaces import TreeNodeProtocol, ElementProtocol


class TreeNode:
    """Node in the hierarchical tree structure."""
    
    def __init__(
        self, 
        element: Optional[ElementProtocol] = None, 
        parent: Optional['TreeNode'] = None
    ):
        """
        Initialize tree node.
        
        Args:
            element: Element associated with this node
            parent: Parent node (None for root)
        """
        self._element = element
        self._parent_ref: Optional[weakref.ReferenceType] = None
        self._children: List['TreeNode'] = []
        self._expanded = False
        self._metadata: Dict[str, Any] = {}
        
        # Set parent with weak reference to avoid circular references
        if parent is not None:
            self._parent_ref = weakref.ref(parent)
    
    def element(self) -> Optional[ElementProtocol]:
        """Get the element associated with this node."""
        return self._element
    
    def set_element(self, element: Optional[ElementProtocol]) -> None:
        """Set the element associated with this node."""
        self._element = element
    
    def parent(self) -> Optional['TreeNode']:
        """Get parent node."""
        if self._parent_ref is None:
            return None
        parent = self._parent_ref()
        return parent if parent is not None else None
    
    def set_parent(self, parent: Optional['TreeNode']) -> None:
        """Set parent node."""
        if parent is not None:
            self._parent_ref = weakref.ref(parent)
        else:
            self._parent_ref = None
    
    def children(self) -> List['TreeNode']:
        """Get list of child nodes (copy to prevent external modification)."""
        return self._children.copy()
    
    def child(self, index: int) -> Optional['TreeNode']:
        """Get child at specific index."""
        if 0 <= index < len(self._children):
            return self._children[index]
        return None
    
    def child_count(self) -> int:
        """Get number of children."""
        return len(self._children)
    
    def add_child(self, child: 'TreeNode') -> None:
        """
        Add child node.
        
        Args:
            child: Child node to add
        """
        if child not in self._children:
            child.set_parent(self)
            self._children.append(child)
    
    def insert_child(self, index: int, child: 'TreeNode') -> None:
        """
        Insert child node at specific index.
        
        Args:
            index: Index to insert at
            child: Child node to insert
        """
        if child not in self._children:
            child.set_parent(self)
            self._children.insert(index, child)
    
    def remove_child(self, child: 'TreeNode') -> bool:
        """
        Remove child node.
        
        Args:
            child: Child node to remove
            
        Returns:
            True if child was removed, False if not found
        """
        if child in self._children:
            child.set_parent(None)
            self._children.remove(child)
            return True
        return False
    
    def remove_child_at(self, index: int) -> Optional['TreeNode']:
        """
        Remove child at specific index.
        
        Args:
            index: Index of child to remove
            
        Returns:
            Removed child node or None if index invalid
        """
        if 0 <= index < len(self._children):
            child = self._children[index]
            child.set_parent(None)
            return self._children.pop(index)
        return None
    
    def index_of_child(self, child: 'TreeNode') -> int:
        """
        Get index of child node.
        
        Args:
            child: Child node to find
            
        Returns:
            Index of child or -1 if not found
        """
        try:
            return self._children.index(child)
        except ValueError:
            return -1
    
    def find_child_by_element_id(self, element_id: str) -> Optional['TreeNode']:
        """
        Find child node by element ID (recursive search).
        
        Args:
            element_id: Element ID to search for
            
        Returns:
            Found node or None
        """
        # Check direct children first
        for child in self._children:
            if child._element and child._element.id == element_id:
                return child
        
        # Recursive search in grandchildren
        for child in self._children:
            found = child.find_child_by_element_id(element_id)
            if found:
                return found
        
        return None
    
    def depth(self) -> int:
        """Calculate depth in tree (root = 0)."""
        depth = 0
        current = self.parent()
        while current:
            depth += 1
            current = current.parent()
        return depth
    
    def path_to_root(self) -> List['TreeNode']:
        """Get path from this node to root."""
        path = []
        current: Optional['TreeNode'] = self
        while current:
            path.append(current)
            current = current.parent()
        return path[::-1]  # Reverse to get root-to-node path
    
    def path_from_root(self) -> List['TreeNode']:
        """Get path from root to this node."""
        return self.path_to_root()
    
    def is_root(self) -> bool:
        """Check if this is a root node."""
        return self.parent() is None
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return len(self._children) == 0
    
    def is_ancestor_of(self, node: 'TreeNode') -> bool:
        """Check if this node is an ancestor of another node."""
        current = node.parent()
        while current:
            if current is self:
                return True
            current = current.parent()
        return False
    
    def is_descendant_of(self, node: 'TreeNode') -> bool:
        """Check if this node is a descendant of another node."""
        return node.is_ancestor_of(self)
    
    def is_expanded(self) -> bool:
        """Check if node is expanded."""
        return self._expanded
    
    def set_expanded(self, expanded: bool) -> None:
        """Set expansion state."""
        self._expanded = expanded
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self._metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self._metadata[key] = value
    
    def remove_metadata(self, key: str) -> bool:
        """Remove metadata key."""
        if key in self._metadata:
            del self._metadata[key]
            return True
        return False
    
    def clear_metadata(self) -> None:
        """Clear all metadata."""
        self._metadata.clear()
    
    def get_all_descendants(self) -> List['TreeNode']:
        """Get all descendant nodes (recursive)."""
        descendants = []
        for child in self._children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants
    
    def get_siblings(self) -> List['TreeNode']:
        """Get sibling nodes (nodes with same parent)."""
        parent = self.parent()
        if parent is None:
            return []
        
        siblings = []
        for child in parent.children():
            if child is not self:
                siblings.append(child)
        return siblings
    
    def get_next_sibling(self) -> Optional['TreeNode']:
        """Get next sibling node."""
        parent = self.parent()
        if parent is None:
            return None
        
        my_index = parent.index_of_child(self)
        if my_index >= 0 and my_index < parent.child_count() - 1:
            return parent.child(my_index + 1)
        return None
    
    def get_previous_sibling(self) -> Optional['TreeNode']:
        """Get previous sibling node."""
        parent = self.parent()
        if parent is None:
            return None
        
        my_index = parent.index_of_child(self)
        if my_index > 0:
            return parent.child(my_index - 1)
        return None
    
    def clear_children(self) -> None:
        """Remove all child nodes."""
        for child in self._children.copy():
            self.remove_child(child)
    
    def size(self) -> int:
        """Get total number of nodes in subtree (including self)."""
        size = 1  # Count self
        for child in self._children:
            size += child.size()
        return size
    
    def __str__(self) -> str:
        """String representation for debugging."""
        element_info = ""
        if self._element:
            element_info = f" ({self._element.type}: {self._element.text[:30]}...)"
        return f"TreeNode{element_info} [{len(self._children)} children]"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (f"TreeNode(element_id={self._element.id if self._element else None}, "
                f"children={len(self._children)}, expanded={self._expanded})")
    
    def validate_tree_integrity(self) -> List[str]:
        """
        Validate tree integrity and return list of issues found.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check parent-child consistency
        for child in self._children:
            if child.parent() is not self:
                errors.append(f"Child {child} has inconsistent parent reference")
        
        # Check for cycles (should not happen with weak references, but safety check)
        visited = set()
        current = self
        while current:
            if id(current) in visited:
                errors.append("Cycle detected in tree structure")
                break
            visited.add(id(current))
            current = current.parent()
        
        # Recursively validate children
        for child in self._children:
            errors.extend(child.validate_tree_integrity())
        
        return errors