"""
Tests for TreeNode class

Comprehensive tests for hierarchical tree node functionality.
"""

import pytest
import weakref
from unittest.mock import Mock

from src.torematrix.ui.components.element_list.models.tree_node import TreeNode


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, element_id: str, text: str = "", element_type: str = "text", confidence: float = 1.0):
        self.id = element_id
        self.text = text
        self.type = element_type
        self.confidence = confidence
        self.metadata = {}


class TestTreeNode:
    """Test cases for TreeNode class."""
    
    def test_node_creation_without_element(self):
        """Test creating a node without an element."""
        node = TreeNode()
        assert node.element() is None
        assert node.parent() is None
        assert node.child_count() == 0
        assert node.is_root()
        assert node.is_leaf()
    
    def test_node_creation_with_element(self):
        """Test creating a node with an element."""
        element = MockElement("test1", "Test content")
        node = TreeNode(element)
        
        assert node.element() is element
        assert node.element().id == "test1"
        assert node.element().text == "Test content"
    
    def test_parent_child_relationship(self):
        """Test parent-child relationships."""
        parent = TreeNode(MockElement("parent"))
        child = TreeNode(MockElement("child"))
        
        # Add child to parent
        parent.add_child(child)
        
        assert child.parent() is parent
        assert parent.child_count() == 1
        assert parent.child(0) is child
        assert not parent.is_leaf()
        assert not child.is_root()
    
    def test_weak_reference_parent(self):
        """Test that parent references are weak to prevent cycles."""
        parent = TreeNode(MockElement("parent"))
        child = TreeNode(MockElement("child"))
        
        parent.add_child(child)
        
        # Parent should exist
        assert child.parent() is parent
        
        # Delete parent
        parent_ref = weakref.ref(parent)
        del parent
        
        # Weak reference should be dead
        assert parent_ref() is None
        # Child's parent should return None
        assert child.parent() is None
    
    def test_multiple_children(self):
        """Test adding multiple children."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        child3 = TreeNode(MockElement("child3"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)
        
        assert parent.child_count() == 3
        assert parent.child(0) is child1
        assert parent.child(1) is child2
        assert parent.child(2) is child3
        
        children = parent.children()
        assert len(children) == 3
        assert child1 in children
        assert child2 in children
        assert child3 in children
    
    def test_child_insertion(self):
        """Test inserting children at specific indices."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        child3 = TreeNode(MockElement("child3"))
        
        parent.add_child(child1)
        parent.add_child(child3)
        parent.insert_child(1, child2)  # Insert between child1 and child3
        
        assert parent.child_count() == 3
        assert parent.child(0) is child1
        assert parent.child(1) is child2
        assert parent.child(2) is child3
    
    def test_child_removal(self):
        """Test removing children."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Remove child1
        assert parent.remove_child(child1) is True
        assert parent.child_count() == 1
        assert parent.child(0) is child2
        assert child1.parent() is None
        
        # Try to remove non-existent child
        assert parent.remove_child(child1) is False
    
    def test_child_removal_by_index(self):
        """Test removing children by index."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Remove at index 0
        removed = parent.remove_child_at(0)
        assert removed is child1
        assert parent.child_count() == 1
        assert parent.child(0) is child2
        
        # Try invalid index
        removed = parent.remove_child_at(5)
        assert removed is None
    
    def test_child_index_lookup(self):
        """Test finding child indices."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert parent.index_of_child(child1) == 0
        assert parent.index_of_child(child2) == 1
        
        # Non-existent child
        child3 = TreeNode(MockElement("child3"))
        assert parent.index_of_child(child3) == -1
    
    def test_find_child_by_element_id(self):
        """Test finding children by element ID."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        grandchild = TreeNode(MockElement("grandchild"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        child1.add_child(grandchild)
        
        # Find direct child
        found = parent.find_child_by_element_id("child1")
        assert found is child1
        
        # Find grandchild (recursive)
        found = parent.find_child_by_element_id("grandchild")
        assert found is grandchild
        
        # Non-existent
        found = parent.find_child_by_element_id("nonexistent")
        assert found is None
    
    def test_depth_calculation(self):
        """Test depth calculation."""
        root = TreeNode(MockElement("root"))
        child = TreeNode(MockElement("child"))
        grandchild = TreeNode(MockElement("grandchild"))
        
        root.add_child(child)
        child.add_child(grandchild)
        
        assert root.depth() == 0
        assert child.depth() == 1
        assert grandchild.depth() == 2
    
    def test_path_to_root(self):
        """Test path calculation to root."""
        root = TreeNode(MockElement("root"))
        child = TreeNode(MockElement("child"))
        grandchild = TreeNode(MockElement("grandchild"))
        
        root.add_child(child)
        child.add_child(grandchild)
        
        # Path from grandchild to root
        path = grandchild.path_to_root()
        assert len(path) == 3
        assert path[0] is root
        assert path[1] is child
        assert path[2] is grandchild
        
        # Path from root to root
        path = root.path_to_root()
        assert len(path) == 1
        assert path[0] is root
    
    def test_ancestor_descendant_relationships(self):
        """Test ancestor/descendant checks."""
        root = TreeNode(MockElement("root"))
        child = TreeNode(MockElement("child"))
        grandchild = TreeNode(MockElement("grandchild"))
        sibling = TreeNode(MockElement("sibling"))
        
        root.add_child(child)
        root.add_child(sibling)
        child.add_child(grandchild)
        
        # Ancestor checks
        assert root.is_ancestor_of(child)
        assert root.is_ancestor_of(grandchild)
        assert child.is_ancestor_of(grandchild)
        assert not child.is_ancestor_of(root)
        assert not sibling.is_ancestor_of(grandchild)
        
        # Descendant checks
        assert grandchild.is_descendant_of(root)
        assert grandchild.is_descendant_of(child)
        assert child.is_descendant_of(root)
        assert not root.is_descendant_of(child)
    
    def test_expansion_state(self):
        """Test expansion state management."""
        node = TreeNode(MockElement("test"))
        
        # Default state
        assert not node.is_expanded()
        
        # Set expanded
        node.set_expanded(True)
        assert node.is_expanded()
        
        # Set collapsed
        node.set_expanded(False)
        assert not node.is_expanded()
    
    def test_metadata_management(self):
        """Test metadata storage and retrieval."""
        node = TreeNode(MockElement("test"))
        
        # Set metadata
        node.set_metadata("key1", "value1")
        node.set_metadata("key2", 42)
        node.set_metadata("key3", {"nested": "dict"})
        
        # Get metadata
        assert node.get_metadata("key1") == "value1"
        assert node.get_metadata("key2") == 42
        assert node.get_metadata("key3") == {"nested": "dict"}
        
        # Default values
        assert node.get_metadata("nonexistent") is None
        assert node.get_metadata("nonexistent", "default") == "default"
        
        # Remove metadata
        assert node.remove_metadata("key1") is True
        assert node.get_metadata("key1") is None
        assert node.remove_metadata("nonexistent") is False
        
        # Clear all metadata
        node.clear_metadata()
        assert node.get_metadata("key2") is None
        assert node.get_metadata("key3") is None
    
    def test_get_all_descendants(self):
        """Test getting all descendants."""
        root = TreeNode(MockElement("root"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        grandchild1 = TreeNode(MockElement("grandchild1"))
        grandchild2 = TreeNode(MockElement("grandchild2"))
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild1)
        child1.add_child(grandchild2)
        
        descendants = root.get_all_descendants()
        assert len(descendants) == 4
        assert child1 in descendants
        assert child2 in descendants
        assert grandchild1 in descendants
        assert grandchild2 in descendants
    
    def test_sibling_operations(self):
        """Test sibling-related operations."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        child3 = TreeNode(MockElement("child3"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)
        
        # Get siblings
        siblings = child2.get_siblings()
        assert len(siblings) == 2
        assert child1 in siblings
        assert child3 in siblings
        assert child2 not in siblings
        
        # Next sibling
        assert child1.get_next_sibling() is child2
        assert child2.get_next_sibling() is child3
        assert child3.get_next_sibling() is None
        
        # Previous sibling
        assert child1.get_previous_sibling() is None
        assert child2.get_previous_sibling() is child1
        assert child3.get_previous_sibling() is child2
        
        # Root node has no siblings
        assert len(parent.get_siblings()) == 0
        assert parent.get_next_sibling() is None
        assert parent.get_previous_sibling() is None
    
    def test_clear_children(self):
        """Test clearing all children."""
        parent = TreeNode(MockElement("parent"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert parent.child_count() == 2
        
        parent.clear_children()
        
        assert parent.child_count() == 0
        assert child1.parent() is None
        assert child2.parent() is None
    
    def test_subtree_size(self):
        """Test subtree size calculation."""
        root = TreeNode(MockElement("root"))
        child1 = TreeNode(MockElement("child1"))
        child2 = TreeNode(MockElement("child2"))
        grandchild = TreeNode(MockElement("grandchild"))
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)
        
        assert root.size() == 4  # root + child1 + child2 + grandchild
        assert child1.size() == 2  # child1 + grandchild
        assert child2.size() == 1  # just child2
        assert grandchild.size() == 1  # just grandchild
    
    def test_string_representations(self):
        """Test string representations."""
        element = MockElement("test1", "Test content", "text")
        node = TreeNode(element)
        
        str_repr = str(node)
        assert "TreeNode" in str_repr
        assert "text" in str_repr
        assert "Test content" in str_repr
        
        repr_str = repr(node)
        assert "TreeNode" in repr_str
        assert "test1" in repr_str
    
    def test_duplicate_child_prevention(self):
        """Test that duplicate children are not added."""
        parent = TreeNode(MockElement("parent"))
        child = TreeNode(MockElement("child"))
        
        parent.add_child(child)
        parent.add_child(child)  # Try to add same child again
        
        assert parent.child_count() == 1
        assert parent.child(0) is child
    
    def test_tree_integrity_validation(self):
        """Test tree integrity validation."""
        # Valid tree
        root = TreeNode(MockElement("root"))
        child = TreeNode(MockElement("child"))
        root.add_child(child)
        
        errors = root.validate_tree_integrity()
        assert len(errors) == 0
        
        # Create inconsistent state for testing
        child2 = TreeNode(MockElement("child2"))
        root._children.append(child2)  # Add without setting parent
        
        errors = root.validate_tree_integrity()
        assert len(errors) > 0
        assert "inconsistent parent reference" in errors[0]
    
    def test_element_modification(self):
        """Test modifying element after node creation."""
        element1 = MockElement("test1", "Original")
        node = TreeNode(element1)
        
        assert node.element() is element1
        
        element2 = MockElement("test2", "Modified")
        node.set_element(element2)
        
        assert node.element() is element2
        assert node.element().text == "Modified"
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        node = TreeNode()
        
        # Operations on empty node
        assert node.child(-1) is None
        assert node.child(0) is None
        assert node.child(100) is None
        
        # Remove from empty
        dummy_child = TreeNode(MockElement("dummy"))
        assert not node.remove_child(dummy_child)
        assert node.remove_child_at(0) is None
        
        # Find in empty
        assert node.find_child_by_element_id("any") is None
        
        # Node without element
        assert node.depth() == 0  # Should work even without element