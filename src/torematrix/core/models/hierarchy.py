"""
Element hierarchy and relationships module.

This module provides functionality for managing parent-child relationships
between elements, tree traversal, and hierarchical operations.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .element import Element, ElementType


class RelationshipType(Enum):
    """Types of relationships between elements"""
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    CONTAINS = "contains"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    REFERENCES = "references"


@dataclass(frozen=True)
class ElementRelationship:
    """
    Represents a relationship between two elements.
    
    Provides typed relationships with additional metadata
    for complex document structures.
    """
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize relationship to dictionary"""
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relationship_type': self.relationship_type.value,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElementRelationship':
        """Deserialize relationship from dictionary"""
        return cls(
            source_id=data['source_id'],
            target_id=data['target_id'],
            relationship_type=RelationshipType(data['relationship_type']),
            metadata=data.get('metadata', {})
        )


class ElementHierarchy:
    """
    Manages hierarchical relationships between elements.
    
    Provides tree operations, validation, and navigation
    for document element hierarchies.
    """
    
    def __init__(self, elements: List[Element]):
        """
        Initialize hierarchy from list of elements.
        
        Args:
            elements: List of elements to build hierarchy from
        """
        self.elements = {elem.element_id: elem for elem in elements}
        self.relationships: List[ElementRelationship] = []
        self._parent_map: Dict[str, str] = {}
        self._children_map: Dict[str, List[str]] = {}
        
        self._build_hierarchy()
    
    def _build_hierarchy(self) -> None:
        """Build hierarchy maps from element parent_id relationships"""
        self._parent_map.clear()
        self._children_map.clear()
        
        # Initialize children map
        for element_id in self.elements:
            self._children_map[element_id] = []
        
        # Build parent-child relationships
        for element in self.elements.values():
            if element.parent_id:
                self._parent_map[element.element_id] = element.parent_id
                
                # Add to children map
                if element.parent_id in self._children_map:
                    self._children_map[element.parent_id].append(element.element_id)
                else:
                    self._children_map[element.parent_id] = [element.element_id]
                
                # Create relationship object
                relationship = ElementRelationship(
                    source_id=element.parent_id,
                    target_id=element.element_id,
                    relationship_type=RelationshipType.PARENT_CHILD
                )
                self.relationships.append(relationship)
    
    def get_parent(self, element_id: str) -> Optional[Element]:
        """Get parent element of given element"""
        parent_id = self._parent_map.get(element_id)
        if parent_id:
            return self.elements.get(parent_id)
        return None
    
    def get_children(self, element_id: str) -> List[Element]:
        """Get direct children of given element"""
        child_ids = self._children_map.get(element_id, [])
        return [self.elements[child_id] for child_id in child_ids if child_id in self.elements]
    
    def get_siblings(self, element_id: str) -> List[Element]:
        """Get sibling elements (same parent)"""
        parent_id = self._parent_map.get(element_id)
        if not parent_id:
            # Root elements are siblings to each other
            return [elem for elem in self.elements.values() 
                   if elem.element_id != element_id and not elem.parent_id]
        
        sibling_ids = [child_id for child_id in self._children_map.get(parent_id, [])
                      if child_id != element_id]
        return [self.elements[sibling_id] for sibling_id in sibling_ids if sibling_id in self.elements]
    
    def get_ancestors(self, element_id: str) -> List[Element]:
        """Get all ancestor elements (recursive parents)"""
        ancestors = []
        current_id = element_id
        
        while current_id in self._parent_map:
            parent_id = self._parent_map[current_id]
            if parent_id in self.elements:
                ancestors.append(self.elements[parent_id])
                current_id = parent_id
            else:
                break
        
        return ancestors
    
    def get_descendants(self, element_id: str) -> List[Element]:
        """Get all descendant elements (recursive children)"""
        descendants = []
        stack = [element_id]
        
        while stack:
            current_id = stack.pop()
            child_ids = self._children_map.get(current_id, [])
            
            for child_id in child_ids:
                if child_id in self.elements:
                    descendants.append(self.elements[child_id])
                    stack.append(child_id)
        
        return descendants
    
    def get_root_elements(self) -> List[Element]:
        """Get elements with no parent (root elements)"""
        return [elem for elem in self.elements.values() if not elem.parent_id]
    
    def get_leaf_elements(self) -> List[Element]:
        """Get elements with no children (leaf elements)"""
        return [elem for elem in self.elements.values() 
               if not self._children_map.get(elem.element_id)]
    
    def get_depth(self, element_id: str) -> int:
        """Get depth of element in hierarchy (0 = root)"""
        depth = 0
        current_id = element_id
        
        while current_id in self._parent_map:
            depth += 1
            current_id = self._parent_map[current_id]
            if depth > 100:  # Prevent infinite loops
                break
        
        return depth
    
    def get_subtree(self, element_id: str) -> List[Element]:
        """Get element and all its descendants"""
        if element_id not in self.elements:
            return []
        
        subtree = [self.elements[element_id]]
        subtree.extend(self.get_descendants(element_id))
        return subtree
    
    def is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if one element is ancestor of another"""
        current_id = descendant_id
        
        while current_id in self._parent_map:
            parent_id = self._parent_map[current_id]
            if parent_id == ancestor_id:
                return True
            current_id = parent_id
            if current_id == descendant_id:  # Circular reference
                break
        
        return False
    
    def validate_hierarchy(self) -> List[str]:
        """
        Validate hierarchy for consistency.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check for circular references
        for element_id in self.elements:
            visited = set()
            current_id = element_id
            
            while current_id in self._parent_map:
                if current_id in visited:
                    errors.append(f"Circular reference detected: {current_id}")
                    break
                visited.add(current_id)
                current_id = self._parent_map[current_id]
        
        # Check for orphaned parent references
        for element in self.elements.values():
            if element.parent_id and element.parent_id not in self.elements:
                errors.append(f"Element {element.element_id} references non-existent parent {element.parent_id}")
        
        return errors
    
    def add_relationship(self, relationship: ElementRelationship) -> None:
        """Add a custom relationship between elements"""
        self.relationships.append(relationship)
    
    def get_relationships(
        self, 
        element_id: str, 
        relationship_type: Optional[RelationshipType] = None
    ) -> List[ElementRelationship]:
        """Get relationships for an element"""
        relationships = []
        
        for rel in self.relationships:
            if rel.source_id == element_id or rel.target_id == element_id:
                if not relationship_type or rel.relationship_type == relationship_type:
                    relationships.append(rel)
        
        return relationships
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize hierarchy to dictionary"""
        return {
            'elements': [elem.to_dict() for elem in self.elements.values()],
            'relationships': [rel.to_dict() for rel in self.relationships]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElementHierarchy':
        """Deserialize hierarchy from dictionary"""
        elements = [Element.from_dict(elem_data) for elem_data in data['elements']]
        hierarchy = cls(elements)
        
        # Add custom relationships
        for rel_data in data.get('relationships', []):
            relationship = ElementRelationship.from_dict(rel_data)
            if relationship.relationship_type != RelationshipType.PARENT_CHILD:
                hierarchy.add_relationship(relationship)
        
        return hierarchy


class HierarchyOperations:
    """Utility operations for element hierarchies"""
    
    @staticmethod
    def flatten_hierarchy(hierarchy: ElementHierarchy) -> List[Element]:
        """Flatten hierarchy to depth-first ordered list"""
        result = []
        
        def traverse(element_id: str, visited: Set[str]) -> None:
            if element_id in visited or element_id not in hierarchy.elements:
                return
            
            visited.add(element_id)
            result.append(hierarchy.elements[element_id])
            
            # Add children
            for child in hierarchy.get_children(element_id):
                traverse(child.element_id, visited)
        
        # Start with root elements
        visited = set()
        for root in hierarchy.get_root_elements():
            traverse(root.element_id, visited)
        
        # Add any orphaned elements
        for element in hierarchy.elements.values():
            if element.element_id not in visited:
                result.append(element)
        
        return result
    
    @staticmethod
    def group_by_type(hierarchy: ElementHierarchy) -> Dict[ElementType, List[Element]]:
        """Group elements by type"""
        groups = {}
        
        for element in hierarchy.elements.values():
            if element.element_type not in groups:
                groups[element.element_type] = []
            groups[element.element_type].append(element)
        
        return groups
    
    @staticmethod
    def group_by_depth(hierarchy: ElementHierarchy) -> Dict[int, List[Element]]:
        """Group elements by depth in hierarchy"""
        groups = {}
        
        for element in hierarchy.elements.values():
            depth = hierarchy.get_depth(element.element_id)
            if depth not in groups:
                groups[depth] = []
            groups[depth].append(element)
        
        return groups
    
    @staticmethod
    def find_by_text(
        hierarchy: ElementHierarchy, 
        search_text: str, 
        case_sensitive: bool = False
    ) -> List[Element]:
        """Find elements containing specific text"""
        results = []
        
        for element in hierarchy.elements.values():
            text = element.text if case_sensitive else element.text.lower()
            search = search_text if case_sensitive else search_text.lower()
            
            if search in text:
                results.append(element)
        
        return results
    
    @staticmethod
    def merge_hierarchies(
        hierarchy1: ElementHierarchy, 
        hierarchy2: ElementHierarchy
    ) -> ElementHierarchy:
        """Merge two hierarchies into one"""
        all_elements = list(hierarchy1.elements.values()) + list(hierarchy2.elements.values())
        
        # Handle ID conflicts by updating duplicates
        seen_ids = set()
        unique_elements = []
        
        for element in all_elements:
            if element.element_id in seen_ids:
                # Generate new ID for duplicate
                import uuid
                new_element = element.copy_with(element_id=str(uuid.uuid4()))
                unique_elements.append(new_element)
            else:
                seen_ids.add(element.element_id)
                unique_elements.append(element)
        
        merged = ElementHierarchy(unique_elements)
        
        # Add custom relationships from both hierarchies
        for relationship in hierarchy1.relationships + hierarchy2.relationships:
            if relationship.relationship_type != RelationshipType.PARENT_CHILD:
                merged.add_relationship(relationship)
        
        return merged
    
    @staticmethod
    def extract_subtree_as_hierarchy(
        hierarchy: ElementHierarchy, 
        root_element_id: str
    ) -> ElementHierarchy:
        """Extract a subtree as a new hierarchy"""
        subtree_elements = hierarchy.get_subtree(root_element_id)
        return ElementHierarchy(subtree_elements)


class HierarchyBuilder:
    """Builder for constructing element hierarchies"""
    
    def __init__(self):
        self.elements: List[Element] = []
        self.relationships: List[ElementRelationship] = []
    
    def add_element(self, element: Element) -> 'HierarchyBuilder':
        """Add element to hierarchy"""
        self.elements.append(element)
        return self
    
    def add_child(self, parent_element: Element, child_element: Element) -> 'HierarchyBuilder':
        """Add child element with parent relationship"""
        # Update child's parent_id
        updated_child = child_element.copy_with(parent_id=parent_element.element_id)
        self.elements.append(updated_child)
        return self
    
    def add_relationship(self, relationship: ElementRelationship) -> 'HierarchyBuilder':
        """Add custom relationship"""
        self.relationships.append(relationship)
        return self
    
    def build(self) -> ElementHierarchy:
        """Build the final hierarchy"""
        hierarchy = ElementHierarchy(self.elements)
        
        # Add custom relationships
        for relationship in self.relationships:
            hierarchy.add_relationship(relationship)
        
        return hierarchy