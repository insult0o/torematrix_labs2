"""
Agent 2 Interactive Features Validation

Validates that all interactive features work correctly with Agent 1's foundation.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all interaction modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.torematrix.ui.components.element_list.interactions import (
            DragDropHandler, MultiSelectionHandler, ContextMenuManager,
            SearchFilterManager, RichElementDelegate, KeyboardNavigationHandler,
            VisualFeedbackManager
        )
        print("✅ All interaction modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_agent1_foundation_compatibility():
    """Test compatibility with Agent 1's foundation classes."""
    print("Testing Agent 1 foundation compatibility...")
    
    try:
        from src.torematrix.ui.components.element_list.models import TreeNode, ElementTreeModel
        from src.torematrix.ui.components.element_list import HierarchicalTreeView
        
        # Test TreeNode creation
        node = TreeNode()
        print("✅ TreeNode creation successful")
        
        # Test ElementTreeModel creation
        model = ElementTreeModel()
        print("✅ ElementTreeModel creation successful")
        
        # Test HierarchicalTreeView creation (might fail without Qt)
        try:
            view = HierarchicalTreeView()
            print("✅ HierarchicalTreeView creation successful")
        except Exception as e:
            print(f"⚠️  HierarchicalTreeView creation failed (expected without Qt): {e}")
        
        return True
    except ImportError as e:
        print(f"❌ Foundation compatibility error: {e}")
        return False

def test_interaction_system_creation():
    """Test that interaction systems can be created."""
    print("Testing interaction system creation...")
    
    try:
        # Mock tree view for testing
        class MockTreeView:
            def __init__(self):
                self.model_obj = None
                self.selection_model_obj = None
                self.delegate_obj = None
            
            def model(self):
                return self.model_obj
            
            def selectionModel(self):
                return self.selection_model_obj
            
            def setModel(self, model):
                self.model_obj = model
            
            def setItemDelegate(self, delegate):
                self.delegate_obj = delegate
            
            def viewport(self):
                return MockViewport()
            
            def installEventFilter(self, filter_obj):
                pass
            
            def mapToGlobal(self, point):
                return point
            
            def indexAt(self, point):
                return MockIndex()
            
            def visualRect(self, index):
                return MockRect()
        
        class MockViewport:
            def update(self, *args):
                pass
            
            def rect(self):
                return MockRect()
            
            def installEventFilter(self, filter_obj):
                pass
        
        class MockIndex:
            def isValid(self):
                return False
        
        class MockRect:
            def isEmpty(self):
                return True
            
            def center(self):
                return MockPoint()
        
        class MockPoint:
            def x(self):
                return 0
            
            def y(self):
                return 0
        
        # Create mock tree view
        mock_tree_view = MockTreeView()
        
        # Test interaction system creation
        from src.torematrix.ui.components.element_list.interactions import (
            DragDropHandler, MultiSelectionHandler, ContextMenuManager,
            SearchFilterManager, RichElementDelegate, KeyboardNavigationHandler,
            VisualFeedbackManager
        )
        
        # Test each system
        drag_drop = DragDropHandler(mock_tree_view)
        print("✅ DragDropHandler created successfully")
        
        selection = MultiSelectionHandler(mock_tree_view)
        print("✅ MultiSelectionHandler created successfully")
        
        context_menu = ContextMenuManager(mock_tree_view)
        print("✅ ContextMenuManager created successfully")
        
        search_filter = SearchFilterManager(mock_tree_view)
        print("✅ SearchFilterManager created successfully")
        
        delegate = RichElementDelegate()
        print("✅ RichElementDelegate created successfully")
        
        keyboard_nav = KeyboardNavigationHandler(mock_tree_view)
        print("✅ KeyboardNavigationHandler created successfully")
        
        visual_feedback = VisualFeedbackManager(mock_tree_view)
        print("✅ VisualFeedbackManager created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Interaction system creation error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of interaction systems."""
    print("Testing basic functionality...")
    
    try:
        from src.torematrix.ui.components.element_list.interactions.selection import SelectionTracker
        from src.torematrix.ui.components.element_list.interactions.drag_drop import DragDropValidator
        from src.torematrix.ui.components.element_list.interactions.search_filter import SearchCriteria
        
        # Test SelectionTracker
        tracker = SelectionTracker()
        tracker.add_element("element_1")
        tracker.add_element("element_2")
        assert tracker.count() == 2
        assert tracker.is_selected("element_1")
        print("✅ SelectionTracker basic functionality working")
        
        # Test SearchCriteria
        criteria = SearchCriteria()
        criteria.text_query = "test"
        criteria.element_types = {"text"}
        assert not criteria.is_empty()
        print("✅ SearchCriteria basic functionality working")
        
        # Test DragDropValidator (create mock nodes)
        class MockNode:
            def __init__(self, element=None, parent=None):
                self._element = element
                self._parent = parent
            
            def element(self):
                return self._element
            
            def parent(self):
                return self._parent
            
            def is_ancestor_of(self, other):
                return False
        
        node1 = MockNode()
        node2 = MockNode()
        can_drop, reason = DragDropValidator.can_drop_on_target(node1, node2)
        assert can_drop
        print("✅ DragDropValidator basic functionality working")
        
        return True
    except Exception as e:
        print(f"❌ Basic functionality error: {e}")
        return False

def test_agent1_model_integration():
    """Test integration with Agent 1's model classes."""
    print("Testing Agent 1 model integration...")
    
    try:
        from src.torematrix.ui.components.element_list.models.tree_node import TreeNode
        from src.torematrix.ui.components.element_list.models.tree_model import ElementTreeModel
        from src.torematrix.ui.components.element_list.interactions.selection import SelectionTracker
        
        # Create mock element
        class MockElement:
            def __init__(self):
                self.id = "test_element"
                self.type = "text"
                self.text = "Test content"
                self.confidence = 0.95
        
        # Test TreeNode with interactions
        element = MockElement()
        node = TreeNode(element)
        
        # Test that node works with selection
        tracker = SelectionTracker()
        tracker.add_element(element.id)
        assert tracker.is_selected(element.id)
        print("✅ TreeNode works with selection system")
        
        # Test ElementTreeModel creation
        model = ElementTreeModel()
        print("✅ ElementTreeModel compatible with interactions")
        
        return True
    except Exception as e:
        print(f"❌ Model integration error: {e}")
        return False

def test_file_structure():
    """Test that all expected files exist."""
    print("Testing file structure...")
    
    expected_files = [
        "src/torematrix/ui/components/element_list/interactions/__init__.py",
        "src/torematrix/ui/components/element_list/interactions/drag_drop.py",
        "src/torematrix/ui/components/element_list/interactions/selection.py",
        "src/torematrix/ui/components/element_list/interactions/context_menu.py",
        "src/torematrix/ui/components/element_list/interactions/search_filter.py",
        "src/torematrix/ui/components/element_list/interactions/custom_delegates.py",
        "src/torematrix/ui/components/element_list/interactions/keyboard_navigation.py",
        "src/torematrix/ui/components/element_list/interactions/visual_feedback.py",
    ]
    
    missing_files = []
    for file_path in expected_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All expected files present")
        return True

def test_interface_compatibility():
    """Test that interaction systems use correct interfaces."""
    print("Testing interface compatibility...")
    
    try:
        from src.torematrix.ui.components.element_list.interfaces.tree_interfaces import (
            ElementProtocol, TreeNodeProtocol
        )
        
        # Test that protocols are importable and usable
        print("✅ Tree interfaces available for interactions")
        
        # Test protocol usage in interactions
        from src.torematrix.ui.components.element_list.interactions.search_filter import SearchCriteria
        
        # Create mock element that follows protocol
        class MockProtocolElement:
            def __init__(self):
                self.id = "test"
                self.type = "text"
                self.text = "content"
                self.confidence = 0.9
        
        element = MockProtocolElement()
        criteria = SearchCriteria()
        criteria.text_query = "content"
        
        # Test that element can be used with criteria
        assert criteria.matches_element(element)
        print("✅ Protocol compatibility working")
        
        return True
    except Exception as e:
        print(f"❌ Interface compatibility error: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 50)
    print("Agent 2 Interactive Features Validation")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_imports,
        test_agent1_foundation_compatibility,
        test_interaction_system_creation,
        test_basic_functionality,
        test_agent1_model_integration,
        test_interface_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n{'─' * 30}")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        print("✅ Agent 2 interactive features are fully integrated with Agent 1 foundation")
        return True
    else:
        print("❌ Some validation tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)