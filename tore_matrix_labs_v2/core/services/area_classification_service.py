#!/usr/bin/env python3
"""
Area Classification Service for TORE Matrix Labs V2

Provides automatic classification of document areas into categories
like IMAGE, TABLE, DIAGRAM, TEXT, etc.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

from ..models.unified_area_model import AreaType, UnifiedArea, AreaCoordinates


class ClassificationConfidence(Enum):
    """Confidence levels for area classification."""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ClassificationResult:
    """Result of area classification."""
    area_type: AreaType
    confidence: ClassificationConfidence
    score: float
    reasoning: str = ""
    alternative_types: List[Tuple[AreaType, float]] = None


class AreaClassificationService:
    """Service for classifying document areas automatically."""
    
    def __init__(self):
        """Initialize the area classification service."""
        self.logger = logging.getLogger(__name__)
        
        # Classification rules and weights
        self.classification_rules = self._initialize_rules()
        
        self.logger.info("Area classification service initialized")
    
    def _initialize_rules(self) -> Dict[str, Any]:
        """Initialize classification rules."""
        return {
            "image_indicators": [
                "jpg", "jpeg", "png", "gif", "bmp", "tiff",
                "image", "figure", "photo", "picture"
            ],
            "table_indicators": [
                "table", "row", "column", "cell", "grid",
                "data", "values", "entries"
            ],
            "diagram_indicators": [
                "diagram", "chart", "graph", "flowchart",
                "schematic", "layout", "map"
            ],
            "text_indicators": [
                "paragraph", "text", "content", "description",
                "explanation", "details"
            ]
        }
    
    def classify_area(self, 
                     coordinates: AreaCoordinates,
                     content_text: str = "",
                     metadata: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify a document area into its appropriate type.
        
        Args:
            coordinates: Area coordinates and dimensions
            content_text: Text content extracted from the area
            metadata: Additional metadata about the area
            
        Returns:
            Classification result with confidence score
        """
        metadata = metadata or {}
        
        # Analyze area characteristics
        characteristics = self._analyze_area_characteristics(
            coordinates, content_text, metadata
        )
        
        # Score each possible area type
        type_scores = self._score_area_types(characteristics)
        
        # Select best classification
        best_type = max(type_scores.items(), key=lambda x: x[1])
        area_type, score = best_type
        
        # Determine confidence level
        confidence = self._determine_confidence(score, type_scores)
        
        # Get alternative classifications
        alternatives = sorted(
            [(t, s) for t, s in type_scores.items() if t != area_type],
            key=lambda x: x[1],
            reverse=True
        )[:3]  # Top 3 alternatives
        
        # Generate reasoning
        reasoning = self._generate_reasoning(area_type, characteristics)
        
        return ClassificationResult(
            area_type=area_type,
            confidence=confidence,
            score=score,
            reasoning=reasoning,
            alternative_types=alternatives
        )
    
    def classify_multiple_areas(self, 
                               areas_data: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """
        Classify multiple areas in batch.
        
        Args:
            areas_data: List of area data dictionaries
            
        Returns:
            List of classification results
        """
        results = []
        
        for area_data in areas_data:
            coordinates = area_data.get("coordinates")
            content_text = area_data.get("content_text", "")
            metadata = area_data.get("metadata", {})
            
            result = self.classify_area(coordinates, content_text, metadata)
            results.append(result)
        
        return results
    
    def _analyze_area_characteristics(self, 
                                    coordinates: AreaCoordinates,
                                    content_text: str,
                                    metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze characteristics of an area for classification."""
        
        characteristics = {
            # Geometric characteristics
            "width": coordinates.width,
            "height": coordinates.height,
            "area_size": coordinates.area,
            "aspect_ratio": coordinates.width / coordinates.height if coordinates.height > 0 else 1.0,
            
            # Content characteristics
            "text_length": len(content_text),
            "text_content": content_text.lower(),
            "has_text": len(content_text.strip()) > 0,
            
            # Metadata characteristics
            "metadata": metadata
        }
        
        # Analyze text patterns
        if content_text:
            characteristics.update(self._analyze_text_patterns(content_text))
        
        return characteristics
    
    def _analyze_text_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze text patterns for classification hints."""
        text_lower = text.lower()
        
        return {
            "has_table_keywords": any(keyword in text_lower 
                                    for keyword in self.classification_rules["table_indicators"]),
            "has_image_keywords": any(keyword in text_lower 
                                    for keyword in self.classification_rules["image_indicators"]),
            "has_diagram_keywords": any(keyword in text_lower 
                                      for keyword in self.classification_rules["diagram_indicators"]),
            "has_structured_data": "\t" in text or "|" in text,
            "line_count": len(text.split("\n")),
            "word_count": len(text.split()),
            "has_numbers": any(char.isdigit() for char in text),
            "has_special_chars": any(char in "[](){}<>|+-=*/" for char in text)
        }
    
    def _score_area_types(self, characteristics: Dict[str, Any]) -> Dict[AreaType, float]:
        """Score each area type based on characteristics."""
        scores = {}
        
        # Score IMAGE type
        scores[AreaType.IMAGE] = self._score_image_type(characteristics)
        
        # Score TABLE type
        scores[AreaType.TABLE] = self._score_table_type(characteristics)
        
        # Score DIAGRAM type
        scores[AreaType.DIAGRAM] = self._score_diagram_type(characteristics)
        
        # Score TEXT type
        scores[AreaType.TEXT] = self._score_text_type(characteristics)
        
        # Score other types
        scores[AreaType.HEADER] = self._score_header_type(characteristics)
        scores[AreaType.FOOTER] = self._score_footer_type(characteristics)
        scores[AreaType.FIGURE] = self._score_figure_type(characteristics)
        scores[AreaType.CHART] = self._score_chart_type(characteristics)
        
        return scores
    
    def _score_image_type(self, characteristics: Dict[str, Any]) -> float:
        """Score IMAGE type likelihood."""
        score = 0.1  # Base score
        
        # High score if no text content
        if not characteristics["has_text"]:
            score += 0.6
        
        # High score for image keywords
        if characteristics.get("has_image_keywords", False):
            score += 0.4
        
        # Consider aspect ratio (images often have specific ratios)
        aspect_ratio = characteristics["aspect_ratio"]
        if 0.5 <= aspect_ratio <= 2.0:  # Common image ratios
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_table_type(self, characteristics: Dict[str, Any]) -> float:
        """Score TABLE type likelihood."""
        score = 0.1  # Base score
        
        # High score for structured data
        if characteristics.get("has_structured_data", False):
            score += 0.5
        
        # High score for table keywords
        if characteristics.get("has_table_keywords", False):
            score += 0.4
        
        # High score for numbers (tables often contain data)
        if characteristics.get("has_numbers", False):
            score += 0.2
        
        # Consider text length (tables have moderate text)
        text_length = characteristics["text_length"]
        if 50 <= text_length <= 1000:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_diagram_type(self, characteristics: Dict[str, Any]) -> float:
        """Score DIAGRAM type likelihood."""
        score = 0.1  # Base score
        
        # High score for diagram keywords
        if characteristics.get("has_diagram_keywords", False):
            score += 0.5
        
        # High score for special characters (diagrams often have symbols)
        if characteristics.get("has_special_chars", False):
            score += 0.3
        
        # Consider aspect ratio (diagrams often square or landscape)
        aspect_ratio = characteristics["aspect_ratio"]
        if aspect_ratio >= 1.0:  # Landscape or square
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_text_type(self, characteristics: Dict[str, Any]) -> float:
        """Score TEXT type likelihood."""
        score = 0.2  # Base score (text is common)
        
        # High score for substantial text content
        if characteristics["has_text"] and characteristics["text_length"] > 100:
            score += 0.5
        
        # High score for multiple lines (paragraphs)
        line_count = characteristics.get("line_count", 0)
        if line_count >= 3:
            score += 0.3
        
        # Lower score if has structured indicators
        if characteristics.get("has_structured_data", False):
            score -= 0.2
        
        return max(min(score, 1.0), 0.0)
    
    def _score_header_type(self, characteristics: Dict[str, Any]) -> float:
        """Score HEADER type likelihood."""
        score = 0.1
        
        # Headers are usually short and at top
        if characteristics["text_length"] < 100:
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_footer_type(self, characteristics: Dict[str, Any]) -> float:
        """Score FOOTER type likelihood."""
        score = 0.1
        
        # Footers are usually short
        if characteristics["text_length"] < 50:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_figure_type(self, characteristics: Dict[str, Any]) -> float:
        """Score FIGURE type likelihood."""
        # Similar to image but with more context
        return self._score_image_type(characteristics) * 0.8
    
    def _score_chart_type(self, characteristics: Dict[str, Any]) -> float:
        """Score CHART type likelihood."""
        # Similar to diagram but more data-focused
        score = self._score_diagram_type(characteristics) * 0.9
        
        if characteristics.get("has_numbers", False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _determine_confidence(self, 
                            best_score: float, 
                            all_scores: Dict[AreaType, float]) -> ClassificationConfidence:
        """Determine confidence level based on scores."""
        
        # Get second best score
        sorted_scores = sorted(all_scores.values(), reverse=True)
        second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        
        # Calculate confidence based on score and separation
        score_gap = best_score - second_best
        
        if best_score >= 0.8 and score_gap >= 0.3:
            return ClassificationConfidence.VERY_HIGH
        elif best_score >= 0.6 and score_gap >= 0.2:
            return ClassificationConfidence.HIGH
        elif best_score >= 0.4 and score_gap >= 0.1:
            return ClassificationConfidence.MEDIUM
        else:
            return ClassificationConfidence.LOW
    
    def _generate_reasoning(self, 
                          area_type: AreaType, 
                          characteristics: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for classification."""
        
        reasons = []
        
        if area_type == AreaType.IMAGE:
            if not characteristics["has_text"]:
                reasons.append("no text content detected")
            if characteristics.get("has_image_keywords"):
                reasons.append("contains image-related keywords")
        
        elif area_type == AreaType.TABLE:
            if characteristics.get("has_structured_data"):
                reasons.append("contains structured data patterns")
            if characteristics.get("has_table_keywords"):
                reasons.append("contains table-related keywords")
            if characteristics.get("has_numbers"):
                reasons.append("contains numerical data")
        
        elif area_type == AreaType.TEXT:
            if characteristics["text_length"] > 100:
                reasons.append("substantial text content")
            if characteristics.get("line_count", 0) >= 3:
                reasons.append("multiple text lines")
        
        elif area_type == AreaType.DIAGRAM:
            if characteristics.get("has_diagram_keywords"):
                reasons.append("contains diagram-related keywords")
            if characteristics.get("has_special_chars"):
                reasons.append("contains special characters/symbols")
        
        if not reasons:
            reasons.append("based on area characteristics and size")
        
        return f"Classified as {area_type.value}: " + ", ".join(reasons)
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """Get classification statistics and performance metrics."""
        return {
            "service_name": "AreaClassificationService",
            "supported_types": [area_type.value for area_type in AreaType],
            "classification_rules": len(self.classification_rules),
            "confidence_levels": [conf.value for conf in ClassificationConfidence]
        }