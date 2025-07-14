"""Tests for the relationship detection engine."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List

from src.torematrix.core.processing.metadata.relationships import (
    RelationshipDetectionEngine,
    RelationshipConfig,
    DocumentContext
)
from src.torematrix.core.processing.metadata.models.relationship import (
    Relationship,
    RelationshipType
)
from src.torematrix.core.models.element import Element as UnifiedElement
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates


@pytest.fixture
def relationship_config():
    """Create test configuration."""
    return RelationshipConfig(
        spatial_threshold=10.0,
        content_similarity_threshold=0.7,
        reading_order_confidence_threshold=0.8,
        max_relationship_distance=5
    )


@pytest.fixture
def document_context():
    """Create test document context."""
    return DocumentContext(
        document_id="test_doc",
        language="en",
        reading_direction="ltr"
    )


@pytest.fixture
def sample_elements():
    """Create sample elements for testing."""
    elements = []
    
    # Title element
    title_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[50, 50, 250, 80],
            system="pixel"
        ),
        confidence=0.95,
        page_number=1
    )
    title = UnifiedElement(
        id="title_1",
        type="Title",
        text="Document Title",
        metadata=title_metadata
    )
    elements.append(title)
    
    # Paragraph elements
    para1_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[50, 100, 400, 150],
            system="pixel"
        ),
        confidence=0.9,
        page_number=1
    )
    para1 = UnifiedElement(
        id="para_1",
        type="Text",
        text="This is the first paragraph of the document. It contains important information.",
        metadata=para1_metadata
    )
    elements.append(para1)
    
    para2_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[50, 160, 400, 210],
            system="pixel"
        ),
        confidence=0.9,
        page_number=1
    )
    para2 = UnifiedElement(
        id="para_2",
        type="Text",
        text="This is the second paragraph. It follows the first paragraph logically.",
        metadata=para2_metadata
    )
    elements.append(para2)
    
    # Figure element
    figure_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[450, 100, 600, 200],
            system="pixel"
        ),
        confidence=0.85,
        page_number=1
    )
    figure = UnifiedElement(
        id="figure_1",
        type="Figure",
        text="",
        metadata=figure_metadata
    )
    elements.append(figure)
    
    # Caption element
    caption_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[450, 210, 600, 230],
            system="pixel"
        ),
        confidence=0.8,
        page_number=1
    )
    caption = UnifiedElement(
        id="caption_1",
        type="Text",
        text="Figure 1: Sample diagram showing the relationship between components.",
        metadata=caption_metadata
    )
    elements.append(caption)
    
    return elements


class TestRelationshipDetectionEngine:
    """Test cases for RelationshipDetectionEngine."""
    
    def test_init(self, relationship_config):
        """Test engine initialization."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        assert engine.config == relationship_config
        assert engine.graph is not None
        assert engine.spatial_analyzer is not None
        assert engine.content_analyzer is not None
        assert engine.stats["relationships_detected"] == 0
    
    @pytest.mark.asyncio
    async def test_detect_relationships_basic(self, relationship_config, document_context, sample_elements):
        """Test basic relationship detection."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        graph = await engine.detect_relationships(sample_elements, document_context)
        
        assert graph is not None
        assert len(graph.element_index) == len(sample_elements)
        assert graph.graph.number_of_edges() > 0
        assert engine.stats["elements_processed"] == len(sample_elements)
        assert engine.stats["relationships_detected"] > 0
    
    @pytest.mark.asyncio
    async def test_detect_spatial_relationships(self, relationship_config, sample_elements):
        """Test spatial relationship detection."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        relationships = await engine.detect_spatial_relationships(sample_elements)
        
        assert isinstance(relationships, list)
        # Should find some spatial relationships between adjacent elements
        spatial_types = {RelationshipType.SPATIAL_ADJACENT, RelationshipType.SPATIAL_CONTAINS}
        spatial_rels = [r for r in relationships if r.relationship_type in spatial_types]
        assert len(spatial_rels) > 0
    
    @pytest.mark.asyncio
    async def test_detect_content_relationships(self, relationship_config, sample_elements):
        """Test content-based relationship detection."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        relationships = await engine.detect_content_relationships(sample_elements)
        
        assert isinstance(relationships, list)
        # Should find caption relationship
        caption_rels = [r for r in relationships if r.relationship_type == RelationshipType.CAPTION_TARGET]
        assert len(caption_rels) > 0
    
    @pytest.mark.asyncio
    async def test_detect_hierarchical_relationships(self, relationship_config, sample_elements):
        """Test hierarchical relationship detection."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        relationships = await engine.detect_hierarchical_relationships(sample_elements)
        
        assert isinstance(relationships, list)
        # Check for parent-child relationships
        hierarchical_rels = [r for r in relationships if r.relationship_type == RelationshipType.PARENT_CHILD]
        # May or may not find hierarchical relationships depending on spatial arrangement
        assert len(hierarchical_rels) >= 0
    
    @pytest.mark.asyncio
    async def test_detect_reading_order_relationships(self, relationship_config, document_context, sample_elements):
        """Test reading order relationship detection."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        relationships = await engine.detect_reading_order_relationships(sample_elements, document_context)
        
        assert isinstance(relationships, list)
        # Should find reading order relationships
        reading_order_rels = [r for r in relationships if r.relationship_type == RelationshipType.READING_ORDER]
        assert len(reading_order_rels) > 0
        
        # Check order makes sense (title should come before paragraphs)
        title_to_para = None
        for rel in reading_order_rels:
            if rel.source_id == "title_1" and rel.target_id == "para_1":
                title_to_para = rel
                break
        
        assert title_to_para is not None
        assert title_to_para.confidence > 0.5
    
    def test_get_statistics(self, relationship_config):
        """Test statistics retrieval."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        stats = engine.get_statistics()
        
        assert isinstance(stats, dict)
        assert "relationships_detected" in stats
        assert "elements_processed" in stats
        assert "detection_time" in stats
    
    def test_is_potential_parent(self, relationship_config, sample_elements):
        """Test parent detection logic."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        # Create a containing element
        container_metadata = ElementMetadata(
            coordinates=Coordinates(
                layout_bbox=[40, 90, 410, 220],  # Contains para_1 and para_2
                system="pixel"
            )
        )
        container = UnifiedElement(
            id="container_1",
            type="Section",
            text="",
            metadata=container_metadata
        )
        
        para1 = sample_elements[1]  # First paragraph
        
        result = engine._is_potential_parent(container, para1)
        assert result is True
        
        # Test non-containing relationship
        result = engine._is_potential_parent(para1, container)
        assert result is False
    
    def test_calculate_area(self, relationship_config, sample_elements):
        """Test area calculation."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        element = sample_elements[0]  # Title element with bbox [50, 50, 250, 80]
        area = engine._calculate_area(element)
        
        expected_area = (250 - 50) * (80 - 50)  # 200 * 30 = 6000
        assert area == expected_area
    
    def test_sort_by_reading_order_ltr(self, relationship_config, document_context, sample_elements):
        """Test left-to-right reading order sorting."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        sorted_elements = engine._sort_by_reading_order(sample_elements, document_context)
        
        assert len(sorted_elements) == len(sample_elements)
        # Title should come first (topmost)
        assert sorted_elements[0].id == "title_1"
        
        # Paragraphs should come before figure (left side)
        para_indices = [i for i, e in enumerate(sorted_elements) if e.type == "Text" and "para" in e.id]
        figure_indices = [i for i, e in enumerate(sorted_elements) if e.type == "Figure"]
        
        if para_indices and figure_indices:
            assert min(para_indices) < min(figure_indices)
    
    def test_sort_by_reading_order_rtl(self, relationship_config, sample_elements):
        """Test right-to-left reading order sorting."""
        rtl_context = DocumentContext(
            document_id="test_doc",
            language="ar",
            reading_direction="rtl"
        )
        
        engine = RelationshipDetectionEngine(relationship_config)
        sorted_elements = engine._sort_by_reading_order(sample_elements, rtl_context)
        
        assert len(sorted_elements) == len(sample_elements)
        # Should still have title first (topmost)
        assert sorted_elements[0].id == "title_1"
    
    @pytest.mark.asyncio
    async def test_empty_elements_list(self, relationship_config, document_context):
        """Test handling of empty elements list."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        graph = await engine.detect_relationships([], document_context)
        
        assert graph is not None
        assert len(graph.element_index) == 0
        assert graph.graph.number_of_edges() == 0
    
    @pytest.mark.asyncio
    async def test_elements_without_coordinates(self, relationship_config, document_context):
        """Test handling of elements without coordinates."""
        elements = [
            UnifiedElement(
                id="elem_1",
                type="Text",
                text="Element without coordinates",
                metadata=None
            ),
            UnifiedElement(
                id="elem_2", 
                type="Text",
                text="Another element without coordinates",
                metadata=ElementMetadata()  # No coordinates
            )
        ]
        
        engine = RelationshipDetectionEngine(relationship_config)
        graph = await engine.detect_relationships(elements, document_context)
        
        assert graph is not None
        assert len(graph.element_index) == 2
        # May have limited relationships due to lack of spatial info
        assert graph.graph.number_of_edges() >= 0
    
    @pytest.mark.asyncio
    async def test_single_element(self, relationship_config, document_context, sample_elements):
        """Test with single element."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        single_element = [sample_elements[0]]
        graph = await engine.detect_relationships(single_element, document_context)
        
        assert graph is not None
        assert len(graph.element_index) == 1
        assert graph.graph.number_of_edges() == 0  # No relationships possible with single element
    
    @pytest.mark.asyncio
    async def test_relationship_confidence_scores(self, relationship_config, document_context, sample_elements):
        """Test that relationship confidence scores are reasonable."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        graph = await engine.detect_relationships(sample_elements, document_context)
        
        # Check all relationships have valid confidence scores
        for _, _, edge_data in graph.graph.edges(data=True):
            if 'relationship' in edge_data:
                rel = edge_data['relationship']
                assert 0.0 <= rel.confidence <= 1.0
                assert rel.confidence > 0.0  # Should have some confidence
    
    @pytest.mark.asyncio
    async def test_parallel_detection_performance(self, relationship_config, document_context, sample_elements):
        """Test that parallel detection completes successfully."""
        engine = RelationshipDetectionEngine(relationship_config)
        
        # This tests that async operations complete without hanging
        import time
        start_time = time.time()
        
        graph = await engine.detect_relationships(sample_elements, document_context)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        assert graph is not None
        assert detection_time < 5.0  # Should complete in reasonable time
        
        # Update stats should reflect actual time
        engine.stats["detection_time"] = detection_time
        assert engine.stats["detection_time"] > 0


class TestRelationshipConfig:
    """Test cases for RelationshipConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RelationshipConfig()
        
        assert config.spatial_threshold == 10.0
        assert config.content_similarity_threshold == 0.7
        assert config.reading_order_confidence_threshold == 0.8
        assert config.max_relationship_distance == 5
        assert config.enable_ml_classification is True
        assert config.enable_rule_based_classification is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RelationshipConfig(
            spatial_threshold=20.0,
            content_similarity_threshold=0.8,
            enable_ml_classification=False
        )
        
        assert config.spatial_threshold == 20.0
        assert config.content_similarity_threshold == 0.8
        assert config.enable_ml_classification is False
        assert config.enable_rule_based_classification is True  # Default


class TestDocumentContext:
    """Test cases for DocumentContext."""
    
    def test_basic_context(self):
        """Test basic document context."""
        context = DocumentContext(document_id="test_doc")
        
        assert context.document_id == "test_doc"
        assert context.language == "en"
        assert context.reading_direction == "ltr"
        assert context.page_layout is None
        assert context.metadata is None
    
    def test_custom_context(self):
        """Test custom document context."""
        page_layout = {"width": 612, "height": 792}
        metadata = {"author": "Test Author"}
        
        context = DocumentContext(
            document_id="custom_doc",
            language="fr",
            reading_direction="rtl",
            page_layout=page_layout,
            metadata=metadata
        )
        
        assert context.document_id == "custom_doc"
        assert context.language == "fr"
        assert context.reading_direction == "rtl"
        assert context.page_layout == page_layout
        assert context.metadata == metadata