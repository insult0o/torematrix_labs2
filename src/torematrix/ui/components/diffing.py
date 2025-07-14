"""
Widget Diffing Engine for Reactive Components.

This module provides virtual DOM-like diffing capabilities for Qt widgets,
enabling efficient updates with minimal re-rendering.
"""

from __future__ import annotations

import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget, QLayout

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")
W = TypeVar("W", bound=QWidget)


class DiffOperation(Enum):
    """Types of diff operations."""
    
    CREATE = auto()      # Create new widget
    UPDATE = auto()      # Update existing widget
    MOVE = auto()        # Move widget to new position
    DELETE = auto()      # Delete widget
    REPLACE = auto()     # Replace widget with different type


@dataclass
class DiffPatch:
    """Represents a single diff operation to apply."""
    
    operation: DiffOperation
    target: Optional[Union[QWidget, str]]  # Widget or ID
    value: Any = None
    old_value: Any = None
    property_name: Optional[str] = None
    index: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def apply(self) -> None:
        """Apply this patch to the target."""
        if self.operation == DiffOperation.UPDATE and self.target:
            if isinstance(self.target, QWidget) and self.property_name:
                setattr(self.target, self.property_name, self.value)
        # Other operations handled by renderer


@dataclass
class VirtualNode:
    """Virtual representation of a widget for diffing."""
    
    widget_type: Type[QWidget]
    props: Dict[str, Any]
    children: List[VirtualNode] = field(default_factory=list)
    key: Optional[str] = None
    ref: Optional[weakref.ref[QWidget]] = None
    
    def __hash__(self) -> int:
        """Make hashable for caching."""
        return hash((self.widget_type, self.key or id(self)))
    
    def get_widget(self) -> Optional[QWidget]:
        """Get the actual widget if available."""
        return self.ref() if self.ref else None


class DiffStrategy(ABC):
    """Base class for different diffing strategies."""
    
    @abstractmethod
    def diff(
        self,
        old_node: Optional[VirtualNode],
        new_node: Optional[VirtualNode]
    ) -> List[DiffPatch]:
        """Generate diff patches between nodes."""
        pass


class SimpleDiffStrategy(DiffStrategy):
    """Simple diffing strategy with basic optimizations."""
    
    def diff(
        self,
        old_node: Optional[VirtualNode],
        new_node: Optional[VirtualNode]
    ) -> List[DiffPatch]:
        """Generate diff patches using simple comparison."""
        patches = []
        
        # Handle creation/deletion
        if old_node is None and new_node is None:
            return patches
        elif old_node is None:
            patches.append(DiffPatch(
                operation=DiffOperation.CREATE,
                target=None,
                value=new_node
            ))
            return patches
        elif new_node is None:
            patches.append(DiffPatch(
                operation=DiffOperation.DELETE,
                target=old_node.get_widget()
            ))
            return patches
        
        # Check if types differ
        if old_node.widget_type != new_node.widget_type:
            patches.append(DiffPatch(
                operation=DiffOperation.REPLACE,
                target=old_node.get_widget(),
                value=new_node
            ))
            return patches
        
        # Diff properties
        patches.extend(self._diff_props(old_node, new_node))
        
        # Diff children
        patches.extend(self._diff_children(old_node, new_node))
        
        return patches
    
    def _diff_props(
        self,
        old_node: VirtualNode,
        new_node: VirtualNode
    ) -> List[DiffPatch]:
        """Diff properties between nodes."""
        patches = []
        widget = old_node.get_widget()
        
        if not widget:
            return patches
        
        # Check changed properties
        all_props = set(old_node.props.keys()) | set(new_node.props.keys())
        
        for prop in all_props:
            old_value = old_node.props.get(prop)
            new_value = new_node.props.get(prop)
            
            if old_value != new_value:
                patches.append(DiffPatch(
                    operation=DiffOperation.UPDATE,
                    target=widget,
                    property_name=prop,
                    value=new_value,
                    old_value=old_value
                ))
        
        return patches
    
    def _diff_children(
        self,
        old_node: VirtualNode,
        new_node: VirtualNode
    ) -> List[DiffPatch]:
        """Diff children using simple index-based comparison."""
        patches = []
        
        old_children = old_node.children
        new_children = new_node.children
        
        # Use key-based diffing if available
        if self._has_keys(old_children) and self._has_keys(new_children):
            return self._diff_keyed_children(old_node, new_node)
        
        # Simple index-based diffing
        max_len = max(len(old_children), len(new_children))
        
        for i in range(max_len):
            old_child = old_children[i] if i < len(old_children) else None
            new_child = new_children[i] if i < len(new_children) else None
            
            child_patches = self.diff(old_child, new_child)
            for patch in child_patches:
                patch.index = i
            patches.extend(child_patches)
        
        return patches
    
    def _has_keys(self, children: List[VirtualNode]) -> bool:
        """Check if children have keys."""
        return all(child.key is not None for child in children)
    
    def _diff_keyed_children(
        self,
        old_node: VirtualNode,
        new_node: VirtualNode
    ) -> List[DiffPatch]:
        """Diff children with keys for optimal reordering."""
        patches = []
        
        old_children = {child.key: child for child in old_node.children}
        new_children = {child.key: child for child in new_node.children}
        
        # Track processed keys
        processed = set()
        
        # Process new children in order
        for i, new_child in enumerate(new_node.children):
            key = new_child.key
            old_child = old_children.get(key)
            
            if old_child:
                # Child exists, check if moved
                old_index = next(
                    (j for j, c in enumerate(old_node.children) if c.key == key),
                    -1
                )
                
                if old_index != i:
                    patches.append(DiffPatch(
                        operation=DiffOperation.MOVE,
                        target=old_child.get_widget(),
                        index=i,
                        metadata={"old_index": old_index}
                    ))
                
                # Diff the child itself
                child_patches = self.diff(old_child, new_child)
                patches.extend(child_patches)
            else:
                # New child
                patches.append(DiffPatch(
                    operation=DiffOperation.CREATE,
                    target=None,
                    value=new_child,
                    index=i
                ))
            
            processed.add(key)
        
        # Remove old children not in new list
        for key, old_child in old_children.items():
            if key not in processed:
                patches.append(DiffPatch(
                    operation=DiffOperation.DELETE,
                    target=old_child.get_widget()
                ))
        
        return patches


class OptimizedDiffStrategy(SimpleDiffStrategy):
    """Optimized diffing with caching and heuristics."""
    
    def __init__(self):
        """Initialize optimized strategy."""
        self._diff_cache: Dict[Tuple[int, int], List[DiffPatch]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def diff(
        self,
        old_node: Optional[VirtualNode],
        new_node: Optional[VirtualNode]
    ) -> List[DiffPatch]:
        """Generate diff with caching."""
        # Check cache
        cache_key = (
            hash(old_node) if old_node else 0,
            hash(new_node) if new_node else 0
        )
        
        if cache_key in self._diff_cache:
            self._cache_hits += 1
            return self._diff_cache[cache_key].copy()
        
        self._cache_misses += 1
        
        # Generate diff
        patches = super().diff(old_node, new_node)
        
        # Cache result
        if len(self._diff_cache) < 1000:  # Limit cache size
            self._diff_cache[cache_key] = patches.copy()
        
        return patches
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._diff_cache),
            "hit_rate": self._cache_hits / max(1, self._cache_hits + self._cache_misses)
        }


class WidgetDiffer:
    """Main diffing engine for Qt widgets."""
    
    def __init__(self, strategy: Optional[DiffStrategy] = None):
        """Initialize differ with strategy."""
        self.strategy = strategy or OptimizedDiffStrategy()
        self._virtual_tree_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._pending_patches: List[DiffPatch] = []
    
    def create_virtual_tree(self, widget: QWidget) -> VirtualNode:
        """Create virtual representation of widget tree."""
        # Check cache
        if widget in self._virtual_tree_cache:
            return self._virtual_tree_cache[widget]
        
        # Extract properties
        props = self._extract_properties(widget)
        
        # Create virtual node
        node = VirtualNode(
            widget_type=type(widget),
            props=props,
            key=widget.objectName() or None,
            ref=weakref.ref(widget)
        )
        
        # Process children
        if hasattr(widget, "layout") and widget.layout():
            layout = widget.layout()
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    child_node = self.create_virtual_tree(item.widget())
                    node.children.append(child_node)
        
        # Cache result
        self._virtual_tree_cache[widget] = node
        
        return node
    
    def diff_widgets(
        self,
        old_widget: Optional[QWidget],
        new_widget: Optional[QWidget]
    ) -> List[DiffPatch]:
        """Generate diff between two widget trees."""
        old_tree = self.create_virtual_tree(old_widget) if old_widget else None
        new_tree = self.create_virtual_tree(new_widget) if new_widget else None
        
        return self.strategy.diff(old_tree, new_tree)
    
    def diff_properties(
        self,
        widget: QWidget,
        old_props: Dict[str, Any],
        new_props: Dict[str, Any]
    ) -> List[DiffPatch]:
        """Generate diff for property changes only."""
        patches = []
        
        all_props = set(old_props.keys()) | set(new_props.keys())
        
        for prop in all_props:
            old_value = old_props.get(prop)
            new_value = new_props.get(prop)
            
            if old_value != new_value:
                patches.append(DiffPatch(
                    operation=DiffOperation.UPDATE,
                    target=widget,
                    property_name=prop,
                    value=new_value,
                    old_value=old_value
                ))
        
        return patches
    
    def batch_patches(self, patches: List[DiffPatch]) -> None:
        """Add patches to pending batch."""
        self._pending_patches.extend(patches)
    
    def get_pending_patches(self) -> List[DiffPatch]:
        """Get and clear pending patches."""
        patches = self._pending_patches.copy()
        self._pending_patches.clear()
        return patches
    
    def _extract_properties(self, widget: QWidget) -> Dict[str, Any]:
        """Extract relevant properties from widget."""
        props = {}
        
        # Common properties
        props["enabled"] = widget.isEnabled()
        props["visible"] = widget.isVisible()
        props["geometry"] = widget.geometry()
        props["toolTip"] = widget.toolTip()
        props["styleSheet"] = widget.styleSheet()
        
        # Widget-specific properties
        if hasattr(widget, "text"):
            props["text"] = widget.text()
        if hasattr(widget, "value"):
            props["value"] = widget.value()
        if hasattr(widget, "checked"):
            props["checked"] = widget.checked()
        
        return props
    
    def invalidate_cache(self, widget: Optional[QWidget] = None) -> None:
        """Invalidate virtual tree cache."""
        if widget:
            self._virtual_tree_cache.pop(widget, None)
        else:
            self._virtual_tree_cache.clear()


# Global differ instance
_widget_differ: Optional[WidgetDiffer] = None


def get_widget_differ() -> WidgetDiffer:
    """Get the global widget differ."""
    global _widget_differ
    if _widget_differ is None:
        _widget_differ = WidgetDiffer()
    return _widget_differ