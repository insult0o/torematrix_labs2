#!/usr/bin/env python3
"""
Content validation and correction engine for TORE Matrix Labs.
Provides enterprise-grade content validation with correction suggestions.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import difflib
import re

from ..config.constants import ValidationState, QualityLevel
from ..config.settings import Settings
from ..models.document_models import Document, ValidationResult, DocumentAnnotation
from .quality_assessor import QualityIssue, QualityIssueType
from .content_extractor import ExtractedContent, DocumentElement


class CorrectionType(Enum):
    """Types of content corrections."""
    OCR_CORRECTION = "ocr_correction"
    FORMATTING_FIX = "formatting_fix"
    SPELLING_CORRECTION = "spelling_correction"
    GRAMMAR_CORRECTION = "grammar_correction"
    STRUCTURE_IMPROVEMENT = "structure_improvement"
    CONTENT_ENHANCEMENT = "content_enhancement"
    METADATA_UPDATE = "metadata_update"


class CorrectionStatus(Enum):
    """Status of content corrections."""
    SUGGESTED = "suggested"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class ContentCorrection:
    """Represents a suggested content correction."""
    id: str
    correction_type: CorrectionType
    element_id: str
    page_number: int
    bbox: Optional[Tuple[float, float, float, float]]
    original_content: str
    suggested_content: str
    confidence: float
    reasoning: str
    status: CorrectionStatus = CorrectionStatus.SUGGESTED
    reviewer_id: Optional[str] = None
    review_date: Optional[datetime] = None
    review_notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationSession:
    """Represents a content validation session."""
    id: str
    document_id: str
    validator_id: str
    session_start: datetime
    session_end: Optional[datetime] = None
    total_issues_reviewed: int = 0
    corrections_applied: int = 0
    corrections_rejected: int = 0
    validation_notes: str = ""
    final_decision: Optional[ValidationState] = None
    confidence_score: float = 0.0


@dataclass
class ValidationMetrics:
    """Validation performance metrics."""
    total_elements_reviewed: int
    issues_identified: int
    corrections_suggested: int
    corrections_applied: int
    average_confidence: float
    review_time_seconds: float
    validator_efficiency: float


class ContentValidator:
    """
    Enterprise-grade content validation and correction engine.
    Provides intelligent correction suggestions and validation workflows.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Validation configuration
        self.confidence_threshold = 0.7
        self.max_corrections_per_element = 5
        self.auto_apply_threshold = 0.95
        
        # Initialize correction engines
        self._init_correction_engines()
        
        self.logger.info("Content validator initialized")
    
    def _init_correction_engines(self):
        """Initialize various correction engines."""
        # OCR correction patterns
        self.ocr_corrections = {
            # Common OCR misreadings
            'rn': 'm',
            'cl': 'd',
            '0': 'O',  # Zero to letter O
            '1': 'I',  # One to letter I
            '5': 'S',  # Five to letter S
            # Add more patterns as needed
        }
        
        # Aviation/ICAO-specific terminology corrections
        self.aviation_terminology = {
            'aircraf': 'aircraft',
            'airpot': 'airport',
            'navagation': 'navigation',
            'comunication': 'communication',
            'aproach': 'approach',
            'departue': 'departure',
            # Add ICAO-specific terms
        }
        
        # Common spelling corrections
        self.spelling_corrections = {
            'teh': 'the',
            'recieve': 'receive',
            'seperate': 'separate',
            'occured': 'occurred',
            'recomend': 'recommend',
        }
    
    def validate_content(self, document: Document, extracted_content: ExtractedContent,
                        quality_issues: List[QualityIssue], validator_id: str) -> ValidationSession:
        """
        Perform comprehensive content validation with correction suggestions.
        
        Args:
            document: Document being validated
            extracted_content: Extracted content to validate
            quality_issues: Issues identified by quality assessment
            validator_id: ID of the validator performing review
            
        Returns:
            ValidationSession with results and corrections
        """
        self.logger.info(f"Starting content validation for document: {document.id}")
        
        session = ValidationSession(
            id=f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            document_id=document.id,
            validator_id=validator_id,
            session_start=datetime.now()
        )
        
        try:
            # Phase 1: Analyze quality issues and generate corrections
            corrections = self._generate_corrections_from_issues(
                extracted_content, quality_issues
            )
            
            # Phase 2: Content-based validation and additional corrections
            content_corrections = self._validate_content_accuracy(
                extracted_content, document.document_type
            )
            corrections.extend(content_corrections)
            
            # Phase 3: Apply high-confidence corrections automatically
            auto_applied = self._apply_automatic_corrections(
                extracted_content, corrections
            )
            session.corrections_applied = len(auto_applied)
            
            # Phase 4: Generate validation report
            metrics = self._calculate_validation_metrics(
                extracted_content, corrections, session.session_start
            )
            
            # Update session
            session.session_end = datetime.now()
            session.total_issues_reviewed = len(quality_issues)
            session.corrections_rejected = len([c for c in corrections if c.status == CorrectionStatus.REJECTED])
            session.confidence_score = metrics.average_confidence
            
            # Determine validation decision
            session.final_decision = self._make_validation_decision(
                document, corrections, metrics
            )
            
            # Store corrections in document
            self._store_corrections_in_document(document, corrections, session)
            
            self.logger.info(f"Content validation completed: {len(corrections)} corrections generated")
            return session
            
        except Exception as e:
            self.logger.error(f"Content validation failed: {str(e)}")
            session.session_end = datetime.now()
            session.final_decision = ValidationState.REJECTED
            raise
    
    def _generate_corrections_from_issues(self, content: ExtractedContent,
                                         issues: List[QualityIssue]) -> List[ContentCorrection]:
        """Generate corrections based on quality issues."""
        corrections = []
        
        for issue in issues:
            if issue.issue_type == QualityIssueType.OCR_ERROR:
                ocr_corrections = self._suggest_ocr_corrections(issue, content)
                corrections.extend(ocr_corrections)
            
            elif issue.issue_type == QualityIssueType.FORMATTING_ERROR:
                format_corrections = self._suggest_formatting_corrections(issue, content)
                corrections.extend(format_corrections)
            
            elif issue.issue_type == QualityIssueType.ENCODING_ERROR:
                encoding_corrections = self._suggest_encoding_corrections(issue, content)
                corrections.extend(encoding_corrections)
        
        return corrections
    
    def _suggest_ocr_corrections(self, issue: QualityIssue, 
                               content: ExtractedContent) -> List[ContentCorrection]:
        """Suggest OCR-specific corrections."""
        corrections = []
        
        # Find the element containing the OCR error
        target_element = self._find_element_by_location(content, issue.location)
        if not target_element:
            return corrections
        
        original_text = target_element.content
        suggested_text = original_text
        
        # Apply OCR correction patterns
        for error_pattern, correction in self.ocr_corrections.items():
            if error_pattern in original_text:
                suggested_text = suggested_text.replace(error_pattern, correction)
        
        # Apply aviation terminology corrections
        for error_term, correct_term in self.aviation_terminology.items():
            if error_term.lower() in original_text.lower():
                suggested_text = re.sub(
                    re.escape(error_term), correct_term, 
                    suggested_text, flags=re.IGNORECASE
                )
        
        if suggested_text != original_text:
            correction = ContentCorrection(
                id=f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(corrections)}",
                correction_type=CorrectionType.OCR_CORRECTION,
                element_id=getattr(target_element, 'id', 'unknown'),
                page_number=target_element.page_number,
                bbox=target_element.bbox,
                original_content=original_text,
                suggested_content=suggested_text,
                confidence=0.8,
                reasoning=f"OCR error correction based on pattern matching: {issue.description}"
            )
            corrections.append(correction)
        
        return corrections
    
    def _suggest_formatting_corrections(self, issue: QualityIssue,
                                      content: ExtractedContent) -> List[ContentCorrection]:
        """Suggest formatting corrections."""
        corrections = []
        
        target_element = self._find_element_by_location(content, issue.location)
        if not target_element:
            return corrections
        
        original_text = target_element.content
        suggested_text = original_text
        
        # Fix excessive whitespace
        if "whitespace" in issue.description.lower():
            suggested_text = re.sub(r'\s+', ' ', suggested_text).strip()
        
        # Fix line breaks
        suggested_text = suggested_text.replace('\n\n\n', '\n\n')
        
        if suggested_text != original_text:
            correction = ContentCorrection(
                id=f"format_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(corrections)}",
                correction_type=CorrectionType.FORMATTING_FIX,
                element_id=getattr(target_element, 'id', 'unknown'),
                page_number=target_element.page_number,
                bbox=target_element.bbox,
                original_content=original_text,
                suggested_content=suggested_text,
                confidence=0.9,
                reasoning=f"Formatting correction: {issue.description}"
            )
            corrections.append(correction)
        
        return corrections
    
    def _suggest_encoding_corrections(self, issue: QualityIssue,
                                    content: ExtractedContent) -> List[ContentCorrection]:
        """Suggest encoding corrections."""
        corrections = []
        
        target_element = self._find_element_by_location(content, issue.location)
        if not target_element:
            return corrections
        
        original_text = target_element.content
        
        # Common encoding fixes
        encoding_fixes = {
            'â€™': "'",  # Smart apostrophe
            'â€œ': '"',  # Smart quote open
            'â€�': '"',  # Smart quote close
            'â€"': '–',  # En dash
            'â€"': '—',  # Em dash
        }
        
        suggested_text = original_text
        for wrong, right in encoding_fixes.items():
            suggested_text = suggested_text.replace(wrong, right)
        
        if suggested_text != original_text:
            correction = ContentCorrection(
                id=f"encoding_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(corrections)}",
                correction_type=CorrectionType.FORMATTING_FIX,
                element_id=getattr(target_element, 'id', 'unknown'),
                page_number=target_element.page_number,
                bbox=target_element.bbox,
                original_content=original_text,
                suggested_content=suggested_text,
                confidence=0.95,
                reasoning="Fixed character encoding issues"
            )
            corrections.append(correction)
        
        return corrections
    
    def _validate_content_accuracy(self, content: ExtractedContent,
                                 document_type) -> List[ContentCorrection]:
        """Validate content accuracy and suggest improvements."""
        corrections = []
        
        # Spell checking
        for element in content.text_elements:
            spelling_corrections = self._check_spelling(element)
            corrections.extend(spelling_corrections)
        
        # Aviation-specific validation
        if document_type.value == 'icao':
            aviation_corrections = self._validate_aviation_content(content)
            corrections.extend(aviation_corrections)
        
        return corrections
    
    def _check_spelling(self, element: DocumentElement) -> List[ContentCorrection]:
        """Check spelling and suggest corrections."""
        corrections = []
        words = element.content.split()
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word in self.spelling_corrections:
                suggested_word = self.spelling_corrections[clean_word]
                
                correction = ContentCorrection(
                    id=f"spell_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(corrections)}",
                    correction_type=CorrectionType.SPELLING_CORRECTION,
                    element_id=getattr(element, 'id', 'unknown'),
                    page_number=element.page_number,
                    bbox=element.bbox,
                    original_content=word,
                    suggested_content=suggested_word,
                    confidence=0.85,
                    reasoning=f"Spelling correction: '{clean_word}' -> '{suggested_word}'"
                )
                corrections.append(correction)
        
        return corrections
    
    def _validate_aviation_content(self, content: ExtractedContent) -> List[ContentCorrection]:
        """Validate aviation-specific content."""
        corrections = []
        
        # Check for proper ICAO terminology usage
        full_text = " ".join([elem.content for elem in content.text_elements])
        
        # Validate ICAO standard phrases
        icao_standards = {
            'acknowledge': 'affirm',
            'okay': 'affirm',
            'yes': 'affirm',
            'no': 'negative',
        }
        
        for informal, formal in icao_standards.items():
            if informal in full_text.lower():
                # This would need more sophisticated context analysis
                pass
        
        return corrections
    
    def _apply_automatic_corrections(self, content: ExtractedContent,
                                   corrections: List[ContentCorrection]) -> List[ContentCorrection]:
        """Apply high-confidence corrections automatically."""
        auto_applied = []
        
        for correction in corrections:
            if (correction.confidence >= self.auto_apply_threshold and 
                correction.correction_type in [CorrectionType.FORMATTING_FIX, 
                                             CorrectionType.SPELLING_CORRECTION]):
                
                # Find and update the element
                target_element = self._find_element_by_id(content, correction.element_id)
                if target_element:
                    target_element.content = target_element.content.replace(
                        correction.original_content, 
                        correction.suggested_content
                    )
                    correction.status = CorrectionStatus.APPLIED
                    auto_applied.append(correction)
                    
                    self.logger.info(f"Auto-applied correction: {correction.id}")
        
        return auto_applied
    
    def _find_element_by_location(self, content: ExtractedContent, 
                                 location: Dict[str, Any]) -> Optional[DocumentElement]:
        """Find element by location information."""
        page_num = location.get('page', 0)
        bbox = location.get('bbox')
        
        for element in content.text_elements:
            if (element.page_number == page_num and 
                bbox and element.bbox == bbox):
                return element
        
        return None
    
    def _find_element_by_id(self, content: ExtractedContent, element_id: str) -> Optional[DocumentElement]:
        """Find element by ID."""
        for element in content.text_elements:
            if getattr(element, 'id', 'unknown') == element_id:
                return element
        return None
    
    def _calculate_validation_metrics(self, content: ExtractedContent,
                                    corrections: List[ContentCorrection],
                                    start_time: datetime) -> ValidationMetrics:
        """Calculate validation performance metrics."""
        review_time = (datetime.now() - start_time).total_seconds()
        
        total_elements = len(content.text_elements)
        issues_identified = len(corrections)
        corrections_applied = len([c for c in corrections if c.status == CorrectionStatus.APPLIED])
        
        average_confidence = (sum(c.confidence for c in corrections) / len(corrections) 
                            if corrections else 0.0)
        
        # Validator efficiency: corrections per minute
        efficiency = (corrections_applied / (review_time / 60)) if review_time > 0 else 0.0
        
        return ValidationMetrics(
            total_elements_reviewed=total_elements,
            issues_identified=issues_identified,
            corrections_suggested=len(corrections),
            corrections_applied=corrections_applied,
            average_confidence=average_confidence,
            review_time_seconds=review_time,
            validator_efficiency=efficiency
        )
    
    def _make_validation_decision(self, document: Document, corrections: List[ContentCorrection],
                                metrics: ValidationMetrics) -> ValidationState:
        """Make final validation decision based on corrections and metrics."""
        # Calculate correction impact
        total_corrections = len(corrections)
        high_confidence_corrections = len([c for c in corrections if c.confidence >= 0.8])
        applied_corrections = len([c for c in corrections if c.status == CorrectionStatus.APPLIED])
        
        # Decision logic
        if total_corrections == 0:
            return ValidationState.APPROVED
        
        correction_ratio = applied_corrections / total_corrections if total_corrections > 0 else 0
        
        if correction_ratio >= 0.8 and metrics.average_confidence >= 0.8:
            return ValidationState.APPROVED
        elif correction_ratio >= 0.5:
            return ValidationState.NEEDS_REVIEW
        else:
            return ValidationState.REJECTED
    
    def _store_corrections_in_document(self, document: Document, 
                                     corrections: List[ContentCorrection],
                                     session: ValidationSession):
        """Store corrections and validation results in document."""
        # Create validation result
        validation_result = ValidationResult(
            validator_id=session.validator_id,
            validation_date=session.session_start,
            state=session.final_decision,
            confidence=session.confidence_score,
            notes=f"Validation session {session.id}: {len(corrections)} corrections generated",
            issues_found=[
                f"{c.correction_type.value}: {c.reasoning}" 
                for c in corrections if c.status != CorrectionStatus.APPLIED
            ],
            corrections_made=[
                f"{c.correction_type.value}: {c.original_content} -> {c.suggested_content}"
                for c in corrections if c.status == CorrectionStatus.APPLIED
            ]
        )
        
        document.add_validation_result(validation_result)
        
        # Store corrections as annotations
        for correction in corrections:
            annotation = DocumentAnnotation(
                id=correction.id,
                document_id=document.id,
                page_number=correction.page_number,
                bbox=correction.bbox or (0, 0, 0, 0),
                annotation_type="correction",
                content=f"{correction.correction_type.value}: {correction.suggested_content}",
                created_by=session.validator_id,
                resolved=(correction.status == CorrectionStatus.APPLIED)
            )
            
            # Add to document custom metadata
            if 'corrections' not in document.custom_metadata:
                document.custom_metadata['corrections'] = []
            
            document.custom_metadata['corrections'].append({
                'id': correction.id,
                'type': correction.correction_type.value,
                'confidence': correction.confidence,
                'status': correction.status.value,
                'reasoning': correction.reasoning
            })
    
    def get_validation_summary(self, document: Document) -> Dict[str, Any]:
        """Get comprehensive validation summary for a document."""
        latest_validation = document.get_latest_validation()
        corrections = document.custom_metadata.get('corrections', [])
        
        if not latest_validation:
            return {'status': 'not_validated'}
        
        summary = {
            'validation_state': latest_validation.state.value,
            'confidence': latest_validation.confidence,
            'validation_date': latest_validation.validation_date.isoformat(),
            'total_corrections': len(corrections),
            'applied_corrections': len([c for c in corrections if c['status'] == 'applied']),
            'pending_corrections': len([c for c in corrections if c['status'] in ['suggested', 'pending_review']]),
            'correction_types': {},
            'issues_found': latest_validation.issues_found,
            'corrections_made': latest_validation.corrections_made,
            'recommendations': []
        }
        
        # Group corrections by type
        for correction in corrections:
            corr_type = correction['type']
            if corr_type not in summary['correction_types']:
                summary['correction_types'][corr_type] = 0
            summary['correction_types'][corr_type] += 1
        
        # Generate recommendations
        if latest_validation.state == ValidationState.NEEDS_REVIEW:
            summary['recommendations'].append("Manual review required for pending corrections")
        elif latest_validation.state == ValidationState.REJECTED:
            summary['recommendations'].append("Document requires significant corrections before approval")
        elif latest_validation.state == ValidationState.APPROVED:
            summary['recommendations'].append("Document approved for production use")
        
        return summary


def create_validation_workflow(settings: Settings) -> ContentValidator:
    """Factory function to create configured content validator."""
    return ContentValidator(settings)