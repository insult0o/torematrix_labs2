#!/usr/bin/env python3
"""
Post-processing pipeline for TORE Matrix Labs.
Comprehensive quality assessment and content optimization after initial extraction.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from ..config.constants import ProcessingStatus, QualityLevel, ValidationState
from ..config.settings import Settings
from ..models.document_models import Document, ValidationResult, ProcessingHistory
from .document_analyzer import DocumentAnalyzer, PageAnalysis
from .content_extractor import ContentExtractor, ExtractedContent
from .quality_assessor import QualityAssessor, QualityAssessment, QualityIssue, QualityIssueType
from .content_validator import ContentValidator, ValidationSession


@dataclass
class PostProcessingResult:
    """Results from post-processing pipeline."""
    document_id: str
    processing_time: float
    quality_assessment: QualityAssessment
    validation_result: ValidationResult
    validation_session: ValidationSession
    content_optimization: Dict[str, Any]
    export_ready: bool
    recommendations: List[str]
    metadata: Dict[str, Any]


@dataclass
class ContentOptimization:
    """Content optimization results."""
    chunk_count: int
    chunk_quality_scores: List[float]
    semantic_boundaries: List[int]
    duplicate_removal_count: int
    formatting_improvements: List[str]
    structure_corrections: List[str]


class PostProcessor:
    """
    Post-processing pipeline that provides comprehensive quality assessment,
    content validation, and optimization for enterprise-grade document processing.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize sub-components
        self.document_analyzer = DocumentAnalyzer(settings)
        self.content_extractor = ContentExtractor(settings)
        self.quality_assessor = QualityAssessor(settings)
        self.content_validator = ContentValidator(settings)
        
        # Post-processing configuration
        self.quality_threshold = settings.processing.quality_threshold
        self.chunk_size = settings.processing.chunk_size
        self.chunk_overlap = settings.processing.chunk_overlap
        
        self.logger.info("Post-processor initialized")
    
    def process_document(self, document: Document, extracted_content: ExtractedContent, 
                        page_analyses: List[PageAnalysis]) -> PostProcessingResult:
        """
        Execute complete post-processing pipeline.
        
        Args:
            document: Document metadata and configuration
            extracted_content: Initially extracted content
            page_analyses: Page analysis results
            
        Returns:
            PostProcessingResult with comprehensive analysis
        """
        self.logger.info(f"Starting post-processing for document: {document.id}")
        start_time = time.time()
        
        try:
            # Phase 1: Quality Assessment
            self.logger.info("Phase 1: Comprehensive quality assessment")
            quality_assessment = self.quality_assessor.assess_quality(
                extracted_content, page_analyses
            )
            
            # Phase 2: Content Validation
            self.logger.info("Phase 2: Content validation and verification")
            validation_result = self._validate_content(
                document, extracted_content, quality_assessment
            )
            
            # Phase 2.5: Advanced Content Validation with Corrections
            self.logger.info("Phase 2.5: Advanced content validation with correction suggestions")
            validation_session = self.content_validator.validate_content(
                document, extracted_content, quality_assessment.issues, "system_validator"
            )
            
            # Phase 3: Content Optimization
            self.logger.info("Phase 3: Content optimization and structuring")
            content_optimization = self._optimize_content(
                extracted_content, quality_assessment
            )
            
            # Phase 4: Export Readiness Assessment
            self.logger.info("Phase 4: Export readiness assessment")
            export_ready = self._assess_export_readiness(
                quality_assessment, validation_result
            )
            
            # Phase 5: Generate Final Recommendations
            self.logger.info("Phase 5: Generating recommendations")
            recommendations = self._generate_comprehensive_recommendations(
                quality_assessment, validation_result, content_optimization
            )
            
            # Create processing history entry
            processing_time = time.time() - start_time
            self._add_processing_history(document, processing_time, quality_assessment)
            
            result = PostProcessingResult(
                document_id=document.id,
                processing_time=processing_time,
                quality_assessment=quality_assessment,
                validation_result=validation_result,
                validation_session=validation_session,
                content_optimization=asdict(content_optimization),
                export_ready=export_ready,
                recommendations=recommendations,
                metadata=self._generate_metadata(document, quality_assessment)
            )
            
            self.logger.info(f"Post-processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Post-processing failed: {str(e)}")
            raise
    
    def _validate_content(self, document: Document, content: ExtractedContent, 
                         quality_assessment: QualityAssessment) -> ValidationResult:
        """
        Perform comprehensive content validation.
        
        Args:
            document: Document being validated
            content: Extracted content
            quality_assessment: Quality assessment results
            
        Returns:
            ValidationResult with validation status and details
        """
        validator_id = f"post_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        validation_date = datetime.now()
        issues_found = []
        corrections_made = []
        
        # Validation Rule 1: Minimum content requirements
        if not content.text_elements or len(content.text_elements) == 0:
            issues_found.append("No text content extracted from document")
        
        # Validation Rule 2: Quality threshold compliance
        if quality_assessment.overall_score < self.quality_threshold:
            issues_found.append(f"Quality score {quality_assessment.overall_score:.2f} below threshold {self.quality_threshold}")
        
        # Validation Rule 3: Critical issues check
        critical_issues = [issue for issue in quality_assessment.issues 
                          if issue.severity == 'critical']
        if critical_issues:
            issues_found.append(f"Found {len(critical_issues)} critical quality issues")
        
        # Validation Rule 4: ICAO compliance (for ICAO documents)
        if document.document_type.value == 'icao':
            icao_issues = self._validate_icao_compliance(content)
            issues_found.extend(icao_issues)
        
        # Validation Rule 5: Content completeness
        completeness_issues = self._validate_content_completeness(content)
        issues_found.extend(completeness_issues)
        
        # Determine validation state
        if not issues_found:
            state = ValidationState.APPROVED
            confidence = 0.95
        elif len(critical_issues) > 0:
            state = ValidationState.REJECTED
            confidence = 0.9
        else:
            state = ValidationState.NEEDS_REVIEW
            confidence = 0.7
        
        return ValidationResult(
            validator_id=validator_id,
            validation_date=validation_date,
            state=state,
            confidence=confidence,
            notes=f"Automated validation completed. {len(issues_found)} issues found.",
            issues_found=issues_found,
            corrections_made=corrections_made
        )
    
    def _validate_icao_compliance(self, content: ExtractedContent) -> List[str]:
        """Validate ICAO document compliance."""
        issues = []
        
        # Check for required ICAO elements
        text_content = " ".join([elem.content for elem in content.text_elements])
        
        # ICAO documents should have specific terminology
        icao_terms = ['ICAO', 'aircraft', 'aviation', 'flight', 'airport', 'ATC', 'navigation']
        found_terms = [term for term in icao_terms if term.lower() in text_content.lower()]
        
        if len(found_terms) < 2:
            issues.append("Document may not be ICAO-compliant (missing aviation terminology)")
        
        # Check for standard ICAO formatting patterns
        if not any(pattern in text_content for pattern in ['Annex', 'Standard', 'Procedure']):
            issues.append("Missing standard ICAO document structure elements")
        
        return issues
    
    def _validate_content_completeness(self, content: ExtractedContent) -> List[str]:
        """Validate content completeness."""
        issues = []
        
        # Check text content
        total_words = sum(len(elem.content.split()) for elem in content.text_elements)
        if total_words < 100:
            issues.append(f"Document has only {total_words} words (may be incomplete)")
        
        # Check for truncated content
        text_content = " ".join([elem.content for elem in content.text_elements])
        if text_content.endswith("...") or "content truncated" in text_content.lower():
            issues.append("Content appears to be truncated")
        
        # Check for extraction errors
        if "extraction error" in text_content.lower():
            issues.append("Extraction errors detected in content")
        
        return issues
    
    def _optimize_content(self, content: ExtractedContent, 
                         quality_assessment: QualityAssessment) -> ContentOptimization:
        """
        Optimize extracted content for better quality and usability.
        
        Args:
            content: Extracted content to optimize
            quality_assessment: Quality assessment results
            
        Returns:
            ContentOptimization with optimization results
        """
        # Initialize optimization tracking
        chunk_count = 0
        chunk_quality_scores = []
        semantic_boundaries = []
        duplicate_removal_count = 0
        formatting_improvements = []
        structure_corrections = []
        
        # Optimization 1: Remove duplicates
        original_count = len(content.text_elements)
        content.text_elements = self._remove_duplicate_content(content.text_elements)
        duplicate_removal_count = original_count - len(content.text_elements)
        
        if duplicate_removal_count > 0:
            formatting_improvements.append(f"Removed {duplicate_removal_count} duplicate text elements")
        
        # Optimization 2: Fix formatting issues
        formatting_fixes = self._fix_formatting_issues(content, quality_assessment.issues)
        formatting_improvements.extend(formatting_fixes)
        
        # Optimization 3: Optimize chunking
        chunks, boundaries, scores = self._optimize_chunking(content)
        chunk_count = len(chunks)
        semantic_boundaries = boundaries
        chunk_quality_scores = scores
        
        # Optimization 4: Structure corrections
        structure_fixes = self._correct_structure_issues(content, quality_assessment.issues)
        structure_corrections.extend(structure_fixes)
        
        return ContentOptimization(
            chunk_count=chunk_count,
            chunk_quality_scores=chunk_quality_scores,
            semantic_boundaries=semantic_boundaries,
            duplicate_removal_count=duplicate_removal_count,
            formatting_improvements=formatting_improvements,
            structure_corrections=structure_corrections
        )
    
    def _remove_duplicate_content(self, text_elements) -> List:
        """Remove duplicate text elements."""
        seen_content = set()
        unique_elements = []
        
        for element in text_elements:
            content_hash = hash(element.content.strip().lower())
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_elements.append(element)
        
        return unique_elements
    
    def _fix_formatting_issues(self, content: ExtractedContent, issues: List[QualityIssue]) -> List[str]:
        """Fix formatting issues identified in quality assessment."""
        fixes = []
        
        for issue in issues:
            if issue.issue_type == QualityIssueType.FORMATTING_ERROR:
                # Apply suggested fixes
                if "whitespace" in issue.description.lower():
                    # Fix excessive whitespace
                    for element in content.text_elements:
                        original = element.content
                        element.content = " ".join(element.content.split())
                        if original != element.content:
                            fixes.append("Normalized whitespace in text elements")
                            break
        
        return fixes
    
    def _optimize_chunking(self, content: ExtractedContent) -> Tuple[List[str], List[int], List[float]]:
        """Optimize content chunking for RAG and LLM applications."""
        chunks = []
        boundaries = []
        scores = []
        
        # Simple sentence-based chunking (can be enhanced with semantic analysis)
        full_text = " ".join([elem.content for elem in content.text_elements])
        sentences = full_text.split('. ')
        
        current_chunk = ""
        current_words = 0
        
        for i, sentence in enumerate(sentences):
            words_in_sentence = len(sentence.split())
            
            if current_words + words_in_sentence > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunks.append(current_chunk.strip())
                boundaries.append(len(current_chunk))
                scores.append(self._calculate_chunk_quality(current_chunk))
                
                # Start new chunk with overlap
                overlap_text = " ".join(current_chunk.split()[-self.chunk_overlap:])
                current_chunk = overlap_text + " " + sentence
                current_words = len(current_chunk.split())
            else:
                current_chunk += " " + sentence
                current_words += words_in_sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            boundaries.append(len(current_chunk))
            scores.append(self._calculate_chunk_quality(current_chunk))
        
        return chunks, boundaries, scores
    
    def _calculate_chunk_quality(self, chunk: str) -> float:
        """Calculate quality score for a text chunk."""
        # Simple quality metrics
        word_count = len(chunk.split())
        sentence_count = chunk.count('. ') + 1
        
        # Quality factors
        length_score = min(word_count / 100, 1.0)  # Prefer chunks around 100 words
        completeness_score = 1.0 if chunk.endswith('.') else 0.8
        readability_score = min(sentence_count / 5, 1.0)  # Prefer 3-5 sentences
        
        return (length_score + completeness_score + readability_score) / 3
    
    def _correct_structure_issues(self, content: ExtractedContent, issues: List[QualityIssue]) -> List[str]:
        """Correct structural issues in content."""
        corrections = []
        
        for issue in issues:
            if issue.issue_type == QualityIssueType.STRUCTURAL_ERROR:
                corrections.append(f"Identified structural issue: {issue.description}")
            elif issue.issue_type == QualityIssueType.READING_ORDER_ERROR:
                corrections.append(f"Reading order issue detected: {issue.description}")
        
        return corrections
    
    def _assess_export_readiness(self, quality_assessment: QualityAssessment, 
                                validation_result: ValidationResult) -> bool:
        """Assess if document is ready for export/production use."""
        # Check quality threshold
        if quality_assessment.overall_score < self.quality_threshold:
            return False
        
        # Check validation status
        if validation_result.state == ValidationState.REJECTED:
            return False
        
        # Check for critical issues
        critical_issues = [issue for issue in quality_assessment.issues 
                          if issue.severity == 'critical']
        if critical_issues:
            return False
        
        return True
    
    def _generate_comprehensive_recommendations(self, quality_assessment: QualityAssessment,
                                              validation_result: ValidationResult,
                                              content_optimization: ContentOptimization) -> List[str]:
        """Generate comprehensive recommendations for document improvement."""
        recommendations = []
        
        # Add quality assessment recommendations
        recommendations.extend(quality_assessment.recommendations)
        
        # Add validation-based recommendations
        if validation_result.state == ValidationState.NEEDS_REVIEW:
            recommendations.append("Document requires manual review before approval")
        elif validation_result.state == ValidationState.REJECTED:
            recommendations.append("Document rejected - address critical issues before reprocessing")
        
        # Add optimization recommendations
        if content_optimization.duplicate_removal_count > 0:
            recommendations.append(f"Removed {content_optimization.duplicate_removal_count} duplicate elements - check source for redundancy")
        
        if content_optimization.chunk_count > 0:
            avg_chunk_quality = sum(content_optimization.chunk_quality_scores) / len(content_optimization.chunk_quality_scores)
            if avg_chunk_quality < 0.7:
                recommendations.append("Low chunk quality detected - consider content restructuring")
        
        # Add general recommendations
        if quality_assessment.overall_score >= 0.9:
            recommendations.append("Excellent quality - ready for production use")
        elif quality_assessment.overall_score >= 0.8:
            recommendations.append("Good quality - minor improvements recommended")
        else:
            recommendations.append("Quality improvements required before production use")
        
        return recommendations
    
    def _add_processing_history(self, document: Document, processing_time: float, 
                               quality_assessment: QualityAssessment):
        """Add processing step to document history."""
        history_entry = ProcessingHistory(
            step_id=f"post_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            step_name="Post-Processing Quality Assessment",
            timestamp=datetime.now(),
            status="completed",
            duration=processing_time,
            input_data={"quality_threshold": self.quality_threshold},
            output_data={
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "issue_count": len(quality_assessment.issues)
            }
        )
        document.add_processing_step(history_entry)
    
    def _generate_metadata(self, document: Document, quality_assessment: QualityAssessment) -> Dict[str, Any]:
        """Generate comprehensive metadata for post-processing results."""
        return {
            "document_id": document.id,
            "document_type": document.document_type.value,
            "processing_timestamp": datetime.now().isoformat(),
            "quality_score": quality_assessment.overall_score,
            "quality_level": quality_assessment.quality_level.value,
            "total_issues": len(quality_assessment.issues),
            "critical_issues": len([i for i in quality_assessment.issues if i.severity == 'critical']),
            "major_issues": len([i for i in quality_assessment.issues if i.severity == 'major']),
            "minor_issues": len([i for i in quality_assessment.issues if i.severity == 'minor']),
            "assessment_metrics": quality_assessment.metrics,
            "processor_version": "1.0.0"
        }
    
    def export_results(self, result: PostProcessingResult, output_path: Path) -> bool:
        """
        Export post-processing results to file.
        
        Args:
            result: Post-processing results to export
            output_path: Path to export file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            export_data = {
                "document_id": result.document_id,
                "processing_time": result.processing_time,
                "quality_assessment": {
                    "overall_score": result.quality_assessment.overall_score,
                    "quality_level": result.quality_assessment.quality_level.value,
                    "metrics": result.quality_assessment.metrics,
                    "issues": [
                        {
                            "type": issue.issue_type.value,
                            "severity": issue.severity,
                            "description": issue.description,
                            "location": issue.location,
                            "confidence": issue.confidence,
                            "suggested_fix": issue.suggested_fix
                        }
                        for issue in result.quality_assessment.issues
                    ],
                    "recommendations": result.quality_assessment.recommendations
                },
                "validation_result": {
                    "state": result.validation_result.state.value,
                    "confidence": result.validation_result.confidence,
                    "issues_found": result.validation_result.issues_found,
                    "corrections_made": result.validation_result.corrections_made
                },
                "content_optimization": result.content_optimization,
                "export_ready": result.export_ready,
                "recommendations": result.recommendations,
                "metadata": result.metadata
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Post-processing results exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export results: {str(e)}")
            return False