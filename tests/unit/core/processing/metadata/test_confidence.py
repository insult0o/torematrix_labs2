"""Comprehensive tests for confidence scoring system."""

import pytest
import math
from datetime import datetime, timedelta

from src.torematrix.core.processing.metadata import (
    ConfidenceScorer, BaseMetadata, DocumentMetadata, 
    ExtractionContext, MetadataValidationResult,
    ExtractionMethod, MetadataType
)


class TestConfidenceScorer:
    """Test suite for ConfidenceScorer class."""
    
    @pytest.fixture
    def default_scorer(self):
        """Create scorer with default weights."""
        return ConfidenceScorer()
    
    @pytest.fixture
    def custom_scorer(self):
        """Create scorer with custom weights."""
        weights = {
            "extraction_method": 0.30,
            "data_quality": 0.25,
            "validation_result": 0.25,
            "source_reliability": 0.15,
            "consistency_check": 0.05
        }
        return ConfidenceScorer(weights)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        return DocumentMetadata(
            confidence_score=0.8,
            source_extractor="TestExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            title="Test Document",
            page_count=5,
            total_elements=25
        )
    
    @pytest.fixture
    def extraction_context(self):
        """Create sample extraction context."""
        return ExtractionContext(
            document_id="test_doc_123",
            extraction_timestamp=datetime.utcnow(),
            extractor_chain=["DocumentExtractor"],
            processing_hints={"high_quality_source": True}
        )
    
    def test_scorer_initialization_default(self):
        """Test scorer initialization with default weights."""
        scorer = ConfidenceScorer()
        
        expected_weights = {
            "extraction_method": 0.25,
            "data_quality": 0.30,
            "validation_result": 0.20,
            "source_reliability": 0.15,
            "consistency_check": 0.10
        }
        
        assert scorer.weights == expected_weights
    
    def test_scorer_initialization_custom(self):
        """Test scorer initialization with custom weights."""
        custom_weights = {
            "extraction_method": 0.4,
            "data_quality": 0.3,
            "validation_result": 0.2,
            "source_reliability": 0.1
        }
        
        scorer = ConfidenceScorer(custom_weights)
        assert scorer.weights == custom_weights
    
    def test_scorer_initialization_invalid_weights(self):
        """Test scorer initialization with invalid weights."""
        invalid_weights = {
            "extraction_method": 0.6,
            "data_quality": 0.5,  # Total > 1.0
        }
        
        with pytest.raises(ValueError, match="Confidence weights must sum to 1.0"):
            ConfidenceScorer(invalid_weights)
    
    def test_calculate_confidence_basic(self, default_scorer, sample_metadata, extraction_context):
        """Test basic confidence calculation."""
        confidence = default_scorer.calculate_confidence(
            sample_metadata, extraction_context
        )
        
        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)
    
    def test_calculate_confidence_with_validation(self, default_scorer, sample_metadata, extraction_context):
        """Test confidence calculation with validation results."""
        validation = MetadataValidationResult(
            is_valid=True,
            confidence_score=0.9,
            validation_errors=[],
            validation_warnings=[]
        )
        sample_metadata.validation_result = validation
        
        confidence = default_scorer.calculate_confidence(
            sample_metadata, extraction_context
        )
        
        # Should have high confidence with good validation
        assert confidence > 0.7
    
    def test_calculate_confidence_with_validation_errors(self, default_scorer, sample_metadata, extraction_context):
        """Test confidence calculation with validation errors."""
        validation = MetadataValidationResult(
            is_valid=False,
            confidence_score=0.3,
            validation_errors=["Missing required field", "Invalid format"],
            validation_warnings=[]
        )
        sample_metadata.validation_result = validation
        
        confidence = default_scorer.calculate_confidence(
            sample_metadata, extraction_context
        )
        
        # Should have lower confidence with validation errors
        assert confidence < 0.5
    
    def test_calculate_confidence_with_additional_factors(self, default_scorer, sample_metadata, extraction_context):
        """Test confidence calculation with additional factors."""
        additional_factors = {
            "custom_factor": 0.95
        }
        
        confidence = default_scorer.calculate_confidence(
            sample_metadata, extraction_context, additional_factors
        )
        
        assert 0.0 <= confidence <= 1.0
    
    def test_score_extraction_method(self, default_scorer):
        """Test extraction method scoring."""
        # High reliability method
        score = default_scorer._score_extraction_method(ExtractionMethod.DIRECT_PARSING)
        assert score == 0.95
        
        # Medium reliability method
        score = default_scorer._score_extraction_method(ExtractionMethod.HEURISTIC_ANALYSIS)
        assert score == 0.70
        
        # Lower reliability method
        score = default_scorer._score_extraction_method(ExtractionMethod.OCR_EXTRACTION)
        assert score == 0.60
    
    def test_score_data_quality_complete(self, default_scorer):
        """Test data quality scoring with complete metadata."""
        metadata = DocumentMetadata(
            confidence_score=0.9,
            source_extractor="TestExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            title="Complete Document",
            author="Test Author",
            page_count=10,
            total_elements=50,
            language="en",
            encoding="utf-8"
        )
        
        score = default_scorer._score_data_quality(metadata)
        assert score > 0.8  # Should be high for complete metadata
    
    def test_score_data_quality_incomplete(self, default_scorer):
        """Test data quality scoring with incomplete metadata."""
        metadata = DocumentMetadata(
            confidence_score=0.2,  # Low confidence
            source_extractor="TestExtractor",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            # Missing many fields
        )
        
        score = default_scorer._score_data_quality(metadata)
        assert score < 0.6  # Should be lower for incomplete metadata
    
    def test_score_validation_result_valid(self, default_scorer):
        """Test validation result scoring for valid metadata."""
        validation = MetadataValidationResult(
            is_valid=True,
            confidence_score=0.95,
            validation_errors=[],
            validation_warnings=[]
        )
        
        score = default_scorer._score_validation_result(validation)
        assert score >= 0.9
    
    def test_score_validation_result_invalid(self, default_scorer):
        """Test validation result scoring for invalid metadata."""
        validation = MetadataValidationResult(
            is_valid=False,
            confidence_score=0.3,
            validation_errors=["Critical error"],
            validation_warnings=[]
        )
        
        score = default_scorer._score_validation_result(validation)
        assert score <= 0.3
    
    def test_score_validation_result_with_warnings(self, default_scorer):
        """Test validation result scoring with warnings."""
        validation = MetadataValidationResult(
            is_valid=True,
            confidence_score=0.8,
            validation_errors=[],
            validation_warnings=["Minor issue", "Format warning"]
        )
        
        score = default_scorer._score_validation_result(validation)
        # Should be reduced due to warnings but still reasonable
        assert 0.6 <= score <= 0.8
    
    def test_score_validation_result_none(self, default_scorer):
        """Test validation result scoring when no validation available."""
        score = default_scorer._score_validation_result(None)
        assert score == 0.5  # Neutral score
    
    def test_score_source_reliability_known_extractor(self, default_scorer, extraction_context):
        """Test source reliability scoring for known extractors."""
        score = default_scorer._score_source_reliability(
            "DocumentMetadataExtractor", extraction_context
        )
        assert score == 0.90  # Known reliable extractor
    
    def test_score_source_reliability_unknown_extractor(self, default_scorer, extraction_context):
        """Test source reliability scoring for unknown extractors."""
        score = default_scorer._score_source_reliability(
            "UnknownExtractor", extraction_context
        )
        assert score == 0.75  # Default score for unknown extractors
    
    def test_score_source_reliability_with_hints(self, default_scorer):
        """Test source reliability with processing hints."""
        # High quality source
        context = ExtractionContext(
            processing_hints={"high_quality_source": True}
        )
        score = default_scorer._score_source_reliability("TestExtractor", context)
        assert score > 0.75
        
        # Low quality source
        context = ExtractionContext(
            processing_hints={"low_quality_source": True}
        )
        score = default_scorer._score_source_reliability("TestExtractor", context)
        assert score < 0.75
    
    def test_score_consistency_timestamp(self, default_scorer, sample_metadata):
        """Test consistency scoring based on timestamps."""
        # Consistent timestamps
        now = datetime.utcnow()
        context = ExtractionContext(extraction_timestamp=now)
        sample_metadata.extraction_timestamp = now
        
        score = default_scorer._score_consistency(sample_metadata, context)
        assert score >= 0.9
        
        # Inconsistent timestamps
        context = ExtractionContext(extraction_timestamp=now)
        sample_metadata.extraction_timestamp = now - timedelta(minutes=5)
        
        score = default_scorer._score_consistency(sample_metadata, context)
        assert score < 0.9
    
    def test_score_consistency_confidence_bounds(self, default_scorer, extraction_context):
        """Test consistency scoring based on confidence bounds."""
        # Reasonable confidence
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING
        )
        score = default_scorer._score_consistency(metadata, extraction_context)
        assert score >= 0.8
        
        # Extreme confidence (too high)
        metadata.confidence_score = 0.999
        score = default_scorer._score_consistency(metadata, extraction_context)
        assert score < 0.9
        
        # Extreme confidence (too low)
        metadata.confidence_score = 0.05
        score = default_scorer._score_consistency(metadata, extraction_context)
        assert score < 0.9
    
    def test_check_field_consistency_document(self, default_scorer):
        """Test field consistency checking for document metadata."""
        # Consistent metadata
        metadata = DocumentMetadata(
            confidence_score=0.8,
            source_extractor="test",
            extraction_method=ExtractionMethod.DIRECT_PARSING,
            page_count=5,
            total_elements=25
        )
        score = default_scorer._check_field_consistency(metadata)
        assert score >= 0.9
        
        # Inconsistent metadata (pages but no elements)
        metadata.total_elements = 0
        score = default_scorer._check_field_consistency(metadata)
        assert score < 0.8
    
    def test_calculate_aggregated_confidence_weighted_average(self, default_scorer, extraction_context):
        """Test aggregated confidence calculation with weighted average."""
        metadata_list = [
            DocumentMetadata(
                confidence_score=0.9,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.PAGE,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.ELEMENT,
                confidence_score=0.7,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
        ]
        
        overall, individual = default_scorer.calculate_aggregated_confidence(
            metadata_list, extraction_context, "weighted_average"
        )
        
        assert 0.0 <= overall <= 1.0
        assert len(individual) == 3
        # Document metadata should have higher weight
        assert overall > 0.7
    
    def test_calculate_aggregated_confidence_minimum(self, default_scorer, extraction_context):
        """Test aggregated confidence calculation with minimum method."""
        metadata_list = [
            BaseMetadata(
                metadata_type=MetadataType.DOCUMENT,
                confidence_score=0.9,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.PAGE,
                confidence_score=0.6,  # Lowest
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
        ]
        
        overall, individual = default_scorer.calculate_aggregated_confidence(
            metadata_list, extraction_context, "minimum"
        )
        
        assert overall == 0.6  # Should be the minimum
    
    def test_calculate_aggregated_confidence_harmonic_mean(self, default_scorer, extraction_context):
        """Test aggregated confidence calculation with harmonic mean."""
        metadata_list = [
            BaseMetadata(
                metadata_type=MetadataType.DOCUMENT,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.PAGE,
                confidence_score=0.9,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
        ]
        
        overall, individual = default_scorer.calculate_aggregated_confidence(
            metadata_list, extraction_context, "harmonic_mean"
        )
        
        # Harmonic mean should be less than arithmetic mean
        arithmetic_mean = (0.8 + 0.9) / 2
        assert overall < arithmetic_mean
    
    def test_calculate_aggregated_confidence_empty_list(self, default_scorer, extraction_context):
        """Test aggregated confidence calculation with empty list."""
        overall, individual = default_scorer.calculate_aggregated_confidence(
            [], extraction_context
        )
        
        assert overall == 0.0
        assert individual == {}
    
    def test_get_metadata_importance_weights(self, default_scorer):
        """Test metadata importance weight calculation."""
        metadata_list = [
            BaseMetadata(
                metadata_type=MetadataType.DOCUMENT,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.PAGE,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.ELEMENT,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            ),
            BaseMetadata(
                metadata_type=MetadataType.RELATIONSHIP,
                confidence_score=0.8,
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
        ]
        
        weights = default_scorer._get_metadata_importance_weights(metadata_list)
        
        assert len(weights) == 4
        assert weights[0] == 1.0  # Document highest
        assert weights[1] == 0.8  # Page
        assert weights[2] == 0.6  # Element
        assert weights[3] == 0.4  # Relationship lowest
    
    def test_get_confidence_breakdown(self, default_scorer, sample_metadata, extraction_context):
        """Test confidence breakdown generation."""
        breakdown = default_scorer.get_confidence_breakdown(
            sample_metadata, extraction_context
        )
        
        # Check all expected factors are present
        expected_factors = [
            "extraction_method", "data_quality", "validation_result",
            "source_reliability", "consistency_check"
        ]
        
        for factor in expected_factors:
            assert factor in breakdown
            assert f"{factor}_weighted" in breakdown
            assert 0.0 <= breakdown[factor] <= 1.0
        
        assert "overall_confidence" in breakdown
        assert 0.0 <= breakdown["overall_confidence"] <= 1.0
    
    def test_update_weights(self, default_scorer):
        """Test weight updates."""
        original_weights = default_scorer.weights.copy()
        
        new_weights = {"extraction_method": 0.5, "data_quality": 0.5}
        default_scorer.update_weights(new_weights)
        
        assert default_scorer.weights["extraction_method"] == 0.5
        assert default_scorer.weights["data_quality"] == 0.5
        # Other weights should remain unchanged
        assert default_scorer.weights["validation_result"] == original_weights["validation_result"]
    
    def test_update_weights_invalid(self, default_scorer):
        """Test invalid weight updates."""
        invalid_weights = {"extraction_method": 0.8, "data_quality": 0.5}  # Sum > 1.0
        
        with pytest.raises(ValueError):
            default_scorer.update_weights(invalid_weights)
    
    def test_confidence_bounds_enforcement(self, default_scorer, sample_metadata, extraction_context):
        """Test that confidence scores are always bounded between 0 and 1."""
        # Test with extreme inputs that might cause out-of-bounds results
        sample_metadata.confidence_score = 2.0  # Invalid but let's see if scorer handles it
        
        confidence = default_scorer.calculate_confidence(
            sample_metadata, extraction_context
        )
        
        assert 0.0 <= confidence <= 1.0
    
    def test_scorer_consistency_across_calls(self, default_scorer, sample_metadata, extraction_context):
        """Test that scorer produces consistent results across multiple calls."""
        confidence1 = default_scorer.calculate_confidence(sample_metadata, extraction_context)
        confidence2 = default_scorer.calculate_confidence(sample_metadata, extraction_context)
        
        assert abs(confidence1 - confidence2) < 1e-10  # Should be identical
    
    def test_scorer_performance_with_large_lists(self, default_scorer, extraction_context):
        """Test scorer performance with large metadata lists."""
        # Create large list of metadata
        metadata_list = []
        for i in range(100):
            metadata = BaseMetadata(
                metadata_type=MetadataType.ELEMENT,
                confidence_score=0.8 + (i % 20) * 0.01,  # Vary confidence slightly
                source_extractor="test",
                extraction_method=ExtractionMethod.DIRECT_PARSING
            )
            metadata_list.append(metadata)
        
        # Should complete in reasonable time
        overall, individual = default_scorer.calculate_aggregated_confidence(
            metadata_list, extraction_context
        )
        
        assert len(individual) == 100
        assert 0.0 <= overall <= 1.0