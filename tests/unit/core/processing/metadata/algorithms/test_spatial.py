"""Tests for spatial relationship algorithms."""

import pytest
from unittest.mock import Mock

from src.torematrix.core.processing.metadata.algorithms.spatial import (
    SpatialAnalyzer,
    BoundingBox,
    SpatialRelationType
)
from src.torematrix.core.processing.metadata.models.relationship import (
    Relationship,
    RelationshipType
)
from src.torematrix.core.models.element import Element as UnifiedElement
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates


@pytest.fixture
def spatial_config():
    """Create test spatial configuration."""
    config = Mock()
    config.spatial_threshold = 10.0
    config.alignment_threshold = 5.0
    return config


@pytest.fixture
def sample_elements():
    """Create sample elements with coordinates for spatial testing."""
    elements = []
    
    # Element 1: Top-left
    elem1_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[50, 50, 150, 100],
            system="pixel"
        ),
        confidence=0.9,
        page_number=1
    )
    elem1 = UnifiedElement(
        id="elem_1",
        type="Text",
        text="Top left element",
        metadata=elem1_metadata
    )
    elements.append(elem1)
    
    # Element 2: Adjacent to the right
    elem2_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[160, 50, 260, 100],
            system="pixel"
        ),
        confidence=0.9,
        page_number=1
    )
    elem2 = UnifiedElement(
        id="elem_2",
        type="Text",
        text="Adjacent right element",
        metadata=elem2_metadata
    )
    elements.append(elem2)
    
    # Element 3: Below element 1
    elem3_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[50, 110, 150, 160],
            system="pixel"
        ),
        confidence=0.9,
        page_number=1
    )
    elem3 = UnifiedElement(
        id="elem_3",
        type="Text",
        text="Below element",
        metadata=elem3_metadata
    )
    elements.append(elem3)
    
    # Element 4: Large container
    elem4_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[40, 40, 270, 170],
            system="pixel"
        ),
        confidence=0.8,
        page_number=1
    )
    elem4 = UnifiedElement(
        id="elem_4",
        type="Section",
        text="Container element",
        metadata=elem4_metadata
    )
    elements.append(elem4)
    
    # Element 5: Overlapping with element 1
    elem5_metadata = ElementMetadata(
        coordinates=Coordinates(
            layout_bbox=[100, 75, 200, 125],
            system="pixel"
        ),
        confidence=0.7,
        page_number=1
    )
    elem5 = UnifiedElement(
        id="elem_5",
        type="Text",
        text="Overlapping element",
        metadata=elem5_metadata
    )
    elements.append(elem5)
    
    return elements


class TestBoundingBox:
    """Test cases for BoundingBox class."""
    
    def test_bounding_box_properties(self):
        """Test bounding box property calculations."""
        bbox = BoundingBox(left=10, top=20, right=60, bottom=70)
        
        assert bbox.width == 50
        assert bbox.height == 50
        assert bbox.area == 2500
        assert bbox.center_x == 35
        assert bbox.center_y == 45
    
    def test_intersection_area(self):
        """Test intersection area calculation."""
        bbox1 = BoundingBox(left=10, top=10, right=50, bottom=50)
        bbox2 = BoundingBox(left=30, top=30, right=70, bottom=70)
        
        # Overlapping boxes
        intersection = bbox1.intersection_area(bbox2)
        assert intersection == 400  # 20 * 20
        
        # Non-overlapping boxes
        bbox3 = BoundingBox(left=100, top=100, right=150, bottom=150)
        intersection = bbox1.intersection_area(bbox3)
        assert intersection == 0
    
    def test_iou(self):
        """Test Intersection over Union calculation."""
        bbox1 = BoundingBox(left=10, top=10, right=50, bottom=50)
        bbox2 = BoundingBox(left=30, top=30, right=70, bottom=70)
        
        iou = bbox1.iou(bbox2)
        
        # Area1 = 1600, Area2 = 1600, Intersection = 400
        # Union = 1600 + 1600 - 400 = 2800
        # IoU = 400 / 2800 = 1/7 ≈ 0.143
        assert abs(iou - (400/2800)) < 0.001
    
    def test_distance_to(self):
        """Test distance calculation between boxes."""
        bbox1 = BoundingBox(left=10, top=10, right=30, bottom=30)
        bbox2 = BoundingBox(left=40, top=10, right=60, bottom=30)
        
        # Adjacent boxes (horizontal gap of 10)
        distance = bbox1.distance_to(bbox2)
        assert distance == 10
        
        # Overlapping boxes
        bbox3 = BoundingBox(left=20, top=20, right=50, bottom=50)
        distance = bbox1.distance_to(bbox3)
        assert distance == 0
        
        # Diagonal separation
        bbox4 = BoundingBox(left=50, top=50, right=70, bottom=70)
        distance = bbox1.distance_to(bbox4)
        expected = ((50-30)**2 + (50-30)**2)**0.5  # sqrt(400 + 400)
        assert abs(distance - expected) < 0.001


class TestSpatialAnalyzer:
    """Test cases for SpatialAnalyzer."""
    
    def test_init(self, spatial_config):
        """Test analyzer initialization."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        assert analyzer.config == spatial_config
        assert analyzer.spatial_threshold == 10.0
        assert analyzer.alignment_threshold == 5.0
    
    @pytest.mark.asyncio
    async def test_analyze_relationship_basic(self, spatial_config, sample_elements):
        """Test basic relationship analysis."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1, elem2 = sample_elements[:2]
        relationships = await analyzer.analyze_relationship(elem1, elem2)
        
        assert isinstance(relationships, list)
        assert len(relationships) > 0
        
        # Should find adjacent relationship
        adjacent_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_ADJACENT]
        assert len(adjacent_rels) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_containment(self, spatial_config, sample_elements):
        """Test containment relationship detection."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        container = sample_elements[3]  # Large container element
        contained = sample_elements[0]  # Element inside container
        
        relationships = await analyzer.analyze_relationship(container, contained)
        
        # Should find containment relationship
        containment_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_CONTAINS]
        assert len(containment_rels) > 0
        
        containment_rel = containment_rels[0]
        assert containment_rel.source_id == container.id
        assert containment_rel.target_id == contained.id
        assert containment_rel.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_adjacency_horizontal(self, spatial_config, sample_elements):
        """Test horizontal adjacency detection."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1, elem2 = sample_elements[:2]  # Horizontally adjacent
        relationships = await analyzer.analyze_relationship(elem1, elem2)
        
        # Should find horizontal adjacency
        adjacent_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_ADJACENT]
        assert len(adjacent_rels) > 0
        
        adjacent_rel = adjacent_rels[0]
        assert adjacent_rel.metadata["direction"] == "right"
        assert adjacent_rel.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_analyze_adjacency_vertical(self, spatial_config, sample_elements):
        """Test vertical adjacency detection."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1 = sample_elements[0]  # Top element
        elem3 = sample_elements[2]  # Bottom element
        
        relationships = await analyzer.analyze_relationship(elem1, elem3)
        
        # Should find vertical adjacency
        adjacent_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_ADJACENT]
        assert len(adjacent_rels) > 0
        
        adjacent_rel = adjacent_rels[0]
        assert adjacent_rel.metadata["direction"] == "bottom"
    
    @pytest.mark.asyncio
    async def test_analyze_alignment(self, spatial_config, sample_elements):
        """Test alignment detection."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1 = sample_elements[0]  # [50, 50, 150, 100]
        elem3 = sample_elements[2]  # [50, 110, 150, 160] - same left/right
        
        relationships = await analyzer.analyze_relationship(elem1, elem3)
        
        # Should find alignment relationships
        alignment_rels = [r for r in relationships 
                         if r.relationship_type == RelationshipType.SPATIAL_ADJACENT 
                         and "alignment" in r.metadata]
        assert len(alignment_rels) > 0
        
        # Should find left and right alignment
        alignments = [r.metadata["alignment"] for r in alignment_rels]
        assert "left" in alignments
        assert "right" in alignments
    
    @pytest.mark.asyncio
    async def test_analyze_overlap(self, spatial_config, sample_elements):
        """Test overlap detection."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1 = sample_elements[0]  # [50, 50, 150, 100]
        elem5 = sample_elements[4]  # [100, 75, 200, 125] - overlaps with elem1
        
        relationships = await analyzer.analyze_relationship(elem1, elem5)
        
        # Should find overlap relationship
        overlap_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_OVERLAPS]
        assert len(overlap_rels) > 0
        
        overlap_rel = overlap_rels[0]
        assert overlap_rel.confidence > 0.5
        assert "intersection_area" in overlap_rel.metadata
        assert "iou" in overlap_rel.metadata
    
    @pytest.mark.asyncio
    async def test_no_coordinates(self, spatial_config):
        """Test handling of elements without coordinates."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        elem1 = UnifiedElement(id="elem_1", type="Text", text="No coords", metadata=None)
        elem2 = UnifiedElement(id="elem_2", type="Text", text="Also no coords", metadata=ElementMetadata())
        
        relationships = await analyzer.analyze_relationship(elem1, elem2)
        
        assert isinstance(relationships, list)
        assert len(relationships) == 0  # No spatial relationships possible
    
    def test_get_bounding_box_valid(self, spatial_config):
        """Test extracting valid bounding box."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[10, 20, 30, 40])
        )
        element = UnifiedElement(id="elem_1", type="Text", text="Test", metadata=metadata)
        
        bbox = analyzer._get_bounding_box(element)
        
        assert bbox is not None
        assert bbox.left == 10
        assert bbox.top == 20
        assert bbox.right == 30
        assert bbox.bottom == 40
    
    def test_get_bounding_box_invalid(self, spatial_config):
        """Test extracting invalid bounding box."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # No metadata
        element1 = UnifiedElement(id="elem_1", type="Text", text="Test", metadata=None)
        bbox = analyzer._get_bounding_box(element1)
        assert bbox is None
        
        # No coordinates
        element2 = UnifiedElement(id="elem_2", type="Text", text="Test", metadata=ElementMetadata())
        bbox = analyzer._get_bounding_box(element2)
        assert bbox is None
        
        # Invalid bbox
        metadata = ElementMetadata(coordinates=Coordinates(layout_bbox=[10, 20]))  # Too few values
        element3 = UnifiedElement(id="elem_3", type="Text", text="Test", metadata=metadata)
        bbox = analyzer._get_bounding_box(element3)
        assert bbox is None
    
    def test_analyze_containment_coverage_ratio(self, spatial_config):
        """Test containment analysis with coverage ratio."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # Create container and contained elements
        container_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[0, 0, 100, 100])
        )
        container = UnifiedElement(id="container", type="Section", text="", metadata=container_metadata)
        
        contained_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[25, 25, 75, 75])  # 50x50 inside 100x100
        )
        contained = UnifiedElement(id="contained", type="Text", text="", metadata=contained_metadata)
        
        bbox1 = analyzer._get_bounding_box(container)
        bbox2 = analyzer._get_bounding_box(contained)
        
        result = analyzer._analyze_containment(container, contained, bbox1, bbox2)
        
        assert result is not None
        assert result.relationship_type == RelationshipType.SPATIAL_CONTAINS
        assert result.source_id == container.id
        assert result.target_id == contained.id
        
        # Coverage ratio should be 0.25 (2500/10000)
        assert abs(result.metadata["coverage_ratio"] - 0.25) < 0.01
    
    def test_analyze_adjacency_gap_calculation(self, spatial_config):
        """Test adjacency analysis with gap calculation."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # Create adjacent elements with specific gap
        elem1_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[0, 0, 50, 50])
        )
        elem1 = UnifiedElement(id="elem_1", type="Text", text="", metadata=elem1_metadata)
        
        elem2_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[55, 0, 105, 50])  # 5 pixel gap
        )
        elem2 = UnifiedElement(id="elem_2", type="Text", text="", metadata=elem2_metadata)
        
        bbox1 = analyzer._get_bounding_box(elem1)
        bbox2 = analyzer._get_bounding_box(elem2)
        
        relationships = analyzer._analyze_adjacency(elem1, elem2, bbox1, bbox2)
        
        assert len(relationships) > 0
        
        adjacent_rel = relationships[0]
        assert adjacent_rel.metadata["gap"] == 5
        assert adjacent_rel.metadata["direction"] == "right"
    
    def test_analyze_alignment_threshold(self, spatial_config):
        """Test alignment detection with threshold."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # Create elements with slight misalignment (within threshold)
        elem1_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[10, 10, 60, 60])
        )
        elem1 = UnifiedElement(id="elem_1", type="Text", text="", metadata=elem1_metadata)
        
        elem2_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[12, 70, 62, 120])  # 2 pixel offset (within 5 pixel threshold)
        )
        elem2 = UnifiedElement(id="elem_2", type="Text", text="", metadata=elem2_metadata)
        
        bbox1 = analyzer._get_bounding_box(elem1)
        bbox2 = analyzer._get_bounding_box(elem2)
        
        relationships = analyzer._analyze_alignment(elem1, elem2, bbox1, bbox2)
        
        # Should find left and right alignment (within threshold)
        alignment_rels = [r for r in relationships if "alignment" in r.metadata]
        assert len(alignment_rels) > 0
        
        alignments = [r.metadata["alignment"] for r in alignment_rels]
        assert "left" in alignments
        assert "right" in alignments
    
    def test_analyze_overlap_threshold(self, spatial_config):
        """Test overlap detection with significance threshold."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # Create elements with minimal overlap (should not trigger)
        elem1_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[0, 0, 100, 100])
        )
        elem1 = UnifiedElement(id="elem_1", type="Text", text="", metadata=elem1_metadata)
        
        elem2_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[95, 95, 105, 105])  # Very small overlap
        )
        elem2 = UnifiedElement(id="elem_2", type="Text", text="", metadata=elem2_metadata)
        
        bbox1 = analyzer._get_bounding_box(elem1)
        bbox2 = analyzer._get_bounding_box(elem2)
        
        result = analyzer._analyze_overlap(elem1, elem2, bbox1, bbox2)
        
        # Should not create overlap relationship for very small overlap
        assert result is None
    
    @pytest.mark.asyncio
    async def test_distant_elements(self, spatial_config):
        """Test handling of distant elements."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        # Create elements far apart (beyond spatial threshold)
        elem1_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[0, 0, 50, 50])
        )
        elem1 = UnifiedElement(id="elem_1", type="Text", text="", metadata=elem1_metadata)
        
        elem2_metadata = ElementMetadata(
            coordinates=Coordinates(layout_bbox=[100, 100, 150, 150])  # Far away
        )
        elem2 = UnifiedElement(id="elem_2", type="Text", text="", metadata=elem2_metadata)
        
        relationships = await analyzer.analyze_relationship(elem1, elem2)
        
        # Should find no or very few relationships due to distance
        adjacent_rels = [r for r in relationships if r.relationship_type == RelationshipType.SPATIAL_ADJACENT]
        assert len(adjacent_rels) == 0  # Too far for adjacency
    
    def test_spatial_relation_types(self):
        """Test spatial relation type enumeration."""
        # Verify all expected spatial relation types exist
        assert hasattr(SpatialRelationType, 'CONTAINS')
        assert hasattr(SpatialRelationType, 'OVERLAPS')
        assert hasattr(SpatialRelationType, 'ADJACENT_LEFT')
        assert hasattr(SpatialRelationType, 'ADJACENT_RIGHT')
        assert hasattr(SpatialRelationType, 'ADJACENT_TOP')
        assert hasattr(SpatialRelationType, 'ADJACENT_BOTTOM')
        assert hasattr(SpatialRelationType, 'ALIGNED_LEFT')
        assert hasattr(SpatialRelationType, 'ALIGNED_RIGHT')
        assert hasattr(SpatialRelationType, 'ALIGNED_CENTER_HORIZONTAL')
        assert hasattr(SpatialRelationType, 'ALIGNED_CENTER_VERTICAL')
    
    @pytest.mark.asyncio
    async def test_confidence_scores_range(self, spatial_config, sample_elements):
        """Test that confidence scores are within valid range."""
        analyzer = SpatialAnalyzer(spatial_config)
        
        for i in range(len(sample_elements)):
            for j in range(i+1, len(sample_elements)):
                relationships = await analyzer.analyze_relationship(sample_elements[i], sample_elements[j])
                
                for rel in relationships:
                    assert 0.0 <= rel.confidence <= 1.0
                    assert rel.confidence > 0.0  # Should have some confidence