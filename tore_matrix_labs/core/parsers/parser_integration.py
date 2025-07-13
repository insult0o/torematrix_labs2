"""
Parser Framework Integration with Document Processor

This module provides integration between the new parser framework
and the existing document processing pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_parser import ParseResult, ParserConfiguration, ParsingStrategy
from .document_parser_factory import DocumentParserFactory
from .elements.base_element import ParsedElement, ElementType
from ..content_extractor import ExtractedContent
from ..document_analyzer import DocumentElement as LegacyTextElement
from ..document_analyzer import PageAnalysis
from ...models.document_models import Document


logger = logging.getLogger(__name__)


class ParserIntegration:
    """Integrates parser framework with existing document processing pipeline"""
    
    def __init__(self, config: Optional[ParserConfiguration] = None):
        """
        Initialize parser integration
        
        Args:
            config: Parser configuration
        """
        self.config = config or ParserConfiguration()
        self.logger = logging.getLogger(__name__)
    
    def parse_with_framework(self, file_path: str) -> Optional[ParseResult]:
        """
        Parse document using the parser framework
        
        Args:
            file_path: Path to document
            
        Returns:
            ParseResult or None if parsing fails
        """
        path = Path(file_path)
        
        # Create parser
        parser = DocumentParserFactory.create_parser(path, self.config)
        if not parser:
            self.logger.error(f"No parser available for {path}")
            return None
        
        # Parse document
        try:
            result = parser.parse(path)
            self.logger.info(f"Parsed {path} with {parser.__class__.__name__}")
            return result
        except Exception as e:
            self.logger.error(f"Parsing failed: {e}")
            return None
    
    def convert_to_extracted_content(self, parse_result: ParseResult) -> ExtractedContent:
        """
        Convert ParseResult to legacy ExtractedContent format
        
        Args:
            parse_result: Result from parser framework
            
        Returns:
            ExtractedContent for existing pipeline
        """
        # Group elements by type
        text_elements = []
        tables = []
        images = []
        
        for element in parse_result.elements:
            if element.element_type in [ElementType.TEXT, ElementType.HEADING, 
                                        ElementType.PARAGRAPH, ElementType.LIST]:
                # Convert to legacy text element
                legacy_elem = self._convert_text_element(element)
                if legacy_elem:
                    text_elements.append(legacy_elem)
            
            elif element.element_type == ElementType.TABLE:
                # Convert table element
                table_data = self._convert_table_element(element)
                if table_data:
                    tables.append(table_data)
            
            elif element.element_type in [ElementType.IMAGE, ElementType.FIGURE]:
                # Convert image element
                image_data = self._convert_image_element(element)
                if image_data:
                    images.append(image_data)
        
        # Create ExtractedContent
        extracted_content = ExtractedContent(
            text_elements=text_elements,
            tables=tables,
            images=images,
            metadata=parse_result.metadata.__dict__ if parse_result.metadata else {},
            extraction_time=parse_result.processing_time,
            quality_score=parse_result.quality.overall_score if parse_result.quality else 0.8
        )
        
        return extracted_content
    
    def enhance_page_analyses(self, page_analyses: List[PageAnalysis], 
                            parse_result: ParseResult) -> List[PageAnalysis]:
        """
        Enhance existing page analyses with parser framework results
        
        Args:
            page_analyses: Existing page analyses
            parse_result: Parser framework results
            
        Returns:
            Enhanced page analyses
        """
        # Create element lookup by page
        elements_by_page: Dict[int, List[ParsedElement]] = {}
        
        for element in parse_result.elements:
            if element.bbox:
                page = element.bbox.page
                if page not in elements_by_page:
                    elements_by_page[page] = []
                elements_by_page[page].append(element)
        
        # Enhance each page analysis
        for page_analysis in page_analyses:
            page_num = page_analysis.page_number
            
            if page_num in elements_by_page:
                page_elements = elements_by_page[page_num]
                
                # Update element counts
                page_analysis.text_elements = len([e for e in page_elements 
                    if e.element_type in [ElementType.TEXT, ElementType.PARAGRAPH]])
                page_analysis.tables = len([e for e in page_elements 
                    if e.element_type == ElementType.TABLE])
                page_analysis.images = len([e for e in page_elements 
                    if e.element_type in [ElementType.IMAGE, ElementType.FIGURE]])
                
                # Update quality score based on element confidence
                if page_elements:
                    avg_confidence = sum(e.metadata.confidence for e in page_elements) / len(page_elements)
                    # Blend with existing quality score
                    page_analysis.quality_score = (page_analysis.quality_score + avg_confidence) / 2
        
        return page_analyses
    
    def _convert_text_element(self, element: ParsedElement) -> Optional[LegacyTextElement]:
        """Convert ParsedElement to legacy TextElement"""
        try:
            # Create legacy text element
            legacy_elem = LegacyTextElement(
                element_type=element.element_type.value,
                content=element.get_text(),
                page_number=element.bbox.page if element.bbox else 0,
                bbox=(element.bbox.x0, element.bbox.y0, element.bbox.x1, element.bbox.y1) 
                     if element.bbox else None,
                confidence=element.metadata.confidence,
                style=element.metadata.style
            )
            return legacy_elem
        except Exception as e:
            self.logger.warning(f"Failed to convert text element: {e}")
            return None
    
    def _convert_table_element(self, element: ParsedElement) -> Optional[Dict[str, Any]]:
        """Convert table ParsedElement to legacy format"""
        try:
            # Get HTML representation
            if hasattr(element, 'to_html'):
                html = element.to_html()
            else:
                html = element.get_text()
            
            table_data = {
                'html': html,
                'text': element.get_text(),
                'page_number': element.bbox.page if element.bbox else 0,
                'bbox': (element.bbox.x0, element.bbox.y0, element.bbox.x1, element.bbox.y1) 
                       if element.bbox else None,
                'confidence': element.metadata.confidence
            }
            
            # Add dimensions if available
            if hasattr(element, '_row_count'):
                table_data['rows'] = element._row_count
                table_data['columns'] = element._column_count
            
            return table_data
        except Exception as e:
            self.logger.warning(f"Failed to convert table element: {e}")
            return None
    
    def _convert_image_element(self, element: ParsedElement) -> Optional[Dict[str, Any]]:
        """Convert image ParsedElement to legacy format"""
        try:
            image_data = {
                'page_number': element.bbox.page if element.bbox else 0,
                'bbox': (element.bbox.x0, element.bbox.y0, element.bbox.x1, element.bbox.y1) 
                       if element.bbox else None,
                'alt_text': element.get_text(),
                'confidence': element.metadata.confidence
            }
            
            # Add image data if available
            if hasattr(element, 'get_base64'):
                base64_data = element.get_base64()
                if base64_data:
                    image_data['data'] = base64_data
            
            # Add dimensions if available
            if hasattr(element, 'get_dimensions'):
                width, height = element.get_dimensions()
                if width and height:
                    image_data['width'] = width
                    image_data['height'] = height
            
            return image_data
        except Exception as e:
            self.logger.warning(f"Failed to convert image element: {e}")
            return None


class EnhancedDocumentProcessor:
    """Enhanced document processor that uses the parser framework"""
    
    def __init__(self, base_processor, parser_config: Optional[ParserConfiguration] = None):
        """
        Initialize enhanced processor
        
        Args:
            base_processor: Existing DocumentProcessor instance
            parser_config: Parser configuration
        """
        self.base_processor = base_processor
        self.parser_integration = ParserIntegration(parser_config)
        self.logger = logging.getLogger(__name__)
    
    def process_document(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process document with parser framework enhancement
        
        Args:
            file_path: Path to document
            **kwargs: Additional arguments for base processor
            
        Returns:
            Processing results
        """
        # Try parser framework first
        parse_result = self.parser_integration.parse_with_framework(file_path)
        
        if parse_result and parse_result.success:
            self.logger.info("Using parser framework results")
            
            # Convert to legacy format
            extracted_content = self.parser_integration.convert_to_extracted_content(parse_result)
            
            # Enhance the existing processing pipeline
            # This is a simplified approach - you might want to integrate more deeply
            kwargs['parser_extracted_content'] = extracted_content
            kwargs['parser_result'] = parse_result
        
        # Continue with normal processing
        return self.base_processor.process_document(file_path, **kwargs)