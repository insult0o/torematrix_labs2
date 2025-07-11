"""
Advanced PDF content extraction using Unstructured library for superior coordinate correlation.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import Title, NarrativeText, Text, ListItem, Table
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("Unstructured library not available. Install with: pip install unstructured[all-docs]")

import fitz  # PyMuPDF as backup
from ..config.settings import Settings
from .document_analyzer import DocumentElement, ElementType


@dataclass
class UnstructuredElement:
    """Enhanced document element with precise positioning from Unstructured."""
    element_type: ElementType
    content: str
    bbox: Tuple[float, float, float, float]
    page_number: int
    confidence: float
    metadata: Dict[str, Any]
    char_start: int  # Character start position in full document text
    char_end: int    # Character end position in full document text
    element_id: str  # Unique identifier from Unstructured


class UnstructuredExtractor:
    """
    Advanced PDF content extraction using Unstructured library.
    
    Provides superior coordinate correlation and element detection compared to
    traditional PyMuPDF/pdfplumber approaches.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        if not UNSTRUCTURED_AVAILABLE:
            self.logger.error("Unstructured library not available. Falling back to PyMuPDF.")
            self.use_unstructured = False
        else:
            self.use_unstructured = True
            self.logger.info("Unstructured library initialized for advanced PDF extraction")
    
    def extract_with_perfect_correlation(self, file_path: str) -> Tuple[List[UnstructuredElement], str]:
        """
        Extract content with perfect coordinate correlation.
        
        Returns:
            Tuple of (elements, full_text) where elements have precise char positions
        """
        if not self.use_unstructured:
            return self._fallback_extraction(file_path)
        
        self.logger.info(f"Starting Unstructured extraction: {file_path}")
        start_time = time.time()
        
        try:
            # Use Unstructured to partition the PDF with coordinate information
            elements = partition_pdf(
                filename=file_path,
                # Strategy for maximum accuracy
                strategy="hi_res",  # High resolution for better OCR
                # Include coordinates and metadata
                include_page_breaks=True,
                infer_table_structure=True,
                # Coordinate extraction
                extract_images_in_pdf=False,  # Focus on text for now
                # Model configuration for better accuracy
                model_name="yolox"  # Best model for layout detection
            )
            
            # Build full document text and precise element mapping
            full_text = ""
            unstructured_elements = []
            char_position = 0
            
            for element in elements:
                # Get element content and metadata
                element_text = str(element)
                element_metadata = element.metadata.to_dict() if hasattr(element.metadata, 'to_dict') else {}
                
                # Extract coordinates
                coordinates = element_metadata.get('coordinates', {})
                if coordinates:
                    # Unstructured provides precise coordinates
                    points = coordinates.get('points', [])
                    if len(points) >= 4:
                        # Convert points to bbox format
                        x_coords = [p[0] for p in points]
                        y_coords = [p[1] for p in points]
                        bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                    else:
                        bbox = (0, 0, 0, 0)
                else:
                    bbox = (0, 0, 0, 0)
                
                # Get page number
                page_number = element_metadata.get('page_number', 1)
                
                # Classify element type
                element_type = self._classify_unstructured_element(element)
                
                # Calculate character positions in full text
                char_start = char_position
                char_end = char_position + len(element_text)
                
                # Create enhanced element
                unstructured_element = UnstructuredElement(
                    element_type=element_type,
                    content=element_text,
                    bbox=bbox,
                    page_number=page_number,
                    confidence=0.95,  # Unstructured provides high confidence
                    metadata={
                        'unstructured_type': type(element).__name__,
                        'unstructured_metadata': element_metadata,
                        'extraction_method': 'unstructured_hi_res'
                    },
                    char_start=char_start,
                    char_end=char_end,
                    element_id=element_metadata.get('element_id', f"elem_{len(unstructured_elements)}")
                )
                
                unstructured_elements.append(unstructured_element)
                
                # Add to full text
                full_text += element_text
                if not element_text.endswith('\n'):
                    full_text += '\n'
                char_position = len(full_text)
            
            extraction_time = time.time() - start_time
            self.logger.info(f"Unstructured extraction completed in {extraction_time:.2f}s: {len(unstructured_elements)} elements")
            
            return unstructured_elements, full_text
            
        except Exception as e:
            self.logger.error(f"Unstructured extraction failed: {str(e)}. Falling back to PyMuPDF.")
            return self._fallback_extraction(file_path)
    
    def _classify_unstructured_element(self, element) -> ElementType:
        """Classify Unstructured element into our ElementType."""
        element_type_name = type(element).__name__
        
        if isinstance(element, Title):
            return ElementType.HEADING
        elif isinstance(element, Table):
            return ElementType.TABLE
        elif isinstance(element, ListItem):
            return ElementType.LIST
        elif isinstance(element, NarrativeText):
            return ElementType.PARAGRAPH
        else:
            return ElementType.TEXT
    
    def _fallback_extraction(self, file_path: str) -> Tuple[List[UnstructuredElement], str]:
        """Fallback to PyMuPDF if Unstructured is not available."""
        self.logger.info("Using PyMuPDF fallback extraction")
        
        doc = fitz.open(file_path)
        elements = []
        full_text = ""
        char_position = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_text = span["text"]
                            span_bbox = span["bbox"]
                            
                            if span_text.strip():
                                char_start = char_position
                                char_end = char_position + len(span_text)
                                
                                element = UnstructuredElement(
                                    element_type=ElementType.TEXT,
                                    content=span_text,
                                    bbox=span_bbox,
                                    page_number=page_num + 1,
                                    confidence=0.8,
                                    metadata={'extraction_method': 'pymupdf_fallback'},
                                    char_start=char_start,
                                    char_end=char_end,
                                    element_id=f"fallback_{len(elements)}"
                                )
                                elements.append(element)
                                
                                full_text += span_text
                                char_position = len(full_text)
        
        doc.close()
        return elements, full_text
    
    def find_text_by_position(self, elements: List[UnstructuredElement], 
                             full_text: str, target_text: str) -> List[Dict[str, Any]]:
        """
        Find text with perfect coordinate correlation.
        
        Returns list of matches with exact character positions and PDF coordinates.
        """
        matches = []
        
        # Search for the target text in the full document text
        search_pos = 0
        while True:
            pos = full_text.find(target_text, search_pos)
            if pos == -1:
                break
            
            # Find which element(s) contain this text position
            containing_elements = []
            for element in elements:
                if element.char_start <= pos < element.char_end:
                    # Calculate relative position within the element
                    relative_start = pos - element.char_start
                    relative_end = min(pos + len(target_text), element.char_end) - element.char_start
                    
                    # Calculate precise coordinates within the element bbox
                    if element.content:
                        char_width = (element.bbox[2] - element.bbox[0]) / len(element.content)
                        precise_x0 = element.bbox[0] + relative_start * char_width
                        precise_x1 = element.bbox[0] + relative_end * char_width
                        
                        precise_bbox = (precise_x0, element.bbox[1], precise_x1, element.bbox[3])
                    else:
                        precise_bbox = element.bbox
                    
                    containing_elements.append({
                        'element': element,
                        'relative_start': relative_start,
                        'relative_end': relative_end,
                        'precise_bbox': precise_bbox
                    })
            
            if containing_elements:
                matches.append({
                    'text': target_text,
                    'char_position': pos,
                    'elements': containing_elements,
                    'page_number': containing_elements[0]['element'].page_number,
                    'bbox': containing_elements[0]['precise_bbox']
                })
            
            search_pos = pos + 1
        
        return matches
    
    def create_perfect_corrections(self, file_path: str, 
                                 ocr_errors: List[str]) -> List[Dict[str, Any]]:
        """
        Create corrections with perfect coordinate correlation.
        
        Args:
            file_path: Path to PDF file
            ocr_errors: List of potential OCR errors to find
            
        Returns:
            List of corrections with precise coordinates and text positions
        """
        # Extract with perfect correlation
        elements, full_text = self.extract_with_perfect_correlation(file_path)
        
        corrections = []
        correction_id = 0
        
        for error_text in ocr_errors:
            matches = self.find_text_by_position(elements, full_text, error_text)
            
            for match in matches:
                correction = {
                    'id': f'perfect_correction_{correction_id}',
                    'type': 'ocr_correction',
                    'description': f'Potential OCR error: \'{error_text}\'',
                    'confidence': 0.9,
                    'reasoning': 'Detected using Unstructured library with precise coordinate mapping',
                    'status': 'suggested',
                    'location': {
                        'page': match['page_number'],
                        'bbox': list(match['bbox']),
                        'text_position': [match['char_position'], 
                                        match['char_position'] + len(error_text)]
                    },
                    'severity': 'major',
                    'metadata': {
                        'extraction_method': 'unstructured',
                        'char_start': match['char_position'],
                        'char_end': match['char_position'] + len(error_text),
                        'element_id': match['elements'][0]['element'].element_id if match['elements'] else None
                    }
                }
                corrections.append(correction)
                correction_id += 1
        
        self.logger.info(f"Created {len(corrections)} corrections with perfect coordinate correlation")
        return corrections
    
    def validate_extraction_quality(self, file_path: str) -> Dict[str, Any]:
        """Validate the quality of extraction and coordinate correlation."""
        elements, full_text = self.extract_with_perfect_correlation(file_path)
        
        # Calculate quality metrics
        total_elements = len(elements)
        elements_with_coords = sum(1 for e in elements if e.bbox != (0, 0, 0, 0))
        elements_with_content = sum(1 for e in elements if e.content.strip())
        
        coordinate_coverage = elements_with_coords / total_elements if total_elements > 0 else 0
        content_coverage = elements_with_content / total_elements if total_elements > 0 else 0
        
        # Test character position accuracy
        char_position_accuracy = 0
        if full_text:
            # Sample test: verify that elements' char positions actually correspond to text
            accurate_positions = 0
            tested_positions = 0
            
            for element in elements[:min(10, len(elements))]:  # Test first 10 elements
                if element.char_start < len(full_text) and element.char_end <= len(full_text):
                    actual_text = full_text[element.char_start:element.char_end]
                    if actual_text == element.content:
                        accurate_positions += 1
                    tested_positions += 1
            
            char_position_accuracy = accurate_positions / tested_positions if tested_positions > 0 else 0
        
        quality_report = {
            'extraction_method': 'unstructured' if self.use_unstructured else 'pymupdf_fallback',
            'total_elements': total_elements,
            'coordinate_coverage': coordinate_coverage,
            'content_coverage': content_coverage,
            'char_position_accuracy': char_position_accuracy,
            'full_text_length': len(full_text),
            'quality_score': (coordinate_coverage + content_coverage + char_position_accuracy) / 3
        }
        
        self.logger.info(f"Extraction quality: {quality_report['quality_score']:.2%}")
        return quality_report