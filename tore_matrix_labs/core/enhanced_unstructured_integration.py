#!/usr/bin/env python3
"""
Enhanced Unstructured Integration for TORE Matrix Labs

Seamlessly integrates the robust unstructured pipeline with existing TORE workflow.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time

from ..config.settings import Settings
from ..models.document_models import Document
from .document_analyzer import DocumentElement, ElementType, PageAnalysis
from .content_extractor import ExtractedContent, ExtractedTable, ExtractedImage

# Import the enhanced processor
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from enhanced_unstructured_processor import EnhancedUnstructuredProcessor, EnhancedElement


class EnhancedUnstructuredIntegration:
    """
    Integration layer connecting enhanced unstructured processing 
    with existing TORE Matrix Labs workflow.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        try:
            self.processor = EnhancedUnstructuredProcessor()
            self.available = True
            self.logger.info("Enhanced unstructured processor initialized successfully")
        except ImportError as e:
            self.logger.error(f"Enhanced unstructured processor not available: {e}")
            self.available = False
    
    def process_document_enhanced(self, file_path: str) -> Dict[str, Any]:
        """
        Process document with enhanced unstructured pipeline and convert to TORE format.
        
        Returns results compatible with existing TORE workflow.
        """
        if not self.available:
            raise RuntimeError("Enhanced unstructured processor not available")
        
        self.logger.info(f"Processing document with enhanced unstructured pipeline: {file_path}")
        start_time = time.time()
        
        try:
            # Parse with enhanced processor (YOUR EXACT REQUIREMENTS)
            enhanced_elements = self.processor.parse_pdf_to_elements(file_path)
            
            # Convert to TORE-compatible format
            document_elements = self._convert_to_tore_elements(enhanced_elements)
            page_analyses = self._create_page_analyses(enhanced_elements)
            extracted_content = self._create_extracted_content(enhanced_elements)
            
            processing_time = time.time() - start_time
            
            # Create comprehensive results matching TORE expectations
            results = {
                'success': True,
                'enhanced_elements': enhanced_elements,  # Raw enhanced elements
                'document_elements': document_elements,   # TORE-compatible elements
                'page_analyses': page_analyses,          # Page analysis objects
                'extracted_content': extracted_content,  # ExtractedContent object
                'processing_time': processing_time,
                'element_count': len(enhanced_elements),
                'pages_processed': len(set(elem.metadata.get('page_number', 1) for elem in enhanced_elements)),
                'metadata': {
                    'extraction_method': 'enhanced_unstructured',
                    'strategy': 'hi_res',
                    'processor_version': '1.0.0'
                }
            }
            
            self.logger.info(f"Enhanced processing completed: {len(enhanced_elements)} elements in {processing_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Enhanced processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _convert_to_tore_elements(self, enhanced_elements: List[EnhancedElement]) -> List[DocumentElement]:
        """Convert enhanced elements to TORE DocumentElement format."""
        tore_elements = []
        
        element_type_mapping = {
            'Title': ElementType.HEADING,
            'NarrativeText': ElementType.PARAGRAPH,
            'Table': ElementType.TABLE,
            'Image': ElementType.IMAGE,
            'ListItem': ElementType.LIST,
            'Header': ElementType.HEADER,
            'Footer': ElementType.FOOTER,
            'FigureCaption': ElementType.CAPTION,
            'CodeSnippet': ElementType.CODE,
            'UncategorizedText': ElementType.TEXT,
            'Text': ElementType.TEXT,
            'PageBreak': ElementType.TEXT,
            'PageNumber': ElementType.TEXT,
            'Address': ElementType.TEXT,
            'EmailAddress': ElementType.TEXT,
            'Formula': ElementType.TEXT
        }
        
        for enhanced_elem in enhanced_elements:
            # Map element type
            element_type = element_type_mapping.get(enhanced_elem.type, ElementType.TEXT)
            
            # Extract coordinates
            coordinates = enhanced_elem.metadata.get('coordinates', {})
            if isinstance(coordinates, dict) and 'bbox' in coordinates:
                bbox = tuple(coordinates['bbox'])
            else:
                bbox = (0, 0, 0, 0)
            
            # Create TORE DocumentElement
            tore_element = DocumentElement(
                element_type=element_type,
                content=enhanced_elem.text or "",
                bbox=bbox,
                page_number=enhanced_elem.metadata.get('page_number', 1),
                confidence=enhanced_elem.metadata.get('detection_class_prob', 0.95),
                metadata={
                    **enhanced_elem.metadata,
                    'original_type': enhanced_elem.type,
                    'element_id': enhanced_elem.element_id,
                    'extraction_method': 'enhanced_unstructured'
                }
            )
            
            tore_elements.append(tore_element)
        
        return tore_elements
    
    def _create_page_analyses(self, enhanced_elements: List[EnhancedElement]) -> List[PageAnalysis]:
        """Create PageAnalysis objects from enhanced elements."""
        # Group elements by page
        pages = {}
        for elem in enhanced_elements:
            page_num = elem.metadata.get('page_number', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(elem)
        
        page_analyses = []
        
        for page_num in sorted(pages.keys()):
            page_elements = pages[page_num]
            
            # Convert to TORE elements for this page
            tore_elements = []
            for enhanced_elem in page_elements:
                element_type = self._map_element_type(enhanced_elem.type)
                coordinates = enhanced_elem.metadata.get('coordinates', {})
                bbox = tuple(coordinates.get('bbox', [0, 0, 0, 0]))
                
                tore_elem = DocumentElement(
                    element_type=element_type,
                    content=enhanced_elem.text or "",
                    bbox=bbox,
                    page_number=page_num,
                    confidence=enhanced_elem.metadata.get('detection_class_prob', 0.95),
                    metadata=enhanced_elem.metadata
                )
                tore_elements.append(tore_elem)
            
            # Analyze page characteristics
            has_tables = any(elem.type == 'Table' for elem in page_elements)
            has_images = any(elem.type == 'Image' for elem in page_elements)
            
            # Create text regions from elements
            text_regions = []
            for elem in page_elements:
                if elem.text and elem.text.strip():
                    coordinates = elem.metadata.get('coordinates', {})
                    bbox = coordinates.get('bbox', [0, 0, 0, 0])
                    text_regions.append({
                        'bbox': bbox,
                        'text': elem.text,
                        'confidence': elem.metadata.get('detection_class_prob', 0.95)
                    })
            
            # Create reading order (simple sequential)
            reading_order = list(range(len(tore_elements)))
            
            # Calculate quality score
            elements_with_coords = sum(1 for elem in page_elements 
                                     if elem.metadata.get('coordinates', {}).get('bbox', [0,0,0,0]) != [0,0,0,0])
            quality_score = elements_with_coords / len(page_elements) if page_elements else 0.0
            
            page_analysis = PageAnalysis(
                page_number=page_num,
                elements=tore_elements,
                layout_type="enhanced_unstructured",
                column_count=1,  # Could be enhanced with layout analysis
                has_tables=has_tables,
                has_images=has_images,
                text_regions=text_regions,
                reading_order=reading_order,
                quality_score=quality_score
            )
            
            page_analyses.append(page_analysis)
        
        return page_analyses
    
    def _create_extracted_content(self, enhanced_elements: List[EnhancedElement]) -> ExtractedContent:
        """Create ExtractedContent object from enhanced elements."""
        
        # Separate elements by type
        text_elements = []
        tables = []
        images = []
        
        for enhanced_elem in enhanced_elements:
            element_type = self._map_element_type(enhanced_elem.type)
            coordinates = enhanced_elem.metadata.get('coordinates', {})
            bbox = tuple(coordinates.get('bbox', [0, 0, 0, 0]))
            
            # Create TORE DocumentElement
            tore_elem = DocumentElement(
                element_type=element_type,
                content=enhanced_elem.text or "",
                bbox=bbox,
                page_number=enhanced_elem.metadata.get('page_number', 1),
                confidence=enhanced_elem.metadata.get('detection_class_prob', 0.95),
                metadata=enhanced_elem.metadata
            )
            
            if enhanced_elem.type == 'Table':
                # Create ExtractedTable
                table_html = enhanced_elem.metadata.get('text_as_html', '')
                table_data = self._parse_table_html(table_html) if table_html else []
                
                extracted_table = ExtractedTable(
                    page_number=enhanced_elem.metadata.get('page_number', 1),
                    bbox=bbox,
                    data=table_data,
                    headers=table_data[0] if table_data else [],
                    confidence=enhanced_elem.metadata.get('detection_class_prob', 0.95),
                    metadata={
                        **enhanced_elem.metadata,
                        'text_as_html': table_html,
                        'extraction_method': 'enhanced_unstructured'
                    }
                )
                tables.append(extracted_table)
                
            elif enhanced_elem.type == 'Image':
                # Create ExtractedImage
                image_base64 = enhanced_elem.metadata.get('image_base64', '')
                image_mime_type = enhanced_elem.metadata.get('image_mime_type', 'image/png')
                
                if image_base64:
                    import base64
                    try:
                        image_data = base64.b64decode(image_base64)
                        
                        extracted_image = ExtractedImage(
                            page_number=enhanced_elem.metadata.get('page_number', 1),
                            bbox=bbox,
                            image_data=image_data,
                            format=image_mime_type.split('/')[-1] if '/' in image_mime_type else 'png',
                            width=0,  # Could be extracted from image data
                            height=0,  # Could be extracted from image data
                            caption=enhanced_elem.text,
                            metadata={
                                **enhanced_elem.metadata,
                                'extraction_method': 'enhanced_unstructured'
                            }
                        )
                        images.append(extracted_image)
                    except Exception as e:
                        self.logger.warning(f"Failed to decode image: {e}")
            
            # Add to text elements
            text_elements.append(tore_elem)
        
        # Create ExtractedContent
        extracted_content = ExtractedContent(
            text_elements=text_elements,
            tables=tables,
            images=images,
            metadata={
                'extraction_method': 'enhanced_unstructured',
                'total_elements': len(enhanced_elements),
                'element_types': list(set(elem.type for elem in enhanced_elements)),
                'pages_processed': len(set(elem.metadata.get('page_number', 1) for elem in enhanced_elements))
            },
            extraction_time=0.0,  # Will be set by caller
            quality_score=0.95  # High quality from unstructured
        )
        
        return extracted_content
    
    def _map_element_type(self, enhanced_type: str) -> ElementType:
        """Map enhanced element type to TORE ElementType."""
        mapping = {
            'Title': ElementType.HEADING,
            'NarrativeText': ElementType.PARAGRAPH,
            'Table': ElementType.TABLE,
            'Image': ElementType.IMAGE,
            'ListItem': ElementType.LIST,
            'Header': ElementType.HEADER,
            'Footer': ElementType.FOOTER,
            'FigureCaption': ElementType.CAPTION,
            'CodeSnippet': ElementType.CODE,
            'UncategorizedText': ElementType.TEXT,
            'Text': ElementType.TEXT,
            'PageBreak': ElementType.TEXT,
            'PageNumber': ElementType.TEXT,
            'Address': ElementType.TEXT,
            'EmailAddress': ElementType.TEXT,
            'Formula': ElementType.TEXT
        }
        return mapping.get(enhanced_type, ElementType.TEXT)
    
    def _parse_table_html(self, html: str) -> List[List[str]]:
        """Parse HTML table to list of lists."""
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            
            if table:
                rows = []
                for tr in table.find_all('tr'):
                    row = []
                    for td in tr.find_all(['td', 'th']):
                        row.append(td.get_text(strip=True))
                    if row:
                        rows.append(row)
                return rows
        except ImportError:
            self.logger.warning("BeautifulSoup not available for HTML table parsing")
        except Exception as e:
            self.logger.warning(f"Failed to parse table HTML: {e}")
        
        return []
    
    def export_enhanced_results(self, enhanced_elements: List[EnhancedElement], 
                               output_dir: str) -> Dict[str, str]:
        """
        Export enhanced results to JSON and HTML as per your requirements.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Export JSON
        json_path = output_path / "parsed_output.json"
        self.processor.save_elements_to_json(enhanced_elements, str(json_path))
        
        # Export HTML
        html_path = output_path / "parsed_preview.html"
        self.processor.save_html_preview(enhanced_elements, str(html_path))
        
        self.logger.info(f"Enhanced results exported to {output_dir}")
        
        return {
            'json_path': str(json_path),
            'html_path': str(html_path)
        }
    
    def integrate_with_document_processor(self, document_processor):
        """
        Integration hook to enhance existing DocumentProcessor.
        
        This allows the enhanced unstructured processing to be used
        as an alternative or supplement to existing extraction methods.
        """
        
        # Store reference to original extract method
        original_extract = document_processor.content_extractor.extract_content
        
        def enhanced_extract(file_path: str, page_analyses: List[PageAnalysis] = None):
            """Enhanced extraction method."""
            
            # Try enhanced unstructured first
            if self.available:
                try:
                    self.logger.info(f"Using enhanced unstructured extraction for: {file_path}")
                    results = self.process_document_enhanced(file_path)
                    
                    if results['success']:
                        # Update extraction time
                        extracted_content = results['extracted_content']
                        extracted_content.extraction_time = results['processing_time']
                        return extracted_content
                    else:
                        self.logger.warning(f"Enhanced extraction failed, falling back: {results.get('error')}")
                        
                except Exception as e:
                    self.logger.warning(f"Enhanced extraction error, falling back: {e}")
            
            # Fallback to original method
            return original_extract(file_path, page_analyses)
        
        # Replace the extraction method
        document_processor.content_extractor.extract_content = enhanced_extract
        self.logger.info("Enhanced unstructured extraction integrated with DocumentProcessor")


def integrate_enhanced_unstructured(settings: Settings) -> EnhancedUnstructuredIntegration:
    """
    Factory function to create and return enhanced unstructured integration.
    
    Use this in main TORE workflow to get enhanced processing capabilities.
    """
    return EnhancedUnstructuredIntegration(settings)