#!/usr/bin/env python3
"""
Special area validation system for text formatting, positioning, and reading order.
Validates extracted content from specialized toolsets before integration.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import re
import time
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from ...config.settings import Settings

# Optional libraries for advanced validation
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    type: str
    severity: ValidationSeverity
    message: str
    location: Dict[str, Any]
    suggestion: str = ""
    auto_fixable: bool = False


class SpecialAreaValidator:
    """Validates special areas for text formatting, positioning, and reading order."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Validation rules and thresholds
        self.validation_rules = {
            'text_formatting': {
                'font_consistency': True,
                'spacing_consistency': True,
                'alignment_validation': True,
                'line_height_validation': True,
                'text_overflow_detection': True
            },
            'positioning': {
                'coordinate_validation': True,
                'boundary_checking': True,
                'overlap_detection': True,
                'alignment_checking': True,
                'spacing_validation': True
            },
            'reading_order': {
                'sequence_validation': True,
                'flow_analysis': True,
                'column_order_checking': True,
                'section_hierarchy': True,
                'navigation_validation': True
            }
        }
        
        # Validation thresholds
        self.thresholds = {
            'font_size_variance': 2.0,  # Maximum allowed font size variance
            'line_spacing_variance': 0.3,  # Maximum line spacing variance
            'alignment_tolerance': 5.0,  # Pixel tolerance for alignment
            'overlap_threshold': 0.1,  # Minimum overlap to consider significant
            'reading_order_confidence': 0.8  # Minimum confidence for reading order
        }
        
        # Metrics tracking
        self.metrics = {
            'validations_performed': 0,
            'issues_found': 0,
            'auto_fixes_applied': 0,
            'validation_time': 0.0
        }
        
        self.logger.info("Special area validator initialized")
    
    def validate_special_area(self, area_data: Dict, extraction_result: Dict, 
                            pdf_document: fitz.Document) -> Dict:
        """Validate a special area extraction result."""
        start_time = time.time()
        
        try:
            self.metrics['validations_performed'] += 1
            
            # Initialize validation result
            validation_result = {
                'success': True,
                'area_id': area_data.get('id', 'unknown'),
                'area_type': area_data.get('type', 'unknown'),
                'issues': [],
                'quality_score': 0.0,
                'confidence': 0.0,
                'auto_fixes': [],
                'recommendations': []
            }
            
            # Skip validation if extraction failed
            if not extraction_result.get('success'):
                validation_result['success'] = False
                validation_result['issues'].append(
                    ValidationIssue(
                        type="extraction_failure",
                        severity=ValidationSeverity.CRITICAL,
                        message="Cannot validate - extraction failed",
                        location=area_data.get('bbox', [0, 0, 0, 0])
                    )
                )
                return validation_result
            
            # Perform validation based on area type
            area_type = area_data.get('type', '').upper()
            
            if area_type == 'TABLE':
                self._validate_table_area(area_data, extraction_result, pdf_document, validation_result)
            elif area_type == 'IMAGE':
                self._validate_image_area(area_data, extraction_result, pdf_document, validation_result)
            elif area_type == 'DIAGRAM':
                self._validate_diagram_area(area_data, extraction_result, pdf_document, validation_result)
            elif area_type == 'CHART':
                self._validate_chart_area(area_data, extraction_result, pdf_document, validation_result)
            elif area_type == 'COMPLEX':
                self._validate_complex_area(area_data, extraction_result, pdf_document, validation_result)
            else:
                self._validate_generic_area(area_data, extraction_result, pdf_document, validation_result)
            
            # Calculate overall quality score
            validation_result['quality_score'] = self._calculate_quality_score(validation_result)
            validation_result['confidence'] = extraction_result.get('confidence_score', 0.0)
            
            # Apply auto-fixes if enabled
            if self.settings.get('auto_fix_enabled', False):
                self._apply_auto_fixes(validation_result, extraction_result)
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_recommendations(validation_result)
            
            # Update metrics
            self.metrics['issues_found'] += len(validation_result['issues'])
            self.metrics['validation_time'] += time.time() - start_time
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Special area validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'area_id': area_data.get('id', 'unknown'),
                'area_type': area_data.get('type', 'unknown'),
                'issues': [],
                'quality_score': 0.0,
                'validation_time': time.time() - start_time
            }
    
    def _validate_table_area(self, area_data: Dict, extraction_result: Dict, 
                           pdf_document: fitz.Document, validation_result: Dict):
        """Validate table area specifics."""
        try:
            structured_content = extraction_result.get('structured_content', {})
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            # Text formatting validation
            self._validate_table_formatting(headers, rows, area_data, validation_result)
            
            # Positioning validation
            self._validate_table_positioning(area_data, pdf_document, validation_result)
            
            # Reading order validation
            self._validate_table_reading_order(headers, rows, area_data, validation_result)
            
            # Table-specific validations
            self._validate_table_structure(headers, rows, validation_result)
            
        except Exception as e:
            self.logger.error(f"Table validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="table_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Table validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_image_area(self, area_data: Dict, extraction_result: Dict, 
                           pdf_document: fitz.Document, validation_result: Dict):
        """Validate image area specifics."""
        try:
            content = extraction_result.get('content', {})
            
            # Text formatting validation (for extracted text)
            text_extraction = content.get('extracted_text', {})
            if text_extraction.get('text'):
                self._validate_image_text_formatting(text_extraction, area_data, validation_result)
            
            # Positioning validation
            self._validate_image_positioning(area_data, pdf_document, validation_result)
            
            # Image-specific validations
            self._validate_image_quality(content, validation_result)
            
        except Exception as e:
            self.logger.error(f"Image validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="image_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Image validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_diagram_area(self, area_data: Dict, extraction_result: Dict, 
                             pdf_document: fitz.Document, validation_result: Dict):
        """Validate diagram area specifics."""
        try:
            content = extraction_result.get('content', {})
            
            # Positioning validation
            self._validate_diagram_positioning(area_data, pdf_document, validation_result)
            
            # Reading order validation for diagram elements
            self._validate_diagram_reading_order(content, area_data, validation_result)
            
            # Diagram-specific validations
            self._validate_diagram_structure(content, validation_result)
            
        except Exception as e:
            self.logger.error(f"Diagram validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="diagram_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Diagram validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_chart_area(self, area_data: Dict, extraction_result: Dict, 
                           pdf_document: fitz.Document, validation_result: Dict):
        """Validate chart area specifics."""
        try:
            content = extraction_result.get('content', {})
            
            # Positioning validation
            self._validate_chart_positioning(area_data, pdf_document, validation_result)
            
            # Chart-specific validations
            self._validate_chart_data_integrity(content, validation_result)
            
        except Exception as e:
            self.logger.error(f"Chart validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="chart_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Chart validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_complex_area(self, area_data: Dict, extraction_result: Dict, 
                             pdf_document: fitz.Document, validation_result: Dict):
        """Validate complex area specifics."""
        try:
            content = extraction_result.get('content', {})
            
            # Text formatting validation
            self._validate_complex_text_formatting(content, area_data, validation_result)
            
            # Positioning validation
            self._validate_complex_positioning(area_data, pdf_document, validation_result)
            
            # Reading order validation
            self._validate_complex_reading_order(content, area_data, validation_result)
            
        except Exception as e:
            self.logger.error(f"Complex area validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="complex_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Complex area validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_generic_area(self, area_data: Dict, extraction_result: Dict, 
                             pdf_document: fitz.Document, validation_result: Dict):
        """Validate generic area."""
        try:
            # Basic positioning validation
            self._validate_basic_positioning(area_data, pdf_document, validation_result)
            
            # Basic content validation
            content = extraction_result.get('content', {})
            if content:
                self._validate_basic_content(content, validation_result)
            
        except Exception as e:
            self.logger.error(f"Generic validation failed: {e}")
            validation_result['issues'].append(
                ValidationIssue(
                    type="generic_validation_error",
                    severity=ValidationSeverity.MAJOR,
                    message=f"Generic validation failed: {str(e)}",
                    location=area_data.get('bbox', [0, 0, 0, 0])
                )
            )
    
    def _validate_table_formatting(self, headers: List, rows: List, 
                                 area_data: Dict, validation_result: Dict):
        """Validate table text formatting."""
        try:
            # Check header consistency
            if headers:
                header_lengths = [len(str(h)) for h in headers]
                if max(header_lengths) - min(header_lengths) > 20:
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="table_header_inconsistency",
                            severity=ValidationSeverity.MINOR,
                            message="Table headers have inconsistent lengths",
                            location=area_data.get('bbox', [0, 0, 0, 0]),
                            suggestion="Consider standardizing header text lengths",
                            auto_fixable=True
                        )
                    )
            
            # Check row consistency
            if rows:
                row_lengths = [len(row) for row in rows]
                expected_length = len(headers) if headers else max(row_lengths)
                
                inconsistent_rows = [i for i, row in enumerate(rows) 
                                   if len(row) != expected_length]
                
                if inconsistent_rows:
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="table_row_inconsistency",
                            severity=ValidationSeverity.MAJOR,
                            message=f"Table has {len(inconsistent_rows)} rows with inconsistent column count",
                            location=area_data.get('bbox', [0, 0, 0, 0]),
                            suggestion="Standardize column count across all rows",
                            auto_fixable=True
                        )
                    )
            
        except Exception as e:
            self.logger.error(f"Table formatting validation failed: {e}")
    
    def _validate_table_positioning(self, area_data: Dict, pdf_document: fitz.Document, 
                                  validation_result: Dict):
        """Validate table positioning."""
        try:
            bbox = area_data.get('bbox', [0, 0, 0, 0])
            page_num = area_data.get('page', 1) - 1
            
            # Check if table is within page bounds
            if page_num < len(pdf_document):
                page = pdf_document[page_num]
                page_rect = page.rect
                
                if (bbox[0] < 0 or bbox[1] < 0 or 
                    bbox[2] > page_rect.width or bbox[3] > page_rect.height):
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="table_position_out_of_bounds",
                            severity=ValidationSeverity.MAJOR,
                            message="Table extends beyond page boundaries",
                            location=bbox,
                            suggestion="Adjust table boundaries to fit within page"
                        )
                    )
            
            # Check table aspect ratio
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            if width > 0 and height > 0:
                aspect_ratio = width / height
                if aspect_ratio > 10 or aspect_ratio < 0.1:
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="table_unusual_aspect_ratio",
                            severity=ValidationSeverity.MINOR,
                            message=f"Table has unusual aspect ratio: {aspect_ratio:.2f}",
                            location=bbox,
                            suggestion="Verify table boundaries are correctly defined"
                        )
                    )
            
        except Exception as e:
            self.logger.error(f"Table positioning validation failed: {e}")
    
    def _validate_table_reading_order(self, headers: List, rows: List, 
                                    area_data: Dict, validation_result: Dict):
        """Validate table reading order."""
        try:
            # Check if headers are present and logical
            if not headers and rows:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="table_missing_headers",
                        severity=ValidationSeverity.MINOR,
                        message="Table appears to be missing headers",
                        location=area_data.get('bbox', [0, 0, 0, 0]),
                        suggestion="Consider adding column headers for better readability"
                    )
                )
            
            # Check for logical data flow in rows
            if rows and len(rows) > 1:
                # Simple heuristic: check if first column has sequential or logical order
                first_column = [row[0] if row else '' for row in rows]
                numeric_values = []
                
                for value in first_column:
                    try:
                        numeric_values.append(float(str(value)))
                    except (ValueError, TypeError):
                        break
                
                # Check if numeric values are in order
                if len(numeric_values) > 2:
                    is_ascending = all(numeric_values[i] <= numeric_values[i+1] 
                                     for i in range(len(numeric_values)-1))
                    is_descending = all(numeric_values[i] >= numeric_values[i+1] 
                                      for i in range(len(numeric_values)-1))
                    
                    if not (is_ascending or is_descending):
                        validation_result['issues'].append(
                            ValidationIssue(
                                type="table_reading_order_unclear",
                                severity=ValidationSeverity.INFO,
                                message="Table data order may not be optimal for reading",
                                location=area_data.get('bbox', [0, 0, 0, 0]),
                                suggestion="Consider organizing data in logical sequence"
                            )
                        )
            
        except Exception as e:
            self.logger.error(f"Table reading order validation failed: {e}")
    
    def _validate_table_structure(self, headers: List, rows: List, validation_result: Dict):
        """Validate table structure integrity."""
        try:
            # Check for empty table
            if not headers and not rows:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="table_empty",
                        severity=ValidationSeverity.CRITICAL,
                        message="Table contains no data",
                        location={},
                        suggestion="Verify table extraction parameters"
                    )
                )
                return
            
            # Check for excessive empty cells
            if rows:
                total_cells = sum(len(row) for row in rows)
                empty_cells = sum(1 for row in rows for cell in row 
                                if not str(cell).strip())
                
                if total_cells > 0:
                    empty_ratio = empty_cells / total_cells
                    if empty_ratio > 0.5:
                        validation_result['issues'].append(
                            ValidationIssue(
                                type="table_excessive_empty_cells",
                                severity=ValidationSeverity.MAJOR,
                                message=f"Table has {empty_ratio:.1%} empty cells",
                                location={},
                                suggestion="Verify table extraction accuracy",
                                auto_fixable=True
                            )
                        )
            
        except Exception as e:
            self.logger.error(f"Table structure validation failed: {e}")
    
    def _validate_image_text_formatting(self, text_extraction: Dict, 
                                      area_data: Dict, validation_result: Dict):
        """Validate formatting of text extracted from images."""
        try:
            text = text_extraction.get('text', '')
            confidence = text_extraction.get('confidence', 0)
            
            # Check OCR confidence
            if confidence < 70:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="image_low_ocr_confidence",
                        severity=ValidationSeverity.MAJOR,
                        message=f"OCR confidence is low: {confidence:.1f}%",
                        location=area_data.get('bbox', [0, 0, 0, 0]),
                        suggestion="Consider image enhancement or manual verification"
                    )
                )
            
            # Check for garbled text
            if text:
                special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.,!?;:\-()]', text)) / len(text)
                if special_char_ratio > 0.3:
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="image_garbled_text",
                            severity=ValidationSeverity.MAJOR,
                            message="Extracted text may contain OCR errors",
                            location=area_data.get('bbox', [0, 0, 0, 0]),
                            suggestion="Manual text review recommended"
                        )
                    )
            
        except Exception as e:
            self.logger.error(f"Image text formatting validation failed: {e}")
    
    def _validate_image_positioning(self, area_data: Dict, pdf_document: fitz.Document, 
                                  validation_result: Dict):
        """Validate image positioning."""
        try:
            bbox = area_data.get('bbox', [0, 0, 0, 0])
            page_num = area_data.get('page', 1) - 1
            
            # Check image size
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            if width < 50 or height < 50:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="image_too_small",
                        severity=ValidationSeverity.MINOR,
                        message=f"Image appears very small: {width}x{height}",
                        location=bbox,
                        suggestion="Verify image boundaries are correct"
                    )
                )
            
            # Check image placement
            if page_num < len(pdf_document):
                page = pdf_document[page_num]
                page_rect = page.rect
                
                # Check if image is well-positioned within page
                margin_left = bbox[0] / page_rect.width
                margin_right = (page_rect.width - bbox[2]) / page_rect.width
                
                if margin_left < 0.05 or margin_right < 0.05:
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="image_edge_placement",
                            severity=ValidationSeverity.MINOR,
                            message="Image is very close to page edge",
                            location=bbox,
                            suggestion="Verify image boundaries don't clip content"
                        )
                    )
            
        except Exception as e:
            self.logger.error(f"Image positioning validation failed: {e}")
    
    def _validate_image_quality(self, content: Dict, validation_result: Dict):
        """Validate image quality metrics."""
        try:
            visual_analysis = content.get('visual_analysis', {})
            quality_assessment = visual_analysis.get('quality_assessment', {})
            
            overall_score = quality_assessment.get('overall_score', 0)
            
            if overall_score < 50:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="image_poor_quality",
                        severity=ValidationSeverity.MAJOR,
                        message=f"Image quality is poor: {overall_score:.1f}/100",
                        location={},
                        suggestion="Consider image enhancement or higher resolution source"
                    )
                )
            
            # Check specific quality metrics
            sharpness = quality_assessment.get('sharpness', 0)
            if sharpness < 40:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="image_low_sharpness",
                        severity=ValidationSeverity.MINOR,
                        message=f"Image sharpness is low: {sharpness:.1f}/100",
                        location={},
                        suggestion="Image may be blurry or low resolution"
                    )
                )
            
        except Exception as e:
            self.logger.error(f"Image quality validation failed: {e}")
    
    def _validate_basic_positioning(self, area_data: Dict, pdf_document: fitz.Document, 
                                  validation_result: Dict):
        """Basic positioning validation for any area type."""
        try:
            bbox = area_data.get('bbox', [0, 0, 0, 0])
            page_num = area_data.get('page', 1) - 1
            
            # Check bbox validity
            if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                validation_result['issues'].append(
                    ValidationIssue(
                        type="invalid_bbox",
                        severity=ValidationSeverity.CRITICAL,
                        message="Area has invalid bounding box coordinates",
                        location=bbox,
                        suggestion="Verify area selection is correct"
                    )
                )
            
            # Check page bounds
            if page_num < len(pdf_document):
                page = pdf_document[page_num]
                page_rect = page.rect
                
                if (bbox[0] < 0 or bbox[1] < 0 or 
                    bbox[2] > page_rect.width or bbox[3] > page_rect.height):
                    validation_result['issues'].append(
                        ValidationIssue(
                            type="area_out_of_bounds",
                            severity=ValidationSeverity.MAJOR,
                            message="Area extends beyond page boundaries",
                            location=bbox,
                            suggestion="Adjust area boundaries to fit within page"
                        )
                    )
            
        except Exception as e:
            self.logger.error(f"Basic positioning validation failed: {e}")
    
    def _validate_basic_content(self, content: Dict, validation_result: Dict):
        """Basic content validation."""
        try:
            # Check if content is empty
            if not content or not any(content.values()):
                validation_result['issues'].append(
                    ValidationIssue(
                        type="empty_content",
                        severity=ValidationSeverity.MAJOR,
                        message="Area contains no extractable content",
                        location={},
                        suggestion="Verify area contains valid content"
                    )
                )
            
        except Exception as e:
            self.logger.error(f"Basic content validation failed: {e}")
    
    def _calculate_quality_score(self, validation_result: Dict) -> float:
        """Calculate overall quality score based on validation issues."""
        try:
            base_score = 100.0
            
            for issue in validation_result.get('issues', []):
                if issue.severity == ValidationSeverity.CRITICAL:
                    base_score -= 30
                elif issue.severity == ValidationSeverity.MAJOR:
                    base_score -= 15
                elif issue.severity == ValidationSeverity.MINOR:
                    base_score -= 5
                elif issue.severity == ValidationSeverity.INFO:
                    base_score -= 1
            
            return max(0.0, base_score)
            
        except Exception as e:
            self.logger.error(f"Quality score calculation failed: {e}")
            return 0.0
    
    def _apply_auto_fixes(self, validation_result: Dict, extraction_result: Dict):
        """Apply automatic fixes to validation issues."""
        try:
            auto_fixes = []
            
            for issue in validation_result.get('issues', []):
                if issue.auto_fixable:
                    fix_applied = self._apply_specific_fix(issue, extraction_result)
                    if fix_applied:
                        auto_fixes.append({
                            'issue_type': issue.type,
                            'fix_description': fix_applied,
                            'timestamp': time.time()
                        })
            
            validation_result['auto_fixes'] = auto_fixes
            self.metrics['auto_fixes_applied'] += len(auto_fixes)
            
        except Exception as e:
            self.logger.error(f"Auto-fix application failed: {e}")
    
    def _apply_specific_fix(self, issue: ValidationIssue, extraction_result: Dict) -> Optional[str]:
        """Apply a specific fix for a validation issue."""
        try:
            if issue.type == "table_row_inconsistency":
                # Fix table row inconsistencies
                structured_content = extraction_result.get('structured_content', {})
                headers = structured_content.get('headers', [])
                rows = structured_content.get('rows', [])
                
                if headers and rows:
                    expected_length = len(headers)
                    for row in rows:
                        while len(row) < expected_length:
                            row.append('')
                        if len(row) > expected_length:
                            row[:] = row[:expected_length]
                    
                    return f"Standardized {len(rows)} rows to {expected_length} columns"
            
            elif issue.type == "table_excessive_empty_cells":
                # Clean up excessive empty cells
                structured_content = extraction_result.get('structured_content', {})
                rows = structured_content.get('rows', [])
                
                cleaned_rows = []
                for row in rows:
                    cleaned_row = [cell if str(cell).strip() else '' for cell in row]
                    cleaned_rows.append(cleaned_row)
                
                structured_content['rows'] = cleaned_rows
                return f"Cleaned empty cells in {len(cleaned_rows)} rows"
            
            return None
            
        except Exception as e:
            self.logger.error(f"Specific fix application failed: {e}")
            return None
    
    def _generate_recommendations(self, validation_result: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        try:
            recommendations = []
            
            # Categorize issues
            critical_issues = [i for i in validation_result.get('issues', []) 
                             if i.severity == ValidationSeverity.CRITICAL]
            major_issues = [i for i in validation_result.get('issues', []) 
                          if i.severity == ValidationSeverity.MAJOR]
            
            # Generate recommendations
            if critical_issues:
                recommendations.append("Address critical issues before proceeding with integration")
            
            if major_issues:
                recommendations.append("Review and fix major issues to improve quality")
            
            if validation_result.get('quality_score', 0) < 70:
                recommendations.append("Quality score is below recommended threshold - manual review suggested")
            
            if validation_result.get('confidence', 0) < 80:
                recommendations.append("Low confidence extraction - consider re-processing with different parameters")
            
            # Add specific recommendations from issues
            for issue in validation_result.get('issues', []):
                if issue.suggestion and issue.suggestion not in recommendations:
                    recommendations.append(issue.suggestion)
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            return []
    
    def validate_reading_order(self, areas: List[Dict], pdf_document: fitz.Document) -> Dict:
        """Validate reading order across multiple special areas."""
        try:
            validation_result = {
                'success': True,
                'reading_order_score': 0.0,
                'issues': [],
                'suggested_order': [],
                'flow_analysis': {}
            }
            
            if not areas:
                return validation_result
            
            # Sort areas by page and position
            sorted_areas = sorted(areas, key=lambda a: (
                a.get('page', 1),
                a.get('bbox', [0, 0, 0, 0])[1],  # Y coordinate
                a.get('bbox', [0, 0, 0, 0])[0]   # X coordinate
            ))
            
            # Analyze reading flow
            flow_issues = []
            
            for i in range(len(sorted_areas) - 1):
                current_area = sorted_areas[i]
                next_area = sorted_areas[i + 1]
                
                # Check if areas are on the same page
                if current_area.get('page') == next_area.get('page'):
                    current_bbox = current_area.get('bbox', [0, 0, 0, 0])
                    next_bbox = next_area.get('bbox', [0, 0, 0, 0])
                    
                    # Check vertical flow
                    if next_bbox[1] < current_bbox[3]:  # Next area starts above current area ends
                        flow_issues.append({
                            'area_indices': [i, i + 1],
                            'issue': 'vertical_flow_reversal',
                            'severity': ValidationSeverity.MINOR
                        })
                    
                    # Check horizontal flow within same vertical region
                    if (abs(current_bbox[1] - next_bbox[1]) < 20 and  # Similar Y positions
                        next_bbox[0] < current_bbox[0]):  # Next area is to the left
                        flow_issues.append({
                            'area_indices': [i, i + 1],
                            'issue': 'horizontal_flow_reversal',
                            'severity': ValidationSeverity.MINOR
                        })
            
            # Calculate reading order score
            total_comparisons = len(sorted_areas) - 1
            flow_score = 100.0 - (len(flow_issues) / max(total_comparisons, 1) * 100)
            
            validation_result['reading_order_score'] = max(0.0, flow_score)
            validation_result['flow_analysis'] = {
                'total_areas': len(areas),
                'flow_issues': len(flow_issues),
                'flow_score': flow_score
            }
            
            # Add flow issues to validation result
            for issue in flow_issues:
                validation_result['issues'].append(
                    ValidationIssue(
                        type=issue['issue'],
                        severity=issue['severity'],
                        message=f"Reading flow issue between areas {issue['area_indices']}",
                        location={},
                        suggestion="Consider reordering areas for better reading flow"
                    )
                )
            
            # Generate suggested order
            validation_result['suggested_order'] = [
                area.get('id', f"area_{i}") for i, area in enumerate(sorted_areas)
            ]
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Reading order validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'reading_order_score': 0.0,
                'issues': [],
                'suggested_order': []
            }
    
    def get_validation_summary(self) -> Dict:
        """Get validation metrics summary."""
        return {
            'metrics': self.metrics.copy(),
            'validation_rules': self.validation_rules,
            'thresholds': self.thresholds
        }
    
    def update_validation_rules(self, new_rules: Dict):
        """Update validation rules."""
        try:
            self.validation_rules.update(new_rules)
            self.logger.info("Validation rules updated")
        except Exception as e:
            self.logger.error(f"Failed to update validation rules: {e}")
    
    def reset_metrics(self):
        """Reset validation metrics."""
        self.metrics = {
            'validations_performed': 0,
            'issues_found': 0,
            'auto_fixes_applied': 0,
            'validation_time': 0.0
        }