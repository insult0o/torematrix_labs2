"""
Output Validator for Agent 4 - Quality assessment and validation.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class OutputValidationResult:
    """Result of output validation."""
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    element_count: int
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]
    quality_metrics: Dict[str, float]
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.recommendations is None:
            self.recommendations = []
        if self.quality_metrics is None:
            self.quality_metrics = {}


class OutputValidator:
    """Comprehensive output quality validator."""
    
    # Expected element types for different document categories
    EXPECTED_ELEMENTS = {
        'pdf': {'Title', 'NarrativeText', 'ListItem', 'Table', 'Header'},
        'office': {'Title', 'NarrativeText', 'Table', 'Header', 'List'},
        'text': {'NarrativeText', 'Header', 'ListItem', 'CodeBlock'},
        'web': {'Title', 'NarrativeText', 'Link', 'Header', 'Table'},
        'email': {'EmailSubject', 'EmailSender', 'EmailBody', 'NarrativeText'}
    }
    
    # Quality thresholds
    MIN_ELEMENTS_THRESHOLD = 1
    MIN_TEXT_LENGTH_THRESHOLD = 10
    MIN_QUALITY_SCORE = 0.3
    
    def __init__(self):
        pass
    
    async def validate_output(self, elements: List[Any], file_path: Path, 
                            processing_time: float = 0.0, **kwargs) -> OutputValidationResult:
        """
        Comprehensive output validation and quality assessment.
        
        Args:
            elements: List of extracted elements
            file_path: Original file path
            processing_time: Time taken to process
            **kwargs: Additional validation options
            
        Returns:
            OutputValidationResult with quality metrics
        """
        result = OutputValidationResult(
            is_valid=False,
            quality_score=0.0,
            element_count=len(elements),
            warnings=[],
            errors=[],
            recommendations=[],
            quality_metrics={}
        )
        
        try:
            # Basic validation checks
            await self._validate_basic_structure(elements, result)
            
            # Content quality assessment
            await self._assess_content_quality(elements, result)
            
            # Element type analysis
            await self._analyze_element_types(elements, file_path, result)
            
            # Text content validation
            await self._validate_text_content(elements, result)
            
            # Structure and completeness check
            await self._check_completeness(elements, file_path, result)
            
            # Performance metrics
            self._add_performance_metrics(processing_time, result)
            
            # Calculate overall quality score
            result.quality_score = self._calculate_quality_score(result)
            
            # Make final validation decision
            result.is_valid = self._make_validation_decision(result)
            
            # Generate recommendations
            self._generate_recommendations(result)
            
            logger.debug(f"Output validation complete: {result.quality_score:.2f} quality score")
            return result
            
        except Exception as e:
            logger.error(f"Output validation failed: {e}")
            result.errors.append(f"Validation exception: {str(e)}")
            return result
    
    async def _validate_basic_structure(self, elements: List[Any], result: OutputValidationResult) -> None:
        """Validate basic output structure."""
        
        # Check if we have any elements
        if not elements:
            result.errors.append("No elements extracted from document")
            return
        
        # Check minimum element threshold
        if len(elements) < self.MIN_ELEMENTS_THRESHOLD:
            result.warnings.append(f"Very few elements extracted: {len(elements)}")
        
        # Check for None or invalid elements
        invalid_count = 0
        for element in elements:
            if element is None:
                invalid_count += 1
            elif not hasattr(element, 'text') and not hasattr(element, 'category'):
                invalid_count += 1
        
        if invalid_count > 0:
            result.warnings.append(f"{invalid_count} invalid/empty elements found")
            result.quality_metrics['invalid_element_ratio'] = invalid_count / len(elements)
    
    async def _assess_content_quality(self, elements: List[Any], result: OutputValidationResult) -> None:
        """Assess the quality of extracted content."""
        
        total_text_length = 0
        meaningful_elements = 0
        empty_elements = 0
        
        for element in elements:
            if hasattr(element, 'text') and element.text:
                text = str(element.text).strip()
                text_length = len(text)
                total_text_length += text_length
                
                if text_length >= self.MIN_TEXT_LENGTH_THRESHOLD:
                    meaningful_elements += 1
                elif text_length == 0:
                    empty_elements += 1
            else:
                empty_elements += 1
        
        # Calculate content metrics
        result.quality_metrics['total_text_length'] = total_text_length
        result.quality_metrics['meaningful_element_ratio'] = meaningful_elements / len(elements) if elements else 0
        result.quality_metrics['empty_element_ratio'] = empty_elements / len(elements) if elements else 0
        result.quality_metrics['average_text_length'] = total_text_length / len(elements) if elements else 0
        
        # Add warnings for poor content quality
        if meaningful_elements == 0:
            result.errors.append("No meaningful content extracted")
        elif meaningful_elements / len(elements) < 0.3:
            result.warnings.append("Low meaningful content ratio")
        
        if empty_elements / len(elements) > 0.5:
            result.warnings.append("High number of empty elements")
    
    async def _analyze_element_types(self, elements: List[Any], file_path: Path, 
                                   result: OutputValidationResult) -> None:
        """Analyze element types and diversity."""
        
        element_types = {}
        error_elements = 0
        
        for element in elements:
            if hasattr(element, 'category'):
                element_type = element.category
            elif hasattr(element, 'type'):
                element_type = element.type
            else:
                element_type = 'Unknown'
            
            # Count error elements
            if element_type in ['Error', 'error']:
                error_elements += 1
            
            element_types[element_type] = element_types.get(element_type, 0) + 1
        
        result.quality_metrics['element_type_diversity'] = len(element_types)
        result.quality_metrics['element_types'] = element_types
        result.quality_metrics['error_element_count'] = error_elements
        
        # Check for appropriate element types based on file format
        file_extension = file_path.suffix.lower()
        expected_category = self._get_format_category(file_extension)
        
        if expected_category and expected_category in self.EXPECTED_ELEMENTS:
            expected_types = self.EXPECTED_ELEMENTS[expected_category]
            found_types = set(element_types.keys())
            
            overlap = len(found_types.intersection(expected_types))
            if overlap == 0:
                result.warnings.append(f"No expected element types found for {expected_category} format")
            
            result.quality_metrics['expected_type_overlap'] = overlap / len(expected_types)
        
        # Warn about too many errors
        if error_elements > 0:
            error_ratio = error_elements / len(elements)
            if error_ratio > 0.1:
                result.warnings.append(f"High error element ratio: {error_ratio:.1%}")
            result.quality_metrics['error_element_ratio'] = error_ratio
    
    async def _validate_text_content(self, elements: List[Any], result: OutputValidationResult) -> None:
        """Validate text content quality."""
        
        text_issues = {
            'non_utf8_chars': 0,
            'very_long_texts': 0,
            'repeated_content': 0,
            'suspicious_patterns': 0
        }
        
        seen_texts = set()
        
        for element in elements:
            if not hasattr(element, 'text') or not element.text:
                continue
                
            text = str(element.text)
            
            # Check for encoding issues
            try:
                text.encode('utf-8')
            except UnicodeEncodeError:
                text_issues['non_utf8_chars'] += 1
            
            # Check for very long texts (might indicate parsing errors)
            if len(text) > 10000:  # More than 10k characters
                text_issues['very_long_texts'] += 1
            
            # Check for repeated content
            text_normalized = text.lower().strip()
            if text_normalized in seen_texts:
                text_issues['repeated_content'] += 1
            seen_texts.add(text_normalized)
            
            # Check for suspicious patterns
            if any(pattern in text.lower() for pattern in ['�', 'unknown', 'error', 'failed']):
                text_issues['suspicious_patterns'] += 1
        
        # Add metrics
        for issue_type, count in text_issues.items():
            if count > 0:
                result.quality_metrics[f'text_{issue_type}'] = count
                ratio = count / len(elements)
                
                if ratio > 0.1:  # More than 10%
                    result.warnings.append(f"High {issue_type.replace('_', ' ')}: {count} instances")
    
    async def _check_completeness(self, elements: List[Any], file_path: Path, 
                                result: OutputValidationResult) -> None:
        """Check if extraction appears complete."""
        
        # File size vs content ratio
        try:
            file_size = file_path.stat().st_size
            total_text = sum(len(str(getattr(e, 'text', ''))) for e in elements)
            
            size_ratio = total_text / file_size if file_size > 0 else 0
            result.quality_metrics['text_to_file_size_ratio'] = size_ratio
            
            # For text files, ratio should be close to 1
            if file_path.suffix.lower() in ['.txt', '.md', '.rst']:
                if size_ratio < 0.5:
                    result.warnings.append("Low text extraction ratio for text file")
            # For other formats, lower ratios are expected
            elif size_ratio < 0.01:
                result.warnings.append("Very low text extraction ratio")
                
        except Exception as e:
            logger.warning(f"Could not check file size ratio: {e}")
        
        # Check for minimum content based on file type
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            # PDFs should typically have multiple elements
            if len(elements) < 3:
                result.warnings.append("PDF produced very few elements")
        elif extension in ['.docx', '.doc']:
            # Word docs should have meaningful structure
            has_title = any(getattr(e, 'category', '') in ['Title', 'Header'] for e in elements)
            if not has_title:
                result.warnings.append("Document lacks title or header structure")
        elif extension in ['.html', '.htm']:
            # HTML should have links or structure
            has_links = any('link' in str(getattr(e, 'category', '')).lower() for e in elements)
            has_structure = any('header' in str(getattr(e, 'category', '')).lower() for e in elements)
            if not (has_links or has_structure):
                result.warnings.append("HTML lacks expected link or header structure")
    
    def _add_performance_metrics(self, processing_time: float, result: OutputValidationResult) -> None:
        """Add performance-related metrics."""
        result.quality_metrics['processing_time'] = processing_time
        
        if result.element_count > 0:
            result.quality_metrics['elements_per_second'] = result.element_count / max(processing_time, 0.001)
        
        # Performance benchmarks
        if processing_time > 30:  # More than 30 seconds
            result.warnings.append("Processing took longer than expected")
        elif processing_time > 120:  # More than 2 minutes
            result.warnings.append("Very slow processing time")
    
    def _calculate_quality_score(self, result: OutputValidationResult) -> float:
        """Calculate overall quality score (0.0 to 1.0)."""
        
        if result.errors:
            return 0.0  # Any errors = 0 quality
        
        score_factors = []
        
        # Content quality factors
        meaningful_ratio = result.quality_metrics.get('meaningful_element_ratio', 0.0)
        score_factors.append(min(meaningful_ratio * 2, 1.0))  # Up to 1.0
        
        # Element diversity
        diversity = result.quality_metrics.get('element_type_diversity', 1)
        diversity_score = min(diversity / 5.0, 1.0)  # Normalize to 5 types
        score_factors.append(diversity_score)
        
        # Text quality
        total_text = result.quality_metrics.get('total_text_length', 0)
        text_score = min(total_text / 1000.0, 1.0)  # Normalize to 1000 chars
        score_factors.append(text_score)
        
        # Error penalty
        error_ratio = result.quality_metrics.get('error_element_ratio', 0.0)
        error_penalty = 1.0 - min(error_ratio * 2, 1.0)
        score_factors.append(error_penalty)
        
        # Expected type overlap (if available)
        type_overlap = result.quality_metrics.get('expected_type_overlap', 0.5)
        score_factors.append(type_overlap)
        
        # Calculate weighted average
        base_score = sum(score_factors) / len(score_factors)
        
        # Apply warning penalty
        warning_penalty = max(0.0, 1.0 - len(result.warnings) * 0.1)
        final_score = base_score * warning_penalty
        
        return max(0.0, min(1.0, final_score))
    
    def _make_validation_decision(self, result: OutputValidationResult) -> bool:
        """Make final validation decision."""
        # Fail if there are errors
        if result.errors:
            return False
        
        # Fail if quality score is too low
        if result.quality_score < self.MIN_QUALITY_SCORE:
            return False
        
        # Fail if no meaningful content
        if result.element_count == 0:
            return False
        
        return True
    
    def _generate_recommendations(self, result: OutputValidationResult) -> None:
        """Generate improvement recommendations."""
        
        if result.quality_score < 0.5:
            result.recommendations.append("Consider using a different processing strategy")
        
        meaningful_ratio = result.quality_metrics.get('meaningful_element_ratio', 0.0)
        if meaningful_ratio < 0.3:
            result.recommendations.append("Many elements have little content - check parsing configuration")
        
        error_ratio = result.quality_metrics.get('error_element_ratio', 0.0)
        if error_ratio > 0.1:
            result.recommendations.append("High error rate - document may be corrupted or complex")
        
        diversity = result.quality_metrics.get('element_type_diversity', 0)
        if diversity < 2:
            result.recommendations.append("Low element diversity - may need format-specific handling")
        
        if len(result.warnings) > 5:
            result.recommendations.append("Many warnings - review document quality and processing strategy")
    
    def _get_format_category(self, extension: str) -> Optional[str]:
        """Get format category from file extension."""
        format_map = {
            '.pdf': 'pdf',
            '.docx': 'office', '.doc': 'office', '.xlsx': 'office', '.pptx': 'office',
            '.txt': 'text', '.md': 'text', '.csv': 'text',
            '.html': 'web', '.htm': 'web', '.xml': 'web',
            '.eml': 'email', '.msg': 'email'
        }
        return format_map.get(extension.lower())
    
    async def validate_batch_output(self, batch_results: List[Any]) -> Dict[str, Any]:
        """Validate output from batch processing."""
        
        total_docs = len(batch_results)
        successful_docs = sum(1 for r in batch_results if getattr(r, 'success', False))
        
        # Aggregate quality scores
        quality_scores = [getattr(r, 'quality_score', 0.0) for r in batch_results if getattr(r, 'success', False)]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Collect all warnings and errors
        all_warnings = []
        all_errors = []
        
        for result in batch_results:
            if hasattr(result, 'warnings'):
                all_warnings.extend(result.warnings)
            if hasattr(result, 'errors'):
                all_errors.extend(result.errors)
        
        return {
            'total_documents': total_docs,
            'successful_documents': successful_docs,
            'success_rate': successful_docs / total_docs if total_docs > 0 else 0.0,
            'average_quality_score': avg_quality,
            'total_warnings': len(all_warnings),
            'total_errors': len(all_errors),
            'batch_quality': 'good' if avg_quality > 0.7 else 'moderate' if avg_quality > 0.4 else 'poor'
        }