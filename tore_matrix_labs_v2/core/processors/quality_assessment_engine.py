#!/usr/bin/env python3
"""
Quality Assessment Engine for TORE Matrix Labs V2

This engine provides comprehensive quality assessment for extracted content,
consolidating quality logic from the original codebase into a single,
robust assessment system.

Key improvements:
- Multi-dimensional quality scoring
- Configurable quality thresholds
- Detailed quality reports
- Performance optimization
- Consistent scoring across all extraction methods

Quality dimensions assessed:
- Text extraction quality (OCR confidence, completeness)
- Document structure quality (layout detection, formatting)
- Content validity (text patterns, language detection)
- Processing quality (extraction time, error rates)
"""

import logging
import re
import string
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

from ..models.unified_document_model import UnifiedDocument


@dataclass
class QualityMetrics:
    """Quality metrics for a document."""
    
    # Overall scores (0.0 - 1.0)
    overall_score: float = 0.0
    extraction_quality: float = 0.0
    structure_quality: float = 0.0
    content_quality: float = 0.0
    processing_quality: float = 0.0
    
    # Detailed metrics
    ocr_confidence: float = 0.0
    text_completeness: float = 0.0
    character_recognition_rate: float = 0.0
    word_recognition_rate: float = 0.0
    
    # Structure metrics
    layout_detection_score: float = 0.0
    table_detection_score: float = 0.0
    image_detection_score: float = 0.0
    paragraph_structure_score: float = 0.0
    
    # Content metrics
    language_consistency: float = 0.0
    text_coherence: float = 0.0
    formatting_preservation: float = 0.0
    special_characters_ratio: float = 0.0
    
    # Processing metrics
    extraction_speed: float = 0.0
    memory_efficiency: float = 0.0
    error_rate: float = 0.0
    
    # Issues detected
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    assessed_at: datetime = field(default_factory=datetime.now)
    assessment_time: float = 0.0


@dataclass
class QualityThresholds:
    """Configurable quality thresholds."""
    
    # Minimum acceptable scores
    min_overall_score: float = 0.8
    min_extraction_quality: float = 0.7
    min_structure_quality: float = 0.6
    min_content_quality: float = 0.7
    min_processing_quality: float = 0.5
    
    # OCR specific thresholds
    min_ocr_confidence: float = 0.8
    min_character_recognition: float = 0.9
    min_word_recognition: float = 0.85
    
    # Content thresholds
    max_special_characters_ratio: float = 0.1
    min_text_coherence: float = 0.7
    min_language_consistency: float = 0.8
    
    # Processing thresholds
    max_extraction_time_per_page: float = 5.0  # seconds
    max_memory_per_page: float = 100.0  # MB
    max_error_rate: float = 0.05


class QualityAssessmentEngine:
    """
    Comprehensive quality assessment engine for document processing.
    
    This engine evaluates the quality of extracted content across multiple
    dimensions and provides detailed reports for validation decisions.
    """
    
    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        """Initialize the quality assessment engine."""
        self.logger = logging.getLogger(__name__)
        self.thresholds = thresholds or QualityThresholds()
        
        # Assessment history for learning
        self.assessment_history: List[QualityMetrics] = []
        
        # Language patterns for validation
        self.language_patterns = {
            "english": re.compile(r'[a-zA-Z\s.,!?;:()"-]+'),
            "alphanumeric": re.compile(r'[a-zA-Z0-9\s.,!?;:()"-]+'),
            "special_chars": re.compile(r'[^\w\s.,!?;:()"-]')
        }
        
        self.logger.info("Quality assessment engine initialized")
    
    def assess_quality(self, 
                      document: UnifiedDocument,
                      extraction_result: Dict[str, Any]) -> QualityMetrics:
        """
        Perform comprehensive quality assessment.
        
        Args:
            document: Document being assessed
            extraction_result: Result from text extraction
            
        Returns:
            Quality metrics with detailed scores and issues
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Assessing quality for: {document.id}")
            
            # Initialize metrics
            metrics = QualityMetrics()
            
            # Assess different quality dimensions
            self._assess_extraction_quality(metrics, extraction_result)
            self._assess_structure_quality(metrics, extraction_result)
            self._assess_content_quality(metrics, extraction_result)
            self._assess_processing_quality(metrics, extraction_result, document)
            
            # Calculate overall score
            metrics.overall_score = self._calculate_overall_score(metrics)
            
            # Identify issues and warnings
            self._identify_issues(metrics)
            
            # Record assessment time
            metrics.assessment_time = (datetime.now() - start_time).total_seconds()
            
            # Store in history
            self.assessment_history.append(metrics)
            
            self.logger.info(f"Quality assessment completed: {metrics.overall_score:.3f}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {str(e)}")
            # Return default metrics with error
            metrics = QualityMetrics()
            metrics.issues.append({
                "type": "assessment_error",
                "message": f"Quality assessment failed: {str(e)}",
                "severity": "critical"
            })
            return metrics
    
    def _assess_extraction_quality(self, 
                                 metrics: QualityMetrics,
                                 extraction_result: Dict[str, Any]):
        """Assess the quality of text extraction."""
        try:
            # Get extraction metadata
            metadata = extraction_result.get("metadata", {})
            text = extraction_result.get("text", "")
            pages = extraction_result.get("pages", [])
            
            # OCR confidence (if available)
            if "confidence" in metadata:
                metrics.ocr_confidence = metadata["confidence"] / 100.0
            else:
                # Estimate confidence based on extraction method
                extractor = metadata.get("extractor", "unknown")
                if extractor == "unstructured":
                    metrics.ocr_confidence = 0.9
                elif extractor == "pymupdf":
                    metrics.ocr_confidence = 0.8
                elif extractor == "ocr":
                    metrics.ocr_confidence = 0.7
                else:
                    metrics.ocr_confidence = 0.5
            
            # Text completeness
            if text:
                # Check for typical completeness indicators
                has_complete_sentences = bool(re.search(r'[.!?]\s+[A-Z]', text))
                has_proper_spacing = not bool(re.search(r'\w{20,}', text))  # No extremely long words
                has_reasonable_length = len(text) > 100
                
                completeness_score = 0.0
                if has_complete_sentences:
                    completeness_score += 0.4
                if has_proper_spacing:
                    completeness_score += 0.3
                if has_reasonable_length:
                    completeness_score += 0.3
                
                metrics.text_completeness = completeness_score
            
            # Character and word recognition rates
            if text:
                total_chars = len(text)
                recognized_chars = len(re.findall(r'[a-zA-Z0-9\s.,!?;:()""-]', text))
                metrics.character_recognition_rate = recognized_chars / total_chars if total_chars > 0 else 0.0
                
                words = text.split()
                if words:
                    # Check for garbled words (too many special characters)
                    good_words = sum(1 for word in words if len(re.findall(r'[a-zA-Z0-9]', word)) > len(word) * 0.7)
                    metrics.word_recognition_rate = good_words / len(words)
            
            # Calculate extraction quality score
            metrics.extraction_quality = (
                metrics.ocr_confidence * 0.3 +
                metrics.text_completeness * 0.3 +
                metrics.character_recognition_rate * 0.2 +
                metrics.word_recognition_rate * 0.2
            )
            
        except Exception as e:
            self.logger.error(f"Extraction quality assessment failed: {str(e)}")
            metrics.extraction_quality = 0.0
    
    def _assess_structure_quality(self,
                                metrics: QualityMetrics,
                                extraction_result: Dict[str, Any]):
        """Assess the quality of document structure detection."""
        try:
            text = extraction_result.get("text", "")
            pages = extraction_result.get("pages", [])
            metadata = extraction_result.get("metadata", {})
            
            # Layout detection score
            if "elements" in metadata:
                # Unstructured provides element detection
                elements = metadata["elements"]
                element_types = {elem.get("type", "unknown") for elem in elements}
                
                # Score based on variety of detected elements
                type_variety_score = min(len(element_types) / 5.0, 1.0)  # Normalize to max 5 types
                metrics.layout_detection_score = type_variety_score
            else:
                # Basic layout detection based on text patterns
                has_paragraphs = bool(re.search(r'\n\s*\n', text))
                has_titles = bool(re.search(r'^[A-Z][A-Z\s]+$', text, re.MULTILINE))
                has_lists = bool(re.search(r'^\s*[•\-\*]\s+', text, re.MULTILINE))
                
                layout_score = 0.0
                if has_paragraphs:
                    layout_score += 0.4
                if has_titles:
                    layout_score += 0.3
                if has_lists:
                    layout_score += 0.3
                
                metrics.layout_detection_score = layout_score
            
            # Table detection score
            table_indicators = [
                len(re.findall(r'\t', text)),  # Tab characters
                len(re.findall(r'\s{3,}', text)),  # Multiple spaces
                len(re.findall(r'\|', text)),  # Pipe characters
            ]
            
            if any(indicator > 10 for indicator in table_indicators):
                metrics.table_detection_score = 0.8
            elif any(indicator > 5 for indicator in table_indicators):
                metrics.table_detection_score = 0.5
            else:
                metrics.table_detection_score = 0.2
            
            # Image detection score (based on gaps or image placeholders)
            image_indicators = [
                len(re.findall(r'\[image\]', text.lower())),
                len(re.findall(r'\[figure\]', text.lower())),
                len(re.findall(r'\[photo\]', text.lower())),
            ]
            
            total_image_indicators = sum(image_indicators)
            if total_image_indicators > 0:
                metrics.image_detection_score = min(total_image_indicators / 5.0, 1.0)
            else:
                metrics.image_detection_score = 0.5  # Neutral score
            
            # Paragraph structure score
            paragraphs = re.split(r'\n\s*\n', text)
            if paragraphs:
                avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
                # Good paragraphs are 20-200 words
                if 20 <= avg_paragraph_length <= 200:
                    metrics.paragraph_structure_score = 1.0
                elif 10 <= avg_paragraph_length <= 300:
                    metrics.paragraph_structure_score = 0.7
                else:
                    metrics.paragraph_structure_score = 0.4
            
            # Calculate structure quality score
            metrics.structure_quality = (
                metrics.layout_detection_score * 0.3 +
                metrics.table_detection_score * 0.25 +
                metrics.image_detection_score * 0.2 +
                metrics.paragraph_structure_score * 0.25
            )
            
        except Exception as e:
            self.logger.error(f"Structure quality assessment failed: {str(e)}")
            metrics.structure_quality = 0.0
    
    def _assess_content_quality(self,
                              metrics: QualityMetrics,
                              extraction_result: Dict[str, Any]):
        """Assess the quality of content accuracy and coherence."""
        try:
            text = extraction_result.get("text", "")
            
            if not text:
                metrics.content_quality = 0.0
                return
            
            # Language consistency
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            
            if total_chars > 0:
                metrics.language_consistency = english_chars / total_chars
            
            # Special characters ratio
            special_chars = len(re.findall(r'[^\w\s.,!?;:()"-]', text))
            if total_chars > 0:
                metrics.special_characters_ratio = special_chars / total_chars
            
            # Text coherence (basic check)
            sentences = re.split(r'[.!?]+', text)
            coherent_sentences = 0
            
            for sentence in sentences:
                words = sentence.strip().split()
                if len(words) >= 3:  # Minimum sentence length
                    # Check for proper capitalization
                    if words[0] and words[0][0].isupper():
                        coherent_sentences += 1
            
            if sentences:
                metrics.text_coherence = coherent_sentences / len(sentences)
            
            # Formatting preservation
            formatting_indicators = [
                bool(re.search(r'\n', text)),  # Line breaks preserved
                bool(re.search(r'  ', text)),  # Multiple spaces preserved
                bool(re.search(r'[A-Z]{2,}', text)),  # Uppercase preserved
                bool(re.search(r'\d+', text)),  # Numbers preserved
            ]
            
            metrics.formatting_preservation = sum(formatting_indicators) / len(formatting_indicators)
            
            # Calculate content quality score
            language_score = metrics.language_consistency
            coherence_score = metrics.text_coherence
            formatting_score = metrics.formatting_preservation
            special_chars_penalty = max(0, 1.0 - (metrics.special_characters_ratio / self.thresholds.max_special_characters_ratio))
            
            metrics.content_quality = (
                language_score * 0.3 +
                coherence_score * 0.3 +
                formatting_score * 0.2 +
                special_chars_penalty * 0.2
            )
            
        except Exception as e:
            self.logger.error(f"Content quality assessment failed: {str(e)}")
            metrics.content_quality = 0.0
    
    def _assess_processing_quality(self,
                                 metrics: QualityMetrics,
                                 extraction_result: Dict[str, Any],
                                 document: UnifiedDocument):
        """Assess the quality of the processing performance."""
        try:
            metadata = extraction_result.get("metadata", {})
            
            # Extraction speed
            extraction_time = metadata.get("extraction_time", 0.0)
            page_count = document.metadata.page_count or 1
            
            time_per_page = extraction_time / page_count
            if time_per_page <= self.thresholds.max_extraction_time_per_page:
                metrics.extraction_speed = 1.0
            else:
                # Penalize slow extraction
                metrics.extraction_speed = max(0.0, 1.0 - (time_per_page - self.thresholds.max_extraction_time_per_page) / 10.0)
            
            # Memory efficiency (estimated)
            text_length = len(extraction_result.get("text", ""))
            if text_length > 0:
                # Rough estimate: 1 char = 1 byte, good efficiency is < 10x text size
                estimated_memory = text_length * 2  # Conservative estimate
                memory_per_page = estimated_memory / (page_count * 1024 * 1024)  # MB
                
                if memory_per_page <= self.thresholds.max_memory_per_page:
                    metrics.memory_efficiency = 1.0
                else:
                    metrics.memory_efficiency = max(0.0, 1.0 - (memory_per_page - self.thresholds.max_memory_per_page) / 100.0)
            else:
                metrics.memory_efficiency = 0.0
            
            # Error rate
            if extraction_result.get("success", False):
                metrics.error_rate = 0.0
            else:
                metrics.error_rate = 1.0
            
            # Calculate processing quality score
            metrics.processing_quality = (
                metrics.extraction_speed * 0.4 +
                metrics.memory_efficiency * 0.3 +
                (1.0 - metrics.error_rate) * 0.3
            )
            
        except Exception as e:
            self.logger.error(f"Processing quality assessment failed: {str(e)}")
            metrics.processing_quality = 0.0
    
    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """Calculate the overall quality score."""
        # Weighted average of all quality dimensions
        overall = (
            metrics.extraction_quality * 0.35 +
            metrics.structure_quality * 0.25 +
            metrics.content_quality * 0.25 +
            metrics.processing_quality * 0.15
        )
        
        return min(max(overall, 0.0), 1.0)  # Clamp to [0, 1]
    
    def _identify_issues(self, metrics: QualityMetrics):
        """Identify issues and warnings based on quality metrics."""
        # Critical issues
        if metrics.overall_score < self.thresholds.min_overall_score:
            metrics.issues.append({
                "type": "low_overall_quality",
                "message": f"Overall quality score {metrics.overall_score:.3f} below threshold {self.thresholds.min_overall_score}",
                "severity": "critical",
                "score": metrics.overall_score
            })
        
        if metrics.extraction_quality < self.thresholds.min_extraction_quality:
            metrics.issues.append({
                "type": "poor_extraction",
                "message": f"Extraction quality {metrics.extraction_quality:.3f} below threshold {self.thresholds.min_extraction_quality}",
                "severity": "high",
                "score": metrics.extraction_quality
            })
        
        if metrics.ocr_confidence < self.thresholds.min_ocr_confidence:
            metrics.issues.append({
                "type": "low_ocr_confidence",
                "message": f"OCR confidence {metrics.ocr_confidence:.3f} below threshold {self.thresholds.min_ocr_confidence}",
                "severity": "medium",
                "score": metrics.ocr_confidence
            })
        
        # Warnings
        if metrics.character_recognition_rate < self.thresholds.min_character_recognition:
            metrics.warnings.append({
                "type": "character_recognition",
                "message": f"Character recognition rate {metrics.character_recognition_rate:.3f} below optimal",
                "score": metrics.character_recognition_rate
            })
        
        if metrics.special_characters_ratio > self.thresholds.max_special_characters_ratio:
            metrics.warnings.append({
                "type": "high_special_characters",
                "message": f"High special character ratio {metrics.special_characters_ratio:.3f}",
                "score": metrics.special_characters_ratio
            })
    
    def get_assessment_summary(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Get a summary of the quality assessment."""
        return {
            "overall_score": metrics.overall_score,
            "requires_validation": metrics.overall_score < self.thresholds.min_overall_score,
            "critical_issues": len([issue for issue in metrics.issues if issue.get("severity") == "critical"]),
            "total_issues": len(metrics.issues),
            "total_warnings": len(metrics.warnings),
            "assessment_time": metrics.assessment_time,
            "key_metrics": {
                "extraction_quality": metrics.extraction_quality,
                "structure_quality": metrics.structure_quality,
                "content_quality": metrics.content_quality,
                "processing_quality": metrics.processing_quality
            }
        }
    
    def update_thresholds(self, new_thresholds: QualityThresholds):
        """Update quality thresholds."""
        self.thresholds = new_thresholds
        self.logger.info("Quality thresholds updated")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the assessment engine."""
        if not self.assessment_history:
            return {"assessments_performed": 0}
        
        scores = [metrics.overall_score for metrics in self.assessment_history]
        assessment_times = [metrics.assessment_time for metrics in self.assessment_history]
        
        return {
            "assessments_performed": len(self.assessment_history),
            "average_score": sum(scores) / len(scores),
            "average_assessment_time": sum(assessment_times) / len(assessment_times),
            "score_distribution": {
                "excellent": len([s for s in scores if s >= 0.9]),
                "good": len([s for s in scores if 0.8 <= s < 0.9]),
                "fair": len([s for s in scores if 0.6 <= s < 0.8]),
                "poor": len([s for s in scores if s < 0.6])
            }
        }