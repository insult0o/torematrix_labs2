#!/usr/bin/env python3
"""
Content integration system for merging special area extractions with original text.
Maintains proper positioning, reading order, and document structure.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import re
import time
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json

import fitz  # PyMuPDF
import numpy as np

from ...config.settings import Settings


class IntegrationMethod(Enum):
    """Content integration methods."""
    REPLACE = "replace"
    ENHANCE = "enhance"
    SUPPLEMENT = "supplement"
    INLINE = "inline"


class ContentType(Enum):
    """Types of content for integration."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    DIAGRAM = "diagram"
    CHART = "chart"
    COMPLEX = "complex"


@dataclass
class IntegrationPoint:
    """Represents a point where content should be integrated."""
    area_id: str
    content_type: ContentType
    position: Tuple[float, float, float, float]  # bbox coordinates
    page_number: int
    original_text: str
    extracted_content: Dict[str, Any]
    integration_method: IntegrationMethod
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationResult:
    """Result of content integration."""
    success: bool
    integrated_content: str
    integration_points: List[IntegrationPoint]
    reading_order: List[str]
    quality_score: float
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentIntegrator:
    """Integrates special area extractions with original document text."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Integration settings
        self.integration_settings = {
            'preserve_original_formatting': True,
            'maintain_reading_order': True,
            'merge_adjacent_text': True,
            'validate_integration': True,
            'add_metadata_markers': False,
            'output_formats': ['text', 'markdown', 'html', 'json']
        }
        
        # Integration strategies for different content types
        self.integration_strategies = {
            ContentType.TEXT: self._integrate_text_content,
            ContentType.TABLE: self._integrate_table_content,
            ContentType.IMAGE: self._integrate_image_content,
            ContentType.DIAGRAM: self._integrate_diagram_content,
            ContentType.CHART: self._integrate_chart_content,
            ContentType.COMPLEX: self._integrate_complex_content
        }
        
        # Reading order detection patterns
        self.reading_patterns = {
            'left_to_right': lambda areas: sorted(areas, key=lambda a: (a.page_number, a.position[1], a.position[0])),
            'top_to_bottom': lambda areas: sorted(areas, key=lambda a: (a.page_number, a.position[1], a.position[0])),
            'column_wise': self._sort_column_wise,
            'custom': self._sort_custom_order
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'minimum_integration_quality': 60.0,
            'text_coherence_threshold': 0.7,
            'position_accuracy_threshold': 0.9,
            'reading_order_confidence': 0.8
        }
        
        # Metrics tracking
        self.metrics = {
            'integrations_performed': 0,
            'successful_integrations': 0,
            'failed_integrations': 0,
            'average_quality_score': 0.0,
            'total_integration_time': 0.0
        }
        
        self.logger.info("Content integrator initialized")
    
    def integrate_content(self, original_text: str, special_areas: List[Dict], 
                         extraction_results: Dict[str, Dict], pdf_document: fitz.Document) -> IntegrationResult:
        """Integrate special area extractions with original text."""
        start_time = time.time()
        
        try:
            self.metrics['integrations_performed'] += 1
            
            # Create integration points
            integration_points = self._create_integration_points(
                special_areas, extraction_results, pdf_document
            )
            
            # Determine optimal reading order
            reading_order = self._determine_reading_order(integration_points)
            
            # Perform integration
            integrated_content = self._perform_integration(
                original_text, integration_points, reading_order, pdf_document
            )
            
            # Validate integration
            validation_result = self._validate_integration(
                original_text, integrated_content, integration_points
            )
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                validation_result, integration_points
            )
            
            # Create result
            result = IntegrationResult(
                success=quality_score >= self.quality_thresholds['minimum_integration_quality'],
                integrated_content=integrated_content,
                integration_points=integration_points,
                reading_order=reading_order,
                quality_score=quality_score,
                issues=validation_result.get('issues', []),
                metadata={
                    'integration_time': time.time() - start_time,
                    'num_integration_points': len(integration_points),
                    'reading_order_method': 'top_to_bottom',  # Default
                    'validation_details': validation_result
                }
            )
            
            # Update metrics
            if result.success:
                self.metrics['successful_integrations'] += 1
            else:
                self.metrics['failed_integrations'] += 1
            
            self.metrics['total_integration_time'] += time.time() - start_time
            self.metrics['average_quality_score'] = (
                (self.metrics['average_quality_score'] * (self.metrics['integrations_performed'] - 1) + 
                 quality_score) / self.metrics['integrations_performed']
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Content integration failed: {e}")
            self.metrics['failed_integrations'] += 1
            return IntegrationResult(
                success=False,
                integrated_content=original_text,
                integration_points=[],
                reading_order=[],
                quality_score=0.0,
                issues=[f"Integration failed: {str(e)}"]
            )
    
    def _create_integration_points(self, special_areas: List[Dict], 
                                 extraction_results: Dict[str, Dict], 
                                 pdf_document: fitz.Document) -> List[IntegrationPoint]:
        """Create integration points from special areas and extraction results."""
        integration_points = []
        
        for area in special_areas:
            area_id = area.get('id', area.get('type', 'unknown'))
            extraction_result = extraction_results.get(area_id, {})
            
            if not extraction_result.get('success', False):
                continue
            
            # Determine content type
            content_type = self._get_content_type(area.get('type', ''))
            
            # Get original text from area
            original_text = self._extract_original_text(area, pdf_document)
            
            # Determine integration method
            integration_method = self._determine_integration_method(
                content_type, extraction_result, area
            )
            
            # Create integration point
            integration_point = IntegrationPoint(
                area_id=area_id,
                content_type=content_type,
                position=area.get('bbox', [0, 0, 0, 0]),
                page_number=area.get('page', 1),
                original_text=original_text,
                extracted_content=extraction_result,
                integration_method=integration_method,
                priority=area.get('priority', 0),
                metadata={
                    'area_type': area.get('type', ''),
                    'special_notes': area.get('special_notes', ''),
                    'high_priority': area.get('high_priority', False)
                }
            )
            
            integration_points.append(integration_point)
        
        return integration_points
    
    def _get_content_type(self, area_type: str) -> ContentType:
        """Get content type enum from area type string."""
        area_type_upper = area_type.upper()
        
        if area_type_upper == 'TABLE':
            return ContentType.TABLE
        elif area_type_upper == 'IMAGE':
            return ContentType.IMAGE
        elif area_type_upper == 'DIAGRAM':
            return ContentType.DIAGRAM
        elif area_type_upper == 'CHART':
            return ContentType.CHART
        elif area_type_upper == 'COMPLEX':
            return ContentType.COMPLEX
        else:
            return ContentType.TEXT
    
    def _extract_original_text(self, area: Dict, pdf_document: fitz.Document) -> str:
        """Extract original text from area."""
        try:
            page_num = area.get('page', 1) - 1
            bbox = area.get('bbox', [0, 0, 0, 0])
            
            if page_num < len(pdf_document):
                page = pdf_document[page_num]
                area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                return page.get_text("text", clip=area_rect)
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Failed to extract original text: {e}")
            return ""
    
    def _determine_integration_method(self, content_type: ContentType, 
                                    extraction_result: Dict, area: Dict) -> IntegrationMethod:
        """Determine the best integration method for the content."""
        # Check if extraction significantly improves original content
        confidence = extraction_result.get('confidence_score', 0)
        
        # High confidence extractions replace original
        if confidence >= 90:
            return IntegrationMethod.REPLACE
        
        # Medium confidence extractions enhance original
        elif confidence >= 70:
            if content_type in [ContentType.TABLE, ContentType.CHART]:
                return IntegrationMethod.REPLACE  # Structured data usually replaces
            else:
                return IntegrationMethod.ENHANCE
        
        # Low confidence extractions supplement original
        elif confidence >= 50:
            return IntegrationMethod.SUPPLEMENT
        
        # Very low confidence just adds inline
        else:
            return IntegrationMethod.INLINE
    
    def _determine_reading_order(self, integration_points: List[IntegrationPoint]) -> List[str]:
        """Determine optimal reading order for integration points."""
        try:
            # Group by page
            pages = {}
            for point in integration_points:
                page_num = point.page_number
                if page_num not in pages:
                    pages[page_num] = []
                pages[page_num].append(point)
            
            # Sort within each page
            reading_order = []
            for page_num in sorted(pages.keys()):
                page_points = pages[page_num]
                
                # Sort by Y coordinate (top to bottom), then X coordinate (left to right)
                sorted_points = sorted(page_points, key=lambda p: (p.position[1], p.position[0]))
                
                # Add to reading order
                for point in sorted_points:
                    reading_order.append(point.area_id)
            
            return reading_order
            
        except Exception as e:
            self.logger.error(f"Failed to determine reading order: {e}")
            return [point.area_id for point in integration_points]
    
    def _sort_column_wise(self, areas: List[IntegrationPoint]) -> List[IntegrationPoint]:
        """Sort areas in column-wise reading order."""
        try:
            # Detect columns based on X coordinates
            x_positions = [area.position[0] for area in areas]
            
            # Simple column detection (more sophisticated methods could be used)
            if len(set(x_positions)) > 1:
                # Multi-column layout
                sorted_areas = sorted(areas, key=lambda a: (a.position[0], a.position[1]))
            else:
                # Single column layout
                sorted_areas = sorted(areas, key=lambda a: (a.position[1], a.position[0]))
            
            return sorted_areas
            
        except Exception as e:
            self.logger.error(f"Column-wise sorting failed: {e}")
            return areas
    
    def _sort_custom_order(self, areas: List[IntegrationPoint]) -> List[IntegrationPoint]:
        """Sort areas based on custom priority and metadata."""
        try:
            return sorted(areas, key=lambda a: (
                -a.priority,  # Higher priority first
                a.page_number,  # Then by page
                a.position[1],  # Then by Y position
                a.position[0]   # Then by X position
            ))
            
        except Exception as e:
            self.logger.error(f"Custom sorting failed: {e}")
            return areas
    
    def _perform_integration(self, original_text: str, 
                           integration_points: List[IntegrationPoint], 
                           reading_order: List[str], 
                           pdf_document: fitz.Document) -> str:
        """Perform the actual content integration."""
        try:
            # Create mapping from area_id to integration point
            point_map = {point.area_id: point for point in integration_points}
            
            # Start with original text
            integrated_content = original_text
            
            # Process integration points in reading order
            for area_id in reading_order:
                if area_id not in point_map:
                    continue
                
                point = point_map[area_id]
                
                # Get integration strategy
                strategy = self.integration_strategies.get(
                    point.content_type, self._integrate_text_content
                )
                
                # Apply integration
                integrated_content = strategy(
                    integrated_content, point, pdf_document
                )
            
            # Post-process integrated content
            integrated_content = self._post_process_integrated_content(
                integrated_content, integration_points
            )
            
            return integrated_content
            
        except Exception as e:
            self.logger.error(f"Integration performance failed: {e}")
            return original_text
    
    def _integrate_text_content(self, current_content: str, 
                              point: IntegrationPoint, 
                              pdf_document: fitz.Document) -> str:
        """Integrate text content."""
        try:
            extracted_content = point.extracted_content.get('content', {})
            
            if point.integration_method == IntegrationMethod.REPLACE:
                # Replace original text with extracted content
                new_text = extracted_content.get('text', point.original_text)
                return current_content.replace(point.original_text, new_text)
            
            elif point.integration_method == IntegrationMethod.ENHANCE:
                # Enhance original text with extracted content
                enhancement = extracted_content.get('enhancement', '')
                if enhancement:
                    enhanced_text = f"{point.original_text}\n{enhancement}"
                    return current_content.replace(point.original_text, enhanced_text)
            
            elif point.integration_method == IntegrationMethod.SUPPLEMENT:
                # Add extracted content as supplement
                supplement = extracted_content.get('supplement', '')
                if supplement:
                    supplemented_text = f"{point.original_text}\n[Supplement: {supplement}]"
                    return current_content.replace(point.original_text, supplemented_text)
            
            else:  # INLINE
                # Add extracted content inline
                inline_content = extracted_content.get('inline', '')
                if inline_content:
                    inline_text = f"{point.original_text} [{inline_content}]"
                    return current_content.replace(point.original_text, inline_text)
            
            return current_content
            
        except Exception as e:
            self.logger.error(f"Text integration failed: {e}")
            return current_content
    
    def _integrate_table_content(self, current_content: str, 
                               point: IntegrationPoint, 
                               pdf_document: fitz.Document) -> str:
        """Integrate table content."""
        try:
            structured_content = point.extracted_content.get('structured_content', {})
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            if not headers or not rows:
                return current_content
            
            # Generate table representation
            if point.integration_method == IntegrationMethod.REPLACE:
                # Create formatted table
                table_lines = []
                
                # Headers
                table_lines.append(' | '.join(headers))
                table_lines.append(' | '.join(['---'] * len(headers)))
                
                # Rows
                for row in rows:
                    table_lines.append(' | '.join(str(cell) for cell in row))
                
                table_text = '\n'.join(table_lines)
                return current_content.replace(point.original_text, table_text)
            
            else:
                # Add table as supplement
                table_summary = f"Table with {len(headers)} columns and {len(rows)} rows"
                supplemented_text = f"{point.original_text}\n[Table: {table_summary}]"
                return current_content.replace(point.original_text, supplemented_text)
            
        except Exception as e:
            self.logger.error(f"Table integration failed: {e}")
            return current_content
    
    def _integrate_image_content(self, current_content: str, 
                               point: IntegrationPoint, 
                               pdf_document: fitz.Document) -> str:
        """Integrate image content."""
        try:
            content = point.extracted_content.get('content', {})
            description = content.get('description', {})
            extracted_text = content.get('extracted_text', {})
            
            if point.integration_method == IntegrationMethod.REPLACE:
                # Replace with image description and extracted text
                replacement_parts = []
                
                if description.get('detailed'):
                    replacement_parts.append(f"[Image: {description['detailed']}]")
                
                if extracted_text.get('text'):
                    replacement_parts.append(f"Text from image: {extracted_text['text']}")
                
                replacement_text = '\n'.join(replacement_parts) if replacement_parts else point.original_text
                return current_content.replace(point.original_text, replacement_text)
            
            else:
                # Add image description as supplement
                img_description = description.get('brief', 'Image content')
                supplemented_text = f"{point.original_text}\n[Image: {img_description}]"
                return current_content.replace(point.original_text, supplemented_text)
            
        except Exception as e:
            self.logger.error(f"Image integration failed: {e}")
            return current_content
    
    def _integrate_diagram_content(self, current_content: str, 
                                 point: IntegrationPoint, 
                                 pdf_document: fitz.Document) -> str:
        """Integrate diagram content."""
        try:
            content = point.extracted_content.get('content', {})
            
            if point.integration_method == IntegrationMethod.REPLACE:
                # Replace with diagram description
                diagram_description = content.get('description', 'Diagram content')
                return current_content.replace(point.original_text, f"[Diagram: {diagram_description}]")
            
            else:
                # Add diagram description as supplement
                diagram_info = content.get('summary', 'Diagram')
                supplemented_text = f"{point.original_text}\n[Diagram: {diagram_info}]"
                return current_content.replace(point.original_text, supplemented_text)
            
        except Exception as e:
            self.logger.error(f"Diagram integration failed: {e}")
            return current_content
    
    def _integrate_chart_content(self, current_content: str, 
                               point: IntegrationPoint, 
                               pdf_document: fitz.Document) -> str:
        """Integrate chart content."""
        try:
            content = point.extracted_content.get('content', {})
            
            if point.integration_method == IntegrationMethod.REPLACE:
                # Replace with chart description and data
                chart_description = content.get('description', 'Chart content')
                chart_data = content.get('data_summary', '')
                
                replacement_parts = [f"[Chart: {chart_description}]"]
                if chart_data:
                    replacement_parts.append(f"Data: {chart_data}")
                
                replacement_text = '\n'.join(replacement_parts)
                return current_content.replace(point.original_text, replacement_text)
            
            else:
                # Add chart description as supplement
                chart_info = content.get('summary', 'Chart')
                supplemented_text = f"{point.original_text}\n[Chart: {chart_info}]"
                return current_content.replace(point.original_text, supplemented_text)
            
        except Exception as e:
            self.logger.error(f"Chart integration failed: {e}")
            return current_content
    
    def _integrate_complex_content(self, current_content: str, 
                                 point: IntegrationPoint, 
                                 pdf_document: fitz.Document) -> str:
        """Integrate complex content."""
        try:
            content = point.extracted_content.get('content', {})
            
            if point.integration_method == IntegrationMethod.REPLACE:
                # Replace with structured content
                structured_text = content.get('structured_text', point.original_text)
                return current_content.replace(point.original_text, structured_text)
            
            else:
                # Add complex content summary as supplement
                complex_summary = content.get('summary', 'Complex content')
                supplemented_text = f"{point.original_text}\n[Complex: {complex_summary}]"
                return current_content.replace(point.original_text, supplemented_text)
            
        except Exception as e:
            self.logger.error(f"Complex content integration failed: {e}")
            return current_content
    
    def _post_process_integrated_content(self, content: str, 
                                       integration_points: List[IntegrationPoint]) -> str:
        """Post-process integrated content."""
        try:
            # Remove excessive whitespace
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            # Normalize line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Merge adjacent similar markers if enabled
            if self.integration_settings.get('merge_adjacent_text', True):
                content = self._merge_adjacent_markers(content)
            
            # Add metadata markers if enabled
            if self.integration_settings.get('add_metadata_markers', False):
                content = self._add_metadata_markers(content, integration_points)
            
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Post-processing failed: {e}")
            return content
    
    def _merge_adjacent_markers(self, content: str) -> str:
        """Merge adjacent similar markers."""
        try:
            # Merge adjacent table markers
            content = re.sub(r'\[Table:[^\]]+\]\s*\[Table:[^\]]+\]', '[Table: Multiple tables]', content)
            
            # Merge adjacent image markers
            content = re.sub(r'\[Image:[^\]]+\]\s*\[Image:[^\]]+\]', '[Image: Multiple images]', content)
            
            # Merge adjacent diagram markers
            content = re.sub(r'\[Diagram:[^\]]+\]\s*\[Diagram:[^\]]+\]', '[Diagram: Multiple diagrams]', content)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Marker merging failed: {e}")
            return content
    
    def _add_metadata_markers(self, content: str, 
                            integration_points: List[IntegrationPoint]) -> str:
        """Add metadata markers to content."""
        try:
            # Add integration metadata at the beginning
            metadata_lines = []
            metadata_lines.append("<!-- Integration Metadata -->")
            metadata_lines.append(f"<!-- Integration Points: {len(integration_points)} -->")
            metadata_lines.append(f"<!-- Integration Time: {time.strftime('%Y-%m-%d %H:%M:%S')} -->")
            
            for point in integration_points:
                metadata_lines.append(f"<!-- {point.area_id}: {point.content_type.value} at page {point.page_number} -->")
            
            metadata_lines.append("<!-- End Integration Metadata -->")
            metadata_lines.append("")
            
            return '\n'.join(metadata_lines) + content
            
        except Exception as e:
            self.logger.error(f"Metadata addition failed: {e}")
            return content
    
    def _validate_integration(self, original_text: str, integrated_content: str, 
                            integration_points: List[IntegrationPoint]) -> Dict[str, Any]:
        """Validate the integration result."""
        try:
            validation_result = {
                'success': True,
                'issues': [],
                'quality_metrics': {},
                'content_preservation': 0.0,
                'integration_completeness': 0.0
            }
            
            # Check content preservation
            original_length = len(original_text)
            integrated_length = len(integrated_content)
            
            if integrated_length == 0:
                validation_result['issues'].append("Integrated content is empty")
                validation_result['success'] = False
                return validation_result
            
            # Calculate content preservation ratio
            preservation_ratio = min(integrated_length / original_length, 1.0) if original_length > 0 else 0.0
            validation_result['content_preservation'] = preservation_ratio
            
            # Check integration completeness
            integrated_areas = sum(1 for point in integration_points if point.area_id in integrated_content)
            completeness_ratio = integrated_areas / len(integration_points) if integration_points else 1.0
            validation_result['integration_completeness'] = completeness_ratio
            
            # Quality metrics
            validation_result['quality_metrics'] = {
                'original_length': original_length,
                'integrated_length': integrated_length,
                'length_ratio': integrated_length / original_length if original_length > 0 else 0.0,
                'integration_points_processed': len(integration_points),
                'integration_points_successful': integrated_areas
            }
            
            # Check for issues
            if preservation_ratio < 0.5:
                validation_result['issues'].append("Significant content loss detected")
            
            if completeness_ratio < 0.8:
                validation_result['issues'].append("Low integration completeness")
            
            # Overall success
            validation_result['success'] = len(validation_result['issues']) == 0
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Integration validation failed: {e}")
            return {
                'success': False,
                'issues': [f"Validation failed: {str(e)}"],
                'quality_metrics': {},
                'content_preservation': 0.0,
                'integration_completeness': 0.0
            }
    
    def _calculate_quality_score(self, validation_result: Dict[str, Any], 
                               integration_points: List[IntegrationPoint]) -> float:
        """Calculate overall quality score for integration."""
        try:
            if not validation_result.get('success', False):
                return 0.0
            
            # Base score
            base_score = 70.0
            
            # Content preservation score (30%)
            preservation_score = validation_result.get('content_preservation', 0.0) * 30
            
            # Integration completeness score (30%)
            completeness_score = validation_result.get('integration_completeness', 0.0) * 30
            
            # Quality bonus for successful high-priority integrations (20%)
            priority_bonus = 0.0
            if integration_points:
                high_priority_count = sum(1 for point in integration_points if point.priority > 0)
                if high_priority_count > 0:
                    priority_bonus = min(high_priority_count / len(integration_points), 1.0) * 20
            
            # Calculate final score
            final_score = base_score + preservation_score + completeness_score + priority_bonus
            
            # Penalize for issues
            issue_penalty = len(validation_result.get('issues', [])) * 10
            final_score -= issue_penalty
            
            return max(0.0, min(100.0, final_score))
            
        except Exception as e:
            self.logger.error(f"Quality score calculation failed: {e}")
            return 0.0
    
    def generate_output_formats(self, integration_result: IntegrationResult) -> Dict[str, str]:
        """Generate integrated content in multiple output formats."""
        try:
            formats = {}
            
            # Text format (default)
            formats['text'] = integration_result.integrated_content
            
            # Markdown format
            formats['markdown'] = self._convert_to_markdown(integration_result)
            
            # HTML format
            formats['html'] = self._convert_to_html(integration_result)
            
            # JSON format
            formats['json'] = self._convert_to_json(integration_result)
            
            return formats
            
        except Exception as e:
            self.logger.error(f"Output format generation failed: {e}")
            return {'text': integration_result.integrated_content}
    
    def _convert_to_markdown(self, integration_result: IntegrationResult) -> str:
        """Convert integrated content to Markdown format."""
        try:
            content = integration_result.integrated_content
            
            # Convert markers to Markdown
            content = re.sub(r'\[Table: ([^\]]+)\]', r'**Table:** \1', content)
            content = re.sub(r'\[Image: ([^\]]+)\]', r'**Image:** \1', content)
            content = re.sub(r'\[Diagram: ([^\]]+)\]', r'**Diagram:** \1', content)
            content = re.sub(r'\[Chart: ([^\]]+)\]', r'**Chart:** \1', content)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Markdown conversion failed: {e}")
            return integration_result.integrated_content
    
    def _convert_to_html(self, integration_result: IntegrationResult) -> str:
        """Convert integrated content to HTML format."""
        try:
            content = integration_result.integrated_content
            
            # Convert markers to HTML
            content = re.sub(r'\[Table: ([^\]]+)\]', r'<div class="table-marker"><strong>Table:</strong> \1</div>', content)
            content = re.sub(r'\[Image: ([^\]]+)\]', r'<div class="image-marker"><strong>Image:</strong> \1</div>', content)
            content = re.sub(r'\[Diagram: ([^\]]+)\]', r'<div class="diagram-marker"><strong>Diagram:</strong> \1</div>', content)
            content = re.sub(r'\[Chart: ([^\]]+)\]', r'<div class="chart-marker"><strong>Chart:</strong> \1</div>', content)
            
            # Convert line breaks to HTML
            content = content.replace('\n', '<br>\n')
            
            return f"<div class='integrated-content'>{content}</div>"
            
        except Exception as e:
            self.logger.error(f"HTML conversion failed: {e}")
            return integration_result.integrated_content
    
    def _convert_to_json(self, integration_result: IntegrationResult) -> str:
        """Convert integrated content to JSON format."""
        try:
            json_data = {
                'integrated_content': integration_result.integrated_content,
                'integration_points': [
                    {
                        'area_id': point.area_id,
                        'content_type': point.content_type.value,
                        'page_number': point.page_number,
                        'position': point.position,
                        'integration_method': point.integration_method.value,
                        'priority': point.priority
                    }
                    for point in integration_result.integration_points
                ],
                'reading_order': integration_result.reading_order,
                'quality_score': integration_result.quality_score,
                'metadata': integration_result.metadata
            }
            
            return json.dumps(json_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"JSON conversion failed: {e}")
            return json.dumps({
                'integrated_content': integration_result.integrated_content,
                'error': str(e)
            })
    
    def update_integration_settings(self, new_settings: Dict[str, Any]):
        """Update integration settings."""
        try:
            self.integration_settings.update(new_settings)
            self.logger.info("Integration settings updated")
        except Exception as e:
            self.logger.error(f"Failed to update integration settings: {e}")
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration performance metrics."""
        return {
            'metrics': self.metrics.copy(),
            'settings': self.integration_settings.copy(),
            'quality_thresholds': self.quality_thresholds.copy()
        }
    
    def reset_metrics(self):
        """Reset integration metrics."""
        self.metrics = {
            'integrations_performed': 0,
            'successful_integrations': 0,
            'failed_integrations': 0,
            'average_quality_score': 0.0,
            'total_integration_time': 0.0
        }