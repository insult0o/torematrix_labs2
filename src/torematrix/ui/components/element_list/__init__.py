"""
Hierarchical Element List Component

This package provides a comprehensive hierarchical tree view for document elements
with support for large datasets, interactive features, and system integration.

Main Components:
- HierarchicalTreeView: Main tree view widget
- ElementTreeModel: Qt model for hierarchical data
- TreeNode: Individual node representation
"""

from .tree_view import HierarchicalTreeView
from .models.tree_model import ElementTreeModel
from .models.tree_node import TreeNode

__all__ = [
    'HierarchicalTreeView',
    'ElementTreeModel', 
    'TreeNode'
]