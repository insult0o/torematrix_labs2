"""
Tree-specific Events

Event classes for tree component communication.
"""

from typing import List, Optional, Any, Dict
from dataclasses import dataclass


@dataclass
class TreeSelectionEvent:
    """Event for tree selection changes."""
    
    selected_element_ids: List[str]
    previously_selected: List[str]
    source: str = "tree_view"
    
    def is_single_selection(self) -> bool:
        """Check if this is a single element selection."""
        return len(self.selected_element_ids) == 1
    
    def is_empty_selection(self) -> bool:
        """Check if selection is empty."""
        return len(self.selected_element_ids) == 0
    
    def get_added_selections(self) -> List[str]:
        """Get newly selected element IDs."""
        return [eid for eid in self.selected_element_ids if eid not in self.previously_selected]
    
    def get_removed_selections(self) -> List[str]:
        """Get deselected element IDs."""
        return [eid for eid in self.previously_selected if eid not in self.selected_element_ids]


@dataclass
class TreeExpansionEvent:
    """Event for tree expansion/collapse changes."""
    
    element_id: str
    expanded: bool
    source: str = "tree_view"
    children_count: Optional[int] = None
    
    def is_expansion(self) -> bool:
        """Check if this is an expansion event."""
        return self.expanded
    
    def is_collapse(self) -> bool:
        """Check if this is a collapse event."""
        return not self.expanded


@dataclass
class TreeNavigationEvent:
    """Event for tree navigation actions."""
    
    target_element_id: str
    action: str  # "scroll_to", "expand_to", "select"
    source: str = "tree_view"
    success: bool = True
    
    def is_scroll_action(self) -> bool:
        """Check if this is a scroll action."""
        return self.action == "scroll_to"
    
    def is_expand_action(self) -> bool:
        """Check if this is an expand action."""
        return self.action == "expand_to"
    
    def is_select_action(self) -> bool:
        """Check if this is a select action."""
        return self.action == "select"


@dataclass
class TreeModelEvent:
    """Event for tree model changes."""
    
    event_type: str  # "element_added", "element_removed", "element_updated", "model_refreshed"
    element_id: Optional[str] = None
    parent_id: Optional[str] = None
    source: str = "tree_model"
    metadata: Optional[Dict[str, Any]] = None
    
    def is_addition(self) -> bool:
        """Check if this is an element addition."""
        return self.event_type == "element_added"
    
    def is_removal(self) -> bool:
        """Check if this is an element removal."""
        return self.event_type == "element_removed"
    
    def is_update(self) -> bool:
        """Check if this is an element update."""
        return self.event_type == "element_updated"
    
    def is_refresh(self) -> bool:
        """Check if this is a model refresh."""
        return self.event_type == "model_refreshed"