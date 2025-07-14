"""
Tests for ElementTreeModel class

Comprehensive tests for Qt tree model functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtCore import QModelIndex, Qt, QObject
from PyQt6.QtWidgets import QApplication
import sys

from src.torematrix.ui.components.element_list.models.tree_model import ElementTreeModel
from src.torematrix.ui.components.element_list.models.tree_node import TreeNode


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, element_id: str, text: str = "", element_type: str = "text", confidence: float = 1.0):
        self.id = element_id
        self.text = text
        self.type = element_type
        self.confidence = confidence
        self.metadata = {}


class MockElementProvider:
    """Mock element provider for testing."""
    
    def __init__(self, elements=None):
        self.elements = elements or []
        self.children_map = {}
    
    def get_root_elements(self):
        return [e for e in self.elements if not any(e.id in children for children in self.children_map.values())]
    
    def get_child_elements(self, parent_id):
        return self.children_map.get(parent_id, [])
    
    def get_element_by_id(self, element_id):
        for element in self.elements:
            if element.id == element_id:
                return element
        return None
    
    def set_children(self, parent_id, children):
        self.children_map[parent_id] = children


@pytest.fixture
def qt_app():
    """Create QApplication for tests that need it."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    yield app


@pytest.fixture
def sample_elements():
    """Create sample elements for testing."""
    return [
        MockElement("root1", "Root Element 1", "title", 0.9),
        MockElement("root2", "Root Element 2", "title", 0.8),
        MockElement("child1", "Child Element 1", "text", 0.7),
        MockElement("child2", "Child Element 2", "text", 0.6),
        MockElement("grandchild1", "Grandchild Element 1", "text", 0.5),
    ]


@pytest.fixture
def element_provider(sample_elements):
    """Create element provider with hierarchical structure."""
    provider = MockElementProvider(sample_elements)
    provider.set_children("root1", [sample_elements[2], sample_elements[3]])  # child1, child2
    provider.set_children("child1", [sample_elements[4]])  # grandchild1
    return provider


class TestElementTreeModel:
    """Test cases for ElementTreeModel class."""
    
    def test_model_creation_without_provider(self, qt_app):
        """Test creating model without element provider."""
        model = ElementTreeModel()
        
        assert model.rowCount() == 0
        assert model.columnCount() == 3  # Content, Type, Confidence
        assert model._element_provider is None
    
    def test_model_creation_with_provider(self, qt_app, element_provider):
        """Test creating model with element provider."""
        model = ElementTreeModel(element_provider)
        
        assert model.rowCount() == 2  # Two root elements
        assert model.columnCount() == 3
        assert model._element_provider is element_provider
    
    def test_header_data(self, qt_app):
        """Test header data retrieval."""
        model = ElementTreeModel()
        
        # Test horizontal headers
        assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "Content"
        assert model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "Type"
        assert model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "Confidence"
        
        # Test tooltips
        tooltip = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
        assert "content" in tooltip.lower()
        
        # Test invalid section
        assert model.headerData(10, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == ""
    
    def test_index_creation(self, qt_app, element_provider):
        """Test model index creation."""
        model = ElementTreeModel(element_provider)
        
        # Valid indices
        root_index = model.index(0, 0)
        assert root_index.isValid()
        
        root_index2 = model.index(1, 0)
        assert root_index2.isValid()
        
        # Invalid indices
        invalid_index = model.index(10, 0)
        assert not invalid_index.isValid()
        
        invalid_index2 = model.index(0, 10)
        assert not invalid_index2.isValid()
    
    def test_parent_child_relationships(self, qt_app, element_provider):
        """Test parent-child index relationships."""
        model = ElementTreeModel(element_provider)
        
        # Get root index
        root_index = model.index(0, 0)  # root1
        assert root_index.isValid()
        
        # Root should have no parent
        root_parent = model.parent(root_index)
        assert not root_parent.isValid()
        
        # Root should have children
        assert model.rowCount(root_index) == 2  # child1, child2
        
        # Get child index
        child_index = model.index(0, 0, root_index)  # child1
        assert child_index.isValid()
        
        # Child's parent should be root
        child_parent = model.parent(child_index)
        assert child_parent.isValid()
        assert child_parent.row() == root_index.row()
        assert child_parent.column() == root_index.column()
    
    def test_data_retrieval(self, qt_app, element_provider):
        """Test data retrieval for different roles."""
        model = ElementTreeModel(element_provider)
        
        # Get root index
        root_index = model.index(0, 0)
        
        # Display role
        content = model.data(root_index, Qt.ItemDataRole.DisplayRole)
        assert content == "Root Element 1"
        
        type_data = model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole)
        assert type_data == "Title"
        
        confidence_data = model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole)
        assert "90.0%" in confidence_data
        
        # User role (element ID)
        element_id = model.data(root_index, Qt.ItemDataRole.UserRole)
        assert element_id == "root1"
        
        # Tooltip role
        tooltip = model.data(root_index, Qt.ItemDataRole.ToolTipRole)
        assert "root1" in tooltip
        assert "Title" in tooltip
        
        # Invalid index
        invalid_data = model.data(QModelIndex(), Qt.ItemDataRole.DisplayRole)
        assert invalid_data is None or invalid_data == ""
    
    def test_hasChildren(self, qt_app, element_provider):
        """Test hasChildren method."""
        model = ElementTreeModel(element_provider)
        
        # Root should have children
        root_index = model.index(0, 0)
        assert model.hasChildren(root_index)
        
        # Get a leaf node
        child_index = model.index(1, 0, root_index)  # child2 (no children)
        assert not model.hasChildren(child_index)
        
        # Invalid index
        assert not model.hasChildren(QModelIndex())
    
    def test_flags(self, qt_app, element_provider):
        """Test item flags."""
        model = ElementTreeModel(element_provider)
        
        root_index = model.index(0, 0)
        flags = model.flags(root_index)
        
        assert flags & Qt.ItemFlag.ItemIsEnabled
        assert flags & Qt.ItemFlag.ItemIsSelectable
        assert flags & Qt.ItemFlag.ItemIsDragEnabled
        
        # Invalid index
        invalid_flags = model.flags(QModelIndex())
        assert invalid_flags == Qt.ItemFlag.NoItemFlags
    
    def test_element_lookup_methods(self, qt_app, element_provider):
        """Test element lookup methods."""
        model = ElementTreeModel(element_provider)
        
        # Get node by element ID
        node = model.get_node_by_element_id("root1")
        assert node is not None
        assert node.element().id == "root1"
        
        # Get element by ID
        element = model.get_element_by_id("child1")
        assert element is not None
        assert element.id == "child1"
        
        # Get index by element ID
        index = model.get_index_by_element_id("root1")
        assert index.isValid()
        assert model.data(index, Qt.ItemDataRole.UserRole) == "root1"
        
        # Non-existent element
        assert model.get_node_by_element_id("nonexistent") is None
        assert model.get_element_by_id("nonexistent") is None
        assert not model.get_index_by_element_id("nonexistent").isValid()
    
    def test_add_element(self, qt_app, element_provider):
        """Test adding elements to the model."""
        model = ElementTreeModel(element_provider)
        
        # Count before addition
        initial_count = model.rowCount()
        
        # Add root element
        new_element = MockElement("new_root", "New Root", "title", 0.95)
        success = model.add_element(new_element)
        
        assert success
        assert model.rowCount() == initial_count + 1
        
        # Verify element was added
        node = model.get_node_by_element_id("new_root")
        assert node is not None
        assert node.element() is new_element
        
        # Add child element
        child_element = MockElement("new_child", "New Child", "text", 0.85)
        success = model.add_element(child_element, "new_root")
        
        assert success
        
        # Verify child was added
        child_node = model.get_node_by_element_id("new_child")
        assert child_node is not None
        assert child_node.parent() is node
    
    def test_remove_element(self, qt_app, element_provider):
        """Test removing elements from the model."""
        model = ElementTreeModel(element_provider)
        
        # Count before removal
        initial_count = model.rowCount()
        
        # Remove element with children (should remove all descendants)
        success = model.remove_element("root1")
        
        assert success
        assert model.rowCount() == initial_count - 1
        
        # Verify element and descendants were removed
        assert model.get_node_by_element_id("root1") is None
        assert model.get_node_by_element_id("child1") is None
        assert model.get_node_by_element_id("grandchild1") is None
        
        # Try to remove non-existent element
        success = model.remove_element("nonexistent")
        assert not success
    
    def test_update_element(self, qt_app, element_provider):
        """Test updating elements in the model."""
        model = ElementTreeModel(element_provider)
        
        # Update existing element
        updated_element = MockElement("root1", "Updated Root Element", "header", 0.95)
        success = model.update_element(updated_element)
        
        assert success
        
        # Verify update
        node = model.get_node_by_element_id("root1")
        assert node.element().text == "Updated Root Element"
        assert node.element().type == "header"
        assert node.element().confidence == 0.95
        
        # Try to update non-existent element
        nonexistent_element = MockElement("nonexistent", "Text", "text", 0.5)
        success = model.update_element(nonexistent_element)
        assert not success
    
    def test_refresh_operations(self, qt_app, element_provider):
        """Test refresh operations."""
        model = ElementTreeModel(element_provider)
        
        # Test refresh element
        success = model.refresh_element("root1")
        assert success  # Should succeed if provider returns element
        
        # Test refresh all
        initial_stats = model.get_tree_statistics()
        model.refresh_all()
        new_stats = model.get_tree_statistics()
        
        # Statistics should be the same after refresh
        assert new_stats['total_elements'] == initial_stats['total_elements']
    
    def test_tree_statistics(self, qt_app, element_provider):
        """Test tree statistics calculation."""
        model = ElementTreeModel(element_provider)
        
        stats = model.get_tree_statistics()
        
        assert 'total_elements' in stats
        assert 'total_nodes' in stats
        assert 'max_depth' in stats
        assert 'average_depth' in stats
        assert 'type_counts' in stats
        assert 'root_children' in stats
        
        assert stats['total_elements'] == 5
        assert stats['root_children'] == 2
        assert stats['type_counts']['title'] == 2
        assert stats['type_counts']['text'] == 3
    
    def test_tree_integrity_validation(self, qt_app, element_provider):
        """Test tree integrity validation."""
        model = ElementTreeModel(element_provider)
        
        # Valid tree should have no errors
        errors = model.validate_tree_integrity()
        assert len(errors) == 0
        
        # Create inconsistent state for testing
        model._element_map["fake_id"] = TreeNode(MockElement("fake", "Fake"))
        
        errors = model.validate_tree_integrity()
        assert len(errors) > 0
    
    def test_model_signals(self, qt_app, element_provider):
        """Test model signal emissions."""
        model = ElementTreeModel(element_provider)
        
        # Connect signal spy
        element_added_calls = []
        element_removed_calls = []
        element_updated_calls = []
        model_refreshed_calls = []
        
        model.elementAdded.connect(lambda eid: element_added_calls.append(eid))
        model.elementRemoved.connect(lambda eid: element_removed_calls.append(eid))
        model.elementUpdated.connect(lambda eid: element_updated_calls.append(eid))
        model.modelRefreshed.connect(lambda: model_refreshed_calls.append(True))
        
        # Test signals
        new_element = MockElement("signal_test", "Signal Test")
        model.add_element(new_element)
        assert "signal_test" in element_added_calls
        
        model.update_element(new_element)
        assert "signal_test" in element_updated_calls
        
        model.remove_element("signal_test")
        assert "signal_test" in element_removed_calls
        
        model.refresh_all()
        assert len(model_refreshed_calls) > 0
    
    def test_set_element_provider(self, qt_app, sample_elements):
        """Test setting element provider after model creation."""
        model = ElementTreeModel()
        
        assert model.rowCount() == 0
        
        # Set provider
        provider = MockElementProvider(sample_elements[:2])  # Only first two elements
        model.set_element_provider(provider)
        
        assert model.rowCount() == 2
        assert model._element_provider is provider
    
    def test_empty_provider_handling(self, qt_app):
        """Test handling of empty element provider."""
        empty_provider = MockElementProvider([])
        model = ElementTreeModel(empty_provider)
        
        assert model.rowCount() == 0
        assert model.columnCount() == 3
        
        # Should handle operations gracefully
        stats = model.get_tree_statistics()
        assert stats['total_elements'] == 0
    
    def test_error_handling(self, qt_app):
        """Test error handling in various scenarios."""
        # Provider that raises exceptions
        error_provider = Mock()
        error_provider.get_root_elements.side_effect = Exception("Test error")
        
        model = ElementTreeModel(error_provider)
        
        # Should not crash, just have empty tree
        assert model.rowCount() == 0
        
        # Test refresh with error
        model.refresh_all()
        assert model.rowCount() == 0
    
    def test_large_dataset_handling(self, qt_app):
        """Test model with larger dataset."""
        # Create large dataset
        elements = []
        for i in range(100):
            elements.append(MockElement(f"element_{i}", f"Element {i}", "text", 0.5))
        
        provider = MockElementProvider(elements)
        model = ElementTreeModel(provider)
        
        assert model.rowCount() == 100
        
        # Test operations on large dataset
        stats = model.get_tree_statistics()
        assert stats['total_elements'] == 100
        
        # Test lookup performance
        element = model.get_element_by_id("element_50")
        assert element is not None
        assert element.text == "Element 50"
    
    def test_deep_hierarchy(self, qt_app):
        """Test model with deep hierarchical structure."""
        elements = []
        provider = MockElementProvider()
        
        # Create chain of 10 levels
        for i in range(10):
            element = MockElement(f"level_{i}", f"Level {i}", "text", 0.5)
            elements.append(element)
            provider.elements.append(element)
            
            if i > 0:
                provider.set_children(f"level_{i-1}", [element])
        
        model = ElementTreeModel(provider)
        
        # Should have 1 root
        assert model.rowCount() == 1
        
        # Navigate down the hierarchy
        current_index = model.index(0, 0)
        depth = 0
        
        while model.hasChildren(current_index):
            depth += 1
            current_index = model.index(0, 0, current_index)
            assert current_index.isValid()
        
        assert depth == 9  # 0-8 have children, 9 is leaf
        
        stats = model.get_tree_statistics()
        assert stats['max_depth'] == 9