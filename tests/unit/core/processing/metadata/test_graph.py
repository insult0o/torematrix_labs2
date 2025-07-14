"""Tests for the relationship graph structure."""

import pytest
import networkx as nx
from unittest.mock import Mock

from src.torematrix.core.processing.metadata.graph import ElementRelationshipGraph
from src.torematrix.core.processing.metadata.models.relationship import (
    Relationship,
    RelationshipType
)
from src.torematrix.core.models.element import Element as UnifiedElement
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates


@pytest.fixture
def sample_elements():
    """Create sample elements for testing."""
    elements = []
    
    # Element 1
    metadata1 = ElementMetadata(
        coordinates=Coordinates(layout_bbox=[0, 0, 100, 50]),
        confidence=0.9,
        page_number=1
    )
    elem1 = UnifiedElement(
        id="elem_1",
        type="Text",
        text="First element",
        metadata=metadata1
    )
    elements.append(elem1)
    
    # Element 2
    metadata2 = ElementMetadata(
        coordinates=Coordinates(layout_bbox=[0, 60, 100, 110]),
        confidence=0.85,
        page_number=1
    )
    elem2 = UnifiedElement(
        id="elem_2",
        type="Text", 
        text="Second element",
        metadata=metadata2
    )
    elements.append(elem2)
    
    # Element 3
    metadata3 = ElementMetadata(
        coordinates=Coordinates(layout_bbox=[120, 0, 220, 50]),
        confidence=0.8,
        page_number=1
    )
    elem3 = UnifiedElement(
        id="elem_3",
        type="Figure",
        text="",
        metadata=metadata3
    )
    elements.append(elem3)
    
    return elements


@pytest.fixture
def sample_relationships():
    """Create sample relationships for testing."""
    relationships = []
    
    # Reading order relationship
    rel1 = Relationship(
        source_id="elem_1",
        target_id="elem_2",
        relationship_type=RelationshipType.READING_ORDER,
        confidence=0.9,
        metadata={"order_index": 0}
    )
    relationships.append(rel1)
    
    # Spatial relationship
    rel2 = Relationship(
        source_id="elem_1",
        target_id="elem_3",
        relationship_type=RelationshipType.SPATIAL_ADJACENT,
        confidence=0.75,
        metadata={"direction": "right"}
    )
    relationships.append(rel2)
    
    # Content relationship
    rel3 = Relationship(
        source_id="elem_2",
        target_id="elem_3",
        relationship_type=RelationshipType.CONTENT_RELATED,
        confidence=0.6,
        metadata={"similarity_score": 0.65}
    )
    relationships.append(rel3)
    
    return relationships


class TestElementRelationshipGraph:
    """Test cases for ElementRelationshipGraph."""
    
    def test_init(self):
        """Test graph initialization."""
        graph = ElementRelationshipGraph()
        
        assert isinstance(graph.graph, nx.MultiDiGraph)
        assert len(graph.element_index) == 0
        assert len(graph.relationship_index) == 0
    
    def test_add_element(self, sample_elements):
        """Test adding elements to graph."""
        graph = ElementRelationshipGraph()
        element = sample_elements[0]
        
        graph.add_element(element)
        
        assert element.id in graph.element_index
        assert element.id in graph.relationship_index
        assert graph.element_index[element.id] == element
        assert len(graph.relationship_index[element.id]) == 0
        assert graph.graph.has_node(element.id)
    
    def test_add_duplicate_element(self, sample_elements):
        """Test adding duplicate element."""
        graph = ElementRelationshipGraph()
        element = sample_elements[0]
        
        graph.add_element(element)
        graph.add_element(element)  # Add again
        
        # Should not create duplicates
        assert len(graph.element_index) == 1
        assert element.id in graph.element_index
    
    def test_add_relationship(self, sample_elements, sample_relationships):
        """Test adding relationships to graph."""
        graph = ElementRelationshipGraph()
        
        # Add elements first
        for element in sample_elements[:2]:
            graph.add_element(element)
        
        relationship = sample_relationships[0]
        graph.add_relationship(
            relationship.source_id,
            relationship.target_id,
            relationship
        )
        
        assert graph.graph.has_edge(relationship.source_id, relationship.target_id)
        assert relationship in graph.relationship_index[relationship.source_id]
        assert relationship in graph.relationship_index[relationship.target_id]
    
    def test_add_relationship_missing_elements(self, sample_relationships):
        """Test adding relationship with missing elements."""
        graph = ElementRelationshipGraph()
        relationship = sample_relationships[0]
        
        with pytest.raises(ValueError, match="not in graph"):
            graph.add_relationship(
                relationship.source_id,
                relationship.target_id,
                relationship
            )
    
    def test_get_element(self, sample_elements):
        """Test retrieving elements."""
        graph = ElementRelationshipGraph()
        element = sample_elements[0]
        graph.add_element(element)
        
        retrieved = graph.get_element(element.id)
        assert retrieved == element
        
        # Test non-existent element
        retrieved = graph.get_element("non_existent")
        assert retrieved is None
    
    def test_get_relationships(self, sample_elements, sample_relationships):
        """Test retrieving relationships for an element."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements[:2]:
            graph.add_element(element)
        
        # Add relationship
        relationship = sample_relationships[0]
        graph.add_relationship(
            relationship.source_id,
            relationship.target_id,
            relationship
        )
        
        # Get relationships for source element
        rels = graph.get_relationships(relationship.source_id)
        assert len(rels) == 1
        assert relationship in rels
        
        # Get relationships for target element
        rels = graph.get_relationships(relationship.target_id)
        assert len(rels) == 1
        assert relationship in rels
    
    def test_get_relationships_by_type(self, sample_elements, sample_relationships):
        """Test retrieving relationships filtered by type."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add multiple relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Filter by reading order
        reading_rels = graph.get_relationships("elem_1", RelationshipType.READING_ORDER)
        assert len(reading_rels) == 1
        assert reading_rels[0].relationship_type == RelationshipType.READING_ORDER
        
        # Filter by spatial
        spatial_rels = graph.get_relationships("elem_1", RelationshipType.SPATIAL_ADJACENT)
        assert len(spatial_rels) == 1
        assert spatial_rels[0].relationship_type == RelationshipType.SPATIAL_ADJACENT
    
    def test_get_outgoing_relationships(self, sample_elements, sample_relationships):
        """Test retrieving outgoing relationships."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Get outgoing relationships from elem_1
        outgoing = graph.get_outgoing_relationships("elem_1")
        assert len(outgoing) == 2  # elem_1 -> elem_2 and elem_1 -> elem_3
        
        source_ids = [rel.source_id for rel in outgoing]
        assert all(sid == "elem_1" for sid in source_ids)
    
    def test_get_incoming_relationships(self, sample_elements, sample_relationships):
        """Test retrieving incoming relationships."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Get incoming relationships to elem_2
        incoming = graph.get_incoming_relationships("elem_2")
        assert len(incoming) == 1  # elem_1 -> elem_2
        assert incoming[0].target_id == "elem_2"
        
        # Get incoming relationships to elem_3
        incoming = graph.get_incoming_relationships("elem_3")
        assert len(incoming) == 2  # elem_1 -> elem_3 and elem_2 -> elem_3
    
    def test_get_neighbors(self, sample_elements, sample_relationships):
        """Test retrieving neighbor elements."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Get neighbors of elem_1
        neighbors = graph.get_neighbors("elem_1")
        assert len(neighbors) == 2
        assert "elem_2" in neighbors
        assert "elem_3" in neighbors
        
        # Get neighbors of elem_2
        neighbors = graph.get_neighbors("elem_2")
        assert len(neighbors) == 2
        assert "elem_1" in neighbors
        assert "elem_3" in neighbors
    
    def test_find_path(self, sample_elements, sample_relationships):
        """Test finding paths between elements."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Find path from elem_1 to elem_3
        path = graph.find_path("elem_1", "elem_3")
        assert path is not None
        assert path[0] == "elem_1"
        assert path[-1] == "elem_3"
        assert len(path) <= 3  # Should be direct or through elem_2
        
        # Test non-existent path
        path = graph.find_path("elem_1", "non_existent")
        assert path is None
    
    def test_get_connected_components(self, sample_elements, sample_relationships):
        """Test getting connected components."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships (creates one connected component)
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        components = graph.get_connected_components()
        assert len(components) == 1  # All elements are connected
        assert len(components[0]) == 3
        
        # Add isolated element
        isolated_elem = UnifiedElement(id="isolated", type="Text", text="Isolated")
        graph.add_element(isolated_elem)
        
        components = graph.get_connected_components()
        assert len(components) == 2  # Now we have isolated element
    
    def test_get_subgraph(self, sample_elements, sample_relationships):
        """Test creating subgraphs."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Create subgraph with first two elements
        subgraph = graph.get_subgraph(["elem_1", "elem_2"])
        
        assert len(subgraph.element_index) == 2
        assert "elem_1" in subgraph.element_index
        assert "elem_2" in subgraph.element_index
        assert "elem_3" not in subgraph.element_index
        
        # Should have only the relationship between elem_1 and elem_2
        assert subgraph.graph.number_of_edges() == 1
    
    def test_filter_by_relationship_type(self, sample_elements, sample_relationships):
        """Test filtering graph by relationship type."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Filter by reading order
        filtered = graph.filter_by_relationship_type(RelationshipType.READING_ORDER)
        
        assert len(filtered.element_index) == 3  # All elements preserved
        assert filtered.graph.number_of_edges() == 1  # Only reading order relationship
        
        # Check that the relationship is correct type
        for _, _, edge_data in filtered.graph.edges(data=True):
            rel = edge_data['relationship']
            assert rel.relationship_type == RelationshipType.READING_ORDER
    
    def test_get_statistics(self, sample_elements, sample_relationships):
        """Test graph statistics."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        stats = graph.get_statistics()
        
        assert stats["num_elements"] == 3
        assert stats["num_relationships"] == 3
        assert "relationship_types" in stats
        assert "average_confidence" in stats
        assert "connected_components" in stats
        assert "is_dag" in stats
        
        # Check relationship type distribution
        rel_types = stats["relationship_types"]
        assert RelationshipType.READING_ORDER.value in rel_types
        assert RelationshipType.SPATIAL_ADJACENT.value in rel_types
        assert RelationshipType.CONTENT_RELATED.value in rel_types
    
    def test_clear(self, sample_elements, sample_relationships):
        """Test clearing the graph."""
        graph = ElementRelationshipGraph()
        
        # Add elements and relationships
        for element in sample_elements:
            graph.add_element(element)
        
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Verify graph has content
        assert len(graph.element_index) > 0
        assert graph.graph.number_of_edges() > 0
        
        # Clear graph
        graph.clear()
        
        # Verify graph is empty
        assert len(graph.element_index) == 0
        assert len(graph.relationship_index) == 0
        assert graph.graph.number_of_nodes() == 0
        assert graph.graph.number_of_edges() == 0
    
    def test_to_dict(self, sample_elements, sample_relationships):
        """Test serializing graph to dictionary."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        for element in sample_elements:
            graph.add_element(element)
        
        # Add relationships
        for rel in sample_relationships:
            graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        graph_dict = graph.to_dict()
        
        assert "elements" in graph_dict
        assert "relationships" in graph_dict
        assert "statistics" in graph_dict
        
        assert len(graph_dict["elements"]) == 3
        assert len(graph_dict["relationships"]) == 3
        
        # Verify element serialization
        assert "elem_1" in graph_dict["elements"]
        assert graph_dict["elements"]["elem_1"]["type"] == "Text"
    
    def test_from_dict(self, sample_elements, sample_relationships):
        """Test deserializing graph from dictionary."""
        # Create original graph
        original_graph = ElementRelationshipGraph()
        
        for element in sample_elements:
            original_graph.add_element(element)
        
        for rel in sample_relationships:
            original_graph.add_relationship(rel.source_id, rel.target_id, rel)
        
        # Serialize to dict
        graph_dict = original_graph.to_dict()
        
        # Deserialize from dict
        restored_graph = ElementRelationshipGraph.from_dict(graph_dict)
        
        assert len(restored_graph.element_index) == len(original_graph.element_index)
        assert restored_graph.graph.number_of_edges() == original_graph.graph.number_of_edges()
        
        # Verify elements are restored
        for elem_id in original_graph.element_index:
            assert elem_id in restored_graph.element_index
    
    def test_len(self, sample_elements):
        """Test graph length operator."""
        graph = ElementRelationshipGraph()
        
        assert len(graph) == 0
        
        for element in sample_elements:
            graph.add_element(element)
        
        assert len(graph) == len(sample_elements)
    
    def test_contains(self, sample_elements):
        """Test graph containment operator."""
        graph = ElementRelationshipGraph()
        element = sample_elements[0]
        
        assert element.id not in graph
        
        graph.add_element(element)
        
        assert element.id in graph
        assert "non_existent" not in graph
    
    def test_iter(self, sample_elements):
        """Test graph iteration."""
        graph = ElementRelationshipGraph()
        
        for element in sample_elements:
            graph.add_element(element)
        
        iterated_elements = list(graph)
        
        assert len(iterated_elements) == len(sample_elements)
        for element in sample_elements:
            assert element in iterated_elements
    
    def test_self_relationship_handling(self, sample_elements):
        """Test handling of self-relationships."""
        graph = ElementRelationshipGraph()
        element = sample_elements[0]
        graph.add_element(element)
        
        # Create self-relationship
        self_rel = Relationship(
            source_id=element.id,
            target_id=element.id,
            relationship_type=RelationshipType.CONTENT_SIMILAR,
            confidence=0.8
        )
        
        graph.add_relationship(element.id, element.id, self_rel)
        
        # Should be added to relationship index only once
        assert len(graph.relationship_index[element.id]) == 1
        assert self_rel in graph.relationship_index[element.id]
    
    def test_multi_edge_support(self, sample_elements):
        """Test support for multiple relationships between same elements."""
        graph = ElementRelationshipGraph()
        
        # Add elements
        elem1, elem2 = sample_elements[:2]
        graph.add_element(elem1)
        graph.add_element(elem2)
        
        # Add multiple relationships between same elements
        rel1 = Relationship(
            source_id=elem1.id,
            target_id=elem2.id,
            relationship_type=RelationshipType.READING_ORDER,
            confidence=0.9
        )
        
        rel2 = Relationship(
            source_id=elem1.id,
            target_id=elem2.id,
            relationship_type=RelationshipType.SPATIAL_ADJACENT,
            confidence=0.8
        )
        
        graph.add_relationship(elem1.id, elem2.id, rel1)
        graph.add_relationship(elem1.id, elem2.id, rel2)
        
        # Both relationships should be preserved
        assert graph.graph.number_of_edges() == 2
        
        # Both should be in relationship index
        elem1_rels = graph.relationship_index[elem1.id]
        assert len(elem1_rels) == 2
        assert rel1 in elem1_rels
        assert rel2 in elem1_rels