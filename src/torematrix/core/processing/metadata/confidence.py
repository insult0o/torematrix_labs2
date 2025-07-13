"""Advanced confidence scoring system for metadata extraction."""

from typing import Dict, List, Any, Optional, Tuple
import statistics
import math
from datetime import datetime

from .types import (
    ExtractionMethod, ExtractionContext, MetadataValidationResult,
    ConfidenceLevel, ExtractorConfig
)
from .schema import BaseMetadata


class ConfidenceScorer:
    """Advanced confidence scoring for metadata extraction results."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize confidence scorer with configurable weights.
        
        Args:
            weights: Custom weights for confidence factors
        """
        self.weights = weights or self._default_weights()
        self._validate_weights()
    
    def _default_weights(self) -> Dict[str, float]:
        """Default confidence scoring weights."""
        return {
            "extraction_method": 0.25,
            "data_quality": 0.30,
            "validation_result": 0.20,
            "source_reliability": 0.15,
            "consistency_check": 0.10
        }
    
    def _validate_weights(self) -> None:
        """Validate that weights sum to 1.0."""
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, rel_tol=1e-6):
            raise ValueError(f"Confidence weights must sum to 1.0, got {total}")
    
    def calculate_confidence(
        self,
        metadata: BaseMetadata,
        extraction_context: ExtractionContext,
        additional_factors: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate comprehensive confidence score for extracted metadata.
        
        Args:
            metadata: The extracted metadata object
            extraction_context: Context information about extraction
            additional_factors: Additional confidence factors
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        factors = {}
        
        # Calculate individual confidence factors
        factors["extraction_method"] = self._score_extraction_method(
            metadata.extraction_method
        )
        factors["data_quality"] = self._score_data_quality(metadata)
        factors["validation_result"] = self._score_validation_result(
            metadata.validation_result
        )
        factors["source_reliability"] = self._score_source_reliability(
            metadata.source_extractor, extraction_context
        )
        factors["consistency_check"] = self._score_consistency(
            metadata, extraction_context
        )
        
        # Include additional factors if provided
        if additional_factors:
            factors.update(additional_factors)
        
        # Calculate weighted confidence score
        confidence = sum(
            self.weights.get(factor, 0.0) * score
            for factor, score in factors.items()
            if factor in self.weights
        )
        
        # Apply normalization and bounds checking
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def _score_extraction_method(self, method: ExtractionMethod) -> float:
        """Score confidence based on extraction method reliability."""
        method_scores = {
            ExtractionMethod.DIRECT_PARSING: 0.95,
            ExtractionMethod.RULE_BASED: 0.85,
            ExtractionMethod.HYBRID: 0.80,
            ExtractionMethod.HEURISTIC_ANALYSIS: 0.70,
            ExtractionMethod.ML_INFERENCE: 0.75,
            ExtractionMethod.OCR_EXTRACTION: 0.60
        }
        return method_scores.get(method, 0.50)
    
    def _score_data_quality(self, metadata: BaseMetadata) -> float:
        """Score confidence based on data quality indicators."""
        quality_score = 1.0
        
        # Check for missing required fields
        if hasattr(metadata, 'title') and not getattr(metadata, 'title'):
            quality_score *= 0.9
        
        # Check for data completeness
        filled_fields = sum(1 for field, value in metadata.dict().items() 
                          if value is not None and value != "")
        total_fields = len(metadata.dict())
        completeness_ratio = filled_fields / total_fields if total_fields > 0 else 0
        quality_score *= (0.5 + 0.5 * completeness_ratio)
        
        # Check for data consistency
        if hasattr(metadata, 'confidence_score'):
            if metadata.confidence_score < 0.3:
                quality_score *= 0.7
        
        return max(0.0, min(1.0, quality_score))
    
    def _score_validation_result(
        self,
        validation: Optional[MetadataValidationResult]
    ) -> float:
        """Score confidence based on validation results."""
        if not validation:
            return 0.5  # Neutral score if no validation
        
        if not validation.is_valid:
            return 0.2  # Low confidence for invalid metadata
        
        # Base score from validation confidence
        score = validation.confidence_score
        
        # Penalize for validation errors
        if validation.validation_errors:
            error_penalty = min(0.3, len(validation.validation_errors) * 0.1)
            score *= (1.0 - error_penalty)
        
        # Minor penalty for warnings
        if validation.validation_warnings:
            warning_penalty = min(0.1, len(validation.validation_warnings) * 0.02)
            score *= (1.0 - warning_penalty)
        
        return max(0.0, min(1.0, score))
    
    def _score_source_reliability(
        self,
        extractor_name: str,
        context: ExtractionContext
    ) -> float:
        """Score confidence based on extractor reliability."""
        # Base reliability scores for known extractors
        extractor_reliability = {
            "DocumentMetadataExtractor": 0.90,
            "PageMetadataExtractor": 0.85,
            "ElementMetadataExtractor": 0.80,
            "OCRMetadataExtractor": 0.65,
            "HeuristicExtractor": 0.70
        }
        
        base_score = extractor_reliability.get(extractor_name, 0.75)
        
        # Adjust based on extractor chain length
        chain_length = len(context.extractor_chain)
        if chain_length > 3:
            base_score *= 0.9  # Slightly lower confidence for long chains
        
        # Adjust based on processing hints
        if context.processing_hints.get("high_quality_source", False):
            base_score *= 1.1
        if context.processing_hints.get("low_quality_source", False):
            base_score *= 0.8
        
        return max(0.0, min(1.0, base_score))
    
    def _score_consistency(
        self,
        metadata: BaseMetadata,
        context: ExtractionContext
    ) -> float:
        """Score confidence based on internal consistency checks."""
        consistency_score = 1.0
        
        # Check timestamp consistency
        extraction_time = metadata.extraction_timestamp
        context_time = context.extraction_timestamp
        time_diff = abs((extraction_time - context_time).total_seconds())
        if time_diff > 60:  # More than 1 minute difference
            consistency_score *= 0.9
        
        # Check for reasonable confidence bounds
        if hasattr(metadata, 'confidence_score'):
            confidence = metadata.confidence_score
            if confidence < 0.1 or confidence > 0.99:
                consistency_score *= 0.8
        
        # Check field value consistency
        consistency_score *= self._check_field_consistency(metadata)
        
        return max(0.0, min(1.0, consistency_score))
    
    def _check_field_consistency(self, metadata: BaseMetadata) -> float:
        """Check internal field value consistency."""
        consistency = 1.0
        
        # Document-specific consistency checks
        if hasattr(metadata, 'page_count') and hasattr(metadata, 'total_elements'):
            page_count = getattr(metadata, 'page_count', 0)
            total_elements = getattr(metadata, 'total_elements', 0)
            
            if page_count > 0 and total_elements == 0:
                consistency *= 0.7  # Likely inconsistent
            elif page_count == 0 and total_elements > 0:
                consistency *= 0.7  # Likely inconsistent
        
        # Page-specific consistency checks
        if hasattr(metadata, 'element_count'):
            element_count = getattr(metadata, 'element_count', 0)
            text_count = getattr(metadata, 'text_element_count', 0)
            image_count = getattr(metadata, 'image_element_count', 0)
            table_count = getattr(metadata, 'table_element_count', 0)
            
            total_typed = text_count + image_count + table_count
            if total_typed > element_count:
                consistency *= 0.6  # Inconsistent counts
        
        return consistency
    
    def calculate_aggregated_confidence(
        self,
        metadata_list: List[BaseMetadata],
        extraction_context: ExtractionContext,
        aggregation_method: str = "weighted_average"
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate aggregated confidence across multiple metadata objects.
        
        Args:
            metadata_list: List of metadata objects
            extraction_context: Extraction context
            aggregation_method: Method for aggregation ('weighted_average', 'minimum', 'harmonic_mean')
            
        Returns:
            Tuple of (overall_confidence, individual_scores)
        """
        if not metadata_list:
            return 0.0, {}
        
        individual_scores = {}
        confidence_scores = []
        
        for metadata in metadata_list:
            confidence = self.calculate_confidence(metadata, extraction_context)
            individual_scores[metadata.metadata_id] = confidence
            confidence_scores.append(confidence)
        
        # Calculate aggregated confidence
        if aggregation_method == "weighted_average":
            # Weight by metadata importance (document > page > element > relationship)
            weights = self._get_metadata_importance_weights(metadata_list)
            overall_confidence = sum(
                score * weight for score, weight in zip(confidence_scores, weights)
            ) / sum(weights) if weights else 0.0
        elif aggregation_method == "minimum":
            overall_confidence = min(confidence_scores)
        elif aggregation_method == "harmonic_mean":
            overall_confidence = statistics.harmonic_mean(confidence_scores)
        else:
            overall_confidence = statistics.mean(confidence_scores)
        
        return overall_confidence, individual_scores
    
    def _get_metadata_importance_weights(
        self,
        metadata_list: List[BaseMetadata]
    ) -> List[float]:
        """Get importance weights for different metadata types."""
        weights = []
        for metadata in metadata_list:
            if metadata.metadata_type.value == "document":
                weights.append(1.0)
            elif metadata.metadata_type.value == "page":
                weights.append(0.8)
            elif metadata.metadata_type.value == "element":
                weights.append(0.6)
            elif metadata.metadata_type.value == "relationship":
                weights.append(0.4)
            else:
                weights.append(0.5)
        return weights
    
    def get_confidence_breakdown(
        self,
        metadata: BaseMetadata,
        extraction_context: ExtractionContext
    ) -> Dict[str, float]:
        """Get detailed breakdown of confidence factors.
        
        Returns:
            Dictionary mapping factor names to their scores
        """
        breakdown = {}
        
        breakdown["extraction_method"] = self._score_extraction_method(
            metadata.extraction_method
        )
        breakdown["data_quality"] = self._score_data_quality(metadata)
        breakdown["validation_result"] = self._score_validation_result(
            metadata.validation_result
        )
        breakdown["source_reliability"] = self._score_source_reliability(
            metadata.source_extractor, extraction_context
        )
        breakdown["consistency_check"] = self._score_consistency(
            metadata, extraction_context
        )
        
        # Add weighted contributions
        for factor, score in breakdown.items():
            weight = self.weights.get(factor, 0.0)
            breakdown[f"{factor}_weighted"] = score * weight
        
        breakdown["overall_confidence"] = self.calculate_confidence(
            metadata, extraction_context
        )
        
        return breakdown
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update confidence scoring weights.
        
        Args:
            new_weights: New weights dictionary
        """
        self.weights.update(new_weights)
        self._validate_weights()