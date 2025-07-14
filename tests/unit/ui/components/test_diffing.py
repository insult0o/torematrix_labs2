"""
Tests for Widget Diffing Engine.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

from torematrix.ui.components.diffing import (
    DiffOperation,
    DiffPatch,
    VirtualNode,
    SimpleDiffStrategy,
    OptimizedDiffStrategy,
    WidgetDiffer,
    get_widget_differ
)


class TestDiffPatch:
    """Test DiffPatch functionality."""
    
    def test_patch_creation(self):
        """Test creating diff patches."""
        patch = DiffPatch(
            operation=DiffOperation.UPDATE,
            target=Mock(spec=QWidget),
            property_name="text",
            value="New Text",
            old_value="Old Text"
        )
        
        assert patch.operation == DiffOperation.UPDATE
        assert patch.property_name == "text"
        assert patch.value == "New Text"
        assert patch.old_value == "Old Text"
    
    def test_patch_apply(self):
        """Test applying patches."""
        widget = Mock(spec=QWidget)
        patch = DiffPatch(
            operation=DiffOperation.UPDATE,
            target=widget,
            property_name="text",
            value="Updated"
        )
        
        patch.apply()
        
        # Should set attribute
        assert hasattr(widget, "text")
        assert widget.text == "Updated"


class TestVirtualNode:
    """Test VirtualNode functionality."""
    
    def test_virtual_node_creation(self):
        """Test creating virtual nodes."""
        node = VirtualNode(
            widget_type=QPushButton,
            props={"text": "Click me", "enabled": True},
            key="button1"
        )
        
        assert node.widget_type == QPushButton
        assert node.props["text"] == "Click me"
        assert node.props["enabled"] is True
        assert node.key == "button1"
    
    def test_virtual_node_hash(self):
        """Test virtual node hashing."""
        node1 = VirtualNode(
            widget_type=QPushButton,
            props={},
            key="button1"
        )
        node2 = VirtualNode(
            widget_type=QPushButton,
            props={},
            key="button1"
        )
        
        # Same key should have same hash
        assert hash(node1) == hash(node2)
    
    def test_get_widget(self):
        """Test getting widget from node."""
        widget = Mock(spec=QWidget)
        node = VirtualNode(
            widget_type=QWidget,
            props={},
            ref=Mock(return_value=widget)
        )
        
        assert node.get_widget() == widget


class TestSimpleDiffStrategy:
    """Test SimpleDiffStrategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = SimpleDiffStrategy()
    
    def test_diff_create_node(self):
        """Test diffing when creating new node."""
        new_node = VirtualNode(
            widget_type=QPushButton,
            props={"text": "New"}
        )
        
        patches = self.strategy.diff(None, new_node)
        
        assert len(patches) == 1
        assert patches[0].operation == DiffOperation.CREATE
        assert patches[0].value == new_node
    
    def test_diff_delete_node(self):
        """Test diffing when deleting node."""
        widget = Mock(spec=QWidget)
        old_node = VirtualNode(
            widget_type=QPushButton,
            props={},
            ref=Mock(return_value=widget)
        )
        
        patches = self.strategy.diff(old_node, None)
        
        assert len(patches) == 1
        assert patches[0].operation == DiffOperation.DELETE
        assert patches[0].target == widget
    
    def test_diff_replace_node(self):
        """Test diffing when replacing node type."""
        widget = Mock(spec=QPushButton)
        old_node = VirtualNode(
            widget_type=QPushButton,
            props={},
            ref=Mock(return_value=widget)
        )
        new_node = VirtualNode(
            widget_type=QLabel,
            props={}
        )
        
        patches = self.strategy.diff(old_node, new_node)
        
        assert len(patches) == 1
        assert patches[0].operation == DiffOperation.REPLACE
        assert patches[0].target == widget
        assert patches[0].value == new_node
    
    def test_diff_update_props(self):
        """Test diffing property updates."""
        widget = Mock(spec=QWidget)
        old_node = VirtualNode(
            widget_type=QPushButton,
            props={"text": "Old", "enabled": True},
            ref=Mock(return_value=widget)
        )
        new_node = VirtualNode(
            widget_type=QPushButton,
            props={"text": "New", "enabled": True}
        )
        
        patches = self.strategy.diff(old_node, new_node)
        
        # Should have one update for "text"
        assert len(patches) == 1
        assert patches[0].operation == DiffOperation.UPDATE
        assert patches[0].property_name == "text"
        assert patches[0].value == "New"
        assert patches[0].old_value == "Old"
    
    def test_diff_children_simple(self):
        """Test diffing children without keys."""
        widget = Mock(spec=QWidget)
        old_node = VirtualNode(
            widget_type=QWidget,
            props={},
            ref=Mock(return_value=widget),
            children=[
                VirtualNode(widget_type=QPushButton, props={"text": "1"}),
                VirtualNode(widget_type=QPushButton, props={"text": "2"})
            ]
        )
        new_node = VirtualNode(
            widget_type=QWidget,
            props={},
            children=[
                VirtualNode(widget_type=QPushButton, props={"text": "1"}),
                VirtualNode(widget_type=QPushButton, props={"text": "3"}),
                VirtualNode(widget_type=QPushButton, props={"text": "4"})
            ]
        )
        
        patches = self.strategy.diff(old_node, new_node)
        
        # Should have updates for second child and create for third
        assert any(p.operation == DiffOperation.UPDATE for p in patches)
        assert any(p.operation == DiffOperation.CREATE for p in patches)
    
    def test_diff_keyed_children(self):
        """Test diffing children with keys."""
        widget = Mock(spec=QWidget)
        old_node = VirtualNode(
            widget_type=QWidget,
            props={},
            ref=Mock(return_value=widget),
            children=[
                VirtualNode(widget_type=QPushButton, props={}, key="btn1"),
                VirtualNode(widget_type=QPushButton, props={}, key="btn2"),
                VirtualNode(widget_type=QPushButton, props={}, key="btn3")
            ]
        )
        new_node = VirtualNode(
            widget_type=QWidget,
            props={},
            children=[
                VirtualNode(widget_type=QPushButton, props={}, key="btn2"),
                VirtualNode(widget_type=QPushButton, props={}, key="btn1"),
                VirtualNode(widget_type=QPushButton, props={}, key="btn4")
            ]
        )
        
        patches = self.strategy.diff(old_node, new_node)
        
        # Should have move operations and delete/create
        operations = {p.operation for p in patches}
        assert DiffOperation.MOVE in operations
        assert DiffOperation.DELETE in operations
        assert DiffOperation.CREATE in operations


class TestOptimizedDiffStrategy:
    """Test OptimizedDiffStrategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = OptimizedDiffStrategy()
    
    def test_caching(self):
        """Test diff caching."""
        node1 = VirtualNode(widget_type=QPushButton, props={"text": "Test"})
        node2 = VirtualNode(widget_type=QPushButton, props={"text": "Test2"})
        
        # First diff - cache miss
        patches1 = self.strategy.diff(node1, node2)
        assert self.strategy._cache_misses == 1
        assert self.strategy._cache_hits == 0
        
        # Same diff - cache hit
        patches2 = self.strategy.diff(node1, node2)
        assert self.strategy._cache_hits == 1
        
        # Results should be equal
        assert len(patches1) == len(patches2)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        node1 = VirtualNode(widget_type=QPushButton, props={})
        node2 = VirtualNode(widget_type=QPushButton, props={})
        
        self.strategy.diff(node1, node2)
        self.strategy.diff(node1, node2)
        self.strategy.diff(None, node1)
        
        stats = self.strategy.get_cache_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["size"] == 2
        assert 0 <= stats["hit_rate"] <= 1


class TestWidgetDiffer:
    """Test WidgetDiffer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.differ = WidgetDiffer()
    
    def test_create_virtual_tree(self):
        """Test creating virtual tree from widget."""
        widget = Mock(spec=QWidget)
        widget.__class__.__name__ = "TestWidget"
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = True
        widget.geometry.return_value = Mock()
        widget.toolTip.return_value = "Test"
        widget.styleSheet.return_value = ""
        widget.objectName.return_value = "test_widget"
        widget.layout.return_value = None
        
        tree = self.differ.create_virtual_tree(widget)
        
        assert tree.widget_type.__name__ == "TestWidget"
        assert tree.key == "test_widget"
        assert tree.props["enabled"] is True
        assert tree.props["visible"] is True
        assert tree.props["toolTip"] == "Test"
    
    def test_create_virtual_tree_with_children(self):
        """Test creating virtual tree with children."""
        parent = Mock(spec=QWidget)
        parent.__class__.__name__ = "ParentWidget"
        parent.objectName.return_value = "parent"
        
        child = Mock(spec=QWidget)
        child.__class__.__name__ = "ChildWidget"
        child.objectName.return_value = "child"
        
        # Mock layout
        layout = Mock()
        layout.count.return_value = 1
        item = Mock()
        item.widget.return_value = child
        layout.itemAt.return_value = item
        parent.layout.return_value = layout
        
        # Mock properties
        for widget in [parent, child]:
            widget.isEnabled.return_value = True
            widget.isVisible.return_value = True
            widget.geometry.return_value = Mock()
            widget.toolTip.return_value = ""
            widget.styleSheet.return_value = ""
        
        tree = self.differ.create_virtual_tree(parent)
        
        assert len(tree.children) == 1
        assert tree.children[0].widget_type.__name__ == "ChildWidget"
    
    def test_diff_properties(self):
        """Test diffing properties only."""
        widget = Mock(spec=QWidget)
        old_props = {"text": "Old", "enabled": True}
        new_props = {"text": "New", "enabled": False, "visible": True}
        
        patches = self.differ.diff_properties(widget, old_props, new_props)
        
        assert len(patches) == 3  # text, enabled, visible
        
        # Check patches
        prop_changes = {p.property_name: p for p in patches}
        assert prop_changes["text"].value == "New"
        assert prop_changes["enabled"].value is False
        assert prop_changes["visible"].value is True
    
    def test_batch_patches(self):
        """Test batching patches."""
        widget = Mock(spec=QWidget)
        patch1 = DiffPatch(DiffOperation.UPDATE, widget, property_name="text", value="1")
        patch2 = DiffPatch(DiffOperation.UPDATE, widget, property_name="enabled", value=True)
        
        self.differ.batch_patches([patch1])
        self.differ.batch_patches([patch2])
        
        pending = self.differ.get_pending_patches()
        
        assert len(pending) == 2
        assert pending[0] == patch1
        assert pending[1] == patch2
        
        # Should be cleared after getting
        assert len(self.differ.get_pending_patches()) == 0
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        widget = Mock(spec=QWidget)
        widget.__class__.__name__ = "TestWidget"
        widget.objectName.return_value = "test"
        widget.layout.return_value = None
        
        # Mock properties
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = True
        widget.geometry.return_value = Mock()
        widget.toolTip.return_value = ""
        widget.styleSheet.return_value = ""
        
        # Create and cache
        tree1 = self.differ.create_virtual_tree(widget)
        assert widget in self.differ._virtual_tree_cache
        
        # Invalidate specific widget
        self.differ.invalidate_cache(widget)
        assert widget not in self.differ._virtual_tree_cache
        
        # Create again and invalidate all
        tree2 = self.differ.create_virtual_tree(widget)
        self.differ.invalidate_cache()
        assert len(self.differ._virtual_tree_cache) == 0


class TestGlobalDiffer:
    """Test global differ instance."""
    
    def test_get_widget_differ(self):
        """Test getting global differ."""
        differ1 = get_widget_differ()
        differ2 = get_widget_differ()
        
        assert differ1 is differ2  # Should be same instance
        assert isinstance(differ1, WidgetDiffer)