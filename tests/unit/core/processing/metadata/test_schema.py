"""Comprehensive tests for metadata schema definitions."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.torematrix.core.processing.metadata import (
    MetadataSchema, DocumentMetadata, PageMetadata, ElementMetadata,
    RelationshipMetadata, BaseMetadata, MetadataType, LanguageCode,
    EncodingType, ExtractionMethod, MetadataValidationResult,
    ExtractionContext
)


class TestBaseMetadata:
    """Test suite for BaseMetadata class."""
    
    def test_base_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = BaseMetadata(
            metadata_type=MetadataType.DOCUMENT,
            confidence_score=0.9,
            source_extractor="TestExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        
        assert metadata.metadata_type == MetadataType.DOCUMENT
        assert metadata.confidence_score == 0.9
        assert metadata.source_extractor == "TestExtractor"
        assert metadata.extraction_method == ExtractionMethod.DIRECT_PARSING
        assert metadata.metadata_id is not None
        assert isinstance(metadata.extraction_timestamp, datetime)
    
    def test_confidence_level_auto_calculation(self):
        """Test automatic confidence level calculation."""
        # Very high confidence
        metadata = BaseMetadata(
            metadata_type=MetadataType.DOCUMENT,
            confidence_score=0.97,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        assert metadata.confidence_level.value == "very_high"
        
        # High confidence
        metadata.confidence_score = 0.88
        metadata = BaseMetadata(**metadata.dict())
        assert metadata.confidence_level.value == "high"
        
        # Medium confidence
        metadata.confidence_score = 0.75
        metadata = BaseMetadata(**metadata.dict())
        assert metadata.confidence_level.value == "medium"
        
        # Low confidence
        metadata.confidence_score = 0.6
        metadata = BaseMetadata(**metadata.dict())
        assert metadata.confidence_level.value == "low"
        
        # Very low confidence
        metadata.confidence_score = 0.3
        metadata = BaseMetadata(**metadata.dict())
        assert metadata.confidence_level.value == "very_low"
    
    def test_base_metadata_validation(self):
        """Test base metadata validation."""
        # Valid metadata
        metadata = BaseMetadata(
            metadata_type=MetadataType.DOCUMENT,
            confidence_score=0.9,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        assert metadata.confidence_score == 0.9
        
        # Invalid confidence score
        with pytest.raises(ValidationError):
            BaseMetadata(
                metadata_type=MetadataType.DOCUMENT,
                confidence_score=1.5,  # > 1.0
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
        
        with pytest.raises(ValidationError):
            BaseMetadata(
                metadata_type=MetadataType.DOCUMENT,
                confidence_score=-0.1,  # < 0.0
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )


class TestDocumentMetadata:
    """Test suite for DocumentMetadata class."""
    
    def test_document_metadata_creation(self):
        """Test document metadata creation."""
        metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="DocumentExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            title="Test Document",
            author="Test Author",
            page_count=5,
            total_elements=25
        )
        
        assert metadata.metadata_type == MetadataType.DOCUMENT
        assert metadata.title == "Test Document"
        assert metadata.author == "Test Author"
        assert metadata.page_count == 5
        assert metadata.total_elements == 25
    
    def test_document_metadata_language_encoding(self):
        """Test language and encoding properties."""
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            language=LanguageCode.ENGLISH,
            language_confidence=0.95,
            encoding=EncodingType.UTF8,
            encoding_confidence=0.99
        )
        
        assert metadata.language == LanguageCode.ENGLISH
        assert metadata.language_confidence == 0.95
        assert metadata.encoding == EncodingType.UTF8
        assert metadata.encoding_confidence == 0.99
    
    def test_document_metadata_dates(self):
        """Test document date handling."""
        creation_date = datetime(2023, 1, 1, 12, 0, 0)
        modification_date = datetime(2023, 6, 1, 15, 30, 0)
        
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            creation_date=creation_date,
            modification_date=modification_date
        )
        
        assert metadata.creation_date == creation_date
        assert metadata.modification_date == modification_date
    
    def test_document_metadata_validation(self):
        """Test document metadata validation."""
        # Valid page count
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_count=10
        )
        assert metadata.page_count == 10
        
        # Invalid page count
        with pytest.raises(ValidationError):
            DocumentMetadata(
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                page_count=-1
            )
    
    def test_document_metadata_consistency_validation(self):
        """Test document consistency validation."""
        # Inconsistent state: pages but no elements
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_count=5,
            total_elements=0
        )
        
        # Should auto-correct to have at least 1 element
        assert metadata.total_elements == 1
    
    def test_document_metadata_quality_scores(self):
        """Test quality score fields."""
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            text_quality_score=0.9,
            structure_quality_score=0.85,
            overall_quality_score=0.875
        )
        
        assert metadata.text_quality_score == 0.9
        assert metadata.structure_quality_score == 0.85
        assert metadata.overall_quality_score == 0.875
    
    def test_document_metadata_security_properties(self):
        """Test security-related properties."""
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            is_encrypted=True,
            has_digital_signature=True,
            permissions={"can_print": True, "can_modify": False}
        )
        
        assert metadata.is_encrypted is True
        assert metadata.has_digital_signature is True
        assert metadata.permissions["can_print"] is True
        assert metadata.permissions["can_modify"] is False


class TestPageMetadata:
    """Test suite for PageMetadata class."""
    
    def test_page_metadata_creation(self):
        """Test page metadata creation."""
        metadata = PageMetadata(
            confidence_score=0.85,
            source_extractor="PageExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123",
            width=612.0,
            height=792.0,
            element_count=10
        )
        
        assert metadata.metadata_type == MetadataType.PAGE
        assert metadata.page_number == 1
        assert metadata.document_id == "doc123"
        assert metadata.width == 612.0
        assert metadata.height == 792.0
        assert metadata.element_count == 10
    
    def test_page_metadata_validation(self):
        """Test page metadata validation."""
        # Valid page number
        metadata = PageMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123"
        )
        assert metadata.page_number == 1
        
        # Invalid page number
        with pytest.raises(ValidationError):
            PageMetadata(
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                page_number=0,  # Must be >= 1
                document_id="doc123"
            )
    
    def test_page_metadata_dimensions(self):
        """Test page dimension properties."""
        metadata = PageMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123",
            width=612.0,
            height=792.0,
            rotation=90.0
        )
        
        assert metadata.width == 612.0
        assert metadata.height == 792.0
        assert metadata.rotation == 90.0
    
    def test_page_metadata_content_metrics(self):
        """Test content metric properties."""
        metadata = PageMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123",
            element_count=15,
            text_element_count=10,
            image_element_count=3,
            table_element_count=2,
            word_count=500,
            character_count=2500
        )
        
        assert metadata.element_count == 15
        assert metadata.text_element_count == 10
        assert metadata.image_element_count == 3
        assert metadata.table_element_count == 2
        assert metadata.word_count == 500
        assert metadata.character_count == 2500
    
    def test_page_metadata_layout_properties(self):
        """Test layout-related properties."""
        metadata = PageMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123",
            column_count=2,
            has_header=True,
            has_footer=True,
            has_margin_notes=False
        )
        
        assert metadata.column_count == 2
        assert metadata.has_header is True
        assert metadata.has_footer is True
        assert metadata.has_margin_notes is False


class TestElementMetadata:
    """Test suite for ElementMetadata class."""
    
    def test_element_metadata_creation(self):
        """Test element metadata creation."""
        metadata = ElementMetadata(
            confidence_score=0.9,
            source_extractor="ElementExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            element_id="elem123",
            element_type="text",
            page_number=1,
            document_id="doc123",
            bbox=[100.0, 200.0, 300.0, 250.0],
            text_content="Sample text content"
        )
        
        assert metadata.metadata_type == MetadataType.ELEMENT
        assert metadata.element_id == "elem123"
        assert metadata.element_type == "text"
        assert metadata.page_number == 1
        assert metadata.document_id == "doc123"
        assert metadata.bbox == [100.0, 200.0, 300.0, 250.0]
        assert metadata.text_content == "Sample text content"
    
    def test_element_metadata_bbox_validation(self):
        """Test bounding box validation."""
        # Valid bbox
        metadata = ElementMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            element_id="elem123",
            element_type="text",
            page_number=1,
            document_id="doc123",
            bbox=[10.0, 20.0, 30.0, 40.0]
        )
        assert metadata.bbox == [10.0, 20.0, 30.0, 40.0]
        
        # Invalid bbox (wrong number of coordinates)
        with pytest.raises(ValidationError):
            ElementMetadata(
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                element_id="elem123",
                element_type="text",
                page_number=1,
                document_id="doc123",
                bbox=[10.0, 20.0, 30.0]  # Only 3 coordinates
            )
    
    def test_element_metadata_semantic_properties(self):
        """Test semantic property fields."""
        metadata = ElementMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            element_id="elem123",
            element_type="text",
            page_number=1,
            document_id="doc123",
            semantic_role="heading",
            heading_level=2,
            reading_order=5
        )
        
        assert metadata.semantic_role == "heading"
        assert metadata.heading_level == 2
        assert metadata.reading_order == 5
    
    def test_element_metadata_formatting(self):
        """Test formatting properties."""
        metadata = ElementMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            element_id="elem123",
            element_type="text",
            page_number=1,
            document_id="doc123",
            font_name="Arial",
            font_size=12.0,
            is_bold=True,
            is_italic=False,
            text_color="#000000"
        )
        
        assert metadata.font_name == "Arial"
        assert metadata.font_size == 12.0
        assert metadata.is_bold is True
        assert metadata.is_italic is False
        assert metadata.text_color == "#000000"


class TestRelationshipMetadata:
    """Test suite for RelationshipMetadata class."""
    
    def test_relationship_metadata_creation(self):
        """Test relationship metadata creation."""
        metadata = RelationshipMetadata(
            confidence_score=0.8,
            source_extractor="RelationshipExtractor",
            extraction_method=ExtractionMethod.ML_INFERENCE,
            source_element_id="elem1",
            target_element_id="elem2",
            relationship_type="follows",
            relationship_strength=0.9
        )
        
        assert metadata.metadata_type == MetadataType.RELATIONSHIP
        assert metadata.source_element_id == "elem1"
        assert metadata.target_element_id == "elem2"
        assert metadata.relationship_type == "follows"
        assert metadata.relationship_strength == 0.9
    
    def test_relationship_metadata_spatial(self):
        """Test spatial relationship properties."""
        metadata = RelationshipMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.HEURISTIC_ANALYSIS,
            source_element_id="elem1",
            target_element_id="elem2",
            relationship_type="spatial",
            spatial_relationship="below",
            distance=50.0
        )
        
        assert metadata.spatial_relationship == "below"
        assert metadata.distance == 50.0
    
    def test_relationship_metadata_semantic(self):
        """Test semantic relationship properties."""
        metadata = RelationshipMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.ML_INFERENCE,
            source_element_id="elem1",
            target_element_id="elem2",
            relationship_type="semantic",
            semantic_relationship="elaborates",
            context_similarity=0.85
        )
        
        assert metadata.semantic_relationship == "elaborates"
        assert metadata.context_similarity == 0.85
    
    def test_relationship_metadata_directional(self):
        """Test directional properties."""
        metadata = RelationshipMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.RULE_BASED,
            source_element_id="elem1",
            target_element_id="elem2",
            relationship_type="reading_order",
            is_bidirectional=False,
            reading_flow_direction="left_to_right"
        )
        
        assert metadata.is_bidirectional is False
        assert metadata.reading_flow_direction == "left_to_right"


class TestMetadataSchema:
    """Test suite for MetadataSchema class."""
    
    def test_metadata_schema_creation(self):
        """Test metadata schema creation."""
        context = ExtractionContext(document_id="doc123")
        schema = MetadataSchema(
            extraction_context=context,
            total_confidence_score=0.85
        )
        
        assert schema.schema_version == "1.0.0"
        assert schema.extraction_context == context
        assert schema.total_confidence_score == 0.85
        assert schema.document_metadata is None
        assert len(schema.page_metadata) == 0
        assert len(schema.element_metadata) == 0
        assert len(schema.relationship_metadata) == 0
    
    def test_metadata_schema_with_content(self):
        """Test schema with actual metadata content."""
        doc_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="DocumentExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            title="Test Document",
            page_count=2
        )
        
        page_metadata = PageMetadata(
            confidence_score=0.85,
            source_extractor="PageExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123"
        )
        
        schema = MetadataSchema(
            document_metadata=doc_metadata,
            page_metadata=[page_metadata]
        )
        
        assert schema.document_metadata == doc_metadata
        assert len(schema.page_metadata) == 1
        assert schema.page_metadata[0] == page_metadata
    
    def test_metadata_schema_consistency_validation(self):
        """Test schema consistency validation."""
        doc_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_count=3,
            total_elements=10
        )
        
        # Create 2 pages (inconsistent with doc page_count of 3)
        page_metadata = [
            PageMetadata(
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                page_number=1,
                document_id="doc123"
            ),
            PageMetadata(
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                page_number=2,
                document_id="doc123"
            )
        ]
        
        # Create 5 elements (inconsistent with doc total_elements of 10)
        element_metadata = [
            ElementMetadata(
                confidence_score=0.7,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING,
                element_id=f"elem{i}",
                element_type="text",
                page_number=1,
                document_id="doc123"
            ) for i in range(5)
        ]
        
        schema = MetadataSchema(
            document_metadata=doc_metadata,
            page_metadata=page_metadata,
            element_metadata=element_metadata
        )
        
        # Should auto-correct inconsistencies
        assert schema.document_metadata.page_count == 2  # Corrected to match actual pages
        assert schema.document_metadata.total_elements == 5  # Corrected to match actual elements
    
    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation."""
        doc_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        
        page_metadata = PageMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_number=1,
            document_id="doc123"
        )
        
        element_metadata = ElementMetadata(
            confidence_score=0.7,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            element_id="elem1",
            element_type="text",
            page_number=1,
            document_id="doc123"
        )
        
        schema = MetadataSchema(
            document_metadata=doc_metadata,
            page_metadata=[page_metadata],
            element_metadata=[element_metadata]
        )
        
        overall_confidence = schema.calculate_overall_confidence()
        expected = (0.9 + 0.8 + 0.7) / 3  # Average of all confidence scores
        assert abs(overall_confidence - expected) < 0.001
    
    def test_calculate_overall_confidence_empty(self):
        """Test overall confidence calculation with empty schema."""
        schema = MetadataSchema()
        confidence = schema.calculate_overall_confidence()
        assert confidence == 0.0
    
    def test_get_metadata_summary(self):
        """Test metadata summary generation."""
        doc_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        
        schema = MetadataSchema(
            document_metadata=doc_metadata,
            total_confidence_score=0.85,
            completeness_score=0.9,
            consistency_score=0.8
        )
        
        summary = schema.get_metadata_summary()
        
        assert summary["schema_version"] == "1.0.0"
        assert summary["has_document_metadata"] is True
        assert summary["page_count"] == 0
        assert summary["element_count"] == 0
        assert summary["relationship_count"] == 0
        assert summary["overall_confidence"] == 0.9  # From doc_metadata
        assert summary["completeness_score"] == 0.9
        assert summary["consistency_score"] == 0.8
    
    def test_metadata_schema_serialization(self):
        """Test schema serialization/deserialization."""
        doc_metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            title="Test Document"
        )
        
        schema = MetadataSchema(document_metadata=doc_metadata)
        
        # Serialize to dict
        schema_dict = schema.dict()
        assert "document_metadata" in schema_dict
        assert schema_dict["document_metadata"]["title"] == "Test Document"
        
        # Deserialize from dict
        new_schema = MetadataSchema(**schema_dict)
        assert new_schema.document_metadata.title == "Test Document"
        assert new_schema.document_metadata.confidence_score == 0.9