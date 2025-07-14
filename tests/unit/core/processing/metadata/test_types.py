"""Tests for metadata type definitions and enums."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.torematrix.core.processing.metadata import (
    MetadataType, LanguageCode, EncodingType, ExtractionMethod,
    ConfidenceLevel, ExtractionContext, MetadataValidationResult,
    ExtractorConfig, MetadataConfig
)


class TestEnumTypes:
    """Test suite for enum type definitions."""
    
    def test_metadata_type_enum(self):
        """Test MetadataType enum values."""
        assert MetadataType.DOCUMENT == "document"
        assert MetadataType.PAGE == "page"
        assert MetadataType.ELEMENT == "element"
        assert MetadataType.RELATIONSHIP == "relationship"
        
        # Test all values are present
        expected_values = {"document", "page", "element", "relationship"}
        actual_values = {item.value for item in MetadataType}
        assert actual_values == expected_values
    
    def test_language_code_enum(self):
        """Test LanguageCode enum values."""
        assert LanguageCode.ENGLISH == "en"
        assert LanguageCode.SPANISH == "es"
        assert LanguageCode.FRENCH == "fr"
        assert LanguageCode.GERMAN == "de"
        assert LanguageCode.UNKNOWN == "unknown"
        
        # Test comprehensive language support
        major_languages = {
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", 
            "zh", "ja", "ko", "ar", "unknown"
        }
        actual_values = {item.value for item in LanguageCode}
        assert actual_values == major_languages
    
    def test_encoding_type_enum(self):
        """Test EncodingType enum values."""
        assert EncodingType.UTF8 == "utf-8"
        assert EncodingType.UTF16 == "utf-16"
        assert EncodingType.ASCII == "ascii"
        assert EncodingType.LATIN1 == "latin-1"
        assert EncodingType.UNKNOWN == "unknown"
        
        # Test common encodings are present
        common_encodings = {
            "utf-8", "utf-16", "utf-32", "ascii", 
            "latin-1", "cp1252", "unknown"
        }
        actual_values = {item.value for item in EncodingType}
        assert actual_values == common_encodings
    
    def test_extraction_method_enum(self):
        """Test ExtractionMethod enum values."""
        assert ExtractionMethod.DIRECT_PARSING == "direct_parsing"
        assert ExtractionMethod.OCR_EXTRACTION == "ocr_extraction"
        assert ExtractionMethod.HEURISTIC_ANALYSIS == "heuristic_analysis"
        assert ExtractionMethod.ML_INFERENCE == "ml_inference"
        assert ExtractionMethod.RULE_BASED == "rule_based"
        assert ExtractionMethod.HYBRID == "hybrid"
        
        # Test all extraction methods
        expected_methods = {
            "direct_parsing", "ocr_extraction", "heuristic_analysis",
            "ml_inference", "rule_based", "hybrid"
        }
        actual_values = {item.value for item in ExtractionMethod}
        assert actual_values == expected_methods
    
    def test_confidence_level_enum(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.VERY_HIGH == "very_high"
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.VERY_LOW == "very_low"
        
        # Test all confidence levels
        expected_levels = {"very_high", "high", "medium", "low", "very_low"}
        actual_values = {item.value for item in ConfidenceLevel}
        assert actual_values == expected_levels


class TestExtractionContext:
    """Test suite for ExtractionContext class."""
    
    def test_extraction_context_creation(self):
        """Test basic extraction context creation."""
        context = ExtractionContext()
        
        assert context.document_id is not None
        assert isinstance(context.extraction_timestamp, datetime)
        assert context.extraction_version == "1.0.0"
        assert isinstance(context.extractor_chain, list)
        assert isinstance(context.processing_hints, dict)
        assert isinstance(context.user_preferences, dict)
    
    def test_extraction_context_with_custom_values(self):
        """Test extraction context with custom values."""
        timestamp = datetime.utcnow()
        context = ExtractionContext(
            document_id="custom_doc_123",
            extraction_timestamp=timestamp,
            extraction_version="2.0.0",
            extractor_chain=["DocumentExtractor", "PageExtractor"],
            processing_hints={"high_quality": True},
            user_preferences={"language": "en"}
        )
        
        assert context.document_id == "custom_doc_123"
        assert context.extraction_timestamp == timestamp
        assert context.extraction_version == "2.0.0"
        assert context.extractor_chain == ["DocumentExtractor", "PageExtractor"]
        assert context.processing_hints["high_quality"] is True
        assert context.user_preferences["language"] == "en"
    
    def test_extraction_context_defaults(self):
        """Test extraction context default values."""
        context = ExtractionContext()
        
        # Should have default UUID format
        assert len(context.document_id) == 36  # UUID format
        assert "-" in context.document_id
        
        # Should have empty defaults
        assert len(context.extractor_chain) == 0
        assert len(context.processing_hints) == 0
        assert len(context.user_preferences) == 0


class TestMetadataValidationResult:
    """Test suite for MetadataValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test basic validation result creation."""
        result = MetadataValidationResult(
            is_valid=True,
            confidence_score=0.85
        )
        
        assert result.is_valid is True
        assert result.confidence_score == 0.85
        assert isinstance(result.validation_errors, list)
        assert isinstance(result.validation_warnings, list)
        assert isinstance(result.validation_timestamp, datetime)
    
    def test_validation_result_with_errors_warnings(self):
        """Test validation result with errors and warnings."""
        result = MetadataValidationResult(
            is_valid=False,
            confidence_score=0.3,
            validation_errors=["Missing required field", "Invalid format"],
            validation_warnings=["Unusual value", "Low confidence"]
        )
        
        assert result.is_valid is False
        assert result.confidence_score == 0.3
        assert len(result.validation_errors) == 2
        assert len(result.validation_warnings) == 2
        assert "Missing required field" in result.validation_errors
        assert "Unusual value" in result.validation_warnings
    
    def test_validation_result_confidence_bounds(self):
        """Test validation result confidence score bounds."""
        # Valid confidence scores
        result = MetadataValidationResult(is_valid=True, confidence_score=0.0)
        assert result.confidence_score == 0.0
        
        result = MetadataValidationResult(is_valid=True, confidence_score=1.0)
        assert result.confidence_score == 1.0
        
        # Invalid confidence scores should raise validation error
        with pytest.raises(ValidationError):
            MetadataValidationResult(is_valid=True, confidence_score=-0.1)
        
        with pytest.raises(ValidationError):
            MetadataValidationResult(is_valid=True, confidence_score=1.1)


class TestExtractorConfig:
    """Test suite for ExtractorConfig class."""
    
    def test_extractor_config_defaults(self):
        """Test extractor config default values."""
        config = ExtractorConfig()
        
        assert config.enabled is True
        assert config.confidence_threshold == 0.5
        assert isinstance(config.extraction_methods, list)
        assert isinstance(config.custom_settings, dict)
        assert config.timeout_seconds == 30.0
        assert config.retry_attempts == 3
    
    def test_extractor_config_custom_values(self):
        """Test extractor config with custom values."""
        config = ExtractorConfig(
            enabled=False,
            confidence_threshold=0.8,
            extraction_methods=[ExtractionMethod.DIRECT_PARSING],
            custom_settings={"setting1": "value1"},
            timeout_seconds=60.0,
            retry_attempts=5
        )
        
        assert config.enabled is False
        assert config.confidence_threshold == 0.8
        assert config.extraction_methods == [ExtractionMethod.DIRECT_PARSING]
        assert config.custom_settings["setting1"] == "value1"
        assert config.timeout_seconds == 60.0
        assert config.retry_attempts == 5
    
    def test_extractor_config_confidence_validation(self):
        """Test confidence threshold validation."""
        # Valid confidence thresholds
        config = ExtractorConfig(confidence_threshold=0.0)
        assert config.confidence_threshold == 0.0
        
        config = ExtractorConfig(confidence_threshold=1.0)
        assert config.confidence_threshold == 1.0
        
        # Invalid confidence thresholds
        with pytest.raises(ValidationError):
            ExtractorConfig(confidence_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            ExtractorConfig(confidence_threshold=1.1)
    
    def test_extractor_config_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        config = ExtractorConfig(timeout_seconds=10.0)
        assert config.timeout_seconds == 10.0
        
        # None timeout (no limit)
        config = ExtractorConfig(timeout_seconds=None)
        assert config.timeout_seconds is None
        
        # Invalid timeout
        with pytest.raises(ValidationError):
            ExtractorConfig(timeout_seconds=-1.0)
        
        with pytest.raises(ValidationError):
            ExtractorConfig(timeout_seconds=0.0)
    
    def test_extractor_config_retry_validation(self):
        """Test retry attempts validation."""
        # Valid retry attempts
        config = ExtractorConfig(retry_attempts=0)
        assert config.retry_attempts == 0
        
        config = ExtractorConfig(retry_attempts=10)
        assert config.retry_attempts == 10
        
        # Invalid retry attempts
        with pytest.raises(ValidationError):
            ExtractorConfig(retry_attempts=-1)


class TestMetadataConfig:
    """Test suite for MetadataConfig class."""
    
    def test_metadata_config_defaults(self):
        """Test metadata config default values."""
        config = MetadataConfig()
        
        assert config.enable_parallel_extraction is True
        assert config.max_workers == 4
        assert config.cache_enabled is True
        assert config.cache_ttl_seconds == 3600
        assert config.default_language == LanguageCode.ENGLISH
        assert config.default_encoding == EncodingType.UTF8
        assert isinstance(config.confidence_weights, dict)
        assert isinstance(config.extractor_configs, dict)
    
    def test_metadata_config_custom_values(self):
        """Test metadata config with custom values."""
        confidence_weights = {
            "extraction_method": 0.3,
            "data_quality": 0.4,
            "validation_result": 0.3
        }
        
        extractor_configs = {
            "DocumentExtractor": ExtractorConfig(confidence_threshold=0.8)
        }
        
        config = MetadataConfig(
            enable_parallel_extraction=False,
            max_workers=8,
            cache_enabled=False,
            cache_ttl_seconds=7200,
            default_language=LanguageCode.SPANISH,
            default_encoding=EncodingType.LATIN1,
            confidence_weights=confidence_weights,
            extractor_configs=extractor_configs
        )
        
        assert config.enable_parallel_extraction is False
        assert config.max_workers == 8
        assert config.cache_enabled is False
        assert config.cache_ttl_seconds == 7200
        assert config.default_language == LanguageCode.SPANISH
        assert config.default_encoding == EncodingType.LATIN1
        assert config.confidence_weights == confidence_weights
        assert "DocumentExtractor" in config.extractor_configs
    
    def test_metadata_config_max_workers_validation(self):
        """Test max workers validation."""
        # Valid worker counts
        config = MetadataConfig(max_workers=1)
        assert config.max_workers == 1
        
        config = MetadataConfig(max_workers=16)
        assert config.max_workers == 16
        
        # Invalid worker counts
        with pytest.raises(ValidationError):
            MetadataConfig(max_workers=0)
        
        with pytest.raises(ValidationError):
            MetadataConfig(max_workers=-1)
    
    def test_metadata_config_cache_ttl_validation(self):
        """Test cache TTL validation."""
        # Valid TTL values
        config = MetadataConfig(cache_ttl_seconds=0)
        assert config.cache_ttl_seconds == 0
        
        config = MetadataConfig(cache_ttl_seconds=86400)
        assert config.cache_ttl_seconds == 86400
        
        # Invalid TTL values
        with pytest.raises(ValidationError):
            MetadataConfig(cache_ttl_seconds=-1)
    
    def test_metadata_config_confidence_weights_validation(self):
        """Test confidence weights validation."""
        # Valid weights (sum to 1.0)
        valid_weights = {
            "extraction_method": 0.4,
            "data_quality": 0.6
        }
        config = MetadataConfig(confidence_weights=valid_weights)
        assert config.confidence_weights == valid_weights
        
        # Empty weights (valid)
        config = MetadataConfig(confidence_weights={})
        assert config.confidence_weights == {}
        
        # Invalid weights (don't sum to 1.0)
        with pytest.raises(ValidationError):
            MetadataConfig(confidence_weights={
                "extraction_method": 0.4,
                "data_quality": 0.7  # Sum = 1.1
            })
    
    def test_metadata_config_serialization(self):
        """Test config serialization and deserialization."""
        original_config = MetadataConfig(
            max_workers=8,
            default_language=LanguageCode.FRENCH,
            confidence_weights={"test": 1.0}
        )
        
        # Serialize to dict
        config_dict = original_config.dict()
        assert config_dict["max_workers"] == 8
        assert config_dict["default_language"] == "fr"
        
        # Deserialize from dict
        new_config = MetadataConfig(**config_dict)
        assert new_config.max_workers == 8
        assert new_config.default_language == LanguageCode.FRENCH
        assert new_config.confidence_weights == {"test": 1.0}