"""
Quality assessment engine for TORE Matrix Labs.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import Counter

from ..config.constants import QualityLevel, QUALITY_THRESHOLDS
from ..config.settings import Settings
from .document_analyzer import DocumentElement, PageAnalysis
from .content_extractor import ExtractedContent, ExtractedTable, ExtractedImage


class QualityIssueType(Enum):
    """Types of quality issues."""
    OCR_ERROR = "ocr_error"
    FORMATTING_ERROR = "formatting_error"
    MISSING_CONTENT = "missing_content"
    CORRUPTED_TABLE = "corrupted_table"
    POOR_IMAGE_QUALITY = "poor_image_quality"
    READING_ORDER_ERROR = "reading_order_error"
    STRUCTURAL_ERROR = "structural_error"
    ENCODING_ERROR = "encoding_error"


@dataclass
class QualityIssue:
    """Represents a quality issue found in the document."""
    issue_type: QualityIssueType
    severity: str  # 'critical', 'major', 'minor'
    description: str
    location: Dict[str, Any]  # page, bbox, etc.
    confidence: float
    suggested_fix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class QualityAssessment:
    """Complete quality assessment results."""
    overall_score: float
    quality_level: QualityLevel
    issues: List[QualityIssue]
    metrics: Dict[str, float]
    recommendations: List[str]
    assessment_time: float


class QualityAssessor:
    """Quality assessment engine."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._init_quality_rules()
    
    def _init_quality_rules(self):
        """Initialize quality assessment rules."""
        # OCR quality patterns
        self.ocr_error_patterns = [
            r'[^\x00-\x7F]+',  # Non-ASCII characters that might be OCR errors
            r'[Il1|]{3,}',     # Sequences of similar characters
            r'[oO0]{3,}',      # Sequences of O/0
            r'\b[A-Z]{2,}[a-z]{2,}[A-Z]{2,}\b',  # Mixed case words
            r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\']{2,}',  # Unusual character sequences
        ]
        
        # Text quality indicators
        self.quality_indicators = {
            'min_word_length': 2,
            'max_word_length': 50,
            'min_sentence_length': 5,
            'max_sentence_length': 1000,
            'min_paragraph_length': 10,
            'max_paragraph_length': 5000,
        }
        
        # Table quality thresholds
        self.table_quality_thresholds = {
            'min_rows': 2,
            'min_columns': 2,
            'max_empty_cells_ratio': 0.3,
            'min_cell_length': 1,
        }
    
    def assess_quality(self, content: ExtractedContent, page_analyses: List[PageAnalysis]) -> QualityAssessment:
        """
        Perform comprehensive quality assessment.
        
        Args:
            content: Extracted content to assess
            page_analyses: Page analysis results
            
        Returns:
            QualityAssessment with detailed results
        """
        self.logger.info("Starting quality assessment")
        start_time = time.time()
        
        try:
            issues = []
            metrics = {}
            
            # Assess text quality
            text_issues, text_metrics = self._assess_text_quality(content.text_elements)
            issues.extend(text_issues)
            metrics.update(text_metrics)
            
            # Assess table quality
            table_issues, table_metrics = self._assess_table_quality(content.tables)
            issues.extend(table_issues)
            metrics.update(table_metrics)
            
            # Assess image quality
            image_issues, image_metrics = self._assess_image_quality(content.images)
            issues.extend(image_issues)
            metrics.update(image_metrics)
            
            # Assess structure quality
            structure_issues, structure_metrics = self._assess_structure_quality(page_analyses)
            issues.extend(structure_issues)
            metrics.update(structure_metrics)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(metrics)
            quality_level = self._determine_quality_level(overall_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(issues, metrics)
            
            assessment_time = time.time() - start_time
            
            assessment = QualityAssessment(
                overall_score=overall_score,
                quality_level=quality_level,
                issues=issues,
                metrics=metrics,
                recommendations=recommendations,
                assessment_time=assessment_time
            )
            
            self.logger.info(f"Quality assessment completed in {assessment_time:.2f}s")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {str(e)}")
            raise
    
    def _assess_text_quality(self, text_elements: List[DocumentElement]) -> Tuple[List[QualityIssue], Dict[str, float]]:
        """Assess text content quality."""
        issues = []
        metrics = {}
        
        if not text_elements:
            return issues, metrics
        
        total_text = ""
        confidence_scores = []
        word_count = 0
        sentence_count = 0
        paragraph_count = 0
        
        for element in text_elements:
            text = element.content
            total_text += text + " "
            confidence_scores.append(element.confidence)
            
            # Basic text statistics
            words = text.split()
            word_count += len(words)
            sentence_count += len(re.findall(r'[.!?]+', text))
            
            if element.element_type.value == 'paragraph':
                paragraph_count += 1
                
            # Check for OCR errors
            ocr_issues = self._detect_ocr_errors(text, element)
            issues.extend(ocr_issues)
            
            # Check for formatting issues
            format_issues = self._detect_formatting_issues(text, element)
            issues.extend(format_issues)
        
        # Calculate metrics
        metrics.update({
            'text_confidence_avg': np.mean(confidence_scores) if confidence_scores else 0.0,
            'text_confidence_min': np.min(confidence_scores) if confidence_scores else 0.0,
            'text_confidence_std': np.std(confidence_scores) if confidence_scores else 0.0,
            'total_words': word_count,
            'total_sentences': sentence_count,
            'total_paragraphs': paragraph_count,
            'avg_words_per_sentence': word_count / sentence_count if sentence_count > 0 else 0.0,
            'avg_sentences_per_paragraph': sentence_count / paragraph_count if paragraph_count > 0 else 0.0,
            'text_length': len(total_text),
            'ocr_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.OCR_ERROR]),
            'formatting_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.FORMATTING_ERROR])
        })
        
        return issues, metrics
    
    def _assess_table_quality(self, tables: List[ExtractedTable]) -> Tuple[List[QualityIssue], Dict[str, float]]:
        """Assess table extraction quality."""
        issues = []
        metrics = {}
        
        if not tables:
            return issues, metrics
        
        total_cells = 0
        empty_cells = 0
        confidence_scores = []
        
        for table in tables:
            confidence_scores.append(table.confidence)
            
            # Count cells
            for row in table.data:
                for cell in row:
                    total_cells += 1
                    if not cell or not str(cell).strip():
                        empty_cells += 1
            
            # Check table structure
            table_issues = self._detect_table_issues(table)
            issues.extend(table_issues)
        
        # Calculate metrics
        empty_cell_ratio = empty_cells / total_cells if total_cells > 0 else 0.0
        
        metrics.update({
            'table_count': len(tables),
            'table_confidence_avg': np.mean(confidence_scores) if confidence_scores else 0.0,
            'table_confidence_min': np.min(confidence_scores) if confidence_scores else 0.0,
            'total_table_cells': total_cells,
            'empty_cell_ratio': empty_cell_ratio,
            'table_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.CORRUPTED_TABLE])
        })
        
        return issues, metrics
    
    def _assess_image_quality(self, images: List[ExtractedImage]) -> Tuple[List[QualityIssue], Dict[str, float]]:
        """Assess image extraction quality."""
        issues = []
        metrics = {}
        
        if not images:
            return issues, metrics
        
        total_size = 0
        resolutions = []
        caption_count = 0
        
        for image in images:
            total_size += len(image.image_data)
            resolutions.append(image.width * image.height)
            
            if image.caption:
                caption_count += 1
            
            # Check for image quality issues
            image_issues = self._detect_image_issues(image)
            issues.extend(image_issues)
        
        # Calculate metrics
        metrics.update({
            'image_count': len(images),
            'total_image_size': total_size,
            'avg_image_size': total_size / len(images) if len(images) > 0 else 0.0,
            'avg_resolution': np.mean(resolutions) if resolutions else 0.0,
            'min_resolution': np.min(resolutions) if resolutions else 0.0,
            'caption_ratio': caption_count / len(images) if len(images) > 0 else 0.0,
            'image_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.POOR_IMAGE_QUALITY])
        })
        
        return issues, metrics
    
    def _assess_structure_quality(self, page_analyses: List[PageAnalysis]) -> Tuple[List[QualityIssue], Dict[str, float]]:
        """Assess document structure quality."""
        issues = []
        metrics = {}
        
        if not page_analyses:
            return issues, metrics
        
        quality_scores = []
        element_counts = []
        
        for page_analysis in page_analyses:
            quality_scores.append(page_analysis.quality_score)
            element_counts.append(len(page_analysis.elements))
            
            # Check reading order
            reading_order_issues = self._detect_reading_order_issues(page_analysis)
            issues.extend(reading_order_issues)
            
            # Check structure consistency
            structure_issues = self._detect_structure_issues(page_analysis)
            issues.extend(structure_issues)
        
        # Calculate metrics
        metrics.update({
            'page_count': len(page_analyses),
            'page_quality_avg': np.mean(quality_scores) if quality_scores else 0.0,
            'page_quality_min': np.min(quality_scores) if quality_scores else 0.0,
            'page_quality_std': np.std(quality_scores) if quality_scores else 0.0,
            'avg_elements_per_page': np.mean(element_counts) if element_counts else 0.0,
            'structure_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.STRUCTURAL_ERROR]),
            'reading_order_error_count': len([issue for issue in issues if issue.issue_type == QualityIssueType.READING_ORDER_ERROR])
        })
        
        return issues, metrics
    
    def _detect_ocr_errors(self, text: str, element: DocumentElement) -> List[QualityIssue]:
        """Detect OCR errors in text."""
        issues = []
        
        for pattern in self.ocr_error_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                issue = QualityIssue(
                    issue_type=QualityIssueType.OCR_ERROR,
                    severity='major',
                    description=f"Potential OCR error: '{match.group()}'",
                    location={
                        'page': element.page_number,
                        'bbox': element.bbox,
                        'text_position': match.span()
                    },
                    confidence=0.7,
                    suggested_fix="Manual review and correction required",
                    metadata={'pattern': pattern, 'match': match.group()}
                )
                issues.append(issue)
        
        return issues
    
    def _detect_formatting_issues(self, text: str, element: DocumentElement) -> List[QualityIssue]:
        """Detect formatting issues in text."""
        issues = []
        
        # Check for excessive whitespace
        if re.search(r'\s{3,}', text):
            issue = QualityIssue(
                issue_type=QualityIssueType.FORMATTING_ERROR,
                severity='minor',
                description="Excessive whitespace detected",
                location={'page': element.page_number, 'bbox': element.bbox},
                confidence=0.9,
                suggested_fix="Remove extra whitespace"
            )
            issues.append(issue)
        
        # Check for mixed encoding
        if any(ord(char) > 127 for char in text):
            issue = QualityIssue(
                issue_type=QualityIssueType.ENCODING_ERROR,
                severity='major',
                description="Non-ASCII characters detected",
                location={'page': element.page_number, 'bbox': element.bbox},
                confidence=0.8,
                suggested_fix="Check character encoding"
            )
            issues.append(issue)
        
        return issues
    
    def _detect_table_issues(self, table: ExtractedTable) -> List[QualityIssue]:
        """Detect issues in table structure."""
        issues = []
        
        # Check minimum size requirements
        if len(table.data) < self.table_quality_thresholds['min_rows']:
            issue = QualityIssue(
                issue_type=QualityIssueType.CORRUPTED_TABLE,
                severity='major',
                description=f"Table has only {len(table.data)} rows (minimum: {self.table_quality_thresholds['min_rows']})",
                location={'page': table.page_number, 'bbox': table.bbox},
                confidence=0.9,
                suggested_fix="Verify table extraction accuracy"
            )
            issues.append(issue)
        
        # Check for too many empty cells
        if table.data:
            total_cells = sum(len(row) for row in table.data)
            empty_cells = sum(1 for row in table.data for cell in row if not cell or not str(cell).strip())
            empty_ratio = empty_cells / total_cells if total_cells > 0 else 0
            
            if empty_ratio > self.table_quality_thresholds['max_empty_cells_ratio']:
                issue = QualityIssue(
                    issue_type=QualityIssueType.CORRUPTED_TABLE,
                    severity='major',
                    description=f"Table has {empty_ratio:.1%} empty cells (threshold: {self.table_quality_thresholds['max_empty_cells_ratio']:.1%})",
                    location={'page': table.page_number, 'bbox': table.bbox},
                    confidence=0.8,
                    suggested_fix="Review table structure and fill missing data"
                )
                issues.append(issue)
        
        return issues
    
    def _detect_image_issues(self, image: ExtractedImage) -> List[QualityIssue]:
        """Detect issues in image extraction."""
        issues = []
        
        # Check resolution
        resolution = image.width * image.height
        if resolution < 10000:  # Less than 100x100 pixels
            issue = QualityIssue(
                issue_type=QualityIssueType.POOR_IMAGE_QUALITY,
                severity='major',
                description=f"Low resolution image: {image.width}x{image.height}",
                location={'page': image.page_number, 'bbox': image.bbox},
                confidence=0.9,
                suggested_fix="Consider higher resolution source"
            )
            issues.append(issue)
        
        # Check for missing caption
        if not image.caption:
            issue = QualityIssue(
                issue_type=QualityIssueType.MISSING_CONTENT,
                severity='minor',
                description="Image has no caption",
                location={'page': image.page_number, 'bbox': image.bbox},
                confidence=0.6,
                suggested_fix="Add descriptive caption"
            )
            issues.append(issue)
        
        return issues
    
    def _detect_reading_order_issues(self, page_analysis: PageAnalysis) -> List[QualityIssue]:
        """Detect reading order issues."""
        issues = []
        
        # Simple check for unusual reading order
        if len(page_analysis.reading_order) != len(page_analysis.elements):
            issue = QualityIssue(
                issue_type=QualityIssueType.READING_ORDER_ERROR,
                severity='major',
                description="Reading order mismatch with elements",
                location={'page': page_analysis.page_number},
                confidence=0.9,
                suggested_fix="Recalculate reading order"
            )
            issues.append(issue)
        
        return issues
    
    def _detect_structure_issues(self, page_analysis: PageAnalysis) -> List[QualityIssue]:
        """Detect document structure issues."""
        issues = []
        
        # Check for pages with no content
        if not page_analysis.elements:
            issue = QualityIssue(
                issue_type=QualityIssueType.MISSING_CONTENT,
                severity='critical',
                description="Page has no extractable content",
                location={'page': page_analysis.page_number},
                confidence=0.95,
                suggested_fix="Check source document quality"
            )
            issues.append(issue)
        
        return issues
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall quality score."""
        score_components = []
        
        # Text quality component
        if 'text_confidence_avg' in metrics:
            text_score = metrics['text_confidence_avg']
            
            # Penalize for errors
            if 'ocr_error_count' in metrics and metrics['total_words'] > 0:
                error_penalty = min(metrics['ocr_error_count'] / metrics['total_words'], 0.5)
                text_score *= (1 - error_penalty)
            
            score_components.append(text_score)
        
        # Table quality component
        if 'table_confidence_avg' in metrics:
            table_score = metrics['table_confidence_avg']
            
            # Penalize for high empty cell ratio
            if 'empty_cell_ratio' in metrics:
                empty_penalty = metrics['empty_cell_ratio'] * 0.5
                table_score *= (1 - empty_penalty)
            
            score_components.append(table_score)
        
        # Page quality component
        if 'page_quality_avg' in metrics:
            score_components.append(metrics['page_quality_avg'])
        
        # Calculate weighted average
        if score_components:
            return sum(score_components) / len(score_components)
        else:
            return 0.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        for level, threshold in QUALITY_THRESHOLDS.items():
            if score >= threshold:
                return level
        return QualityLevel.UNACCEPTABLE
    
    def _generate_recommendations(self, issues: List[QualityIssue], metrics: Dict[str, float]) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []
        
        # Group issues by type
        issue_counts = Counter(issue.issue_type for issue in issues)
        
        # OCR error recommendations
        if issue_counts[QualityIssueType.OCR_ERROR] > 0:
            recommendations.append(f"Found {issue_counts[QualityIssueType.OCR_ERROR]} OCR errors. Consider using higher quality OCR or manual correction.")
        
        # Table error recommendations
        if issue_counts[QualityIssueType.CORRUPTED_TABLE] > 0:
            recommendations.append(f"Found {issue_counts[QualityIssueType.CORRUPTED_TABLE]} table issues. Review table extraction settings.")
        
        # Image quality recommendations
        if issue_counts[QualityIssueType.POOR_IMAGE_QUALITY] > 0:
            recommendations.append(f"Found {issue_counts[QualityIssueType.POOR_IMAGE_QUALITY]} image quality issues. Consider higher resolution sources.")
        
        # Overall quality recommendations
        if metrics.get('text_confidence_avg', 0) < 0.8:
            recommendations.append("Low text confidence detected. Consider re-processing with different extraction settings.")
        
        if metrics.get('empty_cell_ratio', 0) > 0.2:
            recommendations.append("High empty cell ratio in tables. Review table structure and data completeness.")
        
        return recommendations


import time  # Import missing