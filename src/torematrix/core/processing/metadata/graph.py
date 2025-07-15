"""Graph structure for element relationships.

This module provides the ElementRelationshipGraph class for storing and
querying relationships between document elements using NetworkX.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Iterator, Tuple
import networkx as nx
from dataclasses import asdict

from ...models.element import Element as UnifiedElement
from .models.relationship import Relationship, RelationshipType

logger = logging.getLogger(__name__)


class ElementRelationshipGraph:
    """Graph structure for element relationships.
    
    Uses NetworkX MultiDiGraph to store elements as nodes and relationships
    as edges, providing efficient querying and traversal capabilities.
    """
    
    def __init__(self):
        """Initialize the relationship graph."""
        self.graph = nx.MultiDiGraph()
        self.element_index: Dict[str, UnifiedElement] = {}
        self.relationship_index: Dict[str, List[Relationship]] = {}
        
    def add_element(self, element: UnifiedElement):
        """Add element as graph node.
        
        Args:
            element: Element to add to graph
        """
        if element.id in self.element_index:
            logger.warning(f"Element {element.id} already exists in graph")
            return
            
        self.graph.add_node(element.id, element=element)
        self.element_index[element.id] = element
        self.relationship_index[element.id] = []
        
        logger.debug(f"Added element {element.id} to graph")
        
    def add_relationship(
        self, 
        source_id: str, 
        target_id: str,
        relationship: Relationship
    ):
        """Add relationship as graph edge.
        
        Args:
            source_id: Source element ID
            target_id: Target element ID
            relationship: Relationship object
        """
        if source_id not in self.element_index:
            logger.error(f"Source element {source_id} not found in graph")
            raise ValueError(f"Source element {source_id} not in graph")
            
        if target_id not in self.element_index:
            logger.error(f"Target element {target_id} not found in graph")
            raise ValueError(f"Target element {target_id} not in graph")
            
        # Add edge with relationship data
        self.graph.add_edge(
            source_id, 
            target_id,
            key=relationship.id,
            relationship=relationship
        )
        
        # Update relationship index
        self.relationship_index[source_id].append(relationship)
        if target_id != source_id:
            self.relationship_index[target_id].append(relationship)
            
        logger.debug(f"Added relationship {relationship.id} between {source_id} and {target_id}")
        
    def get_element(self, element_id: str) -> Optional[UnifiedElement]:
        """Get element by ID.
        
        Args:
            element_id: Element ID to retrieve
            
        Returns:
            Element if found, None otherwise
        """
        return self.element_index.get(element_id)
        
    def get_relationships(
        self, 
        element_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[Relationship]:
        """Get all relationships for an element.
        
        Args:
            element_id: Element ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of relationships involving the element
        """
        if element_id not in self.relationship_index:
            return []
            
        relationships = self.relationship_index[element_id]
        
        if relationship_type:
            relationships = [
                r for r in relationships 
                if r.relationship_type == relationship_type
            ]
            
        return relationships
        
    def get_outgoing_relationships(
        self, 
        element_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[Relationship]:
        """Get outgoing relationships from an element.
        
        Args:
            element_id: Source element ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of outgoing relationships
        """
        if element_id not in self.graph:
            return []
            
        relationships = []
        
        for _, target_id, edge_data in self.graph.out_edges(element_id, data=True):
            relationship = edge_data['relationship']
            if not relationship_type or relationship.relationship_type == relationship_type:
                relationships.append(relationship)
                
        return relationships
        
    def get_incoming_relationships(
        self, 
        element_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[Relationship]:
        """Get incoming relationships to an element.
        
        Args:
            element_id: Target element ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of incoming relationships
        """
        if element_id not in self.graph:
            return []
            
        relationships = []
        
        for source_id, _, edge_data in self.graph.in_edges(element_id, data=True):
            relationship = edge_data['relationship']
            if not relationship_type or relationship.relationship_type == relationship_type:
                relationships.append(relationship)
                
        return relationships
        
    def get_neighbors(
        self, 
        element_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[str]:
        """Get neighboring element IDs.
        
        Args:
            element_id: Element ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of neighbor element IDs
        """
        if element_id not in self.graph:
            return []
            
        neighbors = set()
        
        # Add outgoing neighbors
        for _, target_id, edge_data in self.graph.out_edges(element_id, data=True):
            relationship = edge_data['relationship']
            if not relationship_type or relationship.relationship_type == relationship_type:
                neighbors.add(target_id)
                
        # Add incoming neighbors
        for source_id, _, edge_data in self.graph.in_edges(element_id, data=True):
            relationship = edge_data['relationship']
            if not relationship_type or relationship.relationship_type == relationship_type:
                neighbors.add(source_id)
                
        return list(neighbors)
        
    def find_path(
        self, 
        source_id: str, 
        target_id: str,
        max_length: int = 5
    ) -> Optional[List[str]]:
        """Find path between elements.
        
        Args:
            source_id: Source element ID
            target_id: Target element ID
            max_length: Maximum path length
            
        Returns:
            Path as list of element IDs, or None if no path found
        """
        if source_id not in self.graph or target_id not in self.graph:
            return None
            
        try:
            path = nx.shortest_path(
                self.graph.to_undirected(), 
                source_id, 
                target_id
            )
            
            if len(path) <= max_length + 1:  # +1 because path includes endpoints
                return path
            else:
                return None
                
        except nx.NetworkXNoPath:
            return None
            
    def get_connected_components(self) -> List[Set[str]]:
        """Get connected component groups.
        
        Returns:
            List of sets, each containing element IDs in a connected component
        """
        undirected_graph = self.graph.to_undirected()
        components = nx.connected_components(undirected_graph)
        return [set(component) for component in components]
        
    def get_subgraph(
        self, 
        element_ids: List[str]
    ) -> 'ElementRelationshipGraph':
        """Get subgraph containing only specified elements.
        
        Args:
            element_ids: List of element IDs to include
            
        Returns:
            New graph containing only specified elements and their relationships
        """
        subgraph = ElementRelationshipGraph()
        
        # Add elements
        for element_id in element_ids:
            if element_id in self.element_index:
                subgraph.add_element(self.element_index[element_id])
                
        # Add relationships between included elements
        for source_id in element_ids:
            if source_id not in self.graph:
                continue
                
            for _, target_id, edge_data in self.graph.out_edges(source_id, data=True):
                if target_id in element_ids:
                    relationship = edge_data['relationship']
                    subgraph.add_relationship(source_id, target_id, relationship)
                    
        return subgraph
        
    def filter_by_relationship_type(
        self, 
        relationship_type: RelationshipType
    ) -> 'ElementRelationshipGraph':
        """Create new graph with only specified relationship type.
        
        Args:
            relationship_type: Type of relationships to include
            
        Returns:
            New graph with filtered relationships
        """
        filtered_graph = ElementRelationshipGraph()
        
        # Add all elements
        for element in self.element_index.values():
            filtered_graph.add_element(element)
            
        # Add only relationships of specified type
        for source_id, target_id, edge_data in self.graph.edges(data=True):
            relationship = edge_data['relationship']
            if relationship.relationship_type == relationship_type:
                filtered_graph.add_relationship(source_id, target_id, relationship)
                
        return filtered_graph
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics.
        
        Returns:
            Dictionary containing graph statistics
        """
        relationship_types = {}
        confidence_scores = []
        
        for _, _, edge_data in self.graph.edges(data=True):
            relationship = edge_data['relationship']
            rel_type = relationship.relationship_type.value
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            confidence_scores.append(relationship.confidence)
            
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "num_elements": len(self.element_index),
            "num_relationships": self.graph.number_of_edges(),
            "relationship_types": relationship_types,
            "average_confidence": avg_confidence,
            "connected_components": len(list(nx.connected_components(self.graph.to_undirected()))),
            "is_dag": nx.is_directed_acyclic_graph(self.graph)
        }
        
    def clear(self):
        """Clear all elements and relationships from graph."""
        self.graph.clear()
        self.element_index.clear()
        self.relationship_index.clear()
        logger.debug("Cleared relationship graph")
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary.
        
        Returns:
            Dictionary representation of the graph
        """
        elements = {
            element_id: element.to_dict() 
            for element_id, element in self.element_index.items()
        }
        
        relationships = []
        for _, _, edge_data in self.graph.edges(data=True):
            relationship = edge_data['relationship']
            relationships.append(asdict(relationship))
            
        return {
            "elements": elements,
            "relationships": relationships,
            "statistics": self.get_statistics()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElementRelationshipGraph':
        """Deserialize graph from dictionary.
        
        Args:
            data: Dictionary representation of graph
            
        Returns:
            Reconstructed graph
        """
        graph = cls()
        
        # Reconstruct elements
        for element_id, element_data in data.get("elements", {}).items():
            element = UnifiedElement.from_dict(element_data)
            graph.add_element(element)
            
        # Reconstruct relationships
        for rel_data in data.get("relationships", []):
            relationship = Relationship(**rel_data)
            graph.add_relationship(
                relationship.source_id,
                relationship.target_id,
                relationship
            )
            
        return graph
        
    def __len__(self) -> int:
        """Get number of elements in graph."""
        return len(self.element_index)
        
    def __contains__(self, element_id: str) -> bool:
        """Check if element exists in graph."""
        return element_id in self.element_index
        
    def __iter__(self) -> Iterator[UnifiedElement]:
        """Iterate over elements in graph."""
        return iter(self.element_index.values())