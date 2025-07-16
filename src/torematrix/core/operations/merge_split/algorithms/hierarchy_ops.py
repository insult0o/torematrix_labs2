"""
Hierarchy Operations for Merge/Split

Handles parent-child relationships and hierarchical structure preservation.
"""

from typing import List, Optional, Dict, Any
from collections import defaultdict
import logging

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class HierarchyProcessor:
    """Processes hierarchical relationships for merge/split operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".HierarchyProcessor")
    
    def analyze_hierarchy(self, elements: List[Element]) -> Dict[str, Any]:
        """Analyze hierarchical relationships among elements."""
        if not elements:
            return {
                "valid": True,
                "roots": [],
                "children": {},
                "parents": {},
                "depth": 0
            }
        
        # Build parent-child relationships
        children = defaultdict(list)
        parents = {}
        roots = []
        
        element_lookup = {elem.element_id: elem for elem in elements}
        
        for elem in elements:
            if elem.parent_id:
                if elem.parent_id in element_lookup:
                    children[elem.parent_id].append(elem.element_id)
                    parents[elem.element_id] = elem.parent_id
                else:
                    roots.append(elem.element_id)
            else:
                roots.append(elem.element_id)
        
        # Calculate maximum depth
        max_depth = self._calculate_max_depth(roots, children)
        
        return {
            "valid": True,
            "roots": roots,
            "children": dict(children),
            "parents": parents,
            "depth": max_depth
        }
    
    def merge_hierarchy(self, elements: List[Element]) -> Optional[str]:
        """Determine parent for merged element."""
        if not elements:
            return None
        
        # If all elements have the same parent, use that
        parent_ids = {elem.parent_id for elem in elements}
        
        if len(parent_ids) == 1:
            return list(parent_ids)[0]
        
        # Use parent of first element
        return elements[0].parent_id
    
    def split_hierarchy(self, element: Element, split_count: int) -> List[Optional[str]]:
        """Determine parent for split elements."""
        # All split elements inherit the same parent
        return [element.parent_id] * split_count
    
    def _calculate_max_depth(self, roots: List[str], children: Dict[str, List[str]]) -> int:
        """Calculate maximum depth of hierarchy."""
        if not roots:
            return 0
        
        max_depth = 0
        for root in roots:
            depth = self._calculate_depth_from_node(root, children)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_depth_from_node(self, node_id: str, children: Dict[str, List[str]]) -> int:
        """Calculate depth from a specific node."""
        if node_id not in children or not children[node_id]:
            return 1
        
        max_child_depth = 0
        for child_id in children[node_id]:
            child_depth = self._calculate_depth_from_node(child_id, children)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth + 1