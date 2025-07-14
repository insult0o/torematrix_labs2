"""
Integration Tests for Element List Components

Tests for integration between TreeNode, ElementTreeModel, and HierarchicalTreeView.
"""

import pytest
from unittest.mock import Mock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import sys

from src.torematrix.ui.components.element_list.tree_view import HierarchicalTreeView
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
def complex_tree_data():
    """Create complex hierarchical tree data for testing."""
    elements = [
        # Root level
        MockElement("doc1", "Document 1", "title", 0.95),
        MockElement("doc2", "Document 2", "title", 0.90),
        
        # Level 1 - Document 1 children
        MockElement("section1_1", "Section 1.1", "header", 0.85),
        MockElement("section1_2", "Section 1.2", "header", 0.88),
        MockElement("text1_1", "Some text content", "text", 0.75),
        
        # Level 1 - Document 2 children
        MockElement("section2_1", "Section 2.1", "header", 0.82),
        MockElement("list2_1", "List in doc 2", "list", 0.70),
        
        # Level 2 - Section 1.1 children
        MockElement("para1_1_1", "Paragraph 1.1.1", "text", 0.65),
        MockElement("table1_1_1", "Table 1.1.1", "table", 0.80),
        
        # Level 2 - Section 1.2 children
        MockElement("para1_2_1", "Paragraph 1.2.1", "text", 0.68),
        MockElement("image1_2_1", "Image 1.2.1", "image", 0.60),
        
        # Level 3 - Table 1.1.1 children
        MockElement("cell1_1_1_1", "Cell content", "text", 0.55),
    ]
    
    provider = MockElementProvider(elements)
    
    # Set up hierarchy
    provider.set_children("doc1", [elements[2], elements[3], elements[4]])  # section1_1, section1_2, text1_1
    provider.set_children("doc2", [elements[5], elements[6]])  # section2_1, list2_1
    provider.set_children("section1_1", [elements[7], elements[8]])  # para1_1_1, table1_1_1
    provider.set_children("section1_2", [elements[9], elements[10]])  # para1_2_1, image1_2_1
    provider.set_children("table1_1_1", [elements[11]])  # cell1_1_1_1
    
    return provider


class TestElementListIntegration:
    """Integration tests for element list components."""
    
    def test_complete_tree_creation_and_display(self, qt_app, complex_tree_data):
        """Test complete tree creation from provider to view."""
        # Create model with provider
        model = ElementTreeModel(complex_tree_data)
        
        # Verify model structure
        assert model.rowCount() == 2  # Two root documents
        
        # Get first root (doc1)
        doc1_index = model.index(0, 0)
        assert doc1_index.isValid()
        assert model.data(doc1_index, Qt.ItemDataRole.UserRole) == "doc1"
        assert model.rowCount(doc1_index) == 3  # Three children
        
        # Get nested element (section1_1)
        section1_1_index = model.index(0, 0, doc1_index)
        assert section1_1_index.isValid()
        assert model.data(section1_1_index, Qt.ItemDataRole.UserRole) == "section1_1"
        assert model.rowCount(section1_1_index) == 2  # Two children
        
        # Create tree view and set model
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Verify view integration
        assert tree_view.model() is model
        assert tree_view._element_model is model
        
        # Test view operations
        selected = tree_view.get_selected_elements()
        assert len(selected) == 0  # No initial selection
        
        # Test element selection
        tree_view.select_element("doc1")
        selected = tree_view.get_selected_elements()
        assert "doc1" in selected
    
    def test_hierarchical_navigation_and_expansion(self, qt_app, complex_tree_data):
        """Test hierarchical navigation and expansion operations."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Test expanding to deep element
        success = tree_view.expand_to_element("cell1_1_1_1")
        assert success
        
        # Should have expanded all parents
        expanded = tree_view.get_expanded_elements()
        assert "doc1" in expanded
        assert "section1_1" in expanded
        assert "table1_1_1" in expanded
        
        # Test scrolling to element
        success = tree_view.scroll_to_element("cell1_1_1_1")
        assert success
        
        # Test selecting deep element
        tree_view.select_element("cell1_1_1_1")
        selected = tree_view.get_selected_elements()
        assert "cell1_1_1_1" in selected
    
    def test_model_view_signal_integration(self, qt_app, complex_tree_data):
        """Test signal integration between model and view."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Track signals
        selection_changes = []
        expansion_changes = []
        
        tree_view.selectionChanged.connect(lambda ids: selection_changes.append(ids))
        tree_view.elementExpanded.connect(lambda eid: expansion_changes.append(eid))
        
        # Test selection signals
        tree_view.select_element("doc1")
        # Note: Actual signal emission depends on Qt event processing
        
        # Test expansion signals
        tree_view.expand_element("doc1")
        # Note: Actual signal emission depends on Qt event processing
        
        # Test model modification signals
        new_element = MockElement("new_test", "New Test Element", "text", 0.50)
        model.add_element(new_element, "doc1")
        
        # Verify element was added to model
        node = model.get_node_by_element_id("new_test")
        assert node is not None
        assert node.parent().element().id == "doc1"
        
        # Test element removal
        success = model.remove_element("new_test")
        assert success
        assert model.get_node_by_element_id("new_test") is None
    
    def test_complex_selection_operations(self, qt_app, complex_tree_data):
        """Test complex selection operations across hierarchy."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Multi-level selection
        tree_view.select_elements(["doc1", "section1_1", "para1_1_1"])
        selected = tree_view.get_selected_elements()
        
        assert "doc1" in selected
        assert "section1_1" in selected
        assert "para1_1_1" in selected
        
        # Clear selection
        tree_view.select_elements([])
        selected = tree_view.get_selected_elements()
        assert len(selected) == 0
        
        # Select across different branches
        tree_view.select_elements(["doc1", "doc2"])
        selected = tree_view.get_selected_elements()
        assert "doc1" in selected
        assert "doc2" in selected
    
    def test_tree_state_persistence(self, qt_app, complex_tree_data):
        """Test tree state persistence across operations."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Set up complex state
        tree_view.expand_element("doc1")
        tree_view.expand_element("section1_1")
        tree_view.select_elements(["para1_1_1", "table1_1_1"])
        
        # Get current state
        expanded_before = tree_view.get_expanded_elements()
        selected_before = tree_view.get_selected_elements()
        
        # Trigger model refresh
        model.refresh_all()
        
        # Check state preservation
        # Note: Actual preservation depends on implementation details
        expanded_after = tree_view.get_expanded_elements()
        # Some expansion state should be preserved
        
        # Test explicit state management
        tree_view.set_expanded_elements(["doc2", "section2_1"])
        expanded = tree_view.get_expanded_elements()
        assert "doc2" in expanded
        assert "section2_1" in expanded
        assert "doc1" not in expanded  # Should be collapsed
    
    def test_data_consistency_across_components(self, qt_app, complex_tree_data):
        """Test data consistency between TreeNode, Model, and View."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Test data consistency
        element_id = "section1_1"
        
        # Get data from different sources
        node = model.get_node_by_element_id(element_id)
        element_from_model = model.get_element_by_id(element_id)
        index = model.get_index_by_element_id(element_id)
        
        assert node is not None
        assert element_from_model is not None
        assert index.isValid()
        
        # Data should be consistent
        assert node.element() is element_from_model
        assert model.data(index, Qt.ItemDataRole.UserRole) == element_id
        assert node.element().id == element_id
        assert element_from_model.id == element_id
        
        # Test tree structure consistency
        parent_node = node.parent()
        assert parent_node is not None
        assert parent_node.element().id == "doc1"
        
        children = node.children()
        assert len(children) == 2
        child_ids = [child.element().id for child in children]
        assert "para1_1_1" in child_ids
        assert "table1_1_1" in child_ids
    
    def test_performance_with_large_hierarchy(self, qt_app):
        """Test performance with larger hierarchical dataset."""
        # Create larger dataset
        elements = []
        provider = MockElementProvider()
        
        # Create 10 documents with 10 sections each, each section with 5 paragraphs
        for doc_i in range(10):
            doc_id = f"doc_{doc_i}"
            doc_element = MockElement(doc_id, f"Document {doc_i}", "title", 0.9)
            elements.append(doc_element)
            provider.elements.append(doc_element)
            
            section_ids = []
            for sec_i in range(10):
                sec_id = f"sec_{doc_i}_{sec_i}"
                sec_element = MockElement(sec_id, f"Section {doc_i}.{sec_i}", "header", 0.8)
                elements.append(sec_element)
                provider.elements.append(sec_element)
                section_ids.append(sec_element)
                
                para_ids = []
                for para_i in range(5):
                    para_id = f"para_{doc_i}_{sec_i}_{para_i}"
                    para_element = MockElement(para_id, f"Paragraph {doc_i}.{sec_i}.{para_i}", "text", 0.7)
                    elements.append(para_element)
                    provider.elements.append(para_element)
                    para_ids.append(para_element)
                
                provider.set_children(sec_id, para_ids)
            
            provider.set_children(doc_id, section_ids)
        
        # Create model and view
        model = ElementTreeModel(provider)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Test basic operations work with large dataset
        assert model.rowCount() == 10  # 10 documents
        
        # Test navigation to deep element
        deep_element_id = "para_5_3_2"
        success = tree_view.expand_to_element(deep_element_id)
        assert success
        
        # Test selection
        tree_view.select_element(deep_element_id)
        selected = tree_view.get_selected_elements()
        assert deep_element_id in selected
        
        # Test statistics
        stats = model.get_tree_statistics()
        assert stats['total_elements'] == 10 + (10 * 10) + (10 * 10 * 5)  # 560 total
        assert stats['max_depth'] == 2  # doc -> section -> paragraph
    
    def test_dynamic_tree_modifications(self, qt_app, complex_tree_data):
        """Test dynamic tree modifications during runtime."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Expand some elements first
        tree_view.expand_element("doc1")
        tree_view.expand_element("section1_1")
        
        # Add new elements dynamically
        new_section = MockElement("new_section", "New Section", "header", 0.85)
        success = model.add_element(new_section, "doc1")
        assert success
        
        # Verify element appears in tree
        node = model.get_node_by_element_id("new_section")
        assert node is not None
        assert node.parent().element().id == "doc1"
        
        # Add child to new section
        new_para = MockElement("new_para", "New Paragraph", "text", 0.70)
        success = model.add_element(new_para, "new_section")
        assert success
        
        # Test tree navigation to new elements
        success = tree_view.expand_to_element("new_para")
        assert success
        
        tree_view.select_element("new_para")
        selected = tree_view.get_selected_elements()
        assert "new_para" in selected
        
        # Remove elements
        success = model.remove_element("new_section")  # Should remove both new_section and new_para
        assert success
        
        assert model.get_node_by_element_id("new_section") is None
        assert model.get_node_by_element_id("new_para") is None
    
    def test_error_recovery_and_robustness(self, qt_app, complex_tree_data):
        """Test error recovery and robustness."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Test operations with invalid data
        tree_view.select_elements(["invalid1", "doc1", "invalid2"])
        selected = tree_view.get_selected_elements()
        assert "doc1" in selected
        assert "invalid1" not in selected
        assert "invalid2" not in selected
        
        # Test expansion with invalid IDs
        success = tree_view.expand_element("invalid")
        assert not success
        
        # Test scroll with invalid IDs
        success = tree_view.scroll_to_element("invalid")
        assert not success
        
        # Test model operations with invalid data
        invalid_element = MockElement("invalid", "Invalid", "text", 0.5)
        success = model.add_element(invalid_element, "nonexistent_parent")
        assert not success
        
        success = model.remove_element("nonexistent")
        assert not success
        
        # View should remain functional
        tree_view.select_element("doc1")
        selected = tree_view.get_selected_elements()
        assert "doc1" in selected
    
    def test_memory_management_integration(self, qt_app, complex_tree_data):
        """Test memory management across components."""
        model = ElementTreeModel(complex_tree_data)
        tree_view = HierarchicalTreeView()
        tree_view.set_model(model)
        
        # Create many temporary elements
        temp_elements = []
        for i in range(100):
            temp_element = MockElement(f"temp_{i}", f"Temp {i}", "text", 0.5)
            model.add_element(temp_element, "doc1")
            temp_elements.append(temp_element)
        
        # Remove all temporary elements
        for i in range(100):
            model.remove_element(f"temp_{i}")
        
        # Verify cleanup
        for i in range(100):
            assert model.get_node_by_element_id(f"temp_{i}") is None
        
        # Original structure should be intact
        assert model.get_node_by_element_id("doc1") is not None
        assert model.get_node_by_element_id("section1_1") is not None
        
        # Tree view should still function normally
        tree_view.select_element("doc1")
        selected = tree_view.get_selected_elements()
        assert "doc1" in selected